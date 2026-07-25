import assert from 'node:assert/strict';
import {Readable} from 'node:stream';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const pitch = require('../functions/cartesia_pitch_shift.js');
const {synthesizeCartesiaAudioArtifactOperation, driveOperationRunOperation} = require('../functions/home_center_mcp.js');

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

function wavDataBytes(wav) {
  assert.equal(wav.slice(0, 4).toString('ascii'), 'RIFF');
  assert.equal(wav.slice(8, 12).toString('ascii'), 'WAVE');
  assert.equal(wav.readUInt16LE(20), 1, 'WAV must be PCM');
  assert.equal(wav.readUInt16LE(22), 1, 'WAV channel count remains mono');
  assert.equal(wav.readUInt16LE(34), 16, 'WAV remains 16-bit PCM');
  return wav.slice(44);
}

function makeTonePcm(freq, sampleRate = 24000, seconds = 1) {
  const frames = Math.floor(sampleRate * seconds);
  const pcm = Buffer.alloc(frames * 2);
  for (let i = 0; i < frames; i++) {
    pcm.writeInt16LE(Math.round(Math.sin(2 * Math.PI * freq * i / sampleRate) * 16000), i * 2);
  }
  return pcm;
}

function peakFrequency(pcm, sampleRate, min = 100, max = 1000) {
  const frames = pcm.length / 2;
  let bestFreq = min;
  let bestPower = -Infinity;
  for (let freq = min; freq <= max; freq += 1) {
    let real = 0;
    let imag = 0;
    for (let i = 0; i < frames; i++) {
      const sample = pcm.readInt16LE(i * 2) / 32768;
      const phase = 2 * Math.PI * freq * i / sampleRate;
      real += sample * Math.cos(phase);
      imag -= sample * Math.sin(phase);
    }
    const power = real * real + imag * imag;
    if (power > bestPower) {
      bestPower = power;
      bestFreq = freq;
    }
  }
  return bestFreq;
}

async function readableToBuffer(readable) {
  const chunks = [];
  for await (const chunk of readable) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  return Buffer.concat(chunks);
}

function makeAdmin() {
  const docs = new Map();
  function firestore() {
    return {
      collection(name) {
        return {
          doc(id) {
            const key = `${name}/${id}`;
            return {
              async get() { return {exists: docs.has(key), data: () => docs.get(key)}; },
              async set(value) { docs.set(key, value); },
            };
          },
          async add(value) {
            const id = `add-${docs.size + 1}`;
            docs.set(`${name}/${id}`, value);
            return {id};
          },
        };
      },
    };
  }
  firestore.FieldValue = {serverTimestamp: () => 'server-timestamp'};
  return {firestore, _docs: docs};
}

function makeGoogle(createdFiles, onCreate = null) {
  return {
    drive() {
      return {
        files: {
          async create({requestBody, media}) {
            if (onCreate) onCreate({requestBody, media});
            assert.ok(media.body instanceof Readable);
            const id = `driveFile${String(createdFiles.size + 1).padStart(12, '0')}`;
            const bytes = await readableToBuffer(media.body);
            const metadata = {id, name: requestBody.name, mimeType: requestBody.mimeType, webViewLink: `https://drive.google.com/file/d/${id}/view`, parents: requestBody.parents || []};
            createdFiles.set(id, {metadata, bytes});
            return {data: metadata};
          },
          async get(args) {
            const stored = createdFiles.get(args.fileId) || [...createdFiles.values()].at(-1);
            assert(stored, 'readback requires a created file');
            if (args.alt === 'media') return {data: stored.bytes.buffer.slice(stored.bytes.byteOffset, stored.bytes.byteOffset + stored.bytes.byteLength)};
            return {data: stored.metadata};
          },
        },
      };
    },
  };
}

