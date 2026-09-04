#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const browserPath = path.join(root, 'functions', 'browser_nerve_api.js');
const mcpPath = path.join(root, 'functions', 'home_center_mcp.js');
const testPath = path.join(root, 'functions', 'browser_nerve_home_center_ops.test.js');

function insertBeforeOnce(text, anchor, insertion, label) {
  const first = text.indexOf(anchor);
  if (first < 0) throw new Error(label + ' anchor missing');
  if (text.indexOf(anchor, first + anchor.length) >= 0) throw new Error(label + ' anchor is not unique');
  return text.slice(0, first) + insertion + text.slice(first);
}

function replaceRegexOnce(text, expression, replacement, label) {
  const matches = [...text.matchAll(new RegExp(expression.source, expression.flags.includes('g') ? expression.flags : expression.flags + 'g'))];
  if (matches.length !== 1) throw new Error(label + ' expected one match, found ' + matches.length);
  return text.replace(expression, replacement);
}

let browser = fs.readFileSync(browserPath, 'utf8');

const operationFunctions = String.raw`
function browserCallerPartition(user = {}) {
  const ownerEmail = safeEmail(user && user.email);
  const owner = ownerKey(ownerEmail);
  return {ownerEmail, owner, caller: {ownerKey: owner, actor: ownerEmail, email: ownerEmail}};
}

function browserSessionId(owner, requestId) {
  return safeId('browser-session-' + hash(String(owner || '') + '\n' + safeId(requestId, 'requestId')).slice(0, 24), 'sessionId');
}

function browserActionId(owner, requestId) {
  return safeId('browser-action-' + hash(String(owner || '') + '\n' + safeId(requestId, 'requestId')).slice(0, 24), 'actionId');
}

function publicBrowserTicket(row = {}) {
  const result = {...safeObject(row.result)};
  delete result.value;
  delete result.inputValue;
  delete result.typedValue;
  return {
    ticketId: safeText(row.ticketId, 180),
    actionId: safeText(row.actionId, 180),
    sessionId: safeText(row.sessionId, 180),
    workerId: safeText(row.workerId, 180),
    action: safeText(row.action, 80),
    target: safeObject(row.target),
    reason: safeText(row.reason, 2000),
    status: safeText(row.status, 80) || 'unknown',
    cancelRequested: row.cancelRequested === true,
    progress: safeObject(row.progress),
    result,
    createdAtMs: Number(row.createdAtMs || 0),
    updatedAtMs: Number(row.updatedAtMs || 0),
    completedAtMs: Number(row.completedAtMs || 0),
  };
}

async function ownedBrowserSession(admin, user, sessionId) {
  const partition = browserCallerPartition(user);
  const cleanSessionId = safeId(sessionId, 'sessionId');
  const ref = admin.firestore().collection(COLLECTIONS.sessions).doc(cleanSessionId);
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Browser Nerve session was not found.'), {status: 404, failureKind: 'browser_nerve_session_not_found'});
  const row = snap.data() || {};
  if (row.ownerKey !== partition.owner) throw Object.assign(new Error('Browser Nerve session was not found for this owner.'), {status: 404, failureKind: 'browser_nerve_session_not_found'});
  return {...partition, sessionId: cleanSessionId, ref, row};
}

async function createBrowserSessionOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const partition = browserCallerPartition(user);
  const sessionId = args.sessionId ? safeId(args.sessionId, 'sessionId') : browserSessionId(partition.owner, requestId);
  const intent = safeText(args.intent, 2000);
  if (!intent) throw Object.assign(new Error('Browser Nerve session intent is required.'), {status: 400, failureKind: 'browser_nerve_intent_required'});
  const startUrl = safeText(args.startUrl, 1000);
  if (startUrl && !safeOrigin(startUrl)) throw Object.assign(new Error('Browser Nerve startUrl must be an absolute URL.'), {status: 400, failureKind: 'browser_nerve_start_url_invalid'});
  const workerId = safeId(args.workerId || 'windows-browser-nerve-01', 'workerId');
  const ref = admin.firestore().collection(COLLECTIONS.sessions).doc(sessionId);
  let idempotent = false;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (snap.exists) {
      const row = snap.data() || {};
      if (row.ownerKey !== partition.owner) throw Object.assign(new Error('Browser Nerve session id is owned by another account.'), {status: 409, failureKind: 'browser_nerve_session_owner_conflict'});
      if (row.requestId !== requestId || row.intent !== intent || safeText(row.startUrl, 1000) !== startUrl || safeText(row.workerId, 180) !== workerId) {
        throw Object.assign(new Error('Browser Nerve session idempotency conflict.'), {status: 409, failureKind: 'browser_nerve_session_idempotency_conflict'});
      }
      idempotent = true;
      return;
    }
    tx.create(ref, {
      apiVersion: API_VERSION,
      contractVersion: CONTRACT_VERSION,
      sessionId,
      requestId,
      ownerKey: partition.owner,
      ownerEmail: partition.ownerEmail,
      intent,
      startUrl,
      workerId,
      surface: {runtime: 'browser_nerve', browser: 'chrome', mode: 'desktop', workerId},
      status: 'ready',
      lastActionId: '',
      lastTicketId: '',
      createdAtMs: nowMs,
      updatedAtMs: nowMs,
    });
  });
  return {sessionId, requestId, workerId, intent, startUrl, status: 'ready', idempotent};
}

async function browserSessionStatusOperation({admin, user, args = {}}) {
  const owned = await ownedBrowserSession(admin, user, args.sessionId);
  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', owned.owner).limit(100).get();
  const tickets = query.docs
    .map((doc) => doc.data() || {})
    .filter((row) => row.sessionId === owned.sessionId)
    .sort((a, b) => Number(a.createdAtMs || 0) - Number(b.createdAtMs || 0))
    .map(publicBrowserTicket);
  return {
    sessionId: owned.sessionId,
    intent: safeText(owned.row.intent, 2000),
    startUrl: safeText(owned.row.startUrl, 1000),
    workerId: safeText(owned.row.workerId || safeObject(owned.row.surface).workerId, 180),
    status: safeText(owned.row.status, 80) || 'unknown',
    lastActionId: safeText(owned.row.lastActionId, 180),
    lastTicketId: safeText(owned.row.lastTicketId, 180),
    lastUrl: safeText(owned.row.lastUrl, 1000),
    lastTitle: safeText(owned.row.lastTitle, 500),
    updatedAtMs: Number(owned.row.updatedAtMs || 0),
    ticketCount: tickets.length,
    tickets,
  };
}

async function enqueueBrowserActionOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const owned = await ownedBrowserSession(admin, user, args.sessionId);
  const action = actionName(args.action);
  const actionId = args.actionId ? safeId(args.actionId, 'actionId') : browserActionId(owned.owner, requestId);
  const workerId = safeId(args.workerId || owned.row.workerId || safeObject(owned.row.surface).workerId || 'windows-browser-nerve-01', 'workerId');
  const target = safeObject(args.target);
  const reason = safeText(args.reason, 2000) || safeText(owned.row.intent, 2000);
  const execution = await enqueueBrowserNerveTicket({
    admin,
    caller: owned.caller,
    args: {sessionId: owned.sessionId, actionId, action, target, value: args.value, reason, workerId},
    nowMs,
  });
  await owned.ref.set({status: 'action_queued', lastActionId: actionId, lastTicketId: execution.ticketId, updatedAtMs: nowMs}, {merge: true});
  return {...execution, requestId, action, target};
}

async function browserTicketStatusOperation({admin, user, args = {}}) {
  const partition = browserCallerPartition(user);
  const ticketId = safeId(args.ticketId, 'ticketId');
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(partition.owner, ticketId));
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Browser Nerve ticket was not found.'), {status: 404, failureKind: 'browser_nerve_ticket_not_found'});
  const row = snap.data() || {};
  if (row.ownerKey !== partition.owner) throw Object.assign(new Error('Browser Nerve ticket was not found for this owner.'), {status: 404, failureKind: 'browser_nerve_ticket_not_found'});
  return publicBrowserTicket(row);
}

async function cancelBrowserTicketOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const partition = browserCallerPartition(user);
  const ticketId = safeId(args.ticketId, 'ticketId');
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(partition.owner, ticketId));
  let result = null;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (!snap.exists) throw Object.assign(new Error('Browser Nerve ticket was not found.'), {status: 404, failureKind: 'browser_nerve_ticket_not_found'});
    const row = snap.data() || {};
    if (row.ownerKey !== partition.owner) throw Object.assign(new Error('Browser Nerve ticket was not found for this owner.'), {status: 404, failureKind: 'browser_nerve_ticket_not_found'});
    if (['completed', 'failed', 'cancelled'].includes(row.status)) {
      result = publicBrowserTicket(row);
      return;
    }
    const status = row.status === 'queued' ? 'cancelled' : row.status;
    const progress = {phase: status === 'cancelled' ? 'cancelled' : 'cancel_requested', message: safeText(args.reason, 400), updatedAtMs: nowMs};
    const next = {...row, status, cancelRequested: true, cancelRequestId: requestId, progress, updatedAtMs: nowMs};
    tx.set(ref, next, {merge: false});
    result = publicBrowserTicket(next);
  });
  return result;
}

`;

