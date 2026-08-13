#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
BIN_DIR="${HC_ADAM_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
TARGET="$BIN_DIR/adam"
VLAD_TARGET="$BIN_DIR/vlad"
ROUTER="$ROOT/tools/adam.py"
WORKER="$ROOT/tools/adam_planned_venice_receipted.py"
CORE_WORKER="$ROOT/tools/adam_planned_venice.py"
JAR_RUNTIME="$ROOT/tools/judgement_jar_runtime.py"
VLAD_CLI="$ROOT/tools/vlad_jars.py"
RECEIPT="$STATE/adam-cli-install-receipt.json"
ACCEPT_RECEIPT="$STATE/adam-phone-worker-acceptance.json"
BRAIN_RECEIPT="$STATE/adam-phone-brain-receipt.json"
JAR_RECEIPT="$STATE/judgement-jar-install-canary.json"

mkdir -p "$STATE" "$BIN_DIR"
for f in \
  "$ROUTER" \
  "$WORKER" \
  "$CORE_WORKER" \
  "$JAR_RUNTIME" \
  "$VLAD_CLI" \
  "$ROOT/config/judgement-jar-runtime.v1.json" \
  "$ROOT/tools/adam_venice_reviewed.py" \
  "$ROOT/tools/adam_codex_phone.py" \
  "$ROOT/tools/venice_plan_review.py" \
  "$ROOT/tools/venice_review.py" \
  "$ROOT/tools/venice_review_receipted.py" \
  "$ROOT/tools/venice_review_memory.py" \
  "$ROOT/AGENTS.md" "$ROOT/MEMORIES.md" "$ROOT/SKILLS.md"; do
  [ -f "$f" ] || { echo "BLOCKED: Adam/Codex/Venice/Jar component missing: $f" >&2; exit 2; }
done
PYTHON_BIN="$(command -v python3 || true)"
[ -n "$PYTHON_BIN" ] || { echo 'BLOCKED: python3 missing.' >&2; exit 3; }

cd "$ROOT"
python3 tools/test_judgement_jar_runtime.py
python3 tools/test_adam_jar_receipt_contract.py
python3 tools/test_adam_overlay_contract.py
python3 tools/test_adam_overlay_delivery_state.py
python3 tools/test_adam_cli_contract.py
python3 tools/test_adam_codex_phone.py
python3 tools/test_adam_venice_review_gate.py
python3 tools/test_venice_plan_review.py
python3 tools/test_venice_review_memory.py
node --test atom/test/judgement-jars.test.mjs
node --test tools/fortress_online_v2_boot.test.mjs
python3 -m py_compile \
  tools/adam.py \
  tools/adam_codex_phone.py \
  tools/adam_venice_reviewed.py \
  tools/adam_planned_venice.py \
  tools/adam_planned_venice_receipted.py \
  tools/judgement_jar_runtime.py \
  tools/vlad_jars.py \
  tools/venice_plan_review.py \
  tools/venice_review.py \
  tools/venice_review_receipted.py \
  tools/venice_review_memory.py \
  tools/accept_adam_executive_phone.py \
  tools/vlad_swarm_daemon.py

TMP_TARGET="$TARGET.tmp.$$"
cat > "$TMP_TARGET" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
case "\${1:-}" in
  terminal|chat|continue|vlad)
    exec "$PYTHON_BIN" "$ROUTER" "\$@"
    ;;
  *)
    exec "$PYTHON_BIN" "$WORKER" "\$@"
    ;;
esac
EOF
chmod 755 "$TMP_TARGET"
mv -f "$TMP_TARGET" "$TARGET"

TMP_VLAD="$VLAD_TARGET.tmp.$$"
cat > "$TMP_VLAD" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec "$PYTHON_BIN" "$VLAD_CLI" "\$@"
EOF
chmod 755 "$TMP_VLAD"
mv -f "$TMP_VLAD" "$VLAD_TARGET"
hash -r 2>/dev/null || true

CANARY="$($TARGET terminal 'printf ADAM_BODY_OK' --cwd "$ROOT" --timeout 10)"
printf '%s\n' "$CANARY" | grep -q 'ADAM_BODY_OK' || { echo 'BLOCKED: Adam body transport canary failed.' >&2; exit 4; }

