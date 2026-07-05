#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
APK="${1:-$ROOT/app/build/outputs/apk/debug/app-debug.apk}"
REMOTE_APK="/data/local/tmp/HomeCenter-debug.apk"

find_rish() {
  if [ -n "${RISH:-}" ] && [ -f "$RISH" ]; then
    printf '%s\n' "$RISH"
    return 0
  fi
  if command -v rish >/dev/null 2>&1; then
    command -v rish
    return 0
  fi
  for candidate in \
    "$HOME/rish" \
    "$HOME/bin/rish" \
    "$HOME/.local/bin/rish" \
    "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish" \
    "/storage/emulated/0/Download/rish"
  do
    if [ -f "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

bootstrap_rish_from_documents() {
  src_rish="/storage/emulated/0/Documents/rish"
  src_dex="/storage/emulated/0/Documents/rish_shizuku.dex"
  dst_dir="$HOME/bin"
  if [ ! -f "$src_rish" ] || [ ! -f "$src_dex" ]; then
    return 1
  fi
  mkdir -p "$dst_dir"
  cp "$src_rish" "$dst_dir/rish"
  cp "$src_dex" "$dst_dir/rish_shizuku.dex"
  chmod 700 "$dst_dir/rish" 2>/dev/null || true
  chmod 400 "$dst_dir/rish_shizuku.dex" 2>/dev/null || true
  printf '%s\n' "$dst_dir/rish"
  return 0
}

if [ ! -f "$APK" ]; then
  echo "APK not found: $APK" >&2
  echo "Run: sh tools/build_debug_apk.sh" >&2
  exit 1
fi

RISH_BIN="$(find_rish || true)"
if [ -z "$RISH_BIN" ]; then
  RISH_BIN="$(bootstrap_rish_from_documents || true)"
fi
if [ -z "$RISH_BIN" ]; then
  echo "Shizuku rish is not configured for Termux." >&2
  echo "One-time setup:" >&2
  echo "1. Install and start Shizuku." >&2
  echo "2. In Shizuku, open 'Use Shizuku in terminal apps' and export/copy rish to Termux." >&2
  echo "3. Either put rish on PATH or run: RISH=/path/to/rish sh tools/install_debug_apk_shizuku.sh" >&2
  exit 2
fi

if [ ! -x "$RISH_BIN" ]; then
  chmod +x "$RISH_BIN" 2>/dev/null || true
fi

echo "Using rish: $RISH_BIN"
"$RISH_BIN" -c "id" >/dev/null

SIZE="$(wc -c < "$APK")"
echo "Streaming $SIZE bytes to $REMOTE_APK"
"$RISH_BIN" -c "cat > '$REMOTE_APK'" < "$APK"

echo "Installing Home Center through Shizuku shell"
"$RISH_BIN" -c "pm install -r '$REMOTE_APK'"

echo "Installed Home Center from $APK"
