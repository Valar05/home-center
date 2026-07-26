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
run_step "secret scan" sh tools/check_no_secrets.sh && run_step "functions syntax" node --check functions/index.js && run_step "home center mcp syntax" node --check functions/home_center_mcp.js && run_step "drive binary chunk contract" node tools/drive_binary_chunk_contract_test.mjs && run_step "command center mcp syntax" node --check functions/command_center_mcp.js && run_step "she raw mcp syntax" node --check functions/she_raw_mcp.js && run_step "cloud render syntax" sh -c 'test ! -f cloud-render/src/server.mjs || node --check cloud-render/src/server.mjs; test ! -f cloud-render/src/render_bundle.mjs || node --check cloud-render/src/render_bundle.mjs' && run_step "cloud worker syntax" node --check cloud-worker/src/cloud_run_worker.mjs && run_step "github admin contract syntax" node --check tools/github_admin_contract_test.mjs && if [ -f ../AGENTS.md ] && [ -f ../.codex/skills/ai-mentorship/SKILL.md ]; then run_step "home center regression" python3 tools/home_center_regression_tests.py; else echo "== home center regression skipped: workspace-only context unavailable"; fi
code=$?
set -e
FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
node -e 'const fs=require("fs"); const data={status:process.argv[1],failedStep:process.argv[2],startedAt:process.argv[3],finishedAt:process.argv[4],runner:"home_center_ci_validate"}; fs.writeFileSync(process.argv[5], JSON.stringify(data,null,2)); fs.writeFileSync(process.argv[6], `# Home Center CI Validate\n\nstatus: ${data.status}\nfailed_step: ${data.failedStep || ""}\nstarted_at: ${data.startedAt}\nfinished_at: ${data.finishedAt}\n`);' "$status" "$failed_step" "$STARTED_AT" "$FINISHED_AT" "$REPORT_JSON" "$REPORT_MD"
cat "$REPORT_MD"
exit "$code"
