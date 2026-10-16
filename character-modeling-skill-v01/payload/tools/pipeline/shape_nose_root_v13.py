from pathlib import Path
import numpy as np,json
from scipy.interpolate import RBFInterpolator
R=Path('__CHAR_PROJECT__/art/assets/authored/city/zbrush-reference-head-v01');src=R/'nose-fit-v12/head-neck.obj';out=R/'nose-fit-v13';out.mkdir(exist_ok=True)
lines=src.read_text().splitlines();v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')])
r=np.sqrt((v[:,0]/2.8)**2+((v[:,1]-10)/3.7)**2)
mask=(v[:,2]<-9)&(((r>.46)&(r<.60))|((r>1.24)&(r<1.42)))
# Fit only the original outer facial skin, never nose recesses or eye shells.
bv=[];skin=set();group=''
for line in (R/'ear-fit-v02/head-neck.obj').read_text().splitlines():
 a=line.split()
 if not a:continue
 if a[0]=='v':bv.append(list(map(float,a[1:4])))
 elif a[0]=='g':group=a[1]
 elif a[0]=='f' and group=='skin':skin.update(int(x)-1 for x in a[1:])
p=np.array(bv)[sorted(skin)];pr=np.sqrt((p[:,0]/2.8)**2+((p[:,1]-10)/3.7)**2)
pts=p[(pr>1)&(pr<1.5)&(p[:,2]<-9)];pts=pts[::max(1,len(pts)//600)]
_,idx=np.unique(np.round(pts[:,:2],5),axis=0,return_index=True);pts=pts[idx]
rbf=RBFInterpolator(pts[:,:2],pts[:,2],smoothing=2.0,kernel='thin_plate_spline')
from scipy.interpolate import PchipInterpolator
profile=PchipInterpolator([9.3,10,11,12,13,13.6,14.4,15],[-14.94,-14.43,-13.96,-13.52,-13.20,-13.11,-13.25,-13.45])
y=v[:,1];x=v[:,0]
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
w=smooth((y-9.35)/.85)*smooth((14.9-y)/1.15)*smooth((2.5-abs(x))/.7)
w[v[:,2]>=-10]=0
# Protect independent eyes and ears, including hidden surfaces.
allowed=set();group=''
for line in lines:
 a=line.split()
 if not a:continue
 if a[0]=='g':group=a[1]
 elif a[0]=='f' and group in ['skin','nose_surface','nose_join']:allowed.update(int(i)-1 for i in a[1:])
w[[i for i in range(len(v)) if i not in allowed]]=0
sel=np.flatnonzero(w>0);old=v.copy()
yy=y[sel];xx=x[sel];baseline=rbf(v[sel,:2]);center=rbf(np.c_[np.zeros(len(sel)),yy])
width=.82+.22*smooth((yy-11)/2.8)
target=baseline+(profile(np.clip(yy,9.3,15))-center)*np.exp(-(xx/width)**2)
v[sel,2]=old[sel,2]*(1-w[sel])+target*w[sel]
k=0
with (out/'head-neck.obj').open('w',encoding='utf8') as f:
 for line in lines:
  if line.startswith('v '):line='v '+' '.join(f'{x:.8f}' for x in v[k]);k+=1
  f.write(line+'\n')
(out/'assembly.json').write_text(json.dumps(dict(source=str(src),method='Smooth surface depth constrained by inner nasal and outer facial rings, replacing irregular graph averaging',changed_vertices=len(sel),max_displacement_cm=float(np.max(np.abs(v-old))),limitations=['Shape pending review','No animation or full self-intersection check']),indent=2),encoding='utf8')
