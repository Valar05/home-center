#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SOURCE="$ROOT/tools/fortress_clip_catalog.py"
INSTALL_ROOT="${HOME}/.local/lib/home-center/clip-catalog"
INSTALLED="$INSTALL_ROOT/fortress_clip_catalog.py"
BIN_DIR="${HOME}/bin"
WRAPPER="$BIN_DIR/fortress-clip"
[ -f "$SOURCE" ] || { echo "BLOCKED: missing $SOURCE" >&2; exit 2; }
mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
cp "$SOURCE" "$INSTALLED.tmp.$$"
chmod 600 "$INSTALLED.tmp.$$"
python -m py_compile "$INSTALLED.tmp.$$"
mv -f "$INSTALLED.tmp.$$" "$INSTALLED"
cat > "$WRAPPER.tmp.$$" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
set -eu
exec python "$INSTALLED" "\$@"
EOF
chmod 700 "$WRAPPER.tmp.$$"
mv -f "$WRAPPER.tmp.$$" "$WRAPPER"
SOURCE_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"
INSTALLED_SHA="$(sha256sum "$INSTALLED" | awk '{print $1}')"
[ "$SOURCE_SHA" = "$INSTALLED_SHA" ] || { echo "BLOCKED: SHA mismatch" >&2; exit 3; }
printf '{"ok":true,"schema":"fortress.clip-catalog-install.v1","sourceSha256":"%s","installedPath":"%s","wrapperPath":"%s","catalogRoot":"/storage/emulated/0/Documents/FortressAudio/Clips"}\n' "$SOURCE_SHA" "$INSTALLED" "$WRAPPER"
