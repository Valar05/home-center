#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_DIR="${HOME_CENTER_STATE_DIR:-$HOME/.local/state/home-center}"
CONFIG_DIR="${HOME_CENTER_CONFIG_DIR:-$HOME/.config/home-center}"
ENDPOINT_FILE="$CONFIG_DIR/shizuku-adb-endpoint"
LOG="$STATE_DIR/shizuku-recover.log"
SHIZUKU_START="/sdcard/Android/data/moe.shizuku.privileged.api/start.sh"
WAIT_SECONDS="${HC_SHIZUKU_RECOVER_WAIT_SECONDS:-90}"
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

try_adb_targets() {
  local target state line port
  if [ -s "$ENDPOINT_FILE" ]; then
    target="$(head -1 "$ENDPOINT_FILE" | tr -d '\r\n')"
    start_via_target "$target" && return 0
  fi

  while read -r target state _; do
    [ "$state" = device ] || continue
    case "$target" in
      *:*) start_via_target "$target" && return 0 ;;
    esac
  done < <(adb devices | tail -n +2)

  if adb mdns services >/dev/null 2>&1; then
    while read -r line; do
      target="$(printf '%s\n' "$line" | sed -nE 's/.*[[:space:]]([^[:space:]]+:[0-9]+)[[:space:]]*$/\1/p')"
      [ -n "$target" ] || continue
      start_via_target "$target" && return 0
    done < <(adb mdns services 2>/dev/null | grep '_adb-tls-connect\._tcp' || true)
  fi

  if command -v ss >/dev/null 2>&1; then
    while read -r port; do
      [ -n "$port" ] || continue
      start_via_target "127.0.0.1:$port" && return 0
    done < <(ss -ltn 2>/dev/null | sed -nE 's/.*[:.]([0-9]{4,5})[[:space:]].*/\1/p' | sort -u)
  fi
  return 1
}

open_wireless_debugging_gate() {
  say "Android hid adbd. Opening Wireless debugging so the only required human action is the system toggle."
  # Pixel/AOSP builds commonly resolve this direct action; fall back to the
  # required platform Developer options action when they do not.
  if am start -a android.settings.WIRELESS_DEBUGGING_SETTINGS >/dev/null 2>&1; then
    return 0
  fi
  am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS >/dev/null 2>&1 || return 1
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

if try_adb_targets; then
  say "Recovered Shizuku automatically"
  exit 0
fi

open_wireless_debugging_gate || true
say "Waiting up to ${WAIT_SECONDS}s for Wireless debugging/adbd to reappear. Turn Wireless debugging ON if Android shows it off; no same-Wi-Fi requirement is being imposed by Home Center."
deadline=$((SECONDS + WAIT_SECONDS))
while [ "$SECONDS" -lt "$deadline" ]; do
  if probe_rish; then
    say "Shizuku became healthy"
    exit 0
  fi
  if try_adb_targets; then
    say "Recovered Shizuku after Android debugging gate reopened"
    exit 0
  fi
  sleep 2
done

say "Still blocked at Android's privilege boundary: Wireless debugging/adbd did not become reachable before timeout."
say "Leave this script running while you enable Wireless debugging, or rerun it afterward. Pairing should not be required unless Android revoked the pairing."
exit 2
