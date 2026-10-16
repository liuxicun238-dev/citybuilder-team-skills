"""Replace underside connectivity only, preserving existing face coordinates.
Clips the lower posterior shell, bridges the broad mandibular boundary to an
anatomically placed cervical ring. No global remeshing or face regeneration.
"""
from pathlib import Path
import json,math
import numpy as np
from scipy.sparse import coo_matrix,diags
ROOT=Path('__CHAR_PROJECT__/art/assets/authored/city/zbrush-reference-head-v01')
OUT=ROOT/'preserve-face-neck-v05';OUT.mkdir(exist_ok=True)
src=ROOT/'profile-cage-v01/head.obj';verts=[];faces=[];groups=[];g='skin'
for line in src.read_text().splitlines():
 p=line.split()
 if not p:continue
 if p[0]=='v':verts.append(list(map(float,p[1:4])))
 elif p[0]=='g':g=p[1]
 elif p[0]=='f':faces.append([int(q)-1 for q in p[1:]]);groups.append(g)
original=np.array(verts);original_count=len(verts);clipped=[];cg=[];cache={}
def signed(p):return p[1]-5.5-.5*p[2]
def crossing(a,b):
 key=tuple(sorted((a,b)))
 if key not in cache:
  p=np.array(verts[a]);q=np.array(verts[b]);s=signed(p);t=signed(q)
  cache[key]=len(verts);verts.append((p+(q-p)*(s/(s-t))).tolist())
 return cache[key]
for face,g in zip(faces,groups):
 if g!='skin':clipped.append(face);cg.append(g);continue
 result=[]
 for a,b in zip(face[-1:]+face[:-1],face):
  sa=signed(verts[a]);sb=signed(verts[b])
  if (sa>=0)!=(sb>=0):result.append(crossing(a,b))
  if sb>=0:result.append(b)
 if len(result)>=3:clipped.append(result);cg.append(g)
counts={};neighbors={}
for face,g in zip(clipped,cg):
 if g!='skin':continue
 for a,b in zip(face,face[1:]+face[:1]):
  k=tuple(sorted((a,b)));counts[k]=counts.get(k,0)+1
  neighbors.setdefault(a,set()).add(b);neighbors.setdefault(b,set()).add(a)
adj={}
for (a,b),n in counts.items():
 if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
if any(len(n)!=2 for n in adj.values()):raise RuntimeError('Boundary is not simple loops')
loops=[];unseen=set(adj)
while unseen:
 start=min(unseen);loop=[start];prev=None
 while True:
  nxt=next(n for n in adj[loop[-1]] if n!=prev)
  if nxt==start:break
  prev=loop[-1];loop.append(nxt)
  if len(loop)>len(adj):raise RuntimeError('Invalid boundary walk')
 loops.append(loop);unseen.difference_update(loop)
candidate=[]
for loop in loops:
 p=np.array([verts[i] for i in loop]);span=np.ptp(p,axis=0)
 if span[2]>8 and p[:,1].min()<1:candidate.append(loop)
if len(candidate)!=1:raise RuntimeError('Cannot identify one broad underside boundary')
loop=candidate[0];points=np.array([verts[i] for i in loop]);angles=np.arctan2(points[:,0],points[:,2]+3)
unwrapped=np.unwrap(angles);da=np.diff(unwrapped);sign=float(np.sign(np.median(da)))
reversals=int((da*sign < -1e-4).sum())
if reversals>2:raise RuntimeError(f'Boundary not star shaped: {reversals}')
targets=np.array([[4.15*math.sin(a),1.3+3.1*math.cos(a),-1.6+5*math.cos(a)] for a in angles])
outer=set(loop);tangents=[]
for i,p,q in zip(loop,points,targets):
 # Clipped triangles have irregular one-ring neighborhoods. Estimating a
 # separate tangent from each one-ring caused alternating folds; use a smooth
 # shared geometric field, not that sampling-dependent derivative.
 d=(q-p)*.75;d[1]-=.15*np.linalg.norm(q-p)
 tangents.append(d)
