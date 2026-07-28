'use strict';

const {createHash, randomUUID} = require('node:crypto');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {Storage} = require('@google-cloud/storage');
const {getFunctions} = require('firebase-admin/functions');
const {ARTIFACT_BUCKET, readArtifactOperation} = require('./artifact_ingest_service');

const FOUNDRY_CAPABILITY_VERSION = 'fortress-model-foundry.v1';
const FOUNDRY_RECIPE_VERSION = 'home-center.foundry-recipe.v1';
const FOUNDRY_TASK_FUNCTION = process.env.FOUNDRY_TASK_FUNCTION || 'foundryAssetWorker';
const FOUNDRY_VIEWER_BASE = process.env.FOUNDRY_VIEWER_BASE || 'https://valar05.github.io/model-viewer-lab/model-viewer.html';
const FOUNDRY_PUBLIC_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
const FOUNDRY_TIMEOUT_MS = Math.min(Number(process.env.FOUNDRY_TIMEOUT_MS || 10 * 60 * 1000), 25 * 60 * 1000);
const FOUNDRY_MAX_SOURCE_BYTES = Number(process.env.FOUNDRY_MAX_SOURCE_BYTES || 256 * 1024 * 1024);
const FOUNDRY_MAX_OUTPUT_BYTES = Number(process.env.FOUNDRY_MAX_OUTPUT_BYTES || 256 * 1024 * 1024);
const FOUNDRY_LOG_MAX_BYTES = Number(process.env.FOUNDRY_LOG_MAX_BYTES || 64 * 1024);
const JOBS = 'foundryAssetJobs';
const IDEMPOTENCY = 'foundryAssetIdempotency';
const PROMOTIONS = 'foundryArtifactPromotions';
let defaultStorageClient = null;

function storageClient() {
  if (!defaultStorageClient) defaultStorageClient = new Storage();
  return defaultStorageClient;
}

function sha256(bytes) { return createHash('sha256').update(bytes).digest('hex'); }
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}
function hashJson(value) { return sha256(Buffer.from(JSON.stringify(stable(value)))); }
function text(value, max = 500) { const clean = typeof value === 'string' ? value.trim() : ''; return clean.slice(0, max); }
function slug(value, fallback = '', max = 120) { return (text(value, max).toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || fallback); }
function fail(code, message, status = 400, details = {}) { const error = new Error(message); error.code = code; error.status = status; error.details = details; return error; }
function ownerEmail(user) { const owner = text(user && user.email, 320).toLowerCase(); if (!owner) throw fail('foundry.owner_required', 'An authenticated owner is required.', 401); return owner; }
function ownerKey(owner) { return sha256(Buffer.from(owner.toLowerCase())).slice(0, 24); }
function assertDigest(value, field) { const digest = text(value, 64).toLowerCase(); if (!/^[a-f0-9]{64}$/.test(digest)) throw fail('foundry.reference.invalid_digest', `${field} must be a SHA-256 digest.`, 400, {field}); return digest; }
function filename(value) { const clean = text(value, 240).replace(/\\/g, '/').split('/').pop().replace(/[^A-Za-z0-9._-]/g, '-'); if (!clean) throw fail('foundry.reference.invalid_filename', 'A stable logical filename is required.'); return clean; }
function mediaType(value) { const clean = text(value, 160).toLowerCase(); return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(clean) ? clean : 'application/octet-stream'; }

function foundryOperationEntries() {
  return {
    'foundry.asset.inspect': {
      summary: 'Queue bounded GLB scene, hierarchy, mesh, skin, animation, bounds, and validation inspection without changing source bytes.',
      write: true,
      requiresRequestId: true,
      input: {source: 'home_center_artifact or foundry_fixture reference', idempotencyKey: 'string', namespace: 'string', reviewPreset: 'optional string'},
    },
    'foundry.asset.run': {
      summary: 'Queue one versioned deterministic hard-surface, character-setup, or animation recipe in an isolated direct-GLB worker.',
      write: true,
      requiresRequestId: true,
      input: {source: 'optional home_center_artifact or foundry_fixture reference', recipe: 'home-center.foundry-recipe.v1 document', parameters: 'bounded object', reviewPreset: 'string', idempotencyKey: 'string', namespace: 'distinct string'},
    },
    'foundry.asset.status': {
      summary: 'Read one bounded owner-scoped Foundry job receipt.',
      write: false,
      input: {jobId: 'string'},
    },
    'foundry.asset.promote': {
      summary: 'Explicitly publish immutable review artifacts from one owner-scoped successful Foundry result without rerunning it.',
      write: true,
      input: {jobId: 'string', resultHash: 'hex', approved: 'must be true', requestId: 'string'},
    },
  };
}