"$VLAD_TARGET" jars list --json > "$JAR_RECEIPT"
python3 - "$JAR_RECEIPT" <<'PY'
import json,sys
obj=json.load(open(sys.argv[1],encoding='utf-8'))
assert obj.get('ok') is True, obj
assert obj.get('count') == 8, obj
assert len(obj.get('jars') or []) == 8, obj
assert all(j.get('path','').startswith('.continue/rules/') for j in obj['jars']), obj
print(json.dumps({'ok':True,'jarCount':8,'catalogSync':obj.get('catalogSync',{}).get('state')},sort_keys=True))
PY

bash tools/ensure_adam_phone_brain.sh | tee "$BRAIN_RECEIPT"
grep -q '"ok":true' "$BRAIN_RECEIPT" || { echo 'BLOCKED: Adam phone model did not become healthy.' >&2; exit 5; }

python3 tools/accept_adam_executive_phone.py | tee "$ACCEPT_RECEIPT"
grep -q '"ok": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam planned/Venice-reviewed Codex worker acceptance failed.' >&2; exit 6; }
grep -q '"venicePlanReviewReceiptVerified": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam pre-execution Venice plan receipt not verified.' >&2; exit 7; }
grep -q '"veniceStopReviewReceiptVerified": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam completion Venice receipt not verified.' >&2; exit 8; }

SOURCE_SHA="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
fi
WORKER_SHA="$(sha256sum "$WORKER" | awk '{print $1}')"

python3 - "$RECEIPT" "$SOURCE_SHA" "$WORKER_SHA" "$TARGET" "$VLAD_TARGET" "$WORKER" "$CANARY" "$ACCEPT_RECEIPT" "$BRAIN_RECEIPT" "$JAR_RECEIPT" <<'PY'
import json,sys,time
path,source_commit,worker_sha,target,vlad_target,worker,canary,accept_path,brain_path,jar_path=sys.argv[1:]
accept=json.load(open(accept_path,encoding='utf-8'))
brain=json.load(open(brain_path,encoding='utf-8'))
jars=json.load(open(jar_path,encoding='utf-8'))
obj={
  'schema':'adam-cli-install-v12-judgement-jar-output-receipts',
  'ok':True,
  'sourceCommit':source_commit,
  'workerSha256':worker_sha,
  'target':target,
  'vladTarget':vlad_target,
  'worker':worker,
  'launcher':'termux-native-codex-worker-planned-venice-reviewed-jar-receipted',
  'interactiveMode':'research-plan-jars-output-kind-antagonize-venice-execute-receipt',
  'codexLocalDocs':accept.get('codexLocalDocs',[]),
  'codexLocalDocsLoaded':accept.get('codexLocalDocsLoaded') is True,
  'jarPersonalityGate':accept.get('jarGate') is True,
  'jarCount':jars.get('count'),
  'jarCatalogSyncState':jars.get('catalogSync',{}).get('state'),
  'jarUsageReceiptsRequired':True,
  'jarOutputKindRequired':True,
  'jarPendingOutbox':True,
  'venicePlanReview':accept.get('venicePlanReviewReceiptVerified') is True,
  'venicePlanDirective':accept.get('venicePlanDirective'),
  'selectedJudgmentJars':accept.get('selectedJudgmentJars',[]),
  'veniceStopReview':accept.get('veniceStopReviewReceiptVerified') is True,
  'veniceStopDirective':accept.get('veniceStopDirective'),
  'daemonBackoff':accept.get('daemonBackoff') is True,
  'knowsOwner':accept.get('knowsOwner') is True,
  'genericAssistantLeak':accept.get('genericAssistantLeak') is True,
  'bodyTransportCanary':'ADAM_BODY_OK' in canary,
  'phoneModelHealthy':brain.get('ok') is True,
  'phoneModelStatus':brain.get('status'),
  'installedAtEpoch':int(time.time()),
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

echo "ADAM/VLAD JUDGMENT JAR RECEIPT WORKERS INSTALLED receipt=$RECEIPT"
