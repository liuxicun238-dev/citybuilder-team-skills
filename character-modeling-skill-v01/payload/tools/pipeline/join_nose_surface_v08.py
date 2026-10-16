"""Local anterior surface graft; preserve source, remove closed backing, bridge real boundaries."""
from pathlib import Path
import numpy as np,json,hashlib,sys
from collections import Counter,defaultdict
from scipy.interpolate import RBFInterpolator
R=Path('__CHAR_PROJECT__/art/assets/authored/city')
src=R/'zbrush-reference-head-v01/ear-fit-v02/head-neck.obj'
nose=R/'citizen-nose-sculpt-v01/a02/nose.obj'
out=R/'zbrush-reference-head-v01/nose-fit-v08';out.mkdir(exist_ok=True)
def read(p):
 v=[];f=[];g=[];name='skin'
 for l in p.read_text().splitlines():
  a=l.split()
  if not a:continue
  if a[0]=='v':v.append(list(map(float,a[1:4])))
  elif a[0]=='g':name=a[1]
  elif a[0]=='f':f.append([int(i.split('/')[0])-1 for i in a[1:]]);g.append(name)
 return np.array(v),f,g
def loops(faces):
 edges=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]));adj=defaultdict(list)
 for (a,b),n in edges.items():
  if n==1:adj[a].append(b);adj[b].append(a)
 if any(len(n)!=2 for n in adj.values()):raise ValueError('Branched boundary')
 unseen=set(adj);result=[]
 while unseen:
  start=min(unseen);p=start;prev=None;loop=[]
  while True:
   loop.append(p);unseen.remove(p);n=next(x for x in adj[p] if x!=prev);prev,p=p,n
   if p==start:break
  result.append(loop)
 return result
v,f,g=read(src);n,nf,ng=read(nose)
faces=[];groups=[]
for face,name in zip(f,g):
 p=v[face].mean(0)
 if name=='nasal_interior':continue
 if name=='skin' and p[2]<-9 and (p[0]/2.8)**2+((p[1]-10)/3.7)**2<1:continue
 faces.append(face);groups.append(name)
headloops=loops(faces)
outer=min(headloops,key=lambda ids:np.linalg.norm(v[ids].mean(0)-[0,10,-13]))
assert abs(v[outer,0].mean())<.5 and v[outer,2].mean()<-10
# Keep only the actual anterior skin of the nose. Nostril recesses are anterior to this cut.
patch=[]
for face in nf:
 p=n[face].mean(0)
 if p[2]>-.21 and (p[0]/2.5)**2+((p[1]-3.1)/3.4)**2<1:patch.append(face)
nl=loops(patch);assert len(nl)==1,len(nl)
inner=nl[0]
# Fit a smooth underlying midface to the head boundary and an exterior annulus.
skinids=np.array(sorted({i for face,name in zip(f,g) if name=='skin' for i in face}))
s=v[skinids];rad=(s[:,0]/2.8)**2+((s[:,1]-10)/3.7)**2
samples=s[(rad>1)&(rad<1.6)&(s[:,2]<-9)]
samples=np.vstack((v[outer],samples[::max(1,len(samples)//400)]))
_,ix=np.unique(np.round(samples[:,:2],6),axis=0,return_index=True);samples=samples[ix]
base=RBFInterpolator(samples[:,:2],samples[:,2],kernel='thin_plate_spline',smoothing=.03)
used=sorted({i for face in faces for i in face});idx={i:j for j,i in enumerate(used)}
verts=v[used].tolist();faces=[[idx[i] for i in face] for face in faces];outer=[idx[i] for i in outer]
nu=sorted({i for face in patch for i in face});ni={i:j+len(verts) for j,i in enumerate(nu)}
q=n[nu].copy();xy=np.c_[q[:,0],q[:,1]+6.9]
pad=-.22+.35*np.sqrt(np.maximum(0,1-(q[:,0]/3.1)**2-((q[:,1]-3.1)/3.6)**2))
delta=np.maximum(0,q[:,2]-pad)
rad=np.sqrt((q[:,0]/2.5)**2+((q[:,1]-3.1)/3.4)**2)
t=np.clip((1-rad)/.30,0,1);fade=t*t*(3-2*t)
new=np.c_[xy,base(xy)-delta*fade]
shrink=np.clip((rad-.30)/.70,0,1);shrink=shrink*shrink*(3-2*shrink)
new[:,0]*=1-.22*shrink
new[:,1]=10+(new[:,1]-10)*(1-.22*shrink)
new[:,2]=base(new[:,:2])-delta*fade
verts+=new.tolist();inner=[ni[i] for i in inner]
for face in patch:faces.append([ni[i] for i in face[::-1]]);groups.append('nose_surface')
# Align both cyclic loops by polar progression, preserving their genuine edges.
V=np.array(verts)
def ordered(ids):
 a=np.arctan2((V[ids,1]-10)/3.7,V[ids,0]/2.8)
 j=int(np.argmin(a));ids=ids[j:]+ids[:j]
 aa=np.unwrap(np.arctan2((V[ids,1]-10)/3.7,V[ids,0]/2.8))
 if aa[-1]<aa[0]:ids=ids[:1]+ids[:0:-1]
 aa=np.unwrap(np.arctan2((V[ids,1]-10)/3.7,V[ids,0]/2.8))
 return ids,np.r_[aa,aa[0]+2*np.pi]
outer,oa=ordered(outer);inner,ia=ordered(inner)
i=j=0;bridge=[]
while i<len(outer) or j<len(inner):
 a=outer[i%len(outer)];b=inner[j%len(inner)]
 if j==len(inner) or (i<len(outer) and oa[i+1]<=ia[j+1]):
  bridge.append([a,outer[(i+1)%len(outer)],b]);i+=1
 else:bridge.append([a,inner[(j+1)%len(inner)],b]);j+=1
faces+=bridge;groups+=['nose_join']*len(bridge)
# Fair only the thin transition collar; no original head vertices are moved.
adj=defaultdict(set)
for face in faces:
 for a,b in zip(face,face[1:]+face[:1]):adj[a].add(b);adj[b].add(a)
patchids=np.array([ni[i] for i in nu]);weights=np.clip((rad-.68)/.22,0,1)*.28
for _ in range(12):
 old=V.copy()
 for i,w in zip(patchids,weights):
  if w:V[i]=old[i]*(1-w)+old[list(adj[i])].mean(0)*w
assert np.array_equal(V[:len(used)],v[used])
with (out/'raw.obj').open('w',encoding='utf8') as stream:
 for p in V:stream.write('v '+' '.join(f'{a:.8f}' for a in p)+'\n')
 last=None
 for face,name in zip(faces,groups):
  if name!=last:stream.write('g '+name+'\n');last=name
  stream.write('f '+' '.join(str(i+1) for i in face)+'\n')
sys.path.insert(0,'__CHAR_PROJECT__/.agents/skills/game-character-modeling/scripts')
from orient_obj import orient
report=orient(out/'raw.obj',out/'head-neck.obj')
(out/'assembly.json').write_text(json.dumps(dict(source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),nose=str(nose),preserved_original_vertices=len(used),original_vertex_max_displacement_cm=0,head_boundary=len(outer),nose_boundary=len(inner),bridging_triangles=len(bridge),method='Remove backing; fit underlying face from outer annulus; graft anterior nose surface with shared-index collar',orientation=report,limitations=['Shape pending rendered inspection','No UV or animation validation','Existing independent ears remain unwelded']),indent=2),encoding='utf8')
print(out)
