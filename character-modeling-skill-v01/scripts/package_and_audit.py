"""Local-only packaging and additional actual source-unit checks; Blender -b only."""
import bpy, json, hashlib, shutil, sys
from pathlib import Path
from mathutils import Vector
import numpy as np
O=Path(sys.argv[sys.argv.index('--')+1]).resolve()
A=O/'workspace/art/assets/authored/city/zbrush-reference-head-v01'
D=O/'deliverable'; D.mkdir(exist_ok=True)
assert bpy.app.background
bpy.ops.wm.open_mainfile(filepath=str(A/'walk-test-v03/citizen-walk.blend'))
sc=bpy.context.scene; body=bpy.data.objects['Citizen_OriginalBody']; rig=bpy.data.objects['Citizen_TestRig']
sc.frame_set(1)
checks=[]
for f in range(1,34):
 sc.frame_set(f)
 dg=bpy.context.evaluated_depsgraph_get(); ev=body.evaluated_get(dg); mesh=ev.to_mesh()
 co=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',co);co=co.reshape(-1,3)
 checks.append({'frame':f,'finite':bool(np.isfinite(co).all()),'min_z_m':float(co[:,2].min()),'max_z_m':float(co[:,2].max())})
 ev.to_mesh_clear()
weights=np.array([sum(g.weight for g in v.groups) for v in body.data.vertices])
audit={'all_33_frames':checks,'weights_sum_min':float(weights.min()),'weights_sum_max':float(weights.max()),'unweighted_vertices':int((weights==0).sum()),'bones':len(rig.data.bones),'vertices':len(body.data.vertices),'polygons':len(body.data.polygons),'posed_dimensions_frame33_m':list(body.dimensions)}
(D/'additional-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(D/'citizen-walk.blend'))
rig.data.pose_position='REST';bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(D/'citizen-rest.blend'))
sc.cycles.samples=16;sc.render.resolution_x=640;sc.render.resolution_y=720
cam=sc.camera
shots=[
 ('head-front',(0,.07,1.65),.40,(0,4,0)),
 ('head-side',(0,.04,1.65),.40,(4,0,0)),
 ('head-oblique',(0,.04,1.65),.40,(3,4,.1)),
 ('head-underjaw',(0,.04,1.56),.40,(.25,1,-.6)),
 ('hand-palm',(.485,.02,.866),.29,(0,4,0)),
 ('hand-dorsal',(.485,.02,.866),.29,(0,-4,0)),
 ('foot-inside',(.132,.07,.09),.32,(-3,1,1)),
 ('foot-bottom',(.132,.07,.09),.32,(0,0,-4)),
]
bpy.ops.object.light_add(type='AREA',location=(0,0,-2));bottom_light=bpy.context.object;bottom_light.data.energy=100;bottom_light.data.size=2;bottom_light.rotation_euler=(Vector((0,0,0))-bottom_light.location).to_track_quat('-Z','Y').to_euler()
for name,target,size,offset in shots:
 bottom_light.hide_render=(name!='foot-bottom')
 bpy.data.objects['Ground'].hide_render=(name=='foot-bottom')
 cam.data.clip_end=4.2 if name=='foot-bottom' else 100
 target=Vector(target);cam.data.ortho_scale=size;cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(D/(name+'.png'));bpy.ops.render.render(write_still=True)
shutil.copyfile(A/'body-detail-v02/body.obj',D/'citizen-original-cm.obj')
for p in (O/'render').glob('*.png'):shutil.copyfile(p,D/('rest-'+p.name))
for p in (A/'walk-test-v03').glob('side-*.png'):shutil.copyfile(p,D/p.name)
