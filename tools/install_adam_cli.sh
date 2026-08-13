#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
BIN_DIR="${HC_ADAM_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
TARGET="$BIN_DIR/adam"
ROUTER="$ROOT/tools/adam.py"
WORKER="$ROOT/tools/adam_receipted_worker.py"
RECEIPT="$STATE/adam-cli-install-receipt.json"
ACCEPT_RECEIPT="$STATE/adam-phone-worker-acceptance.json"
BRAIN_RECEIPT="$STATE/adam-phone-brain-receipt.json"

mkdir -p "$STATE" "$BIN_DIR"
for f in \
  "$ROUTER" \
  "$WORKER" \
  "$ROOT/tools/accept_adam_receipted_phone.py" \
  "$ROOT/tools/adam_planned_venice.py" \
  "$ROOT/tools/adam_venice_reviewed.py" \
  "$ROOT/tools/adam_codex_phone.py" \
  "$ROOT/tools/she_raw_cli.py" \
  "$ROOT/tools/canon_sourcer.py" \
  "$ROOT/config/she-raw-cli.v1.json" \
  "$ROOT/config/she-raw-jar-cache.md" \
  "$ROOT/config/she-raw-aliases.example.json" \
  "$ROOT/config/canon-sources.v1.json" \
  "$ROOT/tools/judgment_jar_runtime.py" \
  "$ROOT/tools/judgment_jars.py" \
  "$ROOT/tools/judgment_jar_receipts.py" \
  "$ROOT/tools/judgment_jar_atom_import.py" \
  "$ROOT/tools/judgment_jar_review_import.py" \
  "$ROOT/tools/jar_receipt.py" \
  "$ROOT/tools/venice_plan_review.py" \
  "$ROOT/tools/venice_review.py" \
  "$ROOT/tools/venice_review_memory.py" \
  "$ROOT/AGENTS.md" "$ROOT/MEMORIES.md" "$ROOT/SKILLS.md"; do
  [ -f "$f" ] || { echo "BLOCKED: Adam/Codex/Venice/Jar component missing: $f" >&2; exit 2; }
done
PYTHON_BIN="$(command -v python3 || true)"
[ -n "$PYTHON_BIN" ] || { echo 'BLOCKED: python3 missing.' >&2; exit 3; }

cd "$ROOT"
python3 tools/judgment_jar_receipt_contract_check.py
python3 tools/test_adam_overlay_contract.py
python3 tools/test_adam_overlay_delivery_state.py
python3 tools/test_adam_cli_contract.py
python3 tools/test_adam_codex_phone.py
python3 tools/test_she_raw_cli.py
python3 -m unittest tests.test_canon_sourcer
python3 tools/test_adam_venice_review_gate.py
python3 tools/test_venice_plan_review.py
python3 tools/test_venice_review_memory.py
node --test tools/fortress_online_v2_boot.test.mjs
python3 -m py_compile \
  tools/adam.py \
  tools/adam_receipted_worker.py \
  tools/accept_adam_receipted_phone.py \
  tools/adam_codex_phone.py \
  tools/she_raw_cli.py \
  tools/canon_sourcer.py \
  tools/adam_venice_reviewed.py \
  tools/adam_planned_venice.py \
  tools/judgment_jar_runtime.py \
  tools/judgment_jars.py \
  tools/judgment_jar_receipts.py \
  tools/judgment_jar_atom_import.py \
  tools/judgment_jar_review_import.py \
  tools/jar_receipt.py \
  tools/venice_plan_review.py \
  tools/venice_review.py \
  tools/venice_review_memory.py \
  tools/accept_adam_executive_phone.py \
  tools/vlad_swarm_daemon.py

SHE_RAW_ALIAS_CONFIG="${HC_SHE_RAW_ALIASES:-$HOME/.config/home-center/she-raw-aliases.json}"
mkdir -p "$(dirname "$SHE_RAW_ALIAS_CONFIG")"
if [ ! -f "$SHE_RAW_ALIAS_CONFIG" ]; then
  cp "$ROOT/config/she-raw-aliases.example.json" "$SHE_RAW_ALIAS_CONFIG"
  chmod 600 "$SHE_RAW_ALIAS_CONFIG"
