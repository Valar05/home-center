#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="${HC_VENICE_BRANCH:-feat/venice-radio-overlay-controls}"
REPO="${HC_REPO:-Valar05/home-center}"
ROOT="${HC_ROOT:-/storage/emulated/0/Documents/GodotProjects/home-center}"
STATE="$HOME/.local/state/home-center"
DL="$HOME/storage/downloads"
APK="$DL/home-center-operator-overlay-venice-radio.apk"
TMP="$PREFIX/tmp/venice-radio-handoff"
PKG="com.homecenter.operatoroverlay"
mkdir -p "$STATE" "$DL" "$TMP"

say(){ printf '[venice-radio-handoff] %s\n' "$*"; }
fail(){ say "BLOCKED: $*"; exit 2; }

command -v git >/dev/null 2>&1 || fail "git missing"
command -v gh >/dev/null 2>&1 || fail "gh missing"
command -v am >/dev/null 2>&1 || fail "Android activity manager unavailable; run in Termux"

say "Refreshing commissioned branch"
cd "$ROOT"
git fetch origin "$BRANCH"

RUN_ID="$(gh run list --repo "$REPO" --workflow 'Operator Overlay Android' --branch "$BRANCH" --limit 20 --json databaseId,conclusion,event --jq '[.[] | select(.conclusion=="success")][0].databaseId // empty' 2>/dev/null || true)"
if [ -n "$RUN_ID" ]; then
  rm -rf "$TMP/artifact"
  mkdir -p "$TMP/artifact"
  if gh run download "$RUN_ID" --repo "$REPO" -n venice-radio-operator-overlay-apk -D "$TMP/artifact" >/dev/null 2>&1; then
    CANDIDATE="$(find "$TMP/artifact" -type f -name '*.apk' | head -1 || true)"
    if [ -n "$CANDIDATE" ] && [ -s "$CANDIDATE" ]; then
      cp "$CANDIDATE" "$APK"
      say "Recovered CI-built APK from run $RUN_ID"
    fi
  fi
fi

if [ ! -s "$APK" ]; then
  say "No usable CI artifact yet; checking reviewed generated artifact branch"
  if git fetch origin generated/operator-overlay-apk >/dev/null 2>&1; then
    if git show FETCH_HEAD:operator-overlay-debug.apk > "$APK.part" 2>/dev/null && \
       git show FETCH_HEAD:operator-overlay-receipt.json > "$TMP/receipt.json" 2>/dev/null; then
      EXPECTED="$(python - "$TMP/receipt.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
print(x.get('sha256',''))
PY
)"
      ACTUAL="$(sha256sum "$APK.part" | awk '{print $1}')"
      SOURCE="$(python - "$TMP/receipt.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
print(x.get('sourceCommit',''))
PY
)"
      HEAD="$(git rev-parse "origin/$BRANCH")"
      if [ -n "$EXPECTED" ] && [ "$EXPECTED" = "$ACTUAL" ] && [ -n "$SOURCE" ] && git merge-base --is-ancestor "$SOURCE" "$HEAD" 2>/dev/null; then
        mv "$APK.part" "$APK"
        say "Using reviewed generated APK sha256=$ACTUAL source=$SOURCE"
      else
        rm -f "$APK.part"
      fi
    fi
  fi
fi

if [ ! -s "$APK" ]; then
  say "No current built APK is available yet. Creating an exact handoff receipt and stopping before installation."
  cat > "$STATE/venice-radio-overlay-handoff.json" <<JSON
{"status":"build_required","branch":"$BRANCH","head":"$(git rev-parse "origin/$BRANCH")","requiredArtifact":"venice-radio-operator-overlay-apk","shizukuRequired":false}
JSON
  fail "APK build is the only remaining machine-side boundary. Shizuku is NOT required. Re-run this same script after the workstation/CI builder publishes the artifact."
fi

SHA="$(sha256sum "$APK" | awk '{print $1}')"
BYTES="$(wc -c < "$APK")"
say "APK ready sha256=$SHA bytes=$BYTES"

URI="content://com.termux.fileprovider$(python - "$APK" <<'PY'
import sys,urllib.parse
print(urllib.parse.quote(sys.argv[1], safe='/'))
PY
)"
am start -a android.intent.action.VIEW -d "$URI" -t application/vnd.android.package-archive --grant-read-uri-permission >/dev/null 2>&1 || \
am start -a android.intent.action.VIEW -d "file://$APK" -t application/vnd.android.package-archive >/dev/null 2>&1 || \
fail "Could not launch Android package installer"

say "ANDROID GATE: approve Install/Update for Home Center Operator Overlay. Waiting for package..."
for _ in $(seq 1 120); do
  pm path "$PKG" >/dev/null 2>&1 && break
  sleep 1
done
pm path "$PKG" >/dev/null 2>&1 || fail "package was not installed within 120 seconds"

am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:$PKG" >/dev/null 2>&1 || true
say "ANDROID GATE: enable 'Display over other apps' for Home Center Operator Overlay. Waiting..."
for _ in $(seq 1 120); do
  if appops get "$PKG" SYSTEM_ALERT_WINDOW 2>/dev/null | grep -Eq 'allow|foreground'; then break; fi
  sleep 1
done
appops get "$PKG" SYSTEM_ALERT_WINDOW 2>/dev/null | grep -Eq 'allow|foreground' || fail "overlay permission was not granted within 120 seconds"

am start -n "$PKG/.MainActivity" >/dev/null 2>&1 || true
sleep 1
am start-foreground-service -n "$PKG/.OperatorOverlayService" >/dev/null 2>&1 || true
sleep 2

STATE_ROW="$(content query --uri content://com.homecenter.operatoroverlay.state/state 2>&1 || true)"
printf '%s\n' "$STATE_ROW"
if printf '%s' "$STATE_ROW" | grep -q 'control_enabled='; then
  cat > "$STATE/venice-radio-overlay-handoff.json" <<JSON
{"status":"installed","branch":"$BRANCH","head":"$(git rev-parse "origin/$BRANCH")","apkSha256":"$SHA","apkBytes":$BYTES,"package":"$PKG","shizukuRequired":false}
JSON
  say "DONE: overlay installed and state provider readable. Venice Radio controls are on the Home Center overlay."
else
  fail "package installed, but overlay state provider is not readable"
fi
