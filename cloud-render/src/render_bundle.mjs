import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {Storage} from '@google-cloud/storage';
import {google} from 'googleapis';

const storage = new Storage();
const TOOL_VERSION = process.env.RENDER_TOOL_VERSION || 'command-center-blender-render-v1';
const CACHE_BUCKET = process.env.RENDER_CACHE_BUCKET || process.env.HOME_CENTER_GENERATED_BUCKET || process.env.COMMAND_CENTER_GENERATED_BUCKET || process.env.COMMAND_CENTER_RENDER_BUCKET || 'home-center-generated';
const MAX_GLB_BYTES = Number(process.env.RENDER_MAX_GLB_BYTES || 250 * 1024 * 1024);
const MAX_SCRIPT_BYTES = Number(process.env.RENDER_MAX_SCRIPT_BYTES || 1024 * 1024);
const MAX_OUTPUT_BYTES = Number(process.env.RENDER_MAX_OUTPUT_BYTES || 400 * 1024 * 1024);
const MAX_OUTPUT_FILE_BYTES = Number(process.env.RENDER_MAX_OUTPUT_FILE_BYTES || 180 * 1024 * 1024);
const RENDER_TIMEOUT_MS = Number(process.env.RENDER_TIMEOUT_MS || 600000);
const REQUIRED_BUNDLE_KINDS = [
  'rendered_frames', 'contact_sheet', 'native_pose_animation_data', 'script_input_hashes',
  'blender_version_settings', 'stdout_stderr', 'fixed_camera_renders', 'diagnostic_view_renders', 'validation_manifest',
  'original_script',
];

