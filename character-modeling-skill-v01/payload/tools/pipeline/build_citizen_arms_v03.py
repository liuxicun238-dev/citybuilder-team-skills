"""Shoulder-side shared-boundary arm loft study, cm Y-up -Z-front."""
from pathlib import Path
from collections import Counter
import sys,json
import numpy as np
from scipy.interpolate import PchipInterpolator
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/pipeline'))
from record_modeling_step import append_event
root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'upper-body-v05/body.obj';out=root/'arms-v03';out.mkdir(exist_ok=True)
aid='arms-v03';ep='character-arms-v01'
append_event(ep,dict(kind='action_started',action_id=aid,technical_status='pending',reference=[str(R/'art/references/citizens-clay-male-v01/front.png')],operation=dict(script=str(Path(__file__).resolve())),objective='Original bilateral upper arm and forearm in A pose, shoulder seam shares vertices; wrist open for later hands'))
v=[];fs=[]
for l in src.read_text(encoding='utf8').splitlines():
 if l.startswith('v '):v.append(list(map(float,l.split()[1:4])))
 elif l.startswith('f '):fs.append([int(t.split('/')[0])-1 for t in l.split()[1:]])
old=np.array(v);keep=[]
for f in fs:
 c=old[f].mean(axis=0)
 cut=abs(c[0])>12 and ((c[1]+14.8)/6.1)**2+((c[2]+1.2)/7.1)**2<1
 if not cut:keep.append(f)
es=Counter()
for f in keep:
 for a,b in zip(f,f[1:]+f[:1]):es[tuple(sorted((a,b)))]+=1
newfaces=[];info=[]
for sign in [-1,1]:
 edges=[e for e,n in es.items() if n==1 and all(sign*old[i,0]>12 and -22<old[i,1]<-7 for i in e)]
 adj={}
 for a,b in edges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
 assert adj and all(len(a)==2 for a in adj.values()),'Shoulder cut must be one closed loop'
 ring=[min(adj)];prev=None
 while True:
  nxt=next(i for i in adj[ring[-1]] if i!=prev);prev=ring[-1]
  if nxt==ring[0]:break
  ring.append(nxt)
 assert len(ring)==len(adj)
 p=old[ring];center=np.array([sign*18.7,-14.8,-1.2]);axis=np.array([sign*.5,-.8660254,0.]);radial=np.array([sign*.8660254,.5,0.]);ez=np.array([0,0,1.])
 delta=p-center;u=delta@radial;w=delta@ez
 signed=np.sum(u*np.roll(w,-1)-w*np.roll(u,-1))
 lengths=np.linalg.norm(np.roll(p,-1,axis=0)-p,axis=1)
 phase=np.sign(signed)*2*np.pi*np.r_[0,np.cumsum(lengths[:-1])]/lengths.sum()
 measured=np.arctan2(w,u)
 offset=np.angle(np.sum(np.exp(1j*(measured-phase))))
 theta=phase+offset
 # Shoulder to elbow 27 cm, elbow to wrist 24 cm; assumed adult proportions.
 radius=PchipInterpolator([0,4,10,19,26,29,34,40,47,51],[6.2,5.7,4.8,4.1,3.25,3.3,3.85,3.35,2.55,2.2])
 last=ring
 for distance in np.linspace(0,51,154)[1:]:
  t=distance/51;cent=center+distance*axis;cent[2]-=2.0*t*t
  rx=float(radius(distance));rz=rx*(.94-.11*np.clip((distance-23)/9,0,1)**2*(3-2*np.clip((distance-23)/9,0,1)))
  ideal=cent+np.cos(theta)[:,None]*radial*rx+np.sin(theta)[:,None]*ez*rz
  initial=center+np.cos(theta)[:,None]*radial*radius(0)+np.sin(theta)[:,None]*ez*radius(0)*.94
  fade=max(0,1-distance/10);fade=fade*fade*(3-2*fade)
  points=ideal+(p-initial)*fade
  # Broad posterior elbow tip and mild anterior upper-arm fullness.
  points[:,2]+=.35*np.exp(-((distance-26)/2.4)**2)*np.maximum(0,np.sin(theta))**4
  points[:,2]-=.30*np.exp(-((distance-14)/6)**2)*np.maximum(0,-np.sin(theta))**3
  cur=list(range(len(v),len(v)+len(ring)));v.extend(points.tolist())
  for j in range(len(ring)):
   k=(j+1)%len(ring);newfaces.extend([(last[j],last[k],cur[k]),(last[j],cur[k],cur[j])])
  last=cur
 info.append(dict(side=sign,shoulder_loop_vertices=len(ring),elbow_cm=(center+26*axis).tolist(),wrist_cm=cent.tolist()))
allfaces=keep+newfaces
from scipy.sparse import coo_matrix,diags
ee=set()
for f in allfaces:
 for a,b in zip(f,list(f[1:])+[f[0]]):ee.add((a,b));ee.add((b,a))
ee=np.array(sorted(ee));vv=np.array(v)
mat=coo_matrix((np.ones(len(ee)),(ee[:,0],ee[:,1])),shape=(len(v),len(v))).tocsr()
mat=diags(1/np.maximum(1,np.asarray(mat.sum(axis=1)).ravel()))@mat
dist=np.sqrt(((np.abs(vv[:,0])-19)/11)**2+((vv[:,1]+15)/12)**2+((vv[:,2]+1.2)/12)**2)
weight=.48*np.clip((1.4-dist)/.5,0,1)
weight[vv[:,1]>-6]=0
for _ in range(160):vv+=(mat@vv-vv)*weight[:,None]
v=vv.tolist()
used=sorted(set(i for f in allfaces for i in f));mapping={j:i+1 for i,j in enumerate(used)}
with (out/'body-raw.obj').open('w',encoding='utf8') as f:
 for i in used:f.write('v '+' '.join(f'{a:.8f}' for a in v[i])+'\n')
 for face in allfaces:f.write('f '+' '.join(str(mapping[i]) for i in face)+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),unit='cm',arms=info,assumed_upper_arm_cm=27,assumed_forearm_cm=24,pose_degrees_from_vertical=30,wrist_open=True,hands=False,stage='Arm proportion and shoulder join study; no animation topology'),indent=2),encoding='utf8')
print(out)
