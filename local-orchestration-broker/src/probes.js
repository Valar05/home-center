'use strict';

const { ADAPTER_NAMES, READ_ONLY_OPERATIONS } = require('./contracts');

function createProbe({ adapter, operation, commissionId, commissionHash, workerId, workerIdentityHash }) {
  if (!ADAPTER_NAMES.includes(adapter)) throw new TypeError(`unsupported adapter: ${adapter}`);
  if (!READ_ONLY_OPERATIONS.includes(operation)) throw new TypeError(`unsupported read-only operation: ${operation}`);
  for (const [key, value] of Object.entries({ commissionId, commissionHash, workerId, workerIdentityHash })) {
    if (typeof value !== 'string' || value.length === 0) throw new TypeError(`${key} is required`);
  }
  return Object.freeze({ schemaVersion: 1, kind: 'probe', mode: 'read_only', adapter, operation, commissionId, commissionHash, worker: Object.freeze({ workerId, identityHash: workerIdentityHash }) });
}

function validateProbeResult(probe, result) {
  if (!result || typeof result !== 'object') return { ok: false, errors: ['result must be an object'] };
  const errors = [];
  if (result.mode !== 'read_only') errors.push('result.mode must be read_only');
  if (result.adapter !== probe.adapter) errors.push('result.adapter identity mismatch');
  if (result.operation !== probe.operation) errors.push('result.operation mismatch');
  if (result.workerId !== probe.worker.workerId || result.workerIdentityHash !== probe.worker.identityHash) errors.push('result.worker identity mismatch');
  if (result.commissionHash !== probe.commissionHash) errors.push('result.commission mismatch');
  if (typeof result.observedAt !== 'string' || result.observedAt.length === 0) errors.push('result.observedAt is required');
  return { ok: errors.length === 0, errors };
}

module.exports = { createProbe, validateProbeResult };
