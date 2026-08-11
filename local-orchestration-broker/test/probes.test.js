'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { adapterInterfaces } = require('../src/adapters');
const { createProbe, validateProbeResult } = require('../src/probes');

const hash = 'd'.repeat(64);

test('every adapter exposes health and identity only', () => {
  assert.deepEqual(Object.keys(adapterInterfaces), ['computer_hands', 'browser_nerve', 'venice_nerve', 'codex', 'continue', 'qwen']);
  for (const descriptor of Object.values(adapterInterfaces)) assert.deepEqual(descriptor.operations, ['health', 'identity']);
});

test('probe results are bound to adapter, worker, and commission identity', () => {
  const probe = createProbe({ adapter: 'qwen', operation: 'health', commissionId: 'c1', commissionHash: hash, workerId: 'w1', workerIdentityHash: hash });
  const result = { mode: 'read_only', adapter: 'qwen', operation: 'health', workerId: 'w1', workerIdentityHash: hash, commissionHash: hash, observedAt: '2026-08-11T06:00:00Z', healthy: true };
  assert.equal(validateProbeResult(probe, result).ok, true);
  assert.equal(validateProbeResult(probe, { ...result, workerId: 'w2' }).ok, false);
});

test('source contains no runtime or mutation implementation', () => {
  const sourceDir = path.join(__dirname, '..', 'src');
  const source = fs.readdirSync(sourceDir).sort().map(file => fs.readFileSync(path.join(sourceDir, file), 'utf8')).join('\n');
  for (const forbidden of ['child_process', 'writeFile', 'appendFile', 'unlink', 'rmSync', 'fetch(', 'http.request', 'https.request', 'browser_sessions.act', 'phone_hands.enqueue']) assert.equal(source.includes(forbidden), false, forbidden);
});
