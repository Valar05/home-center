'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('./computer_hands_api');

test('packet.execute sanitizes bounded multi-step packets', () => {
  const packet = api.sanitizeActionArgs('packet.execute', {label: 'archaeology', steps: [
    {id: 'status', action: 'system.status', arguments: {}},
    {id: 'windows', action: 'window.list', arguments: {}},
    {id: 'shell', action: 'shell.exec', arguments: {command: 'Get-Date'}},
  ]});
  assert.equal(packet.steps.length, 3);
  assert.equal(packet.steps[2].arguments.command, 'Get-Date');
  assert.equal(api.permissionClass('packet.execute', packet), 'high_risk_write');
});

test('packet nesting and oversize step counts fail closed', () => {
  assert.throws(() => api.sanitizeActionArgs('packet.execute', {steps: [{action: 'packet.execute', arguments: {steps: []}}]}), /Nested packet/);
  assert.throws(() => api.sanitizeActionArgs('packet.execute', {steps: Array.from({length: 33}, () => ({action: 'system.status'}))}), /1-32/);
});

test('lane ids preserve safe ids and hash unsafe thread names', () => {
  assert.equal(api.safeLaneId('chat.thread-01'), 'chat.thread-01');
  assert.match(api.safeLaneId('thread with spaces / punctuation'), /^lane-[0-9a-f]{24}$/);
});