function normalizeRecipe(recipe) {
  if (!recipe || typeof recipe !== 'object' || Array.isArray(recipe)) throw fail('foundry.recipe.required', 'recipe is required.');
  if (recipe.version !== FOUNDRY_RECIPE_VERSION) throw fail('foundry.recipe.unsupported_version', `Unsupported recipe version: ${recipe.version || 'missing'}`, 400, {supported: [FOUNDRY_RECIPE_VERSION]});
  const domain = text(recipe.domain, 40);
  if (!['hard_surface', 'character_setup', 'animation', 'inspect'].includes(domain)) throw fail('foundry.recipe.unsupported_domain', `Unsupported Foundry domain: ${domain}`);
  const commands = Array.isArray(recipe.commands) ? recipe.commands : [];
  if (commands.length > 64) throw fail('foundry.limit.commands', 'A recipe may contain at most 64 commands.', 413);
  const supported = {
    hard_surface: ['mechanical_specimen'],
    character_setup: ['add_weapon_bone', 'attach_rigid_prop'],
    animation: ['trim_clip', 'retime_clip', 'set_rotation_key'],
    inspect: ['inspect'],
  }[domain];
  const normalizedCommands = commands.map((command, index) => {
    if (!command || typeof command !== 'object' || Array.isArray(command)) throw fail('foundry.recipe.invalid_command', `Recipe command ${index} must be an object.`);
    if (!supported.includes(command.op)) throw fail('foundry.recipe.unsupported_operation', `Unsupported ${domain} operation: ${text(command.op, 120) || "missing"}`, 400, {supported});
    return stable(command);
  });
  const normalized = {version: FOUNDRY_RECIPE_VERSION, domain, commands: normalizedCommands};
  if (Buffer.byteLength(JSON.stringify(normalized)) > 64 * 1024) throw fail('foundry.limit.recipe', 'Foundry recipe exceeds 64 KiB.', 413);
  return normalized;
}

function normalizeParameters(value) {
  const parameters = value && typeof value === 'object' && !Array.isArray(value) ? stable(value) : {};
  const bytes = Buffer.byteLength(JSON.stringify(parameters));
  if (bytes > 32 * 1024) throw fail('foundry.limit.parameters', 'Foundry parameters exceed 32 KiB.', 413);
  return parameters;
}

async function resolveSource({storage = storageClient(), user, source, recipe}) {
  if (!source) {
    if (recipe.domain !== 'hard_surface') throw fail('foundry.source.required', `${recipe.domain} requires an existing GLB artifact or fixture.`);
    return null;
  }
  if (!source || typeof source !== 'object' || Array.isArray(source)) throw fail('foundry.reference.invalid', 'source must be an artifact reference object.');
  if (source.kind === 'foundry_fixture') {
    const fixtureId = text(source.fixtureId, 120);
    if (fixtureId !== 'foundry-character-v1') throw fail('foundry.reference.unsupported_fixture', `Unsupported Foundry fixture: ${fixtureId}`);
    return {kind: 'foundry_fixture', fixtureId, sha256: hashJson({fixtureId, version: 1}), byteLength: 0, mediaType: 'model/gltf-binary', filename: `${fixtureId}.glb`};
  }
  if (source.kind !== 'home_center_artifact') throw fail('foundry.reference.unsupported_type', `Unsupported artifact reference type: ${text(source.kind, 80) || 'missing'}`);
  const artifactId = slug(source.artifactId, '', 180);
  if (!artifactId) throw fail('foundry.reference.artifact_id_required', 'source.artifactId is required.');
  const {manifest} = await readArtifactOperation({storage, user, args: {artifactId}});
  const destination = manifest && manifest.destination || {};
  const digest = assertDigest(destination.sha256, 'source.sha256');
  const byteLength = Number(destination.byteCount || 0);
  if (!Number.isSafeInteger(byteLength) || byteLength < 1 || byteLength > FOUNDRY_MAX_SOURCE_BYTES) throw fail('foundry.reference.invalid_length', 'Source byte length is invalid or exceeds the Foundry ceiling.', 413, {byteLength, max: FOUNDRY_MAX_SOURCE_BYTES});
  if (source.sha256 && assertDigest(source.sha256, 'source.sha256') !== digest) throw fail('foundry.reference.digest_conflict', 'Source digest does not match the immutable artifact manifest.', 409);
  if (source.byteLength !== undefined && Number(source.byteLength) !== byteLength) throw fail('foundry.reference.length_conflict', 'Source byte length does not match the immutable artifact manifest.', 409);
  const objectName = text(destination.objectName, 1000);
  if (!objectName) throw fail('foundry.reference.storage_missing', 'Artifact manifest has no canonical storage object.', 409);
  return {kind: 'home_center_artifact', artifactId, sha256: digest, byteLength, mediaType: mediaType(manifest.source && manifest.source.mimeType), filename: filename(manifest.source && manifest.source.name || `${artifactId}.glb`), bucket: text(destination.bucket, 240) || ARTIFACT_BUCKET, objectName};
}

