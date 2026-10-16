"""Gas-fired combined-cycle power station (2 units) for the city game, built as separate parts + one assembly.
Reference: art/references/city/power-plant-v01/concept-B-gas.png (user chose B, 2026-10-14), part sheets art/references/city/power-plant-v01/parts/sheet-*.png
Lock (A0 audit, structure, layout, dimensions, material truth table): art/references/city/power-plant-v01/lock.md
Metres. Site: origin at the middle of the street edge, X right along the street, Y into the site, Z up; the public street (Y<0) is not part of the asset.
Every part prototype is built at its own pivot, rendered alone, written to parts/<id>.blend, then placed in the assembly as linked duplicates.
Env: PP_VERSION, PP_PARTS (comma list of ids like PP01,PP04 or all), PP_VIEWS (all / comma list), PP_SAMPLES, PP_ASSEMBLY (1/0).
"""
import bpy,bmesh,math,os,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/pipeline'))
import city_kit_common as C
import power_plant_kit_v01 as P
from record_modeling_step import append_event
PARAMS={}
def E(n,d):
    v=type(d)(os.environ.get(n,d));PARAMS[n]=v;return v
VER=E('PP_VERSION','a09');ONLY=E('PP_PARTS','all');VIEWS=E('PP_VIEWS','all');SAMPLES=E('PP_SAMPLES',32);ASM=E('PP_ASSEMBLY',1)
O=R/'art/assets/authored/city/power-plant-v01'/VER;O.mkdir(parents=True,exist_ok=True)
EP='power-plant-v01';AID='power-plant-'+VER
REF=R/'art/references/city/power-plant-v01'
append_event(EP,dict(kind='action_started',action_id=AID,reference=[str(REF/'concept-B-gas.png')],operation=dict(script=str(Path(__file__)),params=PARAMS)))
K=C.Kit('POWER_PLANT');PROTOS={}
def want(pid):return ONLY=='all' or pid in ONLY.split(',')

# ---------------- materials (lock.md material truth table; clean, maintained, not weathered) ----------------
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
CLAD=C.mat('PP_Cladding',(.55,.57,.59),.40)
CLAD2=C.mat('PP_CladdingLight',(.50,.52,.54),.42)
BLUE=C.mat('PP_BlueBand',(.012,.11,.44),.38)
ROOF=C.mat('PP_RoofSheet',(.48,.51,.54),.30,.55)
MEMB=C.mat('PP_RoofMembrane',(.36,.37,.38),.85)
CONC=C.granite('PP_Concrete',slab=(3.0,1.5),joint=.0025,col1=(.50,.50,.48),col2=(.47,.47,.455),rough=.86)
PLINTH=C.mat('PP_Plinth',(.42,.42,.40),.88)
GLASS=C.mat('PP_Glass',(.045,.07,.09),.06,0,spec=.7)
ALU=C.mat('PP_Aluminium',(.62,.64,.66),.30,1.0)
DOOR=C.mat('PP_DoorSteel',(.33,.35,.37),.45,.3)
STEEL=C.mat('PP_SteelGrey',(.40,.42,.44),.46,.25)
STRUCT=C.mat('PP_SteelStructure',(.24,.26,.28),.50,.35)
YEL=C.mat('PP_SafetyYellow',(.80,.53,.02),.45)
GASY=C.mat('PP_GasYellow',(.84,.62,.04),.36)
RAILB=C.mat('PP_RailBlue',(.025,.17,.50),.42)
GRATE=grid_mat('PP_Grating',(.30,.32,.33))
LOUV=C.mat('PP_Louvre',(.38,.40,.41),.45,.4)
DARK=C.mat('PP_DarkInterior',(.010,.011,.013),.9)
GALV=C.mat('PP_Galvanized',(.56,.58,.59),.40,.85)
INSUL=C.mat('PP_PipeInsulationJacket',(.70,.72,.74),.30,1.0)
TRAN=C.mat('PP_TransformerPaint',(.36,.42,.40),.42,.1)
INS=C.mat('PP_InsulatorSilicone',(.19,.20,.21),.40)
BUS=C.mat('PP_Busbar',(.74,.75,.76),.25,1.0)
RED=C.mat('PP_ObstructionLight',(1.0,.04,.02),.3,0,0,4.0)
REDP=C.mat('PP_RedPaint',(.50,.02,.02),.45)
WHITE=C.mat('PP_WhiteTrim',(.80,.80,.79),.55)
RUB=C.mat('PP_Rubber',(.02,.02,.022),.85)
GRAVEL=noise_mat('PP_Gravel',(.17,.17,.165),(.42,.41,.39),45,.95,.5)
ASPH=noise_mat('PP_Asphalt',(.050,.053,.056),(.085,.088,.090),18,.92,.05)
PAVE=C.granite('PP_Paving',slab=(3.0,3.0),joint=.003,col1=(.40,.40,.385) if VER<'a08' else (.30,.30,.29),col2=(.385,.385,.37) if VER<'a08' else (.285,.285,.275),rough=.88)
MARKW=C.mat('PP_MarkingWhite',(.78,.78,.76),.7)
MARKY=C.mat('PP_MarkingYellow',(.75,.55,.05),.7)
LAWN=noise_mat('PP_Lawn',(.07,.11,.035),(.13,.19,.06),30,.95,.2)
STONE=C.granite('PP_FacadeStone',slab=(1.2,.6),joint=.004,col1=(.52,.53,.53),col2=(.49,.50,.50),rough=.62)
WDARK=C.mat('PP_WindowFrameDark',(.10,.11,.12),.35,.6)
JOINT=C.mat('PP_PanelJoint',(.27,.27,.26),.9)
FANB=C.mat('PP_FanBladeGRP',(.30,.32,.33),.35)
FENCE=C.granite('PP_FencePanel',slab=(3.0,1.1),joint=.003,col1=(.60,.60,.585),col2=(.58,.58,.565),rough=.85)

# ---------------- helpers ----------------
def part(pid,name,**props):
    r=K.part(pid+'_'+name,part_id=pid,**props);PROTOS[pid]=r;return r
def G(pid):return P.Geo(K,pid)
def orb(az,el,D,t):
    t=Vector(t);a,e=math.radians(az),math.radians(el);return tuple(t+Vector((math.cos(a)*math.cos(e),math.sin(a)*math.cos(e),math.sin(e)))*D)
