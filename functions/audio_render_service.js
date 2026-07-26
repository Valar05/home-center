const {createHash, randomUUID} = require('node:crypto');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const zlib = require('node:zlib');
const {CARTESIA_DEFAULT_MODEL_ID, CARTESIA_DEFAULT_VOICE_NAME, openCartesiaStream} = require('./hosted_speech_provider');
const cartesiaPitchShift = require('./cartesia_pitch_shift');
const {GENERATED_ARTIFACT_BUCKET, parseGsRef, uploadGeneratedArtifact, publishGeneratedArtifactToDrive, inspectGeneratedArtifact} = require('./artifact_bucket');

const DEFAULT_SAMPLE_RATE = 48000;
const MAX_DURATION_SECONDS = Number(process.env.HOME_CENTER_AUDIO_RENDER_MAX_SECONDS || 900);
const MAX_ENCODED_OUTPUT_BYTES = Number(process.env.HOME_CENTER_AUDIO_RENDER_MAX_ENCODED_BYTES || 24 * 1024 * 1024);
const MAX_WAV_OUTPUT_BYTES = Number(process.env.HOME_CENTER_AUDIO_RENDER_MAX_WAV_BYTES || 64 * 1024 * 1024);
const MAX_OUTPUT_BYTES = Number(process.env.HOME_CENTER_AUDIO_RENDER_MAX_OUTPUT_BYTES || MAX_WAV_OUTPUT_BYTES);
const INLINE_AUDIO_MAX_BYTES = Number(process.env.HOME_CENTER_AUDIO_RENDER_INLINE_MAX_BYTES || 768 * 1024);
const SPEECH_SEQUENCE_MAX_SEGMENTS = Number(process.env.HOME_CENTER_AUDIO_RENDER_MAX_SPEECH_SEGMENTS || 240);
const SPEECH_SEQUENCE_DEFAULT_CONCURRENCY = Number(process.env.HOME_CENTER_AUDIO_RENDER_SPEECH_CONCURRENCY || 3);
const MAX_SOURCE_BYTES = Number(process.env.HOME_CENTER_AUDIO_RENDER_MAX_SOURCE_BYTES || 50 * 1024 * 1024);
const MAX_GRAPH_NODES = Number(process.env.HOME_CENTER_AUDIO_RENDER_MAX_GRAPH_NODES || 250);
const DEFAULT_TIMEOUT_MS = Number(process.env.HOME_CENTER_AUDIO_RENDER_TIMEOUT_MS || 55000);
const AUDIO_RENDER_LEASE_MS = Number(process.env.HOME_CENTER_AUDIO_RENDER_LEASE_MS || 120000);
const AUDIO_RENDER_STALE_MS = Number(process.env.HOME_CENTER_AUDIO_RENDER_STALE_MS || 10 * 60 * 1000);

const SPEECH_MAX_TEXT_CHARS = 12000;
const CARTESIA_SPEECH_SAMPLE_RATE_MAX = 48000;
const CARTESIA_SUPPORTED_EMOTIONS = Object.freeze([
  'neutral', 'calm', 'angry', 'content', 'sad', 'scared', 'hurt', 'rejected', 'disappointed',
  'distant', 'resigned', 'hesitant', 'insecure', 'contempt', 'sarcastic', 'frustrated',
  'apologetic', 'determined',
]);
const CARTESIA_SUPPORTED_EMOTION_SET = new Set(CARTESIA_SUPPORTED_EMOTIONS);
const STASYA_CANONICAL_PROFILE = Object.freeze({
  character: 'Stasya',
  aliases: Object.freeze(['Stasya']),
  provider: 'cartesia',
  voiceName: 'Milena - Composed Clarifier',
  voiceId: 'b66b3a19-31b3-401f-8b08-40d46a61e4f1',
  modelId: 'sonic-3.5',
  speed: 1.08,
  pitchSemitones: 0,
  direction: 'Cultivated, intimate, dry, playful, capable of hard authority; not a heavy Bond-style Russian accent.',
});
const ISAAC_CANONICAL_PROFILE = Object.freeze({
  character: 'Isaac',
  aliases: Object.freeze(['Isaac Slater']),
  provider: 'cartesia',
  voiceName: 'Clyde - Calm Narrator',
  voiceId: '98a34ef2-2140-4c28-9c71-663dc4dd7022',
  modelId: 'sonic-3.5',
  speed: 0.97,
  pitchSemitones: -1.5,
  direction: 'Controlled American mentor; technical, dry, protective; deep without gravel.',
});
const EVE_CANONICAL_PROFILE = Object.freeze({
  character: 'Eve',
  aliases: Object.freeze(['Eve']),
  provider: 'cartesia',
  voiceName: 'Jacqueline - Reassuring Agent',
  voiceId: '9626c31c-bec5-4cca-baa8-f8ba9e84c8bc',
  modelId: 'sonic-3.5',
  speed: 1.0,
  pitchSemitones: 0,
  direction: 'Warm and composed, observant restraint, emotionally aware without becoming syrupy.',
});
const CANONICAL_CHARACTER_PROFILES = Object.freeze({
  stasya: STASYA_CANONICAL_PROFILE,
  isaac: ISAAC_CANONICAL_PROFILE,
  isaac_slater: ISAAC_CANONICAL_PROFILE,
  eve: EVE_CANONICAL_PROFILE,
});

function audioError(message, status = 400, code = 'audio_render_failed') {
  const err = new Error(message);
  err.status = status;
  err.failureKind = code;
  return err;
}

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function sha256Hex(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}

function assertFinite(value, label, min = -Infinity, max = Infinity) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw audioError(label + ' must be a finite number between ' + min + ' and ' + max + '.', 400, 'audio_render_validation_failed');
  }
  return value;
}

