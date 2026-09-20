#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
SOURCE="$ROOT/tools/fortress_cli.py"
TEST="$ROOT/tools/test_fortress_cli.py"
INSTALL_ROOT="${HC_FORTRESS_CLI_ROOT:-$HOME/.local/lib/home-center/fortress-cli}"
INSTALLED="$INSTALL_ROOT/fortress_cli.py"
BIN_DIR="${HC_FORTRESS_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
TARGET="$BIN_DIR/fortress"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/fortress-cli"
RECEIPT="$STATE/install-receipt.json"

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$STATE"

[ -f "$SOURCE" ] || { echo "BLOCKED: missing $SOURCE" >&2; exit 2; }
[ -f "$TEST" ] || { echo "BLOCKED: missing $TEST" >&2; exit 2; }

python3 -m py_compile "$SOURCE" "$TEST"
python3 "$TEST"

TMP_SOURCE="$INSTALLED.tmp.$$"
cp "$SOURCE" "$TMP_SOURCE"
chmod 700 "$TMP_SOURCE"
mv -f "$TMP_SOURCE" "$INSTALLED"

TMP_TARGET="$TARGET.tmp.$$"
cat > "$TMP_TARGET" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
exec python3 $(printf '%q' "$INSTALLED") "\$@"
EOF
chmod 700 "$TMP_TARGET"
mv -f "$TMP_TARGET" "$TARGET"
hash -r 2>/dev/null || true

VERSION="$("$TARGET" --version)"
printf '%s\n' "$VERSION" | grep -q '^fortress-cli-v1 sha256=' || {
  echo "BLOCKED: fortress --version canary failed" >&2
  exit 3
}

SOURCE_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"
INSTALLED_SHA="$(sha256sum "$INSTALLED" | awk '{print $1}')"
WRAPPER_SHA="$(sha256sum "$TARGET" | awk '{print $1}')"
GIT_HEAD="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  GIT_HEAD="$(git -C "$ROOT" rev-parse HEAD)"
fi

python3 - "$RECEIPT" "$GIT_HEAD" "$SOURCE_SHA" "$INSTALLED_SHA" "$WRAPPER_SHA" "$TARGET" "$INSTALLED" <<'PY'
import json, sys, time
path, git_head, source_sha, installed_sha, wrapper_sha, target, installed = sys.argv[1:]
value = {
    "schema": "fortress-cli-install-v1",
    "ok": True,
    "installedAtEpoch": int(time.time()),
    "sourceCommit": git_head,
    "sourceSha256": source_sha,
    "installedSha256": installed_sha,
    "wrapperSha256": wrapper_sha,
    "target": target,
    "installedSource": installed,
    "mutationClass": "install-local-reversible",
    "modelCalls": False,
    "remoteMutation": False,
    "verbs": ["status", "doctor", "cauldron", "wiko"],
}
open(path, "w", encoding="utf-8").write(json.dumps(value, indent=2, sort_keys=True) + "\n")
print(json.dumps(value, indent=2, sort_keys=True))
PY

echo "FORTRESS CLI INSTALLED receipt=$RECEIPT"