CAM=None
def shot_pp(kit,cam,cd,path,loc,tgt,lens=60,size=(1400,950),samples=48):
    s=kit.scene;s.cycles.samples=samples;cam.location=loc;cd.lens=lens;cd.clip_start=.05;cd.clip_end=6000 if VER>='a09' else 500;cam.rotation_euler=(Vector(tgt)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    s.render.resolution_x,s.render.resolution_y=size;s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
def render_part(root,views):
    global CAM
    if CAM is None:
        cam,cd,items=C.studio(K,800)
        for it in items:
            if it.name=='REVIEW_floor':it.location.z=-.012
        if VER>='a09':
            wn=K.scene.world.node_tree.nodes;wl=K.scene.world.node_tree.links
            bg_cam=wn.new('ShaderNodeBackground');bg_cam.inputs[0].default_value=(.58,.66,.75,1);bg_cam.inputs[1].default_value=1.0
            lp=wn.new('ShaderNodeLightPath');mx=wn.new('ShaderNodeMixShader')
            wl.new(lp.outputs['Is Camera Ray'],mx.inputs['Fac']);wl.new(wn.get('Background').outputs[0],mx.inputs[1]);wl.new(bg_cam.outputs[0],mx.inputs[2])
            wl.new(mx.outputs[0],wn.get('World Output').inputs['Surface'])
        CAM=(cam,cd,items)
    cam,cd,items=CAM;cd.type='PERSP'
    mine={root}|{o for o in K.col.objects if o.parent==root}
    for o in K.col.objects:o.hide_render=o not in mine
    for vn,(az,el,D,t,lens) in views.items():
        if VIEWS!='all' and vn not in VIEWS.split(','):continue
        shot_pp(K,cam,cd,O/(root['part_id']+'-'+vn+'.png'),orb(az,el,D,t),t,lens,(1400,950),SAMPLES)
    for o in K.col.objects:o.hide_render=False

# ======================= PP01 turbine hall =======================
HALL_L,HALL_W,HALL_HE,HALL_HR=88.,30.,20.,23.
GT_X=(-8.,20.);ST_X=-32.                     # hall-local machine axes (lock.md: steam turbine at the left end next to the cooling tower)
BAND0,BAND_H=14.2,1.6;WIN_LO=(6.0,7.5);WIN_HI=(12.45,13.95)
def ribbon(g,F,u0,u1,v0,v1,mull=1.5,frame=ALU,w0=0.):
    """ribbon window; w0 shifts it outward where the wall sheet behind is not cut (gables)"""
    F.box(g,GLASS,(u0+u1)/2,(v0+v1)/2,-.07+w0,u1-u0,v1-v0,.02)
    F.box(g,frame,(u0+u1)/2,v1+.05,.01+w0,u1-u0+.12,.10,.14);F.box(g,frame,(u0+u1)/2,v0-.05,.05+w0,u1-u0+.12,.10,.22)   # head flashing, projecting sill
    n=max(1,round((u1-u0)/mull))
    for i in range(n+1):F.box(g,frame,u0+i*(u1-u0)/n,(v0+v1)/2,-.02+w0,.06,v1-v0,.10)
    if v1-v0>1.2:F.box(g,frame,(u0+u1)/2,v0+(v1-v0)*.55,-.03+w0,u1-u0,.05,.08)
def wall_poly(g,m,F,uv,w0,w1):
    g.loft(m,[F.p(u,v,w0) for u,v in uv],[F.p(u,v,w1) for u,v in uv])
def pdoor(g,F,u,w=1.0,h=2.2,canopy=True):
    F.box(g,DOOR,u,h/2,.02,w,h,.04);F.box(g,ALU,u,h+.04,.02,w+.16,.08,.10)
    for s in (-1,1):F.box(g,ALU,u+s*(w/2+.04),h/2,.02,.08,h,.10)
    F.box(g,ALU,u+w*.35,1.05,.05,.03,.18,.05)
    if canopy:
        F.box(g,ALU,u,h+.45,.55,w+1.0,.08,1.1)
        for s in (-1,1):g.beam(ALU,F.p(u+s*(w/2+.4),h+.48,1.05),F.p(u+s*(w/2+.4),h+1.2,0),.03,.03)
    F.box(g,WHITE,u,h+.25,.12,.32,.12,.14)                                   # bulkhead light over the door
def roller_door(g,F,u0,u1,h):
    F.box(g,DOOR,(u0+u1)/2,h/2,.02,u1-u0,h,.04)
    for i in range(int(h/.11)):F.box(g,DOOR,(u0+u1)/2,.06+i*.11,.045,u1-u0,.02,.02)
    for uu in (u0-.08,u1+.08):F.box(g,ALU,uu,h/2,.04,.16,h,.14)
    F.box(g,CLAD2,(u0+u1)/2,h+.35,.25,u1-u0+.5,.7,.55)                       # coil hood
    F.box(g,YEL,(u0+u1)/2,.05,.08,u1-u0,.10,.04)
def build_hall():
    root=part('PP01','TurbineHall',dimensions=[HALL_L,HALL_W,HALL_HR],gt_axes=list(GT_X),st_axis=ST_X)
    g=G('PP01');L,W,HE,HR=HALL_L,HALL_W,HALL_HE,HALL_HR;x0,x1,y0,y1=-L/2,L/2,-W/2,W/2
    g.box(DARK,(0,0,HE/2),(L-.8,W-.8,HE-.4))                                # dark hall interior seen through the windows
    for c,d in (((0,y0,.6),(L+.12,.30,1.2)),((0,y1,.6),(L+.12,.30,1.2)),((x0,0,.6),(.30,W+.12,1.2)),((x1,0,.6),(.30,W+.12,1.2))):g.box(PLINTH,c,d)
    # long walls
    duct_gaps={-1:[x+L/2 for x in GT_X],1:[x+L/2 for x in GT_X]}
    for y,ns in ((y0,-1),(y1,1)):
        F=P.WF((x0,y,0),0,ns);holes=[]
        doors=[2.6,L-2.6] if ns<0 else [L/2+3.0]
        rd=[(L/2+ST_X-3.5,L/2+ST_X+3.5)] if ns>0 else []
        for u in doors:holes.append((u-.65,u+.65,1.2,2.45))
        for a,b in rd:holes.append((a-.2,b+.2,1.2,8.2))
        lo_w=[];hi_w=[]
        cut=[(c-3.4,c+3.4) for c in duct_gaps[ns]]
        def spans(a,b):
            out=[(a,b)]
            for ca,cb in cut:
                new=[]
                for s0,s1 in out:
                    if cb<=s0 or ca>=s1:new.append((s0,s1))
                    else:
                        if ca>s0:new.append((s0,ca))
                        if cb<s1:new.append((cb,s1))
                out=new
            return [s for s in out if s[1]-s[0]>2]
        for a,b in spans(3.2,L-3.2):holes.append((a,b,WIN_LO[0]-.1,WIN_LO[1]+.1));lo_w.append((a,b))
        hi_w=[(3.2,L-3.2)];holes.append((3.2,L-3.2,WIN_HI[0]-.1,WIN_HI[1]+.1))
        zones=[(1.2,BAND0,CLAD),(BAND0,BAND0+BAND_H,BLUE),(BAND0+BAND_H,HE,CLAD)]
        for v0,v1,m in zones:
            P.ribbed(g,m,F,0,L,v0,v1,skip=holes,base=False)
        # base sheet with openings: horizontal strips between window rows
        rows=sorted({1.2,WIN_LO[0]-.1,WIN_LO[1]+.1,WIN_HI[0]-.1,WIN_HI[1]+.1,BAND0,BAND0+BAND_H,HE})
        for v0,v1 in zip(rows[:-1],rows[1:]):
            m=BLUE if v0>=BAND0-1e-6 and v1<=BAND0+BAND_H+1e-6 else CLAD
            if abs(v0-(WIN_HI[0]-.1))<1e-6:
                F.box(g,m,1.6,(v0+v1)/2,-.04,3.2,v1-v0,.08);F.box(g,m,L-1.6,(v0+v1)/2,-.04,3.2,v1-v0,.08);continue
            if abs(v0-(WIN_LO[0]-.1))<1e-6:
                last=0.
                for a,b in lo_w:
                    F.box(g,m,(last+a)/2,(v0+v1)/2,-.04,a-last,v1-v0,.08);last=b
                F.box(g,m,(last+L)/2,(v0+v1)/2,-.04,L-last,v1-v0,.08);continue
            F.box(g,m,L/2,(v0+v1)/2,-.04,L,v1-v0,.08)
        for a,b in lo_w:ribbon(g,F,a,b,*WIN_LO)
        for a,b in hi_w:ribbon(g,F,a,b,*WIN_HI)
        for u in doors:pdoor(g,F,u)
        for a,b in rd:roller_door(g,F,a,b,8.0)
        for u in (0.,L):F.box(g,ALU,u,(1.2+HE)/2,.02,.22,HE-1.2,.16)                    # corner flashing
        F.box(g,ALU,L/2,HE-.05,.03,L+.2,.12,.12)                                          # eave trim
    # gables: band rises from the front corner to the back eave (sheet-hall panel 3)
    vtop=lambda u:HE+(HR-HE)*(1-abs(u-W/2)/(W/2))
    band=lambda u:BAND0+(HE-BAND_H-BAND0)*u/W
    for x,ns,side in ((x0,1,'L'),(x1,-1,'R')):
        F=P.WF((x,y0,0),math.pi/2,ns);holes=[]
        if side=='L':
            rdu=(W/2+3.0,W/2+9.0);holes.append((rdu[0]-.2,rdu[1]+.2,1.2,8.2));pipe_u=W/2+(-1.0)
        else:rdu=None
        holes.append((7.0,W-7.0,WIN_HI[0]-1.4-.1,WIN_HI[1]-1.4+.1))
        pd=W/2-6.5 if side=='L' else W/2+6.0;holes.append((pd-.65,pd+.65,1.2,2.45))
        wall_poly(g,CLAD,F,[(0,1.2),(W,1.2),(W,HE),(W/2,HR),(0,HE)],-.08,0)
        wall_poly(g,BLUE,F,[(0,band(0)),(W,band(W)),(W,band(W)+BAND_H),(0,band(0)+BAND_H)],0,.004)
        n=int(W/.30)
        for i in range(n):
            u=(i+.5)*W/n;segs=[(1.2,band(u),CLAD),(band(u),band(u)+BAND_H,BLUE),(band(u)+BAND_H,vtop(u),CLAD)]
            for a,b,m in segs:
                cuts=[(a,b)]
                for ua,ub,va,vb in holes:
                    if ua<=u<=ub:
                        nc=[]
                        for s0,s1 in cuts:
                            if vb<=s0 or va>=s1:nc.append((s0,s1))
                            else:
                                if va>s0:nc.append((s0,va))
                                if vb<s1:nc.append((vb,s1))
                        cuts=nc
                for s0,s1 in cuts:
                    if s1-s0>.02:F.box(g,m,u,(s0+s1)/2,.0175,.045,s1-s0,.035)
        ribbon(g,F,7.0,W-7.0,WIN_HI[0]-1.4,WIN_HI[1]-1.4,w0=.075)
        if rdu:roller_door(g,F,rdu[0],rdu[1],8.0)
        pdoor(g,F,pd)
        for a,b in ((-.45,W/2),(W+.45,W/2)):
            ea=HE-.45*(HR-HE)/(W/2)
            g.beam(ALU,F.p(a,ea+.08,.36),F.p(b,HR+.08,.36),.34,.07,up=F.out())      # barge flashing on the roof edge (roof overhangs the gable .35)
    # roof: two slopes, standing seams, ridge cap + ridge ventilator, gutters, downpipes
    ov,og=.45,.35;sl=(HR-HE)/(W/2)
    for s in (-1,1):
        ye=s*(W/2+ov);ze=HE-ov*sl
        A=[(x0-og,ye,ze),(x0-og,0,HR),(x0-og,0,HR+.14),(x0-og,ye,ze+.14)];B=[(x1+og,y,z) for _,y,z in A]
        g.loft(ROOF,A,B)
        n=int((L+2*og)/.5)
        for i in range(n+1):
            x=x0-og+i*(L+2*og)/n;g.beam(ROOF,(x,ye,ze+.17),(x,s*.25,HR+.17),.035,.06)
        g.box(ALU,(0,s*(W/2+ov+.15),ze-.05),(L+2*og,.30,.26))                       # gutter
        for x in ((-43.,43.) if s<0 else (-43.,4.,43.)):                            # corner downpipes (sheet-hall), one more at the back
            yy=s*(W/2+.16);P.tube(g,ALU,[(x,s*(W/2+ov+.15),ze-.15),(x,yy+s*.05,ze-.6),(x,yy,ze-1.2),(x,yy,.55),(x,yy+s*.25,.18)],.075,10,bend=.25)
            for z in range(3,int(ze),3):g.box(ALU,(x,yy-s*.06,z),(.22,.08,.05))
    g.box(ALU,(0,0,HR+.20),(L+2*og,.75,.10));g.box(ALU,(0,0,HR+.12),(L+2*og,1.0,.06))
    VL=72.;g.box(CLAD2,(0,0,HR+.75),(VL,1.0,.9))
    for s in (-1,1):
        for i in range(int(VL/2)):P.louvre_bank(g,LOUV,ALU,P.WF((-VL/2+i*2,s*.52,0),0,s),.1,1.9,HR+.42,HR+1.1,pitch=.12,depth=.06,frame=.04)
    g.box(ALU,(0,0,HR+1.27),(VL+.3,1.5,.10))
    g.flush()
    return root

# ======================= PP02 GT air-inlet filter house =======================
FH=dict(w=12.,d=6.,base=4.0,h=8.0,gap=.8)
def build_filter():
    root=part('PP02','InletFilterHouse',dimensions=[FH['w'],FH['d'],FH['base']+FH['h']])
    g=G('PP02');w,d,zb,h=FH['w'],FH['d'],FH['base'],FH['h'];x0,x1,y0,y1=-w/2,w/2,-d/2,d/2
    g.box(CLAD2,(0,0,zb+h/2),(w,d,h));g.box(ALU,(0,0,zb+h+.06),(w+.12,d+.12,.12))
    for (F,uu) in ((P.WF((x0,y1,zb),0,1),w),(P.WF((x0,y0,zb),math.pi/2,1),d),(P.WF((x1,y0,zb),math.pi/2,-1),d)):
        P.ribbed(g,CLAD2,F,0,uu,0,h,pitch=.6,rib=.04,dr=.03,base=False)
    F=P.WF((x0,y0,zb),0,-1)
    P.ribbed(g,CLAD2,F,0,w,h-2.1,h,pitch=.6,rib=.04,dr=.03,base=False)
    cols=4;hw=(w-.6)/cols
    for row,(v0,v1) in enumerate(((.9,2.85),(3.65,5.6))):
        for c in range(cols):
            u0=.3+c*hw+.08;u1=.3+(c+1)*hw-.08;D=.95;vm=v1-(v1-v0)*.45
            # weather hood (sheet-hall panel 6): sloped top plate, two cheeks, flat bottom, open front behind a bird screen
            V=[F.p(u0,v1,0),F.p(u1,v1,0),F.p(u1,vm,D),F.p(u0,vm,D),F.p(u0,v0,D),F.p(u1,v0,D),F.p(u0,v0,0),F.p(u1,v0,0)]
            g.mesh(CLAD,V,[(0,1,2,3),(0,3,4,6),(1,7,5,2),(6,4,5,7)])
            g.mesh(DARK,[F.p(u0+.03,v0+.02,D-.12),F.p(u1-.03,v0+.02,D-.12),F.p(u1-.03,vm-.02,D-.12),F.p(u0+.03,vm-.02,D-.12),
                         F.p(u0+.03,v0+.02,D-.16),F.p(u1-.03,v0+.02,D-.16),F.p(u1-.03,vm-.02,D-.16),F.p(u0+.03,vm-.02,D-.16)],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
            for k in range(1,int((u1-u0)/.07)):g.beam(GALV,F.p(u0+k*.07,v0,D-.04),F.p(u0+k*.07,vm,D-.04),.006,.006,up=F.out())
            for k in range(1,int((vm-v0)/.07)):g.beam(GALV,F.p(u0,v0+k*.07,D-.04),F.p(u1,v0+k*.07,D-.04),.006,.006,up=F.out())
            g.beam(ALU,F.p(u0,vm,D+.01),F.p(u1,vm,D+.01),.05,.05,up=F.out());g.beam(ALU,F.p(u0,v0,D+.01),F.p(u1,v0,D+.01),.05,.05,up=F.out())
    F.box(g,DOOR,w*.5,h-1.2,.055,.9,1.6,.05)                                  # filter access hatch
    # transition duct into the hall wall (back side)
    g.box(CLAD2,(0,y1+FH['gap']/2+.05,zb+h*.45),(4.2,FH['gap']+.1,3.4));g.box(ALU,(0,y1+.06,zb+h*.45),(4.5,.12,3.7))
    # support frame
    for x in (-w/2+.3,0,w/2-.3):
        for y in (y0+.3,y1-.3):
            g.hbeam(STRUCT,(x,y,.3),(x,y,zb),.3,.3);g.box(CONC,(x,y,.15),(.7,.7,.3));g.box(STRUCT,(x,y,.32),(.45,.45,.03))
        g.hbeam(STRUCT,(x,y0+.3,zb-.15),(x,y1-.3,zb-.15),.25,.3)
    for y in (y0+.3,y1-.3):
        g.hbeam(STRUCT,(-w/2+.3,y,zb-.15),(w/2-.3,y,zb-.15),.25,.3)
        for a,b in ((-w/2+.3,0),(0,w/2-.3)):
            g.beam(STRUCT,(a,y,.6),(b,y,zb-.4),.14,.14,up=(0,1,0));g.beam(STRUCT,(b,y,.6),(a,y,zb-.4),.14,.14,up=(0,1,0))
    for x in (-w/2+.3,w/2-.3):
        g.beam(STRUCT,(x,y0+.3,.6),(x,y1-.3,zb-.4),.14,.14,up=(1,0,0));g.beam(STRUCT,(x,y1-.3,.6),(x,y0+.3,zb-.4),.14,.14,up=(1,0,0))
    # front walkway under the hoods + yellow railing + ladder
    P.grating(g,GRATE,STRUCT,(0,y0-.55,zb),(w,1.1));P.railing(g,YEL,[(x0,y0,zb),(x0,y0-1.1,zb),(x1,y0-1.1,zb),(x1,y0,zb)],h=1.1,step=1.5)
    for x in (x0+.3,0,x1-.3):g.beam(STRUCT,(x,y0,zb-.2),(x,y0-1.1,zb-.2),.12,.2)
    P.ladder(g,YEL,(x1+.05,y0-.55,0),zb,(1,0,0),cage=False)
    g.box(WHITE,(x1-.6,y0-.02,zb+h-.7),(.5,.06,.4))                         # differential-pressure gauge box
    g.flush();return root

# ======================= PP03 electrical annex =======================
def build_annex():
    root=part('PP03','ElectricalAnnex',dimensions=[8,5,4.6])
    g=G('PP03');w,d,h=8.,5.,4.2
    g.box(PLINTH,(0,0,.2),(w+.1,d+.1,.4));g.box(DARK,(0,0,h/2),(w-.3,d-.3,h-.2))
    walls=[(P.WF((-w/2,-d/2,0),0,-1),w),(P.WF((-w/2,d/2,0),0,1),w),(P.WF((-w/2,-d/2,0),math.pi/2,1),d),(P.WF((w/2,-d/2,0),math.pi/2,-1),d)]
    for i,(F,uu) in enumerate(walls):
        holes=[(1.5,2.9,.4,2.6)] if i==0 else ([(1.6,3.4,2.3,3.4)] if i==3 else [])
        F.box(g,CLAD2,uu/2,(h+.4)/2,-.04,uu,h-.4,.08);P.ribbed(g,CLAD2,F,0,uu,.4,h,pitch=.3,skip=holes,base=False)
        F.box(g,ALU,uu/2,h+.25,.0,uu+.1,.5,.10)
    F=walls[0][0];pdoor(g,F,2.2,1.2,2.2)
    P.louvre_bank(g,LOUV,ALU,walls[3][0],1.6,3.4,2.3,3.4,pitch=.11)
    g.box(ALU,(0,0,h+.12),(w+.25,d+.25,.12));g.box(MEMB,(0,0,h+.36),(w-.1,d-.1,.36))
    g.box(GALV,(1.6,1.0,h+.85),(1.1,.7,.6));g.cyl(STRUCT,(1.6,1.0,h+1.16),(1.6,1.0,h+1.18),.28,16)   # roof AC condenser
    g.box(GALV,(-w/2+.6,d/2+.2,h-.4),(.6,.4,.15));g.box(GALV,(-w/2+.6,d/2+.2,h*.5),(.3,.1,h-1.0))       # cable tray riser
    g.flush();return root

# ======================= PP04 heat-recovery steam generator (casing, structure, drums, stair tower) =======================
HR=dict(w=18.,l=20.,z0=1.5,h=27.,col=9.35)
STACK=dict(r=3.0,h=56.,y=HR['l']+3.6)
def build_hrsg():
    root=part('PP04','HRSG',dimensions=[HR['w']+6,HR['l'],HR['h']+4],flow='+Y',inlet_face_y=0.,stack_axis_y=STACK['y'])
    g=G('PP04');w,l,z0,h,cx=HR['w'],HR['l'],HR['z0'],HR['h'],HR['col'];zt=z0+h-1.5
    g.box(STEEL,(0,l/2,(z0+zt)/2),(w,l,zt-z0))
    # vertical stiffeners and horizontal buckstays on the casing (sheet-hrsg: panelled casing)
    for sx in (-1,1):
        F=P.WF((-sx*w/2*0+sx*w/2,0,0),math.pi/2,-sx)
        for i in range(1,int(l/1.0)):F.box(g,STEEL,i*1.0,(z0+zt)/2,.07,.10,zt-z0,.14)
        for zz in [z0+2+3.2*k for k in range(int((zt-z0-2)/3.2)+1)]:F.box(g,STRUCT,l/2,zz,.16,l,.32,.30)
        for i in range(4):F.box(g,DOOR,2.5+i*4.6,z0+4+((i*7)%3)*6,.12,.8,.8,.10)                 # manways
    Fb=P.WF((-w/2,l,0),0,1)
    for i in range(1,int(w/1.0)):Fb.box(g,STEEL,i*1.0,(z0+zt)/2,.07,.10,zt-z0,.14)
    for zz in [z0+2+3.2*k for k in range(int((zt-z0-2)/3.2)+1)]:Fb.box(g,STRUCT,w/2,zz,.16,w,.32,.30)
    # steel structure: columns on piers, girders, roof beams
    ys=[0.,5.,10.,15.,l]
    for sx in (-1,1):
        for y in ys:
            g.box(CONC,(sx*cx,y,.75),(1.1,1.1,1.5));g.hbeam(STRUCT,(sx*cx,y,1.5),(sx*cx,y,zt+1.6),.6,.6)
        for zz in (9.,18.,zt+1.4):g.hbeam(STRUCT,(sx*cx,0,zz),(sx*cx,l,zz),.45,.5)
        for a,b in zip(ys[:-1],ys[1:]):
            g.beam(STRUCT,(sx*cx,a,2.),(sx*cx,b,8.6),.18,.18,up=(1,0,0));g.beam(STRUCT,(sx*cx,b,2.),(sx*cx,a,8.6),.18,.18,up=(1,0,0))
        for y in ys:g.hbeam(STRUCT,(-cx,y,zt+1.4),(cx,y,zt+1.4),.45,.5)
    for y in ys:
        for sx in (-1,1):g.box(STRUCT,(sx*(w/2+.18),y,(z0+zt)/2),(.36,.3,zt-z0))
    for i in range(-4,5):g.box(CONC,(i*2.0,l/2,.6),(1.0,l-1,1.2))                               # casing sole plates on grade beams
    # roof deck, drums, drum houses, risers, safety-valve vents
    zr=zt+1.65;g.box(STEEL,(0,l/2,zr-.03),(2*cx+.6,l+.6,.12))                                   # roof plate deck (sheet-hrsg: grey roof under the drums)
    P.railing(g,YEL,[(-cx-.3,-.3,zr+.03),(cx+.3,-.3,zr+.03),(cx+.3,l+.3,zr+.03),(-cx-.3,l+.3,zr+.03)],closed=True,step=1.8)
    for (yy,r,L) in ((6.0,.95,14.),(11.0,.75,13.),(15.8,1.05,14.)):
        g.lathe(STEEL,[(0,-L/2-.55),(r*.75,-L/2-.4),(r,-L/2),(r,L/2),(r*.75,L/2+.4),(0,L/2+.55)],(0,yy,zr+1.5),28,axis=(1,0,0))
        for sx in (-1,1):g.box(STRUCT,(sx*L*.32,yy,zr+.5),(.5,r*1.6,1.0))
        for k in range(-3,4):g.cyl(INSUL,(k*1.8,yy-r*.3,zr+.05),(k*1.8,yy-r*.3,zr+1.5),.16,10)
        for k in (-1,1):
            g.cyl(STEEL,(k*2.5,yy,zr+1.5+r),(k*2.5,yy,zr+3.6+r),.18,10);g.cyl(STEEL,(k*2.5,yy,zr+3.0+r),(k*2.5,yy,zr+4.2+r),.34,14)
    for yy in (5.5,15.8):
        dh=g.box(CLAD2,(-3.8,yy,zr+1.8),(5.6,4.4,3.6));g.box(ALU,(-3.8,yy,zr+3.65),(5.9,4.7,.12))
        P.louvre_bank(g,LOUV,ALU,P.WF((-6.6,yy-2.2,zr),math.pi/2,1),1.2,3.2,1.2,2.6,pitch=.12)
    # stair tower on +x (sheet-hrsg: zig-zag flights, yellow rails, landings at each level)
    levels=[4.6,9.,13.5,18.,22.5,zr]
    P.zigzag_stair(g,STRUCT,GRATE,YEL,(11.5,7.9,0.),(0,-1),levels,run=3.6,w=1.0,gap=.15,land=1.3)   # tower x 11.0-13.15, y 3.0-9.2
    for xx in (10.95,13.2):
        for y in (2.95,9.25):g.hbeam(STRUCT,(xx,y,0),(xx,y,zr+1.2),.25,.25)
    for z in levels[:-1]:
        for y in (2.95,9.25):g.hbeam(STRUCT,(10.95,y,z-.12),(13.2,y,z-.12),.2,.24)
    for z in (9.,18.):
        if VER>='a09':
            for y0w,y1w in ((-.3,10.05),(13.35,18.8),(19.6,l+.3)):
                P.grating(g,GRATE,STRUCT,(10.25,(y0w+y1w)/2,z),(1.2,y1w-y0w))
            for y in (10.05,13.35,18.8,19.6):g.beam(STRUCT,(9.65,y,z-.06),(10.85,y,z-.06),.08,.12)
        else:
            P.grating(g,GRATE,STRUCT,(10.25,l/2,z),(1.2,l+.6))
        P.railing(g,YEL,[(10.85,-.3,z),(10.85,2.9,z)],step=1.6);P.railing(g,YEL,[(10.85,9.3,z),(10.85,l+.3,z),(9.65,l+.3,z)],step=1.6)
        for y in (0.,5.,10.,15.,l):g.beam(STRUCT,(9.65,y,z-.15),(10.85,y,z-.15),.12,.2)
    for z in (13.5,):
        P.grating(g,GRATE,STRUCT,(-10.25,6,z),(1.2,10));P.railing(g,YEL,[(-10.85,1,z),(-10.85,11,z),(-9.65,11,z)],step=1.6)
        P.ladder(g,YEL,(-10.25,.65,0),z,(0,-1,0))
    # steam / feedwater pipes up the -x side (aluminium-jacketed insulation), over the roof railing into the drums
    for k,(r,yy) in enumerate(((.30,12.6),(.24,13.5),(.20,14.3),(.16,15.0))):
        xx=-(cx+.55+k*.05)
        P.tube(g,INSUL,[(xx-1.2,yy,.3),(xx-1.2,yy,2.0),(xx,yy,3.0),(xx,yy,zr+1.0),(xx+2.0,yy,zr+1.7),(-1.5-k*.8,yy,zr+1.7),(-1.5-k*.8,yy-.2,zr+2.3)],r,12,bend=.9)
        for z in range(4,int(zr),4):g.box(STRUCT,(xx+.2,yy,z),(.5,.12,.1))
    if VER>='a08':
        # sheet-hrsg front/stair panels: insulated risers/downcomers run the full height of the +x face beside the stair tower,
        # from the feed-pump pad up past the 9/18 m walkways (penetrating the grating) and over the roof railing into a drum
        for k,(r,yy) in enumerate(((.26,10.5),(.22,11.35),(.20,12.15),(.17,12.9),(.17,19.2))):
            xx=10.15+(k%2)*.12;xe=5.6-k*.7;ye=11.0 if k<4 else 15.8
            P.tube(g,INSUL,[(xx,yy,2.4),(xx,yy,zr+1.15),(xx-1.2,yy,zr+1.75),(xe,yy,zr+1.75),(xe,ye,zr+1.75)],r,12,bend=.7)
            for z in range(4,int(zr),3):
                if VER>='a09' and z in (9,18):continue
                g.box(STRUCT,((xx+cx+.3)/2,yy,z),(xx-cx-.3+.1,.10,.10))       # pipe clips back to the column line
            g.cyl(STEEL,(xx,yy,2.4),(xx,yy,2.0),r+.06,12)
            if VER>='a09':
                for z in (9.,18.):g.cyl(STEEL,(xx,yy,z-.08),(xx,yy,z+.10),r+.05,12)                        # deck penetration sleeve collar
            if k<4:P.tube(g,STEEL,[(xx,yy,2.0),(xx,yy,1.2),(cx+3.9-1.2,yy,1.2)],r*.6,10,bend=.3)          # drop to the pump pad
        for z in (6.,12.,21.):P.valve(g,STEEL,REDP,(10.15,10.5,z),(0,0,1),.26)                          # isolating valves on the main riser
    # main steam / reheat lines to the steam turbine: down the front column line, then outside the diffuser into the turbine hall back wall (y<0)
    for k,(r,dx,zz) in enumerate(((.32,0.,16.2),(.26,-.85,15.4))):
        xx=-cx-.35+dx;P.tube(g,INSUL,[(-5.5+k,5.1,zr+1.5),(-5.5+k,1.2,zr+1.7),(xx,1.2,zr+1.7),(xx,1.2,zz),(xx,-7.9,zz)],r,12,bend=1.0)
    g.hbeam(STRUCT,(-cx-.75,-4.0,0),(-cx-.75,-4.0,14.9),.3,.3);g.box(CONC,(-cx-.75,-4.0,.2),(.7,.7,.4))
    g.hbeam(STRUCT,(-cx-1.6,-4.0,14.95),(-cx+.3,-4.0,14.95),.25,.3)
    # outlet transition into the stack
    g.box(STEEL,(0,l+1.2,zt-4.6),(6.4,2.6,8.4));g.box(STRUCT,(0,l+1.2,zt-.35),(6.8,2.8,.3))
    # boiler blowdown tank + feed pumps on a pad beside the stair tower
    px=cx+3.9;g.box(CONC,(px,14.5,.15),(4.0,7,.3))
    g.lathe(STEEL,[(0,-1.7),(.6,-1.6),(.8,-1.3),(.8,1.3),(.6,1.6),(0,1.7)],(px,12.4,1.3),20,axis=(0,1,0))
    for sy in (-1,1):g.box(STRUCT,(px,12.4+sy*.9,.6),(1.2,.2,.6))
    for k in range(2):
        yy=15.3+k*2.0;g.box(STEEL,(px-.6,yy,.65),(1.0,.8,.7));g.cyl(STRUCT,(px+.1,yy,.75),(px+1.4,yy,.75),.32,16);g.cyl(BLUE,(px+.3,yy,.75),(px+1.2,yy,.75),.36,16)
        P.tube(g,STEEL,[(px-.6,yy,1.0),(px-.6,yy,2.4),(cx+.3,yy,2.4)],.12,10)
    P.tube(g,STEEL,[(px,12.4,2.1),(px,12.4,3.4),(cx+.3,12.4,3.4)],.14,10)
    g.flush();return root

# ======================= PP05 exhaust stack =======================
def ring_platform(g,c,z,r0,r1,seg=24,gap=None):
    """annular grating platform with radial brackets and a railing; gap=(a0,a1) radians left open for the ladder"""
    c=Vector(c)
    for k in range(seg):
        a=(k+.5)*2*math.pi/seg
        if gap and (gap[0]<=a<=gap[1] or gap[0]<=a-2*math.pi<=gap[1]):continue
        g.box(GRATE,c+Vector((math.cos(a)*(r0+r1)/2,math.sin(a)*(r0+r1)/2,z-.03)),((r1-r0),2*math.pi*r1/seg+.02,.06),rz=a)
        if k%2==0:g.beam(STRUCT,c+Vector((math.cos(a)*r0,math.sin(a)*r0,z-1.0)),c+Vector((math.cos(a)*r1,math.sin(a)*r1,z-.08)),.12,.12)
    pts=[c+Vector((math.cos(a)*(r1-.05),math.sin(a)*(r1-.05),z)) for a in [gap[1]+(2*math.pi-(gap[1]-gap[0]))*i/32 for i in range(33)]] if gap else [c+Vector((math.cos(2*math.pi*i/32)*(r1-.05),math.sin(2*math.pi*i/32)*(r1-.05),z)) for i in range(33)]
    if gap and VER>='a09':
        pts=[c+Vector((math.cos(gap[1])*r0,math.sin(gap[1])*r0,z))]+pts+[c+Vector((math.cos(gap[0])*r0,math.sin(gap[0])*r0,z))]
    P.railing(g,YEL,pts,step=1.4,closed=False)
    g.torus(STRUCT,c+Vector((0,0,z-.06)),r1,.05,(0,0,1),40,4)
def build_stack():
    r,H=STACK['r'],STACK['h']
    root=part('PP05','ExhaustStack',dimensions=[2*r+2.6,2*r+2.6,H+1.5],height=H)
    g=G('PP05')
    g.cyl(CONC,(0,0,0),(0,0,.9),r+.7,40);g.cyl(STRUCT,(0,0,.9),(0,0,1.4),r+.25,40)
    for k in range(16):a=k*2*math.pi/16;g.beam(STRUCT,(math.cos(a)*(r+.05),math.sin(a)*(r+.05),.9),(math.cos(a)*(r+.05),math.sin(a)*(r+.05),3.2),.22,.30,up=(math.cos(a),math.sin(a),0))
    g.lathe(STEEL,[(r,1.4),(r,H-.8),(r+.12,H-.5),(r+.12,H),(r-.18,H),(r-.18,H-1.6),(0,H-1.6)],(0,0,0),48)
    g.disc(DARK,(0,0,H-1.55),r-.2,.05)
    for z in [4.+3.6*k for k in range(int((H-6)/3.6))]:g.cyl(STRUCT,(0,0,z),(0,0,z+.14),r+.09,48)
    ladder_a=0.
    for z in (24.,44.,H-1.0):ring_platform(g,(0,0,0),z,r+.05,r+1.35,28,gap=(-.32,.32) if VER>='a09' else (-.18,.18))
    P.ladder(g,YEL,(r+.02,0,1.4),H-1.0,(1,0,0))
    g.box(WHITE,(-r-.9,0,24.7),(.8,.6,1.3));g.cyl(STEEL,(-r-.05,.3,25.2),(-r-.6,.3,25.2),.09,10)                # CEMS analyser cabinet + sampling probe
    for a in (math.pi/4,3*math.pi/4,5*math.pi/4,7*math.pi/4):
        p=Vector((math.cos(a)*(r+1.25),math.sin(a)*(r+1.25),H-1.0+1.15));g.box(RED,p,(.14,.14,.18));g.box(STRUCT,p-Vector((0,0,.15)),(.06,.06,.15))
    for a in (0,2.1,4.2):g.cyl(GALV,(math.cos(a)*(r-.1),math.sin(a)*(r-.1),H),(math.cos(a)*(r-.1),math.sin(a)*(r-.1),H+1.4),.02,6)
    g.flush();return root

# ======================= PP06 GT exhaust diffuser duct (turbine hall back wall -> HRSG inlet) =======================
DUCT=dict(l=8.,a=(5.,6.,3.),b=(16.6,22.,3.))     # length; (width, height, bottom z) at the hall / HRSG ends
def build_duct():
    root=part('PP06','ExhaustDiffuser',dimensions=[DUCT['b'][0],DUCT['l'],DUCT['b'][1]+DUCT['b'][2]])
    g=G('PP06');L=DUCT['l']
    def sec(t,grow=0.):
        wa,ha,za=DUCT['a'];wb,hb,zb=DUCT['b'];w=wa+(wb-wa)*t+2*grow;hh=ha+(hb-ha)*t+2*grow;z=za+(zb-za)*t-grow;y=.8+(L-.8)*t
        return [(-w/2,y,z),(w/2,y,z),(w/2,y,z+hh),(-w/2,y,z+hh)]
    g.loft(STEEL,sec(0),sec(1),cap=True)
    for i in range(1,8):
        t=i/8;A=sec(t,.10);B=[(x,y+.18,z) for x,y,z in A];g.loft(STRUCT,A,B,cap=True)
    wa,ha,za=DUCT['a']
    for i in range(5):g.box(STEEL if i%2 else STRUCT,(0,.08+i*.15,za+ha/2),(wa+.3+(i%2)*.2,.12,ha+.3+(i%2)*.2))     # expansion bellows at the turbine end
    for y,xx in ((2.4,(-3.,3.)),(6.2,(-6.6,6.6))):
        for x in xx:g.hbeam(STRUCT,(x,y,0),(x,y,3.0),.3,.3);g.box(CONC,(x,y,.2),(.7,.7,.4))
        g.hbeam(STRUCT,(xx[0],y,2.85),(xx[1],y,2.85),.3,.3)
    g.flush();return root

# ======================= PP07 mechanical-draft cooling tower (4 cells) =======================
CT=dict(w=13.,cells=4,cell=12.,deck=10.,inlet=4.6,fan_r=4.25,fan_h=3.4)
def build_cooling():
    w,n,cl,zd,zi=CT['w'],CT['cells'],CT['cell'],CT['deck'],CT['inlet'];L=n*cl;fr=CT['fan_r']
    root=part('PP07','CoolingTower',dimensions=[w,L,zd+CT['fan_h']],cells=n)
    g=G('PP07');x0,x1,y0,y1=-w/2,w/2,-L/2,L/2
    # cold-water basin curb (blue-painted coping, sheet-cool), basin water seen under the inlets
    g.box(CONC,(0,0,.3),(w+1.2,L+1.2,.6));g.box(RAILB,(0,0,.62),(w+1.25,L+1.25,.06))
    g.box(C.mat('PP_BasinWater',(.02,.05,.06),.05,0,0,0,None,.5),(0,0,.5),(w-.4,L-.4,.02))
    g.box(DARK,(0,0,(zi+.6)/2+.3),(w-1.2,L-1.2,zi-.2))                                         # dark fill pack behind the louvres
    g.box(CONC,(0,0,(zi+zd)/2),(w,L,zd-zi));g.box(CONC,(0,0,zd+.15),(w+.2,L+.2,.3))
    # long sides: columns + inclined louvres + X bracing in each bay (10 bays per side over 4 cells)
    nb=10;bay=L/nb
    for x,ns in ((x0,1),(x1,-1)):
        F=P.WF((x,y0,0),math.pi/2,ns)
        for i in range(nb+1):F.box(g,CONC,i*bay,(zi+.6)/2,.0,.45,zi-.6,.45)
        for i in range(nb):
            u0=i*bay+.25;u1=(i+1)*bay-.25
            P.louvre_bank(g,LOUV,STRUCT,F,u0,u1,.7,zi-.1,pitch=.22,tilt=38,w0=-.15,depth=.22,frame=.06)
            g.beam(STRUCT,F.p(u0,.75,.06),F.p(u1,zi-.15,.06),.06,.06,up=F.out());g.beam(STRUCT,F.p(u1,.75,.06),F.p(u0,zi-.15,.06),.06,.06,up=F.out())
        F.box(g,CONC,L/2,zi+.2,.03,L,.4,.06)                                                       # ring beam over the inlets
        for i in range(1,nb):F.box(g,JOINT,i*bay,(zi+zd)/2+.2,.003,.035,zd-zi-.4,.01)               # precast panel joints (sheet-cool: vertical lines)
        F.box(g,JOINT,L/2,(zi+zd)/2+.4,.003,L,.035,.01)
    for y,ns in ((y0,-1),(y1,1)):
        F=P.WF((x0,y,0),0,ns)
        F.box(g,CONC,w/2,(zi+.6)/2,.0,w,zi-.6,.1)
        for i in range(1,3):F.box(g,JOINT,i*w/3,(zi+zd)/2+.2,.003,.035,zd-zi-.4,.01)
    # end door with canopy and steps (y0 end, sheet-cool panels 1/3): door on top of the basin curb
    F=P.WF((x0,y0,.6),0,-1);pdoor(g,F,w/2,1.4,2.3,canopy=False);F.box(g,CONC,w/2,2.75,.75,2.8,.15,1.5)
    F0=P.WF((x0,y0,0),0,-1)
    for i in range(4):F0.box(g,CONC,w/2,(i+1)*.15/2,.6+.3*(4-i)/2,2.4,(i+1)*.15,.3*(4-i))
    # fan deck: blue handrail, fan stacks (flared velocity-recovery cylinders) with 8 blades + hub + motor, partition ridges
    P.railing(g,RAILB,[(x1-.1,y1-1.1,zd+.3),(x1-.1,y0+.1,zd+.3),(x0+.1,y0+.1,zd+.3),(x0+.1,y1-.1,zd+.3),(x1-.1,y1-.1,zd+.3)],step=1.8)   # gap at the stair head
    for i in range(1,n):g.box(CONC,(0,y0+i*cl,zd+.36),(w,.25,.12))
    for i in range(n):
        cy=y0+(i+.5)*cl;c=Vector((0,cy,zd+.3));H=CT['fan_h']
        g.lathe(CLAD2,[(fr+.18,0),(fr+.18,H*.72),(fr+.55,H),(fr+.45,H),(fr,H*.74),(fr,.05)],c,56)
        g.torus(CLAD2,c+Vector((0,0,.05)),fr+.25,.12,(0,0,1),56,6)
        for k in range(12):
            a=k*2*math.pi/12;g.box(CLAD2,c+Vector((math.cos(a)*(fr+.24),math.sin(a)*(fr+.24),H*.36)),(.10,.06,H*.72),rz=a)
        g.disc(DARK,c+Vector((0,0,.15)),fr-.02,.02)
        hz=c+Vector((0,0,.9));g.cyl(STEEL,hz-Vector((0,0,.25)),hz+Vector((0,0,.25)),.55,20)
        for k in range(8):                                                                        # tapered, twisted GRP blades
            a=k*2*math.pi/8+i*.3;M=Matrix.Translation(hz)@Matrix.Rotation(a,4,'Z');V=[];r0,r1=.6,fr-.12
            for rr,cw,tw in ((r0,.34,18),(r1,.17,8)):
                for sgn in (-1,1):
                    for th in (-.025,.025):
                        q=Matrix.Rotation(math.radians(tw),3,'X')@Vector((0,sgn*cw,th));V.append((M@Vector((rr,q.y,q.z,1))).to_3d())
            g.mesh(FANB,V,[(0,1,3,2),(4,6,7,5),(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6)])
        g.cyl(CLAD2,hz+Vector((0,0,.25)),hz+Vector((0,0,1.3)),.32,16);g.cyl(STEEL,hz+Vector((0,0,1.3)),hz+Vector((0,0,1.45)),.36,16)
        for k in range(4):a=k*math.pi/2+math.pi/4;g.beam(STRUCT,hz+Vector((math.cos(a)*.4,math.sin(a)*.4,-.2)),c+Vector((math.cos(a)*(fr-.05),math.sin(a)*(fr-.05),.3)),.10,.14)
    # external stair up the long side at the y1 end (two flights + landing), hot-water risers + distribution header on the deck
    sx=x1+1.3;ra=6.0;yA=y1-1.0-ra-1.3-ra;yB=yA+ra;yC=yB+1.3;yD=yC+ra
    P.flight(g,STRUCT,GRATE,RAILB,(sx,yA,0),(sx,yB,zd/2),1.0)
    P.grating(g,GRATE,STRUCT,(sx,(yB+yC)/2,zd/2),(1.2,1.3))
    P.flight(g,STRUCT,GRATE,RAILB,(sx,yC,zd/2),(sx,yD,zd+.3),1.0)
    P.grating(g,GRATE,STRUCT,(sx-.3,y1-.5,zd+.3),(1.8,1.0))
    for yy in (yB,yC,y1-.05):g.hbeam(STRUCT,(sx+.6,yy,0),(sx+.6,yy,zd+.3 if yy>yC else zd/2),.2,.2)
    P.railing(g,RAILB,[(sx+.6,yB,zd/2),(sx+.6,yC,zd/2)],step=1.3);P.railing(g,RAILB,[(sx+.6,yD,zd+.3),(sx+.6,y1,zd+.3)],step=1.3)
    for yy in (y0+cl*.5,y0+cl*1.5):P.tube(g,STEEL,[(x1+.7,yy,.8),(x1+.7,yy,zd+.9),(x1-1.5,yy,zd+.9)],.35,16,bend=.7)
    P.tube(g,STEEL,[(x0+1.5,y0+.6,zd+.9),(x0+1.5,y1-.6,zd+.9)],.30,16);P.tube(g,STEEL,[(x1-1.5,y0+.6,zd+.9),(x1-1.5,y1-.6,zd+.9)],.30,16)
    for i in range(n):g.cyl(STEEL,(x0+1.5,y0+(i+.5)*cl,zd+.9),(x1-1.5,y0+(i+.5)*cl,zd+.9),.22,12)
    g.flush();return root

# ======================= PP09 main transformer + fire wall + oil pit =======================
def build_transformer():
    root=part('PP09','MainTransformer',dimensions=[9,9,9.5],hv_side='+X',lv_side='-X')
    g=G('PP09')
    g.box(CONC,(0,0,.1),(9.0,9.0,.2));g.box(GRAVEL,(0,0,.27),(8.4,8.4,.14))                      # oil pit with gravel
    for x,y,dx,dy in ((0,4.35,9,.3),(0,-4.35,9,.3),(4.35,0,.3,9),(-4.35,0,.3,9)):g.box(CONC,(x,y,.4),(dx,dy,.5))
    g.box(CONC,(0,0,.55),(5.6,3.0,.5))                                                           # plinth
    tz0,tz1=.8,4.9;g.box(TRAN,(0,0,(tz0+tz1)/2),(5.0,2.6,tz1-tz0));g.box(TRAN,(0,0,tz1+.08),(5.3,2.9,.16))
    for x in (-2.0,-1.0,0,1.0,2.0):
        for s in (-1,1):g.box(TRAN,(x,s*1.33,(tz0+tz1)/2),(.12,.08,tz1-tz0))
    for s in (-1,1):g.box(TRAN,(0,s*1.33,tz0+.4),(5.0,.12,.12));g.box(TRAN,(0,s*1.33,tz1-.4),(5.0,.12,.12))
    # radiator banks both sides (headers + fins + fans)
    for s in (-1,1):
        for bx in (-1.25,1.25):
            yb=s*(1.45+.75)
            for zz in (tz0+.6,tz1-.45):g.cyl(TRAN,(bx,s*1.3,zz),(bx,yb,zz),.08,10)
            g.cyl(TRAN,(bx-1.05,yb,tz1-.45),(bx+1.05,yb,tz1-.45),.11,10);g.cyl(TRAN,(bx-1.05,yb,tz0+.6),(bx+1.05,yb,tz0+.6),.11,10)
            for k in range(14):g.box(TRAN,(bx-1.0+k*2.0/13,yb,(tz0+tz1)/2+.07),(.03,.95,tz1-tz0-1.0))
            for fx in (-.5,.5):g.cyl(STRUCT,(bx+fx,yb,tz0+.05),(bx+fx,yb,tz0+.35),.30,16)
    # conservator on brackets, Buchholz pipe, HV bushings with turrets, neutral bushing, LV bus duct to the hall, cabinet, ladder
    cz=tz1+1.9;g.lathe(TRAN,[(0,-1.7),(.5,-1.65),(.62,-1.4),(.62,1.4),(.5,1.65),(0,1.7)],(-1.6,0,cz),24,axis=(0,1,0))
    for y in (-1.0,1.0):g.beam(STRUCT,(-2.2,y,tz1+.15),(-1.6,y,cz-.55),.12,.12);g.beam(STRUCT,(-1.0,y,tz1+.15),(-1.6,y,cz-.55),.12,.12)
    P.tube(g,TRAN,[(-1.6,.5,cz-.6),(-1.1,.5,tz1+.6),(-.6,.5,tz1+.16)],.06,8)
    for y in (-.9,0,.9):
        g.cyl(TRAN,(1.3,y,tz1+.16),(1.3,y,tz1+.75),.26,16);P.insulator(g,INS,GALV,(1.3,y,tz1+.75),(1.3,y,tz1+3.6),.09,.22,.11,14)
        g.cyl(GALV,(1.3,y,tz1+3.6),(1.3,y,tz1+3.75),.12,12);g.box(BUS,(1.3,y,tz1+3.9),(.25,.12,.3))
    g.cyl(TRAN,(.2,-.9,tz1+.16),(.2,-.9,tz1+.5),.14,12);P.insulator(g,INS,GALV,(.2,-.9,tz1+.5),(.2,-.9,tz1+1.6),.05,.11,.08,12)
    g.box(STRUCT,(-2.9,0,tz1-.6),(.8,2.0,1.2));g.box(STRUCT,(-4.1,0,tz1-.6),(1.8,1.2,1.0))                   # LV terminal box + isolated-phase bus duct towards the hall
    for y in (-.6,.6):g.hbeam(STRUCT,(-4.4,y,0),(-4.4,y,tz1-1.1),.25,.25)
    g.box(STRUCT,(2.7,.9,2.0),(.25,.9,1.2));g.box(DOOR,(2.83,.9,2.0),(.02,.8,1.1))                     # control cabinet
    P.ladder(g,YEL,(2.52,-.6,tz0),tz1+.1,(1,0,0),cage=False)
    g.box(WHITE,(2.53,0,3.4),(.02,.5,.35))                                                      # rating plate
    # fire wall on +y (between neighbours)
    g.box(CONC,(0,4.75,4.0),(9.0,.4,8.0));g.box(CONC,(0,4.75,8.05),(9.2,.55,.1))
    g.flush();return root

# ======================= PP10 220 kV switchyard (5 bays, fence, relay house) =======================
SY=dict(w=52.,d=28.,bays=5,bay=9.)
def disconnector(g,x,y,z0=2.4):
    """3-phase centre-break disconnector across x: each phase a base channel on a post, two rotating post insulators and a blade"""
    for px in (-2.6,0,2.6):
        X=x+px;g.box(CONC,(X,y,.2),(.7,1.8,.4));g.hbeam(STRUCT,(X,y-.6,.4),(X,y-.6,z0),.25,.25);g.hbeam(STRUCT,(X,y+.6,.4),(X,y+.6,z0),.25,.25)
        g.box(GALV,(X,y,z0+.08),(.25,1.9,.16))
        for s in (-1,1):P.insulator(g,INS,GALV,(X,y+s*.7,z0+.16),(X,y+s*.7,z0+2.0),.06,.14,.10,12)
        g.box(BUS,(X,y,z0+2.12),(.08,1.5,.06));g.box(BUS,(X,y-.75,z0+2.12),(.18,.18,.18));g.box(BUS,(X,y+.75,z0+2.12),(.18,.18,.18))
    g.box(STRUCT,(x+3.6,y,1.1),(.5,.4,.8));g.cyl(STRUCT,(x+3.6,y,1.5),(x+3.6,y,z0),.03,6)            # motor operating mechanism
def post_equipment(g,x,y,kind,z0=2.4):
    """3 single-phase post-mounted devices: 'arrester', 'cvt', 'ct'"""
    for px in (-2.6,0,2.6):
        X=x+px;g.box(CONC,(X,y,.2),(.8,.8,.4));g.hbeam(STRUCT,(X,y,.4),(X,y,z0),.3,.3);g.box(GALV,(X,y,z0+.05),(.6,.6,.1))
        if kind=='arrester':
            P.insulator(g,INS,GALV,(X,y,z0+.1),(X,y,z0+2.7),.07,.15,.10,12);g.torus(GALV,(X,y,z0+2.4),.45,.025,(0,0,1),20,4)
            for k in range(3):a=k*2.1;g.beam(GALV,(X,y,z0+2.4),(X+math.cos(a)*.45,y+math.sin(a)*.45,z0+2.4),.02,.02)
            g.box(STRUCT,(X+.35,y,z0-.6),(.16,.12,.22))                                             # surge counter
        elif kind=='cvt':
            g.cyl(STRUCT,(X,y,z0+.1),(X,y,z0+.9),.32,16);P.insulator(g,INS,GALV,(X,y,z0+.9),(X,y,z0+3.6),.09,.20,.11,12);g.cyl(GALV,(X,y,z0+3.6),(X,y,z0+3.8),.14,12)
        else:
            P.insulator(g,INS,GALV,(X,y,z0+.1),(X,y,z0+2.6),.10,.22,.11,12);g.lathe(GALV,[(0,0),(.32,.05),(.36,.4),(.30,.75),(0,.8)],(X,y,z0+2.6),16)
def breaker(g,x,y,z0=2.0):
    """dead-tank SF6 breaker (sheet-switch): horizontal tank across x on a frame, three bushings, mechanism cabinet"""
    for sx in (-2.4,2.4):
        for sy in (-.5,.5):g.hbeam(STRUCT,(x+sx,y+sy,0),(x+sx,y+sy,z0),.22,.22)
    g.box(CONC,(x,y,.15),(5.6,1.8,.3));g.box(STRUCT,(x,y,z0+.05),(5.2,1.3,.1))
    g.lathe(STEEL,[(0,-3.0),(.45,-2.95),(.62,-2.75),(.62,2.75),(.45,2.95),(0,3.0)],(x,y,z0+.75),24,axis=(1,0,0))
    for sx in (-2.0,2.0):g.torus(STEEL,(x+sx,y,z0+.75),.66,.05,(1,0,0),24,4)
    for px in (-2.6,0,2.6):
        g.cyl(STEEL,(x+px,y,z0+1.2),(x+px,y,z0+1.6),.2,14);P.insulator(g,INS,GALV,(x+px,y,z0+1.6),(x+px,y,z0+3.7),.08,.18,.10,12)
    g.box(STRUCT,(x+3.4,y,1.4),(.9,.7,1.4));g.box(DOOR,(x+3.4,y-.36,1.4),(.8,.02,1.2))
def build_switchyard():
    w,d=SY['w'],SY['d'];root=part('PP10','Switchyard',dimensions=[w,d,15],bays=SY['bays'],voltage_kv=220,line_side='+Y')
    g=G('PP10');x0,x1,y0,y1=-w/2,w/2,-d/2,d/2
    g.box(CONC,(0,0,.06),(w,d,.12));g.box(GRAVEL,(0,0,.16),(w-.4,d-.4,.08))
    for bi,x in enumerate([x0+8.5+SY['bay']*i for i in range(SY['bays'])]):
        g.box(CONC,(x,0,.215),(.9,d-2,.03))                                                       # cable trench cover strip
        # line gantry (lattice columns + truss) with suspension strings, then equipment rows towards the busbars
        yg=y1-2.2
        for sx in (-4.4,4.4):P.lattice_column(g,STRUCT,(x+sx,yg,.2),14.,1.1,.7,1.4);g.box(CONC,(x+sx,yg,.15),(1.4,1.4,.3))
        P.lattice_beam(g,GALV,(x-4.4,yg,13.6),(x+4.4,yg,13.6),.9,1.1)
        for px in (-2.6,0,2.6):P.string(g,INS,GALV,(x+px,yg,13.1),(x+px,yg,11.4))
        post_equipment(g,x,y1-5.0,'arrester');post_equipment(g,x,y1-7.6,'cvt');disconnector(g,x,y1-10.6)
        post_equipment(g,x,y1-13.6,'ct');breaker(g,x,y1-17.0);disconnector(g,x,y1-20.6)
        for px in (-2.6,0,2.6):                                                                   # flexible droppers between the equipment terminals
            X=x+px
            P.catenary(g,BUS,(X,yg,11.35),(X,y1-5.0,5.3),.35,.02,10);P.catenary(g,BUS,(X,y1-5.0,5.2),(X,y1-7.6,6.3),.15,.02,6)
            P.catenary(g,BUS,(X,y1-7.6,6.2),(X,y1-9.8,4.6),.15,.02,6);P.catenary(g,BUS,(X,y1-11.4,4.6),(X,y1-13.6,5.4),.12,.02,6)
            P.catenary(g,BUS,(X,y1-13.6,5.4),(X,y1-17.0,5.8),.2,.02,6);P.catenary(g,BUS,(X,y1-17.0,5.8),(X,y1-19.8,4.6),.15,.02,6)
            yb=(y1-23.0 if bi%2==0 else y1-25.5)+(px/2.6)*.7                                     # bay alternates between bus I / bus II
            P.tube(g,BUS,[(X,y1-21.4,4.6),(X,y1-22.2,6.8),(X,yb,8.25)],.03,6,bend=.3)
    # double tubular busbars along x (3 phases side by side) on post insulators
    zb=8.4
    for yb0 in (y1-23.0,y1-25.5):
        for off in (-.7,0,.7):
            g.cyl(BUS,(x0+5.0,yb0+off,zb),(x1-1.0,yb0+off,zb),.075,10)
            for x in [x0+6.0+9.0*i for i in range(6)]:
                g.hbeam(STRUCT,(x,yb0+off,.2),(x,yb0+off,5.4),.25,.25);g.box(GALV,(x,yb0+off,5.5),(.5,.5,.12));P.insulator(g,INS,GALV,(x,yb0+off,5.55),(x,yb0+off,zb-.1),.08,.17,.10,12)
        for x in [x0+6.0+9.0*i for i in range(6)]:g.box(STRUCT,(x,yb0,4.2),(.2,1.9,.2))
    # relay kiosk, lighting masts, fence with a gate on the line (+y) side
    kx=x0+2.6;g.box(CLAD2,(kx,y0+3.0,1.8),(4,4,3.4));g.box(MEMB,(kx,y0+3.0,3.6),(4.3,4.3,.2));F=P.WF((kx+2.0,y0+1.0,0),math.pi/2,-1);pdoor(g,F,2.0,1.0,2.2)
    P.louvre_bank(g,LOUV,ALU,P.WF((kx-2.0,y0+1.0,0),0,-1),1.2,2.8,1.6,2.4,pitch=.1)
    for x,y in ((x0+1.2,y1-1.2),(x1-1.2,y0+1.2)):
        g.cyl(GALV,(x,y,0),(x,y,18),.16,12,r1=.09);g.box(GALV,(x,y,18.2),(1.4,.4,.2))
        for s in (-1,1):g.box(WHITE,(x+s*.45,y-.25,18.05),(.35,.25,.15))
    fence_mesh(g,[(x0,y0),(x1,y0),(x1,y1),(x0+12,y1)],2.3,STRUCT,GALV);fence_mesh(g,[(x0+6,y1),(x0,y1),(x0,y0)],2.3,STRUCT,GALV)
    g.flush();return root
def fence_mesh(g,pts,h,mpost,mmesh,step=2.5,cell=.10,post_m=None):
    """steel post + welded mesh panel fence along a polyline (posts every step)"""
    for a,b in zip(pts[:-1],pts[1:]):
        a=Vector((a[0],a[1],0));b=Vector((b[0],b[1],0));d=b-a;L=d.length;n=max(1,math.ceil(L/step));u=d.normalized();rz=math.atan2(u.y,u.x)
        for k in range(n+1):q=a+d*(k/n);g.box(post_m or mpost,(q.x,q.y,h/2+.05),(.08,.08,h+.1))
        for k in range(n):
            q0=a+d*(k/n);q1=a+d*((k+1)/n);c=(q0+q1)/2;lp=(q1-q0).length-.1
            g.box(mpost,(c.x,c.y,h-.04),(lp,.05,.05),rz);g.box(mpost,(c.x,c.y,.15),(lp,.05,.05),rz)
            for j in range(1,int(lp/cell)):p=q0+u*(.05+j*cell);g.box(mmesh,(p.x,p.y,(h+.15)/2),(.006,.006,h-.2))
            for j in range(1,int((h-.25)/(cell*2))):g.box(mmesh,(c.x,c.y,.15+j*cell*2),(lp,.006,.006),rz)

# ======================= PP11 natural-gas pressure regulating station =======================
GS=dict(w=17.,d=40.)
def build_gas_station():
    w,d=GS['w'],GS['d'];root=part('PP11','GasRegulatingStation',dimensions=[w,d,8],inlet=[w/2,-15,0],outlet=[-w/2,12,1.2])
    g=G('PP11');x0,x1,y0,y1=-w/2,w/2,-d/2,d/2
    g.box(CONC,(0,0,.1),(w,d,.2));g.box(PLINTH,(0,0,.205),(w-.6,d-.6,.01))
    def sup(x,y,z):g.box(CONC,(x,y,.35),(.5,.5,.3));g.box(STRUCT,(x,y,(.5+z)/2),(.12,.12,z-.5));g.box(STRUCT,(x,y,z-.02),(.4,.12,.06))
    zp=1.1
    # inlet riser from underground at the east fence, inlet header with isolation valve and insulating joint
    P.tube(g,GASY,[(x1+.3,-15,-.5),(x1+.3,-15,zp),(x1-2.0,-15,zp),(x0+2.5,-15,zp)],.22,16,bend=.5)
    P.valve(g,STEEL,REDP,(x1-1.0,-15,zp),(1,0,0),.22);g.box(WHITE,(x1-1.7,-15,zp),(.12,.5,.5))                     # inlet isolation valve + insulating joint
    # three vertical filter-separators (sheet-gas: silver vessels with dished heads, flanged nozzles, legs, gauges)
    for k,x in enumerate((-4.,0.,4.)):
        c=Vector((x,-11.5,0));g.lathe(STEEL,[(0,.9),(.45,.95),(.62,1.2),(.62,3.4),(.45,3.65),(0,3.7)],c,24)
        for a in range(3):aa=a*2.1;g.box(STRUCT,c+Vector((math.cos(aa)*.55,math.sin(aa)*.55,.55)),(.12,.12,1.1))
        P.tube(g,GASY,[(x,-15,zp),(x,-14.0,zp),(x,-14.0,2.6),(x,-12.05,2.6)],.16,12,bend=.35);P.flange(g,STEEL,(x,-12.2,2.6),(0,1,0),.16);P.valve(g,STEEL,REDP,(x,-13.2,2.6),(0,1,0),.16)
        P.tube(g,GASY,[(x,-10.95,1.6),(x,-9.6,1.6),(x,-9.6,zp),(x,-6.5,zp)],.16,12,bend=.35);P.flange(g,STEEL,(x,-10.8,1.6),(0,1,0),.16)
        g.cyl(GASY,(x,-11.5,3.7),(x,-11.5,4.0),.1,10);g.disc(WHITE,(x+.45,-11.95,2.6),.09,.03,(1,-1,0),16);g.cyl(STEEL,(x,-11.5,.95),(x,-11.5,.6),.05,8)
    # three parallel regulating runs (valve - meter - monitor - active regulator - valve) on skids
    for x in (-4.,0.,4.):
        for s in (-1,1):g.box(STRUCT,(x+s*.45,1.0,.5),(.12,15.0,.2))                                  # skid frame: two channels + cross members
        for y in [-6.3+1.5*k for k in range(11)]:g.box(STRUCT,(x,y,.5),(1.02,.1,.14))
        for y in (-5.,-1.,3.,7.):g.box(CONC,(x,y,.2),(1.2,.6,.4))
        P.tube(g,GASY,[(x,-6.5,zp),(x,8.5,zp)],.16,12)
        for y in (-5.8,7.6):P.valve(g,STEEL,REDP,(x,y,zp),(0,1,0),.16)
        g.box(STEEL,(x,-3.4,zp),(.5,.7,.5));g.box(WHITE,(x+.27,-3.4,zp+.1),(.02,.35,.25))                      # turbine meter + display
        for y in (0.,3.6):
            g.sphere(STEEL,(x,y,zp),.3,14,8,(1,1.2,1));g.cyl(STEEL,(x,y,zp+.2),(x,y,zp+.55),.08,10)
            g.lathe(STEEL,[(0,0),(.42,.05),(.46,.18),(.30,.30),(0,.34)],(x,y,zp+.55),20);g.cyl(STRUCT,(x,y,zp+.89),(x,y,zp+1.2),.06,8)
            P.tube(g,STEEL,[(x,y+.9,zp+.15),(x+.25,y+.9,zp+.55),(x+.25,y+.3,zp+.75)],.015,6,bend=.08)
            for s in (-1,1):P.flange(g,STEEL,(x,y+s*.42,zp),(0,1,0),.16)
        g.box(STRUCT,(x+.6,1.8,1.6),(.06,.06,1.2));g.cyl(WHITE,(x+.6,1.75,2.25),(x+.6,1.82,2.25),.08,14)              # pressure gauge on a post
    P.tube(g,GASY,[(x0+2.5,-6.5,zp),(x1-2.5,-6.5,zp)],.22,16);P.tube(g,GASY,[(x1-2.5,8.5,zp),(x0+2.5,8.5,zp),(x0+2.5,12,zp),(x0-.5,12,zp)],.22,16,bend=.5)
    P.valve(g,STEEL,REDP,(x0+1.2,12,zp),(1,0,0),.22)
    for y in (-14.,-6.5,8.5,12.):
        for x in (x0+2.5,x1-2.5):sup(x,y,zp-.22)
    # open steel shed with gable roof over the control cabinets (north end), vent stack, extinguishers, sign
    sy0,sy1=13.5,y1-1.0;sw=10.
    for x in (-sw/2,0,sw/2):
        for y in (sy0,sy1):g.hbeam(STRUCT,(x,y,.2),(x,y,4.2),.2,.2)
    for y in (sy0,sy1):g.hbeam(STRUCT,(-sw/2,y,4.2),(sw/2,y,4.2),.2,.25)
    for s in (-1,1):
        A=[(s*(sw/2+.4),sy0-.4,4.0),(0,sy0-.4,5.1),(0,sy0-.4,5.2),(s*(sw/2+.4),sy0-.4,4.1)];B=[(x,sy1+.4,z) for x,_,z in A];g.loft(ROOF,A,B)
        for i in range(int((sy1-sy0+.8)/.25)):
            yy=sy0-.4+i*.25;g.beam(ROOF,(s*(sw/2+.4),yy,4.13),(0,yy,5.23),.03,.04)
    for k,x in enumerate((-3.2,-1.6,0.,1.6)):g.box(GALV,(x,sy1-.8,1.15),(1.4,.7,1.9));g.box(DOOR,(x,sy1-1.16,1.15),(1.3,.02,1.8))
    g.cyl(STEEL,(x1-1.5,y1-1.5,.2),(x1-1.5,y1-1.5,7.5),.11,12);g.cyl(STEEL,(x1-1.5,y1-1.5,7.75),(x1-1.5,y1-1.5,8.0),.32,16,r1=.03)   # vent stack + rain hat
    for a in (0,2.1,4.2):g.beam(STEEL,(x1-1.5,y1-1.5,7.45),(x1-1.5+math.cos(a)*.28,y1-1.5+math.sin(a)*.28,7.78),.02,.02)
    g.box(CONC,(x1-1.5,y1-1.5,.25),(.8,.8,.5))
    for x,y in ((x0+.6,0.),(x1-.6,-6.)):g.box(REDP,(x,y,.8),(.25,.45,.8))
    fence_mesh(g,[(x0-.3,1.5),(x0-.3,y0-.3),(x1+.3,y0-.3),(x1+.3,y1+.3),(x0-.3,y1+.3),(x0-.3,4.5)],2.0,YEL,GALV)
    for y,s in ((1.6,1),(4.4,-1)):                                                                 # double gate leaves (hinged, closed)
        for k in range(1,14):g.box(GALV,(x0-.3,y+s*k*.1,1.05),(.006,.006,1.75))
        for z in (.15,1.95):g.box(YEL,(x0-.3,y+s*.7,z),(.05,1.4,.05))
        if VER>='a09':g.box(YEL,(x0-.3,y+s*1.375,1.05),(.05,.05,1.85))
    if VER>='a09':
        g.box(YEL,(x0-.3,3.0,2.22),(.06,3.06,.06))                                                 # portal header over the double gate
        g.box(WHITE,(x0-.36,3.0,2.52),(.03,1.3,.42));g.box(REDP,(x0-.376,3.0,2.52),(.008,1.22,.34));g.box(WHITE,(x0-.379,3.0,2.52),(.006,1.14,.26))
        for sy in (-.45,.45):g.box(YEL,(x0-.33,3.0+sy,2.28),(.04,.04,.12))
    else:
        g.box(WHITE,(x0-.36,3.0,2.45),(.03,1.3,.4))
    sg=C.text(K,'GS_Sign','严禁烟火',(x0-.39,3.0,2.52 if VER>='a09' else 2.45),.22,REDP,rot=(math.pi/2,0,-math.pi/2),extrude=.006)
    if VER>='a09':
        bpy.context.view_layer.objects.active=sg;sg.select_set(True);bpy.ops.object.convert(target='MESH');sg.select_set(False)
    g.flush();return root

# ======================= PP12 administration + central control building =======================
AD=dict(w=32.4,d=16.,floors=4,fh=3.6)
def window(g,F,u,v,w,h,mull=1):
    """punched window: stone surround, dark backing, glass, dark aluminium frame with mullion(s) and transom, stone sill (sheet-admin panel 6)"""
    for du,dv,dw,dh in ((-w/2-.075,h/2,.15,h+.3),(w/2+.075,h/2,.15,h+.3)):F.box(g,STONE,u+du,v+dv,.06,dw,dh,.12)
    F.box(g,STONE,u,v+h+.075,.06,w+.3,.15,.12);F.box(g,STONE,u,v-.06,.13,w+.4,.12,.26)
    F.box(g,DARK,u,v+h/2,.004,w,h,.008);F.box(g,GLASS,u,v+h/2,.03,w-.08,h-.08,.01)
    for a,b,c_,d_ in ((u,v+.03,w,.06),(u,v+h-.03,w,.06),(u-w/2+.03,v+h/2,.06,h),(u+w/2-.03,v+h/2,.06,h),(u,v+h*.72,w,.05)):F.box(g,WDARK,a,b,.045,c_,d_,.05)
    for j in range(1,mull+1):F.box(g,WDARK,u-w/2+w*j/(mull+1),v+h*.36,.045,.05,h*.72,.05)
def build_admin():
    w,d,nf,fh=AD['w'],AD['d'],AD['floors'],AD['fh'];H=nf*fh;root=part('PP12','AdminControlBuilding',dimensions=[w,d,H+3.2],floors=nf,entrance='-Y')
    g=G('PP12');x0,x1,y0,y1=-w/2,w/2,-d/2,d/2
    g.box(STONE,(0,0,H/2),(w,d,H));g.box(PLINTH,(0,0,.3),(w+.16,d+.16,.6))
    nb=9;bay=w/nb;ent=4
    for (F,L,front) in ((P.WF((x0,y0,0),0,-1),w,True),(P.WF((x0,y1,0),0,1),w,False)):
        for i in range(nb+1):F.box(g,STONE,i*bay,H/2,.08,.45 if 0<i<nb else .7,H,.16)
        for f in range(1,nf):F.box(g,STONE,L/2,f*fh,.05,L,.28,.10)
        for i in range(nb):
            for f in range(nf):
                if front and i==ent and f==0:continue
                if (not front) and i==1 and f==0:pdoor(g,F,(i+.5)*bay,1.6,2.4,canopy=True);continue
                window(g,F,(i+.5)*bay,f*fh+.95,2.1,1.85)
    for (F,L) in ((P.WF((x0,y0,0),math.pi/2,1),d),(P.WF((x1,y0,0),math.pi/2,-1),d)):
        for u in (0,L):F.box(g,STONE,u,H/2,.08,.7,H,.16)
        for f in range(1,nf):F.box(g,STONE,L/2,f*fh,.05,L,.28,.10)
        for u in (L*.3,L*.7):
            for f in range(nf):window(g,F,u,f*fh+.95,2.1,1.85)
    # parapet, coping, roof membrane, stair/lift rooms, condensers, drains, lightning tape
    for c,dd in (((0,y0+.12,H+.45),(w,.24,.9)),((0,y1-.12,H+.45),(w,.24,.9)),((x0+.12,0,H+.45),(.24,d,.9)),((x1-.12,0,H+.45),(.24,d,.9))):g.box(STONE,c,dd)
    for c,dd in (((0,y0+.12,H+.93),(w+.1,.42,.06)),((0,y1-.12,H+.93),(w+.1,.42,.06)),((x0+.12,0,H+.93),(.42,d+.1,.06)),((x1-.12,0,H+.93),(.42,d+.1,.06))):g.box(ALU,c,dd)
    g.box(MEMB,(0,0,H+.06),(w-.5,d-.5,.12))
    for (cx,cy,rw,rd,rh) in ((x0+5.5,1.5,4.4,4.4,3.2),(x1-5.0,1.0,3.4,3.4,3.0)):
        g.box(STONE,(cx,cy,H+rh/2),(rw,rd,rh));g.box(ALU,(cx,cy,H+rh+.05),(rw+.2,rd+.2,.1))
        Fr=P.WF((cx-rw/2,cy-rd/2,H),0,-1);pdoor(g,Fr,rw/2,1.0,2.1,canopy=False);P.louvre_bank(g,LOUV,ALU,P.WF((cx+rw/2,cy-rd/2,H),math.pi/2,-1),rd/2-.6,rd/2+.6,1.8,2.5,pitch=.1)
    for x in (-4.,-1.,2.):g.box(GALV,(x,4.2,H+.75),(1.0,.7,1.3));g.cyl(STRUCT,(x,4.2,H+1.4),(x,4.2,H+1.42),.32,16)
    P.tube(g,GALV,[(x0+.12,y0+.12,H+1.02),(x1-.12,y0+.12,H+1.02),(x1-.12,y1-.12,H+1.02),(x0+.12,y1-.12,H+1.02),(x0+.12,y0+.12,H+1.02)],.012,6,bend=.02,cap=False)
    # entrance: glazed doors, canopy on two columns, steps + ramp with handrails, name letters
    F=P.WF((x0,y0,0),0,-1);uc=(ent+.5)*bay;cw=bay-.5
    F.box(g,DARK,uc,1.6,.004,cw,3.2,.008);F.box(g,GLASS,uc,1.6,.03,cw-.1,3.1,.01)
    for du in (-cw/2,-cw/6,cw/6,cw/2):F.box(g,WDARK,uc+du,1.6,.05,.08,3.2,.08)
    F.box(g,WDARK,uc,2.45,.05,cw,.08,.08);F.box(g,WDARK,uc,3.2,.05,cw+.1,.1,.1)
    for du in (-.04,.04):F.box(g,ALU,uc+du,1.1,.12,.03,.9,.03)
    cd_,cwid=3.6,7.4;F.box(g,ALU,uc,3.75,cd_/2,cwid,.42,cd_);F.box(g,WHITE,uc,3.53,cd_/2,cwid-.1,.02,cd_-.1)
    for s in (-1,1):g.cyl(ALU,F.p(uc+s*(cwid/2-.35),.6,cd_-.35),F.p(uc+s*(cwid/2-.35),3.55,cd_-.35),.14,20)
    for k in range(3):F.box(g,STONE,uc,(k+1)*.075,cd_+.15+.3*(2-k),cwid+1.0,(k+1)*.15,.3)        # three steps up to the .6 m entrance platform
    F.box(g,STONE,uc,.3,cd_/2,cwid+1.0,.6,cd_)
    ru0=uc+cwid/2+.5
    rv=[F.p(ru0,0,.2),F.p(ru0+7.2,0,.2),F.p(ru0+7.2,0,1.8),F.p(ru0,0,1.8),F.p(ru0,.6,.2),F.p(ru0,.6,1.8)]
    g.mesh(STONE,rv,[(0,1,2,3),(0,4,1),(3,2,5),(0,3,5,4),(4,5,2,1)])
    for wv in (.25,1.75):P.railing(g,ALU,[F.p(ru0,.6+1e-3,wv)+Vector((0,0,0)),F.p(ru0+7.2,0,wv)],h=.9,step=1.8,kick=False,post=.04,rail=.04)
    for s in (-1,1):P.railing(g,ALU,[F.p(uc+s*(cwid/2+.2),.6,cd_-.3),F.p(uc+s*(cwid/2+.2),.15,cd_+.85)],h=.9,step=1.5,kick=False,post=.04,rail=.04)
    txt=C.text(K,'Admin_Name','燃气电厂',F.p(uc,3.78,cd_+.03),.34,BLUE,rot=(math.pi/2,0,0),extrude=.02)
    if VER>='a09':
        bpy.context.view_layer.objects.active=txt;txt.select_set(True);bpy.ops.object.convert(target='MESH');txt.select_set(False)
    g.flush();return root

# ======================= PP13 gate: piers, track, motor, guard booth (static) + PP13b sliding leaf + PP13c pedestrian leaf =======================
GT=dict(open=9.0,leaf=9.6,travel=9.9)
def build_gate():
    root=part('PP13','GateAndGuardBooth',dimensions=[22,4,3.6],vehicle_opening=GT['open'],slide_leaf='PP13b',ped_leaf='PP13c',street='-Y')
    g=G('PP13');ho=GT['open']/2
    def pier(x):
        g.box(FENCE,(x,0,1.4),(.7,.7,2.8));g.box(FENCE,(x,0,2.88),(.86,.86,.16));g.box(FENCE,(x,0,3.0),(.6,.6,.1))
    for x in (-ho-.35,ho+.35,ho+2.3):pier(x)
    lx0=-GT['leaf']/2-GT['travel']-.1;lx1=GT['leaf']/2+.1;g.box(STEEL,((lx0+lx1)/2,.32,.02),(lx1-lx0,.08,.04))   # ground rail: closed leaf + travel behind the left wall
    g.box(STRUCT,(-ho-.3,.95,.32),(.45,.32,.55));g.box(CONC,(-ho-.3,.95,.03),(.6,.5,.06))                        # gate operator
    for s in (0,1):g.cyl(GALV,(-ho-.62+s*.04,.32+(.25 if s else -.25),.0),(-ho-.62+s*.04,.32+(.25 if s else -.25),2.1),.04,8)   # guide-roller posts
    # guard booth in the fence line (sheet-gate): rendered walls, ribbon windows on three sides, flat roof with wide white fascia, door to the inside
    bx0,bx1,by0,by1,bh=ho+2.65,ho+6.85,-.25,3.55,2.95
    g.box(FENCE,((bx0+bx1)/2,(by0+by1)/2,bh/2),(bx1-bx0,by1-by0,bh));g.box(DARK,((bx0+bx1)/2,(by0+by1)/2,1.6),(bx1-bx0-.3,by1-by0-.3,2.4))
    g.box(WHITE,((bx0+bx1)/2,(by0+by1)/2,bh+.25),(bx1-bx0+.8,by1-by0+.8,.5));g.box(MEMB,((bx0+bx1)/2,(by0+by1)/2,bh+.51),(bx1-bx0+.6,by1-by0+.6,.03))
    Ff=P.WF((bx0,by0,0),0,-1);Fl=P.WF((bx0,by0,0),math.pi/2,1);Fr=P.WF((bx1,by0,0),math.pi/2,-1);Fb=P.WF((bx0,by1,0),0,1)
    for F,u0,u1 in ((Ff,.5,bx1-bx0-.5),(Fl,.4,by1-by0-.6),(Fr,.6,1.9)):
        F.box(g,DARK,(u0+u1)/2,1.65,.004,u1-u0,1.3,.008);F.box(g,GLASS,(u0+u1)/2,1.65,.025,u1-u0,1.3,.01)
        n=max(1,round((u1-u0)/.9))
        for j in range(n+1):F.box(g,WDARK,u0+j*(u1-u0)/n,1.65,.05,.06,1.36,.06)
        for vv in (1.0,2.3):F.box(g,WDARK,(u0+u1)/2,vv,.05,u1-u0+.06,.06,.06)
        F.box(g,FENCE,(u0+u1)/2,.94,.1,u1-u0+.2,.08,.2)
    pdoor(g,Fb,1.0,.9,2.1,canopy=False);g.box(CONC,(bx0+1.0,by1+.5,.07),(1.4,1.0,.14))
    g.box(STRUCT,((bx0+bx1)/2-.4,(by0+by1)/2-.6,.75),(2.2,.6,.06));g.box(DARK,((bx0+bx1)/2-.6,(by0+by1)/2-.75,1.0),(.5,.06,.35))     # desk + monitor seen through the glass
    g.box(GALV,(bx1+.35,2.2,.8),(.3,.8,.6));g.cyl(STRUCT,(bx1+.51,2.2,.8),(bx1+.53,2.2,.8),.22,16)                                  # AC condenser
    g.cyl(GALV,(bx1+.6,-.6,0),(bx1+.6,-.6,4.2),.06,10);g.box(WHITE,(bx1+.6,-.85,4.05),(.18,.35,.18));g.box(DARK,(bx1+.6,-1.04,4.05),(.12,.03,.1))   # CCTV pole
    nm=C.text(K,'Gate_Name','燃\n气\n电\n厂',(-ho-.35,-.36,1.55),.26,ALU,rot=(math.pi/2,0,0),extrude=.012);g.box(STEEL,(-ho-.35,-.355,1.55),(.42,.01,1.5))
    if VER>='a09':
        bpy.context.view_layer.objects.active=nm;nm.select_set(True);bpy.ops.object.convert(target='MESH');nm.select_set(False)
    g.flush();return root
def build_slide_leaf():
    L=GT['leaf'];root=part('PP13b','SlidingGateLeaf',dimensions=[L,.12,1.95],slide_axis='-X',travel=GT['travel'],pivot='closed position, leaf centre on the ground rail')
    g=G('PP13b');x0,x1=-L/2,L/2
    for z in (.2,1.85):g.box(STRUCT,(0,0,z),(L,.08,.1))
    for x in (x0+.05,x1-.05):g.box(STRUCT,(x,0,1.02),(.1,.1,1.75))
    n=int(L/.13)
    for i in range(1,n):g.box(STRUCT,(x0+i*L/n,0,1.02),(.03,.03,1.6))
    g.box(GALV,(0,.06,.3),(L,.025,.04))                                                       # gear rack
    for x in (x0+.6,x1-.6):g.cyl(STEEL,(x,-.04,.12),(x,.04,.12),.1,16);g.box(STRUCT,(x,0,.18),(.18,.1,.08))
    g.flush();return root
def build_ped_leaf():
    root=part('PP13c','PedestrianGateLeaf',dimensions=[1.2,.06,1.9],hinge='-X edge',swing='inwards')
    g=G('PP13c')
    for z in (.15,1.85):g.box(STRUCT,(.6,0,z),(1.2,.05,.06))
    for x in (.03,1.17):g.box(STRUCT,(x,0,1.0),(.06,.06,1.76))
    for i in range(1,10):g.box(STRUCT,(i*.12,0,1.0),(.025,.025,1.64))
    g.box(GALV,(1.1,-.05,1.05),(.12,.05,.2))
    g.flush();return root

# ======================= PP16 transmission pylon (optional, outside the lot) =======================
def build_pylon():
    root=part('PP16','TransmissionPylon',dimensions=[14,8,36],optional=True,circuits=2)
    g=G('PP16')
    for sx in (-1,1):
        for sy in (-1,1):g.box(CONC,(sx*3.5,sy*3.5,.3),(1.2,1.2,.6))
    P.lattice_column(g,GALV,(0,0,.4),23.6,7.0,2.4,2.0,.14,.08)
    P.lattice_column(g,GALV,(0,0,24.0),10.5,2.4,1.4,1.75,.11,.07)
    for z,L in ((22.4,5.2),(27.0,6.4),(31.4,5.0)):
        for s in (-1,1):
            w=(2.4+(1.4-2.4)*max(0,z-24)/10.5)/2 if z>24 else (7.0+(2.4-7.0)*(z-.4)/23.6)/2
            tip=Vector((s*L,0,z))
            for sy in (-1,1):g.angle(GALV,(s*w,sy*w,z),tip,.1,.008);g.angle(GALV,(s*w,sy*w,z+1.6),tip+Vector((0,0,.05)),.08,.008)
            for k in range(1,5):
                t=k/5;a=Vector((s*(w+(L-w)*t),0,z));g.beam(GALV,a+Vector((0,-w*(1-t),0)),a+Vector((0,w*(1-t),0)),.05,.008);g.beam(GALV,a+Vector((0,-w*(1-t),0)),a+Vector((0,0,1.6*(1-t))),.05,.008)
            P.string(g,INS,GALV,tip,tip-Vector((0,0,2.6)));g.box(GALV,tip-Vector((0,0,2.75)),(.25,.12,.2))
    for s in (-1,1):g.angle(GALV,(s*.7,0,34.5),(s*2.2,0,35.6),.08,.008)
    g.box(WHITE,(0,-3.55,3.0),(.6,.02,.4));g.box(REDP,(0,-3.56,2.4),(.5,.02,.5))                # number plate + danger plate
    g.flush();return root

BUILDERS=[('PP01',build_hall,{'q':(-62,24,120,(0,0,9),40),'front':(-90,6,95,(0,0,10),40),'gable':(15,14,48,(40,0,9),40),'eave':(-70,8,22,(-30,-14,14),40),'back':(70,22,110,(0,0,9),40)}),
          ('PP02',build_filter,{'q':(-55,18,26,(0,0,6),40),'close':(-80,12,11,(2,-2,6),45),'back':(60,20,26,(0,0,6),40)}),
          ('PP03',build_annex,{'q':(-55,20,17,(0,0,2.2),40),'back':(40,24,17,(0,0,2.2),40)}),
          ('PP04',build_hrsg,{'q':(-30,22,62,(0,10,14),40),'stair':(-20,10,24,(10,4,12),40),'top':(-60,55,30,(0,10,28),40),'back':(140,18,62,(0,10,14),40)}),
          ('PP05',build_stack,{'q':(-40,12,115,(0,0,28),35) if VER>='a09' else (-40,10,95,(0,0,28),40),'top':(-30,25,16,(0,0,52),40),'base':(-40,8,16,(0,0,4),40)}),
          ('PP06',build_duct,{'q':(-40,20,32,(0,4,10),40)}),
          ('PP07',build_cooling,{'q':(-35,24,70,(0,0,5),40),'fan':(-60,40,13,(0,-18,11),40),'inlet':(-20,6,14,(6.5,-10,2.5),45),'stair':(20,14,22,(7,16,5),40)}),
          ('PP09',build_transformer,{'q':(-40,20,20,(0,0,3.5),40),'top':(-25,45,9,(1,0,6.5),40),'back':(140,18,20,(0,0,3.5),40)}),
          ('PP10',build_switchyard,{'q':(-55,28,62,(0,0,5),40),'bay':(-70,14,18,(-9,4,4),40),'breaker':(-60,12,9,(0,-3,3),40)}),
          ('PP11',build_gas_station,{'q':(-35,30,50,(0,0,1.5),40),'skid':(-60,22,9,(0,1,1.2),40),'filter':(-120,18,9,(0,-11,2),40)}),
          ('PP12',build_admin,{'q':(-60,14,55,(0,0,7),40),'entry':(-80,6,16,(0,-9,2.5),40),'back':(60,16,55,(0,0,7),40)}),
          ('PP13',build_gate,{'q':(-70,14,26,(4,0,1.5),40),'booth':(-50,10,11,(9,0,1.6),40),'inside':(70,16,24,(4,0,1.5),40)}),
          ('PP13b',build_slide_leaf,{}),('PP13c',build_ped_leaf,{}),
          ('PP16',build_pylon,{'q':(-60,14,72,(0,0,18),38) if VER>='a09' else (-60,10,70,(0,0,18),40)})]
for pid,fn,views in BUILDERS:
    if not want(pid):continue
    root=fn();render_part(root,views);print('PART',pid,C.stats(K))

# ======================= assembly in site coordinates (lock.md 总平面) =======================
SITE_PARTS=['PP01','PP02','PP03','PP04','PP05','PP06','PP07','PP09','PP10','PP11','PP12','PP13','PP13b','PP13c','PP16']
HALL_C=(-4.,75.);GTW=[HALL_C[0]+x for x in GT_X]
TRANS_Y=(66.,75.,84.);SW_C=(58.,22.);GS_C=(77.5,87.);CT_C=(-77.5,82.);AD_C=(-42.,28.);GATE_X=12.;PYLON=((104.,52.),math.radians(122.7))
PLACED=[];SLOTS=[];LANDP=[]
def build_assembly():
    missing=[n for n in SITE_PARTS if n not in PROTOS]
    if missing:print('ASSEMBLY_SKIPPED missing',missing);return None
    site=K.part('POWER_PLANT_SITE',part_id='SITE',lot=[176,136],origin='street edge centre',street='-Y',status='model candidate, user unreviewed, no engine import')
    def put(pid,name,loc,rz=0.):
        r=P.instance(K,PROTOS[pid],name,loc,rz);r.parent=site;PLACED.append(dict(id=name,part=pid,position=[round(v,3) for v in loc],yaw_deg=round(math.degrees(rz),3)));return r
    put('PP01','TurbineHall',(HALL_C[0],HALL_C[1],0))
    for i,x in enumerate(GTW):
        put('PP02','InletFilterHouse_GT%d'%(i+1),(x,HALL_C[1]-HALL_W/2-FH['gap']-FH['d']/2,0));put('PP06','ExhaustDiffuser_GT%d'%(i+1),(x,HALL_C[1]+HALL_W/2,0))
        put('PP04','HRSG_%d'%(i+1),(x,HALL_C[1]+HALL_W/2+DUCT['l'],0));put('PP05','Stack_%d'%(i+1),(x,HALL_C[1]+HALL_W/2+DUCT['l']+STACK['y'],0))
    for name,x in (('ElectricalAnnex_ST',-36.),('ElectricalAnnex_GT',2.)):put('PP03',name,(x,HALL_C[1]-HALL_W/2-.3-2.5,0))
    put('PP07','CoolingTower',(CT_C[0],CT_C[1],0))
    for i,y in enumerate(TRANS_Y):put('PP09','MainTransformer_%d'%(i+1),(50.,y,0))
    put('PP10','Switchyard',(SW_C[0],SW_C[1],0));put('PP11','GasRegulatingStation',(GS_C[0],GS_C[1],0));put('PP12','AdminControlBuilding',(AD_C[0],AD_C[1],0))
    put('PP13','Gate',(GATE_X,0,0));put('PP13b','Gate_SlidingLeaf',(GATE_X,.32,0));put('PP13c','Gate_PedestrianLeaf',(GATE_X+GT['open']/2+.7+.02,0,0))
    py=put('PP16','TransmissionPylon_optional',(PYLON[0][0],PYLON[0][1],0),PYLON[1])
    K.root=site;g=G('SITE')
    # ---- ground: concrete hardstanding, asphalt roads, markings, lawns with curbs, parking ----
    g.box(PAVE,(0,68,-.15),(176,136,.3))
    roads=[(7.5,0,16.5,42),(-67,42,66.5,48.5),(-67,4,-60.5,132.5),(60,42,66.5,132.5),(-67,126,66.5,132.5),(-67,4,7.5,10),(37.5,36,44.5,42),(66.5,88,68.6,92),(-56.5,10,-28,15.3),(-84,49,-67,57.5)]
    for x0,y0,x1,y1 in roads:g.box(ASPH,((x0+x1)/2,(y0+y1)/2,.01),(x1-x0,y1-y0,.02))
    def dashes(a,b,w=.15,dash=3.,gap=3.,m=MARKW):
        a=Vector(a);b=Vector(b);d=b-a;L=d.length;u=d.normalized();rz=math.atan2(u.y,u.x);t=0.
        while t<L:
            e=min(t+dash,L);c=a+u*((t+e)/2);g.box(m,(c.x,c.y,.0225),(e-t,w,.005),rz);t+=dash+gap
    for a,b in (((-60.5,45.25),(60,45.25)),((-63.75,48.5),(-63.75,126)),((63.25,48.5),(63.25,126)),((-60.5,129.25),(60,129.25)),((12,4),(12,42)),((-60.5,7),(7.5,7))):dashes(a,b)
    g.box(MARKW,(12,3.0,.0225),(9.0,.4,.005));g.box(MARKW,(41,37.0,.0225),(7.0,.3,.005))                          # stop lines (gate, switchyard)
    for i in range(12):x=-56+2.5*i;g.box(MARKW,(x,12.65,.0225),(.12,5.3,.005))
    g.box(MARKW,(-42.25,15.25,.0225),(27.5,.12,.005))
    for i in range(11):g.box(CONC,(-54.75+2.5*i,14.6,.075),(1.6,.15,.15))                                        # wheel stops
    for i in range(11):SLOTS.append(dict(id=i,position=[-54.75+2.5*i,12.65,.02],width=2.5,length=5.3,yaw=90.0))
    def lawn(x0,y0,x1,y1):
        g.box(LAWN,((x0+x1)/2,(y0+y1)/2,.06),(x1-x0,y1-y0,.12))
        for c,dd in ((((x0+x1)/2,y0,.09),(x1-x0+.15,.15,.18)),(((x0+x1)/2,y1,.09),(x1-x0+.15,.15,.18)),((x0,(y0+y1)/2,.09),(.15,y1-y0,.18)),((x1,(y0+y1)/2,.09),(.15,y1-y0,.18))):g.box(CONC,c,dd)
    for r in ((-86.5,.5,6.8,3.6),(17.2,.5,86.5,6.6),(-60.3,15.8,-47.4,19.6),(-28.6,15.8,-23.7,19.6),(-60.3,36.6,-23.7,41.2)):lawn(*r)
    if VER>='a08':
        for r in ((-22.2,15.8,-11.0,40.4),(-8.0,15.8,4.6,40.4)):lawn(*r)                                         # lawn east of the office block (reference B); the paved gap x -11..-8 is the footpath
    if VER>='a09':
        g.box(ASPH,(-9.5,41.2,.015),(3.0,1.0,.02))                                                                # footpath link across the south road edge
        for i in range(6):g.box(MARKW,(-9.5,42.7+i*1.0,.023),(2.6,.45,.005))                                      # crosswalk to the turbine hall apron
        for x0w,x1w in ((-23.7,-22.2),(-11.0,-8.0),(4.6,7.4)):
            g.box(PAVE,((x0w+x1w)/2,28.1,.025),(x1w-x0w,24.8,.05))
    g.box(PAVE,(-38,17.7,.03),(18.5,4.2,.06))                                                                      # admin forecourt slabs
    # ---- perimeter wall (sheet-gate panels 6): precast panels with one horizontal joint, pilasters with caps, coping; gap at the gate ----
    def wall(a,b):
        a=Vector((a[0],a[1],0));b=Vector((b[0],b[1],0));d=b-a;L=d.length;n=max(1,round(L/3.0));u=d.normalized();rz=math.atan2(u.y,u.x)
        for k in range(n+1):q=a+d*(k/n);g.box(FENCE,(q.x,q.y,1.27),(.36,.36,2.55),rz);g.box(FENCE,(q.x,q.y,2.6),(.46,.46,.1),rz)
        for k in range(n):
            q0=a+d*(k/n);q1=a+d*((k+1)/n);c=(q0+q1)/2;lp=(q1-q0).length-.36
            g.box(FENCE,(c.x,c.y,1.15),(lp,.12,2.3),rz);g.box(FENCE,(c.x,c.y,2.36),(lp,.24,.08),rz);g.box(JOINT,(c.x,c.y,1.15),(lp,.13,.02),rz)
    gx0=GATE_X-GT['open']/2-.7;gx1=GATE_X+GT['open']/2+2.65+4.2
    for a,b in (((-88,0),(gx0,0)),((gx1,0),(88,0)),((88,0),(88,136)),((88,136),(-88,136)),((-88,136),(-88,0))):wall(a,b)
    # ---- circulating-water bridge: hall left gable -> cooling tower risers, across the left ring road ----
    for yy in (CT_C[1]-18,CT_C[1]-6):
        P.tube(g,STEEL,[(HALL_C[0]-HALL_L/2-.1,yy,5.5),(CT_C[0]+CT['w']/2+.35,yy,5.5)],.38,16)
        for x in (HALL_C[0]-HALL_L/2-.4,CT_C[0]+CT['w']/2+.6):P.flange(g,STEEL,(x,yy,5.5),(1,0,0),.38)
    for x in (-68.,-59.5,-54.,-50.):
        for yy in (CT_C[1]-19.3,CT_C[1]-4.7):g.hbeam(STRUCT,(x,yy,0),(x,yy,5.05),.3,.3);g.box(CONC,(x,yy,.15),(.7,.7,.3))
        g.hbeam(STRUCT,(x,CT_C[1]-19.3,5.0),(x,CT_C[1]-4.7,5.0),.3,.35)
        for yy in (CT_C[1]-18,CT_C[1]-6):g.box(STRUCT,(x,yy,5.13),(.4,.9,.12))
    # ---- natural-gas line: regulating station -> bridge over the right road -> low run behind the hall (under the diffusers) -> each gas turbine ----
    zp=1.1;ox=GS_C[0]-GS['w']/2-.5;oy=GS_C[1]+12
    P.tube(g,GASY,[(ox,oy,zp),(67.8,oy,zp),(67.8,oy,5.6),(58.7,oy,5.6),(58.7,oy,zp),(58.7,93.,zp),(GTW[0]-1.5,93.,zp)],.22,16,bend=.6)
    for x in GTW:P.tube(g,GASY,[(x,93.,zp),(x,90.15,zp)],.16,12);P.valve(g,STEEL,REDP,(x,91.6,zp),(0,1,0),.16)
    P.valve(g,STEEL,REDP,(38.,93.,zp),(1,0,0),.22)
    for x in (59.4,67.2):
        for yy in (oy-1.0,oy+1.0):g.hbeam(STRUCT,(x,yy,0),(x,yy,5.3),.25,.25);g.box(CONC,(x,yy,.15),(.6,.6,.3))
        g.hbeam(STRUCT,(x,oy-1.0,5.3),(x,oy+1.0,5.3),.25,.3)
    x=GTW[0]
    while x<58:
        g.box(CONC,(x,93.,.2),(.5,.5,.4));g.box(STRUCT,(x,93.,.6),(.12,.12,.4));g.box(STRUCT,(x,93.,.84),(.12,.5,.06));x+=4.
    # ---- generator bus ducts: transformers -> hall right gable ----
    for y in TRANS_Y:
        g.box(STRUCT,(42.55,y,4.3),(5.0,1.2,1.0))
        for yy in (y-.5,y+.5):g.hbeam(STRUCT,(42.5,yy,0),(42.5,yy,3.75),.2,.2)
    # ---- overhead lines: transformer HV bushings -> line gantry -> switchyard incoming bays; outgoing bays -> optional pylon ----
    gx=57.0;gys=(61.6,70.75,79.75,88.9)
    for yy in gys:P.lattice_column(g,STRUCT,(gx,yy,.2),15.0,1.1,.7,1.4);g.box(CONC,(gx,yy,.15),(1.4,1.4,.3))
    P.lattice_beam(g,GALV,(gx,gys[0],14.6),(gx,gys[-1],14.6),.9,1.2)
    bays=[SW_C[0]-SY['w']/2+8.5+9*i for i in range(5)];gyy=SW_C[1]+SY['d']/2-2.2
    for ti,(ty,bx) in enumerate(zip(TRANS_Y,(bays[2],bays[1],bays[0]))):
        for k,py_ in enumerate((-.9,0,.9)):
            s=(gx,ty+py_,14.1);b=(gx,ty+py_,12.5);P.string(g,INS,GALV,s,b)
            P.catenary(g,BUS,(50+1.3,ty+py_,4.9+3.9),b,.25,.025,10)
            P.catenary(g,BUS,b,(bx+(-2.6,0,2.6)[k],gyy,11.4),1.1,.025,24)
    pc=Vector((PYLON[0][0],PYLON[0][1],0));Rz=Matrix.Rotation(PYLON[1],3,'Z')
    for side,bx in ((-1,bays[3]),(1,bays[4])):
        for k,(z,L) in enumerate(((22.4,5.2),(27.0,6.4),(31.4,5.0))):
            tip=pc+Rz@Vector((side*L,0,z-2.75));P.catenary(g,BUS,(bx+(-2.6,0,2.6)[k],gyy,11.4),tip,1.4,.025,28)
    # ---- yard lighting, fire hydrants, signage ----
    for x,y in ((-58,41.2),(-30,41.2),(-2,41.2),(26,41.2),(54,49.6),(-68.4,62),(-68.4,94),(-68.4,122),(67.9,56),(67.9,118),(-30,134.),(2,134.),(34,134.),(5.8,22.),(-68.2,14.)):
        g.box(CONC,(x,y,.25),(.45,.45,.5));g.cyl(GALV,(x,y,.5),(x,y,8.5),.10,12,r1=.065)
        d=Vector((-x,68-y,0)).normalized()*.9;g.cyl(GALV,(x,y,8.4),(x+d.x,y+d.y,8.55),.04,8);g.box(STRUCT,(x+d.x,y+d.y,8.5),(.6,.28,.1),math.atan2(d.y,d.x));g.box(WHITE,(x+d.x,y+d.y,8.44),(.5,.22,.02),math.atan2(d.y,d.x))
    for x,y in ((-59.8,52.),(-59.8,100.),(59.3,52.),(59.3,104.),(30.,49.4),(-20.,49.4),(-28.,41.0)):
        g.cyl(REDP,(x,y,0),(x,y,.75),.1,14);g.sphere(REDP,(x,y,.78),.11,12,6);g.cyl(REDP,(x-.18,y,.55),(x+.18,y,.55),.05,10);g.cyl(REDP,(x,y-.18,.55),(x,y+.18,.55),.05,10)
    g.flush()
    # ---- restrained greenery: shared kapok trees + scrub shrubs (hospital lesson: only where a real plant would plant them) ----
    try:
        extraT=[(-16.6,23.5,.12),(-2.0,33.0,.12),(-16.6,35.5,.12)] if VER>='a08' else []
        extraS=[(x,y,.12) for x,y in ((-20.5,17.6),(-18.4,17.6),(-13.0,17.6),(-6.2,17.6),(-4.0,17.6),(2.8,17.6),(2.8,20.0),(-6.2,38.6),(2.8,38.6))] if VER>='a08' else []
        vegetation('Kapok','art/assets/authored/city/kapok-tree-v01/game-a01/CN_Kapok_LOD0.fbx',7.5,[(x,2.0,.12) for x in range(-84,4,9)]+[(x,3.4,.12) for x in range(29,86,9)]+[(-56,39,.12),(-42,39.2,.12),(-28,39,.12),(-53,17.6,.12),(-26,17.6,.12)]+extraT,site,True)
        vegetation('ShrubA','art/assets/authored/city/scrub-shrub-v01/a04/SM_ScrubShrub_A.fbx',.75,[(x,19.0,.12) for x in (-59.,-56.5,-54.,-51.5,-49.)]+[(x,19.0,.12) for x in (-28.,-25.)]+extraS,site)
    except Exception as e:print('VEGETATION_FAIL',e)
    return site
LEAF=C.mat('PP_RealLeaves',(.065,.15,.035),.86)
BARK=C.granite('PP_RealBark',slab=(.08,.6),joint=.001,col1=(.11,.065,.033),col2=(.09,.06,.028),rough=.92)
def vegetation(label,rel,height,placements,parent,tree=False):
    src=R/rel
    if not src.exists():raise FileNotFoundError(src)
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(src));new=list(set(bpy.data.objects)-before)
    meshes=[o for o in new if o.type=='MESH' and 'Flowers' not in o.name];mws={o.name:o.matrix_world.copy() for o in meshes}
    pts=[mws[o.name]@Vector(c) for o in meshes for c in o.bound_box]
    lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    scale=height/(hi.z-lo.z);offset=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z));sources=[]
    for ob in meshes:
        ob.data.transform(Matrix.Scale(scale,4)@Matrix.Translation(offset)@mws[ob.name]);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
        ob.data.materials.clear();ob.data.materials.append(BARK if tree and 'Wood' in ob.name else LEAF);sources.append(ob)
    if tree:
        import hospital_landscape_v02
        sources.append(hospital_landscape_v02.add_crown(K,C,[ob for ob in sources if 'Wood' in ob.name],height,LEAF))
    for i,(x,y,z) in enumerate(placements):
        ang=(i*2.399+len(label))%(2*math.pi)
        for ob in sources:
            q=bpy.data.objects.new(label+'_'+str(i)+'_'+ob.name,ob.data);K.col.objects.link(q);q.parent=parent;q.location=(x,y,z);q.rotation_euler.z=ang
            if tree:q.scale=(.86,1.,1.12)[i%3]*Vector((1,1,1))
        LANDP.append(dict(asset=rel,position=[x,y,z],height=height*((.86,1.,1.12)[i%3] if tree else 1),yaw=ang))
    for ob in new+[s for s in sources if s not in new]:
        if ob.name in bpy.data.objects and ob.parent is None and not ob.name.startswith(label+'_'):bpy.data.objects.remove(ob,do_unlink=True)
