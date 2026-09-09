#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/improper-image-delivery"
mkdir -p "$STATE"

PROMPT="${1:-educational anatomical study of a human hand, dorsal view, tendons and bones, neutral medical atlas composition, no labels}"
SEED="${2:-9092026}"
PROFILE="${3:-plain}"

case "$PROFILE" in plain|fleshpunk) ;; *) echo 'PROFILE must be plain or fleshpunk' >&2; exit 64;; esac

printf '%s\n' 'IMPROPER_IMAGE_CAMPAIGN stage=install-standalone-runtime'
bash "$ROOT/tools/install_fortress_image_phone.sh" >"$STATE/install.stdout" 2>"$STATE/install.stderr" || {
  rc=$?
  tail -c 5000 "$STATE/install.stderr" >&2 || true
  exit "$rc"
}

printf '%s\n' 'IMPROPER_IMAGE_CAMPAIGN stage=accept-runtime'
"$HOME/bin/fortress-image-accept" "$PROMPT" "$SEED" "$PROFILE" >"$STATE/accept.stdout" 2>"$STATE/accept.stderr" || {
  rc=$?
  tail -c 7000 "$STATE/accept.stderr" >&2 || true
  [ ! -f "${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image/fortress-acceptance-latest.json" ] || \
    cat "${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image/fortress-acceptance-latest.json" >&2
  exit "$rc"
}

cp "${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image/fortress-acceptance-latest.json" "$STATE/acceptance-latest.json"
python - "$STATE/acceptance-latest.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
if not r.get('ok'):
    raise SystemExit('IMPROPER_IMAGE_CAMPAIGN BLOCKED: acceptance receipt ok=false')
cap=r.get('capabilityState') or {}
if cap.get('shizukuRequired') is not False:
    raise SystemExit('IMPROPER_IMAGE_CAMPAIGN BLOCKED: receipt did not prove Shizuku independence')
if not cap.get('publicPicturesArtifactDelivered'):
    raise SystemExit('IMPROPER_IMAGE_CAMPAIGN BLOCKED: public Pictures delivery not proven')
print('IMPROPER_IMAGE_CAMPAIGN ACCEPTED')
print(json.dumps(r,ensure_ascii=False,sort_keys=True))
PY
