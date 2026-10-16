"""Local chin shape study, preserve upper face and neck attachment topology."""
from pathlib import Path
import numpy as np,json,sys,hashlib
from scipy.interpolate import PchipInterpolator
R=Path('__CHAR_PROJECT__');root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'mouth-fit-v06/head-neck.obj';out=root/'chin-refine-v02';out.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'tools/pipeline'));from record_modeling_step import append_event
append_event('character-modeling-skill-v01',dict(kind='action_started',technical_status='pending',objective='Round chin projection and soften labiomental transition while protecting lips nose ears',operation=dict(script=str(Path(__file__).resolve())),reference=[str(R/'art/references/citizen-mouth-clay-v01/reference.png')]))
lines=src.read_text().splitlines();v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]);old=v.copy();x,y,z=old.T
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
front=smooth((-z-8.5)/2.8)
vertical=smooth((y+.6)/1.1)*(1-smooth((y-3.45)/.8))
lateral=1-smooth((np.abs(x)-2.4)/2.3)
w=front*vertical*lateral
profile=PchipInterpolator([-.6,0,.5,1,1.8,2.5,3.2,3.8,4.25],[-10.3,-11.44,-12.2,-12.65,-13.,-12.95,-12.75,-12.78,-13.08])
target=profile(np.clip(y,-.6,4.25))+.085*x*x
# Smooth displacement field follows existing volume rather than imposing a flat transverse slab.
v[:,2]=z+front*vertical*(.38*np.exp(-(x/3.1)**4-((y-1.7)/1.3)**2)-.14*np.exp(-(x/2.4)**4-((y-3.2)/.65)**2))
# Gently reduce the block-like frontal width and turn the lower corners upward.
shape=front*vertical*np.exp(-((y-1.8)/1.5)**4)*(1-smooth((np.abs(x)-3.0)/2))
v[:,0]=x*(1-.055*shape)
v[:,1]=y+.10*shape*smooth((np.abs(x)-1.1)/2.2)
protected=(y>=4.25)|(z>=-8.5)|(np.abs(x)>=5)
assert np.max(np.abs(v[protected]-old[protected]))<1e-12
k=0
with (out/'head-neck.obj').open('w',encoding='utf8') as f:
 for l in lines:
  if l.startswith('v '):l='v '+' '.join(f'{q:.8f}' for q in v[k]);k+=1
  f.write(l+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),units='cm',method='Local longitudinal PCHIP chin profile with rounded transverse section and compact deformation weights',protected_vertices=int(protected.sum()),protected_max_displacement_cm=0,changed_vertices=int(np.count_nonzero(np.linalg.norm(v-old,axis=1)>1e-8)),max_displacement_cm=float(np.max(np.linalg.norm(v-old,axis=1))),limitations=['Single-view reference, profile depth is a design assumption','Existing mouth remains unapproved','No topology or animation upgrade']),indent=2),encoding='utf8')
append_event('character-modeling-skill-v01',dict(kind='action_finished',technical_status='succeeded',internal_visual_status='unreviewed',evidence=[dict(path=str(out/'head-neck.obj'),role='candidate_model')]))
