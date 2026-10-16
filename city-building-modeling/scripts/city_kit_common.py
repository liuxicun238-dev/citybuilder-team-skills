"""Shared helpers for the city building kits (Blender 5.x). X forward/right of the part, Y depth, Z up; metres.
Every part is a set of objects under one empty root whose origin is the part pivot (door hinge, slide start, barrier pivot...).
"""
import bpy,bmesh,math,os,sys,json
from pathlib import Path
from mathutils import Vector,Matrix

# ---------------- scene ----------------
def new_scene(collection_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.context.scene;s.unit_settings.system='METRIC'
    col=bpy.data.collections.new(collection_name);s.collection.children.link(col)
    return s,col
class Kit:
    def __init__(self,collection_name='KIT'):
        self.scene,self.col=new_scene(collection_name)
        self.root=None
    def part(self,name,**props):
        """Create the root empty for one part. Returns the empty; later adopt()/box() calls attach to the active part."""
        r=bpy.data.objects.new(name,None);self.col.objects.link(r)
        for k,v in props.items():r[k]=v
        self.root=r;return r
    def adopt(self,o,m=None):
        for c in list(o.users_collection):c.objects.unlink(o)
        self.col.objects.link(o);o.parent=self.root
        if m is not None and (not o.data.materials or o.data.materials[0] is not m):o.data.materials.append(m)
        return o
# ---------------- materials ----------------
def mat(n,c,r=.4,metal=0,coat=0,em=0,alpha=None,spec=None):
    m=bpy.data.materials.get(n)
    if m:return m
    m=bpy.data.materials.new(n);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=r;p.inputs['Metallic'].default_value=metal
    p.inputs['Coat Weight'].default_value=coat;p.inputs['Coat Roughness'].default_value=.08
    if em:p.inputs['Emission Color'].default_value=(*c,1);p.inputs['Emission Strength'].default_value=em
    if alpha is not None:p.inputs['Alpha'].default_value=alpha
    if spec is not None:p.inputs['Specular IOR Level'].default_value=spec
    return m
def granite(name='Granite_panel',slab=(1.2,.6),joint=.008,col1=(.27,.27,.265),col2=(.235,.235,.23),rough=.55):
    """Triplanar (object space) granite slab cladding: slab joints + fine speckle. Procedural placeholder; the game material replaces it."""
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nodes=nt.nodes;links=nt.links;bsdf=nodes['Principled BSDF']
    tc=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(tc.outputs['Object'],sep.inputs[0])
    def brick(a,b):
        c=nodes.new('ShaderNodeCombineXYZ');links.new(sep.outputs[a],c.inputs['X']);links.new(sep.outputs[b],c.inputs['Y'])
        br=nodes.new('ShaderNodeTexBrick');br.inputs['Color1'].default_value=(*col1,1);br.inputs['Color2'].default_value=(*col2,1);br.inputs['Mortar'].default_value=(.10,.10,.10,1)
        br.inputs['Scale'].default_value=1.0;br.inputs['Mortar Size'].default_value=joint;br.inputs['Mortar Smooth'].default_value=.1;br.inputs['Brick Width'].default_value=slab[0];br.inputs['Row Height'].default_value=slab[1];br.offset=.5
        links.new(c.outputs[0],br.inputs['Vector']);return br
    yz,xz,xy=brick('Y','Z'),brick('X','Z'),brick('X','Y')
    vm=nodes.new('ShaderNodeVectorMath');vm.operation='ABSOLUTE';links.new(tc.outputs['Normal'],vm.inputs[0])
    ns=nodes.new('ShaderNodeSeparateXYZ');links.new(vm.outputs[0],ns.inputs[0])
    def powr(sock):
        p=nodes.new('ShaderNodeMath');p.operation='POWER';p.inputs[1].default_value=6.0;links.new(sock,p.inputs[0]);return p.outputs[0]
    wx,wy,wz=powr(ns.outputs['X']),powr(ns.outputs['Y']),powr(ns.outputs['Z'])
    def add(a,b):
        n=nodes.new('ShaderNodeMath');n.operation='ADD';links.new(a,n.inputs[0]);links.new(b,n.inputs[1]);return n.outputs[0]
    def div(a,b):
        n=nodes.new('ShaderNodeMath');n.operation='DIVIDE';links.new(a,n.inputs[0]);links.new(b,n.inputs[1]);return n.outputs[0]
    sxy=add(wx,wy);tot=add(sxy,wz);f1=div(wy,sxy);f2=div(wz,tot)
    def mix(a,b,f):
        n=nodes.new('ShaderNodeMix');n.data_type='RGBA';links.new(f,n.inputs['Factor']);links.new(a,n.inputs['A']);links.new(b,n.inputs['B']);return n.outputs['Result']
    cA=mix(yz.outputs['Color'],xz.outputs['Color'],f1);cB=mix(cA,xy.outputs['Color'],f2)
    nz=nodes.new('ShaderNodeTexNoise');nz.inputs['Scale'].default_value=140;nz.inputs['Detail'].default_value=8;links.new(tc.outputs['Object'],nz.inputs['Vector'])
    mulc=nodes.new('ShaderNodeMix');mulc.data_type='RGBA';mulc.blend_type='MULTIPLY';mulc.inputs['Factor'].default_value=.45;links.new(cB,mulc.inputs['A']);links.new(nz.outputs['Color'],mulc.inputs['B'])
    links.new(mulc.outputs['Result'],bsdf.inputs['Base Color']);bsdf.inputs['Roughness'].default_value=rough
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.08;bump.inputs['Distance'].default_value=.01;links.new(nz.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    return m
def mat_vcol(n,c,r=.8,attr='Col'):
    """Base colour multiplied by a colour attribute (per-vertex light/dark variation baked by the generator)."""
    m=bpy.data.materials.get(n)
    if m:return m
    m=bpy.data.materials.new(n);m.use_nodes=True;nt=m.node_tree;b=nt.nodes['Principled BSDF'];b.inputs['Roughness'].default_value=r
    va=nt.nodes.new('ShaderNodeVertexColor');va.layer_name=attr;mx=nt.nodes.new('ShaderNodeMix');mx.data_type='RGBA';mx.blend_type='MULTIPLY';mx.inputs['Factor'].default_value=1.0;mx.inputs['A'].default_value=(*c,1)
    nt.links.new(va.outputs['Color'],mx.inputs['B']);nt.links.new(mx.outputs['Result'],b.inputs['Base Color']);return m
# ---------------- geometry helpers ----------------
def _fin(o,kit,m):
    kit.adopt(o,m);return o
def bevel(o,w=.004,seg=2,angle=50):
    mod=o.modifiers.new('Edge_radius','BEVEL');mod.width=w;mod.segments=seg;mod.limit_method='ANGLE';mod.angle_limit=math.radians(angle);return o
def box(kit,name,loc,dim,m,b=.004,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot);o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    kit.adopt(o,m)
    if b:bevel(o,b)
    return o
def cyl(kit,name,loc,r,depth,m,axis='Z',verts=32,b=.003):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name
    if axis=='Y':o.rotation_euler.x=math.pi/2
    if axis=='X':o.rotation_euler.y=math.pi/2
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=False);kit.adopt(o,m)
    if b:bevel(o,b,1)
    return o
def boxes(kit,name,items,m,b=.003):
    """One merged mesh from many axis-aligned boxes: items=[(cx,cy,cz,dx,dy,dz),...]."""
    bm=bmesh.new()
    for cx,cy,cz,dx,dy,dz in items:
        r=bmesh.ops.create_cube(bm,size=1.0);bmesh.ops.scale(bm,vec=(dx,dy,dz),verts=r['verts']);bmesh.ops.translate(bm,vec=(cx,cy,cz),verts=r['verts'])
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);kit.adopt(o,m)
    if b:bevel(o,b,1,40)
    return o
