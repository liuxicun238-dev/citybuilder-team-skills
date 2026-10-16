"""Extend the existing chest boundary into rib cage, abdomen and waist, cm."""
from pathlib import Path
from collections import Counter
import sys,json
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.sparse import coo_matrix,diags
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/pipeline'))
from record_modeling_step import append_event
root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'hands-v04/body.obj';out=root/'torso-v03';out.mkdir(exist_ok=True)
append_event('character-torso-v01',dict(kind='action_started',action_id='torso-v03',technical_status='pending',operation=dict(script=str(Path(__file__).resolve())),objective='Complete upper-body volume to waist, preserve existing head arms and hands'))
v=[];faces=[]
for l in src.read_text(encoding='utf8').splitlines():
 if l.startswith('v '):v.append(list(map(float,l.split()[1:4])))
 elif l.startswith('f '):faces.append([int(i)-1 for i in l.split()[1:]])
old=np.array(v);edges=Counter()
for f in faces:
 for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))]+=1
cut=[e for e,n in edges.items() if n==1 and all(abs(old[i,0])<25 and -27<old[i,1]<-20 for i in e)];adj={}
for a,b in cut:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert len(adj)>100 and all(len(a)==2 for a in adj.values())
ring=[min(adj)];prev=None
while True:
 nxt=next(i for i in adj[ring[-1]] if i!=prev);prev=ring[-1]
 if nxt==ring[0]:break
 ring.append(nxt)
assert len(ring)==len(adj)
p=old[ring];theta=np.unwrap(np.arctan2(-(p[:,2]+1.2)/10,p[:,0]/18));last=ring
ys=[0,3,7,12,18,22,25]
width=PchipInterpolator(ys,[18,17.8,17.1,15.8,14.8,14.9,15.7])
front=PchipInterpolator(ys,[10,10.1,10.0,9.4,9.0,9.0,9.2])
back=PchipInterpolator(ys,[10,9.6,9.0,8.5,8.3,8.6,9.0])
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for d in np.linspace(0,25,201)[1:]:
 x=width(d)*np.cos(theta);ss=np.sin(theta);dep=np.where(ss>0,front(d),back(d));z=-1.2-dep*ss;y=np.full(len(ring),-24-d)
 fade=1-smooth(d/6)
 x+=(p[:,0]-18*np.cos(theta))*fade
 z+=(p[:,2]-(-1.2-10*ss))*fade
 y+=(p[:,1]+24)*fade
 ax=np.abs(x);fg=np.maximum(ss,0)**4;bg=np.maximum(-ss,0)**4;on=smooth(d/4)
 # Soft abdominal wall and flank, without carved six-pack grooves.
 belly=.38*np.exp(-((ax-3.6)/3.1)**2-((y+36)/8.5)**2)
 mid=.10*np.exp(-(x/.7)**2-((y+35)/7)**2)
 navel=.34*np.exp(-(x/.48)**2-((y+40)/.50)**2)
 z+=on*fg*(-belly+mid+navel)
 z+=on*bg*(.25*np.exp(-((ax-3)/2.4)**2-((y+36)/8)**2)-.13*np.exp(-(x/.8)**2-((y+35)/8)**2))
 cur=list(range(len(v),len(v)+len(ring)));v.extend(np.stack([x,y,z],axis=1).tolist())
 for j in range(len(ring)):
  k=(j+1)%len(ring);faces.extend([[last[j],last[k],cur[k]],[last[j],cur[k],cur[j]]])
 last=cur
# Fair only the old chest cut and new transition; no head/limb movement.
vv=np.array(v);ee=set()
for f in faces:
 for a,b in zip(f,f[1:]+f[:1]):ee.add((a,b));ee.add((b,a))
ee=np.array(sorted(ee));A=coo_matrix((np.ones(len(ee)),(ee[:,0],ee[:,1])),shape=(len(vv),len(vv))).tocsr();M=diags(1/np.maximum(1,np.asarray(A.sum(axis=1)).ravel()))@A
w=.38*np.exp(-((vv[:,1]+24)/5.5)**4)*(1-smooth((np.abs(vv[:,0])-17)/3));w*=smooth((-18-vv[:,1])/4)
for _ in range(180):vv+=(M@vv-vv)*w[:,None]
protected=(old[:,1]>-18)|(np.abs(old[:,0])>=20)
assert np.array_equal(vv[:len(old)][protected],old[protected])
with (out/'body-raw.obj').open('w',encoding='utf8') as f:
 for p in vv:f.write('v '+' '.join(f'{a:.8f}' for a in p)+'\n')
 for face in faces:f.write('f '+' '.join(str(i+1) for i in face)+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),unit='cm',waist_y_cm=-49,shoulder_width_assumption_cm=42,waist_width_cm=31.4,lower_body_not_built=True,waist_boundary_open=True,protected_head_and_limbs=True,stage='Upper body shape study, no UV rig or clothing'),indent=2),encoding='utf8')
print(out)