function acceptedReceipt(record, attached = false) {
  return {
    contractVersion: 'home-center.foundry-job.v1',
    capabilityVersion: FOUNDRY_CAPABILITY_VERSION,
    accepted: true,
    attached,
    jobId: record.jobId,
    namespace: record.namespace,
    inputHash: record.inputHash,
    state: record.state,
    statusOperation: 'foundry.asset.status',
    statusArgs: {jobId: record.jobId},
    timestamps: {acceptedAt: record.acceptedAt, updatedAt: record.updatedAt},
  };
}

function boundedReport(report) {
  if (!report) return null;
  return {kernelVersion: report.kernelVersion, recipeVersion: report.recipeVersion, domain: report.domain, reviewPreset: report.reviewPreset, bounds: report.bounds, triangleCount: report.triangleCount, vertexCount: report.vertexCount, componentCount: report.componentCount, validation: report.validation, animations: (report.animations || []).slice(0, 20), skins: (report.skins || []).slice(0, 20), preservation: report.preservation || null};
}

function boundedJobReceipt(record) {
  const result = record.result || null;
  return {
    contractVersion: 'home-center.foundry-job.v1',
    capabilityVersion: FOUNDRY_CAPABILITY_VERSION,
    jobId: record.jobId,
    namespace: record.namespace,
    inputHash: record.inputHash,
    state: record.state,
    domain: record.recipe && record.recipe.domain,
    source: record.source ? {kind: record.source.kind, artifactId: record.source.artifactId || null, fixtureId: record.source.fixtureId || null, sha256: record.source.sha256, byteLength: record.source.byteLength, filename: record.source.filename} : null,
    recipe: {version: record.recipe && record.recipe.version, commandCount: Array.isArray(record.recipe && record.recipe.commands) ? record.recipe.commands.length : 0},
    timestamps: {acceptedAt: record.acceptedAt, startedAt: record.startedAt || null, completedAt: record.completedAt || null, failedAt: record.failedAt || null, updatedAt: record.updatedAt},
    execution: {attempt: Number(record.executionAttempt || 0), timedOut: !!record.timedOut, logBytes: record.logBytes || {stdout: 0, stderr: 0}, logsTruncated: !!record.logsTruncated},
    blockingError: record.blockingError ? {code: text(record.blockingError.code, 120), message: text(record.blockingError.message, 1200)} : null,
    result: result ? {resultHash: result.resultHash, cacheKey: result.cacheKey, report: boundedReport(result.report), artifacts: result.artifacts.map((artifact) => ({kind: artifact.kind, name: artifact.name, mediaType: artifact.mediaType, byteLength: artifact.byteLength, sha256: artifact.sha256, storageRef: artifact.storageRef})), promotion: result.promotion || null} : null,
  };
}

async function defaultEnqueue(payload) {
  await getFunctions().taskQueue(FOUNDRY_TASK_FUNCTION).enqueue(payload, {id: `foundry-${payload.jobId}-${payload.executionAttempt || 0}`, dispatchDeadlineSeconds: Math.ceil(FOUNDRY_TIMEOUT_MS / 1000)});
}

