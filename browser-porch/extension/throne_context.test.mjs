import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const worker = fs.readFileSync(path.join(HERE, 'service-worker.js'), 'utf8');
const panel = fs.readFileSync(path.join(HERE, 'throne-panel.mjs'), 'utf8');
const core = fs.readFileSync(path.join(HERE, 'swarm-core.mjs'), 'utf8');
const relayConfig = fs.readFileSync(path.join(HERE, 'relay-config.mjs'), 'utf8');
const html = fs.readFileSync(path.join(HERE, 'sidepanel.html'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(HERE, 'manifest.json'), 'utf8'));

test('worker boot locks operator-handoff and evidence doctrine', () => {
  assert.match(worker, /PORTCULLIS LOCKED/);
  assert.match(worker, /Computer Hands is the desktop body/);
  assert.match(worker, /Phone Hands is the phone body/);
  assert.match(worker, /Drew's hands are the final fallback/);
  assert.match(worker, /requested capability, implemented capability, tested capability, deployed capability, callable capability, delivered capability, and accepted capability/);
  assert.match(worker, /Never use ChatGPT-local scratch\/container execution as proof/);
});

test('Instant workers are bounded slices, not campaign brains', () => {
  assert.match(worker, /chat-mode Instant execution worker/);
  assert.match(worker, /one bounded bite/i);
  assert.match(worker, /Work ONE small feature, repair, proof, or acceptance slice at a time/);
  assert.match(worker, /No Great War/);
  assert.match(worker, /Be usefully needy/);
});

test('service worker owns handoff rotation and the panel is only a client', () => {
  for (const field of ['DURABLE CONTEXT', 'COMPLETED EVIDENCE', 'CURRENT SLICE', 'UNMET ACCEPTANCE', 'ACTIVE CONSTRAINTS', 'EXACT NEXT ACTION']) {
    assert.match(worker, new RegExp(field));
    assert.match(core, new RegExp(field));
  }
  assert.match(core, /planHandoffContinuation/);
  assert.match(worker, /planHandoffContinuation/);
  assert.match(worker, /state: 'handed_off'/);
  assert.match(worker, /assistant_completion_timeout/);
  assert.match(panel, /type: 'throne\.swarm\.run'/);
  assert.doesNotMatch(panel, /Promise\.all\(wave\.map/);
});

test('every worker packet includes durable campaign context before bounded commission', () => {
  assert.match(worker, /DURABLE CAMPAIGN CONTEXT:/);
  assert.match(worker, /COMMISSION — ONE BOUNDED SLICE:/);
  assert.match(worker, /DEFAULT_CAMPAIGN_CONTEXT/);
  assert.match(worker, /Atom\/Vlad on the phone is the operator surface/);
});

test('queued work snapshots context and remains durable in storage', () => {
  assert.match(core, /context: String\(campaignContext \|\| ''\)\.trim\(\)/);
  assert.match(panel, /context locked/);
  assert.match(worker, /chrome\.storage\.local\.get\('throneQueue'\)/);
  assert.match(worker, /recoverInterruptedDispatches/);
});

test('swarm has an explicit bounded parallel worker pool in the service worker', () => {
  assert.match(core, /export const MAX_PARALLEL_WORKERS = 8/);
  assert.match(core, /export function parallelBatch/);
  assert.match(worker, /MAX_PARALLEL_WORKERS/);
  assert.match(worker, /Promise\.all\(wave\.map\(dispatchQueuedJob\)\)/);
  assert.match(worker, /workerTabId/);
  assert.match(worker, /wave_dispatched/);
});

test('workers have independent visible ChatGPT tab identities', () => {
  assert.match(worker, /chrome\.tabs\.create\(\{url: `\$\{CHATGPT_ORIGIN\}\//);
  assert.match(worker, /active: false/);
  assert.match(worker, /throneWorkers/);
  assert.match(worker, /workerTabSummaries/);
  assert.match(worker, /type: 'commission_sent'/);
  assert.match(worker, /jobId/);
  assert.match(worker, /tabId/);
});

test('completion watcher uses immutable pre-dispatch assistant baseline and restart recovery', () => {
  const inspectIndex = worker.indexOf('const before = await inspectWorker(tab.id)');
  const submitIndex = worker.indexOf('func: submitChatGptPrompt');
  assert.ok(inspectIndex >= 0, 'worker must inspect before dispatch');
  assert.ok(submitIndex > inspectIndex, 'baseline inspection must precede prompt submission');
  assert.match(worker, /baselineAssistantCount/);
  assert.match(worker, /finishRunningJob/);
  assert.match(worker, /recoverInterruptedDispatches/);
  assert.match(worker, /job\.state === 'running'/);
});

test('Atom relay is capability-gated and disabled in repository template', () => {
  assert.match(worker, /THRONE_RELAY/);
  assert.match(worker, /authorization: `Bearer \$\{THRONE_RELAY\.capability\}`/);
  assert.match(worker, /\/command/);
  assert.match(worker, /\/complete/);
  assert.match(worker, /\/snapshot/);
  assert.match(relayConfig, /enabled: false/);
  assert.match(relayConfig, /capability: ''/);
  assert.ok(manifest.permissions.includes('alarms'));
  assert.ok(manifest.host_permissions.includes('http://127.0.0.1:9234/*'));
  assert.equal(manifest.background.type, 'module');
});

test('bounded swarm still uses modular handoff core', () => {
  assert.match(html, /id="runSwarm"/);
  assert.match(worker, /MAX_SWARM_SLICES/);
  assert.match(worker, /planHandoffContinuation/);
  assert.match(core, /export const MAX_SWARM_SLICES = 12/);
  assert.match(core, /parseHandoff/);
  assert.match(core, /mergeHandoffContext/);
});

test('ChatGPT cannot be the terminal review gate', () => {
  assert.doesNotMatch(worker, /accepted: true/);
  assert.match(worker, /awaiting_venice_review/);
  assert.match(worker, /reviewer: 'venice-local'/);
  assert.match(worker, /independentOfChatGPT: true/);
  assert.match(worker, /vladRequired: true/);
  assert.match(worker, /finalRelease: 'tetsuya'/);
  assert.match(worker, /accepted: false/);
});

test('manifest pins one visible multi-tab swarm identity', () => {
  assert.equal(manifest.version, '0.6.1');
  assert.ok(manifest.permissions.includes('tabs'));
  assert.match(manifest.description, /multi-tab ChatGPT worker pool/i);
  assert.match(manifest.key, /^MIIB/);
  assert.equal(manifest.background.type, 'module');
});
