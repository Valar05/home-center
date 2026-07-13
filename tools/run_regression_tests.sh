#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

sh tools/check_no_secrets.sh
sh -n tools/install_debug_apk_shizuku.sh
sh -n tools/home_center_shizuku_setup_probe.sh
sh -n tools/home_drive_profile_refresh_loop.sh
sh -n tools/home_drive_profile_refresh_tmux.sh
sh -n tools/home_center_scheduler_tmux.sh
python3 -m py_compile tools/home_center_scheduler.py
node --check tools/home_center_backend_automation_introspect.mjs
python3 -m py_compile tools/home_drive_speaker_profile_scan.py
sh -n tools/docker_install_smoke.sh
python3 tools/home_center_regression_tests.py
node --check functions/command_center_mcp.js
node --check functions/she_raw_mcp.js
node --check tools/command_center_mcp_contract_test.mjs
node --check tools/command_center_cloud_activation_contract_test.mjs
node --check tools/command_center_two_dispatch_acceptance.mjs
node --check tools/command_center_chatgpt_invokability_gate.mjs
node --check tools/command_center_home_bridge_invokability_gate.mjs
node --check tools/command_center_real_capability_gate.mjs
node --check tools/command_center_oneshot_worker.mjs
node --check tools/command_center_verbose_worker_smoke.mjs
node --check cloud-worker/src/cloud_run_worker.mjs
sh -n tools/deploy_command_center_cloud_worker.sh
node tools/command_center_mcp_contract_test.mjs
node tools/command_center_cloud_activation_contract_test.mjs
node --check tools/she_raw_contract_test.mjs
node tools/she_raw_contract_test.mjs
node --check tools/she_raw_cloud_introspection_gate.mjs
node --check tools/she_raw_seed_corpus_firestore.mjs
node tools/command_center_oneshot_worker.mjs --self-test
node --check functions/index.js
node --check tools/home_center_metal_prompt_smoke.mjs
node --check tools/home_center_creative_prompt_smoke.mjs
node --check tools/home_center_turn_contract_smoke.mjs
node --check tools/home_center_google_tool_setup.mjs
node --check tools/home_center_codex_pair.mjs
node --check tools/home_center_install_contract_test.mjs
node tools/home_center_install_contract_test.mjs
node --check tools/drive_bridge_create_tools_test.mjs
node --check tools/chatgpt_connector_acceptance_gate.mjs
sh -n tools/connect_chatgpt_home_center_fast.sh
sh -n tools/shizuku_live_playwright_chatgpt_home_center.sh
node --check browser-worker/src/chatgpt_clean_slate_verify.mjs
node --check tools/browser_worker_contract_test.mjs
node tools/browser_worker_contract_test.mjs
node --check tools/chrome_frame_learning_envelope.mjs
node --check tools/submit_chrome_frame_learning.mjs
node --check tools/chrome_frame_learning_contract_test.mjs
node --check tools/chatgpt_connector_frame_learning_contract_test.mjs
node tools/chrome_frame_learning_contract_test.mjs
node tools/chatgpt_connector_frame_learning_contract_test.mjs
node tools/home_center_artifact_register.mjs --self-test
node tools/home_center_engineering_orient.mjs --self-test
node --check tools/home_center_artifact_register.mjs
node --check tools/home_center_engineering_orient.mjs
node tools/drive_bridge_create_tools_test.mjs
node tools/home_center_calendar_time_test.js
python3 tools/agent_harness.py --all
sh agent-tools/ticktick-list-ingest/tests/run_fixture_smoke.sh
sh agent-tools/walmart-cart-agent/tests/run_fixture_smoke.sh

tmp="${TMPDIR:-/tmp}/home-center-regression-$$"
rm -rf "$tmp"
mkdir -p "$tmp/classes"

javac -d "$tmp/classes" \
  app/src/main/java/com/dclar/homecenter/Command.java \
  app/src/main/java/com/dclar/homecenter/CommandParser.java \
  tools/CommandParserHarness.java
java -cp "$tmp/classes" com.dclar.homecenter.CommandParserHarness
rm -rf "$tmp"

echo "Home Center regression harness: OK"
