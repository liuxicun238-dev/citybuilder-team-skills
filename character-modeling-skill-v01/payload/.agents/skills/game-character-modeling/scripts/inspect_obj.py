"""Read-only OBJ structure check. Does not judge anatomical quality."""
import argparse,json,math,hashlib
from collections import Counter
from pathlib import Path

def inspect(path,unit):
 v=[];faces=[];uvfaces=0
 for line in path.read_text(encoding='utf8',errors='strict').splitlines():
  p=line.split()
  if not p:continue
  if p[0]=='v':
   xyz=tuple(map(float,p[1:4]))
   if len(xyz)!=3 or not all(math.isfinite(x) for x in xyz):raise ValueError('Invalid vertex')
   v.append(xyz)
  elif p[0]=='f':
   ids=[]
   for token in p[1:]:
    i=int(token.split('/')[0]);i=i-1 if i>0 else len(v)+i
    if i<0 or i>=len(v):raise ValueError('Invalid face index')
    ids.append(i)
   if len(ids)<3:raise ValueError('Face has fewer than 3 vertices')
   faces.append(ids);uvfaces+=all(len(x.split('/'))>1 and bool(x.split('/')[1]) for x in p[1:])
 if not v or not faces:raise ValueError('No mesh geometry')
 parent=list(range(len(v)))
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 edges=Counter();directions=Counter();used=set();degenerate=0;triangles=0
 for f in faces:
  used.update(f)
  for a,b in zip(f,f[1:]+f[:1]):
   edges[tuple(sorted((a,b)))]+=1;directions[a,b]+=1;parent[find(a)]=find(b)
  for k in range(1,len(f)-1):
   a,b,c=[v[i] for i in (f[0],f[k],f[k+1])];ab=[b[j]-a[j] for j in range(3)];ac=[c[j]-a[j] for j in range(3)]
   cr=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
   degenerate+=sum(x*x for x in cr)<1e-24;triangles+=1
 scale={'m':1,'cm':.01,'mm':.001}[unit]
 return dict(source=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),unit=unit,vertices=len(v),polygons=len(faces),triangles=triangles,unused_vertices=len(v)-len(used),components=len({find(i) for i in used}),boundary_edges=sum(n==1 for n in edges.values()),nonmanifold_edges=sum(n>2 for n in edges.values()),inconsistent_winding_edges=sum(n==2 and (directions[a,b]==2 or directions[b,a]==2) for (a,b),n in edges.items()),degenerate_triangles=degenerate,faces_with_uv=uvfaces,bounds_m=[[min(p[j] for p in v)*scale for j in range(3)],[max(p[j] for p in v)*scale for j in range(3)]],limitations=['No self-intersection test','No likeness or anatomy judgement','Boundaries/components may be intentional; interpret by part','No animation validation'])
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('obj',type=Path);ap.add_argument('--unit',required=True,choices=['m','cm','mm']);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 report=inspect(a.obj,a.unit);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
