'use strict';

const {
  STATES,
  isRecord,
  requireText,
  requireSha,
  requireEnum,
  requireRfc3339,
  requireStringArray,
  canonicalJson,
  sha256
} = require('./contracts');
const { validateQueueLease } = require('./guards');
const { validateAudioLease } = require('./voice');

const EVENT_KINDS = Object.freeze(['SESSION_EVENT', 'JOB_EVENT', 'FINDING_EVENT', 'RECEIPT_EVENT', 'APPROVAL_EVENT', 'LEASE_EVENT', 'OFFLINE_COMMAND_EVENT', 'PROBE_CONSUMPTION_EVENT', 'CUE_EVENT']);
const CHECKPOINT_REASONS = Object.freeze(['HANDOFF', 'TRANSPORT_TIMEOUT', 'CONTEXT_COMPACTION', 'LANE_SWITCH', 'VOICE_SHUTDOWN', 'QUOTA_PARK']);

function validateSacredSession(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['session must be a plain object'] };
  for (const key of ['sessionId', 'runtime', 'model', 'modelVersion', 'host', 'ticketId', 'jobId', 'laneId', 'promptRef', 'repository', 'worktree', 'branch', 'head', 'resumeCommand']) requireText(value[key], `session.${key}`, errors);
  for (const key of ['identityHash', 'promptSha256']) requireSha(value[key], `session.${key}`, errors);
  requireStringArray(value.evidencePointers, 'session.evidencePointers', errors, { nonEmpty: true });
  requireEnum(value.state, STATES.session, 'session.state', errors);
  if (value.state === 'TRANSPORT_TIMEOUT' && value.resumeCommand.trim() === '') errors.push('TRANSPORT_TIMEOUT must retain exact resumeCommand');
  return { ok: errors.length === 0, errors };
}

function eventDigestPayload(value) {
  return { eventId: value.eventId, streamId: value.streamId, kind: value.kind, sequence: value.sequence, observedAt: value.observedAt, commissionHash: value.commissionHash, queueRevision: value.queueRevision, laneId: value.laneId, payloadHash: value.payloadHash, previousEventHash: value.previousEventHash };
}

function validateAppendOnlyEvent(value, previous) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['event must be a plain object'] };
  if (!EVENT_KINDS.includes(value.kind)) errors.push(`event.kind must be one of ${EVENT_KINDS.join(', ')}`);
  for (const key of ['eventId', 'streamId', 'queueRevision', 'laneId']) requireText(value[key], `event.${key}`, errors);
  requireSha(value.commissionHash, 'event.commissionHash', errors);
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
    if (sha256(eventDigestPayload(value)) !== value.eventHash) errors.push('event.eventHash mismatch');
  }
  if (previous !== undefined) {
    if (!isRecord(previous)) errors.push('previous event must be a plain object');
    else {
      for (const key of ['streamId', 'commissionHash', 'queueRevision', 'laneId']) if (value[key] !== previous[key]) errors.push(`event cannot cross ${key}`);
      if (value.sequence !== previous.sequence + 1) errors.push('event.sequence must append exactly one position');
      if (value.previousEventHash !== previous.eventHash) errors.push('event.previousEventHash must chain to prior event');
      if (Date.parse(value.observedAt) < Date.parse(previous.observedAt)) errors.push('event.observedAt cannot move backwards');
    }
  }
  return { ok: errors.length === 0, errors };
}

function checkpointDigestPayload(value) {
  const payload = { ...value };
  delete payload.checkpointHash;
  return payload;
}