function sanitizeRecipeText(scriptText) {
  const text = safeText(scriptText, 2 * 1024 * 1024);
  if (!text) throw audioError('scriptText is required and must contain a JSON audio recipe.', 400, 'audio_render_recipe_required');
  const blocked = [/require\s*\(/i, /import\s+[^\n]+from/i, /child_process/i, /fetch\s*\(/i, /XMLHttpRequest/i, /process\./i, /fs\./i, /eval\s*\(/i, /Function\s*\(/i, /https?:\/\//i];
  if (blocked.some((pattern) => pattern.test(text))) {
    throw audioError('audio.render accepts declarative JSON recipes only; imports, shell, network, process, and filesystem access are not allowed.', 400, 'audio_render_unsafe_script_rejected');
  }
  try {
    return JSON.parse(text);
  } catch (_) {
    throw audioError('scriptText must be valid JSON for the Home Center audio recipe DSL.', 400, 'audio_render_invalid_json_recipe');
  }
}

class Rng {
  constructor(seed = 1) {
    const h = createHash('sha256').update(String(seed)).digest();
    this.state = h.readUInt32LE(0) || 1;
  }
  next() {
    let x = this.state >>> 0;
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    this.state = x >>> 0;
    return (this.state || 1) / 0xffffffff;
  }
  bipolar() { return this.next() * 2 - 1; }
}

class Clip {
  constructor(channels, sampleRate = DEFAULT_SAMPLE_RATE, label = '') {
    if (!Array.isArray(channels) || !channels.length) throw audioError('clip requires at least one channel.', 500, 'audio_internal_error');
    const frames = channels[0].length;
    for (const channel of channels) {
      if (!(channel instanceof Float32Array) || channel.length !== frames) throw audioError('clip channels must be aligned Float32Array values.', 500, 'audio_internal_error');
    }
    this.channels = channels;
    this.sampleRate = sampleRate;
    this.label = label;
  }
  get channelCount() { return this.channels.length; }
  get frames() { return this.channels[0].length; }
  get duration() { return this.frames / this.sampleRate; }
  clone(label = this.label) { return new Clip(this.channels.map((c) => new Float32Array(c)), this.sampleRate, label); }
}

function makeClip(channelCount, frames, sampleRate, fill = 0, label = '') {
  return new Clip(Array.from({length: channelCount}, () => {
    const c = new Float32Array(frames);
    if (fill) c.fill(fill);
    return c;
  }), sampleRate, label);
}

function ensureClip(value, label = 'clip') {
  if (!(value instanceof Clip)) throw audioError(label + ' is not an audio clip.', 400, 'audio_render_validation_failed');
  return value;
}

function silence({duration = 1, sampleRate = DEFAULT_SAMPLE_RATE, channels = 2} = {}) {
  assertFinite(duration, 'duration', 0, MAX_DURATION_SECONDS);
  return makeClip(Math.max(1, Math.min(8, Math.floor(channels))), Math.round(duration * sampleRate), sampleRate, 0, 'silence');
}

function tone({frequency = 440, duration = 1, sampleRate = DEFAULT_SAMPLE_RATE, channels = 1, gain = 0.5, phase = 0} = {}) {
  assertFinite(frequency, 'frequency', 1, sampleRate / 2);
  assertFinite(duration, 'duration', 0, MAX_DURATION_SECONDS);
  const clip = makeClip(Math.max(1, Math.min(8, Math.floor(channels))), Math.round(duration * sampleRate), sampleRate, 0, 'tone');
  for (let i = 0; i < clip.frames; i++) {
    const v = Math.sin(phase + 2 * Math.PI * frequency * i / sampleRate) * gain;
    for (const channel of clip.channels) channel[i] = v;
  }
  return clip;
}

function noise({duration = 1, sampleRate = DEFAULT_SAMPLE_RATE, channels = 1, gain = 0.25, seed = 1, color = 'white'} = {}) {
  assertFinite(duration, 'duration', 0, MAX_DURATION_SECONDS);
  const rng = new Rng(seed);
  const clip = makeClip(Math.max(1, Math.min(8, Math.floor(channels))), Math.round(duration * sampleRate), sampleRate, 0, 'noise');
  let last = 0;
  for (let i = 0; i < clip.frames; i++) {
    let v = rng.bipolar();
    if (color === 'brown') { last = Math.max(-1, Math.min(1, last * 0.985 + v * 0.12)); v = last; }
    if (color === 'pink') { last = last * 0.85 + v * 0.15; v = last; }
    for (const channel of clip.channels) channel[i] = v * gain;
  }
  return clip;
}

function toChannels(clip, count = 2) {
  ensureClip(clip);
  count = Math.max(1, Math.min(8, Math.floor(count)));
  if (clip.channelCount === count) return clip.clone();
  const out = makeClip(count, clip.frames, clip.sampleRate, 0, clip.label);
  for (let ch = 0; ch < count; ch++) {
    const source = clip.channelCount === 1 ? clip.channels[0] : clip.channels[Math.min(ch, clip.channelCount - 1)];
    out.channels[ch].set(source);
  }
  return out;
}

function resample(clip, sampleRate = DEFAULT_SAMPLE_RATE) {
  ensureClip(clip);
  sampleRate = Math.max(8000, Math.min(96000, Math.floor(sampleRate)));
  if (clip.sampleRate === sampleRate) return clip.clone();
  const frames = Math.max(1, Math.round(clip.frames * sampleRate / clip.sampleRate));
  const out = makeClip(clip.channelCount, frames, sampleRate, 0, clip.label);
  const ratio = clip.sampleRate / sampleRate;
  for (let ch = 0; ch < clip.channelCount; ch++) {
    const src = clip.channels[ch], dst = out.channels[ch];
    for (let i = 0; i < frames; i++) {
      const pos = i * ratio;
      const a = Math.floor(pos);
      const b = Math.min(src.length - 1, a + 1);
      const t = pos - a;
      dst[i] = (src[a] || 0) * (1 - t) + (src[b] || 0) * t;
    }
  }
  return out;
}

function gain(clip, db = 0) {
  ensureClip(clip); assertFinite(db, 'gainDb', -120, 60);
  const mult = Math.pow(10, db / 20);
  const out = clip.clone();
  for (const channel of out.channels) for (let i = 0; i < channel.length; i++) channel[i] *= mult;
  return out;
}

function fade(clip, seconds = 0.01, direction = 'in') {
  ensureClip(clip); assertFinite(seconds, 'fade seconds', 0, MAX_DURATION_SECONDS);
  const frames = Math.min(clip.frames, Math.round(seconds * clip.sampleRate));
  const out = clip.clone();
  for (let i = 0; i < frames; i++) {
    const t = frames <= 1 ? 1 : i / (frames - 1);
    const f = direction === 'out' ? 1 - t : t;
    const idx = direction === 'out' ? clip.frames - frames + i : i;
    for (const channel of out.channels) channel[idx] *= f;
  }
  return out;
}

function trim(clip, start = 0, duration = null) {
  ensureClip(clip); assertFinite(start, 'start', 0, MAX_DURATION_SECONDS);
  if (duration !== null && duration !== undefined) assertFinite(duration, 'duration', 0, MAX_DURATION_SECONDS);
  const a = Math.min(clip.frames, Math.round(start * clip.sampleRate));
  const b = duration === null || duration === undefined ? clip.frames : Math.min(clip.frames, a + Math.round(duration * clip.sampleRate));
  return new Clip(clip.channels.map((c) => c.slice(a, b)), clip.sampleRate, clip.label);
}

function concat(clips) {
  if (!Array.isArray(clips) || !clips.length) throw audioError('concat requires clips.', 400, 'audio_render_validation_failed');
  const sampleRate = clips[0].sampleRate;
  const channelCount = Math.max(...clips.map((clip) => ensureClip(clip).channelCount));
  const normalized = clips.map((clip) => toChannels(resample(clip, sampleRate), channelCount));
  const frames = normalized.reduce((sum, clip) => sum + clip.frames, 0);
  const out = makeClip(channelCount, frames, sampleRate, 0, 'concat');
  let offset = 0;
  for (const clip of normalized) {
    for (let ch = 0; ch < channelCount; ch++) out.channels[ch].set(clip.channels[ch], offset);
    offset += clip.frames;
  }
  return out;
}

function loop(clip, duration) {
  ensureClip(clip); assertFinite(duration, 'duration', 0, MAX_DURATION_SECONDS);
  const frames = Math.round(duration * clip.sampleRate);
  const out = makeClip(clip.channelCount, frames, clip.sampleRate, 0, 'loop');
  if (!clip.frames) return out;
  for (let ch = 0; ch < clip.channelCount; ch++) {
    const src = clip.channels[ch], dst = out.channels[ch];
    for (let i = 0; i < frames; i++) dst[i] = src[i % src.length];
  }
  return out;
}

function crossfade(a, b, seconds = 0.1) {
  ensureClip(a, 'a'); ensureClip(b, 'b');
  const sampleRate = a.sampleRate;
  b = resample(b, sampleRate);
  const channelCount = Math.max(a.channelCount, b.channelCount);
  a = toChannels(a, channelCount); b = toChannels(b, channelCount);
  const fadeFrames = Math.min(a.frames, b.frames, Math.round(seconds * sampleRate));
  const frames = a.frames + b.frames - fadeFrames;
  const out = makeClip(channelCount, frames, sampleRate, 0, 'crossfade');
  for (let ch = 0; ch < channelCount; ch++) {
    out.channels[ch].set(a.channels[ch].slice(0, a.frames - fadeFrames), 0);
    for (let i = 0; i < fadeFrames; i++) {
      const t = fadeFrames <= 1 ? 1 : i / (fadeFrames - 1);
      out.channels[ch][a.frames - fadeFrames + i] = a.channels[ch][a.frames - fadeFrames + i] * (1 - t) + b.channels[ch][i] * t;
    }
    out.channels[ch].set(b.channels[ch].slice(fadeFrames), a.frames);
  }
  return out;
}

function pan(clip, value = 0) {
  ensureClip(clip); assertFinite(value, 'pan', -1, 1);
  const mono = clip.channelCount === 1 ? clip : mixdownMono(clip);
  const out = makeClip(2, mono.frames, mono.sampleRate, 0, clip.label);
  const angle = (value + 1) * Math.PI / 4;
  const l = Math.cos(angle), r = Math.sin(angle);
  for (let i = 0; i < mono.frames; i++) { out.channels[0][i] = mono.channels[0][i] * l; out.channels[1][i] = mono.channels[0][i] * r; }
  return out;
}

function mixdownMono(clip) {
  const out = makeClip(1, clip.frames, clip.sampleRate, 0, clip.label);
  for (let i = 0; i < clip.frames; i++) {
    let s = 0;
    for (const channel of clip.channels) s += channel[i];
    out.channels[0][i] = s / clip.channelCount;
  }
  return out;
}

function reverse(clip) { const out = clip.clone(); for (const c of out.channels) c.reverse(); return out; }

function normalizePeak(clip, targetDb = -1) {
  ensureClip(clip); assertFinite(targetDb, 'targetDb', -60, 0);
  const peak = measure(clip).peak;
  if (peak <= 1e-9) return clip.clone();
  return gain(clip, targetDb - 20 * Math.log10(peak));
}

function normalizeLufs(clip, target = -16) {
  ensureClip(clip); assertFinite(target, 'targetLufs', -60, 0);
  const lufs = measure(clip).integratedLufs;
  if (!Number.isFinite(lufs)) return clip.clone();
  return gain(clip, target - lufs);
}

function biquadLike(clip, kind = 'lowpass', frequency = 1000) {
  ensureClip(clip); assertFinite(frequency, 'frequency', 10, clip.sampleRate / 2 - 10);
  const out = clip.clone();
  const rc = 1 / (2 * Math.PI * frequency);
  const dt = 1 / clip.sampleRate;
  const alpha = dt / (rc + dt);
  for (const channel of out.channels) {
    let low = channel[0] || 0;
    let prevIn = low;
    for (let i = 0; i < channel.length; i++) {
      low += alpha * (channel[i] - low);
      const high = channel[i] - low;
      const band = high - (prevIn - low);
      prevIn = channel[i];
      channel[i] = kind === 'highpass' ? high : kind === 'bandpass' ? band : low;
    }
  }
  return out;
}

function compress(clip, thresholdDb = -12, ratio = 4) {
  ensureClip(clip); assertFinite(thresholdDb, 'thresholdDb', -80, 0); assertFinite(ratio, 'ratio', 1, 40);
  const threshold = Math.pow(10, thresholdDb / 20);
  const out = clip.clone();
  for (const channel of out.channels) for (let i = 0; i < channel.length; i++) {
    const sign = Math.sign(channel[i]); const x = Math.abs(channel[i]);
    channel[i] = sign * (x <= threshold ? x : threshold + (x - threshold) / ratio);
  }
  return out;
}

function limit(clip, ceilingDb = -0.5) {
  ensureClip(clip); assertFinite(ceilingDb, 'ceilingDb', -60, 0);
  const ceiling = Math.pow(10, ceilingDb / 20);
  const out = clip.clone();
  for (const channel of out.channels) for (let i = 0; i < channel.length; i++) channel[i] = Math.max(-ceiling, Math.min(ceiling, channel[i]));
  return out;
}

function distort(clip, drive = 1.5) {
  ensureClip(clip); assertFinite(drive, 'drive', 0, 40);
  const out = clip.clone();
  for (const channel of out.channels) for (let i = 0; i < channel.length; i++) channel[i] = Math.tanh(channel[i] * drive) / Math.tanh(drive || 1);
  return out;
}

function delay(clip, seconds = 0.12, feedback = 0.25, wet = 0.25) {
  ensureClip(clip); assertFinite(seconds, 'delay seconds', 0, 5); assertFinite(feedback, 'feedback', 0, 0.95); assertFinite(wet, 'wet', 0, 1);
  const d = Math.round(seconds * clip.sampleRate);
  const out = clip.clone();
  for (const channel of out.channels) for (let i = d; i < channel.length; i++) channel[i] += (channel[i - d] || 0) * feedback * wet;
  return limit(out, -0.2);
}

function reverb(clip, amount = 0.2, seconds = 0.35) {
  ensureClip(clip); assertFinite(amount, 'amount', 0, 1); assertFinite(seconds, 'seconds', 0, 5);
  let out = clip.clone();
  out = delay(out, Math.min(0.037, seconds), 0.35, amount);
  out = delay(out, Math.min(0.071, seconds), 0.25, amount * 0.75);
  out = delay(out, Math.min(0.113, seconds), 0.18, amount * 0.5);
  return out;
}

function envelope(clip, points = []) {
  ensureClip(clip);
  const out = clip.clone();
  const pts = Array.isArray(points) ? points.map((p) => ({t: safeNumber(p.t, 0), v: safeNumber(p.v, 1)})).sort((a, b) => a.t - b.t) : [];
  if (!pts.length) return out;
  for (let i = 0; i < out.frames; i++) {
    const t = i / out.sampleRate;
    let a = pts[0], b = pts[pts.length - 1];
    for (let j = 0; j < pts.length - 1; j++) if (t >= pts[j].t && t <= pts[j + 1].t) { a = pts[j]; b = pts[j + 1]; break; }
    const f = b.t === a.t ? b.v : a.v + (b.v - a.v) * Math.max(0, Math.min(1, (t - a.t) / (b.t - a.t)));
    for (const channel of out.channels) channel[i] *= f;
  }
  return out;
}

function timeStretch(clip, factor = 1) {
  ensureClip(clip); assertFinite(factor, 'timeStretch factor', 0.25, 4);
  const targetFrames = Math.max(1, Math.round(clip.frames * factor));
  const temp = resample(new Clip(clip.channels.map((c) => c.slice()), Math.round(clip.sampleRate / factor), clip.label), clip.sampleRate);
  if (temp.frames === targetFrames) return temp;
  return trim(loop(temp, targetFrames / clip.sampleRate), 0, targetFrames / clip.sampleRate);
}

function pitchShift(clip, semitones = 0) {
  ensureClip(clip); assertFinite(semitones, 'pitchSemitones', -24, 24);
  if (Math.abs(semitones) < 1e-9) return clip.clone();
  const ratio = Math.pow(2, semitones / 12);
  const pitched = resample(new Clip(clip.channels.map((c) => c.slice()), Math.round(clip.sampleRate / ratio), clip.label), clip.sampleRate);
  return timeStretch(pitched, clip.frames / Math.max(1, pitched.frames));
}

function timeline({duration, sampleRate = DEFAULT_SAMPLE_RATE, channels = 2, items = []}) {
  assertFinite(duration, 'duration', 0, MAX_DURATION_SECONDS);
  const out = makeClip(channels, Math.round(duration * sampleRate), sampleRate, 0, 'timeline');
  for (const item of items) {
    const clip = toChannels(resample(ensureClip(item.clip), sampleRate), channels);
    const offset = Math.max(0, Math.round(safeNumber(item.at, 0) * sampleRate));
    const itemGain = Math.pow(10, safeNumber(item.gainDb, 0) / 20);
    for (let ch = 0; ch < channels; ch++) for (let i = 0; i < clip.frames && offset + i < out.frames; i++) out.channels[ch][offset + i] += clip.channels[ch][i] * itemGain;
  }
  return out;
}

async function blockMix({duration, sampleRate = DEFAULT_SAMPLE_RATE, channels = 2, blockFrames = 65536, items = [], onProgress = null} = {}) {
  assertFinite(duration, 'duration', 0, MAX_DURATION_SECONDS);
  channels = Math.max(1, Math.min(8, Math.floor(channels)));
  blockFrames = Math.max(4096, Math.min(262144, Math.floor(blockFrames)));
  if (!Array.isArray(items) || !items.length || items.length > 500) throw audioError('block_mix.items must contain 1 to 500 items.', 400, 'audio_render_validation_failed');
  const out = makeClip(channels, Math.round(duration * sampleRate), sampleRate, 0, 'block_mix');
  const prepared = items.map((item, index) => {
    const clip = ensureClip(item.clip, 'block_mix item ' + index);
    const atFrame = Math.round(safeNumber(item.at, 0) * sampleRate);
    const sourceOffsetFrames = Math.max(0, Math.round(safeNumber(item.offset, 0) * clip.sampleRate));
    const looped = item.loop === true;
    const availableSeconds = Math.max(0, (clip.frames - sourceOffsetFrames) / clip.sampleRate);
    const itemDuration = item.duration === undefined ? (looped ? Math.max(0, duration - safeNumber(item.at, 0)) : availableSeconds) : safeNumber(item.duration, availableSeconds);
    assertFinite(itemDuration, 'block_mix item duration', 0, MAX_DURATION_SECONDS);
    const durationFrames = Math.round(itemDuration * sampleRate);
    const gainMult = Math.pow(10, safeNumber(item.gainDb, 0) / 20);
    const panValue = Math.max(-1, Math.min(1, safeNumber(item.pan, 0)));
    const monoLeft = panValue <= 0 ? 1 : 1 - panValue;
    const monoRight = panValue >= 0 ? 1 : 1 + panValue;
    const duckClip = item.duckClip ? ensureClip(item.duckClip, 'block_mix duckBy ' + index) : null;
    return {
      clip, atFrame, sourceOffsetFrames, looped, durationFrames, gainMult,
      fadeInFrames: Math.max(0, Math.round(safeNumber(item.fadeIn, 0) * sampleRate)),
      fadeOutFrames: Math.max(0, Math.round(safeNumber(item.fadeOut, 0) * sampleRate)),
      monoLeft, monoRight,
      duckClip,
      duckAtFrame: Math.round(safeNumber(item.duckAt, 0) * sampleRate),
      duckAmount: Math.pow(10, -Math.abs(safeNumber(item.duckAmountDb, 6)) / 20),
    };
  });

  const sampleAt = (clip, sourceFrame, channel, looped) => {
    if (!clip.frames) return 0;
    if (looped) sourceFrame = ((sourceFrame % clip.frames) + clip.frames) % clip.frames;
    if (sourceFrame < 0 || sourceFrame >= clip.frames) return 0;
    const a = Math.floor(sourceFrame);
    const b = looped ? (a + 1) % clip.frames : Math.min(clip.frames - 1, a + 1);
    const t = sourceFrame - a;
    const srcChannel = clip.channels[clip.channelCount === 1 ? 0 : Math.min(channel, clip.channelCount - 1)];
    return (srcChannel[a] || 0) * (1 - t) + (srcChannel[b] || 0) * t;
  };

  const totalBlocks = Math.max(1, Math.ceil(out.frames / blockFrames));
  for (let blockIndex = 0; blockIndex < totalBlocks; blockIndex++) {
    const blockStart = blockIndex * blockFrames;
    const blockEnd = Math.min(out.frames, blockStart + blockFrames);
    for (const item of prepared) {
      const itemStart = Math.max(blockStart, item.atFrame, 0);
      const itemEnd = Math.min(blockEnd, item.atFrame + item.durationFrames, out.frames);
      if (itemEnd <= itemStart) continue;
      const sourceRatio = item.clip.sampleRate / sampleRate;
      const duckRatio = item.duckClip ? item.duckClip.sampleRate / sampleRate : 1;
      for (let frame = itemStart; frame < itemEnd; frame++) {
        const localFrame = frame - item.atFrame;
        const sourceFrame = item.sourceOffsetFrames + localFrame * sourceRatio;
        let itemGain = item.gainMult;
        if (item.fadeInFrames && localFrame < item.fadeInFrames) itemGain *= localFrame / item.fadeInFrames;
        const remaining = item.durationFrames - localFrame;
        if (item.fadeOutFrames && remaining < item.fadeOutFrames) itemGain *= Math.max(0, remaining / item.fadeOutFrames);
        if (item.duckClip) {
          const keyFrame = (frame - item.duckAtFrame) * duckRatio;
          let key = 0;
          for (let keyChannel = 0; keyChannel < item.duckClip.channelCount; keyChannel++) key = Math.max(key, Math.abs(sampleAt(item.duckClip, keyFrame, keyChannel, false)));
          key = Math.min(1, key * 4);
          itemGain *= 1 - key * (1 - item.duckAmount);
        }
        if (item.clip.channelCount === 1 && channels === 2) {
          const value = sampleAt(item.clip, sourceFrame, 0, item.looped) * itemGain;
          out.channels[0][frame] += value * item.monoLeft;
          out.channels[1][frame] += value * item.monoRight;
        } else {
          for (let channel = 0; channel < channels; channel++) out.channels[channel][frame] += sampleAt(item.clip, sourceFrame, channel, item.looped) * itemGain;
        }
      }
    }
    if (typeof onProgress === 'function') await onProgress({phase: 'block_mixing', blockIndex: blockIndex + 1, blockCount: totalBlocks, framesProcessed: blockEnd, totalFrames: out.frames});
    if (blockIndex + 1 < totalBlocks) await new Promise((resolve) => setImmediate(resolve));
  }
  return out;
}

function duck(mixClip, keyClip, amountDb = 5) {
  const out = mixClip.clone();
  keyClip = resample(mixdownMono(keyClip), mixClip.sampleRate);
  const amount = Math.pow(10, -Math.abs(amountDb) / 20);
  for (let i = 0; i < out.frames; i++) {
    const key = Math.min(1, Math.abs(keyClip.channels[0][Math.min(i, keyClip.frames - 1)] || 0) * 4);
    const f = 1 - key * (1 - amount);
    for (const channel of out.channels) channel[i] *= f;
  }
  return out;
}

function measure(clip) {
  ensureClip(clip);
  let peak = 0, sumSq = 0, samples = 0, clippingCount = 0;
  for (const channel of clip.channels) for (let i = 0; i < channel.length; i++) {
    const v = channel[i]; const a = Math.abs(v);
    peak = Math.max(peak, a); sumSq += v * v; samples += 1;
    if (a >= 0.999) clippingCount += 1;
  }
  const rms = samples ? Math.sqrt(sumSq / samples) : 0;
  const integratedLufs = rms > 1e-12 ? 20 * Math.log10(rms) - 0.691 : -Infinity;
  return {duration: clip.duration, sampleRate: clip.sampleRate, channelCount: clip.channelCount, peak, integratedLufs, clippingCount, silent: peak < 1e-5};
}


function outputByteLimit(format, mimeType = '') {
  const clean = safeText(format, 20).toLowerCase();
  if (clean === 'wav' || /wav|wave/i.test(mimeType)) return MAX_WAV_OUTPUT_BYTES;
  if (clean === 'waveform_png' || clean === 'spectrogram_png' || /png/i.test(mimeType)) return Math.min(MAX_OUTPUT_BYTES, 16 * 1024 * 1024);
  return MAX_ENCODED_OUTPUT_BYTES;
}

function preallocatedConcat(clips, label = 'concat') {
  if (!Array.isArray(clips) || !clips.length) throw audioError('concat requires clips.', 400, 'audio_render_validation_failed');
  const sampleRate = clips[0].sampleRate;
  const channelCount = Math.max(...clips.map((clip) => ensureClip(clip).channelCount));
  const normalized = clips.map((clip) => toChannels(resample(clip, sampleRate), channelCount));
  const frames = normalized.reduce((sum, clip) => sum + clip.frames, 0);
  const out = makeClip(channelCount, frames, sampleRate, 0, label);
  let offset = 0;
  for (const clip of normalized) {
    for (let ch = 0; ch < channelCount; ch++) out.channels[ch].set(clip.channels[ch], offset);
    offset += clip.frames;
  }
  return out;
}

async function mapLimitOrdered(items, concurrency, worker) {
  const max = Math.max(1, Math.min(8, Math.floor(Number(concurrency) || SPEECH_SEQUENCE_DEFAULT_CONCURRENCY)));
  const results = new Array(items.length);
  let next = 0;
  let active = 0;
  let maxActive = 0;
  let failed = false;
  return await new Promise((resolve, reject) => {
    const launch = () => {
      if (failed) return;
      if (next >= items.length && active === 0) return resolve({results, maxActive});
      while (active < max && next < items.length) {
        const index = next++;
        active += 1;
        maxActive = Math.max(maxActive, active);
        Promise.resolve(worker(items[index], index))
          .then((value) => { results[index] = value; })
          .catch((err) => { failed = true; reject(err); })
          .finally(() => { active -= 1; launch(); });
      }
    };
    launch();
  });
}

function encodeWav(clip, bitDepth = 16) {
  ensureClip(clip);
  if (bitDepth !== 16) throw audioError('Only PCM16 WAV export is currently supported.', 400, 'audio_render_unsupported_format');
  const bytesPerSample = 2;
  const dataSize = clip.frames * clip.channelCount * bytesPerSample;
  const buffer = Buffer.alloc(44 + dataSize);
  buffer.write('RIFF', 0); buffer.writeUInt32LE(36 + dataSize, 4); buffer.write('WAVE', 8);
  buffer.write('fmt ', 12); buffer.writeUInt32LE(16, 16); buffer.writeUInt16LE(1, 20); buffer.writeUInt16LE(clip.channelCount, 22);
  buffer.writeUInt32LE(clip.sampleRate, 24); buffer.writeUInt32LE(clip.sampleRate * clip.channelCount * bytesPerSample, 28);
  buffer.writeUInt16LE(clip.channelCount * bytesPerSample, 32); buffer.writeUInt16LE(bitDepth, 34); buffer.write('data', 36); buffer.writeUInt32LE(dataSize, 40);
  let o = 44;
  for (let i = 0; i < clip.frames; i++) for (let ch = 0; ch < clip.channelCount; ch++) {
    const s = Math.max(-1, Math.min(1, clip.channels[ch][i]));
    buffer.writeInt16LE(s < 0 ? Math.round(s * 32768) : Math.round(s * 32767), o); o += 2;
  }
  return buffer;
}

function decodeWav(buffer) {
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') throw audioError('Only PCM WAV sources can be decoded by the initial audio.render source loader.', 400, 'audio_render_unsupported_source');
  let pos = 12, fmt = null, dataStart = -1, dataSize = 0;
  while (pos + 8 <= buffer.length) {
    const id = buffer.toString('ascii', pos, pos + 4); const size = buffer.readUInt32LE(pos + 4); pos += 8;
    if (id === 'fmt ') fmt = {format: buffer.readUInt16LE(pos), channels: buffer.readUInt16LE(pos + 2), sampleRate: buffer.readUInt32LE(pos + 4), bits: buffer.readUInt16LE(pos + 14)};
    if (id === 'data') { dataStart = pos; dataSize = size; break; }
    pos += size + (size % 2);
  }
  if (!fmt || fmt.format !== 1 || fmt.bits !== 16 || dataStart < 0) throw audioError('Only PCM16 WAV sources are supported.', 400, 'audio_render_unsupported_source');
  const frames = Math.floor(dataSize / (fmt.channels * 2));
  const out = makeClip(fmt.channels, frames, fmt.sampleRate, 0, 'source');
  let o = dataStart;
  for (let i = 0; i < frames; i++) for (let ch = 0; ch < fmt.channels; ch++) { out.channels[ch][i] = buffer.readInt16LE(o) / 32768; o += 2; }
  return out;
}


function canonicalCharacterProfile(character) {
  const key = safeText(character, 120).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  return key ? CANONICAL_CHARACTER_PROFILES[key] || null : null;
}

function optionalFinite(value, label, min, max, fallback = undefined) {
  if (value === undefined || value === null || value === '') return fallback;
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw audioError(label + ' must be a finite number between ' + min + ' and ' + max + '.', 400, 'audio_render_validation_failed');
  }
  return value;
}

function validateEmotion(value, fallback = 'neutral') {
  const emotion = safeText(value, 80).toLowerCase() || fallback;
  if (!CARTESIA_SUPPORTED_EMOTION_SET.has(emotion)) {
    throw audioError('emotion must be one of: ' + CARTESIA_SUPPORTED_EMOTIONS.join(', ') + '.', 400, 'audio_render_validation_failed');
  }
  return emotion;
}

function resolveSpeechProfile(op = {}, context = {}) {
  const profile = canonicalCharacterProfile(op.character);
  const defaults = context.speechDefaults && typeof context.speechDefaults === 'object' && !Array.isArray(context.speechDefaults) ? context.speechDefaults : {};
  const hasExplicitVoice = safeText(op.voiceId, 160) || safeText(op.voiceName, 120);
  if (!profile && !hasExplicitVoice) {
    throw audioError('speech requires character, voiceId, or voiceName.', 400, 'audio_render_validation_failed');
  }
  const pickText = (key, max, fallback = '') => op[key] !== undefined ? safeText(op[key], max) : fallback;
  const defaultPitch = defaults.pitchSemitones === undefined ? 0 : cartesiaPitchShift.safePitchSemitones(defaults.pitchSemitones, 'speechDefaults.pitchSemitones');
  const resolved = {
    provider: 'cartesia',
    character: profile ? profile.character : safeText(op.character, 120),
    canonicalCharacter: Boolean(profile),
    voiceName: pickText('voiceName', 120, (profile && profile.voiceName) || safeText(defaults.voiceName, 120) || CARTESIA_DEFAULT_VOICE_NAME),
    voiceId: pickText('voiceId', 160, (profile && profile.voiceId) || safeText(defaults.voiceId, 160)),
    modelId: pickText('modelId', 120, (profile && profile.modelId) || safeText(defaults.modelId, 120) || CARTESIA_DEFAULT_MODEL_ID),
    speed: optionalFinite(op.speed, 'speed', 0.6, 1.5, profile && profile.speed !== undefined ? profile.speed : optionalFinite(defaults.speed, 'speechDefaults.speed', 0.6, 1.5, undefined)),
    volume: optionalFinite(op.volume, 'volume', 0.5, 2.0, optionalFinite(defaults.volume, 'speechDefaults.volume', 0.5, 2.0, undefined)),
    emotion: validateEmotion(op.emotion === undefined ? defaults.emotion : op.emotion, validateEmotion(defaults.emotion, 'neutral')),
    pitchSemitones: op.pitchSemitones === undefined
      ? (profile && profile.pitchSemitones !== undefined ? cartesiaPitchShift.safePitchSemitones(profile.pitchSemitones, 'canonical pitchSemitones') : defaultPitch)
      : cartesiaPitchShift.safePitchSemitones(op.pitchSemitones, 'pitchSemitones'),
    direction: profile ? profile.direction : '',
  };
  if (!resolved.voiceId && !resolved.voiceName) resolved.voiceName = CARTESIA_DEFAULT_VOICE_NAME;
  return resolved;
}

function pcm16ToClip(pcm, sampleRate, channels = 1, label = 'speech') {
  const channelBuffers = cartesiaPitchShift.pcm16ToFloat32Channels(pcm, channels);
  return new Clip(channelBuffers, sampleRate, label);
}

async function synthesizeSpeechClip(op = {}, context = {}, overrides = {}) {
  const rawText = overrides.text !== undefined ? overrides.text : op.text || op.transcript;
  const submittedText = typeof rawText === 'string' ? rawText : '';
  const text = safeText(rawText, SPEECH_MAX_TEXT_CHARS);
  if (!text) throw audioError('speech.text is required.', 400, 'audio_render_validation_failed');
  const profile = resolveSpeechProfile({...op, ...overrides}, context);
  const sampleRate = Math.max(8000, Math.min(CARTESIA_SPEECH_SAMPLE_RATE_MAX, Math.floor(safeNumber(op.sampleRate, context.sampleRate || DEFAULT_SAMPLE_RATE)) || DEFAULT_SAMPLE_RATE));
  const generationConfig = {emotion: profile.emotion};
  if (profile.speed !== undefined) generationConfig.speed = profile.speed;
  if (profile.volume !== undefined) generationConfig.volume = profile.volume;
  const startedAtMs = Date.now();
  const speech = await openCartesiaStream(text, {
    apiKeyGetter: context.cartesiaApiKey,
    voiceName: profile.voiceName,
    voiceId: profile.voiceId,
    modelId: profile.modelId,
    format: 'raw',
    sampleRate,
    generationConfig,
  });
  const response = speech.response;
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    const err = new Error('Cartesia speech HTTP ' + response.status + (detail ? ': ' + safeText(detail, 500) : ''));
    err.status = response.status;
    err.failureKind = response.status === 429 ? 'audio_render_speech_provider_rate_limited' : 'audio_render_speech_provider_failed';
    throw err;
  }
  const pcm = Buffer.from(await response.arrayBuffer());
  const providerElapsedMs = Date.now() - startedAtMs;
  if (!pcm.length) throw audioError('Cartesia returned empty speech audio.', 502, 'audio_render_speech_provider_empty');
  if ((pcm.length & 1) === 1) throw audioError('Cartesia returned odd-length PCM for speech.', 502, 'audio_render_speech_provider_pcm_invalid');
  const shifted = profile.pitchSemitones === 0
    ? {pcm, bypassed: true, processor: 'none', pitchScale: 1, inputFrames: pcm.length / 2, outputFrames: pcm.length / 2, durationRatio: 1}
    : await cartesiaPitchShift.pitchShiftPcm16(pcm, {sampleRate, channels: 1, pitchSemitones: profile.pitchSemitones});
  let clip = pcm16ToClip(shifted.pcm, sampleRate, 1, safeText(overrides.label || op.label || op.id, 120) || 'speech');
  if (context.sampleRate && context.sampleRate !== sampleRate) clip = resample(clip, context.sampleRate);
  const takeName = safeText(overrides.takeName || op.takeName || op.takeId || op.id, 120) || ('speech_' + (context.speechProvenance.length + 1));
  const inputFrames = shifted.inputFrames || (pcm.length / 2);
  const outputFrames = shifted.outputFrames || (shifted.pcm.length / 2);
  context.usesCartesia = true;
  const provenance = {
    takeName,
    provider: 'cartesia',
    segmentIndex: overrides.segmentIndex === undefined ? null : overrides.segmentIndex,
    speaker: safeText(overrides.speaker || op.speaker, 120),
    character: profile.character,
    canonicalCharacter: profile.canonicalCharacter,
    voiceName: speech.voiceName,
    voiceId: speech.voiceId,
    modelId: speech.modelId,
    emotionRequested: profile.emotion,
    generationConfig: speech.generationConfig || generationConfig,
    speed: profile.speed === undefined ? null : profile.speed,
    volume: profile.volume === undefined ? null : profile.volume,
    pitchSemitones: profile.pitchSemitones,
    pitchScale: shifted.pitchScale,
    pitchProcessor: shifted.processor,
    pitchBypassed: Boolean(shifted.bypassed),
    inputFrameCount: inputFrames,
    outputFrameCount: outputFrames,
    durationRatio: shifted.durationRatio || (outputFrames / Math.max(1, inputFrames)),
    duration: clip.duration,
    sampleRate,
    channelCount: 1,
    providerByteCount: pcm.length,
    byteCount: shifted.pcm.length,
    inputByteCount: pcm.length,
    submittedCharCount: submittedText.length,
    normalizedCharCount: text.length,
    textCharCount: text.length,
    transcriptSha256: sha256Hex(Buffer.from(text, 'utf8')),
    whitespaceNormalization: submittedText === text ? 'unchanged' : 'trimmed_or_clipped_by_safeText',
    ssmlCompatible: /<[^>]+>/.test(text),
    direction: profile.direction,
    providerTimingMs: providerElapsedMs,
    retryCount: 0,
  };
  if (!overrides.deferProvenance) context.speechProvenance.push(provenance);
  if (typeof context.onSpeechTake === 'function') await context.onSpeechTake(provenance);
  return {clip, profile, speech, provenance};
}

async function ffmpegEncode(inputWav, format, timeoutMs = DEFAULT_TIMEOUT_MS) {
  if (process.env.HOME_CENTER_AUDIO_RENDER_TEST_FAKE_OGG === '1' && format === 'ogg') {
    const digest = sha256Hex(inputWav);
    return Buffer.concat([Buffer.from('OggS\0home-center-test-vorbis-placeholder\0'), Buffer.from(digest, 'ascii')]);
  }
  let ffmpegPath = '';
  try { ffmpegPath = require('ffmpeg-static'); } catch (_) { ffmpegPath = process.env.FFMPEG_PATH || 'ffmpeg'; }
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'home-audio-'));
  const inputPath = path.join(tmp, 'input.wav');
  const outputPath = path.join(tmp, 'output.' + format);
  try {
    await fs.writeFile(inputPath, inputWav);
    const args = ['-hide_banner', '-loglevel', 'error', '-y', '-i', inputPath];
    if (format === 'ogg') args.push('-codec:a', 'libvorbis', '-q:a', '5');
    else if (format === 'flac') args.push('-codec:a', 'flac');
    else if (format === 'mp3') args.push('-codec:a', 'libmp3lame', '-b:a', '192k');
    else throw audioError('Unsupported encoded format: ' + format, 400, 'audio_render_unsupported_format');
    args.push(outputPath);
    await new Promise((resolve, reject) => {
      const child = spawn(ffmpegPath, args, {stdio: ['ignore', 'ignore', 'pipe'], shell: false, env: {PATH: process.env.PATH || ''}});
      let stderr = '';
      const timer = setTimeout(() => { child.kill('SIGKILL'); reject(audioError('Audio encoder timed out.', 504, 'audio_render_encoder_timeout')); }, timeoutMs);
      child.stderr.on('data', (chunk) => { stderr += String(chunk).slice(0, 4000); });
      child.on('error', (err) => { clearTimeout(timer); reject(audioError('Audio encoder failed to start: ' + err.message, 500, 'audio_render_encoder_failed')); });
      child.on('exit', (code) => { clearTimeout(timer); code === 0 ? resolve() : reject(audioError('Audio encoder failed: ' + stderr.slice(0, 500), 500, 'audio_render_encoder_failed')); });
    });
    const out = await fs.readFile(outputPath);
    if (out.length > outputByteLimit(format)) throw audioError('Encoded output exceeds size limit.', 413, 'audio_render_output_too_large');
    return out;
  } finally {
    await fs.rm(tmp, {recursive: true, force: true}).catch(() => {});
  }
}

async function ffmpegEncodeClip(clip, format, timeoutMs = DEFAULT_TIMEOUT_MS, onProgress = null) {
  ensureClip(clip);
  if (process.env.HOME_CENTER_AUDIO_RENDER_TEST_FAKE_OGG === '1' && format === 'ogg') {
    const digest = sha256Hex(encodeWav(clip));
    return Buffer.concat([Buffer.from('OggS\0home-center-test-vorbis-placeholder\0'), Buffer.from(digest, 'ascii')]);
  }
  let ffmpegPath = '';
  try { ffmpegPath = require('ffmpeg-static'); } catch (_) { ffmpegPath = process.env.FFMPEG_PATH || 'ffmpeg'; }
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'home-audio-stream-'));
  const outputPath = path.join(tmp, 'output.' + format);
  let child = null;
  try {
    const args = ['-hide_banner', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', String(clip.sampleRate), '-ac', String(clip.channelCount), '-i', 'pipe:0'];
    if (format === 'ogg') args.push('-codec:a', 'libvorbis', '-q:a', '5');
    else if (format === 'flac') args.push('-codec:a', 'flac');
    else if (format === 'mp3') args.push('-codec:a', 'libmp3lame', '-b:a', '192k');
    else throw audioError('Unsupported encoded format: ' + format, 400, 'audio_render_unsupported_format');
    args.push(outputPath);
    child = spawn(ffmpegPath, args, {stdio: ['pipe', 'ignore', 'pipe'], shell: false, env: {PATH: process.env.PATH || ''}});
    let stderr = '';
    child.stderr.on('data', (chunk) => { stderr += String(chunk).slice(0, 4000); });
    child.stdin.on('error', () => {});
    const exitPromise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => { child.kill('SIGKILL'); reject(audioError('Audio encoder timed out.', 504, 'audio_render_encoder_timeout')); }, timeoutMs);
      child.on('error', (err) => { clearTimeout(timer); reject(audioError('Audio encoder failed to start: ' + err.message, 500, 'audio_render_encoder_failed')); });
      child.on('exit', (code) => { clearTimeout(timer); code === 0 ? resolve() : reject(audioError('Audio encoder failed: ' + stderr.slice(0, 500), 500, 'audio_render_encoder_failed')); });
    });
    const blockFrames = 65536;
    const totalBlocks = Math.max(1, Math.ceil(clip.frames / blockFrames));
    for (let blockIndex = 0; blockIndex < totalBlocks; blockIndex++) {
      const start = blockIndex * blockFrames;
      const end = Math.min(clip.frames, start + blockFrames);
      const pcm = Buffer.allocUnsafe((end - start) * clip.channelCount * 2);
      let offset = 0;
      for (let frame = start; frame < end; frame++) for (let channel = 0; channel < clip.channelCount; channel++) {
        const sample = Math.max(-1, Math.min(1, clip.channels[channel][frame]));
        pcm.writeInt16LE(sample < 0 ? Math.round(sample * 32768) : Math.round(sample * 32767), offset);
        offset += 2;
      }
      if (!child.stdin.write(pcm)) await new Promise((resolve) => child.stdin.once('drain', resolve));
      if (typeof onProgress === 'function') await onProgress({phase: 'encoding', format, blockIndex: blockIndex + 1, blockCount: totalBlocks, framesProcessed: end, totalFrames: clip.frames});
      await new Promise((resolve) => setImmediate(resolve));
    }
    child.stdin.end();
    await exitPromise;
    const out = await fs.readFile(outputPath);
    if (out.length > outputByteLimit(format)) throw audioError('Encoded output exceeds size limit.', 413, 'audio_render_output_too_large');
    return out;
  } catch (err) {
    if (child && child.exitCode === null) child.kill('SIGKILL');
    throw err;
  } finally {
    await fs.rm(tmp, {recursive: true, force: true}).catch(() => {});
  }
}

