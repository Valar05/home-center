'use strict';

const {createHash} = require('node:crypto');

const CONTRACT_VERSION = 'home-center.venus-cauldron-relay.v1';
const PROVIDER_ID = 'local_cauldron';
const ENGINE_ID = 'ollama';
const MAX_MESSAGES = 32;
const MAX_INPUT_CHARS = 24000;
const MAX_OUTPUT_CHARS = 12000;
const LEASE_MS = 55000;

class VenusRelayError extends Error {
  constructor(code, message, status = 400) {
    super(message);
    this.name = 'VenusRelayError';
    this.code = code;
    this.status = status;
  }
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce((out, key) => {
      if (value[key] !== undefined) out[key] = stableValue(value[key]);
      return out;
    }, {});
  }
  return value;
}

function stableJson(value) {
  return JSON.stringify(stableValue(value));
}

function sha256(value) {
  return createHash('sha256').update(String(value)).digest('hex');
}

function safeId(value, label = 'id') {
  const text = String(value || '').trim();
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(text)) throw new VenusRelayError('venus_relay_invalid_id', `${label} must be 6-160 safe identifier characters.`);
  return text;
}

function allowedModel(value, allowlist) {
  const model = String(value || '').trim();
  if (!/^[A-Za-z0-9_.:-]{2,120}$/.test(model)) throw new VenusRelayError('venus_relay_model_invalid', 'model is invalid.');
  if (!Array.isArray(allowlist) || !allowlist.includes(model)) throw new VenusRelayError('venus_relay_model_forbidden', 'model is not enabled on THECAULDRON.', 403);
  return model;
}

function normalizeMessages(messages) {
  if (!Array.isArray(messages) || messages.length < 1 || messages.length > MAX_MESSAGES) {
    throw new VenusRelayError('venus_relay_messages_invalid', `messages must contain 1-${MAX_MESSAGES} items.`);
  }
  let chars = 0;
  const normalized = messages.map((message) => {
    if (!message || typeof message !== 'object' || !['system', 'user', 'assistant'].includes(message.role) || typeof message.content !== 'string') {
      throw new VenusRelayError('venus_relay_message_invalid', 'Only system, user, and assistant messages with string content are accepted.');
    }
    chars += message.content.length;
    return {role: message.role, content: message.content};
  });
  if (chars > MAX_INPUT_CHARS) throw new VenusRelayError('venus_relay_input_too_large', `message content exceeds ${MAX_INPUT_CHARS} characters.`, 413);
  return normalized;
}

function canonicalRequest(input, allowlist) {
  if (input.stream === true) throw new VenusRelayError('venus_relay_stream_unsupported', 'Streaming is not enabled for the outbound relay.');
  if (input.tools || input.functions || input.response_format) throw new VenusRelayError('venus_relay_capability_forbidden', 'Tools, functions, and custom response formats are not enabled.');
  const request = {
    contractVersion: CONTRACT_VERSION,
    provider: PROVIDER_ID,
    engine: ENGINE_ID,
    model: allowedModel(input.model, allowlist),
    messages: normalizeMessages(input.messages),
    temperature: Math.max(0, Math.min(2, Number.isFinite(Number(input.temperature)) ? Number(input.temperature) : 0.78)),
    max_tokens: Math.max(1, Math.min(1200, Number(input.max_tokens) || 900)),
  };
  return {...request, inputSha256: sha256(stableJson(request))};
}

function createTicket({requestId, input, allowlist, nowMs = Date.now()}) {
  const request = canonicalRequest(input || {}, allowlist);
  return {
    ticketId: `vcr-${safeId(requestId, 'requestId')}`,
    status: 'queued',
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
    expiresAtMs: nowMs + 70000,
    request,
    lease: null,
    completion: null,
    failure: null,
    receipt: {provider: PROVIDER_ID, engine: ENGINE_ID, networkPath: 'outbound_poll_only', ollamaExposure: 'loopback_only', humanAcceptance: 'unreviewed'},
  };
}

function reconcileTicket(existing, proposed) {
  if (!existing) return proposed;
  if (!existing.request || existing.request.inputSha256 !== proposed.request.inputSha256) throw new VenusRelayError('venus_relay_idempotency_conflict', 'requestId already exists with different input.', 409);
  return existing;
}

function leaseTicket(ticket, worker, nowMs = Date.now()) {
  safeId(worker.workerId, 'workerId');
  if (!Array.isArray(worker.models) || !worker.models.includes(ticket.request.model)) throw new VenusRelayError('venus_relay_worker_model_mismatch', 'Worker does not advertise the requested model.', 409);
  if (!['queued', 'leased', 'running'].includes(ticket.status)) throw new VenusRelayError('venus_relay_ticket_not_leasable', 'Ticket is not leasable.', 409);
  if (ticket.expiresAtMs <= nowMs) throw new VenusRelayError('venus_relay_ticket_expired', 'Ticket expired before lease.', 410);
  if (ticket.lease && ticket.lease.expiresAtMs > nowMs && ticket.lease.workerId !== worker.workerId) throw new VenusRelayError('venus_relay_ticket_already_leased', 'Ticket has a current lease.', 409);
  return {...ticket, status: 'leased', updatedAtMs: nowMs, lease: {workerId: worker.workerId, leasedAtMs: nowMs, expiresAtMs: nowMs + LEASE_MS}};
}

function completeTicket(ticket, workerId, result, nowMs = Date.now()) {
  if (!ticket.lease || ticket.lease.workerId !== workerId || ticket.lease.expiresAtMs <= nowMs) throw new VenusRelayError('venus_relay_lease_owner_mismatch', 'Worker does not own a current lease.', 409);
  if (!result || result.model !== ticket.request.model || typeof result.content !== 'string') throw new VenusRelayError('venus_relay_completion_invalid', 'Completion model or content is invalid.', 400);
  if (result.content.length > MAX_OUTPUT_CHARS) throw new VenusRelayError('venus_relay_output_too_large', `Completion exceeds ${MAX_OUTPUT_CHARS} characters.`, 413);
  const completion = {
    id: `chatcmpl-${ticket.ticketId}`,
    object: 'chat.completion',
    created: Math.floor(nowMs / 1000),
    model: result.model,
    system_fingerprint: 'local_cauldron:ollama',
    provider: PROVIDER_ID,
    choices: [{index: 0, message: {role: 'assistant', content: result.content}, finish_reason: result.finishReason || 'stop'}],
    usage: result.usage && typeof result.usage === 'object' ? result.usage : {prompt_tokens: 0, completion_tokens: 0, total_tokens: 0},
  };
  return {...ticket, status: 'completed', updatedAtMs: nowMs, lease: null, completion, receipt: {...ticket.receipt, workerId, completedAtMs: nowMs, outputSha256: sha256(result.content)}};
}

module.exports = {CONTRACT_VERSION, PROVIDER_ID, ENGINE_ID, MAX_INPUT_CHARS, MAX_OUTPUT_CHARS, VenusRelayError, stableJson, sha256, safeId, canonicalRequest, createTicket, reconcileTicket, leaseTicket, completeTicket};

