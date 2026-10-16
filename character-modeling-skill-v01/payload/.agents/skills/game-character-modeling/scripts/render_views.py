"""Blender background-only OBJ inspection. Source is never modified."""
import bpy,sys,argparse,json,hashlib
from pathlib import Path
from mathutils import Vector
if not bpy.app.background:raise RuntimeError('Run Blender with -b; UI execution prohibited')
ap=argparse.ArgumentParser();ap.add_argument('--mesh',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--unit',required=True,choices=['cm','m','mm']);ap.add_argument('--frame-manifest',type=Path);ap.add_argument('--include-underjaw',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
a.mesh=a.mesh.resolve();a.out=a.out.resolve()
if a.frame_manifest:a.frame_manifest=a.frame_manifest.resolve()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.obj_import(filepath=str(a.mesh),use_split_groups=False,use_split_objects=False)
objects=[o for o in bpy.context.selected_objects if o.type=='MESH'];bpy.context.view_layer.update()
points=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)]);center=(lo+hi)/2;scale=2/max(hi-lo)
if a.frame_manifest:
 frame=json.loads(a.frame_manifest.read_text(encoding='utf8'));center=Vector(frame['preview_center']);scale=float(frame['preview_scale'])
m=bpy.data.materials.new('Inspection clay');m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.35,.37,.39,1);bs.inputs['Roughness'].default_value=.72
for o in objects:
 o.location=(o.location-center)*scale;o.scale*=scale;o.data.materials.clear();o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.seed=0;scene.render.resolution_x=700;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.world.color=(.22,.22,.22);scene.view_settings.view_transform='AgX'
for pos,energy,size in [((3,4,4),550,4),((-3,2,1),260,3),((0,-3,3),450,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=2.5
views={'front':(0,6,0),'side':(6,0,0),'threequarter':(4,6,.2),'back':(0,-6,0)}
if a.include_underjaw:views['underjaw']=(3,6,-3)
for label,pos in views.items():
 cam.location=pos;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(a.out/(label+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'inspection.blend'))
(a.out/'inspection-manifest.json').write_text(json.dumps(dict(source=str(a.mesh.resolve()),source_sha256=hashlib.sha256(a.mesh.read_bytes()).hexdigest(),source_unit=a.unit,source_axis='OBJ Y up, -Z front; Blender default import axis transform',preview_scale=scale,preview_center=list(center),normalized_preview_not_engine_asset=True,blender=bpy.app.version_string,views=views,background=bpy.app.background),indent=2),encoding='utf8')
