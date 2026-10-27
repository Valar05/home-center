#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
case "${1:-start}" in
 dry-run) echo "Cauldron Pocket TTS v2 installer ready through Home Center Computer Hands. Android playback remains untouched.";;
 status) HOME_CENTER_POCKET_TTS_BACKEND=cauldron python "$ROOT/tools/pocket_tts_home_center_worker.py" doctor;;
 start) python "$ROOT/tools/install_cauldron_pocket_tts.py"; sh "$ROOT/tools/home_center_read_aloud.sh" auto; echo "CAULDRON_POCKET_TTS_READY through Home Center Computer Hands";;
 *) echo "usage: $0 {start|status|dry-run}" >&2;exit 2;;
esac
