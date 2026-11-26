(() => {
  'use strict';
  const {cities, provinces} = window.atlasData;
  const map = window.atlasMap;
  const labelLayout = window.atlasLabels;
  const tiers = ['一线', '新一线', '二线', '三线', '四线', '五线'];
  const colors = ['#9b3454', '#ad5141', '#936820', '#926074', '#6c6279', '#82674e'];
  // One outline per tier. The same glyphs appear on the map, legend and table.
  const symbols = [
    'M0,-1.22 .29,-.38 1.14,-.38 .48,.15 .73,1 0,.49 -.73,1 -.48,.15 -1.14,-.38 -.29,-.38Z',
    'M0,-1.17 1.05,0 0,1.17 -1.05,0Z',
    'M0,-1.12 1.03,.86 -1.03,.86Z',
    'M-.87,-.87H.87V.87H-.87Z',
    'M0,-1 .87,-.5 .87,.5 0,1 -.87,.5 -.87,-.5Z',
    'M0,-.88A.88,.88 0 1 1 0,.88A.88,.88 0 1 1 0,-.88Z',
  ];
  const byId = id => document.getElementById(id);
  const ui = Object.fromEntries([
    'query', 'province', 'legend', 'reset', 'atlas', 'points', 'map-stage',
    'provinces', 'province-labels', 'district-lines', 'boundaries', 'sea-card',
    'sea-detail', 'sea-points', 'sea-mini', 'sea-open', 'marker-count', 'table-tier',
    'zoom-in', 'zoom-out', 'zoom-fit', 'city-leaders', 'city-labels', 'sea-labels',
    'tooltip', 'inset', 'national', 'map-title', 'map-hint', 'city-detail',
    'total', 'counts', 'sort', 'city-rows', 'empty', 'reference-count', 'reference-rows',
    'province-summary',
  ].map(id => [id, byId(id)]));
  const allTiers = tiers.map((_, i) => i);
  const compactScreen = matchMedia('(max-width: 720px), (pointer: coarse) and (max-width: 960px)');
  const defaultTiers = () => new Set(compactScreen.matches ? [0, 1, 2] : allTiers);
  const state = {
    province: '', tiers: defaultTiers(), customTiers: false, query: '', selected: '', inset: false,
  };
  const lookup = new Map(cities.map(city => [city[1], city]));
  const collator = new Intl.Collator('zh-CN');
  const ns = 'http://www.w3.org/2000/svg';
  const zoomSteps = [1, 1.23, 1.7, 2.35, 3.25, 4.5, 6, 8];
  let camera = {zoom: 1, center: null};
  let fittedView;
  let cameraFrame;
  let mapScope;
  let mainMarkers = [];
  let markerScale;

  function resetCamera() {
    camera = {zoom: 1, center: null};
  }

  const swatch = tier => '<svg class="symbol" aria-hidden="true" viewBox="-1.25 -1.25 2.5 2.5">' +
    '<path d="' + symbols[tier] + '" fill="' + colors[tier] + '"></path></svg>';
  const cityDescription = city => city[0] + ' · ' + provinces[city[2]] + ' · ' + tiers[city[3]] + '第 ' + city[4] + ' 位（图序）';
  const rank = (a, b) => a[3] - b[3] || a[4] - b[4];
  const orders = {
    rank,
    province: (a, b) => collator.compare(provinces[a[2]], provinces[b[2]]) || rank(a, b),
    tier: (a, b) => a[3] - b[3] || collator.compare(a[0], b[0]),
    name: (a, b) => collator.compare(a[0], b[0]),
  };

  for (const [code, name] of Object.entries(provinces)) ui.province.add(new Option(name, code));
  ui.legend.innerHTML = '<label><input type="checkbox" data-tier="all">全选</label>' +
    tiers.map((name, i) => '<label><input type="checkbox" data-tier="' + i + '">' + swatch(i) + name + '</label>').join('');
  for (const [i, name] of tiers.entries()) ui['table-tier'].add(new Option(name, String(i)));

  const provincePaths = new Map();
  for (const [code, [outline]] of Object.entries(map.provinces)) {
    const shape = document.createElementNS(ns, 'path');
    shape.dataset.province = code;
    shape.setAttribute('d', outline);
    shape.setAttribute('fill-rule', 'evenodd');
    shape.setAttribute('aria-label', provinces[code]);
    ui.provinces.append(shape);
    provincePaths.set(code, shape);
  }
  ui.boundaries.setAttribute('d', map.boundary);
  for (const node of document.querySelectorAll('.sea-land')) node.setAttribute('d', map.seaLand);
  for (const node of document.querySelectorAll('.sea-boundary')) node.setAttribute('d', map.seaBoundary);
  const provinceLabels = [
    ['65','新疆'], ['54','西藏'], ['63','青海'], ['15','内蒙古'],
    ['23','黑龙江'], ['51','四川'], ['53','云南'], ['45','广西'], ['71','台湾'], ['46','海南'],
  ];
  for (const [code, name] of provinceLabels) {
    // Province anchors come from the same projected geometry the view uses.
    const [, anchor] = map.provinces[code];
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', anchor[0]);
    label.setAttribute('y', anchor[1]);
    label.textContent = name;
    ui['province-labels'].append(label);
  }

  function stats(list) {
    const counts = Array(6).fill(0);
    for (const city of list) counts[city[3]]++;
    return counts;
  }

  const provinceRows = Object.keys(provinces).map(code => {
    const list = cities.filter(city => city[2] === code && !city[5]);
    return '<tr><th scope="row"><button class="city-link" data-province="' + code + '">' +
      provinces[code] + '</button></th><td>' + list.length + '</td>' +
      stats(list).map(n => '<td>' + n + '</td>').join('') + '</tr>';
  });
  ui['province-summary'].innerHTML = provinceRows.join('');

  function fittedBox(svg, bounds, padding) {
    const [left, top, right, bottom] = bounds;
    const size = svg.getBoundingClientRect();
    const aspect = Math.max(1, size.width) / Math.max(1, size.height);
    const width = Math.max(right - left, (bottom - top) * aspect) * padding;
    const height = width / aspect;
    return {center: [(left + right) / 2, (top + bottom) / 2], width, height};
  }

  function fitInset() {
    const {center: [x, y], width, height} = fittedBox(ui['sea-mini'], map.seaFrame, 1.18);
    ui['sea-mini'].setAttribute('viewBox', [x - width / 2, y - height / 2, width, height].join(' '));
    return width / (ui['sea-mini'].clientWidth || 1);
  }

  function currentView() {
    const {width, height} = fittedView;
    return {
      center: camera.center || fittedView.center,
      width: width / camera.zoom,
      height: height / camera.zoom,
    };
  }

  function clampCenter() {
    const {center: [x, y], width, height} = currentView();
    const [baseX, baseY] = fittedView.center;
    const marginX = (fittedView.width - width) / 2;
    const marginY = (fittedView.height - height) / 2;
    camera.center = [
      Math.max(baseX - marginX, Math.min(baseX + marginX, x)),
      Math.max(baseY - marginY, Math.min(baseY + marginY, y)),
    ];
  }

  function positionMarker(node, point, size) {
    node.setAttribute('transform', 'translate(' + point.join(' ') + ') scale(' + size + ')');
  }

  function paintLabels(left, top, width) {
    const rect = ui.atlas.getBoundingClientRect();
    const units = width / (rect.width || 1);
    const obstacles = [];
    for (const control of [ui['zoom-in'].parentElement, ui['sea-card']]) {
      if (control.hidden) continue;
      const box = control.getBoundingClientRect();
      obstacles.push({
        left: box.left - rect.left - 4, right: box.right - rect.left + 4,
        top: box.top - rect.top - 4, bottom: box.bottom - rect.top + 4,
      });
    }

    const showProvinces = !state.province && camera.zoom < 1.6;
    ui['province-labels'].toggleAttribute('hidden', !showProvinces);
    if (showProvinces) {
      const font = rect.width < 600 ? 9 : 13;
      ui['province-labels'].style.fontSize = (font * units) + 'px';
      ui['province-labels'].style.strokeWidth = (2 * units) + 'px';
      for (const [code, name] of provinceLabels) {
        const [, [x, y]] = map.provinces[code];
        const px = (x - left) / units;
        const py = (y - top) / units;
        const halfWidth = (name.length * font * 1.13 + 6) / 2;
        obstacles.push({left: px - halfWidth, right: px + halfWidth, top: py - font, bottom: py + font});
      }
    }

    const focus = state.selected || (mainMarkers.length === 1 ? mainMarkers[0].city[1] : '');
    const level = zoomSteps.indexOf(camera.zoom);
    const placed = labelLayout.place({
      markers: mainMarkers, width: rect.width, height: rect.height, left, top, units,
      level, local: !!state.province, focus, obstacles, colors,
    });
    ui['city-leaders'].replaceChildren(placed.leaders);
    ui['city-labels'].replaceChildren(placed.labels);
    const wide = rect.width >= labelLayout.narrowMap;
    const tier = labelLayout.priorityTier(rect.width, level);
    ui['map-hint'].textContent = state.inset ? '三沙位于永兴岛附近。' :
      wide && tier < 5 ? '当前视野优先显示' + tiers[tier] + '及以上城市名。' +
        (level ? '点击城市名查看详情。' : '点击 ＋ 展开二线城市名。') :
      wide ? '显示当前视野内的各档城市名。点击城市名查看详情。' :
        '放大可看到更多城市名。点击名称查看详情。';
  }

  function paintCamera() {
    const {center: [x, y], width, height} = currentView();
    const left = x - width / 2;
    const top = y - height / 2;
    ui.atlas.setAttribute('viewBox', [left, top, width, height].join(' '));
    const scale = width / (ui.atlas.clientWidth || 1);
    // During a drag labels move with the map. Reflow after release so names
    // do not blink in and out while the reader is moving the view.
    if (scale !== markerScale) {
      for (const {node, point, size} of mainMarkers) positionMarker(node, point, scale * size);
      markerScale = scale;
    }
    if (!drag?.moved) paintLabels(left, top, width);
    ui.atlas.toggleAttribute('data-zoomed', camera.zoom > 1);
    ui['zoom-in'].disabled = camera.zoom === zoomSteps.at(-1);
    ui['zoom-out'].disabled = camera.zoom <= 1;
    ui['zoom-fit'].disabled = camera.zoom <= 1;
  }

  function scheduleCameraPaint() {
    cancelAnimationFrame(cameraFrame);
    cameraFrame = requestAnimationFrame(paintCamera);
  }

  function changeZoom(step) {
    const index = zoomSteps.indexOf(camera.zoom);
    const next = zoomSteps[index + step];
    if (next === undefined) return;
    camera.zoom = next;
    clampCenter();
    hideTooltip();
    scheduleCameraPaint();
  }

  function setView() {
    const {inset, province} = state;
    const scope = inset ? 'sea' : province;
    if (scope !== mapScope) {
      resetCamera();
      mapScope = scope;
    }
    ui['map-stage'].toggleAttribute('data-local', !!province);
    ui['sea-detail'].toggleAttribute('hidden', !inset);
    ui['sea-card'].hidden = !!province;
    ui.provinces.toggleAttribute('hidden', inset);
    ui.boundaries.toggleAttribute('hidden', inset);
    ui['district-lines'].setAttribute('d', !inset && map.districts[province] || '');
    for (const [code, shape] of provincePaths) {
      shape.classList.toggle('selected', code === province);
      shape.classList.toggle('context', !!province && code !== province);
    }
    const frame = inset ? map.seaFrame : province ? map.bounds[province] : map.frame;
    const padding = inset ? 1.18 : province ? 1.20 : 1.065;
    fittedView = fittedBox(ui.atlas, frame, padding);
    clampCenter();
  }

  function matchesScope() {
    const query = state.query.trim().replace(/市$/, '').normalize('NFKC');
    return cities.filter(city => (!state.province || city[2] === state.province) &&
      (!query || city[0].includes(query)));
  }

  function visibleCities() {
    const tier = ui['table-tier'].value;
    return matchesScope().filter(city => tier === '' || city[3] === Number(tier));
  }

  function cityButton(city, label = city[0]) {
    return '<button type="button" class="city-link" data-city="' + city[1] + '"' +
      (city[1] === state.selected ? ' aria-current="true"' : '') + '>' + label + '</button>';
  }

  function render() {
    const list = visibleCities().sort(orders[ui.sort.value]);
    const ordinary = list.filter(city => !city[5]);
    const references = list.filter(city => city[5]);
    const scoped = matchesScope();
    const markers = scoped.filter(city => state.tiers.has(city[3]));
    const selected = scoped.find(city => city[1] === state.selected);
    const scope = provinces[state.province] || '全国';
    const selection = !!(ui['table-tier'].value || state.query.trim());
    setView();
    const miniScale = state.province ? 1 : fitInset();

    ui['map-title'].textContent = state.inset ? '海南省 · 南海诸岛' : scope;
    ui.national.hidden = !state.province;
    ui.inset.hidden = state.province !== '46';
    ui.inset.textContent = state.inset ? '查看海南岛' : '查看南海附图';
    ui.province.value = state.province;
    for (const checkbox of ui.legend.querySelectorAll('input')) {
      const value = checkbox.dataset.tier;
      checkbox.checked = value === 'all' ? state.tiers.size === tiers.length : state.tiers.has(Number(value));
      if (value === 'all') checkbox.indeterminate = state.tiers.size > 0 && state.tiers.size < tiers.length;
    }

    mainMarkers = [];
    markerScale = undefined;
    const group = document.createDocumentFragment();
    const mini = document.createDocumentFragment();
    const miniLabels = document.createDocumentFragment();
    let active;
    const ordinarySize = ui.atlas.clientWidth < 600 ? 3 : 5;
    let shown = 0;
    for (const city of [...markers].reverse()) {
      const [, code, , tier, , reference, , point] = city;
      const sansha = code === '460300';
      if (!point || (state.inset && !sansha) || (state.province && !state.inset && sansha)) continue;
      const miniature = sansha && !state.province;
      const size = code === state.selected ? 8 : miniature ? 4.5 : reference ? ordinarySize + 1.5 : ordinarySize;
      const marker = document.createElementNS(ns, 'path');
      marker.dataset.city = code;
      marker.dataset.tier = tier;
      marker.setAttribute('d', symbols[tier]);
      marker.setAttribute('fill', colors[tier]);
      marker.setAttribute('class', 'marker' + (code === state.selected ? ' active' : ''));
      marker.setAttribute('role', 'img');
      marker.setAttribute('aria-label', cityDescription(city));
      if (miniature) {
        positionMarker(marker, point, size * miniScale);
        mini.append(marker);
        miniLabels.append(labelLayout.makeLabel(city, [point[0] + 7 * miniScale, point[1]], 10 * miniScale, 'start'));
      } else {
        mainMarkers.push({node: marker, point, size, city});
        if (code === state.selected) active = marker;
        else group.append(marker);
      }
      shown++;
    }
    ui.points.replaceChildren(group);
    if (active) ui.points.append(active);
    ui['sea-points'].replaceChildren(mini);
    ui['sea-labels'].replaceChildren(miniLabels);
    paintCamera();
    ui['marker-count'].textContent = '图中 ' + shown + ' 座';
    ui.total.textContent = ordinary.length;
    const countLabel = selection ? '筛选后线级分布' : scope + '线级分布';
    ui.counts.setAttribute('aria-label', countLabel);
    ui.counts.innerHTML = stats(ordinary).map((n, i) => '<span>' + swatch(i) + tiers[i] + ' ' + n + '</span>').join('');
    ui['city-rows'].innerHTML = ordinary.map(city => '<tr data-row="' + city[1] + '"' +
      (city[1] === state.selected ? ' class="active"' : '') + '><td>' + city[4] + '</td><td>' +
      cityButton(city) + '</td><td>' + provinces[city[2]] + '</td><td>' + swatch(city[3]) + tiers[city[3]] + '</td></tr>').join('');
    ui.empty.hidden = !!ordinary.length;
    ui['reference-count'].textContent = references.length + ' 座';
    byId('reference').hidden = !references.length;
    ui['reference-rows'].innerHTML = references.map(city =>
      cityButton(city, swatch(city[3]) + city[0] + ' · ' + tiers[city[3]] + ' ' + city[4])).join('');
    ui['city-detail'].hidden = !selected;
    if (selected) {
      const coord = selected[6].map(n => n.toFixed(3));
      ui['city-detail'].textContent = cityDescription(selected) + '。' +
        (selected[8] ? '城区参考位置' : '公开驻地数据的近似位置') + '，东经 ' + coord[0] + '°，北纬 ' + coord[1] + '°。' +
        (state.tiers.has(selected[3]) ? '' : ' 当前未勾选该线级的地图标记。');
    }
    hideTooltip();
  }

  function selectProvince(code) {
    resetCamera();
    state.province = code;
    state.selected = '';
    state.inset = false;
    render();
    ui['city-rows'].closest('.rows').scrollTop = 0;
  }

  function selectCity(code, origin) {
    const city = lookup.get(code);
    if (!city) return;
    if (origin !== 'map') resetCamera();
    state.province = city[2];
    state.selected = code;
    state.inset = code === '460300';
    render();
    const button = document.querySelector('[data-row="' + code + '"] button') ||
      ui['reference-rows'].querySelector('[data-city="' + code + '"]');
    const list = ui['city-rows'].closest('.rows');
    const row = button?.closest('tr');
    if (row) list.scrollTop = Math.max(0, row.offsetTop - list.offsetTop - list.clientHeight / 3);
    if (origin === 'table') {
      ui.atlas.focus({preventScroll: true});
      ui['map-stage'].scrollIntoView({block: 'nearest'});
    }
  }

  let hovered;
  let highlightedCity = '';
  let highlightedNodes = [];

  function highlightCity(code) {
    if (highlightedCity === code) return;
    for (const node of highlightedNodes) node.classList.remove('is-highlighted');
    highlightedCity = code;
    highlightedNodes = code ? [...ui.atlas.querySelectorAll(
      '[data-city="' + code + '"], [data-leader-for="' + code + '"]'
    )] : [];
    for (const node of highlightedNodes) node.classList.add('is-highlighted');
  }

  function highlightProvince(node) {
    if (hovered === node) return;
    hovered?.classList.remove('hovered');
    hovered = node;
    hovered?.classList.add('hovered');
  }

  function hideTooltip() {
    highlightProvince(undefined);
    highlightCity('');
    ui.tooltip.hidden = true;
  }

  function mapHover(event) {
    if (drag?.moved) return;
    const city = lookup.get(event.target.dataset.city);
    const province = !state.province && event.target.dataset.province;
    if (!city && !province) {
      hideTooltip();
      return;
    }
    highlightProvince(provincePaths.get(province));
    highlightCity(city?.[1] || '');
    ui.tooltip.textContent = city ? cityDescription(city) : provinces[province] + ' · 点击放大';
    ui.tooltip.hidden = false;
    const stage = ui['map-stage'].getBoundingClientRect();
    const x = Math.min(Math.max(6, event.clientX - stage.left + 12), stage.width - ui.tooltip.offsetWidth - 6);
    const y = Math.min(Math.max(6, event.clientY - stage.top + 12), stage.height - ui.tooltip.offsetHeight - 6);
    ui.tooltip.style.transform = 'translate(' + x + 'px,' + y + 'px)';
  }

  function mapClick(event) {
    if (event.target.dataset.city) selectCity(event.target.dataset.city, 'map');
    else if (!state.province && event.target.dataset.province) selectProvince(event.target.dataset.province);
    hideTooltip();
  }

  for (const svg of [ui.atlas, ui['sea-mini']]) {
    svg.addEventListener('pointermove', mapHover);
    svg.addEventListener('pointerleave', hideTooltip);
    svg.addEventListener('click', mapClick);
  }
  ui['sea-open'].addEventListener('click', () => {
    state.province = '46';
    state.inset = true;
    render();
    ui.inset.focus();
  });

  ui['zoom-in'].addEventListener('click', () => changeZoom(1));
  ui['zoom-out'].addEventListener('click', () => changeZoom(-1));
  ui['zoom-fit'].addEventListener('click', () => {
    resetCamera();
    paintCamera();
  });

  let drag;
  let suppressClick = false;
  ui.atlas.addEventListener('pointerdown', event => {
    suppressClick = false;
    if (event.button !== 0 || event.pointerType === 'touch' || camera.zoom <= 1) return;
    drag = {id: event.pointerId, x: event.clientX, y: event.clientY, moved: false};
  });
  ui.atlas.addEventListener('pointermove', event => {
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (!drag.moved) {
      if (Math.hypot(dx, dy) < 5) return;
      drag.moved = true;
      suppressClick = true;
      hideTooltip();
      ui.atlas.setPointerCapture(event.pointerId);
      ui.atlas.classList.add('dragging');
    }
    const {center: [x, y], width, height} = currentView();
    camera.center = [x - dx * width / ui.atlas.clientWidth, y - dy * height / ui.atlas.clientHeight];
    clampCenter();
    drag.x = event.clientX;
    drag.y = event.clientY;
    scheduleCameraPaint();
  });
  function endDrag(event) {
    if (drag?.id !== event.pointerId) return;
    const moved = drag.moved;
    ui.atlas.classList.remove('dragging');
    drag = undefined;
    if (moved) scheduleCameraPaint();
  }
  for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    window.addEventListener(event, endDrag);
  }
  ui.atlas.addEventListener('click', event => {
    if (!suppressClick) return;
    suppressClick = false;
    event.stopImmediatePropagation();
  }, true);

  ui.atlas.addEventListener('keydown', event => {
    if (event.key === 'Escape' && state.province) {
      event.preventDefault();
      selectProvince('');
    }
  });
  ui.legend.addEventListener('change', event => {
    const {tier} = event.target.dataset;
    state.customTiers = true;
    if (tier === 'all') state.tiers = new Set(event.target.checked ? allTiers : []);
    else if (event.target.checked) state.tiers.add(Number(tier));
    else state.tiers.delete(Number(tier));
    render();
  });
  ui.query.addEventListener('input', () => {
    state.query = ui.query.value;
    state.selected = '';
    render();
  });
  ui.query.addEventListener('keydown', event => {
    if (event.key !== 'Enter') return;
    const list = visibleCities();
    if (list.length === 1) selectCity(list[0][1], 'search');
  });
  ui.province.addEventListener('change', () => selectProvince(ui.province.value));
  ui.national.addEventListener('click', () => {
    selectProvince('');
    ui.province.focus();
  });
  ui.inset.addEventListener('click', () => {
    state.inset = !state.inset;
    state.selected = '';
    render();
  });
  const updateTable = () => {
    render();
    ui['city-rows'].closest('.rows').scrollTop = 0;
  };
  ui.sort.addEventListener('change', updateTable);
  ui['table-tier'].addEventListener('change', updateTable);
  ui.reset.addEventListener('click', () => {
    state.tiers = defaultTiers();
    state.customTiers = false;
    ui['table-tier'].value = '';
    state.query = '';
    ui.query.value = '';
    ui.sort.value = 'rank';
    selectProvince('');
  });
  for (const table of [ui['city-rows'], ui['reference-rows']]) {
    table.addEventListener('click', event => {
      const button = event.target.closest('[data-city]');
      if (button) selectCity(button.dataset.city, 'table');
    });
  }
  ui['province-summary'].addEventListener('click', event => {
    const button = event.target.closest('[data-province]');
    if (!button) return;
    selectProvince(button.dataset.province);
    ui.province.focus();
  });

  byId('sources-link').addEventListener('click', () => { byId('sources').open = true; });

  compactScreen.addEventListener('change', () => {
    if (!state.customTiers) {
      state.tiers = defaultTiers();
      render();
    }
  });
  let resizeFrame;
  window.addEventListener('resize', () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(render);
  });
  render();
})();
