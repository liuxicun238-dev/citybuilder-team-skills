"""Replace tube-like sine rolls by contour-driven vermilion cross sections."""
from pathlib import Path
import numpy as np,json,sys
from scipy.interpolate import PchipInterpolator
R=Path('__CHAR_PROJECT__');root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'mouth-fit-v03/head-neck.obj';out=root/'mouth-fit-v06';out.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'tools/pipeline'));from record_modeling_step import append_event
append_event('character-modeling-skill-v01',dict(kind='action_started',technical_status='pending',objective='Replace rejected mouth rolls with reference-contour upper/lower vermilion sections',operation=dict(script=str(Path(__file__).resolve()))))
code=(R/'tools/pipeline/build_mouth_surface_v03.py').read_text();ns={'np':np};exec(code[code.index('def smooth'):code.index('skin=np.array')],ns);olddepth=ns['depth'];smooth=ns['smooth']
def depth(x,y):
 u=np.abs(x)/2.45
 taper=np.maximum(0,1-u*u)**.65
 # Reference contour: shallow central contact dip, broad cupid peaks, lower bowl.
 seam=5.30-.08*np.exp(-(x/.38)**2)+.025*np.exp(-((np.abs(x)-.85)/.55)**2)-.015*u
 uh=(.52+.13*np.exp(-((np.abs(x)-.58)/.34)**2))*taper
 lh=.78*np.maximum(0,1-u*u)**.42
 d=y-seam;q=np.abs(d)/np.maximum(np.where(d>=0,uh,lh),.025)
 upper=PchipInterpolator([0,.2,.55,.85,1,1.25,2],[.31,.37,.26,.095,.012,0,0])
 lower=PchipInterpolator([0,.22,.55,.85,1,1.3,2],[.31,.35,.30,.105,.015,0,0])
 roll=np.where(d>=0,upper(np.clip(q,0,2)),lower(np.clip(q,0,2)))*taper
 roll*=1-smooth((u-.94)/.06)
 mound=.10*np.exp(-(x/2.4)**4-((y-5.3)/1.25)**2)
 # Not a continuous deep slot; central contact is shallow, corners turn inward.
 contact=.045*np.exp(-(d/.035)**2)*taper
 phil=.035*(np.exp(-((x-.32)/.16)**2)+np.exp(-((x+.32)/.16)**2))*np.exp(-((y-6.35)/.48)**2)
 fold=-.035*np.exp(-((y-4.25)/.30)**2-(x/1.45)**4)
 corners=-.055*np.exp(-((np.abs(x)-2.35)/.20)**2-((y-5.28)/.15)**2)
  # Subtle segmented volume; no tube of constant radius across the mouth.
 lobe=np.where(d>=0,1+.10*np.exp(-(x/.35)**2)-.08*np.exp(-((np.abs(x)-.50)/.20)**2),1-.06*np.exp(-(x/.32)**2)+.04*np.exp(-((np.abs(x)-.7)/.35)**2))
 roll*=1+(lobe-1)*smooth(np.abs(d)/.14)
 # Shallow vermilion edge and sparse nonperiodic short creases, all geometric.
 edge=-.016*np.exp(-((q-1.03)/.065)**2)*taper
 creases=np.zeros_like(x)
 for a,length in [(-1.8,.45),(-1.35,.68),(-.97,.51),(-.64,.76),(-.29,.58),(.13,.70),(.45,.50),(.82,.78),(1.19,.57),(1.62,.46),(1.95,.35)]:
  line=a+.07*np.sin(d*4+a)
  creases+=.006*np.exp(-((x-line)/.032)**2)*smooth((q-.12)/.18)*(1-smooth((q-length)/.18))*taper
 return mound+roll-contact+phil+fold+corners+edge-creases
lines=src.read_text().splitlines();v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]);ids=set();g='';faces=[];groups=[]
for line in lines:
 a=line.split()
 if not a:continue
 if a[0]=='g':g=a[1]
 elif a[0]=='f':
  f=[int(i)-1 for i in a[1:]];faces.append(f);groups.append(g)
  if g=='mouth_surface':ids.update(f)
sel=np.array(sorted(ids));x=v[sel,0];y=v[sel,1]
weight=(1-smooth((np.abs(x)-2.8)/.55))*(1-smooth((np.abs(y-5.25)-1.45)/.45))
delta=(olddepth(x,y)-depth(x,y))*weight;v[sel,2]+=delta
k=0
with (out/'head-neck.obj').open('w',encoding='utf8') as s:
 for line in lines:
  if line.startswith('v '):line='v '+' '.join(f'{a:.8f}' for a in v[k]);k+=1
  s.write(line+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),method='Contour-driven PCHIP lip cross sections with shallow contact; only mouth patch depth changes',max_depth_change_cm=float(np.max(np.abs(delta))),limitations=['Closed mouth surface, no animation topology','No pore or lip wrinkle detail','Reference dimensions assumed']),indent=2),encoding='utf8')
append_event('character-modeling-skill-v01',dict(kind='action_finished',technical_status='succeeded',internal_visual_status='unreviewed',evidence=[dict(path=str(out/'head-neck.obj'),role='candidate_model')]))
