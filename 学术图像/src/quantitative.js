import { C,txt,line,rect,circle,arrow,legend,plot,colorbar,fieldImage,radialMap,interpolate,color,spatialRow } from './svg.js';

const column=(q,k,c)=>q[k].map(r=>r.at(c));
const ticks=(a,b,step)=>Array.from({length:Math.floor((b-a)/step)+1},(_,i)=>+(a+i*step).toFixed(8));
const threshold=(p,v=.15)=>line(p.x,p.sy(v),p.x+p.w,p.sy(v),C.gold,2,'stroke-dasharray="8 6"');
function endpoint(p,x,y,label,color=C.navy,dx=-25,dy=-45){return circle(p.sx(x),p.sy(y),5,color,'#fff',2)+line(p.sx(x),p.sy(y)-6,p.sx(x)+dx,p.sy(y)+dy+6,color,1.2)+txt(p.sx(x)+dx,p.sy(y)+dy,label,22,color,'middle');}
function sideNote(x,y,a,b,color=C.ink){return txt(x,y,a,26,color)+txt(x,y+39,b,21,C.mute);}

export function environment(D){
  const e=D.environment;
  let s=legend([{label:'观测',color:C.navy,marker:true},{label:'分段线性插值',color:C.heat},{label:'3–4 h 均值',color:C.gray,dash:true}],174,91,295);
  for(let i=0;i<2;i++){
    const isT=!i,key=isT?'T':'C',range=isT?[26,54]:[.015,.06],cl=isT?C.heat:C.water;
    const p=plot({x:153,y:i?572:164,w:1190,h:261,xd:[0,5],yd:range,xTicks:ticks(0,5,1),yTicks:isT?[28,34,40,46,52]:[.02,.03,.04,.05,.06],xLabel:i?'t / h':'',yLabel:isT?'T∞ / °C':'C∞ / (kg/kg)'});
    s+=rect(p.sx(3),p.y,p.sx(4)-p.sx(3),p.h,'#f0f3f3')+p.base;
    s+=p.clip(p.curve(e.t,e[key],cl,2)+p.dots(e.t,e[key],C.navy,2)+line(p.sx(3),p.sy(e.plateau[i]),p.sx(5),p.sy(e.plateau[i]),C.gray,2,'stroke-dasharray="9 6"'));
    s+=txt(1372,p.sy(e.plateau[i])+6,e.plateau[i].toFixed(isT?3:5),24,cl);
  }
  return s;
}
export function radius(D){
  const r=D.radius,end=D.q[4].endH;let s='';
  [0,3,12,end].forEach((t,i)=>{const cx=280+i*345,R=interpolate(r.curveT,r.curveR,t);s+=circle(cx,145,76,'none',C.gray,1.2,'stroke-dasharray="5 5"')+circle(cx,145,76*R/2,'#deece8',C.teal,2)+arrow(cx,145,cx+76*R/2,145,C.teal,1.8)+txt(cx,254,`t = ${i===3?t.toFixed(4):t} h`,23,C.ink,'middle');});
  const p=plot({x:148,y:330,w:1264,h:244,xd:[0,72],yd:[1.15,2.05],xTicks:[0,12,24,36,48,60,72],yTicks:[1.2,1.4,1.6,1.8,2],yLabel:'R / cm'});
  s+=p.base+p.clip(p.curve(r.curveT,r.curveR,C.teal,3)+p.dots(r.t,r.R,C.navy,2.8)+line(p.sx(end),p.y,p.sx(end),p.y+p.h,C.gold,1.7,'stroke-dasharray="7 6"'));
  s+=legend([{label:'附件2观测',color:C.navy,marker:true},{label:'PCHIP',color:C.teal},{label:`t* = ${end.toFixed(4)} h`,color:C.gold,dash:true}],175,307,338);
  const minimum=Math.floor(Math.min(...r.rate)*10)/10;
  const p2=plot({x:148,y:701,w:1264,h:170,xd:[0,72],yd:[minimum,.02],xTicks:[0,12,24,36,48,60,72],yTicks:[minimum,minimum/2,0],xLabel:'t / h',yLabel:'dR/dt / (cm/h)',yFormat:v=>v.toFixed(2)});
  s+=p2.base+p2.clip(p2.area(r.curveT,r.rate,0,C.teal,.15)+p2.curve(r.curveT,r.rate,C.teal,2.7)+line(p2.sx(end),p2.y,p2.sx(end),p2.y+p2.h,C.gold,1.7,'stroke-dasharray="7 6"'));return s;
}
export function scales(D){
  const q=D.q[3],ss=q.scales;const logs=values=>{const lo=Math.floor(Math.log10(Math.min(...values))),hi=Math.ceil(Math.log10(Math.max(...values)));return {range:[10**lo,10**hi],ticks:Array.from({length:hi-lo+1},(_,i)=>10**(lo+i))};};
  const sup=n=>String(n).split('').map(c=>({'-':'⁻','0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹'}[c])).join('');
  const fmt=v=>'10'+sup(Math.round(Math.log10(v)));
  const a=logs(ss.flatMap(s=>[...s.heat,...s.moisture])),b=logs(ss.flatMap(s=>s.ratio));
  const p=plot({x:152,y:194,w:622,h:601,xd:[0,58],yd:a.range,xTicks:[0,10,20,30,40,50],yTicks:a.ticks,yFormat:fmt,logY:true,xLabel:'t / h',yLabel:'τ / h'});
  const p2=plot({x:1000,y:194,w:459,h:601,xd:[0,58],yd:b.range,xTicks:[0,15,30,45],yTicks:b.ticks,yFormat:fmt,logY:true,xLabel:'t / h',yLabel:'α/D'});
  let s=p.base+p2.base;
  ss.forEach((a,i)=>{s+=p.clip(p.curve(q.t,a.heat,C.heat,3,i?'9 6':'')+p.curve(q.t,a.moisture,C.water,3,i?'9 6':''))+p2.clip(p2.curve(q.t,a.ratio,C.navy,3,i?'9 6':''));});
  s+=legend([{label:'τT = R₀²/α',color:C.heat},{label:'τC = R₀²/D',color:C.water}],199,130,291)+legend([{label:'中心',color:C.ink},{label:'表面',color:C.ink,dash:true}],1012,130,200);
  s+=txt(458,936,'α = k/(ρcₚ)',30,C.heat,'middle')+txt(1170,936,'τC/τT = α/D',30,C.navy,'middle');return s;
}
function doubleFields(D,qNumber,height=422){
  const q=D.q[qNumber],f=q.field,end=qNumber===1?.5:3;
  let s='';const configs=[{x:129,key:'T',range:[28,qNumber===1?37:51],kind:'heat',ticks:qNumber===1?[28,31,34,37]:[28,36,44,51],levels:qNumber===1?[30,32,34,36]:[30,35,40,45,49]},
    {x:903,key:'C',range:qNumber===1?[1.5,2.55]:[.2,2.55],kind:'water',ticks:qNumber===1?[1.5,1.85,2.2,2.55]:[.2,1,1.8,2.55],levels:qNumber===1?[1.7,2,2.3,2.5]:[.5,1,1.5,2,2.5]}];
  for(const c of configs){
    const p=plot({x:c.x,y:99,w:451,h:height,xd:[0,2],yd:[0,end],xTicks:[0,.5,1,1.5,2],yTicks:qNumber===1?[0,.1,.2,.3,.4,.5]:[0,.5,1,1.5,2,2.5,3],xLabel:'r / cm',yLabel:'t / h',grid:false});
    s+=fieldImage(p,f.t,q.r,f[c.key],f.R,c.range,c.kind,{levels:c.levels})+p.base;
    s+=colorbar(c.x+479,99,19,height,c.range,c.kind,c.key==='T'?'T / °C':'C / (kg/kg)',c.ticks);
  }return s;
}
export function q1(D){
  let s=doubleFields(D,1,412);const q=D.q[1];
  [q.profiles[0],q.profiles[2],q.profiles[3]].forEach((p,i)=>{
    const xs=p.r.map(v=>v/2);for(let k=0;k<2;k++){
      const cx=(k?972:199)+i*205,cy=752;s+=radialMap(cx,cy,73,xs,p[k?'C':'T'],k?[1.5,2.55]:[28,37],k?'water':'heat')+txt(cx,872,`t = ${p.t.toFixed(1)} h`,23,C.ink,'middle');
      s+=arrow(cx,cy,cx+73,cy,'#ffffff',1.3);
    }
  });return s;
}
export function q2(D){
  let s=doubleFields(D,2,346);const q=D.q[2];
  for(let k=0;k<2;k++){
    const p=plot({x:k?903:129,y:653,w:451,h:205,xd:[0,2],yd:k?[.2,2.6]:[28,52],xTicks:[0,.5,1,1.5,2],yTicks:k?[.5,1.5,2.5]:[28,36,44,52],xLabel:'r / cm',yLabel:k?'C / (kg/kg)':'T / °C'});
    s+=p.base;q.profiles.forEach((a,i)=>{s+=p.clip(p.curve(a.r,a[k?'C':'T'],[C.gray,C.gold,C.teal,C.navy][i],2.8));});
  }
  s+=legend(q.profiles.map((p,i)=>({label:`t = ${p.t} h`,color:[C.gray,C.gold,C.teal,C.navy][i]})),296,975,280);return s;
}
export function consistency(D){
  const a=D.consistency,eps=1e-12;let s='';
  for(let k=0;k<2;k++){
    const p=plot({x:k?911:148,y:185,w:445,h:536,xd:[0,58],yd:[0,2],xTicks:[0,15,30,45,57.4741],yTicks:[0,.5,1,1.5,2],xFormat:v=>v===57.4741?'57.47':v,xLabel:'t / h',yLabel:'r / cm'});
    // The observed difference is identically zero. A neutral matrix is the honest field.
    const key=k?'T':'C',max=k?a.maxT:a.maxC;
    s+=rect(p.x,p.y,p.w,p.h,color(0,[-eps,eps],'delta'))+p.base;
    for(let i=1;i<21;i++)s+=line(p.x,p.sy(i*.1),p.x+p.w,p.sy(i*.1),'#e1e7e8',.7);
    s+=txt(p.x+p.w/2,124,key==='T'?'ΔT = T₂ − T₃':'ΔC = C₂ − C₃',31,C.ink,'middle');
    s+=rect(p.x+65,p.y+219,p.w-130,87,'#fff','none','fill-opacity=".9"')+txt(p.x+p.w/2,p.y+272,`max |Δ${key}| = ${max}`,27,C.navy,'middle');
    s+=colorbar(p.x+p.w+23,p.y,18,p.h,[-eps,eps],'delta',key==='T'?'ΔT / °C':'ΔC / (kg/kg)',[-eps,0,eps]);
  }
  s+=txt(800,922,`Nₜ = ${a.checkedTimes}     Nᵣ = ${a.checkedRadii}`,28,C.ink,'middle');return s;
}
export function drying(D){
  const q=D.q[3],cc=column(q,'C',0),cs=column(q,'C',-1);
  const p=plot({x:147,y:170,w:1315,h:638,xd:[0,60],yd:[0,2.7],xTicks:[0,10,20,30,40,50,60],yTicks:[0,.5,1,1.5,2,2.5],xLabel:'t / h',yLabel:'C / (kg/kg)'});
  let s=p.base+p.clip(p.area(q.t,cc,0,C.navy,.05)+p.curve(q.t,cc,C.navy,3.5)+p.curve(q.t,q.meanC,C.teal,3)+p.curve(q.t,cs,C.heat,3)+threshold(p));
  s+=legend([{label:'中心 / 最大值',color:C.navy},{label:'柱测度平均',color:C.teal},{label:'表面',color:C.heat},{label:'C = 0.15',color:C.gold,dash:true}],178,100,314);
  const zoom=plot({x:781,y:259,w:601,h:267,xd:[35,58],yd:[.045,.26],xTicks:[35,40,45,50,55],yTicks:[.05,.1,.15,.2,.25]});
  s+=rect(719,216,695,379,'white','#dce5e7','rx="4"')+zoom.base+zoom.clip(zoom.curve(q.t,cc,C.navy,3)+zoom.curve(q.t,q.meanC,C.teal,2.5)+zoom.curve(q.t,cs,C.heat,2.5)+threshold(zoom));
  s+=endpoint(zoom,q.endH,cc.at(-1),`${q.endH.toFixed(4)} h`,C.navy,-70,-34);
  s+=rect(p.sx(35),p.sy(.26),p.sx(58)-p.sx(35),p.sy(.045)-p.sy(.26),'none',C.gray,'stroke-dasharray="7 6"')+line(p.sx(35),p.sy(.26),739,598,C.gray,1.5,'stroke-dasharray="7 6"')+line(p.sx(58),p.sy(.26),1382,598,C.gray,1.5,'stroke-dasharray="7 6"');
  s+=endpoint(p,q.endH,cc.at(-1),'t* = 57.4741 h',C.navy,-80,-60);return s;
}
export function finalProfiles(D){
  let s='';for(let k=0;k<2;k++){
    const q=D.q[k?4:3],x=k?925:145,cl=k?C.teal:C.navy;
    const p=plot({x,y:461,w:487,h:360,xd:[0,1],yd:[0,.165],xTicks:[0,.25,.5,.75,1],yTicks:[0,.05,.1,.15],xLabel:'ξ = r/R',yLabel:'C / (kg/kg)'});
    s+=radialMap(x+243,216,116*q.endR/2,q.final.xi,q.final.C,[.05,.15]);
    s+=txt(x+243,386,`t* = ${q.endH.toFixed(4)} h`,26,cl,'middle');
    s+=p.base+p.clip(p.area(q.final.xi,q.final.C,0,cl,.13)+p.curve(q.final.xi,q.final.C,cl,3.2)+threshold(p));
    s+=txt(x+243,94,k?'R = 1.2 cm':'R = 2.0 cm',27,cl,'middle');
    s+=legend([{label:k?'收缩域终态':'固定域终态',color:cl}],x+135,974,220);
  }s+=colorbar(755,144,15,157,[.05,.15],'water','C / (kg/kg)',[.05,.1,.15]);return s;
}
export function movingField(D){
  const q=D.q[4],f=q.field;
  const p=plot({x:140,y:180,w:513,h:604,xd:[0,2],yd:[0,q.endH],xTicks:[0,.5,1,1.5,2],yTicks:[0,10,20,30,40,50],xLabel:'r / cm',yLabel:'t / h',grid:false});
  let s=fieldImage(p,f.t,q.r,f.C,f.R,[.05,2.55],'water',{levels:[.15,.5,1,2]})+p.base+p.curve(q.R,q.t,C.heat,2.9);
  s+=colorbar(678,180,19,604,[.05,2.55],'water','C / (kg/kg)',[.05,.5,1,1.5,2,2.55]);
  s+=txt(583,307,'r > R(t)',24,C.mute,'middle');
  const p2=plot({x:1005,y:180,w:443,h:604,xd:[0,2],yd:[0,2.7],xTicks:[0,.5,1,1.5,2],yTicks:[0,.5,1,1.5,2,2.5],xLabel:'r / cm',yLabel:'C / (kg/kg)'});
  s+=p2.base;
  const colors=[C.gray,C.gold,C.teal,C.water,C.navy];q.profiles.forEach((p,i)=>{s+=p2.clip(p2.curve(p.r,p.C,colors[i],3)+circle(p2.sx(p.r.at(-1)),p2.sy(p.C.at(-1)),5,colors[i],'white',1.5));});
  s+=legend([{label:'R(t)',color:C.heat}],159,116,230)+legend(q.profiles.map((p,i)=>({label:`${p.t} h`,color:colors[i]})),987,120,111);
  s+=txt(396,935,`R(t*) = ${q.endR.toFixed(1)} cm`,27,C.heat,'middle')+txt(1227,935,`t* = ${q.endH.toFixed(4)} h`,27,C.navy,'middle');return s;
}
export function coupling(D){
  const q=D.q[4],r=D.radius,observed=r.t.map((t,i)=>({t,R:r.R[i]})).filter(p=>p.t<=q.endH);
  const p=plot({x:150,y:125,w:1020,h:251,xd:[0,52],yd:[.55,1.03],xTicks:[0,10,20,30,40,50],yTicks:[.6,.7,.8,.9,1],yLabel:'R/R₀'});
  let s=p.base+p.clip(p.area(q.t,q.R.map(r=>r/2),.6,C.teal,.1)+p.curve(q.t,q.R.map(r=>r/2),C.teal,3)+p.dots(observed.map(r=>r.t),observed.map(r=>r.R/2),C.navy,2.5));
  const p2=plot({x:150,y:551,w:1020,h:299,xd:[0,52],yd:[0,2.7],xTicks:[0,10,20,30,40,50],yTicks:[0,.5,1,1.5,2,2.5],xLabel:'t / h',yLabel:'C / (kg/kg)'});
  s+=p2.base+p2.clip(p2.curve(q.t,column(q,'C',0),C.navy,3)+p2.curve(q.t,column(q,'C',-1),C.heat,3)+threshold(p2));
  s+=legend([{label:'半径输入',color:C.teal},{label:'观测',color:C.navy,marker:true}],174,89,225)+legend([{label:'中心',color:C.navy},{label:'实际表面',color:C.heat}],174,512,225);
  [0,6,24,q.endH].forEach((t,i)=>{const cx=1350,cy=175+i*206,R=interpolate(q.t,q.R,t);s+=circle(cx,cy,61,'none',C.gray,1.3,'stroke-dasharray="5 5"')+circle(cx,cy,61*R/2,'#d9eae5',C.teal,2)+txt(cx,cy+98,`${t===q.endH?t.toFixed(4):t} h`,23,C.ink,'middle');});
  s+=endpoint(p2,q.endH,q.C.at(-1)[0],`${q.endH.toFixed(4)} h`,C.navy,-88,-52);return s;
}
export function comparison(D){
  const q3=D.q[3],q4=D.q[4];let s='';
  for(let k=0;k<2;k++){
    const p=plot({x:k?929:148,y:230,w:494,h:522,xd:[0,60],yd:[0,2.7],xTicks:[0,15,30,45,60],yTicks:[0,.5,1,1.5,2,2.5],xLabel:'t / h',yLabel:'C / (kg/kg)'});
    s+=p.base;
    [q3,q4].forEach((q,i)=>{const a=column(q,'C',k?-1:0),cl=i?C.teal:C.navy;s+=p.clip(p.curve(q.t,a,cl,3.3,i?'9 5':'')+threshold(p))+endpoint(p,q.endH,a.at(-1),q.endH.toFixed(4),cl,i?-65:8,i?-93:-45);});
    const cx=p.x+p.w/2;s+=circle(cx,120,47,'#f4f8f7',C.gray,1.5)+circle(k?cx+47:cx,120,6,k?C.heat:C.navy,'white',1.5)+txt(cx,201,k?'r = R(t)':'r = 0',28,C.ink,'middle');
  }
  s+=legend([{label:'固定域',color:C.navy},{label:'收缩域',color:C.teal,dash:true},{label:'C = 0.15',color:C.gold,dash:true}],395,930,318);return s;
}
