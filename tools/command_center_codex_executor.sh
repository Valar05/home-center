#!/bin/sh
set -eu

: "${COMMAND_CENTER_PROMPT_PACKET:?COMMAND_CENTER_PROMPT_PACKET is required}"
: "${COMMAND_CENTER_ARTIFACT_DIR:?COMMAND_CENTER_ARTIFACT_DIR is required}"

if [ ! -f "$COMMAND_CENTER_PROMPT_PACKET" ]; then
  echo "Command Center prompt packet not found: $COMMAND_CENTER_PROMPT_PACKET" >&2
  exit 78
fi

if [ "${COMMAND_CENTER_CODEX_EXECUTOR_DRY_RUN:-}" = "1" ]; then
  echo "COMMAND_CENTER_CODEX_EXECUTOR_DRY_RUN=1"
  echo "prompt_packet=$COMMAND_CENTER_PROMPT_PACKET"
  echo "artifact_dir=$COMMAND_CENTER_ARTIFACT_DIR"
  exit 0
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is not installed or not on PATH" >&2
  exit 127
fi

mkdir -p "$COMMAND_CENTER_ARTIFACT_DIR"

# Local workers use the saved ChatGPT login, never inherited Platform API keys.
unset OPENAI_API_KEY CODEX_API_KEY

exec codex exec \
  --json \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  - < "$COMMAND_CENTER_PROMPT_PACKET"
