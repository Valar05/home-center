#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
BIN_DIR="${HC_ADAM_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
TARGET="$BIN_DIR/adam"
SOURCE="$ROOT/tools/adam.py"
RECEIPT="$STATE/adam-cli-install-receipt.json"

mkdir -p "$STATE" "$BIN_DIR"
[ -f "$SOURCE" ] || { echo "BLOCKED: Adam router missing: $SOURCE" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo 'BLOCKED: python3 missing.' >&2; exit 3; }

cd "$ROOT"
python3 tools/test_adam_overlay_contract.py
python3 tools/test_adam_cli_contract.py
python3 -m py_compile tools/adam.py
chmod +x "$SOURCE"
ln -sfn "$SOURCE" "$TARGET"

CANARY="$($TARGET terminal 'printf ADAM_CLI_OK' --cwd "$ROOT" --timeout 10)"
printf '%s\n' "$CANARY" | grep -q 'ADAM_CLI_OK' || { echo 'BLOCKED: Adam CLI terminal canary failed.' >&2; exit 4; }

SOURCE_SHA="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
fi
ADAM_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"

python3 - "$RECEIPT" "$SOURCE_SHA" "$ADAM_SHA" "$TARGET" "$SOURCE" "$CANARY" <<'PY'
import json,sys,time
path,source_commit,adam_sha,target,source,canary=sys.argv[1:]
obj={
  'schema':'adam-cli-install-v1',
  'ok':True,
  'sourceCommit':source_commit,
  'adamSha256':adam_sha,
  'target':target,
  'source':source,
  'oneShotModes':['terminal','chat','continue','vlad'],
  'interactiveMode':'shell',
  'terminalCanary':'ADAM_CLI_OK' in canary,
  'installedAtEpoch':int(time.time()),
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

echo "ADAM CLI INSTALLED receipt=$RECEIPT"
