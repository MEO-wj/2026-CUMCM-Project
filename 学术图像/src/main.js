import './style.css';
import { figures } from './catalog.js';
import { renderFigure,sourceInfo } from './renderFigures.js';
import { pngBlob,download,zipBlob } from './export.js';

let selected=/^#(?:0[1-9]|1[0-6])$/.test(location.hash)?location.hash.slice(1):'01';
let settings={background:'white',labelScale:1};
let busy=false,revision=0,currentSVG='';
const icon=`<svg viewBox="0 0 36 36" fill="none" aria-hidden="true"><circle cx="18" cy="18" r="13" stroke="currentColor" stroke-width="1.4"/><circle cx="18" cy="18" r="8" stroke="currentColor" stroke-width="1.4"/><path d="M18 2v32M2 18h32" stroke="currentColor" stroke-width="1.3"/></svg>`;
const groupNames=[...new Set(figures.map(f=>f.group))];
document.querySelector('#app').innerHTML=`
  <aside class="library"><a class="brand" href="#01">${icon}<span>药材烘干<small>学术图像工作台</small></span></a>
  <div class="library-label">FIGURE COLLECTION <span>16</span></div>
  <nav aria-label="图像目录">${groupNames.map((name,i)=>`<section class="group"><h2><span>0${i+1}</span>${name}</h2>${figures.filter(f=>f.group===name).map(f=>`<button class="figure-item" data-id="${f.id}"><span class="figure-number">${f.id}</span><span>${f.name}<small>${f.kind}</small></span><i></i></button>`).join('')}</section>`).join('')}</nav>
  <div class="library-bottom"><span class="live-dot"></span>本地计算结果 · 可复现</div></aside>
  <div class="main-column"><header class="topbar"><div class="breadcrumb">论文图像 <span>/</span> <span id="current-group"></span></div><div class="top-actions"><button id="export-all" class="button secondary">整套导出 ZIP <span>↗</span></button><button id="export-one" class="button primary" disabled>导出当前图 <span>↓</span></button></div></header>
  <main><section class="figure-heading"><div><div id="figure-kind" class="eyebrow"></div><h1 id="figure-name"></h1></div><div class="pager"><button id="previous" aria-label="上一张图">←</button><span id="counter"></span><button id="next" aria-label="下一张图">→</button></div></section>
  <section class="work-area"><div class="preview-column"><div class="stage-toolbar"><span><i class="live-dot"></i>导出画布</span><span>1600 × 1000</span></div><div class="figure-stage" id="figure-stage"><div class="loading">正在载入图像…</div></div><div class="stage-footer"><span id="status" role="status" aria-live="polite">准备中</span><button id="fullscreen" class="text-button">放大预览 ↗</button></div></div>
  <aside class="inspector"><h2>画面设置</h2><label for="background">背景</label><select id="background"><option value="white">白色 · 论文排版</option><option value="transparent">透明</option></select><div class="range-label"><label for="label-scale">标注字号</label><output id="label-value">100%</output></div><input id="label-scale" type="range" min="0.9" max="1.1" step="0.02" value="1"><div class="inspector-rule"></div><h2>导出设置</h2><label for="format">格式</label><select id="format"><option value="png">PNG · 高清图片</option><option value="svg">SVG · 可编辑图形</option></select><label for="resolution">尺寸</label><select id="resolution"><option value="1">1600 × 1000</option><option value="2" selected>3200 × 2000</option><option value="3">4800 × 3000</option></select><p class="setting-note">导出包含图形与核心标注。图题和说明保留在画布外。</p><button class="button reset" id="reset">恢复默认设置</button></aside></section>
  <section class="figure-notes"><div><span class="note-label">图像内容</span><p id="meaning"></p></div><div><span class="note-label">建议位置</span><p id="position"></p></div><div class="wide-note"><span class="note-label">数据与使用说明</span><p id="note"></p></div></section></main></div>`;

