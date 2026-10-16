# Image edit with the user's image endpoint (multipart model + prompt + image; verified 2026-09-24 on provider 01). Used to relight / paint over an actual
# game capture while keeping its composition (lighting targets, material targets).
# Usage: powershell -File gen_edit.ps1 -Image <in.png> -PromptFile <prompt.txt> -Out <out.png> [-Provider 01] [-TimeoutSec 500]
# The key is read from the DPAPI file named in the provider config and never printed or written anywhere.
param([Parameter(Mandatory)][string]$Image, [Parameter(Mandatory)][string]$PromptFile, [Parameter(Mandatory)][string]$Out, [string]$Provider = '01', [int]$TimeoutSec = 500, [string]$Size = '')   # -Size e.g. 1536x1024 (provider 02; 01 rejects size)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$cfg = Get-Content (Join-Path $root ('tools\pipeline\' + $(if ($Provider -eq '02') { 'image-provider-02.json' } else { 'image-provider.json' }))) -Raw -Encoding utf8 | ConvertFrom-Json
$url = if ($cfg.verified_edit_url) { $cfg.verified_edit_url } else { $cfg.generation_url -replace 'generations$', 'edits' }
$dir = Split-Path -Parent $Out; New-Item -ItemType Directory -Force -Path $dir | Out-Null
$resp = Join-Path $dir ('edit-response-' + [IO.Path]::GetFileNameWithoutExtension($Out) + '.json')
$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR((ConvertTo-SecureString ((Get-Content $cfg.credential_path -Raw).Trim())))
$k = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b); [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)
$extra = @(); if ($Size) { $extra = @('-F', "size=$Size") }
& curl.exe -sS --max-time $TimeoutSec -o $resp -w "HTTP %{http_code} in %{time_total}s`n" -H "Authorization: Bearer $k" -F "model=$($cfg.model)" -F "prompt=<$PromptFile" -F "image=@$Image;type=image/png" @extra $url
$k = $null
$env:GEN_RESP = (Resolve-Path $resp).Path; $env:GEN_OUT = $Out
$py = @"
import json, base64, os, pathlib, sys, urllib.request
r = json.loads(pathlib.Path(os.environ['GEN_RESP']).read_text(encoding='utf-8')); out = pathlib.Path(os.environ['GEN_OUT'])
if 'data' not in r: print('NO_IMAGE', json.dumps(r)[:500]); sys.exit(1)
it = r['data'][0]
if it.get('b64_json'): out.write_bytes(base64.b64decode(it['b64_json']))
else: urllib.request.urlretrieve(it['url'], out)
pathlib.Path(os.environ['GEN_RESP']).unlink()
from PIL import Image; print('SAVED', out, Image.open(out).size)
"@
$py | & 'D:\python\python.exe' -
