from pathlib import Path
import numpy as np,json
from scipy.sparse import coo_matrix
R=Path(__file__).resolve().parents[2]; root=R/'art/assets/authored/city/zbrush-reference-head-v01';out=root/'body-detail-v02';out.mkdir(exist_ok=True)
v=[];f=[]
for l in (root/'body-detail-v01/body.obj').read_text().splitlines():
 if l.startswith('v '):v.append(list(map(float,l.split()[1:])))
 elif l.startswith('f '):f.append([int(a)-1 for a in l.split()[1:]])
v=np.array(v);original=v.copy();edges=np.array([(a,b) for face in f for a,b in zip(face,face[1:]+face[:1])]);edges=np.unique(np.sort(edges,axis=1),axis=0)
a,b=edges.T;mat=coo_matrix((np.ones(len(a)*2),(np.r_[a,b],np.r_[b,a])),shape=(len(v),len(v))).tocsr();degree=np.asarray(mat.sum(axis=1)).ravel();degree[degree==0]=1
w=.45*np.exp(-((v[:,1]+49.15)/3.8)**4)
foot=.35*np.clip((-v[:,1]-144)/5,0,1)*np.clip((v[:,2]+19)/5,0,1)
for i in range(100):
 weight=np.maximum(w,foot if i<45 else 0)
 v+=(mat@v/degree[:,None]-v)*weight[:,None]
assert np.max(np.abs(v[original[:,1]>-40]-original[original[:,1]>-40]))<1e-8
with (out/'body.obj').open('w') as o:
 for p in v:o.write('v '+' '.join('%.8f'%a for a in p)+'\n')
 for face in f:o.write('f '+' '.join(str(a+1) for a in face)+'\n')
(out/'construction.json').write_text(json.dumps({'source':str(root/'body-detail-v01/body.obj'),'operation':'Local topology-aware waist fairing and proximal foot fairing; chest and upper limbs unchanged from v01','max_displacement_cm':float(np.linalg.norm(v-original,axis=1).max())},indent=2))
print(out)
