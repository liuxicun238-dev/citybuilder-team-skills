"""Local neck/shoulder clay-form study; no stock meshes or whole-head remesh."""
from pathlib import Path
import sys,json
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/pipeline'))
from record_modeling_step import append_event
root=R/'art/assets/authored/city/zbrush-reference-head-v01';src=root/'upper-body-v03/body.obj';out=root/'upper-body-v05';out.mkdir(exist_ok=True)
ref=R/'art/references/citizens-clay-male-v01/front.png'
lock=R/'art/references/citizens-clay-male-v01/lock.md'
aid='upper-body-v05'
append_event('character-upper-body-v01',dict(kind='action_started',action_id=aid,technical_status='pending',reference=[str(ref)],evidence=[dict(path=str(lock),role='reference_lock')],operation=dict(script=str(Path(__file__).resolve())),objective='Shape neck muscle paths, clavicle transition and upper chest volume with existing shortened neck'))
lines=src.read_text(encoding='utf8').splitlines();v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]);old=v.copy();x,y,z=old.T;ax=np.abs(x)
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
gate=1-smooth((y-.2)/1.6)
front=smooth((-z-1.5)/3.5);back=smooth((z+.4)/3.5)
# Paired, broad sternocleidomastoid paths; fade before jaw and clavicle insertion.
path=1.3+.25*(y+7)
scm=.30*np.exp(-((ax-path)/.9)**2)*np.exp(-((y+2.5)/4.6)**4)
v[:,2]-=gate*front*scm
# Neck-root expansion into trapezius, rather than a vertical cylindrical stalk.
v[:,0]+=gate*np.sign(x)*1.15*np.exp(-((y+5.8)/2.2)**2)*smooth((ax-2.2)/3.4)
v[:,2]+=gate*back*.60*np.exp(-((y+5.2)/3.5)**2)*np.exp(-((ax-4)/4.8)**2)
# Broad clavicle plane with an S-shaped shallow ridge and suprasternal depression.
clavy=-8.25+.15*ax-.018*ax*ax
span=smooth((ax-.7)/1.5)*(1-smooth((ax-15)/3))
ridge=.23*np.exp(-((y-clavy)/1.25)**2)*span
hollow=.07*np.exp(-((y-clavy-1.1)/.9)**2)*span
sternal=.24*np.exp(-(x/1.3)**2-((y+7.9)/1.1)**2)
v[:,2]+=gate*front*(-ridge+hollow+sternal)
# Upper pectorals stay broad, with a soft medial transition; no engraved outlines.
pec=.38*np.exp(-((ax-8)/6.5)**2-((y+15.4)/5.0)**2)
sternum=.15*np.exp(-(x/1.5)**2-((y+16)/5.3)**2)
v[:,2]+=gate*front*(-pec+sternum)
# Rear scapular plane and a restrained spinal channel.
v[:,2]+=gate*back*(.48*np.exp(-((ax-7)/4.5)**2-((y+12)/4.8)**2)-.18*np.exp(-(x/1.2)**2-((y+12)/6)**2))
assert np.array_equal(v[y>=1.8],old[y>=1.8])
k=0
with (out/'body.obj').open('w',encoding='utf8') as f:
 for l in lines:
  if l.startswith('v '):l='v '+' '.join(f'{a:.8f}' for a in v[k]);k+=1
  f.write(l+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(src),unit='cm',source_topology_preserved=True,protected_y_min_cm=1.8,max_displacement_cm=float(np.linalg.norm(v-old,axis=1).max()),status='Anatomical blockout candidate, not final anatomy or animation mesh'),indent=2),encoding='utf8')
print(out)
