import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync(new URL('deploy_functions_termux.sh', import.meta.url), 'utf8');
const workflow = fs.readFileSync(new URL('../.github/workflows/deploy-home-center-mcp.yml', import.meta.url), 'utf8');
const mainGate = fs.readFileSync(new URL('assert_home_center_mcp_main_release.sh', import.meta.url), 'utf8');

for (const fn of ['agentToolTurn', 'agentTurn', 'creativePromptSmoke', 'turnContractSmoke', 'metalPromptSmoke', 'tts', 'speak', 'ttsVoices']) {
  assert.match(script, new RegExp('deploy_credit_backed_http_function ' + fn + ' '));
}
assert.match(script, /creditBackedHttp\) deploy_credit_backed_http ;;/);
assert.match(script, /gcloud functions deploy commandCenterRenderWorker/);
assert.match(script, /gcloud tasks queues "\$QUEUE_ACTION" "\$QUEUE"/);
assert.match(script, /--max-concurrent-dispatches=4/);
assert.match(script, /--max-attempts=1/);
assert.doesNotMatch(script, /firebase deploy --project "\$PROJECT" --only functions:commandCenterRenderWorker/);
assert.equal((workflow.match(/^concurrency:/gm) || []).length, 1);
assert.match(workflow, /workflow_dispatch:/);
assert.match(script, /case " \$FUNCTIONS " in[\s\S]*assert_home_center_mcp_main_release\.sh/, 'deploy script must gate MCP before any cloud mutation');
assert.match(mainGate, /refs\/remotes\/origin\/main/);
assert.match(mainGate, /HEAD_SHA.*MAIN_SHA/);
assert.match(mainGate, /status --porcelain --untracked-files=all/);
assert.match(workflow, /ref: refs\/heads\/main/);
assert.match(workflow, /fetch-depth: 0/);
assert.match(workflow, /Enforce immutable main release source/);
assert.doesNotMatch(workflow, /^  push:/m);
assert.doesNotMatch(workflow, /gcloud services enable/, 'deploy identity must not require Service Usage Admin');
assert.match(workflow, /deploy_functions_termux\.sh "\$PROJECT" homeCenterMcp/);
for (const name of ['HOME_CENTER_SOURCE_REPOSITORY', 'HOME_CENTER_SOURCE_COMMIT', 'HOME_CENTER_SOURCE_REF', 'HOME_CENTER_PUBLIC_MANIFEST_SHA256']) assert.match(script, new RegExp(name));
assert.match(script, /contracts\/home-center-public-tool-manifest\.v1\.json/);
assert.doesNotMatch(workflow, /deploy_command_center_cloud_worker|sheRawMcp|firebase deploy --only firestore/);
console.log('Home Center production deploy contract: OK');
