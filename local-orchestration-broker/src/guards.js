'use strict';

const {
  READ_ONLY_OPERATIONS,
  isRecord,
  validateCommissionEnvelope,
  validateStateRecord,
  requireText,
  requireSha,
  requireRfc3339,
  canonicalJson,
  sha256
} = require('./contracts');

class BrokerGateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'BrokerGateError';
    this.code = code;
  }
}

function equal(actual, expected, code, label) {
  if (actual !== expected) throw new BrokerGateError(code, `${label} mismatch`);
}

function authorizeReadOnly(commission, trusted) {
  const validation = validateCommissionEnvelope(commission);
  if (!validation.ok) throw new BrokerGateError('INVALID_COMMISSION', validation.errors.join('; '));
  if (!isRecord(trusted)) throw new BrokerGateError('TRUST_STATE_MISSING', 'trusted state is required');
  equal(commission.commissionId, trusted.commissionId, 'COMMISSION_MISMATCH', 'commission id');
  equal(commission.commissionHash, trusted.commissionHash, 'COMMISSION_MISMATCH', 'commission hash');
  equal(commission.queue.documentId, trusted.queueDocumentId, 'QUEUE_MISMATCH', 'queue document');
  equal(commission.queue.folderId, trusted.queueFolderId, 'QUEUE_MISMATCH', 'queue folder');
  equal(commission.queue.revision, trusted.queueRevision, 'STALE_REVISION', 'queue revision');
  equal(commission.queue.stateOwner, trusted.stateOwner, 'OWNER_MISMATCH', 'state owner');
  equal(commission.lane.laneId, trusted.laneId, 'LANE_MISMATCH', 'lane id');
  equal(commission.lane.owner, trusted.laneOwner, 'OWNER_MISMATCH', 'lane owner');
  equal(commission.worker.workerId, trusted.workerId, 'IDENTITY_MISMATCH', 'worker id');
  equal(commission.worker.identityHash, trusted.workerIdentityHash, 'IDENTITY_MISMATCH', 'worker identity');
  equal(commission.mutating, trusted.mutating, 'MUTATION_MISMATCH', 'mutating flag');
  equal(JSON.stringify(commission.operations), JSON.stringify(trusted.operations), 'OPERATION_MISMATCH', 'operations');
  if (commission.mutating !== false) throw new BrokerGateError('MUTATION_FORBIDDEN', 'mutating requests are forbidden');
  if (commission.operations.some(operation => !READ_ONLY_OPERATIONS.includes(operation))) throw new BrokerGateError('MUTATION_FORBIDDEN', 'operation is not read-only');
  return Object.freeze({ authorized: true, mode: 'read_only', commissionId: commission.commissionId, commissionHash: commission.commissionHash, laneId: commission.lane.laneId, operations: Object.freeze([...commission.operations]) });
}

function leaseDigestPayload(lease) {
  return {
    leaseId: lease.leaseId,
    documentId: lease.documentId,
    folderId: lease.folderId,
    revision: lease.revision,
    stateOwner: lease.stateOwner,
    holderId: lease.holderId,
    fencingToken: lease.fencingToken,
    acquiredAt: lease.acquiredAt,
    expiresAt: lease.expiresAt
  };
}

function validateQueueLease(lease) {
  const errors = [];
  if (!isRecord(lease)) return { ok: false, errors: ['lease must be a plain object'] };
  for (const key of ['leaseId', 'documentId', 'folderId', 'revision', 'stateOwner', 'holderId']) requireText(lease[key], `lease.${key}`, errors);
  if (!Number.isSafeInteger(lease.fencingToken) || lease.fencingToken < 1) errors.push('lease.fencingToken must be a positive safe integer');
  requireRfc3339(lease.acquiredAt, 'lease.acquiredAt', errors);
  requireRfc3339(lease.expiresAt, 'lease.expiresAt', errors);
  requireSha(lease.leaseDigest, 'lease.leaseDigest', errors);
  if (errors.length === 0 && Date.parse(lease.expiresAt) <= Date.parse(lease.acquiredAt)) errors.push('lease.expiresAt must be later than acquiredAt');
  if (errors.length === 0 && sha256(leaseDigestPayload(lease)) !== lease.leaseDigest) errors.push('lease.leaseDigest does not match its bound scope');
  return { ok: errors.length === 0, errors };
}

