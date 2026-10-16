"""Reusable city & industrial building kit (Blender 5.x; metres, Z up).
Self-contained module: works both inside the city-building-modeling skill package (scripts/)
and inside tools/pipeline/.
Distilled from power_plant_kit_v01.py + build_city_power_plant_v01.py (a01-a09 lessons).
Designed so smaller models can build complex, multi-part architectural and industrial compounds
declaratively without manual 3D matrix math or bmesh boilerplate.

Core guarantees baked into this kit:
1. Per-material bmesh batching (Geo.flush): thousands of ribs, rails, louvers, and rungs become
   one object per material with 38-deg auto-sharp edges (flat boxes, smooth cylinders).
2. Wall-local 2D coordinate frames (WF): place windows, doors, louvers, pilasters, and profiled
   cladding ribs (auto-skipping openings) in (u along wall, v height, w outward) coordinates.
3. a09 anti-bug fixes built in:
   - mesh_text() converts 3D FONT curves to MESH immediately so instance() never drops signage.
   - ring_platform() adds inward return handrails on both sides of the ladder gap.
   - split_walkway() leaves clean framed gaps and pipe sleeves around vertical risers.
   - setup_site_review_context() sets clip_end=6000, 8km grass/street context, and replaces
     camera background rays with clean sky so HDRI buildings/crosses never photobomb renders.
   - place_shared_vegetation() imports shared FBX trees/shrubs when available, and automatically
     falls back to procedural trees/shrubs in standalone environments.
"""
import bpy,bmesh,math,sys
from pathlib import Path
from mathutils import Vector,Matrix

_HERE=Path(__file__).resolve().parent
if str(_HERE) not in sys.path:sys.path.insert(0,str(_HERE))

from power_plant_kit_v01 import (
    SMOOTH_DEG,frame,Geo,WF,
    fillet,tube,flange,valve,
    railing,grating,flight,zigzag_stair,ladder,
    louvre_bank,ribbed,
    insulator,string,catenary,
    lattice_column,lattice_beam,instance,
)

# ---------------- procedural material builders ----------------
def grid_mat(n,c,cell=.04,bar=.45,rough=.5,metal=.6):
    m=bpy.data.materials.get(n)
    if m:return m
    m=bpy.data.materials.new(n);m.use_nodes=True;nt=m.node_tree;b=nt.nodes['Principled BSDF'];tc=nt.nodes.new('ShaderNodeTexCoord')
    br=nt.nodes.new('ShaderNodeTexBrick');br.offset=0;br.inputs['Scale'].default_value=1/cell;br.inputs['Mortar Size'].default_value=bar*cell*.5;br.inputs['Brick Width'].default_value=1.0;br.inputs['Row Height'].default_value=.5
    br.inputs['Color1'].default_value=(.07,.075,.08,1);br.inputs['Color2'].default_value=(.07,.075,.08,1);br.inputs['Mortar'].default_value=(*c,1)
    nt.links.new(tc.outputs['Object'],br.inputs['Vector']);nt.links.new(br.outputs['Color'],b.inputs['Base Color'])
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.6;bump.inputs['Distance'].default_value=.01;nt.links.new(br.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],b.inputs['Normal'])
    b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m

def noise_mat(n,c1,c2,scale=40,rough=.9,bump=.15,metal=0.):
    m=bpy.data.materials.get(n)
    if m:return m
    m=bpy.data.materials.new(n);m.use_nodes=True;nt=m.node_tree;b=nt.nodes['Principled BSDF'];tc=nt.nodes.new('ShaderNodeTexCoord')
    nz=nt.nodes.new('ShaderNodeTexNoise');nz.inputs['Scale'].default_value=scale;nz.inputs['Detail'].default_value=6;nt.links.new(tc.outputs['Object'],nz.inputs['Vector'])
    ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*c1,1);ramp.color_ramp.elements[1].color=(*c2,1);nt.links.new(nz.outputs['Fac'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],b.inputs['Base Color'])
    bp=nt.nodes.new('ShaderNodeBump');bp.inputs['Strength'].default_value=bump;bp.inputs['Distance'].default_value=.02;nt.links.new(nz.outputs['Fac'],bp.inputs['Height']);nt.links.new(bp.outputs['Normal'],b.inputs['Normal'])
    b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m

