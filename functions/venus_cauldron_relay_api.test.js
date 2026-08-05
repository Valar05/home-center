'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('./venus_cauldron_relay_api');

test('model allowlist is explicit, deduplicated, and syntax bounded', () => {
  assert.deepEqual(api.modelAllowlist('qwen3.5:4b, qwen3.5:4b, ../../bad, qwen3.5:2b'), ['qwen3.5:4b', 'qwen3.5:2b']);
});

test('client authentication fails closed when unset or mismatched', () => {
  const req = {get: () => 'Bearer secret'};
  assert.throws(() => api.authenticateClient(req, ''), {failureKind: 'venus_relay_client_auth_invalid'});
  assert.throws(() => api.authenticateClient(req, 'different'), {failureKind: 'venus_relay_client_auth_invalid'});
  assert.doesNotThrow(() => api.authenticateClient(req, 'secret'));
});

test('operation registry exposes register, status, and revoke only', () => {
  assert.deepEqual(Object.keys(api.operationEntries()).sort(), ['venus_relay.worker.register', 'venus_relay.worker.revoke', 'venus_relay.worker.status']);
});

