#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Documents/GodotProjects/home-center"
cd "$ROOT"
exec node tools/learn_chatgpt_connector_frame_lane.mjs "$@"