def standard_palette(C,prefix='BLD',accent=(.012,.11,.44)):
    """Calibrated non-blowing-out material palette (a01-a08 albedo fixes included)."""
    p=lambda s:f'{prefix}_{s}'
    return dict(
        CLAD=C.mat(p('Cladding'),(.55,.57,.59),.40),
        CLAD2=C.mat(p('CladdingLight'),(.50,.52,.54),.42),
        ACCENT=C.mat(p('AccentBand'),accent,.38),
        ROOF=C.mat(p('RoofSheet'),(.48,.51,.54),.30,.55),
        MEMB=C.mat(p('RoofMembrane'),(.36,.37,.38),.85),
        CONC=C.granite(p('Concrete'),slab=(3.0,1.5),joint=.0025,col1=(.50,.50,.48),col2=(.47,.47,.455),rough=.86),
        PLINTH=C.mat(p('Plinth'),(.42,.42,.40),.88),
        GLASS=C.mat(p('Glass'),(.045,.07,.09),.06,0,spec=.7),
        ALU=C.mat(p('Aluminium'),(.62,.64,.66),.30,1.0),
        DOOR=C.mat(p('DoorSteel'),(.33,.35,.37),.45,.3),
        STEEL=C.mat(p('SteelGrey'),(.40,.42,.44),.46,.25),
        STRUCT=C.mat(p('SteelStructure'),(.24,.26,.28),.50,.35),
        YEL=C.mat(p('SafetyYellow'),(.80,.53,.02),.45),
        GASY=C.mat(p('GasYellow'),(.84,.62,.04),.36),
        RAILB=C.mat(p('RailBlue'),(.025,.17,.50),.42),
        GRATE=grid_mat(p('Grating'),(.30,.32,.33)),
        LOUV=C.mat(p('Louvre'),(.38,.40,.41),.45,.4),
        DARK=C.mat(p('DarkInterior'),(.010,.011,.013),.9),
        GALV=C.mat(p('Galvanized'),(.56,.58,.59),.40,.85),
        INSUL=C.mat(p('PipeInsulationJacket'),(.70,.72,.74),.30,1.0),
        TRAN=C.mat(p('EquipmentPaint'),(.36,.42,.40),.42,.1),
        INS=C.mat(p('InsulatorSilicone'),(.19,.20,.21),.40),
        BUS=C.mat(p('Busbar'),(.74,.75,.76),.25,1.0),
        RED=C.mat(p('ObstructionLight'),(1.0,.04,.02),.3,0,0,4.0),
        REDP=C.mat(p('RedPaint'),(.50,.02,.02),.45),
        WHITE=C.mat(p('WhiteTrim'),(.80,.80,.79),.55),
        RUB=C.mat(p('Rubber'),(.02,.02,.022),.85),
        GRAVEL=noise_mat(p('Gravel'),(.17,.17,.165),(.42,.41,.39),45,.95,.5),
        ASPH=noise_mat(p('Asphalt'),(.050,.053,.056),(.085,.088,.090),18,.92,.05),
        PAVE=C.granite(p('Paving'),slab=(3.0,3.0),joint=.003,col1=(.30,.30,.29),col2=(.285,.285,.275),rough=.88),
        MARKW=C.mat(p('MarkingWhite'),(.78,.78,.76),.7),
        MARKY=C.mat(p('MarkingYellow'),(.75,.55,.05),.7),
        LAWN=noise_mat(p('Lawn'),(.07,.11,.035),(.13,.19,.06),30,.95,.2),
        STONE=C.granite(p('FacadeStone'),slab=(1.2,.6),joint=.004,col1=(.52,.53,.53),col2=(.49,.50,.50),rough=.62),
        WDARK=C.mat(p('WindowFrameDark'),(.10,.11,.12),.35,.6),
        JOINT=C.mat(p('PanelJoint'),(.27,.27,.26),.9),
        FENCE=C.granite(p('FencePanel'),slab=(3.0,1.1),joint=.003,col1=(.60,.60,.585),col2=(.58,.58,.565),rough=.85),
        LEAF=C.mat(p('RealLeaves'),(.065,.15,.035),.86),
        BARK=C.granite(p('RealBark'),slab=(.08,.6),joint=.001,col1=(.11,.065,.033),col2=(.09,.06,.028),rough=.92),
    )

