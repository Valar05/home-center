import http from 'node:http';
import {randomUUID} from 'node:crypto';
import {createEphemeralState, createPairReceipt, authorizeCommand, revokePairing, sha256, validatePairIntent} from './contract.mjs';
import {validateRitsuTurn} from './ritsu-turn-protocol.mjs';

const THRONE_MAX_COMMANDS = 64;
const THRONE_LEASE_MS = 90 * 1000;
const THRONE_MAX_JOBS = 12;

export function createRelay({
  host = '127.0.0.1',
  port = 9234,
  extensionOrigin = process.env.HOME_CENTER_BROWSER_PORCH_EXTENSION_ORIGIN,
  nerveCapability = process.env.HOME_CENTER_BROWSER_PORCH_NERVE_CAPABILITY,
  throneCapability = process.env.HOME_CENTER_CHROMIUM_THRONE_CAPABILITY,
  eventSink,
} = {}) {
  if (!/^chrome-extension:\/\/[a-p]{32}$/.test(String(extensionOrigin || ''))) throw new Error('exact Browser Porch extension origin is required');
  if (nerveCapability && String(nerveCapability).length < 32) throw new Error('ephemeral Browser Nerve capability must be at least 32 characters');
  if (throneCapability && String(throneCapability).length < 32) throw new Error('Chromium Throne capability must be at least 32 characters');
  if (!nerveCapability && !throneCapability) throw new Error('at least one local relay capability is required');
  if (typeof eventSink !== 'function') throw new Error('durable Home Center event sink integration is required');

  const state = createEphemeralState();
  const intents = new Map();
  const pending = new Map();
  const completions = new Map();
  const activeTabs = new Map();
  const throneCommands = new Map();
  let throneSnapshot = {atMs: 0, workers: [], queue: [], stopped: false};

  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://${host}:${port}`);
      if (req.method === 'OPTIONS') {
        requireExtension(req, extensionOrigin);
        res.statusCode = 204;
        cors(res, extensionOrigin);
        return res.end();
      }

      // Chromium Throne's long-lived command seam. It is deliberately separate
      // from Browser Porch's short-lived per-tab pairing contract below.
      if (req.method === 'POST' && url.pathname === '/v1/throne/command') {
        requireThrone(req, throneCapability);
        retireThrone(Date.now());
        const command = validateThroneCommand(await body(req));
        if (throneCommands.has(command.commandId)) {
          const existing = throneCommands.get(command.commandId);
          if ((command.action === 'chat.turn' || existing.action === 'chat.turn') &&
              (existing.action !== command.action ||
              sha256(JSON.stringify(existing.turn)) !== sha256(JSON.stringify(command.turn))))
            return send(res, 409, {ok: false, error: 'RITSU_TURN_ID_COLLISION'});
          return send(res, 200, {ok: true, commandId: command.commandId, state: existing.state, duplicate: true});
        }
        if ([...throneCommands.values()].filter((row) => !['completed', 'failed', 'cancelled', 'uncertain'].includes(row.state)).length >= THRONE_MAX_COMMANDS) {
          return send(res, 429, {ok: false, error: 'THRONE_QUEUE_FULL'});
        }
        const row = {...command, state: 'queued', createdAtMs: Date.now(), lease: null, result: null};
        throneCommands.set(command.commandId, row);
        await eventSink({type: 'throne.command.queued', command: publicThroneCommand(row)});
        return send(res, 202, {ok: true, commandId: command.commandId, state: row.state});
      }
      if (req.method === 'GET' && url.pathname === '/v1/throne/command') {
        requireExtensionAndThrone(req, extensionOrigin, throneCapability);
        const nowMs = Date.now();
        retireThrone(nowMs);
        const row = [...throneCommands.values()]
          .filter((item) => item.state === 'queued' || (item.state === 'leased' && Number(item.lease?.expiresAtMs || 0) <= nowMs))
          .sort((a, b) => a.createdAtMs - b.createdAtMs)[0];
        if (!row) return send(res, 204, undefined, extensionOrigin);
        row.state = 'leased';
        // The browser-side single-turn watcher has a 120s reply deadline.
        // The relay lease must exceed it or a valid reply becomes unknowable.
        const leaseMs = row.action === 'chat.turn' ? 180_000 : THRONE_LEASE_MS;
        row.lease = {leasedAtMs: nowMs, expiresAtMs: nowMs + leaseMs};
        await eventSink({type: 'throne.command.leased', command: publicThroneCommand(row)});
        return send(res, 200, {command: leasedThroneCommand(row)}, extensionOrigin);
      }
      if (req.method === 'POST' && url.pathname === '/v1/throne/complete') {
        requireExtensionAndThrone(req, extensionOrigin, throneCapability);
        const input = await body(req);
        const commandId = safeCommandId(input.commandId);
        const row = throneCommands.get(commandId);
        if (!row) return send(res, 404, {ok: false, error: 'THRONE_COMMAND_UNKNOWN'}, extensionOrigin);
        if (row.state !== 'leased') return send(res, 409, {ok: false, error: 'THRONE_COMMAND_NOT_LEASED'}, extensionOrigin);
        row.state = input.ok === false ? 'failed' : 'completed';
        row.result = sanitizeThroneResult(input.result);
        row.completedAtMs = Date.now();
        row.lease = null;
        await eventSink({type: 'throne.command.completed', command: publicThroneCommand(row), result: row.result});
        return send(res, 200, {ok: true, commandId, state: row.state}, extensionOrigin);
      }
      if (req.method === 'POST' && url.pathname === '/v1/throne/snapshot') {
        requireExtensionAndThrone(req, extensionOrigin, throneCapability);
        const input = await body(req);
        throneSnapshot = sanitizeThroneSnapshot(input);
        return send(res, 200, {ok: true, atMs: throneSnapshot.atMs}, extensionOrigin);
      }
      if (req.method === 'GET' && url.pathname === '/v1/throne/result') {
        requireThrone(req, throneCapability);
        retireThrone(Date.now());
        const commandId = safeCommandId(url.searchParams.get('commandId'));
        const row = throneCommands.get(commandId);
        if (!row) return send(res, 404, {ok: false, error: 'THRONE_COMMAND_UNKNOWN'});
        // Results never flow through public/status snapshots; only through bearer-bound readback.
        return send(res, 200, {
          ok: true, commandId, state: row.state,
          result: ['completed', 'failed', 'uncertain'].includes(row.state) ? row.result : null,
          completedAtMs: Number(row.completedAtMs || 0)
        });
      }
      if (req.method === 'GET' && url.pathname === '/v1/throne/status') {
        requireThrone(req, throneCapability);
        retireThrone(Date.now());
        const commands = [...throneCommands.values()].sort((a, b) => b.createdAtMs - a.createdAtMs).slice(0, 50).map(publicThroneCommand);
        return send(res, 200, {ok: true, commands, snapshot: throneSnapshot});
      }
      if (req.method === 'POST' && url.pathname === '/v1/throne/cancel') {
        requireThrone(req, throneCapability);
        const input = await body(req);
        const commandId = safeCommandId(input.commandId);
        const row = throneCommands.get(commandId);
        if (!row) return send(res, 404, {ok: false, error: 'THRONE_COMMAND_UNKNOWN'});
        if (['completed', 'failed'].includes(row.state)) return send(res, 409, {ok: false, error: 'THRONE_COMMAND_TERMINAL'});
        row.state = 'cancelled'; row.lease = null; row.cancelledAtMs = Date.now();
        await eventSink({type: 'throne.command.cancelled', command: publicThroneCommand(row)});
        return send(res, 200, {ok: true, commandId, state: row.state});
      }

      // Existing Browser Porch pairing protocol.
      if (req.method === 'POST' && url.pathname === '/v1/intent') {
        requireNerve(req, nerveCapability);
        const intent = validatePairIntent(await body(req));
        if (intents.has(intent.pairingId)) return send(res, 409, {ok: false, error: 'INTENT_EXISTS'});
        intents.set(intent.pairingId, {intent, intentHash: sha256(JSON.stringify(intent))});
        return send(res, 201, {ok: true, pairingId: intent.pairingId, intentHash: intents.get(intent.pairingId).intentHash});
      }
      if (req.method === 'GET' && url.pathname === '/v1/intent') {
        requireExtension(req, extensionOrigin);
        retireExpired(Date.now());
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
        activeTabs.set(tabKey, receipt.pairingId);
        try {
          await eventSink({type: 'paired', receipt, intentHash: row.intentHash});
        } catch (error) {
          activeTabs.delete(tabKey);
          state.receipts.delete(receipt.pairingId);
          state.usedNonces.delete(row.intent.nonce);
          if (state.events.at(-1)?.type === 'paired' && state.events.at(-1)?.pairingId === receipt.pairingId) state.events.pop();
          throw Object.assign(new Error(`durable pairing receipt failed: ${error.message}`), {code: 'DURABLE_SINK_FAILED', status: 503});
        }
        intents.delete(input.pairingId);
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
    for (const [pairingId, row] of intents) if (row.intent.expiresAtMs <= nowMs) intents.delete(pairingId);
    for (const [pairingId, receipt] of state.receipts) {
      if (receipt.expiresAtMs > nowMs || state.revoked.has(pairingId)) continue;
      state.revoked.add(pairingId);
      pending.delete(pairingId);
      for (const [key, value] of activeTabs) if (value === pairingId) activeTabs.delete(key);
    }
  }

  function retireThrone(nowMs) {
    for (const row of throneCommands.values()) {
      if (row.state === 'leased' && Number(row.lease?.expiresAtMs || 0) <= nowMs) {
        if (row.action === 'chat.turn') {
          // A browser may already have submitted this text. Never resend after
          // expiry without independent readback; mark unknown instead.
          row.state = 'uncertain';
          row.result = {ok: false, error: 'THRONE_COMPLETION_UNKNOWN'};
          row.completedAtMs = nowMs;
          row.lease = null;
        } else {
          row.state = 'queued'; row.lease = null;
        }
      }
    }
    const terminal = [...throneCommands.values()].filter((row) => ['completed', 'failed', 'cancelled', 'uncertain'].includes(row.state)).sort((a, b) => Number(b.completedAtMs || b.cancelledAtMs || b.createdAtMs) - Number(a.completedAtMs || a.cancelledAtMs || a.createdAtMs));
    for (const row of terminal.slice(THRONE_MAX_COMMANDS)) throneCommands.delete(row.commandId);
  }
}

