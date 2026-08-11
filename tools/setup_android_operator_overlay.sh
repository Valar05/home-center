#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PACKAGE="com.homecenter.operatoroverlay"
ARTIFACT_BRANCH="${HC_OPERATOR_OVERLAY_ARTIFACT_BRANCH:-generated/operator-overlay-apk}"
OUT="${HC_OPERATOR_OVERLAY_APK:-$HOME/storage/downloads/home-center-operator-overlay.apk}"
RECEIPT="$HOME/.local/state/home-center/operator-overlay-build-receipt.json"
STATE="$HOME/.local/state/home-center"
STAGED="/data/local/tmp/home-center-operator-overlay.apk"
mkdir -p "$STATE" "$(dirname "$OUT")"

RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"
[ -x "$RISH_BIN" ] || { echo 'BLOCKED: rish missing; Shizuku authority is required.' >&2; exit 2; }

cd "$ROOT"
echo '[1/7] Fetching reviewed overlay build artifact'
git fetch origin "$ARTIFACT_BRANCH"
git show "origin/$ARTIFACT_BRANCH:operator-overlay-debug.apk" > "$OUT.part"
git show "origin/$ARTIFACT_BRANCH:operator-overlay-receipt.json" > "$RECEIPT"
mv "$OUT.part" "$OUT"

EXPECTED="$(python - "$RECEIPT" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding='utf-8'))['sha256'])
PY
)"
ACTUAL="$(sha256sum "$OUT" | awk '{print $1}')"
[ "$ACTUAL" = "$EXPECTED" ] || { echo "BLOCKED: APK SHA mismatch expected=$EXPECTED actual=$ACTUAL" >&2; exit 3; }

REAL_OUT="$(readlink -f "$OUT")"
[ -n "$REAL_OUT" ] && [ -f "$REAL_OUT" ] || { echo "BLOCKED: resolved APK path missing: $REAL_OUT" >&2; exit 4; }

echo '[2/7] Staging APK where Android system_server can read it'
STAGED_SHA="$("$RISH_BIN" -c "set -e; cp '$REAL_OUT' '$STAGED'; chmod 644 '$STAGED'; sha256sum '$STAGED'" 2>&1 | grep -Eo '[0-9a-f]{64}' | tail -1)"
[ "$STAGED_SHA" = "$EXPECTED" ] || { echo "BLOCKED: staged APK SHA mismatch expected=$EXPECTED actual=$STAGED_SHA" >&2; exit 5; }

echo '[3/7] Installing overlay APK through Shizuku shell'
INSTALL_OUT="$("$RISH_BIN" -c "pm install -r '$STAGED'" 2>&1)"
printf '%s\n' "$INSTALL_OUT" | tee "$STATE/operator-overlay-install.txt"
printf '%s\n' "$INSTALL_OUT" | grep -qx 'Success' || { echo 'BLOCKED: Android package install did not return Success.' >&2; exit 6; }

echo '[4/7] Granting only the user-visible overlay app-op'
"$RISH_BIN" -c "appops set $PACKAGE SYSTEM_ALERT_WINDOW allow"
"$RISH_BIN" -c "pm grant $PACKAGE android.permission.POST_NOTIFICATIONS 2>/dev/null || true"

echo '[5/7] Starting persistent operator overlay'
"$RISH_BIN" -c "am start-foreground-service -n $PACKAGE/.OperatorOverlayService >/dev/null 2>&1 || am start -n $PACKAGE/.MainActivity >/dev/null"
sleep 2

echo '[6/7] Verifying package, app-op, and user-owned state'
VERIFY="$("$RISH_BIN" -c "pm list packages $PACKAGE; appops get $PACKAGE SYSTEM_ALERT_WINDOW; content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1)"
printf '%s\n' "$VERIFY" | tee "$STATE/operator-overlay-state.txt"
printf '%s\n' "$VERIFY" | grep -q "package:$PACKAGE" || { echo 'BLOCKED: installed package not visible.' >&2; exit 7; }
printf '%s\n' "$VERIFY" | grep -q 'SYSTEM_ALERT_WINDOW: allow' || { echo 'BLOCKED: overlay app-op not allowed.' >&2; exit 8; }
printf '%s\n' "$VERIFY" | grep -q 'control_enabled=' || { echo 'BLOCKED: operator state provider unreadable.' >&2; exit 9; }

echo '[7/7] Cleaning privileged staging file'
"$RISH_BIN" -c "rm -f '$STAGED'" || true

echo
cat "$RECEIPT"
echo
printf 'OPERATOR OVERLAY INSTALLED sha256=%s apk=%s\n' "$ACTUAL" "$REAL_OUT"
