const fs = require('node:fs');

const PITCH_SEMITONES_MIN = -12;
const PITCH_SEMITONES_MAX = 12;
const PCM_CHANNELS = 1;
const PCM_BYTES_PER_SAMPLE = 2;
let rubberBandPromise = null;
let pitchShiftImplementationForTest = null;

function safePitchSemitones(value, field = 'pitchSemitones') {
  if (value === undefined || value === null) return 0;
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    const err = new Error(`${field} must be a finite number between ${PITCH_SEMITONES_MIN} and ${PITCH_SEMITONES_MAX}.`);
    err.status = 400;
    throw err;
  }
  if (value < PITCH_SEMITONES_MIN || value > PITCH_SEMITONES_MAX) {
    const err = new Error(`${field} must be between ${PITCH_SEMITONES_MIN} and ${PITCH_SEMITONES_MAX} semitones.`);
    err.status = 400;
    throw err;
  }
  return value === 0 ? 0 : value;
}

function pitchScaleForSemitones(semitones) {
  return Math.pow(2, semitones / 12);
}

function pcm16ToFloat32Channels(pcm, channels = PCM_CHANNELS) {
  if (!Buffer.isBuffer(pcm)) pcm = Buffer.from(pcm || []);
  if (pcm.length % (PCM_BYTES_PER_SAMPLE * channels) !== 0) {
    const err = new Error('PCM byte length is not aligned to channel count.');
    err.status = 502;
    throw err;
  }
  const frames = pcm.length / PCM_BYTES_PER_SAMPLE / channels;
  const channelBuffers = Array.from({length: channels}, () => new Float32Array(frames));
  for (let frame = 0; frame < frames; frame++) {
    for (let channel = 0; channel < channels; channel++) {
      const offset = (frame * channels + channel) * PCM_BYTES_PER_SAMPLE;
      channelBuffers[channel][frame] = Math.max(-1, Math.min(1, pcm.readInt16LE(offset) / 32768));
    }
  }
  return channelBuffers;
}

function float32ChannelsToPcm16(channelBuffers, channels = PCM_CHANNELS) {
  if (!Array.isArray(channelBuffers) || channelBuffers.length !== channels || !channelBuffers[0]) {
    const err = new Error('DSP returned invalid channel buffers.');
    err.status = 502;
    throw err;
  }
  const frames = channelBuffers[0].length;
  const out = Buffer.alloc(frames * channels * PCM_BYTES_PER_SAMPLE);
  for (let channel = 1; channel < channels; channel++) {
    if (!channelBuffers[channel] || channelBuffers[channel].length !== frames) {
      const err = new Error('DSP returned mismatched channel buffer lengths.');
      err.status = 502;
      throw err;
    }
  }
  for (let frame = 0; frame < frames; frame++) {
    for (let channel = 0; channel < channels; channel++) {
      const sample = Math.max(-1, Math.min(1, Number(channelBuffers[channel][frame]) || 0));
      const value = sample < 0 ? Math.round(sample * 32768) : Math.round(sample * 32767);
      out.writeInt16LE(Math.max(-32768, Math.min(32767, value)), (frame * channels + channel) * PCM_BYTES_PER_SAMPLE);
    }
  }
  return out;
}

async function loadRubberBand() {
  if (rubberBandPromise) return rubberBandPromise;
  rubberBandPromise = (async () => {
    const rubberband = require('rubberband-wasm');
    const wasmPath = require.resolve('rubberband-wasm/dist/rubberband.wasm');
    const wasm = await WebAssembly.compile(fs.readFileSync(wasmPath));
    const api = await rubberband.RubberBandInterface.initialize(wasm);
    return {api, options: rubberband.RubberBandOption};
  })();
  return rubberBandPromise;
}

function copyFloat32(view) {
  const out = new Float32Array(view.length);
  out.set(view);
  return out;
}

