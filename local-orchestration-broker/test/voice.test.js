'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { hash, audioLease } = require('./helpers');
const { sha256 } = require('../src/contracts');
const { CONTROL_PHASES, FAILURE_DEGRADATION, validateControlYield, validateNarrationRoute, validateAsmrProjection, validateAssembly, validatePlayback, validateFailureContinuation, audioCacheKeyPayload, validateAudioCacheEntry, validateAudioCuePalette, validateAudioCacheReceipt, validateAudioCacheMiss, validateLocalMultitaskPlan } = require('../src/voice');

const cachePolicy = { byteBudget: 65_536, maxEntries: 16, eviction: 'LRU', expiryRequired: true, supersessionRequired: true, backgroundRefill: true };
function cachedEntry(overrides = {}) {
  const entry = { kind: 'local_audio.cache', cueId: 'soft-click', profileId: 'asmr-neutral', version: '1', contentSha256: hash('8'), byteLength: 4096, preRendered: true, buffered: true, bytesVerified: true, decodedReady: true, semanticEffect: false, createdAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T11:00:00Z', supersededBy: null, ...overrides };
  entry.cacheKey = sha256(audioCacheKeyPayload(entry));
  return entry;
}

test('voice-to-local control yield has exactly three fenced phases', () => {
  assert.deepEqual(CONTROL_PHASES, ['YIELD_LOCAL', 'LOCAL_OWNS_ACTUATOR', 'RETURN_TO_VOICE']);
  const base = { yieldId: 'y1', commissionId: 'c1', commissionHash: hash('a'), queueRevision: 'r1', laneId: 'lane-1', actuatorId: 'local_playback', observedAt: '2026-08-11T10:00:00Z' };
  assert.equal(validateControlYield({ ...base, phase: 'YIELD_LOCAL', from: 'voice_aperture', to: 'local_broker' }).ok, true);
  assert.equal(validateControlYield({ ...base, phase: 'LOCAL_OWNS_ACTUATOR', from: 'local_broker', to: 'local_playback' }).ok, true);
  assert.equal(validateControlYield({ ...base, phase: 'RETURN_TO_VOICE', from: 'local_playback', to: 'voice_aperture' }).ok, true);
  assert.equal(validateControlYield({ ...base, phase: 'YIELD_LOCAL', from: 'voice_aperture', to: 'speakers' }).ok, false);
});

test('ChatGPT Voice carries exact local Venice while Adam remains interface narrator', () => {
  const route = { routeId: 'v1', provider: 'venice_local', purpose: 'LIVE_VENICE_RELAY', carrier: 'chatgpt_voice', speaker: 'Venice', interfaceNarrator: 'Adam', sourceReceiptSha256: hash('b'), exactWords: true, allowImpersonation: false, textMirror: 'Venice: exact local words' };
  assert.equal(validateNarrationRoute(route).ok, true);
  assert.equal(validateNarrationRoute({ ...route, sourceReceiptSha256: undefined }).ok, false);
  assert.equal(validateNarrationRoute({ ...route, speaker: 'Adam' }).ok, false);
  assert.equal(validateNarrationRoute({ ...route, allowImpersonation: true }).ok, false);
});

test('Piper is separately commissioned durable personal-touch audio with no automation', () => {
  const route = { routeId: 'p1', provider: 'piper', purpose: 'PERSONAL_TOUCH_DURABLE_AUDIO', separatelyCommissioned: true, autoSynthesize: false, autoPlayback: false, artifactDigest: hash('c'), textMirror: 'crafted line' };
  assert.equal(validateNarrationRoute(route).ok, true);
  assert.equal(validateNarrationRoute({ ...route, purpose: 'ROUTINE_NARRATION' }).ok, false);
  assert.equal(validateNarrationRoute({ ...route, autoPlayback: true }).ok, false);
});

test('Gemini and Orus are polished-artifact-only', () => {
  for (const provider of ['gemini', 'orus']) {
    const route = { routeId: provider, provider, purpose: 'POLISHED_ARTIFACT', separatelyCommissioned: true, artifactDigest: hash('d'), textMirror: 'artifact text' };
    assert.equal(validateNarrationRoute(route).ok, true);
    assert.equal(validateNarrationRoute({ ...route, purpose: 'LIVE_VENICE_RELAY' }).ok, false);
    assert.equal(validateNarrationRoute({ ...route, separatelyCommissioned: false }).ok, false);
  }
});

test('local assembly and playback remain separate typed states', () => {
  const assembly = { assemblyId: 'a1', kind: 'NARRATION_AND_ASMR', inputRefs: ['artifact://voice'], mediaType: 'audio/wav', artifactRef: 'artifact://assembly', artifactSha256: hash('e'), local: true, played: false };
  assert.equal(validateAssembly(assembly).ok, true);
  const playback = { playbackId: 'play-1', kind: 'LOCAL_PLAYBACK', assemblyId: 'a1', assemblySha256: hash('e'), deviceId: 'speakers-1', audioLease: audioLease() };
  assert.equal(validatePlayback(playback).ok, true);
  assert.equal(validateAssembly({ ...assembly, played: true }).ok, false);
  assert.equal(validatePlayback({ ...playback, audioLease: undefined }).ok, false);
});

test('dynamic ASMR is optional, muteable, text-mirrored, nonsemantic, and leased', () => {
  const projection = { projectionId: 'asmr-1', eventType: 'soft-click', textMirror: '[soft click]', optional: true, muteable: true, semanticEffect: false, audioLease: audioLease() };
  assert.equal(validateAsmrProjection(projection).ok, true);
  assert.equal(validateAsmrProjection({ ...projection, semanticEffect: true }).ok, false);
  assert.equal(validateAsmrProjection({ ...projection, muteable: false }).ok, false);
});

test('never fail fully degradation parks one lane and keeps independent work rolling', () => {
  for (const [failureKind, policy] of Object.entries(FAILURE_DEGRADATION)) {
    const value = { failureKind, failedLaneId: 'failed-lane', independentLaneIds: ['independent-lane'], failedLaneState: 'PARKED', independentLaneState: 'REALLOCATED', continuation: policy.continuation, claimedSuccess: false, safetyGatesFailClosed: true };
    assert.equal(validateFailureContinuation(value).ok, true, failureKind);
    assert.equal(validateFailureContinuation({ ...value, claimedSuccess: true }).ok, false);
    assert.equal(validateFailureContinuation({ ...value, failedLaneState: 'COMPLETED_PRESERVED' }).ok, false);
  }
});

test('local audio cache is hash-pinned, decoded-ready, bounded, expiring, superseding, and LRU', () => {
  const entry = cachedEntry();
  assert.equal(validateAudioCacheEntry(entry, cachePolicy).ok, true);
  assert.equal(validateAudioCacheEntry({ ...entry, contentSha256: hash('9') }, cachePolicy).ok, false);
  assert.equal(validateAudioCacheEntry({ ...entry, decodedReady: false }, cachePolicy).ok, false);
  assert.equal(validateAudioCacheEntry({ ...entry, byteLength: 65_537 }, cachePolicy).ok, false);
  assert.equal(validateAudioCacheEntry(entry, { ...cachePolicy, eviction: 'FIFO' }).ok, false);
  assert.equal(validateAudioCuePalette([entry], cachePolicy, '2026-08-11T10:30:00Z').ok, true);
  assert.equal(validateAudioCuePalette([entry], { ...cachePolicy, maxEntries: 0 }, '2026-08-11T10:30:00Z').ok, false);
  assert.equal(validateAudioCuePalette([cachedEntry({ expiresAt: '2026-08-11T10:20:00Z' })], cachePolicy, '2026-08-11T10:30:00Z').ok, false);
});

test('cache hit, playback start, and refill queue are separate receipts', () => {
  const base = { receiptId: 'cache-r1', cacheKey: hash('a'), observedAt: '2026-08-11T10:01:00Z' };
  const entry = cachedEntry();
  const useBase = { ...base, cacheKey: entry.cacheKey };
  assert.equal(validateAudioCacheReceipt({ ...useBase, kind: 'CACHE_HIT', playStarted: false }, { entry, policy: cachePolicy }).ok, true);
  assert.equal(validateAudioCacheReceipt({ ...useBase, kind: 'CACHE_HIT', playStarted: true }, { entry, policy: cachePolicy }).ok, false);
  assert.equal(validateAudioCacheReceipt({ ...useBase, kind: 'PLAY_STARTED', audioLease: audioLease() }, { entry, policy: cachePolicy }).ok, true);
  assert.equal(validateAudioCacheReceipt({ ...useBase, kind: 'PLAY_STARTED', audioLease: audioLease() }).ok, false);
  assert.equal(validateAudioCacheReceipt({ ...base, kind: 'REFILL_QUEUED', background: true }).ok, true);
});

test('cache miss skips cue and keeps live Voice/text/local work without stale replay or Gemini fallback', () => {
  const miss = { cacheKey: hash('b'), cueSkipped: true, liveVoiceContinues: true, textContinues: true, refillQueued: true, refillMode: 'BACKGROUND', staleSemanticReplay: false, geminiFallback: false, claimedPlayback: false };
  assert.equal(validateAudioCacheMiss(miss).ok, true);
  assert.equal(validateAudioCacheMiss({ ...miss, cueSkipped: false }).ok, false);
  assert.equal(validateAudioCacheMiss({ ...miss, geminiFallback: true }).ok, false);
  assert.equal(validateAudioCacheMiss({ ...miss, staleSemanticReplay: true }).ok, false);
});

test('local multitask means one supervisory Voice over many fenced local lanes', () => {
  const plan = { kind: 'LOCAL_MULTITASK_PLAN', definition: 'ONE_SUPERVISORY_VOICE_MANY_FENCED_LOCAL_LANES', planId: 'm1', commissionHash: hash('c'), queueRevision: 'r1', stateOwner: 'Adam', voiceOwnsActuator: false, continueIndependentLanes: true, executionBudget: 'LOCAL_OR_INCLUDED_ONLY', lanes: [
    { laneId: 'audio', owner: 'worker-a', isolatedPath: '/isolated/audio', branch: 'agent/audio', operations: ['assemble'], materialTransitionBudget: 1 },
    { laneId: 'broker', owner: 'worker-b', isolatedPath: '/isolated/broker', branch: 'agent/broker', operations: ['validate'], materialTransitionBudget: 1 }
  ] };
  assert.equal(validateLocalMultitaskPlan(plan).ok, true);
  assert.equal(validateLocalMultitaskPlan({ ...plan, voiceOwnsActuator: true }).ok, false);
  assert.equal(validateLocalMultitaskPlan({ ...plan, lanes: [plan.lanes[0], { ...plan.lanes[1], isolatedPath: plan.lanes[0].isolatedPath }] }).ok, false);
  assert.equal(validateLocalMultitaskPlan({ ...plan, lanes: [{ ...plan.lanes[0], materialTransitionBudget: 2 }] }).ok, false);
});
