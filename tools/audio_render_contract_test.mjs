import assert from 'node:assert/strict';
import {Readable} from 'node:stream';
import {EventEmitter} from 'node:events';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import fs from 'node:fs';

process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE = '1';
process.env.HOME_CENTER_GENERATED_BUCKET = 'home-center-generated';
process.env.HOME_CENTER_AUDIO_RENDER_TEST_FAKE_OGG = '1';
const require = createRequire(import.meta.url);
const homeCenterSource = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
assert(homeCenterSource.includes("'audio.render'"), 'operation registry must expose audio.render');
assert(homeCenterSource.includes("'audio.render_artifacts'"), 'operation registry must expose audio.render_artifacts readback verifier');
assert(homeCenterSource.includes("'audio.render_register'"), 'operation registry must expose receipt-only Reader registration recovery');
assert(homeCenterSource.includes('renderAudioOperation({google, admin, auth, user'), 'drive_operation must dispatch audio.render directly');
assert(!/audio\.render[\s\S]{0,500}commandCenterOperationRunOperation/.test(homeCenterSource), 'audio.render must not route through Command Center');
assert(homeCenterSource.includes('authenticated Audio Reader discovery'), 'registry must advertise authenticated Reader playback delivery');
assert(homeCenterSource.includes('speech_sequence, and block_mix nodes'), 'registry must advertise speech, speech_sequence, and block_mix recipe nodes');
assert(homeCenterSource.includes("'audio.render_status'"), 'operation registry must expose audio.render_status recovery');
assert(homeCenterSource.includes('speech_sequence'), 'registry must advertise speech_sequence recipe nodes');
assert(homeCenterSource.includes("requireCreditGatedEmail(user && user.email, 'audio.render')"), 'audio.render credit-capable path must be approved-account gated');

const {driveOperationRunOperation, createHomeCenterMcpServer} = require('../functions/home_center_mcp.js');
const {uploadGeneratedArtifact} = require('../functions/artifact_bucket.js');
const cartesiaPitchShift = require('../functions/cartesia_pitch_shift.js');
const {sanitizeRecipeText, renderRecipe, executeAudioRenderJob, materializeSources, resolveSpeechProfile, CARTESIA_SUPPORTED_EMOTIONS, limits, primitives} = require('../functions/audio_render_service.js');

const {tone, noise, silence, trim, concat, loop, fade, crossfade, gain, normalizePeak, normalizeLufs, pan, pitchShift, timeStretch, reverse, biquadLike, compress, limit, distort, delay, reverb, envelope, timeline, blockMix, duck, resample, toChannels, encodeWav, decodeWav, waveformPng, spectrogramPng, measure, waitForWritableDrain} = primitives;

assert.ok(limits.MAX_SOURCE_BYTES >= limits.MAX_WAV_OUTPUT_BYTES, 'downstream source ceiling must accept every reusable WAV checkpoint the renderer can create');

{
  const blockedInput = new EventEmitter();
  const encoderTimeout = new Promise((_, reject) => setImmediate(() => reject(Object.assign(new Error('test encoder timeout'), {failureKind: 'audio_render_encoder_timeout'}))));
  await assert.rejects(
    () => waitForWritableDrain(blockedInput, encoderTimeout),
    (err) => err && err.failureKind === 'audio_render_encoder_timeout',
    'blocked encoder input must terminate when the encoder timeout fires instead of waiting forever for drain',
  );
}

function sha256(buffer) { return createHash('sha256').update(buffer).digest('hex'); }

function pcm16Tone(sampleRate = 16000, duration = 0.24, frequency = 330, gain = 0.32) {
  const frames = Math.round(sampleRate * duration);
  const out = Buffer.alloc(frames * 2);
  for (let i = 0; i < frames; i++) {
    const sample = Math.max(-0.98, Math.min(0.98, Math.sin(2 * Math.PI * frequency * i / sampleRate) * gain));
    out.writeInt16LE(Math.round(sample * 32767), i * 2);
  }
  return out;
}

const cartesiaCalls = [];
const cartesiaCompletions = [];
let activeProviderCalls = 0;
let maxActiveProviderCalls = 0;
globalThis.__cartesiaFake = {durationSeconds: null, delayMs: 0, gain: 0.32};
globalThis.fetch = async (url, options = {}) => {
  assert.ok(String(url).includes('/tts/bytes'), 'audio.render speech tests must call Cartesia TTS bytes only');
  const body = JSON.parse(String(options.body || '{}'));
  const indexMatch = String(body.transcript || '').match(/segment-(\d+)/);
  const segmentIndex = indexMatch ? Number(indexMatch[1]) : cartesiaCalls.length;
  const callIndex = cartesiaCalls.length;
  activeProviderCalls += 1;
  maxActiveProviderCalls = Math.max(maxActiveProviderCalls, activeProviderCalls);
  cartesiaCalls.push({url: String(url), body, callIndex, segmentIndex, activeAtStart: activeProviderCalls});
  const delay = globalThis.__cartesiaFake.delayMs ? Math.max(0, globalThis.__cartesiaFake.delayMs + ((119 - segmentIndex) % 5)) : 0;
  if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
  const duration = globalThis.__cartesiaFake.durationSeconds || (0.24 + cartesiaCalls.length * 0.01);
  const pcm = pcm16Tone(body.output_format && body.output_format.sample_rate || 16000, duration, 300 + segmentIndex * 3, globalThis.__cartesiaFake.gain || 0.32);
  cartesiaCompletions.push(segmentIndex);
  activeProviderCalls -= 1;
  return {ok: true, status: 200, text: async () => '', arrayBuffer: async () => pcm.buffer.slice(pcm.byteOffset, pcm.byteOffset + pcm.byteLength)};
};
const pitchCalls = [];
cartesiaPitchShift.setPitchShiftImplementationForTest(async (pcm, options = {}) => {
  pitchCalls.push({...options, byteCount: pcm.length});
  return {pcm, bypassed: false, processor: 'test-pitch', pitchScale: Math.pow(2, options.pitchSemitones / 12), inputFrames: pcm.length / 2, outputFrames: pcm.length / 2, durationRatio: 1};
});
async function readableToBuffer(readable) {
  const chunks = [];
  for await (const chunk of readable) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  return Buffer.concat(chunks);
}

