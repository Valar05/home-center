'use strict';

function planRequests(input = {}) {
  const unknowns = Array.isArray(input.materialUnknowns) ? [...new Set(input.materialUnknowns.filter(Boolean))] : [];
  const cached = new Set(Array.isArray(input.cachedFacts) ? input.cachedFacts : []);
  const writes = Array.isArray(input.requiredWrites) ? [...new Set(input.requiredWrites.filter(Boolean))] : [];
  const verifications = Array.isArray(input.requiredVerifications) ? [...new Set(input.requiredVerifications.filter(Boolean))] : [];

  const reads = unknowns.filter((x) => !cached.has(x));
  return {
    reads,
    writes,
    verifications,
    maxRequests: reads.length + writes.length + verifications.length,
    policy: {
      reuseFreshResults: true,
      blindRetryForbidden: true,
      duplicateReadForbidden: true,
      pollOnlyWhenStateCanChange: true,
      rateLimitResponse: 'backoff_reduce_scope_continue',
    },
  };
}

function guardRequest(history = [], next = {}) {
  const key = `${next.kind || ''}:${next.target || ''}:${next.intent || ''}`;
  const duplicate = history.some((x) => `${x.kind || ''}:${x.target || ''}:${x.intent || ''}` === key && x.resultFresh !== false);
  if (duplicate) return { allowed: false, reason: 'fresh_equivalent_result_exists' };
  if (next.retry === true && !next.changedStrategy) return { allowed: false, reason: 'blind_retry_forbidden' };
  if (next.kind === 'poll' && next.stateCanChange !== true) return { allowed: false, reason: 'meaningless_poll_forbidden' };
  return { allowed: true };
}

function onRateLimit(plan = {}) {
  return {
    action: 'continue',
    retryMode: 'backoff',
    reduceRequests: true,
    reuseCachedResults: true,
    preserveMission: true,
    remainingWork: plan,
  };
}

if (require.main === module) {
  const assert = require('node:assert/strict');
  const p = planRequests({ materialUnknowns: ['branch sha', 'branch sha', 'desktop status'], cachedFacts: ['desktop status'], requiredWrites: ['budget module'], requiredVerifications: ['readback'] });
  assert.deepEqual(p.reads, ['branch sha']);
  assert.equal(p.maxRequests, 3);
  assert.equal(guardRequest([{kind:'read',target:'fileA',intent:'state',resultFresh:true}], {kind:'read',target:'fileA',intent:'state'}).allowed, false);
  assert.equal(guardRequest([], {kind:'read',target:'fileA',intent:'state',retry:true,changedStrategy:false}).allowed, false);
  assert.equal(guardRequest([], {kind:'poll',target:'ci',intent:'status',stateCanChange:false}).allowed, false);
  assert.equal(onRateLimit(p).action, 'continue');
  console.log('fortress_v2_request_budget self-test: PASS');
}

module.exports = { planRequests, guardRequest, onRateLimit };
