#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const packageJson = JSON.parse(fs.readFileSync(new URL('../browser-worker/package.json', import.meta.url), 'utf8'));
const workerSource = fs.readFileSync(new URL('../browser-worker/src/browser_worker.mjs', import.meta.url), 'utf8');
const docs = fs.readFileSync(new URL('../docs/BROWSER_HANDS.md', import.meta.url), 'utf8');

assert.equal(packageJson.dependencies.playwright, 'latest');
assert.equal(packageJson.type, 'module');
assert.match(packageJson.description, /first-class app function/i);
assert.match(workerSource, /from 'playwright'/);
assert.match(workerSource, /chromium\.launch/);
assert.match(workerSource, /HOME_CENTER_CHROMIUM_EXECUTABLE/);
assert.match(workerSource, /executablePath/);
assert.match(workerSource, /mode: 'desktop'/);
assert.match(workerSource, /record/);
assert.match(workerSource, /blocked_human_required/);
assert.match(workerSource, /detectPageBlockers/);

assert.match(workerSource, /buildSelectorLadderFromElementMeta/);
assert.match(workerSource, /runBrowserReplay/);
assert.match(workerSource, /selector_drift/);
assert.match(workerSource, /householdLearningContract/);
assert.match(workerSource, /learnedBy: safeText\(options\.learnedBy/);
assert.match(workerSource, /replayAudience: safeText\(options\.replayAudience/);
assert.match(workerSource, /html_id_data_testid_aria_role_label_first_no_pixel_coordinates/);
assert.doesNotMatch(workerSource, /pixel_coordinates'\s*,\s*\n\s*}\);/);
assert.match(workerSource, /not a robot/);
assert.match(workerSource, /redacted/);
assert.doesNotMatch(JSON.stringify(packageJson.scripts), /chatgpt|connector|clean.slate/i);
const retiredConnectorPaths = [
  '../browser-worker/src/chatgpt_clean_slate_verify.mjs',
  '../browser-worker/src/chatgpt_plugin_debug.mjs',
  '../tools/connect_chatgpt_home_center_fast.sh',
  '../tools/chatgpt_connector_acceptance_gate.mjs',
  '../tools/shizuku_live_playwright_chatgpt_home_center.sh',
];
for (const retiredPath of retiredConnectorPaths) assert.equal(fs.existsSync(new URL(retiredPath, import.meta.url)), false, retiredPath + ' must stay deleted');
const chromeSeed = fs.readFileSync(new URL('../functions/app_control_seed/com.android.chrome.150.0.7871.114+787111433.json', import.meta.url), 'utf8');
assert.doesNotMatch(chromeSeed, /chatgptCommandCenterConnector|plugin_asdk_app|Command Center connector/i);
assert.match(docs, /Playwright is an essential Home Center app function/);
assert.match(docs, /Amazon is not prioritized/);
assert.match(docs, /Debian\/proot/);
assert.match(docs, /not the acceptance target/);
console.log('Browser worker contract test: OK');
