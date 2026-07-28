import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const absent = [
  '.github/workflows/deploy-cloud-run-blender-build.yml',
  'cloud-render',
  'factory/sherman-cleanroom-cloudrun-a',
  'functions/render_input_validation.js',
  'tools/deploy_command_center_blender_render.sh',
  'tools/command_center_blender_render_contract_test.mjs',
  'tools/home_center_render_blender_glb_protocol_test.mjs',
  'cloud-worker',
  'tools/deploy_command_center_cloud_worker.sh',
  'tools/command_center_codex_executor.sh',
  'tools/command_center_chatgpt_invokability_gate.mjs',
  'tools/command_center_cloud_run_worker_proof.mjs',
  'tools/command_center_health_ladder.mjs',
  'tools/command_center_base_manifests',
];
for (const relative of absent) assert.equal(fs.existsSync(path.join(root, relative)), false, relative + ' must remain deleted');

const active = [
  'functions/index.js',
  'functions/home_center_mcp.js',
  'functions/command_center_mcp.js',
  'functions/package.json',
  'ops/worker_profiles.v1.json',
  'tools/deploy_functions_termux.sh',
  'tools/deploy_foundry_worker.sh',
  'contracts/home-center-top-level-mcp.v1.json',
  'contracts/home-center-public-tool-manifest.v1.json',
].map((relative) => ({relative, source: fs.readFileSync(path.join(root, relative), 'utf8')}));

const forbidden = [
  ['top-level renderer', /render_blender_glb/i],
  ['retired Cloud Run service', /command-center-blender-render/i],
  ['retired task worker', /commandCenterRenderWorker/],
  ['retired public operation', /command_center\.render\.blender/i],
  ['retired deployment environment', /COMMAND_CENTER_RENDER_SERVICE_URL|COMMAND_CENTER_RENDER_BUCKET/],
];
for (const file of active) for (const [label, pattern] of forbidden) assert.doesNotMatch(file.source, pattern, file.relative + ' still contains ' + label);

const commandSource = fs.readFileSync(path.join(root, 'functions/command_center_mcp.js'), 'utf8');
const homeSource = fs.readFileSync(path.join(root, 'functions/home_center_mcp.js'), 'utf8');
for (const source of [commandSource, homeSource]) {
  assert.match(source, /capability_retired\.use_foundry/);
  assert.match(source, /foundry\.asset\.run/);
}
assert.doesNotMatch(commandSource, /function renderBlender|executeQueuedRenderRequest|invokeRenderService/);
assert.doesNotMatch(commandSource, /server\.registerTool\('command_center\.(?:agents|workers|hosts|jobs|machine_images|provisioning|codex_sessions|routing|proof)\./);
assert.doesNotMatch(homeSource, /^\s*'(?:agents|workers|hosts|jobs|machine_images|provisioning|codex_sessions|routing|proof)\./m);
assert.doesNotMatch(homeSource, /function renderBlender|materializeHomeCenterRenderSources|materializeRenderReviewArtifactsOperation/);
assert.doesNotMatch(fs.readFileSync(path.join(root, 'functions/index.js'), 'utf8'), /executeQueuedRenderRequest|commandCenterRenderWorker/);
assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'ops/worker_profiles.v1.json'), 'utf8')).assignments['command-center-blender-render'], undefined);

const topLevel = JSON.parse(fs.readFileSync(path.join(root, 'contracts/home-center-top-level-mcp.v1.json'), 'utf8'));
assert.equal(topLevel.some((tool) => tool.name === 'render_blender_glb'), false);
assert.equal(topLevel.some((tool) => /foundry/i.test(tool.name)), false);
const publicManifest = JSON.parse(fs.readFileSync(path.join(root, 'contracts/home-center-public-tool-manifest.v1.json'), 'utf8'));
assert.equal(JSON.stringify(publicManifest).includes('render_blender_glb'), false);

const foundryFiles = ['functions/foundry_capability.js','functions/foundry_kernel.mjs','functions/foundry_worker_process.mjs','functions/foundry_review_renderer.mjs','functions/foundry_script_runtime.mjs'];
for (const relative of foundryFiles) {
  const source = fs.readFileSync(path.join(root, relative), 'utf8');
  assert.doesNotMatch(source, /\bbpy\b|Blender Python|cloud.?blender|spawn\s*\([^\n]*blender/i, relative + ' may not invoke or fall back to the retired renderer');
  assert.doesNotMatch(source, /FOUNDRY_RECIPE_VERSION|mechanical_specimen|foundry-character-v1|fixtureId/, relative + ' retains Foundry V1 execution');
}

console.log(JSON.stringify({ok:true,retiredExecutionReachability:0,replacement:'drive_operation/foundry.asset.run',historicalReceipts:'generic read-only receipt discovery only'},null,2));
