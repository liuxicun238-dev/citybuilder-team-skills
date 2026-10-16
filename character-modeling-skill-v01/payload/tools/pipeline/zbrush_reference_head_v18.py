"""Continuous triangulated anatomical landmark surface, original geometry."""
import math,json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator,RBFInterpolator
from scipy.spatial import Delaunay
ROOT=Path('__CHAR_A18__');ROOT.mkdir(parents=True,exist_ok=True)
V=[];F=[];G=[]
def vert(p):V.append(tuple(float(x) for x in p));return len(V)-1
def face(ids,g='skin'):F.append(tuple(ids));G.append(g)
def curve(points):return PchipInterpolator(*zip(*points))
width=curve([(0,2.8),(.5,4),(1.5,5.2),(3,6.25),(5.2,6.8),(7,7.25),(9,7.7),(11,8),(13,8.0),(15,7.85),(17,8.1),(18,8.2)])
front=curve([(0,8.5),(1,9),(2,9.05),(3,8.7),(4,8.7),(5.2,8.65),(6.4,8.5),(8,8.4),(10,8.5),(12,8.7),(13.2,8.6),(14.3,8.9),(15.5,9.3),(17,9.5),(18,9.25),(20,8.4),(22,6.5),(23,4.5),(23.8,1.9),(24,.01)])
back=curve([(0,1.5),(1,4),(2.5,6),(5,8),(8,9),(11,9.5),(15,9.65),(18,9.0),(20,8.1),(22,6.3),(23,4.5),(23.8,1.9),(24,.01)])
mid=curve([(0,8.5),(1,9),(2,9.05),(3,8.7),(4,9.15),(5.2,9.65),(6.4,9.4),(7.5,9.55),(8.1,10.4),(8.8,11.3),(9.4,11.2),(10.5,10.4),(12,9.6),(13.2,9.0),(14.3,9.1),(15.5,9.3),(17,9.5),(18,9.25),(20,8.4),(22,6.5),(23,4.5),(23.8,1.9),(24,.01)])
# Front silhouette measured against reference crown/chin normalization (24 cm assumption).
width=curve([(0,.45),(.15,1.45),(.5,2.6),(1,3.5),(2,4.6),(3,5.35),(4,5.8),(5.2,6.25),(7,6.95),(9,7.5),(11,7.85),(13,7.95),(15,7.95),(17,8.0),(18,7.95),(19,7.65),(20,7.1),(21,6.3),(22,5.1),(23,3.5),(23.8,1.5),(24,.001)])

def w(y):return max(.001,float(width(y)))
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
nose_width=curve([(0,3),(5,3),(6.5,2.6),(6.9,2.2),(7.4,1.9),(8.5,1.85),(9.5,1.6),(11,1.2),(14,1.5),(24,2)])
def base_xy(x,y):
    return np.array(surface(math.asin(max(-.999999,min(.999999,x/w(y)))),y))
nose_sections_y=np.array([6.9,7.5,8.0,8.5,9.0,10.0,11.5,13.5,14.5])
nose_sections=np.array([
 [.95,.75,.33,.08,0], [1.0,.8,.55,.18,0], [1.8,1.3,1.4,.65,0],
 [2.3,2.1,1.5,.45,0], [2.5,1.9,.85,.12,0], [2.1,1.5,.45,.02,0],
 [1.2,.6,.12,0,0], [.3,.12,0,0,0], [0,0,0,0,0]])
