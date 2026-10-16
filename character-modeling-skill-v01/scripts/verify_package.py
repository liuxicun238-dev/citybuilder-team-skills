"""Verify the portable package inventory without third-party dependencies."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf8'))
errors=[]
for item in manifest['files']:
 p=(root/item['path']).resolve()
 if root not in p.parents:errors.append('Unsafe manifest path: '+item['path']);continue
 if not p.is_file():errors.append('Missing: '+item['path']);continue
 if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:errors.append('Changed: '+item['path'])
if errors:
 print('\n'.join(errors));sys.exit(1)
print('Package verified:',len(manifest['files']),'files')
