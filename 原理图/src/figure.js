import { FIELD_GRADIENTS } from './colorScale.js';

export const FIGURE_WIDTH = 2144;
export const FIGURE_HEIGHT = 1328;

const NAVY = '#142e62';
const HEAT = '#ed402b';
const WATER = '#087edb';
const FLOW_LABEL_SIZE = 40;
const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[c]);

function text(x, y, value, { size = 30, fill = NAVY, weight = 500, anchor = 'start', rotate = 0, factor = 1 } = {}) {
  return `<text x="${x}" y="${y}" fill="${fill}" font-size="${size * factor}" font-weight="${weight}" text-anchor="${anchor}"${rotate ? ` transform="rotate(${rotate} ${x} ${y})"` : ''}>${esc(value)}</text>`;
}

function arrow(x1, y1, x2, y2, color = WATER, width = 6, halo = false) {
  const id = color === HEAT ? 'heat' : color === WATER ? 'water' : 'dimension';
  const d = `M ${x1} ${y1} L ${x2} ${y2}`;
  return `${halo ? `<path d="${d}" fill="none" stroke="#ffffff" stroke-opacity=".5" stroke-width="${width + 1.6}" stroke-linecap="round"/>` : ''}<path d="${d}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" marker-end="url(#${id}Arrow)"/>`;
}

function wavePath(x1, y1, x2, y2, amplitude = 6, waves = 2) {
  const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
  const nx = -dy / len, ny = dx / len;
  const point = (t) => {
    const sway = Math.sin(t * Math.PI * 2 * waves) * Math.sin(t * Math.PI) * amplitude;
    return [x1 + dx * t + nx * sway, y1 + dy * t + ny * sway];
  };
  const tangent = (t) => {
    const slope = amplitude * (2 * Math.PI * waves * Math.cos(2 * Math.PI * waves * t) * Math.sin(Math.PI * t)
      + Math.PI * Math.sin(2 * Math.PI * waves * t) * Math.cos(Math.PI * t));
    return [dx + nx * slope, dy + ny * slope];
  };
  const coord = (p) => `${p[0].toFixed(3)} ${p[1].toFixed(3)}`;
  let d = `M ${x1} ${y1}`;
  const steps = 16;
  for (let i = 1; i <= steps; i++) {
    const a = point((i - 1) / steps), b = point(i / steps);
    const da = tangent((i - 1) / steps), db = tangent(i / steps);
    const scale = 1 / (3 * steps);
    d += ` C ${coord([a[0] + da[0] * scale, a[1] + da[1] * scale])}, ${coord([b[0] - db[0] * scale, b[1] - db[1] * scale])}, ${coord(b)}`;
  }
  return d;
}

function wave(x1, y1, x2, y2, color, width = 5, amplitude = 7) {
  const heat = color === HEAT;
  const dx = x2 - x1, dy = y2 - y1, length = Math.hypot(dx, dy);
  const ux = dx / length, uy = dy / length, nx = -uy, ny = ux;
  const headLength = width * 3.4, halfHeadWidth = width * 1.6;
  const base = [x2 - ux * headLength, y2 - uy * headLength];
  const neck = [base[0] - ux * width, base[1] - uy * width];
  const shaftEnd = [base[0] + ux * width, base[1] + uy * width];
  const curveLength = Math.hypot(neck[0] - x1, neck[1] - y1);
  const waves = curveLength > 50 ? 2 : 1;
  const d = `${wavePath(x1, y1, neck[0], neck[1], Math.min(amplitude, curveLength * 0.22), waves)} L ${shaftEnd[0]} ${shaftEnd[1]}`;
  // A separate symmetric head and straight neck keep the wave from entering the head sideways.
  const head = `M ${x2} ${y2} L ${base[0] + nx * halfHeadWidth} ${base[1] + ny * halfHeadWidth} L ${base[0] - nx * halfHeadWidth} ${base[1] - ny * halfHeadWidth} Z`;
  return `<g data-wave-arrow="${heat ? 'heat' : 'water'}"><path d="${d}" fill="none" stroke="url(#${heat ? 'heatWave' : 'waterWave'})" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"/><path data-arrow-head="true" d="${head}" fill="${color}"/></g>`;
}

function gradient(id, colors) {
  return `<linearGradient id="${id}" x1="0%" y1="0%" x2="100%" y2="0%">${colors.map((color, i) => `<stop offset="${i / (colors.length - 1) * 100}%" stop-color="${color}"/>`).join('')}</linearGradient>`;
}

