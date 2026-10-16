"""Make connected OBJ face winding consistent. Does not infer outward direction."""
import argparse,json,hashlib
from pathlib import Path
from collections import defaultdict,deque

def orient(source,target):
 if source.resolve()==target.resolve():raise ValueError('Output must differ from source')
 lines=source.read_text(encoding='utf8').splitlines();faces=[];count=0;edges=defaultdict(list)
 for line_no,line in enumerate(lines):
  p=line.split()
  if not p:continue
  if p[0]=='v':count+=1
  if p[0]!='f':continue
  tokens=p[1:]
  if any(len(t.split('/'))>2 and t.split('/')[2] for t in tokens):raise ValueError('Explicit vertex normals unsupported; export a geometry-only OBJ first')
  ids=[]
  for t in tokens:
   i=int(t.split('/')[0]);i=i-1 if i>0 else count+i
   if i<0 or i>=count:raise ValueError('Invalid vertex reference')
   ids.append(i)
  index=len(faces);faces.append((line_no,tokens))
  for a,b in zip(ids,ids[1:]+ids[:1]):
   if a==b:raise ValueError('Collapsed edge')
   edges[tuple(sorted((a,b)))].append((index,1 if a<b else -1))
 adj=defaultdict(list)
 for e,items in edges.items():
  if len(items)>2:raise ValueError('Nonmanifold edge: ambiguous orientation')
  if len(items)==2:
   (a,da),(b,db)=items;rel=-da*db;adj[a].append((b,rel));adj[b].append((a,rel))
 signs={};components=0
 for seed in range(len(faces)):
  if seed in signs:continue
  components+=1;signs[seed]=1;q=deque([seed])
  while q:
   a=q.popleft()
   for b,rel in adj[a]:
    wanted=signs[a]*rel
    if b in signs:
     if signs[b]!=wanted:raise ValueError('Non-orientable component or conflicting topology')
    else:signs[b]=wanted;q.append(b)
 changed=0
 for i,(line_no,tokens) in enumerate(faces):
  if signs[i]<0:lines[line_no]='f '+' '.join(reversed(tokens));changed+=1
 target.parent.mkdir(parents=True,exist_ok=True);target.write_text('\n'.join(lines)+'\n',encoding='utf8')
 return dict(source=str(source.resolve()),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),output=str(target.resolve()),flipped_faces=changed,face_components=components,limitations=['Consistent does not guarantee outward normals','No vertex movement, self-intersection repair or hole closing','Geometry-only OBJ; explicit vertex normals rejected'])
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--report',required=True,type=Path);a=ap.parse_args();report=orient(a.input,a.out);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
