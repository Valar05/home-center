#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
GEN="$ROOT/tools/venice_fleshpunk_phone.sh"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
mkdir -p "$STATE"

[ -f "$GEN" ] || { echo "BLOCKED: image generator missing at $GEN" >&2; exit 2; }

# Reading existing receipts is offline and must not require THECAULDRON.
if [ "${1:-}" = receipts ]; then
  exec bash "$GEN" "$@"
fi

AXIS="$STATE/ssh-axis.json"
if python "$ROOT/tools/ssh_axis.py" check --target cauldron --json >"$AXIS" 2>"$STATE/ssh-axis.err"; then
  ENDPOINT="$(python - "$AXIS" <<'PY'
import json,sys
try:
    data=json.load(open(sys.argv[1],encoding='utf-8'))
    rows=data.get('ssh_axis') or []
    row=next((r for r in rows if r.get('target')=='cauldron' and r.get('callable')),None)
    print((row or {}).get('endpoint') or '')
except Exception:
    print('')
PY
)"
else
  ENDPOINT="$(python "$ROOT/tools/resolve_cauldron_ssh.py" 2>"$STATE/resolve.err")" || {
    cat "$STATE/ssh-axis.err" >&2 || true
    cat "$STATE/resolve.err" >&2 || true
    echo 'BLOCKED: THECAULDRON could not be resolved without Shizuku.' >&2
    exit 41
  }
  export FORTRESS_CAULDRON_SSH="$ENDPOINT"
  python "$ROOT/tools/ssh_axis.py" check --target cauldron --json >"$AXIS" 2>"$STATE/ssh-axis.err" || {
    cat "$AXIS" >&2 || true
    cat "$STATE/ssh-axis.err" >&2 || true
    echo 'BLOCKED: resolved THECAULDRON endpoint did not pass SSH Axis.' >&2
    exit 41
  }
fi

[ -n "${ENDPOINT:-}" ] || {
  echo 'BLOCKED: SSH Axis returned no verified THECAULDRON endpoint.' >&2
  exit 41
}
export FORTRESS_CAULDRON_SSH="$ENDPOINT"
exec bash "$GEN" "$@"
