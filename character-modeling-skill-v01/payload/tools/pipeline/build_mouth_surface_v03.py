"""Original closed-mouth surface. Whole patch CDT graft, not a pasted closed solid."""
from pathlib import Path
from collections import Counter
import numpy as np,json,subprocess,sys,hashlib
from scipy.interpolate import RBFInterpolator
R=Path('__CHAR_PROJECT__');root=R/'art/assets/authored/city/zbrush-reference-head-v01';out=root/'mouth-fit-v03';out.mkdir(exist_ok=True)
local=R/'art/assets/authored/city/citizen-mouth-sculpt-v01/a03';local.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'tools/pipeline'));from record_modeling_step import append_event
append_event('character-modeling-skill-v01',dict(kind='action_started',technical_status='pending',objective='Closed lips rebuilt from white clay reference, preserve nose and ears',operation=dict(script=str(Path(__file__).resolve())),reference=[str(R/'art/references/citizen-mouth-clay-v01/reference.png')]))
source=root/'nose-fit-v13/head-neck.obj';v=[];faces=[];gs=[];g='skin'
for l in source.read_text().splitlines():
 p=l.split()
 if not p:continue
 if p[0]=='v':v.append(list(map(float,p[1:4])))
 elif p[0]=='g':g=p[1]
 elif p[0]=='f':faces.append([int(t)-1 for t in p[1:]]);gs.append(g)
v0=np.array(v);kept=[];kg=[]
for f,g in zip(faces,gs):
 p=v0[f].mean(0)
 if g in ['skin','nose_surface','nose_join'] and p[2]<-9 and (p[0]/4.1)**2+((p[1]-5.25)/2.25)**2<1:continue
 kept.append(f);kg.append(g)
counts=Counter(tuple(sorted((a,b))) for f,g in zip(kept,kg) for a,b in zip(f,f[1:]+f[:1]));adj={}
for (a,b),n in counts.items():
 if n==1:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(ns)==2 for ns in adj.values())
unseen=set(adj);loops=[]
while unseen:
 loop=[min(unseen)];prev=None
 while True:
  nxt=next(i for i in adj[loop[-1]] if i!=prev)
  if nxt==loop[0]:break
  prev=loop[-1];loop.append(nxt)
 loops.append(loop);unseen.difference_update(loop)
print([(len(a),v0[a].mean(0).tolist(),np.ptp(v0[a],axis=0).tolist()) for a in loops]);loop=next(a for a in loops if 4<v0[a,1].mean()<7 and 7<np.ptp(v0[a,0])<9);outer=v0[loop,:2]
def inside(p):
 p=np.atleast_2d(p);r=np.zeros(len(p),bool)
 for a,b in zip(outer,np.roll(outer,-1,axis=0)):
  r^=((a[1]>p[:,1])!=(b[1]>p[:,1]))&(p[:,0]<(b[0]-a[0])*(p[:,1]-a[1])/(b[1]-a[1]+1e-25)+a[0])
 return r
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def depth(x,y):
 u=np.abs(x)/2.45;taper=np.sqrt(np.maximum(0,1-u*u));width=1-smooth((u-.88)/.12)
 seam=5.25-.055*np.exp(-(x/.38)**2)+.035*np.exp(-((np.abs(x)-.8)/.42)**2)
 d=y-seam
 uh=(.42+.18*np.exp(-((np.abs(x)-.65)/.4)**2))*taper
 lh=.72*taper
 h=np.where(d>=0,uh,lh);q=np.abs(d)/np.maximum(h,.03)
 # A broad oral mound supports the lips; bounded, never follows old protruding lips.
 mound=.16*np.exp(-(x/2.35)**4-((y-5.25)/1.05)**2)
 roll=np.where(q<1,np.sin(np.pi*(.25+.75*np.clip(q,0,1)))**1.5,0)*(.22-.035*np.tanh(d/.10))*width*taper**.7
 seamdent=.025*np.exp(-(d/.045)**2)*width
 # Lightly indicate the upper vermilion boundary and philtrum, without a cut groove.
 peak=.008*np.exp(-((d-uh)/.075)**2)*width*(d>0)
 phil=.045*(np.exp(-((x-.30)/.15)**2)+np.exp(-((x+.30)/.15)**2))*np.exp(-((y-6.25)/.52)**2)
 chin=-.075*np.exp(-((y-4.35)/.24)**2-(x/1.4)**4)
 corners=-.07*np.exp(-((np.abs(x)-2.38)/.16)**2-((y-5.27)/.12)**2)
 return mound+roll-seamdent+peak+phil+chin+corners
