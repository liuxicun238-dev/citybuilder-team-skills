import bpy,sys,json
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
assert bpy.app.background
R=Path('__CHAR_PROJECT__/art/assets/authored/city/zbrush-reference-head-v01')
src=R/'nose-fit-v08/head-neck.obj';out=R/'nose-fit-v09';out.mkdir(exist_ok=True)
v=[];f=[];g=[];name='skin';removed=[]
for line in src.read_text().splitlines():
 a=line.split()
 if not a:continue
 if a[0]=='v':v.append(tuple(map(float,a[1:4])))
 elif a[0]=='g':name=a[1]
 elif a[0]=='f':
  face=[int(x)-1 for x in a[1:]]
  if name=='nose_join':removed.append(face)
  else:f.append(face);g.append(name)
edges=Counter(tuple(sorted((a,b))) for face in removed for a,b in zip(face,face[1:]+face[:1]))
boundary=[e for e,n in edges.items() if n==1];ids=sorted({i for e in boundary for i in e});index={x:i for i,x in enumerate(ids)}
coords=[Vector(v[i][:2]) for i in ids];constraints=[(index[a],index[b]) for a,b in boundary]
res=delaunay_2d_cdt(coords,constraints,[],0,1e-8,True)
cv,ce,cf,orig,_,_=res
mapped=[]
for i,origids in enumerate(orig):
 if len(origids)!=1:raise RuntimeError('Intersecting collar boundaries')
 mapped.append(ids[origids[0]])
# Even-odd crossing of both boundary loops identifies the annulus.
def inside(x,y):
 odd=False
 for a,b in boundary:
  ax,ay=v[a][:2];bx,by=v[b][:2]
  if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:odd=not odd
 return odd
count=0
for face in cf:
 x=sum(cv[i].x for i in face)/len(face);y=sum(cv[i].y for i in face)/len(face)
 if inside(x,y):f.append([mapped[i] for i in face]);g.append('nose_join');count+=1
with (out/'raw.obj').open('w',encoding='utf8') as s:
 for p in v:s.write('v '+' '.join(map(str,p))+'\n')
 last=None
 for face,name in zip(f,g):
  if name!=last:s.write('g '+name+'\n');last=name
  s.write('f '+' '.join(str(i+1) for i in face)+'\n')
sys.path.insert(0,'__CHAR_PROJECT__/.agents/skills/game-character-modeling/scripts')
from orient_obj import orient
report=orient(out/'raw.obj',out/'head-neck.obj')
(out/'assembly.json').write_text(json.dumps(dict(source=str(src),method='Constrained Delaunay annulus replaces angular zipper; real boundary edges preserved',triangles=count,orientation=report),indent=2),encoding='utf8')
print('Collar faces',count)
