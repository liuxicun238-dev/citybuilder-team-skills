import bpy,bmesh,json
from pathlib import Path
assert bpy.app.background
R=Path('__CHAR_PROJECT__/art/assets/authored/city/zbrush-reference-head-v01');src=R/'nose-fit-v09/head-neck.obj';out=R/'nose-fit-v10';out.mkdir(exist_ok=True)
v=[];f=[];g=[];names=[];name='skin'
for l in src.read_text().splitlines():
 a=l.split()
 if not a:continue
 if a[0]=='v':v.append(tuple(map(float,a[1:4])))
 elif a[0]=='g':
  name=a[1]
  if name not in names:names.append(name)
 elif a[0]=='f':f.append([int(i)-1 for i in a[1:]]);g.append(names.index(name))
me=bpy.data.meshes.new('NoseSurface');me.from_pydata(v,[],f);bm=bmesh.new();bm.from_mesh(me);layer=bm.faces.layers.int.new('source_group');bm.faces.ensure_lookup_table()
for face,group in zip(bm.faces,g):face[layer]=group
joinid=names.index('nose_join');edges={e for face in bm.faces if face[layer]==joinid for e in face.edges}
result=bmesh.ops.subdivide_edges(bm,edges=list(edges),cuts=3,use_grid_fill=True)
region={v for face in bm.faces if face[layer]==joinid for v in face.verts}
weights={v:1. for v in region};front=region.copy()
for weight in [.9,.7,.45,.2]:
 nxt={e.other_vert(v) for v in front for e in v.link_edges}-weights.keys()
 for v in nxt:weights[v]=weight
 front=nxt
for _ in range(45):
 change={v:sum(e.other_vert(v).co.z for e in v.link_edges)/len(v.link_edges) for v in weights}
 for v,z in change.items():v.co.z+=(z-v.co.z)*.40*weights[v]
bm.verts.index_update();bm.normal_update()
with (out/'head-neck.obj').open('w',encoding='utf8') as s:
 for v in bm.verts:s.write('v '+' '.join(f'{x:.8f}' for x in v.co)+'\n')
 last=None
 for face in bm.faces:
  name=names[face[layer]]
  if name!=last:s.write('g '+name+'\n');last=name
  s.write('f '+' '.join(str(v.index+1) for v in face.verts)+'\n')
(out/'assembly.json').write_text(json.dumps(dict(source=str(src),method='Subdivide shared collar edges, depth-only weighted fairing across both sides',affected_vertices=len(weights),iterations=45,limitations=['No full self-intersection or animation check','Nose shape draft; ear attachments remain independent']),indent=2),encoding='utf8')
print('Fairing vertices',len(weights))
