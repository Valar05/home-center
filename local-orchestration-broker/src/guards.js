'use strict';

const { READ_ONLY_OPERATIONS, validateCommissionEnvelope } = require('./contracts');

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
  if (!trusted || typeof trusted !== 'object') throw new BrokerGateError('TRUST_STATE_MISSING', 'trusted state is required');
  equal(commission.queue.revision, trusted.queueRevision, 'STALE_REVISION', 'queue revision');
  equal(commission.queue.stateOwner, trusted.stateOwner, 'OWNER_MISMATCH', 'state owner');
  equal(commission.lane.owner, trusted.laneOwner, 'OWNER_MISMATCH', 'lane owner');
  equal(commission.worker.workerId, trusted.workerId, 'IDENTITY_MISMATCH', 'worker id');
  equal(commission.worker.identityHash, trusted.workerIdentityHash, 'IDENTITY_MISMATCH', 'worker identity');
  equal(commission.commissionHash, trusted.commissionHash, 'COMMISSION_MISMATCH', 'commission hash');
  if (commission.mutating !== false) throw new BrokerGateError('MUTATION_FORBIDDEN', 'mutating requests are forbidden');
  if (commission.operations.some(operation => !READ_ONLY_OPERATIONS.includes(operation))) throw new BrokerGateError('MUTATION_FORBIDDEN', 'operation is not read-only');
  return Object.freeze({ authorized: true, mode: 'read_only', commissionId: commission.commissionId, operations: Object.freeze([...commission.operations]) });
}

module.exports = { BrokerGateError, authorizeReadOnly };
