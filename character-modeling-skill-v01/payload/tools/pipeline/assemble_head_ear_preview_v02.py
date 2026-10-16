"""Non-destructive bilateral ear fitting preview, source units cm."""
from pathlib import Path
import numpy as np,json,hashlib,math
ROOT=Path('__CHAR_PROJECT__/art/assets/authored/city')
head=ROOT/'zbrush-reference-head-v01/preserve-face-neck-v05/head-neck.obj'
ear=ROOT/'citizen-ear-sculpt-v01/a04/ear.obj'
out=ROOT/'zbrush-reference-head-v01/ear-fit-v02';out.mkdir(exist_ok=True)
def read(p):
 v=[];faces=[];groups=[];g='skin'
 for l in p.read_text(encoding='utf8').splitlines():
  a=l.split()
  if not a:continue
  if a[0]=='v':v.append(list(map(float,a[1:4])))
  elif a[0]=='g':g=a[1]
  elif a[0]=='f':faces.append([int(i)-1 for i in a[1:]]);groups.append(g)
 return np.array(v),faces,groups
v,f,g=read(head);ev,ef,eg=read(ear)
keep=[i for i,n in enumerate(g) if n!='ear'];faces=[f[i] for i in keep];groups=[g[i] for i in keep]
used=sorted({i for face in faces for i in face});mapping={i:j for j,i in enumerate(used)}
verts=v[used].tolist();faces=[[mapping[i] for i in face] for face in faces]
angle=math.radians(20)
for sign in [1,-1]:
 u=ev[:,0]*.70;h=ev[:,1]*.84;w=ev[:,2]*.84
 p=np.c_[sign*(7.85+u*math.sin(angle)+w*math.cos(angle)),8.0+h,-.30+u*math.cos(angle)-w*math.sin(angle)]
 offset=len(verts);verts+=p.tolist()
 for face in ef:
  ids=[offset+i for i in face]
  # Local [u,h,w] to head [outward,height,posterior] reverses orientation on right.
  if sign==1:ids.reverse()
  faces.append(ids);groups.append('new_ear_right' if sign==1 else 'new_ear_left')
with (out/'head-neck.obj').open('w',encoding='utf8') as stream:
 for p in verts:stream.write('v '+' '.join(f'{x:.8f}' for x in p)+'\n')
 last=None
 for face,name in zip(faces,groups):
  if last!=name:stream.write('g '+name+'\n');last=name
  stream.write('f '+' '.join(str(i+1) for i in face)+'\n')
(out/'assembly.json').write_text(json.dumps(dict(head_source=str(head),ear_source=str(ear),head_sha256=hashlib.sha256(head.read_bytes()).hexdigest(),ear_sha256=hashlib.sha256(ear.read_bytes()).hexdigest(),scale_xyz=[.70,.84,.84],height_origin_cm=8.0,outward_angle_degrees=20,retained_head_coordinates_unchanged=True,removed_only_group='ear',status='visual assembly preview',limitations=['Ear roots intersect scalp; not welded','Small refinement after user acknowledged prior fitting','No UV rigging or game integration']),indent=2),encoding='utf8')