function crc32(buf) {
  let table = crc32.table;
  if (!table) {
    table = crc32.table = Array.from({length: 256}, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  }
  let c = 0xffffffff;
  for (const b of buf) c = table[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const t = Buffer.from(type, 'ascii');
  const out = Buffer.alloc(12 + data.length);
  out.writeUInt32BE(data.length, 0); t.copy(out, 4); data.copy(out, 8);
  out.writeUInt32BE(crc32(Buffer.concat([t, data])), 8 + data.length);
  return out;
}

function makePng(width, height, pixelFn) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y++) {
    const row = y * (width * 4 + 1); raw[row] = 0;
    for (let x = 0; x < width; x++) {
      const [r, g, b, a] = pixelFn(x, y);
      const o = row + 1 + x * 4; raw[o] = r; raw[o + 1] = g; raw[o + 2] = b; raw[o + 3] = a;
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), pngChunk('IHDR', ihdr), pngChunk('IDAT', zlib.deflateSync(raw)), pngChunk('IEND', Buffer.alloc(0))]);
}

function waveformPng(clip, width = 900, height = 260) {
  const mono = mixdownMono(clip);
  const peaks = Array.from({length: width}, (_, x) => {
    const a = Math.floor(x * mono.frames / width), b = Math.max(a + 1, Math.floor((x + 1) * mono.frames / width));
    let p = 0; for (let i = a; i < b; i++) p = Math.max(p, Math.abs(mono.channels[0][i] || 0)); return p;
  });
  return makePng(width, height, (x, y) => {
    const mid = height / 2; const amp = peaks[x] * (height * 0.46);
    return Math.abs(y - mid) <= amp ? [29, 122, 128, 255] : [248, 250, 252, 255];
  });
}

