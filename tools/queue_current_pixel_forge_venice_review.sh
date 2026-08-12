#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
cd "$ROOT"
python3 tools/queue_venice_review_phone.py \
  --repo "$ROOT" \
  --base "${1:-HEAD~12}" \
  --head "${2:-HEAD}" \
  --acceptance "$(cat tools/vlad_pixel_forge_acceptance.txt)"
