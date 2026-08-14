import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HANDOFF_FIELDS,
  MAX_SWARM_SLICES,
  MAX_PARALLEL_WORKERS,
  WORKER_DOCTRINE,
  WORKER_REASONING_MODE,
  mergeHandoffContext,
  newJob,
  parseHandoff,
  parseVeniceDirective,
  planHandoffContinuation,
  planVeniceContinuation,
} from './swarm-core.mjs';

const VALID = `HANDOFF\n\nDURABLE CONTEXT\nIssue #48: safe writing-document rename/move.\n\nCOMPLETED EVIDENCE\nProvider rename and move preserved file ID and content.\n\nCURRENT SLICE\nPlanner routing and human-readable confirmation.\n\nUNMET ACCEPTANCE\nProve natural-language planner route and cleanup scratch.\n\nACTIVE CONSTRAINTS\nNo raw IDs in user-facing confirmation. Preserve source content.\n\nEXACT NEXT ACTION\nRun the rename/move planner regression and verify the destination name appears in confirmation.`;

test('valid six-field handoff parses in order', () => {
  const handoff = parseHandoff(VALID);
  assert.ok(handoff);
  assert.deepEqual(Object.keys(handoff), [...HANDOFF_FIELDS]);
});

test('missing or empty field fails closed', () => {
  assert.equal(parseHandoff(VALID.replace(/ACTIVE CONSTRAINTS[\s\S]*?EXACT NEXT ACTION/, 'EXACT NEXT ACTION')), null);
  assert.equal(parseHandoff(VALID.replace('CURRENT SLICE\nPlanner routing and human-readable confirmation.', 'CURRENT SLICE\n\n')), null);
});

test('handoff continuation remains in the persistent Pro worker', () => {
  const continuation = planHandoffContinuation('CAMPAIGN BASE', VALID, 'job-fixed');
  assert.ok(continuation);
  assert.equal(continuation.job.id, 'job-fixed');
  assert.equal(continuation.job.newWorker, false);
  assert.equal(continuation.job.source, 'handoff');
  assert.equal(continuation.job.commission, continuation.handoff['EXACT NEXT ACTION']);
});

test('fresh worker rotation is explicit recovery only', () => {
  assert.equal(newJob('normal', 'ctx', true, 'manual').newWorker, false);
  assert.equal(newJob('relay', 'ctx', true, 'atom-relay').newWorker, false);
  assert.equal(newJob('recover', 'ctx', true, 'explicit-recovery').newWorker, true);
});

test('durable context is bounded and omits next action from history', () => {
  const handoff = parseHandoff(VALID);
  const context = mergeHandoffContext('x'.repeat(30000), handoff, 24000);
  assert.ok(context.length <= 24000);
  assert.doesNotMatch(context, /EXACT NEXT ACTION:/);
});

test('worker doctrine binds single Pro, phone sovereignty, Harroway, and She-Raw', () => {
  const job = newJob('prove one thing', 'ctx');
  assert.equal(job.workerDoctrine.reasoningMode, 'Pro reasoning');
  assert.equal(WORKER_REASONING_MODE, 'Pro reasoning');
  assert.equal(MAX_PARALLEL_WORKERS, 1);
  assert.equal(WORKER_DOCTRINE.singlePersistentProWorker, true);
  assert.equal(WORKER_DOCTRINE.phoneSovereign, true);
  assert.equal(WORKER_DOCTRINE.phoneControlFromProWorker, false);
  assert.equal(WORKER_DOCTRINE.harrowayConsultationRequired, true);
  assert.equal(WORKER_DOCTRINE.sheRawMotivationRequired, true);
  assert.equal(WORKER_DOCTRINE.narratedContinuationForbidden, true);
  assert.equal(WORKER_DOCTRINE.localVeniceRequired, false);
});

test('Venice parser uses final explicit directive', () => {
  assert.equal(parseVeniceDirective('DIRECTIVE: CONTINUE_REQUIRED'), 'CONTINUE_REQUIRED');
  assert.equal(parseVeniceDirective('DIRECTIVE: CONTINUE_REQUIRED\nwork\nDIRECTIVE: STOP_ALLOWED'), 'STOP_ALLOWED');
  assert.equal(parseVeniceDirective('no review here'), null);
});

test('CONTINUE_REQUIRED stays in same Pro conversation and demands action', () => {
  const continuation = planVeniceContinuation('CAMPAIGN BASE', 'DIRECTIVE: CONTINUE_REQUIRED', 'venice-next');
  assert.equal(continuation.directive, 'CONTINUE_REQUIRED');
  assert.equal(continuation.job.newWorker, false);
  assert.match(continuation.job.commission, /same Pro worker conversation/i);
  assert.match(continuation.job.commission, /take it now instead of narrating it/i);
  assert.match(continuation.job.commission, /She-Raw.*roast/i);
});

test('missing Venice review does not become permission to stop', () => {
  const continuation = planVeniceContinuation('CAMPAIGN BASE', 'implementation finished but no review');
  assert.equal(continuation.directive, 'MISSING');
  assert.equal(continuation.job.newWorker, false);
  assert.match(continuation.job.commission, /Only STOP_ALLOWED permits normal stopping/);
});

test('STOP_ALLOWED and HALT_REQUIRED create no continuation', () => {
  assert.equal(planVeniceContinuation('ctx', 'DIRECTIVE: STOP_ALLOWED').job, null);
  assert.equal(planVeniceContinuation('ctx', 'DIRECTIVE: HALT_REQUIRED').job, null);
});

test('campaign cap is bounded without implying mission stop', () => {
  assert.equal(MAX_SWARM_SLICES, 12);
  assert.equal(WORKER_DOCTRINE.responseBoundaryIsStop, false);
});
