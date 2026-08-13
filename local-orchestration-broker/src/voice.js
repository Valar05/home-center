'use strict';

const { isRecord, requireText, requireSha, requireRfc3339, requireStringArray, canonicalJson, sha256 } = require('./contracts');
const { authorizeApproval } = require('./guards');

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

const FLOW_STATES = Object.freeze(['QUEUED', 'YIELD_LOCAL', 'LOCAL_WORKING', 'MATERIAL_TRANSITION', 'BLOCKED', 'RETURN_TO_VOICE']);
const CACHE_RECEIPT_KINDS = Object.freeze(['CACHE_HIT', 'CACHE_MISS', 'REFILL_QUEUED', 'REFILL_READY', 'PLAY_STARTED', 'PLAY_FINISHED', 'PLAY_FAILED', 'PLAY_MUTED']);

function digestWithout(value, key) {
  const payload = { ...value };
  delete payload[key];
  return payload;
}

function validateControlYield(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['control yield must be a plain object'] };
  if (!CONTROL_PHASES.includes(value.phase)) errors.push(`control.phase must be one of ${CONTROL_PHASES.join(', ')}`);
  for (const key of ['transitionId', 'commissionId', 'queueRevision', 'laneId', 'jobId', 'sessionId', 'idempotencyKey', 'action', 'target', 'leaseId', 'leaseDigest']) requireText(value[key], `control.${key}`, errors);
  requireSha(value.commissionHash, 'control.commissionHash', errors);
  requireSha(value.leaseDigest, 'control.leaseDigest', errors);
  requireSha(value.transitionHash, 'control.transitionHash', errors);
  requireRfc3339(value.observedAt, 'control.observedAt', errors);
  if (!Number.isSafeInteger(value.fencingToken) || value.fencingToken < 1) errors.push('control.fencingToken must be positive');
  if (!Number.isSafeInteger(value.phaseSequence) || value.phaseSequence !== CONTROL_PHASES.indexOf(value.phase) + 1) errors.push('control.phaseSequence does not match phase');
  requireStringArray(value.stopGates, 'control.stopGates', errors, { nonEmpty: true });
  if (!isRecord(value.device) || !isRecord(value.mobileSession)) errors.push('control requires device and mobileSession identity');
  else {
    for (const key of ['deviceId', 'appId', 'buildId', 'accountId']) requireText(value.device[key], `control.device.${key}`, errors);
    for (const key of ['mobileSessionId', 'conversationId', 'turnId']) requireText(value.mobileSession[key], `control.mobileSession.${key}`, errors);
  }
  if (value.phase === 'YIELD_LOCAL' && value.previousPhaseHash !== null) errors.push('YIELD_LOCAL previousPhaseHash must be null');
  if (value.phase !== 'YIELD_LOCAL') {
    requireSha(value.previousPhaseHash, 'control.previousPhaseHash', errors);
    if (!isRecord(options.previous) || options.previous.transitionHash !== value.previousPhaseHash || options.previous.transitionId !== value.transitionId || options.previous.phaseSequence + 1 !== value.phaseSequence) errors.push('control previous phase chain mismatch');
  }
  const leaseOptions = { now: value.observedAt, trustedLease: options.trustedLease, registry: options.leaseRegistry, activeLeases: options.activeLeases };
  errors.push(...validateAudioLease(options.trustedLease, leaseOptions).errors.map(error => `control ${error}`));
  if (!isRecord(options.trustedLease) || options.trustedLease.leaseId !== value.leaseId || options.trustedLease.leaseDigest !== value.leaseDigest || options.trustedLease.fencingToken !== value.fencingToken) errors.push('control trusted lease mismatch');
  else {
    for (const key of ['commissionHash','queueRevision','laneId','jobId','sessionId','action']) if (value[key] !== options.trustedLease[key]) errors.push(`control.${key} does not match trusted lease`);
    if (canonicalJson(value.device) !== canonicalJson(options.trustedLease.target) || value.mobileSession.conversationId !== options.trustedLease.conversationId) errors.push('control device/mobile conversation does not match trusted lease');
  }
  if (value.phase !== 'YIELD_LOCAL' && isRecord(options.previous)) for (const key of ['transitionId','commissionId','commissionHash','queueRevision','laneId','jobId','sessionId','idempotencyKey','action','target','leaseId','leaseDigest','fencingToken','device','mobileSession']) if (canonicalJson(value[key]) !== canonicalJson(options.previous[key])) errors.push(`control.${key} changed across phases`);
  if (!validateTransitionCas(options.phaseCas,value,options.transitionRegistry)) errors.push('every control phase requires persistent exact CAS');
  if (value.phase === 'RETURN_TO_VOICE') {
    requireSha(value.actionReceiptHash, 'control.actionReceiptHash', errors);
    if (typeof options.resolveActionReceipt !== 'function') errors.push('RETURN_TO_VOICE requires trusted action receipt resolution');
    else {
      const receipt = options.resolveActionReceipt(value.actionReceiptHash);
      for (const key of ['transitionId', 'commissionHash', 'queueRevision', 'laneId', 'jobId', 'sessionId', 'idempotencyKey', 'action', 'target', 'leaseId', 'leaseDigest']) if (!isRecord(receipt) || receipt[key] !== value[key]) errors.push(`RETURN_TO_VOICE receipt ${key} mismatch`);
      if (!isRecord(receipt) || !['COMPLETED', 'FAILED'].includes(receipt.state)) errors.push('RETURN_TO_VOICE requires terminal action receipt');
    }
    if (!isRecord(options.cas) || options.cas.expectedPhase !== 'LOCAL_OWNS_ACTUATOR' || options.cas.nextPhase !== 'RETURN_TO_VOICE' || options.cas.transitionId !== value.transitionId || options.cas.expectedTransitionHash !== value.previousPhaseHash) errors.push('RETURN_TO_VOICE requires exact transition CAS');
  }
  if (errors.length === 0 && sha256(digestWithout(value, 'transitionHash')) !== value.transitionHash) errors.push('control.transitionHash mismatch');
  return { ok: errors.length === 0, errors };
}

