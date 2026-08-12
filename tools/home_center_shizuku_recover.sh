#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_DIR="${HOME_CENTER_STATE_DIR:-$HOME/.local/state/home-center}"
CONFIG_DIR="${HOME_CENTER_CONFIG_DIR:-$HOME/.config/home-center}"
ENDPOINT_FILE="$CONFIG_DIR/shizuku-adb-endpoint"
LOG="$STATE_DIR/shizuku-recover.log"
SHIZUKU_START="/sdcard/Android/data/moe.shizuku.privileged.api/start.sh"
mkdir -p "$STATE_DIR" "$CONFIG_DIR"
exec > >(tee -a "$LOG") 2>&1

say() { printf '[shizuku-recover] %s\n' "$*"; }

find_rish() {
  if [ -n "${RISH:-}" ] && [ -f "$RISH" ]; then printf '%s\n' "$RISH"; return 0; fi
  if command -v rish >/dev/null 2>&1; then command -v rish; return 0; fi
  for p in "$HOME/rish" "$HOME/bin/rish" "$HOME/.local/bin/rish" \
    "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish" \
    "/storage/emulated/0/Documents/rish" "/storage/emulated/0/Download/rish"; do
    [ -f "$p" ] && { printf '%s\n' "$p"; return 0; }
  done
  return 1
}

probe_rish() {
  local rish_bin
  rish_bin="$(find_rish 2>/dev/null || true)"
  [ -n "$rish_bin" ] || return 1
  chmod +x "$rish_bin" 2>/dev/null || true
  "$rish_bin" -c 'id' >/dev/null 2>&1
}

start_via_target() {
  local target="$1"
  [ -n "$target" ] || return 1
  say "Trying paired ADB target $target"
  adb connect "$target" >/dev/null 2>&1 || true
  adb -s "$target" get-state 2>/dev/null | grep -qx device || return 1
  adb -s "$target" shell "sh '$SHIZUKU_START'" || return 1
  printf '%s\n' "$target" > "$ENDPOINT_FILE"
  sleep 1
  probe_rish
}

say "Checking current Shizuku/rish state"
if probe_rish; then
  say "Shizuku already healthy"
  exit 0
fi

if ! command -v adb >/dev/null 2>&1; then
  say "adb client missing; installing Termux android-tools"
  pkg install -y android-tools
fi

# First reuse the last endpoint that actually worked. This survives ordinary
# Wi-Fi changes when adbd remains alive and the endpoint is localhost-reachable.
if [ -s "$ENDPOINT_FILE" ]; then
  target="$(head -1 "$ENDPOINT_FILE" | tr -d '\r\n')"
  if start_via_target "$target"; then
    say "Recovered Shizuku through remembered ADB endpoint"
    exit 0
  fi
fi

# Reuse any ADB connection Termux already knows about.
while read -r target state _; do
  [ "$state" = device ] || continue
  case "$target" in
    *:*)
      if start_via_target "$target"; then
        say "Recovered Shizuku through existing ADB connection"
        exit 0
      fi
      ;;
  esac
done < <(adb devices | tail -n +2)

# Android 11+ Wireless Debugging advertises a TLS connect service while it is
# available. This avoids hard-coding a Wi-Fi address and also works when the
# service is discoverable locally after a network transition.
if adb mdns services >/dev/null 2>&1; then
  while read -r line; do
    target="$(printf '%s\n' "$line" | sed -nE 's/.*[[:space:]]([^[:space:]]+:[0-9]+)[[:space:]]*$/\1/p')"
    [ -n "$target" ] || continue
    if start_via_target "$target"; then
      say "Recovered Shizuku through mDNS-discovered ADB"
      exit 0
    fi
  done < <(adb mdns services 2>/dev/null | grep '_adb-tls-connect\._tcp' || true)
fi

# Last cheap local attempt: if Android still has adbd listening on a local TCP
# socket, ss exposes the port without requiring us to scan the whole network.
if command -v ss >/dev/null 2>&1; then
  while read -r port; do
    [ -n "$port" ] || continue
    target="127.0.0.1:$port"
    if start_via_target "$target"; then
      say "Recovered Shizuku through localhost adbd"
      exit 0
    fi
  done < <(ss -ltn 2>/dev/null | sed -nE 's/.*[:.]([0-9]{4,5})[[:space:]].*/\1/p' | sort -u)
fi

say "Automatic recovery exhausted. Android has killed or hidden adbd, so an unprivileged Termux process cannot recreate Shizuku by itself."
say "Open Shizuku and start via Wireless debugging (or reconnect USB ADB once), then rerun this script. Pairing should not be required again unless Android revoked it."
say "After recovery, keep Developer options + USB debugging enabled and enable 'Disable adb authorization timeout' to reduce future drops."
exit 2
