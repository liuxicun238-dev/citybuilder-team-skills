"""Original isolated nose: blended volumes and real inferior nasal cavities."""
from pathlib import Path
import numpy as np,json,sys
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
R=Path('__CHAR_PROJECT__');out=R/'art/assets/authored/city/citizen-nose-sculpt-v01/a02';out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'tools/pipeline'))
from record_modeling_step import append_event
append_event('character-modeling-skill-v01',dict(kind='action_started',technical_status='pending',objective='Original nose volume with inferior-facing cavities from local clay reference',operation=dict(script=str(Path(__file__).resolve())),reference=[str(R/'art/references/citizen-nose-clay-v01/reference.png')]))
step=.035;xs=np.arange(-3.4,3.4,step);ys=np.arange(-.8,7.4,step);zs=np.arange(-1,3.2,step)
X,Y,Z=np.meshgrid(xs,ys,zs,indexing='ij')
def ell(c,r):return (np.sqrt(((X-c[0])/r[0])**2+((Y-c[1])/r[1])**2+((Z-c[2])/r[2])**2)-1)*min(r)
def smin(a,b,k):
 h=np.maximum(k-np.abs(a-b),0)/k;return np.minimum(a,b)-h*h*k*.25
def smax(a,b,k):return -smin(-a,-b,k)
field=ell((0,3.1,-.22),(3.1,3.6,.35))
# Smoothly varying bridge section; roots widen into the glabella.
t=np.clip(Y,1.7,6.25)
width=PchipInterpolator([1.7,2.3,3.2,4.2,5.3,6.25],[.72,.64,.52,.43,.42,.60])(t)
depth=PchipInterpolator([1.7,2.3,3.2,4.2,5.3,6.25],[1.00,.97,.76,.53,.30,.12])(t)
bridge=(np.sqrt((X/width)**2+((Z-(depth-.06))/depth)**2)-1)*np.minimum(width,depth)
bridge=np.maximum(bridge,np.maximum(1.7-Y,Y-6.25));field=smin(field,bridge,.40)
field=smin(field,ell((0,1.80,.35),(1.48,.85,.63)),.42)
for sg in [-1,1]:
 field=smin(field,ell((sg*.20,2.02,1.51),(.57,.57,.63)),.36)
 field=smin(field,ell((sg*.95,1.62,.78),(.58,.48,.61)),.38)
 field=smin(field,ell((sg*.67,2.65,.23),(.70,1.25,.42)),.36)
field=smin(field,ell((0,1.35,1.03),(.24,.32,.40)),.22)
# Philtrum support under columella, terminating in the surrounding skin pad.
field=smin(field,ell((0,.85,.08),(.46,.65,.25)),.32)
for sg in [-1,1]:
 dy=Y-1.22;dz=Z-1.02
 long=.80*dy-.60*dz;cross=.60*dy+.80*dz
 hole=(np.sqrt(((X-sg*.83)/.31)**2+(long/.60)**2+(cross/.27)**2)-1)*.27
 field=smax(field,-hole,.065)
field=gaussian_filter(field,.6)
v,f,_,_=marching_cubes(field,0,spacing=(step,step,step));v+=np.array([xs[0],ys[0],zs[0]])
with (out/'nose.obj').open('w',encoding='utf8') as stream:
 for p in v:stream.write('v '+' '.join(f'{q:.7f}' for q in p)+'\n')
 stream.write('g nose\n')
 for face in f:stream.write('f '+' '.join(str(int(i)+1) for i in face)+'\n')
(out/'construction.json').write_text(json.dumps(dict(unit='cm',axes='X lateral Y superior Z outward',voxel_cm=step,reference=str(R/'art/references/citizen-nose-clay-v01/reference.png'),features=['tapered bridge','paired tip domes','alar wings','columella','two inferior oblique blind cavities','philtrum support'],limitations=['Designed dimensions, not measured anatomy','Single reference view','No UV/rigging'],status='awaiting actual renders'),indent=2),encoding='utf8')
append_event('character-modeling-skill-v01',dict(kind='action_finished',technical_status='succeeded',internal_visual_status='unreviewed',evidence=[dict(path=str(out/'nose.obj'),role='source_model')]))
