"""Large-scale sagittal cage correction; no local facial detail changes.
Use original authored topology. Axes cm: Y up, -Z face.
"""
from pathlib import Path
import math,json
import numpy as np
ROOT=Path('__CHAR_PROJECT__/art/assets/authored/city/zbrush-reference-head-v01')
OUT=ROOT/'profile-cage-v01';OUT.mkdir(exist_ok=True)
src=ROOT/'topology-a19/reference-head.obj';lines=src.read_text().splitlines()
v=[];vl=[];groups={};g=''
for k,line in enumerate(lines):
 p=line.split()
 if not p:continue
 if p[0]=='v':vl.append(k);v.append(list(map(float,p[1:4])))
 elif p[0]=='g':g=p[1]
 elif p[0]=='f':groups.setdefault(g,set()).update(int(q.split('/')[0])-1 for q in p[1:])
v=np.array(v);new=v.copy()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def depth(z):return z*(1.07-.28*math.tanh(z/2))-1.1
for i,(x,y,z) in enumerate(v):
 new[i,2]=depth(z)
 # Elevate the posterior mandibular border, retaining anterior chin height.
 new[i,1]=y+5.0*smooth((z+5)/10)*(1-smooth(y/10))
# Eyeballs remain spheres, material boundaries transformed exactly once.
eyes=set().union(*(ids for name,ids in groups.items() if name.startswith('eye_')))
for i in eyes:
 new[i]=v[i]+np.array([0,0,depth(-6.65)+6.65])
# Preserve local eye/globe support while the surrounding cage transitions.
for i in groups['skin']:
 x,y,z=v[i]
 if z>-3:continue
 for sg in [-1,1]:
  dx=x-sg*3.42;dy=y-13;r=math.sqrt((dx/1.4)**2+(dy/1.0)**2)
  if r<2.2:
   weight=1-smooth((r-1)/1.2)
   translated=z+depth(-6.65)+6.65
   new[i,2]=new[i,2]*(1-weight)+translated*weight
for k,p in zip(vl,new):lines[k]='v '+' '.join(f'{q:.8f}' for q in p)
(OUT/'head.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
(OUT/'proportion-notes.json').write_text(json.dumps(dict(reference='art/references/citizens-clay-male-v01/profile-candidate.png',reference_assumptions=dict(crown_pixel_y=30,chin_pixel_y=825,head_height_cm=24,depth_origin_pixel_x=700,eye_line_pixel_y=405,nose_tip_pixel_y=540,mouth_pixel_y=670),observations=['Reference ear sits farther back relative to nose than original mesh','Original posterior lower contour stays too low, creating square block','Global depth cage separates facial projection from posterior skull depth'],source=str(src),eye_center_before=[3.42,13,-6.65],eye_center_after=[3.42,13,depth(-6.65)],source_bounds=[v.min(axis=0).tolist(),v.max(axis=0).tolist()],candidate_bounds=[new.min(axis=0).tolist(),new.max(axis=0).tolist()],limitations=['Approximate reference; not calibrated orthographic scan','No new facial details','No neck yet','No self-intersection test']),indent=2),encoding='utf8')
