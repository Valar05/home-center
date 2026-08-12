#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="$HOME/.local/state/home-center/fortress-resume"
PIXEL_STATE="${HC_PIXEL_FORGE_STATE:-$HOME/.local/state/home-center/pixel-forge}"
OUT="${1:?usage: fortress_refresh_phone_evidence.sh OUTPUT_JSON}"
STAMP="$(date +%Y%m%d-%H%M%S)"
PROMPT="${HC_PIXEL_FORGE_SMOKE_PROMPT:-tiny one-screen fleshpunk farm creature, readable pixel-art silhouette, game sprite, no text}"
REQUEST="$PIXEL_STATE/smoke-request.json"
OVERLAY_RECEIPT="$HOME/.local/state/home-center/adam-overlay-recovery.json"
MNN_RECEIPT="$PIXEL_STATE/mnn-bootstrap.json"
MODEL_RECEIPT="$PIXEL_STATE/model-stage.json"
mkdir -p "$STATE" "$PIXEL_STATE" "$(dirname "$OUT")"
cd "$ROOT"

# This script is intentionally idempotent and phone-native. It may be rerun after
# every Venice repair so semantic approval never rests on stale runtime evidence.
bash tools/recover_adam_overlay_phone.sh
python3 tools/vlad_pixel_forge_probe.py | tee "$STATE/$STAMP.pixel-probe.json"
bash tools/bootstrap_vlad_pixel_forge_mnn_phone.sh
python3 tools/stage_vlad_pixel_model_phone.py | tee "$STATE/$STAMP.model-stage.stdout.json"
python3 tools/vlad_pixel_request.py "$PROMPT" --seed 42 --width 512 --height 512 --steps 4 --cfg 1.0 --out "$REQUEST"
python3 tools/vlad_pixel_generate_mnn_phone.py "$REQUEST" --canonical-size 32 --colors 16 | tee "$STATE/$STAMP.pixel-generate.json"
python3 tools/fortress_collect_phone_evidence.py \
  --overlay "$OVERLAY_RECEIPT" \
  --probe "$STATE/$STAMP.pixel-probe.json" \
  --mnn "$MNN_RECEIPT" \
  --model "$MODEL_RECEIPT" \
  --generation "$STATE/$STAMP.pixel-generate.json" \
  --out "$OUT"
printf 'FORTRESS PHONE EVIDENCE REFRESHED %s\n' "$OUT"
