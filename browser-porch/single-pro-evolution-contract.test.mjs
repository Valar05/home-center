import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  MAX_PARALLEL_WORKERS,
  WORKER_REASONING_MODE,
  WORKER_DOCTRINE,
  newJob,
  parallelBatch,
  planHandoffContinuation,
  planVeniceContinuation,
} from './extension/swarm-core.mjs';

const panel = readFileSync(new URL('./extension/throne-panel.mjs', import.meta.url), 'utf8');
const html = readFileSync(new URL('./extension/sidepanel.html', import.meta.url), 'utf8');
const memory = readFileSync(new URL('../skills/venice-review-memory/SKILL.md', import.meta.url), 'utf8');
const serviceWorker = readFileSync(new URL('./extension/service-worker.js', import.meta.url), 'utf8');

const HANDOFF = `DURABLE CONTEXT:\nctx\nCOMPLETED EVIDENCE:\nevidence\nCURRENT SLICE:\nslice\nUNMET ACCEPTANCE:\nunmet\nACTIVE CONSTRAINTS:\nconstraints\nEXACT NEXT ACTION:\nadvance`;

function assertContains(haystack, needle) {
  assert.ok(haystack.includes(needle), `missing: ${needle}`);
}

test('Chromium Throne has exactly one normal Pro worker lane', () => {
  assert.equal(MAX_PARALLEL_WORKERS, 1);
  assert.equal(WORKER_REASONING_MODE, 'Pro reasoning');
  assert.equal(WORKER_DOCTRINE.singlePersistentProWorker, true);
  assert.equal(WORKER_DOCTRINE.phoneSovereign, true);
  assert.equal(WORKER_DOCTRINE.phoneControlFromProWorker, false);
  assert.equal(WORKER_DOCTRINE.harrowayConsultationRequired, true);
  assert.equal(WORKER_DOCTRINE.sheRawMotivationRequired, true);
  assert.equal(WORKER_DOCTRINE.narratedContinuationForbidden, true);
  const jobs = [newJob('a', 'ctx'), newJob('b', 'ctx'), newJob('c', 'ctx')];
  assert.equal(parallelBatch(jobs, 99).length, 1);
});

test('worker rotation is explicit recovery only', () => {
  assert.equal(newJob('normal', 'ctx', true, 'manual').newWorker, false);
  assert.equal(newJob('relay', 'ctx', true, 'atom-relay').newWorker, false);
  assert.equal(newJob('recovery', 'ctx', true, 'explicit-recovery').newWorker, true);
  assert.doesNotMatch(html, /id="newWorker"[^>]*checked/i);
  assertContains(html, 'Explicit recovery only: rotate into a fresh worker conversation');
  assertContains(panel, "newWorker.checked ? 'explicit-recovery' : 'manual'");
});

test('handoff and Venice continuation stay in the same Pro conversation', () => {
  const handoff = planHandoffContinuation('base', HANDOFF);
  assert.ok(handoff);
  assert.equal(handoff.job.newWorker, false);
  const continuePlan = planVeniceContinuation('base', 'DIRECTIVE: CONTINUE_REQUIRED');
  assert.equal(continuePlan.job.newWorker, false);
  assert.match(continuePlan.job.commission, /same Pro worker conversation/i);
  assert.match(continuePlan.job.commission, /take it now instead of narrating it/i);
  assert.match(continuePlan.job.commission, /She-Raw.*roast/i);
});

test('campaign seed binds the actual evolution loop and phone sovereignty', () => {
  for (const phrase of [
    'one visible authenticated ChatGPT Pro worker',
    'Pro worker never owns an unlock/continuous-phone-control loop',
    'Harroway/operator consultation',
    'creative insults are load-bearing motivational pressure',
    "don't talk to me means execute",
    'Prove at least two successful generations',
    'GitHub source is not phone-runtime proof',
  ]) assertContains(panel, phrase);
});

test('all paid-for failures are durable scars with She-Raw pressure', () => {
  const scars = [
    'Bootstrap dependency failure dumped back to operator',
    'Shell quoting and heredoc captivity',
    'Foreground worker took the operator shell hostage',
    'Invisible liveness',
    'Adam-only operation',
    'Giant prompt truncation',
    'Prompt mistaken for executable handoff',
    'Status panel substituted for capability',
    'Failure record substituted for repair',
    'Wrong/stale architecture seam',
    'Architecture recommendation without required consultation',
    'Narrated continuation substituted for execution',
    'Dead joke substituted for worker motivation',
    'Operator imperative misread as permission to stop',
  ];
  for (const scar of scars) assertContains(memory, `### ${scar}`);
  const roastCount = (memory.match(/She-Raw roast:/g) || []).length;
  assert.ok(roastCount >= 14, `expected >=14 load-bearing roasts, got ${roastCount}`);
  assertContains(memory, 'A cattle prod wired to nothing is just an ugly stick');
  assertContains(memory, 'museum butcher');
  assertContains(memory, 'tiny emperor');
});

test('current service worker still consumes single-worker core rather than a replacement control plane', () => {
  assert.match(serviceWorker, /MAX_PARALLEL_WORKERS/);
  assert.match(serviceWorker, /parallelBatch\(throneQueue, Math\.min\(MAX_PARALLEL_WORKERS/);
  assert.match(serviceWorker, /THRONE_RELAY/);
  assert.match(serviceWorker, /runStoredSwarm/);
  assert.doesNotMatch(panel, /Phone Hands.*unlock/i);
});

test('Harroway semantics remain consequence without confiscation and proof laundering', () => {
  assert.match(panel, /GOVERNANCE: Harroway\/operator consultation/i);
  assert.match(panel, /requested \/ implemented \/ tested \/ deployed \/ callable \/ delivered \/ accepted remain distinct/i);
  assert.match(panel, /Home Center\/Termux\/tmux\/local authorized machinery performs phone actions/i);
});
