#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
BIN_DIR="${HC_ADAM_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
TARGET="$BIN_DIR/adam"
ROUTER="$ROOT/tools/adam.py"
WORKER="$ROOT/tools/adam_codex_phone.py"
RECEIPT="$STATE/adam-cli-install-receipt.json"
ACCEPT_RECEIPT="$STATE/adam-phone-worker-acceptance.json"
BRAIN_RECEIPT="$STATE/adam-phone-brain-receipt.json"

mkdir -p "$STATE" "$BIN_DIR"
for f in "$ROUTER" "$WORKER"; do
  [ -f "$f" ] || { echo "BLOCKED: Adam component missing: $f" >&2; exit 2; }
done
PYTHON_BIN="$(command -v python3 || true)"
[ -n "$PYTHON_BIN" ] || { echo 'BLOCKED: python3 missing.' >&2; exit 3; }

cd "$ROOT"
python3 tools/test_adam_overlay_contract.py
python3 tools/test_adam_cli_contract.py
python3 tools/test_adam_codex_phone.py
python3 -m py_compile tools/adam.py tools/adam_codex_phone.py tools/accept_adam_executive_phone.py

# Keep the already-working explicit overlay transport contract. Bare Adam and
# ordinary text args use the new Codex-shaped phone worker. Explicit legacy body
# modes remain available only as body transports for overlay/runtime compatibility.
TMP_TARGET="$TARGET.tmp.$$"
cat > "$TMP_TARGET" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
case "\${1:-}" in
  terminal|chat|continue|vlad|shell)
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

# Body transport canary: preserve the overlay's proven terminal route.
CANARY="$($TARGET terminal 'printf ADAM_BODY_OK' --cwd "$ROOT" --timeout 10)"
printf '%s\n' "$CANARY" | grep -q 'ADAM_BODY_OK' || { echo 'BLOCKED: Adam body transport canary failed.' >&2; exit 4; }

# The worker uses the existing phone-local model only as planner/classifier.
bash tools/ensure_adam_phone_brain.sh | tee "$BRAIN_RECEIPT"
grep -q '"ok":true' "$BRAIN_RECEIPT" || { echo 'BLOCKED: Adam phone model did not become healthy.' >&2; exit 5; }

# Live proof: Jar-loaded Codex worker must produce a governed owner-aware reply;
# raw model prose cannot pass this acceptance because the worker suppresses it.
python3 tools/accept_adam_executive_phone.py | tee "$ACCEPT_RECEIPT"
grep -q '"ok": true' "$ACCEPT_RECEIPT" || { echo 'BLOCKED: Adam Codex phone worker acceptance failed.' >&2; exit 6; }

SOURCE_SHA="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
fi
WORKER_SHA="$(sha256sum "$WORKER" | awk '{print $1}')"

python3 - "$RECEIPT" "$SOURCE_SHA" "$WORKER_SHA" "$TARGET" "$WORKER" "$CANARY" "$ACCEPT_RECEIPT" "$BRAIN_RECEIPT" <<'PY'
import json,sys,time
path,source_commit,worker_sha,target,worker,canary,accept_path,brain_path=sys.argv[1:]
accept=json.load(open(accept_path,encoding='utf-8'))
brain=json.load(open(brain_path,encoding='utf-8'))
obj={
  'schema':'adam-cli-install-v7-codex-phone',
  'ok':True,
  'sourceCommit':source_commit,
  'workerSha256':worker_sha,
  'target':target,
  'worker':worker,
  'launcher':'termux-native-codex-shaped-phone-worker',
  'interactiveMode':'codex-worker-loop',
  'jarPersonalityGate':accept.get('jarGate') is True,
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

echo "ADAM CODEX-SHAPED PHONE WORKER INSTALLED receipt=$RECEIPT"
