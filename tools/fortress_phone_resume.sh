#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="$HOME/.local/state/home-center/fortress-resume"
PIXEL_STATE="${HC_PIXEL_FORGE_STATE:-$HOME/.local/state/home-center/pixel-forge}"
mkdir -p "$STATE" "$PIXEL_STATE"
cd "$ROOT"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECEIPT="$STATE/$STAMP.json"
# Active Pixel Forge/overlay slice anchor. Override for a new commission.
BASE="${HC_FORTRESS_BASE:-cf75f35f3a379f3612f6b8a560a53229c9c8417c}"
HEAD_REF="${HC_FORTRESS_HEAD:-HEAD}"
ACCEPTANCE="${HC_FORTRESS_ACCEPTANCE:-Recover Adam overlay on primary phone, establish Vlad Pixel Forge capability telemetry, bootstrap and exercise the bounded phone-local MNN pixel-art experiment, compact survivors into tiny canonical artifacts, and obtain Venice semantic PASS after applying her critique. GitHub CI is forbidden; Godot may be a forge but is not the delivery runtime.}"
PROMPT="${HC_PIXEL_FORGE_SMOKE_PROMPT:-tiny one-screen fleshpunk farm creature, readable pixel-art silhouette, game sprite, no text}"
REQUEST="$PIXEL_STATE/smoke-request.json"

# Canonical source first. No Actions/CI invocation.
git fetch origin main
git checkout main
git pull --ff-only origin main

# The phone is the proof body.
bash tools/run_fortress_local_contracts.sh
bash tools/recover_adam_overlay_phone.sh
python3 tools/vlad_pixel_forge_probe.py | tee "$STATE/$STAMP.pixel-probe.json"
bash tools/bootstrap_vlad_pixel_forge_mnn_phone.sh
python3 tools/stage_vlad_pixel_model_phone.py | tee "$STATE/$STAMP.model-stage.log"
python3 tools/vlad_pixel_request.py "$PROMPT" --seed 42 --width 512 --height 512 --steps 4 --cfg 1.0 --out "$REQUEST"
python3 tools/vlad_pixel_generate_mnn_phone.py "$REQUEST" --canonical-size 32 --colors 16 | tee "$STATE/$STAMP.pixel-generate.json"

# Venice is not a report-at-the-end step. FAIL -> repair through the deterministic
# coding lane -> commit validated repair -> re-review.
python3 tools/fortress_venice_loop.py \
  --base "$BASE" \
  --head "$HEAD_REF" \
  --acceptance "$ACCEPTANCE" \
  --max-rounds "${HC_FORTRESS_VENICE_ROUNDS:-4}" \
  | tee "$STATE/$STAMP.venice-loop.json"

python3 - "$STATE/$STAMP.venice-loop.json" "$STATE/$STAMP.pixel-generate.json" "$RECEIPT" <<'PY'
import json,sys,time
loop=json.load(open(sys.argv[1],encoding='utf-8'))
gen=json.load(open(sys.argv[2],encoding='utf-8'))
obj={
  'schema':'fortress-phone-resume-v3',
  'ok': bool(loop.get('ok')) and bool(gen.get('ok')) and bool(gen.get('intermediateDeleted')),
  'veniceLoop': loop,
  'pixelGeneration': gen,
  'overlayReceipt': str(__import__('pathlib').Path.home()/'.local/state/home-center/adam-overlay-recovery.json'),
  'ciUsed': False,
  'godotRuntimeUsed': False,
  'completedAtEpoch': int(time.time()),
}
open(sys.argv[3],'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
if not obj['ok']:
  raise SystemExit(1)
PY