function validateNarrationRoute(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['narration route must be a plain object'] };
  for (const key of ['routeId', 'provider', 'purpose', 'textMirror']) requireText(value[key], `narration.${key}`, errors);
  if (value.provider === 'venice_local') {
    for(const key of ['queueRevision','laneId','sessionId']) requireText(value[key],`narration.${key}`,errors);requireSha(value.commissionHash,'narration.commissionHash',errors);
    if (value.purpose !== 'LIVE_VENICE_RELAY') errors.push('local Venice route must be LIVE_VENICE_RELAY');
    if (value.primarySurface !== 'venice_mobile') errors.push('Venice mobile must remain the primary command and receipt surface');
    if (value.carrier === 'chatgpt_voice' && value.diagnosticCarrier !== true) errors.push('desktop ChatGPT Voice is diagnostic/relay-only, never the primary mobile surface');
    if (value.speaker !== 'Venice' || value.interfaceNarrator !== 'Adam') errors.push('Venice must remain the attributed speaker and Adam the interface narrator');
    requireSha(value.sourceReceiptSha256, 'narration.sourceReceiptSha256', errors);
    if (value.exactWords !== true || value.allowImpersonation !== false) errors.push('local Venice relay must preserve exact words and forbid impersonation');
    const source = typeof options.resolveSourceReceipt === 'function' ? options.resolveSourceReceipt(value.sourceReceiptSha256) : null;
    if (!isRecord(source) || source.receiptHash !== value.sourceReceiptSha256 || source.speaker !== 'Venice' || source.exactText !== value.textMirror || source.terminal !== true || source.commissionHash!==value.commissionHash||source.queueRevision!==value.queueRevision||source.laneId!==value.laneId||source.sessionId!==value.sessionId) errors.push('local Venice route requires a trusted exact terminal full-scope source receipt');
  } else if (value.provider === 'piper') {
    if (value.purpose !== 'PERSONAL_TOUCH_DURABLE_AUDIO') errors.push('Piper is allowed only for PERSONAL_TOUCH_DURABLE_AUDIO');
    if (value.separatelyCommissioned !== true) errors.push('Piper requires separatelyCommissioned=true');
    if (value.autoSynthesize !== false || value.autoPlayback !== false) errors.push('Piper cannot auto-synthesize or auto-play');
    requireSha(value.artifactDigest, 'narration.artifactDigest', errors);
  } else if (value.provider === 'gemini' || value.provider === 'orus') {
    requireSha(value.commissionHash,'narration.commissionHash',errors);
    if (value.purpose !== 'POLISHED_ARTIFACT') errors.push('Gemini and Orus are allowed only for POLISHED_ARTIFACT');
    if (value.separatelyCommissioned !== true) errors.push('Gemini and Orus require separatelyCommissioned=true');
    requireSha(value.artifactDigest, 'narration.artifactDigest', errors);
    for (const key of ['spendingAuthorityId', 'deliveryAuthorityId', 'publicationAuthorityId']) requireText(value[key], `narration.${key}`, errors);
    if (value.humanAcceptanceRequired !== true || value.humanAccepted !== false || value.acceptanceState !== 'PENDING_HUMAN' || value.autoPublish !== false || value.autoDeliver !== false) errors.push('polished provider route requires pending separate human acceptance');
    if (typeof options.resolveApproval !== 'function') errors.push('polished route requires trusted approvals');
    else for (const [kind,key] of [['SPENDING','spendingAuthorityId'],['DELIVERY','deliveryAuthorityId'],['PUBLICATION','publicationAuthorityId']]) { const a=options.resolveApproval(value[key]); try{const out=authorizeApproval(a,{actor:'Drew',action:`polished:${kind}`,target:value.provider,artifactDigest:value.artifactDigest,environment:'POLISHED_ARTIFACT',commissionHash:value.commissionHash,idempotencyKey:`${value.routeId}:${kind}`},options.now,options.approvalRegistry);if(!out.cas)errors.push(`${kind} approval CAS missing`);}catch(error){errors.push(`${kind} approval mismatch: ${error.code||error.message}`);} }
  } else errors.push('narration.provider must be venice_local, piper, gemini, or orus');
  return { ok: errors.length === 0, errors };
}

