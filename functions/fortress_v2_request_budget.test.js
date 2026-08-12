'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { planRequests, guardRequest, onRateLimit } = require('./fortress_v2_request_budget');

test('deduplicates unknowns and skips fresh cached facts', () => {
  const p = planRequests({ materialUnknowns:['sha','sha','desktop'], cachedFacts:['desktop'], requiredWrites:['module'], requiredVerifications:['readback'] });
  assert.deepEqual(p.reads, ['sha']);
  assert.equal(p.maxRequests, 3);
});

test('forbids duplicate fresh read', () => {
  const r = guardRequest([{kind:'read',target:'x',intent:'state',resultFresh:true}], {kind:'read',target:'x',intent:'state'});
  assert.deepEqual(r, {allowed:false, reason:'fresh_equivalent_result_exists'});
});

test('forbids blind retry', () => {
  const r = guardRequest([], {kind:'write',target:'x',intent:'mutate',retry:true,changedStrategy:false});
  assert.equal(r.allowed, false);
  assert.equal(r.reason, 'blind_retry_forbidden');
});

test('forbids meaningless polling', () => {
  const r = guardRequest([], {kind:'poll',target:'ci',intent:'status',stateCanChange:false});
  assert.equal(r.allowed, false);
  assert.equal(r.reason, 'meaningless_poll_forbidden');
});

test('rate limit backs off without abandoning mission', () => {
  const r = onRateLimit({remaining:['test','shadow']});
  assert.equal(r.action, 'continue');
  assert.equal(r.retryMode, 'backoff');
  assert.equal(r.reduceRequests, true);
  assert.equal(r.preserveMission, true);
});
