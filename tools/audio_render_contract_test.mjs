import assert from 'node:assert/strict';
import {Readable} from 'node:stream';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import fs from 'node:fs';

process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
const require = createRequire(import.meta.url);
const homeCenterSource = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
assert(homeCenterSource.includes("'audio.render'"), 'operation registry must expose audio.render');
assert(homeCenterSource.includes("'audio.render_artifacts'"), 'operation registry must expose audio.render_artifacts readback verifier');
assert(homeCenterSource.includes('renderAudioOperation({google, admin, auth, user'), 'drive_operation must dispatch audio.render directly');
assert(!/audio\.render[\s\S]{0,500}commandCenterOperationRunOperation/.test(homeCenterSource), 'audio.render must not route through Command Center');
assert(homeCenterSource.includes('structured inline-playable MCP audio block'), 'registry must advertise inline playable audio');
assert(homeCenterSource.includes('speech and audition nodes'), 'registry must advertise speech and audition recipe nodes');
assert(homeCenterSource.includes("requireCreditGatedEmail(user && user.email, 'audio.render')"), 'audio.render credit-capable path must be approved-account gated');

const {driveOperationRunOperation, createHomeCenterMcpServer} = require('../functions/home_center_mcp.js');
const cartesiaPitchShift = require('../functions/cartesia_pitch_shift.js');
const {sanitizeRecipeText, renderRecipe, materializeSources, resolveSpeechProfile, CARTESIA_SUPPORTED_EMOTIONS, primitives} = require('../functions/audio_render_service.js');

const {tone, noise, silence, trim, concat, loop, fade, crossfade, gain, normalizePeak, normalizeLufs, pan, pitchShift, timeStretch, reverse, biquadLike, compress, limit, distort, delay, reverb, envelope, timeline, duck, resample, toChannels, encodeWav, decodeWav, waveformPng, spectrogramPng, measure} = primitives;

function sha256(buffer) { return createHash('sha256').update(buffer).digest('hex'); }

function pcm16Tone(sampleRate = 16000, duration = 0.24, frequency = 330) {
  const frames = Math.round(sampleRate * duration);
  const out = Buffer.alloc(frames * 2);
  for (let i = 0; i < frames; i++) {
    const sample = Math.sin(2 * Math.PI * frequency * i / sampleRate) * 0.32;
    out.writeInt16LE(Math.round(sample * 32767), i * 2);
  }
  return out;
}

const cartesiaCalls = [];
globalThis.fetch = async (url, options = {}) => {
  assert.ok(String(url).includes('/tts/bytes'), 'audio.render speech tests must call Cartesia TTS bytes only');
  const body = JSON.parse(String(options.body || '{}'));
  cartesiaCalls.push({url: String(url), body});
  const pcm = pcm16Tone(body.output_format && body.output_format.sample_rate || 16000, 0.24 + cartesiaCalls.length * 0.01, 300 + cartesiaCalls.length * 25);
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
const wav = encodeWav(toChannels(base, 2));
assert.equal(wav.slice(0,4).toString('ascii'), 'RIFF');
assert.equal(decodeWav(wav).channelCount, 2);
assert.equal(waveformPng(base).slice(1,4).toString('ascii'), 'PNG');
assert.equal(spectrogramPng(base).slice(1,4).toString('ascii'), 'PNG');

const inlineSource = wav.toString('base64');
const materialized = await materializeSources({sources: {dialogue: {contentBase64: inlineSource, mimeType: 'audio/wav', sha256: sha256(wav)}}});
assert.equal(materialized.dialogue.sha256, sha256(wav));
assert.equal(materialized.dialogue.decoded.channelCount, 2);
await assert.rejects(() => materializeSources({sources: {bad: {contentBase64: inlineSource, mimeType: 'audio/wav', sha256: '0'.repeat(64)}}}), /sha256 mismatch/);
await assert.rejects(() => materializeSources({sources: {net: {ref: 'https://example.com/a.wav'}}}), /Unsupported source ref provider/);


const isaacProfile = resolveSpeechProfile({character: 'Isaac', emotion: 'hurt'});
assert.equal(isaacProfile.voiceName, 'Clyde - Calm Narrator');
assert.equal(isaacProfile.voiceId, '98a34ef2-2140-4c28-9c71-663dc4dd7022');
assert.equal(isaacProfile.modelId, 'sonic-3.5');
assert.equal(isaacProfile.speed, 0.97);
assert.equal(isaacProfile.pitchSemitones, -1.5);
assert.ok(CARTESIA_SUPPORTED_EMOTIONS.includes('rejected'));
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
  google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'},
  args: {operation: 'audio.render', args: {scriptText: JSON.stringify(recipe), requestId: 'audio-render-contract-001', parentFolderId: 'folder12345', settings: {timeoutMs: 20000}}},
});
assert.equal(routed.operation, 'audio.render');
assert.equal(routed.completed, true);
assert.equal(routed.result.ok, true);
assert.equal(routed.result.status, 'completed');
assert.equal(routed.result.noAgentRuntime, true);
assert.equal(routed.result.noCommandCenter, true);
assert.equal(routed.result.outputs.length, 4);
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
const replay = await driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, args: {operation: 'audio.render', args: {scriptText: JSON.stringify(recipe), requestId: 'audio-render-contract-001', parentFolderId: 'folder12345', settings: {timeoutMs: 20000}}}});
assert.equal(replay.result.idempotent, true);
await assert.rejects(() => driveOperationRunOperation({google: fakeGoogle(), admin, auth: {}, user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'}, args: {operation: 'audio.render', args: {scriptText: JSON.stringify({...recipe, seed: 'other'}), requestId: 'audio-render-contract-001', settings: {timeoutMs: 20000}}}}), /idempotencyKey was reused/);

const server = createHomeCenterMcpServer({google: fakeGoogle(), admin, googleClientId: () => '', googleClientSecret: () => '', cartesiaApiKey: () => ''});
assert.ok(server._registeredTools.drive_operation, 'stable drive_operation tool remains registered');
assert.ok(!server._registeredTools.audio_render, 'audio.render must not require a new top-level MCP tool');
console.log('Home Center audio.render contract: OK');
