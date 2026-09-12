export const W = 1600, H = 1000;
export const C = { ink:'#203748', mute:'#607381', grid:'#e4ebed', heat:'#d85f32', water:'#197e96', navy:'#234e76', teal:'#438d76', gold:'#b79042', gray:'#9ba9ae' };
export const esc = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
let serial = 0;
export const txt = (x,y,s,size=24,fill=C.ink,anchor='start',extra='') => `<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" text-anchor="${anchor}" ${extra}>${esc(s)}</text>`;
export function math(x,y,s,size=24,fill=C.ink,anchor='start'){
  const parts=s.split(/([_^]\{[^}]+\})/g).filter(Boolean).map(part=>{
    const m=part.match(/^([_^])\{([^}]+)\}$/);
    return m?`<tspan font-size="${size*.7}" baseline-shift="${m[1]==='_'?'sub':'super'}">${esc(m[2])}</tspan>`:esc(part);
  }).join('');
  return `<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" text-anchor="${anchor}">${parts}</text>`;
}
export const line = (x1,y1,x2,y2,color=C.ink,width=2,extra='') => `<path d="M${x1},${y1}L${x2},${y2}" fill="none" stroke="${color}" stroke-width="${width}" ${extra}/>`;
export const rect = (x,y,w,h,fill='none',stroke='none',extra='') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" ${extra}/>`;
export const circle = (x,y,r,fill='none',stroke=C.ink,width=2,extra='') => `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${width}" ${extra}/>`;
export const arrow = (x1,y1,x2,y2,color=C.ink,width=3,dash='') => {
  const a=Math.atan2(y2-y1,x2-x1),l=width*4.1,side=l*.42;
  const bx=x2-Math.cos(a)*l,by=y2-Math.sin(a)*l;
  return line(x1,y1,bx,by,color,width,dash ? `stroke-dasharray="${dash}"` : '')+`<path d="M${x2} ${y2}L${bx-Math.sin(a)*side} ${by+Math.cos(a)*side}L${bx+Math.sin(a)*side} ${by-Math.cos(a)*side}Z" fill="${color}"/>`;
};
export function wave(x1,y1,x2,y2,color=C.heat) {
  const n=50,dx=x2-x1,dy=y2-y1,l=Math.hypot(dx,dy),a=Math.atan2(dy,dx);
  let d=''; for(let i=0;i<n;i++){const t=i/n,off=8*Math.sin(t*Math.PI*6)*Math.sin(t*Math.PI);d+=`${i?'L':'M'}${x1+t*dx-off*dy/l} ${y1+t*dy+off*dx/l}`;}
  return `<path d="${d}" fill="none" stroke="${color}" stroke-width="3.5"/>`+arrow(x2-Math.cos(a)*18,y2-Math.sin(a)*18,x2,y2,color,3.5);
}
export function legend(items,x,y,gap=220){return items.map((a,i)=>line(x+i*gap,y-7,x+i*gap+34,y-7,a.color,3,a.dash?'stroke-dasharray="8 5"':'')+(a.marker?circle(x+i*gap+17,y-7,4.5,'white',a.color,2):'')+txt(x+i*gap+46,y,a.label,22)).join('');}
export function pathXY(xs,ys,sx,sy){let started=false;return xs.map((x,i)=>{const y=ys[i];if(x==null||y==null||!Number.isFinite(y)){started=false;return '';}const p=`${sx(x).toFixed(2)} ${sy(y).toFixed(2)}`;const s=(started?'L':'M')+p;started=true;return s;}).join('');}
export const lin = (lo,hi,start,length) => v=>start+(v-lo)/(hi-lo)*length;
export function plot(o){
  const {x,y,w,h,xd,yd}=o;const log=o.logY;const yy=log?yd.map(Math.log10):yd;
  const sx=lin(...xd,x,w),sy=v=>y+h-( (log?Math.log10(v):v)-yy[0])/(yy[1]-yy[0])*h;
  const id=`clip-${serial++}`;
  let base=`<defs><clipPath id="${id}">${rect(x,y,w,h)}</clipPath></defs>`;
  const xf=o.xFormat??(v=>String(v)), yf=o.yFormat??(v=>String(v));
  (o.yTicks??yd).forEach(v=>{const a=sy(v);base+=(o.grid===false?'':line(x,a,x+w,a,C.grid,1))+line(x-6,a,x,a,C.mute,1.4)+txt(x-14,a+7,yf(v),20,C.mute,'end');});
  (o.xTicks??xd).forEach(v=>{const a=sx(v);base+=line(a,y+h,a,y+h+6,C.mute,1.4)+txt(a,y+h+31,xf(v),20,C.mute,'middle');});
  base+=line(x,y,x,y+h,C.mute,1.5)+line(x,y+h,x+w,y+h,C.mute,1.5);
  if(o.xLabel)base+=txt(x+w/2,y+h+77,o.xLabel,26,C.ink,'middle');
  if(o.yLabel)base+=txt(x-78,y+h/2,o.yLabel,26,C.ink,'middle',`transform="rotate(-90 ${x-78} ${y+h/2})"`);
  return {sx,sy,x,y,w,h,base,clip:s=>`<g clip-path="url(#${id})">${s}</g>`,
    curve:(xs,ys,color=C.navy,width=3,dash='')=>`<path d="${pathXY(xs,ys,sx,sy)}" fill="none" stroke="${color}" stroke-width="${width}" ${dash?`stroke-dasharray="${dash}"`:''}/>` ,
    dots:(xs,ys,color=C.navy,r=3)=>xs.map((v,i)=>circle(sx(v),sy(ys[i]),r,'white',color,1.5)).join(''),
    area:(xs,ys,baseY,color,alpha=.12)=>`<path d="${pathXY(xs,ys,sx,sy)}L${sx(xs.at(-1))} ${sy(baseY)}L${sx(xs[0])} ${sy(baseY)}Z" fill="${color}" fill-opacity="${alpha}"/>`,
  };
}
const scales={
  heat:['#fff6d5','#f9d589','#efa158','#d96a3e','#a33636','#59223e'],
  water:['#eff8e7','#b9dcc2','#76b7b9','#358da5','#236482','#203851'],
  delta:['#346796','#a9c6d9','#f5f6f5','#e4b7a4','#b05043'],
};
export function rgb(value,range,kind='water'){
  const stops=scales[kind],t=Math.min(1,Math.max(0,(value-range[0])/(range[1]-range[0])))*(stops.length-1),i=Math.min(stops.length-2,Math.floor(t)),f=t-i;
  const a=stops[i],b=stops[i+1];return [1,3,5].map(j=>Math.round(parseInt(a.slice(j,j+2),16)*(1-f)+parseInt(b.slice(j,j+2),16)*f));
}
export const color = (v,range,kind='water') => `rgb(${rgb(v,range,kind).join(',')})`;
export function colorbar(x,y,w,h,range,kind,label,ticks){
  const id=`gradient-${serial++}`;
  const defs=`<defs><linearGradient id="${id}" x1="0" y1="1" x2="0" y2="0">${Array.from({length:25},(_,i)=>`<stop offset="${i/24}" stop-color="${color(range[0]+(range[1]-range[0])*i/24,range,kind)}"/>`).join('')}</linearGradient></defs>`;
  let s=defs+rect(x,y,w,h,`url(#${id})`,C.grid);
  (ticks??range).forEach(v=>{const yy=y+h-(v-range[0])/(range[1]-range[0])*h;s+=line(x+w,yy,x+w+5,yy,C.mute,1.4)+txt(x+w+12,yy+7,String(v),19,C.mute);});
  return s+txt(x+w+85,y+h/2,label,23,C.ink,'middle',`transform="rotate(-90 ${x+w+85} ${y+h/2})"`);
}
export function interpolate(xs,ys,v){if(v<=xs[0])return ys[0];if(v>=xs.at(-1))return ys.at(-1);let l=0,r=xs.length-1;while(r-l>1){const m=(l+r)>>1;if(xs[m]<=v)l=m;else r=m;}return ys[l]+(ys[r]-ys[l])*(v-xs[l])/(xs[r]-xs[l]);}
export function spatialRow(r,values,R){
  const pairs=r.map((v,i)=>[v,values[i]]).filter(p=>p[0]!==null&&p[1]!==null&&p[0]<=R+1e-10);
  if(!pairs.length||Math.abs(pairs.at(-1)[0]-R)>1e-9)pairs.push([R,values.at(-1)]);
  return {r:pairs.map(p=>p[0]),v:pairs.map(p=>p[1])};
}
export function fieldImage(p,times,r,values,radii,range,kind,{levels=[],outside='#eef1f2'}={}){
  const nx=241,ny=221,canvas=document.createElement('canvas');canvas.width=nx;canvas.height=ny;
  const ctx=canvas.getContext('2d'),pixels=ctx.createImageData(nx,ny),grid=[];
  const rows=values.map((row,i)=>spatialRow(r,row,radii?.[i]??r.at(-1)));
  let ti=0;
  for(let j=0;j<ny;j++){
    const t=times[0]+(times.at(-1)-times[0])*j/(ny-1);
    while(ti<times.length-2&&times[ti+1]<t)ti++;
    const f=(t-times[ti])/(times[ti+1]-times[ti]),row=[];
    const boundary=radii?interpolate(times,radii,t):r.at(-1);
    for(let i=0;i<nx;i++){
      const x=2*i/(nx-1);let v=null;
      if(x<=boundary+1e-10){
        const a=interpolate(rows[ti].r,rows[ti].v,x),b=interpolate(rows[ti+1].r,rows[ti+1].v,x);v=a+(b-a)*f;
      }
      row.push(v);const k=((ny-1-j)*nx+i)*4;
      const col=v===null?[238,241,242]:rgb(v,range,kind);pixels.data.set([...col,255],k);
    }grid.push(row);
  }
  ctx.putImageData(pixels,0,0);
  let s=rect(p.x,p.y,p.w,p.h,outside)+`<image x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" preserveAspectRatio="none" href="${canvas.toDataURL()}"/>`;
  // Marching squares of the displayed bilinear reconstruction; never extrapolate outside R(t).
  for(const level of levels){let d='';for(let j=0;j<ny-1;j+=2)for(let i=0;i<nx-1;i+=2){
    const pts=[[i,j],[i+2,j],[i+2,j+2],[i,j+2]],v=pts.map(([a,b])=>grid[b]?.[a]);if(v.some(x=>x==null))continue;
    const cuts=[];for(let k=0;k<4;k++){const l=(k+1)%4;if((v[k]<level)===(v[l]<level)||v[k]===v[l])continue;const f=(level-v[k])/(v[l]-v[k]);cuts.push([p.x+(pts[k][0]+(pts[l][0]-pts[k][0])*f)/(nx-1)*p.w,p.y+p.h-(pts[k][1]+(pts[l][1]-pts[k][1])*f)/(ny-1)*p.h]);}
    if(cuts.length===2)d+=`M${cuts[0][0].toFixed(1)} ${cuts[0][1].toFixed(1)}L${cuts[1][0].toFixed(1)} ${cuts[1][1].toFixed(1)}`;
  }s+=`<path d="${d}" fill="none" stroke="white" stroke-width="1.3" stroke-opacity=".75"/>`;}
  return s;
}
export function radialMap(cx,cy,R,xs,ys,range,kind='water'){
  let s='';const n=120;for(let i=n;i>=1;i--){const f=i/n;s+=circle(cx,cy,R*f,color(interpolate(xs,ys,f),range,kind),'none');}
  return s+circle(cx,cy,R,'none',C.mute,1.5);
}
export function wrap(body,{background='white',labelScale=1}={}){
  serial=0;
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img"><defs><style>text{font-family:"Times New Roman","SimSun","Songti SC",serif;font-kerning:normal}path{stroke-linecap:round;stroke-linejoin:round}</style><pattern id="outside-hatch" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M0 12L12 0" stroke="#d7dee0" stroke-width="1"/></pattern><linearGradient id="metal" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#faf9ed"/><stop offset=".42" stop-color="#e9d7b4"/><stop offset="1" stop-color="#bfa789"/></linearGradient></defs>${background==='white'?rect(0,0,W,H,'#fff'):''}${body}</svg>`;
  return svg.replace(/font-size="([\d.]+)"/g,(_,n)=>`font-size="${Number(n)*labelScale}"`);
}
