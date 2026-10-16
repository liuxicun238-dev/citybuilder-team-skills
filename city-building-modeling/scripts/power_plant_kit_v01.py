"""Industrial detail kit for the city gas power plant (Blender 5.x; metres, Z up).
Geo collects geometry per material in bmesh and flushes one object per material, so a part with thousands of ribs/rails/rungs stays a handful of objects.
Shading: every face smooth, edges sharper than SMOOTH_DEG marked sharp (boxes stay flat, cylinders/tubes stay round).
Reference: art/references/city/power-plant-v01/lock.md
"""
import bpy,bmesh,math
from mathutils import Vector,Matrix

SMOOTH_DEG=38
def frame(z,up=(0,0,1)):
    """4x4 rotation whose local Z = z; local Y lies in the plane of z and up (so a beam's height h stands 'up')."""
    z=Vector(z).normalized();u=Vector(up).normalized()
    if abs(z.dot(u))>.999:u=Vector((1,0,0)) if abs(z.x)<.9 else Vector((0,1,0))
    x=u.cross(z).normalized();y=z.cross(x)
    return Matrix((x,y,z)).transposed().to_4x4()

class Geo:
    def __init__(s,kit,name):s.kit=kit;s.name=name;s.b={}
    def bm(s,m):
        if m not in s.b:s.b[m]=bmesh.new()
        return s.b[m]
    def boxM(s,m,M):
        bm=s.bm(m);r=bmesh.ops.create_cube(bm,size=1.0);bmesh.ops.transform(bm,matrix=M,verts=r['verts'])
    def box(s,m,c,d,rz=0.,rx=0.,ry=0.):
        if min(d)<=0:return
        s.boxM(m,Matrix.Translation(Vector(c))@Matrix.Rotation(rz,4,'Z')@Matrix.Rotation(ry,4,'Y')@Matrix.Rotation(rx,4,'X')@Matrix.Diagonal((d[0],d[1],d[2],1)))
    def boxa(s,m,a,b):
        """axis-aligned box between two corners"""
        a=Vector(a);b=Vector(b);s.box(m,(a+b)/2,(abs(b.x-a.x),abs(b.y-a.y),abs(b.z-a.z)))
    def beam(s,m,p0,p1,w,h=None,up=(0,0,1)):
        p0=Vector(p0);p1=Vector(p1);v=p1-p0;L=v.length
        if L<1e-5:return
        s.boxM(m,Matrix.Translation((p0+p1)/2)@frame(v,up)@Matrix.Diagonal((w,h or w,L,1)))
    def hbeam(s,m,p0,p1,b=.3,h=.3,tf=.022,tw=.014,up=(0,0,1)):
        """H/I section: flanges width b (local x), depth h (local y)."""
        p0=Vector(p0);p1=Vector(p1);v=p1-p0;L=v.length
        if L<1e-5:return
        T=Matrix.Translation((p0+p1)/2)@frame(v,up)
        for cy,dx,dy in ((h/2-tf/2,b,tf),(-h/2+tf/2,b,tf),(0,tw,h-2*tf)):s.boxM(m,T@Matrix.Translation((0,cy,0))@Matrix.Diagonal((dx,dy,L,1)))
    def angle(s,m,p0,p1,a=.08,t=.008,up=(0,0,1)):
        """L angle section (lattice members)."""
        p0=Vector(p0);p1=Vector(p1);v=p1-p0;L=v.length
        if L<1e-5:return
        T=Matrix.Translation((p0+p1)/2)@frame(v,up)
        s.boxM(m,T@Matrix.Translation((0,-a/2+t/2,0))@Matrix.Diagonal((a,t,L,1)));s.boxM(m,T@Matrix.Translation((-a/2+t/2,0,0))@Matrix.Diagonal((t,a,L,1)))
    def cyl(s,m,p0,p1,r,seg=16,r1=None,cap=True):
        p0=Vector(p0);p1=Vector(p1);v=p1-p0;L=v.length
        if L<1e-5:return
        bm=s.bm(m);bmesh.ops.create_cone(bm,cap_ends=cap,cap_tris=False,segments=seg,radius1=r,radius2=(r if r1 is None else r1),depth=L,matrix=Matrix.Translation((p0+p1)/2)@frame(v))
    def disc(s,m,c,r,t,axis=(0,0,1),seg=16):
        c=Vector(c);a=Vector(axis).normalized()*t/2;s.cyl(m,c-a,c+a,r,seg)
    def sphere(s,m,c,r,seg=12,rings=8,scale=(1,1,1)):
        bm=s.bm(m);res=bmesh.ops.create_uvsphere(bm,u_segments=seg,v_segments=rings,radius=r)
        bmesh.ops.transform(bm,matrix=Matrix.Translation(Vector(c))@Matrix.Diagonal((*scale,1)),verts=res['verts'])
    def lathe(s,m,prof,c=(0,0,0),seg=32,axis=None):
        """revolve (r,z) profile around local Z; r==0 rows collapse to one pole vertex. axis: optional direction for local Z."""
        bm=s.bm(m);c=Vector(c);R=frame(axis) if axis else Matrix.Identity(4);rows=[]
        for r,z in prof:
            if r<=1e-6:rows.append([bm.verts.new(c+(R@Vector((0,0,z,1))).to_3d())])
            else:rows.append([bm.verts.new(c+(R@Vector((r*math.cos(2*math.pi*k/seg),r*math.sin(2*math.pi*k/seg),z,1))).to_3d()) for k in range(seg)])
        for A,B in zip(rows[:-1],rows[1:]):
            for k in range(seg):
                if len(A)==1 and len(B)==1:continue
                if len(A)==1:bm.faces.new((A[0],B[(k+1)%seg],B[k]))
                elif len(B)==1:bm.faces.new((A[k],A[(k+1)%seg],B[0]))
                else:bm.faces.new((A[k],A[(k+1)%seg],B[(k+1)%seg],B[k]))
    def torus(s,m,c,R,r,normal=(0,0,1),su=24,sv=6,a0=0.,a1=2*math.pi):
        bm=s.bm(m);c=Vector(c);F=frame(normal);full=abs(a1-a0-2*math.pi)<1e-6;nu=su if full else su+1;rows=[]
        for i in range(nu):
            a=a0+(a1-a0)*i/su;ca,sa=math.cos(a),math.sin(a);row=[]
            for j in range(sv):
                b=2*math.pi*j/sv;rr=R+r*math.cos(b);row.append(bm.verts.new(c+(F@Vector((rr*ca,rr*sa,r*math.sin(b),1))).to_3d()))
            rows.append(row)
        pairs=list(zip(rows,rows[1:]+([rows[0]] if full else [])))
        for A,B in pairs:
            for j in range(sv):bm.faces.new((A[j],B[j],B[(j+1)%sv],A[(j+1)%sv]))
    def mesh(s,m,verts,faces):
        bm=s.bm(m);vs=[bm.verts.new(Vector(v)) for v in verts]
        for f in faces:
            try:bm.faces.new([vs[i] for i in f])
            except ValueError:pass
    def prism(s,m,pts,z0,z1):
        """vertical extrusion of an XY polygon (counter-clockwise)"""
        n=len(pts);V=[(x,y,z0) for x,y in pts]+[(x,y,z1) for x,y in pts]
        F=[tuple(range(n))[::-1],tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)];s.mesh(m,V,F)
    def loft(s,m,A,B,cap=True):
        """quad-loop loft between two closed loops of equal length"""
        n=len(A);V=list(A)+list(B);F=[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
        if cap:F+=[tuple(range(n))[::-1],tuple(range(n,2*n))]
        s.mesh(m,V,F)
    def flush(s,smooth_deg=None,recalc=True):
        out=[];lim=math.cos(math.radians(smooth_deg or SMOOTH_DEG))
        for m,bm in s.b.items():
            if recalc:bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            bm.normal_update()
            for f in bm.faces:f.smooth=True
            for e in bm.edges:
                lf=e.link_faces
                if len(lf)!=2 or lf[0].normal.dot(lf[1].normal)<lim:e.smooth=False
            nm=s.name+'_'+m.name.replace('PP_','');me=bpy.data.meshes.new(nm);bm.to_mesh(me);bm.free()
            o=bpy.data.objects.new(nm,me);s.kit.adopt(o,m);out.append(o)
        s.b={};return out

# ---------------- wall frame: u along the wall, v up, w outward ----------------
class WF:
    def __init__(s,O,rz,ns=-1):s.O=Vector(O);s.rz=rz;s.ns=ns;s.R=Matrix.Rotation(rz,3,'Z')
    def p(s,u,v,w=0.):return s.O+s.R@Vector((u,s.ns*w,v))
    def out(s):return s.R@Vector((0,s.ns,0))
    def along(s):return s.R@Vector((1,0,0))
    def box(s,g,m,u,v,w,du,dv,dw):
        if du>0 and dv>0 and dw>0:g.box(m,s.p(u,v,w),(du,dw,dv),rz=s.rz)

# ---------------- pipes ----------------
def fillet(pts,rad,n=6):
    P=[Vector(p) for p in pts];out=[P[0]]
    for i in range(1,len(P)-1):
        a,b,c=P[i-1],P[i],P[i+1];d1=(b-a);d2=(c-b)
        if d1.length<1e-6 or d2.length<1e-6:continue
        d1.normalize();d2.normalize();ang=math.acos(max(-1,min(1,d1.dot(d2))))
        if ang<1e-3:out.append(b);continue
        t=min(rad*math.tan(ang/2),(b-a).length*.45,(c-b).length*.45);p1=b-d1*t;p2=b+d2*t
        for k in range(n+1):
            q=k/n;out.append((1-q)**2*p1+2*(1-q)*q*b+q*q*p2)
    out.append(P[-1]);return out
def tube(g,m,pts,r,seg=12,bend=None,cap=True):
    P=fillet(pts,bend or 2.2*r) if len(pts)>2 else [Vector(p) for p in pts]
    Q=[P[0]]
    for p in P[1:]:
        if (p-Q[-1]).length>1e-4:Q.append(p)
    P=Q
    if len(P)<2:return
    T=[(P[min(i+1,len(P)-1)]-P[max(i-1,0)]).normalized() for i in range(len(P))]
    a=Vector((0,0,1)) if abs(T[0].z)<.9 else Vector((1,0,0));n=a.cross(T[0]).normalized();bm=g.bm(m);V=[]
    for i,p in enumerate(P):
        t=T[i];n=(n-t*n.dot(t))
        if n.length<1e-6:n=(Vector((0,0,1)) if abs(t.z)<.9 else Vector((1,0,0))).cross(t)
        n.normalize();b=t.cross(n)
        V.append([bm.verts.new(p+(n*math.cos(2*math.pi*k/seg)+b*math.sin(2*math.pi*k/seg))*r) for k in range(seg)])
    for A,B in zip(V[:-1],V[1:]):
        for k in range(seg):bm.faces.new((A[k],A[(k+1)%seg],B[(k+1)%seg],B[k]))
    if cap:bm.faces.new(V[0][::-1]);bm.faces.new(V[-1])
def flange(g,m,c,axis,r,t=.04,seg=16):
    g.disc(m,c,r*1.45,t,axis,seg)
def valve(g,mbody,mwheel,c,axis,r,wheel_up=True):
    """gate/globe valve on a pipe: body, two flanges, bonnet + stem + hand wheel"""
    c=Vector(c);ax=Vector(axis).normalized();g.sphere(mbody,c,r*1.35,12,8,(1,1,1))
    for sgn in (-1,1):flange(g,mbody,c+ax*sgn*r*1.4,ax,r)
    up=Vector((0,0,1)) if wheel_up else Vector((0,0,-1))
    g.cyl(mbody,c,c+up*r*2.6,r*.55,10);g.cyl(mbody,c+up*r*2.6,c+up*r*4.0,r*.12,8);g.torus(mwheel,c+up*r*4.0,r*1.2,r*.12,up,16,5)
    for k in range(3):
        a=k*2*math.pi/3;q=Vector((math.cos(a),math.sin(a),0))*r*1.2;g.beam(mwheel,c+up*r*4.0,c+up*r*4.0+q,r*.12,r*.12)

# ---------------- access steel ----------------
def railing(g,m,pts,z=None,h=1.1,step=1.6,closed=False,post=.05,rail=.042,kick=True,mid=True):
    P=[Vector((p[0],p[1],p[2] if len(p)>2 else (z or 0.))) for p in pts]
    if closed:P=P+[P[0]]
    up=Vector((0,0,1))
    for i,(a,b) in enumerate(zip(P[:-1],P[1:])):
        d=b-a;L=d.length
        if L<1e-4:continue
        n=max(1,math.ceil(L/step))
        for k in range(n+1):
            if k==n and (closed or i<len(P)-2):continue
            q=a+d*(k/n);g.box(m,q+up*(h/2),(post,post,h))
        g.beam(m,a+up*h,b+up*h,rail,rail)
        if mid:g.beam(m,a+up*(h*.52),b+up*(h*.52),rail*.8,rail*.8)
        if kick:g.beam(m,a+up*.07,b+up*.07,.008,.12)
def grating(g,m,mframe,c,d,rz=0.):
    """platform deck: grating slab + edge angle"""
    g.box(m,(c[0],c[1],c[2]-.02),(d[0],d[1],.04),rz)
    R=Matrix.Rotation(rz,3,'Z')
    for sx,sy,dx,dy in ((0,d[1]/2,d[0],.012),(0,-d[1]/2,d[0],.012),(d[0]/2,0,.012,d[1]),(-d[0]/2,0,.012,d[1])):
        g.box(mframe,Vector(c)+R@Vector((sx,sy,-.05)),(dx,dy,.12),rz)
def flight(g,ms,mt,mr,p0,p1,w=1.0,rails=(-1,1)):
    """straight stair flight from p0 (bottom nosing, centre) to p1 (top landing edge, centre): channel stringers, grating treads, sloped handrails"""
    p0=Vector(p0);p1=Vector(p1);d=p1-p0;hor=Vector((d.x,d.y,0));run=hor.length;rise=d.z
    if run<1e-3:return
    u=hor.normalized();nrm=Vector((-u.y,u.x,0));k=max(2,round(rise/.18));rz=math.atan2(u.y,u.x)
    for sg in (-1,1):
        off=nrm*(sg*(w/2+.02))
        g.beam(ms,p0+off+Vector((0,0,-.12)),p1+off+Vector((0,0,-.12)),.035,.25,up=(0,0,1))
    for i in range(k):
        c=p0+u*(run*(i+.5)/k)+Vector((0,0,rise*(i+.5)/k))
        g.box(mt,c,(run/k+.04,w,.035),rz)
    for sg in rails:
        off=nrm*(sg*(w/2+.04));railing(g,mr,[p0+off,p1+off],h=1.0,step=1.3,kick=False)
def zigzag_stair(g,ms,mt,mr,base,u,levels,run=3.4,w=1.0,gap=.15,land=1.3):
    """switch-back stair tower: flights alternate along +u/-u; base = foot of the first flight (centre of the first lane); levels = list of landing heights.
    returns landing boxes (centre, size) so callers can join walkways."""
    u=Vector((u[0],u[1],0)).normalized();nrm=Vector((-u.y,u.x,0));base=Vector(base);z=base.z;lanes=(0,1);out=[]
    for i,zt in enumerate(levels):
        lane=i%2;off=nrm*(lane*(w+gap));d=u if lane==0 else -u
        start=base+off+(Vector((0,0,0)) if lane==0 else u*run);start.z=z
        end=start+d*run;end.z=zt
        flight(g,ms,mt,mr,start,end,w,rails=(-1,1))
        lc=(base+u*(run+land/2) if lane==0 else base-u*(land/2))+nrm*((w+gap)/2);lc.z=zt
        grating(g,mt,ms,lc,(land,2*w+gap),math.atan2(u.y,u.x));out.append((lc,(land,2*w+gap)))
        z=zt
    return out
def ladder(g,m,base,top_z,out,w=.46,cage=True,cage_from=2.5):
    """vertical ladder fixed to a wall/shell: base = point on the surface at the ladder centre (z = foot), out = horizontal unit vector away from the surface"""
    out=Vector((out[0],out[1],0)).normalized();side=Vector((-out.y,out.x,0));b=Vector(base);z0=b.z;H=top_z+1.1-z0;off=out*.22
    for sg in (-1,1):g.box(m,b+off+side*(sg*w/2)+Vector((0,0,H/2)),(.06,.06,H) if abs(out.x)>abs(out.y) else (.06,.06,H))
    n=int((top_z-z0)/.3)
    for i in range(1,n+1):g.beam(m,b+off-side*(w/2)+Vector((0,0,i*.3)),b+off+side*(w/2)+Vector((0,0,i*.3)),.026,.026)
    for zz in [z0+.8+2.0*i for i in range(int((top_z-z0)/2.0)+1)]:
        for sg in (-1,1):g.beam(m,b+side*(sg*w/2)+Vector((0,0,zz)),b+off+side*(sg*w/2)+Vector((0,0,zz)),.05,.012)
    if cage and top_z-z0>cage_from+1:
        cc=b+off+out*.36;a0=math.atan2(-side.y,-side.x);zz=z0+cage_from
        while zz<=top_z+1.0:
            ring=[cc+Vector((math.cos(a0-math.pi*k/8)*.38,math.sin(a0-math.pi*k/8)*.38,zz)) for k in range(9)]
            tube(g,m,ring,.012,6,bend=.01,cap=False);zz+=1.0
        for k in (1,3,5,7):
            a=a0-math.pi*k/8;p=cc+Vector((math.cos(a)*.38,math.sin(a)*.38,0))
            g.beam(m,Vector((p.x,p.y,z0+cage_from)),Vector((p.x,p.y,top_z+1.0)),.05,.008,up=(p-cc))
def louvre_bank(g,mb,mf,F,u0,u1,v0,v1,pitch=.14,tilt=42,w0=0.,depth=.10,frame=.06):
    """inclined louvre blades between u0..u1, v0..v1 on a wall frame, with a perimeter frame"""
    n=max(1,int((v1-v0)/pitch));t=math.radians(tilt)
    for i in range(n):
        v=v0+(i+.5)*(v1-v0)/n
        g.boxM(mb,Matrix.Translation(F.p((u0+u1)/2,v,w0+depth/2))@Matrix.Rotation(F.rz,4,'Z')@Matrix.Rotation(-F.ns*t,4,'X')@Matrix.Diagonal((u1-u0,depth*1.15,.012,1)))
    for uu in (u0,u1):F.box(g,mf,uu,(v0+v1)/2,w0+depth/2,frame,v1-v0+frame,depth+.02)
    for vv in (v0,v1):F.box(g,mf,(u0+u1)/2,vv,w0+depth/2,u1-u0+frame,frame,depth+.02)
def ribbed(g,m,F,u0,u1,v0,v1,pitch=.30,rib=.045,dr=.035,base=True,vtop=None,skip=()):
    """profiled metal sheet: base sheet + trapezoid ribs. vtop(u) gives a sloped top (gables). skip = [(ua,ub,va,vb)] openings."""
    if base and vtop is None:F.box(g,m,(u0+u1)/2,(v0+v1)/2,-.04,u1-u0,v1-v0,.08)
    n=int((u1-u0)/pitch)
    for i in range(n):
        u=u0+(i+.5)*(u1-u0)/n;top=min(v1,vtop(u)) if vtop else v1
        if top<=v0:continue
        segs=[(v0,top)]
        for ua,ub,va,vb in skip:
            if ua-rib<=u<=ub+rib:
                new=[]
                for a,b in segs:
                    if vb<=a or va>=b:new.append((a,b))
                    else:
                        if va>a:new.append((a,va))
                        if vb<b:new.append((vb,b))
                segs=new
        for a,b in segs:
            if b-a>.02:F.box(g,m,u,(a+b)/2,dr/2,rib,b-a,dr)
def insulator(g,mi,mm,p0,p1,r=.075,shed=.17,pitch=.10,seg=12):
    """composite post insulator: core + alternating sheds + metal end fittings"""
    p0=Vector(p0);p1=Vector(p1);v=p1-p0;L=v.length;ax=v.normalized()
    g.cyl(mm,p0,p0+ax*.12,r*1.6,seg);g.cyl(mm,p1-ax*.12,p1,r*1.6,seg);g.cyl(mi,p0+ax*.12,p1-ax*.12,r,seg)
    n=int((L-.3)/pitch)
    for i in range(n):
        c=p0+ax*(.18+i*pitch);g.cyl(mi,c,c+ax*.025,shed if i%2==0 else shed*.75,seg,r1=(shed if i%2==0 else shed*.75)*.92)
def string(g,mi,mm,top,bot,shed=.13,pitch=.15):
    """suspension insulator string (hanging)"""
    insulator(g,mi,mm,bot,top,.035,shed,pitch,10)
def catenary(g,m,a,b,sag=.6,r=.018,n=12):
    a=Vector(a);b=Vector(b);pts=[a+(b-a)*(i/n)-Vector((0,0,sag*4*(i/n)*(1-i/n))) for i in range(n+1)]
    tube(g,m,pts,r,6,bend=.01,cap=False)
def lattice_column(g,m,base,H,w0,w1,panel=1.2,a=.09,brace=.06):
    """square lattice column (4 angle chords tapering w0->w1, zig-zag bracing on all faces)"""
    b=Vector(base);n=max(1,int(H/panel))
    def corner(i,z):
        w=(w0+(w1-w0)*z/H)/2;sx=(1,-1,-1,1)[i];sy=(1,1,-1,-1)[i];return b+Vector((sx*w,sy*w,z))
    for i in range(4):g.angle(m,corner(i,0),corner(i,H),a,.008)
    for k in range(n):
        z0=H*k/n;z1=H*(k+1)/n
        for i in range(4):
            j=(i+1)%4
            if k%2==0:g.beam(m,corner(i,z0),corner(j,z1),brace,.01)
            else:g.beam(m,corner(j,z0),corner(i,z1),brace,.01)
            g.beam(m,corner(i,z1),corner(j,z1),brace,.01)
def lattice_beam(g,m,p0,p1,d=1.0,panel=1.2,a=.08,brace=.05):
    """horizontal box truss of square section d between p0 and p1 (centre line)"""
    p0=Vector(p0);p1=Vector(p1);v=p1-p0;L=v.length;u=v.normalized();s=Vector((-u.y,u.x,0));z=Vector((0,0,1));n=max(1,int(L/panel))
    C=[s*d/2+z*d/2,-s*d/2+z*d/2,-s*d/2-z*d/2,s*d/2-z*d/2]
    for c in C:g.angle(m,p0+c,p1+c,a,.008)
    for k in range(n):
        q0=p0+v*(k/n);q1=p0+v*((k+1)/n)
        for i in range(4):
            j=(i+1)%4
            if k%2==0:g.beam(m,q0+C[i],q1+C[j],brace,.01)
            else:g.beam(m,q0+C[j],q1+C[i],brace,.01)
            g.beam(m,q1+C[i],q1+C[j],brace,.01)
def instance(kit,proto,name,loc,rz=0.):
    """linked duplicate of a part (meshes shared) under a new root placed at loc/rz"""
    r=bpy.data.objects.new(name,None);kit.col.objects.link(r)
    for k in proto.keys():r[k]=proto[k]
    r['instance_of']=proto.name;r.location=loc;r.rotation_euler.z=rz
    for o in [o for o in kit.col.objects if o.parent==proto]:
        c=o.copy();kit.col.objects.link(c);c.parent=r;c.matrix_parent_inverse=o.matrix_parent_inverse.copy();c.matrix_basis=o.matrix_basis.copy()
    return r
