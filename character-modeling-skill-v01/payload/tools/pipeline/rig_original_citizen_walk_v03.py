import bpy,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parents[2];O=R/'art/assets/authored/city/zbrush-reference-head-v01/walk-test-v03';O.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.obj_import(filepath=str(O.parent/'body-detail-v02/body.obj'),use_split_groups=False,use_split_objects=False)
body=bpy.context.object;body.name='Citizen_OriginalBody'
mw=body.matrix_world.copy()
for v in body.data.vertices:
 co=mw@v.co;v.co=Vector((co.x*.01,co.y*.01,(co.z+154)*.01))
body.matrix_world=Matrix.Identity(4)
for p in body.data.polygons:p.use_smooth=True
bones={}
def B(n,a,b,parent=None):bones[n]=(Vector(a),Vector(b),parent)
B('root',(0,0,0),(0,0,.15));B('pelvis',(0,.012,.91),(0,.012,1.04),'root');B('spine',(0,.012,1.04),(0,.012,1.25),'pelvis');B('chest',(0,.012,1.25),(0,.012,1.43),'spine');B('neck',(0,.012,1.43),(0,.012,1.55),'chest');B('head',(0,.012,1.55),(0,.012,1.77),'neck')
for s,sg in [('L',1),('R',-1)]:
 B('clavicle'+s,(0,.012,1.43),(sg*.187,.012,1.392),'chest')
 B('arm'+s,(sg*.187,.012,1.392),(sg*.322,.022,1.158),'clavicle'+s)
 B('forearm'+s,(sg*.322,.022,1.158),(sg*.442,.032,.9503),'arm'+s)
 B('hand'+s,(sg*.442,.032,.9503),(sg*.53,.032,.798),'forearm'+s)
 B('thigh'+s,(sg*.093,.008,.91),(sg*.115,.018,.48),'pelvis')
 B('shin'+s,(sg*.115,.018,.48),(sg*.132,.01,.09),'thigh'+s)
 B('foot'+s,(sg*.132,.01,.09),(sg*.132,.15,.025),'shin'+s)
 B('toe'+s,(sg*.132,.15,.025),(sg*.132,.21,.025),'foot'+s)
bpy.ops.object.armature_add();rig=bpy.context.object;rig.name='Citizen_TestRig';bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
for n,(a,b,pa) in bones.items():
 e=rig.data.edit_bones.new(n);e.head=a;e.tail=b
 if pa:e.parent=rig.data.edit_bones[pa]
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
v=np.array([tuple(v.co) for v in body.data.vertices]);names=[n for n in bones if n!='root'];ds=[]
for n in names:
 a,b,_=bones[n];a=np.array(a);d=np.array(b)-a;t=np.clip((v-a)@d/(d@d),0,1);dist=np.sum((v-a-t[:,None]*d)**2,axis=1)
 if n[-1:] in ('L','R'):
  sg=1 if n[-1]=='L' else -1;dist+=np.where(v[:,0]*sg<0,1,0)
 arm_mask=np.clip((np.abs(v[:,0])-(.17+np.clip((1.3-v[:,2])/.2,0,1)*.035))/.065,0,1)
 if n.startswith(('arm','forearm','hand','clavicle')):dist+=(1-arm_mask)*.08
 elif n in ('pelvis','spine','chest'):dist+=arm_mask*.08
 ds.append(dist)
dist=np.array(ds).T
# Compact support around nearest skeleton segment: smooth skin across joints.
w=np.exp(-(dist-dist.min(axis=1)[:,None])/.0025);w[w<.02]=0;w/=w.sum(axis=1)[:,None]
for j,n in enumerate(names):
 vg=body.vertex_groups.new(name=n);q=np.rint(w[:,j]*200).astype(int)
 for val in np.unique(q):
  if val:vg.add(np.flatnonzero(q==val).tolist(),float(val)/200,'REPLACE')