function image(data, box) {
  const padX = (data.padding ?? 0) * box.width / data.width;
  const padY = (data.padding ?? 0) * box.height / data.height;
  return `<image href="${data.url}" x="${box.x - padX}" y="${box.y - padY}" width="${box.width + padX * 2}" height="${box.height + padY * 2}"/>`;
}

function badge(x, y, width, title, factor) {
  return `<rect x="${x}" y="${y}" width="${width}" height="64" rx="16" fill="#e8eefc"/>${text(x + width / 2, y + 43, title, { size: 32, weight: 650, anchor: 'middle', factor })}`;
}

function bullets(centerX, y, lines, factor, lineHeight = 57) {
  const context = document.createElement('canvas').getContext('2d');
  context.font = `500 ${27 * factor}px "Times New Roman", "Songti SC", "SimSun", serif`;
  const width = Math.max(...lines.map((line) => context.measureText(`• ${line}`).width));
  const x = centerX - width / 2;
  return lines.map((line, i) => text(x, y + i * lineHeight, `• ${line}`, { size: 27, factor })).join('');
}

function processArrow(x, y) {
  return `<path d="M ${x - 8} ${y} H ${x + 8} V ${y + 42} H ${x + 21} L ${x} ${y + 70} L ${x - 21} ${y + 42} H ${x - 8} Z" fill="url(#processArrow)"/>`;
}

function stageFlux(rendered, box, resolution, visible) {
  if (!visible) return '';
  return [['heatArrows', HEAT], ['waterArrows', WATER]].map(([key, color]) =>
    (rendered.anchors?.[key] || []).map(([a, b]) => {
      const start = [box.x + a[0] / resolution, box.y + a[1] / resolution];
      const end = [box.x + b[0] / resolution, box.y + b[1] / resolution];
      return wave(...start, ...end, color, color === WATER ? 4.8 : 4.2, color === WATER ? 6 : 4.8);
    }).join(''),
  ).join('');
}

function dimensionLines(whole, box, resolution, factor) {
  const anchors = whole.anchors;
  if (!anchors) return '';
  const point = (p) => [box.x + p[0] / resolution, box.y + p[1] / resolution];
  const a = point(anchors.frontCenter), b = point(anchors.backCenter);
  const delta = [b[0] - a[0], b[1] - a[1]];
  const length = Math.hypot(...delta);
  const n = [delta[1] / length, -delta[0] / length];
  const start = point(anchors.lengthStart);
  const end = point(anchors.lengthEnd);
  const normalPosition = (p) => p[0] * n[0] + p[1] * n[1];
  const linePosition = Math.max(normalPosition(start), normalPosition(end)) + 29;
  const p = [start[0] + n[0] * (linePosition - normalPosition(start)), start[1] + n[1] * (linePosition - normalPosition(start))];
  const q = [end[0] + n[0] * (linePosition - normalPosition(end)), end[1] + n[1] * (linePosition - normalPosition(end))];
  const angle = Math.atan2(delta[1], delta[0]) * 180 / Math.PI;
  const radius = point(anchors.radiusEnd);
  return `<g stroke="#262626" fill="none" stroke-width="2.8">
    <path d="M ${start[0] - n[0] * 2} ${start[1] - n[1] * 2} L ${p[0] + n[0] * 12} ${p[1] + n[1] * 12} M ${end[0] - n[0] * 2} ${end[1] - n[1] * 2} L ${q[0] + n[0] * 12} ${q[1] + n[1] * 12}" stroke-width="2"/>
    <path d="M ${p[0]} ${p[1]} L ${q[0]} ${q[1]}" marker-start="url(#dimensionStart)" marker-end="url(#dimensionArrow)"/>
    <path d="M ${a[0]} ${a[1]} L ${radius[0]} ${radius[1]}" marker-end="url(#dimensionArrow)"/>
    <circle cx="${a[0]}" cy="${a[1]}" r="3" fill="#262626" stroke="none"/>
  </g>${text((p[0] + q[0]) / 2 + n[0] * 24, (p[1] + q[1]) / 2 + n[1] * 24, '长 25 cm', { size: 38, fill: '#202020', weight: 550, anchor: 'middle', rotate: angle, factor })}
  ${text((a[0] + radius[0]) / 2 + 18, (a[1] + radius[1]) / 2 + 38 * factor * 0.34, 'R = 2 cm', { size: 38, fill: '#202020', weight: 550, anchor: 'start', factor })}`;
}

