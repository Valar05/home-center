#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

sh tools/check_no_secrets.sh
sh -n tools/install_debug_apk_shizuku.sh
python3 tools/home_center_regression_tests.py
node --check functions/command_center_mcp.js
node --check tools/command_center_mcp_contract_test.mjs
node --check tools/command_center_chatgpt_invokability_gate.mjs
node --check tools/command_center_oneshot_worker.mjs
node --check tools/command_center_verbose_worker_smoke.mjs
node tools/command_center_mcp_contract_test.mjs
node tools/command_center_oneshot_worker.mjs --self-test
node --check functions/index.js
node --check tools/home_center_metal_prompt_smoke.mjs
node --check tools/home_center_creative_prompt_smoke.mjs
node --check tools/home_center_turn_contract_smoke.mjs
node --check tools/home_center_google_tool_setup.mjs
node --check tools/home_center_codex_pair.mjs
node --check tools/drive_bridge_create_tools_test.mjs
node --check tools/chatgpt_connector_acceptance_gate.mjs
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
