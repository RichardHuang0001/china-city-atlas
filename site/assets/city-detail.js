// Lazy-loaded city detail panel and 2016-2026 rank/economic chart module.
window.atlasDetail = (() => {
  'use strict';
  const ns = 'http://www.w3.org/2000/svg';
  const DECADE_YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
  let renderedDetailKey = '';

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const fmtNum = (val, digits = 0) => (val === null || val === undefined || Number.isNaN(val))
    ? null
    : Number(val).toLocaleString('zh-CN', {maximumFractionDigits: digits, minimumFractionDigits: digits});

  function buildKpiItem(label, valueText, unitText) {
    const wrap = document.createElement('div');
    const dt = el('dt', '', label);
    const dd = el('dd', '');
    if (valueText === null) {
      dd.textContent = '暂无数据';
    } else {
      dd.textContent = valueText;
      if (unitText) dd.append(el('small', '', unitText));
    }
    wrap.append(dt, dd);
    return wrap;
  }

  function buildTransportRow(label, text, isEmpty = false) {
    const row = el('div', 'detail-tr-row');
    row.append(el('dt', '', label));
    row.append(el('dd', isEmpty ? 'is-empty' : '', text));
    return row;
  }

  function formatTransportItems(tr, isTop3) {
    const [
      apCnt, apPaxWan, apGrade,
      hsrStns, hsrTrains, hsrReach,
      hasMetro, crossMetro, otherUr, urModes, urLines, urKm, urPaxWan, crScStns,
    ] = tr;
    let apText = '暂无民航运输机场';
    if (apCnt > 0) {
      const grade = apGrade ? '（' + apGrade + '）' : '';
      apText = isTop3 && apPaxWan > 0
        ? apCnt + ' 座' + grade + ' · 2025年吞吐 ' + fmtNum(apPaxWan, 0) + ' 万人次'
        : apCnt + ' 座' + grade;
    }
    let hsrText = '暂无高铁/动车组停靠';
    if (hsrStns > 0) {
      hsrText = isTop3
        ? hsrStns + ' 站 · 日均 ' + fmtNum(hsrTrains, 0) + ' 班（G/D/C，直达 ' + hsrReach + ' 城）'
        : hsrStns + ' 站（G/D/C 动车组）';
    }
    let metroText = '暂无地铁';
    let metroEmpty = true;
    if (hasMetro) {
      metroEmpty = false;
      if (isTop3 && urPaxWan) {
        const paxStr = urPaxWan >= 10000
          ? (urPaxWan / 10000).toFixed(2) + ' 亿人次'
          : fmtNum(urPaxWan, 0) + ' 万人次';
        metroText = urLines + ' 条（总网 ' + urKm + ' km）· 2025年客运 ' + paxStr;
      } else {
        metroText = urLines + ' 条（' + urKm + ' km）';
      }
    } else if (crossMetro) {
      metroEmpty = false;
      metroText = '跨市延伸接入（' + urModes + (urKm > 0 ? ' · ' + urKm + ' km' : '') + '）';
    }
    let urText = '暂无其他城轨制式';
    let urEmpty = true;
    const nonMetroModes = urModes
      ? urModes.split(';').filter(m => m && m !== '地铁' && m !== '跨市地铁')
      : [];
    if (otherUr && nonMetroModes.length) {
      urEmpty = false;
      const modeStr = nonMetroModes.join('、');
      if (!hasMetro && !crossMetro && urLines > 0) {
        urText = modeStr + ' ' + urLines + ' 条（' + urKm + ' km）' + (isTop3 && urPaxWan ? ' · 年客运 ' + fmtNum(urPaxWan, 0) + ' 万人次' : '');
      } else {
        urText = '含' + modeStr + (crScStns > 0 ? '；国铁市域/城际 ' + crScStns + ' 站' : '');
      }
    } else if (crScStns > 0) {
      urEmpty = false;
      urText = '国铁市域/城际（S/C 线）' + crScStns + ' 站';
    }
    return [
      ['机场', apText, apCnt === 0],
      ['高铁', hsrText, hsrStns === 0],
      ['地铁', metroText, metroEmpty],
      ['城轨', urText, urEmpty],
    ];
  }

  function mixHex(a, b, t) {
    const k = Math.max(0, Math.min(1, t));
    const pa = i => parseInt(a.slice(i, i + 2), 16);
    const pb = i => parseInt(b.slice(i, i + 2), 16);
    const ch = (v1, v2) => Math.round(v1 + (v2 - v1) * k).toString(16).padStart(2, '0');
    return '#' + ch(pa(1), pb(1)) + ch(pa(3), pb(3)) + ch(pa(5), pb(5));
  }

  function rankDropSeverity(rk, rStart) {
    if (rk <= rStart) return 0;
    const dropAbs = rk - rStart;
    const dropRel = dropAbs / Math.max(15, rStart);
    return Math.max(0, Math.min(1, ((dropAbs - 2) / 38) * 0.55 + (dropRel / 0.85) * 0.45));
  }

  function rankEnvelope(ranks) {
    const best = Math.min(...ranks);
    const worst = Math.max(...ranks);
    const span = worst - best;
    if (span === 0) {
      const pad = Math.max(4, Math.min(8, Math.round(best * 0.8)));
      const yTop = Math.max(1, best - pad);
      const yBottom = Math.min(337, yTop + pad * 2);
      return {best, worst, yTop, yBottom};
    }
    const padTop = Math.max(1, Math.min(18, Math.ceil(span * 0.22)));
    const padBot = Math.max(2, Math.min(20, Math.ceil(span * 0.28)));
    let yTop = Math.max(1, best - padTop);
    let yBottom = Math.min(337, worst + padBot);
    if (yBottom - yTop < 4) {
      yBottom = Math.min(337, yTop + 4);
      yTop = Math.max(1, yBottom - 4);
    }
    return {best, worst, yTop, yBottom};
  }

  const rankHeightPct = (r, yTop, yBottom) => 14 + 78 * ((yBottom - r) / (yBottom - yTop));

  function buildDecadeRankCard(cityName, entry, decadeMeta) {
    const card = el('section', 'detail-card detail-card--decade');
    card.setAttribute('aria-label', cityName + ' 2016-2026 全国排名与经济发展趋势');
    const head = el('div', 'detail-card-head');
    head.append(el('h4', '', '2016-2026'));

    if (!entry) {
      head.append(el('span', 'detail-card-sub', '排名与经济发展指数'));
      card.append(head, el('p', 'city-detail-loading', '正在按需加载 2016–2026 排名与经济指数…'));
      return card;
    }

    const [ranks, tiersHistory, edis = [], rawGrs = [], flags = []] = entry;
    const {best, worst, yTop, yBottom} = rankEnvelope(ranks);
    const rStart = ranks[0];
    const rEnd = ranks[10];
    const delta = rStart - rEnd;
    const endSev = rankDropSeverity(rEnd, rStart);

    const kpis = el('div', 'decade-kpis');
    kpis.append(el('span', 'decade-lvl', '第 ' + rEnd + ' 名'));
    const deltaText = delta > 0 ? '↑' + delta + '位' : delta < 0 ? '↓' + Math.abs(delta) + '位' : '持平';
    const deltaTone = delta > 0 ? 'is-up' : delta === 0 ? 'is-flat' : endSev >= 0.45 ? 'is-down' : 'is-mild-down';
    kpis.append(el('span', 'decade-delta ' + deltaTone, deltaText));
    const ediStart = edis[0];
    const ediEnd = edis[9];
    if (ediEnd !== null && ediEnd !== undefined) {
      kpis.append(el('span', 'decade-edi-pill', '经济 ' + ediEnd.toFixed(1)));
    }
    head.append(kpis);

    const ediSummary = (ediStart !== null && ediStart !== undefined && ediEnd !== null && ediEnd !== undefined)
      ? ' · 经济 ' + ediStart.toFixed(1) + '→' + ediEnd.toFixed(1) + '（' + (ediEnd - ediStart >= 0 ? '+' : '') + (ediEnd - ediStart).toFixed(1) + '）'
      : '';
    const defaultReadout = '排名 #' + rStart + '→#' + rEnd + ediSummary;
    const readout = el('div', 'decade-readout', defaultReadout);

    const plot = el('div', 'decade-plot');
    const guides = el('div', 'decade-guides');
    guides.setAttribute('aria-hidden', 'true');
    const midRank = Math.round((yTop + yBottom) / 2);
    const addGuide = (rankVal) => {
      const g = el('div', 'decade-guide');
      g.style.bottom = rankHeightPct(rankVal, yTop, yBottom).toFixed(1) + '%';
      g.append(el('span', '', '#' + rankVal));
      guides.append(g);
    };
    addGuide(yTop);
    if (midRank !== yTop && midRank !== yBottom) addGuide(midRank);
    addGuide(yBottom);

    const baseHeight = rankHeightPct(rStart, yTop, yBottom);
    const baseLine = el('div', 'decade-base-line');
    baseLine.style.bottom = baseHeight.toFixed(2) + '%';
    guides.append(baseLine);

    for (const tickVal of [85, 50, 15]) {
      const rg = el('span', 'decade-guide-right', String(tickVal));
      rg.style.bottom = tickVal + '%';
      guides.append(rg);
    }

    const barsWrap = el('div', 'decade-bars');
    const lineLayer = el('div', 'decade-line-layer');
    lineLayer.setAttribute('aria-hidden', 'true');
    const lineSvg = document.createElementNS(ns, 'svg');
    lineSvg.setAttribute('class', 'decade-line-svg');
    lineSvg.setAttribute('viewBox', '0 0 110 100');
    lineSvg.setAttribute('preserveAspectRatio', 'none');
    lineLayer.append(lineSvg);

    const pts = [];
    for (let i = 0; i < 10; i++) {
      if (edis[i] === null || edis[i] === undefined) continue;
      pts.push(((i + 0.5) * 10).toFixed(2) + ',' + (100 - edis[i]).toFixed(2));
    }
    if (pts.length >= 2) {
      const halo = document.createElementNS(ns, 'polyline');
      halo.setAttribute('points', pts.join(' '));
      halo.setAttribute('fill', 'none');
      halo.setAttribute('stroke', 'rgba(255,252,247,0.88)');
      halo.setAttribute('stroke-width', '4.4');
      halo.setAttribute('vector-effect', 'non-scaling-stroke');
      halo.setAttribute('stroke-linecap', 'round');
      halo.setAttribute('stroke-linejoin', 'round');

      const line = document.createElementNS(ns, 'polyline');
      line.setAttribute('points', pts.join(' '));
      line.setAttribute('fill', 'none');
      line.setAttribute('stroke', '#c46d1e');
      line.setAttribute('stroke-width', '2.25');
      line.setAttribute('vector-effect', 'non-scaling-stroke');
      line.setAttribute('stroke-linecap', 'round');
      line.setAttribute('stroke-linejoin', 'round');
      lineSvg.append(halo, line);
    }

    const dots = [];
    for (let i = 0; i < 10; i++) {
      if (edis[i] === null || edis[i] === undefined) {
        dots.push(null);
        continue;
      }
      const fl = flags[i] || 0;
      const dot = el('span', 'decade-dot' + (fl === 2 ? ' is-neg' : fl === 1 ? ' is-slow' : ''));
      dot.style.left = (((i + 0.5) / 11) * 100).toFixed(3) + '%';
      dot.style.bottom = edis[i].toFixed(1) + '%';
      lineLayer.append(dot);
      dots.push(dot);
    }

    const natGrList = decadeMeta?.natGr || [];
    ranks.forEach((rk, idx) => {
      const h = rankHeightPct(rk, yTop, yBottom);
      const y = DECADE_YEARS[idx];
      const tr = tiersHistory[idx];

      const col = document.createElement('button');
      col.type = 'button';
      col.className = 'decade-bar-col' + (idx === 10 ? ' is-latest' : '') + (rk > rStart ? ' is-dip' : '');
      col.setAttribute('aria-label', y + '年 第' + rk + '名');

      const track = el('div', 'decade-bar-track');
      if (rk < rStart) {
        track.style.height = h.toFixed(2) + '%';
        const gainT = Math.min(1, (rStart - rk) / 14);
        const capTop = mixHex('#e78a94', '#e8556b', gainT);
        const capBot = mixHex('#d16b7a', '#cb3c54', gainT);
        const liftSeg = el('span', 'decade-seg-lift');
        liftSeg.style.height = (((h - baseHeight) / h) * 100).toFixed(2) + '%';
        liftSeg.style.background = 'linear-gradient(180deg, ' + capTop + ' 0%, ' + capBot + ' 100%)';
        const baseSeg = el('span', 'decade-seg-base');
        track.append(liftSeg, baseSeg);
      } else if (rk > rStart) {
        const sev = rankDropSeverity(rk, rStart);
        let fillTop, fillBot;
        if (sev <= 0.45) {
          const k = sev / 0.45;
          fillTop = mixHex('#c88692', '#b07b87', k);
          fillBot = mixHex('#ae6977', '#945f6d', k);
        } else {
          const k = (sev - 0.45) / 0.55;
          fillTop = mixHex('#b07b87', '#958b98', k);
          fillBot = mixHex('#945f6d', '#756b78', k);
        }
        track.style.height = baseHeight.toFixed(2) + '%';
        const defSeg = el('span', 'decade-seg-deficit');
        defSeg.style.height = (((baseHeight - h) / baseHeight) * 100).toFixed(2) + '%';
        defSeg.style.opacity = (0.38 + 0.62 * sev).toFixed(2);
        const baseSeg = el('span', 'decade-seg-base');
        baseSeg.style.background = 'linear-gradient(180deg, ' + fillTop + ' 0%, ' + fillBot + ' 100%)';
        track.append(defSeg, baseSeg);
      } else {
        track.style.height = h.toFixed(2) + '%';
        track.append(el('span', 'decade-seg-base'));
      }

      col.append(track);
      const showTip = () => {
        for (const child of barsWrap.children) child.classList.remove('is-active');
        for (const d of dots) if (d) d.classList.remove('is-active');
        col.classList.add('is-active');
        if (dots[idx]) dots[idx].classList.add('is-active');

        if (idx === 10) {
          readout.replaceChildren(
            el('strong', '', String(y)),
            document.createTextNode(' · #' + rk + '（' + tr + '） · 宏观年报待出'),
          );
          return;
        }
        const nodesOut = [
          el('strong', '', String(y)),
          document.createTextNode(' · #' + rk),
        ];
        const ediVal = edis[idx];
        if (ediVal !== null && ediVal !== undefined) {
          nodesOut.push(document.createTextNode(' · '), el('strong', '', '经济 ' + ediVal.toFixed(1)));
        }
        const gr = rawGrs[idx];
        if (gr !== null && gr !== undefined) {
          const nat = natGrList[idx];
          const natStr = nat !== undefined ? ' / 全国+' + nat.toFixed(1) + '%' : '';
          const grTxt = (gr >= 0 ? '+' : '') + gr.toFixed(1) + '%';
          const fl = flags[idx] || 0;
          nodesOut.push(document.createTextNode('（'));
          if (fl === 2) nodesOut.push(el('span', 'tone-warn', grTxt));
          else if (fl === 1) nodesOut.push(el('span', 'tone-slow', grTxt));
          else nodesOut.push(document.createTextNode(grTxt));
          nodesOut.push(document.createTextNode(natStr + '）'));
        }
        readout.replaceChildren(...nodesOut);
      };
      col.addEventListener('pointerenter', showTip);
      col.addEventListener('focus', showTip);
      col.addEventListener('click', showTip);
      barsWrap.append(col);
    });

    plot.addEventListener('pointerleave', () => {
      for (const child of barsWrap.children) child.classList.remove('is-active');
      for (const d of dots) if (d) d.classList.remove('is-active');
      readout.textContent = defaultReadout;
    });
    plot.append(guides, barsWrap, lineLayer);

    const xAxis = el('div', 'decade-x-axis');
    xAxis.setAttribute('aria-hidden', 'true');
    DECADE_YEARS.forEach((y, idx) => {
      const fl = idx < 10 ? (flags[idx] || 0) : 0;
      const cls = idx === 10 ? 'is-latest' : fl === 2 ? 'is-neg' : fl === 1 ? 'is-slow' : '';
      xAxis.append(el('span', cls, '\'' + String(y).slice(2)));
    });

    const foot = el('div', 'decade-foot');
    foot.append(
      el('span', '', '左轴柱：排名 #' + best + '–#' + worst),
      el('span', '', '右轴线：16–25 经济指数（\'26待出）'),
    );

    card.append(head, readout, plot, xAxis, foot);
    return card;
  }

  function resetKey() {
    renderedDetailKey = '';
  }

  function render(container, selected, ctx) {
    if (!selected) {
      container.hidden = true;
      renderedDetailKey = '';
      return;
    }
    const {
      FIELD, provinces, tiers, rankUnit, swatch, markerHidden,
      profiles, profilesReady, decadeData, decadeRanksReady,
      ensureProfiles, ensureDecadeRanks,
    } = ctx;
    const code = selected[FIELD.code];
    const tier = selected[FIELD.tier];
    const decadeCities = decadeData.cities || decadeData;
    const prof = profiles[code];
    const decadeEntry = decadeCities[code];
    const nextKey = code + '|' + (markerHidden ? '0' : '1') + '|' + (prof ? '1' : '0') + '|' + (decadeEntry ? '1' : '0');
    container.hidden = false;
    if (nextKey === renderedDetailKey) return;
    renderedDetailKey = nextKey;

    const coord = selected[FIELD.coord].map(n => n.toFixed(3));
    const head = el('div', 'city-detail-head');
    const titleRow = el('div', 'city-detail-title-row');
    const h3 = el('h3', 'city-detail-name');
    h3.innerHTML = swatch(tier);
    h3.append(document.createTextNode(selected[FIELD.name]));
    const rankMeta = el(
      'span',
      'city-detail-rank',
      provinces[selected[FIELD.province]] + ' · ' + tiers[tier] + '第 ' + selected[FIELD.rank] + ' ' + rankUnit,
    );
    titleRow.append(h3, rankMeta);
    if (prof?.p) titleRow.append(el('span', 'city-detail-pos', prof.p));
    if (markerHidden) titleRow.append(el('span', 'city-detail-hidden-note', '当前未勾选该线级标记'));

    const aside = el('div', 'city-detail-aside');
    aside.append(
      el('span', 'city-detail-coord', (selected[FIELD.urbanRef] ? '城区参考' : '驻地近似') + ' · ' + coord[0] + '°E, ' + coord[1] + '°N'),
    );
    const closeBtn = el('button', 'city-detail-close', '收起');
    closeBtn.type = 'button';
    closeBtn.dataset.action = 'close-detail';
    closeBtn.setAttribute('aria-label', '关闭城市详情');
    aside.append(closeBtn);
    head.append(titleRow, aside);

    const nodes = [head];

    if (prof) {
      const lead = el('div', 'city-detail-lead');
      lead.append(el('p', 'city-detail-intro', prof.i));

      const tagsWrap = el('div', 'city-detail-tags');
      if (prof.hc?.length) {
        tagsWrap.append(el('span', 'detail-tag detail-tag--hist', '国家历史文化名城'));
      }
      for (const tag of prof.h || []) {
        if (tag === '国家历史文化名城') continue;
        tagsWrap.append(el('span', 'detail-tag', tag));
      }
      const spots5a = prof.a5 || [];
      const maxSpots = 4;
      for (const s of spots5a.slice(0, maxSpots)) {
        tagsWrap.append(el('span', 'detail-tag detail-tag--scenic', '5A · ' + s));
      }
      if (spots5a.length > maxSpots) {
        const more = el('span', 'detail-tag detail-tag--scenic', '等 ' + spots5a.length + ' 处 5A 景区');
        more.title = spots5a.join('、');
        tagsWrap.append(more);
      } else if (!spots5a.length) {
        for (const s of (prof.th || []).slice(0, 3)) {
          tagsWrap.append(el('span', 'detail-tag detail-tag--scenic', s));
        }
      }
      if (tagsWrap.childNodes.length) lead.append(tagsWrap);
      nodes.push(lead);

      const grid = el('div', 'city-detail-grid');

      const econCard = el('section', 'detail-card');
      const econHead = el('div', 'detail-card-head');
      econHead.append(el('h4', '', '经济与商业概况'), el('span', 'detail-card-sub', '知城 2025/2026 归档'));
      const kpis = el('dl', 'detail-kpis');
      const [gdp, pop, retail, mallCnt, commScore] = prof.ec || [];
      kpis.append(
        buildKpiItem('地区生产总值', fmtNum(gdp, 0), '亿元'),
        buildKpiItem('常住人口', fmtNum(pop, 0), '万人'),
        buildKpiItem('社会消费品零售总额', fmtNum(retail, 0), '亿元'),
        buildKpiItem(
          '购物中心 / 商业集聚度',
          mallCnt !== null && mallCnt !== undefined ? fmtNum(mallCnt, 0) + ' 座' : fmtNum(commScore, 1) + ' 分',
          mallCnt !== null && mallCnt !== undefined && commScore !== null ? ' · ' + fmtNum(commScore, 1) + ' 分' : '',
        ),
      );
      econCard.append(econHead, kpis);

      const trCard = el('section', 'detail-card');
      const trHead = el('div', 'detail-card-head');
      const isTop3 = tier <= 3;
      trHead.append(
        el('h4', '', '四大公共交通基础设施'),
        el('span', 'detail-card-sub', isTop3 ? '含数量与承载规模' : '有无与数量概览'),
      );
      const trList = el('dl', 'detail-transport-list');
      for (const [label, text, isEmpty] of formatTransportItems(prof.tr || [], isTop3)) {
        trList.append(buildTransportRow(label, text, isEmpty));
      }
      trCard.append(trHead, trList);

      grid.append(econCard, trCard, buildDecadeRankCard(selected[FIELD.name], decadeEntry, decadeData.meta));
      if (!decadeEntry && !decadeRanksReady) ensureDecadeRanks();
      nodes.push(grid);
    } else if (!profilesReady) {
      nodes.push(el('p', 'city-detail-loading', '正在按需加载该城市人文简介、经济与交通数据…'));
      ensureProfiles();
    }

    container.replaceChildren(...nodes);
  }

  return {render, resetKey};
})();
