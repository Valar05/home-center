#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  printf '%s\n' "Regnet QA requires Python 3; set PYTHON_BIN to an available interpreter." >&2
  exit 127
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/tools/renee.py" "$@"