function validateAudioLease(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['audio lease must be a plain object'] };
  for (const key of ['leaseId', 'holderId', 'commissionHash', 'queueRevision', 'laneId', 'jobId', 'sessionId', 'conversationId', 'channel', 'action', 'idempotencyNamespace']) requireText(value[key], `audioLease.${key}`, errors);
  requireSha(value.commissionHash, 'audioLease.commissionHash', errors);
  requireSha(value.leaseDigest, 'audioLease.leaseDigest', errors);
  if (!isRecord(value.target)) errors.push('audioLease.target must be a plain object');
  else for (const key of ['deviceId', 'appId', 'accountId']) requireText(value.target[key], `audioLease.target.${key}`, errors);
  if (!Number.isSafeInteger(value.fencingToken) || value.fencingToken < 1) errors.push('audioLease.fencingToken must be a positive safe integer');
  requireRfc3339(value.acquiredAt, 'audioLease.acquiredAt', errors);
  requireRfc3339(value.expiresAt, 'audioLease.expiresAt', errors);
  if (!['ACTIVE', 'CONSUMED', 'REVOKED'].includes(value.state)) errors.push('audioLease.state is unsupported');
  if (!['AUDIBLE_ALLOWED', 'MUTED', 'MUTED_UNATTENDED'].includes(value.muteState)) errors.push('audioLease.muteState is unsupported');
  if (value.unattended === true && value.muteState !== 'MUTED_UNATTENDED') errors.push('unattended lease must be MUTED_UNATTENDED');
  requireRfc3339(options.now, 'audioLease options.now', errors);
  if (!isRecord(options.trustedLease) || canonicalJson(options.trustedLease) !== canonicalJson(value)) errors.push('audioLease trusted persistent identity mismatch');
  if (!isRecord(options.registry) || !Array.isArray(options.registry.consumedLeaseIds) || options.registry.consumedLeaseIds.includes(value.leaseId)) errors.push('audioLease replay registry missing or lease consumed');
  if (Array.isArray(options.activeLeases)) for (const active of options.activeLeases) if (active.leaseId !== value.leaseId && active.state === 'ACTIVE' && actuatorKey(active) === actuatorKey(value)) errors.push('audioLease overlaps an active actuator on the same physical output');
  if (errors.length === 0) {
    if (Date.parse(value.expiresAt) <= Date.parse(value.acquiredAt) || Date.parse(options.now) >= Date.parse(value.expiresAt)) errors.push('audioLease is expired or invalid');
    if (sha256(digestWithout(value, 'leaseDigest')) !== value.leaseDigest) errors.push('audioLease.leaseDigest mismatch');
  }
  return { ok: errors.length === 0, errors };
}

