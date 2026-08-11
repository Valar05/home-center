'use strict';

const { isRecord, requireText, requireSha, requireRfc3339, requireStringArray, sha256 } = require('./contracts');

const CONTROL_PHASES = Object.freeze(['YIELD_LOCAL', 'LOCAL_OWNS_ACTUATOR', 'RETURN_TO_VOICE']);
const ASSEMBLY_KINDS = Object.freeze(['AUDIO_TIMELINE', 'NARRATION_AND_ASMR', 'POLISHED_ARTIFACT']);
const FAILURE_DEGRADATION = Object.freeze({
  PIPER_FAILURE: Object.freeze({ parkedComponent: 'piper', continuation: 'TEXT_FALLBACK', preserve: Object.freeze(['commissioned_local_lanes']) }),
  ASMR_FAILURE: Object.freeze({ parkedComponent: 'asmr_projection', continuation: 'SILENT_WITH_TEXT_MIRROR', preserve: Object.freeze(['narration', 'commissioned_local_lanes']) }),
  PLAYBACK_FAILURE: Object.freeze({ parkedComponent: 'local_playback', continuation: 'ASSEMBLY_REMAINS_INTACT', preserve: Object.freeze(['assembly_artifact', 'commissioned_local_lanes']) }),
  VOICE_FAILURE: Object.freeze({ parkedComponent: 'voice_aperture', continuation: 'HOME_CENTER_AND_LOCAL_CONTINUE', preserve: Object.freeze(['durable_queue', 'commissioned_local_lanes']) }),
  TRANSPORT_TIMEOUT: Object.freeze({ parkedComponent: 'transport', continuation: 'PRESERVE_EXACT_SESSION_FOR_RESUME', preserve: Object.freeze(['session_id', 'resume_command', 'rollout', 'worktree']) }),
  QUOTA_EXHAUSTED: Object.freeze({ parkedComponent: 'new_chatgpt_work', continuation: 'LOCAL_COMMISSIONED_LANES_CONTINUE', preserve: Object.freeze(['durable_queue', 'existing_sessions']) }),
  AUDIO_CACHE_MISS: Object.freeze({ parkedComponent: 'missing_cue', continuation: 'SKIP_CUE_KEEP_VOICE_AND_TEXT', preserve: Object.freeze(['live_voice', 'text', 'commissioned_local_lanes']) })
});

const AUDIO_CACHE_RECEIPT_KINDS = Object.freeze(['CACHE_HIT', 'PLAY_STARTED', 'REFILL_QUEUED']);

function validateControlYield(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['control yield must be a plain object'] };
  if (!CONTROL_PHASES.includes(value.phase)) errors.push(`control.phase must be one of ${CONTROL_PHASES.join(', ')}`);
  for (const key of ['yieldId', 'commissionId', 'queueRevision', 'laneId', 'actuatorId', 'from', 'to']) requireText(value[key], `control.${key}`, errors);
  requireSha(value.commissionHash, 'control.commissionHash', errors);
  requireRfc3339(value.observedAt, 'control.observedAt', errors);
  if (value.phase === 'YIELD_LOCAL' && (value.from !== 'voice_aperture' || value.to !== 'local_broker')) errors.push('YIELD_LOCAL must transfer voice_aperture to local_broker');
  if (value.phase === 'LOCAL_OWNS_ACTUATOR' && value.to !== value.actuatorId) errors.push('LOCAL_OWNS_ACTUATOR must bind to the named actuator');
  if (value.phase === 'RETURN_TO_VOICE' && value.to !== 'voice_aperture') errors.push('RETURN_TO_VOICE must return to voice_aperture');
  return { ok: errors.length === 0, errors };
}

function validateNarrationRoute(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['narration route must be a plain object'] };
  for (const key of ['routeId', 'provider', 'purpose', 'textMirror']) requireText(value[key], `narration.${key}`, errors);
  if (value.provider === 'venice_local') {
    if (value.purpose !== 'LIVE_VENICE_RELAY') errors.push('local Venice route must be LIVE_VENICE_RELAY');
    if (value.carrier !== 'chatgpt_voice') errors.push('live local Venice audio must use chatgpt_voice as the audible carrier');
    if (value.speaker !== 'Venice' || value.interfaceNarrator !== 'Adam') errors.push('Venice must remain the attributed speaker and Adam the interface narrator');
    requireSha(value.sourceReceiptSha256, 'narration.sourceReceiptSha256', errors);
    if (value.exactWords !== true || value.allowImpersonation !== false) errors.push('local Venice relay must preserve exact words and forbid impersonation');
  } else if (value.provider === 'piper') {
    if (value.purpose !== 'PERSONAL_TOUCH_DURABLE_AUDIO') errors.push('Piper is allowed only for PERSONAL_TOUCH_DURABLE_AUDIO');
    if (value.separatelyCommissioned !== true) errors.push('Piper requires separatelyCommissioned=true');
    if (value.autoSynthesize !== false || value.autoPlayback !== false) errors.push('Piper cannot auto-synthesize or auto-play');
    requireSha(value.artifactDigest, 'narration.artifactDigest', errors);
  } else if (value.provider === 'gemini' || value.provider === 'orus') {
    if (value.purpose !== 'POLISHED_ARTIFACT') errors.push('Gemini and Orus are allowed only for POLISHED_ARTIFACT');
    if (value.separatelyCommissioned !== true) errors.push('Gemini and Orus require separatelyCommissioned=true');
    requireSha(value.artifactDigest, 'narration.artifactDigest', errors);
  } else errors.push('narration.provider must be venice_local, piper, gemini, or orus');
  return { ok: errors.length === 0, errors };
}

