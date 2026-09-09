#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BIN="$TMP/bin"; STATE="$TMP/state"; mkdir -p "$BIN" "$STATE"
cat >"$BIN/termux-notification" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${HC_TEST_NOTIFY_LOG:?}"
SH
chmod +x "$BIN/termux-notification"
export PATH="$BIN:$PATH"
export HC_STATE_DIR="$STATE"
export HC_REPO_ROOT="$ROOT"
export HC_TEST_NOTIFY_LOG="$TMP/notify.log"

# Canary 1: no heartbeat => button must advertise OFFLINE and never false-green.
bash "$ROOT/tools/home_center_recovery_button.sh" status >/dev/null
python3 - "$STATE/home-center-recovery-button-latest.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['phase']=='degraded' and x['ok'] is False, x
assert x['truth']['homeCenterRecovered'] is False, x
PY
grep -q 'HOME CENTER • OFFLINE' "$TMP/notify.log"
grep -q 'TURN HOME CENTER ON' "$TMP/notify.log"

# Canary 2: fresh exact primary-phone heartbeat => status may report ON.
python3 - "$STATE/phone-relay-heartbeat.json" <<'PY'
import json,sys,time
json.dump({'schema':'home-center-phone-relay-heartbeat-v1','deviceId':'primary-phone','pid':123,'state':'poll_ok','lastSuccessAtEpoch':int(time.time())},open(sys.argv[1],'w'))
PY
: >"$TMP/notify.log"
bash "$ROOT/tools/home_center_recovery_button.sh" status >/dev/null
python3 - "$STATE/home-center-recovery-button-latest.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['phase']=='healthy' and x['ok'] is True, x
assert x['truth']['homeCenterRecovered'] is True, x
PY
grep -q 'HOME CENTER • ON' "$TMP/notify.log"
grep -q 'TURN HOME CENTER ON' "$TMP/notify.log"

# Canary 3: stale heartbeat must regress to OFFLINE, not PID theater.
python3 - "$STATE/phone-relay-heartbeat.json" <<'PY'
import json,sys,time
json.dump({'schema':'home-center-phone-relay-heartbeat-v1','deviceId':'primary-phone','pid':123,'state':'poll_ok','lastSuccessAtEpoch':int(time.time())-999},open(sys.argv[1],'w'))
PY
bash "$ROOT/tools/home_center_recovery_button.sh" status >/dev/null
python3 - "$STATE/home-center-recovery-button-latest.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['phase']=='degraded' and x['ok'] is False, x
PY

echo 'PASS home-center-recovery-button canaries'