tangents=np.array(tangents);rings=[loop]
for j in range(1,17):
 t=j/16;h00=2*t**3-3*t*t+1;h10=t**3-2*t*t+t;h01=-2*t**3+3*t*t;h11=t**3-t*t
 ring=[]
 for p,q,d in zip(points,targets,tangents):
  end=np.array([0,-np.linalg.norm(q-p)*.8,0]);pos=h00*p+h10*d+h01*q+h11*end
  ring.append(len(verts));verts.append(pos.tolist())
 rings.append(ring)
for j in range(1,25):
 t=j/24;ring=[]
 for a,q in zip(angles,targets):
  pos=[(4.15+.20*t)*math.sin(a),q[1]*(1-t)-8*t,(-1.6+.4*t)+5*math.cos(a)]
  ring.append(len(verts));verts.append(pos)
 rings.append(ring)
for a,b in zip(rings,rings[1:]):
 for j in range(len(loop)):
  n=(j+1)%len(loop);clipped.append([a[j],a[n],b[n],b[j]]);cg.append('neck_patch')
protected_set={i for i,(x,y,z) in enumerate(original) if z<-8 and y>1.5}
# Constrained surface relaxation only in the repaired underside/nape; facial
# coordinates and independent eye/ear meshes remain locked.
edges=set();skin_ids=set()
for f,g in zip(clipped,cg):
 if g not in ('skin','neck_patch'):continue
 skin_ids.update(f)
 for a,b in zip(f,f[1:]+f[:1]):edges.add((a,b));edges.add((b,a))
rr,cc=zip(*edges);adjmat=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(verts),len(verts))).tocsr();degree=np.asarray(adjmat.sum(1)).ravel();avg=diags(1/np.maximum(degree,1))@adjmat
pos=np.array(verts);weights=np.zeros(len(verts))
for i in skin_ids:
 if i in protected_set:continue
 if i>=original_count:weights[i]=.45 if pos[i,1]>-7.8 else 0
 elif pos[i,1]<1.5:
  weights[i]=.45*max(0,min(1,(1.5-pos[i,1])/1.0))
 elif pos[i,2]>-8 and pos[i,1]<10:
  weights[i]=.45*max(0,min(1,(10-pos[i,1])/2))
for _ in range(100):pos+=(avg@pos-pos)*weights[:,None]
verts=pos.tolist()
used=sorted(set(i for f in clipped for i in f));mapping={i:j for j,i in enumerate(used)}
with (OUT/'head-neck-raw.obj').open('w',encoding='utf8') as f:
 for i in used:f.write('v '+' '.join(f'{q:.8f}' for q in verts[i])+'\n')
 last=None
 for face,g in zip(clipped,cg):
  if g!=last:f.write('g '+g+'\n');last=g
  f.write('f '+' '.join(str(mapping[i]+1) for i in face)+'\n')
# Check every original coordinate kept, and protected face geometry fully retained.
protected=[i for i,(x,y,z) in enumerate(original) if z<-8 and y>1.5]
missing=set(protected)-set(used)
if missing:raise RuntimeError('Protected facial vertex removed')
maxmove=max(np.linalg.norm(np.array(verts[i])-original[i]) for i in protected)
if maxmove!=0:raise RuntimeError('Protected face changed')
(OUT/'preservation.json').write_text(json.dumps(dict(source=str(src),protected_vertices=len(protected),protected_max_movement_cm=float(maxmove),protected_missing_vertices=len(missing),boundary_vertices=len(loop),boundary_bounds_cm=[points.min(0).tolist(),points.max(0).tolist()],boundary_angle_reversals=reversals,source_coordinate_count=original_count,output_vertices=len(used),output_faces=len(clipped),limitations=['Face shape retains original defects','Cervical/jaw geometry awaiting five-view visual inspection','No self-intersection or animation tests']),indent=2),encoding='utf8')
