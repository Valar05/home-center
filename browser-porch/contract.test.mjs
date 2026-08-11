import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CONTRACT_VERSION, CHATGPT_ORIGIN, sha256, canonical, createEphemeralState, createPairReceipt, authorizeCommand, revokePairing} from './contract.mjs';

const NOW = 1_786_452_000_000;
const ACCOUNT = sha256('fixture local account label');
const baseIntent = (overrides = {}) => ({contractVersion: CONTRACT_VERSION, pairingId: 'pairing-0001', sessionId: 'session-0001', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', commissionHash: sha256('browser porch commission'), expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: ACCOUNT, nonce: 'nonce-000001', issuedAtMs: NOW - 1000, expiresAtMs: NOW + 59000, mode: 'observe', ...overrides});
const observation = (overrides = {}) => ({gesture: 'extension_action_click', tabId: 37, url: 'https://chatgpt.com/', authenticationState: 'dom_verified', accountHash: ACCOUNT, tabSessionId: 'tab-session-0001', leaseId: 'lease-000001', ...overrides});

function paired() { const state = createEphemeralState(); const receipt = createPairReceipt(baseIntent(), observation(), state, NOW); return {state, receipt}; }
function command(receipt, overrides = {}) { return {commandId: 'command-0001', action: 'inventory', sessionId: receipt.sessionId, workerId: receipt.workerId, commissionId: receipt.commissionId, commissionHash: receipt.commissionHash, origin: receipt.origin, accountHash: receipt.accountHash, tabId: receipt.tabId, tabSessionId: receipt.tabSessionId, leaseId: receipt.leaseId, currentUrl: 'https://chatgpt.com/', currentDocumentId: receipt.tabSessionId, currentAccountHash: ACCOUNT, authenticationState: 'dom_verified', ...overrides}; }

test('explicit user gesture creates an append-only observe-only receipt without secrets', () => {
  const {state, receipt} = paired();
  assert.equal(receipt.mode, 'observe'); assert.equal(receipt.cookiesRead, false); assert.equal(receipt.credentialsRead, false); assert.equal(receipt.secretsPersisted, false);
  assert.deepEqual(state.events.map((row) => row.type), ['paired']);
  const {receiptHash, ...unsigned} = receipt;
  assert.equal(receiptHash, sha256(canonical(unsigned)));
});
test('wrong origin is rejected', () => assert.throws(() => createPairReceipt(baseIntent(), observation({url: 'https://evil.example/'}), createEphemeralState(), NOW), {code: 'ORIGIN_MISMATCH'}));
test('wrong account is rejected', () => assert.throws(() => createPairReceipt(baseIntent(), observation({accountHash: sha256('other')}), createEphemeralState(), NOW), {code: 'ACCOUNT_MISMATCH'}));
test('wrong tab is rejected at command time', () => { const {state, receipt} = paired(); assert.throws(() => authorizeCommand(receipt, command(receipt, {tabId: 99}), state, NOW), {code: 'TAB_ID_MISMATCH'}); });
test('stale pairing is rejected', () => assert.throws(() => createPairReceipt(baseIntent({expiresAtMs: NOW - 1}), observation(), createEphemeralState(), NOW), {code: 'STALE_PAIRING'}));
test('replayed pairing nonce is rejected', () => { const state = createEphemeralState(); createPairReceipt(baseIntent(), observation(), state, NOW); assert.throws(() => createPairReceipt(baseIntent({pairingId: 'pairing-0002'}), observation(), state, NOW), {code: 'PAIRING_REPLAY'}); });
test('cross-session use is rejected', () => { const {state, receipt} = paired(); assert.throws(() => authorizeCommand(receipt, command(receipt, {sessionId: 'session-other'}), state, NOW), {code: 'SESSION_ID_MISMATCH'}); });
test('tab navigation away is rejected', () => { const {state, receipt} = paired(); assert.throws(() => authorizeCommand(receipt, command(receipt, {currentUrl: 'https://example.com/'}), state, NOW), {code: 'TAB_NAVIGATED'}); });
test('same-origin new document is rejected', () => { const {state, receipt} = paired(); assert.throws(() => authorizeCommand(receipt, command(receipt, {currentDocumentId: 'document-other'}), state, NOW), {code: 'TAB_DOCUMENT_CHANGED'}); });
test('extension restart fails closed because a new ephemeral state knows no pairing', () => { const {receipt} = paired(); assert.throws(() => authorizeCommand(receipt, command(receipt), createEphemeralState(), NOW), {code: 'PAIRING_UNKNOWN'}); });
test('revoke is immediate and append-only', () => { const {state, receipt} = paired(); revokePairing(receipt.pairingId, state, NOW); assert.throws(() => authorizeCommand(receipt, command(receipt), state, NOW), {code: 'PAIRING_REVOKED'}); assert.deepEqual(state.events.map((row) => row.type), ['paired', 'revoked']); });
test('mutation without separate approval is rejected', () => { const {state, receipt} = paired(); assert.throws(() => authorizeCommand(receipt, command(receipt, {action: 'conversation.move'}), state, NOW), {code: 'MUTATION_NOT_APPROVED'}); });
test('mutation approval cannot cross command digest', () => { const {state, receipt} = paired(); const mutation = command(receipt, {action: 'conversation.move', target: {conversationId: 'conv-000001', projectId: 'project-0001'}, mutationApproval: {approvalId: 'approval-0001', pairingId: receipt.pairingId, sessionId: receipt.sessionId, workerId: receipt.workerId, commissionId: receipt.commissionId, commissionHash: receipt.commissionHash, origin: receipt.origin, accountHash: receipt.accountHash, tabId: receipt.tabId, tabSessionId: receipt.tabSessionId, expiresAtMs: NOW + 10_000, commandDigest: sha256('wrong')}}); assert.throws(() => authorizeCommand(receipt, mutation, state, NOW), {code: 'APPROVAL_DIGEST_MISMATCH'}); });
test('false authentication claims are rejected', () => assert.throws(() => createPairReceipt(baseIntent(), observation({authenticationState: 'unverified'}), createEphemeralState(), NOW), {code: 'AUTHENTICATION_UNVERIFIED'}));
test('missing user gesture is rejected', () => assert.throws(() => createPairReceipt(baseIntent(), observation({gesture: 'background_probe'}), createEphemeralState(), NOW), {code: 'USER_GESTURE_REQUIRED'}));
test('command replay is rejected', () => { const {state, receipt} = paired(); authorizeCommand(receipt, command(receipt), state, NOW); assert.throws(() => authorizeCommand(receipt, command(receipt), state, NOW), {code: 'COMMAND_REPLAY'}); });
test('extension has no cookie, credential, storage, arbitrary-tab, or broad-host authority', () => {
  const manifest = JSON.parse(readFileSync(new URL('./extension/manifest.json', import.meta.url), 'utf8'));
  assert.deepEqual(manifest.permissions, ['activeTab', 'scripting']);
  assert.deepEqual(manifest.host_permissions, ['http://127.0.0.1:9234/*']);
  const source = readFileSync(new URL('./extension/service-worker.js', import.meta.url), 'utf8');
  for (const forbidden of ['chrome.cookies', 'document.cookie', 'chrome.storage', 'chrome.debugger', '<all_urls>', 'password']) assert.equal(source.includes(forbidden), false, forbidden);
});
