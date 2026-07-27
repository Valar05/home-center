const {createHash, randomUUID} = require('node:crypto');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
let ffmpegPath = process.env.FFMPEG_PATH || '';
if (!ffmpegPath) {
  try {
    ffmpegPath = require('ffmpeg-static');
  } catch {
    ffmpegPath = 'ffmpeg';
  }
}
const {
  GENERATED_ARTIFACT_BUCKET,
  inspectGeneratedArtifact,
  uploadGeneratedArtifact,
  publishGeneratedArtifactToDrive,
} = require('./artifact_bucket');
const {
  primitives: {
    decodeWav,
    encodeWav,
    trim,
    concat,
    silence,
    fade,
    gain,
    normalizePeak,
    pan,
    biquadLike,
    compress,
    limit,
    distort,
    timeline,
    toChannels,
    waveformPng,
    spectrogramPng,
    measure,
  },
} = require('./audio_render_service');

const ENGINE_VERSION = 'home-center-sfx-forge-v1';
const SCHEMA_VERSION = 'home-center.sfx-forge.v1';
const MAX_SOURCE_BYTES = Number(process.env.HOME_CENTER_SFX_MAX_SOURCE_BYTES || 25 * 1024 * 1024);
const MAX_EVENTS = Number(process.env.HOME_CENTER_SFX_MAX_EVENTS || 240);
const MAX_CANDIDATES = Number(process.env.HOME_CENTER_SFX_MAX_CANDIDATES || 32);
const DEFAULT_TRANSCRIPTION_MODEL = process.env.HOME_CENTER_SFX_TRANSCRIPTION_MODEL || 'gpt-4o-transcribe-diarize';

function forgeError(message, status = 400, code = 'sfx_forge_failed') {
  const err = new Error(message);
  err.status = status;
  err.failureKind = code;
  return err;
}

function safeText(value, max = 1200) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function assertFinite(value, label, min = -Infinity, max = Infinity) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw forgeError(`${label} must be a finite number between ${min} and ${max}.`, 400, 'sfx_forge_validation_failed');
  }
  return value;
}

function sha256Hex(value) {
  return createHash('sha256').update(value).digest('hex');
}

function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}

function safeSegment(value, fallback = 'artifact') {
  return safeText(value, 120).replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 120) || fallback;
}

function extensionFor(name, mimeType = '') {
  const ext = path.extname(String(name || '')).toLowerCase();
  if (ext) return ext;
  if (/m4a|mp4/.test(mimeType)) return '.m4a';
  if (/mpeg|mp3/.test(mimeType)) return '.mp3';
  if (/wav/.test(mimeType)) return '.wav';
  if (/ogg/.test(mimeType)) return '.ogg';
  return '.bin';
}

function forgeRequestId(args = {}, helpers = {}) {
  return helpers.createRequestId
    ? helpers.createRequestId(args.requestId || args.idempotencyKey)
    : safeText(args.requestId || args.idempotencyKey, 160) || randomUUID();
}

function executionAuthorized(args = {}) {
  if (args.approved !== true) {
    throw forgeError('approved=true is required to authorize Forge execution. This is not artistic acceptance.', 403, 'sfx_forge_execution_not_authorized');
  }
}

function normalizedSourceInput(args = {}) {
  const sourceRef = safeText(args.sourceRef || args.ref, 1400);
  const expectedSha256 = safeText(args.expectedSha256 || args.sourceSha256, 64).toLowerCase();
  if (!sourceRef.startsWith(`gs://${GENERATED_ARTIFACT_BUCKET}/audio/`)) {
    throw forgeError('sourceRef must be an immutable audio object in the canonical generated bucket.', 400, 'sfx_forge_source_ref_invalid');
  }
  if (!/^[a-f0-9]{64}$/.test(expectedSha256)) {
    throw forgeError('expectedSha256 must be the immutable parent source SHA-256.', 400, 'sfx_forge_parent_hash_required');
  }
  return {sourceRef, expectedSha256};
}

async function materializeImmutableSource(args = {}) {
  const {sourceRef, expectedSha256} = normalizedSourceInput(args);
  const source = await inspectGeneratedArtifact(sourceRef);
  if (!source || !Buffer.isBuffer(source.bytes)) throw forgeError('Immutable source could not be materialized.', 404, 'sfx_forge_source_missing');
  if (source.byteCount > MAX_SOURCE_BYTES) throw forgeError('Source exceeds the Forge v1 size limit.', 413, 'sfx_forge_source_too_large');
  if (source.sha256 !== expectedSha256) throw forgeError('Immutable parent source SHA-256 mismatch.', 409, 'sfx_forge_parent_hash_mismatch');
  return source;
}

function runProcess(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {stdio: ['ignore', 'pipe', 'pipe'], ...options});
    const stdout = [];
    const stderr = [];
    child.stdout.on('data', (chunk) => stdout.push(Buffer.from(chunk)));
    child.stderr.on('data', (chunk) => stderr.push(Buffer.from(chunk)));
    child.on('error', (err) => reject(forgeError(`Forge process failed to start: ${err.message}`, 500, 'sfx_forge_process_failed')));
    child.on('close', (code) => {
      const result = {code, stdout: Buffer.concat(stdout), stderr: Buffer.concat(stderr)};
      if (code === 0) return resolve(result);
      reject(forgeError(`Forge media process failed (${code}): ${result.stderr.toString('utf8').slice(-1200)}`, 422, 'sfx_forge_media_failed'));
    });
  });
}

