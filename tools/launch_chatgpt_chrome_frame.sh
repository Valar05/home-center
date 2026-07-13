#!/data/data/com.termux/files/usr/bin/sh
set -eu

URL="${1:-https://chatgpt.com/}"
RUN_ID="${RUN_ID:-chatgpt-frame-$(date +%Y%m%d%H%M%S)}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$REPO_ROOT/tools/chatgpt_connector_evidence"
OUT="$OUT_DIR/chrome_frame_${RUN_ID}.txt"
RISH="${RISH:-$HOME/bin/rish}"

finish() {
  code="$1"
  status="$2"
  message="$3"
  {
    echo "status=$status"
    echo "exitCode=$code"
    echo "finishedAt=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >> "$OUT"
  node "$REPO_ROOT/tools/chrome_frame_learning_envelope.mjs" --evidence "$OUT" --run-id "$RUN_ID" --url "$URL" --status "$status" --out-dir "$OUT_DIR" >> "$OUT" 2>&1 || true
  printf '%s\nEvidence: %s\nLearning: %s\n' "$message" "$OUT" "$OUT_DIR/chrome_frame_${RUN_ID}.learning.json"
  exit "$code"
}

mkdir -p "$OUT_DIR"

if [ ! -f "$RISH" ]; then
  echo "blocked_local_setup: Shizuku rish not found at $RISH" > "$OUT"
  finish 2 "blocked_local_setup" "Shizuku rish not found."
fi

echo "runId=$RUN_ID" > "$OUT"
echo "url=$URL" >> "$OUT"
echo "rule=bounded_chrome_frame_only" >> "$OUT"

# Prefer a freeform task with explicit bounds. If the device ignores these flags,
# the verification below refuses success.
"$RISH" -c "am start -W --display 0 --windowingMode 5 --activity-clear-top -a android.intent.action.VIEW -d '$URL' com.android.chrome" >> "$OUT" 2>&1 || true
sleep 1

"$RISH" -c "dumpsys activity activities | grep -E 'RootTask|Task\\{|ActivityRecord|mActivityComponent|windowingMode|bounds=|bnds=|topResumedActivity|mFocusedApp|Chrome|Termux' | head -220" >> "$OUT" 2>&1 || true

if grep -q "com.android.chrome" "$OUT" && grep -Eq "windowingMode=freeform|WindowingMode=freeform|windowingMode=5|bnds=\\[[0-9]+,[0-9]+\\]\\[[0-9]+,[0-9]+\\]|bounds=\\[[0-9]+,[0-9]+\\]\\[[0-9]+,[0-9]+\\]" "$OUT"; then
  "$RISH" -c "am start --display 0 --activity-reorder-to-front -n com.termux/.app.TermuxActivity" >> "$OUT" 2>&1 || true
  sleep 1
  "$RISH" -c "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|com.android.chrome|com.termux|bounds|bnds' | head -120" >> "$OUT" 2>&1 || true
  finish 0 "bounded_frame_active" "Chrome bounded frame is active or preserved."
fi

finish 1 "not_verified_bounded" "Chrome did not verify as a bounded/freeform frame. I am not treating this as acceptable."