async function queueFoundryRun({admin, storage = storageClient(), user, args = {}, enqueue = defaultEnqueue}) {
  const owner = ownerEmail(user);
  const recipe = normalizeRecipe(args.recipe);
  const source = await resolveSource({storage, user, source: args.source || null, recipe});
  const idempotencyKey = slug(args.idempotencyKey || args.requestId, '', 180);
  const namespace = slug(args.namespace, '', 120);
  if (!idempotencyKey) throw fail('foundry.idempotency_key_required', 'idempotencyKey is required.');
  if (!namespace) throw fail('foundry.namespace_required', 'A distinct job namespace is required.');
  const parameters = normalizeParameters(args.parameters);
  const reviewPreset = slug(args.reviewPreset, 'fixed-four-view', 80);
  const logical = {capabilityVersion: FOUNDRY_CAPABILITY_VERSION, source, recipe, parameters, reviewPreset, namespace};
  const inputHash = hashJson(logical);
  const ownerHash = ownerKey(owner);
  const jobId = sha256(Buffer.from(`${ownerHash}:${namespace}:${inputHash}`)).slice(0, 40);
  const idemId = `${ownerHash}-${sha256(Buffer.from(idempotencyKey)).slice(0, 32)}`;
  const jobRef = admin.firestore().collection(JOBS).doc(jobId);
  const idemRef = admin.firestore().collection(IDEMPOTENCY).doc(idemId);
  const now = new Date().toISOString();
  let attached = false;
  await admin.firestore().runTransaction(async (transaction) => {
    const idemSnap = await transaction.get(idemRef);
    if (idemSnap.exists) {
      const existing = idemSnap.data() || {};
      if (existing.inputHash !== inputHash || existing.namespace !== namespace) throw fail('foundry.idempotency_conflict', 'Idempotency key is already bound to different Foundry inputs.', 409);
      attached = true;
      return;
    }
    const record = {contractVersion: 'home-center.foundry-job.v1', capabilityVersion: FOUNDRY_CAPABILITY_VERSION, jobId, owner, ownerHash, namespace, inputHash, idempotencyKeyHash: sha256(Buffer.from(idempotencyKey)), source, recipe, parameters, reviewPreset, state: 'accepted', enqueueStatus: 'pending', executionAttempt: 0, acceptedAt: now, updatedAt: now};
    transaction.create(jobRef, record);
    transaction.create(idemRef, {jobId, ownerHash, namespace, inputHash, createdAt: now});
  });
  if (attached) {
    const snapshot = await jobRef.get();
    if (!snapshot.exists) throw fail('foundry.job_missing', 'Idempotency receipt points to a missing job.', 500);
    return acceptedReceipt(snapshot.data(), true);
  }
  try {
    await enqueue({jobId, inputHash, executionAttempt: 0});
    await jobRef.set({state: 'queued', enqueueStatus: 'enqueued', updatedAt: new Date().toISOString()}, {merge: true});
  } catch (error) {
    await jobRef.set({state: 'enqueue_failed', enqueueStatus: 'failed', blockingError: {code: 'foundry.enqueue_failed', message: text(error.message || String(error), 1200)}, updatedAt: new Date().toISOString()}, {merge: true});
    throw fail('foundry.enqueue_failed', `Foundry worker enqueue failed: ${text(error.message || String(error), 600)}`, 503);
  }
  const snapshot = await jobRef.get();
  return acceptedReceipt(snapshot.data(), false);
}

async function inspectFoundryAsset(context) {
  const args = context.args || {};
  return queueFoundryRun({...context, args: {...args, recipe: {version: FOUNDRY_RECIPE_VERSION, domain: 'inspect', commands: [{op: 'inspect'}]}, parameters: {}, reviewPreset: args.reviewPreset || 'fixed-four-view'}});
}

async function foundryStatus({admin, user, args = {}}) {
  const jobId = text(args.jobId, 80);
  if (!/^[a-f0-9]{40}$/.test(jobId)) throw fail('foundry.job_id_invalid', 'jobId is invalid.');
  const snapshot = await admin.firestore().collection(JOBS).doc(jobId).get();
  if (!snapshot.exists) throw fail('foundry.job_not_found', 'Foundry job was not found.', 404);
  const record = snapshot.data() || {};
  if (record.owner !== ownerEmail(user)) throw fail('foundry.job_forbidden', 'Foundry job is not owned by this caller.', 403);
  return boundedJobReceipt(record);
}

function publicArtifactUrl(promotionId, name) {
  return `${FOUNDRY_PUBLIC_BASE}/foundry/artifacts/${encodeURIComponent(promotionId)}/${encodeURIComponent(name)}`;
}

