#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
mkdir -p "$STATE"

usage(){
  cat <<'EOF'
usage: venice_fleshpunk_phone.sh generate "PROMPT" [SEED]
       venice_fleshpunk_phone.sh status
       venice_fleshpunk_phone.sh receipts

Generates through THECAULDRON's localhost-only ComfyUI using the installed
SD 1.5 checkpoint + drw_fleshpunk_v1 LoRA, then copies the PNG back to phone.
EOF
}

case "${1:-}" in
  status)
    python "$ROOT/tools/ssh_axis.py" check --target cauldron --json
    exit $?
    ;;
  receipts)
    [ -f "$STATE/latest.json" ] && cat "$STATE/latest.json" || { echo '{}'; exit 2; }
    exit 0
    ;;
  generate) ;;
  *) usage >&2; exit 64 ;;
esac

PROMPT="${2:-}"
[ -n "$PROMPT" ] || { echo 'PROMPT is required' >&2; exit 64; }
SEED="${3:-}"
if [ -z "$SEED" ]; then
  SEED="$(python - <<'PY'
import secrets
print(secrets.randbelow(2**31-1)+1)
PY
)"
fi
case "$SEED" in (*[!0-9]*|'') echo 'SEED must be an integer' >&2; exit 64;; esac

# Prove the endpoint before sending any work. If the cached/default address is
# stale, reuse the existing authenticated WLAN rediscovery path.
if ! python "$ROOT/tools/ssh_axis.py" check --target cauldron --json >"$STATE/ssh-axis.json"; then
  if [ ! -f "$ROOT/tools/resolve_cauldron_ssh.py" ]; then
    cat "$STATE/ssh-axis.json" >&2
    echo 'BLOCKED: THECAULDRON SSH Axis is not callable and resolver is unavailable.' >&2
    exit 41
  fi
  RESOLVED="$(python "$ROOT/tools/resolve_cauldron_ssh.py" 2>"$STATE/resolve.err")" || {
    cat "$STATE/resolve.err" >&2 || true
    echo 'BLOCKED: THECAULDRON could not be rediscovered.' >&2
    exit 41
  }
  export FORTRESS_CAULDRON_SSH="$RESOLVED"
  python "$ROOT/tools/ssh_axis.py" check --target cauldron --json >"$STATE/ssh-axis.json" || {
    cat "$STATE/ssh-axis.json" >&2
    exit 41
  }
fi

ENDPOINT="${FORTRESS_CAULDRON_SSH:-dclar@192.168.40.213}"
if [ "$ENDPOINT" = 'dclar@192.168.40.213' ] && [ -s "$HOME/.local/state/fortress-online/cauldron-ssh-endpoint.json" ]; then
  CACHED="$(python - "$HOME/.local/state/fortress-online/cauldron-ssh-endpoint.json" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1],encoding='utf-8')).get('endpoint',''))
except Exception: print('')
PY
)"
  [ -z "$CACHED" ] || ENDPOINT="$CACHED"
fi
HOSTPORT="$ENDPOINT"; PORT=22
if [[ "$HOSTPORT" =~ ^(.+):([0-9]+)$ ]]; then HOSTPORT="${BASH_REMATCH[1]}"; PORT="${BASH_REMATCH[2]}"; fi

REQ="$STATE/request.json"
python - "$PROMPT" "$SEED" >"$REQ" <<'PY'
import json,sys
print(json.dumps({'prompt':sys.argv[1], 'seed':int(sys.argv[2])}, ensure_ascii=False))
PY

REMOTE_REQ='C:/Users/Public/venice-fleshpunk-request.json'
REMOTE_PS='C:/Users/Public/venice-fleshpunk-generate.ps1'
REMOTE_RESULT='C:/Users/Public/venice-fleshpunk-result.json'
REMOTE_PNG='C:/Users/Public/venice-fleshpunk-latest.png'
LOCAL_PS="$STATE/generate.ps1"
cat >"$LOCAL_PS" <<'PS'
$ErrorActionPreference='Stop'
$req = Get-Content -Raw 'C:\Users\Public\venice-fleshpunk-request.json' | ConvertFrom-Json
$comfy = 'http://127.0.0.1:8188'
$checkpoint = 'v1-5-pruned-emaonly.safetensors'
$lora = 'drw_fleshpunk_v1.safetensors'
$loraPath = Join-Path $env:LOCALAPPDATA "VeniceImageBridge\ComfyUI\models\loras\$lora"
if (-not (Test-Path $loraPath)) { throw "Fleshpunk LoRA missing: $loraPath" }
$loraSha = (Get-FileHash -Algorithm SHA256 $loraPath).Hash.ToLowerInvariant()
try { $null = Invoke-RestMethod -TimeoutSec 5 "$comfy/system_stats" } catch { throw "ComfyUI unavailable on 127.0.0.1:8188: $($_.Exception.Message)" }

