#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

sh tools/check_no_secrets.sh
sh tools/test_voice_script_planner.sh
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
node --check tools/home_center_authorization_contract_test.mjs
node tools/home_center_authorization_contract_test.mjs
node --check tools/grounded_motion_oauth_contract_test.mjs
node tools/grounded_motion_oauth_contract_test.mjs
node --check tools/home_center_status_contract_test.mjs
node tools/home_center_status_contract_test.mjs
node --check functions/sms_calendar_intake.js
node --check tools/sms_calendar_contract_test.mjs
node tools/sms_calendar_contract_test.mjs
node --check functions/she_raw_mcp.js
node --check tools/command_center_mcp_contract_test.mjs
sh -n tools/deploy_functions_termux.sh
sh -n tools/assert_home_center_mcp_main_release.sh
node tools/home_center_mcp_main_release_gate_test.mjs
node tools/home_center_production_deploy_contract_test.mjs
node tools/command_center_mcp_contract_test.mjs
node --check tools/cloud_blender_retirement_contract_test.mjs
node tools/cloud_blender_retirement_contract_test.mjs
node tools/artifact_delivery_contract_test.mjs
node --check tools/she_raw_cloud_introspection_gate.mjs
node --check tools/she_raw_seed_corpus_firestore.mjs
node --check functions/index.js
node --check functions/hosted_speech_provider.js
node --check functions/gemini_speech_provider.js
node --check functions/gemini_tts_artifact_service.js
node tools/gemini_tts_contract_test.mjs
node --check functions/audio_library_api.js
node --check tools/audio_library_contract_test.mjs
node tools/audio_library_contract_test.mjs
node tools/audio_reader_registration_contract_test.mjs
node tools/audio_render_contract_test.mjs
node --check functions/household_evidence.js
node --check tools/household_evidence_contract_test.mjs
node tools/household_evidence_contract_test.mjs
node --check tools/cartesia_mcp_artifact_contract_test.mjs
node tools/cartesia_mcp_artifact_contract_test.mjs
node --check tools/home_center_metal_prompt_smoke.mjs
node --check tools/home_center_creative_prompt_smoke.mjs
node --check tools/home_center_turn_contract_smoke.mjs
node --check tools/home_center_google_tool_setup.mjs
node --check tools/home_center_codex_pair.mjs
node --check tools/home_center_install_contract_test.mjs
node tools/home_center_install_contract_test.mjs
node --check tools/drive_bridge_create_tools_test.mjs
node --check tools/browser_worker_contract_test.mjs
node tools/browser_worker_contract_test.mjs
node tools/home_center_artifact_register.mjs --self-test
node tools/home_center_engineering_orient.mjs --self-test
node --check tools/home_center_artifact_register.mjs
node --check tools/home_center_engineering_orient.mjs
node tools/drive_bridge_create_tools_test.mjs
node --check tools/droobiedoo_context_source_contract_test.mjs
node tools/droobiedoo_context_source_contract_test.mjs
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
  app/src/main/java/com/dclar/homecenter/SmsCalendarIngestionContract.java \
  app/src/main/java/com/dclar/homecenter/SmsReminderClassifier.java \
  tools/CommandParserHarness.java \
  tools/SmsReminderClassifierHarness.java
java -cp "$tmp/classes" com.dclar.homecenter.CommandParserHarness
java -cp "$tmp/classes" com.dclar.homecenter.SmsReminderClassifierHarness
rm -rf "$tmp"

echo "Home Center regression harness: OK"
