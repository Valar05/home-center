#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

PROJECT="${1:-${FIREBASE_PROJECT:-}}"
if [ -z "$PROJECT" ]; then
  echo "Usage: sh tools/deploy_firebase.sh <firebase-project-id>" >&2
  echo "Or set FIREBASE_PROJECT=<firebase-project-id>." >&2
  exit 2
fi

if ! command -v firebase >/dev/null 2>&1; then
  echo "Firebase CLI is not installed." >&2
  echo "Install it with: npm install -g firebase-tools" >&2
  echo "Then run: firebase login --no-localhost" >&2
  exit 127
fi

sh tools/check_no_secrets.sh
firebase deploy --only firestore --project "$PROJECT"

if [ -f functions/package.json ]; then
  if ! command -v node >/dev/null 2>&1; then
    echo "Node.js is required to deploy Firebase Functions." >&2
    exit 127
  fi

  if [ ! -d functions/node_modules ]; then
    echo "functions/node_modules is missing." >&2
    echo "Run: npm --prefix functions install" >&2
    exit 1
  fi

  NODE_BIN="$(command -v node)"
  TMP_PARENT="${TMPDIR:-/data/data/com.termux/files/usr/tmp}"
  DEPLOY_DIR="$TMP_PARENT/home-center-functions-deploy"
  BIN_DIR="$DEPLOY_DIR/functions/node_modules/.bin"
  SDK_BIN="$DEPLOY_DIR/functions/node_modules/firebase-functions/lib/bin/firebase-functions.js"
  WRAPPER="$BIN_DIR/firebase-functions"
  SPAWN_PATCH="$DEPLOY_DIR/termux-firebase-spawn-patch.js"
  FUNCTIONS_LOG="$DEPLOY_DIR/functions-deploy.log"

  # Android shared storage is mounted noexec, but Firebase Functions discovery
  # executes the firebase-functions SDK binary. Stage in Termux temp storage.
  rm -rf "$DEPLOY_DIR"
  mkdir -p "$DEPLOY_DIR"
  cp firebase.json "$DEPLOY_DIR/firebase.json"
  cp -R functions "$DEPLOY_DIR/functions"

  if [ ! -f "$SDK_BIN" ]; then
    echo "Firebase Functions SDK binary is missing: $SDK_BIN" >&2
    echo "Run: npm --prefix functions install" >&2
    exit 1
  fi

  mkdir -p "$BIN_DIR"
  cat > "$WRAPPER" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
exec "$NODE_BIN" "$SDK_BIN" "\$@"
EOF
  cat > "$SPAWN_PATCH" <<'EOF'
const childProcess = require("child_process");

const originalSpawn = childProcess.spawn;

childProcess.spawn = function patchedSpawn(command, args, options) {
  if (String(command).endsWith("/node_modules/.bin/firebase-functions")) {
    options = options || {};
    options.env = Object.assign({}, options.env, {
      LD_PRELOAD: "/data/data/com.termux/files/usr/lib/libtermux-exec.so",
      LD_LIBRARY_PATH: [
        "/data/data/com.termux/files/usr/lib",
        options.env && options.env.LD_LIBRARY_PATH ? options.env.LD_LIBRARY_PATH : "",
      ].filter(Boolean).join(":"),
    });
  }
  return originalSpawn.call(this, command, args, options);
};
EOF
  chmod -R u+rwX,go+rX "$DEPLOY_DIR"
  chmod 755 "$WRAPPER" "$SDK_BIN" "$SPAWN_PATCH" "$NODE_BIN" 2>/dev/null || true

  set +e
  (cd "$DEPLOY_DIR" && NODE_OPTIONS="--require=$SPAWN_PATCH" firebase deploy --only functions --project "$PROJECT") >"$FUNCTIONS_LOG" 2>&1
  FUNCTIONS_STATUS=$?
  set -e
  cat "$FUNCTIONS_LOG"
  if [ "$FUNCTIONS_STATUS" -ne 0 ]; then
    exit "$FUNCTIONS_STATUS"
  fi
  if grep -E "Permission denied|Failed to find location of Firebase Functions SDK|Failed to load function definition" "$FUNCTIONS_LOG" >/dev/null; then
    echo "Firebase Functions deploy failed during source discovery." >&2
    exit 1
  fi
  if ! grep "Deploy complete!" "$FUNCTIONS_LOG" >/dev/null; then
    echo "Firebase Functions deploy did not report completion." >&2
    exit 1
  fi
fi