# ---------------- facade & architectural openings (on a WF wall frame) ----------------
def wall_poly(g,m,F,uv,w0,w1):
    """Extrude an arbitrary 2D (u,v) polygon on wall frame F between depths w0 and w1 (e.g. sloped gable bands)."""
    g.loft(m,[F.p(u,v,w0) for u,v in uv],[F.p(u,v,w1) for u,v in uv])

def ribbon_window(g,F,u0,u1,v0,v1,m_glass,m_frame,mull=1.5,w0=0.):
    """Horizontal ribbon window with head flashing, projecting sill, vertical mullions, and transom."""
    F.box(g,m_glass,(u0+u1)/2,(v0+v1)/2,-.07+w0,u1-u0,v1-v0,.02)
    F.box(g,m_frame,(u0+u1)/2,v1+.05,.01+w0,u1-u0+.12,.10,.14)
    F.box(g,m_frame,(u0+u1)/2,v0-.05,.05+w0,u1-u0+.12,.10,.22)
    n=max(1,round((u1-u0)/mull))
    for i in range(n+1):F.box(g,m_frame,u0+i*(u1-u0)/n,(v0+v1)/2,-.02+w0,.06,v1-v0,.10)
    if v1-v0>1.2:F.box(g,m_frame,(u0+u1)/2,v0+(v1-v0)*.55,-.03+w0,u1-u0,.05,.08)

def punched_window(g,F,u,v,w,h,m_stone,m_dark,m_glass,m_frame,mull=1):
    """Punched office/civic window: stone surround + sill, dark interior backing, glass, dark mullions & transom."""
    for du,dv,dw,dh in ((-w/2-.075,h/2,.15,h+.3),(w/2+.075,h/2,.15,h+.3)):F.box(g,m_stone,u+du,v+dv,.06,dw,dh,.12)
    F.box(g,m_stone,u,v+h+.075,.06,w+.3,.15,.12);F.box(g,m_stone,u,v-.06,.13,w+.4,.12,.26)
    F.box(g,m_dark,u,v+h/2,.004,w,h,.008);F.box(g,m_glass,u,v+h/2,.03,w-.08,h-.08,.01)
    for a,b,c_,d_ in ((u,v+.03,w,.06),(u,v+h-.03,w,.06),(u-w/2-.03,v+h/2,.06,h),(u+w/2-.03,v+h/2,.06,h),(u,v+h*.72,w,.05)):
        F.box(g,m_frame,a,b,.045,c_,d_,.05)
    for j in range(1,mull+1):F.box(g,m_frame,u-w/2+w*j/(mull+1),v+h*.36,.045,.05,h*.72,.05)

def person_door(g,F,u,m_door,m_frame,m_light,w=1.0,h=2.2,canopy=True):
    """Personnel door with frame, handle, bulkhead light, and optional tie-rod canopy."""
    F.box(g,m_door,u,h/2,.02,w,h,.04);F.box(g,m_frame,u,h+.04,.02,w+.16,.08,.10)
    for s in (-1,1):F.box(g,m_frame,u+s*(w/2+.04),h/2,.02,.08,h,.10)
    F.box(g,m_frame,u+w*.35,1.05,.05,.03,.18,.05)
    if canopy:
        F.box(g,m_frame,u,h+.45,.55,w+1.0,.08,1.1)
        for s in (-1,1):g.beam(m_frame,F.p(u+s*(w/2+.4),h+.48,1.05),F.p(u+s*(w/2+.4),h+1.2,0),.03,.03)
    F.box(g,m_light,u,h+.25,.12,.32,.12,.14)

