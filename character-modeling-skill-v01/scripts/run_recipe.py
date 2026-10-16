"""Portable same-recipe character rebuild. No existing character mesh input."""
from pathlib import Path
import subprocess,os,json,hashlib,time,shutil,sys,argparse
P=Path(__file__).resolve().parents[1];R=P/'payload'
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);ap.add_argument('--blender',required=True);ap.add_argument('--resume',action='store_true');ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args()
O=args.out.resolve();PY=Path(sys.executable);BL=shutil.which(args.blender) or str(Path(args.blender).expanduser().resolve())
if O==P or P in O.parents:raise ValueError('Use an output directory outside the skill package')
if not Path(BL).is_file():raise FileNotFoundError('Blender executable not found: '+BL)
for dependency in ['numpy','scipy','skimage','PIL']:__import__(dependency)
if O.exists() and any(O.iterdir()) and not args.resume:raise FileExistsError('Choose an empty output directory or use --resume for an existing run')
O.mkdir(parents=True,exist_ok=True);W=O/'workspace';W.mkdir(exist_ok=True)
for d in ['tmp','blender-config','blender-scripts','blender-data','cache']: (O/d).mkdir(exist_ok=True)
env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(O/'tmp'),TMP=str(O/'tmp'),TMPDIR=str(O/'tmp'),BLENDER_USER_CONFIG=str(O/'blender-config'),BLENDER_USER_SCRIPTS=str(O/'blender-scripts'),BLENDER_USER_DATAFILES=str(O/'blender-data'),XDG_CACHE_HOME=str(O/'cache'),MODELING_DATASET_ROOT=str(O/'records'))
ver=subprocess.run([BL,'--version'],env=env,capture_output=True,text=True,encoding='utf8',errors='replace',check=True)
(O/'environment.json').write_text(json.dumps({'python':sys.version,'blender':ver.stdout,'blender_executable':BL},indent=2),encoding='utf8')
steps=[];manifest=[]
scriptnames=['zbrush_reference_head_v18.py','head_profile_cage_v01.py','repair_neck_preserve_face_v01.py','assemble_head_ear_preview_v02.py','build_nose_clay_v01.py','join_nose_surface_v08.py','retriangulate_nose_collar_v09.py','fair_nose_join_v10.py','fit_nose_transition_v12.py','shape_nose_root_v13.py','build_mouth_surface_v03.py','reform_mouth_v06.py','refine_chin_v02.py','fair_chin_v03.py','build_citizen_upper_body_v03.py','sculpt_upper_body_v05.py','build_citizen_arms_v03.py','build_citizen_hands_v04.py','build_upper_torso_complete_v03.py','refine_citizen_body_details_v01.py','fair_citizen_body_details_v02.py','rig_original_citizen_walk_v03.py','check_original_walk_v01.py','head_constrained_triangles_v01.py','record_modeling_step.py']
# Resume is explicit by completed step records; no existing mesh is imported from the original project.
for rel in [Path('tools/pipeline')/n for n in scriptnames]+[Path('.agents/skills/game-character-modeling/scripts')/n for n in ['orient_obj.py','inspect_obj.py','render_views.py']]+[Path('.agents/skills/game-ear-modeling/scripts')/n for n in ['build-ear-example.py','refine-ear-example.py']]:
 src=R/rel;dst=W/rel;dst.parent.mkdir(parents=True,exist_ok=True);s=src.read_text(encoding='utf-8-sig');s=s.replace('__CHAR_PROJECT__',W.as_posix()).replace('__CHAR_A18__',(W/'art/assets/authored/city/zbrush-reference-head-v01/a18').as_posix()).replace('__CHAR_BLENDER__',Path(BL).as_posix());dst.write_text(s,encoding='utf8');manifest.append({'source':str(rel),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'adapted_sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
for name in ['citizens-clay-male-v01','citizen-ear-clay-v01','citizen-nose-clay-v01','citizen-mouth-clay-v01']:
 src=R/'art/references'/name;dst=W/'art/references'/name;shutil.copytree(src,dst,dirs_exist_ok=True)
(W/'tools/pipeline/modeling_training_config.json').write_text(json.dumps({'dataset_root':str(O/'records')}))
A=W/'art/assets/authored/city/zbrush-reference-head-v01';A.mkdir(parents=True,exist_ok=True);E=W/'art/assets/authored/city/citizen-ear-sculpt-v01'
def run(label,cmd,expect):
 target=Path(expect);stamp=O/(label+'.done.json')
 if stamp.exists() and target.exists():
  prior=json.loads(stamp.read_text(encoding='utf8'))
  if hashlib.sha256(target.read_bytes()).hexdigest()!=prior['sha256']:raise RuntimeError('Completed output changed: '+str(target))
  return
 print('START',label,flush=True);t=time.time();log=O/(label+'.log')
 with log.open('w',encoding='utf8') as f:p=subprocess.run([str(x) for x in cmd],cwd=W,env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode or not target.exists():raise RuntimeError(str(label)+' failed, see '+str(log))
 d={'step':label,'seconds':time.time()-t,'output':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()};stamp.write_text(json.dumps(d,indent=2));print('DONE',label,flush=True)
def py(n,out,*extra):
 source=W/'tools/pipeline'/n
 command=[BL,'-b','--python',source] if 'import bpy' in source.read_text(encoding='utf8') else [PY,'-X','utf8','-B',source]
 run(n,[*command,*extra],out)
def orient(dir,raw,final):run('orient-'+dir,[PY,'-X','utf8','-B',W/'.agents/skills/game-character-modeling/scripts/orient_obj.py',A/dir/raw,'--out',A/dir/final,'--report',A/dir/'orientation.json'],A/dir/final)
(O/'recipe-manifest.json').write_text(json.dumps({'no_prebuilt_mesh_copied':True,'sources':manifest},ensure_ascii=False,indent=2))
if args.prepare_only:
 print('PREPARED',O);sys.exit(0)
py('zbrush_reference_head_v18.py',A/'a18/reference-head.obj')
(A/'topology-a19').mkdir(exist_ok=True)
run('head-orientation',[PY,'-X','utf8','-B',W/'.agents/skills/game-character-modeling/scripts/orient_obj.py',A/'a18/reference-head.obj','--out',A/'topology-a19/reference-head.obj','--report',A/'topology-a19/orientation.json'],A/'topology-a19/reference-head.obj')
py('head_profile_cage_v01.py',A/'profile-cage-v01/head.obj');py('repair_neck_preserve_face_v01.py',A/'preserve-face-neck-v05/head-neck-raw.obj');orient('preserve-face-neck-v05','head-neck-raw.obj','head-neck.obj')
run('ear-build',[PY,'-X','utf8','-B',W/'.agents/skills/game-ear-modeling/scripts/build-ear-example.py','--out',E/'a03'],E/'a03/ear.obj')
run('ear-refine',[PY,'-X','utf8','-B',W/'.agents/skills/game-ear-modeling/scripts/refine-ear-example.py','--out',E/'a04'],E/'a04/ear.obj')
py('assemble_head_ear_preview_v02.py',A/'ear-fit-v02/head-neck.obj');py('build_nose_clay_v01.py',W/'art/assets/authored/city/citizen-nose-sculpt-v01/a02/nose.obj');py('join_nose_surface_v08.py',A/'nose-fit-v08/head-neck.obj')
run('nose-collar',[BL,'-b','--python',W/'tools/pipeline/retriangulate_nose_collar_v09.py'],A/'nose-fit-v09/head-neck.obj')
for n,d in [('fair_nose_join_v10.py','nose-fit-v10'),('fit_nose_transition_v12.py','nose-fit-v12'),('shape_nose_root_v13.py','nose-fit-v13'),('build_mouth_surface_v03.py','mouth-fit-v03'),('reform_mouth_v06.py','mouth-fit-v06'),('refine_chin_v02.py','chin-refine-v02'),('fair_chin_v03.py','chin-refine-v03')]:py(n,A/d/'head-neck.obj')
for n,d in [('build_citizen_upper_body_v03.py','upper-body-v03'),('sculpt_upper_body_v05.py','upper-body-v05'),('build_citizen_arms_v03.py','arms-v03'),('build_citizen_hands_v04.py','hands-v04'),('build_upper_torso_complete_v03.py','torso-v03'),('refine_citizen_body_details_v01.py','body-detail-v01')]:
 raw='body.obj' if d=='upper-body-v05' else 'body-raw.obj';py(n,A/d/raw)
 if raw!='body.obj':orient(d,raw,'body.obj')
py('fair_citizen_body_details_v02.py',A/'body-detail-v02/body.obj')
run('inspect-full-body',[PY,'-X','utf8','-B',W/'.agents/skills/game-character-modeling/scripts/inspect_obj.py',A/'body-detail-v02/body.obj','--unit','cm','--out',O/'inspection.json'],O/'inspection.json')
run('render-full-body',[BL,'-b','--python',W/'.agents/skills/game-character-modeling/scripts/render_views.py','--','--mesh',A/'body-detail-v02/body.obj','--unit','cm','--out',O/'render'],O/'render/inspection.blend')
run('rig-walk',[BL,'-b','--python',W/'tools/pipeline/rig_original_citizen_walk_v03.py'],A/'walk-test-v03/checks.json')
run('walk-audit',[BL,'-b','--python',W/'tools/pipeline/check_original_walk_v01.py'],A/'walk-test-v03/audit.json')
run('package',[BL,'-b','--python',P/'scripts/package_and_audit.py','--',O],O/'deliverable/citizen-original-cm.obj')
run('boundary-classification',[PY,'-X','utf8','-B',P/'scripts/classify_boundaries.py',O],O/'boundary-classification.json')
from PIL import Image
ims=[Image.open(p).convert('RGB') for p in sorted((A/'walk-test-v03/frames').glob('*.png'))]
if len(ims)!=16:raise RuntimeError('Expected 16 walk preview frames')
ims[0].save(O/'deliverable/walk-preview.gif',save_all=True,append_images=ims[1:],duration=83,loop=0)
files=[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (O/'deliverable').iterdir() if p.is_file() and p.name!='manifest.json']
(O/'deliverable/manifest.json').write_text(json.dumps({'files':files,'status':'Generated; requires actual visual inspection. Not game-ready.'},indent=2),encoding='utf8')
print('COMPLETE',O,flush=True)
