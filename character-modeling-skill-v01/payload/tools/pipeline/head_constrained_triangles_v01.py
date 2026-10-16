import json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
r=Path(sys.argv[sys.argv.index('--')+1]);d=json.loads((r/'cdt-input.json').read_text())
v,e,f,ov,oe,of=delaunay_2d_cdt([Vector(p) for p in d['uv']],d['edges'],[],0,1e-8,True)
if any(not ids for ids in ov):raise RuntimeError('Unexpected constraint intersection or inserted vertex')
faces=[[ov[i][0] for i in face] for face in f]
(r/'cdt-output.json').write_text(json.dumps({'faces':faces,'merged_vertices':sum(len(x)>1 for x in ov),'input_vertices':len(d['uv']),'output_vertices':len(v),'method':'Blender constrained Delaunay; explicit eyelid lip nostril edges'}))