def roller_door(g,F,u0,u1,h,m_door,m_frame,m_hood):
    """Industrial roll-up equipment door with horizontal slats, side guides, and top coil hood."""
    F.box(g,m_door,(u0+u1)/2,h/2,.02,u1-u0,h,.04)
    for i in range(int(h/.11)):F.box(g,m_door,(u0+u1)/2,.06+i*.11,.045,u1-u0,.02,.02)
    for uu in (u0-.08,u1+.08):F.box(g,m_frame,uu,h/2,.04,.16,h,.14)
    F.box(g,m_hood,(u0+u1)/2,h+.35,.25,u1-u0+.5,.7,.55)

def downpipe(g,m_pipe,m_clip,F,u,v0,v1,r=.055,w=.08,clip_step=3.0):
    """Rainwater downpipe along wall frame F at coordinate u, with wall brackets every clip_step."""
    g.cyl(m_pipe,F.p(u,v0,w),F.p(u,v1,w),r,12)
    z=v0+1.2
    while z<v1-.5:
        F.box(g,m_clip,u,z,w/2,r*2.4,.04,w);z+=clip_step

# ---------------- industrial platforms, fences & converted mesh text (a09 safe) ----------------
def ring_platform(g,m_grate,m_struct,m_rail,c,z,r0,r1,seg=24,gap=(-.32,.32)):
    """Annular grating platform on a cylinder/stack with brackets, toe ring, and inward return rails at the ladder gap."""
    c=Vector(c)
    for k in range(seg):
        a=(k+.5)*2*math.pi/seg
        if gap and (gap[0]<=a<=gap[1] or gap[0]<=a-2*math.pi<=gap[1]):continue
        g.box(m_grate,c+Vector((math.cos(a)*(r0+r1)/2,math.sin(a)*(r0+r1)/2,z-.03)),((r1-r0),2*math.pi*r1/seg+.02,.06),rz=a)
        if k%2==0:g.beam(m_struct,c+Vector((math.cos(a)*r0,math.sin(a)*r0,z-1.0)),c+Vector((math.cos(a)*r1,math.sin(a)*r1,z-.08)),.12,.12)
    pts=[c+Vector((math.cos(a)*(r1-.05),math.sin(a)*(r1-.05),z)) for a in [gap[1]+(2*math.pi-(gap[1]-gap[0]))*i/32 for i in range(33)]] if gap else [c+Vector((math.cos(2*math.pi*i/32)*(r1-.05),math.sin(2*math.pi*i/32)*(r1-.05),z)) for i in range(33)]
    if gap:
        pts=[c+Vector((math.cos(gap[1])*r0,math.sin(gap[1])*r0,z))]+pts+[c+Vector((math.cos(gap[0])*r0,math.sin(gap[0])*r0,z))]
    railing(g,m_rail,pts,step=1.4,closed=False)
    g.torus(m_struct,c+Vector((0,0,z-.06)),r1,.05,(0,0,1),40,4)

def split_walkway(g,m_grate,m_struct,m_sleeve,x,spans_y,z,w=1.2,risers=()):
    """Grating walkway along Y split into clean spans [(y0,y1),...] so vertical risers never pierce grating;
    adds end trim beams and circular sleeve collars at each riser (x_r, y_r, r_r)."""
    for y0w,y1w in spans_y:
        grating(g,m_grate,m_struct,(x,(y0w+y1w)/2,z),(w,y1w-y0w))
        for yy in (y0w,y1w):g.beam(m_struct,(x-w/2,yy,z-.06),(x+w/2,yy,z-.06),.08,.12)
    for xr,yr,rr in risers:
        g.cyl(m_sleeve,(xr,yr,z-.08),(xr,yr,z+.10),rr+.05,12)

