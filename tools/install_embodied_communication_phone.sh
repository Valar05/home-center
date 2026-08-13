#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SOURCE="$ROOT/tools/fortress_read_aloud.py"
INSTALL_ROOT="${HOME}/.local/lib/home-center/embodied-communication"
INSTALLED="$INSTALL_ROOT/fortress_read_aloud.py"
BIN_DIR="${HOME}/bin"
WRAPPER="$BIN_DIR/fortress-read"

if [ ! -f "$SOURCE" ]; then
  echo "BLOCKED: Pocket Space runtime source missing: $SOURCE" >&2
  exit 2
fi

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
TMP="$INSTALLED.tmp.$$"
cp "$SOURCE" "$TMP"
chmod 600 "$TMP"
python -m py_compile "$TMP"
mv -f "$TMP" "$INSTALLED"
chmod 600 "$INSTALLED"

cat > "$WRAPPER.tmp.$$" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
set -eu
exec python "$INSTALLED" "\$@"
EOF
chmod 700 "$WRAPPER.tmp.$$"
mv -f "$WRAPPER.tmp.$$" "$WRAPPER"

SOURCE_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"
INSTALLED_SHA="$(sha256sum "$INSTALLED" | awk '{print $1}')"
if [ "$SOURCE_SHA" != "$INSTALLED_SHA" ]; then
  echo "BLOCKED: installed Pocket Space runtime SHA mismatch" >&2
  exit 3
fi

SOURCE_COMMIT=""
if command -v git >/dev/null 2>&1; then
  SOURCE_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
fi
DOCTOR="$($WRAPPER --doctor)"
python - "$SOURCE_COMMIT" "$SOURCE_SHA" "$INSTALLED" "$WRAPPER" "$DOCTOR" <<'PY'
import json, sys
commit, sha, installed, wrapper, doctor_raw = sys.argv[1:]
doctor = json.loads(doctor_raw)
if not doctor.get('ok'):
    raise SystemExit('BLOCKED: installed Pocket Space doctor is not ready: ' + json.dumps(doctor, ensure_ascii=False))
print(json.dumps({
    'ok': True,
    'schema': 'fortress.embodied-phone-install.v1',
    'sourceCommit': commit,
    'sourceSha256': sha,
    'installedPath': installed,
    'wrapperPath': wrapper,
    'doctor': doctor,
}, ensure_ascii=False))
PY
