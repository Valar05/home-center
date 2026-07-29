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

const FOUNDRY_CAPABILITY_VERSION = 'fortress-model-foundry.v2';
const FOUNDRY_RUN_VERSION = 'home-center.foundry-run.v2';
const FOUNDRY_SCRIPT_VERSION = 'foundry-js.v1';
const FOUNDRY_TASK_FUNCTION = process.env.FOUNDRY_TASK_FUNCTION || 'foundryAssetWorker';
const FOUNDRY_VIEWER_BASE = process.env.FOUNDRY_VIEWER_BASE || 'https://valar05.github.io/model-viewer-lab/model-viewer.html';
const FOUNDRY_PUBLIC_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
const FOUNDRY_TIMEOUT_MS = Math.min(Number(process.env.FOUNDRY_TIMEOUT_MS || 10 * 60 * 1000), 25 * 60 * 1000);
const FOUNDRY_MAX_SOURCE_BYTES = Number(process.env.FOUNDRY_MAX_SOURCE_BYTES || 256 * 1024 * 1024);
const FOUNDRY_MAX_SCRIPT_BYTES = Number(process.env.FOUNDRY_MAX_SCRIPT_BYTES || 256 * 1024);
const FOUNDRY_MAX_MODEL_SHEET_IMAGE_BYTES = 16 * 1024 * 1024;
const FOUNDRY_MAX_MODEL_SHEET_BYTES = 48 * 1024 * 1024;
const FOUNDRY_MODEL_SHEET_VERSION = 'home-center.foundry-model-sheet.v1';
const FOUNDRY_MAX_OUTPUT_BYTES = Number(process.env.FOUNDRY_MAX_OUTPUT_BYTES || 256 * 1024 * 1024);
const FOUNDRY_LOG_MAX_BYTES = Number(process.env.FOUNDRY_LOG_MAX_BYTES || 64 * 1024);
const FOUNDRY_STATUS_LOG_EXCERPT_BYTES = Math.max(1024, Math.min(Number(process.env.FOUNDRY_STATUS_LOG_EXCERPT_BYTES) || 8 * 1024, 16 * 1024));
const JOBS = 'foundryAssetJobs';
const IDEMPOTENCY = 'foundryAssetIdempotency';
const PUBLICATIONS = 'foundryArtifactPromotions';
const REVIEW_RECORDS = 'artifactReviewRecords';
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
function slug(value, fallback = '', max = 120) { return text(value, max).toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || fallback; }
function fail(code, message, status = 400, details = {}) { const error = new Error(message); error.code = code; error.status = status; error.details = details; return error; }
function ownerEmail(user) { const owner = text(user && user.email, 320).toLowerCase(); if (!owner) throw fail('foundry.owner_required', 'An authenticated owner is required.', 401); return owner; }
function ownerKey(owner) { return sha256(Buffer.from(owner.toLowerCase())).slice(0, 24); }
function assertDigest(value, field) { const digest = text(value, 64).toLowerCase(); if (!/^[a-f0-9]{64}$/.test(digest)) throw fail('foundry.reference.invalid_digest', field + ' must be a SHA-256 digest.', 400, {field}); return digest; }
function filename(value) { const clean = text(value, 240).replace(/\\/g, '/').split('/').pop().replace(/[^A-Za-z0-9._-]/g, '-'); if (!clean) throw fail('foundry.reference.invalid_filename', 'A stable logical filename is required.'); return clean; }
function mediaType(value) { const clean = text(value, 160).toLowerCase(); return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(clean) ? clean : 'application/octet-stream'; }

function foundryOperationEntries() {
  return {
    'foundry.asset.inspect': {
      summary: 'Queue owner-scoped direct-GLB inspection and six-view evidence without changing source bytes.',
      write: true,
      requiresRequestId: true,
      input: {source: 'home_center_artifact with required sha256 and byteLength', idempotencyKey: 'string', namespace: 'string', reviewPreset: 'optional fixed-six-view'},
    },
    'foundry.asset.run': {
      summary: 'Queue one sandboxed Foundry JavaScript program that loads a complete immutable GLB, performs batched direct-GLB edits, and publishes one immutable unreviewed successor.',
      write: true,
      requiresRequestId: true,
      input: {contractVersion: FOUNDRY_RUN_VERSION, domain: 'hard_surface|character_setup|animation', source: 'optional home_center_artifact with required sha256 and byteLength', script: 'inline foundry-js.v1 text or owner-scoped home_center_artifact reference', parameters: 'bounded object', reviewPreset: 'fixed-six-view', modelSheet: 'optional calibrated home-center.foundry-model-sheet.v1 with immutable front/side/top PNG artifacts', idempotencyKey: 'string', namespace: 'distinct string', parent: 'optional {jobId,resultHash}'},
      output: {accepted: 'boolean', jobId: 'stable string', inputHash: 'sha256', state: 'queued|running|completed|failed', review: 'immutable links when completed; humanAcceptance remains unreviewed'},
    },
    'foundry.asset.status': {
      summary: 'Read one bounded owner-scoped Foundry job receipt, including immutable review links when ready.',
      write: false,
      input: {jobId: 'string'},
    },
    'foundry.asset.promote': {
      summary: 'Promote an immutable Foundry result only after a separate accepted artifact review record; never rerun or rewrite bytes.',
      write: true,
      input: {jobId: 'string', resultHash: 'hex', reviewRequestId: 'accepted artifact review record', requestId: 'string'},
    },
  };
}

function normalizeParameters(value) {
  const parameters = value && typeof value === 'object' && !Array.isArray(value) ? stable(value) : {};
  const bytes = Buffer.byteLength(JSON.stringify(parameters));
  if (bytes > 32 * 1024) throw fail('foundry.limit.parameters', 'Foundry parameters exceed 32 KiB.', 413);
  return parameters;
}

