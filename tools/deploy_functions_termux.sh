#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
STAGE="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/home-center-functions-deploy-$(date +%Y%m%d%H%M%S)"

mkdir -p "$STAGE/functions"
cp "$ROOT/firebase.json" "$ROOT/.firebaserc" "$STAGE/"
cp "$ROOT/functions/index.js" "$ROOT/functions/package.json" "$ROOT/functions/package-lock.json" "$STAGE/functions/"

npm install --prefix "$STAGE/functions" >/dev/null
FUNCTIONS_MANIFEST_OUTPUT_PATH="$STAGE/functions/functions.yaml" node "$STAGE/functions/node_modules/firebase-functions/lib/bin/firebase-functions.js" "$STAGE/functions" ignored
firebase deploy --only functions --project "$PROJECT" --config "$STAGE/firebase.json"
