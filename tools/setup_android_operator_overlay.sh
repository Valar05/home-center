#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PACKAGE="com.homecenter.operatoroverlay"
ARTIFACT_BRANCH="${HC_OPERATOR_OVERLAY_ARTIFACT_BRANCH:-generated/operator-overlay-apk}"
OUT="${HC_OPERATOR_OVERLAY_APK:-$HOME/storage/downloads/home-center-operator-overlay.apk}"
RECEIPT="$HOME/.local/state/home-center/operator-overlay-build-receipt.json"
STATE="$HOME/.local/state/home-center"
mkdir -p "$STATE" "$(dirname "$OUT")"

RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"
[ -x "$RISH_BIN" ] || { echo 'BLOCKED: rish missing; Shizuku authority is required.' >&2; exit 2; }

cd "$ROOT"
echo '[1/6] Fetching reviewed overlay build artifact'
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

echo '[2/6] Installing overlay APK through Shizuku shell'
"$RISH_BIN" -c "pm install -r '$OUT'" | tee "$STATE/operator-overlay-install.txt"

echo '[3/6] Granting only the user-visible overlay app-op'
"$RISH_BIN" -c "appops set $PACKAGE SYSTEM_ALERT_WINDOW allow"
"$RISH_BIN" -c "pm grant $PACKAGE android.permission.POST_NOTIFICATIONS 2>/dev/null || true"

echo '[4/6] Starting persistent operator overlay'
"$RISH_BIN" -c "am start-foreground-service -n $PACKAGE/.OperatorOverlayService >/dev/null 2>&1 || am start -n $PACKAGE/.MainActivity >/dev/null"

sleep 2

echo '[5/6] Verifying package and overlay permission'
"$RISH_BIN" -c "pm path $PACKAGE; appops get $PACKAGE SYSTEM_ALERT_WINDOW"

echo '[6/6] Reading user-owned control state'
"$RISH_BIN" -c "content query --uri content://com.homecenter.operatoroverlay.state/state" | tee "$STATE/operator-overlay-state.txt"

echo
cat "$RECEIPT"
echo
printf 'OPERATOR OVERLAY INSTALLED sha256=%s apk=%s\n' "$ACTUAL" "$OUT"
