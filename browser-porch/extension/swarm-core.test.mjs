import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HANDOFF_FIELDS,
  MAX_SWARM_SLICES,
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
  assert.match(handoff['COMPLETED EVIDENCE'], /preserved file ID and content/);
  assert.match(handoff['EXACT NEXT ACTION'], /planner regression/);
});

test('missing or empty field fails closed', () => {
  assert.equal(parseHandoff(VALID.replace(/ACTIVE CONSTRAINTS[\s\S]*?EXACT NEXT ACTION/, 'EXACT NEXT ACTION')), null);
  assert.equal(parseHandoff(VALID.replace('CURRENT SLICE\nPlanner routing and human-readable confirmation.', 'CURRENT SLICE\n\n')), null);
});

test('handoff continuation rotates into a fresh bounded job', () => {
  const continuation = planHandoffContinuation('CAMPAIGN BASE', VALID, 'job-fixed');
  assert.ok(continuation);
  assert.equal(continuation.job.id, 'job-fixed');
  assert.equal(continuation.job.newWorker, true);
  assert.equal(continuation.job.source, 'handoff');
  assert.equal(continuation.job.state, 'queued');
  assert.equal(continuation.job.commission, continuation.handoff['EXACT NEXT ACTION']);
  assert.match(continuation.context, /LATEST WORKER HANDOFF/);
  assert.match(continuation.context, /COMPLETED EVIDENCE/);
  assert.match(continuation.context, /ACTIVE CONSTRAINTS/);
});

test('durable context is bounded and does not append next action as history', () => {
  const handoff = parseHandoff(VALID);
  const context = mergeHandoffContext('x'.repeat(30000), handoff, 24000);
  assert.ok(context.length <= 24000);
  assert.doesNotMatch(context, /EXACT NEXT ACTION:/);
});

test('manual job requires a real bounded commission and carries worker doctrine', () => {
  assert.throws(() => newJob('   ', 'ctx'), /commission_required/);
  const job = newJob('prove one thing', 'ctx', true, 'manual', 'manual-1');
  assert.equal(job.commission, 'prove one thing');
  assert.equal(job.context, 'ctx');
  assert.equal(job.workerDoctrine.reasoningMode, 'Pro reasoning');
  assert.equal(job.workerDoctrine.veniceReviewMode, 'judgment_jar_emulation');
  assert.equal(job.workerDoctrine.veniceReviewSemantics, 'primary-judgment-jar');
  assert.equal(job.workerDoctrine.stopGate, 'STOP_ALLOWED');
  assert.equal(job.workerDoctrine.responseBoundaryIsStop, false);
  assert.equal(WORKER_REASONING_MODE, 'Pro reasoning');
  assert.equal(WORKER_DOCTRINE.localVeniceRequired, false);
});

test('Venice parser uses the final explicit completion directive', () => {
  assert.equal(parseVeniceDirective('DIRECTIVE: CONTINUE_REQUIRED'), 'CONTINUE_REQUIRED');
  assert.equal(parseVeniceDirective('DIRECTIVE: CONTINUE_REQUIRED\nwork\nDIRECTIVE: STOP_ALLOWED'), 'STOP_ALLOWED');
  assert.equal(parseVeniceDirective('no review here'), null);
});

test('CONTINUE_REQUIRED creates a fresh successor for the same commissioned slice', () => {
  const continuation = planVeniceContinuation('CAMPAIGN BASE', 'VERDICT: FAIL\nDIRECTIVE: CONTINUE_REQUIRED\nFINDING: repair the listener', 'venice-next');
  assert.equal(continuation.directive, 'CONTINUE_REQUIRED');
  assert.ok(continuation.job);
  assert.equal(continuation.job.id, 'venice-next');
  assert.equal(continuation.job.source, 'venice-continue');
  assert.match(continuation.job.commission, /Continue the SAME bounded commissioned slice/);
  assert.match(continuation.context, /LATEST WORKER CHECKPOINT/);
});

test('missing Venice review does not become permission to stop', () => {
  const continuation = planVeniceContinuation('CAMPAIGN BASE', 'implementation finished but no review');
  assert.equal(continuation.directive, 'MISSING');
  assert.ok(continuation.job);
  assert.equal(continuation.job.source, 'venice-missing-review');
  assert.match(continuation.job.commission, /Only STOP_ALLOWED permits normal stopping/);
});

test('STOP_ALLOWED and HALT_REQUIRED do not create continuation jobs', () => {
  const stopped = planVeniceContinuation('ctx', 'VERDICT: PASS\nDIRECTIVE: STOP_ALLOWED');
  const halted = planVeniceContinuation('ctx', 'VERDICT: FAIL\nDIRECTIVE: HALT_REQUIRED');
  assert.equal(stopped.directive, 'STOP_ALLOWED');
  assert.equal(stopped.job, null);
  assert.equal(halted.directive, 'HALT_REQUIRED');
  assert.equal(halted.job, null);
});

test('swarm hard cap stays bounded without implying mission stop', () => {
  assert.equal(MAX_SWARM_SLICES, 12);
  assert.equal(WORKER_DOCTRINE.responseBoundaryIsStop, false);
});