function detailLeaders(whole, box, resolution, cx, cy, radius) {
  const project = (p) => [box.x + p[0] / resolution, box.y + p[1] / resolution];
  const top = project(whole.anchors.detailTop);
  const bottom = project(whole.anchors.detailBottom);
  const x = cx - radius * 0.78;
  return `<path d="M ${top[0]} ${top[1]} L ${x} ${cy - radius * 0.63} M ${bottom[0]} ${bottom[1]} L ${x} ${cy + radius * 0.63}" fill="none" stroke="#454545" stroke-width="2.7" stroke-dasharray="11 11"/>`;
}

export function buildFigure(renderer, state, resolution = 1) {
  const factor = state.labelScale;
  const separated = state.fieldLayout === 'separated';
  const wholeBox = { x: 58, y: 292, width: 770, height: 585 };
  const crossBox = { x: 835, y: 377, width: 490, height: 490 };
  const stageBoxes = [
    { x: 1394, y: 179, width: 415, height: 300 },
    { x: 1394, y: 557, width: 415, height: 300 },
    { x: 1394, y: 927, width: 415, height: 300 },
  ];
  const render = (kind, box, stage) => renderer.render(kind, {
    width: Math.round(box.width * resolution), height: Math.round(box.height * resolution),
    stage, angle: state.angle, textureStrength: state.textureStrength, appearance: state.appearance,
  });
  const whole = render('whole', wholeBox, 'initial');
  const captionX = wholeBox.x + (whole.contentBounds.minX + whole.contentBounds.maxX) / (2 * resolution);
  const captionY = wholeBox.y + whole.contentBounds.maxY / resolution + 46 + 37 * factor;
  const cross = render(separated ? 'crossSeparated' : 'cross', crossBox, 'warming');
  const stages = stageBoxes.map((box, i) => render('cutaway', box, ['initial', 'warming', 'drying'][i]));
  const cx = crossBox.x + crossBox.width / 2, cy = crossBox.y + crossBox.height / 2;
  const radius = 206;
  const radial = (angle, r) => [cx + Math.cos(angle * Math.PI / 180) * r, cy + Math.sin(angle * Math.PI / 180) * r];
  let heatFlow = '', waterFlow = '';
  for (const angle of [-136, -113, -90, -67, -44]) {
    heatFlow += wave(...radial(angle, radius + 142), ...radial(angle, radius + 8), HEAT, 5.2);
  }
  for (const angle of separated ? [202.5, 247.5, 292.5, 337.5] : [22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5]) {
    heatFlow += `<g data-inner-heat-arrow="true">${arrow(...radial(angle, radius - 15), ...radial(angle, 78), HEAT, 6, true)}</g>`;
  }
  for (const angle of separated ? [22.5, 67.5, 112.5, 157.5] : [0, 45, 90, 135, 180, 225, 270, 315]) {
    waterFlow += arrow(...radial(angle, 78), ...radial(angle, radius - 15), WATER, 6, true);
  }
  for (const angle of [40, 65, 90, 115, 140]) {
    waterFlow += wave(...radial(angle, radius + 9), ...radial(angle, radius + 101), WATER, 4.4);
  }
  const drawing = `
    ${detailLeaders(whole, wholeBox, resolution, cx, cy, radius)}
    ${image(whole, wholeBox)}
    ${dimensionLines(whole, wholeBox, resolution, factor)}
    ${text(captionX, captionY, '圆柱形中药材', { size: 37, fill: '#202020', weight: 650, anchor: 'middle', factor })}
    ${image(cross, crossBox)}
    ${heatFlow}${waterFlow}
    ${separated ? `<path data-field-divider="true" d="M ${cx - radius} ${cy} H ${cx + radius}" stroke="#fff" stroke-opacity=".92" stroke-width="3.2"/>` : ''}
    ${text(cx, 246, '热量由外向内传递', { size: FLOW_LABEL_SIZE, fill: HEAT, weight: 650, anchor: 'middle', factor })}
    ${text(cx, 1012, '水分由内部向表面迁移', { size: FLOW_LABEL_SIZE, fill: WATER, weight: 650, anchor: 'middle', factor })}
    <g data-stage-column="true" transform="translate(0 -40)">
    ${image(stages[0], stageBoxes[0])}
    ${badge(1813, 185, 300, '初始状态', factor)}
    ${bullets(1963, 303, ['温度：28 °C', '水分浓度：2.55 kg/kg'], factor, 57)}
    ${processArrow(1602, 479)}
    ${badge(1813, 560, 300, '预热平衡阶段', factor)}
    ${image(stages[1], stageBoxes[1])}${stageFlux(stages[1], stageBoxes[1], resolution, true)}
    ${bullets(1963, 678, ['表面温度先升高', '内部温度逐渐上升', '水分向表面迁移'], factor, 57)}
    ${processArrow(1602, 857)}
    ${badge(1813, 935, 300, '恒温干燥阶段', factor)}
    ${image(stages[2], stageBoxes[2])}${stageFlux(stages[2], stageBoxes[2], resolution, true)}
    ${bullets(1963, 1053, ['内部温差逐渐减小', '水分持续向外迁移', '含水率逐渐降低'], factor, 57)}
    </g>
    ${wave(77, 1218, 218, 1218, HEAT, 5.3, 9)}
    ${text(240, 1229, '热量传递', { size: 27, weight: 600, factor })}
    <rect x="400" y="1201" width="83" height="32" rx="2" fill="url(#temperatureScale)"/>
    ${text(500, 1228, '温度低 → 高', { size: 26, factor })}
    ${arrow(702, 1218, 785, 1218, WATER, 8)}
    ${text(810, 1229, '水分迁移', { size: 27, weight: 600, factor })}
    <rect x="967" y="1201" width="80" height="32" rx="2" fill="url(#moistureScale)"/>
    ${text(1065, 1228, '含水率低 → 高', { size: 26, factor })}
  `;
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 ${FIGURE_WIDTH} ${FIGURE_HEIGHT}" width="${FIGURE_WIDTH}" height="${FIGURE_HEIGHT}" role="img" aria-labelledby="figure-title figure-description">
    <title id="figure-title">${esc(state.title)}</title>
    <desc id="figure-description">圆柱形中药材的热风干燥原理。热量从外部传入，净干燥时水分从内部向表面迁移。${separated ? '中央截面上半显示温度场，下半显示含水率场；两半表示同一径向截面的两个物理量。右侧阶段图保留复合透视示意。' : '暖色受热层与蓝色含水层在同一透视图中展示。'}透视效果为定性示意。</desc>
    <defs>
      <style>text{font-family:"Times New Roman","Songti SC","SimSun",serif;font-kerning:normal;}</style>
      <marker id="heatArrow" markerWidth="4.5" markerHeight="4.5" refX="3.5" refY="2.25" orient="auto" viewBox="0 0 4.5 4.5"><path d="M 0 0 L 4.5 2.25 L 0 4.5 L 1 2.25 Z" fill="${HEAT}"/></marker>
      <marker id="waterArrow" markerWidth="4.5" markerHeight="4.5" refX="3.5" refY="2.25" orient="auto" viewBox="0 0 4.5 4.5"><path d="M 0 0 L 4.5 2.25 L 0 4.5 L 1 2.25 Z" fill="${WATER}"/></marker>
      <marker id="dimensionArrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" viewBox="0 0 6 6"><path d="M 0 0 L 6 3 L 0 6 Z" fill="#262626"/></marker>
      <marker id="dimensionStart" markerWidth="6" markerHeight="6" refX="1" refY="3" orient="auto" viewBox="0 0 6 6"><path d="M 6 0 L 0 3 L 6 6 Z" fill="#262626"/></marker>
      <linearGradient id="heatWave" x1="0%" y1="0%" x2="0%" y2="100%"><stop stop-color="#ffb5a4"/><stop offset="1" stop-color="${HEAT}"/></linearGradient>
      <linearGradient id="waterWave" x1="0%" y1="0%" x2="0%" y2="100%"><stop stop-color="${WATER}"/><stop offset="1" stop-color="#50c4f3"/></linearGradient>
      <linearGradient id="processArrow" x1="0%" y1="0%" x2="100%" y2="0%"><stop stop-color="#9bc0f0"/><stop offset="1" stop-color="#4c8cd8"/></linearGradient>
      ${gradient('temperatureScale', separated ? FIELD_GRADIENTS.temperatureSeparated : FIELD_GRADIENTS.temperature)}
      ${gradient('moistureScale', FIELD_GRADIENTS.moisture)}
    </defs>
    ${state.background === 'white' ? `<rect data-background="white" width="${FIGURE_WIDTH}" height="${FIGURE_HEIGHT}" fill="#fff"/>` : ''}
    ${drawing}
  </svg>`;
}
