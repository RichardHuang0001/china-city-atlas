// Label spacing and priorities are measured in screen pixels, independent of projection.
window.atlasLabels = (() => {
  'use strict';
  const svgNamespace = 'http://www.w3.org/2000/svg';
  const narrowMap = 650;

  function createSpatialIndex() {
    const cellSize = 32;
    const cells = new Map();

    function query(box) {
      const hits = new Set();
      const minX = Math.floor(box.left / cellSize);
      const maxX = Math.floor(box.right / cellSize);
      const minY = Math.floor(box.top / cellSize);
      const maxY = Math.floor(box.bottom / cellSize);
      for (let x = minX; x <= maxX; x++) {
        for (let y = minY; y <= maxY; y++) {
          const bucket = cells.get(x + ',' + y);
          if (!bucket) continue;
          for (const item of bucket) {
            if (box.left < item.right && box.right > item.left &&
                box.top < item.bottom && box.bottom > item.top) {
              hits.add(item);
            }
          }
        }
      }
      return hits;
    }

    function add(item) {
      const minX = Math.floor(item.left / cellSize);
      const maxX = Math.floor(item.right / cellSize);
      const minY = Math.floor(item.top / cellSize);
      const maxY = Math.floor(item.bottom / cellSize);
      for (let x = minX; x <= maxX; x++) {
        for (let y = minY; y <= maxY; y++) {
          const key = x + ',' + y;
          if (!cells.has(key)) cells.set(key, []);
          cells.get(key).push(item);
        }
      }
    }

    return {add, query};
  }

  function boxArea(box) {
    return Math.max(0, box.right - box.left) * Math.max(0, box.bottom - box.top);
  }

  function intersectionArea(a, b) {
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return w > 0 && h > 0 ? w * h : 0;
  }

  function priorityTier(width, level, local = false) {
    if (width >= narrowMap) {
      return local ? Math.min(5, 3 + level) : Math.min(5, 1 + level);
    }
    // A narrow map leaves room for the symbols and coastlines at every step.
    if (local) return Math.min(5, 2 + level);
    return level < 2 ? 0 : Math.min(5, level - 1);
  }

  function disclosureRange(width, level, local, minTier) {
    let reveal = priorityTier(width, level, local);
    let fillMax = local ? 5 : Math.min(5, 2 + level);
    // If the user filters out all higher tiers, disclose starting from their highest checked tier.
    if (minTier > reveal) {
      reveal = minTier;
      fillMax = Math.max(fillMax, minTier);
    }
    return {reveal, fillMax};
  }

  function makeLabel(city, [x, y], fontSize, anchor, selected = false, priority = false) {
    const text = document.createElementNS(svgNamespace, 'text');
    text.dataset.city = city[1];
    text.dataset.tier = city[3];
    text.setAttribute('class', 'city-label' +
      (selected ? ' selected' : city[3] < 2 ? ' major' : '') + (priority ? ' priority' : ''));
    text.setAttribute('x', x);
    text.setAttribute('y', y);
    text.setAttribute('text-anchor', anchor);
    text.setAttribute('font-size', fontSize);
    text.setAttribute('stroke-width', fontSize * .24);
    text.textContent = city[0];
    return text;
  }

  function closeOptions(x, y, gap, height) {
    const halfH = height / 2;
    const diagX = gap * .86;
    const diagY = gap * .52 + halfH * .48;
    return [
      {x: x + gap, y, anchor: 'start', order: 0},
      {x: x - gap, y, anchor: 'end', order: 1},
      {x, y: y - gap - halfH, anchor: 'middle', order: 2},
      {x, y: y + gap + halfH, anchor: 'middle', order: 3},
      {x: x + diagX, y: y - diagY, anchor: 'start', order: 4},
      {x: x + diagX, y: y + diagY, anchor: 'start', order: 5},
      {x: x - diagX, y: y - diagY, anchor: 'end', order: 6},
      {x: x - diagX, y: y + diagY, anchor: 'end', order: 7},
    ];
  }

  function displacedOptions(x, y, gap, height, maxDistance) {
    const options = [];
    for (let distance = 12; distance <= maxDistance; distance += 8) {
      for (let direction = 0; direction < 16; direction++) {
        const angle = direction * Math.PI / 8;
        const dx = Math.cos(angle);
        const dy = Math.sin(angle);
        const vertical = Math.abs(dx) < .36;
        options.push({
          x: x + dx * (gap + distance),
          y: y + dy * (gap + distance) + (vertical ? Math.sign(dy) * height / 2 : 0),
          anchor: vertical ? 'middle' : dx > 0 ? 'start' : 'end',
          distance,
          displaced: true,
        });
      }
    }
    return options;
  }

  function labelBox(point, width, height) {
    const left = point.x - (point.anchor === 'middle' ? width / 2 : point.anchor === 'end' ? width : 0);
    return {left, right: left + width, top: point.y - height / 2, bottom: point.y + height / 2};
  }

  function evaluateText(box, textIndex, allowOverlap) {
    const selfArea = boxArea(box);
    let totalOverlap = 0;
    let maxRatio = 0;
    let score = 0;
    for (const other of textIndex.query(box)) {
      if (other.uiObstacle) return null;
      const area = intersectionArea(box, other);
      if (!area) continue;
      const otherArea = boxArea(other);
      const ratio = Math.max(area / selfArea, area / otherArea);
      if (!allowOverlap || ratio > allowOverlap) return null;
      totalOverlap += area / selfArea;
      if (totalOverlap > allowOverlap * 1.3) return null;
      if (ratio > maxRatio) maxRatio = ratio;
      score += ratio * (other.provinceLabel ? 26 : 120);
    }
    return {score, maxRatio};
  }

  function evaluateMarkers(box, tier, isFocus, pointsIndex, strictHigherMarkers) {
    let score = 0;
    let blockedHigher = false;
    for (const marker of pointsIndex.query(box)) {
      const area = intersectionArea(box, marker);
      if (!area) continue;
      const ratio = area / boxArea(marker);
      if (marker.isFocus || marker.tier < tier) {
        if (strictHigherMarkers && !isFocus && ratio > .25) return null;
        blockedHigher = true;
        score += 90 + ratio * 180;
      } else if (marker.tier === tier) {
        if (strictHigherMarkers && !isFocus && ratio > .3) return null;
        score += 36 + ratio * 70;
      }
      // Lower-tier markers (marker.tier > tier) are ignored so toggling them never shifts or drops higher tiers.
    }
    return {score, blockedHigher};
  }

  function leaderQuality(x, y, radius, box, tier, textIndex, pointsIndex) {
    const nearX = Math.max(box.left, Math.min(box.right, x));
    const nearY = Math.max(box.top, Math.min(box.bottom, y));
    const length = Math.hypot(nearX - x, nearY - y);
    const dx = (nearX - x) / length;
    const dy = (nearY - y) / length;
    let penalty = 0;
    for (let step = radius + 2; step < length - 2; step += 4) {
      const px = x + dx * step;
      const py = y + dy * step;
      const sample = {left: px - .5, right: px + .5, top: py - .5, bottom: py + .5};
      for (const hit of textIndex.query(sample)) {
        if (!hit.provinceLabel) penalty += 9;
      }
      if (step > radius + 5) {
        for (const marker of pointsIndex.query(sample)) {
          if (marker.tier <= tier) penalty += 2;
        }
      }
    }
    return {
      cost: length + penalty * 10,
      penalty,
      line: [x, y, nearX - dx * 2, nearY - dy * 2],
    };
  }

  function hasNearbyLabel(box, spacingPad, textIndex) {
    if (spacingPad <= 0) return false;
    const padded = {
      left: box.left - spacingPad,
      right: box.right + spacingPad,
      top: box.top - spacingPad * .65,
      bottom: box.bottom + spacingPad * .65,
    };
    for (const hit of textIndex.query(padded)) {
      if (!hit.uiObstacle && !hit.provinceLabel) return true;
    }
    return false;
  }

  function choosePlacement({
    x, y, radius, tier, isFocus, width, height, fontSize, name,
    required, preferred, spacingPad, mobile, textIndex, pointsIndex,
  }) {
    const labelWidth = Array.from(name).length * fontSize + 1.5;
    const labelHeight = fontSize + 1.5;
    const gap = radius + 2.5;
    const softOverlapLimit = required ? .28 : preferred ? .2 : .12;
    const strictMarkers = !required;

    let bestClose;
    for (const option of closeOptions(x, y, gap, labelHeight)) {
      const box = labelBox(option, labelWidth, labelHeight);
      if (box.left < 3 || box.top < 3 || box.right > width - 3 || box.bottom > height - 3) continue;
      if (hasNearbyLabel(box, spacingPad, textIndex)) continue;
      const textEval = evaluateText(box, textIndex, softOverlapLimit);
      if (!textEval) continue;
      const markerEval = evaluateMarkers(box, tier, isFocus, pointsIndex, strictMarkers);
      if (!markerEval) continue;
      const score = option.order * 1.4 + textEval.score + markerEval.score;
      if (score === 0) return {option, box};
      if (!bestClose || score < bestClose.score) bestClose = {option, box, score, textEval, markerEval};
    }

    // Prefer slight close overlap over drawing a leader line whenever reasonably legible.
    if (bestClose && bestClose.textEval.maxRatio <= (required ? .22 : softOverlapLimit) &&
        !bestClose.markerEval.blockedHigher) {
      return bestClose;
    }

    if (!required) return bestClose;

    const maxLeader = mobile ? 24 : 36;
    let bestLeader;
    for (const option of displacedOptions(x, y, gap, labelHeight, maxLeader)) {
      const box = labelBox(option, labelWidth, labelHeight);
      if (box.left < 3 || box.top < 3 || box.right > width - 3 || box.bottom > height - 3) continue;
      const textEval = evaluateText(box, textIndex, 0);
      if (!textEval) continue;
      const markerEval = evaluateMarkers(box, tier, isFocus, pointsIndex, true);
      if (!markerEval) continue;
      const {line, cost, penalty} = leaderQuality(x, y, radius, box, tier, textIndex, pointsIndex);
      if (penalty > 0) continue;
      const score = 38 + cost + markerEval.score;
      if (!bestLeader || score < bestLeader.score) bestLeader = {option, box, line, score};
    }

    if (bestClose && (!bestLeader || bestClose.score <= bestLeader.score)) return bestClose;
    if (bestLeader) return bestLeader;
    if (bestClose) return bestClose;

    // Last resort for required cities (Tier 0 / selected): relax overlap cap on close options.
    let relaxed;
    for (const option of closeOptions(x, y, gap, labelHeight)) {
      const box = labelBox(option, labelWidth, labelHeight);
      if (box.left < 3 || box.top < 3 || box.right > width - 3 || box.bottom > height - 3) continue;
      const textEval = evaluateText(box, textIndex, .55);
      if (!textEval) continue;
      const markerEval = evaluateMarkers(box, tier, isFocus, pointsIndex, false);
      const score = option.order + textEval.score + markerEval.score;
      if (!relaxed || score < relaxed.score) relaxed = {option, box, score};
    }
    return relaxed;
  }

  function drawLeader(city, [x1, y1, x2, y2], left, top, units, color) {
    const leader = document.createElementNS(svgNamespace, 'g');
    leader.dataset.leaderFor = city[1];
    leader.setAttribute('class', 'label-leader');
    leader.setAttribute('stroke', color);
    const line = document.createElementNS(svgNamespace, 'line');
    line.setAttribute('x1', left + x1 * units);
    line.setAttribute('y1', top + y1 * units);
    line.setAttribute('x2', left + x2 * units);
    line.setAttribute('y2', top + y2 * units);
    const halo = line.cloneNode();
    halo.setAttribute('class', 'leader-halo');
    line.setAttribute('class', 'leader-ink');
    leader.append(halo, line);
    return leader;
  }

  function place({markers, width, height, left, top, units, level, local, focus, obstacles, colors}) {
    const labels = document.createDocumentFragment();
    const leaders = document.createDocumentFragment();
    if (!markers.length) return {labels, leaders};
    const mobile = width < narrowMap;
    const font = mobile ? 11 : 12.5;
    const textIndex = createSpatialIndex();
    const pointsIndex = createSpatialIndex();
    for (const box of obstacles) textIndex.add({...box});

    const candidates = [];
    let minTier = 5;
    for (const {city, point, size} of markers) {
      const x = (point[0] - left) / units;
      const y = (point[1] - top) / units;
      if (x < 0 || y < 0 || x > width || y > height) continue;
      const radius = size + 1.35;
      const isFocus = city[1] === focus;
      const tier = isFocus ? -1 : city[3];
      if (city[3] < minTier) minTier = city[3];
      pointsIndex.add({
        left: x - radius, right: x + radius, top: y - radius, bottom: y + radius,
        tier, isFocus,
      });
      candidates.push({city, x, y, radius, tier, isFocus});
    }
    if (!candidates.length) return {labels, leaders};

    const {reveal, fillMax} = disclosureRange(width, level, local, minTier);
    const spacingPad = local ? 0 : Math.max(4, (mobile ? 18 : 14) - level * 3);

    // Place highest-priority cities first so lower tiers never displace higher tiers.
    candidates.sort((a, b) =>
      Number(b.isFocus) - Number(a.isFocus) ||
      a.city[3] - b.city[3] || a.city[4] - b.city[4]);

    const placedLabels = [];
    for (const candidate of candidates) {
      const {city, isFocus} = candidate;
      if (!isFocus && city[3] > fillMax) continue;
      const preferred = city[3] <= reveal;
      const required = isFocus || city[3] === 0 || (!mobile && preferred);
      const fontSize = isFocus ? font + 1.5 : city[3] < 2 ? font + .5 : font;
      const best = choosePlacement({
        ...candidate, width, height, fontSize, name: city[0],
        required, preferred, spacingPad: preferred || isFocus ? 0 : spacingPad,
        mobile, textIndex, pointsIndex,
      });
      if (!best) continue;
      const {option, box, line} = best;
      if (line) leaders.append(drawLeader(city, line, left, top, units, colors[city[3]]));
      placedLabels.push(makeLabel(city, [left + option.x * units, top + option.y * units],
        fontSize * units, option.anchor, isFocus, required));
      textIndex.add(box);
    }

    // Append in reverse priority order so higher-tier labels paint on top if slightly overlapping.
    for (let i = placedLabels.length - 1; i >= 0; i--) {
      labels.append(placedLabels[i]);
    }
    return {labels, leaders};
  }

  return {makeLabel, place, priorityTier, narrowMap};
})();
