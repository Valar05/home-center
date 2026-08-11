import test from 'node:test';
import assert from 'node:assert/strict';
import {createRelay} from './relay.mjs';
import {CONTRACT_VERSION, CHATGPT_ORIGIN, sha256} from './contract.mjs';

test('loopback relay requires ephemeral proof and enforces one pending writer', async (t) => {
  const extensionOrigin = `chrome-extension://${'a'.repeat(32)}`;
  const nerveCapability = 'n'.repeat(48);
  const durableEvents = [];
  const server = createRelay({port: 0, extensionOrigin, nerveCapability, eventSink: async (event) => durableEvents.push(event)});
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}/v1`;
  const now = Date.now();
  const nonce = 'nonce-relay-0001';
  const intent = {contractVersion: CONTRACT_VERSION, pairingId: 'pairing-relay-01', sessionId: 'session-relay-01', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: sha256('account'), nonce, issuedAtMs: now - 100, expiresAtMs: now + 30_000, mode: 'observe'};
  const nerve = {authorization: `Bearer ${nerveCapability}`};
  const extension = {origin: extensionOrigin};
  assert.equal((await post(`${base}/intent`, intent, nerve)).status, 201);
  const observation = {gesture: 'extension_action_click', windowId: 3, tabId: 7, documentId: 'document-relay-01', url: 'https://chatgpt.com/', authenticationState: 'dom_verified', accountHash: sha256('account')};
  assert.equal((await post(`${base}/pair`, {pairingId: 'unregistered-01', observation}, extension)).status, 409);
  const pair = await post(`${base}/pair`, {pairingId: intent.pairingId, observation}, extension);
  assert.equal(pair.status, 201);
  assert.equal(durableEvents.length, 1);
  assert.equal((await fetch(`${base}/pairing?pairingId=${intent.pairingId}`)).status, 403);
  assert.equal((await fetch(`${base}/pairing?pairingId=${intent.pairingId}`, {headers: nerve})).status, 200);
  const command = {pairingId: intent.pairingId, commandId: 'command-relay-01', action: 'inventory'};
  assert.equal((await post(`${base}/command`, command, nerve)).status, 202);
  assert.equal((await fetch(`${base}/command?pairingId=${intent.pairingId}`)).status, 403);
  assert.equal((await fetch(`${base}/command?pairingId=${intent.pairingId}`, {headers: extension})).status, 200);
  const forged = await post(`${base}/complete`, {pairingId: intent.pairingId, commandId: 'command-wrong', result: {ok: true}}, extension);
  assert.equal(forged.status, 409);
  const second = await post(`${base}/command`, {...command, commandId: 'command-relay-02'}, nerve);
  assert.equal(second.status, 409);
  assert.equal((await second.json()).error, 'PAIRING_LEASE_BUSY');
  assert.equal((await post(`${base}/revoke`, {pairingId: intent.pairingId})).status, 403);
  assert.equal((await post(`${base}/revoke`, {pairingId: intent.pairingId}, extension)).status, 200);
  assert.equal(durableEvents.length, 2);
  const preflight = await fetch(`${base}/intent`, {method: 'OPTIONS', headers: {origin: extensionOrigin, 'access-control-request-method': 'GET'}});
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get('access-control-allow-origin'), extensionOrigin);
  assert.match(preflight.headers.get('access-control-allow-methods'), /POST/);
});

test('relay server-minted tab fence rejects a second live receipt for one document', async (t) => {
  const extensionOrigin = `chrome-extension://${'b'.repeat(32)}`;
  const nerveCapability = 'c'.repeat(48);
  const server = createRelay({port: 0, extensionOrigin, nerveCapability});
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}/v1`;
  const now = Date.now();
  const common = {contractVersion: CONTRACT_VERSION, sessionId: 'session-relay-02', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: sha256('account'), issuedAtMs: now - 100, expiresAtMs: now + 30_000, mode: 'observe'};
  const nerve = {authorization: `Bearer ${nerveCapability}`};
  const extension = {origin: extensionOrigin};
  for (const n of [1, 2]) assert.equal((await post(`${base}/intent`, {...common, pairingId: `pairing-fence-0${n}`, nonce: `nonce-fence-000${n}`}, nerve)).status, 201);
  const observation = {gesture: 'extension_action_click', windowId: 1, tabId: 2, documentId: 'document-fence-01', url: 'https://chatgpt.com/', authenticationState: 'dom_verified', accountHash: sha256('account')};
  assert.equal((await post(`${base}/pair`, {pairingId: 'pairing-fence-01', observation}, extension)).status, 201);
  const duplicate = await post(`${base}/pair`, {pairingId: 'pairing-fence-02', observation}, extension);
  assert.equal(duplicate.status, 409);
  assert.equal((await duplicate.json()).error, 'TAB_LEASE_BUSY');
});

async function post(url, value, extra = {}) {
  return fetch(url, {method: 'POST', headers: {'content-type': 'application/json', ...extra}, body: JSON.stringify(value)});
}