function validateAudioLease(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['audio lease must be a plain object'] };
  for (const key of ['leaseId', 'holderId', 'deviceId']) requireText(value[key], `audioLease.${key}`, errors);
  if (!Number.isSafeInteger(value.fencingToken) || value.fencingToken < 1) errors.push('audioLease.fencingToken must be a positive safe integer');
  requireRfc3339(value.acquiredAt, 'audioLease.acquiredAt', errors);
  requireRfc3339(value.expiresAt, 'audioLease.expiresAt', errors);
  if (errors.length === 0 && Date.parse(value.expiresAt) <= Date.parse(value.acquiredAt)) errors.push('audioLease.expiresAt must be later than acquiredAt');
  return { ok: errors.length === 0, errors };
}

function validateAsmrProjection(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['ASMR projection must be a plain object'] };
  for (const key of ['projectionId', 'eventType', 'textMirror']) requireText(value[key], `asmr.${key}`, errors);
  if (value.optional !== true || value.muteable !== true || value.semanticEffect !== false) errors.push('ASMR projection must be optional, muteable, and nonsemantic');
  const lease = validateAudioLease(value.audioLease);
  errors.push(...lease.errors);
  return { ok: errors.length === 0, errors };
}

function validateAssembly(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['assembly must be a plain object'] };
  for (const key of ['assemblyId', 'mediaType', 'artifactRef']) requireText(value[key], `assembly.${key}`, errors);
  if (!ASSEMBLY_KINDS.includes(value.kind)) errors.push(`assembly.kind must be one of ${ASSEMBLY_KINDS.join(', ')}`);
  requireStringArray(value.inputRefs, 'assembly.inputRefs', errors, { nonEmpty: true });
  requireSha(value.artifactSha256, 'assembly.artifactSha256', errors);
  if (value.local !== true) errors.push('assembly.local must be true');
  if (value.played !== false) errors.push('assembly.played must remain false until a separate playback receipt');
  return { ok: errors.length === 0, errors };
}

function validatePlayback(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['playback must be a plain object'] };
  for (const key of ['playbackId', 'assemblyId', 'deviceId']) requireText(value[key], `playback.${key}`, errors);
  requireSha(value.assemblySha256, 'playback.assemblySha256', errors);
  if (value.kind !== 'LOCAL_PLAYBACK') errors.push('playback.kind must be LOCAL_PLAYBACK');
  const lease = validateAudioLease(value.audioLease);
  errors.push(...lease.errors);
  if (value.asmrProjection !== undefined) errors.push(...validateAsmrProjection(value.asmrProjection).errors);
  return { ok: errors.length === 0, errors };
}

function validateFailureContinuation(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['failure continuation must be a plain object'] };
  const expected = FAILURE_DEGRADATION[value.failureKind];
  if (!expected) return { ok: false, errors: ['failure.failureKind is unsupported'] };
  requireText(value.failedLaneId, 'failure.failedLaneId', errors);
  requireStringArray(value.independentLaneIds, 'failure.independentLaneIds', errors, { nonEmpty: true });
  if (value.failedLaneState !== 'PARKED') errors.push('failed action must park only its lane');
  if (value.independentLaneState !== 'REALLOCATED') errors.push('independent lanes must be REALLOCATED');
  if (value.continuation !== expected.continuation) errors.push('failure continuation does not match the degradation ladder');
  if (value.claimedSuccess !== false) errors.push('degraded continuation cannot invent success');
  if (value.safetyGatesFailClosed !== true) errors.push('safety gates must remain fail closed');
  return { ok: errors.length === 0, errors };
}

function audioCacheKeyPayload(value) {
  return { cueId: value.cueId, profileId: value.profileId, version: value.version, contentSha256: value.contentSha256 };
}