function safeCommandId(value) {
  const text = String(value || '').trim();
  if (!/^[A-Za-z0-9_.:-]{6,180}$/.test(text)) throw Object.assign(new Error('valid commandId required'), {code: 'THRONE_COMMAND_ID_INVALID', status: 400});
  return text;
}

function validateThroneCommand(input = {}) {
  const commandId = safeCommandId(input.commandId);
  const action = String(input.action || '').trim();
  if (action === 'chat.turn') {
    const turn = validateRitsuTurn(input.turn);
    if (commandId !== `ritsu.${turn.turnId}`)
      throw Object.assign(new Error('commandId must match turnId'), {code: 'RITSU_COMMAND_ID_MISMATCH', status: 400});
    return {commandId, action, turn, jobs: [], source: 'ritsu-cockpit',
      createdAt: String(input.createdAt || '')};
  }
  if (!['swarm.enqueue', 'swarm.stop', 'swarm.resume', 'swarm.status'].includes(action)) throw Object.assign(new Error('unsupported throne action'), {code: 'THRONE_ACTION_UNSUPPORTED', status: 400});
  const jobs = Array.isArray(input.jobs) ? input.jobs.slice(0, THRONE_MAX_JOBS).map((job, index) => {
    const commission = String(job?.commission || '').trim();
    if (!commission || commission.length > 32000) throw Object.assign(new Error(`job ${index + 1} commission invalid`), {code: 'THRONE_JOB_INVALID', status: 400});
    return {jobId: safeCommandId(job.jobId || `${commandId}-job-${index + 1}`), commission, context: String(job.context || '').trim().slice(0, 24000)};
  }) : [];
  if (action === 'swarm.enqueue' && !jobs.length) throw Object.assign(new Error('swarm.enqueue requires at least one bounded job'), {code: 'THRONE_JOBS_REQUIRED', status: 400});
  return {commandId, action, jobs, source: String(input.source || 'atom-vlad').slice(0, 120), createdAt: String(input.createdAt || '')};
}

