#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="$HOME/.local/state/home-center/fortress-resume"
mkdir -p "$STATE"
cd "$ROOT"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECEIPT="$STATE/$STAMP.json"
EVIDENCE="$STATE/$STAMP.phone-evidence.json"
BASE="${HC_FORTRESS_BASE:-cf75f35f3a379f3612f6b8a560a53229c9c8417c}"
HEAD_REF="${HC_FORTRESS_HEAD:-HEAD}"
ACCEPTANCE="${HC_FORTRESS_ACCEPTANCE:-Recover Adam overlay on primary phone, establish Vlad Pixel Forge capability telemetry, bootstrap and exercise the bounded phone-local MNN pixel-art experiment, compact survivors into tiny canonical artifacts, and obtain Venice semantic PASS after applying her critique. GitHub CI is forbidden; Godot may be a forge but is not the delivery runtime.}"

# Never trample phone-side work while trying to recover the phone-side work system.
DIRTY="$(git status --porcelain)"
if [ -n "$DIRTY" ]; then
  printf 'BLOCKED: home-center working tree is dirty; preserve/reconcile it before Fortress resume.\n%s\n' "$DIRTY" >&2
  exit 30
fi

# Canonical source first. No Actions/CI invocation.
git fetch origin main
git checkout main
git pull --ff-only origin main
bash tools/run_fortress_local_contracts.sh

# Initial proof and every later post-repair proof use the exact same phone-native
# path, preventing stale generation receipts from entering Venice or final state.
bash tools/fortress_refresh_phone_evidence.sh "$EVIDENCE"

# Venice FAIL -> phone worker repair -> local tests -> durable push -> fresh phone
# proof -> Venice again. Default 0 means no arbitrary retry ceiling.
python3 tools/fortress_venice_loop.py \
  --base "$BASE" \
  --head "$HEAD_REF" \
  --acceptance "$ACCEPTANCE" \
  --evidence-file "$EVIDENCE" \
  --max-rounds "${HC_FORTRESS_VENICE_ROUNDS:-0}" \
  | tee "$STATE/$STAMP.venice-loop.json"

python3 - "$STATE/$STAMP.venice-loop.json" "$EVIDENCE" "$RECEIPT" <<'PY'
import hashlib,json,sys,time
loop_path,evidence_path,out_path=sys.argv[1:]
loop_raw=open(loop_path,'rb').read(); ev_raw=open(evidence_path,'rb').read()
loop=json.loads(loop_raw); ev=json.loads(ev_raw)
rounds=loop.get('rounds') or []
last=rounds[-1] if rounds else {}
venice=last.get('venice') or {}
obj={
  'schema':'fortress-phone-resume-v6',
  'ok': bool(loop.get('ok')) and bool(ev.get('ok')),
  'device':'primary-phone',
  'venice':{
    'passed': bool(venice.get('externalReviewGateSatisfied')),
    'verdict': venice.get('verdict'),
    'rounds': len(rounds),
    'lastReviewReceipt': last.get('receipt'),
    'loopSha256': hashlib.sha256(loop_raw).hexdigest(),
  },
  'phoneEvidence':{
    'ok': bool(ev.get('ok')),
    'evidenceSha256': ev.get('evidenceSha256'),
    'receiptSha256': hashlib.sha256(ev_raw).hexdigest(),
  },
  'ciUsed': False,
  'godotRuntimeUsed': False,
  'completedAtEpoch': int(time.time()),
}
text=json.dumps(obj,indent=2,sort_keys=True)+'\n'
if len(text.encode()) > 32768:
  raise SystemExit('compact acceptance receipt unexpectedly exceeds 32 KiB')
open(out_path,'w',encoding='utf-8').write(text)
print(text,end='')
if not obj['ok']:
  raise SystemExit(1)
PY

# Preserve a compact phone-produced acceptance pointer after Venice PASS. Full
# runtime/review receipts remain in phone state and are addressed by hashes.
DEST="artifacts/fortress/phone/$STAMP.json"
mkdir -p "$(dirname "$DEST")"
cp "$RECEIPT" "$DEST"
git add "$DEST"
git commit -m "Record Fortress phone acceptance $STAMP"
if ! git push origin HEAD:main; then
  git fetch origin main
  git rebase origin/main
  git push origin HEAD:main
fi
printf 'FORTRESS PHONE SLICE ACCEPTED receipt=%s durable=%s\n' "$RECEIPT" "$DEST"
