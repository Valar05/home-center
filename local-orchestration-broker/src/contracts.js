'use strict';

const crypto = require('node:crypto');

const STATES = Object.freeze({
  queue: Object.freeze(['OPEN', 'PAUSED_GATE', 'MORNING_HANDOFF', 'CLOSED']),
  lane: Object.freeze(['QUEUED', 'READY', 'ACTIVE', 'WAITING_EXTERNAL', 'WAITING_APPROVAL', 'TRANSPORT_TIMEOUT', 'BLOCKED', 'TRANSITION_VERIFIED', 'PARKED', 'REALLOCATED', 'COMPLETED_PRESERVED']),
  job: Object.freeze(['DRAFT', 'VALIDATED', 'LEASED', 'DISPATCHED', 'RUNNING', 'VERIFYING', 'RECEIPT_READY', 'MATERIAL_TRANSITION', 'COMPLETED_PRESERVED', 'WAITING_EVIDENCE', 'WAITING_APPROVAL', 'TRANSPORT_TIMEOUT', 'FAILED_RETRYABLE', 'BLOCKED_TERMINAL', 'CANCELLED']),
  session: Object.freeze(['REGISTERED', 'RUNNING', 'QUIESCENT', 'TRANSPORT_TIMEOUT', 'READY_TO_RESUME', 'BLOCKED', 'BLOCKED_NONRESUMABLE', 'NONRESUMABLE_PROVEN', 'COMPLETED_PRESERVED']),
  approval: Object.freeze(['NOT_REQUIRED', 'REQUIRED', 'PENDING', 'GRANTED_SCOPED', 'DENIED', 'EXPIRED', 'CONSUMED']),
  compaction: Object.freeze(['UNCOMPACTED', 'COMPACTION_PENDING', 'COMPACTION_UNVERIFIED', 'COMPACTED_READBACK_VERIFIED'])
});

const CAPABILITY_KEYS = Object.freeze(['requested', 'implemented', 'tested', 'deployed', 'callable', 'delivered', 'accepted']);
const READ_ONLY_OPERATIONS = Object.freeze(['health', 'identity']);
const ADAPTER_NAMES = Object.freeze(['computer_hands', 'browser_nerve', 'venice_nerve', 'codex', 'continue', 'qwen', 'piper', 'local_assembler', 'local_playback', 'voice_aperture']);
const SHA256 = /^[a-f0-9]{64}$/;
const RFC3339 = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?Z$/;