async function withSourceFiles(source, callback) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'sfx-forge-'));
  const input = path.join(dir, `source${extensionFor(source.name, source.mimeType)}`);
  await fs.writeFile(input, source.bytes);
  try {
    return await callback({dir, input});
  } finally {
    await fs.rm(dir, {recursive: true, force: true}).catch(() => {});
  }
}

async function decodeWorkingPcm(source) {
  return withSourceFiles(source, async ({dir, input}) => {
    const output = path.join(dir, 'working-pcm16.wav');
    await runProcess(ffmpegPath, ['-hide_banner', '-nostdin', '-y', '-i', input, '-map', '0:a:0', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', output]);
    return fs.readFile(output);
  });
}

async function standardsMetrics(source) {
  return withSourceFiles(source, async ({input}) => {
    const result = await runProcess(ffmpegPath, ['-hide_banner', '-nostdin', '-nostats', '-i', input, '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-']);
    const text = result.stderr.toString('utf8');
    const summary = text.slice(Math.max(0, text.lastIndexOf('Summary:')));
    const integrated = summary.match(/Integrated loudness:\s+I:\s+(-?[\d.]+)\s+LUFS/i);
    const threshold = summary.match(/Integrated loudness:[\s\S]*?Threshold:\s+(-?[\d.]+)\s+LUFS/i);
    const lra = summary.match(/Loudness range:\s+LRA:\s+(-?[\d.]+)\s+LU/i);
    const truePeak = summary.match(/True peak:\s+Peak:\s+(-?[\d.]+)\s+dBFS/i);
    return {
      standard: 'EBU R128 / ITU-R BS.1770 via FFmpeg ebur128',
      integratedLufs: integrated ? Number(integrated[1]) : null,
      relativeGateThresholdLufs: threshold ? Number(threshold[1]) : null,
      loudnessRangeLu: lra ? Number(lra[1]) : null,
      truePeakDbtp: truePeak ? Number(truePeak[1]) : null,
      parserEvidenceSha256: sha256Hex(Buffer.from(summary, 'utf8')),
    };
  });
}

function monoSamples(clip) {
  const mono = new Float32Array(clip.frames);
  for (const channel of clip.channels) {
    for (let i = 0; i < mono.length; i += 1) mono[i] += channel[i] / clip.channelCount;
  }
  return mono;
}

function percentile(values, q) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.max(0, Math.min(sorted.length - 1, Math.round((sorted.length - 1) * q)));
  return sorted[index];
}

function fftReal(samples) {
  const n = samples.length;
  const real = new Float64Array(n);
  const imag = new Float64Array(n);
  for (let i = 0; i < n; i += 1) real[i] = samples[i];
  for (let i = 1, j = 0; i < n; i += 1) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [real[i], real[j]] = [real[j], real[i]];
      [imag[i], imag[j]] = [imag[j], imag[i]];
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const angle = -2 * Math.PI / len;
    const wlenR = Math.cos(angle);
    const wlenI = Math.sin(angle);
    for (let i = 0; i < n; i += len) {
      let wr = 1;
      let wi = 0;
      for (let j = 0; j < len / 2; j += 1) {
        const uR = real[i + j];
        const uI = imag[i + j];
        const vR = real[i + j + len / 2] * wr - imag[i + j + len / 2] * wi;
        const vI = real[i + j + len / 2] * wi + imag[i + j + len / 2] * wr;
        real[i + j] = uR + vR;
        imag[i + j] = uI + vI;
        real[i + j + len / 2] = uR - vR;
        imag[i + j + len / 2] = uI - vI;
        const nextWr = wr * wlenR - wi * wlenI;
        wi = wr * wlenI + wi * wlenR;
        wr = nextWr;
      }
    }
  }
  return {real, imag};
}

function spectralProfile(mono, sampleRate, centerFrame) {
  const size = 4096;
  const start = Math.max(0, Math.min(mono.length - size, centerFrame - 256));
  const window = new Float64Array(size);
  let sumSquares = 0;
  for (let i = 0; i < size; i += 1) {
    const sample = mono[start + i] || 0;
    const hann = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (size - 1));
    window[i] = sample * hann;
    sumSquares += sample * sample;
  }
  const {real, imag} = fftReal(window);
  const bands = [
    ['sub', 20, 80],
    ['mass', 80, 250],
    ['lowMid', 250, 800],
    ['identity', 800, 3000],
    ['presence', 3000, 8000],
    ['air', 8000, Math.min(20000, sampleRate / 2)],
  ];
  const bandEnergy = Object.fromEntries(bands.map(([name]) => [name, 0]));
  const bins = [];
  let total = 0;
  let weighted = 0;
  let logSum = 0;
  let positiveBins = 0;
  for (let bin = 1; bin < size / 2; bin += 1) {
    const frequency = bin * sampleRate / size;
    const power = real[bin] * real[bin] + imag[bin] * imag[bin] + 1e-18;
    bins.push({frequency, power});
    total += power;
    weighted += frequency * power;
    logSum += Math.log(power);
    positiveBins += 1;
    for (const [name, low, high] of bands) if (frequency >= low && frequency < high) bandEnergy[name] += power;
  }
  const arithmetic = total / Math.max(1, positiveBins);
  const flatness = Math.exp(logSum / Math.max(1, positiveBins)) / Math.max(1e-18, arithmetic);
  const peaks = bins.filter((entry, index) => index > 0 && index < bins.length - 1 && entry.power > bins[index - 1].power && entry.power >= bins[index + 1].power)
    .sort((a, b) => b.power - a.power)
    .slice(0, 5)
    .map((entry) => ({frequencyHz: Number(entry.frequency.toFixed(1)), relativeDb: Number((10 * Math.log10(entry.power / Math.max(1e-18, total))).toFixed(2))}));
  const normalizedBands = Object.fromEntries(Object.entries(bandEnergy).map(([name, value]) => [name, total ? Number((value / total).toFixed(6)) : 0]));
  return {
    rms: Math.sqrt(sumSquares / size),
    spectralCentroidHz: total ? Number((weighted / total).toFixed(2)) : 0,
    spectralFlatness: Number(flatness.toFixed(6)),
    bandEnergyRatio: normalizedBands,
    dominantPeaks: peaks,
  };
}

