import './style.css';
import { createHerbRenderer } from './render.js';
import { buildFigure, FIGURE_WIDTH, FIGURE_HEIGHT } from './figure.js';

const DEFAULTS = Object.freeze({ appearance: 'fibrous', fieldLayout: 'composite', background: 'white', angle: 0, textureStrength: 1, labelScale: 1, title: '烘干过程变化示意' });
let state = { ...DEFAULTS };
try {
  const appearance = sessionStorage.getItem('herb-diagram-appearance');
  if (appearance === 'fibrous' || appearance === 'starchy') state.appearance = appearance;
} catch { /* A blocked browser storage area must not prevent drawing. */ }
let renderer;
let pendingRender;
let busy = false;

document.querySelector('#app').innerHTML = `
  <header class="toolbar">
    <div class="identity"><svg viewBox="0 0 32 32" aria-hidden="true"><ellipse cx="11" cy="21" rx="6" ry="8" transform="rotate(-30 11 21)"/><path d="M7 14 22 5c3-2 9 9 5 12L14 27"/></svg><h1>药材烘干原理图</h1></div>
    <div class="toolbar-actions"><button class="plain-button" id="fit-button" aria-pressed="true">适应窗口</button><span class="divider"></span><span class="canvas-size">2144 × 1328</span><button id="export-button" class="primary-button" disabled><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2v10m-4-4 4 4 4-4M3 13v4h14v-4"/></svg><span>导出 PNG</span></button></div>
  </header>
  <main class="workspace">
    <section class="stage" aria-label="原理图预览">
      <div id="figure-frame" class="figure-frame"><div class="loading"><span class="spinner"></span>正在生成药材纹理与剖面…</div></div>
    </section>
    <aside class="settings" aria-label="画面与导出设置">
      <section class="setting-section">
        <h2>画面</h2>
        <label class="field-label" for="appearance">药材外观</label><select id="appearance"><option value="fibrous">细纵皱根段 · 黄芪／甘草式</option><option value="starchy">粉质切段 · 葛根／山药式</option></select>
        <label class="field-label" for="field-layout">中央截面</label><select id="field-layout"><option value="composite">复合示意 · 原版</option><option value="separated">上下分区 · 温度 / 含水率</option></select>
        <div class="range-heading"><label for="angle">观察角度</label><output id="angle-value">0°</output></div><input type="range" id="angle" min="-15" max="15" step="1" value="0" />
        <div class="range-heading"><label for="texture">表皮纹理</label><output id="texture-value">100%</output></div><input type="range" id="texture" min="0" max="1.8" step="0.05" value="1" />
        <div class="range-heading"><label for="label-scale">标注字号</label><output id="label-scale-value">100%</output></div><input type="range" id="label-scale" min="0.9" max="1.2" step="0.01" value="1" />
        <button id="reset-button" class="reset-button">恢复参考构图</button>
      </section>
      <section class="setting-section">
        <h2>导出</h2>
        <span class="field-label">背景</span>
        <div class="segmented" role="group" aria-label="导出背景"><button data-background="white" class="selected" aria-pressed="true"><i class="white-swatch"></i>白色</button><button data-background="transparent" aria-pressed="false"><i class="transparent-swatch"></i>透明</button></div>
        <p class="field-hint" id="background-hint">白色背景会包含在导出图片中。</p>
        <label class="field-label" for="format">格式</label><select id="format"><option value="png">PNG 图片</option><option value="svg">SVG · 矢量文字与标注</option></select>
        <label class="field-label" for="resolution">图像精度</label><select id="resolution"><option value="1">1× · 2144 × 1328</option><option value="2" selected>2× · 4288 × 2656</option><option value="3">3× · 6432 × 3984</option></select>
        <p class="field-hint">SVG 保留文字和箭头，药材为嵌入式三维渲染图像。</p>
      </section>
      <p class="scope-note" id="scope-note">暖色表现受热，蓝色含水层表现水分变化；两类箭头分别表示传热与水分迁移。仅作定性示意。</p>
      <div id="status" role="status" aria-live="polite">正在准备预览</div>
    </aside>
  </main>`;

const frame = document.querySelector('#figure-frame');
const exportButton = document.querySelector('#export-button');
const status = document.querySelector('#status');
const formatInput = document.querySelector('#format');
document.querySelector('#appearance').value = state.appearance;