function isRecord(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function requireText(value, path, errors) {
  if (typeof value !== 'string' || value.trim() === '') errors.push(`${path} must be a non-empty string`);
}

function requireSha(value, path, errors) {
  if (!SHA256.test(value || '')) errors.push(`${path} must be a lowercase SHA-256`);
}

function requireEnum(value, allowed, path, errors) {
  if (!allowed.includes(value)) errors.push(`${path} must be one of ${allowed.join(', ')}`);
}

function requireRfc3339(value, path, errors) {
  const match = typeof value === 'string' ? RFC3339.exec(value) : null;
  if (!match || !Number.isFinite(Date.parse(value))) return errors.push(`${path} must be an RFC3339 UTC timestamp`);
  const [, year, month, day, hour, minute, second] = match.map(Number);
  const parsed = new Date(Date.parse(value));
  if (parsed.getUTCFullYear() !== year || parsed.getUTCMonth() + 1 !== month || parsed.getUTCDate() !== day || parsed.getUTCHours() !== hour || parsed.getUTCMinutes() !== minute || parsed.getUTCSeconds() !== second) errors.push(`${path} must be a real RFC3339 UTC timestamp`);
}

function requireExactKeys(value, allowed, path, errors) {
  if (!isRecord(value)) return;
  const actual = Object.keys(value).sort();
  const expected = [...allowed].sort();
  if (actual.join(',') !== expected.join(',')) errors.push(`${path} must contain exactly ${expected.join(', ')}`);
}

function requireStringArray(value, path, errors, { nonEmpty = false } = {}) {
  if (!Array.isArray(value) || (nonEmpty && value.length === 0) || value.some(item => typeof item !== 'string' || item.trim() === '')) {
    errors.push(`${path} must be ${nonEmpty ? 'a non-empty' : 'an'} array of non-empty strings`);
  }
}

function canonicalJson(value) {
  const ancestors = new Set();
  function encode(current, path) {
    if (current === null) return 'null';
    const type = typeof current;
    if (type === 'string' || type === 'boolean') return JSON.stringify(current);
    if (type === 'number') {
      if (!Number.isFinite(current) || Object.is(current, -0)) throw new TypeError(`${path} contains a non-canonical number`);
      return JSON.stringify(current);
    }
    if (type === 'undefined' || type === 'function' || type === 'symbol' || type === 'bigint') throw new TypeError(`${path} contains unsupported ${type}`);
    if (ancestors.has(current)) throw new TypeError(`${path} contains a cycle`);
    ancestors.add(current);
    try {
      if (Array.isArray(current)) {
        if (Object.getOwnPropertySymbols(current).length > 0) throw new TypeError(`${path} contains symbol keys`);
        const names = Object.getOwnPropertyNames(current);
        const allowed = new Set(['length', ...Array.from({ length: current.length }, (_, index) => String(index))]);
        if (names.some(name => !allowed.has(name))) throw new TypeError(`${path} contains non-index array properties`);
        for (let index = 0; index < current.length; index += 1) {
          if (!Object.hasOwn(current, index)) throw new TypeError(`${path} is sparse at ${index}`);
          const descriptor = Object.getOwnPropertyDescriptor(current, String(index));
          if (!descriptor || !Object.hasOwn(descriptor, 'value')) throw new TypeError(`${path}[${index}] must be a data property`);
        }
        return `[${current.map((item, index) => encode(item, `${path}[${index}]`)).join(',')}]`;
      }
      if (!isRecord(current)) throw new TypeError(`${path} must contain only plain JSON objects`);
      if (Object.getOwnPropertySymbols(current).length > 0) throw new TypeError(`${path} contains symbol keys`);
      const keys = Object.getOwnPropertyNames(current).sort();
      for (const key of keys) {
        const descriptor = Object.getOwnPropertyDescriptor(current, key);
        if (!descriptor || !descriptor.enumerable || !Object.hasOwn(descriptor, 'value')) throw new TypeError(`${path}.${key} must be an enumerable data property`);
      }
      return `{${keys.map(key => `${JSON.stringify(key)}:${encode(current[key], `${path}.${key}`)}`).join(',')}}`;
    } finally {
      ancestors.delete(current);
    }
  }
  return encode(value, '$');
}

function sha256(value) {
  return crypto.createHash('sha256').update(typeof value === 'string' ? value : canonicalJson(value)).digest('hex');
}

function commissionDigestPayload(value) {
  return {
    commissionId: value.commissionId,
    queue: {
      documentId: value.queue.documentId,
      folderId: value.queue.folderId,
      revision: value.queue.revision,
      stateOwner: value.queue.stateOwner
    },
    lane: { laneId: value.lane.laneId, owner: value.lane.owner },
    worker: { workerId: value.worker.workerId, identityHash: value.worker.identityHash },
    mutating: value.mutating,
    operations: [...value.operations]
  };
}

function computeCommissionHash(value) {
  return sha256(commissionDigestPayload(value));
}

function validateCommissionEnvelope(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['commission must be a plain object'] };
  requireExactKeys(value, ['commissionId', 'commissionHash', 'queue', 'lane', 'worker', 'mutating', 'operations'], 'commission', errors);
  requireText(value.commissionId, 'commission.commissionId', errors);
  requireSha(value.commissionHash, 'commission.commissionHash', errors);
  if (!isRecord(value.queue)) errors.push('commission.queue must be a plain object');
  else {
    requireExactKeys(value.queue, ['documentId', 'folderId', 'revision', 'stateOwner'], 'commission.queue', errors);
    for (const key of ['documentId', 'folderId', 'revision', 'stateOwner']) requireText(value.queue[key], `commission.queue.${key}`, errors);
  }
  if (!isRecord(value.lane)) errors.push('commission.lane must be a plain object');
  else {
    requireExactKeys(value.lane, ['laneId', 'owner'], 'commission.lane', errors);
    for (const key of ['laneId', 'owner']) requireText(value.lane[key], `commission.lane.${key}`, errors);
  }
  if (!isRecord(value.worker)) errors.push('commission.worker must be a plain object');
  else {
    requireExactKeys(value.worker, ['workerId', 'identityHash'], 'commission.worker', errors);
    requireText(value.worker.workerId, 'commission.worker.workerId', errors);
    requireSha(value.worker.identityHash, 'commission.worker.identityHash', errors);
  }
  if (typeof value.mutating !== 'boolean') errors.push('commission.mutating must be boolean');
  requireStringArray(value.operations, 'commission.operations', errors, { nonEmpty: true });
  if (Array.isArray(value.operations) && new Set(value.operations).size !== value.operations.length) errors.push('commission.operations must not contain duplicates');
  if (errors.length === 0) {
    try {
      if (computeCommissionHash(value) !== value.commissionHash) errors.push('commission.commissionHash does not match the canonical bound payload');
    } catch (error) {
      errors.push(`commission is not canonical: ${error.message}`);
    }
  }
  return { ok: errors.length === 0, errors };
}

function validateStateRecord(kind, value) {
  const errors = [];
  if (!Object.hasOwn(STATES, kind)) errors.push(`unknown state kind: ${kind}`);
  else requireEnum(value, STATES[kind], `state.${kind}`, errors);
  return { ok: errors.length === 0, errors };
}

function validateCapabilityStates(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['capabilityStates must be a plain object'] };
  const keys = Object.keys(value).sort();
  if (keys.join(',') !== [...CAPABILITY_KEYS].sort().join(',')) errors.push(`capabilityStates must contain exactly ${CAPABILITY_KEYS.join(', ')}`);
  for (const key of CAPABILITY_KEYS) if (typeof value[key] !== 'boolean') errors.push(`capabilityStates.${key} must be boolean`);
  return { ok: errors.length === 0, errors };
}