nose_cols=[PchipInterpolator(nose_sections_y,nose_sections[:,i]) for i in range(5)]
def surface(theta,y):
    x=w(y)*math.sin(theta);c=math.cos(theta)
    if c<0:return (x,y,-float(back(y))*c)
    q=abs(x)/w(y)
    z=-float(front(y))*max(0,1-q*q)**.5
    nasalwidth=float(nose_width(y))
    weight=1-smooth(abs(x)/nasalwidth)
    if 6.9<=y<=14.5:
        qn=min(1,abs(x)/2.2)
        section=PchipInterpolator([0,.3,.6,.82,1],[float(col(y)) for col in nose_cols])
        z-=float(section(qn))
    elif y<6.9:
        z-=(float(mid(y))-float(front(y)))*weight
    # Defined upper/lower lip volumes following the mouth width, fading at corners.
    if abs(x)<2.6 and 4.2<y<6.5:
        u=abs(x)/2.6;fall=(1-u*u)**1.5
        upperline=5.72+.14*math.sin(math.pi*u)
        lowerline=4.94
        for line,height,spread in [(upperline,.14,.42),(lowerline,.18,.46)]:
            d=abs(y-line)/spread
            if d<1:z-=height*fall*(1-d*d)**2
    # Broad cheek/brow planes anchored to the reference, not image luminance.
    cheek=(1-smooth(abs(abs(x)-4.8)/2.5))*(1-smooth(abs(y-10.2)/3.5))
    z-=.28*cheek
    # Continuous superciliary arch, referenced to brow line 2.1 cm above the eyes.
    bx=abs(x);brow_y=15.05-.18*((bx-3.1)/2.5)**2
    if 1.2<bx<6.2:
        across=math.sin(math.pi*(bx-1.2)/5.0)**2
        d=abs(y-brow_y)/.85
        if d<1:z-=.30*across*(1-d*d)**2
    return (x,y,z)

# Front patch and posterior hemisphere share the exact sagittal-side boundary.
Y=160;N=160;ys=np.linspace(.02,23.98,Y+1)
frontids=[];coords=[];backgrid={};controls=[];values=[]
def addctrl(x,y,z):
    controls.append((x,y));values.append(z-float(base_xy(x,y)[2]))
def inside(points,poly):
    p=np.asarray(points);out=np.zeros(len(p),dtype=bool)
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        out^=((a[1]>p[:,1])!=(b[1]>p[:,1])) & (p[:,0]<(b[0]-a[0])*(p[:,1]-a[1])/(b[1]-a[1]+1e-20)+a[0])
    return out
holes=[];rim_data=[]
for sg in [-1,1]:
    cx=sg*3.42;cy=13;poly=[]
    for j in range(80):
        a=j*2*math.pi/80;c=math.cos(a);s=math.sin(a)
        x=cx+1.25*c;y=cy+(.60 if s>0 else .35)*s+sg*.045*(x-cx)
        z=-6.65-math.sqrt(max(.01,1.3**2-(x-cx)**2-(y-cy)**2))-.055
        poly.append((x,y));rim_data.append((x,y,z,'eye'))
        addctrl(x,y,z)
        # Following rings are continuous skin, supported by the full eye globe.
        for scale in [1.25,1.65,2.4]:
            dx=(x-cx)*scale;dy=(y-cy)*scale
            xx=cx+dx;yy=cy+dy
            basez=float(base_xy(xx,yy)[2]);r2=dx*dx+dy*dy
            zz=min(basez,-6.65-math.sqrt(max(.0,1.3**2-r2))-.09) if r2<1.3**2 else basez
            if scale==1.25:zz-=.025
            addctrl(xx,yy,zz)
    holes.append(np.array(poly))
poly=[]
for j in range(100):
    a=j*2*math.pi/100;c=math.cos(a);s=math.sin(a)
    x=2.5*c;y=5.28-.075*(1-c*c)+(.045 if s>0 else .035)*s
    z=-9.55+.65*abs(c)**1.7
    poly.append((x,y));rim_data.append((x,y,z,'mouth'));addctrl(x,y,z)
    for scale,dy,zadd in [(1.02,.23,.16),(1.08,.47,.04),(1.2,.85,-.25)]:
        xx=x*scale;yy=5.28+dy*s
        zz=z-zadd
        if abs(c)<.85:addctrl(xx,yy,zz)