function authorizeCompactionFence(lease, trusted, now) {
  const validation = validateQueueLease(lease);
  if (!validation.ok) throw new BrokerGateError('INVALID_LEASE', validation.errors.join('; '));
  if (!isRecord(trusted) || typeof trusted.registryId !== 'string' || trusted.registryId.trim()==='' || !Number.isSafeInteger(trusted.revision) || trusted.revision < 0 || !isRecord(trusted.leaseRecord) || !isRecord(trusted.records) || !Array.isArray(trusted.consumedLeaseIds) || !Array.isArray(trusted.consumedIdempotencyKeys)) throw new BrokerGateError('TRUST_STATE_MISSING', 'complete trusted persistent lease registry is required');
  requireNow(now);
  const trustedValidation = validateQueueLease(trusted.leaseRecord);
  if (!trustedValidation.ok) throw new BrokerGateError('TRUST_STATE_INVALID', trustedValidation.errors.join('; '));
  equal(canonicalRecord(lease), canonicalRecord(trusted.leaseRecord), 'LEASE_IDENTITY_MISMATCH', 'complete lease record');
  if (trusted.consumedLeaseIds.includes(lease.leaseId)) throw new BrokerGateError('LEASE_REPLAY', 'lease already consumed');
  if (Date.parse(now) >= Date.parse(lease.expiresAt)) throw new BrokerGateError('LEASE_EXPIRED', 'queue lease expired');
  const consumed = { ...lease, consumedAt: now };
  if (canonicalRecord(trusted.records[lease.leaseId])!==canonicalRecord(lease)) throw new BrokerGateError('LEASE_IDENTITY_MISMATCH','registry lease record mismatch');
  const cas = createConsumptionCas({ registry: trusted, recordId: lease.leaseId, currentRecord: lease, nextRecord: consumed, idempotencyKey: `queue-lease:${lease.leaseId}:${lease.leaseDigest}` });
  const casValidation=validateConsumptionCas(cas,trusted); if(!casValidation.ok) throw new BrokerGateError('INVALID_CAS',casValidation.errors.join('; '));
  return Object.freeze({ authorized: true, leaseId: lease.leaseId, leaseDigest: lease.leaseDigest, fencingToken: lease.fencingToken, requiredRevision: lease.revision, registryId: trusted.registryId, expectedRegistryRevision: trusted.revision, cas: Object.freeze(cas) });
}

function approvalDigestPayload(approval) {
  return {
    approvalId: approval.approvalId,
    actor: approval.actor,
    action: approval.action,
    target: approval.target,
    artifactDigest: approval.artifactDigest,
    environment: approval.environment,
    commissionHash: approval.commissionHash,
    issuedAt: approval.issuedAt,
    expiresAt: approval.expiresAt,
    maxUses: approval.maxUses,
    useCount: approval.useCount,
    state: approval.state,
    consumedAt: approval.consumedAt ?? null
  };
}

function validateApproval(approval) {
  const errors = [];
  if (!isRecord(approval)) return { ok: false, errors: ['approval must be a plain object'] };
  for (const key of ['approvalId', 'actor', 'action', 'target', 'environment']) requireText(approval[key], `approval.${key}`, errors);
  for (const key of ['artifactDigest', 'commissionHash', 'approvalDigest']) requireSha(approval[key], `approval.${key}`, errors);
  requireRfc3339(approval.issuedAt, 'approval.issuedAt', errors);
  requireRfc3339(approval.expiresAt, 'approval.expiresAt', errors);
  if (approval.maxUses !== 1) errors.push('approval.maxUses must equal 1');
  if (!Number.isSafeInteger(approval.useCount) || approval.useCount < 0 || approval.useCount > 1) errors.push('approval.useCount must be 0 or 1');
  errors.push(...validateStateRecord('approval', approval.state).errors);
  if (errors.length === 0 && Date.parse(approval.expiresAt) <= Date.parse(approval.issuedAt)) errors.push('approval.expiresAt must be later than issuedAt');
  if (approval.state === 'GRANTED_SCOPED' && approval.useCount !== 0) errors.push('GRANTED_SCOPED approval must be unused');
  if (approval.state === 'CONSUMED') {
    if (approval.useCount !== 1) errors.push('CONSUMED approval must have useCount=1');
    requireRfc3339(approval.consumedAt, 'approval.consumedAt', errors);
  } else if (approval.consumedAt !== undefined) errors.push('approval.consumedAt is allowed only for CONSUMED');
  if (errors.length === 0 && sha256(approvalDigestPayload(approval)) !== approval.approvalDigest) errors.push('approval.approvalDigest does not match its bound scope');
  return { ok: errors.length === 0, errors };
}