if (!browser.includes('async function createBrowserSessionOperation')) {
  browser = insertBeforeOnce(
    browser,
    'async function leaseRequest({admin, worker, nowMs = Date.now()}) {',
    operationFunctions,
    'Browser Nerve operation functions',
  );
}

const operationBlock = String.raw`function browserNerveOperationEntries() {
  return {
    'browser_nerve.worker.register': {summary: 'Mint a ten-minute bootstrap code for the dedicated outbound Windows Browser Nerve selector worker.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional windows-browser-nerve-01'}},
    'browser_nerve.worker.status': {summary: 'Read Browser Nerve worker heartbeat, selector capability, and queued browser work.', write: false, requiresRequestId: false, requiredScopes: [], input: {workerId: 'optional windows-browser-nerve-01'}},
    'browser_nerve.session.create': {summary: 'Create one owner-scoped durable Browser Nerve session for Chromium Throne browser work.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', sessionId: 'optional stable id', intent: 'bounded commissioned outcome', startUrl: 'optional absolute URL', workerId: 'optional windows-browser-nerve-01'}},
    'browser_nerve.session.status': {summary: 'Read one owner-scoped Browser Nerve session and its redacted action tickets.', write: false, requiresRequestId: false, requiredScopes: [], input: {sessionId: 'stable session id'}},
    'browser_nerve.action.enqueue': {summary: 'Queue one semantic Browser Nerve action in an existing owner-scoped session.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable idempotency id', sessionId: 'stable session id', actionId: 'optional stable id', action: SUPPORTED_ACTIONS, target: 'selector or URL target object', value: 'optional bounded input; never returned by status', reason: 'bounded commissioned reason', workerId: 'optional windows-browser-nerve-01'}},
    'browser_nerve.ticket.status': {summary: 'Read one owner-scoped Browser Nerve action ticket without returning typed input values.', write: false, requiresRequestId: false, requiredScopes: [], input: {ticketId: 'stable ticket id'}},
    'browser_nerve.ticket.cancel': {summary: 'Request cancellation of one owner-scoped Browser Nerve action ticket.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable cancellation id', ticketId: 'stable ticket id', reason: 'optional bounded reason'}},
  };
}
async function browserNerveOperationRunOperation({admin, user, operation, args = {}}) {
  if (operation === 'browser_nerve.worker.register') return registerWorkerOperation({admin, user, args});
  if (operation === 'browser_nerve.worker.status') return workerStatusOperation({admin, user, args});
  if (operation === 'browser_nerve.session.create') return createBrowserSessionOperation({admin, user, args});
  if (operation === 'browser_nerve.session.status') return browserSessionStatusOperation({admin, user, args});
  if (operation === 'browser_nerve.action.enqueue') return enqueueBrowserActionOperation({admin, user, args});
  if (operation === 'browser_nerve.ticket.status') return browserTicketStatusOperation({admin, user, args});
  if (operation === 'browser_nerve.ticket.cancel') return cancelBrowserTicketOperation({admin, user, args});
  throw Object.assign(new Error('Unsupported Browser Nerve operation.'), {status: 400});
}
`;

