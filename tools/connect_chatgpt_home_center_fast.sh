#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Documents/GodotProjects/home-center"
cd "$ROOT"

RUN_ID="chatgpt-home-center-fast-$(date +%Y%m%d%H%M%S)"
VERIFY_PROMPT=0
WAIT_MS=7000
PROMPT_TIMEOUT_MS=90000
FALLBACK_HEADLESS=0
FRAME_MODE=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --run-id)
      RUN_ID="$2"
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
    --allow-headless-fallback)
      FALLBACK_HEADLESS=1
      shift
      ;;
    --fullscreen)
      FRAME_MODE=0
      shift
      ;;
    --frame|--subwindow|--freeform)
      FRAME_MODE=1
      shift
      ;;
    --help)
      echo "Usage: sh tools/connect_chatgpt_home_center_fast.sh [--run-id ID] [--verify-prompt] [--wait-ms N] [--prompt-timeout-ms N] [--frame|--fullscreen] [--allow-headless-fallback]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

EVIDENCE_DIR="tools/chatgpt_connector_evidence/$RUN_ID"
mkdir -p "$EVIDENCE_DIR"

node tools/command_center_home_bridge_invokability_gate.mjs --json --run-id "$RUN_ID-home" > "$EVIDENCE_DIR/backend_home_bridge.json"

LIVE_ARGS="--run-id $RUN_ID-live --wait-ms $WAIT_MS --prompt-timeout-ms $PROMPT_TIMEOUT_MS"
if [ "$FRAME_MODE" -eq 1 ]; then
  LIVE_ARGS="$LIVE_ARGS --frame"
fi
if [ "$VERIFY_PROMPT" -eq 1 ]; then
  LIVE_ARGS="$LIVE_ARGS --verify-prompt"
fi

set +e
sh tools/shizuku_live_playwright_chatgpt_home_center.sh $LIVE_ARGS > "$EVIDENCE_DIR/shizuku_live_playwright.json"
PW_STATUS=$?
set -e

if [ "$PW_STATUS" -eq 0 ]; then
  node -e '
const fs = require("fs");
const path = process.argv[1];
const raw = fs.readFileSync(path, "utf8").trim();
const parsed = JSON.parse(raw);
console.log(JSON.stringify({ok:true,status:parsed.status || "ok",evidenceDir:process.argv[2],playwright:parsed}, null, 2));
' "$EVIDENCE_DIR/shizuku_live_playwright.json" "$EVIDENCE_DIR"
  exit 0
fi

STATUS="$(node -e '
const fs = require("fs");
const raw = fs.readFileSync(process.argv[1], "utf8").trim() || "{}";
let parsed = {};
try { parsed = JSON.parse(raw); } catch (_) {}
console.log(parsed.status || "");
' "$EVIDENCE_DIR/shizuku_live_playwright.json")"

if [ "$FALLBACK_HEADLESS" -eq 1 ]; then
  set +e
  PW_ARGS="--run-id $RUN_ID-clean --wait-ms $WAIT_MS --prompt-timeout-ms $PROMPT_TIMEOUT_MS --ensure-home-center-connected"
  if [ "$VERIFY_PROMPT" -eq 1 ]; then
    PW_ARGS="$PW_ARGS --verify-prompt"
  fi
  sh tools/run_chatgpt_clean_slate_verify.sh $PW_ARGS > "$EVIDENCE_DIR/headless_playwright_fallback.json"
  HEADLESS_STATUS=$?
  set -e
  node -e '
const fs = require("fs");
const evidenceDir = process.argv[1];
function readJson(file) {
  const text = fs.existsSync(file) ? fs.readFileSync(file, "utf8").trim() : "{}";
  if (!text) return {};
  try { return JSON.parse(text); } catch (_) {}
  const line = text.split(/\n/).filter((item) => item.trim().startsWith("{")).pop() || "{}";
  return JSON.parse(line);
}
console.log(JSON.stringify({ok:false,status:"headless_fallback_ran",evidenceDir,livePlaywright:readJson(`${evidenceDir}/shizuku_live_playwright.json`),headlessFallback:readJson(`${evidenceDir}/headless_playwright_fallback.json`)}, null, 2));
' "$EVIDENCE_DIR"
  exit "$HEADLESS_STATUS"
fi

node -e '
const fs = require("fs");
const evidenceDir = process.argv[1];
const raw = fs.readFileSync(`${evidenceDir}/shizuku_live_playwright.json`, "utf8").trim() || "{}";
const parsed = JSON.parse(raw);
console.log(JSON.stringify({ok:false,status:parsed.status || "failed",reason:parsed.reason || "",evidenceDir,livePlaywright:parsed,nextAction:parsed.nextAction || "Inspect live Shizuku Playwright evidence and update connector selector ladder."}, null, 2));
' "$EVIDENCE_DIR"
exit "$PW_STATUS"