const stores = new Map();
const files = new Map();
let createCalls = 0;
function collectionStore(name) { if (!stores.has(name)) stores.set(name, new Map()); return stores.get(name); }
function fakeAdmin() {
  function firestore() {
    return {collection(name) {
      const store = collectionStore(name);
      return {
        doc(id) { return {async get() { return {exists: store.has(id), data: () => store.get(id)}; }, async set(value) { store.set(id, value); }}; },
        async add(value) { const id = 'add-' + (store.size + 1); store.set(id, value); return {id}; },
        where() { return {limit() { return {async get() { return {empty: true, docs: []}; }}; }}; },
      };
    }};
  }
  firestore.FieldValue = {serverTimestamp: () => 'server-timestamp'};
  return {firestore};
}
function fakeGoogle() {
  return {drive() { return {files: {
    async create({requestBody, media}) {
      assert.ok(media.body instanceof Readable);
      const id = 'audioFile' + (++createCalls);
      const bytes = await readableToBuffer(media.body);
      const metadata = {id, name: requestBody.name, mimeType: requestBody.mimeType, webViewLink: 'https://drive.google.com/file/d/' + id + '/view', parents: requestBody.parents || ['root']};
      files.set(id, {metadata, bytes});
      return {data: metadata};
    },
    async get(args) {
      const stored = files.get(args.fileId);
      assert.ok(stored, 'missing fake file ' + args.fileId);
      if (args.alt === 'media') return {data: stored.bytes.buffer.slice(stored.bytes.byteOffset, stored.bytes.byteOffset + stored.bytes.byteLength)};
      return {data: stored.metadata};
    },
  }}; }};
}

assert.throws(() => sanitizeRecipeText('fetch("https://example.com")'), /declarative JSON recipes only/);
assert.throws(() => sanitizeRecipeText('{bad json'), /valid JSON/);

const sampleRate = 16000;
const base = tone({frequency: 440, duration: 0.2, sampleRate, channels: 1, gain: 0.3});
assert.equal(base.sampleRate, sampleRate);
assert.equal(base.channelCount, 1);
assert.equal(silence({duration: 0.1, sampleRate, channels: 2}).channelCount, 2);
assert.equal(noise({duration: 0.1, sampleRate, seed: 'a'}).frames, 1600);
assert.equal(trim(base, 0, 0.1).frames, 1600);
assert.equal(concat([base, base]).frames, base.frames * 2);
assert.equal(loop(base, 0.5).frames, 8000);
assert.ok(measure(fade(base, 0.05, 'in')).peak <= measure(base).peak + 1e-6);
assert.ok(crossfade(base, base, 0.02).frames < base.frames * 2);
assert.ok(measure(gain(base, -6)).peak < measure(base).peak);
assert.ok(measure(normalizePeak(base, -3)).peak > measure(base).peak);
assert.ok(Number.isFinite(measure(normalizeLufs(base, -20)).integratedLufs));
assert.equal(pan(base, -0.2).channelCount, 2);
assert.equal(toChannels(base, 2).channelCount, 2);
assert.equal(resample(base, 8000).sampleRate, 8000);
assert.equal(reverse(base).frames, base.frames);
assert.equal(biquadLike(base, 'lowpass', 500).frames, base.frames);
assert.equal(compress(base, -20, 2).frames, base.frames);
assert.ok(measure(limit(gain(base, 12), -1)).peak <= 0.9);
assert.equal(distort(base, 3).frames, base.frames);
assert.equal(delay(base, 0.01, 0.2, 0.2).frames, base.frames);
assert.equal(reverb(base, 0.1, 0.2).frames, base.frames);
assert.equal(envelope(base, [{t:0,v:0},{t:0.2,v:1}]).frames, base.frames);
const shifted = pitchShift(base, 12);
assert.ok(Math.abs(shifted.duration - base.duration) < 0.02, 'pitch shift should roughly preserve duration');
assert.ok(Math.abs(timeStretch(base, 1.5).duration - base.duration * 1.5) < 0.05);
const bed = timeline({duration: 0.4, sampleRate, channels: 2, items: [{clip: pan(base, 0), at: 0}, {clip: pan(base, 0.3), at: 0.1, gainDb: -6}]});
assert.equal(bed.channelCount, 2);
assert.equal(duck(bed, base, 5).frames, bed.frames);

