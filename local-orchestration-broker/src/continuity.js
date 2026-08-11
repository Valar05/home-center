'use strict';

const {
  STATES,
  isRecord,
  requireText,
  requireSha,
  requireEnum,
  requireRfc3339,
  requireStringArray,
  sha256
} = require('./contracts');
const { validateQueueLease } = require('./guards');

const EVENT_KINDS = Object.freeze(['SESSION_EVENT', 'JOB_EVENT', 'FINDING_EVENT', 'RECEIPT_EVENT']);
const CHECKPOINT_REASONS = Object.freeze(['HANDOFF', 'TRANSPORT_TIMEOUT', 'CONTEXT_COMPACTION', 'LANE_SWITCH']);

function validateSacredSession(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['session must be a plain object'] };
  for (const key of ['sessionId', 'runtime', 'model', 'modelVersion', 'host', 'ticketId', 'jobId', 'laneId', 'promptRef', 'repository', 'worktree', 'branch', 'head', 'resumeCommand']) requireText(value[key], `session.${key}`, errors);
  for (const key of ['identityHash', 'promptSha256']) requireSha(value[key], `session.${key}`, errors);
  requireStringArray(value.evidencePointers, 'session.evidencePointers', errors, { nonEmpty: true });
  requireEnum(value.state, STATES.session, 'session.state', errors);
  if (value.state === 'TRANSPORT_TIMEOUT' && value.resumeCommand.trim() === '') errors.push('TRANSPORT_TIMEOUT must retain the exact resumeCommand');
  return { ok: errors.length === 0, errors };
}

function validateAppendOnlyEvent(value, previous) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['event must be a plain object'] };
  if (!EVENT_KINDS.includes(value.kind)) errors.push(`event.kind must be one of ${EVENT_KINDS.join(', ')}`);
  requireText(value.eventId, 'event.eventId', errors);
  if (!Number.isSafeInteger(value.sequence) || value.sequence < 1) errors.push('event.sequence must be a positive safe integer');
  requireRfc3339(value.observedAt, 'event.observedAt', errors);
  requireSha(value.payloadHash, 'event.payloadHash', errors);
  if (!isRecord(value.payload)) errors.push('event.payload must be a plain object');
  if (value.sequence === 1) {
    if (value.previousEventHash !== null) errors.push('first event.previousEventHash must be null');
  } else requireSha(value.previousEventHash, 'event.previousEventHash', errors);
  requireSha(value.eventHash, 'event.eventHash', errors);
  if (errors.length === 0) {
    if (sha256(value.payload) !== value.payloadHash) errors.push('event.payloadHash mismatch');
    const digest = sha256(eventDigestPayload(value));
    if (digest !== value.eventHash) errors.push('event.eventHash mismatch');
  }
  if (previous !== undefined) {
    if (!isRecord(previous)) errors.push('previous event must be a plain object');
    else {
      if (value.sequence !== previous.sequence + 1) errors.push('event.sequence must append exactly one position');
      if (value.previousEventHash !== previous.eventHash) errors.push('event.previousEventHash must chain to prior event');
      if (Date.parse(value.observedAt) < Date.parse(previous.observedAt)) errors.push('event.observedAt cannot move backwards');
    }
  }
  return { ok: errors.length === 0, errors };
}

function eventDigestPayload(value) {
  return {
    eventId: value.eventId,
    kind: value.kind,
    sequence: value.sequence,
    observedAt: value.observedAt,
    payloadHash: value.payloadHash,
    previousEventHash: value.previousEventHash
  };
}