function spectrogramPng(clip, width = 900, height = 360) {
  const mono = mixdownMono(clip);
  const bins = 96, win = 1024;
  const cols = Array.from({length: width}, (_, x) => {
    const start = Math.floor(x * Math.max(1, mono.frames - win) / width);
    const mags = [];
    for (let b = 0; b < bins; b++) {
      const freq = 40 * Math.pow(clip.sampleRate / 80 / 40, b / (bins - 1));
      let re = 0, im = 0;
      for (let n = 0; n < win && start + n < mono.frames; n++) {
        const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * n / (win - 1));
        const ph = 2 * Math.PI * freq * n / clip.sampleRate;
        const s = mono.channels[0][start + n] * w;
        re += s * Math.cos(ph); im -= s * Math.sin(ph);
      }
      mags.push(Math.log10(1 + Math.sqrt(re * re + im * im) / win * 80));
    }
    return mags;
  });
  return makePng(width, height, (x, y) => {
    const b = Math.floor((1 - y / (height - 1)) * (bins - 1));
    const v = Math.max(0, Math.min(1, cols[x][b]));
    return [Math.round(18 + v * 220), Math.round(28 + v * 90), Math.round(42 + v * 40), 255];
  });
}

function layerSwordImpact(seed, sampleRate) {
  const metal = envelope(tone({frequency: 2400, duration: 0.08, sampleRate, channels: 1, gain: 0.9}), [{t:0,v:0},{t:0.003,v:1},{t:0.08,v:0}]);
  const body = envelope(biquadLike(noise({duration: 0.32, sampleRate, channels: 1, gain: 0.9, seed: seed + ':body', color: 'brown'}), 'lowpass', 180), [{t:0,v:0},{t:0.01,v:1},{t:0.32,v:0}]);
  const ring = envelope(tone({frequency: 910, duration: 1.25, sampleRate, channels: 1, gain: 0.45}), [{t:0,v:0.8},{t:0.18,v:0.35},{t:1.25,v:0}]);
  const tendon = envelope(biquadLike(distort(noise({duration: 0.42, sampleRate, channels: 1, gain: 0.38, seed: seed + ':tendon', color: 'pink'}), 4), 'bandpass', 620), [{t:0,v:0},{t:0.035,v:0.8},{t:0.42,v:0}]);
  const env = reverb(envelope(noise({duration: 1.4, sampleRate, channels: 1, gain: 0.12, seed: seed + ':space', color: 'pink'}), [{t:0,v:0.4},{t:1.4,v:0}]), 0.28, 0.4);
  const mix = timeline({duration: 1.55, sampleRate, channels: 2, items: [
    {clip: pan(metal, -0.1), at: 0, gainDb: -3}, {clip: pan(body, 0.03), at: 0.012, gainDb: -5},
    {clip: pan(ring, 0.18), at: 0.025, gainDb: -10}, {clip: pan(tendon, -0.24), at: 0.05, gainDb: -15}, {clip: pan(env, 0), at: 0.02, gainDb: -18},
  ]});
  return {mix: limit(normalizePeak(mix, -1.2), -0.5), stems: {metal, body, ring, tendon, reflection: env}};
}

function layerTavernCellar(seed, sampleRate, duration = 20) {
  const room = loop(biquadLike(noise({duration: 4, sampleRate, channels: 1, gain: 0.12, seed: seed + ':room', color: 'brown'}), 'lowpass', 90), duration);
  const fire = loop(biquadLike(noise({duration: 2.5, sampleRate, channels: 1, gain: 0.18, seed: seed + ':fire', color: 'pink'}), 'bandpass', 950), duration);
  const air = loop(biquadLike(noise({duration: 5, sampleRate, channels: 1, gain: 0.08, seed: seed + ':air', color: 'pink'}), 'highpass', 700), duration);
  const rng = new Rng(seed + ':wood');
  const knocks = [];
  for (let i = 0; i < 16; i++) knocks.push({clip: envelope(tone({frequency: 90 + rng.next() * 170, duration: 0.18, sampleRate, channels: 1, gain: 0.13}), [{t:0,v:0},{t:0.01,v:1},{t:0.18,v:0}]), at: 0.6 + rng.next() * (duration - 1.2), gainDb: -10});
  const detail = timeline({duration, sampleRate, channels: 2, items: knocks.map((k, i) => ({clip: pan(k.clip, i % 2 ? -0.4 : 0.4), at: k.at, gainDb: k.gainDb}))});
  let mix = timeline({duration, sampleRate, channels: 2, items: [
    {clip: pan(room, 0), at: 0, gainDb: -16}, {clip: pan(fire, -0.28), at: 0, gainDb: -22}, {clip: pan(air, 0.25), at: 0, gainDb: -25}, {clip: detail, at: 0, gainDb: -6},
  ]});
  const fadeSeconds = 1.2;
  const tail = trim(mix, duration - fadeSeconds, fadeSeconds);
  const head = trim(mix, 0, fadeSeconds);
  const seam = crossfade(tail, head, fadeSeconds);
  mix = fade(fade(mix, fadeSeconds, 'in'), fadeSeconds, 'out');
  return {mix: limit(normalizePeak(mix, -3), -1), stems: {room, fire, air, detail}, seam};
}

