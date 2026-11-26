// Label spacing and priorities are measured in screen pixels, independent of projection.
window.atlasLabels = (() => {
  'use strict';
  const svgNamespace = 'http://www.w3.org/2000/svg';
  const narrowMap = 650;

  function indexRectangles() {
    const cellSize = 32;
    const cells = new Map();

    function visit(box, callback) {
      for (let x = Math.floor(box.left / cellSize); x <= Math.floor(box.right / cellSize); x++) {
        for (let y = Math.floor(box.top / cellSize); y <= Math.floor(box.bottom / cellSize); y++) {
          if (callback(x + ',' + y)) return true;
        }
      }
      return false;
    }

    return {
      add(box) {
        visit(box, key => {
          if (!cells.has(key)) cells.set(key, []);
          cells.get(key).push(box);
          return false;
        });
      },
      overlaps(box) {
        return visit(box, key => cells.get(key)?.some(other =>
          box.left < other.right && box.right > other.left &&
          box.top < other.bottom && box.bottom > other.top));
      },
    };
  }

  function priorityTier(width, level) {
    if (width >= narrowMap) return Math.min(5, 1 + level);
    // A narrow map leaves room for the symbols and coastlines at every step.
    return Math.min(3, Math.max(0, level - 1));
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
    text.setAttribute('stroke-width', fontSize * .21);
    text.textContent = city[0];
    return text;
  }

  function labelOptions(x, y, gap, height, maxDistance) {
    const options = [
      {x: x + gap, y, anchor: 'start'},
      {x: x - gap, y, anchor: 'end'},
      {x, y: y - gap - height / 2, anchor: 'middle'},
      {x, y: y + gap + height / 2, anchor: 'middle'},
    ];
    for (let distance = 8; distance <= maxDistance; distance += (distance < 24 ? 8 : 12)) {
      for (let direction = 0; direction < 16; direction++) {
        const angle = direction * Math.PI / 8;
        const dx = Math.cos(angle);
        const dy = Math.sin(angle);
        const vertical = Math.abs(dx) < .36;
        options.push({
          x: x + dx * (gap + distance),
          y: y + dy * (gap + distance) + (vertical ? Math.sign(dy) * height / 2 : 0),
          anchor: vertical ? 'middle' : dx > 0 ? 'start' : 'end',
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

  function leaderQuality(x, y, radius, box, text, points) {
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
      if (text.overlaps(sample)) penalty += 9;
      else if (step > radius + 5 && points.overlaps(sample)) penalty += 2;
    }
    return {
      cost: length + penalty * 10,
      penalty,
      line: [x, y, nearX - dx * 2, nearY - dy * 2],
    };
  }

  function choosePlacement({x, y, radius, width, height, fontSize, name, required, preferred, mobile, text, points}) {
    const labelWidth = Array.from(name).length * fontSize + 4;
    const labelHeight = fontSize + 4;
    const gap = radius + 3;
    const search = required ? (mobile ? 56 : 122) : preferred ? 24 : 0;
    let fallback;
    for (const option of labelOptions(x, y, gap, labelHeight, search)) {
      const box = labelBox(option, labelWidth, labelHeight);
      if (box.left < 4 || box.top < 4 || box.right > width - 4 || box.bottom > height - 4 ||
          text.overlaps(box)) continue;
      const overMarker = points.overlaps(box);
      if (!overMarker && !option.displaced) return {option, box};
      if (!option.displaced || (overMarker && !required)) continue;

      const {line, cost, penalty} = leaderQuality(x, y, radius, box, text, points);
      if (!overMarker && !penalty && (!required || cost <= 28)) return {option, box, line};
      if (required) {
        const score = cost + (overMarker ? 400 : 0);
        if (!fallback || score < fallback.score) fallback = {option, box, line, score};
      }
    }
    return fallback;
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
    const reveal = priorityTier(width, level);
    const basePitch = local ? (mobile ? 72 : 57) : (mobile ? 94 : 98);
    const pitch = Math.max(local ? 0 : mobile ? 42 : 28, basePitch - level * (mobile ? 15 : 22));
    const rowPitch = pitch * .59;
    const occupiedCells = new Set();
    const text = indexRectangles();
    const points = indexRectangles();
    for (const box of obstacles) text.add(box);

    const candidates = [];
    for (const {city, point, size} of markers) {
      const x = (point[0] - left) / units;
      const y = (point[1] - top) / units;
      if (x < 0 || y < 0 || x > width || y > height) continue;
      const radius = size + 1.35;
      points.add({left: x - radius, right: x + radius, top: y - radius, bottom: y + radius});
      candidates.push({city, x, y, radius});
    }

    candidates.sort((a, b) =>
      Number(b.city[1] === focus) - Number(a.city[1] === focus) ||
      a.city[3] - b.city[3] || a.city[4] - b.city[4]);

    for (const candidate of candidates) {
      const {city, x, y} = candidate;
      const selected = city[1] === focus;
      const preferred = city[3] <= reveal;
      const required = selected || city[3] === 0 || (!mobile && preferred);
      const cell = pitch ? Math.floor(x / pitch) + ',' + Math.floor(y / rowPitch) : '';
      if (cell && !selected && !preferred && occupiedCells.has(cell)) continue;
      const fontSize = selected ? font + 1.5 : city[3] < 2 ? font + .5 : font;
      const best = choosePlacement({...candidate, width, height, fontSize, name: city[0],
        required, preferred, mobile, text, points});
      if (!best) continue;
      const {option, box, line} = best;
      if (line) leaders.append(drawLeader(city, line, left, top, units, colors[city[3]]));
      labels.append(makeLabel(city, [left + option.x * units, top + option.y * units],
        fontSize * units, option.anchor, selected, required));
      text.add(box);
      if (cell) occupiedCells.add(cell);
    }
    return {labels, leaders};
  }

  return {makeLabel, place, priorityTier, narrowMap};
})();
