import { chromium } from 'playwright';
import { existsSync } from 'node:fs';
import { mkdir,writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const app=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.resolve(app,'..');
const url=process.env.FIGURE_STUDIO_URL||'http://127.0.0.1:5183';
const output=path.join(root,'results','figures');
const qa=path.join(app,'output','playwright');
const executable=process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||[
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
].find(p=>existsSync(p));

let server;
async function alive(){try{const r=await fetch(url);return r.ok;}catch{return false;}}
if(!(await alive())){
  server=spawn(process.execPath,[path.join(app,'node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port','5183','--strictPort'],{cwd:app,stdio:'pipe',windowsHide:true});
  server.on('error',e=>console.error(e.message));
  for(let i=0;i<60&&!(await alive());i++)await new Promise(r=>setTimeout(r,250));
}
if(!(await alive()))throw new Error('无法启动预览，请先执行 npm run build');
let browser;
try{
  browser=await chromium.launch({headless:true,executablePath:executable,args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1760,height:1140},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url,{waitUntil:'networkidle'});
  await page.evaluate(()=>window.figureStudio.ready);
  await mkdir(output,{recursive:true});await mkdir(qa,{recursive:true});
  const report={sources:await page.evaluate(()=>window.figureStudio.sourceInfo()),figures:[],errors};
  if(report.sources.maxC!==0||report.sources.maxT!==0)throw new Error('一致性检查值改变，需要核对新版数据与图11');
  for(let i=1;i<=16;i++){
    const id=String(i).padStart(2,'0');
    await page.evaluate(id=>window.figureStudio.show(id),id);
    const verification=await page.evaluate(()=>{
      const svg=document.querySelector('#figure-stage svg');
      if(!svg)throw new Error('画布中没有 SVG');
      const text=[...svg.querySelectorAll('text')];
      const overflow=text.filter(t=>{const b=t.getBoundingClientRect(),r=svg.getBoundingClientRect();return b.left<r.left-1||b.top<r.top-1||b.right>r.right+1||b.bottom>r.bottom+1;}).map(t=>t.textContent);
      const forbidden=text.filter(t=>/G\d{2}|候选图|图\s*\d+|undefined|NaN/.test(t.textContent)).map(t=>t.textContent);
      return {overflow,forbidden,texts:text.length,images:svg.querySelectorAll('image').length};
    });
    if(verification.overflow.length||verification.forbidden.length)throw new Error(`${id} 标注越界或含多余内容：${JSON.stringify(verification)}`);
    const data=await page.evaluate(id=>window.figureStudio.png(id,2),id);
    await writeFile(path.join(output,`${id}.png`),Buffer.from(data.split(',')[1],'base64'));
    report.figures.push({id,...verification});
    console.log(`Exported ${id}.png (3200 × 2000)`);
    if([1,9,14].includes(i))await page.screenshot({path:path.join(qa,`preview-${id}.png`),fullPage:true});
  }
  if(errors.length)throw new Error(`页面错误：${errors.join('; ')}`);
  await writeFile(path.join(qa,'export-checks.json'),JSON.stringify(report,null,2));
  console.log('16 figures exported; source checks and SVG label bounds passed.');
}finally{
  await browser?.close();server?.kill();
}