async function materializeSources({google, auth, sources = {}}) {
  const out = {};
  for (const [name, source] of Object.entries(sources || {})) {
    if (!/^[A-Za-z0-9_.-]{1,80}$/.test(name)) throw audioError('Invalid source name: ' + name, 400, 'audio_render_invalid_source');
    let buffer, provider = 'inline', mimeType = 'application/octet-stream', originalRef = '';
    if (source && typeof source === 'object' && source.contentBase64) {
      buffer = Buffer.from(String(source.contentBase64), 'base64');
      mimeType = safeText(source.mimeType, 120) || mimeType;
      originalRef = 'inline:' + name;
    } else if (source && typeof source === 'object' && source.ref) {
      const ref = safeText(source.ref, 1200);
      originalRef = ref;
      if (ref.toLowerCase().startsWith('drive://')) {
        if (!google || !auth) throw audioError('drive:// sources require Google OAuth context.', 401, 'audio_render_source_auth_required');
        const fileId = ref.slice('drive://'.length).split(/[?#]/)[0];
        const drive = google.drive({version: 'v3', auth});
        const metadata = await drive.files.get({fileId, fields: 'id,name,mimeType,size', supportsAllDrives: true});
        mimeType = metadata.data.mimeType || mimeType;
        const media = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
        buffer = Buffer.isBuffer(media.data) ? media.data : Buffer.from(media.data);
        provider = 'google_drive';
      } else if (ref.toLowerCase().startsWith('gs://')) {
        const parsed = parseGsRef(ref);
        if (!parsed || parsed.bucket !== GENERATED_ARTIFACT_BUCKET) throw audioError('gs:// sources must reference the canonical generated artifact bucket.', 400, 'audio_render_source_bucket_forbidden');
        const artifact = await inspectGeneratedArtifact(ref);
        if (!artifact || !artifact.bytes) throw audioError('Generated artifact source not found: ' + ref, 404, 'audio_render_source_not_found');
        buffer = Buffer.from(artifact.bytes);
        mimeType = artifact.mimeType || mimeType;
        provider = 'generated_artifact_bucket';
      } else {
        throw audioError('Unsupported source ref provider for ' + name + ': use canonical gs://, drive://, or inline contentBase64.', 400, 'audio_render_unsupported_source_ref');
      }
    } else {
      throw audioError('Source ' + name + ' must provide contentBase64 or ref.', 400, 'audio_render_invalid_source');
    }
    if (!buffer || buffer.length > MAX_SOURCE_BYTES) throw audioError('Source ' + name + ' is missing or too large.', 413, 'audio_render_source_too_large');
    const expectedSha = safeText(source.sha256 || source.expectedSha256, 128).toLowerCase();
    const digest = sha256Hex(buffer);
    if (expectedSha && expectedSha !== digest) throw audioError('Source ' + name + ' sha256 mismatch.', 400, 'audio_render_source_hash_mismatch');
    let clip = null, decoded = null;
    if (/wav|wave/i.test(mimeType) || String(source.name || '').toLowerCase().endsWith('.wav')) {
      clip = decodeWav(buffer);
      decoded = measure(clip);
    }
    out[name] = {name, originalRef, provider, mimeType, byteCount: buffer.length, sha256: digest, decoded, clip};
  }
  return out;
}

async function applyOp(op, clips, sources, context) {
  const id = safeText(op.id, 120);
  const type = safeText(op.op || op.type, 80);
  const sr = Math.floor(safeNumber(op.sampleRate, context.sampleRate));
  const one = (field = 'clip') => ensureClip(clips.get(safeText(op[field], 120)), field);
  const list = (field = 'clips') => (op[field] || []).map((id) => ensureClip(clips.get(safeText(id, 120)), 'clip ' + id));
  let clip = null;
  if (type === 'load') {
    const source = sources[safeText(op.source || op.name, 80)];
    if (!source || !source.clip) throw audioError('Source is not decoded audio: ' + (op.source || op.name), 400, 'audio_render_source_not_audio');
    clip = source.clip;
  } else if (type === 'silence') clip = silence({duration: safeNumber(op.duration, 1), sampleRate: sr, channels: safeNumber(op.channels, 2)});
  else if (type === 'tone') clip = tone({frequency: safeNumber(op.frequency, 440), duration: safeNumber(op.duration, 1), sampleRate: sr, channels: safeNumber(op.channels, 1), gain: safeNumber(op.gain, 0.5), phase: safeNumber(op.phase, 0)});
  else if (type === 'noise') clip = noise({duration: safeNumber(op.duration, 1), sampleRate: sr, channels: safeNumber(op.channels, 1), gain: safeNumber(op.gain, 0.25), seed: op.seed || context.seed, color: safeText(op.color, 20) || 'white'});
  else if (type === 'trim' || type === 'slice') clip = trim(one(), safeNumber(op.start, 0), op.duration === undefined ? null : safeNumber(op.duration, 1));
  else if (type === 'concat') clip = concat(list());
  else if (type === 'loop') clip = loop(one(), safeNumber(op.duration, 1));
  else if (type === 'fade_in') clip = fade(one(), safeNumber(op.seconds, op.duration || 0.01), 'in');
  else if (type === 'fade_out') clip = fade(one(), safeNumber(op.seconds, op.duration || 0.01), 'out');
  else if (type === 'crossfade') clip = crossfade(ensureClip(clips.get(safeText(op.a, 120)), 'a'), ensureClip(clips.get(safeText(op.b, 120)), 'b'), safeNumber(op.seconds, 0.1));
  else if (type === 'gain') clip = gain(one(), safeNumber(op.db, op.gainDb || 0));
  else if (type === 'normalize_peak') clip = normalizePeak(one(), safeNumber(op.targetDb, -1));
  else if (type === 'normalize_lufs') clip = normalizeLufs(one(), safeNumber(op.targetLufs, -16));
  else if (type === 'pan') clip = pan(one(), safeNumber(op.value, op.pan || 0));
  else if (type === 'stereo' || type === 'channels') clip = toChannels(one(), safeNumber(op.channels, 2));
  else if (type === 'pitch_shift') clip = pitchShift(one(), safeNumber(op.semitones, op.pitchSemitones || 0));
  else if (type === 'time_stretch') clip = timeStretch(one(), safeNumber(op.factor, 1));
  else if (type === 'reverse') clip = reverse(one());
  else if (type === 'filter' || type === 'eq') clip = biquadLike(one(), safeText(op.kind, 20) || 'lowpass', safeNumber(op.frequency, 1000));
  else if (type === 'compression' || type === 'compress') clip = compress(one(), safeNumber(op.thresholdDb, -12), safeNumber(op.ratio, 4));
  else if (type === 'limiting' || type === 'limit') clip = limit(one(), safeNumber(op.ceilingDb, -0.5));
  else if (type === 'distortion' || type === 'saturation' || type === 'distort') clip = distort(one(), safeNumber(op.drive, 1.5));
  else if (type === 'delay') clip = delay(one(), safeNumber(op.seconds, 0.12), safeNumber(op.feedback, 0.25), safeNumber(op.wet, 0.25));
  else if (type === 'reverb') clip = reverb(one(), safeNumber(op.amount, 0.2), safeNumber(op.seconds, 0.35));
  else if (type === 'envelope') clip = envelope(one(), op.points || []);
  else if (type === 'resample') clip = resample(one(), safeNumber(op.sampleRate, context.sampleRate));
  else if (type === 'timeline' || type === 'layer') clip = timeline({duration: safeNumber(op.duration, 1), sampleRate: sr, channels: safeNumber(op.channels, 2), items: (op.items || []).map((item) => ({...item, clip: ensureClip(clips.get(safeText(item.clip, 120)), 'timeline item')}))});
  else if (type === 'block_mix') clip = await blockMix({duration: safeNumber(op.duration, 1), sampleRate: sr, channels: safeNumber(op.channels, 2), blockFrames: safeNumber(op.blockFrames, 65536), items: (op.items || []).map((item) => ({...item, clip: ensureClip(clips.get(safeText(item.clip, 120)), 'block_mix item'), duckClip: safeText(item.duckBy, 120) ? ensureClip(clips.get(safeText(item.duckBy, 120)), 'block_mix duckBy') : null})), onProgress: context.onRenderProgress});
  else if (type === 'duck') clip = duck(one('mix'), one('keyedBy'), safeNumber(op.amountDb, 5));
  else if (type === 'speech') {
    const synthesized = await synthesizeSpeechClip(op, context);
    clip = synthesized.clip;
  }
  else if (type === 'audition') {
    const emotions = Array.isArray(op.emotions) ? op.emotions.map((emotion) => validateEmotion(emotion)) : [];
    if (!emotions.length || emotions.length > 24) throw audioError('audition.emotions must contain 1 to 24 supported emotions.', 400, 'audio_render_validation_failed');
    const prefix = safeText(op.takePrefix || op.id || 'take', 80).replace(/[^A-Za-z0-9_.-]+/g, '_') || 'take';
    const takeClips = [];
    for (const emotion of emotions) {
      const takeId = prefix + '_' + emotion;
      const synthesized = await synthesizeSpeechClip(op, context, {emotion, takeName: takeId, label: takeId});
      clips.set(takeId, synthesized.clip);
      takeClips.push(synthesized.clip);
      if (op.outputTakes !== false) context.auditionTakes.push({takeName: takeId, emotionRequested: emotion});
    }
    const pause = silence({duration: safeNumber(op.pauseSeconds, 0.65), sampleRate: sr, channels: 1});
    clip = preallocatedConcat(takeClips.flatMap((take, index) => index ? [pause, take] : [take]), 'audition');
  }
  else if (type === 'speech_sequence') {
    const segments = Array.isArray(op.segments) ? op.segments : [];
    if (!segments.length || segments.length > SPEECH_SEQUENCE_MAX_SEGMENTS) throw audioError('speech_sequence.segments must contain 1 to ' + SPEECH_SEQUENCE_MAX_SEGMENTS + ' items.', 400, 'audio_render_validation_failed');
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i] && typeof segments[i] === 'object' && !Array.isArray(segments[i]) ? segments[i] : {};
      if (!safeText(seg.speaker, 120)) throw audioError('speech_sequence.segments[' + i + '].speaker is required.', 400, 'audio_render_validation_failed');
      if (!safeText(seg.character, 120) && !safeText(seg.voiceId, 160) && !safeText(seg.voiceName, 120)) throw audioError('speech_sequence.segments[' + i + '] requires character, voiceId, or voiceName.', 400, 'audio_render_validation_failed');
    }
    const pause = silence({duration: Math.max(0, Math.min(5, safeNumber(op.pauseMs, 0) / 1000)), sampleRate: sr, channels: 1});
    const requestedConcurrency = op.concurrency === undefined ? context.speechConcurrency : op.concurrency;
    const startedAtMs = Date.now();
    const {results, maxActive} = await mapLimitOrdered(segments, requestedConcurrency, async (segment, index) => {
      const seg = segment && typeof segment === 'object' && !Array.isArray(segment) ? segment : {};
      return await synthesizeSpeechClip({...seg, sampleRate: op.sampleRate || seg.sampleRate || sr}, context, {segmentIndex: index, speaker: seg.speaker, takeName: safeText(op.id, 80) + '_' + index, label: safeText(op.id, 80) + '_' + index, deferProvenance: true});
    });
    const parts = [];
    for (let i = 0; i < results.length; i++) {
      if (i > 0 && pause.frames) parts.push(pause);
      parts.push(results[i].clip);
    }
    clip = preallocatedConcat(parts, safeText(op.id, 80) || 'speech_sequence');
    const limitDb = op.master && typeof op.master === 'object' && op.master.limitDb !== undefined ? safeNumber(op.master.limitDb, -1) : -1;
    clip = limit(clip, limitDb);
    const sequenceProvenance = {
      id: safeText(op.id, 120),
      op: 'speech_sequence',
      segmentCount: segments.length,
      pauseMs: Math.max(0, Math.min(5000, Math.floor(safeNumber(op.pauseMs, 0)) || 0)),
      requestedConcurrency: Math.max(1, Math.min(8, Math.floor(Number(requestedConcurrency) || SPEECH_SEQUENCE_DEFAULT_CONCURRENCY))),
      maxActiveProviderCalls: maxActive,
      elapsedMs: Date.now() - startedAtMs,
      mastering: {limitDb, limiter: 'home_center_peak_limit'},
      submittedCharacterCount: segments.reduce((sum, seg) => sum + (typeof (seg && seg.text) === 'string' ? seg.text.length : 0), 0),
      normalizedCharacterCount: results.reduce((sum, item) => sum + item.provenance.normalizedCharCount, 0),
      segments: results.map((item, index) => ({...item.provenance, index, segmentIndex: index})),
    };
    context.speechSequences.push(sequenceProvenance);
    for (const item of sequenceProvenance.segments) context.speechProvenance.push(item);
  }
  else if (type === 'sword_impact') { const layered = layerSwordImpact(context.seed, sr); clip = layered.mix; Object.entries(layered.stems).forEach(([k, v]) => clips.set((op.stemPrefix || 'sword') + '_' + k, toChannels(resample(v, sr), 2))); }
  else if (type === 'tavern_cellar') { const layered = layerTavernCellar(context.seed, sr, safeNumber(op.duration, 20)); clip = layered.mix; clips.set((op.stemPrefix || 'tavern') + '_seam', layered.seam); Object.entries(layered.stems).forEach(([k, v]) => clips.set((op.stemPrefix || 'tavern') + '_' + k, toChannels(resample(v, sr), 2))); }
  else throw audioError('Unsupported audio recipe operation: ' + type, 400, 'audio_render_unsupported_operation');
  if (clip.duration > MAX_DURATION_SECONDS) throw audioError('Clip exceeds maximum duration.', 413, 'audio_render_duration_limit');
  if (id) clips.set(id, clip);
  return clip;
}

