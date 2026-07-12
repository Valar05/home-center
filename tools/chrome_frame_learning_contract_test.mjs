#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {buildChromeFrameLearningEnvelope} from './chrome_frame_learning_envelope.mjs';

const repoRoot = path.resolve(new URL('..', import.meta.url).pathname);
const launcher = fs.readFileSync(path.join(repoRoot, 'tools/launch_chatgpt_chrome_frame.sh'), 'utf8');
const submitter = fs.readFileSync(path.join(repoRoot, 'tools/submit_chrome_frame_learning.mjs'), 'utf8');
const appControlDoc = fs.readFileSync(path.join(repoRoot, 'docs/APP_CONTROL_BUCKET.md'), 'utf8');
const browserDoc = fs.readFileSync(path.join(repoRoot, 'docs/BROWSER_HANDS.md'), 'utf8');
const debugDoc = fs.readFileSync(path.join(repoRoot, 'docs/CHATGPT_PLUGIN_INSTALL_DEBUG.md'), 'utf8');

assert.match(launcher, /chrome_frame_learning_envelope\.mjs/);
assert.match(launcher, /Learning:/);
assert.match(launcher, /--windowingMode 5/);
assert.match(launcher, /activity-reorder-to-front -n com\.termux/);
assert.match(submitter, /command_center_operation/);
assert.match(submitter, /HOME_CENTER_MCP_BEARER_TOKEN/);
assert.match(submitter, /codex-hub\.json/);
assert.match(appControlDoc, /Termux and Home Center are different inputs to the same code path/);
assert.match(appControlDoc, /app_control\.record_run/);
assert.match(browserDoc, /Real Android Chrome frame discoveries belong to the same Home Center browser-hands learning path/);
assert.match(browserDoc, /browser_sessions\.record_episode/);
assert.match(debugDoc, /chrome_frame_<runId>\.learning\.json/);

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-frame-learning-'));
const evidencePath = path.join(tempDir, 'chrome_frame_test.txt');
fs.writeFileSync(evidencePath, [
  'runId=test-frame',
  'url=https://chatgpt.com/',
  'rule=bounded_chrome_frame_only',
  'RootTask windowingMode=freeform bounds=[449,867][997,1947]',
  'mCurrentFocus=Window{u0 com.termux/com.termux.app.TermuxActivity}',
  'status=bounded_frame_active',
].join('\n'));

const envelope = buildChromeFrameLearningEnvelope({evidence: evidencePath, runId: 'test-frame', url: 'https://chatgpt.com/', status: 'bounded_frame_active'});
assert.equal(envelope.homeCenterOwnership.sharedCodePath, 'command_center_operation');
assert.equal(envelope.homeCenterOwnership.termuxRole, 'input runner and local debugger');
assert.deepEqual(envelope.operations.map((op) => op.operation), ['app_control.record_run', 'browser_sessions.record_episode']);
assert.equal(envelope.operations[0].args.frameLane.wholePhoneFallbackAllowed, false);
assert.equal(envelope.operations[0].args.frameLane.requiresUserRespectedSubframe, true);
assert.equal(envelope.operations[0].args.frameLane.verifiedBounded, true);
assert.equal(envelope.operations[1].args.discoveryCandidates.length, 2);

const envelopePath = path.join(tempDir, 'chrome_frame_test.learning.json');
fs.writeFileSync(envelopePath, JSON.stringify(envelope, null, 2) + '\n');
const dryRun = execFileSync('node', ['tools/submit_chrome_frame_learning.mjs', '--envelope', envelopePath, '--dry-run'], {cwd: repoRoot, encoding: 'utf8'});
assert.match(dryRun, /app_control\.record_run/);
assert.match(dryRun, /browser_sessions\.record_episode/);

console.log('Chrome frame learning contract test: OK');