const blockProgress = [];
const blockMixed = await blockMix({
  duration: 0.8, sampleRate, channels: 2, blockFrames: 4096,
  items: [
    {clip: noise({duration: 0.08, sampleRate, channels: 1, gain: 0.03, seed: 'block-bed'}), at: 0, duration: 0.8, loop: true, gainDb: -10, fadeIn: 0.05, fadeOut: 0.05, duckClip: base, duckAmountDb: 7},
    {clip: base, at: 0.2, gainDb: -2, pan: 0.15},
  ],
  onProgress: async (progress) => blockProgress.push(progress),
});
assert.equal(blockMixed.frames, Math.round(0.8 * sampleRate));
assert.equal(blockMixed.channelCount, 2);
assert.ok(blockProgress.length > 1, 'block_mix must report bounded progress');
assert.equal(blockProgress.at(-1).framesProcessed, blockMixed.frames);
assert.equal(blockProgress.at(-1).blockIndex, blockProgress.at(-1).blockCount);
assert.equal(measure(blockMixed).silent, false);

const roomProbeSource = tone({frequency: 720, duration: 0.025, sampleRate, channels: 1, gain: 0.18});
const roomProbe = await blockMix({
  duration: 0.8, sampleRate, channels: 2, blockFrames: 4096,
  items: [{
    clip: roomProbeSource,
    at: 0,
    room: {sizeMeters: 24, decaySeconds: 0.62, preDelayMs: 18, wetDb: -8, damping: 0.55, stereoSpread: 0.9, reflectionCount: 10},
  }],
});
let roomTailEnergy = 0;
let roomStereoDelta = 0;
for (let i = Math.round(sampleRate * 0.12); i < roomProbe.frames; i++) {
  roomTailEnergy += Math.abs(roomProbe.channels[0][i]) + Math.abs(roomProbe.channels[1][i]);
  roomStereoDelta += Math.abs(roomProbe.channels[0][i] - roomProbe.channels[1][i]);
}
assert.ok(roomTailEnergy > 0.01, 'room-size reflections must survive after the dry source ends');
assert.ok(roomStereoDelta > 0.001, 'room-size reflections must create deterministic stereo spread');
assert.equal(measure(roomProbe).clippingCount, 0);

const wav = encodeWav(toChannels(base, 2));
assert.equal(wav.slice(0,4).toString('ascii'), 'RIFF');
assert.equal(decodeWav(wav).channelCount, 2);
assert.equal(waveformPng(base).slice(1,4).toString('ascii'), 'PNG');
assert.equal(spectrogramPng(base).slice(1,4).toString('ascii'), 'PNG');

const inlineSource = wav.toString('base64');
const materialized = await materializeSources({sources: {dialogue: {contentBase64: inlineSource, mimeType: 'audio/wav', sha256: sha256(wav)}}});
assert.equal(materialized.dialogue.sha256, sha256(wav));
assert.equal(materialized.dialogue.decoded.channelCount, 2);
const canonicalSource = await uploadGeneratedArtifact({bytes: wav, name: 'canonical-source.wav', mimeType: 'audio/wav', owner: 'drew', project: 'vacation-of-a-lifetime', stage: 'parts', artifactType: 'audio', requestId: 'canonical-source-contract'});
const canonicalMaterialized = await materializeSources({sources: {narration: {ref: canonicalSource.storageRef, sha256: canonicalSource.sha256}}});
assert.equal(canonicalMaterialized.narration.provider, 'generated_artifact_bucket');
assert.equal(canonicalMaterialized.narration.originalRef, canonicalSource.storageRef);
assert.equal(canonicalMaterialized.narration.sha256, canonicalSource.sha256);
assert.equal(canonicalMaterialized.narration.decoded.duration, materialized.dialogue.decoded.duration);
await assert.rejects(() => materializeSources({sources: {forbidden: {ref: 'gs://another-bucket/audio/source.wav'}}}), /canonical generated artifact bucket/);
await assert.rejects(() => materializeSources({sources: {bad: {contentBase64: inlineSource, mimeType: 'audio/wav', sha256: '0'.repeat(64)}}}), /sha256 mismatch/);
await assert.rejects(() => materializeSources({sources: {net: {ref: 'https://example.com/a.wav'}}}), /Unsupported source ref provider/);


