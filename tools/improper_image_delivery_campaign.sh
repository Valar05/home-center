#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/improper-image-delivery"
mkdir -p "$STATE"

PROMPT="${1:-educational anatomical study of a human hand, dorsal view, tendons and bones, neutral medical atlas composition, no labels}"
SEED="${2:-9092026}"
PROFILE="${3:-plain}"

case "$PROFILE" in plain|fleshpunk) ;; *) echo 'PROFILE must be plain or fleshpunk' >&2; exit 64;; esac

printf '%s\n' 'IMPROPER_IMAGE_CAMPAIGN stage=install'
bash "$ROOT/tools/install_atom_phone.sh" | tee "$STATE/install.stdout"
printf '%s\n' 'IMPROPER_IMAGE_CAMPAIGN stage=accept'
"$HOME/bin/fortress-image-accept" "$PROMPT" "$SEED" "$PROFILE" | tee "$STATE/accept.stdout"
cp "${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image/fortress-acceptance-latest.json" "$STATE/acceptance-latest.json"
python - "$STATE/acceptance-latest.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
if not r.get('ok'):
    raise SystemExit('IMPROPER_IMAGE_CAMPAIGN BLOCKED: acceptance receipt ok=false')
print('IMPROPER_IMAGE_CAMPAIGN ACCEPTED')
print('profile='+str(r.get('profile')))
print('promptId='+str(r.get('promptId')))
print('publicPhonePath='+str(r.get('publicPhonePath')))
print('pngSha256='+str(r.get('pngSha256')))
PY
