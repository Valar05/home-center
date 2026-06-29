#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

PROJECT="${1:-${FIREBASE_PROJECT:-}}"
sh tools/build_debug_apk.sh

if [ -n "$PROJECT" ]; then
  sh tools/deploy_firebase.sh "$PROJECT"
else
  echo "No Firebase project supplied; APK deploy complete and Firebase deploy skipped."
  echo "To deploy Firebase: sh tools/deploy_firebase.sh <firebase-project-id>"
fi