async function promoteFoundryResult({admin, user, args = {}}) {
  if (args.approved !== true) throw fail('foundry.promotion.approval_required', 'Foundry promotion requires approved=true.', 409);
  const jobId = text(args.jobId, 80);
  const resultHash = assertDigest(args.resultHash, 'resultHash');
  const jobRef = admin.firestore().collection(JOBS).doc(jobId);
  const snapshot = await jobRef.get();
  if (!snapshot.exists) throw fail('foundry.job_not_found', 'Foundry job was not found.', 404);
  const record = snapshot.data() || {};
  if (record.owner !== ownerEmail(user)) throw fail('foundry.job_forbidden', 'Foundry job is not owned by this caller.', 403);
  if (record.state !== 'completed' || !record.result) throw fail('foundry.promotion.not_ready', 'Only a successful terminal Foundry result may be promoted.', 409);
  if (record.result.resultHash !== resultHash) throw fail('foundry.promotion.result_conflict', 'Promotion resultHash does not match the terminal Foundry result.', 409);
  const promotionId = sha256(Buffer.from(`${jobId}:${resultHash}`)).slice(0, 40);
  const promotionRef = admin.firestore().collection(PROMOTIONS).doc(promotionId);
  const existing = await promotionRef.get();
  let promotion;
  if (existing.exists) promotion = existing.data();
  else {
    const artifacts = Object.fromEntries(record.result.artifacts.map((artifact) => [artifact.name, {name: artifact.name, kind: artifact.kind, mediaType: artifact.mediaType, byteLength: artifact.byteLength, sha256: artifact.sha256, bucket: artifact.bucket, objectName: artifact.objectName}]));
    promotion = {contractVersion: 'home-center.foundry-promotion.v1', promotionId, jobId, resultHash, ownerHash: record.ownerHash, namespace: record.namespace, artifacts, approvedAt: new Date().toISOString(), immutable: true};
    await promotionRef.create(promotion);
  }
  const links = Object.values(promotion.artifacts).map((artifact) => ({kind: artifact.kind, name: artifact.name, mediaType: artifact.mediaType, byteLength: artifact.byteLength, sha256: artifact.sha256, url: publicArtifactUrl(promotionId, artifact.name)}));
  const glb = links.find((artifact) => artifact.kind === 'glb');
  const manifest = links.find((artifact) => artifact.kind === 'manifest');
  const viewerUrl = glb ? `${FOUNDRY_VIEWER_BASE}?src=${encodeURIComponent(glb.url)}${manifest ? `&manifest=${encodeURIComponent(manifest.url)}` : ''}&title=${encodeURIComponent(`Foundry ${record.namespace}`)}` : null;
  const bounded = {promotionId, resultHash, immutable: true, links, viewerUrl, promotedAt: promotion.approvedAt};
  await jobRef.set({result: {...record.result, promotion: bounded}, updatedAt: new Date().toISOString()}, {merge: true});
  return bounded;
}

function boundedLogWriter(filePath, limit) {
  const stream = fs.createWriteStream(filePath, {flags: 'wx'});
  let bytes = 0, truncated = false;
  return {
    write(chunk) { const buffer = Buffer.from(chunk); const remaining = Math.max(0, limit - bytes); if (remaining) stream.write(buffer.subarray(0, remaining)); bytes += Math.min(buffer.length, remaining); if (buffer.length > remaining) truncated = true; },
    end() { return new Promise((resolve, reject) => { stream.once('error', reject); stream.end(resolve); }); },
    stats() { return {bytes, truncated}; },
  };
}

async function runChildProcess({requestPath, outputDir, stdoutPath, stderrPath, timeoutMs = FOUNDRY_TIMEOUT_MS, spawnImpl = spawn}) {
  const child = spawnImpl(process.execPath, [path.join(__dirname, 'foundry_worker_process.mjs'), requestPath, outputDir], {cwd: __dirname, detached: true, stdio: ['ignore', 'pipe', 'pipe'], env: {...process.env, FOUNDRY_WORKER: 'true'}});
  const stdout = boundedLogWriter(stdoutPath, FOUNDRY_LOG_MAX_BYTES);
  const stderr = boundedLogWriter(stderrPath, FOUNDRY_LOG_MAX_BYTES);
  child.stdout.on('data', (chunk) => stdout.write(chunk)); child.stderr.on('data', (chunk) => stderr.write(chunk));
  let timedOut = false;
  const exit = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { timedOut = true; try { process.kill(-child.pid, 'SIGKILL'); } catch (_) { try { child.kill('SIGKILL'); } catch (_) {} } }, timeoutMs);
    child.once('error', (error) => { clearTimeout(timer); reject(error); });
    child.once('close', (code, signal) => { clearTimeout(timer); resolve({code, signal}); });
  });
  await Promise.all([stdout.end(), stderr.end()]);
  return {...exit, timedOut, stdout: stdout.stats(), stderr: stderr.stats()};
}