const isaacProfile = resolveSpeechProfile({character: 'Isaac', emotion: 'hurt'});
assert.equal(isaacProfile.voiceName, 'Clyde - Calm Narrator');
assert.equal(isaacProfile.voiceId, '98a34ef2-2140-4c28-9c71-663dc4dd7022');
assert.equal(isaacProfile.modelId, 'sonic-3.5');
assert.equal(isaacProfile.speed, 0.97);
assert.equal(isaacProfile.pitchSemitones, -1.5);
assert.ok(CARTESIA_SUPPORTED_EMOTIONS.includes('rejected'));
const stasyaProfile = resolveSpeechProfile({character: 'stasya'});
assert.equal(stasyaProfile.voiceName, 'Milena - Composed Clarifier');
assert.equal(stasyaProfile.voiceId, 'b66b3a19-31b3-401f-8b08-40d46a61e4f1');
assert.equal(stasyaProfile.speed, 1.08);
assert.equal(stasyaProfile.pitchSemitones, 0);
const eveProfile = resolveSpeechProfile({character: 'EVE'});
assert.equal(eveProfile.voiceName, 'Jacqueline - Reassuring Agent');
assert.equal(eveProfile.voiceId, '9626c31c-bec5-4cca-baa8-f8ba9e84c8bc');
assert.equal(eveProfile.speed, 1.0);
assert.equal(eveProfile.pitchSemitones, 0);
const overriddenProfile = resolveSpeechProfile({character: 'isaac', voiceName: 'Override Voice', voiceId: 'voice-123', modelId: 'model-x', speed: 1.1, volume: 0.8, pitchSemitones: -2, emotion: 'distant'});
assert.equal(overriddenProfile.voiceId, 'voice-123');
assert.equal(overriddenProfile.speed, 1.1);
assert.equal(overriddenProfile.volume, 0.8);
assert.equal(overriddenProfile.pitchSemitones, -2);
assert.throws(() => resolveSpeechProfile({character: 'isaac', emotion: 'gleefully_fake'}), /emotion must be one of/);
assert.throws(() => resolveSpeechProfile({character: 'isaac', speed: '1.0'}), /speed must be a finite number/);
assert.throws(() => resolveSpeechProfile({character: 'isaac', volume: 3}), /volume must be a finite number/);

const beforeSpeechCalls = cartesiaCalls.length;
const speechRecipe = {
  seed: 'speech-contract', sampleRate: 16000,
  graph: [
    {id: 'line', op: 'speech', text: '<speak>You cheated on me.</speak>', character: 'Isaac', emotion: 'hurt'},
    {id: 'room', op: 'noise', duration: 1.0, channels: 1, gain: 0.02, seed: 'room', color: 'brown'},
    {id: 'room_ducked', op: 'duck', mix: 'room', keyedBy: 'line', amountDb: 7},
    {id: 'treated', op: 'timeline', duration: 1.2, channels: 2, items: [{clip: 'room_ducked', at: 0, gainDb: -18}, {clip: 'line', at: 0.35, gainDb: -1}]},
    {id: 'final', op: 'limit', clip: 'treated', ceilingDb: -1},
  ],
  final: 'final',
  outputs: [
    {name: 'toast-hurt.wav', format: 'wav', clip: 'line'},
    {name: 'toast-hurt.ogg', format: 'ogg', clip: 'line'},
    {name: 'toast-treated.wav', format: 'wav', clip: 'final'},
  ],
};
const speechRendered = await renderRecipe(speechRecipe, {}, {timeoutMs: 20000, cartesiaApiKey: () => 'test-cartesia-key'});
assert.equal(cartesiaCalls.length, beforeSpeechCalls + 1, 'speech node must call Cartesia exactly once');
assert.equal(cartesiaCalls.at(-1).body.voice.id, '98a34ef2-2140-4c28-9c71-663dc4dd7022');
assert.equal(cartesiaCalls.at(-1).body.model_id, 'sonic-3.5');
assert.deepEqual(cartesiaCalls.at(-1).body.generation_config, {emotion: 'hurt', speed: 0.97});
assert.ok(pitchCalls.some((call) => call.pitchSemitones === -1.5), 'Isaac speech must use canonical pitch processor');
assert.equal(speechRendered.usesCartesia, true);
assert.equal(speechRendered.speechProvenance[0].voiceName, 'Clyde - Calm Narrator');
assert.equal(speechRendered.speechProvenance[0].emotionRequested, 'hurt');
assert.equal(speechRendered.speechProvenance[0].durationRatio, 1);
assert.equal(speechRendered.speechProvenance[0].ssmlCompatible, true);
assert.ok(speechRendered.rendered.find((item) => item.name === 'toast-hurt.ogg'));

const callsBeforeInvalid = cartesiaCalls.length;
await assert.rejects(() => renderRecipe({sampleRate: 16000, graph: [{id: 'bad', op: 'speech', text: 'bad', character: 'isaac', emotion: 'notreal'}], final: 'bad'}, {}, {cartesiaApiKey: () => 'test'}), /emotion must be one of/);
assert.equal(cartesiaCalls.length, callsBeforeInvalid, 'invalid speech controls must fail before provider invocation');
await assert.rejects(() => renderRecipe({sampleRate: 16000, graph: [{id: 'bad', op: 'speech', text: 'bad', character: 'isaac', pitchSemitones: '1'}], final: 'bad'}, {}, {cartesiaApiKey: () => 'test'}), /pitchSemitones must be a finite number/);
assert.equal(cartesiaCalls.length, callsBeforeInvalid, 'invalid pitch must fail before provider invocation');

