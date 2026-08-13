#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"

# Judgment-Jar Venice is the primary review path. Do not spend phone compute or
# manufacture a local-model dependency merely because this compatibility wrapper
# is named selfheal. Only an explicit --local-venice request may start/repair the
# optional local reviewer runtime.
local_requested=0
for arg in "$@"; do
  if [ "$arg" = "--local-venice" ]; then local_requested=1; break; fi
done
if [ "$local_requested" -eq 1 ]; then
  bash "$ROOT/tools/ensure_venice_local.sh"
fi
exec python3 "$ROOT/tools/venice_review_receipted.py" "$@"
