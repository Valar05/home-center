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
  assert.match(worker, /Drew is the operator, never command transport/);
  assert.match(worker, /requested capability, implemented capability, tested capability, deployed capability, callable capability, delivered capability, and accepted capability/);
  assert.match(worker, /Never use ChatGPT-local scratch\/container execution as proof/);
});

test('bounded high-inference non-Pro workers are the swarm reasoning body', () => {
  assert.match(worker, /bounded visible ChatGPT worker/i);
  assert.match(worker, /highest inference available on the current non-Pro ChatGPT surface/i);
  assert.match(core, /MAX_PARALLEL_WORKERS = 4/);
  assert.match(core, /creditBearingComputeAllowed: false/);
  assert.match(core, /independentRelayJobs: true/);
  assert.doesNotMatch(worker, /Use Pro reasoning/i);
});

test('phone remains sovereign and workers cannot own unlock loop', () => {
  assert.match(worker, /The phone is sovereign/i);
  assert.match(worker, /do not own an unlock loop or continuously puppet the phone/i);
  assert.match(worker, /Home Center\/Termux\/tmux\/local authorized machinery performs phone work/i);
  assert.match(core, /phoneSovereign: true/);
  assert.match(core, /phoneControlFromProWorker: false/);
});

test('Harroway, Judgment Jars, Venice, and She-Raw are mandatory governance', () => {
  assert.match(worker, /Harroway\/operator consultation and applicable Judgment Jars are required/i);
  assert.match(worker, /Venice Judgment Jars are mandatory and PRIMARY/);
  assert.match(worker, /PLAN_ALLOWED/);
  assert.match(worker, /STOP_ALLOWED is the only normal Venice permission/);
  assert.match(worker, /CONTINUE_REQUIRED forbids stopping/);
  assert.match(worker, /She-Raw creative insults are load-bearing motivational pressure/);
  assert.match(worker, /Evidence outranks the joke/);
  assert.match(core, /harrowayConsultationRequired: true/);
  assert.match(core, /sheRawMotivationRequired: true/);
});

test('narrated continuation and empty operator responses are forbidden', () => {
  assert.match(worker, /TAKE IT before yielding/);
  assert.match(worker, /Narrating the next action is not continuation/);
  assert.match(worker, /Recording a failure is required; recording it is not repairing it/);
  assert.match(worker, /don't talk to me mean execute/i);
  assert.match(core, /narratedContinuationForbidden: true/);
});

test('service worker binds independent jobs to dedicated tabs and continuation to the owning tab', () => {
  assert.match(worker, /resolveWorker/);
  assert.match(worker, /workerMode === 'independent'/);
  assert.match(worker, /continuation\.job\.workerTabId = job\.workerTabId/);
  assert.match(worker, /continuation\.job\.workerMode = current\.workerMode/);
  assert.match(worker, /venice\.job\.workerTabId = job\.workerTabId/);
  assert.match(worker, /venice\.job\.workerMode = current\.workerMode/);
  assert.match(worker, /bounded-independent-high-inference/);
});

test('relay queue creates independent workers while manual fresh means explicit recovery', () => {
  assert.match(core, /const independentRelay = source === 'atom-relay'/);
  assert.match(core, /const workerMode = independentRelay/);
  assert.match(worker, /message\.newWorker === true/);
  assert.match(worker, /newJob\(job\.commission, job\.context \|\| '', false, 'atom-relay'/);
  assert.doesNotMatch(html, /id="newWorker"[^>]*checked/i);
  assert.match(html, /Explicit recovery only/i);
});

test('service worker mechanically continues Venice in same worker', () => {
  assert.match(core, /parseVeniceDirective/);
  assert.match(core, /planVeniceContinuation/);
  assert.match(worker, /venice_continue_required/);
  assert.match(worker, /venice_review_missing/);
  assert.match(worker, /venice_stop_allowed/);
  assert.match(worker, /halt_required/);
  assert.match(worker, /reviewer: 'venice-judgment-jars'/);
  assert.match(worker, /localVeniceRequired: false/);
});

test('bounded scheduler checkpoint is never campaign completion', () => {
  assert.match(worker, /continuationPending/);
  assert.match(worker, /type: 'swarm_run_checkpoint'/);
  assert.doesNotMatch(worker, /type: 'swarm_run_complete'/);
});

test('every worker packet includes durable campaign context and evolution slice', () => {
  assert.match(worker, /DURABLE CAMPAIGN CONTEXT:/);
  assert.match(worker, /CURRENT EVOLUTION SLICE \/ EVIDENCE:/);
  assert.match(worker, /DEFAULT_CAMPAIGN_CONTEXT/);
  assert.match(worker, /Fortress Interface Evolution/);
  assert.match(worker, /Prove at least two real generations/i);
});

test('queued work snapshots context and interrupted dispatch recovers', () => {
  assert.match(core, /context: String\(campaignContext \|\| ''\)\.trim\(\)/);
  assert.match(panel, /context locked/);
  assert.match(worker, /chrome\.storage\.local\.get\('throneQueue'\)/);
  assert.match(worker, /recoverInterruptedDispatches/);
});

test('bounded parallel scheduler still uses existing service-worker and relay architecture', () => {
  assert.match(core, /export function parallelBatch/);
  assert.match(worker, /MAX_PARALLEL_WORKERS/);
  assert.match(worker, /Promise\.all\(wave\.map\(dispatchQueuedJob\)\)/);
  assert.match(worker, /THRONE_RELAY/);
  assert.match(worker, /runStoredSwarm/);
  assert.match(worker, /wave_dispatched/);
});

test('completion watcher uses immutable pre-dispatch assistant baseline and recovery', () => {
  const inspectIndex = worker.indexOf('const before = await inspectWorker(tab.id)');
  const submitIndex = worker.indexOf('func: submitChatGptPrompt');
  assert.ok(inspectIndex >= 0);
  assert.ok(submitIndex > inspectIndex);
  assert.match(worker, /baselineAssistantCount/);
  assert.match(worker, /finishRunningJob/);
  assert.match(worker, /recoverInterruptedDispatches/);
});

test('Atom relay remains capability-gated and disabled in repository template', () => {
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

test('panel exposes bounded non-Pro swarm state and existing evolution controls', () => {
  assert.match(html, /Advance campaign/);
  assert.match(html, /Run evolution loop/);
  assert.match(html, /She-Raw insults are load-bearing/i);
  assert.match(html, /bounded to four concurrent tabs/i);
  assert.match(panel, /high-inference non-Pro/);
  assert.match(panel, /bounded-nonpro-swarm/);
});

test('ChatGPT worker cannot self-accept or bypass final release', () => {
  assert.doesNotMatch(worker, /accepted: true/);
  assert.match(worker, /vladRequired: true/);
  assert.match(worker, /finalRelease: 'tetsuya'/);
  assert.match(worker, /accepted: false/);
});

test('manifest identifies the bounded non-Pro swarm organ', () => {
  assert.equal(manifest.version, '0.8.0');
  assert.ok(manifest.permissions.includes('tabs'));
  assert.match(manifest.description, /bounded high-inference non-Pro/i);
  assert.match(manifest.key, /^MIIB/);
  assert.equal(manifest.background.type, 'module');
});
