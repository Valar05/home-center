import http from 'node:http';
import {createEphemeralState, createPairReceipt, authorizeCommand, revokePairing, sha256, validatePairIntent} from './contract.mjs';

const state = createEphemeralState();
let intent = null;
const pending = new Map();
const completions = new Map();

export function createRelay({host = '127.0.0.1', port = 9234} = {}) {
  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://${host}:${port}`);
      if (req.method === 'POST' && url.pathname === '/v1/intent') {
        intent = validatePairIntent(await body(req));
        return send(res, 201, {ok: true, pairingId: intent.pairingId});
      }
      if (req.method === 'GET' && url.pathname === '/v1/intent') {
        if (!intent) return send(res, 404, {ok: false, error: 'NO_INTENT'});
        return send(res, 200, intent);
      }
      if (req.method === 'POST' && url.pathname === '/v1/pair') {
        const input = await body(req);
        const receipt = createPairReceipt(input.intent, input.observation, state);
        intent = null;
        return send(res, 201, {ok: true, receipt});
      }
      if (req.method === 'GET' && url.pathname === '/v1/pairing') {
        const receipt = state.receipts.get(url.searchParams.get('pairingId'));
        if (!receipt) return send(res, 404, {ok: false, error: 'PAIRING_UNKNOWN'});
        requireLeaseProof(req, receipt);
        return send(res, 200, {receipt});
      }
      if (req.method === 'POST' && url.pathname === '/v1/command') {
        const command = await body(req);
        const receipt = state.receipts.get(command.pairingId);
        if (!receipt) return send(res, 404, {ok: false, error: 'PAIRING_UNKNOWN'});
        requireLeaseProof(req, receipt);
        if (pending.has(command.pairingId)) return send(res, 409, {ok: false, error: 'PAIRING_LEASE_BUSY'});
        pending.set(command.pairingId, command);
        return send(res, 202, {ok: true, commandId: command.commandId});
      }
      if (req.method === 'GET' && url.pathname === '/v1/command') {
        const command = pending.get(url.searchParams.get('pairingId'));
        return command ? send(res, 200, {command}) : send(res, 204);
      }
      if (req.method === 'POST' && url.pathname === '/v1/authorize') {
        const input = await body(req);
        return send(res, 200, authorizeCommand(input.pairing, input.command, state));
      }
      if (req.method === 'POST' && url.pathname === '/v1/complete') {
        const input = await body(req);
        pending.delete(input.pairingId);
        completions.set(input.commandId, input.result);
        return send(res, 200, {ok: true});
      }
      if (req.method === 'GET' && url.pathname === '/v1/complete') {
        const result = completions.get(url.searchParams.get('commandId'));
        return result ? send(res, 200, {result}) : send(res, 404, {ok: false, error: 'RESULT_UNKNOWN'});
      }
      if (req.method === 'POST' && url.pathname === '/v1/revoke') {
        const input = await body(req);
        return send(res, 200, revokePairing(input.pairingId, state));
      }
      if (req.method === 'GET' && url.pathname === '/v1/events') return send(res, 200, {events: state.events});
      return send(res, 404, {ok: false, error: 'ROUTE_NOT_FOUND'});
    } catch (error) {
      return send(res, 400, {ok: false, error: error.code || 'BROWSER_PORCH_FAILED', detail: error.message});
    }
  }).listen(port, host);
}

function requireLeaseProof(req, receipt) {
  const proof = String(req.headers['x-browser-porch-lease'] || '');
  if (!proof || sha256(proof) !== receipt.nonceHash) throw Object.assign(new Error('ephemeral lease proof mismatch'), {code: 'LEASE_PROOF_MISMATCH'});
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

function send(res, status, value) {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json');
  res.setHeader('cache-control', 'no-store');
  res.setHeader('access-control-allow-origin', 'chrome-extension://*');
  res.end(status === 204 ? '' : JSON.stringify(value));
}

if (process.argv[1] === new URL(import.meta.url).pathname) createRelay();
