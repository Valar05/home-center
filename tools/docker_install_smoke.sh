#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
IMAGE="${HOME_CENTER_INSTALL_IMAGE:-home-center-install-contract}"
cd "$ROOT"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed here. Run this on a desktop, CI runner, or cloud worker with Docker." >&2
  exit 2
fi
docker build -f tools/install-harness/Dockerfile -t "$IMAGE" .
docker run --rm "$IMAGE"
