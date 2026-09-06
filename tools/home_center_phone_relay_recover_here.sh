#!/system/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
export HC_PHONE_REPO="${HC_PHONE_REPO:-$ROOT}"
exec sh "$ROOT/tools/home_center_phone_relay_recover.sh"
