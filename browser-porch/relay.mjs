import http from 'node:http';
import {randomUUID} from 'node:crypto';
import {createEphemeralState, createPairReceipt, authorizeCommand, revokePairing, sha256, validatePairIntent} from './contract.mjs';

const state = createEphemeralState();
export function createRelay({host = '127.0.0.1', port = 9234, extensionOrigin = process.env.HOME_CENTER_BROWSER_PORCH_EXTENSION_ORIGIN, nerveCapability = process.env.HOME_CENTER_BROWSER_PORCH_NERVE_CAPABILITY, eventSink} = {}) {
  if (!/^chrome-extension:\/\/[a-p]{32}$/.test(String(extensionOrigin || ''))) throw new Error('exact Browser Porch extension origin is required');
  if (String(nerveCapability || '').length < 32) throw new Error('ephemeral Browser Nerve capability is required');
  if (typeof eventSink !== 'function') throw new Error('durable Home Center event sink integration is required');
  const state = createEphemeralState();
  const intents = new Map();
  const pending = new Map();
  const completions = new Map();
  const activeTabs = new Map();
  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://${host}:${port}`);
      if (req.method === 'OPTIONS') {
        requireExtension(req, extensionOrigin);
        res.statusCode = 204;
        cors(res, extensionOrigin);
        return res.end();
      }
      if (req.method === 'POST' && url.pathname === '/v1/intent') {
        requireNerve(req, nerveCapability);
        const intent = validatePairIntent(await body(req));
        if (intents.has(intent.pairingId)) return send(res, 409, {ok: false, error: 'INTENT_EXISTS'});
        intents.set(intent.pairingId, {intent, intentHash: sha256(JSON.stringify(intent))});
        return send(res, 201, {ok: true, pairingId: intent.pairingId, intentHash: intents.get(intent.pairingId).intentHash});
      }
      if (req.method === 'GET' && url.pathname === '/v1/intent') {
        requireExtension(req, extensionOrigin);
        const row = [...intents.values()].sort((a, b) => a.intent.issuedAtMs - b.intent.issuedAtMs)[0];
        if (!row) return send(res, 404, {ok: false, error: 'NO_INTENT'}, extensionOrigin);
        return send(res, 200, row.intent, extensionOrigin);
      }
      if (req.method === 'POST' && url.pathname === '/v1/pair') {
        requireExtension(req, extensionOrigin);
        const input = await body(req);
        const row = intents.get(input.pairingId);
        if (!row) return send(res, 409, {ok: false, error: 'INTENT_NOT_REGISTERED'}, extensionOrigin);
        const observation = input.observation || {};
        if (!/^[A-Za-z0-9_.:-]{6,180}$/.test(String(observation.documentId || ''))) return send(res, 400, {ok: false, error: 'DOCUMENT_ID_REQUIRED'}, extensionOrigin);
        retireExpired(Date.now());
        const tabKey = `${extensionOrigin}:${observation.windowId}:${observation.tabId}`;
        if (activeTabs.has(tabKey)) return send(res, 409, {ok: false, error: 'TAB_LEASE_BUSY'}, extensionOrigin);
        const receipt = createPairReceipt(row.intent, {...observation, tabSessionId: observation.documentId, leaseId: `lease-${randomUUID()}`}, state);
        intents.delete(input.pairingId);
        activeTabs.set(tabKey, receipt.pairingId);
        await eventSink({type: 'paired', receipt, intentHash: row.intentHash});
        return send(res, 201, {ok: true, receipt}, extensionOrigin);
      }
      if (req.method === 'GET' && url.pathname === '/v1/pairing') {
        requireNerve(req, nerveCapability);
        const receipt = state.receipts.get(url.searchParams.get('pairingId'));
        if (!receipt) return send(res, 404, {ok: false, error: 'PAIRING_UNKNOWN'});
        return send(res, 200, {receipt});
      }
      if (req.method === 'POST' && url.pathname === '/v1/command') {
        requireNerve(req, nerveCapability);
        const command = await body(req);
        retireExpired(Date.now());
        const receipt = state.receipts.get(command.pairingId);
        if (!receipt) return send(res, 404, {ok: false, error: 'PAIRING_UNKNOWN'});
        if (state.revoked.has(command.pairingId) || receipt.expiresAtMs <= Date.now()) return send(res, 410, {ok: false, error: 'PAIRING_INACTIVE'});
        if (pending.has(command.pairingId)) return send(res, 409, {ok: false, error: 'PAIRING_LEASE_BUSY'});
        pending.set(command.pairingId, command);
        return send(res, 202, {ok: true, commandId: command.commandId});
      }
      if (req.method === 'GET' && url.pathname === '/v1/command') {
        requireExtension(req, extensionOrigin);
        retireExpired(Date.now());
        const command = pending.get(url.searchParams.get('pairingId'));
        return command ? send(res, 200, {command}, extensionOrigin) : send(res, 204, undefined, extensionOrigin);
      }
      if (req.method === 'POST' && url.pathname === '/v1/authorize') {
        requireExtension(req, extensionOrigin);
        const input = await body(req);
        return send(res, 200, authorizeCommand(input.pairing, input.command, state), extensionOrigin);
      }
      if (req.method === 'POST' && url.pathname === '/v1/complete') {
        requireExtension(req, extensionOrigin);
        const input = await body(req);
        const expected = pending.get(input.pairingId);
        if (!expected || expected.commandId !== input.commandId) return send(res, 409, {ok: false, error: 'PENDING_COMMAND_MISMATCH'}, extensionOrigin);
        pending.delete(input.pairingId);
        completions.set(input.commandId, input.result);
        return send(res, 200, {ok: true}, extensionOrigin);
      }
      if (req.method === 'GET' && url.pathname === '/v1/complete') {
        requireNerve(req, nerveCapability);
        const result = completions.get(url.searchParams.get('commandId'));
        return result ? send(res, 200, {result}) : send(res, 404, {ok: false, error: 'RESULT_UNKNOWN'});
      }
      if (req.method === 'POST' && url.pathname === '/v1/revoke') {
        const extension = req.headers.origin === extensionOrigin;
        if (extension) requireExtension(req, extensionOrigin); else requireNerve(req, nerveCapability);
        const input = await body(req);
        const receipt = state.receipts.get(input.pairingId);
        const result = revokePairing(input.pairingId, state);
        pending.delete(input.pairingId);
        if (receipt) for (const [key, value] of activeTabs) if (value === receipt.pairingId) activeTabs.delete(key);
        await eventSink({type: 'revoked', receiptHash: receipt?.receiptHash, pairingId: input.pairingId, atMs: result.atMs});
        return send(res, 200, result, extension ? extensionOrigin : undefined);
      }
      if (req.method === 'GET' && url.pathname === '/v1/events') { requireNerve(req, nerveCapability); return send(res, 200, {events: state.events}); }
      return send(res, 404, {ok: false, error: 'ROUTE_NOT_FOUND'});
    } catch (error) {
      return send(res, Number(error.status) || 400, {ok: false, error: error.code || 'BROWSER_PORCH_FAILED', detail: error.message}, req.headers.origin === extensionOrigin ? extensionOrigin : undefined);
    }
  }).listen(port, host);

  function retireExpired(nowMs) {
    for (const [pairingId, receipt] of state.receipts) {
      if (receipt.expiresAtMs > nowMs || state.revoked.has(pairingId)) continue;
      state.revoked.add(pairingId);
      pending.delete(pairingId);
      for (const [key, value] of activeTabs) if (value === pairingId) activeTabs.delete(key);
    }
  }
}

function requireExtension(req, extensionOrigin) {
  if (req.headers.origin !== extensionOrigin) throw Object.assign(new Error('exact extension origin required'), {code: 'EXTENSION_ORIGIN_MISMATCH', status: 403});
}

function requireNerve(req, nerveCapability) {
  if (req.headers.authorization !== `Bearer ${nerveCapability}`) throw Object.assign(new Error('Browser Nerve capability required'), {code: 'NERVE_CAPABILITY_MISMATCH', status: 403});
}

async function body(req) {
  const chunks = [];
  let bytes = 0;
  for await (const chunk of req) {
    bytes += chunk.length;
    if (bytes > 64 * 1024) throw Object.assign(new Error('request too large'), {code: 'REQUEST_TOO_LARGE'});
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
}

function cors(res, origin) {
  res.setHeader('access-control-allow-origin', origin);
  res.setHeader('access-control-allow-methods', 'GET, POST, OPTIONS');
  res.setHeader('access-control-allow-headers', 'content-type');
  res.setHeader('vary', 'Origin');
}

function send(res, status, value, origin) {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json');
  res.setHeader('cache-control', 'no-store');
  if (origin) cors(res, origin);
  res.end(status === 204 ? '' : JSON.stringify(value));
}