async function rubberBandPitchShiftPcm16(pcm, {sampleRate, channels = PCM_CHANNELS, pitchSemitones}) {
  const semitones = safePitchSemitones(pitchSemitones);
  if (semitones === 0) return {pcm, bypassed: true, processor: 'none', pitchScale: 1};
  const cleanSampleRate = Math.max(8000, Math.min(48000, Math.floor(Number(sampleRate || 24000)) || 24000));
  const cleanChannels = Math.max(1, Math.min(2, Math.floor(Number(channels || PCM_CHANNELS)) || PCM_CHANNELS));
  const channelBuffers = pcm16ToFloat32Channels(pcm, cleanChannels);
  const inputFrames = channelBuffers[0].length;
  if (!inputFrames) return {pcm, bypassed: true, processor: 'none', pitchScale: 1};
  const {api, options} = await loadRubberBand();
  const pitchScale = pitchScaleForSemitones(semitones);
  const rbOptions = options.RubberBandOptionProcessOffline |
    options.RubberBandOptionPitchHighQuality |
    options.RubberBandOptionEngineFiner |
    options.RubberBandOptionChannelsTogether;
  const state = api.rubberband_new(cleanSampleRate, cleanChannels, rbOptions, 1, pitchScale);
  if (!state) {
    const err = new Error('cartesia_pitch_shift_failed: Rubber Band state allocation failed.');
    err.status = 502;
    throw err;
  }
  let channelArrayPtr = 0;
  const channelDataPtr = [];
  try {
    api.rubberband_set_pitch_scale(state, pitchScale);
    api.rubberband_set_time_ratio(state, 1);
    api.rubberband_set_expected_input_duration(state, inputFrames);
    let blockFrames = Math.max(1024, Math.min(16384, api.rubberband_get_samples_required(state) || 4096));
    api.rubberband_set_max_process_size(state, blockFrames);
    blockFrames = Math.max(blockFrames, api.rubberband_get_samples_required(state) || blockFrames);
    channelArrayPtr = api.malloc(cleanChannels * 4);
    for (let channel = 0; channel < cleanChannels; channel++) {
      const ptr = api.malloc(blockFrames * 4);
      channelDataPtr.push(ptr);
      api.memWritePtr(channelArrayPtr + channel * 4, ptr);
    }

    for (let read = 0; read < inputFrames;) {
      const remaining = Math.min(blockFrames, inputFrames - read);
      for (let channel = 0; channel < cleanChannels; channel++) api.memWrite(channelDataPtr[channel], channelBuffers[channel].subarray(read, read + remaining));
      read += remaining;
      api.rubberband_study(state, channelArrayPtr, remaining, read >= inputFrames ? 1 : 0);
    }

    const outputChunks = Array.from({length: cleanChannels}, () => []);
    function retrieve(final = false) {
      while (true) {
        const available = api.rubberband_available(state);
        if (available < 1) break;
        if (!final && available < blockFrames) break;
        const want = Math.min(blockFrames, available);
        const received = api.rubberband_retrieve(state, channelArrayPtr, want);
        if (received < 1) break;
        for (let channel = 0; channel < cleanChannels; channel++) outputChunks[channel].push(copyFloat32(api.memReadF32(channelDataPtr[channel], received)));
      }
    }

    for (let read = 0; read < inputFrames;) {
      const remaining = Math.min(blockFrames, inputFrames - read);
      for (let channel = 0; channel < cleanChannels; channel++) api.memWrite(channelDataPtr[channel], channelBuffers[channel].subarray(read, read + remaining));
      read += remaining;
      api.rubberband_process(state, channelArrayPtr, remaining, read >= inputFrames ? 1 : 0);
      retrieve(false);
    }
    retrieve(true);
    const outputFrames = outputChunks[0].reduce((sum, chunk) => sum + chunk.length, 0);
    if (!outputFrames) {
      const err = new Error('cartesia_pitch_shift_failed: Rubber Band returned empty audio.');
      err.status = 502;
      throw err;
    }
    const shifted = outputChunks.map((chunks) => {
      const out = new Float32Array(outputFrames);
      let offset = 0;
      for (const chunk of chunks) {
        out.set(chunk, offset);
        offset += chunk.length;
      }
      return out;
    });
    return {
      pcm: float32ChannelsToPcm16(shifted, cleanChannels),
      bypassed: false,
      processor: 'rubberband-wasm',
      pitchScale,
      inputFrames,
      outputFrames,
      durationRatio: outputFrames / inputFrames,
    };
  } catch (err) {
    if (!err.status) err.status = 502;
    if (!/^cartesia_pitch_shift_failed/.test(err.message || '')) err.message = 'cartesia_pitch_shift_failed: ' + (err.message || String(err));
    throw err;
  } finally {
    for (const ptr of channelDataPtr) {
      if (ptr) api.free(ptr);
    }
    if (channelArrayPtr) api.free(channelArrayPtr);
    api.rubberband_delete(state);
  }
}

async function pitchShiftPcm16(pcm, options = {}) {
  if (pitchShiftImplementationForTest) return pitchShiftImplementationForTest(pcm, options);
  return rubberBandPitchShiftPcm16(pcm, options);
}

function setPitchShiftImplementationForTest(fn) {
  pitchShiftImplementationForTest = typeof fn === 'function' ? fn : null;
}

module.exports = {
  PITCH_SEMITONES_MIN,
  PITCH_SEMITONES_MAX,
  safePitchSemitones,
  pitchScaleForSemitones,
  pcm16ToFloat32Channels,
  float32ChannelsToPcm16,
  pitchShiftPcm16,
  setPitchShiftImplementationForTest,
};