async function renderRecipe(recipe, sources, settings = {}) {
  if (!recipe || typeof recipe !== 'object' || Array.isArray(recipe)) throw audioError('Recipe must be a JSON object.', 400, 'audio_render_validation_failed');
  const sampleRate = Math.floor(safeNumber(recipe.sampleRate || settings.sampleRate, DEFAULT_SAMPLE_RATE));
  if (sampleRate < 8000 || sampleRate > 96000) throw audioError('sampleRate must be between 8000 and 96000.', 400, 'audio_render_validation_failed');
  const seed = safeText(recipe.seed || settings.seed || 'home-center-audio', 200);
  const graph = Array.isArray(recipe.graph) ? recipe.graph : [];
  if (!graph.length || graph.length > MAX_GRAPH_NODES) throw audioError('Recipe graph must contain 1 to ' + MAX_GRAPH_NODES + ' nodes.', 400, 'audio_render_validation_failed');
  const clips = new Map();
  const context = {sampleRate, seed, speechDefaults: recipe.speechDefaults || settings.speechDefaults || {}, cartesiaApiKey: settings.cartesiaApiKey || (() => ''), speechConcurrency: settings.speechConcurrency || recipe.speechConcurrency || SPEECH_SEQUENCE_DEFAULT_CONCURRENCY, onSpeechTake: settings.onSpeechTake, onRenderProgress: settings.onRenderProgress, speechProvenance: [], speechSequences: [], auditionTakes: [], usesCartesia: false};
  const graphStartedAtMs = Date.now();
  for (const op of graph) await applyOp(op || {}, clips, sources, context);
  const graphElapsedMs = Date.now() - graphStartedAtMs;
  const finalId = safeText(recipe.final || (graph[graph.length - 1] || {}).id, 120);
  const finalClip = ensureClip(clips.get(finalId), 'final clip');
  const outputs = Array.isArray(recipe.outputs) && recipe.outputs.length ? recipe.outputs : [{name: 'audio.wav', format: 'wav', clip: finalId}, {name: 'audio.ogg', format: 'ogg', clip: finalId}];
  const rendered = [];
  for (const output of outputs) {
    const name = safeText(output.name, 240) || ('audio.' + safeText(output.format, 10));
    const format = safeText(output.format || name.split('.').pop(), 20).toLowerCase();
    const clip = ensureClip(clips.get(safeText(output.clip || finalId, 120)), 'output clip');
    let bytes, mimeType;
    if (format === 'wav') { bytes = encodeWav(clip); mimeType = 'audio/wav'; }
    else if (format === 'ogg') { bytes = await ffmpegEncodeClip(clip, 'ogg', safeNumber(settings.timeoutMs, DEFAULT_TIMEOUT_MS), settings.onRenderProgress); mimeType = 'audio/ogg'; }
    else if (format === 'flac') { bytes = await ffmpegEncodeClip(clip, 'flac', safeNumber(settings.timeoutMs, DEFAULT_TIMEOUT_MS), settings.onRenderProgress); mimeType = 'audio/flac'; }
    else if (format === 'mp3') { bytes = await ffmpegEncodeClip(clip, 'mp3', safeNumber(settings.timeoutMs, DEFAULT_TIMEOUT_MS), settings.onRenderProgress); mimeType = 'audio/mpeg'; }
    else if (format === 'waveform_png') { bytes = waveformPng(clip); mimeType = 'image/png'; }
    else if (format === 'spectrogram_png') { bytes = spectrogramPng(clip); mimeType = 'image/png'; }
    else throw audioError('Unsupported export format: ' + format, 400, 'audio_render_unsupported_format');
    if (bytes.length > outputByteLimit(format, mimeType)) throw audioError('Output ' + name + ' exceeds byte limit for ' + format + '.', 413, 'audio_render_output_too_large');
    const m = measure(clip);
    rendered.push({name, format, mimeType, bytes, clipMetrics: m, byteCount: bytes.length, sha256: sha256Hex(bytes)});
  }
  return {clips, finalClip, rendered, finalMetrics: measure(finalClip), seed, sampleRate, phaseTimings: {graphElapsedMs}, speechProvenance: context.speechProvenance, speechSequences: context.speechSequences, auditionTakes: context.auditionTakes, usesCartesia: context.usesCartesia};
}

function audioArtifactContext(args = {}, rendered = null, item = null) {
  const settings = args.settings && typeof args.settings === 'object' && !Array.isArray(args.settings) ? args.settings : {};
  const stage = safeText(args.stage || settings.stage || (args.approved === true || settings.approved === true ? 'final' : 'voice-test'), 120) || 'voice-test';
  const project = safeText(args.project || settings.project || 'home-center', 160) || 'home-center';
  const owner = safeText(args.owner || settings.owner || 'drew', 120) || 'drew';
  const engine = rendered && rendered.usesCartesia ? 'cartesia' : safeText(args.engine || settings.engine || 'home-center-audio', 120) || 'home-center-audio';
  const artifactType = item && /^image\//.test(item.mimeType) ? 'image' : 'audio';
  return {owner, project, stage, engine, createdBy: 'home-center-mcp', jobId: safeText(args.jobId || settings.jobId, 180), commit: safeText(args.commit || settings.commit || process.env.K_REVISION || process.env.FUNCTION_TARGET || '', 80), approved: args.approved === true || settings.approved === true, requestId: safeText(args.requestId || args.idempotencyKey, 180), artifactType};
}

function shouldPublishAudioToDrive(args = {}, parentFolderId = '') {
  if (args.publishToDrive === false) return false;
  if (args.publishToDrive === true) return true;
  const settings = args.settings && typeof args.settings === 'object' && !Array.isArray(args.settings) ? args.settings : {};
  if (settings.publishToDrive === false) return false;
  if (settings.publishToDrive === true) return true;
  if (args.approved === true || settings.approved === true || safeText(args.stage || settings.stage, 80).toLowerCase() === 'final') return true;
  return true; // Backward-compatible mirror: existing audio.render clients still receive Drive resource links after GCS verification.
}

async function uploadVerified({google, auth, parentFolderId, item, artifactContext = {}, publishToDrive = true}) {
  const storageArtifact = await uploadGeneratedArtifact({...artifactContext, bytes: item.bytes, name: item.name, mimeType: item.mimeType});
  const driveArtifact = publishToDrive ? await publishGeneratedArtifactToDrive({google, auth, parentFolderId, artifact: storageArtifact, bytes: item.bytes}) : null;
  return {
    ...item,
    bytes: undefined,
    bucket: storageArtifact.bucket,
    object: storageArtifact.object,
    storageRef: storageArtifact.storageRef,
    durableRef: storageArtifact.storageRef,
    primaryStore: 'gcs',
    artifactBucket: GENERATED_ARTIFACT_BUCKET,
    metadata: storageArtifact.metadata,
    readbackByteCount: storageArtifact.readbackByteCount,
    readbackSha256: storageArtifact.readbackSha256,
    verified: true,
    drive: driveArtifact,
    driveDurableRef: driveArtifact && driveArtifact.durableRef || '',
    fileId: driveArtifact && driveArtifact.fileId || '',
    id: driveArtifact && driveArtifact.fileId || '',
    webViewLink: driveArtifact && driveArtifact.webViewLink || '',
    parentFolderId: driveArtifact && driveArtifact.parentFolderId || parentFolderId || '',
    chatGptFileRef: driveArtifact && driveArtifact.chatGptFileRef || null,
  };
}



async function ffmpegDecodeCheck(buffer, name, mimeType, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const lower = String(name || '').toLowerCase();
  if (lower.endsWith('.wav') || /wav|wave/i.test(mimeType)) {
    try {
      const clip = decodeWav(buffer);
      return {ok: true, decoder: 'home_center_pcm16_wav_decoder', duration: clip.duration, sampleRate: clip.sampleRate, channelCount: clip.channelCount};
    } catch (err) {
      return {ok: false, decoder: 'home_center_pcm16_wav_decoder', error: 'wav_decode_failed'};
    }
  }
  const encoded = lower.endsWith('.ogg') || /ogg/i.test(mimeType) || lower.endsWith('.mp3') || /mpeg|mp3/i.test(mimeType) || lower.endsWith('.flac') || /flac/i.test(mimeType);
  if (!encoded) return {ok: true, skipped: true, reason: 'not_an_audio_decode_target'};
  if (process.env.HOME_CENTER_AUDIO_RENDER_TEST_FAKE_OGG === '1' && (lower.endsWith('.ogg') || /ogg/i.test(mimeType))) {
    return {ok: true, skipped: true, reason: 'test_fake_ogg_placeholder'};
  }
  let ffmpegPath = '';
  try { ffmpegPath = require('ffmpeg-static'); } catch (_) { ffmpegPath = process.env.FFMPEG_PATH || 'ffmpeg'; }
  const ext = lower.endsWith('.mp3') || /mpeg|mp3/i.test(mimeType) ? 'mp3' : lower.endsWith('.flac') || /flac/i.test(mimeType) ? 'flac' : 'ogg';
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'home-audio-decode-'));
  const inputPath = path.join(tmp, 'input.' + ext);
  try {
    await fs.writeFile(inputPath, buffer);
    return await new Promise((resolve) => {
      const child = spawn(ffmpegPath, ['-hide_banner', '-v', 'error', '-i', inputPath, '-f', 'null', '-'], {stdio: ['ignore', 'ignore', 'pipe'], shell: false, env: {PATH: process.env.PATH || ''}});
      let stderr = '';
      const timer = setTimeout(() => { child.kill('SIGKILL'); resolve({ok: false, decoder: 'ffmpeg', error: 'decode_timeout'}); }, timeoutMs);
      child.stderr.on('data', (chunk) => { stderr += String(chunk).slice(0, 4000); });
      child.on('error', (err) => { clearTimeout(timer); resolve({ok: false, decoder: 'ffmpeg', error: 'decode_start_failed', detail: safeText(err.message, 300)}); });
      child.on('exit', (code) => { clearTimeout(timer); resolve(code === 0 ? {ok: true, decoder: 'ffmpeg'} : {ok: false, decoder: 'ffmpeg', error: 'decode_failed', exitCode: code, detail: safeText(stderr, 500)}); });
    });
  } finally {
    await fs.rm(tmp, {recursive: true, force: true}).catch(() => {});
  }
}

function inspectArtifactBytes(name, mimeType, buffer) {
  const lower = String(name || '').toLowerCase();
  if (lower.endsWith('.wav') || /wav|wave/i.test(mimeType)) {
    try { return {container: 'wav', ...wavHeaderInfo(buffer)}; } catch (err) { return {container: 'wav', valid: false, error: 'wav_header_invalid'}; }
  }
  if (lower.endsWith('.png') || /png/i.test(mimeType)) {
    const valid = buffer.length >= 24 && buffer[0] === 137 && buffer.slice(1, 4).toString('ascii') === 'PNG';
    return {container: 'png', valid, width: valid ? buffer.readUInt32BE(16) : 0, height: valid ? buffer.readUInt32BE(20) : 0};
  }
  if (lower.endsWith('.ogg') || /ogg/i.test(mimeType)) {
    return {container: 'ogg', valid: buffer.slice(0, 4).toString('ascii') === 'OggS', magic: buffer.slice(0, 4).toString('ascii')};
  }
  return {container: 'binary', valid: buffer.length > 0, magicHex: buffer.slice(0, 12).toString('hex')};
}

function wavHeaderInfo(buffer) {
  if (buffer.length < 44 || buffer.slice(0, 4).toString('ascii') !== 'RIFF' || buffer.slice(8, 12).toString('ascii') !== 'WAVE') {
    throw audioError('Invalid WAV header.', 400, 'audio_render_artifact_invalid_wav');
  }
  const channels = buffer.readUInt16LE(22);
  const sampleRate = buffer.readUInt32LE(24);
  const bits = buffer.readUInt16LE(34);
  const dataBytes = buffer.readUInt32LE(40);
  const duration = dataBytes / Math.max(1, sampleRate * channels * (bits / 8));
  return {valid: true, channels, sampleRate, bits, dataBytes, duration};
}

