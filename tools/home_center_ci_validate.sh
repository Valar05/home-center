#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
REPORT_DIR="generated/ci-reports"
mkdir -p "$REPORT_DIR"
REPORT_JSON="$REPORT_DIR/home_center_ci_validate.json"
REPORT_MD="$REPORT_DIR/home_center_ci_validate.md"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status="passed"
failed_step=""

run_step() {
  name="$1"
  shift
  echo "== $name"
  if ! "$@"; then
    status="failed"
    failed_step="$name"
    return 1
  fi
}

set +e
run_step "secret scan" sh tools/check_no_secrets.sh   && run_step "functions syntax" node --check functions/index.js   && run_step "worker profile contract" node tools/worker_profile_contract_test.mjs   && run_step "home center mcp syntax" node --check functions/home_center_mcp.js   && run_step "sfx forge syntax" node --check functions/sfx_forge_service.js   && run_step "status contract" node tools/home_center_status_contract_test.mjs   && run_step "audio library indexed browse contract" node --test tools/audio_library_browse_contract_test.mjs   && run_step "armory range contract" node tools/armory_range_contract_test.mjs   && run_step "drive binary chunk contract" node tools/drive_binary_chunk_contract_test.mjs   && run_step "drive file ingest contract" node tools/drive_file_ingest_contract_test.mjs   && run_step "drive audio ingest contract" node tools/drive_audio_ingest_contract_test.mjs   && run_step "sfx forge contract" node tools/sfx_forge_contract_test.mjs   && run_step "command center mcp syntax" node --check functions/command_center_mcp.js   && run_step "she raw mcp syntax" node --check functions/she_raw_mcp.js   && run_step "cloud render syntax" sh -c 'test ! -f cloud-render/src/server.mjs || node --check cloud-render/src/server.mjs; test ! -f cloud-render/src/render_bundle.mjs || node --check cloud-render/src/render_bundle.mjs'   && if command -v convert >/dev/null 2>&1 && command -v identify >/dev/null 2>&1; then run_step "cloud render gif contract" node tools/cloud_render_gif_contract_test.mjs && run_step "blender gif construction contract" node tools/blender_gif_construction_contract_test.mjs; else echo "== cloud render gif contract skipped: ImageMagick convert/identify unavailable"; fi   && run_step "cloud worker syntax" node --check cloud-worker/src/cloud_run_worker.mjs   && run_step "github admin contract" node tools/github_admin_contract_test.mjs   && run_step "home center regression" python3 tools/home_center_regression_tests.py
code=$?
set -e
FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
node -e 'const fs=require("fs"); const data={status:process.argv[1],failedStep:process.argv[2],startedAt:process.argv[3],finishedAt:process.argv[4],runner:"home_center_ci_validate"}; fs.writeFileSync(process.argv[5], JSON.stringify(data,null,2)); fs.writeFileSync(process.argv[6], `# Home Center CI Validate

status: ${data.status}
failed_step: ${data.failedStep || ""}
started_at: ${data.startedAt}
finished_at: ${data.finishedAt}
`);' "$status" "$failed_step" "$STARTED_AT" "$FINISHED_AT" "$REPORT_JSON" "$REPORT_MD"
cat "$REPORT_MD"
exit "$code"
