#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE="${HC_HANDS_ROUTER_STATE:-$HOME/.local/state/home-center/hands-router}"
RUN="$STATE/run"
mkdir -p "$RUN"
case "${1:-start}" in
  start)
    printf '1\n' > "$STATE/enabled"
    if [ -f "$RUN/pid" ] && kill -0 "$(cat "$RUN/pid")" 2>/dev/null; then
      echo "hands-router already running pid=$(cat "$RUN/pid")"
      exit 0
    fi
    nohup sh -c 'ROOT="$1"; while :; do python3 "$ROOT/tools/hands_router.py" drain --limit 8 >/dev/null 2>&1 || true; sleep "${HC_HANDS_POLL_SECONDS:-1}"; done' sh "$ROOT" >"$RUN/router.log" 2>&1 &
    echo $! > "$RUN/pid"
    echo "hands-router started pid=$!"
    ;;
  stop)
    printf '0\n' > "$STATE/enabled"
    if [ -f "$RUN/pid" ] && kill -0 "$(cat "$RUN/pid")" 2>/dev/null; then kill "$(cat "$RUN/pid")" || true; fi
    rm -f "$RUN/pid"
    echo "hands-router stopped and disabled"
    ;;
  on) python3 "$ROOT/tools/hands_router.py" on ;;
  off) python3 "$ROOT/tools/hands_router.py" off ;;
  status) python3 "$ROOT/tools/hands_router.py" status ;;
  *) echo "usage: $0 {start|stop|on|off|status}" >&2; exit 2 ;;
esac
