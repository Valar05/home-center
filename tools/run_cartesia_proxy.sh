#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

. /data/data/com.termux/files/home/.bashrc
exec python3 tools/cartesia_proxy.py "$@"
