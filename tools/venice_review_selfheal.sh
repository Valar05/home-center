#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
bash "$ROOT/tools/ensure_venice_local.sh"
exec python3 "$ROOT/tools/venice_review.py" "$@"