function validateRollingCheckpoint(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['checkpoint must be a plain object'] };
  for (const key of ['checkpointId', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner']) requireText(value[key], `checkpoint.${key}`, errors);
  requireEnum(value.reason, CHECKPOINT_REASONS, 'checkpoint.reason', errors);
  requireRfc3339(value.createdAt, 'checkpoint.createdAt', errors);
  if (!Number.isSafeInteger(value.compactionWatermark) || value.compactionWatermark < 1) errors.push('checkpoint.compactionWatermark must be a positive safe integer');
  requireSha(value.eventHashAtWatermark, 'checkpoint.eventHashAtWatermark', errors);
  if (!Array.isArray(value.activeLeases)) errors.push('checkpoint.activeLeases must be an array');
  else value.activeLeases.forEach((lease, index) => errors.push(...validateQueueLease(lease).errors.map(error => `checkpoint.activeLeases[${index}] ${error}`)));
  if (!Array.isArray(value.unresolvedGates)) errors.push('checkpoint.unresolvedGates must be an array');
  else value.unresolvedGates.forEach((gate, index) => {
    if (!isRecord(gate)) return errors.push(`checkpoint.unresolvedGates[${index}] must be a plain object`);
    for (const key of ['gateId', 'laneId', 'action', 'reason', 'requiredAuthority']) requireText(gate[key], `checkpoint.unresolvedGates[${index}].${key}`, errors);
  });
  requireStringArray(value.evidencePointers, 'checkpoint.evidencePointers', errors, { nonEmpty: true });
  if (!Array.isArray(value.sessions)) errors.push('checkpoint.sessions must be an array');
  else value.sessions.forEach((session, index) => {
    const validation = validateSacredSession(session);
    errors.push(...validation.errors.map(error => `checkpoint.sessions[${index}] ${error}`));
  });
  if (!Array.isArray(value.pendingReceipts)) errors.push('checkpoint.pendingReceipts must be an array');
  else value.pendingReceipts.forEach((receipt, index) => validatePendingReceipt(receipt, `checkpoint.pendingReceipts[${index}]`, errors));
  requireSha(value.checkpointHash, 'checkpoint.checkpointHash', errors);
  if (errors.length === 0 && sha256(checkpointDigestPayload(value)) !== value.checkpointHash) errors.push('checkpoint.checkpointHash mismatch');
  return { ok: errors.length === 0, errors };
}

function checkpointDigestPayload(value) {
  const payload = { ...value };
  delete payload.checkpointHash;
  return payload;
}

function validateContextRebuild(rebuild, trusted) {
  const errors = [];
  if (!isRecord(rebuild) || !isRecord(trusted)) return { ok: false, errors: ['rebuild and trusted state must be plain objects'] };
  for (const key of ['queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner']) {
    requireText(rebuild[key], `rebuild.${key}`, errors);
    if (rebuild[key] !== trusted[key]) errors.push(`rebuild.${key} does not match durable truth`);
  }
  for (const key of ['checkpointHash', 'eventHashAtWatermark']) {
    requireSha(rebuild[key], `rebuild.${key}`, errors);
    if (rebuild[key] !== trusted[key]) errors.push(`rebuild.${key} does not match durable truth`);
  }
  if (!Number.isSafeInteger(rebuild.compactionWatermark) || rebuild.compactionWatermark !== trusted.compactionWatermark) errors.push('rebuild.compactionWatermark does not match durable truth');
  requireStringArray(rebuild.sessionIds, 'rebuild.sessionIds', errors);
  if (!Array.isArray(rebuild.pendingReceipts)) errors.push('rebuild.pendingReceipts must be an array');
  else rebuild.pendingReceipts.forEach((receipt, index) => validatePendingReceipt(receipt, `rebuild.pendingReceipts[${index}]`, errors));
  if (Array.isArray(trusted.sessionIds) && JSON.stringify([...rebuild.sessionIds].sort()) !== JSON.stringify([...trusted.sessionIds].sort())) errors.push('rebuild.sessionIds are incomplete or stale');
  if (Array.isArray(trusted.pendingReceipts) && Array.isArray(rebuild.pendingReceipts) && canonicalList(rebuild.pendingReceipts, 'receiptId') !== canonicalList(trusted.pendingReceipts, 'receiptId')) errors.push('rebuild.pendingReceipts are incomplete or stale');
  if (rebuild.source !== 'DURABLE_QUEUE_REGISTRY_AND_PENDING_RECEIPTS') errors.push('rebuild.source must be DURABLE_QUEUE_REGISTRY_AND_PENDING_RECEIPTS');
  return { ok: errors.length === 0, errors };
}

function validatePendingReceipt(value, path, errors) {
  if (!isRecord(value)) return errors.push(`${path} must be a plain object`);
  for (const key of ['receiptId', 'laneId']) requireText(value[key], `${path}.${key}`, errors);
  requireSha(value.receiptHash, `${path}.receiptHash`, errors);
}

function canonicalList(values, key) {
  return JSON.stringify([...values].sort((a, b) => String(a[key]).localeCompare(String(b[key]))));
}

module.exports = {
  EVENT_KINDS,
  CHECKPOINT_REASONS,
  validateSacredSession,
  validateAppendOnlyEvent,
  eventDigestPayload,
  validateRollingCheckpoint,
  checkpointDigestPayload,
  validateContextRebuild
};