fi

TMP_TARGET="$TARGET.tmp.$"
cat > "$TMP_TARGET" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
case "\${1:-}" in
  terminal|chat|continue|vlad|scene|she-raw)
    exec "$PYTHON_BIN" "$ROUTER" "\$@"
    ;;
  *)
    exec "$PYTHON_BIN" "$WORKER" "\$@"
    ;;
esac
EOF
chmod 755 "$TMP_TARGET"
mv -f "$TMP_TARGET" "$TARGET"
hash -r 2>/dev/null || true

CANARY="$($TARGET terminal 'printf ADAM_BODY_OK' --cwd "$ROOT" --timeout 10)"
printf '%s\n' "$CANARY" | grep -q 'ADAM_BODY_OK' || { echo 'BLOCKED: Adam body transport canary failed.' >&2; exit 4; }

bash tools/ensure_adam_phone_brain.sh | tee "$BRAIN_RECEIPT"
grep -q '"ok":true' "$BRAIN_RECEIPT" || { echo 'BLOCKED: Adam phone model did not become healthy.' >&2; exit 5; }

SHE_RAW_CANARY="$($TARGET she-raw --doctor)"
printf '%s\n' "$SHE_RAW_CANARY" | grep -q '"ready": true' || { echo 'BLOCKED: direct local She Raw runtime did not become ready.' >&2; exit 9; }

python3 tools/accept_adam_receipted_phone.py | tee "$ACCEPT_RECEIPT"
grep -q '"ok": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam planned/Venice-reviewed Codex worker acceptance failed.' >&2; exit 6; }
grep -q '"venicePlanReviewReceiptVerified": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam pre-execution Venice plan receipt not verified.' >&2; exit 7; }
grep -q '"veniceStopReviewReceiptVerified": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam completion Venice receipt not verified.' >&2; exit 8; }

SOURCE_SHA="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
fi
WORKER_SHA="$(sha256sum "$WORKER" | awk '{print $1}')"

python3 - "$RECEIPT" "$SOURCE_SHA" "$WORKER_SHA" "$TARGET" "$WORKER" "$CANARY" "$ACCEPT_RECEIPT" "$BRAIN_RECEIPT" "$SHE_RAW_CANARY" "$SHE_RAW_ALIAS_CONFIG" <<'PY'
import json,sys,time
path,source_commit,worker_sha,target,worker,canary,accept_path,brain_path,she_raw_canary,alias_path=sys.argv[1:]
accept=json.load(open(accept_path,encoding='utf-8'))
brain=json.load(open(brain_path,encoding='utf-8'))
obj={
  'schema':'adam-cli-install-v12-receipted-jars-plan-venice-stop-memory-daemon',
  'ok':True,
  'sourceCommit':source_commit,
  'workerSha256':worker_sha,
  'target':target,
  'worker':worker,
  'launcher':'termux-native-codex-worker-planned-venice-reviewed-receipted-jars',
  'interactiveMode':'research-plan-jars-antagonize-venice-execute',
  'judgmentJarFastAccessSurfaces':['judgment_jars','home_center','vlad'],
  'commandCenterExists':False,
  'judgmentJarContextReceipts':True,
  'judgmentJarOutputReceiptCommand':'python3 tools/jar_receipt.py record',
  'judgmentJarReceiptDelivery':'existing vlad-jars sync heartbeat to Home Center with readback',
  'codexLocalDocs':accept.get('codexLocalDocs',[]),
  'codexLocalDocsLoaded':accept.get('codexLocalDocsLoaded') is True,
  'jarPersonalityGate':accept.get('jarGate') is True,
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
  'sheRawLocalOnly':True,
  'sheRawDoctorReady':'"ready": true' in she_raw_canary,
  'sheRawAliasConfig':alias_path,
  'innerFortressSceneRoute':True,
  'installedAtEpoch':int(time.time()),
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

echo "ADAM RECEIPTED-JAR RESEARCH/PLAN/VENICE/CODEX PHONE WORKER INSTALLED receipt=$RECEIPT"
