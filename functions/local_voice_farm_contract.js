'use strict';

const {createHash} = require('node:crypto');

const CONTRACT_VERSION = 'home-center.local-voice-farm.v1';
const PROVIDER_ID = 'local_cauldron';
const ENGINE_ID = 'kokoro-onnx';
const DEFAULT_VOICE_PROFILE = 'fixed:kokoro:af_heart';
const MAX_TEXT_CHARS = 32000;
const DEFAULT_SEGMENT_CHARS = 420;

class LocalVoiceFarmError extends Error {
  constructor(code, message, status = 400, details = {}) {
    super(message);
    this.name = 'LocalVoiceFarmError';
    this.code = code;
    this.status = status;
    Object.assign(this, details);
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
  return createHash('sha256').update(value).digest('hex');
}

function assertId(value, label = 'id') {
  const text = String(value || '');
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(text)) {
    throw new LocalVoiceFarmError('local_voice_invalid_id', `${label} must be 6-160 safe identifier characters.`);
  }
  return text;
}

function splitTextLossless(text, maxChars = DEFAULT_SEGMENT_CHARS) {
  if (typeof text !== 'string' || !text.length) {
    throw new LocalVoiceFarmError('local_voice_text_required', 'text is required.');
  }
  if (text.length > MAX_TEXT_CHARS) {
    throw new LocalVoiceFarmError('local_voice_text_too_long', `text exceeds ${MAX_TEXT_CHARS} characters.`, 413);
  }
  const limit = Math.max(120, Math.min(1200, Number(maxChars) || DEFAULT_SEGMENT_CHARS));
  const segments = [];
  let offset = 0;
  while (offset < text.length) {
    let end = Math.min(text.length, offset + limit);
    if (end < text.length) {
      const window = text.slice(offset, end);
      const matches = [...window.matchAll(/[.!?;:,]\s+|\s+/g)];
      const last = matches.length ? matches[matches.length - 1] : null;
      if (last && last.index >= Math.floor(limit * 0.55)) end = offset + last.index + last[0].length;
    }
    const value = text.slice(offset, end);
    segments.push({index: segments.length, text: value, textSha256: sha256(value)});
    offset = end;
  }
  if (segments.map((segment) => segment.text).join('') !== text) {
    throw new LocalVoiceFarmError('local_voice_split_integrity_failed', 'The automatic split plan changed the transcript.', 500);
  }
  return segments;
}

function validateVoiceProfile(profileId, profile = null) {
  const id = String(profileId || DEFAULT_VOICE_PROFILE);
  if (id.startsWith('fixed:kokoro:')) {
    return {profileId: id, kind: 'fixed', consentRequired: false, acceptedIdentityClaim: false};
  }
  if (!profile || profile.profileId !== id) {
    throw new LocalVoiceFarmError('local_voice_profile_unknown', 'The requested voice profile is not allowlisted.', 403);
  }
  if (profile.kind !== 'clone' || profile.consent !== true || !profile.owner || !/^[a-f0-9]{64}$/.test(String(profile.referenceSha256 || ''))) {
    throw new LocalVoiceFarmError('local_voice_profile_unconsented', 'Clone profiles require consent, provenance owner, and an immutable reference hash.', 403);
  }
  if (!Array.isArray(profile.permittedUses) || !profile.permittedUses.includes('tts')) {
    throw new LocalVoiceFarmError('local_voice_profile_use_forbidden', 'The voice profile does not permit TTS rendering.', 403);
  }
  return {
    profileId: id,
    kind: 'clone',
    owner: profile.owner,
    referenceSha256: profile.referenceSha256,
    permittedUses: [...profile.permittedUses],
    consentRequired: true,
    acceptedIdentityClaim: false,
  };
}

function canonicalRequest(input = {}, profile = null) {
  const requestId = assertId(input.requestId, 'requestId');
  const provider = String(input.provider || PROVIDER_ID);
  if (provider !== PROVIDER_ID) throw new LocalVoiceFarmError('local_voice_provider_required', `provider must be ${PROVIDER_ID}.`);
  const engine = String(input.engine || ENGINE_ID);
  if (engine !== ENGINE_ID) throw new LocalVoiceFarmError('local_voice_engine_unsupported', `engine must be ${ENGINE_ID}.`);
  const text = String(input.text || '');
  const voice = validateVoiceProfile(input.voiceProfileId || DEFAULT_VOICE_PROFILE, profile);
  const splitPlan = splitTextLossless(text, input.segmentChars);
  const request = {
    contractVersion: CONTRACT_VERSION,
    requestId,
    provider,
    engine,
    modelRevision: String(input.modelRevision || 'kokoro-v1.0'),
    voice,
    speed: Math.max(0.5, Math.min(2, Number(input.speed) || 1)),
    format: 'wav',
    sampleRate: 24000,
    text,
    textSha256: sha256(text),
    splitPlan,
  };
  return {...request, inputSha256: sha256(stableJson(request))};
}