function detectTransients(clip) {
  const mono = monoSamples(clip);
  const window = Math.max(16, Math.round(clip.sampleRate * 0.005));
  const hop = Math.max(8, Math.round(clip.sampleRate * 0.0025));
  const envelope = [];
  for (let frame = 0; frame + window <= mono.length; frame += hop) {
    let square = 0;
    let peak = 0;
    for (let i = 0; i < window; i += 1) {
      const value = Math.abs(mono[frame + i]);
      peak = Math.max(peak, value);
      square += value * value;
    }
    envelope.push({frame: frame + Math.floor(window / 2), rms: Math.sqrt(square / window), peak});
  }
  const noiseFloor = percentile(envelope.map((entry) => entry.rms), 0.25);
  const candidates = [];
  const history = Math.max(4, Math.round(0.05 * clip.sampleRate / hop));
  const minGapFrames = Math.round(0.08 * clip.sampleRate);
  for (let i = history; i < envelope.length - 1; i += 1) {
    let baseline = 0;
    for (let j = i - history; j < i; j += 1) baseline += envelope[j].rms;
    baseline /= history;
    const current = envelope[i];
    const threshold = Math.max(noiseFloor * 5, baseline * 2.2, 0.006);
    if (current.rms < threshold || current.rms < envelope[i - 1].rms || current.rms < envelope[i + 1].rms) continue;
    const prior = candidates[candidates.length - 1];
    if (prior && current.frame - prior.frame < minGapFrames) {
      if (current.rms > prior.rms) candidates[candidates.length - 1] = {...current};
      continue;
    }
    candidates.push({...current});
  }
  return {
    detector: {method: '5ms RMS onset over adaptive 50ms baseline', windowMs: 5, hopMs: 2.5, minimumGapMs: 80, noiseFloorRms: noiseFloor},
    candidates: candidates.slice(0, 240).map((entry, index) => ({
      candidateId: `transient-${String(index + 1).padStart(3, '0')}`,
      timeSeconds: Number((entry.frame / clip.sampleRate).toFixed(4)),
      peak: Number(entry.peak.toFixed(6)),
      rms: Number(entry.rms.toFixed(6)),
      sourceFrame: entry.frame,
      spectral: spectralProfile(mono, clip.sampleRate, entry.frame),
      classification: 'unknown',
      humanAccepted: false,
    })),
  };
}

async function transcribeSlate(source, openAiApiKey, options = {}) {
  if (options.enabled === false) return null;
  const apiKey = typeof openAiApiKey === 'function' ? openAiApiKey() : openAiApiKey;
  if (!safeText(apiKey, 1000)) throw forgeError('OPENAI_API_KEY is not configured for slate transcription.', 503, 'sfx_forge_transcription_unavailable');
  const model = safeText(options.model, 120) || DEFAULT_TRANSCRIPTION_MODEL;
  const form = new FormData();
  form.set('file', new Blob([source.bytes], {type: source.mimeType || 'audio/mp4'}), source.name || 'source.m4a');
  form.set('model', model);
  if (model === 'gpt-4o-transcribe-diarize') {
    form.set('response_format', 'diarized_json');
    form.set('chunking_strategy', 'auto');
  } else if (model === 'whisper-1') {
    form.set('response_format', 'verbose_json');
    form.append('timestamp_granularities[]', 'segment');
    form.append('timestamp_granularities[]', 'word');
  } else {
    form.set('response_format', 'json');
  }
  const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
    method: 'POST',
    headers: {Authorization: `Bearer ${apiKey}`},
    body: form,
  });
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : {}; } catch (_) { payload = {text}; }
  if (!response.ok) throw forgeError(`Slate transcription failed: HTTP ${response.status} ${safeText(payload && (payload.error && payload.error.message || payload.text), 600)}`, 502, 'sfx_forge_transcription_failed');
  return {
    provider: 'openai',
    endpoint: 'audio.transcriptions',
    model,
    responseFormat: model === 'gpt-4o-transcribe-diarize' ? 'diarized_json' : model === 'whisper-1' ? 'verbose_json' : 'json',
    responseSha256: sha256Hex(Buffer.from(stableJson(payload), 'utf8')),
    text: safeText(payload.text, 20000),
    language: safeText(payload.language, 80),
    duration: safeNumber(payload.duration, 0) || null,
    segments: Array.isArray(payload.segments) ? payload.segments.map((segment) => ({
      id: segment.id,
      speaker: safeText(segment.speaker, 80),
      start: safeNumber(segment.start, 0),
      end: safeNumber(segment.end, 0),
      text: safeText(segment.text, 4000),
      avgLogprob: Number.isFinite(segment.avg_logprob) ? segment.avg_logprob : null,
      noSpeechProbability: Number.isFinite(segment.no_speech_prob) ? segment.no_speech_prob : null,
    })) : [],
    words: Array.isArray(payload.words) ? payload.words.map((word) => ({start: safeNumber(word.start, 0), end: safeNumber(word.end, 0), word: safeText(word.word, 300)})) : [],
    usage: payload.usage || null,
    semanticAuthority: 'transcription_assist_only_source_audio_remains_authority',
  };
}

