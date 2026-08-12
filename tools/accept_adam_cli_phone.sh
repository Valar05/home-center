#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
RECEIPT="$STATE/adam-cli-phone-acceptance.json"
PACKAGE="com.homecenter.operatoroverlay"
ADAM_BIN="${HC_ADAM_BIN:-${PREFIX:-$HOME/.local}/bin/adam}"
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"
mkdir -p "$STATE"

[ -x "$ADAM_BIN" ] || { echo "BLOCKED: Adam CLI not executable: $ADAM_BIN" >&2; exit 2; }
[ -x "$RISH_BIN" ] || { echo "BLOCKED: rish missing: $RISH_BIN" >&2; exit 3; }

cd "$ROOT"
python3 tools/test_adam_overlay_contract.py
python3 tools/test_adam_cli_contract.py
python3 -m py_compile tools/adam.py tools/vlad_swarm_daemon.py

CANARY="$($ADAM_BIN terminal 'printf ADAM_PHONE_ACCEPT_OK' --cwd "$ROOT" --timeout 10)"
printf '%s\n' "$CANARY" | grep -q 'ADAM_PHONE_ACCEPT_OK' || { echo 'BLOCKED: CLI one-shot canary failed.' >&2; exit 4; }

OVERLAY_STATE="$($RISH_BIN -c "content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1)"
printf '%s\n' "$OVERLAY_STATE" | grep -q 'adam_request_id=' || { echo 'BLOCKED: overlay Adam state unavailable.' >&2; exit 5; }

VLAD_PIDS="$(pgrep -f '[p]ython.*vlad_swarm_daemon.py' | tr '\n' ' ' | sed 's/[[:space:]]*$//' || true)"
[ -n "$VLAD_PIDS" ] || { echo 'BLOCKED: Vlad swarm daemon is not running.' >&2; exit 6; }

SOURCE_SHA="$(git rev-parse HEAD 2>/dev/null || printf unknown)"
ADAM_SHA="$(sha256sum "$ROOT/tools/adam.py" | awk '{print $1}')"
CLI_TARGET="$(readlink -f "$ADAM_BIN" 2>/dev/null || printf '%s' "$ADAM_BIN")"

python3 - "$RECEIPT" "$SOURCE_SHA" "$ADAM_SHA" "$ADAM_BIN" "$CLI_TARGET" "$VLAD_PIDS" "$OVERLAY_STATE" <<'PY'
import json,sys,time
path,source,adam_sha,adam_bin,target,vlad_pids,overlay=sys.argv[1:]
obj={
  'schema':'adam-cli-phone-acceptance-v1',
  'ok':True,
  'sourceCommit':source,
  'adamSha256':adam_sha,
  'adamCommand':adam_bin,
  'adamTarget':target,
  'bareAdamMode':'shell',
  'oneShotModes':['terminal','chat','continue','vlad'],
  'terminalCanary':True,
  'overlayAdamStateVisible':'adam_request_id=' in overlay,
  'vladDaemonAlive':bool(vlad_pids.strip()),
  'vladPids':vlad_pids.strip().split(),
  'verifiedAtEpoch':int(time.time()),
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

echo "ADAM CLI PHONE ACCEPTED receipt=$RECEIPT"
