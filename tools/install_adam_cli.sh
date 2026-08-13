#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
BIN_DIR="${HC_ADAM_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
TARGET="$BIN_DIR/adam"
VLAD_TARGET="$BIN_DIR/vlad"
ROUTER="$ROOT/tools/adam.py"
WORKER="$ROOT/tools/adam_planned_venice_receipted.py"
VLAD_TOOL="$ROOT/tools/vlad.py"
JAR_CACHE="${HC_JUDGMENT_JARS_CACHE:-$HOME/.local/state/home-center/vlad-swarm/judgment-jars.json}"
JAR_CONFIG="${HC_JUDGMENT_JARS_CONFIG:-$ROOT/config/judgment-jars.v1.json}"
RECEIPT="$STATE/adam-cli-install-receipt.json"
ACCEPT_RECEIPT="$STATE/adam-phone-worker-acceptance.json"
BRAIN_RECEIPT="$STATE/adam-phone-brain-receipt.json"
JAR_STATUS_RECEIPT="$STATE/adam-judgment-jar-usage-status.json"

mkdir -p "$STATE" "$BIN_DIR"
for f in \
  "$ROUTER" "$WORKER" "$VLAD_TOOL" \
  "$ROOT/tools/adam_planned_venice.py" \
  "$ROOT/tools/adam_venice_reviewed.py" \
  "$ROOT/tools/adam_codex_phone.py" \
  "$ROOT/tools/judgment_jars.py" \
  "$ROOT/tools/judgment_jar_receipts.py" \
  "$ROOT/tools/judgment_jar_common.py" \
  "$ROOT/tools/judgment_jar_cabinet.py" \
  "$ROOT/tools/judgment_jar_registry.py" \
  "$ROOT/tools/home_center_mcp_client.py" \
  "$ROOT/tools/venice_plan_review.py" \
  "$ROOT/tools/venice_review.py" \
  "$ROOT/tools/venice_review_receipted.py" \
  "$ROOT/tools/venice_review_memory.py" \
  "$JAR_CONFIG" \
  "$ROOT/AGENTS.md" "$ROOT/MEMORIES.md" "$ROOT/SKILLS.md"; do
  [ -f "$f" ] || { echo "BLOCKED: Adam/Codex/Venice/Judgment-Jar component missing: $f" >&2; exit 2; }
done
PYTHON_BIN="$(command -v python3 || true)"
[ -n "$PYTHON_BIN" ] || { echo 'BLOCKED: python3 missing.' >&2; exit 3; }

cd "$ROOT"
python3 tools/test_judgment_jar_registry.py
python3 tools/test_judgment_jar_receipts.py
python3 tools/test_adam_jar_receipt_contract.py
python3 tools/test_adam_overlay_contract.py
python3 tools/test_adam_overlay_delivery_state.py
python3 tools/test_adam_cli_contract.py
python3 tools/test_adam_codex_phone.py
python3 tools/test_adam_venice_review_gate.py
python3 tools/test_venice_plan_review.py
python3 tools/test_venice_review_memory.py
node --test atom/test/judgment-jars.test.mjs
node --test tools/fortress_online_v2_boot.test.mjs
python3 -m py_compile \
  tools/adam.py \
  tools/adam_codex_phone.py \
  tools/adam_venice_reviewed.py \
  tools/adam_planned_venice.py \
  tools/adam_planned_venice_receipted.py \
  tools/judgment_jars.py \
  tools/judgment_jar_receipts.py \
  tools/judgment_jar_common.py \
  tools/judgment_jar_cabinet.py \
  tools/judgment_jar_registry.py \
  tools/vlad.py \
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
exec env \
  HC_REPO_ROOT=$(printf '%q' "$ROOT") \
  HC_JUDGMENT_JARS_CACHE=$(printf '%q' "$JAR_CACHE") \
  HC_JUDGMENT_JARS_CONFIG=$(printf '%q' "$JAR_CONFIG") \
  "$PYTHON_BIN" "$VLAD_TOOL" "\$@"
EOF
chmod 755 "$TMP_VLAD"
mv -f "$TMP_VLAD" "$VLAD_TARGET"
hash -r 2>/dev/null || true

