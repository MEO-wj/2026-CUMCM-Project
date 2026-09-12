import { C,txt,math,line,rect,circle,arrow,wave,legend } from './svg.js';

const polar=(x,y,r,a)=>[x+r*Math.cos(a),y+r*Math.sin(a)];
function ring(cx,cy,ro,ri,fill,stroke=C.mute){
  return `<path d="M${cx-ro} ${cy}a${ro} ${ro} 0 1 0 ${2*ro} 0a${ro} ${ro} 0 1 0 ${-2*ro} 0M${cx-ri} ${cy}a${ri} ${ri} 0 1 1 ${2*ri} 0a${ri} ${ri} 0 1 1 ${-2*ri} 0" fill="${fill}" fill-rule="evenodd" stroke="${stroke}" stroke-width="1.5"/>`;
}
export function herb(renderer,kind,x,y,w,h,stage='warming'){
  const image=renderer.render(kind,{width:Math.round(w*1.5),height:Math.round(h*1.5),appearance:'starchy',stage,angle:0,textureStrength:.85});
  const pad=image.padding/1.5;
  return `<image x="${x-pad}" y="${y-pad}" width="${w+2*pad}" height="${h+2*pad}" href="${image.url}"/>`;
}
export function mechanism(renderer){
  let s=herb(renderer,'whole',45,195,720,455,'initial');
  s+=herb(renderer,'crossSeparated',910,176,490,490);
  s+=line(627,309,937,280,C.gray,1.8,'stroke-dasharray="8 7"')+line(608,515,944,591,C.gray,1.8,'stroke-dasharray="8 7"');
  const cx=1155,cy=421,R=224;
  for(const a of [-150,-115,-80,-45]){const r=a*Math.PI/180;s+=wave(...polar(cx,cy,R+103,r),...polar(cx,cy,R+12,r),C.heat)+arrow(...polar(cx,cy,R-12,r),...polar(cx,cy,90,r),C.heat,4);}
  for(const a of [32,68,108,147]){const r=a*Math.PI/180;s+=arrow(...polar(cx,cy,87,r),...polar(cx,cy,R-12,r),C.water,4)+wave(...polar(cx,cy,R+12,r),...polar(cx,cy,R+92,r),C.water);}
  s+=circle(cx,cy,4,C.ink,'none')+arrow(cx,cy,cx+R,cy,C.ink,2)+txt(cx+22,cy-15,'r = 0',24)+txt(cx+126,cy-15,'R(t)',25);
  s+=txt(1155,86,'q',34,C.heat,'middle')+txt(1155,801,'J',34,C.water,'middle');
  s+=herb(renderer,'cutaway',65,668,345,249,'drying');
  s+=txt(434,753,'T₀ = 28 °C',29)+txt(434,805,'C₀ = 2.55 kg/kg',29)+txt(434,857,'R₀ = 2 cm',29);
  s+=legend([{label:'q = h(T∞ − Tₛ)',color:C.heat},{label:'J = hₘ(Cₛ − C∞)',color:C.water}],893,903,343);
  return s;
}
function moduleBox(x,y,w,label,icon,equation){
  const cx=x+w/2,cy=y+155;
  return rect(x,y,w,305,'#f9fbfb','#dbe4e6','rx="20" stroke-width="1.5"')+txt(x+30,y+45,label,27,C.ink)+`<g transform="translate(${cx} ${cy}) scale(.82) translate(${-cx} ${-cy})">${icon(cx,cy)}</g>`+math(cx,y+278,equation,23,C.ink,'middle');
}
function inputIcon(cx,cy){let s='';for(let j=0;j<2;j++){s+=line(cx-104,cy+45+j*50,cx+106,cy+45+j*50,C.gray,1.3)+line(cx-104,cy-65+j*50,cx-104,cy+45+j*50,C.gray,1.3);for(let i=0;i<7;i++)s+=circle(cx-88+i*30,cy+30+j*50-80*(1-Math.exp(-i*.7)),4,'white',j?C.water:C.heat,2);s+=`<path d="M${cx-88},${cy+30+j*50}C${cx-40},${cy-55+j*50} ${cx+20},${cy-55+j*50} ${cx+93},${cy-55+j*50}" fill="none" stroke="${j?C.water:C.heat}" stroke-width="2.5"/>`;}return s;}
function propertyIcon(cx,cy){let s='';for(let j=0;j<3;j++)s+=`<path d="M${cx-95} ${cy+70}C${cx-85} ${cy-95+j*35} ${cx+5} ${cy-70+j*35} ${cx+98} ${cy-75+j*35}" fill="none" stroke="${[C.heat,C.water,C.teal][j]}" stroke-width="3"/>`;return s+line(cx-98,cy-100,cx-98,cy+75,C.mute,1.5)+line(cx-98,cy+75,cx+105,cy+75,C.mute,1.5);}
function fvIcon(cx,cy){let s='';for(let i=5;i>=1;i--)s+=circle(cx,cy,i*20,i%2?'#ebf3f3':'#fff',C.water,1.2);return s+arrow(cx-115,cy,cx-26,cy,C.water,3)+arrow(cx+26,cy,cx+115,cy,C.water,3);}
function moveIcon(cx,cy){return circle(cx,cy,104,'none',C.gray,2,'stroke-dasharray="8 6"')+circle(cx,cy,67,'#e2f0ee',C.teal,2.5)+arrow(cx-96,cy,cx-73,cy,C.teal,3)+arrow(cx+96,cy,cx+73,cy,C.teal,3)+arrow(cx,cy-96,cx,cy-73,C.teal,3)+arrow(cx,cy+96,cx,cy+73,C.teal,3);}
function checkIcon(cx,cy){return line(cx-102,cy+35,cx+110,cy+35,C.heat,2,'stroke-dasharray="6 5"')+`<path d="M${cx-95} ${cy-93}C${cx-79} ${cy+2} ${cx+2} ${cy+43} ${cx+96} ${cy+43}" fill="none" stroke="${C.navy}" stroke-width="3.5"/>`+circle(cx+36,cy+35,7,C.water,'white',2)+txt(cx+49,cy+4,'t*',25,C.water);}
export function workflow(){
  let s=moduleBox(100,104,395,'观测输入',inputIcon,'T∞(t), C∞(t), R(t)')+moduleBox(600,104,395,'物性更新',propertyIcon,'D(C,T), k(C), ρcₚ')+moduleBox(1100,104,395,'守恒通量',fvIcon,'d(U_{i}V_{i})/dt = F_{i−1/2} − F_{i+1/2}');
  s+=moduleBox(850,601,490,'动边界映射',moveIcon,'ξ = r/R(t)')+moduleBox(200,601,490,'终点与一致性',checkIcon,'max C ≤ 0.15');
  s+=arrow(505,257,580,257,C.mute,3)+arrow(1004,257,1080,257,C.mute,3)+`<path d="M1300 429V490H1100V576" fill="none" stroke="${C.mute}" stroke-width="3"/>`+arrow(1100,540,1100,583,C.mute,3)+arrow(829,754,711,754,C.mute,3);
  s+=`<path d="M869 926V956H1539V66H798V80" fill="none" stroke="${C.teal}" stroke-width="2.3" stroke-dasharray="8 7"/>`+arrow(798,54,798,83,C.teal,2.5)+txt(1430,509,'t + Δt',25,C.teal,'middle');return s;
}
export function boundaries(renderer){
  const cx=395,cy=446,R=235;let s=herb(renderer,'crossSeparated',135,186,520,520);
  s+=circle(cx,cy,R+45,'none',C.gray,2,'stroke-dasharray="8 8"')+arrow(cx,cy,cx+R,cy,C.ink,2.5)+circle(cx,cy,4,C.ink,'none');
  s+=txt(372,420,'r = 0',25)+txt(540,420,'R(t)',26)+txt(395,809,'∂T/∂r = 0',31,C.heat,'middle')+txt(395,863,'∂C/∂r = 0',31,C.water,'middle');
  s+=line(599,300,840,256,C.gray,1.8,'stroke-dasharray="7 6"')+line(619,588,840,734,C.gray,1.8,'stroke-dasharray="7 6"');
  s+=rect(847,228,189,533,'#f7ecd9')+rect(1036,228,120,533,'#edf4f6')+rect(1156,228,321,533,'#fbfcfc');
  s+=line(1036,208,1036,784,C.ink,2)+line(1156,228,1156,761,C.gray,1.5,'stroke-dasharray="6 6"');
  s+=txt(927,184,'药材',27,C.ink,'middle')+txt(1096,184,'气膜',27,C.ink,'middle')+txt(1325,184,'热风',27,C.ink,'middle');
  s+=wave(1410,368,896,368,C.heat)+arrow(896,616,1410,616,C.water,4);
  s+=txt(1394,319,'T∞',32,C.heat,'end')+txt(996,319,'Tₛ',32,C.heat,'middle')+txt(996,565,'Cₛ',32,C.water,'middle')+txt(1394,565,'C∞',32,C.water,'end');
  s+=txt(1160,426,'q = h(T∞ − Tₛ)',29,C.heat,'middle')+txt(1160,679,'J = hₘ(Cₛ − C∞)',29,C.water,'middle');
  s+=txt(1160,845,'k ∂T/∂r = h(T∞ − Tₛ)',28,C.heat,'middle')+txt(1160,901,'−D ∂C/∂r = hₘ(Cₛ − C∞)',28,C.water,'middle');return s;
}
export function volumes(){
  const cx=392,cy=444;let s='';const rad=[0,57,116,173,222,261];
  for(let i=rad.length-1;i>0;i--)s+=ring(cx,cy,rad[i],rad[i-1],i===3?'#c5e2e1':i%2?'#f1f6f6':'#fff');
  for(let i=1;i<rad.length;i++){const rr=(rad[i]+rad[i-1])/2;s+=circle(cx+rr,cy,5,i===3?C.water:C.ink,'white',1.4);}
  s+=arrow(cx,cy,cx+309,cy,C.ink,2)+txt(cx+311,cy+35,'r',29)+txt(cx-18,cy-26,'0',24);
  s+=line(cx+116,cy,cx+116,cy+92,C.gray,1,'stroke-dasharray="5 5"')+line(cx+173,cy,cx+173,cy+142,C.gray,1,'stroke-dasharray="5 5"');
  s+=math(cx+108,cy+120,'r_{i−1/2}',24,C.ink,'end')+math(cx+181,cy+169,'r_{i+1/2}',24)+math(cx+145,cy-24,'r_{i}',25,C.water,'middle');
  s+=line(566,232,799,265,C.gray,1.5,'stroke-dasharray="7 6"')+line(565,655,799,645,C.gray,1.5,'stroke-dasharray="7 6"');
  const xs=[812,1019,1226];for(let i=0;i<3;i++){s+=rect(xs[i],282,207,325,i===1?'#d4eae8':'#f4f7f7',C.gray,'stroke-width="1.4"')+circle(xs[i]+103,cy,6,C.ink,'white',1.5)+txt(xs[i]+103,670,['i − 1','i','i + 1'][i],28,C.ink,'middle');}
  s+=arrow(922,356,1118,356,C.water,4)+arrow(1127,540,1330,540,C.water,4)+math(1019,316,'F_{i−1/2}',28,C.water,'middle')+math(1226,589,'F_{i+1/2}',28,C.water,'middle');
  s+=math(1120,186,'r_{i−1/2} < r < r_{i+1/2}',32,C.ink,'middle');
  s+=math(400,837,'V_{i} = πL(r²_{i+1/2} − r²_{i−1/2})',30,C.ink,'middle')+math(1116,837,'d(U_{i}V_{i})/dt = F_{i−1/2} − F_{i+1/2}',30,C.ink,'middle')+math(400,904,'F_{1/2} = 0',28,C.water,'middle');return s;
}
export function mapping(){
  let s='';const centers=[330,820];
  for(let k=0;k<2;k++){const cx=centers[k],R=k?154:233;for(let i=7;i>0;i--)s+=circle(cx,397,R*i/7,i%2?'#f0f6f5':'#fff',C.teal,1.3);s+=circle(cx,397,233,'none',C.gray,1.3,'stroke-dasharray="7 7"');for(const a of [0,Math.PI/3,Math.PI*2/3,Math.PI,4*Math.PI/3,5*Math.PI/3])s+=line(cx,397,...polar(cx,397,R,a),C.gray,1.1);s+=arrow(cx,397,cx+R,397,C.ink,2)+txt(cx+R/2,379,k?'R(t)':'R₀',28,C.ink,'middle');s+=txt(cx,697,k?'t > 0':'t = 0',27,C.ink,'middle');}
  s+=arrow(585,397,636,397,C.teal,4);for(const a of [-Math.PI/2,Math.PI/2])s+=arrow(...polar(820,397,218,a),...polar(820,397,165,a),C.teal,3);
  s+=arrow(1073,397,1156,397,C.mute,3)+txt(1110,145,'ξ = r/R(t)',27,C.ink,'middle');
  for(let i=7;i>=1;i--)s+=rect(1205,182+(7-i)*58,205,58,i%2?'#e1efec':'#f7faf9',C.gray);
  s+=line(1460,182,1460,588,C.ink,1.5)+txt(1480,192,'1',25)+txt(1480,599,'0',25)+txt(1470,390,'ξ',29,C.ink,'middle');
  s+=txt(1306,697,'0 ≤ ξ ≤ 1',28,C.ink,'middle');
  s+=txt(555,842,'uᵣ(r,t) = ξ Ṙ(t)',34,C.teal,'middle')+txt(1176,842,'r = R(t) ξ',34,C.ink,'middle')+txt(817,925,'∂/∂r = (1/R) ∂/∂ξ',31,C.ink,'middle');return s;
}