skin=np.array(sorted({i for f,g in zip(faces,gs) if g=='skin' for i in f}));p=v0[skin];rad=(p[:,0]/4.1)**2+((p[:,1]-5.25)/2.25)**2
samples=p[(rad>1)&(rad<1.5)&(p[:,2]<-9)];samples=np.vstack((v0[loop],samples[::max(1,len(samples)//400)]));_,ix=np.unique(samples[:,:2],axis=0,return_index=True);samples=samples[ix]
base=RBFInterpolator(samples[:,:2],samples[:,2],smoothing=.08)
grid=np.array([[x,y] for y in np.arange(2.8,7.7,.035) for x in np.arange(-4.4,4.4,.045)]);grid=grid[inside(grid)]
def distance(points):
 best=np.full(len(points),1e8)
 for a,b in zip(outer,np.roll(outer,-1,axis=0)):
  d=b-a;t=np.clip(((points-a)@d)/(d@d),0,1);best=np.minimum(best,np.linalg.norm(points-a-t[:,None]*d,axis=1))
 return best
grid=grid[distance(grid)>.025];uv=np.vstack((outer,grid));ids=loop.copy()
z=base(grid)-depth(grid[:,0],grid[:,1])*smooth(distance(grid)/.5)
for (x,y),zz in zip(grid,z):ids.append(len(v));v.append([x,y,zz])
edges=[[j,(j+1)%len(outer)] for j in range(len(outer))]
(out/'cdt-input.json').write_text(json.dumps(dict(uv=uv.tolist(),edges=edges)),encoding='utf8')
with (out/'cdt.log').open('w') as log:subprocess.run(['__CHAR_BLENDER__','-b','--python',str(R/'tools/pipeline/head_constrained_triangles_v01.py'),'--',str(out)],stdout=log,stderr=subprocess.STDOUT,check=True)
tri=json.loads((out/'cdt-output.json').read_text())['faces']
patch=[]
for f in tri:
 if inside(uv[f].mean(0))[0]:kept.append([ids[i] for i in f]);kg.append('mouth_surface');patch.append(f)
used=sorted({i for f in kept for i in f});mapping={i:j for j,i in enumerate(used)}
with (out/'raw.obj').open('w') as f:
 for i in used:f.write('v '+' '.join(f'{q:.8f}' for q in v[i])+'\n')
 last=None
 for face,g in zip(kept,kg):
  if g!=last:f.write('g '+g+'\n');last=g
  f.write('f '+' '.join(str(mapping[i]+1) for i in face)+'\n')
sys.path.insert(0,str(R/'.agents/skills/game-character-modeling/scripts'));from orient_obj import orient
orient(out/'raw.obj',out/'head-neck.obj')
with (local/'mouth.obj').open('w') as f:
 for i in ids:
  x,y,z=v[i];f.write(f'v {x:.8f} {y-5.25:.8f} {-z-13:.8f}\n')
 for face in patch:f.write('f '+' '.join(str(i+1) for i in face[::-1])+'\n')
(out/'construction.json').write_text(json.dumps(dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),method='Whole continuous closed-mouth patch; anatomical height field and constrained boundary triangulation',preserved_original_vertices=True,limitations=['Closed mouth groove, no mouth cavity or animation topology','Assumed proportions; shape unreviewed','Independent study is an open surface']),indent=2),encoding='utf8')
append_event('character-modeling-skill-v01',dict(kind='action_finished',technical_status='succeeded',internal_visual_status='unreviewed',evidence=[dict(path=str(out/'head-neck.obj'),role='candidate_model'),dict(path=str(local/'mouth.obj'),role='local_surface')]))
print(out)
