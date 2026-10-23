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
  const intent = {contractVersion: CONTRACT_VERSION, pairingId: 'pairing-relay-01', sessionId: 'session-relay-01', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', commissionHash: sha256('commission'), expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: sha256('account'), nonce, issuedAtMs: now - 100, expiresAtMs: now + 30_000, mode: 'observe'};
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

test('throne queue is separately authenticated, origin-bound, leased, and durably receipted', async (t) => {
  const extensionOrigin = `chrome-extension://${'j'.repeat(32)}`;
  const throneCapability = 't'.repeat(48);
  const durableEvents = [];
  const server = createRelay({port: 0, extensionOrigin, throneCapability, eventSink: async (event) => durableEvents.push(event)});
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}/v1/throne`;
  const auth = {authorization: `Bearer ${throneCapability}`};
  const extension = {...auth, origin: extensionOrigin};
  const wrongOrigin = {...auth, origin: `chrome-extension://${'k'.repeat(32)}`};
  const command = {commandId: 'atom-swarm-command-001', action: 'swarm.enqueue', source: 'atom-vlad', jobs: [
    {jobId: 'atom-job-001', commission: 'Inspect SSH recovery only.', context: 'FORTRESS campaign'},
    {jobId: 'atom-job-002', commission: 'Inspect overlay recovery only.', context: 'FORTRESS campaign'},
  ]};

  assert.equal((await post(`${base}/command`, command)).status, 403);
  assert.equal((await post(`${base}/command`, command, auth)).status, 202);
  assert.equal((await post(`${base}/command`, command, auth)).status, 200, 'idempotent duplicate should not duplicate work');
  assert.equal(durableEvents[0].type, 'throne.command.queued');

  // Real MV3 fetch sometimes sends no Origin header, even with host
  // permissions. A valid bearer alone may lease on loopback; explicit
  // wrong/opaque origins must still fail closed.
  assert.equal((await fetch(`${base}/command`, {headers: wrongOrigin})).status, 403);
  assert.equal((await fetch(`${base}/command`, {headers: {...auth,origin:'null'}})).status, 403);
  const leased = await fetch(`${base}/command`, {headers: auth});
  assert.equal(leased.status, 200);
  const leasedJson = await leased.json();
  assert.equal(leasedJson.command.commandId, command.commandId);
  assert.equal(leasedJson.command.state, 'leased');
  assert.equal(leasedJson.command.jobs.length, 2);
  assert.equal((await fetch(`${base}/command`, {headers: extension})).status, 204, 'active lease must not be handed out twice');
  assert.equal(durableEvents.at(-1).type, 'throne.command.leased');

  assert.equal((await post(`${base}/complete`, {commandId: command.commandId, ok: true, result: {accepted: false}}, wrongOrigin)).status, 403);
  const complete = await post(`${base}/complete`, {commandId: command.commandId, ok: true, result: {accepted: false, workerCount: 2}}, extension);
  assert.equal(complete.status, 200);
  assert.equal(durableEvents.at(-1).type, 'throne.command.completed');
  assert.equal((await fetch(`${base}/command`, {headers: auth})).status, 204);
  assert.equal((await fetch(`${base}/command`, {headers: extension})).status, 204);

  const status = await fetch(`${base}/status`, {headers: auth});
  assert.equal(status.status, 200);
  const statusJson = await status.json();
  assert.equal(statusJson.commands[0].state, 'completed');
  assert.equal(statusJson.commands[0].commandId, command.commandId);
});