def wire_fence(g,pts,h,mpost,mmesh,step=2.5,cell=.10,post_m=None):
    """Welded wire mesh security fence along polyline pts."""
    P=[Vector((p[0],p[1],0)) for p in pts]
    for a,b in zip(P[:-1],P[1:]):
        d=b-a;L=d.length;n=max(1,round(L/step));u=d.normalized();rz=math.atan2(u.y,u.x)
        for k in range(n+1):q=a+d*(k/n);g.box(post_m or mpost,(q.x,q.y,h/2+.05),(.08,.08,h+.1))
        for k in range(n):
            q0=a+d*(k/n);q1=a+d*((k+1)/n);c=(q0+q1)/2;lp=(q1-q0).length-.08
            for z in (.15,h-.05):g.box(mpost,(c.x,c.y,z),(lp,.04,.04),rz)
            for j in range(1,int(lp/cell)):p=q0+u*(.05+j*cell);g.box(mmesh,(p.x,p.y,(h+.15)/2),(.006,.006,h-.2))
            for j in range(1,int((h-.25)/(cell*2))):g.box(mmesh,(c.x,c.y,.15+j*cell*2),(lp,.006,.006),rz)

def mesh_text(kit,C,name,body,loc,size,m,rot=(math.pi/2,0,0),extrude=.01,font='C:/Windows/Fonts/msyhbd.ttc',align='CENTER'):
    """Create 3D text and immediately convert to MESH so linked instances never lose text objects (a09 lesson)."""
    o=C.text(kit,name,body,loc,size,m,rot=rot,extrude=extrude,font=font,align=align)
    bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o.select_set(False)
    return o

# ---------------- site layout helpers (walls, roads, markings, lawns, props, greenery) ----------------
def precast_wall(g,m_fence,m_joint,a,b,bay=3.0,h=2.3):
    """Precast concrete perimeter wall with capped pilasters, coping, and horizontal panel joint."""
    a=Vector((a[0],a[1],0));b=Vector((b[0],b[1],0));d=b-a;L=d.length;n=max(1,round(L/bay));rz=math.atan2(d.y,d.x)
    for k in range(n+1):
        q=a+d*(k/n);g.box(m_fence,(q.x,q.y,(h+.25)/2),(.36,.36,h+.25),rz);g.box(m_fence,(q.x,q.y,h+.30),(.46,.46,.10),rz)
    for k in range(n):
        q0=a+d*(k/n);q1=a+d*((k+1)/n);c=(q0+q1)/2;lp=(q1-q0).length-.36
        g.box(m_fence,(c.x,c.y,h/2),(lp,.12,h),rz);g.box(m_fence,(c.x,c.y,h+.06),(lp,.24,.08),rz);g.box(m_joint,(c.x,c.y,h/2),(lp,.13,.02),rz)

def road_dashes(g,m_mark,a,b,w=.15,dash=3.,gap=3.,z=.0225):
    """Dashed centreline marking between 2D/3D points a and b."""
    a=Vector((a[0],a[1],0));b=Vector((b[0],b[1],0));d=b-a;L=d.length;u=d.normalized();rz=math.atan2(u.y,u.x);t=0.
    while t<L:
        e=min(t+dash,L);c=a+u*((t+e)/2);g.box(m_mark,(c.x,c.y,z),(e-t,w,.005),rz);t+=dash+gap

def crosswalk(g,m_mark,x,y0,n_stripes=6,w=2.6,stripe=.45,pitch=1.0,z=.023):
    """Pedestrian zebra crossing across an E-W road."""
    for i in range(n_stripes):g.box(m_mark,(x,y0+i*pitch,z),(w,stripe,.005))

def curbed_lawn(g,m_lawn,m_curb,x0,y0,x1,y1):
    """Raised grass bed with concrete curb stones on all four sides."""
    g.box(m_lawn,((x0+x1)/2,(y0+y1)/2,.06),(x1-x0,y1-y0,.12))
    for c,dd in ((((x0+x1)/2,y0,.09),(x1-x0+.15,.15,.18)),(((x0+x1)/2,y1,.09),(x1-x0+.15,.15,.18)),
                 ((x0,(y0+y1)/2,.09),(.15,y1-y0,.18)),((x1,(y0+y1)/2,.09),(.15,y1-y0,.18))):
        g.box(m_curb,c,dd)

