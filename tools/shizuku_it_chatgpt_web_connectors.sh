#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Documents/GodotProjects/home-center"
cd "$ROOT"
exec node tools/shizuku_it_chatgpt_web_connectors.mjs "$@"
