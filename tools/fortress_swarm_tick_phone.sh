#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/swarm-manager"
STAMP="$(date +%Y%m%dT%H%M%S)"
SHOT="$STATE/phone-$STAMP.png"
UIXML="$STATE/phone-$STAMP.xml"
TMUX="$STATE/tmux-$STAMP.txt"
STATUS="$STATE/status-$STAMP.txt"
DECISION="$STATE/decision-$STAMP.txt"
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"
mkdir -p "$STATE"

fail(){ echo "BLOCKED: $*" >&2; exit 2; }
[ -x "$RISH_BIN" ] || fail "rish missing; cannot observe the actual phone"
command -v tmux >/dev/null 2>&1 || fail "tmux missing; cannot inspect local swarm sessions"

# Observe before talking. Screenshot is primary visual evidence; UI XML is a machine-readable companion.
"$RISH_BIN" -c 'screencap -p' > "$SHOT"
[ -s "$SHOT" ] || fail "phone screenshot produced no bytes"

set +e
"$RISH_BIN" -c 'uiautomator dump /data/local/tmp/hc-swarm-ui.xml >/dev/null 2>&1; cat /data/local/tmp/hc-swarm-ui.xml; rm -f /data/local/tmp/hc-swarm-ui.xml' > "$UIXML"
set -e

tmux list-sessions -F '#{session_name}\t#{session_attached}\t#{session_windows}\t#{session_activity}' > "$TMUX" 2>&1 || true
{
  echo "=== PHONE SWARM TICK $STAMP ==="
  echo "screenshot=$SHOT"
  echo "ui=$UIXML"
  echo "tmux=$TMUX"
  echo
  echo "--- active campaign receipts ---"
  find "$HOME/.local/state/home-center" -maxdepth 4 -type f \( -name 'receipt.json' -o -name 'launch.json' -o -name 'current.json' -o -name '*acceptance*.json' \) -print 2>/dev/null | sort | tail -80
  echo
  echo "--- tmux sessions ---"
  cat "$TMUX"
  echo
  echo "--- ui text ---"
  if [ -s "$UIXML" ]; then
    python3 - "$UIXML" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
vals=[]
for key in ('text','content-desc'):
  vals += re.findall(rf'{key}="([^"]+)"',s)
seen=[]
for v in vals:
  v=v.replace('&amp;','&').strip()
  if v and v not in seen:
    seen.append(v)
for v in seen[:200]: print(v)
PY
  else
    echo "UI XML unavailable; screenshot remains authoritative visual capture."
  fi
} > "$STATUS"

PROMPT="$(cat <<EOF
FORTRESS ONLINE — SWARM MANAGER TICK
You are not here to converse. You are managing the existing phone-local swarm.

Fresh phone evidence has been captured:
SCREENSHOT: $SHOT
UI XML: $UIXML
TMUX STATE: $TMUX
STATUS BUNDLE: $STATUS

Read the machine-readable status and all active campaign receipts/checkpoints. Determine the single highest-value next swarm-management action. Prefer resuming/repairing an existing worker over inventing a new one. If a worker has exited prematurely, resume it. If a campaign is alive but stalled, inspect its log/checkpoint and intervene. Preserve Saint Andrew CONTINUE law and Time Now latency pressure. Do not report status as work. Execute the next authorized local action, then checkpoint what changed.
EOF
)"

if command -v adam >/dev/null 2>&1; then
  adam "$PROMPT" | tee "$DECISION"
elif [ -f "$ROOT/tools/adam_venice_reviewed.py" ]; then
  python3 "$ROOT/tools/adam_venice_reviewed.py" "$PROMPT" | tee "$DECISION"
else
  fail "no phone-local Adam worker available after observation"
fi

python3 - "$STATE/last-tick.json" "$STAMP" "$SHOT" "$UIXML" "$TMUX" "$STATUS" "$DECISION" <<'PY'
import json,os,sys,time,hashlib
out,stamp,shot,ui,tmux,status,decision=sys.argv[1:]
def sha(p):
    if not os.path.isfile(p): return None
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
obj={
 'schema':'fortress-phone-swarm-tick-v1',
 'capturedAt':stamp,
 'writtenAtEpoch':int(time.time()),
 'screenshot':shot,
 'screenshotSha256':sha(shot),
 'uiXml':ui,
 'tmuxState':tmux,
 'statusBundle':status,
 'decisionReceipt':decision,
 'rule':'observe actual phone -> inspect swarm -> execute next action -> checkpoint; conversation is not management'
}
open(out,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