function artifactReceipt(artifact, role = '') {
  return {
    role,
    name: artifact.name,
    mimeType: artifact.mimeType,
    byteCount: artifact.byteCount,
    sha256: artifact.sha256,
    readbackByteCount: artifact.readbackByteCount,
    readbackSha256: artifact.readbackSha256,
    storageRef: artifact.storageRef,
    verified: artifact.verified,
    drive: artifact.drive || null,
  };
}

function forgePrefix(args, requestId) {
  const owner = safeSegment(args.owner || 'drew', 'drew').toLowerCase();
  const family = safeSegment(args.family || 'unclassified', 'unclassified').toLowerCase();
  return `audio/${owner}/sfx-armory/forge/${family}/${safeSegment(requestId, 'job')}`;
}

async function uploadForgeArtifact(args, requestId, item, google = null, auth = null) {
  const artifact = await uploadGeneratedArtifact({
    bytes: item.bytes,
    name: item.name,
    mimeType: item.mimeType,
    owner: safeText(args.owner, 120) || 'drew',
    ownerEmail: safeText(args.ownerEmail, 320),
    project: safeText(args.project, 160) || 'sfx-armory',
    stage: safeText(item.stage, 120) || 'forge',
    engine: ENGINE_VERSION,
    createdBy: 'home-center-sfx-forge',
    jobId: requestId,
    approved: false,
    requestId,
    artifactType: safeText(item.artifactType, 120) || 'sfx-forge',
    prefix: forgePrefix(args, requestId),
  });
  if (args.publishToDrive === true) {
    if (!google || !auth) throw forgeError('publishToDrive requires an authenticated Drive context.', 401, 'sfx_forge_drive_context_required');
    artifact.drive = await publishGeneratedArtifactToDrive({
      google,
      auth,
      parentFolderId: safeText(args.parentFolderId, 200),
      artifact,
      bytes: item.bytes,
    });
  }
  return artifact;
}

function forgeAuditEntry({user, requestId, operation, inputSha256, status, args, result = null, error = '', progress = null}) {
  return {
    actor: user && (user.email || user.uid) || 'unknown',
    authKind: user && user.authKind,
    tool: operation,
    operation,
    requestId,
    status,
    callerNote: args.callerNote,
    providerSummary: `${operation} ${status}.`,
    result,
    inputSha256,
    progress,
    error,
    sfxForgeJob: {
      schemaVersion: SCHEMA_VERSION,
      engineVersion: ENGINE_VERSION,
      requestId,
      operation,
      sourceRef: safeText(args.sourceRef || args.ref, 1400),
      parentSha256: safeText(args.expectedSha256 || args.sourceSha256, 64),
      humanAcceptance: 'unreviewed',
    },
  };
}

async function withForgeIdempotency({operation, user, admin, args, helpers, run}) {
  executionAuthorized(args);
  const requestId = forgeRequestId(args, helpers);
  const input = {...args, approved: undefined, callerNote: undefined};
  const inputSha256 = sha256Hex(Buffer.from(stableJson(input), 'utf8'));
  const existing = helpers.existingAudit ? await helpers.existingAudit(admin, requestId) : null;
  if (existing && safeText(existing.inputSha256, 128) && existing.inputSha256 !== inputSha256) {
    throw forgeError('requestId was reused with different SFX Forge inputs.', 409, 'sfx_forge_idempotency_conflict');
  }
  if (existing && ['completed', 'success'].includes(safeText(existing.status, 80)) && existing.result) {
    return {...existing.result, idempotent: true};
  }
  if (helpers.auditWrite) await helpers.auditWrite(admin, forgeAuditEntry({user, requestId, operation, inputSha256, status: 'running', args, progress: {phase: 'materializing_source'}}));
  try {
    const result = await run({requestId, inputSha256});
    const completed = {...result, ok: true, status: 'completed', operation, requestId, inputSha256, executionAuthorized: true, humanAcceptance: 'unreviewed', idempotent: false, noCommandCenter: true, noCodexWorker: true};
    if (helpers.auditWrite) await helpers.auditWrite(admin, forgeAuditEntry({user, requestId, operation, inputSha256, status: 'completed', args, result: completed, progress: {phase: 'completed', artifactCount: completed.artifacts && completed.artifacts.length || 0}}));
    return completed;
  } catch (err) {
    if (helpers.auditWrite) await helpers.auditWrite(admin, forgeAuditEntry({user, requestId, operation, inputSha256, status: 'failed', args, error: safeText(err.message, 1000), result: {ok: false, status: 'failed', code: safeText(err.failureKind || err.code, 120) || 'sfx_forge_failed', message: safeText(err.message, 800), requestId, inputSha256}})).catch(() => {});
    throw err;
  }
}