function cleanArtifactRef(value) {
  const ref = safeText(value && (value.durableRef || value.storageRef || value.ref || value.uri) || value, 1200);
  if (ref.toLowerCase().startsWith('gs://')) {
    const parsed = parseGsRef(ref);
    if (!parsed) throw audioError('Invalid GCS artifact ref.', 400, 'audio_render_artifact_ref_invalid');
    return {ref, provider: 'gcs', bucket: parsed.bucket, object: parsed.object};
  }
  if (!ref.toLowerCase().startsWith('drive://')) throw audioError('audio.render_artifacts accepts gs:// generated artifact refs and legacy drive:// published refs.', 400, 'audio_render_artifact_ref_invalid');
  const fileId = ref.slice('drive://'.length).split(/[?#]/)[0];
  if (!/^[A-Za-z0-9_.-]{8,220}$/.test(fileId)) throw audioError('Invalid Drive artifact ref.', 400, 'audio_render_artifact_ref_invalid');
  return {ref, provider: 'drive', fileId};
}

async function inspectAudioArtifactsOperation({google, auth, args = {}}) {
  const refs = Array.isArray(args.artifactRefs) ? args.artifactRefs : Array.isArray(args.refs) ? args.refs : [];
  if (!refs.length || refs.length > 40) throw audioError('artifactRefs must contain 1 to 40 gs:// generated artifact refs or legacy drive:// refs.', 400, 'audio_render_artifact_refs_required');
  const expectedByRef = new Map((Array.isArray(args.expected) ? args.expected : []).map((item) => [safeText(item.durableRef || item.storageRef || item.ref || item.uri, 1200), item]));
  const drive = google.drive({version: 'v3', auth});
  const artifacts = [];
  for (const raw of refs) {
    const cleaned = cleanArtifactRef(raw);
    let metadata = {};
    let bytes = null;
    let name = '';
    let mimeType = '';
    let webViewLink = '';
    if (cleaned.provider === 'gcs') {
      const artifact = await inspectGeneratedArtifact(cleaned.ref);
      bytes = artifact.bytes;
      metadata = artifact.metadata || {};
      name = artifact.name || '';
      mimeType = artifact.mimeType || metadata.mimeType || '';
    } else {
      const metadataResult = await drive.files.get({fileId: cleaned.fileId, fields: 'id,name,mimeType,size,webViewLink,parents', supportsAllDrives: true});
      metadata = metadataResult.data || {};
      const media = await drive.files.get({fileId: cleaned.fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
      bytes = Buffer.isBuffer(media.data) ? media.data : Buffer.from(media.data);
      name = metadata.name || '';
      mimeType = metadata.mimeType || '';
      webViewLink = metadata.webViewLink || '';
    }
    const digest = {byteCount: bytes.length, sha256: sha256Hex(bytes)};
    const expected = expectedByRef.get(cleaned.ref) || (raw && typeof raw === 'object' ? raw : {});
    const expectedByteCount = expected.byteCount === undefined || expected.byteCount === null ? null : Math.floor(safeNumber(expected.byteCount, -1));
    const expectedSha256 = safeText(expected.sha256 || expected.expectedSha256, 128).toLowerCase();
    const artifact = {
      durableRef: cleaned.ref,
      provider: cleaned.provider,
      fileId: cleaned.fileId || '',
      bucket: cleaned.bucket || '',
      object: cleaned.object || '',
      name,
      mimeType,
      webViewLink,
      byteCount: digest.byteCount,
      sha256: digest.sha256,
      expectedByteCount,
      expectedSha256,
      byteCountMatches: expectedByteCount === null ? true : expectedByteCount === digest.byteCount,
      sha256Matches: expectedSha256 ? expectedSha256 === digest.sha256 : true,
      header: inspectArtifactBytes(name, mimeType, bytes),
    };
    if (args.decodeCheck === true) artifact.decodeCheck = await ffmpegDecodeCheck(bytes, artifact.name, artifact.mimeType, safeNumber(args.timeoutMs, DEFAULT_TIMEOUT_MS));
    artifacts.push(artifact);
  }
  return {ok: artifacts.every((item) => item.byteCountMatches && item.sha256Matches && item.header.valid !== false && (!item.decodeCheck || item.decodeCheck.ok)), operation: 'audio.render_artifacts', artifactCount: artifacts.length, decodeCheck: args.decodeCheck === true, artifacts};
}

function audioContentFor(item, returnInlineAudio = true) {
  if (!returnInlineAudio || !item || !item.bytes || !/^audio\//.test(item.mimeType)) return null;
  if (item.bytes.length > INLINE_AUDIO_MAX_BYTES) return null;
  return {type: 'audio', data: item.bytes.toString('base64'), mimeType: item.mimeType, annotations: {audience: ['user'], priority: 1}};
}


function normalizeAudioRenderRequest(args = {}, helpers = {}) {
  const requestId = helpers.createRequestId ? helpers.createRequestId(args.requestId || args.idempotencyKey) : safeText(args.requestId || args.idempotencyKey, 160) || randomUUID();
  const settings = args.settings && typeof args.settings === 'object' && !Array.isArray(args.settings) ? args.settings : {};
  const recipe = sanitizeRecipeText(args.scriptText || args.recipeText);
  const normalizedInput = {scriptText: recipe, sources: args.sources || {}, settings};
  const inputSha256 = sha256Hex(Buffer.from(stableJson(normalizedInput), 'utf8'));
  return {requestId, settings, recipe, normalizedInput, inputSha256};
}

function audioRenderStatusOperationName(requestId) {
  return {operation: 'audio.render_status', args: {requestId}};
}

function countSpeechTakesInRecipe(recipe = {}) {
  const graph = Array.isArray(recipe.graph) ? recipe.graph : [];
  return graph.reduce((sum, op) => {
    const type = safeText(op && (op.op || op.type), 80).toLowerCase();
    if (type === 'speech_sequence') return sum + (Array.isArray(op.segments) ? op.segments.length : 0);
    if (type === 'speech') return sum + 1;
    if (type === 'audition') return sum + (Array.isArray(op.emotions) ? op.emotions.length : 0);
    return sum;
  }, 0);
}

function audioRenderJobRequest(args = {}, settings = {}) {
  return {
    scriptText: safeText(args.scriptText || args.recipeText, 2 * 1024 * 1024),
    sources: args.sources || {},
    settings,
    returnInlineAudio: args.returnInlineAudio === false ? false : undefined,
    publishToDrive: args.publishToDrive === false ? false : args.publishToDrive === true ? true : undefined,
    parentFolderId: safeText(args.parentFolderId, 220),
    owner: safeText(args.owner, 120),
    project: safeText(args.project, 160),
    stage: safeText(args.stage, 120),
    approved: args.approved === true,
    manifestName: safeText(args.manifestName, 240),
    callerNote: safeText(args.callerNote, 800),
  };
}

function audioRenderAcceptedReceipt({requestId, inputSha256, status = 'queued', audit = null, idempotent = false, progress = null}) {
  const receipt = {
    ok: true,
    accepted: true,
    status,
    operation: 'audio.render',
    requestId,
    renderId: requestId,
    idempotencyKey: requestId,
    inputSha256,
    idempotent,
    state: status,
    statusOperation: audioRenderStatusOperationName(requestId),
    submittedAtMs: audit && audit.submittedAtMs || audit && audit.timestampMs || Date.now(),
    updatedAtMs: audit && audit.updatedAtMs || audit && audit.timestampMs || Date.now(),
    lease: audit && audit.lease || null,
    progress: progress || audit && audit.progress || {phase: status, synthesizedTakes: 0, totalTakes: 0, outputCount: 0},
  };
  return {...receipt, _mcpContent: {content: [{type: 'text', text: JSON.stringify(receipt, null, 2)}]}};
}

function inputConflict(existing, inputSha256) {
  const existingHash = safeText(existing && (existing.inputSha256 || existing.result && existing.result.inputSha256), 128);
  return existingHash && existingHash !== inputSha256;
}

function audioJobActor(user = {}) {
  return (user && (user.email || user.uid)) || 'unknown';
}

async function writeAudioAudit(helpers, admin, entry) {
  if (!helpers.auditWrite) return {audit: entry};
  return await helpers.auditWrite(admin, entry);
}

function audioProgressPatch(progress = {}, patch = {}) {
  return {...(progress || {}), ...patch, updatedAtMs: Date.now()};
}

function startAudioHeartbeatLoop(callback) {
  let stopped = false;
  let pending = Promise.resolve();
  const intervalMs = Math.max(5000, Math.min(30000, Math.floor(AUDIO_RENDER_LEASE_MS / 3)));
  const timer = setInterval(() => {
    if (stopped) return;
    pending = pending.then(() => callback()).catch(() => {});
  }, intervalMs);
  if (typeof timer.unref === 'function') timer.unref();
  return {
    async stop() {
      stopped = true;
      clearInterval(timer);
      await pending;
    },
  };
}

async function executeAudioRenderJob({google, admin, auth, user, args = {}, helpers = {}, cartesiaApiKey = () => '', normalized = null, existingProgress = null}) {
  const {requestId, settings, recipe, inputSha256} = normalized || normalizeAudioRenderRequest(args, helpers);
  const actor = audioJobActor(user);
  const authKind = user && user.authKind;
  const parentFolderId = helpers.safeDriveFileId && safeText(args.parentFolderId, 220) ? helpers.safeDriveFileId(args.parentFolderId) : safeText(args.parentFolderId, 220);
  const leaseId = randomUUID();
  const startedAtMs = Date.now();
  let progress = audioProgressPatch(existingProgress || {}, {phase: 'materializing_sources', synthesizedTakes: existingProgress && existingProgress.synthesizedTakes || 0, totalTakes: existingProgress && existingProgress.totalTakes || countSpeechTakesInRecipe(recipe), outputCount: 0});
  const phaseTimings = {startedAtMs};
  let publicationHeartbeat = null;
  await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'running', callerNote: args.callerNote, providerSummary: 'audio.render worker running.', result: null, inputSha256, audioRenderJob: {requestId, inputSha256, submittedAtMs: startedAtMs, publishToDrive: shouldPublishAudioToDrive(args, parentFolderId), storage: GENERATED_ARTIFACT_BUCKET, request: audioRenderJobRequest(args, settings)}, progress, lease: {leaseId, holder: 'home-center-audio-worker', heartbeatAtMs: Date.now(), expiresAtMs: Date.now() + AUDIO_RENDER_LEASE_MS}});
  try {
    const sourceCount = Object.keys(args.sources || {}).length;
    const materializationHeartbeat = startAudioHeartbeatLoop(async () => {
      progress = audioProgressPatch(progress, {phase: 'materializing_sources', sourceCount});
      await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'running', callerNote: args.callerNote, providerSummary: 'audio.render materializing ' + sourceCount + ' verified source(s).', result: null, inputSha256, progress, lease: {leaseId, holder: 'home-center-audio-worker', heartbeatAtMs: Date.now(), expiresAtMs: Date.now() + AUDIO_RENDER_LEASE_MS}});
    });
    let materializedSources;
    try {
      materializedSources = await materializeSources({google, auth, sources: args.sources || {}});
    } finally {
      await materializationHeartbeat.stop();
    }
    phaseTimings.materializationMs = Date.now() - startedAtMs;
    progress = audioProgressPatch(progress, {phase: 'sources_materialized', sourceCount, materializedSourceBytes: Object.values(materializedSources).reduce((sum, source) => sum + (source.byteCount || 0), 0)});
    await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'running', callerNote: args.callerNote, providerSummary: 'audio.render verified ' + sourceCount + ' source(s).', result: null, inputSha256, progress, lease: {leaseId, holder: 'home-center-audio-worker', heartbeatAtMs: Date.now(), expiresAtMs: Date.now() + AUDIO_RENDER_LEASE_MS}}).catch(() => {});
    const onSpeechTake = async (take) => {
      progress = audioProgressPatch(progress, {phase: 'synthesizing', synthesizedTakes: Math.max((progress.synthesizedTakes || 0) + 1, (take.segmentIndex || 0) + 1), lastTake: {segmentIndex: take.segmentIndex, speaker: take.speaker, character: take.character, voiceId: take.voiceId, transcriptSha256: take.transcriptSha256, providerByteCount: take.providerByteCount, duration: take.duration}});
      await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'running', callerNote: args.callerNote, providerSummary: 'audio.render synthesized take ' + progress.synthesizedTakes + '.', result: null, inputSha256, progress, lease: {leaseId, holder: 'home-center-audio-worker', heartbeatAtMs: Date.now(), expiresAtMs: Date.now() + AUDIO_RENDER_LEASE_MS}}).catch(() => {});
    };
    const renderHeartbeat = startAudioHeartbeatLoop(async () => {
      const phase = progress.phase || 'rendering_recipe';
      progress = audioProgressPatch(progress, {phase, sourceCount});
      await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'running', callerNote: args.callerNote, providerSummary: 'audio.render heartbeat during ' + phase + '.', result: null, inputSha256, progress, lease: {leaseId, holder: 'home-center-audio-worker', heartbeatAtMs: Date.now(), expiresAtMs: Date.now() + AUDIO_RENDER_LEASE_MS}});
    });
    let rendered;
    const renderStartedAtMs = Date.now();
    progress = audioProgressPatch(progress, {phase: 'rendering_recipe', render: {phase: 'starting'}});
    try {
      rendered = await renderRecipe(recipe, materializedSources, {...settings, cartesiaApiKey, onSpeechTake, onRenderProgress: async (renderProgress) => { progress = audioProgressPatch(progress, {phase: renderProgress.phase || 'rendering_recipe', render: renderProgress}); }});
      phaseTimings.renderRecipeMs = Date.now() - renderStartedAtMs;
    } finally {
      await renderHeartbeat.stop();
    }
    const artifactContextBase = audioArtifactContext(args, rendered);
    const publishToDrive = shouldPublishAudioToDrive(args, parentFolderId);
    if (rendered.finalMetrics.silent) throw audioError('Rendered audio is silent.', 422, 'audio_render_silent_output');
    if (rendered.finalMetrics.clippingCount > 0 && settings.allowClipping !== true) throw audioError('Rendered audio clipped; lower gain or enable allowClipping explicitly.', 422, 'audio_render_clipped_output');
    progress = audioProgressPatch(progress, {phase: 'publishing_artifacts', totalTakes: rendered.speechProvenance.length || progress.totalTakes || 0, outputCount: rendered.rendered.length});
    await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'running', callerNote: args.callerNote, providerSummary: 'audio.render publishing verified artifacts.', result: null, inputSha256, progress, lease: {leaseId, holder: 'home-center-audio-worker', heartbeatAtMs: Date.now(), expiresAtMs: Date.now() + AUDIO_RENDER_LEASE_MS}}).catch(() => {});
    const publicationStartedAtMs = Date.now();
    let publicationSubphase = 'outputs';
    publicationHeartbeat = startAudioHeartbeatLoop(async () => {
      progress = audioProgressPatch(progress, {phase: 'publishing_artifacts', publicationSubphase});
      await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'running', callerNote: args.callerNote, providerSummary: 'audio.render heartbeat during artifact publication.', result: null, inputSha256, progress, lease: {leaseId, holder: 'home-center-audio-worker', heartbeatAtMs: Date.now(), expiresAtMs: Date.now() + AUDIO_RENDER_LEASE_MS}});
    });
    const uploaded = [];
    for (let outputIndex = 0; outputIndex < rendered.rendered.length; outputIndex++) {
      const item = rendered.rendered[outputIndex];
      publicationSubphase = 'output_' + (outputIndex + 1) + '_of_' + rendered.rendered.length;
      progress = audioProgressPatch(progress, {phase: 'publishing_artifacts', publicationSubphase, publishedOutputCount: outputIndex, publicationTargetCount: rendered.rendered.length + 1});
      uploaded.push(await uploadVerified({google, auth, parentFolderId, item, artifactContext: {...artifactContextBase, artifactType: /^image\//.test(item.mimeType) ? 'image' : 'audio'}, publishToDrive}));
    }
    phaseTimings.outputPublicationMs = Date.now() - publicationStartedAtMs;
    const primary = uploaded.find((item) => item.mimeType === 'audio/ogg') || uploaded.find((item) => /^audio\//.test(item.mimeType)) || uploaded[0];
    const manifest = {
      operation: 'audio.render', renderer: 'home-center-deterministic-audio-v1', artifactStore: {primary: 'gcs', bucket: GENERATED_ARTIFACT_BUCKET, drivePublish: publishToDrive ? 'post_render_publish_step' : 'disabled', driveIsRenderCache: false}, runtimeBoundary: 'Home Center MCP async audio worker; direct Cartesia provider only when speech nodes are present; no Command Center, Codex, LLM, GitHub Actions renderer, or Termux runtime path.',
      requestId, inputSha256, seed: rendered.seed, sampleRate: rendered.sampleRate, phaseTimings: {...phaseTimings, ...rendered.phaseTimings, totalBeforeManifestMs: Date.now() - startedAtMs}, finalMetrics: {...rendered.finalMetrics, integratedLufs: Number.isFinite(rendered.finalMetrics.integratedLufs) ? rendered.finalMetrics.integratedLufs : null},
      sourceCount: Object.keys(materializedSources).length, sources: Object.values(materializedSources).map((src) => ({name: src.name, originalRef: src.originalRef, provider: src.provider, mimeType: src.mimeType, byteCount: src.byteCount, sha256: src.sha256, decoded: src.decoded})),
      speech: {usesCartesia: rendered.usesCartesia, supportedEmotions: CARTESIA_SUPPORTED_EMOTIONS, canonicalProfiles: Object.fromEntries(Object.entries(CANONICAL_CHARACTER_PROFILES).filter(([key, profile]) => key === String(profile.character).toLowerCase()).map(([key, profile]) => [key, {character: profile.character, aliases: profile.aliases, provider: profile.provider, voiceName: profile.voiceName, voiceId: profile.voiceId, modelId: profile.modelId, speed: profile.speed, pitchSemitones: profile.pitchSemitones, direction: profile.direction}])), takes: rendered.speechProvenance, sequences: rendered.speechSequences, auditionTakes: rendered.auditionTakes, limits: {maxDurationSeconds: MAX_DURATION_SECONDS, maxSpeechSequenceSegments: SPEECH_SEQUENCE_MAX_SEGMENTS, defaultSpeechConcurrency: SPEECH_SEQUENCE_DEFAULT_CONCURRENCY, maxWavBytes: MAX_WAV_OUTPUT_BYTES, maxEncodedBytes: MAX_ENCODED_OUTPUT_BYTES, inlineAudioMaxBytes: INLINE_AUDIO_MAX_BYTES}},
      outputs: uploaded.map((item) => ({name: item.name, mimeType: item.mimeType, duration: item.clipMetrics.duration, sampleRate: item.clipMetrics.sampleRate, channelCount: item.clipMetrics.channelCount, bitDepth: item.mimeType === 'audio/wav' ? 16 : null, codec: item.format === 'ogg' ? 'vorbis' : item.format, byteCount: item.byteCount, sha256: item.sha256, readbackByteCount: item.readbackByteCount, readbackSha256: item.readbackSha256, peak: item.clipMetrics.peak, integratedLufs: Number.isFinite(item.clipMetrics.integratedLufs) ? item.clipMetrics.integratedLufs : null, clippingCount: item.clipMetrics.clippingCount, durableRef: item.durableRef, storageRef: item.storageRef, primaryStore: item.primaryStore, metadata: item.metadata, driveDurableRef: item.driveDurableRef, fileId: item.fileId, chatGptFileRef: item.chatGptFileRef, webViewLink: item.webViewLink})),
      noAgentRuntime: true, noCommandCenter: true, noCodex: true, noGithubActionsRenderer: true, noTermuxRuntime: true,
    };
    const manifestBytes = Buffer.from(JSON.stringify(manifest, null, 2), 'utf8');
    publicationSubphase = 'manifest';
    progress = audioProgressPatch(progress, {phase: 'publishing_artifacts', publicationSubphase, publishedOutputCount: uploaded.length, publicationTargetCount: rendered.rendered.length + 1});
    const manifestStartedAtMs = Date.now();
    const manifestUpload = await uploadVerified({google, auth, parentFolderId, item: {name: safeText(args.manifestName, 240) || 'audio-render-manifest-' + requestId + '.json', format: 'json', mimeType: 'application/json', bytes: manifestBytes, byteCount: manifestBytes.length, sha256: sha256Hex(manifestBytes), clipMetrics: rendered.finalMetrics}, artifactContext: {...artifactContextBase, artifactType: 'manifest'}, publishToDrive});
    await publicationHeartbeat.stop();
    publicationHeartbeat = null;
    phaseTimings.manifestPublicationMs = Date.now() - manifestStartedAtMs;
    phaseTimings.totalMs = Date.now() - startedAtMs;
    const result = {...manifest, phaseTimings: {...manifest.phaseTimings, ...phaseTimings}, manifest: {fileId: manifestUpload.fileId, durableRef: manifestUpload.durableRef, storageRef: manifestUpload.storageRef, driveDurableRef: manifestUpload.driveDurableRef, primaryStore: manifestUpload.primaryStore, metadata: manifestUpload.metadata, byteCount: manifestUpload.byteCount, sha256: manifestUpload.sha256, readbackByteCount: manifestUpload.readbackByteCount, readbackSha256: manifestUpload.readbackSha256}, primaryOutput: manifest.outputs.find((item) => primary && item.name === primary.name) || manifest.outputs[0], ok: true, status: 'completed', completedAtMs: Date.now()};
    const affectedStorageRefs = uploaded.map((u) => u.storageRef).concat([manifestUpload.storageRef]).filter(Boolean);
    const affectedFileIds = uploaded.map((u) => u.fileId).concat([manifestUpload.fileId]).filter(Boolean);
    const audit = await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'completed', fileId: primary && (primary.fileId || primary.storageRef) || '', affectedFileIds, affectedStorageRefs, callerNote: args.callerNote, providerSummary: 'Rendered deterministic audio artifact ' + (primary && primary.name || 'audio') + ' (' + (primary && primary.byteCount || 0) + ' bytes).', result, inputSha256, progress: audioProgressPatch(progress, {phase: 'completed', outputCount: uploaded.length + 1, completedAtMs: result.completedAtMs}), lease: null});
    result.audit = audit.audit ? {...audit.audit, result: null} : audit.audit;
    if (helpers.recordActionAudit) await helpers.recordActionAudit(admin, user || {}, 'audio.render', primary && (primary.storageRef || primary.fileId) || '', 'Rendered deterministic audio artifact ' + (primary && primary.name || 'audio') + ' (' + (primary && primary.byteCount || 0) + ' bytes).', requestId).catch(() => {});
    const inlinePrimary = rendered.rendered.find((item) => primary && item.name === primary.name);
    const content = [{type: 'text', text: JSON.stringify(result, null, 2)}];
    if (primary && primary.chatGptFileRef) content.push(primary.chatGptFileRef);
    const audioBlock = audioContentFor(inlinePrimary, args.returnInlineAudio !== false);
    if (audioBlock) content.push(audioBlock);
    result._mcpContent = {content};
    return result;
  } catch (err) {
    if (publicationHeartbeat) await publicationHeartbeat.stop();
    const failure = {ok: false, status: 'failed', code: safeText(err && (err.failureKind || err.code), 120) || 'audio_render_failed', message: safeText(err && err.message, 500), inputSha256, failedAtMs: Date.now()};
    await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'failed', callerNote: args.callerNote, providerSummary: 'audio.render failed: ' + failure.code, result: failure, inputSha256, progress: audioProgressPatch(progress, {phase: 'failed', errorCode: failure.code}), lease: null}).catch(() => {});
    throw err;
  }
}

