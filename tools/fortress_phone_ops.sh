#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center"
mkdir -p "$STATE"
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"

json_receipt() {
  local ok="$1" op="$2" detail="$3"
  python3 - "$ok" "$op" "$detail" <<'PY'
import json,sys,time,socket
ok,op,detail=sys.argv[1:]
print(json.dumps({
  "schema":"fortress.phone-ops.v1",
  "ok":ok=="1",
  "operation":op,
  "detail":detail,
  "device":socket.gethostname(),
  "atEpoch":int(time.time())
}, sort_keys=True))
PY
}

need_rish() {
  [ -x "$RISH_BIN" ] || { json_receipt 0 "$1" "rish/Shizuku unavailable"; exit 2; }
}

rish() { "$RISH_BIN" -c "$1"; }

status() {
  need_rish status
  local out
  out="$(rish "pm list packages com.homecenter.operatoroverlay; appops get com.homecenter.operatoroverlay SYSTEM_ALERT_WINDOW 2>/dev/null || true; content query --uri content://com.homecenter.operatoroverlay.state/state 2>/dev/null || true; pidof com.android.chrome 2>/dev/null || true" 2>&1 || true)"
  printf '%s\n' "$out" > "$STATE/fortress-phone-ops-status.txt"
  json_receipt 1 status "$(printf '%s' "$out" | tr '\n' ' ' | cut -c1-900)"
}

overlay_restart() {
  exec bash "$ROOT/tools/recover_adam_overlay_phone.sh"
}

chrome_open() {
  need_rish chrome-open
  local url="${1:-https://chatgpt.com/}"
  case "$url" in http://*|https://*) ;; *) json_receipt 0 chrome-open "URL must be http(s)"; exit 3;; esac
  local pkg=""
  for candidate in com.android.chrome com.chrome.beta com.chrome.dev org.chromium.chrome; do
    if rish "pm list packages $candidate" 2>/dev/null | grep -q "package:$candidate"; then pkg="$candidate"; break; fi
  done
  [ -n "$pkg" ] || { json_receipt 0 chrome-open "No supported Chromium package found"; exit 4; }
  rish "am start -a android.intent.action.VIEW -d '$url' -p '$pkg'" >/dev/null
  sleep 1
  local top
  top="$(rish "dumpsys activity activities | grep -m1 mResumedActivity" 2>/dev/null || true)"
  printf '%s\n' "$top" | grep -q "$pkg" || { json_receipt 0 chrome-open "launch attempted but resumed activity was: $top"; exit 5; }
  json_receipt 1 chrome-open "foreground=$pkg url=$url"
}

chrome_reload() {
  need_rish chrome-reload
  # Android keyevent 285 is KEYCODE_REFRESH on modern Android. If the active
  # browser ignores it, the canary will fail rather than pretending success.
  rish "input keyevent 285" >/dev/null
  json_receipt 1 chrome-reload "KEYCODE_REFRESH dispatched to foreground app"
}

canary() {
  if [ -x "$ROOT/tools/accept_adam_cli_phone.sh" ]; then
    exec bash "$ROOT/tools/accept_adam_cli_phone.sh"
  fi
  json_receipt 0 canary "accept_adam_cli_phone.sh missing"
  exit 6
}

help_text() {
  cat <<'EOF'
fortress-phone-ops commands:
  status
  overlay-restart
  chrome-open [https://url]
  chrome-reload
  canary
EOF
}

op="${1:-help}"; shift || true
case "$op" in
  status) status "$@" ;;
  overlay-restart|restart|restart-overlay) overlay_restart "$@" ;;
  chrome-open|chrome|chromium) chrome_open "$@" ;;
  chrome-reload|reload) chrome_reload "$@" ;;
  canary|test) canary "$@" ;;
  help|-h|--help) help_text ;;
  *) json_receipt 0 "$op" "unsupported operation"; help_text >&2; exit 64 ;;
esac
