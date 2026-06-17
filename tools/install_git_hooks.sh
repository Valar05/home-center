#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

git -c safe.directory="$ROOT" config core.hooksPath .githooks
cat <<'MSG'
Configured git core.hooksPath=.githooks.

Android shared storage often does not preserve executable bits. If git refuses to run a hook with permission errors, use the explicit commands instead:

  sh tools/check_no_secrets.sh
  sh tools/build_debug_apk.sh
  sh tools/deploy_firebase.sh <firebase-project-id>
MSG