async function analyzeSourceOperation({google, auth, admin, user, openAiApiKey = () => '', args = {}, helpers = {}}) {
  return withForgeIdempotency({
    operation: 'sfx.analyze_source',
    user,
    admin,
    args,
    helpers,
    run: async ({requestId, inputSha256}) => {
      const source = await materializeImmutableSource(args);
      const wavBytes = await decodeWorkingPcm(source);
      const clip = decodeWav(wavBytes);
      const basic = measure(clip);
      const r128 = await standardsMetrics(source);
      const transientAnalysis = detectTransients(clip);
      const transcription = await transcribeSlate(source, openAiApiKey, args.transcription || {});
      const uploaded = [];
      uploaded.push(await uploadForgeArtifact(args, requestId, {name: 'working-pcm16.wav', mimeType: 'audio/wav', bytes: wavBytes, stage: 'working', artifactType: 'working-descendant'}, google, auth));
      uploaded.push(await uploadForgeArtifact(args, requestId, {name: 'source-waveform.png', mimeType: 'image/png', bytes: waveformPng(clip, 1800, 480), stage: 'evidence', artifactType: 'waveform'}, google, auth));
      uploaded.push(await uploadForgeArtifact(args, requestId, {name: 'source-spectrogram.png', mimeType: 'image/png', bytes: spectrogramPng(clip, 1800, 900), stage: 'evidence', artifactType: 'spectrogram'}, google, auth));
      const report = {
        schemaVersion: SCHEMA_VERSION,
        engineVersion: ENGINE_VERSION,
        operation: 'sfx.analyze_source',
        requestId,
        inputSha256,
        source: {
          storageRef: args.sourceRef,
          name: source.name,
          mimeType: source.mimeType,
          byteCount: source.byteCount,
          sha256: source.sha256,
          immutableParent: true,
          canonicalReplaced: false,
        },
        decode: {
          workingFormat: 'PCM16 WAV',
          sampleRate: clip.sampleRate,
          channels: clip.channelCount,
          durationSeconds: clip.duration,
          workingSha256: sha256Hex(wavBytes),
          workingByteCount: wavBytes.length,
          normalized: false,
        },
        measurements: {
          samplePeak: basic.peak,
          rms: basic.rms,
          crestFactorDb: basic.rms > 0 ? 20 * Math.log10(basic.peak / basic.rms) : null,
          clippingSampleCount: basic.clippingCount,
          standards: r128,
        },
        transientAnalysis,
        transcription,
        semanticAuthority: 'source_audio',
        metricsGrantArtisticAcceptance: false,
        humanAcceptance: 'unreviewed',
      };
      const reportBytes = Buffer.from(JSON.stringify(report, null, 2), 'utf8');
      const reportUpload = await uploadForgeArtifact(args, requestId, {name: 'source-analysis.json', mimeType: 'application/json', bytes: reportBytes, stage: 'qa', artifactType: 'analysis'}, google, auth);
      uploaded.push(reportUpload);
      if (transcription) {
        const transcriptBytes = Buffer.from(JSON.stringify(transcription, null, 2), 'utf8');
        uploaded.push(await uploadForgeArtifact(args, requestId, {name: 'spoken-slate-transcription.json', mimeType: 'application/json', bytes: transcriptBytes, stage: 'annotations', artifactType: 'transcription'}, google, auth));
      }
      return {
        source: report.source,
        decode: report.decode,
        measurements: report.measurements,
        transientAnalysis,
        transcription,
        artifacts: uploaded.map((artifact) => artifactReceipt(artifact)),
        analysisManifest: artifactReceipt(reportUpload, 'source-analysis'),
        canonicalSourceReplaced: false,
      };
    },
  });
}

function normalizedEvent(event, index, duration) {
  const eventId = safeSegment(event.eventId || `event-${index + 1}`, `event-${index + 1}`);
  const labelRange = event.spokenLabelTimeRange || event.labelTimeRange || null;
  const impactRange = event.impactTimeRange || event.sourceTimeRange || null;
  if (!Array.isArray(impactRange) || impactRange.length !== 2) {
    throw forgeError(`${eventId}.impactTimeRange must be [startSeconds,endSeconds].`, 400, 'sfx_forge_event_range_required');
  }
  const start = assertFinite(impactRange[0], `${eventId}.impactTimeRange[0]`, 0, duration);
  const end = assertFinite(impactRange[1], `${eventId}.impactTimeRange[1]`, start, duration);
  if (end <= start) throw forgeError(`${eventId}.impactTimeRange must have positive duration.`, 400, 'sfx_forge_event_range_invalid');
  let spoken = null;
  if (Array.isArray(labelRange) && labelRange.length === 2) {
    const labelStart = assertFinite(labelRange[0], `${eventId}.spokenLabelTimeRange[0]`, 0, duration);
    const labelEnd = assertFinite(labelRange[1], `${eventId}.spokenLabelTimeRange[1]`, labelStart, duration);
    if (labelEnd > labelStart) spoken = [labelStart, labelEnd];
  }
  return {
    eventId,
    labelSlateText: safeText(event.labelSlateText || event.label || 'unknown', 800) || 'unknown',
    spokenLabelTimeRange: spoken,
    impactTimeRange: [start, end],
    takeNumber: event.takeNumber === undefined ? null : safeText(String(event.takeNumber), 80),
    strikeActionClass: safeText(event.strikeActionClass || event.strikeClass || 'unknown', 160) || 'unknown',
    eventType: safeText(event.eventType || event.category || 'impact', 120) || 'impact',
    position: safeText(event.position || 'unknown', 120) || 'unknown',
    distance: safeText(event.distance || 'unknown', 120) || 'unknown',
    glove: safeText(event.glove || 'unknown', 120) || 'unknown',
    force: safeText(event.force || 'unknown', 120) || 'unknown',
    confidence: event.confidence === undefined ? null : assertFinite(event.confidence, `${eventId}.confidence`, 0, 1),
    ambiguityNotes: safeText(event.ambiguityNotes, 1000),
    disposition: safeText(event.disposition || 'candidate', 80).toLowerCase(),
    rejectionReason: safeText(event.rejectionReason, 800),
  };
}

