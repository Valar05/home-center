'use strict';

const {
  ADAPTER_NAMES,
  READ_ONLY_OPERATIONS,
  SHA256,
  isRecord,
  requireText,
  requireSha,
  requireRfc3339,
  sha256
} = require('./contracts');

const PROBE_SCHEMA_VERSION = '1.0.0';
const PROBE_KIND = 'LOCAL_BROKER_PROBE';
const RESULT_KIND = 'LOCAL_BROKER_PROBE_RESULT';

function createProbe(input) {
  const probe = {
    schemaVersion: PROBE_SCHEMA_VERSION,
    kind: PROBE_KIND,
    mode: 'read_only',
    probeId: input.probeId,
    nonceHash: input.nonceHash,
    adapter: input.adapter,
    operation: input.operation,
    commission: { commissionId: input.commissionId, commissionHash: input.commissionHash },
    queue: {
      documentId: input.queueDocumentId,
      folderId: input.queueFolderId,
      revision: input.queueRevision,
      stateOwner: input.stateOwner
    },
    lane: { laneId: input.laneId, owner: input.laneOwner },
    worker: { workerId: input.workerId, identityHash: input.workerIdentityHash },
    issuedAt: input.issuedAt,
    expiresAt: input.expiresAt
  };
  if (input.adapter === 'browser_nerve') probe.browserIdentity = { accountId: input.accountId, conversationId: input.conversationId, cdpTargetId: input.cdpTargetId };
  const validation = validateProbe(probe);
  if (!validation.ok) throw new TypeError(validation.errors.join('; '));
  return deepFreeze(probe);
}

function validateProbe(probe) {
  const errors = [];
  if (!isRecord(probe)) return { ok: false, errors: ['probe must be a plain object'] };
  if (probe.schemaVersion !== PROBE_SCHEMA_VERSION) errors.push(`probe.schemaVersion must be ${PROBE_SCHEMA_VERSION}`);
  if (probe.kind !== PROBE_KIND) errors.push(`probe.kind must be ${PROBE_KIND}`);
  if (probe.mode !== 'read_only') errors.push('probe.mode must be read_only');
  requireText(probe.probeId, 'probe.probeId', errors);
  requireSha(probe.nonceHash, 'probe.nonceHash', errors);
  if (!ADAPTER_NAMES.includes(probe.adapter)) errors.push('probe.adapter is unsupported');
  if (!READ_ONLY_OPERATIONS.includes(probe.operation)) errors.push('probe.operation is unsupported');
  validateIdentityParts(probe, 'probe', errors);
  requireRfc3339(probe.issuedAt, 'probe.issuedAt', errors);
  requireRfc3339(probe.expiresAt, 'probe.expiresAt', errors);
  if (errors.length === 0 && Date.parse(probe.expiresAt) <= Date.parse(probe.issuedAt)) errors.push('probe.expiresAt must be later than issuedAt');
  if (probe.adapter === 'browser_nerve') validateBrowserIdentity(probe.browserIdentity, 'probe.browserIdentity', errors);
  else if (probe.browserIdentity !== undefined) errors.push('probe.browserIdentity is allowed only for browser_nerve');
  return { ok: errors.length === 0, errors };
}

