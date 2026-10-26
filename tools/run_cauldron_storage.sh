#!/usr/bin/env bash
# Termux -> THECAULDRON storage campaign, without SFTP/SCP.
# Downloads a pinned PowerShell script and streams it over authenticated SSH stdin.
set -euo pipefail
[[ "${PREFIX:-}" == *com.termux* ]] || { echo 'Run this in Termux.' >&2; exit 2; }
for c in curl ssh iconv base64 mktemp; do command -v "$c" >/dev/null || { echo "Missing dependency: $c" >&2; exit 2; }; done
mode=Audit
venv=''
case "${1:-}" in
  '') ;;
  --audit) ;;
  --clean) mode=CleanCaches ;;
  --clean-chatterbox-venv) mode=CleanCaches; venv=' -RemoveChatterboxVenv' ;;
  *) echo 'Usage: bash run_cauldron_storage.sh [--audit|--clean|--clean-chatterbox-venv]' >&2; exit 2 ;;
esac
script_url="https://raw.githubusercontent.com/Valar05/home-center/b0875fd8f9578a2694924c35a8bef6def4125595/tools/cauldron_storage_audit.ps1"
tmp="$(mktemp "${TMPDIR:-/data/data/com.termux/files/usr/tmp}/cauldron-audit.XXXXXXXX.ps1")"
trap 'rm -f "$tmp"' EXIT
curl --fail --location --silent --show-error --retry 2 "$script_url" -o "$tmp"
[[ -s "$tmp" ]] || { echo 'Downloaded script is empty.' >&2; exit 3; }
bootstrap='$src=[Console]::In.ReadToEnd(); & ([scriptblock]::Create($src)) -Mode '${mode}"${venv}"' -Confirm:$false'
# Encode a *short* bootstrap, not the 10KB script, to avoid cmd.exe argument limits.
encoded="$(printf '%s' "$bootstrap" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\r\n')"
echo "CAULDRON_STORAGE_MODE=$mode; STREAM=ssh-stdin; NO_SFTP=1"
echo 'Protecting PocketTTS, its voice profiles, Hugging Face caches, Ollama models and project sources.'
exec ssh -T -p 10022 \
  -o ConnectTimeout=8 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=yes \
  dclar@100.68.37.106 \
  powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand "$encoded" < "$tmp"
