from pathlib import Path
import numpy as np,json,sys
from scipy.sparse import coo_matrix,diags
R=Path('__CHAR_PROJECT__');root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'chin-refine-v02/head-neck.obj';out=root/'chin-refine-v03';out.mkdir(exist_ok=True)
lines=src.read_text().splitlines();v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]);old=v.copy();edges=set()
for line in lines:
 if line.startswith('f '):
  f=[int(i)-1 for i in line.split()[1:]]
  for a,b in zip(f,f[1:]+f[:1]):edges.add((a,b));edges.add((b,a))
e=np.array(sorted(edges));A=coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(len(v),len(v))).tocsr();M=diags(1/np.maximum(1,np.asarray(A.sum(axis=1)).ravel()))@A
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
x,y,z=old.T;w=smooth((y+1.8)/1.6)*(1-smooth((y-3.0)/1.2))*smooth((-z-6.5)/3.0)*(1-smooth((np.abs(x)-3.8)/1.8))*.38
for _ in range(65):v+=(M@v-v)*w[:,None]
assert np.array_equal(v[y>=4.2],old[y>=4.2])
k=0
with (out/'head-neck.obj').open('w',encoding='utf8') as f:
 for line in lines:
  if line.startswith('v '):line='v '+' '.join(f'{q:.8f}' for q in v[k]);k+=1
  f.write(line+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),method='Local weighted geometric fairing across chin and underside, lips and upper face pinned',iterations=65,max_displacement_cm=float(np.linalg.norm(v-old,axis=1).max()),protected_upper_face_displacement_cm=0),indent=2),encoding='utf8')
