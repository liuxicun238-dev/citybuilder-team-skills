"""Original shoulder/chest blockout from the existing neck boundary, centimetres."""
from pathlib import Path
from collections import Counter
import sys,json
import numpy as np
from scipy.interpolate import PchipInterpolator
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/pipeline'))
from record_modeling_step import append_event
root=R/'art/assets/authored/city/zbrush-reference-head-v01'
src=root/'chin-refine-v03/head-neck.obj';out=root/'upper-body-v03';out.mkdir(exist_ok=True)
ref=R/'art/references/citizens-clay-male-v01/front.png'
append_event('character-upper-body-v01',dict(kind='action_started',technical_status='pending',action_id='upper-body-v03',reference=[str(ref)],operation=dict(script=str(Path(__file__).resolve())),objective='From-scratch neck-to-shoulder and upper chest blockout, preserve existing head'))
lines=src.read_text(encoding='utf8').splitlines();v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]);es=Counter()
for l in lines:
 if l.startswith('f '):
  f=[int(i.split('/')[0])-1 for i in l.split()[1:]]
  for a,b in zip(f,f[1:]+f[:1]):es[tuple(sorted((a,b)))]+=1
edges=[e for e,n in es.items() if n==1 and max(v[list(e),1])<-7.99]
adj={}
for a,b in edges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(n)==2 for n in adj.values())
ring=[min(adj)];prev=None
while True:
 nxt=next(i for i in adj[ring[-1]] if i!=prev);prev=ring[-1]
 if nxt==ring[0]:break
 ring.append(nxt)
assert len(ring)==len(adj)
p=v[ring];theta=np.unwrap(np.arctan2(-(p[:,2]+1.2)/5,p[:,0]/4.35))
print('angular steps',np.diff(theta).min(),np.diff(theta).max())
depths=np.array([8,8.5,9,10,11,12,14,17,21,26,28.])
width=PchipInterpolator(depths,[4.35,4.45,5.1,8,12.5,16.5,20,21,20.3,18.5,18.])
depth=PchipInterpolator(depths,[5,5.1,5.5,6.2,7.1,8,9.5,10.5,11.1,10.4,10.])
nv=[];faces=[];last=ring;N=len(v)
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for d in np.linspace(8,28,161)[1:]:
 x=width(d)*np.cos(theta);z=-1.2-depth(d)*np.sin(theta);y=np.full(len(ring),-d)
 # Exact shared neck edge, with a compact falloff of the old contour residual.
 fade=1-smooth((d-8)/2)
 x+=(p[:,0]-4.35*np.cos(theta))*fade
 z+=(p[:,2]-(-1.2-5*np.sin(theta)))*fade
 front=np.maximum(0,np.sin(theta))**5
 ax=np.abs(x);clavy=-12.4+.07*ax-.010*ax*ax
 clav=.46*np.exp(-((y-clavy)/.65)**2)*smooth((ax-1)/2)*(1-smooth((ax-15)/3))
 pec=.60*np.exp(-((ax-8)/5.4)**2-((y+20)/4.3)**2)
 notch=.38*np.exp(-(x/1.5)**2-((y+12.2)/1.3)**2)
 z+=front*(-clav-pec+notch)
 back=np.maximum(0,-np.sin(theta))**4
 z+=back*.4*np.exp(-((ax-8)/4.8)**2-((y+18)/5)**2)
 cur=list(range(N+len(nv),N+len(nv)+len(ring)))
 nv.extend(np.stack([x,y+4,z],axis=1).tolist())
 for j in range(len(ring)):
  k=(j+1)%len(ring);faces.extend([(last[j],last[k],cur[k]),(last[j],cur[k],cur[j])])
 last=cur
with (out/'body-raw.obj').open('w',encoding='utf8') as f:
 vi=0
 for l in lines:
  if l.startswith('v '):
   a=v[vi].copy();vi+=1
   if a[1]<2:a[1]+=4*float(smooth((2-a[1])/10))
   l='v '+' '.join(f'{q:.8f}' for q in a)
  f.write(l+'\n')
 for p in nv:f.write('v '+' '.join(f'{a:.8f}' for a in p)+'\n')
 f.write('g upper_body\n')
 for face in faces:f.write('f '+' '.join(str(i+1) for i in face)+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),unit='cm',neck_boundary_vertices=len(ring),new_vertices=len(nv),shoulder_width_cm=42,assumed_future_stature_cm=178,stage='Shoulder girdle and upper chest only; arms, abdomen and lower body absent',head_above_chin_unchanged=True,neck_shortening_cm=4,neck_transition_y_cm=[-8,2],shoulder_raise_cm=4),indent=2),encoding='utf8')
append_event('character-upper-body-v01',dict(kind='action_finished',action_id='upper-body-v03',technical_status='succeeded',user_acceptance='unreviewed',evidence=[dict(path=str(out/'body-raw.obj'),role='candidate_model'),dict(path=str(Path(__file__).resolve()),role='actual_script')]))
print(out)
