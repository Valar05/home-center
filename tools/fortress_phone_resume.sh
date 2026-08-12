#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="$HOME/.local/state/home-center/fortress-resume"
mkdir -p "$STATE"
cd "$ROOT"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECEIPT="$STATE/$STAMP.json"
VENICE_RECEIPT="$STATE/$STAMP.venice.json"
BASE="${HC_FORTRESS_BASE:-HEAD~1}"
HEAD_REF="${HC_FORTRESS_HEAD:-HEAD}"
ACCEPTANCE="${HC_FORTRESS_ACCEPTANCE:-Recover Adam overlay on primary phone, establish Vlad Pixel Forge capability telemetry, and bootstrap the bounded phone-local MNN pixel-art experiment without GitHub CI or Godot runtime delivery.}"

write_receipt() {
  python3 - "$RECEIPT" "$@" <<'PY'
import json,sys,time
path=sys.argv[1]
obj={'schema':'fortress-phone-resume-v1','createdAtEpoch':int(time.time()),'argv':sys.argv[2:]}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
}

ensure_venice() {
  if python3 tools/venice_review.py --repo "$ROOT" --base "$BASE" --head "$HEAD_REF" --acceptance "$ACCEPTANCE" --receipt "$VENICE_RECEIPT"; then
    return 0
  fi

  if grep -q 'ollama_unavailable' "$VENICE_RECEIPT" 2>/dev/null || ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    if command -v ollama >/dev/null 2>&1; then
      (ollama serve >"$STATE/ollama.log" 2>&1 & echo $! >"$STATE/ollama.pid") || true
      sleep 2
    fi
  fi

  MODEL="${VENICE_REVIEW_MODEL:-qwen2.5-coder:1.5b}"
  if command -v ollama >/dev/null 2>&1 && ! ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$MODEL"; then
    ollama pull "$MODEL" || true
  fi

  python3 tools/venice_review.py --repo "$ROOT" --base "$BASE" --head "$HEAD_REF" --acceptance "$ACCEPTANCE" --receipt "$VENICE_RECEIPT"
}

# Canonical source first. No Actions/CI invocation.
git fetch origin main
git checkout main
git pull --ff-only origin main

bash tools/recover_adam_overlay_phone.sh
python3 tools/vlad_pixel_forge_probe.py | tee "$STATE/$STAMP.pixel-probe.json"

# Bootstrap only after the probe succeeds. The bootstrap itself enforces bounded storage/headroom.
bash tools/bootstrap_vlad_pixel_forge_mnn_phone.sh

# Venice decides whether this coding slice may stop. If she is unavailable, repair and retry.
ensure_venice

python3 - "$VENICE_RECEIPT" "$RECEIPT" <<'PY'
import json,sys,time
v=json.load(open(sys.argv[1],encoding='utf-8'))
obj={
  'schema':'fortress-phone-resume-v1',
  'ok': bool(v.get('externalReviewGateSatisfied')),
  'venice': v,
  'overlayReceipt': str(__import__('pathlib').Path.home()/'.local/state/home-center/adam-overlay-recovery.json'),
  'pixelProbe': 'recorded',
  'mnnBootstrap': 'attempted',
  'ciUsed': False,
  'godotRuntimeUsed': False,
  'completedAtEpoch': int(time.time()),
}
open(sys.argv[2],'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
if not obj['ok']:
  raise SystemExit(1)
PY