function conservativeClean(raw) {
  let cleaned = biquadLike(raw, 'highpass', 25);
  cleaned = fade(cleaned, Math.min(0.0015, cleaned.duration / 4), 'in');
  cleaned = fade(cleaned, Math.min(0.004, cleaned.duration / 4), 'out');
  return cleaned;
}

async function segmentSourceOperation({google, auth, admin, user, args = {}, helpers = {}}) {
  return withForgeIdempotency({
    operation: 'sfx.segment',
    user,
    admin,
    args,
    helpers,
    run: async ({requestId, inputSha256}) => {
      const source = await materializeImmutableSource(args);
      const wavBytes = await decodeWorkingPcm(source);
      const sourceClip = decodeWav(wavBytes);
      const supplied = Array.isArray(args.events) ? args.events : [];
      if (!supplied.length || supplied.length > MAX_EVENTS) throw forgeError(`events must contain 1-${MAX_EVENTS} ordered entries.`, 400, 'sfx_forge_events_required');
      const events = supplied.map((event, index) => normalizedEvent(event || {}, index, sourceClip.duration));
      const uploaded = [];
      const eventArtifacts = [];
      const auditionParts = [];
      const abParts = [];
      for (const event of events) {
        const [start, end] = event.impactTimeRange;
        const raw = trim(sourceClip, start, end - start);
        const cleaned = conservativeClean(raw);
        const rejected = event.disposition === 'rejected' || event.disposition === 'unusable';
        const rawBytes = encodeWav(raw);
        const rawUpload = await uploadForgeArtifact(args, requestId, {
          name: `${event.eventId}-raw.wav`,
          mimeType: 'audio/wav',
          bytes: rawBytes,
          stage: rejected ? 'rejected' : 'raw-events',
          artifactType: rejected ? 'rejected-event' : 'raw-event',
        }, google, auth);
        uploaded.push(rawUpload);
        const entry = {
          event,
          parentSourceRef: args.sourceRef,
          parentSourceSha256: source.sha256,
          raw: artifactReceipt(rawUpload, rejected ? 'rejected-raw' : 'raw-event'),
          cleaned: null,
          cleanupRecipe: {
            schemaVersion: SCHEMA_VERSION,
            operations: [
              {op: 'highpass', cutoffHz: 25, purpose: 'remove subsonic recorder/DC motion only'},
              {op: 'fade', inMs: 1.5, outMs: 4, purpose: 'prevent edit clicks without erasing physical tail'},
            ],
            normalization: false,
            denoise: false,
            tailPreserved: true,
          },
        };
        if (!rejected) {
          const cleanBytes = encodeWav(cleaned);
          const cleanUpload = await uploadForgeArtifact(args, requestId, {
            name: `${event.eventId}-cleaned-dry.wav`,
            mimeType: 'audio/wav',
            bytes: cleanBytes,
            stage: event.eventType === 'impact' ? 'cleaned-events' : safeSegment(event.eventType, 'components'),
            artifactType: 'cleaned-dry-event',
          }, google, auth);
          uploaded.push(cleanUpload);
          entry.cleaned = artifactReceipt(cleanUpload, 'cleaned-dry-event');
          const slate = event.spokenLabelTimeRange
            ? trim(sourceClip, event.spokenLabelTimeRange[0], event.spokenLabelTimeRange[1] - event.spokenLabelTimeRange[0])
            : silence({duration: 0.15, sampleRate: sourceClip.sampleRate, channels: sourceClip.channelCount});
          auditionParts.push(slate, silence({duration: 0.18, sampleRate: sourceClip.sampleRate, channels: sourceClip.channelCount}), normalizePeak(cleaned, -3), silence({duration: 0.45, sampleRate: sourceClip.sampleRate, channels: sourceClip.channelCount}));
          abParts.push(normalizePeak(raw, -3), silence({duration: 0.18, sampleRate: sourceClip.sampleRate, channels: sourceClip.channelCount}), normalizePeak(cleaned, -3), silence({duration: 0.55, sampleRate: sourceClip.sampleRate, channels: sourceClip.channelCount}));
        }
        eventArtifacts.push(entry);
      }
      if (auditionParts.length) {
        const reel = concat(auditionParts);
        uploaded.push(await uploadForgeArtifact(args, requestId, {name: 'normalized-audition-reel.wav', mimeType: 'audio/wav', bytes: encodeWav(reel), stage: 'reels', artifactType: 'audition-reel'}, google, auth));
        const ab = concat(abParts);
        uploaded.push(await uploadForgeArtifact(args, requestId, {name: 'raw-versus-cleaned-ab-reel.wav', mimeType: 'audio/wav', bytes: encodeWav(ab), stage: 'reels', artifactType: 'ab-reel'}, google, auth));
      }
      const manifest = {
        schemaVersion: SCHEMA_VERSION,
        engineVersion: ENGINE_VERSION,
        operation: 'sfx.segment',
        requestId,
        inputSha256,
        parent: {sourceRef: args.sourceRef, sha256: source.sha256, byteCount: source.byteCount, immutable: true},
        eventOrder: events.map((event) => event.eventId),
        events: eventArtifacts,
        categories: Object.fromEntries([...new Set(events.map((event) => event.eventType))].map((type) => [type, events.filter((event) => event.eventType === type).map((event) => event.eventId)])),
        humanAcceptance: 'unreviewed',
        canonicalSourceReplaced: false,
      };
      const manifestBytes = Buffer.from(JSON.stringify(manifest, null, 2), 'utf8');
      const manifestUpload = await uploadForgeArtifact(args, requestId, {name: 'event-manifest.json', mimeType: 'application/json', bytes: manifestBytes, stage: 'manifests', artifactType: 'event-manifest'}, google, auth);
      uploaded.push(manifestUpload);
      return {
        parent: manifest.parent,
        events: eventArtifacts,
        artifacts: uploaded.map((artifact) => artifactReceipt(artifact)),
        eventManifest: artifactReceipt(manifestUpload, 'event-manifest'),
        rejectedEventIds: events.filter((event) => ['rejected', 'unusable'].includes(event.disposition)).map((event) => event.eventId),
        canonicalSourceReplaced: false,
      };
    },
  });
}

