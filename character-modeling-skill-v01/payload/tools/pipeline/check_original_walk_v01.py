import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[2];O=R/'art/assets/authored/city/zbrush-reference-head-v01/walk-test-v03'
bpy.ops.wm.open_mainfile(filepath=str(O/'citizen-walk.blend'));sc=bpy.context.scene;body=bpy.data.objects['Citizen_OriginalBody'];rig=bpy.data.objects['Citizen_TestRig']
poses=[]
for f in [1,33]:
 sc.frame_set(f);bpy.context.view_layer.update();poses.append(np.array([list(row) for p in rig.pose.bones for row in p.matrix]))
audit={'cycle_matrix_max_error':float(np.abs(poses[0]-poses[1]).max()),'weight_sum_min':min(sum(g.weight for g in v.groups) for v in body.data.vertices),'weight_sum_max':max(sum(g.weight for g in v.groups) for v in body.data.vertices)}
(O/'audit.json').write_text(json.dumps(audit,indent=2));cam=sc.camera;cam.location=(5,0,1.5);cam.rotation_euler=(Vector((0,0,.9))-cam.location).to_track_quat('-Z','Y').to_euler()
for f in [1,9,17,25]:
 sc.frame_set(f);sc.render.filepath=str(O/f'side-{f:03d}.png');bpy.ops.render.render(write_still=True)
