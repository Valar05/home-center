#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Documents/GodotProjects/home-center"
cd "$ROOT"

cat >&2 <<MSG
chatgpt_home_center_shizuku_acceptance.sh no longer sends ChatGPT prompts directly.
The 2026-07-11 frame/OAuth run proved that prompt sending before connected-state evidence is a false acceptance path.
Use the fast Home Center learning integration instead:

  sh tools/learn_chatgpt_connector_frame_lane.sh --submit

For contract validation only:

  node tools/chatgpt_connector_frame_learning_contract_test.mjs
MSG

exec sh tools/learn_chatgpt_connector_frame_lane.sh "$@"
