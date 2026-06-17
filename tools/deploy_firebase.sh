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
