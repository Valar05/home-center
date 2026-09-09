#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
PUBLIC_DIR="${FORTRESS_IMAGE_PUBLIC_DIR:-/storage/emulated/0/Pictures/Fortress}"
mkdir -p "$STATE"

usage(){
  cat <<'EOF'
usage: venice_fleshpunk_phone.sh generate "PROMPT" [SEED]
       venice_fleshpunk_phone.sh status
       venice_fleshpunk_phone.sh doctor
       venice_fleshpunk_phone.sh receipts

Canonical phone -> THECAULDRON image transport.
Environment:
  FORTRESS_IMAGE_PROFILE=fleshpunk|plain   (default: fleshpunk for compatibility)
  FORTRESS_IMAGE_WIDTH=512                 (128..1024, multiple of 64)
  FORTRESS_IMAGE_HEIGHT=768                (128..1024, multiple of 64)
  FORTRESS_IMAGE_PUBLIC_DIR=/storage/emulated/0/Pictures/Fortress

The renderer remains THECAULDRON's localhost-only ComfyUI. Successful PNG bytes
are SHA-256 verified after return to the phone, atomically published to the
public Pictures directory, and recorded in the receipt.
EOF
}

check_dimension(){
  local name="$1" value="$2"
  case "$value" in (*[!0-9]*|'') echo "$name must be an integer" >&2; exit 64;; esac
  if [ "$value" -lt 128 ] || [ "$value" -gt 1024 ] || [ $((value % 64)) -ne 0 ]; then
    echo "$name must be 128..1024 and a multiple of 64" >&2
    exit 64
  fi
}

case "${1:-}" in
  status)
    python "$ROOT/tools/ssh_axis.py" check --target cauldron --json
    exit $?
    ;;
  doctor)
    PROFILE="${FORTRESS_IMAGE_PROFILE:-fleshpunk}"
    case "$PROFILE" in fleshpunk|plain) ;; *) echo "unsupported FORTRESS_IMAGE_PROFILE=$PROFILE" >&2; exit 64;; esac
    WIDTH="${FORTRESS_IMAGE_WIDTH:-512}"; HEIGHT="${FORTRESS_IMAGE_HEIGHT:-768}"
    check_dimension FORTRESS_IMAGE_WIDTH "$WIDTH"; check_dimension FORTRESS_IMAGE_HEIGHT "$HEIGHT"
    mkdir -p "$PUBLIC_DIR"
    [ -w "$PUBLIC_DIR" ] || { echo "BLOCKED: public image directory is not writable: $PUBLIC_DIR" >&2; exit 42; }
    python "$ROOT/tools/ssh_axis.py" check --target cauldron --json >"$STATE/ssh-axis.json"
    python - "$PROFILE" "$WIDTH" "$HEIGHT" "$PUBLIC_DIR" <<'PY'
import json,sys
print(json.dumps({
  'schema':'fortress-image-phone-doctor.v1','ok':True,'profile':sys.argv[1],
  'width':int(sys.argv[2]),'height':int(sys.argv[3]),'publicDir':sys.argv[4],
  'transport':'ssh_axis:cauldron','renderer':'comfyui-loopback'
},sort_keys=True))
PY
    exit 0
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
PROFILE="${FORTRESS_IMAGE_PROFILE:-fleshpunk}"
case "$PROFILE" in fleshpunk|plain) ;; *) echo "unsupported FORTRESS_IMAGE_PROFILE=$PROFILE" >&2; exit 64;; esac
WIDTH="${FORTRESS_IMAGE_WIDTH:-512}"; HEIGHT="${FORTRESS_IMAGE_HEIGHT:-768}"
check_dimension FORTRESS_IMAGE_WIDTH "$WIDTH"; check_dimension FORTRESS_IMAGE_HEIGHT "$HEIGHT"
mkdir -p "$PUBLIC_DIR"
[ -w "$PUBLIC_DIR" ] || { echo "BLOCKED: public image directory is not writable: $PUBLIC_DIR" >&2; exit 42; }

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
python - "$PROMPT" "$SEED" "$PROFILE" "$WIDTH" "$HEIGHT" >"$REQ" <<'PY'
import json,sys
print(json.dumps({
  'prompt':sys.argv[1], 'seed':int(sys.argv[2]), 'profile':sys.argv[3],
  'width':int(sys.argv[4]), 'height':int(sys.argv[5])
}, ensure_ascii=False))
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
$profile = [string]$req.profile
$width = [int]$req.width
$height = [int]$req.height
$lora = $null
$loraSha = $null
try { $null = Invoke-RestMethod -TimeoutSec 5 "$comfy/system_stats" } catch { throw "ComfyUI unavailable on 127.0.0.1:8188: $($_.Exception.Message)" }

