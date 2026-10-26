#!/usr/bin/env bash
# Termux -> THECAULDRON, no SCP/SFTP or Windows file management.
set -euo pipefail
[[ "${PREFIX:-}" == *com.termux* ]] || { echo 'Run in Termux.' >&2; exit 2; }
for tool in curl ssh iconv base64 mktemp; do command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 2; }; done
mode=Install
case "${1:-}" in
  ""|--install) ;;
  --audit) mode=Audit ;;
  --test) mode=Test ;;
  *) echo 'Usage: run_pose_vision.sh [--audit|--install|--test]' >&2; exit 2 ;;
esac
url="https://raw.githubusercontent.com/Valar05/home-center/392ffe52106a853510ed952462fb0e0911e5f0b8/tools/install_pose_vision.ps1"
tmp="$(mktemp "${TMPDIR:-/data/data/com.termux/files/usr/tmp}/pose-vision.XXXXXXXX.ps1")"
trap 'rm -f "$tmp"' EXIT
curl -fLsS --retry 2 "$url" -o "$tmp"
[[ -s "$tmp" ]] || { echo 'Installer download empty' >&2; exit 3; }
bootstrap='$code=[Console]::In.ReadToEnd(); & ([scriptblock]::Create($code)) -Mode '
bootstrap+="$mode"
encoded="$(printf %s "$bootstrap" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\r\n')"
echo "POSE_VISION_MODE=$mode; SSH_STDIN=1; NO_SFTP=1"
ssh -T -p 10022 -o ConnectTimeout=8 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=yes dclar@100.68.37.106 powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand "$encoded" < "$tmp"