def mesh_obj(kit,name,verts,faces,m,smooth=False):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);kit.adopt(o,m)
    for p in me.polygons:p.use_smooth=smooth
    return o
def text(kit,name,body,loc,size,m,rot=(math.pi/2,0,0),extrude=.008,font='C:/Windows/Fonts/msyhbd.ttc',align='CENTER'):
    f=bpy.data.fonts.load(font);cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.font=f;cu.align_x=align;cu.align_y='CENTER';cu.size=size;cu.extrude=extrude
    o=bpy.data.objects.new(name,cu);kit.col.objects.link(o);o.parent=kit.root;o.location=loc;o.rotation_euler=rot;cu.materials.append(m);return o
def ring_leaves(kit,name,centre,radius,n,start,end,m,size=.045,rot_axis='Y'):
    """Gold laurel leaves along an arc in the XZ plane (used by the simplified emblem)."""
    bm=bmesh.new()
    for i in range(n):
        a=start+(end-start)*i/(n-1);x=centre[0]+radius*math.cos(a);z=centre[2]+radius*math.sin(a)
        r=bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=size)
        bmesh.ops.scale(bm,vec=(.55,.25,1.0),verts=r['verts']);bmesh.ops.rotate(bm,cent=(0,0,0),matrix=Matrix.Rotation(a,3,'Y'),verts=r['verts']);bmesh.ops.translate(bm,vec=(x,centre[1],z),verts=r['verts'])
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);kit.adopt(o,m)
    for p in me.polygons:p.use_smooth=True
    return o