holes.append(np.array(poly))
# Actual paired nostril apertures with shallow interior cavities.
nostril_rims=[]
for sg in [-1,1]:
    poly=[];samples=[]
    for j in range(48):
        a=2*math.pi*j/48;x=sg*(1.08+.36*math.cos(a));y=7.92+.15*math.sin(a)+.08*math.cos(a)
        z=float(base_xy(x,y)[2]);poly.append((x,y));samples.append((x,y,z));rim_data.append((x,y,z,'nostril'))
    holes.append(np.array(poly));nostril_rims.append(samples)
# Reference-constrained cranial and facial landmarks, explicit depths in cm.
for y in [1,2,3,7,9,10.5,12,15,16.5,18,20,22,23.5]:
    for ratio in [-.98,-.85,-.7,0,.7,.85,.98]:
        x=w(y)*ratio
        if y<15 and abs(ratio)<.01 and y>3:continue
        addctrl(x,y,float(base_xy(x,y)[2]))
# Nose bridge, rounded tip, alar sidewalls, and nasal base.
for x,y,z in [(0,14,-8.9),(0,12,-9.5),(0,10.5,-10.1),(0,9.3,-10.9),(0,8.8,-11),(0,8.1,-10.2),(0,7.6,-9.3),(.7,9.1,-10.65),(1.2,8.4,-9.8),(1.55,8.1,-9.1),(.8,7.8,-9.2),(1.8,9.5,-8.5),(2.2,10.7,-8.2),(4.7,10.1,-8.0),(5.8,8.5,-7.1),(0,6.7,-9.0),(0,3.8,-8.65),(0,2.2,-9.05)]:
    addctrl(x,y,z)
    if x:addctrl(-x,y,z)