CANARY="$($TARGET terminal 'printf ADAM_BODY_OK' --cwd "$ROOT" --timeout 10)"
printf '%s\n' "$CANARY" | grep -q 'ADAM_BODY_OK' || { echo 'BLOCKED: Adam body transport canary failed.' >&2; exit 4; }

"$VLAD_TARGET" jars status >/dev/null
"$VLAD_TARGET" jars usage-status > "$JAR_STATUS_RECEIPT"
python3 - "$JAR_STATUS_RECEIPT" <<'PY'
import json,sys
value=json.load(open(sys.argv[1],encoding='utf-8'))
assert value.get('ok') is True, value
assert value.get('outputKinds'), value
assert value.get('historyPath'), value
assert value.get('pendingOutboxPath'), value
print(json.dumps({'ok':True,'outputKinds':value['outputKinds'],'pendingUsageReceipts':value.get('pendingUsageReceipts')},sort_keys=True))
PY

bash tools/ensure_adam_phone_brain.sh | tee "$BRAIN_RECEIPT"
grep -q '"ok":true' "$BRAIN_RECEIPT" || { echo 'BLOCKED: Adam phone model did not become healthy.' >&2; exit 5; }

python3 tools/accept_adam_executive_phone.py | tee "$ACCEPT_RECEIPT"
grep -q '"ok": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam receipt-enforced planned/Venice-reviewed worker acceptance failed.' >&2; exit 6; }
grep -q '"venicePlanReviewReceiptVerified": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam pre-execution Venice plan receipt not verified.' >&2; exit 7; }
grep -q '"veniceStopReviewReceiptVerified": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam completion Venice receipt not verified.' >&2; exit 8; }
grep -q '"terminalJarUsageReceiptVerified": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam terminal Judgment Jar usage receipt not verified.' >&2; exit 9; }

SOURCE_SHA="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
fi
WORKER_SHA="$(sha256sum "$WORKER" | awk '{print $1}')"

python3 - "$RECEIPT" "$SOURCE_SHA" "$WORKER_SHA" "$TARGET" "$VLAD_TARGET" "$WORKER" "$CANARY" "$ACCEPT_RECEIPT" "$BRAIN_RECEIPT" "$JAR_STATUS_RECEIPT" <<'PY'
import json,sys,time
(path,source_commit,worker_sha,target,vlad_target,worker,canary,
 accept_path,brain_path,jar_status_path)=sys.argv[1:]
accept=json.load(open(accept_path,encoding='utf-8'))
brain=json.load(open(brain_path,encoding='utf-8'))
jar_status=json.load(open(jar_status_path,encoding='utf-8'))
obj={
  'schema':'adam-cli-install-v12-judgment-jar-usage-receipts',
  'ok':True,
  'sourceCommit':source_commit,
  'workerSha256':worker_sha,
  'target':target,
  'vladTarget':vlad_target,
  'worker':worker,
  'launcher':'termux-native-planned-venice-reviewed-judgment-jar-receipted',
  'interactiveMode':'research-plan-jars-output-kind-antagonize-venice-execute-receipt',
  'codexLocalDocs':accept.get('codexLocalDocs',[]),
  'codexLocalDocsLoaded':accept.get('codexLocalDocsLoaded') is True,
  'jarPersonalityGate':accept.get('jarGate') is True,
  'judgmentJarUsageReceipts':accept.get('judgmentJarUsageReceipts') is True,
  'judgmentJarOutputKindRequired':accept.get('judgmentJarOutputKindRequired') is True,
  'selectedJarContextUsageReceiptIds':accept.get('selectedJarContextUsageReceiptIds',[]),
  'planReviewJarUsageReceiptIds':accept.get('planReviewJarUsageReceiptIds',[]),
  'stopReviewJarUsageReceiptIds':accept.get('stopReviewJarUsageReceiptIds',[]),
  'terminalJarUsageReceiptVerified':accept.get('terminalJarUsageReceiptVerified') is True,
  'jarOutputKinds':jar_status.get('outputKinds') or [],
  'jarUsageHistoryPath':jar_status.get('historyPath'),
  'jarPendingOutboxPath':jar_status.get('pendingOutboxPath'),
  'jarPendingUsageReceipts':jar_status.get('pendingUsageReceipts'),
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

echo "ADAM/VLAD JUDGMENT-JAR-RECEIPTED PHONE WORKERS INSTALLED receipt=$RECEIPT"
