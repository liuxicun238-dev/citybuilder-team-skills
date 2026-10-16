"""Original lower-body volume study. Centimetres, Y-up, -Z-front."""
from pathlib import Path
from collections import Counter
import numpy as np,json,sys
from scipy.interpolate import PchipInterpolator
from skimage.measure import marching_cubes
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/pipeline'))
from record_modeling_step import append_event
root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'torso-v03/body.obj';out=root/'body-detail-v01';out.mkdir(exist_ok=True)
append_event('character-lower-body-v01',dict(kind='action_started',action_id='body-detail-v01',technical_status='pending',operation=dict(script=str(Path(__file__).resolve())),objective='Original pelvis, two separated legs and feet; preserve source upper body; assumed 178cm stature'))
step=.32;lo=np.array([-26.,-155.5,-24.]);top=-49.3
axes=[np.arange(-26,26+step/2,step,dtype=np.float32),np.arange(top,-155.5,-step,dtype=np.float32)[::-1],np.arange(-27,16+step/2,step,dtype=np.float32)]
lo=np.array([a[0] for a in axes]);x,y,z=np.meshgrid(*axes,indexing='ij')
def sm(a,b,k):h=np.maximum(k-np.abs(a-b),0)/k;return np.minimum(a,b)-h*h*k*.25
def ell(cx,cy,cz,rx,ry,rz):return (np.sqrt(((x-cx)/rx)**2+((y-cy)/ry)**2+((z-cz)/rz)**2)-1)*min(rx,ry,rz)
py=np.array([-76,-71,-65,-59,-54,top])
pw=PchipInterpolator(py,[.5,8,15,17.3,17,15.7])(np.clip(y,py[0],top)).astype(np.float32)
pd=PchipInterpolator(py,[.5,6,9.4,10.4,9.8,9.2])(np.clip(y,py[0],top)).astype(np.float32)
field=np.maximum((np.sqrt((x/pw)**2+((z+1.2)/pd)**2)-1)*pd,-76-y)
ly=[-150,-144,-135,-124,-113,-106,-98,-86,-74,-63,-53]
wr=[3.1,3.3,4.5,5.7,5.4,4.65,5.8,7.6,8.1,8.3,5]
dr=[3.6,3.7,5.0,6.2,5.4,4.9,6.1,8.5,9.5,9.0,5]
yy=np.clip(y,ly[0],ly[-1])
rw=PchipInterpolator(ly,wr)(yy).astype(np.float32);rd=PchipInterpolator(ly,dr)(yy).astype(np.float32)
cx=PchipInterpolator(ly,[13.2,13.1,12.7,12.2,11.8,11.5,11,10.4,9.8,9.3,8.8])(yy).astype(np.float32)
cz=PchipInterpolator(ly,[-1,-1,.4,1.2,0,-1.8,-1.2,-.8,-.8,-.8,-.8])(yy).astype(np.float32)
for sign in [-1,1]:
 leg=(np.sqrt(((x-sign*cx)/rw)**2+((z-cz)/rd)**2)-1)*np.minimum(rw,rd)
 leg=np.maximum(leg,np.maximum(-150-y,y+53))
 field=sm(field,leg,2.1)
 # Subtle posterior glute volume and rounded knees, not separate attached objects.
 field=sm(field,ell(sign*8.0,-65,4.3,8.5,11.0,5.5),1.8)
 field=sm(field,ell(sign*11.5,-106,-4.3,3.3,3.6,2.9),.6)
 # Heel, instep and forefoot volumes with separated distal toes.
 foot=ell(sign*13.2,-151.2,2.2,3.45,3.8,4.8)
 foot=sm(foot,ell(sign*13.2,-149.7,-4.0,3.7,4.7,7.0),1.1)
 foot=sm(foot,ell(sign*13.2,-151.5,-10.7,4.65,3.0,6.0),.9)
 toe_specs=[(-3.0,-18.3,1.22,3.7),(-.8,-18.1,.98,3.8),(1.05,-17.5,.87,3.35),(2.65,-16.7,.76,2.8),(3.9,-15.8,.63,2.25)]
 for offset,cztoe,rx,rz in toe_specs:
  foot=sm(foot,ell(sign*(13.2+offset),-152.2,cztoe,rx,1.65 if rx>1 else 1.4,rz),.25)
 # Medial arch removes underside volume only, without a hole through the dorsum.
 arch=ell(sign*9.8,-154.6,-3.8,3.5,2.7,5.4)
 foot=np.maximum(foot,-arch)
 field=sm(field,foot,.85)