function startAudioRenderBackground(context) {
  if (context.args && context.args.disableBackgroundWorker === true) return;
  setImmediate(() => {
    executeAudioRenderJob(context).catch(() => {});
  });
}

async function renderAudioOperation({google, admin, auth, user, args = {}, helpers = {}, cartesiaApiKey = () => ''}) {
  const normalized = normalizeAudioRenderRequest(args, helpers);
  const {requestId, inputSha256} = normalized;
  const existing = helpers.existingAudit ? await helpers.existingAudit(admin, requestId) : null;
  if (existing && inputConflict(existing, inputSha256)) throw audioError('idempotencyKey was reused with different audio.render inputs.', 409, 'audio_render_idempotency_conflict');
  if (existing && (existing.status === 'success' || existing.status === 'completed') && existing.result) return {...existing.result, idempotent: true, audit: existing, _mcpContent: null};
  if (existing && ['queued', 'running', 'stalled', 'recoverable', 'failed'].includes(safeText(existing.status, 80))) return audioRenderAcceptedReceipt({requestId, inputSha256, status: safeText(existing.status, 80), audit: existing, idempotent: true});
  const actor = audioJobActor(user);
  const authKind = user && user.authKind;
  const queuedAtMs = Date.now();
  const progress = {phase: 'queued', synthesizedTakes: 0, totalTakes: countSpeechTakesInRecipe(normalized.recipe), outputCount: 0, updatedAtMs: queuedAtMs};
  const job = {requestId, inputSha256, submittedAtMs: queuedAtMs, statusOperation: audioRenderStatusOperationName(requestId), storage: {primary: 'gcs', bucket: GENERATED_ARTIFACT_BUCKET}, publishToDrive: shouldPublishAudioToDrive(args, safeText(args.parentFolderId, 220)), chargeSafety: {idempotencyKey: requestId, providerExactlyOnce: 'not_guaranteed_across_ambiguous_provider_failure', ambiguousFailuresBecome: 'stalled_or_quarantined'}, request: audioRenderJobRequest(args, normalized.settings)};
  await writeAudioAudit(helpers, admin, {actor, authKind, tool: 'audio.render', operation: 'audio.render', requestId, status: 'queued', callerNote: args.callerNote, providerSummary: 'audio.render accepted for asynchronous execution.', result: {ok: true, accepted: true, status: 'queued', operation: 'audio.render', requestId, inputSha256, statusOperation: audioRenderStatusOperationName(requestId)}, inputSha256, audioRenderJob: job, progress, lease: null, submittedAtMs: queuedAtMs, updatedAtMs: queuedAtMs});
  if (args.waitForCompletion === true) return await executeAudioRenderJob({google, admin, auth, user, args, helpers, cartesiaApiKey, normalized, existingProgress: progress});
  startAudioRenderBackground({google, admin, auth, user, args, helpers, cartesiaApiKey, normalized, existingProgress: progress});
  return audioRenderAcceptedReceipt({requestId, inputSha256, status: 'queued', audit: {timestampMs: queuedAtMs, submittedAtMs: queuedAtMs, progress}, idempotent: false});
}

async function audioRenderStatusOperation({admin, requestId, helpers = {}}) {
  const audit = helpers.existingAudit ? await helpers.existingAudit(admin, requestId) : null;
  if (!audit) return {ok: false, operation: 'audio.render_status', requestId, status: 'missing'};
  let status = audit.status === 'success' ? 'completed' : safeText(audit.status, 80) || 'completed';
  const now = Date.now();
  const heartbeatAtMs = audit.lease && Number(audit.lease.heartbeatAtMs || 0) || Number(audit.updatedAtMs || audit.timestampMs || 0);
  const stale = ['queued', 'running'].includes(status) && heartbeatAtMs && now - heartbeatAtMs > AUDIO_RENDER_STALE_MS;
  if (stale && helpers.auditWrite) {
    status = 'stalled';
    await helpers.auditWrite(admin, {...audit, actor: audit.actor || 'unknown', authKind: audit.authKind, tool: 'audio.render', operation: 'audio.render', requestId, status, providerSummary: 'audio.render stalled after heartbeat expiry; no paid retry was launched.', result: audit.result || {ok: false, status, inputSha256: audit.inputSha256, code: 'audio_render_stalled', message: 'The render worker heartbeat expired. Existing provider outcome is ambiguous; inspect checkpoints before resuming.'}, inputSha256: audit.inputSha256, progress: audioProgressPatch(audit.progress || {}, {phase: 'stalled', stalledAtMs: now}), lease: null}).catch(() => {});
  }
  return {ok: status !== 'missing', operation: 'audio.render_status', requestId, status, state: status, inputSha256: audit.inputSha256 || audit.result && audit.result.inputSha256 || '', result: audit.result || null, progress: audit.progress || null, lease: audit.lease || null, timestamps: {timestampMs: audit.timestampMs || 0, submittedAtMs: audit.submittedAtMs || audit.timestampMs || 0, updatedAtMs: audit.updatedAtMs || audit.timestampMs || 0, heartbeatAtMs}, audit: {...audit, result: null}};
}

module.exports = {renderAudioOperation, audioRenderStatusOperation, executeAudioRenderJob, inspectAudioArtifactsOperation, uploadVerified, renderRecipe, sanitizeRecipeText, materializeSources, resolveSpeechProfile, CARTESIA_SUPPORTED_EMOTIONS, CANONICAL_CHARACTER_PROFILES, limits: {MAX_DURATION_SECONDS, MAX_WAV_OUTPUT_BYTES, MAX_ENCODED_OUTPUT_BYTES, SPEECH_SEQUENCE_MAX_SEGMENTS, SPEECH_SEQUENCE_DEFAULT_CONCURRENCY, INLINE_AUDIO_MAX_BYTES}, primitives: {Clip, silence, tone, noise, trim, concat, loop, fade, crossfade, gain, normalizePeak, normalizeLufs, pan, pitchShift, timeStretch, reverse, biquadLike, compress, limit, distort, delay, reverb, envelope, timeline, blockMix, duck, resample, toChannels, encodeWav, decodeWav, waveformPng, spectrogramPng, measure, layerSwordImpact, layerTavernCellar}};