function sourceRegionKey(region) {
  return `${Number(region[0]).toFixed(4)}:${Number(region[1]).toFixed(4)}`;
}

function applyLayerProcessing(clip, layer = {}, controls = {}) {
  let output = clip;
  const force = controls.force === undefined ? 0.5 : assertFinite(controls.force, 'controls.force', 0, 1);
  const mass = controls.mass === undefined ? 0.5 : assertFinite(controls.mass, 'controls.mass', 0, 1);
  const distance = controls.distance === undefined ? 0 : assertFinite(controls.distance, 'controls.distance', 0, 1);
  const intensity = controls.intensity === undefined ? 0.5 : assertFinite(controls.intensity, 'controls.intensity', 0, 1);
  const role = safeText(layer.role, 80).toLowerCase();
  if (distance > 0) output = biquadLike(output, 'lowpass', 18000 - distance * 12000);
  if (role === 'body_deformation' || role === 'internal_fill') output = gain(output, (mass - 0.5) * 5);
  if (role === 'contact' || role === 'surface_slap') output = gain(output, (force - 0.5) * 4);
  if (layer.highpassHz !== undefined) output = biquadLike(output, 'highpass', assertFinite(layer.highpassHz, 'layer.highpassHz', 10, 20000));
  if (layer.lowpassHz !== undefined) output = biquadLike(output, 'lowpass', assertFinite(layer.lowpassHz, 'layer.lowpassHz', 20, 22000));
  if (layer.gainDb !== undefined) output = gain(output, assertFinite(layer.gainDb, 'layer.gainDb', -60, 24));
  if (layer.compressor) output = compress(output, safeNumber(layer.compressor.thresholdDb, -18), safeNumber(layer.compressor.ratio, 2));
  if (layer.saturation) output = distort(output, 1 + intensity * assertFinite(layer.saturation, 'layer.saturation', 0, 5));
  return output;
}

