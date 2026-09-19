#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
PUBLIC_DIR="${FORTRESS_IMAGE_PUBLIC_DIR:-/storage/emulated/0/Pictures/Fortress}"
REMOTE_RUNTIME_LOCAL="$ROOT/tools/fortress_image_cauldron.ps1"
mkdir -p "$STATE"

usage(){
  cat <<'EOF'
usage: venice_fleshpunk_phone.sh generate "PROMPT" [SEED]
       venice_fleshpunk_phone.sh setup
       venice_fleshpunk_phone.sh models
       venice_fleshpunk_phone.sh doctor
       venice_fleshpunk_phone.sh status
       venice_fleshpunk_phone.sh receipts

Canonical phone -> THECAULDRON image transport. The higher-level
fortress-image CLI compiles named presets into these environment variables.

Environment:
  FORTRESS_IMAGE_PROFILE=plain|fleshpunk|<compiled preset>
  FORTRESS_IMAGE_CHECKPOINT=<checkpoint basename>
  FORTRESS_IMAGE_LORAS_JSON=[{"filename":"x.safetensors","model":0.5,"clip":0.5}]
  FORTRESS_IMAGE_POSITIVE_PREFIX=<text>
  FORTRESS_IMAGE_NEGATIVE=<text>
  FORTRESS_IMAGE_STEPS=28
  FORTRESS_IMAGE_CFG=7.0
  FORTRESS_IMAGE_SAMPLER=dpmpp_2m
  FORTRESS_IMAGE_SCHEDULER=karras
  FORTRESS_IMAGE_WIDTH=512
  FORTRESS_IMAGE_HEIGHT=768
  FORTRESS_IMAGE_MODE=single|sheet
  FORTRESS_IMAGE_COUNT=1..12
  FORTRESS_IMAGE_CONTACT_COLS=1..6
  FORTRESS_IMAGE_MANAGED_ASSETS_JSON=[...]

ComfyUI remains localhost-only on THECAULDRON. Successful PNG bytes are
SHA-256 verified after return to the phone, atomically published to
/storage/emulated/0/Pictures/Fortress, and recorded in the receipt.
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

check_uint(){
  local name="$1" value="$2" lo="$3" hi="$4"
  case "$value" in (*[!0-9]*|'') echo "$name must be an integer" >&2; exit 64;; esac
  if [ "$value" -lt "$lo" ] || [ "$value" -gt "$hi" ]; then
    echo "$name must be $lo..$hi" >&2
    exit 64
  fi
}

ACTION="${1:-}"
case "$ACTION" in
  status)
    python "$ROOT/tools/ssh_axis.py" check --target cauldron --json
    exit $?
    ;;
  receipts)
    [ -f "$STATE/latest.json" ] && cat "$STATE/latest.json" || { echo '{}'; exit 2; }
    exit 0
    ;;
  generate|setup|models|doctor) ;;
  *) usage >&2; exit 64 ;;
esac

[ -f "$REMOTE_RUNTIME_LOCAL" ] || {
  echo "BLOCKED: versioned THECAULDRON image runtime missing: $REMOTE_RUNTIME_LOCAL" >&2
  exit 2
}

PROFILE="${FORTRESS_IMAGE_PROFILE:-fleshpunk}"
CHECKPOINT="${FORTRESS_IMAGE_CHECKPOINT:-}"
LORAS_JSON="${FORTRESS_IMAGE_LORAS_JSON:-}"
POSITIVE_PREFIX="${FORTRESS_IMAGE_POSITIVE_PREFIX:-}"
NEGATIVE="${FORTRESS_IMAGE_NEGATIVE:-low quality, blurry, malformed anatomy, malformed hands, extra fingers, missing fingers, watermark, signature, unwanted text, jpeg artifacts}"
STEPS="${FORTRESS_IMAGE_STEPS:-28}"
CFG="${FORTRESS_IMAGE_CFG:-7.0}"
SAMPLER="${FORTRESS_IMAGE_SAMPLER:-euler_ancestral}"
SCHEDULER="${FORTRESS_IMAGE_SCHEDULER:-normal}"
WIDTH="${FORTRESS_IMAGE_WIDTH:-512}"
HEIGHT="${FORTRESS_IMAGE_HEIGHT:-768}"
MODE="${FORTRESS_IMAGE_MODE:-single}"
COUNT="${FORTRESS_IMAGE_COUNT:-1}"
COLS="${FORTRESS_IMAGE_CONTACT_COLS:-1}"
MANAGED_ASSETS_JSON="${FORTRESS_IMAGE_MANAGED_ASSETS_JSON:-[]}"