function actuatorKey(lease) { return `${lease?.target?.deviceId || ''}:${lease?.target?.outputId || 'default-audio'}`; }
function validateTransitionCas(cas,value,registry){if(!isRecord(cas)||!isRecord(registry)||typeof registry.registryId!=='string'||!Number.isSafeInteger(registry.revision)||!isRecord(registry.transitionHeads)||!Array.isArray(registry.consumedIdempotencyKeys))return false;const expected=value.previousPhaseHash??null;if(cas.registryId!==registry.registryId||cas.expectedRevision!==registry.revision||cas.nextRevision!==registry.revision+1||cas.transitionId!==value.transitionId||cas.expectedPhase!==(value.phase==='YIELD_LOCAL'?'NONE':CONTROL_PHASES[value.phaseSequence-2])||cas.nextPhase!==value.phase||cas.expectedTransitionHash!==expected||registry.transitionHeads[value.transitionId]!==expected||cas.nextTransitionHash!==value.transitionHash||cas.idempotencyKey!==`${value.idempotencyKey}:${value.phase}`||registry.consumedIdempotencyKeys.includes(cas.idempotencyKey))return false;const p={...cas};delete p.casHash;return /^[a-f0-9]{64}$/.test(cas.casHash||'')&&sha256(p)===cas.casHash;}
function validateActionCas(cas, value, receiptHash, registry) { if(!isRecord(cas)||!isRecord(registry)||typeof registry.registryId!=='string'||!Number.isSafeInteger(registry.revision)||!Array.isArray(registry.consumedIdempotencyKeys))return false;if(cas.registryId!==registry.registryId||cas.expectedRevision!==registry.revision||cas.nextRevision!==registry.revision+1||cas.leaseId!==value.audioLease?.leaseId||cas.leaseDigest!==value.audioLease?.leaseDigest||cas.fencingToken!==value.audioLease?.fencingToken||cas.actionId!==(value.playbackId||value.projectionId)||cas.idempotencyKey!==value.idempotencyKey||cas.receiptHash!==receiptHash||registry.consumedIdempotencyKeys.includes(cas.idempotencyKey))return false;const p={...cas};delete p.casHash;return /^[a-f0-9]{64}$/.test(cas.casHash||'')&&sha256(p)===cas.casHash; }