def parking_row(g,m_mark,m_conc,x0,y_centre,count,bay_w=2.5,bay_l=5.3,yaw=90.0,slots_out=None):
    """Row of perpendicular parking bays along X with painted lines, back line, and concrete wheel stops."""
    for i in range(count+1):
        x=x0+bay_w*i;g.box(m_mark,(x,y_centre,.0225),(.12,bay_l,.005))
    g.box(m_mark,(x0+bay_w*count/2,y_centre+bay_l/2-.05,.0225),(bay_w*count,.12,.005))
    for i in range(count):
        cx=x0+bay_w*(i+.5);g.box(m_conc,(cx,y_centre+bay_l/2-.7,.075),(1.6,.15,.15))
        if slots_out is not None:
            slots_out.append(dict(id=len(slots_out),position=[round(cx,3),round(y_centre,3),.02],width=bay_w,length=bay_l,yaw=yaw))

def yard_light(g,m_conc,m_pole,m_head,m_lens,x,y,aim_xy=(0,60),h=8.5):
    """Tapered galvanized yard light pole on concrete pedestal, aimed toward aim_xy."""
    g.box(m_conc,(x,y,.25),(.45,.45,.5));g.cyl(m_pole,(x,y,.5),(x,y,h),.10,12,r1=.065)
    d=Vector((aim_xy[0]-x,aim_xy[1]-y,0)).normalized()*.9;rz=math.atan2(d.y,d.x)
    g.cyl(m_pole,(x,y,h-.1),(x+d.x,y+d.y,h+.05),.04,8)
    g.box(m_head,(x+d.x,y+d.y,h),(.6,.28,.1),rz);g.box(m_lens,(x+d.x,y+d.y,h-.06),(.5,.22,.02),rz)

def fire_hydrant(g,m_red,x,y):
    """Standard outdoor red pillar fire hydrant."""
    g.cyl(m_red,(x,y,0),(x,y,.75),.1,14);g.sphere(m_red,(x,y,.78),.11,12,6)
    g.cyl(m_red,(x-.18,y,.55),(x+.18,y,.55),.05,10);g.cyl(m_red,(x,y-.18,.55),(x,y+.18,.55),.05,10)

def place_shared_vegetation(kit,C,root_dir,label,rel_fbx,height,placements,parent,m_bark,m_leaf,tree=False,out_list=None):
    """Import shared game-ready tree/shrub FBX once and link-duplicate at placements;
    falls back to procedural tree/shrub geometry if external FBX is not present."""
    src=Path(root_dir)/rel_fbx if root_dir else Path(rel_fbx)
    if not src.exists():
        g=Geo(kit,label+'_proc')
        if tree:
            g.cyl(m_bark,(0,0,0),(0,0,height*.52),height*.028,10,r1=height*.014)
            for dx,dy,dz,rx,ry,rz in ((0,0,height*.68,height*.24,height*.22,height*.22),
                                      (height*.10,height*.06,height*.58,height*.18,height*.17,height*.16),
                                      (-height*.11,-height*.05,height*.60,height*.18,height*.17,height*.15)):
                g.sphere(m_leaf,(dx,dy,dz),1.0,12,8,(rx,ry,rz))
        else:
            g.sphere(m_leaf,(0,0,height*.45),1.0,10,6,(height*.55,height*.50,height*.45))
        sources=g.flush()
        for s in sources:s.parent=None
        new=[]
    else:
        before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(src));new=list(set(bpy.data.objects)-before)
        meshes=[o for o in new if o.type=='MESH' and 'Flowers' not in o.name];mws={o.name:o.matrix_world.copy() for o in meshes}
        pts=[mws[o.name]@Vector(c) for o in meshes for c in o.bound_box]
        lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
        scale=height/(hi.z-lo.z);offset=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z));sources=[]
        for ob in meshes:
            ob.data.transform(Matrix.Scale(scale,4)@Matrix.Translation(offset)@mws[ob.name]);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
            ob.data.materials.clear();ob.data.materials.append(m_bark if tree and 'Wood' in ob.name else m_leaf);sources.append(ob)
        if tree:
            try:
                import hospital_landscape_v02
                sources.append(hospital_landscape_v02.add_crown(kit,C,[ob for ob in sources if 'Wood' in ob.name],height,m_leaf))
            except Exception:pass
    for i,(x,y,z) in enumerate(placements):
        ang=(i*2.399+len(label))%(2*math.pi)
        for ob in sources:
            q=bpy.data.objects.new(label+'_'+str(i)+'_'+ob.name,ob.data);kit.col.objects.link(q);q.parent=parent;q.location=(x,y,z);q.rotation_euler.z=ang
            if tree:q.scale=(.86,1.,1.12)[i%3]*Vector((1,1,1))
        if out_list is not None:
            out_list.append(dict(asset=str(rel_fbx),position=[x,y,z],height=height*((.86,1.,1.12)[i%3] if tree else 1),yaw=ang))
    for ob in new+[s for s in sources if s not in new]:
        if ob.name in bpy.data.objects and ob.parent is None and not ob.name.startswith(label+'_'):bpy.data.objects.remove(ob,do_unlink=True)