mod=body.modifiers.new('Skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True;body.parent=rig
# Author world-space bone goals, bake local channels. Foot paths are a treadmill-style cycle.
rest={n:rig.data.bones[n].matrix_local.copy() for n in bones};sc=bpy.context.scene;sc.render.fps=24;sc.frame_start=1;sc.frame_end=32
for p in rig.pose.bones:p.rotation_mode='QUATERNION'
def mat(n,a,b):
 a,b=Vector(a),Vector(b);rot=(bones[n][1]-bones[n][0]).rotation_difference(b-a).to_matrix().to_4x4();m=rot@rest[n];m.translation=a;return m
for frame in range(1,34):
 phase=2*math.pi*(frame-1)/32;bob=.008*math.cos(2*phase);goals={};shift=Vector((.008*math.sin(phase),0,bob-.04))
 for n,(a,b,pa) in bones.items():goals[n]=(a+shift,b+shift)
 goals['root']=(bones['root'][0],bones['root'][1])
 for s,sg in [('L',1),('R',-1)]:
  t=((frame-1)/32+(0 if sg==1 else .5))%1
  if t<.6:fy=.22-.44*t/.6;lift=0
  else:u=(t-.6)/.4;fy=-.22+.44*(u-math.sin(2*math.pi*u)/(2*math.pi));lift=.10*math.sin(math.pi*u)
  hip=bones['thigh'+s][0]+shift;ank=Vector((sg*.132,fy+.01,.09+lift));d=ank-hip;D=d.length;u=d.normalized();l1=(bones['thigh'+s][1]-bones['thigh'+s][0]).length;l2=(bones['shin'+s][1]-bones['shin'+s][0]).length
  h=(l1*l1-l2*l2+D*D)/(2*D);bend=Vector((0,1,0));bend=(bend-u*bend.dot(u)).normalized();knee=hip+u*h+bend*math.sqrt(max(0,l1*l1-h*h))
  toe=ank+Vector((0,.14,-.065));tip=toe+Vector((0,.06,0));goals['thigh'+s]=(hip,knee);goals['shin'+s]=(knee,ank);goals['foot'+s]=(ank,toe);goals['toe'+s]=(toe,tip)
  sh=bones['arm'+s][0]+shift;swing=-.15*math.sin(phase+(0 if sg==1 else math.pi));el=sh+Vector((sg*.065,swing*.65,-.262));wr=el+Vector((sg*.035,swing*.45+.035,-.235));hand=wr+Vector((sg*.025,.015,-.173));goals['arm'+s]=(sh,el);goals['forearm'+s]=(el,wr);goals['hand'+s]=(wr,hand)
 for n in bones:
  p=rig.pose.bones[n];p.matrix=mat(n,*goals[n]);bpy.context.view_layer.update();p.keyframe_insert('location',frame=frame);p.keyframe_insert('rotation_quaternion',frame=frame);p.keyframe_insert('scale',frame=frame)
rig.animation_data.action.name='Walk_Test_32f'
matl=bpy.data.materials.new('White clay');matl.diffuse_color=(.55,.57,.6,1);matl.use_nodes=True;bs=matl.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.35,.37,.39,1);bs.inputs['Roughness'].default_value=.72;body.data.materials.clear();body.data.materials.append(matl)
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='Ground'
fm=bpy.data.materials.new('Ground');fm.diffuse_color=(.055,.06,.07,1);fm.use_nodes=True;fm.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.045,.05,.06,1);floor.data.materials.append(fm)
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.render.resolution_x=520;sc.render.resolution_y=640;sc.render.resolution_percentage=100;sc.world.color=(.2,.2,.2)
for pos,en,size in [((3,4,5),500,4),((-3,2,3),250,3),((0,-3,4),450,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=en;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(3,5,2.2));cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=2.15;cam.rotation_euler=(Vector((0,0,.9))-cam.location).to_track_quat('-Z','Y').to_euler()
sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(O/'citizen-walk.blend'))
frames=O/'frames';frames.mkdir(exist_ok=True)
checks=[]
for f in range(1,33,2):
 sc.frame_set(f);deps=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(deps);mesh=ev.to_mesh();co=np.array([tuple(v.co) for v in mesh.vertices]);checks.append({'frame':f,'finite':bool(np.isfinite(co).all()),'min_z':float(co[:,2].min())});ev.to_mesh_clear();sc.render.filepath=str(frames/f'{f:03d}.png');bpy.ops.render.render(write_still=True)
(O/'checks.json').write_text(json.dumps({'bones':len(bones),'vertex_count':len(v),'frames':checks,'limitations':['Test rig, no finger bones or face rig','Procedural treadmill walk, not motion capture','High resolution sculpt mesh, no game LOD']},indent=2))
