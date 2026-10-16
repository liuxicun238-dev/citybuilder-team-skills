"""Template for multi-part city & industrial building generators (Blender 5.x; metres, Z up).
Works standalone from the city-building-modeling skill package or inside tools/pipeline/.
Copy to tools/pipeline/build_city_<building>_v01.py (or any working folder) and fill in BUILDERS + build_assembly().
"""
import bpy,math,os,sys,json
from pathlib import Path
from mathutils import Vector,Matrix

_HERE=Path(__file__).resolve().parent
R=_HERE.parents[1] if (_HERE.parents[1]/'tools/pipeline').exists() else _HERE.parent
for _p in (R/'tools/pipeline', _HERE.parent/'scripts', _HERE/'scripts', _HERE):
    if _p.exists() and str(_p) not in sys.path:sys.path.insert(0,str(_p))

import city_kit_common as C
import building_kit_v01 as B
try:
    from record_modeling_step import append_event
except Exception:
    def append_event(*a,**kw):pass

PARAMS={}
def E(n,d):
    v=type(d)(os.environ.get(n,d));PARAMS[n]=v;return v

ASSET='example-facility-v01'
VER=E('BLD_VERSION','a01');ONLY=E('BLD_PARTS','all');VIEWS=E('BLD_VIEWS','all');SAMPLES=E('BLD_SAMPLES',32);ASM=E('BLD_ASSEMBLY',1)
O=R/'art/assets/authored/city'/ASSET/VER;O.mkdir(parents=True,exist_ok=True)
REF=R/'art/references/city'/ASSET
append_event(ASSET,dict(kind='action_started',action_id=f'{ASSET}-{VER}',reference=[str(REF/'concept.png')],operation=dict(script=str(Path(__file__)),params=PARAMS)))

K=C.Kit('CITY_BUILDING');PROTOS={}
M=B.standard_palette(C,prefix='BLD',accent=(.012,.11,.44))
globals().update(M)  # exposes CLAD, CLAD2, ACCENT, ROOF, MEMB, CONC, PLINTH, GLASS, ALU, DOOR, STEEL, STRUCT, YEL, GASY, GRATE, LOUV, DARK, GALV, INSUL, STONE, WDARK, FENCE, PAVE, ASPH, MARKW, LAWN, etc.

def want(pid):return ONLY=='all' or pid in ONLY.split(',')
def part(pid,name,**props):
    r=K.part(pid+'_'+name,part_id=pid,**props);PROTOS[pid]=r;return r
def G(pid):return B.Geo(K,pid)

CAM=None
def render_part(root,views):
    global CAM
    if CAM is None:
        cam,cd,items=C.studio(K,800)
        for it in items:
            if it.name=='REVIEW_floor':it.location.z=-.012
        CAM=(cam,cd,items)
    cam,cd,items=CAM;cd.type='PERSP'
    mine={root}|{o for o in K.col.objects if o.parent==root}
    for o in K.col.objects:o.hide_render=o not in mine
    for vn,(az,el,D,t,lens) in views.items():
        if VIEWS!='all' and vn not in VIEWS.split(','):continue
        B.shot_building(K,cam,cd,O/(root['part_id']+'-'+vn+'.png'),B.orb(az,el,D,t),t,lens,(1400,950),SAMPLES)
    for o in K.col.objects:o.hide_render=False