function publicThroneCommand(row = {}) {
  return {commandId: row.commandId, action: row.action, jobs: row.jobs || [],
    turn: row.turn ? {sessionId: row.turn.sessionId, turnId: row.turn.turnId,
      channel: row.turn.channel} : undefined,
    source: row.source || '', state: row.state || 'unknown',
    createdAtMs: Number(row.createdAtMs || 0), lease: row.lease || null,
    completedAtMs: Number(row.completedAtMs || 0), cancelledAtMs: Number(row.cancelledAtMs || 0)};
}
function leasedThroneCommand(row = {}) {
  return {...publicThroneCommand(row), turn: row.turn || undefined};
}

function sanitizeThroneResult(value) {
  const text = JSON.stringify(value && typeof value === 'object' ? value : {value});
  if (Buffer.byteLength(text, 'utf8') > 256 * 1024) throw Object.assign(new Error('throne result too large'), {code: 'THRONE_RESULT_TOO_LARGE', status: 413});
  return JSON.parse(text);
}

function sanitizeThroneSnapshot(input = {}) {
  const workers = Array.isArray(input.workers) ? input.workers.slice(0, 16).map((worker) => ({tabId: Number(worker?.tabId || 0), jobId: String(worker?.jobId || '').slice(0, 180), state: String(worker?.state || 'unknown').slice(0, 80), title: String(worker?.title || '').slice(0, 240), updatedAt: String(worker?.updatedAt || '')})) : [];
  const queue = Array.isArray(input.queue) ? input.queue.slice(0, 64).map((job) => ({id: String(job?.id || '').slice(0, 180), state: String(job?.state || 'unknown').slice(0, 80), workerTabId: Number(job?.workerTabId || 0), source: String(job?.source || '').slice(0, 80)})) : [];
  return {atMs: Date.now(), workers, queue, stopped: input.stopped === true};
}