if [ -z "$CHECKPOINT" ]; then
  case "$PROFILE" in
    plain)
      CHECKPOINT='v1-5-pruned-emaonly.safetensors'
      [ -n "$LORAS_JSON" ] || LORAS_JSON='[]'
      ;;
    fleshpunk)
      CHECKPOINT='v1-5-pruned-emaonly.safetensors'
      [ -n "$LORAS_JSON" ] || LORAS_JSON='[{"filename":"drw_fleshpunk_v1.safetensors","model":0.85,"clip":0.85}]'
      ;;
    all)
      [ "$ACTION" = setup ] || { echo "BLOCKED: profile=all is setup-only" >&2; exit 64; }
      [ -n "$LORAS_JSON" ] || LORAS_JSON='[]'
      ;;
    *)
      echo "BLOCKED: compiled preset $PROFILE did not provide FORTRESS_IMAGE_CHECKPOINT" >&2
      exit 64
      ;;
  esac
fi
[ -n "$LORAS_JSON" ] || LORAS_JSON='[]'

if [ "$ACTION" = generate ]; then
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
  check_dimension FORTRESS_IMAGE_WIDTH "$WIDTH"
  check_dimension FORTRESS_IMAGE_HEIGHT "$HEIGHT"
  check_uint FORTRESS_IMAGE_STEPS "$STEPS" 1 80
  check_uint FORTRESS_IMAGE_COUNT "$COUNT" 1 12
  check_uint FORTRESS_IMAGE_CONTACT_COLS "$COLS" 1 6
  case "$MODE" in single|sheet) ;; *) echo 'FORTRESS_IMAGE_MODE must be single or sheet' >&2; exit 64;; esac
  if [ "$MODE" = single ] && [ "$COUNT" -ne 1 ]; then
    echo 'single mode requires FORTRESS_IMAGE_COUNT=1' >&2
    exit 64
  fi
  if [ "$COLS" -gt "$COUNT" ]; then
    echo 'FORTRESS_IMAGE_CONTACT_COLS cannot exceed FORTRESS_IMAGE_COUNT' >&2
    exit 64
  fi
  mkdir -p "$PUBLIC_DIR"
  [ -w "$PUBLIC_DIR" ] || {
    echo "BLOCKED: public image directory is not writable: $PUBLIC_DIR" >&2
    exit 42
  }
else
  PROMPT=''
  SEED=0
fi

if ! python "$ROOT/tools/ssh_axis.py" check --target cauldron --json >"$STATE/ssh-axis.json"; then
  [ -f "$ROOT/tools/resolve_cauldron_ssh.py" ] || {
    cat "$STATE/ssh-axis.json" >&2
    echo 'BLOCKED: THECAULDRON SSH Axis is not callable and resolver is unavailable.' >&2
    exit 41
  }
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
if [[ "$HOSTPORT" =~ ^(.+):([0-9]+)$ ]]; then
  HOSTPORT="${BASH_REMATCH[1]}"
  PORT="${BASH_REMATCH[2]}"
fi

REQ="$STATE/request.json"
RUNTIME_SHA="$(sha256sum "$REMOTE_RUNTIME_LOCAL" | awk '{print $1}')"
ACTION="$ACTION" PROFILE="$PROFILE" CHECKPOINT="$CHECKPOINT" LORAS_JSON="$LORAS_JSON" POSITIVE_PREFIX="$POSITIVE_PREFIX" NEGATIVE="$NEGATIVE" STEPS="$STEPS" CFG="$CFG" SAMPLER="$SAMPLER" SCHEDULER="$SCHEDULER" WIDTH="$WIDTH" HEIGHT="$HEIGHT" MODE="$MODE" COUNT="$COUNT" COLS="$COLS" MANAGED_ASSETS_JSON="$MANAGED_ASSETS_JSON" PROMPT="$PROMPT" SEED="$SEED" RUNTIME_SHA="$RUNTIME_SHA" python - >"$REQ" <<'PY'
import json, os

def load_json(name):
    try:
        value=json.loads(os.environ[name])
    except Exception as exc:
        raise SystemExit(f"BLOCKED: invalid {name}: {exc}")
    return value