# ======================= B01 example industrial hall (level 1+2+3 details) =======================
def build_main_hall():
    L,W,HE,HR=48.,20.,14.,16.2
    root=part('B01','MainHall',dimensions=[L,W,HR])
    g=G('B01');x0,x1,y0,y1=-L/2,L/2,-W/2,W/2
    g.box(PLINTH,(0,0,.5),(L+.12,W+.12,1.0));g.box(DARK,(0,0,HE/2),(L-.4,W-.4,HE-.4))
    # Front/back walls with profiled ribs, accent band, ribbon windows, personnel doors, and corner downpipes
    for (F,front) in ((B.WF((x0,y0,0),0,-1),True),(B.WF((x0,y1,0),0,1),False)):
        holes=[(4.,L-4.,8.8,10.2),(4.,L-4.,4.0,5.2)]
        if front:holes+=[(7.2,8.4,0.,2.3)]
        F.box(g,CLAD,L/2,(HE+1.)/2,-.04,L,HE-1.,.08)
        B.ribbed(g,CLAD,F,0,L,1.0,HE,pitch=.30,skip=holes,base=False)
        F.box(g,ACCENT,L/2,11.2,.02,L,1.2,.05)
        B.ribbon_window(g,F,4.,L-4.,8.8,10.2,GLASS,ALU,mull=1.5)
        B.ribbon_window(g,F,4.,L-4.,4.0,5.2,GLASS,ALU,mull=1.5)
        if front:B.person_door(g,F,7.8,DOOR,ALU,WHITE,1.2,2.2,canopy=True)
        for u in (.4,L-.4):B.downpipe(g,GALV,STRUCT,F,u,.2,HE-.2)
    # Gable walls with sloped top ribs and roll-up equipment door
    for (F,has_roller) in ((B.WF((x0,y0,0),math.pi/2,1),True),(B.WF((x1,y0,0),math.pi/2,-1),False)):
        vtop=lambda u:HE+(HR-HE)*(1.-abs(u-W/2)/(W/2))
        B.wall_poly(g,CLAD,F,[(0,1.),(W,1.),(W,HE),(W/2,HR),(0,HE)],-.08,0.)
        holes=[(W/2-2.5,W/2+2.5,0.,5.0)] if has_roller else []
        B.ribbed(g,CLAD,F,0,W,1.0,HR,pitch=.30,vtop=vtop,skip=holes,base=False)
        if has_roller:B.roller_door(g,F,W/2-2.5,W/2+2.5,5.0,DOOR,ALU,CLAD2)
    # Double-pitched standing-seam roof + ridge ventilator
    for s in (-1,1):
        B.wall_poly(g,ROOF,B.WF((x0,0,0),0,1),[(-0.4,HR),(L+.4,HR)],0,s*(W/2+.5))
    g.box(CLAD2,(0,0,HR+.45),(L*.6,2.2,.9));g.box(ROOF,(0,0,HR+.95),(L*.6+.3,2.5,.1))
    g.flush();return root

# ======================= B02 example gate + sliding leaf =======================
GT=dict(open=8.0,leaf=8.6,travel=8.9)
def build_gate():
    root=part('B02','GateAndBooth',dimensions=[18,4,3.4],vehicle_opening=GT['open'])
    g=G('B02');ho=GT['open']/2
    for x in (-ho-.35,ho+.35):
        g.box(FENCE,(x,0,1.4),(.7,.7,2.8));g.box(FENCE,(x,0,2.88),(.86,.86,.16))
    B.mesh_text(K,C,'Gate_Sign','示\n范\n建\n筑',(-ho-.35,-.36,1.55),.24,ALU,rot=(math.pi/2,0,0),extrude=.012)
    g.flush();return root

def build_slide_leaf():
    L=GT['leaf'];root=part('B02b','SlidingGateLeaf',dimensions=[L,.12,1.9],slide_axis='-X',travel=GT['travel'])
    g=G('B02b');x0,x1=-L/2,L/2
    for z in (.2,1.8):g.box(STRUCT,(0,0,z),(L,.08,.1))
    for i in range(int(L/.14)+1):g.box(STRUCT,(x0+i*L/int(L/.14),0,1.0),(.03,.03,1.55))
    g.flush();return root

BUILDERS=[
    ('B01',build_main_hall,{'q':(-58,22,72,(0,0,7),40),'front':(-90,8,65,(0,0,7),40)}),
    ('B02',build_gate,{'q':(-65,14,22,(2,0,1.5),40)}),
    ('B02b',build_slide_leaf,{}),
]
for pid,fn,views in BUILDERS:
    if not want(pid):continue
    root=fn();render_part(root,views);print('PART',pid,C.stats(K))