function createTicket(input, profile = null, nowMs = Date.now()) {
  const request = canonicalRequest(input, profile);
  return {
    ticketId: `lvr-${request.requestId}`,
    owner: String(input.owner || ''),
    status: 'queued',
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
    lease: null,
    completedSegmentIndexes: [],
    request,
    receipt: {
      contractVersion: CONTRACT_VERSION,
      inputSha256: request.inputSha256,
      exactTranscript: true,
      splitPlanRequired: true,
      providerFallbackAllowed: false,
      cloudSpeechSynthesisAllowed: false,
      humanAcceptance: 'unreviewed',
    },
  };
}

function reconcileTicket(existing, proposed) {
  if (!existing) return proposed;
  if (existing.request.inputSha256 !== proposed.request.inputSha256) {
    throw new LocalVoiceFarmError('local_voice_idempotency_conflict', 'requestId already exists with different immutable input.', 409);
  }
  return existing;
}

function leaseTicket(ticket, worker, nowMs = Date.now(), leaseMs = 90000) {
  assertId(worker.workerId, 'workerId');
  if (!worker.capabilities || !worker.capabilities.includes(ticket.request.engine)) {
    throw new LocalVoiceFarmError('local_voice_worker_capability_mismatch', 'Worker does not advertise the requested engine.', 409);
  }
  if (!['queued', 'leased', 'running'].includes(ticket.status)) {
    throw new LocalVoiceFarmError('local_voice_ticket_not_leasable', `Ticket status ${ticket.status} is not leasable.`, 409);
  }
  if (ticket.lease && ticket.lease.expiresAtMs > nowMs && ticket.lease.workerId !== worker.workerId) {
    throw new LocalVoiceFarmError('local_voice_ticket_already_leased', 'Ticket has a current lease.', 409);
  }
  return {...ticket, status: 'leased', updatedAtMs: nowMs, lease: {workerId: worker.workerId, leasedAtMs: nowMs, heartbeatAtMs: nowMs, expiresAtMs: nowMs + leaseMs}};
}

function heartbeatTicket(ticket, workerId, nowMs = Date.now(), leaseMs = 90000) {
  if (!ticket.lease || ticket.lease.workerId !== workerId) throw new LocalVoiceFarmError('local_voice_lease_owner_mismatch', 'Worker does not own this lease.', 409);
  if (ticket.lease.expiresAtMs < nowMs) throw new LocalVoiceFarmError('local_voice_lease_expired', 'Worker lease expired.', 409);
  return {...ticket, status: 'running', updatedAtMs: nowMs, lease: {...ticket.lease, heartbeatAtMs: nowMs, expiresAtMs: nowMs + leaseMs}};
}

function validateArtifactReceipt(ticket, artifact = {}) {
  if (!/^[a-f0-9]{64}$/.test(String(artifact.sha256 || '')) || Number(artifact.byteCount || 0) < 44) {
    throw new LocalVoiceFarmError('local_voice_artifact_invalid', 'Artifact receipt requires WAV bytes and SHA-256.', 400);
  }
  if (artifact.provider !== PROVIDER_ID || artifact.engine !== ticket.request.engine || artifact.cloudSpeechSynthesisUsed === true) {
    throw new LocalVoiceFarmError('local_voice_artifact_identity_mismatch', 'Artifact provider or engine identity does not match the ticket.', 409);
  }
  if (artifact.inputSha256 !== ticket.request.inputSha256) {
    throw new LocalVoiceFarmError('local_voice_artifact_input_mismatch', 'Artifact input hash does not match the ticket.', 409);
  }
  return {
    ...artifact,
    verified: artifact.readbackSha256 === artifact.sha256 && Number(artifact.readbackByteCount) === Number(artifact.byteCount),
    humanAcceptance: 'unreviewed',
    acceptedIdentityClaim: false,
  };
}

module.exports = {
  CONTRACT_VERSION,
  PROVIDER_ID,
  ENGINE_ID,
  DEFAULT_VOICE_PROFILE,
  LocalVoiceFarmError,
  stableJson,
  sha256,
  splitTextLossless,
  validateVoiceProfile,
  canonicalRequest,
  createTicket,
  reconcileTicket,
  leaseTicket,
  heartbeatTicket,
  validateArtifactReceipt,
};