if (!browser.includes("'browser_nerve.action.enqueue'")) {
  browser = replaceRegexOnce(
    browser,
    /function browserNerveOperationEntries\(\) \{[\s\S]*?\n\}\nasync function browserNerveOperationRunOperation\(\{admin, user, operation, args = \{\}\}\) \{[\s\S]*?\n\}\n/,
    operationBlock,
    'Browser Nerve operation registry and runner',
  );
}

const exportOld = "  ownerKey, actionName, pairedBrowserWorkerId, pairWithComputerHands, registerWorkerOperation, workerStatusOperation, enqueueBrowserNerveTicket,\n  browserNerveOperationEntries, browserNerveOperationRunOperation, createBrowserNerveHandler,\n";
const exportNew = "  ownerKey, actionName, pairedBrowserWorkerId, pairWithComputerHands, registerWorkerOperation, workerStatusOperation, enqueueBrowserNerveTicket,\n  browserSessionId, browserActionId, publicBrowserTicket, createBrowserSessionOperation, browserSessionStatusOperation, enqueueBrowserActionOperation, browserTicketStatusOperation, cancelBrowserTicketOperation,\n  browserNerveOperationEntries, browserNerveOperationRunOperation, createBrowserNerveHandler,\n";
if (!browser.includes('createBrowserSessionOperation, browserSessionStatusOperation')) {
  if (!browser.includes(exportOld)) throw new Error('Browser Nerve export anchor missing');
  browser = browser.replace(exportOld, exportNew);
}
fs.writeFileSync(browserPath, browser);

let mcp = fs.readFileSync(mcpPath, 'utf8');
const priorRevision = "const HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-08-03.voice-tiers-host-file-v1';";
const nextRevision = "const HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-09-04.browser-nerve-action-surface-v1';";
if (mcp.includes(priorRevision)) mcp = mcp.replace(priorRevision, nextRevision);
else if (!mcp.includes(nextRevision)) throw new Error('Home Center connector revision changed; refuse to overwrite a newer registry revision');
if (!mcp.includes('...browserNerveOperationEntries()')) throw new Error('Home Center registry no longer spreads Browser Nerve operations');
if (!mcp.includes('browserNerveOperationRunOperation({admin, user, operation, args: operationArgs})')) throw new Error('Home Center runner no longer dispatches Browser Nerve operations');
fs.writeFileSync(mcpPath, mcp);

const testSource = String.raw`'use strict';

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
`;
fs.writeFileSync(testPath, testSource);

console.log(JSON.stringify({ok: true, changed: ['functions/browser_nerve_api.js', 'functions/home_center_mcp.js', 'functions/browser_nerve_home_center_ops.test.js']}));
