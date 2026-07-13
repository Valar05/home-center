#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Documents/GodotProjects/home-center"
cd "$ROOT"

RUN_ID="shizuku-live-playwright-$(date +%Y%m%d%H%M%S)"
CHATGPT_URL="https://chatgpt.com/#settings/Plugins"
CDP_PORT="${HOME_CENTER_CHROME_CDP_PORT:-9222}"
BRIDGE_SRC="$ROOT/tools/chrome_devtools_bridge"
BRIDGE_BIN="/data/local/tmp/home-center-chrome-devtools-bridge"
RISH="${RISH:-$HOME/bin/rish}"
VERIFY_PROMPT=0
WAIT_MS=7000
PROMPT_TIMEOUT_MS=90000
FRAME_MODE=0
FRAME_BOUNDS="${HOME_CENTER_CHROME_FRAME_BOUNDS:-80,220,1040,1780}"
WATCHDOG_PID=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --run-id)
      RUN_ID="$2"
      shift 2
      ;;
    --url)
      CHATGPT_URL="$2"
      shift 2
      ;;
    --verify-prompt)
      VERIFY_PROMPT=1
      shift
      ;;
    --wait-ms)
      WAIT_MS="$2"
      shift 2
      ;;
    --prompt-timeout-ms)
      PROMPT_TIMEOUT_MS="$2"
      shift 2
      ;;
    --frame|--subwindow|--freeform)
      FRAME_MODE=1
      shift
      ;;
    --bounds)
      FRAME_BOUNDS="$2"
      shift 2
      ;;
    --help)
      echo "Usage: sh tools/shizuku_live_playwright_chatgpt_home_center.sh [--run-id ID] [--verify-prompt] [--url URL] [--wait-ms N] [--prompt-timeout-ms N] [--frame] [--bounds L,T,R,B]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

OUT_DIR="$ROOT/tools/chatgpt_connector_evidence/$RUN_ID"
mkdir -p "$OUT_DIR"

if [ ! -f "$RISH" ]; then
  echo "{\"ok\":false,\"status\":\"blocked_local_setup\",\"reason\":\"Shizuku rish not found at $RISH\",\"evidenceDir\":\"$OUT_DIR\"}"
  exit 2
fi

"$RISH" -c "cat > '$BRIDGE_BIN'; chmod 700 '$BRIDGE_BIN'" < "$BRIDGE_SRC"
"$RISH" -c "pkill -f '$BRIDGE_BIN' >/dev/null 2>&1 || true" >/dev/null 2>&1 || true

RESTORE_FRAME_CMD="task_id=\$(dumpsys activity activities | grep -B4 -A8 'com.android.chrome' | grep -o 'Task{[^#]*#[0-9]*' | tail -1 | sed 's/.*#//'); am start -W --display 0 --windowingMode 5 --activity-clear-top -a android.intent.action.VIEW -d '$CHATGPT_URL' com.android.chrome >/dev/null 2>&1 || true; if [ -n \"\$task_id\" ]; then am task resize \"\$task_id\" $FRAME_BOUNDS >/dev/null 2>&1 || true; am task move-to-front \"\$task_id\" >/dev/null 2>&1 || true; fi"

start_frame_watchdog() {
  if [ "$FRAME_MODE" -ne 1 ]; then
    return
  fi
  (
    i=0
    while [ "$i" -lt 180 ]; do
      i=$((i + 1))
      "$RISH" -c "$RESTORE_FRAME_CMD" >> "$OUT_DIR/frame_watchdog.txt" 2>&1 || true
      "$RISH" -c "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|com.android.chrome|com.termux|bounds|bnds' | head -40" >> "$OUT_DIR/frame_watchdog.txt" 2>&1 || true
      sleep 2
    done
  ) &
  WATCHDOG_PID="$!"
}

