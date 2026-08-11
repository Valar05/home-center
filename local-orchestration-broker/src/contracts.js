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

const READ_ONLY_OPERATIONS = Object.freeze(['health', 'identity']);
const ADAPTER_NAMES = Object.freeze(['computer_hands', 'browser_nerve', 'venice_nerve', 'codex', 'continue', 'qwen']);
const SHA256 = /^[a-f0-9]{64}$/;

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function requireText(value, path, errors) {
  if (typeof value !== 'string' || value.trim() === '') errors.push(`${path} must be a non-empty string`);
}

function requireEnum(value, allowed, path, errors) {
  if (!allowed.includes(value)) errors.push(`${path} must be one of ${allowed.join(', ')}`);
}

function validateCommissionEnvelope(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['commission must be an object'] };
  requireText(value.commissionId, 'commission.commissionId', errors);
  if (!SHA256.test(value.commissionHash || '')) errors.push('commission.commissionHash must be a lowercase SHA-256');
  if (!isRecord(value.queue)) errors.push('commission.queue must be an object');
  else {
    requireText(value.queue.documentId, 'commission.queue.documentId', errors);
    requireText(value.queue.folderId, 'commission.queue.folderId', errors);
    requireText(value.queue.revision, 'commission.queue.revision', errors);
    requireText(value.queue.stateOwner, 'commission.queue.stateOwner', errors);
  }
  if (!isRecord(value.lane)) errors.push('commission.lane must be an object');
  else {
    requireText(value.lane.laneId, 'commission.lane.laneId', errors);
    requireText(value.lane.owner, 'commission.lane.owner', errors);
  }
  if (!isRecord(value.worker)) errors.push('commission.worker must be an object');
  else {
    requireText(value.worker.workerId, 'commission.worker.workerId', errors);
    if (!SHA256.test(value.worker.identityHash || '')) errors.push('commission.worker.identityHash must be a lowercase SHA-256');
  }
  if (value.mutating !== false) errors.push('commission.mutating must be false');
  if (!Array.isArray(value.operations) || value.operations.length === 0) errors.push('commission.operations must be a non-empty array');
  else value.operations.forEach((operation, index) => requireEnum(operation, READ_ONLY_OPERATIONS, `commission.operations[${index}]`, errors));
  return { ok: errors.length === 0, errors };
}

function validateStateRecord(kind, value) {
  const errors = [];
  if (!Object.hasOwn(STATES, kind)) errors.push(`unknown state kind: ${kind}`);
  else requireEnum(value, STATES[kind], `state.${kind}`, errors);
  return { ok: errors.length === 0, errors };
}

function validateFindingCard(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['finding must be an object'] };
  for (const key of ['findingId', 'observedBySession', 'observedAt', 'claim', 'gateImpact', 'recommendedAction']) requireText(value[key], `finding.${key}`, errors);
  if (!Array.isArray(value.affectedLaneIds) || value.affectedLaneIds.length === 0) errors.push('finding.affectedLaneIds must be non-empty');
  if (!Array.isArray(value.evidenceRefs)) errors.push('finding.evidenceRefs must be an array');
  if (!Array.isArray(value.evidenceHashes) || value.evidenceHashes.some(hash => !SHA256.test(hash))) errors.push('finding.evidenceHashes must contain lowercase SHA-256 values');
  requireEnum(value.confidence, ['high', 'medium', 'low'], 'finding.confidence', errors);
  if (value.scopeChange !== false) errors.push('finding.scopeChange must be false');
  return { ok: errors.length === 0, errors };
}

function validateReceipt(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['receipt must be an object'] };
  for (const key of ['receiptId', 'commissionHash', 'laneId', 'workerId', 'priorState', 'newState', 'remainingGate', 'nextAction']) requireText(value[key], `receipt.${key}`, errors);
  if (!SHA256.test(value.commissionHash || '')) errors.push('receipt.commissionHash must be a lowercase SHA-256');
  for (const key of ['artifacts', 'tests', 'evidenceRefs', 'findings']) if (!Array.isArray(value[key])) errors.push(`receipt.${key} must be an array`);
  return { ok: errors.length === 0, errors };
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (isRecord(value)) return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

function sha256(value) {
  return crypto.createHash('sha256').update(typeof value === 'string' ? value : canonicalJson(value)).digest('hex');
}

module.exports = { STATES, READ_ONLY_OPERATIONS, ADAPTER_NAMES, validateCommissionEnvelope, validateStateRecord, validateFindingCard, validateReceipt, canonicalJson, sha256 };