# Duplicate control coordinates collapsed before the thin-plate solve.
c=np.asarray(controls);v=np.asarray(values);keys=np.round(c,5);_,ix=np.unique(keys,axis=0,return_index=True)
field=lambda xy:np.zeros(len(xy))
# Head rings provide consistent density, but facial triangles no longer meet rectangular patches.
for iy,y in enumerate(ys):
    for j in range(N//2+1):
        theta=-math.pi/2+j*2*math.pi/N;p=surface(theta,float(y));xy=np.array([[p[0],p[1]]])
        if any(inside(xy,h)[0] for h in holes):continue
        i=vert(p);frontids.append(i);coords.append(p[:2]);backgrid[iy,j]=i
    # Posterior side reuses both endpoints of the front half.
    for j in range(N//2+1,N):backgrid[iy,j]=vert(surface(-math.pi/2+j*2*math.pi/N,float(y)))
for iy in range(Y):
    for j in range(N//2,N):
        k=(j+1)%N;face((backgrid[iy,j],backgrid[iy+1,j],backgrid[iy+1,k],backgrid[iy,k]))
for x,y,z,kind in rim_data:
    frontids.append(vert((x,y,z)));coords.append((x,y))
ring_rx=curve([(0,1.25),(.08,1.30),(.25,1.55),(.5,2.1),(1,3.05)])
ring_up=curve([(0,.60),(.08,.68),(.25,.95),(.5,1.5),(1,2.6)])
ring_lo=curve([(0,.35),(.08,.43),(.25,.74),(.5,1.25),(1,2.5)])
for sg in [-1,1]:
    for t in [.035,.07,.12,.18,.25,.35,.5,.7]:
        for j in range(80):
            a=j*2*math.pi/80;dx=float(ring_rx(t))*math.cos(a)
            x=sg*3.42+dx;y=13+float(ring_up(t) if math.sin(a)>0 else ring_lo(t))*math.sin(a)+sg*.045*dx
            p=base_xy(x,y);frontids.append(vert(p));coords.append((x,y))
coords=np.array(coords);delta=field(coords)
# Continuous eye support field uses the same anatomical rings as the isolated study.
rx=curve([(0,1.25),(.08,1.30),(.25,1.55),(.5,2.1),(1,3.05)])
up=curve([(0,.60),(.08,.68),(.25,.95),(.5,1.5),(1,2.6)])
lo=curve([(0,.35),(.08,.43),(.25,.74),(.5,1.25),(1,2.5)])
for k,i in enumerate(frontids):
    x,y=coords[k];z=float(base_xy(x,y)[2])
    if abs(x)>w(y)*.9999:z=0
    for cx in [-3.42,3.42]:
        dx=x-cx;dy=y-13-.045*np.sign(cx)*dx
        h=up if dy>=0 else lo
        if (dx/3.05)**2+(dy/float(h(1)))**2>1:continue
        low,high=0.,1.
        for _ in range(15):
            t=(low+high)/2
            if (dx/float(rx(t)))**2+(dy/float(h(t)))**2>1:low=t
            else:high=t
        t=(low+high)/2;rho=math.hypot(dx,dy)
        globe=-6.65-math.sqrt(max(.0,1.3**2-min(rho,1.28)**2))-.065
        blend=smooth(t/.45)
        # Face support is raised smoothly outside the tarsal cover.
        support=z
        local=globe*(1-blend)+support*blend
        if dy>0:
            # Recessed upper lid crease in the same skin; never an added ring.
            d=abs(t-.21)/.065
            if d<1:local+=.025*(1-d*d)**2*min(1,dy/.5)
        if rho<1.3:local=min(local,-6.65-math.sqrt(1.3**2-rho*rho)-.045)
        fade=1-smooth((t-.55)/.45)
        z=z*(1-fade)+local*fade
    V[i]=(x,y,z)
# Triangulate the intrinsic theta-height rectangle. XY convex hull filled across
# the concave head silhouette and created long bridging triangles on the temples.
uv=np.array([(8*math.asin(max(-1,min(1,x/w(y)))),y) for x,y in coords])
# All anatomical openings are explicit CDT constraints, not centroid-only cutouts.
from scipy.spatial import cKDTree
import subprocess
index=cKDTree(coords);edges=[]
for h in holes:
    dist,ids=index.query(h)
    if max(dist)>1e-6:raise RuntimeError('missing aperture vertex')
    edges.extend((int(ids[j]),int(ids[(j+1)%len(ids)])) for j in range(len(ids)))
(ROOT/'cdt-input.json').write_text(json.dumps({'uv':uv.tolist(),'edges':edges}))
with (ROOT/'cdt.log').open('w') as log:
    subprocess.run(['__CHAR_BLENDER__','-b','--python','__CHAR_PROJECT__/tools/pipeline/head_constrained_triangles_v01.py','--',str(ROOT)],stdout=log,stderr=subprocess.STDOUT,check=True)
cdt=json.loads((ROOT/'cdt-output.json').read_text());simplices=np.array(cdt['faces'])
centers=uv[simplices].mean(axis=1);remove=np.zeros(len(centers),bool)
for h in holes:
    param=np.array([(8*math.asin(max(-1,min(1,x/w(y)))),y) for x,y in h])
    remove|=inside(centers,param)
for f,bad in zip(simplices,remove):
    if not bad:face(tuple(frontids[i] for i in f[::-1]))
# Reuse aperture vertices for the cavity; no dark decal substitutes for geometry.
for samples in nostril_rims:
    ids=[]
    for p in samples:
        xy=np.array(p[:2]);k=int(np.argmin(np.sum((coords-xy)**2,axis=1)));ids.append(frontids[k])
    center=np.mean(np.array([V[i] for i in ids]),axis=0);center[2]+=.45
    inset=[vert(tuple(np.array(V[i])*.4+center*.6)) for i in ids]
    cap=vert(center)
    for j in range(len(ids)):
        n=(j+1)%len(ids);face((ids[j],ids[n],inset[n],inset[j]),'nasal_interior');face((inset[j],inset[n],cap),'nasal_interior')
def sphere(cx,cy,cz,r,name):
    st=len(V); lat=40;lon=64
    # Sphere forward axis -Z; iris is a curved subset, never a floating disc.
    for i in range(lat+1):
        a=math.pi*(.0001+(1-.0002)*i/lat)
        for j in range(lon):
            t=j*2*math.pi/lon;vert((cx+r*math.sin(a)*math.cos(t),cy+r*math.sin(a)*math.sin(t),cz-r*math.cos(a)))
    for i in range(lat):
        for j in range(lon):
            a=st+i*lon+j;b=st+i*lon+(j+1)%lon
            g=name+('_pupil' if i<2 else '_iris' if i<5 else '_sclera')
            face((a,b,b+lon,a+lon),g)
for s in [-1,1]:sphere(s*3.42,13,-6.65,1.3,'eye_'+str(s))
# Original pinna surface: helix, antihelix forks, concha and tragus integrated
# into one shell. Distances are measured in the ear's YZ plane, not painted bumps.
def line_distance(p,points):
    best=100.
    for aa,bb in zip(points,points[1:]):
        aa=np.array(aa);bb=np.array(bb);d=bb-aa;t=np.clip(np.dot(p-aa,d)/np.dot(d,d),0,1)
        best=min(best,float(np.linalg.norm(p-aa-t*d)))
    return best
def ridge(d,width,height):
    return height*max(0,1-(d/width)**2)**2
anti=[(8.5,1.2),(9.2,1.65),(10.2,1.9),(11.25,1.9),(12.25,1.5),(12.75,.9)]
fork=[(11.1,1.85),(11.65,1.0),(12.1,.55)]
tragus=[(9.7,.22),(10.25,.04),(10.7,.15)]
for sg in [-1,1]:
    rows=[];num=128
    for k in range(41):
        r=.001+.999*k/40;row=[]
        for j in range(num):
            angle=2*math.pi*j/num;co=math.cos(angle);si=math.sin(angle)
            y=10.4+2.85*r*co
            z=1.15+(.93+.37*smooth((co+.7)/.7))*r*si+.25*r*co
            p=np.array((y,z))
            helix=ridge(abs(r-.88),.16,.55)
            inner=ridge(line_distance(p,anti),.32,.33)+ridge(line_distance(p,fork),.27,.22)
            trag=ridge(line_distance(p,tragus),.30,.33)
            concha=-ridge(math.hypot((y-10.2)/1.1,(z-.7)/.7),1,.19)
            lobe=ridge(math.hypot((y-7.95)/.65,(z-1.0)/.6),1,.18)
            height=.20+.16*r+helix+inner+trag+concha+lobe
            angle=math.radians(22);zz=z-1.15
            xx=7.65+height*math.cos(angle)+zz*math.sin(angle)
            zp=1.15+zz*math.cos(angle)-height*math.sin(angle)
            row.append(vert((sg*xx,y,zp)))
        rows.append(row)
    for inner,outer in zip(rows,rows[1:]):
        for j in range(num):
            n=(j+1)%num;f=(inner[j],outer[j],outer[n],inner[n]);face(f if sg>0 else f[::-1],'ear')
    center=vert((sg*7.55,10.4,1.15))
    for j in range(num):
        n=(j+1)%num;f=(rows[-1][j],center,rows[-1][n]);face(f if sg>0 else f[::-1],'ear')

with (ROOT/'reference-head.obj').open('w') as f:
    for p in V:f.write('v '+' '.join(f'{v:.6f}' for v in p)+'\n')
    group=None
    for ids,g in zip(F,G):
        if g!=group:f.write('g '+g+'\n');group=g
        f.write('f '+' '.join(str(i+1) for i in ids)+'\n')
(ROOT/'geometry.json').write_text(json.dumps({'vertices':len(V),'faces':len(F),'method':'intrinsic theta-height triangulation; original surface, independent eyes','status':'unreviewed'}))
