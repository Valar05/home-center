#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="$HOME/.local/state/home-center/venice-review"
mkdir -p "$STATE"
cd "$ROOT"

MODEL="${VENICE_REVIEW_MODEL:-qwen2.5-coder:1.5b}"
OLLAMA_HOST_URL="${OLLAMA_HOST:-http://127.0.0.1:11434}"

have_ollama_api() {
  curl -fsS "${OLLAMA_HOST_URL%/}/api/tags" >/dev/null 2>&1
}

start_ollama_if_needed() {
  if have_ollama_api; then
    return 0
  fi
  command -v ollama >/dev/null 2>&1 || return 1
  if command -v sv >/dev/null 2>&1 && [ -d "$PREFIX/var/service/ollama" ]; then
    sv up ollama >/dev/null 2>&1 || true
  else
    nohup ollama serve >>"$STATE/ollama.log" 2>&1 </dev/null &
    echo $! >"$STATE/ollama.pid"
  fi
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    have_ollama_api && return 0
    sleep 1
  done
  return 1
}

ensure_model() {
  command -v ollama >/dev/null 2>&1 || return 1
  if ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$MODEL"; then
    return 0
  fi
  ollama pull "$MODEL"
}

if ! start_ollama_if_needed; then
  echo 'VENICE_REVIEW_BLOCKED: Ollama API unavailable and local Ollama could not be started.' >&2
  exit 20
fi
if ! ensure_model; then
  echo "VENICE_REVIEW_BLOCKED: model unavailable: $MODEL" >&2
  exit 21
fi

exec python3 tools/venice_review.py "$@"