const auditionStart = cartesiaCalls.length;
const auditionRecipe = {sampleRate: 16000, graph: [{id: 'takes', op: 'audition', text: 'You cheated on me.', character: 'isaac', emotions: ['neutral', 'hurt', 'rejected'], pauseSeconds: 0.1}], final: 'takes', outputs: [{name: 'takes.wav', format: 'wav', clip: 'takes'}, {name: 'take-neutral.wav', format: 'wav', clip: 'takes_neutral'}, {name: 'take-hurt.wav', format: 'wav', clip: 'takes_hurt'}]};
const auditionRendered = await renderRecipe(auditionRecipe, {}, {timeoutMs: 20000, cartesiaApiKey: () => 'test'});
assert.equal(cartesiaCalls.length, auditionStart + 3, 'audition must synthesize each emotion as a separate provider context');
assert.deepEqual(cartesiaCalls.slice(auditionStart).map((call) => call.body.generation_config.emotion), ['neutral', 'hurt', 'rejected']);
assert.equal(auditionRendered.auditionTakes.length, 3);
assert.equal(auditionRendered.rendered.filter((item) => /take-/.test(item.name)).length, 2);


const longStartCalls = cartesiaCalls.length;
const longStartPitchCalls = pitchCalls.length;
const longStartCompletions = cartesiaCompletions.length;
activeProviderCalls = 0;
maxActiveProviderCalls = 0;
globalThis.__cartesiaFake = {durationSeconds: 5, delayMs: 4, gain: 0.92};
const longSegments = Array.from({length: 120}, (_, index) => {
  const mod = index % 3;
  const character = mod === 0 ? 'Stasya' : mod === 1 ? 'Isaac' : 'Eve';
  return {speaker: character, character, emotion: mod === 1 ? 'hurt' : 'neutral', text: `long-form segment-${index} belongs to ${character}.`};
});
const longRecipe = {
  seed: 'long-sequence-contract', sampleRate: 24000,
  graph: [{id: 'scene', op: 'speech_sequence', segments: longSegments, pauseMs: 120, concurrency: 4, master: {limitDb: -1}}],
  final: 'scene',
  outputs: [{name: 'long-sequence.ogg', format: 'ogg', clip: 'scene'}],
};
const longRendered = await renderRecipe(longRecipe, {}, {timeoutMs: 20000, cartesiaApiKey: () => 'test'});
const longCalls = cartesiaCalls.slice(longStartCalls);
assert.equal(longCalls.length, 120, 'speech_sequence must call provider once per segment');
assert.equal(maxActiveProviderCalls, 4, 'speech_sequence must not exceed configured concurrency');
assert.ok(cartesiaCompletions.slice(longStartCompletions).some((value, index, arr) => index > 0 && value < arr[index - 1]), 'fake provider should complete out of order');
assert.equal(longRendered.speechSequences.length, 1);
assert.equal(longRendered.speechSequences[0].segmentCount, 120);
assert.deepEqual(longRendered.speechSequences[0].segments.map((segment) => segment.index), Array.from({length: 120}, (_, i) => i));
assert.equal(longRendered.speechSequences[0].segments[0].speaker, 'Stasya');
assert.equal(longRendered.speechSequences[0].segments[1].speaker, 'Isaac');
assert.equal(longRendered.speechSequences[0].segments[2].speaker, 'Eve');
assert.equal(longRendered.speechSequences[0].segments[0].voiceId, 'b66b3a19-31b3-401f-8b08-40d46a61e4f1');
assert.equal(longRendered.speechSequences[0].segments[1].voiceId, '98a34ef2-2140-4c28-9c71-663dc4dd7022');
assert.equal(longRendered.speechSequences[0].segments[2].voiceId, '9626c31c-bec5-4cca-baa8-f8ba9e84c8bc');
assert.equal(longRendered.finalMetrics.duration > 600, true, 'synthetic final clip must exceed 600 seconds');
assert.equal(longRendered.finalMetrics.clippingCount, 0);
assert.ok(longRendered.finalMetrics.peak <= Math.pow(10, -1 / 20) + 1e-4, 'speech_sequence default limiter should cap peak near -1 dB');
assert.equal(longRendered.rendered.length, 1);
assert.equal(longRendered.rendered[0].mimeType, 'audio/ogg');
assert.equal(pitchCalls.slice(longStartPitchCalls).filter((call) => call.pitchSemitones === -1.5).length, 40, 'Isaac sequence segments must use canonical pitch processor');
globalThis.__cartesiaFake = {durationSeconds: null, delayMs: 0, gain: 0.32};


