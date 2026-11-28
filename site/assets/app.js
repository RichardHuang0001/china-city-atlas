(() => {
  'use strict';
  const {meta = {}, cities, provinces} = window.atlasData;
  const map = window.atlasMap;
  const labelLayout = window.atlasLabels;
  window.atlasProfiles = window.atlasProfiles || {};
  window.atlasDecadeRanks = window.atlasDecadeRanks || {};
  window.atlasDistricts = window.atlasDistricts || {};
  window.atlasSubdistricts = window.atlasSubdistricts || {};
  const FIELD = {
    name: 0, code: 1, province: 2, tier: 3, rank: 4,
    reference: 5, coord: 6, point: 7, urbanRef: 8,
  };
  const DEFAULT_TIERS = [
    {name: '一线', color: '#9b3454', scale: 1.09},
    {name: '新一线', color: '#ad5141', scale: 1.04},
    {name: '二线', color: '#936820', scale: 1},
    {name: '三线', color: '#926074', scale: 0.95},
    {name: '四线', color: '#6c6279', scale: 0.9},
    {name: '五线', color: '#82674e', scale: 0.85},
  ];
  const MAP_CONFIG = {
    insetProvince: '46',
    insetCity: '460300',
    insetTitle: '海南省 · 南海诸岛',
    insetHint: '三沙位于永兴岛附近。',
    districtZoomIndex: 3,
    provinceLabelMaxZoom: 1.6,
    zoomSteps: [1, 1.23, 1.7, 2.35, 3.25, 4.5, 6, 8],
    provinceLabels: [
      ['65', '新疆'], ['54', '西藏'], ['63', '青海'], ['15', '内蒙古'],
      ['23', '黑龙江'], ['51', '四川'], ['53', '云南'], ['45', '广西'], ['71', '台湾'], ['46', '海南'],
    ],
    // Derived from map-base.js (generated from site/assets/subdistricts/*.js).
    subdistrictBounds: map.subdistrictBounds || {},
    subdistrictLabelMaxUnits: 0.23,
  };
  const subdistrictProvinceMap = {};
  for (const cityCode of Object.keys(MAP_CONFIG.subdistrictBounds)) {
    const prov = cityCode.slice(0, 2);
    (subdistrictProvinceMap[prov] = subdistrictProvinceMap[prov] || []).push(cityCode);
  }
  const referenceProvinces = new Set(
    cities.filter(city => city[FIELD.reference]).map(city => city[FIELD.province]),
  );
  const tierConfig = Array.isArray(meta.tiers) && meta.tiers.length ? meta.tiers : DEFAULT_TIERS;
  const tiers = tierConfig.map(item => item.name);
  const colors = tierConfig.map(item => item.color);
  const tierScales = tierConfig.map(item => item.scale);
  const maxTier = tiers.length - 1;
  // Six distinct badge silhouettes + white geometric numerals (Scheme A) shared by map, legend, and table.
  const badges = [
    'M0,-1.17 .29,-.83 .74,-.90 .70,-.45 1.07,-.18 .82,.19 .94,.62 .51,.74 .30,1.12 0,.93 -.30,1.12 -.51,.74 -.94,.62 -.82,.19 -1.07,-.18 -.70,-.45 -.74,-.90 -.29,-.83Z',
    'M-.12,-1.02 Q0,-1.14 .12,-1.02 L1.02,-.12 Q1.14,0 1.02,.12 L.12,1.02 Q0,1.14 -.12,1.02 L-1.02,.12 Q-1.14,0 -1.02,-.12Z',
    'M-.69,-.91 H.69 Q.85,-.91 .85,-.75 V.05 C.85,.56 .37,.90 0,1.06 C-.37,.90 -.85,.56 -.85,.05 V-.75 Q-.85,-.91 -.69,-.91Z',
    'M-.56,-.86 H.56 Q.86,-.86 .86,-.56 V.56 Q.86,.86 .56,.86 H-.56 Q-.86,.86 -.86,.56 V-.56 Q-.86,-.86 -.56,-.86Z',
    'M0,-.96 L.83,-.48 V.48 L0,.96 L-.83,.48 V-.48Z',
    'M0,-.82 A.82,.82 0 1 1 0,.82 A.82,.82 0 1 1 0,-.82Z',
  ];
  const digits = [
    'M-.17,-.24 L.05,-.39 L.05,.39 M-.19,.39 L.22,.39',
    'M-.40,-.19 L-.23,-.32 L-.23,.32 M-.39,.32 L-.09,.32 M.14,-.13 H.40 M.27,-.26 V0',
    'M-.25,-.27 C-.25,-.48 .25,-.48 .25,-.25 C.25,-.05 -.25,.13 -.25,.30 L.27,.30',
    'M-.24,-.26 C-.16,-.42 .24,-.42 .24,-.20 C.24,-.04 .05,-.02 -.06,-.02 C.09,-.02 .26,.04 .26,.21 C.26,.41 -.16,.42 -.26,.26',
    'M.13,.37 L.13,-.37 L-.28,.13 L.28,.13',
    'M.22,-.35 L-.18,-.35 L-.21,-.04 C-.10,-.11 .24,-.09 .24,.14 C.24,.37 -.12,.40 -.24,.26',
  ];
  const byId = id => document.getElementById(id);
  const ui = Object.fromEntries([
    'query', 'province', 'legend', 'reset', 'atlas', 'points', 'map-stage', 'map-loading',
    'provinces', 'city-highlight', 'province-labels', 'subdistrict-lines', 'district-lines', 'boundaries', 'sea-card',
    'sea-detail', 'sea-points', 'sea-mini', 'sea-open', 'marker-count', 'table-tier',
    'zoom-in', 'zoom-out', 'zoom-fit', 'city-leaders', 'subdistrict-labels', 'city-labels', 'sea-labels',
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
  const lookup = new Map(cities.map(city => [city[FIELD.code], city]));
  const collator = new Intl.Collator('zh-CN');
  const ns = 'http://www.w3.org/2000/svg';
  const zoomSteps = MAP_CONFIG.zoomSteps;
  const provinceLabels = MAP_CONFIG.provinceLabels;
  let camera = {zoom: 1, center: null};
  let fittedView;
  let cameraFrame;
  let mapScope;
  let districtScope = '';
  let subdistrictScope = '';
  let mainMarkers = [];
  let markerScale;

  const assetVersion = document.querySelector('meta[name="asset-version"]')?.content || '';
  const withVersion = path => (assetVersion ? path + '?v=' + assetVersion : path);
  const assetPromises = new Map();
  function loadScriptOnce(key, src) {
    if (assetPromises.has(key)) return assetPromises.get(key);
    const promise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = withVersion(src);
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => {
        assetPromises.delete(key);
        reject(new Error('Failed to load ' + src));
      };
      document.head.append(script);
    });
    assetPromises.set(key, promise);
    return promise;
  }

  let detailReady = !!window.atlasDetail;
  let profilesReady = Object.keys(window.atlasProfiles).length > 0;
  let decadeRanksReady = !!(window.atlasDecadeRanks?.cities && Object.keys(window.atlasDecadeRanks.cities).length);
  function refreshSelectedDetail() {
    if (!state.selected) return;
    const selected = lookup.get(state.selected);
    if (selected) {
      window.atlasDetail?.resetKey();
      renderCityDetail(selected);
    }
  }
  function ensureDetailModule() {
    if (detailReady || window.atlasDetail) {
      detailReady = true;
      return Promise.resolve(window.atlasDetail);
    }
    return loadScriptOnce('detail', 'assets/city-detail.js')
      .then(() => {
        detailReady = true;
        refreshSelectedDetail();
        return window.atlasDetail;
      })
      .catch(() => null);
  }
  function ensureProfiles() {
    if (profilesReady || Object.keys(window.atlasProfiles).length > 0) {
      profilesReady = true;
      return Promise.resolve(window.atlasProfiles);
    }
    return loadScriptOnce('profiles', 'assets/city-profiles.js')
      .then(() => {
        profilesReady = true;
        refreshSelectedDetail();
        return window.atlasProfiles;
      })
      .catch(() => window.atlasProfiles);
  }
  function ensureDecadeRanks() {
    if (decadeRanksReady || (window.atlasDecadeRanks?.cities && Object.keys(window.atlasDecadeRanks.cities).length > 0)) {
      decadeRanksReady = true;
      return Promise.resolve(window.atlasDecadeRanks);
    }
    return loadScriptOnce('decadeRanks', 'assets/city-decade-ranks.js')
      .then(() => {
        decadeRanksReady = true;
        refreshSelectedDetail();
        return window.atlasDecadeRanks;
      })
      .catch(() => window.atlasDecadeRanks);
  }

  function renderCityDetail(selected) {
    if (!selected) {
      ui['city-detail'].hidden = true;
      window.atlasDetail?.resetKey();
      return;
    }
    if (window.atlasDetail) {
      window.atlasDetail.render(ui['city-detail'], selected, {
        FIELD,
        provinces,
        tiers,
        rankUnit,
        swatch,
        markerHidden: !state.tiers.has(selected[FIELD.tier]),
        profiles: window.atlasProfiles || {},
        profilesReady,
        decadeData: window.atlasDecadeRanks || {},
        decadeRanksReady,
        ensureProfiles,
        ensureDecadeRanks,
      });
      return;
    }
    // Skeleton fallback when user clicks a city before lazy city-detail.js finishes loading.
    ui['city-detail'].hidden = false;
    const tier = selected[FIELD.tier];
    const head = document.createElement('div');
    head.className = 'city-detail-head';
    const titleRow = document.createElement('div');
    titleRow.className = 'city-detail-title-row';
    const h3 = document.createElement('h3');
    h3.className = 'city-detail-name';
    h3.innerHTML = swatch(tier);
    h3.append(document.createTextNode(selected[FIELD.name]));
    const rankMeta = document.createElement('span');
    rankMeta.className = 'city-detail-rank';
    rankMeta.textContent = provinces[selected[FIELD.province]] + ' · ' + tiers[tier] + '第 ' + selected[FIELD.rank] + ' ' + rankUnit;
    titleRow.append(h3, rankMeta);
    const aside = document.createElement('div');
    aside.className = 'city-detail-aside';
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'city-detail-close';
    closeBtn.dataset.action = 'close-detail';
    closeBtn.setAttribute('aria-label', '关闭城市详情');
    closeBtn.textContent = '收起';
    aside.append(closeBtn);
    head.append(titleRow, aside);
    const loading = document.createElement('p');
    loading.className = 'city-detail-loading';
    loading.textContent = '正在按需加载城市详情面板…';
    ui['city-detail'].replaceChildren(head, loading);
    ensureDetailModule();
    ensureProfiles();
    ensureDecadeRanks();
  }

  function resetCamera() {
    camera = {zoom: 1, center: null};
  }

  function applyEditionMeta() {
    if (meta.title) document.title = meta.title;
    const desc = document.querySelector('meta[name="description"]');
    if (desc && meta.description) desc.setAttribute('content', meta.description);
    if (meta.editionLabel && byId('edition-year')) byId('edition-year').textContent = meta.editionLabel;
    if (meta.subtitle && byId('hero-subtitle')) byId('hero-subtitle').textContent = meta.subtitle;
    if (meta.rankLabel && byId('rank-header')) byId('rank-header').textContent = meta.rankLabel;
    const rankOpt = ui.sort?.querySelector('option[value="rank"]');
    if (rankOpt && meta.rankSortLabel) rankOpt.textContent = meta.rankSortLabel;
    const sourceCard = byId('source-tier-card');
    if (sourceCard && meta.sourceNote) {
      const h3 = document.createElement('h3');
      h3.textContent = meta.sourceTitle || '城市线级';
      const p = document.createElement('p');
      p.textContent = meta.sourceNote;
      const nodes = [h3, p];
      if (Array.isArray(meta.sourceLinks)) {
        meta.sourceLinks.forEach((item, idx) => {
          if (idx > 0) nodes.push(document.createTextNode(' · '));
          const a = document.createElement('a');
          a.href = item.url;
          a.target = '_blank';
          a.rel = 'noopener';
          a.textContent = item.label;
          nodes.push(a);
        });
      }
      sourceCard.replaceChildren(...nodes);
    }
  }

  const swatch = tier => '<svg class="symbol" aria-hidden="true" viewBox="-1.35 -1.35 2.7 2.7">' +
    '<path d="' + badges[tier] + '" fill="' + colors[tier] + '"></path>' +
    '<path class="symbol-digit" d="' + digits[tier] + '"></path></svg>';
  const rankUnit = meta.rankUnit || '位（线内序）';
  const cityDescription = city => city[FIELD.name] + ' · ' + provinces[city[FIELD.province]] + ' · ' + tiers[city[FIELD.tier]] + '第 ' + city[FIELD.rank] + ' ' + rankUnit;
  const rank = (a, b) => a[FIELD.tier] - b[FIELD.tier] || a[FIELD.rank] - b[FIELD.rank];
  const orders = {
    rank,
    province: (a, b) => collator.compare(provinces[a[FIELD.province]], provinces[b[FIELD.province]]) || rank(a, b),
    tier: (a, b) => a[FIELD.tier] - b[FIELD.tier] || collator.compare(a[FIELD.name], b[FIELD.name]),
    name: (a, b) => collator.compare(a[FIELD.name], b[FIELD.name]),
  };

  applyEditionMeta();
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
    const counts = Array(tiers.length).fill(0);
    for (const city of list) counts[city[FIELD.tier]]++;
    return counts;
  }

  const provinceRows = Object.keys(provinces).map(code => {
    const list = cities.filter(city => city[FIELD.province] === code && !city[FIELD.reference]);
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
    for (const control of [
      ui['zoom-in'].parentElement,
      ui.national,
      document.querySelector('.zoom-tip'),
      ui['sea-card'],
    ]) {
      if (!control || control.hidden) continue;
      const box = control.getBoundingClientRect();
      obstacles.push({
        left: box.left - rect.left - 4, right: box.right - rect.left + 4,
        top: box.top - rect.top - 4, bottom: box.bottom - rect.top + 4,
        uiObstacle: true,
      });
    }

    const showProvinces = !state.province && camera.zoom < MAP_CONFIG.provinceLabelMaxZoom;
    ui['province-labels'].toggleAttribute('hidden', !showProvinces);
    if (showProvinces) {
      const font = rect.width < 600 ? 9 : 13;
      ui['province-labels'].style.fontSize = (font * units) + 'px';
      ui['province-labels'].style.strokeWidth = (2 * units) + 'px';
      for (const [code, name] of provinceLabels) {
        const [, [x, y]] = map.provinces[code];
        const px = (x - left) / units;
        const py = (y - top) / units;
        const halfWidth = (name.length * font * 1.08 + 2) / 2;
        const halfHeight = font * .65;
        obstacles.push({
          left: px - halfWidth, right: px + halfWidth,
          top: py - halfHeight, bottom: py + halfHeight,
          provinceLabel: true,
        });
      }
    }

    const focus = state.selected || (mainMarkers.length === 1 ? mainMarkers[0].city[FIELD.code] : '');
    const level = zoomLevel(camera.zoom);
    const local = !!state.province;
    const subdistricts = activeSubdistrictItems(units);
    const placed = labelLayout.place({
      markers: mainMarkers, subdistricts, width: rect.width, height: rect.height, left, top, units,
      level, local, focus, obstacles, colors, maxTier, field: FIELD,
    });
    ui['city-leaders'].replaceChildren(placed.leaders);
    ui['subdistrict-labels'].replaceChildren(placed.subdistrictLabels);
    ui['city-labels'].replaceChildren(placed.labels);
    const wide = rect.width >= labelLayout.narrowMap;
    const tier = labelLayout.priorityTier(rect.width, level, local, maxTier);
    const zoomTag = camera.zoom > 1 ? '（' + camera.zoom.toFixed(2).replace(/\.?0+$/, '') + '×）' : '';
    ui['map-hint'].textContent = state.inset ? MAP_CONFIG.insetHint :
      wide && tier < maxTier ? '当前' + zoomTag + '优先显示' + tiers[tier] + '及以上，' +
        (local ? '拖动可浏览邻省，' : '') + '点击 ＋ 展开' + tiers[tier + 1] + '城市名。' :
      wide ? '当前' + zoomTag + '显示视野内的各档城市名，' + (local ? '拖动可浏览邻省，' : '') + '点击名称查看详情。' :
        (local ? '可单指拖动浏览邻省，' : camera.zoom > 1 ? '当前 ' + zoomTag.slice(1, -1) + '，可单指拖动地图，' : '放大可逐级看到更多城市名，') +
        '点击名称查看详情。';
  }

  const districtProvinceSet = new Set(map.districtProvinces || []);
  const cityRegionPaths = new Map();
  const districtCombinedCache = new Map();
  function registerDistrictChunk(prov) {
    const entry = window.atlasDistricts?.[prov];
    if (!entry || districtCombinedCache.has(prov)) return;
    if (typeof entry === 'string') {
      districtCombinedCache.set(prov, entry);
    } else {
      for (const [code, path] of Object.entries(entry)) cityRegionPaths.set(code, path);
      districtCombinedCache.set(prov, Object.values(entry).join(''));
    }
  }
  for (const prov of Object.keys(window.atlasDistricts)) registerDistrictChunk(prov);

  function ensureDistrict(prov) {
    if (!prov || !districtProvinceSet.has(prov)) return Promise.resolve('');
    if (window.atlasDistricts[prov]) {
      registerDistrictChunk(prov);
      return Promise.resolve(districtCombinedCache.get(prov) || '');
    }
    return loadScriptOnce('district:' + prov, 'assets/districts/' + prov + '.js')
      .then(() => {
        registerDistrictChunk(prov);
        const activeCode = highlightedCity || state.selected;
        if (!state.inset && activeCode && lookup.get(activeCode)?.[FIELD.province] === prov) {
          ui['city-highlight'].setAttribute('d', cityRegionPath(activeCode));
        }
        const needNational = !state.province && camera.zoom >= zoomSteps[MAP_CONFIG.districtZoomIndex];
        if (!state.inset && (state.province === prov || needNational)) {
          updateDistrictLines();
        }
        return districtCombinedCache.get(prov) || '';
      })
      .catch(() => '');
  }

  function visibleBoundsKeys(keys, getBox) {
    if (!fittedView) return [];
    const {center: [cx, cy], width, height} = currentView();
    const left = cx - width / 2;
    const right = cx + width / 2;
    const top = cy - height / 2;
    const bottom = cy + height / 2;
    const hits = [];
    for (const key of keys) {
      const box = getBox(key);
      if (box && box[2] >= left && box[0] <= right && box[3] >= top && box[1] <= bottom) hits.push(key);
    }
    return hits;
  }

  const visibleDistrictProvinces = () => visibleBoundsKeys(districtProvinceSet, prov => map.bounds[prov]);
  const visibleSubdistrictCities = () => visibleBoundsKeys(
    Object.keys(MAP_CONFIG.subdistrictBounds),
    code => MAP_CONFIG.subdistrictBounds[code],
  );

  function ensureSubdistrict(cityCode) {
    if (!cityCode || !MAP_CONFIG.subdistrictBounds[cityCode]) return Promise.resolve(null);
    if (window.atlasSubdistricts[cityCode]) return Promise.resolve(window.atlasSubdistricts[cityCode]);
    return loadScriptOnce('subdistrict:' + cityCode, 'assets/subdistricts/' + cityCode + '.js')
      .then(() => {
        if (!drag?.moved && fittedView && !state.inset && activeSubdistrictCities().includes(cityCode)) {
          updateSubdistrictLines();
          scheduleCameraPaint();
        }
        return window.atlasSubdistricts[cityCode] || null;
      })
      .catch(() => null);
  }

  function activeSubdistrictCities() {
    const {inset, province} = state;
    if (inset) return [];
    if (province) return subdistrictProvinceMap[province] || [];
    return camera.zoom >= zoomSteps[MAP_CONFIG.districtZoomIndex] ? visibleSubdistrictCities() : [];
  }

  function activeSubdistrictItems(units) {
    if (state.inset) return [];
    const isMunicipality = !!state.province && referenceProvinces.has(state.province);
    if (!isMunicipality && units > MAP_CONFIG.subdistrictLabelMaxUnits) return [];
    const items = [];
    for (const cityCode of activeSubdistrictCities()) {
      const shard = window.atlasSubdistricts[cityCode];
      if (shard?.items) items.push(...shard.items);
    }
    return items;
  }

  function updateSubdistrictLines() {
    const targets = activeSubdistrictCities();
    if (!targets.length) {
      if (subdistrictScope !== '') {
        subdistrictScope = '';
        ui['subdistrict-lines'].setAttribute('d', '');
      }
      return;
    }
    if (!drag?.moved) {
      for (const code of targets) {
        if (!window.atlasSubdistricts[code]) ensureSubdistrict(code);
      }
    }
    const loaded = targets.filter(code => window.atlasSubdistricts[code]);
    const nextSig = (state.province || 'nat') + ':' + loaded.join(',');
    if (nextSig === subdistrictScope) return;
    subdistrictScope = nextSig;
    ui['subdistrict-lines'].setAttribute('d', loaded.map(code => window.atlasSubdistricts[code].path).join(''));
  }

  const cityRegionPath = code => {
    const city = code && lookup.get(code);
    if (!city) return '';
    if (city[FIELD.reference]) return map.provinces[city[FIELD.province]]?.[0] || '';
    return cityRegionPaths.get(code) || '';
  };
  const seaHighlightNodes = [...document.querySelectorAll('.sea-city-highlight')];

  function updateDistrictLines() {
    const {inset, province} = state;
    if (inset) {
      if (districtScope !== '') {
        districtScope = '';
        ui['district-lines'].setAttribute('d', '');
      }
      return;
    }
    if (province) {
      const ready = districtCombinedCache.has(province);
      const nextSig = province + ':' + (ready ? '1' : '0');
      if (!ready && !drag?.moved) ensureDistrict(province);
      if (nextSig === districtScope) return;
      districtScope = nextSig;
      ui['district-lines'].setAttribute('d', districtCombinedCache.get(province) || '');
      return;
    }
    if (camera.zoom >= zoomSteps[MAP_CONFIG.districtZoomIndex]) {
      const targets = visibleDistrictProvinces();
      if (!drag?.moved) {
        for (const prov of targets) {
          if (!districtCombinedCache.has(prov)) ensureDistrict(prov);
        }
      }
      const loaded = targets.filter(prov => districtCombinedCache.has(prov));
      const nextSig = 'nat:' + loaded.join(',');
      if (nextSig === districtScope) return;
      districtScope = nextSig;
      ui['district-lines'].setAttribute('d', loaded.map(prov => districtCombinedCache.get(prov)).join(''));
      return;
    }
    if (districtScope !== '') {
      districtScope = '';
      ui['district-lines'].setAttribute('d', '');
    }
  }

  function zoomLevel(zoom) {
    let best = 0;
    for (let i = 1; i < zoomSteps.length; i++) {
      if (zoom >= (zoomSteps[i - 1] + zoomSteps[i]) / 2) best = i;
    }
    return best;
  }

  function paintCamera() {
    updateDistrictLines();
    updateSubdistrictLines();
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
    ui.atlas.toggleAttribute('data-zoomed', camera.zoom > 1 || (!!state.province && !state.inset));
    ui['zoom-in'].disabled = camera.zoom >= zoomSteps.at(-1);
    ui['zoom-out'].disabled = camera.zoom <= 1;
    ui['zoom-fit'].disabled = camera.zoom <= 1;
  }

  function scheduleCameraPaint() {
    cancelAnimationFrame(cameraFrame);
    cameraFrame = requestAnimationFrame(paintCamera);
  }

  function changeZoom(step) {
    let next;
    if (step > 0) {
      next = zoomSteps.find(z => z > camera.zoom * 1.03);
    } else {
      for (let i = zoomSteps.length - 1; i >= 0; i--) {
        if (zoomSteps[i] < camera.zoom * .97) {
          next = zoomSteps[i];
          break;
        }
      }
    }
    if (next === undefined) return;
    if (camera.zoom <= 1 && !camera.center && state.selected && !state.inset) {
      const selected = lookup.get(state.selected);
      if (selected?.[FIELD.point]) camera.center = [...selected[FIELD.point]];
    }
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
    updateDistrictLines();
    updateSubdistrictLines();
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
    return cities.filter(city => (!state.province || city[FIELD.province] === state.province) &&
      (!query || city[FIELD.name].includes(query)));
  }

  function visibleCities() {
    const tier = ui['table-tier'].value;
    return matchesScope().filter(city => tier === '' || city[FIELD.tier] === Number(tier));
  }

  function cityButton(city, label = city[FIELD.name]) {
    const code = city[FIELD.code];
    return '<button type="button" class="city-link" data-city="' + code + '"' +
      (code === state.selected ? ' aria-current="true"' : '') + '>' + label + '</button>';
  }

  // Cache the 337 SVG marker nodes once so filtering/searching/resizing never recreates DOM nodes.
  const markerCache = new Map();
  function getMarkerNode(city) {
    const code = city[FIELD.code];
    let node = markerCache.get(code);
    if (!node) {
      const tier = city[FIELD.tier];
      node = document.createElementNS(ns, 'g');
      node.dataset.city = code;
      node.dataset.tier = tier;
      node.setAttribute('role', 'img');
      node.setAttribute('aria-label', cityDescription(city));
      const badge = document.createElementNS(ns, 'path');
      badge.setAttribute('class', 'marker-badge');
      badge.setAttribute('d', badges[tier]);
      badge.setAttribute('fill', colors[tier]);
      const digit = document.createElementNS(ns, 'path');
      digit.setAttribute('class', 'marker-digit');
      digit.setAttribute('d', digits[tier]);
      node.append(badge, digit);
      markerCache.set(code, node);
    }
    node.setAttribute('class', 'marker' + (code === state.selected ? ' active' : ''));
    return node;
  }

  function renderTable() {
    const list = visibleCities().sort(orders[ui.sort.value]);
    const ordinary = list.filter(city => !city[FIELD.reference]);
    const references = list.filter(city => city[FIELD.reference]);
    const scope = provinces[state.province] || '全国';
    const selection = !!(ui['table-tier'].value || state.query.trim());

    ui.total.textContent = ordinary.length;
    const countLabel = selection ? '筛选后线级分布' : scope + '线级分布';
    ui.counts.setAttribute('aria-label', countLabel);
    ui.counts.innerHTML = stats(ordinary).map((n, i) => '<span>' + swatch(i) + tiers[i] + ' ' + n + '</span>').join('');
    ui['city-rows'].innerHTML = ordinary.map(city => '<tr data-row="' + city[FIELD.code] + '"' +
      (city[FIELD.code] === state.selected ? ' class="active"' : '') + '><td>' + city[FIELD.rank] + '</td><td>' +
      cityButton(city) + '</td><td>' + provinces[city[FIELD.province]] + '</td><td>' + swatch(city[FIELD.tier]) + tiers[city[FIELD.tier]] + '</td></tr>').join('');
    ui.empty.hidden = !!ordinary.length;
    ui['reference-count'].textContent = references.length + ' 座';
    byId('reference').hidden = !references.length;
    ui['reference-rows'].innerHTML = references.map(city =>
      cityButton(city, swatch(city[FIELD.tier]) + city[FIELD.name] + ' · ' + tiers[city[FIELD.tier]] + ' ' + city[FIELD.rank])).join('');
  }

  function renderMap({skipPaint = false} = {}) {
    const scoped = matchesScope();
    const markers = scoped.filter(city => state.tiers.has(city[FIELD.tier]));
    const selected = scoped.find(city => city[FIELD.code] === state.selected);
    const scope = provinces[state.province] || '全国';
    setView();
    const miniScale = state.province ? 1 : fitInset();

    ui['map-title'].textContent = state.inset ? MAP_CONFIG.insetTitle : scope;
    ui.national.hidden = !state.province;
    ui.inset.hidden = state.province !== MAP_CONFIG.insetProvince;
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
    const ordinarySize = ui.atlas.clientWidth < 600 ? 4.8 : 7;
    let shown = 0;
    for (const city of [...markers].reverse()) {
      const code = city[FIELD.code];
      const tier = city[FIELD.tier];
      const reference = city[FIELD.reference];
      const point = city[FIELD.point];
      const sansha = code === MAP_CONFIG.insetCity;
      if (!point || (state.inset && !sansha) || (state.province && !state.inset && sansha)) continue;
      const miniature = sansha && !state.province;
      const baseSize = code === state.selected ? Math.max(8.8, ordinarySize * 1.25) :
        miniature ? 5.2 : reference ? ordinarySize + .9 : ordinarySize;
      const size = baseSize * tierScales[tier];
      const marker = getMarkerNode(city);
      if (miniature) {
        positionMarker(marker, point, size * miniScale);
        mini.append(marker);
        miniLabels.append(labelLayout.makeLabel(city, [point[0] + 8 * miniScale, point[1]], 10 * miniScale, 'start'));
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
    if (!skipPaint) paintCamera();
    ui['marker-count'].textContent = '图中 ' + shown + ' 座';
    renderCityDetail(selected);
    hideTooltip();
  }

  function render(options) {
    renderMap(options);
    renderTable();
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
    state.province = city[FIELD.province];
    state.selected = code;
    state.inset = code === MAP_CONFIG.insetCity;
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

  function syncRegionHighlight(code = highlightedCity || state.selected) {
    ui['city-highlight'].setAttribute('d', state.inset ? '' : cityRegionPath(code));
    const seaPath = (code && map.seaCities?.[code]) || '';
    for (const node of seaHighlightNodes) node.setAttribute('d', seaPath);
  }

  function highlightCity(code) {
    if (highlightedCity === code) return;
    for (const node of highlightedNodes) node.classList.remove('is-highlighted');
    highlightedCity = code;
    highlightedNodes = code ? [...ui.atlas.querySelectorAll(
      '[data-city="' + code + '"], [data-leader-for="' + code + '"]'
    )] : [];
    for (const node of highlightedNodes) node.classList.add('is-highlighted');
    syncRegionHighlight(code || state.selected);
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
    syncRegionHighlight(state.selected);
    ui.tooltip.hidden = true;
  }

  function mapHover(event) {
    if (drag?.moved || event.pointerType === 'touch') return;
    const cityNode = event.target.closest('[data-city]');
    const provinceNode = state.province ? null : event.target.closest('[data-province]');
    const city = cityNode && lookup.get(cityNode.dataset.city);
    const province = provinceNode?.dataset.province || (!state.province && city && city[FIELD.province]);
    if (!city && !province) {
      hideTooltip();
      return;
    }
    highlightProvince(provincePaths.get(province));
    if (city) {
      ensureDistrict(city[FIELD.province]);
      ensureSubdistrict(city[FIELD.code]);
    }
    highlightCity(city?.[FIELD.code] || '');
    ui.tooltip.textContent = city ? cityDescription(city) : provinces[province] + ' · 点击放大';
    ui.tooltip.hidden = false;
    const stage = ui['map-stage'].getBoundingClientRect();
    const x = Math.min(Math.max(6, event.clientX - stage.left + 12), stage.width - ui.tooltip.offsetWidth - 6);
    const y = Math.min(Math.max(6, event.clientY - stage.top + 12), stage.height - ui.tooltip.offsetHeight - 6);
    ui.tooltip.style.transform = 'translate(' + x + 'px,' + y + 'px)';
  }

  function mapClick(event) {
    const cityNode = event.target.closest('[data-city]');
    const provinceNode = state.province ? null : event.target.closest('[data-province]');
    if (cityNode) selectCity(cityNode.dataset.city, 'map');
    else if (provinceNode) selectProvince(provinceNode.dataset.province);
    hideTooltip();
  }

  for (const svg of [ui.atlas, ui['sea-mini']]) {
    svg.addEventListener('pointermove', mapHover);
    svg.addEventListener('pointerleave', hideTooltip);
    svg.addEventListener('click', mapClick);
  }
  ui['sea-open'].addEventListener('click', () => {
    state.province = MAP_CONFIG.insetProvince;
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

  function exitProvinceToPan(clientY) {
    const prevView = currentView();
    const prevRect = ui.atlas.getBoundingClientRect();
    const worldPerPx = prevView.width / (prevRect.width || 1);
    const py = clientY - prevRect.top;
    const anchorY = (prevView.center[1] - prevView.height / 2) + py * worldPerPx;

    state.province = '';
    state.selected = '';
    mapScope = '';
    ui['map-stage'].toggleAttribute('data-local', false);
    const newRect = ui.atlas.getBoundingClientRect();
    const nationalFitted = fittedBox(ui.atlas, map.frame, 1.065);
    camera.zoom = Math.max(1, Math.min(20, nationalFitted.width / (worldPerPx * (newRect.width || 1))));
    const newWorldPerPx = nationalFitted.width / camera.zoom / (newRect.width || 1);
    const newTop = anchorY - py * newWorldPerPx;
    camera.center = [prevView.center[0], newTop + (newRect.height * newWorldPerPx) / 2];
    fittedView = nationalFitted;
    clampCenter();
    // Skip immediate paintCamera() here because the active pointermove schedules it on rAF.
    render({skipPaint: true});
  }

  let drag;
  let dragFrame;
  let suppressClick = false;
  function paintDragTransform() {
    if (!drag?.moved) return;
    const tx = (drag.startCenter[0] - camera.center[0]) * drag.pxPerWorld;
    const ty = (drag.startCenter[1] - camera.center[1]) * drag.pxPerWorld;
    ui.atlas.style.transform = 'translate3d(' + tx.toFixed(1) + 'px,' + ty.toFixed(1) + 'px,0)';
  }
  ui.atlas.addEventListener('pointerdown', event => {
    suppressClick = false;
    if (!event.isPrimary) {
      ui.atlas.classList.remove('dragging');
      ui.atlas.style.transform = '';
      drag = undefined;
      return;
    }
    const pannable = camera.zoom > 1 || (!!state.province && !state.inset);
    if ((event.pointerType === 'mouse' && event.button !== 0) || !pannable) return;
    drag = {
      id: event.pointerId, x: event.clientX, y: event.clientY,
      moved: false, threshold: 4, gain: event.pointerType === 'touch' ? 1.75 : 1,
    };
  });
  ui.atlas.addEventListener('pointermove', event => {
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (!drag.moved) {
      if (Math.hypot(dx, dy) < drag.threshold) return;
      drag.moved = true;
      if (state.province && !state.inset) {
        exitProvinceToPan(event.clientY);
        paintCamera();
      }
      const view = currentView();
      const [baseX, baseY] = fittedView.center;
      const marginX = Math.max(0, (fittedView.width - view.width) / 2);
      const marginY = Math.max(0, (fittedView.height - view.height) / 2);
      drag.startX = drag.x;
      drag.startY = drag.y;
      drag.startCenter = [...view.center];
      drag.pxPerWorld = (ui.atlas.clientWidth || 1) / view.width;
      drag.minCenter = [baseX - marginX, baseY - marginY];
      drag.maxCenter = [baseX + marginX, baseY + marginY];
      suppressClick = true;
      hideTooltip();
      ui.atlas.setPointerCapture(event.pointerId);
      ui.atlas.classList.add('dragging');
    }
    const totalDx = (event.clientX - drag.startX) * drag.gain;
    const totalDy = (event.clientY - drag.startY) * drag.gain;
    camera.center = [
      Math.max(drag.minCenter[0], Math.min(drag.maxCenter[0], drag.startCenter[0] - totalDx / drag.pxPerWorld)),
      Math.max(drag.minCenter[1], Math.min(drag.maxCenter[1], drag.startCenter[1] - totalDy / drag.pxPerWorld)),
    ];
    cancelAnimationFrame(dragFrame);
    dragFrame = requestAnimationFrame(paintDragTransform);
  });
  function endDrag(event) {
    if (drag?.id !== event.pointerId) return;
    const moved = drag.moved;
    cancelAnimationFrame(dragFrame);
    ui.atlas.classList.remove('dragging');
    ui.atlas.style.transform = '';
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
    } else if (event.key === '+' || event.key === '=') {
      event.preventDefault();
      changeZoom(1);
    } else if (event.key === '-' || event.key === '_') {
      event.preventDefault();
      changeZoom(-1);
    } else if (event.key === '0') {
      event.preventDefault();
      resetCamera();
      paintCamera();
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
  let queryTimer;
  ui.query.addEventListener('input', () => {
    state.query = ui.query.value;
    state.selected = '';
    clearTimeout(queryTimer);
    queryTimer = setTimeout(() => render(), 80);
  });
  ui.query.addEventListener('keydown', event => {
    if (event.key !== 'Enter') return;
    clearTimeout(queryTimer);
    const list = visibleCities();
    if (list.length === 1) selectCity(list[0][FIELD.code], 'search');
    else render();
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
    renderTable();
    ui['city-rows'].closest('.rows').scrollTop = 0;
  };
  ui.sort.addEventListener('change', updateTable);
  ui['table-tier'].addEventListener('change', updateTable);
  ui.reset.addEventListener('click', () => {
    clearTimeout(queryTimer);
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
  ui['city-detail'].addEventListener('click', event => {
    if (event.target.closest('[data-action="close-detail"]')) {
      state.selected = '';
      render();
    }
  });
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
  let lastOrdinarySize = ui.atlas.clientWidth < 600 ? 4.8 : 7;
  let resizeFrame;
  function handleResize() {
    const nextOrdinarySize = ui.atlas.clientWidth < 600 ? 4.8 : 7;
    if (!fittedView || nextOrdinarySize !== lastOrdinarySize) {
      lastOrdinarySize = nextOrdinarySize;
      render();
      return;
    }
    const {inset, province} = state;
    const frame = inset ? map.seaFrame : province ? map.bounds[province] : map.frame;
    const padding = inset ? 1.18 : province ? 1.20 : 1.065;
    fittedView = fittedBox(ui.atlas, frame, padding);
    clampCenter();
    if (!province) fitInset();
    markerScale = undefined;
    paintCamera();
  }
  window.addEventListener('resize', () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(handleResize);
  });
  render();
  if (ui['map-loading']) ui['map-loading'].hidden = true;
  const scheduleIdle = window.requestIdleCallback || (fn => setTimeout(fn, 80));
  scheduleIdle(() => {
    ensureDetailModule();
    ensureProfiles();
    ensureDecadeRanks();
  });
})();