if [ "$FRAME_MODE" -eq 1 ]; then
  "$RISH" -c "$RESTORE_FRAME_CMD; sleep 1; dumpsys activity activities | grep -E 'RootTask|Task\\{|ActivityRecord|windowingMode|bounds=|bnds=|mFocusedApp|Chrome|Termux' | head -220; dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|com.android.chrome|com.termux|bounds|bnds' | head -120" > "$OUT_DIR/shizuku_launch.txt" 2>&1 || true
  if ! grep -q "com.android.chrome" "$OUT_DIR/shizuku_launch.txt" || ! grep -Eq "windowingMode=freeform|WindowingMode=freeform|windowingMode=5|bnds=\\[[0-9]+,[0-9]+\\]\\[[0-9]+,[0-9]+\\]|bounds=\\[[0-9]+,[0-9]+\\]\\[[0-9]+,[0-9]+\\]" "$OUT_DIR/shizuku_launch.txt"; then
    echo "{\"ok\":false,\"status\":\"blocked_chrome_frame\",\"reason\":\"Chrome did not verify as a bounded/freeform subwindow; refusing fullscreen takeover.\",\"evidenceDir\":\"$OUT_DIR\",\"launchEvidence\":\"$OUT_DIR/shizuku_launch.txt\"}"
    exit 2
  fi
  start_frame_watchdog
else
  "$RISH" -c "am start -W --activity-clear-top -a android.intent.action.VIEW -d '$CHATGPT_URL' com.android.chrome; sleep 1; dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|com.android.chrome|com.termux' | head -80" > "$OUT_DIR/shizuku_launch.txt" 2>&1 || true
fi

timeout 5 "$RISH" -c "nohup '$BRIDGE_BIN' '$CDP_PORT' chrome_devtools_remote > '/sdcard/Documents/GodotProjects/home-center/tools/chatgpt_connector_evidence/$RUN_ID/chrome_devtools_bridge.txt' 2>&1 < /dev/null & echo \$!" > "$OUT_DIR/chrome_devtools_bridge.pid" 2> "$OUT_DIR/chrome_devtools_bridge_start.err" || true
BRIDGE_PID="$(cat "$OUT_DIR/chrome_devtools_bridge.pid" 2>/dev/null | tr -dc '0-9' | head -c 12 || true)"
cleanup() {
  if [ -n "$WATCHDOG_PID" ]; then
    kill "$WATCHDOG_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$BRIDGE_PID" ]; then
    "$RISH" -c "kill '$BRIDGE_PID' >/dev/null 2>&1 || true" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM
sleep 1

if ! curl -sS "http://127.0.0.1:$CDP_PORT/json/version" > "$OUT_DIR/cdp_version.json" 2> "$OUT_DIR/cdp_version.err"; then
  echo "{\"ok\":false,\"status\":\"blocked_chrome_cdp\",\"reason\":\"Android Chrome DevTools socket was not reachable through Shizuku bridge.\",\"evidenceDir\":\"$OUT_DIR\",\"launchEvidence\":\"$OUT_DIR/shizuku_launch.txt\",\"bridgeEvidence\":\"$OUT_DIR/chrome_devtools_bridge.txt\"}"
  exit 2
fi

PW_ARGS="--run-id $RUN_ID-clean --url $CHATGPT_URL --cdp-url http://127.0.0.1:$CDP_PORT --ensure-home-center-connected --wait-ms $WAIT_MS --prompt-timeout-ms $PROMPT_TIMEOUT_MS"
if [ "$VERIFY_PROMPT" -eq 1 ]; then
  PW_ARGS="$PW_ARGS --verify-prompt"
fi

set +e
proot-distro login debian -- sh -lc "
set -eu
cd /storage/emulated/0/Documents/GodotProjects/home-center/browser-worker
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
if [ ! -d node_modules/playwright ]; then npm install --ignore-scripts --no-bin-links >/dev/null; fi
node src/chatgpt_clean_slate_verify.mjs $PW_ARGS
" > "$OUT_DIR/playwright_live_cdp.json" 2> "$OUT_DIR/playwright_live_cdp.err"
PW_STATUS="$?"
set -e

node -e '
const fs = require("fs");
const outDir = process.argv[1];
function readLastJson(file) {
  const text = fs.existsSync(file) ? fs.readFileSync(file, "utf8").trim() : "";
  if (!text) return {};
  try { return JSON.parse(text); } catch (_) {}
  const line = text.split(/\n/).filter((item) => item.trim().startsWith("{")).pop() || "{}";
  return JSON.parse(line);
}
const result = readLastJson(`${outDir}/playwright_live_cdp.json`);
console.log(JSON.stringify({ok: result.ok === true, status: result.status || "unknown", reason: result.reason || "", evidenceDir: outDir, liveAndroidChrome: true, frameMode: process.argv[2] === "1", frameWatchdog: process.argv[2] === "1", playwright: result}, null, 2));
' "$OUT_DIR" "$FRAME_MODE"
exit "$PW_STATUS"