function typedError(message, status = 400, failureKind = 'input_validation') {
  const err = new Error(message);
  err.status = status;
  err.failureKind = failureKind;
  return err;
}
function sha256Buffer(buffer) { return crypto.createHash('sha256').update(buffer).digest('hex'); }
function sha256File(file) { return sha256Buffer(fs.readFileSync(file)); }
function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}';
  return JSON.stringify(value);
}
function safeName(value) { return String(value || 'render').replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 100) || 'render'; }
function parseGs(ref) { const m = String(ref).match(/^gs:\/\/([^/]+)\/(.+)$/); if (!m) throw typedError('Invalid gs ref: ' + ref, 400, 'input_validation'); return {bucket: m[1], name: m[2]}; }
function nowMs() { return Date.now(); }
async function timedPhase(timings, name, fn) {
  const startedAtMs = nowMs();
  try {
    return await fn();
  } finally {
    timings[name + 'Ms'] = (timings[name + 'Ms'] || 0) + Math.max(0, nowMs() - startedAtMs);
  }
}
function timedSyncPhase(timings, name, fn) {
  const startedAtMs = nowMs();
  try {
    return fn();
  } finally {
    timings[name + 'Ms'] = (timings[name + 'Ms'] || 0) + Math.max(0, nowMs() - startedAtMs);
  }
}
function artifactObjectName(cacheKey, relPath, contentType = '') {
  const cleanRel = String(relPath || 'artifact.bin').replace(/^\/+/, '');
  const lower = cleanRel.toLowerCase();
  if (lower.endsWith('.gif')) return `renders/gifs/${cacheKey}/${cleanRel}`;
  if (lower.includes('contact-sheet') || contentType === 'image/png' && /contact/i.test(cleanRel)) return `renders/contact-sheets/${cacheKey}/${cleanRel}`;
  if (lower.endsWith('.glb')) return `glb/${cacheKey}/${cleanRel}`;
  if (lower.endsWith('.log') || lower.endsWith('.txt') || lower === 'stdout.txt' || lower === 'stderr.txt') return `logs/blender/${cacheKey}/${cleanRel}`;
  return `renders/blender/${cacheKey}/${cleanRel}`;
}
function artifactTypeFor(relPath, contentType = '') {
  const lower = String(relPath || '').toLowerCase();
  if (lower.endsWith('.gif')) return 'gif';
  if (lower.includes('contact-sheet')) return 'contact_sheet';
  if (lower.endsWith('.glb')) return 'glb';
  if (lower.endsWith('.log') || lower.endsWith('.txt') || lower === 'stdout.txt' || lower === 'stderr.txt') return 'log';
  if (/^image\//.test(contentType)) return 'rendered_frames';
  return 'render';
}
async function uploadFile(localPath, cacheKey, relPath, contentType = '') {
  if (!CACHE_BUCKET) return 'file://' + localPath;
  const dest = artifactObjectName(cacheKey, relPath, contentType);
  const sha256 = sha256File(localPath);
  await storage.bucket(CACHE_BUCKET).upload(localPath, {destination: dest, metadata: {contentType: contentType || contentTypeFor(localPath), metadata: {sha256, owner: 'drew', project: 'home-center', stage: 'temp', engine: 'blender', createdBy: 'command-center-cloud-render', jobId: cacheKey, commit: process.env.K_REVISION || '', timestamp: new Date().toISOString(), approved: 'false', artifactType: artifactTypeFor(relPath, contentType)}}});
  return `gs://${CACHE_BUCKET}/${dest}`;
}
function driveFileId(ref) { const raw = String(ref).replace(/^drive:\/\//i, ''); return raw.split(/[?#/]/).filter(Boolean).pop() || raw; }
function providerStatus(err) {
  return Number(err && (err.status || err.code || err.response?.status)) || 0;
}
function redactedProviderMessage(err) {
  const status = providerStatus(err);
  const text = String(err && err.message || err || '').replace(/Bearer\s+[A-Za-z0-9._~+\/-]+/gi, 'Bearer [redacted]').slice(0, 240);
  return status ? 'HTTP ' + status + (text ? ': ' + text : '') : text;
}
async function downloadGs(ref) {
  try {
    const {bucket, name} = parseGs(ref);
    const [buf] = await storage.bucket(bucket).file(name).download();
    return buf;
  } catch (err) {
    throw typedError('render_input_gcs_read_auth_failed: renderer could not read staged GCS input (' + redactedProviderMessage(err) + ').', providerStatus(err) || 403, 'render_input_gcs_read_auth_failed');
  }
}
async function downloadDrive(ref, token) {
  if (!token) throw typedError('drive_input_download_auth_failed: Drive render input requires a user Google OAuth access token.', 401, 'drive_input_download_auth_failed');
  try {
    const auth = new google.auth.OAuth2();
    auth.setCredentials({access_token: token});
    const drive = google.drive({version: 'v3', auth});
    const res = await drive.files.get({fileId: driveFileId(ref), alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
    return Buffer.from(res.data);
  } catch (err) {
    throw typedError('drive_input_download_auth_failed: renderer could not download Drive input (' + redactedProviderMessage(err) + ').', providerStatus(err) || 401, 'drive_input_download_auth_failed');
  }
}
function bucketInputFor(ref, bucketInputs) {
  const raw = String(ref).replace(/^bucket:\/\//i, '').replace(/^command-center\//i, '');
  const objectId = raw.split(/[?#]/)[0].split('/').filter(Boolean).pop() || raw;
  return (bucketInputs || []).find((item) => item.objectId === objectId || item.path === raw || item.objectUri === ref);
}
function decodeUploadObject(upload, role) {
  if (!upload || typeof upload !== 'object') return null;
  const base64 = upload.base64 || upload.contentBase64 || upload.dataBase64 || upload.data || '';
  if (!base64) return null;
  return Buffer.from(String(base64), 'base64');
}
async function resolveRef(ref, request, role) {
  const direct = role === 'glb' ? decodeUploadObject(request.glbUpload, role) : decodeUploadObject(request.scriptUpload, role);
  if (direct) return direct;
  if (/^gs:\/\//i.test(ref)) return downloadGs(ref);
  if (/^drive:\/\//i.test(ref)) return downloadDrive(ref, request.googleOAuthAccessToken || '');
  if (/^bucket:\/\//i.test(ref)) {
    const item = bucketInputFor(ref, request.bucketInputs || []);
    if (!item) throw typedError('Bucket input was not provided by Command Center for ' + role + ': ' + ref, 404, 'transport');
    if (item.body) return Buffer.from(item.body, 'utf8');
    if (item.objectUri && /^gs:\/\//i.test(item.objectUri)) return downloadGs(item.objectUri);
    if (item.objectUri && /^drive:\/\//i.test(item.objectUri)) return downloadDrive(item.objectUri, request.googleOAuthAccessToken || '');
    throw typedError('Bucket input has no supported body/objectUri for ' + role + ': ' + ref, 400, 'transport');
  }
  throw typedError('Unsupported ref for ' + role + ': ' + ref, 400, 'input_validation');
}
function validateGlbBytes(bytes, label) {
  if (!Buffer.isBuffer(bytes) || bytes.length < 12) throw typedError(label + ' is too small to be a GLB file.');
  if (bytes.length > MAX_GLB_BYTES) throw typedError(label + ' exceeds max GLB size ' + MAX_GLB_BYTES + ' bytes.', 413, 'input_validation');
  if (bytes.slice(0, 4).toString('ascii') !== 'glTF') throw typedError(label + ' is not a GLB: missing glTF magic.');
  if (bytes.readUInt32LE(4) !== 2) throw typedError(label + ' must be GLB version 2.');
  if (bytes.readUInt32LE(8) > bytes.length) throw typedError(label + ' declares more bytes than were supplied.');
}
function validateScriptBytes(bytes, label) {
  if (!Buffer.isBuffer(bytes) || bytes.length === 0) throw typedError(label + ' is empty.');
  if (bytes.length > MAX_SCRIPT_BYTES) throw typedError(label + ' exceeds max script size ' + MAX_SCRIPT_BYTES + ' bytes.', 413, 'input_validation');
  if (bytes.includes(0)) throw typedError(label + ' must be a text Python script, not binary data.');
}
function listFiles(dir) {
  const out = [];
  const stack = [dir];
  while (stack.length) {
    const cur = stack.pop();
    if (!fs.existsSync(cur)) continue;
    for (const ent of fs.readdirSync(cur, {withFileTypes: true})) {
      const full = path.join(cur, ent.name);
      if (ent.isDirectory()) stack.push(full); else out.push(full);
    }
  }
  return out.sort();
}
function enforceOutputLimits(dir) {
  let total = 0;
  for (const file of listFiles(dir)) {
    const size = fs.statSync(file).size;
    if (size > MAX_OUTPUT_FILE_BYTES) throw typedError('Renderer output file exceeds limit: ' + path.basename(file), 413, 'artifact_publication');
    total += size;
    if (total > MAX_OUTPUT_BYTES) throw typedError('Renderer outputs exceed total limit ' + MAX_OUTPUT_BYTES + ' bytes.', 413, 'artifact_publication');
  }
}
function contentType(file) {
  const ext = path.extname(file).toLowerCase();
  if (ext === '.png') return 'image/png';
  if (ext === '.gif') return 'image/gif';
  if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg';
  if (ext === '.glb') return 'model/gltf-binary';
  if (ext === '.blend') return 'application/octet-stream';
  if (ext === '.json') return 'application/json';
  if (ext === '.py') return 'text/x-python';
  if (ext === '.txt' || ext === '.log') return 'text/plain';
  return 'application/octet-stream';
}
async function cachedManifest(cacheKey) {
  if (!CACHE_BUCKET) return null;
  const file = storage.bucket(CACHE_BUCKET).file(`renders/blender/${cacheKey}/validation-manifest.json`);
  const [exists] = await file.exists();
  if (!exists) return null;
  const [buf] = await file.download();
  const manifest = JSON.parse(buf.toString('utf8'));
  return {...manifest, cacheHit: true};
}
function makeContactSheet(frames, outPath) {
  if (!frames.length) return false;
  const montage = spawnSync('montage', [...frames, '-geometry', '480x360+8+8', '-background', '#111111', outPath], {encoding: 'utf8', timeout: 60000});
  if (montage.status === 0 && fs.existsSync(outPath)) return true;
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-contact-sheet-'));
  const rowFiles = [];
  for (let index = 0; index < frames.length; index += 4) {
    const rowFile = path.join(workDir, `row-${String(index / 4).padStart(2, '0')}.png`);
    const row = spawnSync('convert', [...frames.slice(index, index + 4), '+append', rowFile], {encoding: 'utf8', timeout: 60000});
    if (row.status !== 0 || !fs.existsSync(rowFile)) return false;
    rowFiles.push(rowFile);
  }
  const sheet = spawnSync('convert', [...rowFiles, '-append', outPath], {encoding: 'utf8', timeout: 60000});
  return sheet.status === 0 && fs.existsSync(outPath);
}

function numberArray(value) {
  return Array.isArray(value) ? value.map((item) => Number(item)).filter((item) => Number.isFinite(item)) : [];
}
function firstArray(...values) {
  for (const value of values) if (Array.isArray(value)) return value;
  return null;
}
function integerFrame(value, label) {
  const number = Number(value);
  if (!Number.isInteger(number) || number < 0) throw typedError(label + ' must be a non-negative integer frame index.');
  return number;
}
function pngDimensions(file) {
  const result = spawnSync('identify', ['-format', '%w %h', file], {encoding: 'utf8', timeout: 15000});
  if (result.status !== 0) throw typedError('GIF assembly could not inspect PNG dimensions for ' + path.basename(file) + ': ' + String(result.stderr || result.stdout || '').slice(0, 240), 500, 'artifact_publication');
  const match = String(result.stdout || '').trim().match(/^(\d+)\s+(\d+)$/);
  if (!match) throw typedError('GIF assembly received invalid PNG dimension metadata for ' + path.basename(file) + '.', 500, 'artifact_publication');
  return {width: Number(match[1]), height: Number(match[2])};
}
function buildGifPlaybackContract(frames, scriptManifest = {}, settings = {}) {
  const renderedFrameNames = Array.isArray(scriptManifest.renderedFrames) ? scriptManifest.renderedFrames : [];
  const evidenceSource = firstArray(settings.evidenceFrames, scriptManifest.evidenceFrames);
  const evidenceFrames = frames.map((file, index) => {
    const declared = evidenceSource && evidenceSource[index] !== undefined ? evidenceSource[index] : index;
    return {index: integerFrame(declared, 'evidenceFrames[' + index + ']'), sourceIndex: index, file, manifestPath: renderedFrameNames[index] || path.basename(file)};
  });
  const evidenceSeen = new Set();
  for (const frame of evidenceFrames) {
    if (evidenceSeen.has(frame.index)) throw typedError('evidenceFrames contains duplicate index ' + frame.index + '.');
    evidenceSeen.add(frame.index);
  }
  const explicitGifFrames = Array.isArray(settings.gifFrames) || Array.isArray(scriptManifest.gifFrames);
  const rawGifFrames = firstArray(settings.gifFrames, scriptManifest.gifFrames) || evidenceFrames.map((frame) => frame.index);
  const gifFrames = rawGifFrames.map((value, index) => integerFrame(value, 'gifFrames[' + index + ']'));
  if (!gifFrames.length) throw typedError('gifFrames must not be empty.');
  const allowRepeat = settings.allowRepeatedGifFrames === true || scriptManifest.allowRepeatedGifFrames === true;
  if (!allowRepeat) {
    const seen = new Set();
    for (const frame of gifFrames) {
      if (seen.has(frame)) throw typedError('gifFrames contains duplicate index ' + frame + '; set allowRepeatedGifFrames only when repeated playback is intentional.');
      seen.add(frame);
    }
  }
  const explicitTiming = Array.isArray(settings.gifTimingMs) || Array.isArray(scriptManifest.gifTimingMs);
  let rawTiming = firstArray(settings.gifTimingMs, scriptManifest.gifTimingMs);
  if (!rawTiming && explicitGifFrames) throw typedError('gifTimingMs is required when gifFrames is explicit.');
  if (!rawTiming) {
    const sourceTiming = firstArray(scriptManifest.frameDurationsMs, settings.frameDurationsMs) || [];
    rawTiming = gifFrames.map((frame, index) => {
      const evidence = evidenceFrames.find((item) => item.index === frame);
      return Number(sourceTiming[evidence ? evidence.sourceIndex : index] || 100) || 100;
    });
  }
  const gifTimingMs = numberArray(rawTiming).map((ms) => Math.max(1, Math.round(ms)));
  if (gifTimingMs.length !== gifFrames.length) throw typedError('gifTimingMs.length must equal gifFrames.length.');
  const selected = gifFrames.map((frame) => {
    const match = evidenceFrames.find((item) => item.index === frame);
    if (!match) throw typedError('gifFrames requested missing evidence frame index ' + frame + '.');
    return match;
  });
  return {
    authoredKeys: numberArray(firstArray(settings.authoredKeys, scriptManifest.authoredKeys) || []),
    evidenceFrames: evidenceFrames.map((frame) => frame.index),
    gifFrames,
    gifTimingMs,
    allowRepeatedGifFrames: allowRepeat,
    explicitGifFrames,
    explicitGifTiming: explicitTiming,
    selectedFrames: selected.map((frame, index) => ({playbackIndex: index, evidenceFrame: frame.index, sourceIndex: frame.sourceIndex, manifestPath: frame.manifestPath, timingMs: gifTimingMs[index]})),
  };
}
function makeLoopingGif(frames, outPath, {scriptManifest = {}, settings = {}} = {}) {
  if (!frames.length) return null;
  const contract = buildGifPlaybackContract(frames, scriptManifest, settings);
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-looping-gif-'));
  const selectedFiles = contract.selectedFrames.map((frame) => frames[frame.sourceIndex]);
  const prepared = [];
  const firstSize = pngDimensions(selectedFiles[0]);
  for (const [index, frame] of selectedFiles.entries()) {
    const size = pngDimensions(frame);
    if (size.width !== firstSize.width || size.height !== firstSize.height) throw typedError('GIF assembly requires compatible PNG dimensions; ' + path.basename(frame) + ' differs from the first selected frame.');
    const preparedPath = path.join(workDir, 'gif-frame-' + String(index).padStart(3, '0') + '.png');
    const preparedRef = 'PNG32:' + preparedPath;
    const convert = spawnSync('convert', ['-size', firstSize.width + 'x' + firstSize.height, 'xc:none', frame, '-alpha', 'on', '-compose', 'Over', '-composite', preparedRef], {encoding: 'utf8', timeout: 30000});
    if (convert.status !== 0 || !fs.existsSync(preparedPath)) throw typedError('GIF assembly failed to prepare transparent frame ' + index + ': ' + String(convert.stderr || convert.stdout || '').slice(0, 240), 500, 'artifact_publication');
    prepared.push(preparedPath);
  }
  const args = ['-background', 'none'];
  prepared.forEach((frame, index) => {
    const delayCs = Math.max(1, Math.round(contract.gifTimingMs[index] / 10));
    args.push('-dispose', 'Background', '-delay', String(delayCs), frame);
  });
  args.push('-loop', '0', outPath);
  const convert = spawnSync('convert', args, {encoding: 'utf8', timeout: 60000});
  if (convert.status !== 0 || !fs.existsSync(outPath)) throw typedError('GIF assembly failed: ' + String(convert.stderr || convert.stdout || '').slice(0, 240), 500, 'artifact_publication');
  return contract;
}
function boolOption(value, fallback = true) {
  if (value === false || value === 'false' || value === 0 || value === '0') return false;
  if (value === true || value === 'true' || value === 1 || value === '1') return true;
  return fallback;
}
function renderBundleOptions(request = {}) {
  const settings = request.settings || {};
  const contract = request.executionContract || {};
  const includeBlend = boolOption(settings.includeBlend ?? contract.includeBlend, true);
  const includeDiagnostics = boolOption(settings.includeDiagnostics ?? contract.includeDiagnostics, true);
  return {includeBlend, includeDiagnostics};
}
function requiredBundleKindsFor(options = {}) {
  const required = REQUIRED_BUNDLE_KINDS.filter((kind) => options.includeDiagnostics || kind !== 'diagnostic_view_renders');
  if (options.includeBlend) required.push('three_d_artifact');
  return required;
}
function localManifestPath(outputDir, value) {
  if (!value) return '';
  const resolved = path.resolve(outputDir, value);
  const absolute = path.isAbsolute(value) ? path.normalize(value) : resolved;
  const relative = path.relative(outputDir, absolute);
  if (relative.startsWith('..') || path.isAbsolute(relative)) return '';
  return absolute;
}
function existingManifestFiles(outputDir, values) {
  return (Array.isArray(values) ? values : []).map((value) => localManifestPath(outputDir, value)).filter((file) => file && fs.existsSync(file));
}
function writePythonNetworkWrapper(wrapperPath) {
  fs.writeFileSync(wrapperPath, `import os, runpy, socket, sys\n\nclass _NetworkDisabled(Exception):\n    pass\n\ndef _blocked(*args, **kwargs):\n    raise RuntimeError('Network and process escape are disabled inside Command Center Blender render scripts')\n\nsocket.socket = _blocked\nsocket.create_connection = _blocked\nos.system = _blocked\nos.popen = _blocked\ntry:\n    import numpy as _np\n    if not hasattr(_np, 'bool'):\n        _np.bool = bool\nexcept Exception:\n    pass\nfor name in ['http.client', 'urllib.request', 'urllib3', 'requests', 'ftplib', 'smtplib', 'subprocess']:\n    sys.modules[name] = None\nif '--' not in sys.argv or len(sys.argv[sys.argv.index('--') + 1:]) < 5:\n    raise SystemExit('Usage after --: user_script glb output_dir settings_json manifest_json')\nargs = sys.argv[sys.argv.index('--') + 1:]\nscript = args[0]\nsys.argv = [script, '--'] + args[1:]\nrunpy.run_path(script, run_name='__main__')\n`, 'utf8');
}
function blenderResultFailureKind(result) {
  if (result.error && String(result.error.message || '').toLowerCase().includes('timeout')) return 'timeout';
  if (result.signal === 'SIGTERM' || result.signal === 'SIGKILL') return 'timeout';
  return 'blender_execution';
}
function parseScriptManifest(scriptManifestPath, result) {
  if (!fs.existsSync(scriptManifestPath)) {
    return {scriptManifest: {}, failureKind: result.status === 0 ? 'artifact_publication' : blenderResultFailureKind(result), manifestError: 'Blender script did not produce script-output-manifest.json.'};
  }
  try {
    return {scriptManifest: JSON.parse(fs.readFileSync(scriptManifestPath, 'utf8')), failureKind: '', manifestError: ''};
  } catch (err) {
    return {scriptManifest: {}, failureKind: 'artifact_publication', manifestError: 'Blender script manifest was not valid JSON: ' + (err.message || String(err))};
  }
}

export async function renderBundle(request = {}) {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-blender-render-'));
  const inputDir = path.join(work, 'input');
  const outputDir = path.join(work, 'output');
  fs.mkdirSync(inputDir, {recursive: true}); fs.mkdirSync(outputDir, {recursive: true});
  let manifest = null;
  const timings = {startedAtMs: nowMs()};
  try {
    const options = renderBundleOptions(request);
    const requiredBundleKinds = requiredBundleKindsFor(options);
    const glbBytes = await timedPhase(timings, 'resolveGlb', () => resolveRef(request.glbRef || '', request, 'glb'));
    const scriptBytes = await timedPhase(timings, 'resolveScript', () => resolveRef(request.scriptRef || '', request, 'script'));
    timedSyncPhase(timings, 'validateInputs', () => {
      validateGlbBytes(glbBytes, 'glb input');
      validateScriptBytes(scriptBytes, 'script input');
    });
    const glbPath = path.join(inputDir, 'input.glb');
    const scriptPath = path.join(inputDir, 'render.py');
    const wrapperPath = path.join(inputDir, 'network_disabled_wrapper.py');
    timedSyncPhase(timings, 'writeInputs', () => { fs.writeFileSync(glbPath, glbBytes); fs.writeFileSync(scriptPath, scriptBytes); writePythonNetworkWrapper(wrapperPath); });
    const glbHash = sha256Buffer(glbBytes);
    const scriptHash = sha256Buffer(scriptBytes);
    const settings = request.settings || {};
    const blenderVersion = timedSyncPhase(timings, 'blenderVersion', () => spawnSync('blender', ['--background', '--version'], {encoding: 'utf8', timeout: 30000}));
    const blenderVersionText = (blenderVersion.stdout || blenderVersion.stderr || '').split('\n').slice(0, 3).join('\n');
    const cacheKey = crypto.createHash('sha256').update(stableJson({glbHash, scriptHash, settings, executionContract: request.executionContract || {}, blenderVersion: blenderVersionText, toolVersion: TOOL_VERSION})).digest('hex');
    if (request.cache !== false) {
      const hit = await timedPhase(timings, 'cacheLookup', () => cachedManifest(cacheKey));
      if (hit) return {...hit, ok: true, status: 'completed', cacheHit: true, renderId: request.renderId || hit.renderId || '', cacheKey, timings: {...hit.timings, cacheLookupMs: timings.cacheLookupMs || 0, totalMs: Math.max(0, nowMs() - timings.startedAtMs)}};
    }
    const settingsPath = path.join(inputDir, 'settings.json');
    const scriptManifestPath = path.join(outputDir, 'script-output-manifest.json');
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
    const stdoutPath = path.join(outputDir, 'stdout.txt');
    const stderrPath = path.join(outputDir, 'stderr.txt');
    const blenderEnv = {...process.env, LIBGL_ALWAYS_SOFTWARE: '1'};
    const result = timedSyncPhase(timings, 'blenderExecution', () => spawnSync('blender', ['--background', '--python-exit-code', '88', '--python', wrapperPath, '--', scriptPath, glbPath, outputDir, settingsPath, scriptManifestPath], {encoding: 'utf8', timeout: RENDER_TIMEOUT_MS, maxBuffer: 80 * 1024 * 1024, env: blenderEnv}));
    fs.writeFileSync(stdoutPath, result.stdout || ''); fs.writeFileSync(stderrPath, result.stderr || result.error?.message || '');
    const parsed = timedSyncPhase(timings, 'parseScriptManifest', () => parseScriptManifest(scriptManifestPath, result));
    const scriptManifest = parsed.scriptManifest;
    const frames = existingManifestFiles(outputDir, scriptManifest.renderedFrames || []);
    const fixed = existingManifestFiles(outputDir, scriptManifest.fixedCameraRenders || []);
    const diagnostics = existingManifestFiles(outputDir, scriptManifest.diagnosticViewRenders || []);
    const contactSheet = path.join(outputDir, 'contact-sheet.png');
    timedSyncPhase(timings, 'contactSheet', () => makeContactSheet(frames, contactSheet));
    let generatedLoopingGif = '';
    let gifPlaybackContract = null;
    if (frames.length) {
      const gifPath = path.join(outputDir, 'walk-loop.gif');
      gifPlaybackContract = timedSyncPhase(timings, 'loopingGif', () => makeLoopingGif(frames, gifPath, {scriptManifest, settings}));
      if (gifPlaybackContract) {
        generatedLoopingGif = 'walk-loop.gif';
        fs.writeFileSync(path.join(outputDir, 'gif-playback-contract.json'), JSON.stringify({schema: 'home-center.blender-gif-playback-contract.v1', ...gifPlaybackContract}, null, 2));
      }
    }
    const outputFilesBeforeHashes = listFiles(outputDir);
    const hashesPath = path.join(outputDir, 'script-input-hashes.json');
    const outputHashes = {};
    for (const file of outputFilesBeforeHashes) outputHashes[path.relative(outputDir, file)] = {sha256: sha256File(file), byteCount: fs.statSync(file).size};
    fs.writeFileSync(hashesPath, JSON.stringify({
      glbRef: request.glbRef || '', scriptRef: request.scriptRef || '', glbHash, scriptHash,
      settingsHash: sha256Buffer(Buffer.from(stableJson(settings))), toolVersion: TOOL_VERSION,
      stagedInputs: request.stagedInputs || [], outputHashes,
    }, null, 2));
    const blenderSettingsPath = path.join(outputDir, 'blender-version-settings.json');
    fs.writeFileSync(blenderSettingsPath, JSON.stringify({blenderVersion: blenderVersionText, settings, renderToolVersion: TOOL_VERSION, exitCode: result.status, signal: result.signal || ''}, null, 2));
    timedSyncPhase(timings, 'enforceOutputLimits', () => enforceOutputLimits(outputDir));
    const validation = {
      schema: 'command-center.blender-render.validation.v1',
      atomicOperation: 'GLB + script + execution contract -> durable 3D artifact + visual evidence',
      framesAreInsufficient: true,
      presentBundleKinds: [],
      glbHash,
      scriptHash,
      cacheKey,
      blenderExitCode: result.status,
      blenderSignal: result.signal || '',
      failureKind: parsed.failureKind || (result.status === 0 ? '' : blenderResultFailureKind(result)),
      manifestError: parsed.manifestError || '',
      gifPlaybackContract,
    };
    const refs = {renderedFrames: [], fixedCameraRenders: [], diagnosticViewRenders: [], threeDArtifacts: [], nativePoseAnimationData: [], loopingGif: '', gifPlaybackContract: ''};
    const add = async (kind, local, rel, key, ctype) => {
      if (!local || !fs.existsSync(local)) return '';
      const uri = await timedPhase(timings, 'uploadArtifacts', () => uploadFile(local, cacheKey, rel, ctype || contentType(local)));
      if (!validation.presentBundleKinds.includes(kind)) validation.presentBundleKinds.push(kind);
      if (key) refs[key] = Array.isArray(refs[key]) ? [...refs[key], uri] : uri;
      return uri;
    };
    for (const [i, f] of frames.entries()) await add('rendered_frames', f, `frames/${i}-${safeName(path.basename(f))}`, 'renderedFrames');
    for (const [i, f] of fixed.entries()) await add('fixed_camera_renders', f, `fixed/${i}-${safeName(path.basename(f))}`, 'fixedCameraRenders');
    if (options.includeDiagnostics) for (const [i, f] of diagnostics.entries()) await add('diagnostic_view_renders', f, `diagnostic/${i}-${safeName(path.basename(f))}`, 'diagnosticViewRenders');
    refs.contactSheet = await add('contact_sheet', contactSheet, 'contact-sheet.png', '', 'image/png');
    refs.loopingGif = await add('looping_gif', localManifestPath(outputDir, generatedLoopingGif || scriptManifest.loopingGif), 'walk-loop.gif', '', 'image/gif');
    refs.gifPlaybackContract = await add('gif_playback_contract', localManifestPath(outputDir, 'gif-playback-contract.json'), 'gif-playback-contract.json', 'gifPlaybackContract', 'application/json');
    refs.modifiedBlend = options.includeBlend ? await add('three_d_artifact', localManifestPath(outputDir, scriptManifest.modifiedBlend), 'modified.blend', 'threeDArtifacts') : '';
    refs.animatedGlb = await add('three_d_artifact', localManifestPath(outputDir, scriptManifest.animatedGlb), 'animated.glb', 'threeDArtifacts');
    refs.nativePoseAnimationData = [await add('native_pose_animation_data', localManifestPath(outputDir, scriptManifest.nativePoseAnimationData), 'native-pose-animation.json', '', 'application/json')].filter(Boolean);
    refs.originalScript = await add('original_script', scriptPath, 'original-script.py', '', 'text/x-python');
    refs.scriptInputHashes = await add('script_input_hashes', hashesPath, 'script-input-hashes.json', '', 'application/json');
    refs.blenderVersionSettings = await add('blender_version_settings', blenderSettingsPath, 'blender-version-settings.json', '', 'application/json');
    refs.stdout = await add('stdout_stderr', stdoutPath, 'stdout.txt', '', 'text/plain');
    refs.stderr = await add('stdout_stderr', stderrPath, 'stderr.txt', '', 'text/plain');
    if (!validation.presentBundleKinds.includes('validation_manifest')) validation.presentBundleKinds.push('validation_manifest');
    const missing = requiredBundleKinds.filter((kind) => !validation.presentBundleKinds.includes(kind));
    validation.ok = result.status === 0 && missing.length === 0 && !validation.failureKind;
    validation.missingBundleKinds = missing;
    timings.finishedAtMs = nowMs();
    timings.totalMs = Math.max(0, timings.finishedAtMs - timings.startedAtMs);
    manifest = {ok: validation.ok, status: validation.ok ? 'completed' : 'failed', failureKind: validation.ok ? '' : (validation.failureKind || 'artifact_publication'), cacheHit: false, renderId: request.renderId || '', cacheKey, refs, validationManifest: validation, bundle: {refs, validationManifest: validation, artifactHashes: outputHashes, gifPlaybackContract}, artifactHashes: outputHashes, gifPlaybackContract, timings, renderOptions: options, renderRefs: refs.renderedFrames, contactSheetRef: refs.contactSheet, loopingGifRef: refs.loopingGif, gifPlaybackContractRef: refs.gifPlaybackContract, threeDArtifactRefs: refs.threeDArtifacts, modifiedBlendRef: refs.modifiedBlend, animatedGlbRef: refs.animatedGlb, nativeDataRefs: refs.nativePoseAnimationData, originalScriptRef: refs.originalScript, scriptInputHashesRef: refs.scriptInputHashes, blenderVersionSettingsRef: refs.blenderVersionSettings, stdoutRef: refs.stdout, stderrRef: refs.stderr, fixedCameraRenderRefs: refs.fixedCameraRenders, diagnosticRenderRefs: refs.diagnosticViewRenders};
    const manifestPath = path.join(outputDir, 'validation-manifest.json');
    validation.timings = timings;
    validation.renderOptions = options;
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    refs.validationManifest = await uploadFile(manifestPath, cacheKey, 'validation-manifest.json', 'application/json');
    manifest.manifestRef = refs.validationManifest;
    manifest.validationManifestRef = refs.validationManifest;
    manifest.refs = refs;
    if (CACHE_BUCKET) await storage.bucket(CACHE_BUCKET).file(`renders/blender/${cacheKey}/validation-manifest.json`).save(JSON.stringify(manifest, null, 2), {contentType: 'application/json'});
    return manifest;
  } catch (err) {
    if (manifest) return manifest;
    throw err;
  } finally {
    if (CACHE_BUCKET) fs.rmSync(work, {recursive: true, force: true});
  }
}

export {buildGifPlaybackContract, makeLoopingGif, decodeUploadObject, validateGlbBytes, validateScriptBytes, sha256Buffer};