async function validateGlbFile(filePath, expectedByteLength) {
  const handle = await fsp.open(filePath, 'r');
  try {
    const header = Buffer.alloc(12); const {bytesRead} = await handle.read(header, 0, 12, 0);
    if (bytesRead !== 12 || header.toString('ascii', 0, 4) !== 'glTF') throw fail('foundry.source.invalid_glb_magic', 'Source is not a binary glTF file.', 415);
    const version = header.readUInt32LE(4), declaredLength = header.readUInt32LE(8);
    if (version !== 2) throw fail('foundry.source.unsupported_glb_version', `Foundry requires GLB version 2; received ${version}.`, 415);
    if (declaredLength !== expectedByteLength) throw fail('foundry.source.glb_length_mismatch', 'GLB declared length does not match the verified artifact byte length.', 409, {declaredLength, expectedByteLength});
  } finally { await handle.close(); }
}

async function digestFile(filePath) {
  const hash = createHash('sha256'); let byteLength = 0;
  for await (const chunk of fs.createReadStream(filePath)) { hash.update(chunk); byteLength += chunk.length; }
  return {sha256: hash.digest('hex'), byteLength};
}

function artifactKind(name) {
  if (name.endsWith('.glb')) return 'glb';
  if (name === 'contact-sheet.png') return 'contactSheet';
  if (name === 'skeletal-overlay.png') return 'skeletalOverlay';
  if (name === 'foundry-manifest.json') return 'manifest';
  if (name === 'validation-report.json') return 'report';
  if (name === 'preservation-evidence.json') return 'evidence';
  return 'artifact';
}

function contentType(name) {
  if (name.endsWith('.glb')) return 'model/gltf-binary';
  if (name.endsWith('.png')) return 'image/png';
  if (name.endsWith('.json')) return 'application/json';
  return 'application/octet-stream';
}

async function uploadImmutableFile({storage = storageClient(), bucketName = ARTIFACT_BUCKET, localPath, objectName, metadata}) {
  const file = storage.bucket(bucketName).file(objectName);
  const expected = await digestFile(localPath);
  let reused = false;
  try {
    await storage.bucket(bucketName).upload(localPath, {destination: objectName, resumable: expected.byteLength > 8 * 1024 * 1024, validation: 'crc32c', preconditionOpts: {ifGenerationMatch: 0}, metadata: {contentType: metadata.mediaType, metadata}});
  } catch (error) {
    if (![409, 412].includes(Number(error && error.code)) && !/condition|already exists/i.test(String(error && error.message))) throw error;
    reused = true;
  }
  const [remote] = await file.download();
  const actual = {byteLength: remote.length, sha256: sha256(remote)};
  if (actual.byteLength !== expected.byteLength || actual.sha256 !== expected.sha256) throw fail('foundry.output.readback_mismatch', `Foundry output failed readback verification: ${path.basename(localPath)}`, 502);
  return {...expected, bucket: bucketName, objectName, storageRef: `gs://${bucketName}/${objectName}`, reused};
}