# Flat soles, shared ground plane. Grid extends below it so the feet are closed.
field=np.maximum(field,-154-y)
lv,lf,_,_=marching_cubes(field.astype(np.float32),0,spacing=(step,step,step),allow_degenerate=False);lv+=lo
def boundary(fs):
 ee=Counter()
 for f in fs:
  for a,b in zip(f,list(f[1:])+[f[0]]):ee[tuple(sorted((int(a),int(b))))]+=1
 return [e for e,n in ee.items() if n==1]
lid=sorted(set(i for e in boundary(lf) for i in e));assert len(lid)>40 and np.max(np.abs(lv[lid,1]-top))<1e-3
v=[];fs=[]
for l in src.read_text(encoding='utf8').splitlines():
 if l.startswith('v '):v.append(list(map(float,l.split()[1:4])))
 elif l.startswith('f '):fs.append([int(i)-1 for i in l.split()[1:]])
# Rebuild a broad front chest transition; retain head, arms and hands exactly.
ov=np.array(v);xx,yy0,zz=ov.T
def smooth(a):a=np.clip(a,0,1);return a*a*(3-2*a)
stations=[-49,-40,-32,-26,-20,-16,-12,-8]
dep=PchipInterpolator(stations,[9.2,9.1,9.8,10.6,11.5,11.3,9.3,6.0])(np.clip(yy0,-49,-8))
wid=PchipInterpolator(stations,[15.7,14.8,16.9,18,20.5,21,18,6])(np.clip(yy0,-49,-8))
target=-1.2-dep*np.sqrt(np.maximum(0,1-(xx/wid)**2))
target-=.35*np.exp(-((np.abs(xx)-7)/5)**4-((yy0+19)/4.0)**2)
w=smooth((yy0+35)/7)*(1-smooth((yy0+17)/6))*(1-smooth((np.abs(xx)-12)/5))*smooth((-zz-2)/4)
ov[:,2]=zz*(1-w)+target*w
v=ov.tolist()
old=np.array(v);ids=sorted(set(i for e in boundary(fs) for i in e if abs(old[i,1]+49)<1e-5 and abs(old[i,0])<20));assert len(ids)>100
def order(ids,vs):
 p=vs[ids];a=np.mod(np.arctan2((p[:,2]+1.2)/9.2,p[:,0]/15.7),2*np.pi);o=np.argsort(a);return [ids[i] for i in o],a[o]
ar,aa=order(ids,old);lr,la=order(lid,lv);start=len(v);v.extend(lv.tolist());fs.extend([[start+int(i) for i in f] for f in lf]);lr=[start+i for i in lr]
i=j=0
while i<len(ar) or j<len(lr):
 na=aa[(i+1)%len(ar)]+(2*np.pi if i+1>=len(ar) else 0) if i<len(ar) else float('inf')
 nb=la[(j+1)%len(lr)]+(2*np.pi if j+1>=len(lr) else 0) if j<len(lr) else float('inf')
 a=ar[i%len(ar)];b=lr[j%len(lr)]
 if na<nb:fs.append([a,ar[(i+1)%len(ar)],b]);i+=1
 else:fs.append([a,lr[(j+1)%len(lr)],b]);j+=1
with (out/'body-raw.obj').open('w',encoding='utf8') as f:
 for p in v:f.write('v '+' '.join(f'{a:.8f}' for a in p)+'\n')
 for face in fs:f.write('f '+' '.join(str(i+1) for i in face)+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),unit='cm',assumed_height_cm=178,hip_width_cm=36,knee_y_cm=-106,ankle_y_cm=-145,sole_y_cm=-154,voxel_cm=step,upper_body_unchanged=False,head_arms_hands_preserved=True,feet='Heel instep arch and five toe volumes; no nails',status='Full body shape study, no rig or UV'),indent=2),encoding='utf8')
print(out)
