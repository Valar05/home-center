#!/usr/bin/env bash
# Phone-side retrieval companion. Usage: pocket pull JOB_ID
set -euo pipefail
if [[ "${1:-}" != "pull" || ! "${2:-}" =~ ^[A-Za-z0-9_-]{8,80}$ ]]; then
  echo 'Usage: pocket pull JOB_ID' >&2; exit 2
fi
command -v scp >/dev/null || { echo 'OpenSSH scp is required in Termux' >&2; exit 2; }
: "${POCKET_CAULDRON_HOST:?Set POCKET_CAULDRON_HOST to the existing SSH host/address for THECAULDRON}"
remote_dir="${POCKET_REMOTE_DIR:-C:/Users/dclar/PocketASMR}"
downloads="${POCKET_DOWNLOADS:-$HOME/storage/downloads}"
mkdir -p "$downloads"
dest="$downloads/ritsu-asmr-$2.wav"
if [[ -e "$dest" ]]; then echo "Refusing overwrite: $dest" >&2; exit 3; fi
# scp is intentionally hidden behind this single command; no manual SFTP navigation.
scp -- "$POCKET_CAULDRON_HOST:$remote_dir/jobs/$2/audio.wav" "$dest"
[[ -s "$dest" ]] || { rm -f "$dest"; echo 'Downloaded empty file' >&2; exit 1; }
echo "DOWNLOADED $dest"
echo "Open this WAV with your phone music player and use your earbuds."
