"""Original implicit palm/finger study with wrist boundary stitching. All units cm."""
from pathlib import Path
from collections import Counter
import numpy as np,json,sys
from skimage.measure import marching_cubes
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/pipeline'))
from record_modeling_step import append_event
root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'arms-v03/body.obj';out=root/'hands-v04';out.mkdir(exist_ok=True)
append_event('character-hands-v01',dict(kind='action_started',action_id='hands-v04',technical_status='pending',operation=dict(script=str(Path(__file__).resolve())),objective='From-scratch palm, four separated fingers and opposable thumb; prototype proportions, no texture or stock base'))
step=.12;lo=np.array([-5.,.30,-3.]);hi=np.array([8.,19.,3.])
axes=[np.arange(lo[i],hi[i]+step*.5,step) for i in range(3)]
u,t,z=np.meshgrid(*axes,indexing='ij');P=np.stack([u,t,z],axis=-1)
def ell(c,r):return (np.sqrt(np.sum(((P-c)/r)**2,axis=-1))-1)*min(r)
def smin(a,b,k):h=np.maximum(k-np.abs(a-b),0)/k;return np.minimum(a,b)-h*h*k*.25
def capsule(a,b,ra,rb,depth=.82):
 q=P.copy();q[...,2]/=depth;a=np.array(a,dtype=float);b=np.array(b,dtype=float);a[2]/=depth;b[2]/=depth
 ab=b-a;f=np.clip(np.sum((q-a)*ab,axis=-1)/np.dot(ab,ab),0,1)
 return np.linalg.norm(q-a-f[...,None]*ab,axis=-1)-(ra+(rb-ra)*f)
from scipy.interpolate import PchipInterpolator
stations=[-1,0,2,4,6,7.5,8.5,9.8]
ww=PchipInterpolator(stations,[2.2,2.2,2.8,3.5,3.7,3.55,3.2,.1])(np.clip(t,-1,9.8))
wd=PchipInterpolator(stations,[1.826,1.826,1.5,1.4,1.3,1.2,1.05,.1])(np.clip(t,-1,9.8))
field=np.maximum((np.sqrt((u/ww)**2+(z/wd)**2)-1)*wd,t-9.8)
field=smin(field,ell(np.array([1.8,4.0,-.25]),np.array([2.0,3.1,1.4])),.55)
specs=[(-2.65,7.9,13.6,.64,-.50),(-.95,8.8,16.2,.77,-.20),(.85,9.0,17.1,.81,.15),(2.50,8.5,15.8,.75,.42)]
for x,start,end,r,splay in specs:
 joints=[(x,start,0),(x+splay*.5,start+(end-start)*.48,-.10),(x+splay*.85,start+(end-start)*.78,-.27),(x+splay,end,-.47)]
 for j in range(3):field=smin(field,capsule(joints[j],joints[j+1],r*(1-.12*j),r*(.88-.12*j)),.20 if j else .30)
thumb=[(2.6,3.3,-.15),(4.9,5.1,-.35),(6.1,7.2,-.6),(6.25,8.6,-.9)]
for j in range(3):field=smin(field,capsule(thumb[j],thumb[j+1],1.05-.17*j,.92-.17*j,.90),.48 if j==0 else .25)
hv,hf,_,_=marching_cubes(field.astype(np.float32),0,spacing=(step,step,step),allow_degenerate=False);hv+=lo
def boundary(faces):
 e=Counter()
 for f in faces:
  for a,b in zip(f,list(f[1:])+[f[0]]):e[tuple(sorted((int(a),int(b))))]+=1
 return [e for e,n in e.items() if n==1]
he=boundary(hf);hids=sorted(set(i for e in he for i in e));assert len(hids)>20 and np.max(np.abs(hv[hids,1]-.3))<1e-4
def write(path,verts,faces):
 with path.open('w',encoding='utf8') as f:
  for p in verts:f.write('v '+' '.join(f'{a:.8f}' for a in p)+'\n')
  for face in faces:f.write('f '+' '.join(str(int(i)+1) for i in face)+'\n')
write(out/'hand-local.obj',hv,hf)
v=[];faces=[]
for l in src.read_text(encoding='utf8').splitlines():
 if l.startswith('v '):v.append(list(map(float,l.split()[1:4])))
 elif l.startswith('f '):faces.append([int(i)-1 for i in l.split()[1:]])
old=np.array(v);be=boundary(faces)
for sign in [-1,1]:
 center=np.array([sign*44.2,-58.9672954,-3.2]);along=np.array([sign*.5,-.8660254,0]);across=np.array([sign*.8660254,.5,0]);dep=np.array([0,0,1])
 ids=sorted(set(i for e in be for i in e if sign*old[i,0]>38 and old[i,1]<-55))
 assert len(ids)>50
 def ordered(ids,verts,center,across):
  q=verts[ids]-center;ang=np.mod(np.arctan2(q[:,2]/1.826,(q@across)/2.2),2*np.pi);o=np.argsort(ang);return [ids[j] for j in o],ang[o]
 ar,aa=ordered(ids,old,center,across)
 world=center+hv[:,0,None]*across+hv[:,1,None]*along+hv[:,2,None]*dep
 start=len(v);v.extend(world.tolist());faces.extend([[start+int(i) for i in f] for f in hf])
 hr,ha=ordered(hids,world,center+.3*along,across);hr=[start+i for i in hr]
 # Join two ordered rings with a monotone angular zipper, sharing actual wrist vertices.
 i=j=0
 while i<len(ar) or j<len(hr):
  na=aa[(i+1)%len(ar)]+(2*np.pi if i+1>=len(ar) else 0) if i<len(ar) else float('inf')
  nh=ha[(j+1)%len(hr)]+(2*np.pi if j+1>=len(hr) else 0) if j<len(hr) else float('inf')
  a=ar[i%len(ar)];b=hr[j%len(hr)]
  if na<nh:faces.append([a,ar[(i+1)%len(ar)],b]);i+=1
  else:faces.append([a,hr[(j+1)%len(hr)],b]);j+=1
write(out/'body-raw.obj',v,faces)
(out/'construction.json').write_text(json.dumps(dict(source=str(src),unit='cm',hand_length_cm=float(hv[:,1].max()),local_axes='u transverse toward thumb, t distal, z depth; palms face -Z',grid_cm=step,assumptions='Adult neutral relaxed hand proportions, not measured anatomy',method='Smooth union of palm volume and articulated variable-radius finger capsules; angular wrist stitching',has_nails=False,has_skin_creases=False),indent=2),encoding='utf8')
print(out)
