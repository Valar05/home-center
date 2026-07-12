#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';

const repoRoot = path.resolve(new URL('..', import.meta.url).pathname);
const profile = JSON.parse(fs.readFileSync(path.join(repoRoot, 'functions/app_control_seed/com.android.chrome.150.0.7871.114+787111433.json'), 'utf8'));
assert(profile.workflows.chatgptCommandCenterConnector, 'Chrome seed must include ChatGPT connector workflow');
const workflow = profile.workflows.chatgptCommandCenterConnector;
assert.match(workflow.intent, /Command Center connector/);
assert(workflow.preferredPath.some((step) => /approval prompts/.test(step)), 'workflow must remember approval prompts kill the frame');
assert(workflow.preferredPath.some((step) => /force-stop com\.openai\.chatgpt/.test(step)), 'workflow must quarantine installed ChatGPT app callback');
assert(workflow.successSignals.some((step) => /connected to dclarke1005@gmail\.com/i.test(step)), 'workflow must gate on connected-state evidence');
assert(profile.failureFixes.some((fix) => /Codex approval prompt/.test(fix.symptom || '')), 'profile must include approval prompt failure fix');

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'chatgpt-frame-learn-'));
const evidenceDir = path.join(tempDir, 'evidence');
fs.mkdirSync(evidenceDir);
fs.writeFileSync(path.join(evidenceDir, 'screen_promptfree_after_callback_restore_chrome.png'), 'fake');
const output = execFileSync('node', ['tools/learn_chatgpt_connector_frame_lane.mjs', '--evidence-dir', evidenceDir, '--out-dir', tempDir, '--run-id', 'contract-test', '--dry-run', '--json'], {cwd: repoRoot, encoding: 'utf8'}).trim();
const parsed = JSON.parse(output);
assert.equal(parsed.ok, true);
assert.deepEqual(parsed.operations, ['app_control.put_profile', 'app_control.record_run', 'browser_sessions.record_episode']);
const envelope = JSON.parse(fs.readFileSync(parsed.envelopePath, 'utf8'));
assert.equal(envelope.operations[0].operation, 'app_control.put_profile');
assert.equal(envelope.operations[0].args.profile.workflows.chatgptCommandCenterConnector.metricsBaseline.targetNextRunElapsedMs, 5000);
assert.equal(envelope.operations[1].args.frameLane.wholePhoneFallbackAllowed, false);
assert.equal(envelope.operations[1].args.frameLane.approvalPromptsForbiddenDuringFrame, true);
assert.match(envelope.operations[2].args.visibleTextSummary, /connected to dclarke1005@gmail\.com/i);
assert.match(parsed.submitStdout, /app_control\.put_profile/);
console.log('ChatGPT connector frame learning contract test: OK');
