"""Rebuild scientifically mapped core figures. Never uses legacy placeholder bars."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib import font_manager
from scipy.interpolate import PchipInterpolator
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/figures/core_16'
BASE=OUT/'基础图'; BASE.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'题目要求结果数据/复算依据'
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':10,
 'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#183649','text.color':'#183649',
 'axes.edgecolor':'#78909C','axes.linewidth':.8,'savefig.dpi':240,'figure.facecolor':'white'})
NAVY,TEAL,ORANGE='#183649','#007f86','#d96931'
Q={q:dict(np.load(DATA/f'result{q}_未舍入.npz')) for q in range(1,5)}
M={q:json.loads((DATA/f'result{q}_生成记录.json').read_text(encoding='utf-8')) for q in Q}
def workbook(i):
 w=load_workbook(ROOT/f'代码/附件/附件{i}.xlsx',read_only=True,data_only=True)
 a=np.array(list(w.active.values)[1:],float); w.close(); return a
E,R=workbook(1),workbook(2)
records=[]
def axes(title,nr=1,nc=2):
 f,aa=plt.subplots(nr,nc,figsize=(12,7),squeeze=False)
 f.subplots_adjust(left=.09,right=.93,bottom=.15,top=.82,wspace=.4,hspace=.5)
 # Publication figures receive captions externally; no G-number or prose title inside.
 return f,aa.ravel()
def panel(ax,label,x,y):
 ax.set_title(label,loc='left',fontsize=11,pad=12);ax.set(xlabel=x,ylabel=y);ax.grid(alpha=.14,axis='y')
def save(f,id,title,note,source,position,kind):
 p=BASE/f'{id}.png';f.savefig(p);plt.close(f)
 records.append(dict(id=id,title=title,source=source,note=note,position=position,kind=kind,file=str(p.relative_to(OUT))))
def t(q):return Q[q]['time_s']/3600
def field(ax,q,key,hours,title):
 z=Q[q]; rows=np.where(t(q)<=hours)[0];rows=rows[np.linspace(0,len(rows)-1,min(400,len(rows)),dtype=int)]
 xx=z['radius_cm']; tt=t(q)[rows]; a=z[key][rows]
 im=ax.pcolormesh(xx,tt,a,shading='nearest',cmap='inferno' if key=='T' else 'YlGnBu')
 cs=ax.contour(xx,tt,a,levels=5,colors='white',linewidths=.5,alpha=.7);ax.clabel(cs,fontsize=7,inline=True)
 panel(ax,title,'物理半径 r / cm','时间 t / h');ax.set_xlim(0,2);ax.grid(False)
 plt.colorbar(im,ax=ax,pad=.03,fraction=.046,label='T / °C' if key=='T' else 'C / (kg水/kg干物质)')

# Inputs are actual attachment observations, not simulated center temperatures.
f,a=axes('G13  环境输入：观测、预热与平台',2,1)
for ax,j,color,unit,label in zip(a,[1,2],[ORANGE,TEAL],['环境温度 / °C','空气等效含水率 / (kg/kg)'],['(a) 温度输入','(b) 水分边界输入']):
 ax.plot(E[:,0]/3600,E[:,j],color=color,lw=1.2,label='分段线性插值')
 ax.scatter(E[:,0]/3600,E[:,j],s=7,color=color,label='附件1观测点')
 ax.axvspan(3,4,color='#e4ecef',alpha=.6); ax.set_xlim(0,4);panel(ax,label,'时间 / h',unit);ax.legend(fontsize=8,loc='lower right')
save(f,'G13','前4小时环境输入','241个观测点；灰区为3–4 h平台估计窗口。空气等效含水率不是相对湿度。','附件1.xlsx','§5.1 输入数据','共享轴观测双面板')

f,a=axes('G15  实测半径与插值收缩速率',2,1); pp=PchipInterpolator(R[:,0]/3600,R[:,1]);tt=np.linspace(0,72,1500)
a[0].plot(tt,pp(tt),color=TEAL,label='PCHIP插值');a[0].scatter(R[:,0]/3600,R[:,1],s=9,color=NAVY,label='附件2观测')
for ax in a:ax.axvline(M[4]['stop_time_h'],color=ORANGE,ls='--',lw=1)
a[0].legend(fontsize=8);panel(a[0],'(a) 半径观测与插值','时间 / h','R / cm')
a[1].fill_between(tt,pp.derivative()(tt),0,color=TEAL,alpha=.22);a[1].plot(tt,pp.derivative()(tt),color=TEAL)
panel(a[1],'(b) 插值函数的解析导数','时间 / h','dR/dt / (cm/h)')
save(f,'G15','半径观测与收缩速率','145个观测点；虚线为问题四结束时刻。导数来自PCHIP，不是实测速率或独立验证。','附件2.xlsx、M4','§8.1 收缩输入','观测曲线＋导数面积图')

f,a=axes('G19  热扩散与水分扩散的局部特征尺度')
q=3;z=Q[q]
for col,name,ls in [(0,'中心','-'),(-1,'表面','--')]:
 c=z['C'][:,col];temp=z['T'][:,col];alpha=(.21+.38*c/(1+c))/((650+128*c)*(1450+2736*c/(1+c)))
 d=2.4e-3*np.exp(-.45/c-3850/(temp+273.15))
 a[0].semilogy(t(q),.02**2/alpha/3600,color=ORANGE,ls=ls,label='热尺度 '+name)
 a[0].semilogy(t(q),.02**2/d/3600,color=TEAL,ls=ls,label='水分尺度 '+name)
 a[1].semilogy(t(q),alpha/d,color=NAVY,ls=ls,label=name)
panel(a[0],'(a) 局部尺度 τ = R² / 扩散率','时间 / h','τ / h');panel(a[1],'(b) 比值 τ水 / τ热 = α / D','时间 / h','无量纲比值')
for ax in a:ax.legend(fontsize=8)
save(f,'G19','局部扩散特征时间','α=k/(ρ_emp cp)；采用问题三物性与中心/表面状态。这些局部尺度不是实测干燥时间。','N3、问题3/main.py物性','§6.2 / §7.2 机制解释','对数尺度双面板')

for id,q,h in [('G21',1,.5),('G26',2,3)]:
 f,a=axes(f'{id}  问题{q}：温度与含水率的时空演化')
 field(a[0],q,'T',h,'(a) 温度场与等温线');field(a[1],q,'C',h,'(b) 含水率场与等值线')
 save(f,id,f'问题{q}双场时空图','径向为原始0.1 cm输出点；时间显示抽样≤400行。等值线为输出点之间的可视化重构。',f'N{q}',f'问题{q}结果小节','双色标双场等值图')

f,a=axes('G33  固定域干燥：表面先响应，中心决定终点')
z=Q[3];xx=z['radius_cm']/2;mean=2*np.trapezoid(z['C']*xx,xx,axis=1)
for ax in a:
 ax.plot(t(3),z['C'].max(axis=1),color=NAVY,label='输出点最大值（与中心一致）')
 ax.plot(t(3),mean,color=TEAL,label='柱测度平均（21点近似）')
 ax.plot(t(3),z['C'][:,-1],color=ORANGE,label='表面')
 ax.axhline(.15,color='#888888',ls='--',lw=1,label='达标阈值 0.15')
panel(a[0],'(a) 全程响应','时间 / h','C / (kg水/kg干物质)');panel(a[1],'(b) 后期拖尾放大','时间 / h','C / (kg水/kg干物质)')
a[1].set(xlim=(35,58),ylim=(.045,.26));a[0].legend(fontsize=8)
save(f,'G33','全程干燥与拖尾',f"结束时刻 {M[3]['stop_time_h']:.4f} h；达标按全域最大值判定，不能用平均值提前结束。",'N3、M3','§7.2 终点与干燥机制','全程＋拖尾局部放大')

f,a=axes('G35  达标终态：中心与表面并不具有相同含水率')
for ax,q,color in zip(a,[3,4],[NAVY,TEAL]):
 z=Q[q];ax.fill_between(z['final_xi'],z['final_C'],0,color=color,alpha=.14);ax.plot(z['final_xi'],z['final_C'],color=color,lw=2)
 ax.axhline(.15,color=ORANGE,ls='--',lw=1);ax.set_ylim(0,.165)
 panel(ax,f'({"a" if q==3 else "b"}) 问题{q}，结束于 {M[q]["stop_time_h"]:.4f} h','材料坐标 ξ = r/R','C / (kg水/kg干物质)')
 ax.text(.05,.04,f'R = {z["R_m"][-1]*100:.2f} cm\n表面 C = {z["final_C"][-1]:.5f}',transform=ax.transAxes,fontsize=10)
save(f,'G35','各自达标终态剖面','每幅使用5121个终态节点；两个状态属于各自结束时刻，不是同一时刻对比。','N3/N4 final_xi、final_C','§7.2 / §8.2 终态','终态填充剖面双面板')

# Actual physical coordinates + explicit surface samples. Never scale r twice.
f,a=axes('G41  收缩域中的水分迁移与物理边界')
z=Q[4];ids=np.linspace(0,len(t(4))-1,500,dtype=int);rr=np.linspace(0,2,450);zz=np.full((len(ids),len(rr)),np.nan)
for row,j in enumerate(ids):
 mask=np.isfinite(z['radius_cm']) & z['domain_mask'][j];rx=np.r_[z['radius_cm'][mask],z['R_m'][j]*100];cc=np.r_[z['C'][j,mask],z['C'][j,-1]]
 rx,ii=np.unique(rx,return_index=True);cc=cc[ii];inside=rr<=rx[-1];zz[row,inside]=np.interp(rr[inside],rx,cc)
a[0].set_facecolor('#e9edef');im=a[0].pcolormesh(rr,t(4)[ids],zz,cmap='YlGnBu',shading='nearest',vmin=.05,vmax=2.55)
a[0].plot(z['R_m']*100,t(4),color=ORANGE,lw=1.7,label='实际表面 R(t)');a[0].legend(fontsize=8)
cs=a[0].contour(rr,t(4)[ids],zz,levels=[.15,.5,1,2],colors='white',linewidths=.7);a[0].clabel(cs,fontsize=8)
plt.colorbar(im,ax=a[0],fraction=.046,label='C / (kg水/kg干物质)')
panel(a[0],'(a) 实际物理域；灰色为域外','r / cm','t / h');a[0].grid(False)
for hh in [0,6,12,24,48]:
 j=np.argmin(abs(t(4)-hh));mask=np.isfinite(z['radius_cm'])&z['domain_mask'][j];rx=np.r_[z['radius_cm'][mask],z['R_m'][j]*100];cc=np.r_[z['C'][j,mask],z['C'][j,-1]]
 a[1].plot(rx,cc,lw=1.5,label=f'{hh} h');a[1].scatter(rx[-1],cc[-1],s=18)
panel(a[1],'(b) 剖面在各自实际表面终止','r / cm','C / (kg水/kg干物质)');a[1].legend(fontsize=8)
save(f,'G41','动边界物理域与截面','实际表面列参与重构；仅在域内逐行线性插值，未增加求解精度；灰区不是零含水率。','N4 radius_cm/R_m/C/domain_mask','§8.2 动边界结果','边界遮罩等值图＋截面族')

f,a=axes('G43  几何趋稳之后，中心仍持续脱水',2,1);z=Q[4]
a[0].plot(t(4),z['R_m']/.02,color=TEAL);a[0].fill_between(t(4),z['R_m']/.02,.6,color=TEAL,alpha=.14)
mask=R[:,0]/3600<=t(4)[-1];a[0].scatter(R[mask,0]/3600,R[mask,1]/2,s=12,color=NAVY,label='半径观测');a[0].legend(fontsize=8)
panel(a[0],'(a) 相对半径','t / h','R/R0')
a[1].plot(t(4),z['C'][:,0],color=NAVY,label='中心');a[1].plot(t(4),z['C'][:,-1],color=ORANGE,label='实际表面');a[1].axhline(.15,ls='--',color='#888888',lw=1);a[1].legend(fontsize=8)
panel(a[1],'(b) 中心与表面含水率','t / h','C / (kg水/kg干物质)')
save(f,'G43','收缩与脱水的时间关系','共享时间轴，避免双纵轴造成斜率误读；半径观测作为模型输入，不构成独立验证。','附件2、N4','§8.2 机制讨论（可选）','几何－状态对齐双面板')

f,a=axes('G46  两种模型情景的同尺度干燥对比')
for q,c in [(3,NAVY),(4,TEAL)]:
 for ax,col in zip(a,[0,-1]):
  ax.plot(t(q),Q[q]['C'][:,col],color=c,label=f'问题{q}')
  ax.scatter(t(q)[-1],Q[q]['C'][-1,col],color=c,s=30,zorder=3)
panel(a[0],'(a) 中心响应','t / h','C / (kg水/kg干物质)');panel(a[1],'(b) 表面响应','t / h','C / (kg水/kg干物质)')
for ax in a:ax.axhline(.15,color=ORANGE,ls='--',lw=1);ax.legend(fontsize=9)
save(f,'G46','固定域与收缩域情景比较',f"结束时刻：{M[3]['stop_time_h']:.4f} h / {M[4]['stop_time_h']:.4f} h。物性与几何同时改变，差异不能全归因于收缩。",'N3/N4、M3/M4','§8.2 结果比较','同尺度中心－表面对照')

f,a=axes('G32  问题二与三的共同输出一致性')
idx=np.searchsorted(Q[2]['time_s'],Q[3]['time_s']);assert np.allclose(Q[2]['time_s'][idx],Q[3]['time_s'],atol=1e-6,rtol=0)
checks={}
for ax,key in zip(a,['C','T']):
 diff=Q[2][key][idx]-Q[3][key];mx=float(np.max(abs(diff)));checks[key]=mx
 im=ax.imshow(diff.T,aspect='auto',origin='lower',extent=[0,t(3)[-1],0,2],cmap='RdBu_r',vmin=-max(mx,1e-12),vmax=max(mx,1e-12))
 panel(ax,f'({"a" if key=="C" else "b"}) {key}2 − {key}3','t / h','r / cm');ax.grid(False)
 ax.text(.5,.5,f'max |Δ{key}| = {mx:.1e}',transform=ax.transAxes,ha='center',bbox=dict(facecolor='white',edgecolor='none',alpha=.9),fontsize=13)
save(f,'G32','两问输出一致性','对齐全部共同时间和21个输出半径；显示范围±1e-12。零差值是实现一致性，不是独立物理验证。','N2/N3共同时间和输出点','附录：一致性核验','二维差值矩阵')
(OUT/'基础图数据记录.json').write_text(json.dumps({'figures':records,'checks':checks,'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.npz')}},ensure_ascii=False,indent=2),encoding='utf-8')
print('Produced',len(records),'numeric figures; consistency',checks)