test('relay server-minted tab fence rejects a second live receipt for one document', async (t) => {
  const extensionOrigin = `chrome-extension://${'b'.repeat(32)}`;
  const nerveCapability = 'c'.repeat(48);
  const server = createRelay({port: 0, extensionOrigin, nerveCapability, eventSink: async () => {}});
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}/v1`;
  const now = Date.now();
  const common = {contractVersion: CONTRACT_VERSION, sessionId: 'session-relay-02', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', commissionHash: sha256('commission'), expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: sha256('account'), issuedAtMs: now - 100, expiresAtMs: now + 30_000, mode: 'observe'};
  const nerve = {authorization: `Bearer ${nerveCapability}`};
  const extension = {origin: extensionOrigin};
  for (const n of [1, 2]) assert.equal((await post(`${base}/intent`, {...common, pairingId: `pairing-fence-0${n}`, nonce: `nonce-fence-000${n}`}, nerve)).status, 201);
  const observation = {gesture: 'extension_action_click', windowId: 1, tabId: 2, documentId: 'document-fence-01', url: 'https://chatgpt.com/', authenticationState: 'dom_verified', accountHash: sha256('account')};
  assert.equal((await post(`${base}/pair`, {pairingId: 'pairing-fence-01', observation}, extension)).status, 201);
  const duplicate = await post(`${base}/pair`, {pairingId: 'pairing-fence-02', observation}, extension);
  assert.equal(duplicate.status, 409);
  assert.equal((await duplicate.json()).error, 'TAB_LEASE_BUSY');
});

test('expired pairing rejects commands and releases the exact tab fence', async (t) => {
  const extensionOrigin = `chrome-extension://${'d'.repeat(32)}`;
  const nerveCapability = 'e'.repeat(48);
  const server = createRelay({port: 0, extensionOrigin, nerveCapability, eventSink: async () => {}});
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}/v1`;
  const now = Date.now();
  const common = {contractVersion: CONTRACT_VERSION, sessionId: 'session-expiry-01', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', commissionHash: sha256('commission'), expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: sha256('account'), issuedAtMs: now - 10, mode: 'observe'};
  const nerve = {authorization: `Bearer ${nerveCapability}`};
  const extension = {origin: extensionOrigin};
  const first = {...common, pairingId: 'pairing-expiry-01', nonce: 'nonce-expiry-001', expiresAtMs: now + 80};
  const second = {...common, pairingId: 'pairing-expiry-02', nonce: 'nonce-expiry-002', expiresAtMs: now + 30_000};
  for (const intent of [first, second]) assert.equal((await post(`${base}/intent`, intent, nerve)).status, 201);
  const observation = {gesture: 'extension_action_click', windowId: 9, tabId: 10, documentId: 'document-expiry-01', url: 'https://chatgpt.com/', authenticationState: 'dom_verified', accountHash: sha256('account')};
  assert.equal((await post(`${base}/pair`, {pairingId: first.pairingId, observation}, extension)).status, 201);
  await new Promise((resolve) => setTimeout(resolve, 100));
  const staleCommand = {pairingId: first.pairingId, commandId: 'command-expiry-01', action: 'inventory'};
  assert.equal((await post(`${base}/command`, staleCommand, nerve)).status, 410);
  assert.equal((await post(`${base}/pair`, {pairingId: second.pairingId, observation: {...observation, documentId: 'document-expiry-02'}}, extension)).status, 201);
});

test('relay refuses to start without a durable event sink', () => {
  assert.throws(() => createRelay({port: 0, extensionOrigin: `chrome-extension://${'f'.repeat(32)}`, nerveCapability: 'g'.repeat(48)}), /event sink/);
});

test('durable sink failure rolls back pairing authority and tab fence', async (t) => {
  const extensionOrigin = `chrome-extension://${'h'.repeat(32)}`;
  const nerveCapability = 'i'.repeat(48);
  const server = createRelay({port: 0, extensionOrigin, nerveCapability, eventSink: async () => { throw new Error('durable sink unavailable'); }});
  await new Promise((resolve) => server.once('listening', resolve));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}/v1`;
  const now = Date.now();
  const intent = {contractVersion: CONTRACT_VERSION, pairingId: 'pairing-sink-001', sessionId: 'session-sink-001', workerId: 'windows-browser-nerve-01', commissionId: 'browser-porch-01', commissionHash: sha256('commission'), expectedOrigin: CHATGPT_ORIGIN, expectedAccountHash: sha256('account'), nonce: 'nonce-sink-0001', issuedAtMs: now - 10, expiresAtMs: now + 30_000, mode: 'observe'};
  const nerve = {authorization: `Bearer ${nerveCapability}`};
  const extension = {origin: extensionOrigin};
  const observation = {gesture: 'extension_action_click', windowId: 4, tabId: 5, documentId: 'document-sink-001', url: 'https://chatgpt.com/', authenticationState: 'dom_verified', accountHash: sha256('account')};
  assert.equal((await post(`${base}/intent`, intent, nerve)).status, 201);
  const failed = await post(`${base}/pair`, {pairingId: intent.pairingId, observation}, extension);
  assert.equal(failed.status, 503);
  assert.equal((await failed.json()).error, 'DURABLE_SINK_FAILED');
  assert.equal((await fetch(`${base}/pairing?pairingId=${intent.pairingId}`, {headers: nerve})).status, 404);
  assert.equal((await post(`${base}/command`, {pairingId: intent.pairingId, commandId: 'command-sink-001', action: 'inventory'}, nerve)).status, 404);
  const retry = await post(`${base}/pair`, {pairingId: intent.pairingId, observation}, extension);
  assert.equal(retry.status, 503);
  assert.equal((await retry.json()).error, 'DURABLE_SINK_FAILED');
});

async function post(url, value, extra = {}) {
  return fetch(url, {method: 'POST', headers: {'content-type': 'application/json', ...extra}, body: JSON.stringify(value)});
}