const blockRecipeProgress = [];
const blockRecipe = {
  seed: 'block-mix-contract', sampleRate: 16000,
  graph: [
    {id: 'dialogue', op: 'tone', frequency: 310, duration: 0.35, channels: 1, gain: 0.24},
    {id: 'air', op: 'noise', duration: 0.06, channels: 1, gain: 0.025, seed: 'air-loop', color: 'pink'},
    {id: 'final', op: 'block_mix', duration: 1.1, channels: 2, blockFrames: 4096, items: [
      {clip: 'air', at: 0, duration: 1.1, loop: true, gainDb: -8, fadeIn: 0.08, fadeOut: 0.08, duckBy: 'dialogue', duckAmountDb: 6},
      {clip: 'dialogue', at: 0.25, gainDb: -1, pan: -0.1}
    ]}
  ],
  final: 'final',
  outputs: [{name: 'block-mix.ogg', format: 'ogg', clip: 'final'}],
};
const blockRenderedA = await renderRecipe(blockRecipe, {}, {timeoutMs: 20000, onRenderProgress: async (progress) => blockRecipeProgress.push(progress)});
const blockRenderedB = await renderRecipe(blockRecipe, {}, {timeoutMs: 20000});
assert.equal(blockRenderedA.rendered[0].sha256, blockRenderedB.rendered[0].sha256, 'block_mix must remain deterministic');
assert.equal(blockRenderedA.finalMetrics.duration, 1.1);
assert.ok(blockRenderedA.phaseTimings.graphElapsedMs >= 0);
assert.ok(blockRecipeProgress.some((progress) => progress.phase === 'block_mixing' && progress.blockIndex === progress.blockCount), 'block_mix DSL must surface terminal block progress');

const recipe = {
  seed: 'contract-seed', sampleRate: 16000,
  graph: [
    {id: 'a', op: 'tone', frequency: 220, duration: 0.3, channels: 1, gain: 0.2},
    {id: 'b', op: 'noise', duration: 0.3, channels: 1, gain: 0.04, seed: 'n'},
    {id: 'mix', op: 'timeline', duration: 0.45, channels: 2, items: [{clip: 'a', at: 0}, {clip: 'b', at: 0.05, gainDb: -6}]},
    {id: 'final', op: 'limit', clip: 'mix', ceilingDb: -1},
  ],
  final: 'final',
  outputs: [
    {name: 'contract.wav', format: 'wav', clip: 'final'},
    {name: 'contract.ogg', format: 'ogg', clip: 'final'},
    {name: 'contract-waveform.png', format: 'waveform_png', clip: 'final'},
    {name: 'contract-spectrogram.png', format: 'spectrogram_png', clip: 'final'},
  ],
};
const renderedA = await renderRecipe(recipe, {}, {timeoutMs: 20000});
const renderedB = await renderRecipe(recipe, {}, {timeoutMs: 20000});
assert.equal(renderedA.rendered[0].sha256, renderedB.rendered[0].sha256, 'seeded WAV render must be deterministic');
assert.equal(renderedA.finalMetrics.silent, false);
assert.equal(renderedA.finalMetrics.clippingCount, 0);
assert.ok(renderedA.rendered.find((item) => item.mimeType === 'audio/ogg').byteCount > 100);