# ======================= Site Assembly =======================
SITE_PARTS=['B01','B02','B02b']
PLACED=[];SLOTS=[];LANDP=[]
def build_assembly():
    if any(n not in PROTOS for n in SITE_PARTS):return None
    site=K.part('FACILITY_SITE',part_id='SITE',lot=[100,80],origin='street edge centre',street='-Y')
    def put(pid,name,loc,rz=0.):
        r=B.instance(K,PROTOS[pid],name,loc,rz);r.parent=site
        PLACED.append(dict(id=name,part=pid,position=[round(v,3) for v in loc],yaw_deg=round(math.degrees(rz),3)));return r
    put('B01','MainHall',(0.,44.,0.))
    put('B02','Gate',(0.,0.,0.));put('B02b','Gate_SlidingLeaf',(0.,.32,0.))
    K.root=site;g=G('SITE')
    g.box(PAVE,(0,40,-.15),(100,80,.3))
    g.box(ASPH,(0,12,.01),(8.,24.,.02));B.road_dashes(g,MARKW,(0,2),(0,22))
    B.crosswalk(g,MARKW,0.,20.,n_stripes=5)
    B.parking_row(g,MARKW,CONC,-36.,10.,6,slots_out=SLOTS)
    B.curbed_lawn(g,LAWN,CONC,10.,4.,44.,18.)
    gx0=-GT['open']/2-.7;gx1=GT['open']/2+.7
    for a,b in (((-50,0),(gx0,0)),((gx1,0),(50,0)),((50,0),(50,80)),((50,80),(-50,80)),((-50,80),(-50,0))):
        B.precast_wall(g,FENCE,JOINT,a,b)
    for x,y in ((-25,22),(25,22)):B.yard_light(g,CONC,GALV,STRUCT,WHITE,x,y,aim_xy=(0,40))
    B.fire_hydrant(g,REDP,-12,24)
    g.flush();return site

SITE=build_assembly() if ASM else None
if SITE:
    xs=-80.
    for pid in SITE_PARTS:
        pr=PROTOS[pid];w=(pr.get('dimensions') or [10,10,10])[0];pr.location=(xs+w/2,-50.,0);xs+=w+8.
    cam,cd,items=CAM if CAM else C.studio(K,800)
    protos=set();[protos.update({pr}|{o for o in K.col.objects if o.parent==pr}) for pr in PROTOS.values()]
    for o in K.col.objects:o.hide_render=o in protos
    B.setup_site_review_context(K,LAWN,ASPH,MARKW,items)
    for vn,(az,el,D,t,lens) in {'aerial':(-58,28,190,(0,40,5),40),'front':(-90,10,130,(0,40,6),40)}.items():
        if VIEWS!='all' and vn not in VIEWS.split(','):continue
        B.shot_building(K,cam,cd,O/('site-'+vn+'.png'),B.orb(az,el,D,t),t,lens,(1600,1000),max(SAMPLES,32))
    for o in K.col.objects:o.hide_render=False
    (O/'assembly.json').write_text(json.dumps(dict(units='m',lot=[100,80],parts=PLACED,parking_slots=SLOTS,landscape=LANDP),ensure_ascii=False,indent=2),encoding='utf-8')

K.scene.render.engine='BLENDER_EEVEE'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'building-kit.blend'))
append_event(ASSET,dict(kind='action_finished',action_id=f'{ASSET}-{VER}',technical_status='succeeded',user_acceptance='unreviewed',evidence=[dict(path=str(Path(__file__)),role='actual_script'),dict(path=str(O/'building-kit.blend'),role='editable_model')]+[dict(path=str(p),role='actual_render') for p in O.glob('*.png')]))
print('BUILDING_DONE',C.stats(K))
