#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const browserPath = path.join(root, 'functions', 'browser_nerve_api.js');
const testPath = path.join(root, 'functions', 'browser_nerve_home_center_ops.test.js');
let browser = fs.readFileSync(browserPath, 'utf8');

function replaceOnce(text, before, after, label) {
  const first = text.indexOf(before);
  if (first < 0) throw new Error(label + ' anchor missing');
  if (text.indexOf(before, first + before.length) >= 0) throw new Error(label + ' anchor is not unique');
  return text.slice(0, first) + after + text.slice(first + before.length);
}

if (!browser.includes('const requestFingerprint = hash(JSON.stringify({sessionId, actionId, action, workerId, target, value, reason}));')) {
  browser = replaceOnce(
    browser,
    "  const reason = safeText(args.reason, 2000);\n  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId));",
    "  const reason = safeText(args.reason, 2000);\n  const requestFingerprint = hash(JSON.stringify({sessionId, actionId, action, workerId, target, value, reason}));\n  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId));",
    'Browser Nerve request fingerprint',
  );
  browser = replaceOnce(
    browser,
    "      if (old.actionId !== actionId || old.sessionId !== sessionId || old.action !== action) throw Object.assign(new Error('Browser Nerve ticket idempotency conflict.'), {status: 409});",
    "      const oldFingerprint = safeText(old.requestFingerprint, 128) || hash(JSON.stringify({sessionId: old.sessionId, actionId: old.actionId, action: old.action, workerId: old.workerId, target: safeObject(old.target), value: old.value == null ? '' : String(old.value), reason: safeText(old.reason, 2000)}));\n      if (oldFingerprint !== requestFingerprint) throw Object.assign(new Error('Browser Nerve ticket idempotency conflict.'), {status: 409, failureKind: 'browser_nerve_ticket_idempotency_conflict'});",
    'Browser Nerve full idempotency comparison',
  );
  browser = replaceOnce(
    browser,
    "      workerId, action, target, value, reason, status: 'queued', cancelRequested: false,",
    "      workerId, action, target, value, reason, requestFingerprint, status: 'queued', cancelRequested: false,",
    'Browser Nerve stored request fingerprint',
  );
}

if (!browser.includes("!['http:', 'https:'].includes(parsedStartUrl.protocol)")) {
  browser = replaceOnce(
    browser,
    "  const startUrl = safeText(args.startUrl, 1000);\n  if (startUrl && !safeOrigin(startUrl)) throw Object.assign(new Error('Browser Nerve startUrl must be an absolute URL.'), {status: 400, failureKind: 'browser_nerve_start_url_invalid'});",
    "  const startUrl = safeText(args.startUrl, 1000);\n  let parsedStartUrl = null;\n  try { if (startUrl) parsedStartUrl = new URL(startUrl); } catch {}\n  if (startUrl && (!parsedStartUrl || !['http:', 'https:'].includes(parsedStartUrl.protocol))) throw Object.assign(new Error('Browser Nerve startUrl must be an absolute HTTP(S) URL.'), {status: 400, failureKind: 'browser_nerve_start_url_invalid'});",
    'Browser Nerve HTTP start URL validation',
  );
}

if (!browser.includes("failureKind: 'browser_nerve_navigate_url_invalid'")) {
  browser = replaceOnce(
    browser,
    "  const target = safeObject(args.target);\n  const reason = safeText(args.reason, 2000) || safeText(owned.row.intent, 2000);",
    "  const target = safeObject(args.target);\n  if (action === 'navigate') {\n    const navigateUrl = safeText(target.url, 1000);\n    let parsedNavigateUrl = null;\n    try { if (navigateUrl) parsedNavigateUrl = new URL(navigateUrl); } catch {}\n    if (!parsedNavigateUrl || !['http:', 'https:'].includes(parsedNavigateUrl.protocol)) throw Object.assign(new Error('Browser Nerve navigate target.url must be an absolute HTTP(S) URL.'), {status: 400, failureKind: 'browser_nerve_navigate_url_invalid'});\n  }\n  const reason = safeText(args.reason, 2000) || safeText(owned.row.intent, 2000);",
    'Browser Nerve navigate URL validation',
  );
}

fs.writeFileSync(browserPath, browser);