function validateEvidence(value, path, errors) {
  if (!isRecord(value)) return errors.push(`${path} must be a plain object`);
  for (const key of ['evidenceId', 'kind', 'ref']) requireText(value[key], `${path}.${key}`, errors);
  requireSha(value.sha256, `${path}.sha256`, errors);
  requireRfc3339(value.observedAt, `${path}.observedAt`, errors);
}

function validateFindingCard(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['finding must be a plain object'] };
  for (const key of ['findingId', 'observedBySession', 'claim', 'recommendedAction']) requireText(value[key], `finding.${key}`, errors);
  requireRfc3339(value.observedAt, 'finding.observedAt', errors);
  requireStringArray(value.affectedLaneIds, 'finding.affectedLaneIds', errors, { nonEmpty: true });
  requireStringArray(value.evidenceRefs, 'finding.evidenceRefs', errors, { nonEmpty: true });
  if (!Array.isArray(value.evidenceHashes) || value.evidenceHashes.length === 0 || value.evidenceHashes.some(hash => !SHA256.test(hash))) errors.push('finding.evidenceHashes must be a non-empty array of lowercase SHA-256 values');
  if (Array.isArray(value.evidenceRefs) && Array.isArray(value.evidenceHashes) && value.evidenceRefs.length !== value.evidenceHashes.length) errors.push('finding evidenceRefs and evidenceHashes must have equal lengths');
  requireEnum(value.confidence, ['high', 'medium', 'low'], 'finding.confidence', errors);
  requireEnum(value.gateImpact, ['none', 'narrows', 'blocks', 'unblocks'], 'finding.gateImpact', errors);
  if (value.scopeChange !== false) errors.push('finding.scopeChange must be false');
  requireStringArray(value.sentTo, 'finding.sentTo', errors, { nonEmpty: true });
  if (!Array.isArray(value.acknowledgements)) errors.push('finding.acknowledgements must be an array');
  else {
    const acknowledgements = new Map();
    value.acknowledgements.forEach((ack, index) => {
      if (!isRecord(ack)) return errors.push(`finding.acknowledgements[${index}] must be a plain object`);
      requireText(ack.sessionId, `finding.acknowledgements[${index}].sessionId`, errors);
      requireRfc3339(ack.at, `finding.acknowledgements[${index}].at`, errors);
      if (typeof ack.planChanged !== 'boolean') errors.push(`finding.acknowledgements[${index}].planChanged must be boolean`);
      requireText(ack.note, `finding.acknowledgements[${index}].note`, errors);
      if (acknowledgements.has(ack.sessionId)) errors.push(`finding.acknowledgements duplicates ${ack.sessionId}`);
      acknowledgements.set(ack.sessionId, ack);
    });
    if (Array.isArray(value.sentTo)) for (const sessionId of value.sentTo) if (!acknowledgements.has(sessionId)) errors.push(`finding missing acknowledgement from ${sessionId}`);
    if (Array.isArray(value.sentTo)) for (const sessionId of acknowledgements.keys()) if (!value.sentTo.includes(sessionId)) errors.push(`finding acknowledgement from unsent recipient ${sessionId}`);
  }
  return { ok: errors.length === 0, errors };
}

function validateReceipt(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['receipt must be a plain object'] };
  for (const key of ['receiptId', 'commissionId', 'laneId', 'workerId', 'priorState', 'newState', 'remainingGate', 'nextAction']) requireText(value[key], `receipt.${key}`, errors);
  requireSha(value.commissionHash, 'receipt.commissionHash', errors);
  requireEnum(value.jobState, STATES.job, 'receipt.jobState', errors);
  const capability = validateCapabilityStates(value.capabilityStates);
  errors.push(...capability.errors);
  for (const key of ['artifacts', 'tests', 'findings']) requireStringArray(value[key], `receipt.${key}`, errors);
  if (!Array.isArray(value.evidence) || value.evidence.length === 0) errors.push('receipt.evidence must be a non-empty array');
  else value.evidence.forEach((item, index) => validateEvidence(item, `receipt.evidence[${index}]`, errors));
  if (value.jobState === 'MATERIAL_TRANSITION') {
    if (!Array.isArray(value.tests) || value.tests.length === 0) errors.push('MATERIAL_TRANSITION requires at least one test or verification receipt');
    if (value.priorState === value.newState) errors.push('MATERIAL_TRANSITION requires a changed state');
  }
  return { ok: errors.length === 0, errors };
}

module.exports = {
  STATES,
  CAPABILITY_KEYS,
  READ_ONLY_OPERATIONS,
  ADAPTER_NAMES,
  SHA256,
  RFC3339,
  isRecord,
  requireText,
  requireSha,
  requireEnum,
  requireRfc3339,
  requireStringArray,
  requireExactKeys,
  validateCommissionEnvelope,
  validateStateRecord,
  validateCapabilityStates,
  validateFindingCard,
  validateReceipt,
  commissionDigestPayload,
  computeCommissionHash,
  canonicalJson,
  sha256
};