const stage=document.querySelector('#figure-stage'),status=document.querySelector('#status');
const one=document.querySelector('#export-one'),all=document.querySelector('#export-all');
function refreshMetadata(){const f=figures.find(f=>f.id===selected);document.querySelector('#figure-name').textContent=f.name;document.querySelector('#figure-kind').textContent=f.kind;document.querySelector('#current-group').textContent=f.group;document.querySelector('#counter').textContent=`${selected} / 16`;for(const key of ['meaning','position','note'])document.querySelector(`#${key}`).textContent=f[key];document.querySelectorAll('[data-id]').forEach(b=>{const a=b.dataset.id===selected;b.classList.toggle('active',a);b.setAttribute('aria-current',a?'true':'false');});}
async function show(id=selected){
  selected=id;refreshMetadata();history.replaceState(null,'',`#${id}`);const version=++revision;
  one.disabled=true;status.textContent='正在渲染…';
  try{const svg=await renderFigure(id,settings);if(version!==revision)return;currentSVG=svg;stage.innerHTML=svg;stage.classList.toggle('transparent',settings.background==='transparent');stage.dataset.figure=id;status.textContent='预览已更新';one.disabled=busy;}
  catch(error){if(version!==revision)return;stage.innerHTML='<div class="loading">图像载入失败，请查看下方状态。</div>';status.textContent=`生成失败：${error.message}`;console.error(error);}
}
document.querySelectorAll('[data-id]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.id)));
document.querySelector('#previous').addEventListener('click',()=>show(String(Number(selected)===1?16:Number(selected)-1).padStart(2,'0')));
document.querySelector('#next').addEventListener('click',()=>show(String(Number(selected)===16?1:Number(selected)+1).padStart(2,'0')));
document.querySelector('#background').addEventListener('change',e=>{settings.background=e.target.value;show();});
document.querySelector('#label-scale').addEventListener('input',e=>{settings.labelScale=Number(e.target.value);document.querySelector('#label-value').textContent=`${Math.round(settings.labelScale*100)}%`;show();});
document.querySelector('#format').addEventListener('change',e=>document.querySelector('#resolution').disabled=e.target.value==='svg');
document.querySelector('#reset').addEventListener('click',()=>{settings={background:'white',labelScale:1};document.querySelector('#background').value='white';document.querySelector('#label-scale').value='1';document.querySelector('#label-value').textContent='100%';show();});
document.querySelector('#fullscreen').addEventListener('click',()=>{stage.classList.toggle('expanded');document.querySelector('#fullscreen').textContent=stage.classList.contains('expanded')?'适应窗口 ↙':'放大预览 ↗';});
window.addEventListener('hashchange',()=>{if(/^#(?:0[1-9]|1[0-6])$/.test(location.hash))show(location.hash.slice(1));});
async function exportBlob(id,format,scale,options){const svg=await renderFigure(id,options);return format==='svg'?new Blob([svg],{type:'image/svg+xml;charset=utf-8'}):pngBlob(svg,scale);}
async function exportAction(every){
  if(busy)return;busy=true;one.disabled=all.disabled=true;
  const format=document.querySelector('#format').value,scale=Number(document.querySelector('#resolution').value),options={...settings},requestedId=selected;
  try{
    if(every){const files=[];for(const f of figures){status.textContent=`正在导出 ${f.id} / 16…`;files.push({name:`${f.id}.${format}`,blob:await exportBlob(f.id,format,scale,options)});await new Promise(r=>setTimeout(r,0));}download(await zipBlob(files),`药材烘干学术图像_${format.toUpperCase()}.zip`);}
    else download(await exportBlob(requestedId,format,scale,options),`${requestedId}.${format}`);
    status.textContent=every?'16 张图已打包下载':'图片已下载';
  }catch(e){status.textContent=`导出失败：${e.message}`;console.error(e);}finally{busy=false;one.disabled=all.disabled=false;}
}
one.addEventListener('click',()=>exportAction(false));all.addEventListener('click',()=>exportAction(true));

// Batch exporter uses the same renderer and encoder as the visible buttons.
window.figureStudio={
  ready:show(), render:renderFigure, show,
  sourceInfo:()=>({hashes:sourceInfo.hashes,endHours:sourceInfo.endHours,endR:sourceInfo.endR,maxC:sourceInfo.checks.maxC,maxT:sourceInfo.checks.maxT}),
  async png(id,scale=2,options={background:'white',labelScale:1}){
    const blob=await exportBlob(id,'png',scale,options);return await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(blob);});
  },
};
