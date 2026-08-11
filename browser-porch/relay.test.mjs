import test from 'node:test';
import assert from 'node:assert/strict';
import {createRelay} from './relay.mjs';
import {CONTRACT_VERSION, CHATGPT_ORIGIN, sha256} from './contract.mjs';

test('loopback relay requires ephemeral proof and enforces one pending writer', async (t) => {
  const server = createRelay({port: 0});
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}/v1`;
  const now = Date.now();
  const nonce = 'nonce-relay-0001';
  const intent = {contractVersion: CONTRACT_VERSION, pairingId: 'pairing-relay-01', sessionId: 'session-relay-01', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: sha256('account'), nonce, issuedAtMs: now - 100, expiresAtMs: now + 30_000, mode: 'observe'};
  assert.equal((await post(`${base}/intent`, intent)).status, 201);
  const observation = {gesture: 'extension_action_click', tabId: 7, url: 'https://chatgpt.com/', authenticationState: 'dom_verified', accountHash: sha256('account'), tabSessionId: 'tab-session-relay', leaseId: 'lease-relay-01'};
  const pair = await post(`${base}/pair`, {intent, observation});
  assert.equal(pair.status, 201);
  assert.equal((await fetch(`${base}/pairing?pairingId=${intent.pairingId}`)).status, 400);
  const headers = {'x-browser-porch-lease': nonce};
  assert.equal((await fetch(`${base}/pairing?pairingId=${intent.pairingId}`, {headers})).status, 200);
  const command = {pairingId: intent.pairingId, commandId: 'command-relay-01', action: 'inventory'};
  assert.equal((await post(`${base}/command`, command, headers)).status, 202);
  const second = await post(`${base}/command`, {...command, commandId: 'command-relay-02'}, headers);
  assert.equal(second.status, 409);
  assert.equal((await second.json()).error, 'PAIRING_LEASE_BUSY');
});

async function post(url, value, extra = {}) {
  return fetch(url, {method: 'POST', headers: {'content-type': 'application/json', ...extra}, body: JSON.stringify(value)});
}