function requireExtension(req, extensionOrigin) {
  if (req.headers.origin !== extensionOrigin) throw Object.assign(new Error('exact extension origin required'), {code: 'EXTENSION_ORIGIN_MISMATCH', status: 403});
}
function requireNerve(req, nerveCapability) {
  if (!nerveCapability || req.headers.authorization !== `Bearer ${nerveCapability}`) throw Object.assign(new Error('Browser Nerve capability required'), {code: 'NERVE_CAPABILITY_MISMATCH', status: 403});
}
function requireThrone(req, throneCapability) {
  if (!throneCapability || req.headers.authorization !== `Bearer ${throneCapability}`) throw Object.assign(new Error('Chromium Throne capability required'), {code: 'THRONE_CAPABILITY_MISMATCH', status: 403});
}
function requireExtensionAndThrone(req, extensionOrigin, throneCapability) {
  // Chromium MV3 extension requests with host_permissions sometimes omit the
  // Origin header, even though their script runs under chrome-extension://.
  // A missing Origin is NOT a mismatched Origin: the high-entropy capability
  // remains mandatory, the HTTP listener remains 127.0.0.1-only, and an
  // explicit hostile or opaque Origin is always rejected.
  requireThrone(req, throneCapability);
  if (req.headers.origin != null) requireExtension(req, extensionOrigin);
}

async function body(req) {
  const chunks = [];
  let bytes = 0;
  for await (const chunk of req) {
    bytes += chunk.length;
    if (bytes > 256 * 1024) throw Object.assign(new Error('request too large'), {code: 'REQUEST_TOO_LARGE'});
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
}
function cors(res, origin) {
  res.setHeader('access-control-allow-origin', origin);
  res.setHeader('access-control-allow-methods', 'GET, POST, OPTIONS');
  res.setHeader('access-control-allow-headers', 'content-type, authorization');
  res.setHeader('vary', 'Origin');
}
function send(res, status, value, origin) {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json');
  res.setHeader('cache-control', 'no-store');
  if (origin) cors(res, origin);
  res.end(status === 204 ? '' : JSON.stringify(value));
}
