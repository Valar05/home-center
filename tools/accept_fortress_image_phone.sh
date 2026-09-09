#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
ATOM="$HOME/.local/share/atom"
BIN="$HOME/bin"
PROMPT="${1:-educational anatomical study of a human hand, dorsal view, tendons and bones, neutral medical atlas composition, no labels}"
SEED="${2:-9092026}"
PROFILE="${3:-plain}"
OUT="$STATE/fortress-acceptance-latest.json"
mkdir -p "$STATE"

fail(){
  local code="$1" detail="$2"
  python - "$OUT" "$code" "$detail" <<'PY'
import datetime,json,sys
path,code,detail=sys.argv[1:]
obj={'schema':'fortress-image-phone-acceptance.v1','ok':False,'state':'blocked','code':code,'detail':detail,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2)+'\n')
print(json.dumps(obj))
PY
  exit 2
}

case "$PROFILE" in plain|fleshpunk) ;; *) fail PROFILE_INVALID "profile must be plain or fleshpunk";; esac
[ -d "$ATOM" ] || fail ATOM_NOT_INSTALLED "Atom runtime missing at $ATOM"
[ -x "$BIN/fortress-image" ] || fail IMAGE_COMMAND_MISSING "fortress-image command is not installed"
[ -x "$BIN/fortress-image-ui" ] || fail IMAGE_UI_MISSING "fortress-image-ui command is not installed"
[ -f "$ATOM/tools/venice_fleshpunk_phone.sh" ] || fail GENERATOR_MISSING "installed canonical generator source is missing"

if ! FORTRESS_IMAGE_PROFILE="$PROFILE" "$BIN/fortress-image" doctor >"$STATE/fortress-acceptance-doctor.stdout" 2>"$STATE/fortress-acceptance-doctor.stderr"; then
  detail="$(tail -c 3000 "$STATE/fortress-acceptance-doctor.stderr" 2>/dev/null || true)"
  fail DOCTOR_FAILED "$detail"
fi

rm -f "$STATE/latest.json" "$STATE/latest.png"
if ! FORTRESS_IMAGE_PROFILE="$PROFILE" "$BIN/fortress-image" generate "$PROMPT" "$SEED" >"$STATE/fortress-acceptance-generate.stdout" 2>"$STATE/fortress-acceptance-generate.stderr"; then
  detail="$(tail -c 5000 "$STATE/fortress-acceptance-generate.stderr" 2>/dev/null || true)"
  fail GENERATION_FAILED "$detail"
fi

[ -s "$STATE/latest.png" ] || fail PHONE_PNG_MISSING "generator returned no non-empty phone state PNG"
[ -s "$STATE/latest.json" ] || fail GENERATION_RECEIPT_MISSING "generator returned no generation receipt"

python - "$STATE/latest.json" "$STATE/latest.png" "$OUT" "$PROFILE" <<'PY'
import datetime,hashlib,json,os,sys
from pathlib import Path
receipt_path,phone_path,out_path,expected_profile=sys.argv[1:]
r=json.load(open(receipt_path,encoding='utf-8-sig'))
phone=Path(phone_path)
actual=hashlib.sha256(phone.read_bytes()).hexdigest()
public=Path(str(r.get('publicPhonePath') or ''))
errors=[]
if not r.get('ok'): errors.append('generation receipt ok=false')
if r.get('contract')!='fortress-image-phone.v1': errors.append(f"unexpected contract {r.get('contract')!r}")
if r.get('profile')!=expected_profile: errors.append(f"unexpected profile {r.get('profile')!r}")
if not r.get('promptId'): errors.append('missing ComfyUI promptId')
if not r.get('checkpoint'): errors.append('missing checkpoint')
if r.get('pngSha256')!=actual: errors.append('remote PNG SHA-256 does not match phone state bytes')
if r.get('phoneSha256')!=actual: errors.append('phone state SHA-256 does not match phone state bytes')
if not str(public).startswith('/storage/emulated/0/Pictures/Fortress/'):
    errors.append(f'public path is outside Pictures/Fortress: {public}')
if not public.is_file():
    errors.append(f'public PNG missing: {public}')
    public_hash=None
else:
    public_hash=hashlib.sha256(public.read_bytes()).hexdigest()
    if public_hash!=actual: errors.append('public Pictures PNG SHA-256 does not match returned phone bytes')
    if r.get('publicPhoneSha256')!=public_hash: errors.append('receipt publicPhoneSha256 does not match public bytes')
if expected_profile=='fleshpunk':
    if r.get('lora')!='drw_fleshpunk_v1.safetensors': errors.append(f"unexpected LoRA {r.get('lora')!r}")
    if not r.get('loraSha256'): errors.append('missing Fleshpunk LoRA SHA-256')
else:
    if r.get('lora') not in (None,''): errors.append('plain profile unexpectedly loaded a LoRA')
obj={
  'schema':'fortress-image-phone-acceptance.v1','ok':not errors,
  'state':'accepted_runtime_slice' if not errors else 'blocked','errors':errors,
  'capabilityState':{
    'implemented':True,'phoneInstalled':True,'cauldronSshCallable':True,
    'generationObserved':bool(r.get('promptId')),
    'phoneStateArtifactDelivered':r.get('phoneSha256')==actual,
    'publicPicturesArtifactDelivered':bool(public_hash and public_hash==actual),
    'drewPerceptualAccepted':False
  },
  'prompt':r.get('prompt'),'seed':r.get('seed'),'profile':r.get('profile'),
  'checkpoint':r.get('checkpoint'),'lora':r.get('lora'),'loraSha256':r.get('loraSha256'),
  'promptId':r.get('promptId'),'phonePath':str(phone),'publicPhonePath':str(public),
  'pngSha256':actual,'accessibleSummary':r.get('requestDerivedAltText'),
  'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()
}
open(out_path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(obj,ensure_ascii=False))
if errors: raise SystemExit(3)
PY

if command -v termux-notification >/dev/null 2>&1; then
  PUBLIC="$(python - "$STATE/latest.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding='utf-8')).get('publicPhonePath',''))
PY
)"
  termux-notification --id 6501 --title 'Improper image lane accepted' \
    --content 'THECAULDRON rendered it; identical verified PNG bytes reached Pictures/Fortress.' \
    --button1 'Open image' --button1-action "bash -l -c 'termux-open \"$PUBLIC\"'" >/dev/null 2>&1 || true
fi

cat "$OUT"