function modelSheetRecordFields(modelSheet) {
  if (!modelSheet) return {modelSheet: null, modelSheetJson: null};
  const modelSheetJson = JSON.stringify(modelSheet), byteLength = Buffer.byteLength(modelSheetJson);
  if (byteLength > 512 * 1024) throw fail('foundry.limit.model_sheet_record', 'Resolved model-sheet registration exceeds the durable job-record ceiling.', 413, {byteLength, max: 512 * 1024});
  return {
    modelSheet: {contractVersion: modelSheet.contractVersion, id: modelSheet.id, units: modelSheet.units, scaleAnchor: modelSheet.scaleAnchor},
    modelSheetJson,
  };
}
function modelSheetFromRecord(record) {
  if (record && typeof record.modelSheetJson === 'string' && record.modelSheetJson) {
    try { return JSON.parse(record.modelSheetJson); }
    catch (_) { throw fail('foundry.model_sheet.record_invalid', 'Durable model-sheet JSON could not be decoded.', 500); }
  }
  return record && record.modelSheet && record.modelSheet.views ? JSON.parse(JSON.stringify(record.modelSheet)) : null;
}
function normalizeDomain(value, allowInspect = false) {
  const domain = text(value, 40);
  const supported = allowInspect ? ['hard_surface', 'character_setup', 'animation', 'inspect'] : ['hard_surface', 'character_setup', 'animation'];
  if (!supported.includes(domain)) throw fail('foundry.domain.unsupported', 'Unsupported Foundry domain: ' + (domain || 'missing'), 400, {supported});
  return domain;
}
async function resolveArtifactReference({storage, user, reference, role, maxBytes, allowedMediaTypes}) {
  if (!reference || typeof reference !== 'object' || Array.isArray(reference) || reference.kind !== 'home_center_artifact') throw fail('foundry.reference.unsupported_type', role + ' must be a home_center_artifact reference.');
  const artifactId = slug(reference.artifactId, '', 180);
  if (!artifactId) throw fail('foundry.reference.artifact_id_required', role + '.artifactId is required.');
  const expectedSha = assertDigest(reference.sha256, role + '.sha256');
  const expectedLength = Number(reference.byteLength);
  if (!Number.isSafeInteger(expectedLength) || expectedLength < 1) throw fail('foundry.reference.invalid_length', role + '.byteLength is required and must be positive.');
  const {manifest} = await readArtifactOperation({storage, user, args: {artifactId}});
  const destination = manifest && manifest.destination || {};
  const digest = assertDigest(destination.sha256, role + '.sha256');
  const byteLength = Number(destination.byteCount || 0);
  if (byteLength !== expectedLength) throw fail('foundry.reference.length_conflict', role + ' byte length does not match the immutable artifact manifest.', 409, {expected: expectedLength, actual: byteLength});
  if (digest !== expectedSha) throw fail('foundry.reference.digest_conflict', role + ' digest does not match the immutable artifact manifest.', 409, {expected: expectedSha, actual: digest});
  if (byteLength > maxBytes) throw fail('foundry.reference.invalid_length', role + ' exceeds the Foundry ceiling.', 413, {byteLength, max: maxBytes});
  const objectName = text(destination.objectName, 1000);
  if (!objectName) throw fail('foundry.reference.storage_missing', role + ' artifact has no canonical storage object.', 409);
  const type = mediaType(manifest.source && manifest.source.mimeType);
  if (allowedMediaTypes && !allowedMediaTypes.has(type)) throw fail('foundry.reference.invalid_media_type', role + ' media type is not supported.', 415, {mediaType: type, supported: Array.from(allowedMediaTypes)});
  return {kind: 'home_center_artifact', artifactId, sha256: digest, byteLength, mediaType: type, filename: filename(manifest.source && manifest.source.name || artifactId), bucket: text(destination.bucket, 240) || ARTIFACT_BUCKET, objectName};
}
async function resolveSource({storage = storageClient(), user, source, domain}) {
  if (!source) {
    if (domain !== 'hard_surface') throw fail('foundry.source.required', domain + ' requires an immutable GLB source.');
    return null;
  }
  return resolveArtifactReference({storage, user, reference: source, role: 'source', maxBytes: FOUNDRY_MAX_SOURCE_BYTES, allowedMediaTypes: new Set(['model/gltf-binary', 'application/octet-stream'])});
}
async function resolveScript({storage = storageClient(), user, script}) {
  if (!script || typeof script !== 'object' || Array.isArray(script)) throw fail('foundry.script.required', 'script is required.');
  if (script.kind === 'inline') {
    if (script.version !== FOUNDRY_SCRIPT_VERSION) throw fail('foundry.script.unsupported_version', 'Unsupported Foundry script version: ' + (script.version || 'missing'), 400, {supported: [FOUNDRY_SCRIPT_VERSION]});
    const scriptText = typeof script.text === 'string' ? script.text : '';
    const byteLength = Buffer.byteLength(scriptText, 'utf8');
    if (!scriptText.trim()) throw fail('foundry.script.required', 'Inline Foundry script text is empty.');
    if (byteLength > FOUNDRY_MAX_SCRIPT_BYTES) throw fail('foundry.limit.script', 'Foundry script exceeds 256 KiB.', 413);
    const digest = sha256(Buffer.from(scriptText));
    if (script.sha256 && assertDigest(script.sha256, 'script.sha256') !== digest) throw fail('foundry.script.digest_conflict', 'Inline script digest does not match its text.', 409);
    return {kind: 'inline', version: FOUNDRY_SCRIPT_VERSION, sha256: digest, byteLength, mediaType: 'text/javascript', filename: filename(script.filename || 'foundry-script.js'), text: scriptText};
  }
  const resolved = await resolveArtifactReference({storage, user, reference: script, role: 'script', maxBytes: FOUNDRY_MAX_SCRIPT_BYTES, allowedMediaTypes: new Set(['text/javascript', 'application/javascript', 'text/plain'])});
  return {...resolved, version: FOUNDRY_SCRIPT_VERSION};
}