function validateRollingCheckpoint(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['checkpoint must be a plain object'] };
  for (const key of ['checkpointId', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner']) requireText(value[key], `checkpoint.${key}`, errors);
  requireSha(value.commissionHash, 'checkpoint.commissionHash', errors);
  requireEnum(value.reason, CHECKPOINT_REASONS, 'checkpoint.reason', errors);
  requireRfc3339(value.createdAt, 'checkpoint.createdAt', errors);
  if (!Array.isArray(value.watermarks) || value.watermarks.length === 0) errors.push('checkpoint.watermarks must be a non-empty per-stream array');
  else {
    const streams = new Set();
    value.watermarks.forEach((watermark, index) => {
      if (!isRecord(watermark)) return errors.push(`checkpoint.watermarks[${index}] must be a plain object`);
      requireText(watermark.streamId, `checkpoint.watermarks[${index}].streamId`, errors);
      requireText(watermark.laneId, `checkpoint.watermarks[${index}].laneId`, errors);
      requireSha(watermark.commissionHash, `checkpoint.watermarks[${index}].commissionHash`, errors);
      if(watermark.commissionHash!==value.commissionHash)errors.push(`checkpoint.watermarks[${index}] commissionHash mismatch`);
      if (!Number.isSafeInteger(watermark.sequence) || watermark.sequence < 1) errors.push(`checkpoint.watermarks[${index}].sequence must be positive`);
      requireSha(watermark.eventHash, `checkpoint.watermarks[${index}].eventHash`, errors);
      if (streams.has(watermark.streamId)) errors.push(`checkpoint duplicate watermark ${watermark.streamId}`);
      streams.add(watermark.streamId);
    });
  }
  if (!Array.isArray(value.activeLeases)) errors.push('checkpoint.activeLeases must be an array');
  else value.activeLeases.forEach((entry, index) => {
    if (!isRecord(entry) || !['QUEUE', 'ACTUATOR', 'AUDIO'].includes(entry.leaseKind) || !isRecord(entry.lease)) return errors.push(`checkpoint.activeLeases[${index}] must be a typed lease`);
    if (entry.leaseKind === 'QUEUE') errors.push(...validateQueueLease(entry.lease).errors.map(error => `checkpoint.activeLeases[${index}] ${error}`));
    else errors.push(...validateAudioLease(entry.lease, { now: value.createdAt, trustedLease: entry.lease, registry: { consumedLeaseIds: [] }, activeLeases: value.activeLeases.filter(x=>x.leaseKind!=='QUEUE').map(x=>x.lease) }).errors.map(error => `checkpoint.activeLeases[${index}] ${error}`));
  });
  if (!Array.isArray(value.unresolvedGates)) errors.push('checkpoint.unresolvedGates must be an array');
  else value.unresolvedGates.forEach((gate, index) => {
    if (!isRecord(gate)) return errors.push(`checkpoint.unresolvedGates[${index}] must be a plain object`);
    for (const key of ['gateId', 'laneId', 'action', 'reason', 'requiredAuthority']) requireText(gate[key], `checkpoint.unresolvedGates[${index}].${key}`, errors);
  });
  requireStringArray(value.evidencePointers, 'checkpoint.evidencePointers', errors, { nonEmpty: true });
  if (!Array.isArray(value.sessions)) errors.push('checkpoint.sessions must be an array');
  else value.sessions.forEach((session, index) => errors.push(...validateSacredSession(session).errors.map(error => `checkpoint.sessions[${index}] ${error}`)));
  if (!Array.isArray(value.pendingReceipts)) errors.push('checkpoint.pendingReceipts must be an array');
  else value.pendingReceipts.forEach((receipt, index) => validatePendingReceipt(receipt, `checkpoint.pendingReceipts[${index}]`, errors));
  requireSha(value.checkpointHash, 'checkpoint.checkpointHash', errors);
  if (errors.length === 0 && sha256(checkpointDigestPayload(value)) !== value.checkpointHash) errors.push('checkpoint.checkpointHash mismatch');
  return { ok: errors.length === 0, errors };
}

function validateReplayPlan(plan, trustedCheckpoint) {
  const errors = [];
  const checkpointValidation = validateRollingCheckpoint(trustedCheckpoint);
  if (!checkpointValidation.ok) return { ok: false, errors: checkpointValidation.errors.map(error => `trusted checkpoint ${error}`) };
  if (!isRecord(plan) || plan.checkpointHash !== trustedCheckpoint.checkpointHash || plan.queueRevision !== trustedCheckpoint.queueRevision) return { ok: false, errors: ['replay plan does not bind trusted checkpoint/revision'] };
  if (!Array.isArray(plan.streamReplays)) return { ok: false, errors: ['replay plan requires streamReplays'] };
  const eventIds = new Set();
  const entityKeys = new Set();
  const replayStreams = new Set();
  for (const replay of plan.streamReplays) {
    if (!isRecord(replay) || replayStreams.has(replay.streamId)) { errors.push('duplicate or invalid replay stream'); continue; }
    replayStreams.add(replay.streamId);
    const watermark = trustedCheckpoint.watermarks.find(item => item.streamId === replay.streamId);
    if (!watermark) { errors.push(`replay stream ${replay.streamId} lacks watermark`); continue; }
    if(replay.laneId!==watermark.laneId)errors.push(`replay stream ${replay.streamId} lane mismatch`);
    let previous = { streamId: watermark.streamId, commissionHash: watermark.commissionHash, queueRevision: trustedCheckpoint.queueRevision, laneId: watermark.laneId, sequence: watermark.sequence, eventHash: watermark.eventHash, observedAt: trustedCheckpoint.createdAt };
    if (!Array.isArray(replay.events)) { errors.push(`replay stream ${replay.streamId} events missing`); continue; }
    for (const event of replay.events) {
      errors.push(...validateAppendOnlyEvent(event, previous).errors.map(error => `${replay.streamId} ${error}`));
      if (eventIds.has(event.eventId)) errors.push(`duplicate eventId ${event.eventId}`);
      eventIds.add(event.eventId);
      for (const key of ['sessionId', 'receiptId', 'commandId', 'idempotencyKey', 'approvalId', 'leaseId']) if (typeof event.payload?.[key] === 'string') {
        const entity = `${key}:${event.payload[key]}`;
        if (entityKeys.has(entity)) errors.push(`duplicate replay entity ${entity}`);
        entityKeys.add(entity);
      }
      previous = event;
    }
  }
  requireStringArray(plan.sessionIds, 'replay.sessionIds', errors);
  requireStringArray(plan.pendingReceiptIds, 'replay.pendingReceiptIds', errors);
  if (new Set(plan.sessionIds || []).size !== (plan.sessionIds || []).length) errors.push('replay duplicate sessionIds');
  if (new Set(plan.pendingReceiptIds || []).size !== (plan.pendingReceiptIds || []).length) errors.push('replay duplicate pendingReceiptIds');
  if (plan.source !== 'DURABLE_QUEUE_REGISTRY_PENDING_RECEIPTS_AND_OFFLINE_COMMANDS') errors.push('replay source must include durable queue, registries, pending receipts, and offline commands');
  if (canonicalJson([...(plan.sessionIds||[])].sort())!==canonicalJson(trustedCheckpoint.sessions.map(x=>x.sessionId).sort())) errors.push('replay sessionIds must exactly match checkpoint');
  if (canonicalJson([...(plan.pendingReceiptIds||[])].sort())!==canonicalJson(trustedCheckpoint.pendingReceipts.map(x=>x.receiptId).sort())) errors.push('replay pendingReceiptIds must exactly match checkpoint');
  if (replayStreams.size !== trustedCheckpoint.watermarks.length || trustedCheckpoint.watermarks.some(x=>!replayStreams.has(x.streamId))) errors.push('replay must include every checkpoint watermark stream');
  return { ok: errors.length === 0, errors };
}

function validateContextRebuild(rebuild, trusted) {
  const errors = [];
  if (!isRecord(rebuild) || !isRecord(trusted)) return { ok: false, errors: ['rebuild and trusted state must be plain objects'] };
  for (const key of ['queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner', 'checkpointHash']) if (rebuild[key] !== trusted[key]) errors.push(`rebuild.${key} does not match durable truth`);
  if (canonicalJson(rebuild.watermarks) !== canonicalJson(trusted.watermarks)) errors.push('rebuild per-stream watermarks are stale or incomplete');
  if (canonicalList(rebuild.sessionIds, x => x) !== canonicalList(trusted.sessionIds, x => x)) errors.push('rebuild.sessionIds are incomplete or stale');
  if (canonicalList(rebuild.pendingReceipts, x => x.receiptId) !== canonicalList(trusted.pendingReceipts, x => x.receiptId)) errors.push('rebuild.pendingReceipts are incomplete or stale');
  for (const key of ['activeLeases','unresolvedGates','offlineCommands','leaseRegistry','approvalRegistry','probeConsumptionRegistry','cueRegistry']) {
    if(rebuild[key]===undefined||trusted[key]===undefined) errors.push(`rebuild.${key} durable state is required`);
    else if(canonicalJson(rebuild[key])!==canonicalJson(trusted[key])) errors.push(`rebuild.${key} is incomplete or stale`);
  }
  if (rebuild.source !== 'DURABLE_QUEUE_REGISTRY_PENDING_RECEIPTS_AND_OFFLINE_COMMANDS') errors.push('rebuild source is not durable enough');
  return { ok: errors.length === 0, errors };
}

function validatePendingReceipt(value, path, errors) {
  if (!isRecord(value)) return errors.push(`${path} must be a plain object`);
  for (const key of ['receiptId', 'laneId']) requireText(value[key], `${path}.${key}`, errors);
  requireSha(value.receiptHash, `${path}.receiptHash`, errors);
}

function canonicalList(values, key) {
  if (!Array.isArray(values)) return 'INVALID';
  return canonicalJson([...values].sort((a, b) => String(key(a)).localeCompare(String(key(b)))));
}

module.exports = { EVENT_KINDS, CHECKPOINT_REASONS, validateSacredSession, validateAppendOnlyEvent, eventDigestPayload, validateRollingCheckpoint, checkpointDigestPayload, validateReplayPlan, validateContextRebuild };
