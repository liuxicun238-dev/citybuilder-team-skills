"""Original ear volume from manually traced reference structures, cm; no base mesh."""
from pathlib import Path
import sys,json,numpy as np
from scipy.interpolate import splprep,splev
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from skimage.measure import marching_cubes
ROOT=Path('__CHAR_PROJECT__');import argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);args=ap.parse_args();OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(ROOT/'tools/pipeline'))
from record_modeling_step import append_event
append_event('character-modeling-skill-v01',dict(kind='action_started',technical_status='pending',objective='Original isolated right ear from clay reference; continuous implicit cartilage volume',operation=dict(script=str(Path(__file__).resolve())),reference=[str(ROOT/'art/references/citizen-ear-clay-v01/reference.png')]))
S=6.5/1340
def xy(points):
 p=np.array(points,float);return np.c_[(p[:,0]-500)*S,(1410-p[:,1])*S]
def spline(points,n=500,closed=False):
 p=xy(points);t,_=splprep(p.T,s=0,per=closed,k=min(3,len(p)-1));return np.array(splev(np.linspace(0,1,n),t)).T
outline=spline([(165,400),(250,250),(390,120),(550,70),(710,130),(840,300),(915,530),(915,760),(860,960),(740,1130),(620,1280),(480,1395),(355,1390),(270,1300),(235,1170),(165,1030),(100,870),(90,745),(125,610),(160,510),(165,400)],1000,True)
step=.032
xs=np.arange(-2.3,2.4,step);ys=np.arange(-.25,6.85,step);zs=np.arange(-1.2,1.25,step)
X,Y=np.meshgrid(xs,ys,indexing='ij');P=np.c_[X.ravel(),Y.ravel()]
d=cKDTree(outline).query(P)[0].reshape(X.shape)
inside=np.zeros(X.shape,bool)
for a,b in zip(outline,np.roll(outline,-1,axis=0)):
 inside^=((a[1]>Y)!=(b[1]>Y))&(X<(b[0]-a[0])*(Y-a[1])/(b[1]-a[1]+1e-20)+a[0])
sd=np.where(inside,-d,d)
def gauss(px,py,rx,ry):
 cx,cy=xy([[px,py]])[0];return np.exp(-((X-cx)/rx)**2-((Y-cy)/ry)**2)
front=.12+.12*np.sqrt(np.maximum(d,0))
front-=.68*gauss(440,785,.72,.84)+.27*gauss(435,370,.45,.5)
front+=.28*gauss(410,1230,.75,.72)
back=-.25-.55*gauss(450,780,.9,1.25)
# Thickness rounds down toward the silhouette instead of a vertical plate edge.
edge=np.clip(d/.20,0,1);mid=(front+back)/2;half=(front-back)/2*np.sqrt(edge)
front=mid+half;back=mid-half
Z=zs[None,None,:]
field=np.maximum(sd[:,:,None],np.maximum(Z-front[:,:,None],back[:,:,None]-Z)).astype(np.float32)
def smin(a,b,k=.13):
 h=np.maximum(k-np.abs(a-b),0)/k;return np.minimum(a,b)-h*h*k*.25
features=[]
def ridge(name,points,radius,depth,z):
 global field
 path=spline(points,600);dist,ids=cKDTree(path).query(P);dist=dist.reshape(X.shape)
 t=ids.reshape(X.shape)/599
 taper=.1+.9*np.sin(np.pi*t)**.45
 r=radius*taper
 # Elliptical cross sections fuse into the bowl, with rounded raised cartilage.
 end=np.minimum(t,1-t);fade=np.clip(end/.12,0,1);fade=fade*fade*(3-2*fade)
 centerz=-.12+(z+.12)*fade
 thickness=depth*(.2+.8*fade)
 f=(np.sqrt((dist[:,:,None]/np.maximum(r[:,:,None],.02))**2+((Z-centerz[:,:,None])/thickness[:,:,None])**2)-1)*min(radius,depth)
 field=smin(field,f.astype(np.float32),.23)
 features.append(dict(name=name,points_pixels=points,radius_cm=radius,depth_cm=depth,height_cm=z))
ridge('helix',[(250,560),(220,400),(300,250),(435,150),(585,135),(730,220),(825,385),(870,605),(860,825),(790,1010),(670,1165),(550,1290)],.25,.28,.26)
ridge('antihelix_main_superior',[(400,1020),(480,940),(620,910),(705,805),(720,665),(670,500),(610,370),(535,250)],.29,.24,.24)
ridge('inferior_crus',[(665,500),(580,465),(470,450),(380,405)],.19,.19,.25)
ridge('crus_helix',[(230,450),(280,535),(370,605),(475,650)],.19,.20,.16)
ridge('tragus',[(225,620),(255,700),(255,795),(215,870)],.32,.35,.30)
ridge('antitragus',[(390,1010),(430,945),(500,925),(555,925)],.24,.25,.29)
field=gaussian_filter(field,.8)
verts,faces,normals,_=marching_cubes(field,0,spacing=(step,step,step));verts+=np.array([xs[0],ys[0],zs[0]])
rr=faces.ravel();cc=faces[:,[1,2,0]].ravel();graph=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(verts),len(verts)))
nc,labels=connected_components(graph,directed=False);sizes=np.bincount(labels);main=int(sizes.argmax())
assert max([n for i,n in enumerate(sizes) if i!=main],default=0)<100,'Unexpected separate anatomical component'
faces=faces[labels[faces[:,0]]==main];used=np.unique(faces);mapping=np.full(len(verts),-1);mapping[used]=np.arange(len(used));faces=mapping[faces];verts=verts[used]
with (OUT/'ear.obj').open('w',encoding='utf8') as f:
 for p in verts:f.write('v '+' '.join(f'{q:.6f}' for q in p)+'\n')
 f.write('g ear\n')
 for p in faces:f.write('f '+' '.join(str(int(i)+1) for i in p)+'\n')
(OUT/'construction.json').write_text(json.dumps(dict(unit='cm',axes='X image right, Y superior, Z outward',reference=str(ROOT/'art/references/citizen-ear-clay-v01/reference.png'),features=features,voxel_cm=step,vertices=len(verts),triangles=len(faces),limitations=['Reference is one view; posterior design assumed','No head attachment or game topology','Not ZBrush brush sculpting'],status='pending actual render'),indent=2),encoding='utf8')
append_event('character-modeling-skill-v01',dict(kind='action_finished',technical_status='succeeded',internal_visual_status='unreviewed',evidence=[dict(path=str(OUT/'ear.obj'),role='source_model'),dict(path=str(OUT/'construction.json'),role='construction')]))
print(OUT)
