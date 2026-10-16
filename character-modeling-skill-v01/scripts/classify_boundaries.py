from pathlib import Path
from collections import Counter,defaultdict
import json,numpy as np,sys
O=Path(sys.argv[1]).resolve();p=O/'deliverable/citizen-original-cm.obj'
v=[];edges=Counter()
for l in p.open(encoding='utf8'):
 if l.startswith('v '):v.append(list(map(float,l.split()[1:4])))
 elif l.startswith('f '):
  f=[int(t.split('/')[0])-1 for t in l.split()[1:]]
  for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))]+=1
adj=defaultdict(set)
for (a,b),n in edges.items():
 if n==1:adj[a].add(b);adj[b].add(a)
v=np.array(v);seen=set();groups=[]
for start in adj:
 if start in seen:continue
 stack=[start];ids=[];seen.add(start)
 while stack:
  i=stack.pop();ids.append(i)
  for j in adj[i]:
   if j not in seen:seen.add(j);stack.append(j)
 a=v[ids];c=a.mean(axis=0);ext=np.ptp(a,axis=0)
 if c[1]>23:label='tiny crown opening'
 elif abs(abs(c[0])-3.42)<.1 and abs(c[1]-13)<.2 and ext.max()<.01:label='tiny eyeball pole opening'
 elif abs(abs(c[0])-3.42)<.2 and 12<c[1]<14:label='eyelid/eyeball interface opening'
 else:label='unclassified opening; inspect geometry before assigning anatomy'
 groups.append({'vertex_count':len(ids),'all_degree_2':all(len(adj[i])==2 for i in ids),'centre_cm':c.tolist(),'extent_cm':ext.tolist(),'interpretation':label})
(O/'boundary-classification.json').write_text(json.dumps({'axis':'source cm, Y-up, -Z-front','groups':groups,'limitation':'Spatial interpretation only; not a self-intersection or watertightness validation'},indent=2))
