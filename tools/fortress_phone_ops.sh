#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center"
CHROMIUM="$ROOT/tools/android_chromium_control.py"
NIGHT_STATUS="$ROOT/tools/fortress_night_status.py"
RELAY_RECOVER="$ROOT/tools/home_center_phone_relay_recover.sh"
mkdir -p "$STATE"
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"

json_receipt() {
  local ok="$1" op="$2" detail="$3"
  python3 - "$ok" "$op" "$detail" <<'PY'
import json,sys,time,socket
ok,op,detail=sys.argv[1:]
print(json.dumps({
  "schema":"fortress.phone-ops.v2",
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

need_chromium_controller() {
  [ -f "$CHROMIUM" ] || { json_receipt 0 "$1" "android_chromium_control.py missing"; exit 3; }
}

decode_url() {
  [ "$#" -eq 1 ] || return 1
  printf '%s' "$1" | base64 -d 2>/dev/null
}

status() {
  need_rish status
  local overlay chromium
  overlay="$(rish "pm list packages com.homecenter.operatoroverlay; appops get com.homecenter.operatoroverlay SYSTEM_ALERT_WINDOW 2>/dev/null || true; content query --uri content://com.homecenter.operatoroverlay.state/state 2>/dev/null || true" 2>&1 || true)"
  if [ -f "$CHROMIUM" ]; then
    chromium="$(python3 "$CHROMIUM" status 2>&1 || true)"
  else
    chromium='{"ok":false,"error":"android_chromium_control.py missing"}'
  fi
  printf '%s\n' "$overlay" > "$STATE/fortress-phone-ops-status.txt"
  printf '%s\n' "$chromium" > "$STATE/fortress-phone-ops-chromium-status.json"
  python3 - "$overlay" "$chromium" <<'PY'
import json,sys,time,socket
overlay,chromium=sys.argv[1:]
try: browser=json.loads(chromium.splitlines()[-1])
except Exception: browser={"ok":False,"raw":chromium[-2000:]}
print(json.dumps({
  "schema":"fortress.phone-ops.status.v2",
  "ok":bool("com.homecenter.operatoroverlay" in overlay and browser.get("ok")),
  "device":socket.gethostname(),
  "atEpoch":int(time.time()),
  "overlay":overlay[-2200:],
  "chromium":browser,
}, sort_keys=True))
PY
}

night_status() {
  [ -f "$NIGHT_STATUS" ] || { json_receipt 0 night-status "fortress_night_status.py missing"; exit 3; }
  exec python3 "$NIGHT_STATUS"
}

home_center_recover() {
  [ -f "$RELAY_RECOVER" ] || { json_receipt 0 home-center-recover "home_center_phone_relay_recover.sh missing"; exit 3; }
  exec bash "$RELAY_RECOVER"
}

overlay_restart() {
  exec bash "$ROOT/tools/recover_adam_overlay_phone.sh"
}

chrome_open() {
  need_chromium_controller chrome-open
  exec python3 "$CHROMIUM" open "${1:-https://chatgpt.com/}"
}

chrome_open_b64() {
  need_chromium_controller chrome-open-b64
  local url
  url="$(decode_url "${1:-}")" || { json_receipt 0 chrome-open-b64 "invalid base64 URL"; exit 64; }
  exec python3 "$CHROMIUM" open "$url"
}

chrome_navigate() {
  need_chromium_controller chrome-navigate
  [ "$#" -ge 1 ] || { json_receipt 0 chrome-navigate "URL required"; exit 64; }
  exec python3 "$CHROMIUM" navigate "$1"
}

chrome_navigate_b64() {
  need_chromium_controller chrome-navigate-b64
  local url
  url="$(decode_url "${1:-}")" || { json_receipt 0 chrome-navigate-b64 "invalid base64 URL"; exit 64; }
  exec python3 "$CHROMIUM" navigate "$url"
}

chrome_reload() {
  need_chromium_controller chrome-reload
  exec python3 "$CHROMIUM" reload
}

chrome_back() {
  need_chromium_controller chrome-back
  exec python3 "$CHROMIUM" back
}

canary() {
  need_chromium_controller canary
  exec python3 "$CHROMIUM" canary
}

help_text() {
  cat <<'EOF'
fortress-phone-ops commands:
  status
  night-status
  home-center-recover
  overlay-restart
  chrome-open [https://url]
  chrome-open-b64 <base64-url>
  chrome-navigate <https://url>
  chrome-navigate-b64 <base64-url>
  chrome-reload
  chrome-back
  canary
EOF
}

op="${1:-help}"; shift || true
case "$op" in
  status) status "$@" ;;
  night-status|night|night-core) night_status "$@" ;;
  home-center-recover|restart-hc|turn-hc-on|restart) home_center_recover "$@" ;;
  overlay-restart|restart-overlay) overlay_restart "$@" ;;
  chrome-open|chrome|chromium) chrome_open "$@" ;;
  chrome-open-b64) chrome_open_b64 "$@" ;;
  chrome-navigate|navigate) chrome_navigate "$@" ;;
  chrome-navigate-b64) chrome_navigate_b64 "$@" ;;
  chrome-reload|reload) chrome_reload "$@" ;;
  chrome-back|back) chrome_back "$@" ;;
  canary|test|chrome-canary) canary "$@" ;;
  help|-h|--help) help_text ;;
  *) json_receipt 0 "$op" "unsupported operation"; help_text >&2; exit 64 ;;
esac