action=os.environ["ACTION"]
obj={
    "schema":"fortress-image-cauldron-request.v2",
    "action":action,
    "profile":os.environ["PROFILE"],
    "checkpoint":os.environ["CHECKPOINT"],
    "loras":load_json("LORAS_JSON"),
    "managedAssets":load_json("MANAGED_ASSETS_JSON"),
    "runtimeSha256":os.environ["RUNTIME_SHA"],
}
if action=="generate":
    obj.update({
        "prompt":os.environ["PROMPT"],
        "seed":int(os.environ["SEED"]),
        "positivePrefix":os.environ["POSITIVE_PREFIX"],
        "negative":os.environ["NEGATIVE"],
        "steps":int(os.environ["STEPS"]),
        "cfg":float(os.environ["CFG"]),
        "sampler":os.environ["SAMPLER"],
        "scheduler":os.environ["SCHEDULER"],
        "width":int(os.environ["WIDTH"]),
        "height":int(os.environ["HEIGHT"]),
        "mode":os.environ["MODE"],
        "count":int(os.environ["COUNT"]),
        "cols":int(os.environ["COLS"]),
    })
print(json.dumps(obj,ensure_ascii=False))
PY

REMOTE_REQ='C:/Users/Public/fortress-image-request.json'
REMOTE_PS='C:/Users/Public/fortress-image-cauldron.ps1'
REMOTE_RESULT='C:/Users/Public/fortress-image-result.json'
REMOTE_PNG='C:/Users/Public/fortress-image-latest.png'

scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$REQ" "$HOSTPORT:$REMOTE_REQ"
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$REMOTE_RUNTIME_LOCAL" "$HOSTPORT:$REMOTE_PS"

set +e
ssh -p "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT"   "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\\Users\\Public\\fortress-image-cauldron.ps1"   | tee "$STATE/remote.stdout"
REMOTE_RC=${PIPESTATUS[0]}
set -e

if scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new     "$HOSTPORT:$REMOTE_RESULT" "$STATE/control-latest.json.part" 2>"$STATE/result-scp.err"; then
  mv "$STATE/control-latest.json.part" "$STATE/control-latest.json"
fi

if [ "$REMOTE_RC" -ne 0 ]; then
  [ ! -f "$STATE/control-latest.json" ] || cat "$STATE/control-latest.json" >&2
  exit "$REMOTE_RC"
fi

if [ "$ACTION" != generate ]; then
  [ -f "$STATE/control-latest.json" ] || {
    cat "$STATE/result-scp.err" >&2 || true
    echo 'BLOCKED: THECAULDRON returned no control receipt.' >&2
    exit 43
  }
  cat "$STATE/control-latest.json"
  exit 0
fi

scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new   "$HOSTPORT:$REMOTE_RESULT" "$STATE/latest.json.part"
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new   "$HOSTPORT:$REMOTE_PNG" "$STATE/latest.png.part"
mv "$STATE/latest.json.part" "$STATE/latest.json"
mv "$STATE/latest.png.part" "$STATE/latest.png"

python - "$STATE/latest.json" "$STATE/latest.png" "$PUBLIC_DIR" "$RUNTIME_SHA" <<'PY'
import hashlib,json,os,sys
from pathlib import Path

receipt_path=Path(sys.argv[1])
phone_path=Path(sys.argv[2])
public_root=Path(sys.argv[3])
runtime_sha=sys.argv[4]
r=json.load(open(receipt_path,encoding='utf-8-sig'))
data=phone_path.read_bytes()
h=hashlib.sha256(data).hexdigest()
if not r.get('ok') or h != r.get('pngSha256'):
    raise SystemExit(f"receipt mismatch remote={r.get('pngSha256')} local={h}")
public_root.mkdir(parents=True,exist_ok=True)
prompt_id=''.join(c for c in str(r.get('promptId') or 'latest') if c.isalnum() or c in '-_') or 'latest'
preset=''.join(c for c in str(r.get('profile') or 'image') if c.isalnum() or c in '-_') or 'image'
public_path=public_root/(preset+'-'+prompt_id+'.png')
temp=public_path.with_name(public_path.name+'.part')
temp.write_bytes(data)
if hashlib.sha256(temp.read_bytes()).hexdigest()!=h:
    raise SystemExit('public image temporary readback mismatch')
os.replace(temp,public_path)
public_hash=hashlib.sha256(public_path.read_bytes()).hexdigest()
if public_hash!=h:
    raise SystemExit('public image final readback mismatch')
r['phonePath']=str(phone_path)
r['phoneSha256']=h
r['publicPhonePath']=str(public_path)
r['publicPhoneSha256']=public_hash
r['remoteRuntimeSha256']=runtime_sha
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
