#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

APK="${1:-$HOME/storage/downloads/home-center-operator-overlay-venice-radio.apk}"
PKG="com.homecenter.operatoroverlay"
STATE="${HOME_CENTER_STATE_DIR:-$HOME/.local/state/home-center}"
mkdir -p "$STATE"

say(){ printf '[overlay-userland] %s\n' "$*"; }

if [ ! -s "$APK" ]; then
  say "APK missing: $APK"
  exit 2
fi

SHA="$(sha256sum "$APK" | awk '{print $1}')"
BYTES="$(wc -c < "$APK" | tr -d ' ')"
printf '{"apk":"%s","sha256":"%s","byteCount":%s,"requestedAt":"%s"}\n' \
  "$APK" "$SHA" "$BYTES" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "$STATE/operator-overlay-userland-install-request.json"

say "Launching Android package installer for verified local APK"
if command -v termux-open >/dev/null 2>&1; then
  termux-open --view "$APK" >/dev/null 2>&1 || true
else
  am start -a android.intent.action.VIEW \
    -d "file://$APK" -t application/vnd.android.package-archive >/dev/null 2>&1 || true
fi

say "Waiting for package installation"
for _ in $(seq 1 120); do
  if pm path "$PKG" >/dev/null 2>&1; then
    say "Package installed"
    break
  fi
  sleep 1
done

if ! pm path "$PKG" >/dev/null 2>&1; then
  say "Android package installer still needs the Install confirmation. Leave this script running and confirm it."
  exit 3
fi

say "Opening Android overlay permission for Home Center"
am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:$PKG" >/dev/null 2>&1 || \
  am start -a android.settings.MANAGE_OVERLAY_PERMISSION -d "package:$PKG" >/dev/null 2>&1 || true

say "Waiting for overlay permission"
for _ in $(seq 1 120); do
  if appops get "$PKG" SYSTEM_ALERT_WINDOW 2>/dev/null | grep -q 'allow'; then
    say "Overlay permission granted"
    break
  fi
  sleep 1
done

if ! appops get "$PKG" SYSTEM_ALERT_WINDOW 2>/dev/null | grep -q 'allow'; then
  say "Android still needs the 'Display over other apps' toggle. Leave this script running and enable it."
  exit 4
fi

say "Starting Home Center operator overlay without Shizuku"
am start -n "$PKG/.MainActivity" >/dev/null 2>&1 || true
sleep 2

if pm path "$PKG" >/dev/null 2>&1; then
  printf '{"ok":true,"package":"%s","sha256":"%s","installedAt":"%s"}\n' \
    "$PKG" "$SHA" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "$STATE/operator-overlay-userland-install-receipt.json"
  say "READY package=$PKG sha256=$SHA"
  exit 0
fi

say "Install verification failed"
exit 5
