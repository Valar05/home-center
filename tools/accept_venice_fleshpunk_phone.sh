#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
ATOM="$HOME/.local/share/atom"
BIN="$HOME/bin"
PROMPT="${1:-a flesh-punk field mechanic in a rain-dark trench workshop, biomechanical tools, practical workwear, environmental composition}"
SEED="${2:-8132026}"
mkdir -p "$STATE"

fail(){
  local code="$1" detail="$2"
  python - "$STATE/acceptance-latest.json" "$code" "$detail" <<'PY'
import json,sys,datetime
path,code,detail=sys.argv[1:]
obj={
  'schema':'venice-fleshpunk-phone-acceptance.v1','ok':False,'state':'blocked',
  'code':code,'detail':detail,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2)+'\n')
print(json.dumps(obj))
PY
  exit 2
}

[ -d "$ATOM" ] || fail ATOM_NOT_INSTALLED "Atom runtime missing at $ATOM"
[ -x "$BIN/venice-image" ] || fail IMAGE_COMMAND_MISSING "venice-image command is not installed"
[ -x "$BIN/venice-image-ui" ] || fail IMAGE_UI_MISSING "venice-image-ui command is not installed"
[ -f "$ATOM/tools/venice_fleshpunk_phone.sh" ] || fail GENERATOR_MISSING "installed generator source is missing"
[ -f "$ATOM/tools/ssh_axis.py" ] || fail SSH_AXIS_MISSING "installed SSH Axis source is missing"

# Prove current workstation transport before starting the expensive render.
if ! python "$ATOM/tools/ssh_axis.py" check --target cauldron --json >"$STATE/acceptance-ssh.json"; then
  fail CAULDRON_SSH_UNCALLABLE "THECAULDRON failed the end-to-end SSH Axis canary"
fi

rm -f "$STATE/latest.json" "$STATE/latest.png"
if ! "$BIN/venice-image" generate "$PROMPT" "$SEED" >"$STATE/acceptance-generate.stdout" 2>"$STATE/acceptance-generate.stderr"; then
  detail="$(tail -c 3000 "$STATE/acceptance-generate.stderr" 2>/dev/null || true)"
  fail GENERATION_FAILED "$detail"
fi

[ -s "$STATE/latest.png" ] || fail PHONE_PNG_MISSING "generator returned no non-empty phone PNG"
[ -s "$STATE/latest.json" ] || fail GENERATION_RECEIPT_MISSING "generator returned no generation receipt"

python - "$STATE/latest.json" "$STATE/latest.png" "$STATE/acceptance-latest.json" <<'PY'
import hashlib,json,sys,datetime,os
receipt_path,png_path,out_path=sys.argv[1:]
r=json.load(open(receipt_path,encoding='utf-8-sig'))
actual=hashlib.sha256(open(png_path,'rb').read()).hexdigest()
errors=[]
if not r.get('ok'): errors.append('generation receipt ok=false')
if r.get('lora')!='drw_fleshpunk_v1.safetensors': errors.append(f"unexpected LoRA {r.get('lora')!r}")
if not r.get('loraSha256'): errors.append('missing LoRA SHA-256')
if not r.get('promptId'): errors.append('missing ComfyUI promptId')
if r.get('pngSha256')!=actual: errors.append('remote PNG SHA-256 does not match phone bytes')
if r.get('phoneSha256')!=actual: errors.append('phone receipt SHA-256 does not match phone bytes')
obj={
  'schema':'venice-fleshpunk-phone-acceptance.v1',
  'ok':not errors,
  'state':'accepted_runtime_slice' if not errors else 'blocked',
  'errors':errors,
  'capabilityState':{
    'implemented':True,
    'phoneInstalled':True,
    'cauldronSshCallable':True,
    'loraRuntimeObserved':bool(r.get('loraSha256')),
    'generationObserved':bool(r.get('promptId')),
    'phoneArtifactDelivered':r.get('pngSha256')==actual and r.get('phoneSha256')==actual,
    'drewPerceptualAccepted':False
  },
  'prompt':r.get('prompt'),
  'seed':r.get('seed'),
  'checkpoint':r.get('checkpoint'),
  'lora':r.get('lora'),
  'loraSha256':r.get('loraSha256'),
  'promptId':r.get('promptId'),
  'phonePath':os.path.abspath(png_path),
  'pngSha256':actual,
  'accessibleSummary':r.get('accessibleSummary'),
  'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()
}
open(out_path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(obj,ensure_ascii=False))
if errors: raise SystemExit(3)
PY

if command -v termux-notification >/dev/null 2>&1; then
  termux-notification --id 6501 --title 'Fleshpunk image accepted' \
    --content 'Runtime proof passed: THECAULDRON rendered with the Fleshpunk LoRA and the verified PNG returned to this phone.' \
    --button1 'Open image' --button1-action "bash -l -c 'termux-open $STATE/latest.png'" >/dev/null 2>&1 || true
fi

cat "$STATE/acceptance-latest.json"
