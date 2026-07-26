import assert from 'node:assert/strict';
import fs from 'node:fs';

const registry = JSON.parse(fs.readFileSync(new URL('../ops/worker_execution_contract.v1.json', import.meta.url), 'utf8'));
const doctrine = fs.readFileSync(new URL('../docs/RELIABLE_WORKER_EXECUTION_CONTRACT.md', import.meta.url), 'utf8');

assert.equal(registry.schemaVersion, 'home-center.worker-execution-contract.v1');
assert.deepEqual(registry.states.active, ['accepted', 'queued', 'leased', 'running', 'checkpointed', 'publishing']);
assert.deepEqual(registry.states.terminal, ['completed', 'failed', 'quarantined', 'cancelled']);
assert.equal(new Set([...registry.states.active, ...registry.states.terminal]).size, 10, 'states must be unique');

for (const field of ['requestId', 'operation', 'inputHash', 'executionPolicy', 'publicationPolicy']) {
  assert.ok(registry.requiredRequestFields.includes(field), `request contract missing ${field}`);
}
for (const field of ['jobId', 'requestId', 'inputHash', 'state', 'acceptedAt', 'statusResource', 'publicationPolicy', 'attachedToExistingJob']) {
  assert.ok(registry.requiredReceiptFields.includes(field), `receipt contract missing ${field}`);
}

assert.equal(registry.idempotency.sameRequestSameHash, 'attach');
assert.equal(registry.idempotency.sameRequestDifferentHash, 'reject');
assert.equal(registry.idempotency.conflictCode, 'REQUEST_ID_CONFLICT');
assert.equal(registry.lease.singleActiveHolder, true);
assert.equal(registry.lease.expiredMeansProviderDidNothing, false);
assert.equal(registry.checkpoint.requiredBeforeAndAfterIrreversibleBoundary, true);
assert.equal(registry.checkpoint.inlineLargeArtifacts, false);

for (const operationClass of ['safe_to_retry', 'idempotent_with_provider_key', 'ambiguous_cost_bearing', 'non_retryable']) {
  assert.ok(registry.providerOperationClasses.includes(operationClass), `provider classification missing ${operationClass}`);
}
assert.equal(registry.ambiguousCostBearingOutcome.state, 'quarantined');
assert.equal(registry.ambiguousCostBearingOutcome.automaticRetry, false);
assert.equal(registry.publication.publishToDriveFalseIsHardBoundary, true);
assert.equal(registry.publication.generationAndPublicationAreSeparateStages, true);
assert.equal(registry.contextProtection.boundedStatus, true);
assert.equal(registry.contextProtection.inlineLogs, false);
assert.equal(registry.contextProtection.inlineLargeArtifacts, false);

for (const forbidden of ['visual_acceptance', 'editorial_acceptance', 'audio_quality_acceptance', 'canon_acceptance', 'human_acceptance']) {
  assert.ok(registry.verification.workerMayNotClaim.includes(forbidden), `verification boundary missing ${forbidden}`);
}

for (const phrase of [
  'Long-running, expensive, externally billed, or failure-prone work returns a durable receipt',
  'A request ID identifies one exact intent',
  'Infrastructure retries must not become accidental billing retries',
  '`publishToDrive: false` forbids Drive copies',
  'Conversation context is not an operational log sink',
  'Terminal jobs cannot silently re-execute'
]) {
  assert.ok(doctrine.includes(phrase), `doctrine missing required rule: ${phrase}`);
}

console.log(JSON.stringify({
  ok: true,
  schemaVersion: registry.schemaVersion,
  activeStates: registry.states.active.length,
  terminalStates: registry.states.terminal.length,
  providerOperationClasses: registry.providerOperationClasses.length,
  referenceCandidate: registry.referenceCandidate
}, null, 2));
