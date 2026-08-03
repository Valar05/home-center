import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

process.env.HOME_CENTER_GEMINI_MAX_RETRIES = '0';
const require = createRequire(import.meta.url);
const policy = require('../functions/voice_tier_policy.js');
const gemini = require('../functions/gemini_speech_provider.js');
const {renderRecipe, resolveSpeechProfile} = require('../functions/audio_render_service.js');

const config = policy.loadVoiceTierConfig({});
const publicPolicy = policy.publicPolicy(config);
assert.equal(publicPolicy.tiers.utility.provider, 'cartesia');
assert.equal(publicPolicy.tiers.utility.modelId, 'sonic-3.5');
assert.equal(publicPolicy.tiers.draft.modelId, gemini.GEMINI_FLASH_TTS_MODEL);
assert.equal(publicPolicy.tiers.canon.modelId, gemini.GEMINI_PRO_TTS_MODEL);
assert.equal(policy.requestedTier({useCase: 'captions'}, config), 'utility');
assert.equal(policy.requestedTier({useCase: 'ordinary_dialogue'}, config), 'draft');
assert.equal(policy.requestedTier({useCase: 'final_performance'}, config), 'canon');
assert.deepEqual(policy.downwardRoutes('canon', config).map((route) => route.tier), ['canon', 'draft', 'utility']);
assert.equal(policy.isQuotaError({status: 429}), true);
assert.equal(policy.isQuotaError({status: 503, failureKind: 'provider_unavailable'}), false);

const canon = policy.primaryRoute('canon', config);
const draft = policy.primaryRoute('draft', config);
const utility = policy.primaryRoute('utility', config);
const locks = policy.acceptedLocks({acceptedVoice: true, lockDirection: true, voiceName: 'Kore', direction: 'Restrained and urgent.'});
assert.deepEqual(policy.routePreservesLocks(canon, draft, locks), {ok: true});
assert.equal(policy.routePreservesLocks(canon, utility, locks).ok, false);
assert.equal(policy.tierReceipt({requested: 'canon', rendered: 'draft', config}).degraded, true);
assert.equal(policy.tierReceipt({requested: 'canon', rendered: 'draft', config}).canon, false);
assert.equal(policy.tierReceipt({requested: 'canon', rendered: 'canon', config}).canon, true);
const override = JSON.parse(JSON.stringify(policy.DEFAULT_CONFIG));
override.providers.cartesia_utility.configuredMarginalUsdPerSecond = 0.01;
override.providers.gemini_flash.configuredMarginalUsdPerSecond = 0.001;
const overriddenConfig = policy.loadVoiceTierConfig({HOME_CENTER_VOICE_TIER_CONFIG_JSON: JSON.stringify(override)});
assert.equal(policy.primaryRoute('utility', overriddenConfig).provider, 'gemini');

const legacy = resolveSpeechProfile({op: 'speech', character: 'Isaac', text: 'Legacy line.'}, {speechDefaults: {}});
assert.equal(legacy.voiceTier, '');
assert.equal(legacy.provider, 'cartesia');
const directed = resolveSpeechProfile({op: 'speech', useCase: 'dialogue', voiceName: 'Kore', direction: 'Low and exact.', text: 'Tiered line.'}, {speechDefaults: {}});
assert.equal(directed.voiceTier, 'draft');
assert.equal(directed.provider, 'gemini');
assert.equal(directed.modelId, gemini.GEMINI_FLASH_TTS_MODEL);

const pcm = Buffer.alloc(gemini.GEMINI_SAMPLE_RATE * 2 / 4);
for (let i = 0; i < pcm.length; i += 2) pcm.writeInt16LE(i % 400 === 0 ? 12000 : 1000, i);
const calls = [];
const previousFetch = global.fetch;
global.fetch = async (_url, init = {}) => {
  const body = JSON.parse(init.body || '{}');
  calls.push(body.model);
  if (body.model === gemini.GEMINI_PRO_TTS_MODEL) {
    return {ok: false, status: 429, headers: {get: () => '0'}, text: async () => 'quota exhausted'};
  }
  return {ok: true, status: 200, headers: {get: () => null}, json: async () => ({output_audio: {data: pcm.toString('base64'), mime_type: 'audio/l16', sample_rate: 24000, channels: 1}, usage: {total_input_tokens: 10, total_output_tokens: 20}}), text: async () => ''};
};
try {
  const rendered = await renderRecipe({
    sampleRate: 24000,
    graph: [{id: 'canon_take', op: 'speech', voiceTier: 'canon', voiceName: 'Kore', acceptedVoice: true, lockDirection: true, direction: 'Restrained and urgent.', text: 'The gate holds.'}],
    final: 'canon_take',
    outputs: [{name: 'canon.wav', format: 'wav', clip: 'canon_take'}],
  }, {}, {geminiApiKey: () => 'test-key'});
  assert.deepEqual(calls, [gemini.GEMINI_PRO_TTS_MODEL, gemini.GEMINI_FLASH_TTS_MODEL]);
  assert.equal(rendered.speechProvenance[0].requestedTier, 'canon');
  assert.equal(rendered.speechProvenance[0].renderedTier, 'draft');
  assert.equal(rendered.speechProvenance[0].degraded, true);
  assert.equal(rendered.speechProvenance[0].canon, false);
  assert.equal(rendered.speechProvenance[0].modelId, gemini.GEMINI_FLASH_TTS_MODEL);
  assert.equal(rendered.voiceTierReceipts[0].attempts[0].quotaError, true);
  assert.equal(rendered.voiceTierReceipts[0].attempts[1].status, 'success');
} finally {
  global.fetch = previousFetch;
}

const refusalCalls = [];
global.fetch = async (_url, init = {}) => {
  const body = JSON.parse(init.body || '{}');
  refusalCalls.push(body.model);
  return {ok: false, status: 403, headers: {get: () => null}, text: async () => 'provider refused'};
};
try {
  await assert.rejects(() => renderRecipe({sampleRate: 24000, graph: [{id: 'canon_refused', op: 'speech', voiceTier: 'canon', voiceName: 'Kore', text: 'Do not substitute.'}], final: 'canon_refused'}, {}, {geminiApiKey: () => 'test-key'}), (error) => error.failureKind === 'gemini_provider_refused');
  assert.deepEqual(refusalCalls, [gemini.GEMINI_PRO_TTS_MODEL]);
} finally {
  global.fetch = previousFetch;
}

console.log('Home Center voice tier contract: OK');
