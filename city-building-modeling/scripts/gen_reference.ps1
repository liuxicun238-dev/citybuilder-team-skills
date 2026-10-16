# Generate a multi-panel modeling reference with the user's image endpoint (text-only /v1/images/generations).
# Usage: powershell -File gen_reference.ps1 -Dir <reference dir> -PromptFile <prompt.txt> [-Out reference.png]
# The key is read from the DPAPI file named in tools/pipeline/image-provider.json and never printed or written anywhere.
param([Parameter(Mandatory)][string]$Dir, [Parameter(Mandatory)][string]$PromptFile, [string]$Out = 'reference.png', [int]$TimeoutSec = 400, [string]$Provider = '01', [string]$Size = '')   # Provider 01 = image-provider.json (lunaxias), 02 = image-provider-02.json (apikey.fan)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$cfgName = if ($Provider -eq '02') { 'image-provider-02.json' } else { 'image-provider.json' }
$cfg = Get-Content (Join-Path $root ('tools\pipeline\' + $cfgName)) -Raw -Encoding utf8 | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$prompt = [IO.File]::ReadAllText((Resolve-Path $PromptFile).Path, [Text.Encoding]::UTF8)   # Get-Content -Raw adds PS properties -> JSON {"value":...} -> HTTP 400
$bh = @{ model = $cfg.model; prompt = $prompt }; if ($Size) { $bh.size = $Size }
$body = $bh | ConvertTo-Json -Compress
$req = Join-Path $Dir 'request-body.json'; [IO.File]::WriteAllText($req, $body, (New-Object Text.UTF8Encoding $false))
$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR((ConvertTo-SecureString ((Get-Content $cfg.credential_path -Raw).Trim())))
$k = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b); [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)
$resp = Join-Path $Dir 'response.json'
& curl.exe -sS --max-time $TimeoutSec -o $resp -w "HTTP %{http_code} in %{time_total}s`n" -H "Authorization: Bearer $k" -H "Content-Type: application/json" --data-binary "@$req" $cfg.generation_url
$k = $null
$env:GEN_DIR = (Resolve-Path $Dir).Path; $env:GEN_OUT = $Out   # pass non-ASCII paths via env, not inside piped code (console encoding mangles them)
$py = @"
import json, base64, pathlib, sys
import os; d = pathlib.Path(os.environ['GEN_DIR']); out = os.environ['GEN_OUT']; r = json.loads((d / 'response.json').read_text(encoding='utf-8'))
if 'data' not in r: print('NO_IMAGE', json.dumps(r)[:500]); sys.exit(1)
it = r['data'][0]
if it.get('b64_json'): (d / out).write_bytes(base64.b64decode(it['b64_json']))
else:
    import urllib.request; urllib.request.urlretrieve(it['url'], d / out)
(d / 'response.json').unlink()
from PIL import Image; print('SAVED', d / out, Image.open(d / out).size, {k: v for k, v in r.items() if k not in ('data',)})
"@
$py | & 'D:\python\python.exe' -
