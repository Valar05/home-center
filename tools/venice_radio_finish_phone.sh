#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="${HC_ROOT:-/storage/emulated/0/Documents/GodotProjects/home-center}"
SOURCE_BRANCH="${VENICE_RADIO_BRANCH:-feat/venice-radio-internet-transport-v2}"
APK_BRANCH="${VENICE_OVERLAY_APK_BRANCH:-generated/venice-radio-overlay-apk}"
PKG="com.homecenter.operatoroverlay"
STATE="$HOME/.local/state/home-center/venice-radio"
DL="$HOME/storage/downloads"
APK="$DL/home-center-operator-overlay-venice-radio.apk"
RECEIVER="$PREFIX/tmp/venice-radio-phone-receiver.sh"
mkdir -p "$STATE" "$DL"
log(){ printf '[venice-radio-finish] %s\n' "$*"; }

cd "$REPO_ROOT"
log 'fetching reviewed overlay artifact'
git fetch origin "$APK_BRANCH"
git show FETCH_HEAD:operator-overlay-receipt.json > "$PREFIX/tmp/venice-overlay-receipt.json"
git show FETCH_HEAD:operator-overlay-debug.apk > "$APK"
EXP="$(python - "$PREFIX/tmp/venice-overlay-receipt.json" <<'PY'
import json,sys; print(json.load(open(sys.argv[1]))['sha256'])
PY
)"
ACT="$(sha256sum "$APK" | awk '{print $1}')"
[ "$EXP" = "$ACT" ] || { log "APK hash mismatch expected=$EXP actual=$ACT"; exit 42; }
log "APK verified sha256=$ACT bytes=$(wc -c < "$APK")"

if ! pm path "$PKG" >/dev/null 2>&1; then
  termux-open "$APK" >/dev/null 2>&1 || true
  am start -a android.intent.action.VIEW -d "file://$APK" -t application/vnd.android.package-archive >/dev/null 2>&1 || true
  log 'ANDROID GATE: approve Install/Update; waiting'
  for _ in $(seq 1 180); do pm path "$PKG" >/dev/null 2>&1 && break; sleep 1; done
fi
pm path "$PKG" >/dev/null 2>&1 || { log 'waiting_for_install_approval'; exit 43; }
log 'package installed'

if ! appops get "$PKG" SYSTEM_ALERT_WINDOW 2>/dev/null | grep -Eq 'allow|foreground'; then
  am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:$PKG" >/dev/null 2>&1 || \
  am start -a android.settings.MANAGE_OVERLAY_PERMISSION -d "package:$PKG" >/dev/null 2>&1 || true
  log "ANDROID GATE: enable Display over other apps; waiting"
  for _ in $(seq 1 180); do appops get "$PKG" SYSTEM_ALERT_WINDOW 2>/dev/null | grep -Eq 'allow|foreground' && break; sleep 1; done
fi
appops get "$PKG" SYSTEM_ALERT_WINDOW 2>/dev/null | grep -Eq 'allow|foreground' || { log 'waiting_for_overlay_permission'; exit 44; }
log 'overlay permission granted'

am start -n "$PKG/.MainActivity" >/dev/null 2>&1 || true
sleep 1
am start-foreground-service -n "$PKG/.OperatorOverlayService" >/dev/null 2>&1 || true
sleep 2

log 'fetching live radio receiver'
git fetch origin "$SOURCE_BRANCH"
git show FETCH_HEAD:tools/venice_radio_phone_receiver.sh > "$RECEIVER"
chmod +x "$RECEIVER"
rm -f "$STATE/STOP"
pkill -f 'venice_radio_phone_receiver.sh' >/dev/null 2>&1 || true
nohup "$RECEIVER" >> "$STATE/receiver-nohup.log" 2>&1 </dev/null &
echo $! > "$STATE/receiver.pid"
log "receiver pid=$(cat "$STATE/receiver.pid")"

for _ in $(seq 1 90); do
  if [ -s "$STATE/receiver.json" ] && python - "$STATE/receiver.json" <<'PY' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1])); raise SystemExit(0 if x.get('status')=='playing' and int(x.get('lastSequence') or 0)>0 else 1)
PY
  then break; fi
  sleep 1
done

[ -s "$STATE/receiver.json" ] || { log 'receiver state missing'; tail -80 "$STATE/receiver-nohup.log" 2>/dev/null || true; exit 45; }
cat "$STATE/receiver.json"
INFO="$(termux-media-player info 2>/dev/null || true)"
printf '%s\n' "$INFO"
printf '%s' "$INFO" | grep -qi 'Status: Playing' || { log 'receiver not playing'; tail -80 "$STATE/receiver-nohup.log" 2>/dev/null || true; exit 46; }
OVERLAY_STATE="$(content query --uri content://com.homecenter.operatoroverlay.state/state 2>&1 || true)"
printf '%s\n' "$OVERLAY_STATE"
log 'DONE: overlay installed, receiver playing, media controls live'