const oldFetch = globalThis.fetch;
const user = {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'};
const sampleRate = 24000;
const rawOne = Buffer.from([1, 0, 2, 0, 3, 0, 4, 0]);
const rawTwo = Buffer.from([5, 0, 6, 0, 7, 0, 8, 0]);
const singleWav = Buffer.concat([Buffer.from('RIFF....WAVEfmt ', 'ascii'), Buffer.from('compat')]);
let fetchCalls = [];

function installFetch() {
  fetchCalls = [];
  globalThis.fetch = async (url, options = {}) => {
    assert.equal(url, 'https://api.cartesia.ai/tts/bytes');
    const body = JSON.parse(options.body);
    fetchCalls.push(body);
    if (body.transcript === 'Compatibility request.') return new Response(singleWav, {status: 200});
    if (body.transcript === 'Zero pitch segment.') return new Response(rawOne, {status: 200});
    if (body.transcript === 'First shifted segment.') return new Response(rawOne, {status: 200});
    if (body.transcript === 'Second shifted segment.') return new Response(rawTwo, {status: 200});
    if (body.transcript === 'DSP failure segment.') return new Response(rawOne, {status: 200});
    throw new Error(`unexpected transcript ${body.transcript}`);
  };
}

try {
  installFetch();
  const compatFiles = new Map();
  const compat = await synthesizeCartesiaAudioArtifactOperation({google: makeGoogle(compatFiles), admin: makeAdmin(), auth: {}, user, cartesiaApiKey: () => 'test-cartesia-key', args: {text: 'Compatibility request.', requestId: 'pitch-compat-001', name: 'compat'}});
  assert.equal(compat.pitchSemitones, 0, 'existing requests default to zero pitch');
  assert.equal(compat.pitchProcessor, 'none');
  assert.equal(compat.segments[0].pitchBypassed, true);
  assert.equal(fetchCalls.length, 1);
  assert.equal(compat.byteCount, singleWav.length);
  assert.equal(compat.sha256, sha256(singleWav));

  let dspCalls = 0;
  pitch.setPitchShiftImplementationForTest(async () => { dspCalls += 1; throw new Error('zero pitch should not call DSP'); });
  installFetch();
  const zeroFiles = new Map();
  const zero = await synthesizeCartesiaAudioArtifactOperation({google: makeGoogle(zeroFiles), admin: makeAdmin(), auth: {}, user, cartesiaApiKey: () => 'test-cartesia-key', args: {segments: [{speaker: 'Zero', text: 'Zero pitch segment.', pitchSemitones: 0}], format: 'wav', sampleRate, requestId: 'pitch-zero-001', name: 'zero'}});
  assert.equal(dspCalls, 0, 'zero pitch segment bypasses DSP entirely');
  assert.equal(zero.segments[0].pitchProcessor, 'none');
  assert.equal(zero.sampleRate, sampleRate);
  assert.equal(zero.channelCount, 1);
  assert.equal(zero.pcmFormat, 'pcm_s16le');
  assert.deepEqual(wavDataBytes(zeroFiles.get(zero.fileId).bytes), rawOne);

  const observedPitches = [];
  pitch.setPitchShiftImplementationForTest(async (pcm, options) => {
    observedPitches.push(options.pitchSemitones);
    return {pcm: Buffer.from([...pcm].map((value) => (value + observedPitches.length) & 0xff)), bypassed: false, processor: 'test-dsp', pitchScale: pitch.pitchScaleForSemitones(options.pitchSemitones), inputFrames: pcm.length / 2, outputFrames: pcm.length / 2, durationRatio: 1};
  });
  installFetch();
  const shiftedFiles = new Map();
  const shifted = await driveOperationRunOperation({google: makeGoogle(shiftedFiles), admin: makeAdmin(), auth: {}, user, cartesiaApiKey: () => 'test-cartesia-key', args: {operation: 'tts.synthesize', args: {pitchSemitones: -2, segments: [{speaker: 'A', text: 'First shifted segment.', pitchSemitones: -1}, {speaker: 'B', text: 'Second shifted segment.'}], pauseMs: 10, format: 'wav', sampleRate, requestId: 'pitch-shifted-001', name: 'shifted'}}});
  assert.equal(shifted.completed, true);
  assert.deepEqual(observedPitches, [-1, -2], 'segment override wins over top-level default; default applies to remaining segments');
  assert.deepEqual(shifted.result.segments.map((segment) => segment.speaker), ['A', 'B'], 'segment order is preserved');
  assert.deepEqual(shifted.result.segments.map((segment) => segment.pitchSemitones), [-1, -2]);
  assert.equal(shifted.result.pitchSemitones, -2);
  const shiftedBytes = shiftedFiles.get(shifted.result.fileId).bytes;
  assert.equal(shifted.result.byteCount, shiftedBytes.length);
  assert.equal(shifted.result.sha256, sha256(shiftedBytes));
  assert.equal(shifted.result.readbackByteCount, shifted.result.byteCount);
  assert.equal(shifted.result.readbackSha256, shifted.result.sha256);
  assert.equal(shiftedBytes.readUInt32LE(24), sampleRate);
  assert.equal(shiftedBytes.readUInt16LE(22), 1);
  assert.equal(shiftedBytes.readUInt16LE(34), 16);

  pitch.setPitchShiftImplementationForTest(null);
  for (const bad of [NaN, Infinity, -13, 13, '-1']) {
    installFetch();
    const created = new Map();
    await assert.rejects(
      () => synthesizeCartesiaAudioArtifactOperation({google: makeGoogle(created), admin: makeAdmin(), auth: {}, user, cartesiaApiKey: () => 'test-cartesia-key', args: {text: 'Compatibility request.', pitchSemitones: bad, requestId: `pitch-invalid-${String(bad)}`}}),
      /pitchSemitones must/
    );
    assert.equal(fetchCalls.length, 0, 'invalid pitch fails before Cartesia');
    assert.equal(created.size, 0, 'invalid pitch fails before Drive write');
  }

  pitch.setPitchShiftImplementationForTest(async () => {
    const err = new Error('cartesia_pitch_shift_failed: injected DSP failure');
    err.status = 502;
    throw err;
  });
  installFetch();
  const failureFiles = new Map();
  await assert.rejects(
    () => synthesizeCartesiaAudioArtifactOperation({google: makeGoogle(failureFiles), admin: makeAdmin(), auth: {}, user, cartesiaApiKey: () => 'test-cartesia-key', args: {segments: [{text: 'DSP failure segment.', pitchSemitones: -1}], requestId: 'pitch-dsp-fail-001'}}),
    /cartesia_pitch_shift_failed/
  );
  assert.equal(fetchCalls.length, 1, 'DSP failure happens after provider PCM arrives');
  assert.equal(failureFiles.size, 0, 'DSP failure must not upload partial or unshifted audio');

  pitch.setPitchShiftImplementationForTest(null);
  const testTone = makeTonePcm(440, sampleRate, 1);
  const semitones = -2;
  const processed = await pitch.pitchShiftPcm16(testTone, {sampleRate, channels: 1, pitchSemitones: semitones});
  const expectedRatio = 2 ** (semitones / 12);
  const inputPeak = peakFrequency(testTone, sampleRate, 300, 600);
  const outputPeak = peakFrequency(processed.pcm, sampleRate, 300, 600);
  assert.equal(inputPeak, 440);
  assert(Math.abs((outputPeak / inputPeak) - expectedRatio) < 0.01, `frequency ratio ${outputPeak / inputPeak} should approximate ${expectedRatio}`);
  assert(Math.abs((processed.pcm.length / testTone.length) - 1) <= 0.01, 'tempo-preserving pitch shift keeps duration within 1%');
  assert.equal(processed.pcm.length % 2, 0, 'shifted output remains aligned 16-bit mono PCM');

  console.log('Cartesia pitch shift contract: OK');
} finally {
  pitch.setPitchShiftImplementationForTest(null);
  globalThis.fetch = oldFetch;
}