def emblem(kit,centre,radius,gold,navy,red,facing='-Y'):
    """Simplified police-badge style roundel (game placeholder, not the official artwork): gold ring, navy disc, red shield, gold star + two laurel arcs."""
    cx,cy,cz=centre;s=-1 if facing=='-Y' else 1;out=[]
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=.04,location=(cx,cy,cz),rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='Emblem_ring';kit.adopt(o,gold);out.append(o)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius*.80,depth=.05,location=(cx,cy+s*.004,cz),rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='Emblem_disc';kit.adopt(o,navy);out.append(o)
    sh=[(-.30,.28),(.30,.28),(.30,-.02),(.0,-.34),(-.30,-.02)]
    verts=[(cx+x*radius*.78,cy+s*.032,cz+z*radius*.78) for x,z in sh];o=mesh_obj(kit,'Emblem_shield',verts,[tuple(range(5))],red);sol=o.modifiers.new('S','SOLIDIFY');sol.thickness=.01;out.append(o)
    star=[(cx+(radius*(.17 if i%2==0 else .07))*math.cos(math.pi/2+i*math.pi/5),cy+s*.04,cz+radius*.26+(radius*(.17 if i%2==0 else .07))*math.sin(math.pi/2+i*math.pi/5)) for i in range(10)]
    o=mesh_obj(kit,'Emblem_star',star,[tuple(range(10))],gold);sol=o.modifiers.new('S','SOLIDIFY');sol.thickness=.01;out.append(o)
    out.append(ring_leaves(kit,'Emblem_laurel_L',(cx,cy+s*.03,cz),radius*.66,7,math.radians(200),math.radians(285),gold,radius*.10))
    out.append(ring_leaves(kit,'Emblem_laurel_R',(cx,cy+s*.03,cz),radius*.66,7,math.radians(-105),math.radians(-20),gold,radius*.10))
    return out
# ---------------- review studio ----------------
def studio(kit,floor_size=60,key_scale=1.0):
    s=kit.scene;w=bpy.data.worlds.new('Neutral_studio');w.use_nodes=True;s.world=w;n=w.node_tree.nodes;l=w.node_tree.links
    env=n.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(Path(bpy.utils.system_resource('DATAFILES'))/'studiolights/world/city.exr'));env.image.pack();l.new(env.outputs[0],n.get('Background').inputs[0]);n.get('Background').inputs[1].default_value=.7
    items=[];fl=mat('Studio_floor',(.30,.31,.32),.8);bpy.ops.mesh.primitive_plane_add(size=floor_size,location=(0,0,(-.45 if floor_size>100 else -.002)));q=bpy.context.object;q.name='REVIEW_floor';q.data.materials.append(fl);items.append(q)
    if floor_size>100:
        for name,loc,power in [('Sun',(-40,-50,70),3.2),('Fill',(60,-30,40),.8),('Back',(0,80,50),.6)]:
            d=bpy.data.lights.new(name,'SUN');d.energy=power;d.angle=math.radians(4);q=bpy.data.objects.new(name,d);s.collection.objects.link(q);q.location=loc;q.rotation_euler=(Vector((0,0,0))-q.location).to_track_quat('-Z','Y').to_euler();items.append(q)
    else:
      for name,loc,power,size in [('Key',(14,-16,18),5500*key_scale,10),('Fill',(-14,-8,10),2200*key_scale,10),('Rim',(-8,18,12),3000*key_scale,8)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;q=bpy.data.objects.new(name,d);s.collection.objects.link(q);q.location=loc;q.rotation_euler=(Vector((0,0,1))-q.location).to_track_quat('-Z','Y').to_euler();items.append(q)
    cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);s.collection.objects.link(cam);s.camera=cam
    s.render.engine='CYCLES';s.cycles.use_denoising=True;s.view_settings.view_transform='Khronos PBR Neutral';s.view_settings.exposure=-.3;s.render.image_settings.file_format='PNG'
    try:
        pr=bpy.context.preferences.addons['cycles'].preferences;pr.compute_device_type='OPTIX';pr.get_devices()
        for d in pr.devices:d.use=(d.type!='CPU')
        s.cycles.device='GPU'
    except Exception as e:print('GPU_FAIL',e)
    return cam,cd,items