# ---------------- camera, studio & review context (a09 safe) ----------------
def orb(az,el,D,t):
    t=Vector(t);a,e=math.radians(az),math.radians(el)
    return tuple(t+Vector((math.cos(a)*math.cos(e),math.sin(a)*math.cos(e),math.sin(e)))*D)

def shot_building(kit,cam,cd,path,loc,tgt,lens=40,size=(1400,950),samples=32,clip_end=6000):
    s=kit.scene;s.cycles.samples=samples;cam.location=loc;cd.lens=lens;cd.clip_start=.05;cd.clip_end=clip_end
    cam.rotation_euler=(Vector(tgt)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    s.render.resolution_x,s.render.resolution_y=size;s.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)

def setup_site_review_context(kit,m_lawn,m_asph,m_mark,studio_items,ext=4000,street_y=(-16.,-.4)):
    """Add review-only grass horizon, public street, and clean sky camera ray override (never exported to parts)."""
    def ctx_plane(name,m,x0,y0,x1,y1,z):
        me=bpy.data.meshes.new(name);me.from_pydata([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)],[],[(0,1,2,3)]);me.materials.append(m)
        ob=bpy.data.objects.new(name,me);kit.col.objects.link(ob);return ob
    ctx_plane('REVIEW_context_grass',m_lawn,-ext,-ext,ext,ext,-.008)
    ctx_plane('REVIEW_context_street',m_asph,-ext,street_y[0],ext,street_y[1],-.004)
    ym=(street_y[0]+street_y[1])/2
    for i in range(-120,120):ctx_plane('REVIEW_context_dash%d'%i,m_mark,i*6.,ym-.1,i*6.+3.,ym+.1,-.002)
    for it in studio_items:
        if it.name=='REVIEW_floor':it.hide_render=True
    if 'ShaderNodeLightPath' not in [n.bl_idname for n in kit.scene.world.node_tree.nodes]:
        wn=kit.scene.world.node_tree.nodes;wl=kit.scene.world.node_tree.links
        bg_cam=wn.new('ShaderNodeBackground');bg_cam.inputs[0].default_value=(.58,.66,.75,1);bg_cam.inputs[1].default_value=1.0
        lp=wn.new('ShaderNodeLightPath');mx=wn.new('ShaderNodeMixShader')
        wl.new(lp.outputs['Is Camera Ray'],mx.inputs['Fac']);wl.new(wn.get('Background').outputs[0],mx.inputs[1]);wl.new(bg_cam.outputs[0],mx.inputs[2])
        wl.new(mx.outputs[0],wn.get('World Output').inputs['Surface'])