function validateAsmrProjection(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['ASMR projection must be a plain object'] };
  for (const key of ['projectionId', 'cueId', 'textMirror', 'responsibleActor', 'idempotencyKey']) requireText(value[key], `asmr.${key}`, errors);
  if (value.optional !== true || value.muteable !== true || value.semanticEffect !== false) errors.push('ASMR projection must be optional, muteable, and nonsemantic');
  if (!isRecord(value.event)) errors.push('asmr.event must be a plain object');
  else {
    for (const key of ['commissionHash', 'queueRevision', 'laneId', 'jobId', 'sessionId', 'eventHash']) requireText(value.event[key], `asmr.event.${key}`, errors);
    requireSha(value.event.commissionHash, 'asmr.event.commissionHash', errors);
    requireSha(value.event.eventHash, 'asmr.event.eventHash', errors);
    if (!FLOW_STATES.includes(value.event.flowState)) errors.push('asmr.event.flowState is unsupported');
    if (!Number.isSafeInteger(value.event.eventSequence) || value.event.eventSequence < 1) errors.push('asmr.event.eventSequence must be positive');
    requireRfc3339(value.event.issuedAt, 'asmr.event.issuedAt', errors);
    requireRfc3339(value.event.expiresAt, 'asmr.event.expiresAt', errors);
    if (!value.textMirror.includes(value.event.flowState) || !value.textMirror.includes(value.event.laneId) || !value.textMirror.includes(value.responsibleActor)) errors.push('ASMR text mirror must contain state, lane, and responsible actor');
    if (!isRecord(options.authoritativeEvent) || canonicalJson(value.event) !== canonicalJson(options.authoritativeEvent)) errors.push('ASMR requires exact authoritative flow event');
  }
  const lease = validateAudioLease(value.audioLease, options.leaseOptions || {});
  errors.push(...lease.errors);
  if (isRecord(value.event) && isRecord(value.audioLease)) for (const key of ['commissionHash','queueRevision','laneId','jobId','sessionId']) if(value.event[key]!==value.audioLease[key]) errors.push(`ASMR event ${key} does not match audio lease`);
  if (!validateActionCas(options.consumptionCas, value, value.event?.eventHash,options.actionRegistry)) errors.push('ASMR requires persistent lease-bound consumption CAS');
  if (value.requestedAudible === true && (value.audioLease?.muteState !== 'AUDIBLE_ALLOWED' || value.audioLease?.unattended === true)) errors.push('mute/unattended state dominates ASMR readiness');
  if (isRecord(value.event) && Number.isFinite(Date.parse(options.now)) && Date.parse(options.now) >= Date.parse(value.event.expiresAt)) errors.push('ASMR event expired');
  if (!isRecord(options.eventRegistry) || !Array.isArray(options.eventRegistry.consumedEventHashes) || options.eventRegistry.consumedEventHashes.includes(value.event?.eventHash)) errors.push('ASMR consumed-event registry missing or replay detected');
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

function validatePlayback(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['playback must be a plain object'] };
  for (const key of ['playbackId', 'assemblyId', 'commissionHash', 'queueRevision', 'laneId', 'jobId', 'sessionId', 'conversationId', 'idempotencyKey']) requireText(value[key], `playback.${key}`, errors);
  requireSha(value.assemblySha256, 'playback.assemblySha256', errors);
  requireSha(value.commissionHash, 'playback.commissionHash', errors);
  if (value.kind !== 'LOCAL_PLAYBACK') errors.push('playback.kind must be LOCAL_PLAYBACK');
  if (!isRecord(value.target)) errors.push('playback.target must be a plain object');
  else for (const key of ['deviceId', 'appId', 'accountId']) requireText(value.target[key], `playback.target.${key}`, errors);
  const lease = validateAudioLease(value.audioLease, options.leaseOptions || {});
  errors.push(...lease.errors);
  if (isRecord(value.audioLease)) {
    for (const key of ['commissionHash','queueRevision','laneId','jobId','sessionId','conversationId']) if(value[key]!==value.audioLease[key]) errors.push(`playback.${key} does not match audio lease`);
    if (canonicalJson(value.target)!==canonicalJson(value.audioLease.target)) errors.push('playback target does not match audio lease');
    if (value.audioLease.action!=='PLAY_ASSEMBLY') errors.push('playback requires PLAY_ASSEMBLY lease action');
  }
  if (!validateActionCas(options.consumptionCas, value, value.actionReceiptHash ?? null,options.actionRegistry)) errors.push('playback requires persistent lease-bound consumption CAS');
  if (value.asmrProjection !== undefined) errors.push('media playback cannot share the dynamic ASMR channel');
  if (!['REQUESTED', 'STARTED', 'FINISHED', 'FAILED', 'MUTED'].includes(value.state)) errors.push('playback.state is unsupported');
  if (['STARTED', 'FINISHED', 'FAILED', 'MUTED'].includes(value.state)) {
    requireSha(value.actionReceiptHash, 'playback.actionReceiptHash', errors);
    if (typeof options.resolveActionReceipt !== 'function') errors.push('playback state requires trusted action receipt');
    else {
      const receipt = options.resolveActionReceipt(value.actionReceiptHash);
      for (const key of ['playbackId', 'assemblyId', 'assemblySha256', 'commissionHash', 'queueRevision', 'laneId', 'jobId', 'sessionId', 'conversationId', 'idempotencyKey']) if (!isRecord(receipt) || receipt[key] !== value[key]) errors.push(`playback receipt ${key} mismatch`);
      if (!isRecord(receipt) || receipt.state !== value.state) errors.push('playback receipt state mismatch');
    }
  }
  return { ok: errors.length === 0, errors };
}

