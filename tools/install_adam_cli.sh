#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
BIN_DIR="${HC_ADAM_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
TARGET="$BIN_DIR/adam"
SOURCE="$ROOT/tools/adam.py"
RECEIPT="$STATE/adam-cli-install-receipt.json"
EXEC_RECEIPT="$STATE/adam-executive-acceptance.json"
BRAIN_RECEIPT="$STATE/adam-phone-brain-receipt.json"

mkdir -p "$STATE" "$BIN_DIR"
[ -f "$SOURCE" ] || { echo "BLOCKED: Adam router missing: $SOURCE" >&2; exit 2; }
PYTHON_BIN="$(command -v python3 || true)"
[ -n "$PYTHON_BIN" ] || { echo 'BLOCKED: python3 missing.' >&2; exit 3; }

cd "$ROOT"
python3 tools/test_adam_overlay_contract.py
python3 tools/test_adam_cli_contract.py
python3 -m py_compile tools/adam.py tools/accept_adam_executive_phone.py

# Android shared storage is commonly mounted noexec. Do not symlink an executable
# entrypoint to the repo there. Install a tiny executable wrapper in Termux's
# native prefix and invoke the shared-storage source through Python explicitly.
TMP_TARGET="$TARGET.tmp.$$"
cat > "$TMP_TARGET" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec "$PYTHON_BIN" "$SOURCE" "\$@"
EOF
chmod 755 "$TMP_TARGET"
mv -f "$TMP_TARGET" "$TARGET"
hash -r 2>/dev/null || true

CANARY="$($TARGET terminal 'printf ADAM_CLI_OK' --cwd "$ROOT" --timeout 10)"
printf '%s\n' "$CANARY" | grep -q 'ADAM_CLI_OK' || { echo 'BLOCKED: Adam CLI terminal canary failed.' >&2; exit 4; }

# Bare Adam depends on the already-existing local phone brain. Health-check it and
# start that existing daemon when necessary before exercising the chatbot path.
bash tools/ensure_adam_phone_brain.sh | tee "$BRAIN_RECEIPT"
grep -q '"ok":true' "$BRAIN_RECEIPT" || { echo 'BLOCKED: Adam phone brain did not become healthy.' >&2; exit 5; }

# Bare Adam is a chatbot/executive, not a Bash prompt. Prove the live local model
# resolves a greeting to conversation before declaring the install usable.
python3 tools/accept_adam_executive_phone.py | tee "$EXEC_RECEIPT"
grep -q '"ok": true' "$EXEC_RECEIPT" || { echo 'BLOCKED: Adam conversational executive canary failed.' >&2; exit 6; }

SOURCE_SHA="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
fi
ADAM_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"

python3 - "$RECEIPT" "$SOURCE_SHA" "$ADAM_SHA" "$TARGET" "$SOURCE" "$CANARY" "$EXEC_RECEIPT" "$BRAIN_RECEIPT" <<'PY'
import json,sys,time
path,source_commit,adam_sha,target,source,canary,exec_receipt,brain_receipt=sys.argv[1:]
executive=json.load(open(exec_receipt,encoding='utf-8'))
brain=json.load(open(brain_receipt,encoding='utf-8'))
obj={
  'schema':'adam-cli-install-v3',
  'ok':True,
  'sourceCommit':source_commit,
  'adamSha256':adam_sha,
  'target':target,
  'source':source,
  'launcher':'termux-native-wrapper',
  'oneShotModes':['terminal','chat','continue','vlad'],
  'interactiveMode':'conversational-executive',
  'terminalCanary':'ADAM_CLI_OK' in canary,
  'phoneBrainHealthy':brain.get('ok') is True,
  'phoneBrainStatus':brain.get('status'),
  'chatbotCanary':executive.get('ok') is True,
  'chatbotKind':executive.get('plan',{}).get('kind'),
  'localExecutive':executive.get('localExecutive'),
  'installedAtEpoch':int(time.time()),
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

echo "ADAM CONVERSATIONAL EXECUTIVE INSTALLED receipt=$RECEIPT"
