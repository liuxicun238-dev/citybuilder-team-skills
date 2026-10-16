"""Small local tragus fairing on acknowledged ear, source cm."""
from pathlib import Path
import numpy as np,json
from scipy.sparse import coo_matrix,diags
root=Path('__CHAR_PROJECT__/art/assets/authored/city/citizen-ear-sculpt-v01')
source=root/'a03/ear.obj';import argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
lines=source.read_text().splitlines();v=[];rows=[];faces=[]
for i,l in enumerate(lines):
 p=l.split()
 if p and p[0]=='v':rows.append(i);v.append(list(map(float,p[1:])))
 elif p and p[0]=='f':faces.append([int(t)-1 for t in p[1:]])
v=np.array(v);q=v.copy();edges={(a,b) for f in faces for a,b in zip(f,f[1:]+f[:1])};edges|={(b,a) for a,b in edges};rr,cc=zip(*edges)
A=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(v),len(v))).tocsr();A=diags(1/np.maximum(np.asarray(A.sum(1)).ravel(),1))@A
x,y,z=v.T
w=np.maximum(0,1-((x+1.2)/.65)**2-((y-3.1)/.95)**2)**2*np.clip((z+.1)/.25,0,1)
for _ in range(18):q+=(A@q-q)*(.25*w[:,None])
for i,p in zip(rows,q):lines[i]='v '+' '.join(f'{a:.8f}' for a in p)
(out/'ear.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
(out/'refinement.json').write_text(json.dumps(dict(source=str(source),max_movement_cm=float(np.linalg.norm(q-v,axis=1).max()),method='18 local Laplacian steps, tragus only, unchanged connectivity'),indent=2),encoding='utf8')