function validateProbeResult(probe, result, options = {}) {
  const errors = [];
  const probeValidation = validateProbe(probe);
  if (!probeValidation.ok) return { ok: false, errors: probeValidation.errors.map(error => `invalid expected ${error}`) };
  if (!isRecord(result)) return { ok: false, errors: ['result must be a plain object'] };
  if (result.schemaVersion !== PROBE_SCHEMA_VERSION) errors.push(`result.schemaVersion must be ${PROBE_SCHEMA_VERSION}`);
  if (result.kind !== RESULT_KIND) errors.push(`result.kind must be ${RESULT_KIND}`);
  if (result.mode !== 'read_only') errors.push('result.mode must be read_only');
  for (const key of ['probeId', 'nonceHash', 'adapter', 'operation']) if (result[key] !== probe[key]) errors.push(`result.${key} mismatch`);
  validateIdentityParts(result, 'result', errors);
  compareIdentityParts(probe, result, errors);
  requireRfc3339(result.observedAt, 'result.observedAt', errors);
  requireText(result.resultId, 'result.resultId', errors);
  requireSha(result.resultHash, 'result.resultHash', errors);
  if (probe.operation === 'health' && typeof result.healthy !== 'boolean') errors.push('health result.healthy must be boolean');
  if (probe.operation === 'identity' && result.identityVerified !== true) errors.push('identity result.identityVerified must be true');
  if (probe.adapter === 'browser_nerve') {
    validateBrowserIdentity(result.browserIdentity, 'result.browserIdentity', errors);
    for (const key of ['accountId', 'conversationId', 'cdpTargetId']) if (result.browserIdentity?.[key] !== probe.browserIdentity[key]) errors.push(`result.browserIdentity.${key} mismatch`);
  }
  const now = options.now;
  requireRfc3339(now, 'options.now', errors);
  const maxAgeMs = options.maxAgeMs;
  if (!Number.isSafeInteger(maxAgeMs) || maxAgeMs < 0) errors.push('options.maxAgeMs must be a non-negative safe integer');
  if (!isReplayCollection(options.seenProbeIds)) errors.push('options.seenProbeIds replay registry is required');
  if (!isReplayCollection(options.seenResultIds)) errors.push('options.seenResultIds replay registry is required');
  if (errors.length === 0) {
    const observed = Date.parse(result.observedAt);
    const current = Date.parse(now);
    if (current < Date.parse(probe.issuedAt) || current >= Date.parse(probe.expiresAt)) errors.push('probe is not active at validation time');
    if (observed < Date.parse(probe.issuedAt) || observed > current) errors.push('result.observedAt is outside the valid observation window');
    if (current - observed > maxAgeMs) errors.push('result is stale');
    if (hasSeen(options.seenProbeIds, probe.probeId)) errors.push('probe replay detected');
    if (hasSeen(options.seenResultIds, result.resultId)) errors.push('result replay detected');
    if (sha256(resultDigestPayload(result)) !== result.resultHash) errors.push('result.resultHash does not match its canonical payload');
  }
  return { ok: errors.length === 0, errors };
}

function resultDigestPayload(result) {
  const payload = { ...result };
  delete payload.resultHash;
  return payload;
}

function validateIdentityParts(value, path, errors) {
  if (!isRecord(value.commission)) errors.push(`${path}.commission must be a plain object`);
  else {
    requireText(value.commission.commissionId, `${path}.commission.commissionId`, errors);
    requireSha(value.commission.commissionHash, `${path}.commission.commissionHash`, errors);
  }
  if (!isRecord(value.queue)) errors.push(`${path}.queue must be a plain object`);
  else for (const key of ['documentId', 'folderId', 'revision', 'stateOwner']) requireText(value.queue[key], `${path}.queue.${key}`, errors);
  if (!isRecord(value.lane)) errors.push(`${path}.lane must be a plain object`);
  else for (const key of ['laneId', 'owner']) requireText(value.lane[key], `${path}.lane.${key}`, errors);
  if (!isRecord(value.worker)) errors.push(`${path}.worker must be a plain object`);
  else {
    requireText(value.worker.workerId, `${path}.worker.workerId`, errors);
    requireSha(value.worker.identityHash, `${path}.worker.identityHash`, errors);
  }
}

function compareIdentityParts(probe, result, errors) {
  for (const section of ['commission', 'queue', 'lane', 'worker']) {
    if (!isRecord(result[section])) continue;
    for (const [key, expected] of Object.entries(probe[section])) if (result[section][key] !== expected) errors.push(`result.${section}.${key} mismatch`);
  }
}

function validateBrowserIdentity(value, path, errors) {
  if (!isRecord(value)) return errors.push(`${path} must be a plain object`);
  for (const key of ['accountId', 'conversationId', 'cdpTargetId']) requireText(value[key], `${path}.${key}`, errors);
}

function hasSeen(collection, id) {
  if (collection instanceof Set) return collection.has(id);
  if (Array.isArray(collection)) return collection.includes(id);
  throw new TypeError('replay collections must be arrays or Sets');
}

function isReplayCollection(collection) {
  return collection instanceof Set || Array.isArray(collection);
}

function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const nested of Object.values(value)) deepFreeze(nested);
  }
  return value;
}

module.exports = {
  PROBE_SCHEMA_VERSION,
  PROBE_KIND,
  RESULT_KIND,
  createProbe,
  validateProbe,
  validateProbeResult,
  resultDigestPayload
};
