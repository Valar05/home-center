'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  SUPPORTED_ACTIONS,
  browserSessionId,
  browserActionId,
  publicBrowserTicket,
  browserNerveOperationEntries,
} = require('./browser_nerve_api');

test('Home Center Browser Nerve registry exposes the bounded action surface', () => {
  const entries = browserNerveOperationEntries();
  const expected = [
    'browser_nerve.worker.register',
    'browser_nerve.worker.status',
    'browser_nerve.session.create',
    'browser_nerve.session.status',
    'browser_nerve.action.enqueue',
    'browser_nerve.ticket.status',
    'browser_nerve.ticket.cancel',
  ];
  for (const operation of expected) assert.ok(entries[operation], 'missing operation: ' + operation);
  assert.equal(entries['browser_nerve.action.enqueue'].write, true);
  assert.equal(entries['browser_nerve.action.enqueue'].requiresRequestId, true);
  assert.deepEqual(entries['browser_nerve.action.enqueue'].input.action, SUPPORTED_ACTIONS);
  assert.equal(entries['browser_nerve.ticket.status'].write, false);
  assert.equal(entries['browser_nerve.ticket.cancel'].write, true);
});

test('session and action ids are deterministic but occupy different namespaces', () => {
  const owner = 'owner_fixture_1234567890';
  const request = 'social-request-0001';
  assert.equal(browserSessionId(owner, request), browserSessionId(owner, request));
  assert.equal(browserActionId(owner, request), browserActionId(owner, request));
  assert.notEqual(browserSessionId(owner, request), browserActionId(owner, request));
});

test('public ticket status never returns queued or completed typed values', () => {
  const visible = publicBrowserTicket({
    ticketId: 'nerve-ticket-0001',
    actionId: 'browser-action-0001',
    sessionId: 'browser-session-0001',
    workerId: 'windows-browser-nerve-01',
    action: 'type',
    value: 'private draft text',
    status: 'completed',
    result: {ok: true, value: 'private draft text', typedValue: 'private draft text', url: 'https://example.invalid/post/1'},
  });
  assert.equal(Object.prototype.hasOwnProperty.call(visible, 'value'), false);
  assert.equal(Object.prototype.hasOwnProperty.call(visible.result, 'value'), false);
  assert.equal(Object.prototype.hasOwnProperty.call(visible.result, 'typedValue'), false);
  assert.equal(visible.result.url, 'https://example.invalid/post/1');
});

test('Home Center dynamic registry carries Browser Nerve operations without new top-level MCP tools', () => {
  const source = fs.readFileSync(path.join(__dirname, 'home_center_mcp.js'), 'utf8');
  assert.match(source, /\.\.\.browserNerveOperationEntries\(\)/);
  assert.match(source, /browserNerveOperationRunOperation\(\{admin, user, operation, args: operationArgs\}\)/);
  assert.match(source, /2026-09-04\.browser-nerve-action-surface-v1/);
});
