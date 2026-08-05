'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const relay = require('./venus_cauldron_contract');

const allowlist = ['qwen3.5:4b'];
const input = {model: 'qwen3.5:4b', messages: [{role: 'system', content: 'You are Venus.'}, {role: 'user', content: 'Vow.'}], temperature: 0.78, max_tokens: 900};

test('canonical request strips unapproved fields and binds an allowlisted model', () => {
  const request = relay.canonicalRequest({...input, user: 'ignored'}, allowlist);
  assert.equal(request.provider, 'local_cauldron');
  assert.equal(request.engine, 'ollama');
  assert.equal(request.model, 'qwen3.5:4b');
  assert.equal(request.user, undefined);
});

test('forbidden models, tools, multimodal content, and streaming fail closed', () => {
  assert.throws(() => relay.canonicalRequest({...input, model: 'gpt-oss:20b'}, allowlist), {code: 'venus_relay_model_forbidden'});
  assert.throws(() => relay.canonicalRequest({...input, tools: [{}]}, allowlist), {code: 'venus_relay_capability_forbidden'});
  assert.throws(() => relay.canonicalRequest({...input, stream: true}, allowlist), {code: 'venus_relay_stream_unsupported'});
  assert.throws(() => relay.canonicalRequest({...input, messages: [{role: 'user', content: [{type: 'text', text: 'no'}]}]}, allowlist), {code: 'venus_relay_message_invalid'});
});

test('idempotency is immutable', () => {
  const first = relay.createTicket({requestId: 'venus-canary-001', input, allowlist, nowMs: 1000});
  assert.equal(relay.reconcileTicket(first, relay.createTicket({requestId: 'venus-canary-001', input, allowlist, nowMs: 2000})), first);
  assert.throws(() => relay.reconcileTicket(first, relay.createTicket({requestId: 'venus-canary-001', input: {...input, messages: [{role: 'user', content: 'changed'}]}, allowlist})), {code: 'venus_relay_idempotency_conflict'});
});

test('lease and completion preserve worker, model, and provider identity', () => {
  const ticket = relay.createTicket({requestId: 'venus-canary-002', input, allowlist, nowMs: 1000});
  assert.throws(() => relay.leaseTicket(ticket, {workerId: 'cauldron-llm-01', models: []}, 2000), {code: 'venus_relay_worker_model_mismatch'});
  const leased = relay.leaseTicket(ticket, {workerId: 'cauldron-llm-01', models: allowlist}, 2000);
  const complete = relay.completeTicket(leased, 'cauldron-llm-01', {model: 'qwen3.5:4b', content: 'A reply.'}, 3000);
  assert.equal(complete.completion.provider, 'local_cauldron');
  assert.equal(complete.completion.system_fingerprint, 'local_cauldron:ollama');
  assert.equal(complete.receipt.ollamaExposure, 'loopback_only');
});