$workflow = @{
  '1'=@{class_type='CheckpointLoaderSimple';inputs=@{ckpt_name=$checkpoint}}
}
$modelRef=@('1',0)
$clipRef=@('1',1)
if ($profile -eq 'fleshpunk') {
  $lora = 'drw_fleshpunk_v1.safetensors'
  $loraPath = Join-Path $env:LOCALAPPDATA "VeniceImageBridge\ComfyUI\models\loras\$lora"
  if (-not (Test-Path $loraPath)) { throw "Fleshpunk LoRA missing: $loraPath" }
  $loraSha = (Get-FileHash -Algorithm SHA256 $loraPath).Hash.ToLowerInvariant()
  $workflow['2']=@{class_type='LoraLoader';inputs=@{model=@('1',0);clip=@('1',1);lora_name=$lora;strength_model=0.85;strength_clip=0.85}}
  $modelRef=@('2',0)
  $clipRef=@('2',1)
} elseif ($profile -ne 'plain') {
  throw "Unsupported image profile: $profile"
}
$workflow['3']=@{class_type='CLIPTextEncode';inputs=@{text=[string]$req.prompt;clip=$clipRef}}
$workflow['4']=@{class_type='CLIPTextEncode';inputs=@{text='low quality, blurry, malformed anatomy, watermark, unwanted text';clip=$clipRef}}
$workflow['5']=@{class_type='EmptyLatentImage';inputs=@{width=$width;height=$height;batch_size=1}}
$workflow['6']=@{class_type='KSampler';inputs=@{model=$modelRef;seed=[int64]$req.seed;steps=28;cfg=7.0;sampler_name='euler_ancestral';scheduler='normal';positive=@('3',0);negative=@('4',0);latent_image=@('5',0);denoise=1.0}}
$workflow['7']=@{class_type='VAEDecode';inputs=@{samples=@('6',0);vae=@('1',2)}}
$workflow['8']=@{class_type='SaveImage';inputs=@{filename_prefix='Fortress_Image_Phone';images=@('7',0)}}
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
$loraPhrase = if ($lora) { " with LoRA $lora" } else { '' }
$spokenSummary = "Generated local image for requested scene: $([string]$req.prompt). Seed $([int64]$req.seed). Profile $profile, model $checkpoint$loraPhrase. This summary describes the request and generation settings, not an independent visual inspection of the rendered pixels."
$result=[ordered]@{
  schema='venice-fleshpunk-phone-receipt.v1'; contract='fortress-image-phone.v1'; ok=$true;
  prompt=[string]$req.prompt; seed=[int64]$req.seed; profile=$profile; width=$width; height=$height;
  checkpoint=$checkpoint; lora=$lora; loraSha256=$loraSha; promptId=$promptId;
  requestDerivedAltText=$spokenSummary; altTextProvenance='request_and_generation_settings_not_visual_inspection';
  remoteOutput='C:\Users\Public\venice-fleshpunk-latest.png'; pngSha256=$pngSha; generatedAt=(Get-Date).ToString('o')
}
$result | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 'C:\Users\Public\venice-fleshpunk-result.json'
$result | ConvertTo-Json -Compress -Depth 8
PS

scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$REQ" "$HOSTPORT:$REMOTE_REQ"
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$LOCAL_PS" "$HOSTPORT:$REMOTE_PS"
ssh -p "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT" \
  "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\\Users\\Public\\venice-fleshpunk-generate.ps1" \
  | tee "$STATE/remote.stdout"

scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT:$REMOTE_RESULT" "$STATE/latest.json.part"
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT:$REMOTE_PNG" "$STATE/latest.png.part"
mv "$STATE/latest.json.part" "$STATE/latest.json"
mv "$STATE/latest.png.part" "$STATE/latest.png"

python - "$STATE/latest.json" "$STATE/latest.png" "$PUBLIC_DIR" <<'PY'
import hashlib,json,os,shutil,sys
from pathlib import Path
receipt_path=Path(sys.argv[1]); phone_path=Path(sys.argv[2]); public_root=Path(sys.argv[3])
r=json.load(open(receipt_path,encoding='utf-8-sig'))
data=phone_path.read_bytes(); h=hashlib.sha256(data).hexdigest()
if not r.get('ok') or h != r.get('pngSha256'):
    raise SystemExit(f"receipt mismatch remote={r.get('pngSha256')} local={h}")
public_root.mkdir(parents=True,exist_ok=True)
prompt_id=''.join(c for c in str(r.get('promptId') or 'latest') if c.isalnum() or c in '-_') or 'latest'
public_path=public_root/(prompt_id+'.png')
temp=public_path.with_name(public_path.name+'.part')
temp.write_bytes(data)
if hashlib.sha256(temp.read_bytes()).hexdigest()!=h:
    raise SystemExit('public image temporary readback mismatch')
os.replace(temp,public_path)
public_hash=hashlib.sha256(public_path.read_bytes()).hexdigest()
if public_hash!=h:
    raise SystemExit('public image final readback mismatch')
r['phonePath']=str(phone_path); r['phoneSha256']=h
r['publicPhonePath']=str(public_path); r['publicPhoneSha256']=public_hash
receipt_path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(r.get('requestDerivedAltText',''))
print(json.dumps(r,ensure_ascii=False))
PY

PUBLIC_PATH="$(python - "$STATE/latest.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding='utf-8')).get('publicPhonePath',''))
PY
)"
if [ -n "$PUBLIC_PATH" ] && command -v termux-media-scan >/dev/null 2>&1; then
  termux-media-scan "$PUBLIC_PATH" >/dev/null 2>&1 || true
fi
