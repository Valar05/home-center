#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
APK="${1:-$ROOT/app/build/outputs/apk/debug/app-debug.apk}"
REMOTE_APK="/data/local/tmp/HomeCenter-debug.apk"
PACKAGE="com.dclar.homecenter"
STATE_DIR="$HOME/.local/state/home-center"
RECEIPT="$STATE_DIR/home-center-install-receipt.json"

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

certificate_digest() {
  apksigner verify --print-certs "$1" 2>/dev/null |
    sed -n 's/^Signer #1 certificate SHA-256 digest: //p' |
    head -n 1 |
    tr 'A-F' 'a-f'
}

copy_installed_apk() {
  destination="$1"
  installed_path="$("$RISH_BIN" -c "pm path '$PACKAGE'" 2>/dev/null |
    sed -n 's/^package://p' |
    head -n 1)"
  if [ -z "$installed_path" ]; then
    return 1
  fi
  "$RISH_BIN" -c "cat '$installed_path'" > "$destination"
}

if [ ! -f "$APK" ]; then
  echo "APK not found: $APK" >&2
  echo "Run: sh tools/build_debug_apk.sh" >&2
  exit 1
fi

command -v apksigner >/dev/null 2>&1 || {
  echo "BLOCKED: apksigner is required for certificate verification." >&2
  exit 2
}
command -v sha256sum >/dev/null 2>&1 || {
  echo "BLOCKED: sha256sum is required for APK readback." >&2
  exit 2
}

RISH_BIN="$(find_rish || true)"
if [ -z "$RISH_BIN" ]; then
  RISH_BIN="$(bootstrap_rish_from_documents || true)"
fi
if [ -z "$RISH_BIN" ]; then
  echo "Shizuku rish is not configured for Termux." >&2
  echo "One-time setup:" >&2
  echo "1. Install and start Shizuku." >&2
  echo "2. In Shizuku, open 'Use Shizuku in terminal apps' and export/copy rish to Termux." >&2
  echo "3. Either put rish on PATH or set RISH to the exported rish path." >&2
  exit 2
fi

if [ ! -x "$RISH_BIN" ]; then
  chmod +x "$RISH_BIN" 2>/dev/null || true
fi

echo "Using rish: $RISH_BIN"
"$RISH_BIN" -c "id" >/dev/null

NEW_CERT="$(certificate_digest "$APK")"
if [ -z "$NEW_CERT" ]; then
  echo "BLOCKED: could not read the candidate APK signing certificate." >&2
  exit 3
fi
NEW_SHA="$(sha256sum "$APK" | awk '{print $1}')"

TMP_ROOT="${TMPDIR:-$HOME/.cache}"
mkdir -p "$TMP_ROOT" "$STATE_DIR"
INSTALLED_APK="$(mktemp "$TMP_ROOT/home-center-installed.XXXXXX.apk")"
cleanup() {
  rm -f "$INSTALLED_APK"
}
trap cleanup EXIT HUP INT TERM

INSTALLED_CERT_BEFORE=""
if copy_installed_apk "$INSTALLED_APK"; then
  INSTALLED_CERT_BEFORE="$(certificate_digest "$INSTALLED_APK")"
  if [ -z "$INSTALLED_CERT_BEFORE" ]; then
    echo "BLOCKED: installed Home Center certificate could not be verified." >&2
    exit 3
  fi
  if [ "$INSTALLED_CERT_BEFORE" != "$NEW_CERT" ]; then
    echo "BLOCKED: candidate signer does not match the installed Home Center signer." >&2
    echo "No uninstall, data retention gamble, or replacement was attempted." >&2
    echo "Build on the signer-owning device or use the established release keystore." >&2
    echo "installed_cert_sha256=$INSTALLED_CERT_BEFORE" >&2
    echo "candidate_cert_sha256=$NEW_CERT" >&2
    exit 3
  fi
fi

SIZE="$(wc -c < "$APK")"
echo "Streaming $SIZE bytes to $REMOTE_APK"
"$RISH_BIN" -c "cat > '$REMOTE_APK'" < "$APK"

echo "Installing Home Center through Shizuku shell"
INSTALL_OUTPUT="$("$RISH_BIN" -c "pm install -r '$REMOTE_APK'" 2>&1)"
printf '%s\n' "$INSTALL_OUTPUT"

if ! printf '%s\n' "$INSTALL_OUTPUT" | grep -q "^Success"; then
  echo "Home Center install failed without uninstalling or replacing private app data." >&2
  exit 1
fi

: > "$INSTALLED_APK"
copy_installed_apk "$INSTALLED_APK" || {
  echo "BLOCKED: install returned success but installed APK readback failed." >&2
  exit 4
}
INSTALLED_CERT_AFTER="$(certificate_digest "$INSTALLED_APK")"
INSTALLED_SHA="$(sha256sum "$INSTALLED_APK" | awk '{print $1}')"
if [ "$INSTALLED_CERT_AFTER" != "$NEW_CERT" ]; then
  echo "BLOCKED: installed signer readback differs from the candidate signer." >&2
  exit 4
fi
if [ "$INSTALLED_SHA" != "$NEW_SHA" ]; then
  echo "BLOCKED: installed APK bytes differ from the candidate APK." >&2
  exit 4
fi

SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || printf 'unknown')"
TMP_RECEIPT="$RECEIPT.tmp.$$"
cat > "$TMP_RECEIPT" <<EOF
{
  "schemaVersion": "home-center.android-install-receipt.v1",
  "package": "$PACKAGE",
  "sourceSha": "$SOURCE_SHA",
  "candidateApkSha256": "$NEW_SHA",
  "installedApkSha256": "$INSTALLED_SHA",
  "candidateSignerSha256": "$NEW_CERT",
  "installedSignerSha256": "$INSTALLED_CERT_AFTER",
  "installMode": "same-signer-update-only",
  "dataDeletionAttempted": false,
  "status": "verified"
}
EOF
chmod 600 "$TMP_RECEIPT"
mv -f "$TMP_RECEIPT" "$RECEIPT"

echo "Installed and verified Home Center from $APK"
echo "receipt=$RECEIPT"