function validateAudioCacheEntry(value, policy) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['audio cache entry must be a plain object'] };
  if (value.kind !== 'local_audio.cache') errors.push('audioCache.kind must be local_audio.cache');
  for (const key of ['cueId', 'profileId', 'version']) requireText(value[key], `audioCache.${key}`, errors);
  requireSha(value.contentSha256, 'audioCache.contentSha256', errors);
  requireSha(value.cacheKey, 'audioCache.cacheKey', errors);
  if (!Number.isSafeInteger(value.byteLength) || value.byteLength < 1) errors.push('audioCache.byteLength must be a positive safe integer');
  if (value.preRendered !== true || value.buffered !== true || value.bytesVerified !== true || value.decodedReady !== true) errors.push('audioCache cue must be pre-rendered, buffered, byte-verified, and decoded ready');
  if (value.semanticEffect !== false) errors.push('audioCache cue must be nonsemantic');
  requireRfc3339(value.createdAt, 'audioCache.createdAt', errors);
  requireRfc3339(value.expiresAt, 'audioCache.expiresAt', errors);
  if (value.supersededBy !== null) requireSha(value.supersededBy, 'audioCache.supersededBy', errors);
  if (!isRecord(policy)) errors.push('audio cache policy must be a plain object');
  else {
    if (!Number.isSafeInteger(policy.byteBudget) || policy.byteBudget < 1) errors.push('audioCachePolicy.byteBudget must be positive');
    if (!Number.isSafeInteger(policy.maxEntries) || policy.maxEntries < 1) errors.push('audioCachePolicy.maxEntries must be positive');
    if (policy.eviction !== 'LRU' || policy.expiryRequired !== true || policy.supersessionRequired !== true || policy.backgroundRefill !== true) errors.push('audio cache policy must enforce LRU, expiry, supersession, and background refill');
    if (Number.isSafeInteger(value.byteLength) && Number.isSafeInteger(policy.byteBudget) && value.byteLength > policy.byteBudget) errors.push('audioCache entry exceeds byte budget');
  }
  if (errors.length === 0) {
    if (sha256(audioCacheKeyPayload(value)) !== value.cacheKey) errors.push('audioCache.cacheKey does not bind cue/profile/version/hash');
    if (Date.parse(value.expiresAt) <= Date.parse(value.createdAt)) errors.push('audioCache.expiresAt must be later than createdAt');
  }
  return { ok: errors.length === 0, errors };
}

function validateAudioCacheReceipt(value, context = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['audio cache receipt must be a plain object'] };
  if (!AUDIO_CACHE_RECEIPT_KINDS.includes(value.kind)) errors.push(`audio cache receipt.kind must be one of ${AUDIO_CACHE_RECEIPT_KINDS.join(', ')}`);
  requireText(value.receiptId, 'audioCacheReceipt.receiptId', errors);
  requireSha(value.cacheKey, 'audioCacheReceipt.cacheKey', errors);
  requireRfc3339(value.observedAt, 'audioCacheReceipt.observedAt', errors);
  if (value.kind === 'CACHE_HIT' || value.kind === 'PLAY_STARTED') {
    if (!isRecord(context.entry) || !isRecord(context.policy)) errors.push('cache use receipt requires its cache entry and policy');
    else {
      errors.push(...validateAudioCacheEntry(context.entry, context.policy).errors.map(error => `cache use ${error}`));
      if (context.entry.cacheKey !== value.cacheKey) errors.push('cache use receipt cacheKey mismatch');
      if (context.entry.supersededBy !== null) errors.push('cache use cannot replay a superseded cue');
      if (Date.parse(value.observedAt) >= Date.parse(context.entry.expiresAt)) errors.push('cache use cannot replay an expired cue');
    }
  }
  if (value.kind === 'CACHE_HIT' && value.playStarted !== false) errors.push('CACHE_HIT must not imply playback');
  if (value.kind === 'PLAY_STARTED') {
    errors.push(...validateAudioLease(value.audioLease).errors);
    if (errors.length === 0 && (Date.parse(value.observedAt) < Date.parse(value.audioLease.acquiredAt) || Date.parse(value.observedAt) >= Date.parse(value.audioLease.expiresAt))) errors.push('PLAY_STARTED must occur inside the audio lease');
  }
  if (value.kind === 'REFILL_QUEUED' && value.background !== true) errors.push('REFILL_QUEUED must be background work');
  return { ok: errors.length === 0, errors };
}