const testSource = String.raw`'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  SUPPORTED_ACTIONS,
  ownerKey,
  browserSessionId,
  browserActionId,
  publicBrowserTicket,
  createBrowserSessionOperation,
  enqueueBrowserActionOperation,
  browserTicketStatusOperation,
  cancelBrowserTicketOperation,
  browserNerveOperationEntries,
} = require('./browser_nerve_api');

function fakeAdmin() {
  const rows = new Map();
  const snapshot = (key) => ({
    exists: rows.has(key),
    data: () => rows.get(key),
  });
  const doc = (collectionName, id) => {
    const key = collectionName + '/' + id;
    return {
      key,
      path: key,
      async get() { return snapshot(key); },
      async set(value, options = {}) {
        const previous = rows.get(key) || {};
        rows.set(key, options.merge ? {...previous, ...value} : {...value});
      },
    };
  };
  const collection = (name) => ({
    doc(id) { return doc(name, id); },
    where(field, operator, expected) {
      assert.equal(operator, '==');
      return {
        limit() {
          return {
            async get() {
              const prefix = name + '/';
              const docs = [...rows.entries()]
                .filter(([key, value]) => key.startsWith(prefix) && value[field] === expected)
                .map(([, value]) => ({data: () => value}));
              return {docs};
            },
          };
        },
      };
    },
  });
  const firestore = {
    collection,
    async runTransaction(callback) {
      const tx = {
        async get(ref) { return ref.get(); },
        create(ref, value) {
          if (rows.has(ref.key)) throw new Error('already exists');
          rows.set(ref.key, {...value});
        },
        set(ref, value, options = {}) {
          const previous = rows.get(ref.key) || {};
          rows.set(ref.key, options.merge ? {...previous, ...value} : {...value});
        },
        update(ref, value) {
          if (!rows.has(ref.key)) throw new Error('missing');
          rows.set(ref.key, {...rows.get(ref.key), ...value});
        },
      };
      return callback(tx);
    },
  };
  return {admin: {firestore: () => firestore}, rows};
}

const user = {email: 'dclarke1005@gmail.com'};

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

test('owner-scoped session and action lifecycle is idempotent, redacted, and cancellable', async () => {
  const {admin} = fakeAdmin();
  const session = await createBrowserSessionOperation({
    admin,
    user,
    args: {requestId: 'session-request-0001', intent: 'Publish one approved thought', startUrl: 'https://example.invalid/'},
    nowMs: 1000,
  });
  const first = await enqueueBrowserActionOperation({
    admin,
    user,
    args: {requestId: 'action-request-0001', sessionId: session.sessionId, action: 'type', target: {role: 'textbox', name: 'Post'}, value: 'approved draft', reason: 'approved publication'},
    nowMs: 2000,
  });
  const replay = await enqueueBrowserActionOperation({
    admin,
    user,
    args: {requestId: 'action-request-0001', sessionId: session.sessionId, action: 'type', target: {role: 'textbox', name: 'Post'}, value: 'approved draft', reason: 'approved publication'},
    nowMs: 3000,
  });
  assert.equal(first.ticketId, replay.ticketId);
  assert.equal(replay.idempotent, true);
  await assert.rejects(
    enqueueBrowserActionOperation({
      admin,
      user,
      args: {requestId: 'action-request-0001', sessionId: session.sessionId, action: 'type', target: {role: 'textbox', name: 'Post'}, value: 'different draft', reason: 'approved publication'},
      nowMs: 4000,
    }),
    /idempotency conflict/,
  );
  const visible = await browserTicketStatusOperation({admin, user, args: {ticketId: first.ticketId}});
  assert.equal(Object.prototype.hasOwnProperty.call(visible, 'value'), false);
  const cancelled = await cancelBrowserTicketOperation({admin, user, args: {requestId: 'cancel-request-0001', ticketId: first.ticketId, reason: 'operator stop'}, nowMs: 5000});
  assert.equal(cancelled.status, 'cancelled');
  assert.equal(cancelled.cancelRequested, true);
});

test('session creation and navigate actions reject non-HTTP execution surfaces', async () => {
  const {admin} = fakeAdmin();
  await assert.rejects(
    createBrowserSessionOperation({admin, user, args: {requestId: 'session-request-0002', intent: 'Reject unsafe URL', startUrl: 'javascript:alert(1)'}}),
    /HTTP\(S\)/,
  );
  const session = await createBrowserSessionOperation({admin, user, args: {requestId: 'session-request-0003', intent: 'Navigate safely', startUrl: 'https://example.invalid/'}});
  await assert.rejects(
    enqueueBrowserActionOperation({admin, user, args: {requestId: 'action-request-0002', sessionId: session.sessionId, action: 'navigate', target: {url: 'file:///etc/passwd'}}}),
    /HTTP\(S\)/,
  );
});

test('Home Center dynamic registry carries Browser Nerve operations without new top-level MCP tools', () => {
  const source = fs.readFileSync(path.join(__dirname, 'home_center_mcp.js'), 'utf8');
  assert.match(source, /\.\.\.browserNerveOperationEntries\(\)/);
  assert.match(source, /browserNerveOperationRunOperation\(\{admin, user, operation, args: operationArgs\}\)/);
  assert.match(source, /2026-09-04\.browser-nerve-action-surface-v1/);
  assert.equal(ownerKey(user.email).startsWith('owner_'), true);
});
`;
fs.writeFileSync(testPath, testSource);

console.log(JSON.stringify({ok: true, hardened: ['full-payload idempotency', 'HTTP(S)-only initial navigation', 'Firestore lifecycle contract']}));