$workflow = @{
  '1'=@{class_type='CheckpointLoaderSimple';inputs=@{ckpt_name=$checkpoint}}
  '2'=@{class_type='LoraLoader';inputs=@{model=@('1',0);clip=@('1',1);lora_name=$lora;strength_model=0.85;strength_clip=0.85}}
  '3'=@{class_type='CLIPTextEncode';inputs=@{text=[string]$req.prompt;clip=@('2',1)}}
  '4'=@{class_type='CLIPTextEncode';inputs=@{text='low quality, blurry, malformed anatomy, watermark, text';clip=@('2',1)}}
  '5'=@{class_type='EmptyLatentImage';inputs=@{width=512;height=768;batch_size=1}}
  '6'=@{class_type='KSampler';inputs=@{model=@('2',0);seed=[int64]$req.seed;steps=28;cfg=7.0;sampler_name='euler_ancestral';scheduler='normal';positive=@('3',0);negative=@('4',0);latent_image=@('5',0);denoise=1.0}}
  '7'=@{class_type='VAEDecode';inputs=@{samples=@('6',0);vae=@('1',2)}}
  '8'=@{class_type='SaveImage';inputs=@{filename_prefix='Venice_Fleshpunk_Phone';images=@('7',0)}}
}
$body = @{prompt=$workflow} | ConvertTo-Json -Depth 20
$queued = Invoke-RestMethod -Method Post -ContentType 'application/json' -Body $body "$comfy/prompt"
$promptId = [string]$queued.prompt_id
if (-not $promptId) { throw 'ComfyUI returned no prompt_id' }
$deadline=(Get-Date).AddMinutes(5)
$out=$null
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Milliseconds 750
  $history=Invoke-RestMethod -TimeoutSec 10 "$comfy/history/$promptId"
  $record=$history.$promptId
  if ($record -and $record.outputs -and $record.outputs.'8' -and $record.outputs.'8'.images.Count -gt 0) { $out=$record.outputs.'8'.images[0]; break }
  if ($record -and $record.status -and $record.status.status_str -eq 'error') { throw "ComfyUI prompt failed: $($record.status | ConvertTo-Json -Compress -Depth 8)" }
}
if (-not $out) { throw "Timed out waiting for ComfyUI prompt $promptId" }
$filename=[string]$out.filename; $subfolder=[string]$out.subfolder
$outputRoot=Join-Path $env:LOCALAPPDATA 'VeniceImageBridge\ComfyUI\output'
$src=if ($subfolder) { Join-Path (Join-Path $outputRoot $subfolder) $filename } else { Join-Path $outputRoot $filename }
if (-not (Test-Path $src)) { throw "Generated image missing: $src" }
Copy-Item -Force $src 'C:\Users\Public\venice-fleshpunk-latest.png'
$pngSha=(Get-FileHash -Algorithm SHA256 'C:\Users\Public\venice-fleshpunk-latest.png').Hash.ToLowerInvariant()
$result=[ordered]@{
  schema='venice-fleshpunk-phone-receipt.v1'; ok=$true; prompt=[string]$req.prompt; seed=[int64]$req.seed;
  checkpoint=$checkpoint; lora=$lora; loraSha256=$loraSha; promptId=$promptId;
  remoteOutput='C:\Users\Public\venice-fleshpunk-latest.png'; pngSha256=$pngSha; generatedAt=(Get-Date).ToString('o')
}
$result | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 'C:\Users\Public\venice-fleshpunk-result.json'
$result | ConvertTo-Json -Compress -Depth 8
PS

scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$REQ" "$HOSTPORT:$REMOTE_REQ"
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$LOCAL_PS" "$HOSTPORT:$REMOTE_PS"
ssh -p "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT" \
  "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\Public\\venice-fleshpunk-generate.ps1" \
  | tee "$STATE/remote.stdout"

scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT:$REMOTE_RESULT" "$STATE/latest.json.part"
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT:$REMOTE_PNG" "$STATE/latest.png.part"
mv "$STATE/latest.json.part" "$STATE/latest.json"
mv "$STATE/latest.png.part" "$STATE/latest.png"

python - "$STATE/latest.json" "$STATE/latest.png" <<'PY'
import hashlib,json,sys
r=json.load(open(sys.argv[1],encoding='utf-8-sig'))
h=hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
if not r.get('ok') or h != r.get('pngSha256'):
    raise SystemExit(f"receipt mismatch remote={r.get('pngSha256')} local={h}")
r['phonePath']=sys.argv[2]; r['phoneSha256']=h
open(sys.argv[1],'w',encoding='utf-8').write(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(r,ensure_ascii=False))
PY