async function executeFoundryJob(admin, payload = {}, dependencies = {}) {
  const storage = dependencies.storage || storageClient();
  const jobId = text(payload.jobId, 80);
  const jobRef = admin.firestore().collection(JOBS).doc(jobId);
  let record = null;
  let shouldExecute = true;
  const leaseId = randomUUID();
  const nowMs = Date.now();
  const startedAt = new Date(nowMs).toISOString();
  await admin.firestore().runTransaction(async (transaction) => {
    const snapshot = await transaction.get(jobRef);
    if (!snapshot.exists) throw fail('foundry.job_not_found', 'Foundry worker job was not found.', 404);
    record = snapshot.data() || {};
    if (record.inputHash !== payload.inputHash) throw fail('foundry.worker.input_conflict', 'Worker payload input hash does not match the durable job.', 409);
    if (record.state === 'completed') { shouldExecute = false; return; }
    if (record.state === 'running' && Number(record.leaseExpiresAtMs || 0) > nowMs) { shouldExecute = false; return; }
    transaction.set(jobRef, {state: 'running', startedAt: record.startedAt || startedAt, updatedAt: startedAt, executionAttempt: Number(payload.executionAttempt || 0), leaseId, leaseExpiresAtMs: nowMs + FOUNDRY_TIMEOUT_MS + 60 * 1000}, {merge: true});
  });
  if (!shouldExecute) return boundedJobReceipt(record);
  const tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), `foundry-${jobId}-`));
  const inputPath = path.join(tempDir, 'source.glb');
  const requestPath = path.join(tempDir, 'request.json');
  const outputDir = path.join(tempDir, 'output');
  const stdoutPath = path.join(tempDir, 'stdout.log');
  const stderrPath = path.join(tempDir, 'stderr.log');
  await fsp.mkdir(outputDir);
  let execution = null;
  try {
    if (record.source && record.source.kind === 'home_center_artifact') {
      await storage.bucket(record.source.bucket).file(record.source.objectName).download({destination: inputPath});
      const digest = await digestFile(inputPath);
      if (digest.byteLength !== record.source.byteLength || digest.sha256 !== record.source.sha256) throw fail('foundry.source.readback_mismatch', 'Foundry source failed byte length or SHA-256 verification.', 409);
      await validateGlbFile(inputPath, digest.byteLength);
    }
    await fsp.writeFile(requestPath, JSON.stringify({recipe: record.recipe, parameters: record.parameters, reviewPreset: record.reviewPreset, fixtureId: record.source && record.source.fixtureId || '', sourcePath: record.source && record.source.kind === 'home_center_artifact' ? inputPath : ''}));
    execution = await runChildProcess({requestPath, outputDir, stdoutPath, stderrPath, timeoutMs: dependencies.timeoutMs || FOUNDRY_TIMEOUT_MS, spawnImpl: dependencies.spawnImpl || spawn});
    if (execution.timedOut) throw fail('foundry.worker.timeout', 'Foundry worker exceeded its bounded runtime and the process tree was terminated.', 504);
    if (execution.code !== 0) throw fail('foundry.worker.failed', `Foundry worker exited with code ${execution.code}; inspect bounded job logs.`, 500, {signal: execution.signal});
    const names = (await fsp.readdir(outputDir)).sort();
    let totalBytes = 0;
    const identities = [];
    for (const name of names) { const digest = await digestFile(path.join(outputDir, name)); totalBytes += digest.byteLength; identities.push({name, ...digest}); }
    if (totalBytes > FOUNDRY_MAX_OUTPUT_BYTES) throw fail('foundry.limit.output', 'Foundry outputs exceed the configured ceiling.', 413, {totalBytes, max: FOUNDRY_MAX_OUTPUT_BYTES});
    const resultHash = hashJson(identities);
    const cacheKey = sha256(Buffer.from(`${record.namespace}:${record.inputHash}:${resultHash}`));
    const prefix = `foundry/v1/${record.ownerHash}/${record.namespace}/${record.inputHash}/${resultHash}`;
    const artifacts = [];
    for (const identity of identities) {
      const kind = artifactKind(identity.name), type = contentType(identity.name);
      const uploaded = await uploadImmutableFile({storage, localPath: path.join(outputDir, identity.name), objectName: `${prefix}/${identity.name}`, metadata: {jobId, namespace: record.namespace, inputHash: record.inputHash, resultHash, kind, mediaType: type, sha256: identity.sha256, byteLength: String(identity.byteLength)}});
      artifacts.push({kind, name: identity.name, mediaType: type, ...uploaded});
    }
    const logs = {};
    for (const [streamName, localPath] of [['stdout', stdoutPath], ['stderr', stderrPath]]) {
      const uploaded = await uploadImmutableFile({storage, localPath, objectName: `${prefix}/logs/${streamName}.log`, metadata: {jobId, namespace: record.namespace, inputHash: record.inputHash, resultHash, kind: `${streamName}Log`, mediaType: 'text/plain'}});
      logs[streamName] = {storageRef: uploaded.storageRef, byteLength: uploaded.byteLength, sha256: uploaded.sha256};
    }
    const report = JSON.parse(await fsp.readFile(path.join(outputDir, 'validation-report.json'), 'utf8'));
    const completedAt = new Date().toISOString();
    const result = {resultHash, cacheKey, report, artifacts, logs, totalBytes, immutable: true, publicationState: 'private_unpromoted'};
    await jobRef.set({state: 'completed', completedAt, updatedAt: completedAt, result, logBytes: {stdout: execution.stdout.bytes, stderr: execution.stderr.bytes}, logsTruncated: execution.stdout.truncated || execution.stderr.truncated, timedOut: false, blockingError: null, leaseId: null, leaseExpiresAtMs: 0}, {merge: true});
    return boundedJobReceipt({...record, state: 'completed', completedAt, updatedAt: completedAt, result, logBytes: {stdout: execution.stdout.bytes, stderr: execution.stderr.bytes}, logsTruncated: execution.stdout.truncated || execution.stderr.truncated});
  } catch (error) {
    const failedAt = new Date().toISOString();
    const failureLogs = {};
    if (execution) {
      for (const [streamName, localPath] of [['stdout', stdoutPath], ['stderr', stderrPath]]) {
        try {
          const uploaded = await uploadImmutableFile({storage, localPath, objectName: `foundry/v1/${record.ownerHash}/${record.namespace}/${record.inputHash}/attempt-${Number(payload.executionAttempt || 0)}/logs/${streamName}.log`, metadata: {jobId, namespace: record.namespace, inputHash: record.inputHash, kind: `${streamName}Log`, mediaType: 'text/plain'}});
          failureLogs[streamName] = {storageRef: uploaded.storageRef, byteLength: uploaded.byteLength, sha256: uploaded.sha256};
        } catch (_) {}
      }
    }
    await jobRef.set({state: 'failed', failedAt, updatedAt: failedAt, timedOut: error.code === 'foundry.worker.timeout', logBytes: execution ? {stdout: execution.stdout.bytes, stderr: execution.stderr.bytes} : {stdout: 0, stderr: 0}, logsTruncated: execution ? execution.stdout.truncated || execution.stderr.truncated : false, failureLogs, leaseId: null, leaseExpiresAtMs: 0, blockingError: {code: text(error.code, 120) || 'foundry.worker.failed', message: text(error.message || String(error), 1200)}}, {merge: true});
    throw error;
  } finally {
    await fsp.rm(tempDir, {recursive: true, force: true});
  }
}