const admin = fakeAdmin();
const routed = await driveOperationRunOperation({
  google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key',
  args: {operation: 'audio.render', args: {scriptText: JSON.stringify(recipe), requestId: 'audio-render-contract-001', parentFolderId: 'folder12345', settings: {timeoutMs: 20000}, waitForCompletion: true}},
});
assert.equal(routed.operation, 'audio.render');
assert.equal(routed.completed, true);
assert.equal(routed.result.ok, true);
assert.equal(routed.result.status, 'completed');
assert.equal(routed.result.noAgentRuntime, true);
assert.equal(routed.result.noCommandCenter, true);
assert.ok(routed.result.phaseTimings.renderRecipeMs >= 0);
assert.ok(routed.result.phaseTimings.totalMs >= routed.result.phaseTimings.renderRecipeMs);
assert.equal(routed.result.outputs.length, 4);
assert.equal(routed.result.artifactStore.primary, 'gcs');
assert.equal(routed.result.artifactStore.bucket, 'home-center-generated');
assert.ok(routed.result.outputs.every((item) => item.durableRef.startsWith('gs://home-center-generated/')));
assert.ok(routed.result.outputs.every((item) => item.storageRef === item.durableRef && item.primaryStore === 'gcs'));
assert.ok(routed.result.outputs.every((item) => item.driveDurableRef.startsWith('drive://')));
assert.ok(routed.result.outputs.every((item) => item.metadata && item.metadata.ownerEmail === 'dclarke1005@gmail.com' && item.metadata.approved === 'false' && item.metadata.humanAcceptance === 'unreviewed'));
assert.equal(routed.result.readerRegistration.authorization.state, 'owner_scoped');
assert.equal(routed.result.readerRegistration.discovery.ok, true);
assert.equal(routed.result.readerRegistration.playback.ok, true);
assert.equal(routed.result.readerRegistration.bytePreservation.unchanged, true);
assert.equal(routed.result.humanAcceptance, 'unreviewed');
assert.ok(routed.result.outputs.every((item) => item.sha256 === item.readbackSha256 && item.byteCount === item.readbackByteCount));
assert.ok(routed._mcpContent.content.some((item) => item.type === 'audio' && item.mimeType === 'audio/ogg'));
assert.equal(collectionStore('driveBridgeAudit').get('audio-render-contract-001').operation, 'audio.render');
const expectedArtifacts = routed.result.outputs.map((item) => ({durableRef: item.durableRef, byteCount: item.byteCount, sha256: item.sha256}));
const inspected = await driveOperationRunOperation({
  google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'},
  args: {operation: 'audio.render_artifacts', args: {artifactRefs: expectedArtifacts.map((item) => item.durableRef), expected: expectedArtifacts, decodeCheck: true}},
});
assert.equal(inspected.operation, 'audio.render_artifacts');
assert.equal(inspected.completed, true);
assert.equal(inspected.result.ok, true);
assert.equal(inspected.result.artifactCount, expectedArtifacts.length);
assert.ok(inspected.result.artifacts.some((item) => item.header.container === 'wav' && item.header.valid));
assert.ok(inspected.result.artifacts.some((item) => item.header.container === 'ogg' && item.header.valid));
assert.ok(inspected.result.artifacts.every((item) => item.sha256Matches && item.byteCountMatches));
assert.equal(inspected.result.decodeCheck, true);
assert.ok(inspected.result.artifacts.filter((item) => /^audio\//.test(item.mimeType)).every((item) => item.decodeCheck && item.decodeCheck.ok));
const mismatch = await driveOperationRunOperation({
  google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'},
  args: {operation: 'audio.render_artifacts', args: {artifactRefs: [expectedArtifacts[0].durableRef], expected: [{...expectedArtifacts[0], sha256: '0'.repeat(64)}]}},
});
assert.equal(mismatch.result.ok, false);
assert.equal(mismatch.result.artifacts[0].sha256Matches, false);
const replay = await driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key', args: {operation: 'audio.render', args: {scriptText: JSON.stringify(recipe), requestId: 'audio-render-contract-001', parentFolderId: 'folder12345', settings: {timeoutMs: 20000}, waitForCompletion: true}}});
assert.equal(replay.result.idempotent, true);
await assert.rejects(() => driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key', args: {operation: 'audio.render', args: {scriptText: JSON.stringify({...recipe, seed: 'other'}), requestId: 'audio-render-contract-001', settings: {timeoutMs: 20000}, waitForCompletion: true}}}), /idempotencyKey was reused/);



function audioHelpers() {
  return {
    createRequestId: (value) => String(value || ''),
    existingAudit: async (_admin, requestId) => collectionStore('driveBridgeAudit').get(requestId) || null,
    auditWrite: async (_admin, entry) => {
      const requestId = String(entry.requestId || '');
      const existing = collectionStore('driveBridgeAudit').get(requestId);
      if (existing && ['success', 'completed'].includes(existing.status)) return {idempotent: true, audit: existing};
      const payload = {...entry, requestId, timestampMs: Date.now(), updatedAtMs: Date.now()};
      collectionStore('driveBridgeAudit').set(requestId, payload);
      return {idempotent: false, audit: payload};
    },
    recordActionAudit: async () => {},
    safeDriveFileId: (value) => value,
  };
}

const providerCallsBeforeRouteLong = cartesiaCalls.length;
const driveWritesBeforeRouteLong = createCalls;
globalThis.__cartesiaFake = {durationSeconds: 5, delayMs: 1, gain: 0.8};
const longArgs = {scriptText: JSON.stringify(longRecipe), requestId: 'audio-render-long-sequence-001', settings: {timeoutMs: 20000, speechConcurrency: 4}, returnInlineAudio: false, publishToDrive: false, disableBackgroundWorker: true};
const routedLong = await driveOperationRunOperation({
  google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key',
  args: {operation: 'audio.render', args: longArgs},
});
assert.equal(routedLong.completed, false, 'long audio.render must return an accepted receipt, not hold the connector open');
assert.equal(routedLong.result.accepted, true);
assert.equal(routedLong.result.status, 'queued');
assert.equal(routedLong.result.inputSha256.length, 64);
assert.deepEqual(routedLong.result.statusOperation, {operation: 'audio.render_status', args: {requestId: 'audio-render-long-sequence-001'}});
assert.equal(cartesiaCalls.length, providerCallsBeforeRouteLong, 'accepted response must not call Cartesia before returning');
assert.equal(createCalls, driveWritesBeforeRouteLong, 'accepted response must not write Drive before returning');
const retryQueued = await driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key', args: {operation: 'audio.render', args: longArgs}});
assert.equal(retryQueued.result.idempotent, true, 'same key/hash retry must attach to queued job');
assert.equal(cartesiaCalls.length, providerCallsBeforeRouteLong, 'queued retry must not call provider');
await assert.rejects(() => driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key', args: {operation: 'audio.render', args: {...longArgs, scriptText: JSON.stringify({...longRecipe, seed: 'changed'})}}}), /idempotencyKey was reused/);
const completedLong = await executeAudioRenderJob({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key', args: longArgs, helpers: audioHelpers()});
assert.equal(completedLong.ok, true);
assert.equal(completedLong.status, 'completed');
assert.equal(completedLong.outputs.length, 1);
assert.equal(completedLong.speech.sequences[0].segmentCount, 120);
assert.equal(cartesiaCalls.length - providerCallsBeforeRouteLong, 120);
assert.equal(createCalls, driveWritesBeforeRouteLong, 'publishToDrive=false must create zero Drive files for audio or manifest');
assert.ok(completedLong.outputs[0].durableRef.startsWith('gs://home-center-generated/audio/dclarke1005-gmail.com/review/'));
assert.equal(completedLong.outputs[0].driveDurableRef, '');
assert.equal(completedLong.outputs[0].chatGptFileRef, null);
assert.equal(completedLong.manifest.driveDurableRef, '');
assert.equal(completedLong.artifactStore.drivePublish, 'disabled');
const completedAudit = collectionStore('driveBridgeAudit').get('audio-render-long-sequence-001');
assert.equal(completedAudit.status, 'completed');
assert.equal(completedAudit.affectedFileIds.length, 0, 'GCS-only render must not record Drive file ids');
assert.equal(completedAudit.affectedStorageRefs.length, 3, 'GCS-only paid render records output, manifest, and reusable speech checkpoint refs');
assert.ok(completedAudit.progress.speechCheckpoint, 'paid render must retain a reusable speech checkpoint');
assert.equal(completedAudit.progress.speechCheckpoint.verified, true);
assert.equal(completedAudit.progress.speechCheckpoint.reusableWithoutProviderCall, true);
assert.ok(completedAudit.progress.speechCheckpoint.durableRef.startsWith('gs://home-center-generated/'));
assert.equal(completedAudit.result.speechCheckpoint.sha256, completedAudit.progress.speechCheckpoint.sha256);
assert.equal(completedAudit.progress.phase, 'completed');
assert.ok(completedAudit.progress.synthesizedTakes >= 120, 'worker must checkpoint individual synthesized takes');
const routedLongExpected = completedLong.outputs.map((item) => ({durableRef: item.durableRef, byteCount: item.byteCount, sha256: item.sha256}));
const routedLongInspect = await driveOperationRunOperation({
  google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'},
  args: {operation: 'audio.render_artifacts', args: {artifactRefs: routedLongExpected.map((item) => item.durableRef), expected: routedLongExpected, decodeCheck: true}},
});
assert.equal(routedLongInspect.result.ok, true);
assert.equal(routedLongInspect.result.artifacts[0].decodeCheck.ok, true);
const providerCallsBeforeReplay = cartesiaCalls.length;
const driveWritesBeforeReplay = createCalls;
const replayLong = await driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, cartesiaApiKey: () => 'test-cartesia-key', args: {operation: 'audio.render', args: longArgs}});
assert.equal(replayLong.result.idempotent, true);
assert.equal(replayLong.result.status, 'completed');
assert.equal(cartesiaCalls.length, providerCallsBeforeReplay, 'idempotent completed replay must not call Cartesia again');
assert.equal(createCalls, driveWritesBeforeReplay, 'idempotent completed replay must not write Drive again');
const statusLong = await driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, args: {operation: 'audio.render_status', args: {requestId: 'audio-render-long-sequence-001'}}});
assert.equal(statusLong.result.status, 'completed');
assert.equal(statusLong.result.result.requestId, 'audio-render-long-sequence-001');
await assert.rejects(() => driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'junewren28@gmail.com', authKind: 'google_oauth_bearer'}, args: {operation: 'audio.render_status', args: {requestId: 'audio-render-long-sequence-001'}}}), /not owned/);
const legacyResult = {...completedAudit.result};
delete legacyResult.readerRegistration;
collectionStore('driveBridgeAudit').set('audio-render-legacy-completed-001', {...completedAudit, requestId: 'audio-render-legacy-completed-001', status: 'completed', result: legacyResult});
const legacyStatus = await driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, args: {operation: 'audio.render_status', args: {requestId: 'audio-render-legacy-completed-001'}}});
assert.equal(legacyStatus.result.status, 'registration_required', 'legacy completion without Reader proof must not remain completed');
const staleAudit = {...completedAudit, status: 'running', result: null, lease: {heartbeatAtMs: Date.now() - 20 * 60 * 1000}, progress: {phase: 'synthesizing', synthesizedTakes: 7, totalTakes: 120}};
collectionStore('driveBridgeAudit').set('audio-render-stale-001', staleAudit);
const staleStatus = await driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, args: {operation: 'audio.render_status', args: {requestId: 'audio-render-stale-001'}}});
assert.equal(staleStatus.result.status, 'needs_reconciliation', 'paid partial work without byte checkpoints must fail closed');
assert.equal(staleStatus.result.progress.recoverySafety.synthesizedTakes, 7);
assert.equal(staleStatus.result.progress.recoverySafety.durableTakeCheckpoints, 0);
assert.equal(staleStatus.result.progress.recoverySafety.paidReplayAllowed, false);
assert.equal(cartesiaCalls.length, providerCallsBeforeReplay, 'stale watchdog must not retry paid synthesis');
globalThis.__cartesiaFake = {durationSeconds: null, delayMs: 0, gain: 0.32};

const server = createHomeCenterMcpServer({google: fakeGoogle(), admin, googleClientId: () => '', googleClientSecret: () => '', cartesiaApiKey: () => ''});
assert.ok(server._registeredTools.drive_operation, 'stable drive_operation tool remains registered');
assert.ok(!server._registeredTools.audio_render, 'audio.render must not require a new top-level MCP tool');
console.log('Home Center audio.render contract: OK');