SITE=build_assembly() if ASM else None
if SITE:
    # prototypes move to a labelled display row south of the street (parts review); the assembly renders hide them
    xs=-140.
    for pid in SITE_PARTS:
        pr=PROTOS[pid];w=(pr.get('dimensions') or [10,10,10])[0];pr.location=(xs+w/2,-90.,0);xs+=w+12.
    cam,cd,items=CAM if CAM else C.studio(K,800)
    if not CAM:
        for it in items:
            if it.name=='REVIEW_floor':it.location.z=-.012
    protos=set();[protos.update({pr}|{o for o in K.col.objects if o.parent==pr}) for pr in PROTOS.values()]
    for o in K.col.objects:o.hide_render=o in protos
    for it in items:
        if it.name=='REVIEW_floor':it.scale=(3,3,1);it.location.y=60
    if VER>='a08':
        def ctx_plane(name,m,x0,y0,x1,y1,z):
            me=bpy.data.meshes.new(name);me.from_pydata([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)],[],[(0,1,2,3)]);me.materials.append(m)
            ob=bpy.data.objects.new(name,me);K.col.objects.link(ob);return ob
        ext=4000 if VER>='a09' else 1500
        ctx_plane('REVIEW_context_grass',LAWN,-ext,-ext,ext,ext,-.008)
        ctx_plane('REVIEW_context_street',ASPH,-ext,-16,ext,-.4,-.004)
        for i in range(-120 if VER>='a09' else -60,120 if VER>='a09' else 60):ctx_plane('REVIEW_context_dash%d'%i,MARKW,i*6.,-8.3,i*6.+3.,-8.1,-.002)
        for it in items:
            if it.name=='REVIEW_floor':it.hide_render=True
    if VER>='a09' and 'ShaderNodeLightPath' not in [n.bl_idname for n in K.scene.world.node_tree.nodes]:
        wn=K.scene.world.node_tree.nodes;wl=K.scene.world.node_tree.links
        bg_cam=wn.new('ShaderNodeBackground');bg_cam.inputs[0].default_value=(.58,.66,.75,1);bg_cam.inputs[1].default_value=1.0
        lp=wn.new('ShaderNodeLightPath');mx=wn.new('ShaderNodeMixShader')
        wl.new(lp.outputs['Is Camera Ray'],mx.inputs['Fac']);wl.new(wn.get('Background').outputs[0],mx.inputs[1]);wl.new(bg_cam.outputs[0],mx.inputs[2])
        wl.new(mx.outputs[0],wn.get('World Output').inputs['Surface'])
    AV={'aerial':(-58,30,330,(2,70,6),40),'front':(-90,9,190,(2,60,8),40),'gate':(-62,14,60,(14,8,2),40),'back':(118,26,300,(0,72,8),40),
        'hrsg':(80,18,95,(2,108,16),40),'eye':(-35,2.2,40,(0,62,5),32),'top':(-90,89.5,300,(0,68,0),40),'yard':(-30,22,70,(55,40,6),40)}
    for vn,(az,el,D,t,lens) in AV.items():
        if VIEWS!='all' and vn not in VIEWS.split(','):continue
        cd.type='PERSP';shot_pp(K,cam,cd,O/('site-'+vn+'.png'),orb(az,el,D,t),t,lens,(1600,1000),max(SAMPLES,32))
    for o in K.col.objects:o.hide_render=False
    manifest=dict(units='m',frame='origin = street edge centre, X along the street, Y into the site, Z up; street (Y<0) not included',lot=[176,136],
        parts=PLACED,parking_slots=SLOTS,landscape=LANDP,
        connections=[dict(id='vehicle-gate',type='vehicle',position=[GATE_X,0,0],width=GT['open'],gate_leaf='Gate_SlidingLeaf',slide_axis='-X',travel=GT['travel']),
                     dict(id='pedestrian-gate',type='pedestrian',position=[GATE_X+GT['open']/2+1.3,0,0],width=1.2),
                     dict(id='gas-inlet',type='gas_pipeline',position=[GS_C[0]+GS['w']/2+.3,GS_C[1]-15,-.5]),
                     dict(id='power-out',type='hv_line_220kv',position=[PYLON[0][0],PYLON[0][1],0],note='optional pylon; or the switchyard outgoing gantries')],
        status='model candidate, user unreviewed, no engine import',reference='concept-B-gas.png')
    (O/'assembly.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

# ---------------- save ----------------
K.scene.render.engine='BLENDER_EEVEE'
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.shading.type='MATERIAL';sp.clip_start=.2;sp.clip_end=2000;sp.overlay.show_overlays=False
            eye=Vector(orb(-58,30,330,(2,70,6)));tgt=Vector((2,70,6))
            sp.region_3d.view_location=tgt;sp.region_3d.view_distance=(eye-tgt).length;sp.region_3d.view_rotation=(tgt-eye).to_track_quat('-Z','Y')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'power-plant-kit.blend'))
lib=O/'parts';lib.mkdir(exist_ok=True)
for pid,root in PROTOS.items():
    obs={root}|{o for o in K.col.objects if o.parent==root}
    bpy.data.libraries.write(str(lib/(root.name+'.blend')),obs,fake_user=True,compress=True)
(O/'metrics.json').write_text(json.dumps(C.stats(K),indent=2),encoding='utf-8')
append_event(EP,dict(kind='action_finished',action_id=AID,technical_status='succeeded',user_acceptance='unreviewed',evidence=[dict(path=str(Path(__file__)),role='actual_script'),dict(path=str(O/'power-plant-kit.blend'),role='editable_model')]+[dict(path=str(p),role='actual_render') for p in O.glob('*.png')]))
print('POWER_PLANT_DONE',C.stats(K))
