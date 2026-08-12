#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV="${HC_PIXEL_VENV:-$ROOT/.venv-pixel-forge}"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "python3 not found" >&2
  exit 2
fi

"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel
"$VENV/bin/python" -m pip install \
  'torch>=2.3' \
  'diffusers>=0.30' \
  'transformers>=4.42' \
  'accelerate>=0.33' \
  'peft>=0.12' \
  'safetensors>=0.4' \
  'Pillow>=10.4'

cat <<EOF
Pixel forge environment ready:
  $VENV/bin/python $ROOT/tools/pixel_forge.py doctor

Public Hugging Face models are used; no HF API token is required.
Model weights remain in the normal Hugging Face cache and are reused between runs.
EOF