function validateAudioCuePalette(entries, policy, now) {
  const errors = [];
  const timeErrors = [];
  requireRfc3339(now, 'audioPalette.now', timeErrors);
  errors.push(...timeErrors);
  if (!Array.isArray(entries) || entries.length === 0) return { ok: false, errors: [...errors, 'audio palette must be a non-empty array'] };
  if (!isRecord(policy)) return { ok: false, errors: [...errors, 'audio cache policy must be a plain object'] };
  if (Number.isSafeInteger(policy.maxEntries) && entries.length > policy.maxEntries) errors.push('audio palette exceeds maxEntries');
  let bytes = 0;
  const keys = new Set();
  entries.forEach((entry, index) => {
    const validation = validateAudioCacheEntry(entry, policy);
    errors.push(...validation.errors.map(error => `audioPalette[${index}] ${error}`));
    if (keys.has(entry.cacheKey)) errors.push(`audioPalette duplicates cache key ${entry.cacheKey}`);
    keys.add(entry.cacheKey);
    if (Number.isSafeInteger(entry.byteLength)) bytes += entry.byteLength;
    if (Number.isFinite(Date.parse(now)) && Number.isFinite(Date.parse(entry.expiresAt)) && Date.parse(now) >= Date.parse(entry.expiresAt)) errors.push(`audioPalette[${index}] is expired`);
    if (entry.supersededBy !== null) errors.push(`audioPalette[${index}] is superseded`);
  });
  if (Number.isSafeInteger(policy.byteBudget) && bytes > policy.byteBudget) errors.push('audio palette exceeds byteBudget');
  return { ok: errors.length === 0, errors };
}

function validateAudioCacheMiss(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['audio cache miss must be a plain object'] };
  requireSha(value.cacheKey, 'audioCacheMiss.cacheKey', errors);
  if (value.cueSkipped !== true || value.liveVoiceContinues !== true || value.textContinues !== true) errors.push('cache miss must skip the cue while live Voice and text continue');
  if (value.refillQueued !== true || value.refillMode !== 'BACKGROUND') errors.push('cache miss must queue a background refill');
  if (value.staleSemanticReplay !== false) errors.push('cache miss must forbid stale semantic replay');
  if (value.geminiFallback !== false) errors.push('cache miss must not route to Gemini');
  if (value.claimedPlayback !== false) errors.push('cache miss cannot claim playback');
  return { ok: errors.length === 0, errors };
}

function validateLocalMultitaskPlan(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['local multitask plan must be a plain object'] };
  if (value.kind !== 'LOCAL_MULTITASK_PLAN' || value.definition !== 'ONE_SUPERVISORY_VOICE_MANY_FENCED_LOCAL_LANES') errors.push('local multitask must mean one supervisory Voice over many fenced local lanes');
  for (const key of ['planId', 'queueRevision', 'stateOwner']) requireText(value[key], `multitask.${key}`, errors);
  requireSha(value.commissionHash, 'multitask.commissionHash', errors);
  if (value.stateOwner !== 'Adam') errors.push('Adam must remain the sole state owner');
  if (value.voiceOwnsActuator !== false || value.continueIndependentLanes !== true) errors.push('Voice owns no actuator and independent local lanes must continue');
  if (value.executionBudget !== 'LOCAL_OR_INCLUDED_ONLY') errors.push('multitask.executionBudget must be LOCAL_OR_INCLUDED_ONLY');
  if (!Array.isArray(value.lanes) || value.lanes.length === 0) errors.push('multitask.lanes must be a non-empty array');
  else {
    const ids = new Set();
    const paths = new Set();
    const branches = new Set();
    value.lanes.forEach((lane, index) => {
      if (!isRecord(lane)) return errors.push(`multitask.lanes[${index}] must be a plain object`);
      for (const key of ['laneId', 'owner', 'isolatedPath', 'branch']) requireText(lane[key], `multitask.lanes[${index}].${key}`, errors);
      requireStringArray(lane.operations, `multitask.lanes[${index}].operations`, errors, { nonEmpty: true });
      if (lane.materialTransitionBudget !== 1) errors.push(`multitask.lanes[${index}].materialTransitionBudget must equal 1`);
      for (const [set, key] of [[ids, 'laneId'], [paths, 'isolatedPath'], [branches, 'branch']]) {
        if (set.has(lane[key])) errors.push(`multitask.lanes duplicate ${key} ${lane[key]}`);
        set.add(lane[key]);
      }
    });
  }
  return { ok: errors.length === 0, errors };
}

module.exports = {
  CONTROL_PHASES,
  ASSEMBLY_KINDS,
  FAILURE_DEGRADATION,
  AUDIO_CACHE_RECEIPT_KINDS,
  validateControlYield,
  validateNarrationRoute,
  validateAudioLease,
  validateAsmrProjection,
  validateAssembly,
  validatePlayback,
  validateFailureContinuation,
  audioCacheKeyPayload,
  validateAudioCacheEntry,
  validateAudioCuePalette,
  validateAudioCacheReceipt,
  validateAudioCacheMiss,
  validateLocalMultitaskPlan
};