async function renderSourceConditionedOperation({google, auth, admin, user, args = {}, helpers = {}}) {
  return withForgeIdempotency({
    operation: 'sfx.render',
    user,
    admin,
    args,
    helpers,
    run: async ({requestId, inputSha256}) => {
      const source = await materializeImmutableSource(args);
      const sourceClip = decodeWav(await decodeWorkingPcm(source));
      const recipe = args.recipe && typeof args.recipe === 'object' && !Array.isArray(args.recipe) ? args.recipe : {};
      const candidates = Array.isArray(recipe.candidates) ? recipe.candidates : [];
      if (!candidates.length || candidates.length > MAX_CANDIDATES) throw forgeError(`recipe.candidates must contain 1-${MAX_CANDIDATES} candidates.`, 400, 'sfx_forge_candidates_required');
      const allRegionKeys = [];
      const candidateRegionSets = [];
      for (const candidate of candidates) {
        const layers = Array.isArray(candidate.layers) ? candidate.layers : [];
        if (!layers.length) throw forgeError('Every candidate requires at least one named physical source layer.', 400, 'sfx_forge_layers_required');
        const keys = new Set();
        for (const layer of layers) {
          const region = layer.sourceTimeRange;
          if (!Array.isArray(region) || region.length !== 2) throw forgeError('Every source layer requires sourceTimeRange [start,end].', 400, 'sfx_forge_layer_range_required');
          assertFinite(region[0], 'layer.sourceTimeRange[0]', 0, sourceClip.duration);
          assertFinite(region[1], 'layer.sourceTimeRange[1]', region[0], sourceClip.duration);
          const key = sourceRegionKey(region);
          keys.add(key);
          allRegionKeys.push(key);
        }
        candidateRegionSets.push([...keys].sort().join('|'));
      }
      if (candidates.length > 1 && new Set(candidateRegionSets).size !== candidates.length) {
        throw forgeError('Candidate family reuses the same source-region set; pitch-shifted or disguised clones are not permitted.', 422, 'sfx_forge_clone_family_rejected');
      }
      if (candidates.length > 1 && new Set(allRegionKeys).size < 2) {
        throw forgeError('A multi-candidate family requires at least two materially distinct source regions.', 422, 'sfx_forge_distinct_sources_required');
      }
      const uploaded = [];
      const renderedCandidates = [];
      for (let index = 0; index < candidates.length; index += 1) {
        const candidate = candidates[index];
        const candidateId = safeSegment(candidate.candidateId || `candidate-${index + 1}`, `candidate-${index + 1}`);
        const controls = candidate.controls && typeof candidate.controls === 'object' ? candidate.controls : {};
        const layers = [];
        let duration = 0;
        for (const layer of candidate.layers) {
          const region = layer.sourceTimeRange;
          const physical = trim(sourceClip, region[0], region[1] - region[0]);
          const processed = applyLayerProcessing(physical, layer, controls);
          layers.push({clip: toChannels(processed, 2), at: safeNumber(layer.atSeconds, 0), gainDb: 0, pan: safeNumber(layer.pan, 0)});
          duration = Math.max(duration, safeNumber(layer.atSeconds, 0) + processed.duration);
        }
        let mixed = timeline({duration: Math.min(sourceClip.duration, duration + 0.05), sampleRate: sourceClip.sampleRate, channels: 2, items: layers});
        mixed = limit(mixed, safeNumber(candidate.ceilingDb, -1));
        const bytes = encodeWav(mixed);
        const artifact = await uploadForgeArtifact(args, requestId, {name: `${candidateId}.wav`, mimeType: 'audio/wav', bytes, stage: 'candidates', artifactType: 'source-conditioned-candidate'}, google, auth);
        uploaded.push(artifact);
        renderedCandidates.push({
          candidateId,
          controls,
          sourceRegions: candidate.layers.map((layer) => ({role: safeText(layer.role, 80) || 'unknown', sourceTimeRange: layer.sourceTimeRange, sourceRegionKey: sourceRegionKey(layer.sourceTimeRange)})),
          metrics: measure(mixed),
          artifact: artifactReceipt(artifact, 'candidate'),
          state: 'candidate',
          humanAcceptance: 'unreviewed',
        });
      }
      const canonicalRecipe = {
        schemaVersion: SCHEMA_VERSION,
        engineVersion: ENGINE_VERSION,
        seed: safeText(recipe.seed, 160) || 'deterministic-no-randomness',
        sourceRef: args.sourceRef,
        sourceSha256: source.sha256,
        candidates,
      };
      const recipeSha256 = sha256Hex(Buffer.from(stableJson(canonicalRecipe), 'utf8'));
      const manifest = {
        schemaVersion: SCHEMA_VERSION,
        engineVersion: ENGINE_VERSION,
        operation: 'sfx.render',
        requestId,
        inputSha256,
        recipeSha256,
        recipe: canonicalRecipe,
        parent: {sourceRef: args.sourceRef, sha256: source.sha256, immutable: true},
        candidates: renderedCandidates,
        forbiddenVariationStrategies: ['pitch_shifted_clones', 'untraceable_source_substitution', 'oscillator_as_material_identity'],
        humanAcceptance: 'unreviewed',
      };
      const manifestBytes = Buffer.from(JSON.stringify(manifest, null, 2), 'utf8');
      const manifestUpload = await uploadForgeArtifact(args, requestId, {name: 'source-conditioned-render-manifest.json', mimeType: 'application/json', bytes: manifestBytes, stage: 'manifests', artifactType: 'render-manifest'}, google, auth);
      uploaded.push(manifestUpload);
      return {
        recipeSha256,
        parent: manifest.parent,
        candidates: renderedCandidates,
        artifacts: uploaded.map((artifact) => artifactReceipt(artifact)),
        renderManifest: artifactReceipt(manifestUpload, 'render-manifest'),
        canonicalSourceReplaced: false,
      };
    },
  });
}

async function sfxForgeStatusOperation({admin, requestId, helpers = {}}) {
  const id = safeText(requestId, 160);
  if (!id) throw forgeError('requestId is required.', 400, 'sfx_forge_request_id_required');
  const audit = helpers.existingAudit ? await helpers.existingAudit(admin, id) : null;
  if (!audit) return {ok: false, operation: 'sfx.status', requestId: id, status: 'missing'};
  return {
    ok: true,
    operation: 'sfx.status',
    requestId: id,
    status: safeText(audit.status, 80) || 'unknown',
    inputSha256: safeText(audit.inputSha256, 128),
    result: audit.result || null,
    progress: audit.progress || null,
    humanAcceptance: audit.result && audit.result.humanAcceptance || 'unreviewed',
  };
}

module.exports = {
  ENGINE_VERSION,
  SCHEMA_VERSION,
  DEFAULT_TRANSCRIPTION_MODEL,
  analyzeSourceOperation,
  segmentSourceOperation,
  renderSourceConditionedOperation,
  sfxForgeStatusOperation,
  internals: {
    stableJson,
    detectTransients,
    spectralProfile,
    conservativeClean,
    normalizedEvent,
    sourceRegionKey,
    applyLayerProcessing,
    standardsMetrics,
    decodeWorkingPcm,
    transcribeSlate,
  },
};
