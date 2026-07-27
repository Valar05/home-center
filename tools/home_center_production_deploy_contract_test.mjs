import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync(new URL('deploy_functions_termux.sh', import.meta.url), 'utf8');
const workflow = fs.readFileSync(new URL('../.github/workflows/deploy-home-center-mcp.yml', import.meta.url), 'utf8');

for (const fn of ['agentToolTurn', 'agentTurn', 'creativePromptSmoke', 'turnContractSmoke', 'metalPromptSmoke', 'tts', 'speak', 'ttsVoices']) {
  assert.match(script, new RegExp('deploy_credit_backed_http_function ' + fn + ' '));
}
assert.match(script, /creditBackedHttp\) deploy_credit_backed_http ;;/);
assert.equal((workflow.match(/^concurrency:/gm) || []).length, 1);
assert.match(workflow, /workflow_dispatch:/);
assert.doesNotMatch(workflow, /^  push:/m);
assert.match(workflow, /gcloud services enable speech\.googleapis\.com --project="\$PROJECT"/);
assert.match(workflow, /deploy_functions_termux\.sh "\$PROJECT" homeCenterMcp/);
assert.doesNotMatch(workflow, /deploy_command_center_cloud_worker|sheRawMcp|firebase deploy --only firestore/);
console.log('Home Center production deploy contract: OK');