function validateFailureContinuation(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['failure continuation must be a plain object'] };
  const expected = FAILURE_DEGRADATION[value.failureKind];
  if (!expected) return { ok: false, errors: ['failure.failureKind is unsupported'] };
  requireText(value.failedLaneId, 'failure.failedLaneId', errors);
  requireStringArray(value.independentLaneIds, 'failure.independentLaneIds', errors);
  if (!['PARKED', 'WAITING_APPROVAL', 'TRANSPORT_TIMEOUT', 'WAITING_EVIDENCE'].includes(value.failedLaneState)) errors.push('failed action must retain a typed recoverable lane state');
  if (Array.isArray(value.independentLaneIds) && value.independentLaneIds.length === 0) {
    if (value.independentLaneState !== 'NONE_AVAILABLE' || value.systemState !== 'PAUSED_GATE' || value.textContinuity !== true) errors.push('zero independent lanes require recoverable PAUSED_GATE text continuity');
  } else if (value.independentLaneState !== 'REALLOCATED' || value.systemState !== 'ACTIVE_DEGRADED') errors.push('independent lanes must be REALLOCATED under ACTIVE_DEGRADED');
  if (value.continuation !== expected.continuation) errors.push('failure continuation does not match the degradation ladder');
  if (value.claimedSuccess !== false) errors.push('degraded continuation cannot invent success');
  if (value.safetyGatesFailClosed !== true) errors.push('safety gates must remain fail closed');
  return { ok: errors.length === 0, errors };
}

function audioCacheKeyPayload(value) {
  return { kind: value.entryKind, cueOrPhraseId: value.cueOrPhraseId, profileId: value.profileId, version: value.version, contentSha256: value.contentSha256, codecAndSampleFormat: value.codecAndSampleFormat, durationMs: value.durationMs, commissionHash: value.commissionHash, sourceReceiptHash: value.sourceReceiptHash };
}

