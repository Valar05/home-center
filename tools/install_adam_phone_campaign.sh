#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
SCRIPT="$ROOT/tools/adam_phone_campaign.sh"
[ -f "$SCRIPT" ] || { echo "BLOCKED: campaign script missing: $SCRIPT" >&2; exit 2; }
bash "$SCRIPT" install-service
exec "${PREFIX:-$HOME/.local}/bin/adam-campaign" run