function finiteVector(value, length, field) {
  if (!Array.isArray(value) || value.length !== length || value.some((entry) => !Number.isFinite(Number(entry)))) {
    throw fail('foundry.model_sheet.invalid_vector', field + ' must contain ' + length + ' finite numbers.', 400, {field});
  }
  return value.map(Number);
}
function unitVector(value, field) {
  const out = finiteVector(value, 3, field), length = Math.hypot(...out);
  if (Math.abs(length - 1) > 0.001) throw fail('foundry.model_sheet.invalid_axis', field + ' must be a unit vector.', 400, {field, length});
  return out;
}
function normalizeSheetPoint(value, field) {
  const point = finiteVector(value, 2, field);
  if (point.some((entry) => entry < 0 || entry > 640)) throw fail('foundry.model_sheet.point_out_of_bounds', field + ' must lie inside the 640x640 registered plane.', 400, {field, point});
  return point;
}
function assertOrthogonal(a, b, field) {
  const dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  if (Math.abs(dot) > 0.001) throw fail('foundry.model_sheet.axes_not_orthogonal', field + ' axes must be orthogonal.', 400, {field, dot});
}
async function resolveModelSheet({storage = storageClient(), user, modelSheet}) {
  if (!modelSheet) return null;
  if (!modelSheet || typeof modelSheet !== 'object' || Array.isArray(modelSheet) || modelSheet.contractVersion !== FOUNDRY_MODEL_SHEET_VERSION) {
    throw fail('foundry.model_sheet.unsupported_version', 'A home-center.foundry-model-sheet.v1 object is required.', 400, {supported: [FOUNDRY_MODEL_SHEET_VERSION]});
  }
  const id = slug(modelSheet.id, '', 160);
  if (!id) throw fail('foundry.model_sheet.id_required', 'modelSheet.id is required.');
  if (modelSheet.units !== 'm') throw fail('foundry.model_sheet.units_required', 'Model-sheet world coordinates must use meters.');
  const axisFrame = modelSheet.axisFrame || {};
  const forward = unitVector(axisFrame.forward, 'axisFrame.forward');
  const up = unitVector(axisFrame.up, 'axisFrame.up');
  const left = unitVector(axisFrame.left, 'axisFrame.left');
  assertOrthogonal(forward, up, 'axisFrame');
  assertOrthogonal(forward, left, 'axisFrame');
  assertOrthogonal(up, left, 'axisFrame');
  const scaleAnchorValue = modelSheet.scaleAnchor || {};
  const scaleAnchor = {name: text(scaleAnchorValue.name, 160), meters: Number(scaleAnchorValue.meters)};
  if (!scaleAnchor.name || !Number.isFinite(scaleAnchor.meters) || scaleAnchor.meters <= 0 || scaleAnchor.meters > 100) {
    throw fail('foundry.model_sheet.scale_anchor_invalid', 'A named, positive scale anchor in meters is required.');
  }
  const provenance = Array.isArray(modelSheet.provenance) ? modelSheet.provenance.map((entry, index) => ({
    title: text(entry && entry.title, 300),
    url: text(entry && entry.url, 1200),
    license: text(entry && entry.license, 120),
    publisher: text(entry && entry.publisher, 240),
    publishedAt: text(entry && entry.publishedAt, 40),
    pages: Array.isArray(entry && entry.pages) ? entry.pages.slice(0, 32).map((value) => text(value, 120)).filter(Boolean) : [],
    processing: text(entry && entry.processing, 1000),
  })) : [];
  if (!provenance.length || provenance.some((entry) => !entry.title || !/^https:\/\//.test(entry.url) || entry.license !== 'public-domain-us-government')) {
    throw fail('foundry.model_sheet.provenance_required', 'Every model sheet requires cited public-domain US-government provenance and processing notes.');
  }
  const frameLeft = [forward[1] * up[2] - forward[2] * up[1], forward[2] * up[0] - forward[0] * up[2], forward[0] * up[1] - forward[1] * up[0]];
  if (frameLeft.some((value, index) => Math.abs(value - left[index]) > 0.001)) throw fail('foundry.model_sheet.axis_handedness', 'axisFrame must satisfy forward cross up equals left.', 400);
  const expected = {
    front: {direction: forward, up, horizontal: left.map((value) => -value)},
    side: {direction: left, up, horizontal: forward},
    top: {direction: up, up: forward, horizontal: left},
  };
  const views = {};
  let totalBytes = 0;
  for (const viewName of ['front', 'side', 'top']) {
    const raw = modelSheet.views && modelSheet.views[viewName];
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw fail('foundry.model_sheet.view_required', 'Model sheet requires front, side, and top views.', 400, {view: viewName});
    if (Number(raw.width) !== 640 || Number(raw.height) !== 640) throw fail('foundry.model_sheet.image_dimensions', 'Registered model-sheet planes must be declared as 640x640.', 400, {view: viewName});
    const image = await resolveArtifactReference({storage, user, reference: raw.image, role: 'modelSheet.views.' + viewName + '.image', maxBytes: FOUNDRY_MAX_MODEL_SHEET_IMAGE_BYTES, allowedMediaTypes: new Set(['image/png'])});
    totalBytes += image.byteLength;
    const camera = {
      direction: unitVector(raw.camera && raw.camera.direction, 'views.' + viewName + '.camera.direction'),
      up: unitVector(raw.camera && raw.camera.up, 'views.' + viewName + '.camera.up'),
      horizontal: unitVector(raw.camera && raw.camera.horizontal, 'views.' + viewName + '.camera.horizontal'),
    };
    for (const key of ['direction', 'up', 'horizontal']) {
      if (camera[key].some((value, index) => Math.abs(value - expected[viewName][key][index]) > 0.001)) {
        throw fail('foundry.model_sheet.camera_frame_conflict', viewName + ' camera must agree with the declared model-sheet axisFrame.', 400, {view: viewName, key, expected: expected[viewName][key], actual: camera[key]});
      }
    }
    assertOrthogonal(camera.direction, camera.up, 'views.' + viewName + '.camera');
    assertOrthogonal(camera.direction, camera.horizontal, 'views.' + viewName + '.camera');
    assertOrthogonal(camera.up, camera.horizontal, 'views.' + viewName + '.camera');
    const originPx = normalizeSheetPoint(raw.originPx, 'views.' + viewName + '.originPx');
    const originWorld = finiteVector(raw.originWorld || [0, 0, 0], 3, 'views.' + viewName + '.originWorld');
    const pixelsPerMeter = Number(raw.pixelsPerMeter);
    if (!Number.isFinite(pixelsPerMeter) || pixelsPerMeter < 10 || pixelsPerMeter > 10000) throw fail('foundry.model_sheet.scale_invalid', 'pixelsPerMeter must be from 10 to 10000.', 400, {view: viewName});
    const contourPx = Array.isArray(raw.contourPx) ? raw.contourPx.map((point, index) => normalizeSheetPoint(point, 'views.' + viewName + '.contourPx[' + index + ']')) : [];
    if (contourPx.length < 3 || contourPx.length > 2048) throw fail('foundry.model_sheet.contour_invalid', 'Each registered view requires 3-2048 contour points.', 400, {view: viewName});
    const aperturesPx = Array.isArray(raw.aperturesPx) ? raw.aperturesPx.map((polygon, polygonIndex) => {
      const points = Array.isArray(polygon) ? polygon.map((point, pointIndex) => normalizeSheetPoint(point, 'views.' + viewName + '.aperturesPx[' + polygonIndex + '][' + pointIndex + ']')) : [];
      if (points.length < 3 || points.length > 512) throw fail('foundry.model_sheet.aperture_invalid', 'Each registered aperture requires 3-512 points.', 400, {view: viewName, polygonIndex});
      return points;
    }) : [];
    if (aperturesPx.length > 16) throw fail('foundry.model_sheet.aperture_invalid', 'Each registered view supports at most 16 aperture-feature contours.', 400, {view: viewName});
    const landmarks = Array.isArray(raw.landmarks) ? raw.landmarks.map((entry, index) => ({
      name: text(entry && entry.name, 160),
      pixel: normalizeSheetPoint(entry && entry.pixel, 'views.' + viewName + '.landmarks[' + index + '].pixel'),
      cagePointId: text(entry && entry.cagePointId, 80),
    })) : [];
    if (landmarks.length < 3 || landmarks.length > 64 || landmarks.some((entry) => !entry.name || !/^x\d+:y\d+:z\d+$/.test(entry.cagePointId))) {
      throw fail('foundry.model_sheet.landmarks_invalid', 'Each registered view requires 3-64 named cage-point landmarks.', 400, {view: viewName});
    }
    views[viewName] = {width: 640, height: 640, image, camera, originPx, originWorld, pixelsPerMeter, contourPx, aperturesPx, landmarks};
  }
  if (totalBytes > FOUNDRY_MAX_MODEL_SHEET_BYTES) throw fail('foundry.limit.model_sheet', 'Model-sheet images exceed the 48 MiB aggregate ceiling.', 413, {totalBytes, max: FOUNDRY_MAX_MODEL_SHEET_BYTES});
  return {contractVersion: FOUNDRY_MODEL_SHEET_VERSION, id, units: 'm', axisFrame: {forward, up, left}, scaleAnchor, provenance, views};
}

async function resolveParent({admin, owner, parent, source}) {
  if (!parent) return null;
  const jobId = text(parent.jobId, 80), resultHash = assertDigest(parent.resultHash, 'parent.resultHash');
  if (!/^[a-f0-9]{40}$/.test(jobId)) throw fail('foundry.parent.job_id_invalid', 'parent.jobId is invalid.');
  const snapshot = await admin.firestore().collection(JOBS).doc(jobId).get();
  if (!snapshot.exists) throw fail('foundry.parent.not_found', 'Parent Foundry job was not found.', 404);
  const record = snapshot.data() || {};
  if (record.owner !== owner) throw fail('foundry.parent.forbidden', 'Parent Foundry job is not owned by this caller.', 403);
  if (record.state !== 'completed' || !record.result || record.result.resultHash !== resultHash) throw fail('foundry.parent.result_conflict', 'Parent must bind an exact terminal Foundry result.', 409);
  const glb = record.result.artifacts.find((artifact) => artifact.kind === 'glb');
  if (source && glb && source.sha256 !== glb.sha256) throw fail('foundry.parent.source_conflict', 'Successor source must match the exact parent GLB digest.', 409, {parentSha256: glb.sha256, sourceSha256: source.sha256});
  return {jobId, resultHash, revision: Number(record.revision || 0) + 1};
}

function acceptedReceipt(record, attached = false) {
  return {contractVersion: 'home-center.foundry-job.v2', capabilityVersion: FOUNDRY_CAPABILITY_VERSION, accepted: true, attached, jobId: record.jobId, namespace: record.namespace, inputHash: record.inputHash, state: record.state, statusOperation: 'foundry.asset.status', statusArgs: {jobId: record.jobId}, timestamps: {acceptedAt: record.acceptedAt, updatedAt: record.updatedAt}};
}
function boundedReport(report) {
  if (!report) return null;
  return {kernelVersion: report.kernelVersion, runVersion: report.runVersion, domain: report.domain, reviewPreset: report.reviewPreset, bounds: report.bounds, triangleCount: report.triangleCount, vertexCount: report.vertexCount, componentCount: report.componentCount, validation: report.validation, animations: (report.animations || []).slice(0, 20), skins: (report.skins || []).slice(0, 20), preservation: report.preservation || null};
}
function boundedJobReceipt(record) {
  const result = record.result || null;
  const legacy = record.contractVersion !== 'home-center.foundry-job.v2';
  return {
    contractVersion: legacy ? record.contractVersion || 'home-center.foundry-job.v1' : 'home-center.foundry-job.v2',
    capabilityVersion: record.capabilityVersion || FOUNDRY_CAPABILITY_VERSION,
    jobId: record.jobId,
    namespace: record.namespace,
    inputHash: record.inputHash,
    state: record.state,
    domain: record.domain || record.recipe && record.recipe.domain,
    revision: Number(record.revision || 0),
    parent: record.parent || null,
    legacyReadOnly: legacy,
    source: record.source ? {kind: record.source.kind, artifactId: record.source.artifactId || null, sha256: record.source.sha256, byteLength: record.source.byteLength, filename: record.source.filename} : null,
    script: record.script ? {kind: record.script.kind, artifactId: record.script.artifactId || null, version: record.script.version, sha256: record.script.sha256, byteLength: record.script.byteLength, filename: record.script.filename} : null,
    timestamps: {acceptedAt: record.acceptedAt, startedAt: record.startedAt || null, completedAt: record.completedAt || null, failedAt: record.failedAt || null, updatedAt: record.updatedAt},
    execution: {attempt: Number(record.executionAttempt || 0), timedOut: !!record.timedOut, logBytes: record.logBytes || {stdout: 0, stderr: 0}, logsTruncated: !!record.logsTruncated},
    blockingError: record.blockingError ? {code: text(record.blockingError.code, 120), message: text(record.blockingError.message, 1200)} : null,
    result: result ? {resultHash: result.resultHash, cacheKey: result.cacheKey, report: boundedReport(result.report), artifacts: result.artifacts.map((artifact) => ({kind: artifact.kind, name: artifact.name, mediaType: artifact.mediaType, byteLength: artifact.byteLength, sha256: artifact.sha256, storageRef: artifact.storageRef})), review: result.review || null, promotion: result.promotion || null} : null,
  };
}

function redactFailureLog(value) {
  return String(value || '')
    .replace(/(authorization\s*:\s*bearer\s+)[^\s]+/gi, '$1[REDACTED]')
    .replace(/([?&](?:x-goog-signature|x-goog-credential|token|access_token)=)[^&\s]+/gi, '$1[REDACTED]')
    .replace(/((?:api[_-]?key|secret|password)\s*[=:]\s*)[^\s,;]+/gi, '$1[REDACTED]');
}

async function boundedFailureLogs({storage = storageClient(), record}) {
  if (record.state !== 'failed' || !record.failureLogs || typeof record.failureLogs !== 'object') return null;
  const attempt = Number(record.executionAttempt || 0);
  const expectedPrefix = 'foundry/v2/' + record.ownerHash + '/' + record.namespace + '/' + record.inputHash + '/attempt-' + attempt + '/logs/';
  const out = {};
  for (const streamName of ['stdout', 'stderr']) {
    const descriptor = record.failureLogs[streamName];
    if (!descriptor) continue;
    const storageRef = text(descriptor.storageRef, 1600);
    const expectedRef = 'gs://' + ARTIFACT_BUCKET + '/' + expectedPrefix + streamName + '.log';
    const byteLength = Number(descriptor.byteLength || 0);
    const digest = text(descriptor.sha256, 64).toLowerCase();
    const base = {storageRef, byteLength, sha256: digest};
    if (storageRef !== expectedRef || !Number.isSafeInteger(byteLength) || byteLength < 0 || !/^[a-f0-9]{64}$/.test(digest)) {
      out[streamName] = {...base, readbackVerified: false, error: {code: 'foundry.failure_log.invalid_descriptor', message: 'Stored failure-log identity does not match this job.'}};
      continue;
    }
    try {
      const [bytes] = await storage.bucket(ARTIFACT_BUCKET).file(expectedPrefix + streamName + '.log').download();
      const value = Buffer.from(bytes);
      if (value.length !== byteLength || sha256(value) !== digest) {
        out[streamName] = {...base, readbackVerified: false, error: {code: 'foundry.failure_log.readback_mismatch', message: 'Stored failure-log bytes do not match their receipt.'}};
        continue;
      }
      const excerptBytes = value.subarray(Math.max(0, value.length - FOUNDRY_STATUS_LOG_EXCERPT_BYTES));
      out[streamName] = {
        ...base,
        readbackVerified: true,
        excerpt: redactFailureLog(excerptBytes.toString('utf8')),
        excerptByteLength: excerptBytes.length,
        excerptTruncated: value.length > excerptBytes.length || !!record.logsTruncated,
      };
    } catch (error) {
      out[streamName] = {...base, readbackVerified: false, error: {code: 'foundry.failure_log.read_failed', message: text(error.message || String(error), 500)}};
    }
  }
  return out;
}

async function defaultEnqueue(payload) {
  await getFunctions().taskQueue(FOUNDRY_TASK_FUNCTION).enqueue(payload, {id: 'foundry-' + payload.jobId + '-' + (payload.executionAttempt || 0), dispatchDeadlineSeconds: Math.ceil(FOUNDRY_TIMEOUT_MS / 1000)});
}
async function queueFoundryRun({admin, storage = storageClient(), user, args = {}, enqueue = defaultEnqueue}) {
  if (args.recipe) throw fail('foundry.contract.retired', 'Recipe-based Foundry V1 execution is retired. Use home-center.foundry-run.v2 with a foundry-js.v1 script.', 410, {replacement: 'foundry.asset.run'});
  if (args.contractVersion !== FOUNDRY_RUN_VERSION) throw fail('foundry.contract.unsupported_version', 'Unsupported Foundry run contract: ' + (args.contractVersion || 'missing'), 400, {supported: [FOUNDRY_RUN_VERSION]});
  const owner = ownerEmail(user), domain = normalizeDomain(args.domain, args.__internalInspect === true), source = await resolveSource({storage, user, source: args.source || null, domain}), script = await resolveScript({storage, user, script: args.script}), modelSheet = await resolveModelSheet({storage, user, modelSheet: args.modelSheet || null});
  const idempotencyKey = slug(args.idempotencyKey || args.requestId, '', 180), namespace = slug(args.namespace, '', 120);
  if (!idempotencyKey) throw fail('foundry.idempotency_key_required', 'idempotencyKey is required.');
  if (!namespace) throw fail('foundry.namespace_required', 'A distinct job namespace is required.');
  const parameters = normalizeParameters(args.parameters), reviewPreset = slug(args.reviewPreset, 'fixed-six-view', 80);
  if (reviewPreset !== 'fixed-six-view') throw fail('foundry.review.unsupported_preset', 'Foundry V2 supports fixed-six-view.', 400, {supported: ['fixed-six-view']});
  const parent = await resolveParent({admin, owner, parent: args.parent || null, source});
  const scriptIdentity = {...script}; delete scriptIdentity.text;
  const logical = {capabilityVersion: FOUNDRY_CAPABILITY_VERSION, contractVersion: FOUNDRY_RUN_VERSION, domain, source, script: scriptIdentity, parameters, reviewPreset, modelSheet, namespace, parent};
  const modelSheetRecord = modelSheetRecordFields(modelSheet);
  const inputHash = hashJson(logical), ownerHash = ownerKey(owner), jobId = sha256(Buffer.from(ownerHash + ':' + namespace + ':' + inputHash)).slice(0, 40), idemId = ownerHash + '-' + sha256(Buffer.from(idempotencyKey)).slice(0, 32);
  const jobRef = admin.firestore().collection(JOBS).doc(jobId), idemRef = admin.firestore().collection(IDEMPOTENCY).doc(idemId), now = new Date().toISOString();
  let attached = false;
  await admin.firestore().runTransaction(async (transaction) => {
    const idemSnap = await transaction.get(idemRef);
    if (idemSnap.exists) {
      const existing = idemSnap.data() || {};
      if (existing.inputHash !== inputHash || existing.namespace !== namespace) throw fail('foundry.idempotency_conflict', 'Idempotency key is already bound to different Foundry inputs.', 409);
      attached = true;
      return;
    }
    const record = {contractVersion: 'home-center.foundry-job.v2', capabilityVersion: FOUNDRY_CAPABILITY_VERSION, jobId, owner, ownerHash, namespace, inputHash, idempotencyKeyHash: sha256(Buffer.from(idempotencyKey)), source, script, domain, parameters, reviewPreset, ...modelSheetRecord, parent, revision: parent ? parent.revision : 0, state: 'accepted', enqueueStatus: 'pending', executionAttempt: 0, acceptedAt: now, updatedAt: now, humanAcceptance: 'unreviewed'};
    transaction.create(jobRef, record);
    transaction.create(idemRef, {jobId, ownerHash, namespace, inputHash, contractVersion: FOUNDRY_RUN_VERSION, createdAt: now});
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
    throw fail('foundry.enqueue_failed', 'Foundry worker enqueue failed: ' + text(error.message || String(error), 600), 503);
  }
  return acceptedReceipt((await jobRef.get()).data(), false);
}
async function inspectFoundryAsset(context) {
  const args = context.args || {};
  return queueFoundryRun({...context, args: {...args, __internalInspect: true, contractVersion: FOUNDRY_RUN_VERSION, domain: 'inspect', script: {kind: 'inline', version: FOUNDRY_SCRIPT_VERSION, filename: 'inspect.foundry.js', text: "foundry.asset.inspect(); foundry.review.fixedViews(['front','back','left','right','top','perspective']);"}, parameters: {}, reviewPreset: 'fixed-six-view'}});
}
async function foundryStatus({admin, storage = storageClient(), user, args = {}}) {
  const jobId = text(args.jobId, 80);
  if (!/^[a-f0-9]{40}$/.test(jobId)) throw fail('foundry.job_id_invalid', 'jobId is invalid.');
  const snapshot = await admin.firestore().collection(JOBS).doc(jobId).get();
  if (!snapshot.exists) throw fail('foundry.job_not_found', 'Foundry job was not found.', 404);
  const record = snapshot.data() || {};
  if (record.owner !== ownerEmail(user)) throw fail('foundry.job_forbidden', 'Foundry job is not owned by this caller.', 403);
  const receipt = boundedJobReceipt(record);
  const failureLogs = await boundedFailureLogs({storage, record});
  if (failureLogs) receipt.failureLogs = failureLogs;
  return receipt;
}
function publicArtifactUrl(publicationId, name) { return FOUNDRY_PUBLIC_BASE + '/foundry/artifacts/' + encodeURIComponent(publicationId) + '/' + encodeURIComponent(name); }
function publicationLinks(publication, namespace) {
  const links = Object.values(publication.artifacts).map((artifact) => ({kind: artifact.kind, name: artifact.name, mediaType: artifact.mediaType, byteLength: artifact.byteLength, sha256: artifact.sha256, url: publicArtifactUrl(publication.publicationId || publication.promotionId, artifact.name)}));
  const glb = links.find((artifact) => artifact.kind === 'glb'), manifest = links.find((artifact) => artifact.kind === 'manifest');
  const viewerUrl = glb ? FOUNDRY_VIEWER_BASE + '?src=' + encodeURIComponent(glb.url) + (manifest ? '&manifest=' + encodeURIComponent(manifest.url) : '') + '&title=' + encodeURIComponent('Foundry ' + namespace) : null;
  return {links, viewerUrl};
}
async function publishReviewPacket({admin, record, resultHash, artifacts}) {
  const publicationId = sha256(Buffer.from('review:' + record.jobId + ':' + resultHash)).slice(0, 40), ref = admin.firestore().collection(PUBLICATIONS).doc(publicationId);
  const artifactMap = Object.fromEntries(artifacts.map((artifact) => [artifact.name, {name: artifact.name, kind: artifact.kind, mediaType: artifact.mediaType, byteLength: artifact.byteLength, sha256: artifact.sha256, bucket: artifact.bucket, objectName: artifact.objectName}]));
  const publication = {contractVersion: 'home-center.foundry-review-publication.v2', publicationId, jobId: record.jobId, resultHash, ownerHash: record.ownerHash, namespace: record.namespace, artifacts: artifactMap, publicationKind: 'automatic_review', transportState: 'review_ready', humanAcceptance: 'unreviewed', immutable: true, publishedAt: new Date().toISOString()};
  const existing = await ref.get();
  if (!existing.exists) await ref.create(publication);
  else if (existing.data().resultHash !== resultHash) throw fail('foundry.review.publication_conflict', 'Review publication identity conflict.', 409);
  const links = publicationLinks(publication, record.namespace);
  return {publicationId, resultHash, immutable: true, transportState: 'review_ready', humanAcceptance: 'unreviewed', ...links, publishedAt: publication.publishedAt};
}
async function promoteFoundryResult({admin, user, args = {}}) {
  const owner = ownerEmail(user), jobId = text(args.jobId, 80), resultHash = assertDigest(args.resultHash, 'resultHash'), reviewRequestId = text(args.reviewRequestId, 180);
  if (!reviewRequestId) throw fail('foundry.promotion.review_required', 'An accepted artifact review record is required.', 409);
  const [jobSnapshot, reviewSnapshot] = await Promise.all([admin.firestore().collection(JOBS).doc(jobId).get(), admin.firestore().collection(REVIEW_RECORDS).doc(reviewRequestId).get()]);
  if (!jobSnapshot.exists) throw fail('foundry.job_not_found', 'Foundry job was not found.', 404);
  if (!reviewSnapshot.exists) throw fail('foundry.promotion.review_not_found', 'Artifact review record was not found.', 404);
  const record = jobSnapshot.data() || {}, review = reviewSnapshot.data() || {};
  if (record.owner !== owner || review.ownerEmail !== owner) throw fail('foundry.job_forbidden', 'Job or review is not owned by this caller.', 403);
  if (record.state !== 'completed' || !record.result || record.result.resultHash !== resultHash) throw fail('foundry.promotion.result_conflict', 'Promotion must bind the exact terminal Foundry result.', 409);
  if (record.modelSheet && record.result?.report?.modelSheetFit?.overallPass !== true) throw fail('foundry.promotion.model_sheet_fit_required', 'Model-sheet front, side, and top fit must all pass before promotion.', 409, {modelSheetId: record.modelSheet.id});
  if (review.verdict !== 'accepted' || !review.result || review.result.promotionAllowed !== true || review.result.producer && review.result.producer.receiptId !== jobId) throw fail('foundry.promotion.review_not_accepted', 'Review does not accept this exact Foundry receipt.', 409);
  if (record.domain === 'hard_surface') {
    const validation = record.result.report && record.result.report.validation || {}, simplificationEvidence = review.result.simplificationEvidence;
    if (validation.topologyValid !== true || validation.budgetValid !== true) throw fail('foundry.promotion.machine_gates_failed', 'Hard-surface topology and production budgets must pass before promotion.', 409, {topologyValid: validation.topologyValid, budgetValid: validation.budgetValid});
    if (review.result.purposeValid !== true || !Array.isArray(simplificationEvidence) || !simplificationEvidence.length || simplificationEvidence.some((entry) => !entry || entry.status !== 'passed' || entry.method !== 'remove_or_merge' || !Array.isArray(entry.views) || !entry.views.length || !(Number(entry.maxVisibleErrorPx) > 0))) {
      throw fail('foundry.promotion.purpose_review_required', 'Hard-surface promotion requires accepted remove-or-merge evidence for the exact result.', 409);
    }
  }
  const promotionId = sha256(Buffer.from('promotion:' + jobId + ':' + resultHash + ':' + reviewRequestId)).slice(0, 40), ref = admin.firestore().collection(PUBLICATIONS).doc(promotionId);
  const artifacts = Object.fromEntries(record.result.artifacts.map((artifact) => [artifact.name, {name: artifact.name, kind: artifact.kind, mediaType: artifact.mediaType, byteLength: artifact.byteLength, sha256: artifact.sha256, bucket: artifact.bucket, objectName: artifact.objectName}]));
  const promotion = {contractVersion: 'home-center.foundry-promotion.v2', promotionId, publicationId: promotionId, jobId, resultHash, reviewRequestId, ownerHash: record.ownerHash, namespace: record.namespace, artifacts, publicationKind: 'accepted_promotion', topologyValid: record.result.report?.validation?.topologyValid ?? null, budgetValid: record.result.report?.validation?.budgetValid ?? null, purposeValid: record.domain === 'hard_surface' ? true : null, humanAcceptance: 'accepted', immutable: true, promotedAt: new Date().toISOString()};
  const existing = await ref.get(); if (!existing.exists) await ref.create(promotion);
  const links = publicationLinks(promotion, record.namespace), bounded = {promotionId, resultHash, reviewRequestId, humanAcceptance: 'accepted', immutable: true, ...links, promotedAt: promotion.promotedAt};
  await jobSnapshot.ref.set({result: {...record.result, promotion: bounded}, humanAcceptance: 'accepted', updatedAt: new Date().toISOString()}, {merge: true});
  return bounded;
}

function boundedLogWriter(filePath, limit) {
  const stream = fs.createWriteStream(filePath, {flags: 'wx'}); let bytes = 0, truncated = false;
  return {write(chunk) { const buffer = Buffer.from(chunk), remaining = Math.max(0, limit - bytes); if (remaining) stream.write(buffer.subarray(0, remaining)); bytes += Math.min(buffer.length, remaining); if (buffer.length > remaining) truncated = true; }, end() { return new Promise((resolve, reject) => { stream.once('error', reject); stream.end(resolve); }); }, stats() { return {bytes, truncated}; }};
}
async function runChildProcess({requestPath, outputDir, stdoutPath, stderrPath, timeoutMs = FOUNDRY_TIMEOUT_MS, spawnImpl = spawn}) {
  const child = spawnImpl(process.execPath, ['--max-old-space-size=3072', path.join(__dirname, 'foundry_worker_process.mjs'), requestPath, outputDir], {cwd: __dirname, detached: true, stdio: ['ignore', 'pipe', 'pipe'], env: {...process.env, FOUNDRY_WORKER: 'true'}});
  const stdout = boundedLogWriter(stdoutPath, FOUNDRY_LOG_MAX_BYTES), stderr = boundedLogWriter(stderrPath, FOUNDRY_LOG_MAX_BYTES);
  child.stdout.on('data', (chunk) => stdout.write(chunk)); child.stderr.on('data', (chunk) => stderr.write(chunk));
  let timedOut = false;
  const exit = await new Promise((resolve, reject) => { const timer = setTimeout(() => { timedOut = true; try { process.kill(-child.pid, 'SIGKILL'); } catch (_) { try { child.kill('SIGKILL'); } catch (_) {} } }, timeoutMs); child.once('error', (error) => { clearTimeout(timer); reject(error); }); child.once('close', (code, signal) => { clearTimeout(timer); resolve({code, signal}); }); });
  await Promise.all([stdout.end(), stderr.end()]);
  return {...exit, timedOut, stdout: stdout.stats(), stderr: stderr.stats()};
}
async function validateGlbFile(filePath, expectedByteLength) {
  const handle = await fsp.open(filePath, 'r');
  try { const header = Buffer.alloc(12), {bytesRead} = await handle.read(header, 0, 12, 0); if (bytesRead !== 12 || header.toString('ascii', 0, 4) !== 'glTF') throw fail('foundry.source.invalid_glb_magic', 'Source is not a binary glTF file.', 415); const version = header.readUInt32LE(4), declaredLength = header.readUInt32LE(8); if (version !== 2) throw fail('foundry.source.unsupported_glb_version', 'Foundry requires GLB version 2; received ' + version + '.', 415); if (declaredLength !== expectedByteLength) throw fail('foundry.source.glb_length_mismatch', 'GLB declared length does not match verified bytes.', 409, {declaredLength, expectedByteLength}); } finally { await handle.close(); }
}
async function digestFile(filePath) { const hash = createHash('sha256'); let byteLength = 0; for await (const chunk of fs.createReadStream(filePath)) { hash.update(chunk); byteLength += chunk.length; } return {sha256: hash.digest('hex'), byteLength}; }
function artifactKind(name) { if (name.endsWith('.glb')) return 'glb'; if (/^fixed-.*\.png$/.test(name)) return 'fixedView'; if (/^reference-(front|side|top)\.png$/.test(name)) return 'modelSheetReference'; if (/^overlay-(front|side|top)-(cage|surface)\.png$/.test(name)) return 'modelSheetOverlay'; if (/^difference-(front|side|top)\.png$/.test(name)) return 'modelSheetDifference'; if (name === 'model-sheet-contact-sheet.png') return 'modelSheetContactSheet'; if (name === 'model-sheet-registration.json') return 'modelSheetRegistration'; if (name === 'model-sheet-fit-report.json') return 'modelSheetFitReport'; if (name === 'contact-sheet.png') return 'contactSheet'; if (name === 'skeletal-overlay.png') return 'skeletalOverlay'; if (name === 'foundry-manifest.json') return 'manifest'; if (name === 'validation-report.json') return 'report'; if (name === 'preservation-evidence.json') return 'evidence'; if (name === 'change-evidence.json') return 'changeEvidence'; return 'artifact'; }
function contentType(name) { if (name.endsWith('.glb')) return 'model/gltf-binary'; if (name.endsWith('.png')) return 'image/png'; if (name.endsWith('.json')) return 'application/json'; return 'application/octet-stream'; }
async function uploadImmutableFile({storage = storageClient(), bucketName = ARTIFACT_BUCKET, localPath, objectName, metadata}) {
  const file = storage.bucket(bucketName).file(objectName), expected = await digestFile(localPath); let reused = false;
  try { await storage.bucket(bucketName).upload(localPath, {destination: objectName, resumable: expected.byteLength > 8 * 1024 * 1024, validation: 'crc32c', preconditionOpts: {ifGenerationMatch: 0}, metadata: {contentType: metadata.mediaType, metadata}}); }
  catch (error) { if (![409, 412].includes(Number(error && error.code)) && !/condition|already exists/i.test(String(error && error.message))) throw error; reused = true; }
  const [remote] = await file.download(), actual = {byteLength: remote.length, sha256: sha256(remote)};
  if (actual.byteLength !== expected.byteLength || actual.sha256 !== expected.sha256) throw fail('foundry.output.readback_mismatch', 'Foundry output failed readback verification: ' + path.basename(localPath), 502);
  return {...expected, bucket: bucketName, objectName, storageRef: 'gs://' + bucketName + '/' + objectName, reused};
}
async function downloadVerified(storage, identity, destination, role) {
  await storage.bucket(identity.bucket).file(identity.objectName).download({destination});
  const digest = await digestFile(destination);
  if (digest.byteLength !== identity.byteLength || digest.sha256 !== identity.sha256) throw fail('foundry.' + role + '.readback_mismatch', 'Foundry ' + role + ' failed byte length or SHA-256 verification.', 409);
  return digest;
}
async function executeFoundryJob(admin, payload = {}, dependencies = {}) {
  const storage = dependencies.storage || storageClient(), jobId = text(payload.jobId, 80), jobRef = admin.firestore().collection(JOBS).doc(jobId); let record = null, shouldExecute = true;
  const leaseId = randomUUID(), nowMs = Date.now(), startedAt = new Date(nowMs).toISOString();
  await admin.firestore().runTransaction(async (transaction) => { const snapshot = await transaction.get(jobRef); if (!snapshot.exists) throw fail('foundry.job_not_found', 'Foundry worker job was not found.', 404); record = snapshot.data() || {}; if (record.inputHash !== payload.inputHash) throw fail('foundry.worker.input_conflict', 'Worker payload input hash does not match durable job.', 409); if (record.state === 'completed' || record.state === 'running' && Number(record.leaseExpiresAtMs || 0) > nowMs) { shouldExecute = false; return; } if (record.contractVersion !== 'home-center.foundry-job.v2') throw fail('foundry.contract.retired', 'Queued Foundry V1 execution is retired.', 410); transaction.set(jobRef, {state: 'running', startedAt: record.startedAt || startedAt, updatedAt: startedAt, executionAttempt: Number(payload.executionAttempt || 0), leaseId, leaseExpiresAtMs: nowMs + FOUNDRY_TIMEOUT_MS + 60000}, {merge: true}); });
  if (!shouldExecute) return boundedJobReceipt(record);
  const tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'foundry-' + jobId + '-')), inputPath = path.join(tempDir, 'source.glb'), scriptPath = path.join(tempDir, 'foundry-script.js'), requestPath = path.join(tempDir, 'request.json'), outputDir = path.join(tempDir, 'output'), stdoutPath = path.join(tempDir, 'stdout.log'), stderrPath = path.join(tempDir, 'stderr.log');
  await fsp.mkdir(outputDir); let execution = null;
  try {
    if (record.source) { await downloadVerified(storage, record.source, inputPath, 'source'); await validateGlbFile(inputPath, record.source.byteLength); }
    if (record.script.kind === 'home_center_artifact') await downloadVerified(storage, record.script, scriptPath, 'script');
    const workerModelSheet = modelSheetFromRecord(record);
    if (workerModelSheet) {
      for (const viewName of ['front', 'side', 'top']) {
        const imagePath = path.join(tempDir, 'model-sheet-' + viewName + '.png');
        await downloadVerified(storage, workerModelSheet.views[viewName].image, imagePath, 'model_sheet_' + viewName);
        workerModelSheet.views[viewName].imagePath = imagePath;
      }
    }
    const request = {contractVersion: FOUNDRY_RUN_VERSION, domain: record.domain, parameters: record.parameters, reviewPreset: record.reviewPreset, modelSheet: workerModelSheet, scriptVersion: record.script.version, scriptSeed: parseInt(record.inputHash.slice(0, 8), 16), scriptPath: record.script.kind === 'home_center_artifact' ? scriptPath : '', scriptText: record.script.kind === 'inline' ? record.script.text : '', sourcePath: record.source ? inputPath : ''};
    await fsp.writeFile(requestPath, JSON.stringify(request));
    execution = await runChildProcess({requestPath, outputDir, stdoutPath, stderrPath, timeoutMs: dependencies.timeoutMs || FOUNDRY_TIMEOUT_MS, spawnImpl: dependencies.spawnImpl || spawn});
    if (execution.timedOut) throw fail('foundry.worker.timeout', 'Foundry worker exceeded bounded runtime and the process tree was terminated.', 504);
    if (execution.code !== 0) throw fail('foundry.worker.failed', 'Foundry worker exited with code ' + execution.code + '; inspect bounded job logs.', 500, {signal: execution.signal});
    const names = (await fsp.readdir(outputDir)).sort(); let totalBytes = 0; const identities = [];
    for (const name of names) { const digest = await digestFile(path.join(outputDir, name)); totalBytes += digest.byteLength; identities.push({name, ...digest}); }
    if (totalBytes > FOUNDRY_MAX_OUTPUT_BYTES) throw fail('foundry.limit.output', 'Foundry outputs exceed configured ceiling.', 413, {totalBytes, max: FOUNDRY_MAX_OUTPUT_BYTES});
    const resultHash = hashJson(identities), cacheKey = sha256(Buffer.from(record.namespace + ':' + record.inputHash + ':' + resultHash)), prefix = 'foundry/v2/' + record.ownerHash + '/' + record.namespace + '/' + record.inputHash + '/' + resultHash, artifacts = [];
    for (const identity of identities) { const kind = artifactKind(identity.name), type = contentType(identity.name), uploaded = await uploadImmutableFile({storage, localPath: path.join(outputDir, identity.name), objectName: prefix + '/' + identity.name, metadata: {jobId, namespace: record.namespace, inputHash: record.inputHash, resultHash, kind, mediaType: type, sha256: identity.sha256, byteLength: String(identity.byteLength)}}); artifacts.push({kind, name: identity.name, mediaType: type, ...uploaded}); }
    const logs = {};
    for (const [streamName, localPath] of [['stdout', stdoutPath], ['stderr', stderrPath]]) { const uploaded = await uploadImmutableFile({storage, localPath, objectName: prefix + '/logs/' + streamName + '.log', metadata: {jobId, namespace: record.namespace, inputHash: record.inputHash, resultHash, kind: streamName + 'Log', mediaType: 'text/plain'}}); logs[streamName] = {storageRef: uploaded.storageRef, byteLength: uploaded.byteLength, sha256: uploaded.sha256}; }
    const report = JSON.parse(await fsp.readFile(path.join(outputDir, 'validation-report.json'), 'utf8')), review = await publishReviewPacket({admin, record, resultHash, artifacts}), completedAt = new Date().toISOString(), result = {resultHash, cacheKey, report, artifacts, logs, totalBytes, immutable: true, publicationState: 'review_ready', review};
    await jobRef.set({state: 'completed', completedAt, updatedAt: completedAt, result, humanAcceptance: 'unreviewed', logBytes: {stdout: execution.stdout.bytes, stderr: execution.stderr.bytes}, logsTruncated: execution.stdout.truncated || execution.stderr.truncated, timedOut: false, blockingError: null, leaseId: null, leaseExpiresAtMs: 0}, {merge: true});
    return boundedJobReceipt({...record, state: 'completed', completedAt, updatedAt: completedAt, result, logBytes: {stdout: execution.stdout.bytes, stderr: execution.stderr.bytes}, logsTruncated: execution.stdout.truncated || execution.stderr.truncated});
  } catch (error) {
    const failedAt = new Date().toISOString(), failureLogs = {};
    if (execution) for (const [streamName, localPath] of [['stdout', stdoutPath], ['stderr', stderrPath]]) try { const uploaded = await uploadImmutableFile({storage, localPath, objectName: 'foundry/v2/' + record.ownerHash + '/' + record.namespace + '/' + record.inputHash + '/attempt-' + Number(payload.executionAttempt || 0) + '/logs/' + streamName + '.log', metadata: {jobId, namespace: record.namespace, inputHash: record.inputHash, kind: streamName + 'Log', mediaType: 'text/plain'}}); failureLogs[streamName] = {storageRef: uploaded.storageRef, byteLength: uploaded.byteLength, sha256: uploaded.sha256}; } catch (_) {}
    await jobRef.set({state: 'failed', failedAt, updatedAt: failedAt, timedOut: error.code === 'foundry.worker.timeout', logBytes: execution ? {stdout: execution.stdout.bytes, stderr: execution.stderr.bytes} : {stdout: 0, stderr: 0}, logsTruncated: execution ? execution.stdout.truncated || execution.stderr.truncated : false, failureLogs, leaseId: null, leaseExpiresAtMs: 0, blockingError: {code: text(error.code, 120) || 'foundry.worker.failed', message: text(error.message || String(error), 1200)}}, {merge: true});
    throw error;
  } finally { await fsp.rm(tempDir, {recursive: true, force: true}); }
}
async function runFoundryOperation({operation, admin, storage, user, args, enqueue}) {
  if (operation === 'foundry.asset.inspect') return inspectFoundryAsset({admin, storage, user, args, enqueue});
  if (operation === 'foundry.asset.run') return queueFoundryRun({admin, storage, user, args, enqueue});
  if (operation === 'foundry.asset.status') return foundryStatus({admin, storage, user, args});
  if (operation === 'foundry.asset.promote') return promoteFoundryResult({admin, user, args});
  throw fail('foundry.operation.unsupported', 'Unsupported Foundry operation: ' + operation);
}
function installFoundryArtifactRoutes(app, {admin, storage = storageClient()}) {
  app.get('/foundry/artifacts/:publicationId/:name', async (req, res) => {
    try { const publicationId = text(req.params.publicationId, 80), name = filename(req.params.name); if (!/^[a-f0-9]{40}$/.test(publicationId)) throw fail('foundry.publication.invalid', 'Publication identifier is invalid.', 404); const snapshot = await admin.firestore().collection(PUBLICATIONS).doc(publicationId).get(); if (!snapshot.exists) throw fail('foundry.publication.not_found', 'Foundry review artifact was not found.', 404); const publication = snapshot.data() || {}, artifact = publication.artifacts && publication.artifacts[name]; if (!artifact || artifact.name !== name) throw fail('foundry.publication.artifact_not_found', 'Foundry review artifact was not found.', 404); res.set('Access-Control-Allow-Origin', '*'); res.set('Cache-Control', 'public, max-age=31536000, immutable'); res.set('Content-Type', artifact.mediaType); res.set('Content-Length', String(artifact.byteLength)); res.set('ETag', '"' + artifact.sha256 + '"'); res.set('X-Content-Type-Options', 'nosniff'); storage.bucket(artifact.bucket).file(artifact.objectName).createReadStream().on('error', (error) => { if (!res.headersSent) res.status(502).json({error: 'foundry.artifact.read_failed', message: text(error.message, 300)}); else res.destroy(error); }).pipe(res); }
    catch (error) { res.status(error.status || 500).json({error: error.code || 'foundry.artifact.failed', message: text(error.message || String(error), 600), details: error.details || {}}); }
  });
}

module.exports = {FOUNDRY_CAPABILITY_VERSION, FOUNDRY_RUN_VERSION, FOUNDRY_SCRIPT_VERSION, FOUNDRY_MODEL_SHEET_VERSION, FOUNDRY_TASK_FUNCTION, foundryOperationEntries, resolveSource, resolveScript, resolveModelSheet, modelSheetRecordFields, modelSheetFromRecord, queueFoundryRun, inspectFoundryAsset, foundryStatus, promoteFoundryResult, executeFoundryJob, runFoundryOperation, installFoundryArtifactRoutes, boundedJobReceipt, runChildProcess, hashJson};