function validateAudioCacheEntry(value, policy) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['audio cache entry must be a plain object'] };
  if (value.kind !== 'local_audio.cache') errors.push('audioCache.kind must be local_audio.cache');
  if (!['NONSEMANTIC_CUE', 'PIPER_COMMISSIONED_PHRASE'].includes(value.entryKind)) errors.push('audioCache.entryKind is unsupported');
  for (const key of ['cueOrPhraseId', 'profileId', 'version', 'codecAndSampleFormat']) requireText(value[key], `audioCache.${key}`, errors);
  requireSha(value.contentSha256, 'audioCache.contentSha256', errors);
  requireSha(value.sourceReceiptHash, 'audioCache.sourceReceiptHash', errors);
  if (value.entryKind === 'PIPER_COMMISSIONED_PHRASE') requireSha(value.commissionHash, 'audioCache.commissionHash', errors);
  else if (value.commissionHash !== null) errors.push('nonsemantic cue commissionHash must be null');
  requireSha(value.cacheKey, 'audioCache.cacheKey', errors);
  if (!Number.isSafeInteger(value.byteSize) || value.byteSize < 1) errors.push('audioCache.byteSize must be a positive safe integer');
  if (!Number.isSafeInteger(value.durationMs) || value.durationMs < 1) errors.push('audioCache.durationMs must be a positive safe integer');
  if (!Number.isSafeInteger(value.decodedMemoryBytes) || value.decodedMemoryBytes < 0) errors.push('audioCache.decodedMemoryBytes must be non-negative');
  if (value.preRendered !== true || value.buffered !== true || !['VERIFIED_BYTES', 'DECODED_READY'].includes(value.readiness)) errors.push('audioCache cue must be pre-rendered, buffered, and verified/decode-ready');
  if (value.entryKind === 'NONSEMANTIC_CUE' && value.semanticEffect !== false) errors.push('nonsemantic cache cue must be nonsemantic');
  requireRfc3339(value.createdAt, 'audioCache.createdAt', errors);
  requireRfc3339(value.expiresAt, 'audioCache.expiresAt', errors);
  if (value.supersedes !== null) requireSha(value.supersedes, 'audioCache.supersedes', errors);
  if (value.supersededBy !== null) requireSha(value.supersededBy, 'audioCache.supersededBy', errors);
  if (!isRecord(policy)) errors.push('audio cache policy must be a plain object');
  else {
    if (!Number.isSafeInteger(policy.byteBudget) || policy.byteBudget < 1) errors.push('audioCachePolicy.byteBudget must be positive');
    if (!Number.isSafeInteger(policy.maxEntries) || policy.maxEntries < 1) errors.push('audioCachePolicy.maxEntries must be positive');
    if (!Number.isSafeInteger(policy.decodedMemoryBudget) || policy.decodedMemoryBudget < 1 || !Number.isSafeInteger(policy.durationBudgetMs) || policy.durationBudgetMs < 1) errors.push('audio cache policy requires decoded-memory and duration budgets');
    if (policy.eviction !== 'LRU' || policy.expiryRequired !== true || policy.supersessionRequired !== true || policy.backgroundRefill !== true || policy.preserveActiveLease !== true) errors.push('audio cache policy must enforce LRU, expiry, supersession, background refill, and active-lease preservation');
    if (Number.isSafeInteger(value.byteSize) && Number.isSafeInteger(policy.byteBudget) && value.byteSize > policy.byteBudget) errors.push('audioCache entry exceeds byte budget');
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
  if (!CACHE_RECEIPT_KINDS.includes(value.kind)) errors.push(`audio cache receipt.kind must be one of ${CACHE_RECEIPT_KINDS.join(', ')}`);
  requireText(value.receiptId, 'audioCacheReceipt.receiptId', errors);
  requireSha(value.cacheKey, 'audioCacheReceipt.cacheKey', errors);
  requireRfc3339(value.observedAt, 'audioCacheReceipt.observedAt', errors);
  if (['CACHE_HIT', 'PLAY_STARTED', 'PLAY_FINISHED', 'PLAY_FAILED', 'PLAY_MUTED'].includes(value.kind)) {
    if (!isRecord(context.entry) || !isRecord(context.policy)) errors.push('cache use receipt requires its cache entry and policy');
    else {
      errors.push(...validateAudioCacheEntry(context.entry, context.policy).errors.map(error => `cache use ${error}`));
      if (context.entry.cacheKey !== value.cacheKey) errors.push('cache use receipt cacheKey mismatch');
      if (context.entry.supersededBy !== null) errors.push('cache use cannot replay a superseded cue');
      if (Date.parse(value.observedAt) >= Date.parse(context.entry.expiresAt)) errors.push('cache use cannot replay an expired cue');
    }
  }
  if (['CACHE_HIT', 'CACHE_MISS', 'REFILL_QUEUED', 'REFILL_READY'].includes(value.kind) && value.playbackClaim !== false) errors.push(`${value.kind} must not imply playback`);
  if (['PLAY_STARTED', 'PLAY_FINISHED', 'PLAY_FAILED', 'PLAY_MUTED'].includes(value.kind)) {
    errors.push(...validateAudioLease(value.audioLease, context.leaseOptions || {}).errors);
    if (errors.length === 0 && (Date.parse(value.observedAt) < Date.parse(value.audioLease.acquiredAt) || Date.parse(value.observedAt) >= Date.parse(value.audioLease.expiresAt))) errors.push('PLAY_STARTED must occur inside the audio lease');
  }
  if (value.kind === 'CACHE_MISS' && value.cueSkipped !== true) errors.push('CACHE_MISS must skip the cue');
  if (value.kind === 'REFILL_QUEUED' && (value.background !== true || value.authorized !== true || value.idempotent !== true)) errors.push('REFILL_QUEUED must be authorized idempotent background work');
  if (value.kind === 'REFILL_READY') {
    requireSha(value.refillReceiptHash, 'audioCacheReceipt.refillReceiptHash', errors);
    if (value.readiness !== 'DECODED_READY' && value.readiness !== 'VERIFIED_BYTES') errors.push('REFILL_READY requires verified readiness');
  }
  if (value.kind === 'PLAY_MUTED' && value.audioLease?.muteState === 'AUDIBLE_ALLOWED') errors.push('PLAY_MUTED requires a muted lease');
  if (value.humanAcceptanceClaim !== false) errors.push('cache/play receipts cannot claim human acceptance');
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
  let duration = 0;
  let decodedMemory = 0;
  const keys = new Set();
  entries.forEach((entry, index) => {
    const validation = validateAudioCacheEntry(entry, policy);
    errors.push(...validation.errors.map(error => `audioPalette[${index}] ${error}`));
    if (keys.has(entry.cacheKey)) errors.push(`audioPalette duplicates cache key ${entry.cacheKey}`);
    keys.add(entry.cacheKey);
    if (Number.isSafeInteger(entry.byteSize)) bytes += entry.byteSize;
    if (Number.isSafeInteger(entry.durationMs)) duration += entry.durationMs;
    if (Number.isSafeInteger(entry.decodedMemoryBytes)) decodedMemory += entry.decodedMemoryBytes;
    if (Number.isFinite(Date.parse(now)) && Number.isFinite(Date.parse(entry.expiresAt)) && Date.parse(now) >= Date.parse(entry.expiresAt)) errors.push(`audioPalette[${index}] is expired`);
    if (entry.supersededBy !== null) errors.push(`audioPalette[${index}] is superseded`);
  });
  if (Number.isSafeInteger(policy.byteBudget) && bytes > policy.byteBudget) errors.push('audio palette exceeds byteBudget');
  if (Number.isSafeInteger(policy.durationBudgetMs) && duration > policy.durationBudgetMs) errors.push('audio palette exceeds durationBudgetMs');
  if (Number.isSafeInteger(policy.decodedMemoryBudget) && decodedMemory > policy.decodedMemoryBudget) errors.push('audio palette exceeds decodedMemoryBudget');
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

function validateCastVoice01(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['CAST-VOICE-01 must be a plain object'] };
  const expectedTokens = {
    'local fist': 'UNRESOLVED',
    Vadam: 'UNRESOLVED',
    'She-Raw': 'CANONICAL_SINGLE_IDENTITY',
    'She Raw': 'SPOKEN_VARIANT_OF_SHE-RAW',
    Mabeea: 'CANONICAL_SINGLE_IDENTITY',
    Mabea: 'SURFACE_VARIANT_OF_MABEEA',
    'full perspective': 'ACTIVE_ACCEPTED_THIRD_PERSON_CAMERA',
    ASMR: 'LOCAL_NONSEMANTIC_LAYER',
    'additional quotes': 'UNRESOLVED_SUGGESTED_CORRECTION'
  };
  if (value.profileId !== 'CAST-VOICE-01' || canonicalJson(value.tokens) !== canonicalJson(expectedTokens)) errors.push('CAST-VOICE-01 protected token ledger mismatch');
  requireText(value.sourceText, 'cast.sourceText', errors);
  requireSha(value.sourceTextHash, 'cast.sourceTextHash', errors);
  for (const token of Object.keys(expectedTokens)) if (typeof value.sourceText === 'string' && !value.sourceText.includes(token)) errors.push(`cast.sourceText missing exact token ${token}`);
  if (typeof value.sourceText === 'string' && sha256(value.sourceText) !== value.sourceTextHash) errors.push('cast.sourceTextHash mismatch');
  if (value.normalizationAllowed !== false || value.additionalQuotesCorrectionApplied !== false || value.additionalQuotesSuggestedCorrection !== 'additional quotas') errors.push('CAST-VOICE-01 must preserve exact unresolved tokens without applying suggested correction');
  if (!isRecord(value.roles) || value.roles.Drew !== 'player_final_author' || value.roles.Adam !== 'narrator_dm_interface_state_owner' || value.roles.Stanley !== 'reference_lens_only' || value.roles.Venice !== 'chatgpt_cognition_mobile_voice') errors.push('CAST-VOICE-01 role contract mismatch');
  return { ok: errors.length === 0, errors };
}

module.exports = {
  CONTROL_PHASES,
  ASSEMBLY_KINDS,
  FAILURE_DEGRADATION,
  CACHE_RECEIPT_KINDS,
  actuatorKey,
  FLOW_STATES,
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
  validateLocalMultitaskPlan,
  validateCastVoice01
};