async function runFoundryOperation({operation, admin, storage, user, args, enqueue}) {
  if (operation === 'foundry.asset.inspect') return inspectFoundryAsset({admin, storage, user, args, enqueue});
  if (operation === 'foundry.asset.run') return queueFoundryRun({admin, storage, user, args, enqueue});
  if (operation === 'foundry.asset.status') return foundryStatus({admin, user, args});
  if (operation === 'foundry.asset.promote') return promoteFoundryResult({admin, user, args});
  throw fail('foundry.operation.unsupported', `Unsupported Foundry operation: ${operation}`);
}

function installFoundryArtifactRoutes(app, {admin, storage = storageClient()}) {
  app.get('/foundry/artifacts/:promotionId/:name', async (req, res) => {
    try {
      const promotionId = text(req.params.promotionId, 80);
      const name = filename(req.params.name);
      if (!/^[a-f0-9]{40}$/.test(promotionId)) throw fail('foundry.promotion.invalid', 'Promotion identifier is invalid.', 404);
      const snapshot = await admin.firestore().collection(PROMOTIONS).doc(promotionId).get();
      if (!snapshot.exists) throw fail('foundry.promotion.not_found', 'Promoted Foundry artifact was not found.', 404);
      const promotion = snapshot.data() || {};
      const artifact = promotion.artifacts && promotion.artifacts[name];
      if (!artifact || artifact.name !== name) throw fail('foundry.promotion.artifact_not_found', 'Promoted Foundry artifact was not found.', 404);
      res.set('Access-Control-Allow-Origin', '*');
      res.set('Cache-Control', 'public, max-age=31536000, immutable');
      res.set('Content-Type', artifact.mediaType);
      res.set('Content-Length', String(artifact.byteLength));
      res.set('ETag', `"${artifact.sha256}"`);
      res.set('X-Content-Type-Options', 'nosniff');
      storage.bucket(artifact.bucket).file(artifact.objectName).createReadStream().on('error', (error) => { if (!res.headersSent) res.status(502).json({error: 'foundry.artifact.read_failed', message: text(error.message, 300)}); else res.destroy(error); }).pipe(res);
    } catch (error) {
      res.status(error.status || 500).json({error: error.code || 'foundry.artifact.failed', message: text(error.message || String(error), 600), details: error.details || {}});
    }
  });
}

module.exports = {
  FOUNDRY_CAPABILITY_VERSION,
  FOUNDRY_RECIPE_VERSION,
  FOUNDRY_TASK_FUNCTION,
  foundryOperationEntries,
  normalizeRecipe,
  resolveSource,
  queueFoundryRun,
  inspectFoundryAsset,
  foundryStatus,
  promoteFoundryResult,
  executeFoundryJob,
  runFoundryOperation,
  installFoundryArtifactRoutes,
  boundedJobReceipt,
  runChildProcess,
  hashJson,
};
