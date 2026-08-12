#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
CONFIG_DIR="${HOME}/.config/home-center"
ENV_FILE="${HC_PHONE_HANDS_ENV_FILE:-$CONFIG_DIR/phone-hands.env}"
PORT="${HC_PHONE_HANDS_PORT:-8787}"
ENABLE_SHELL=0
BACKGROUND=0

for arg in "$@"; do
  case "$arg" in
    --shell) ENABLE_SHELL=1 ;;
    --background) BACKGROUND=1 ;;
    --help|-h)
      cat <<'EOF'
Usage: tools/start_android_phone_hands.sh [--shell] [--background]

Starts the Home Center Android Phone Hands service in Termux.
The service accepts only Tailscale-address-space peers and requires a bearer
secret stored locally under ~/.config/home-center. Secrets are never written
into the repository or Drive.

  --shell       explicitly enable arbitrary Android-shell actions
  --background  launch under nohup and write ~/.config/home-center/phone-hands.pid
EOF
      exit 0
      ;;
  esac
done

mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR" 2>/dev/null || true

find_rish() {
  if [ -n "${RISH:-}" ] && [ -f "$RISH" ]; then printf '%s\n' "$RISH"; return 0; fi
  if command -v rish >/dev/null 2>&1; then command -v rish; return 0; fi
  for candidate in "$HOME/bin/rish" "$HOME/rish" "$HOME/.local/bin/rish" \
    "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish" \
    "/storage/emulated/0/Documents/rish" "/storage/emulated/0/Download/rish"; do
    [ -f "$candidate" ] && { printf '%s\n' "$candidate"; return 0; }
  done
  return 1
}

RISH_BIN="$(find_rish 2>/dev/null || true)"
[ -n "$RISH_BIN" ] || { echo "BLOCKED: rish not found. Export rish from Shizuku into Termux." >&2; exit 2; }
chmod +x "$RISH_BIN" 2>/dev/null || true

# Android shared storage is commonly mounted noexec. Never infer that chmod makes
# a shared-storage rish directly executable; run it through Termux sh instead.
rish_exec() {
  case "$RISH_BIN" in
    /storage/*) sh "$RISH_BIN" "$@" ;;
    *) "$RISH_BIN" "$@" ;;
  esac
}

if ! rish_exec -c 'id; dumpsys window 2>/dev/null | grep -E "mCurrentFocus|mFocusedApp" | head -1' >/dev/null 2>&1; then
  echo "BLOCKED: Shizuku/rish probe failed. Start Shizuku and authorize Termux." >&2
  exit 3
fi

if ! rish_exec -c 'pm list packages 2>/dev/null | grep -i tailscale' | grep -q 'package:'; then
  echo "BLOCKED: Tailscale Android app was not found through Android package state." >&2
  exit 4
fi

if [ ! -f "$ENV_FILE" ]; then
  TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
  umask 077
  cat > "$ENV_FILE" <<EOF
HC_PHONE_HANDS_TOKEN='$TOKEN'
HC_PHONE_HANDS_PORT='$PORT'
HC_PHONE_HANDS_ALLOW_SHELL='0'
EOF
  chmod 600 "$ENV_FILE"
  echo "Created local Phone Hands secret at $ENV_FILE"
fi

# shellcheck disable=SC1090
. "$ENV_FILE"
export HC_PHONE_HANDS_TOKEN
export HC_PHONE_HANDS_PORT="${HC_PHONE_HANDS_PORT:-$PORT}"

# The Python bridge launches RISH as an executable. When Shizuku exported rish
# to shared storage, give the bridge an executable wrapper in Termux internal
# storage so the noexec mount cannot break runtime commands after startup.
case "$RISH_BIN" in
  /storage/*)
    RISH_WRAPPER="$CONFIG_DIR/rish-wrapper"
    cat > "$RISH_WRAPPER" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec sh "$RISH_SHARED_PATH" "$@"
EOF
    chmod 700 "$RISH_WRAPPER"
    export RISH_SHARED_PATH="$RISH_BIN"
    export RISH="$RISH_WRAPPER"
    ;;
  *)
    export RISH="$RISH_BIN"
    ;;
esac

if [ "$ENABLE_SHELL" = "1" ]; then
  export HC_PHONE_HANDS_ALLOW_SHELL=1
else
  export HC_PHONE_HANDS_ALLOW_SHELL="${HC_PHONE_HANDS_ALLOW_SHELL:-0}"
fi

BRIDGE="$ROOT/tools/android_phone_hands_bridge.py"
[ -f "$BRIDGE" ] || { echo "BLOCKED: $BRIDGE is missing" >&2; exit 5; }

TAILSCALE_STATE="$(rish_exec -c 'dumpsys connectivity 2>/dev/null | grep -i tailscale | head -4' 2>/dev/null || true)"
if [ -z "$TAILSCALE_STATE" ]; then
  echo "WARNING: Tailscale package exists, but active VPN state could not be proven from dumpsys."
  echo "Open Tailscale and make sure this phone is connected before remote verification."
fi

if [ "$BACKGROUND" = "1" ]; then
  LOG="$CONFIG_DIR/phone-hands.log"
  PIDFILE="$CONFIG_DIR/phone-hands.pid"
  nohup python "$BRIDGE" >>"$LOG" 2>&1 &
  PID=$!
  printf '%s\n' "$PID" > "$PIDFILE"
  chmod 600 "$PIDFILE"
  sleep 1
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "BLOCKED: Phone Hands exited during startup. Read $LOG" >&2
    exit 6
  fi
  echo "Phone Hands running: pid=$PID port=$HC_PHONE_HANDS_PORT log=$LOG"
else
  exec python "$BRIDGE"
fi
