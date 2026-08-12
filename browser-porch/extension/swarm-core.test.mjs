import test from 'node:test';
import assert from 'node:assert/strict';
import {HANDOFF_FIELDS, MAX_SWARM_SLICES, mergeHandoffContext, newJob, parseHandoff, planHandoffContinuation} from './swarm-core.mjs';

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

test('manual job requires a real bounded commission', () => {
  assert.throws(() => newJob('   ', 'ctx'), /commission_required/);
  const job = newJob('prove one thing', 'ctx', true, 'manual', 'manual-1');
  assert.equal(job.commission, 'prove one thing');
  assert.equal(job.context, 'ctx');
});

test('swarm hard cap stays bounded', () => {
  assert.equal(MAX_SWARM_SLICES, 12);
});