function refreshBackground() {
  frame.classList.toggle('transparent', state.background === 'transparent');
  document.querySelectorAll('[data-background]').forEach((button) => {
    if (!(button instanceof HTMLButtonElement)) return;
    const selected = button.dataset.background === state.background;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  document.querySelector('#background-hint').textContent = state.background === 'transparent'
    ? '棋盘格只用于预览，不会出现在导出文件中。'
    : '白色背景会包含在导出图片中。';
}

function refreshFigure() {
  if (!renderer || busy) return;
  try {
    frame.innerHTML = buildFigure(renderer, state, 1.5);
    refreshBackground();
    document.querySelector('#scope-note').textContent = state.fieldLayout === 'separated'
      ? '中央截面上半为温度场，下半为含水率场，表示同一截面的两个物理量。右侧阶段图保留复合示意；各色场均为定性表达。'
      : '暖色表现受热，蓝色含水层表现水分变化；两类箭头分别表示传热与水分迁移。仅作定性示意。';
    status.textContent = '预览已更新';
  } catch (error) {
    console.error(error);
    status.textContent = `画面生成失败：${error.message}`;
  }
}

function scheduleFigure() {
  clearTimeout(pendingRender);
  pendingRender = setTimeout(refreshFigure, 90);
}

for (const [id, key, format] of [
  ['angle', 'angle', (v) => `${v}°`],
  ['texture', 'textureStrength', (v) => `${Math.round(v * 100)}%`],
  ['label-scale', 'labelScale', (v) => `${Math.round(v * 100)}%`],
]) {
  document.querySelector(`#${id}`).addEventListener('input', (event) => {
    state[key] = Number(event.target.value);
    document.querySelector(`#${id}-value`).textContent = format(state[key]);
    scheduleFigure();
  });
}

document.querySelector('#appearance').addEventListener('change', (event) => {
  state.appearance = event.target.value;
  try { sessionStorage.setItem('herb-diagram-appearance', state.appearance); } catch { /* Preview remains usable without storage. */ }
  refreshFigure();
});

document.querySelector('#field-layout').addEventListener('change', (event) => {
  state.fieldLayout = event.target.value;
  refreshFigure();
});

document.querySelectorAll('button[data-background]').forEach((button) => button.addEventListener('click', () => {
  state.background = button.dataset.background;
  refreshBackground();
  // Background is an SVG layer, so this change does not require another 3D render.
  const svg = frame.querySelector('svg');
  svg?.querySelector('[data-background="white"]')?.remove();
  if (svg && state.background === 'white') {
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    for (const [key, value] of Object.entries({ width: FIGURE_WIDTH, height: FIGURE_HEIGHT, fill: '#fff', 'data-background': 'white' })) rect.setAttribute(key, value);
    svg.insertBefore(rect, svg.querySelector('defs').nextSibling);
  }
  status.textContent = state.background === 'transparent' ? '透明背景预览' : '白色背景预览';
}));

document.querySelector('#reset-button').addEventListener('click', () => {
  const { background, appearance, fieldLayout } = state;
  state = { ...DEFAULTS, background, appearance, fieldLayout };
  for (const [id, value, display] of [['angle', 0, '0°'], ['texture', 1, '100%'], ['label-scale', 1, '100%']]) {
    document.querySelector(`#${id}`).value = value;
    document.querySelector(`#${id}-value`).textContent = display;
  }
  refreshFigure();
});

document.querySelector('#fit-button').addEventListener('click', (event) => {
  const natural = frame.classList.toggle('natural-size');
  event.currentTarget.textContent = natural ? '100% · 点击适应' : '适应窗口';
  event.currentTarget.setAttribute('aria-pressed', String(!natural));
});

formatInput.addEventListener('change', () => {
  exportButton.querySelector('span').textContent = `导出 ${formatInput.value.toUpperCase()}`;
});

export async function svgToPng(svg, scale) {
  const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }));
  const image = new Image();
  try {
    image.src = url;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = FIGURE_WIDTH * scale;
    canvas.height = FIGURE_HEIGHT * scale;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('无法创建图片画布');
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    return await new Promise((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('图片编码失败')), 'image/png'));
  } finally {
    URL.revokeObjectURL(url);
  }
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

exportButton.addEventListener('click', async () => {
  if (!renderer || busy) return;
  busy = true;
  exportButton.disabled = true;
  clearTimeout(pendingRender);
  const scale = Number(document.querySelector('#resolution').value);
  const format = formatInput.value;
  const snapshot = { ...state };
  status.textContent = '正在生成导出图像…';
  try {
    await new Promise(requestAnimationFrame);
    await document.fonts.ready;
    const svg = buildFigure(renderer, snapshot, scale);
    const blob = format === 'svg'
      ? new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
      : await svgToPng(svg, scale);
    download(blob, `药材烘干原理图_${snapshot.appearance === 'starchy' ? '粉质切段' : '细纵皱根段'}${snapshot.fieldLayout === 'separated' ? '_上下分区' : ''}_${snapshot.background === 'transparent' ? '透明' : '白底'}.${format}`);
    status.textContent = `已生成 ${format.toUpperCase()}，请查看浏览器下载`;
  } catch (error) {
    console.error(error);
    status.textContent = `导出失败：${error.message}`;
  } finally {
    busy = false;
    exportButton.disabled = false;
    if (Object.keys(snapshot).some((key) => snapshot[key] !== state[key])) refreshFigure();
  }
});

async function initialize() {
  try {
    renderer = await createHerbRenderer();
    if (renderer.availableAppearances) {
      for (const option of document.querySelector('#appearance').options) option.disabled = !renderer.availableAppearances.includes(option.value);
    }
    await document.fonts.ready;
    refreshFigure();
    exportButton.disabled = false;
    status.textContent = '可以调整画面，或选择背景后导出';
  } catch (error) {
    console.error(error);
    frame.innerHTML = '<div class="loading error">无法初始化三维渲染。请使用支持 WebGL 2 的浏览器重新打开。</div>';
    status.textContent = error.message;
  }
}

initialize();
window.addEventListener('pagehide', (event) => { if (!event.persisted) renderer?.dispose(); });