def shot(kit,cam,cd,path,loc,tgt,lens=60,size=(1400,950),samples=48):
    s=kit.scene;s.cycles.samples=samples;cam.location=loc;cd.lens=lens;cd.clip_start=.05;cd.clip_end=500;cam.rotation_euler=(Vector(tgt)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    s.render.resolution_x,s.render.resolution_y=size;s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
# ---------------- export ----------------
def export_part(root_obj,path,y_forward=False):
    """FBX of one part: the root empty's children (meshes; curves/text converted). Origin = part pivot; +X forward, +Z up."""
    bpy.ops.object.select_all(action='DESELECT')
    kids=[o for o in bpy.data.objects if o.parent==root_obj]
    for o in kids:
        if o.type in('CURVE','FONT'):
            bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o.select_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.data.objects:
        if o.parent==root_obj and o.type=='MESH':o.select_set(True)
    root_obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,axis_forward='X',axis_up='Z',object_types={'MESH','EMPTY'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',path_mode='COPY',embed_textures=False)
def stats(kit):
    objs=[o for o in kit.col.objects if o.type=='MESH'];return dict(objects=len(objs),polygons=sum(len(o.data.polygons) for o in objs))

class WinSet:
    """Recessed window units on a wall face whose outward normal is o*Y (o=-1: front/street side). Collects boxes per material group, flush() makes 4 merged objects.
    back = dark panel just in front of the wall, so the glass reads as glass and not as the wall colour; frame/mullions have real depth; stone sill + head."""
    def __init__(s):s.back=[];s.glass=[];s.frame=[];s.stone=[]
    def add(s,cx,cz,w,h,y_face=0.0,o=-1,mull=1,trans=1,sill=True,head=True,d=.09,t=.07):
        y=lambda off:y_face+o*off
        s.back.append((cx,y(.012),cz,w,.02,h));s.glass.append((cx,y(.035),cz,w-.1,.01,h-.1))
        s.frame+=[(cx,y(d/2),cz+h/2-t/2,w,d,t),(cx,y(d/2),cz-h/2+t/2,w,d,t),(cx-w/2+t/2,y(d/2),cz,t,d,h),(cx+w/2-t/2,y(d/2),cz,t,d,h)]
        for j in range(1,mull+1):s.frame.append((cx-w/2+w*j/(mull+1),y(d/2),cz,t*.7,d*.9,h))
        for j in range(1,trans+1):s.frame.append((cx,y(d/2),cz-h/2+h*(.62 if trans==1 else j/(trans+1)),w,d*.9,t*.7))
        if sill:s.stone.append((cx,y(.10),cz-h/2-.04,w+.30,.20,.08))
        if head:s.stone.append((cx,y(.07),cz+h/2+.05,w+.20,.14,.10))
    def flush(s,kit,name,mats):
        out=[]
        for key,items,b in (('back',s.back,0),('glass',s.glass,0),('frame',s.frame,.002),('stone',s.stone,.004)):
            if items:out.append(boxes(kit,name+'_'+key,items,mats[key],b))
        return out