function authorizeApproval(approval, requested, now, trustedRegistry) {
  const validation = validateApproval(approval);
  if (!validation.ok) throw new BrokerGateError('INVALID_APPROVAL', validation.errors.join('; '));
  if (!isRecord(requested)) throw new BrokerGateError('APPROVAL_SCOPE_MISSING', 'requested approval scope is required');
  if (!isRecord(trustedRegistry) || !isRecord(trustedRegistry.records) || !isRecord(trustedRegistry.records[approval.approvalId]) || !Array.isArray(trustedRegistry.consumedIdempotencyKeys)) throw new BrokerGateError('TRUST_STATE_MISSING', 'trusted persistent approval registry is required');
  requireNow(now);
  equal(canonicalRecord(approval), canonicalRecord(trustedRegistry.records[approval.approvalId]), 'APPROVAL_IDENTITY_MISMATCH', 'complete approval record');
  if (approval.state !== 'GRANTED_SCOPED' || approval.useCount !== 0) throw new BrokerGateError('APPROVAL_UNAVAILABLE', 'approval is not an unused scoped grant');
  if (Date.parse(now) >= Date.parse(approval.expiresAt)) throw new BrokerGateError('APPROVAL_EXPIRED', 'approval expired');
  for (const key of ['actor', 'action', 'target', 'artifactDigest', 'environment', 'commissionHash']) equal(approval[key], requested[key], 'APPROVAL_SCOPE_MISMATCH', key);
  const idempotencyKey = requested.idempotencyKey;
  if (typeof idempotencyKey !== 'string' || idempotencyKey.trim() === '') throw new BrokerGateError('APPROVAL_SCOPE_MISSING', 'approval idempotencyKey is required');
  if (trustedRegistry.consumedIdempotencyKeys.includes(idempotencyKey)) throw new BrokerGateError('APPROVAL_REPLAY', 'approval idempotency key already consumed');
  const consumed = { ...approval, state: 'CONSUMED', useCount: 1, consumedAt: now };
  consumed.approvalDigest = sha256(approvalDigestPayload(consumed));
  const cas = createConsumptionCas({ registry: trustedRegistry, recordId: approval.approvalId, currentRecord: approval, nextRecord: consumed, idempotencyKey });
  return Object.freeze({ consumed: Object.freeze(consumed), cas: Object.freeze(cas) });
}

function createConsumptionCas({ registry, recordId, currentRecord, nextRecord, idempotencyKey }) {
  const value = {
    registryId: registry.registryId,
    expectedRegistryRevision: registry.revision,
    recordId,
    expectedRecordHash: sha256(currentRecord),
    nextRecord,
    nextRecordHash: sha256(nextRecord),
    idempotencyKey
  };
  value.casHash = sha256(value);
  return value;
}

function validateConsumptionCas(cas, trustedRegistry) {
  const errors = [];
  if (!isRecord(cas) || !isRecord(trustedRegistry) || !isRecord(trustedRegistry.records)) return { ok: false, errors: ['CAS and trusted registry must be plain objects'] };
  for (const key of ['registryId', 'recordId', 'idempotencyKey']) requireText(cas[key], `cas.${key}`, errors);
  for (const key of ['expectedRecordHash', 'nextRecordHash', 'casHash']) requireSha(cas[key], `cas.${key}`, errors);
  if (!Number.isSafeInteger(cas.expectedRegistryRevision) || cas.expectedRegistryRevision !== trustedRegistry.revision) errors.push('CAS registry revision mismatch');
  if (cas.registryId !== trustedRegistry.registryId) errors.push('CAS registry identity mismatch');
  const current = trustedRegistry.records[cas.recordId];
  if (!isRecord(current) || sha256(current) !== cas.expectedRecordHash) errors.push('CAS current record mismatch');
  if (!isRecord(cas.nextRecord) || sha256(cas.nextRecord) !== cas.nextRecordHash) errors.push('CAS next record mismatch');
  if (!Array.isArray(trustedRegistry.consumedIdempotencyKeys) || trustedRegistry.consumedIdempotencyKeys.includes(cas.idempotencyKey)) errors.push('CAS idempotency replay');
  if (isRecord(cas)) {
    const payload = { ...cas };
    delete payload.casHash;
    if (SHA256_LIKE(cas.casHash) && sha256(payload) !== cas.casHash) errors.push('CAS hash mismatch');
  }
  return { ok: errors.length === 0, errors };
}

function canonicalRecord(value) {
  return canonicalJson(value);
}

function SHA256_LIKE(value) {
  return typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
}

function requireNow(now) {
  const errors = [];
  requireRfc3339(now, 'now', errors);
  if (errors.length) throw new BrokerGateError('INVALID_TIME', errors.join('; '));
}

module.exports = {
  BrokerGateError,
  authorizeReadOnly,
  leaseDigestPayload,
  validateQueueLease,
  authorizeCompactionFence,
  approvalDigestPayload,
  validateApproval,
  authorizeApproval,
  createConsumptionCas,
  validateConsumptionCas
};
