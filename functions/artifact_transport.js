'use strict';

const {createHash} = require('node:crypto');

const ARTIFACT_TRANSPORT_VERSION = 'home-center.artifact-transport.v1';
const ARTIFACT_REFERENCE_VERSION = 'home-center.artifact-reference.v1';
const BLENDER_RENDER_CONTRACT_VERSION = 'home-center.blender-render-request.v2';
const DEFAULT_STAGE_CONCURRENCY = 4;
const MAX_STAGE_CONCURRENCY = 8;
const LEGACY_BASE64_MAX_BYTES = 64 * 1024;
const LOCATION_KINDS = Object.freeze(['gcs', 'drive', 'github', 'host_upload', 'command_center_bucket', 'inline_metadata']);
const TRANSFER_STATES = Object.freeze(['accepted', 'resolving', 'staging', 'ready', 'executing', 'publishing', 'completed', 'failed', 'quarantined', 'expired', 'aborted']);

class ArtifactTransportError extends Error {
  constructor(code, message, {status = 400, field = '', retryable = false, details = {}} = {}) {
    super(message);
    this.name = 'ArtifactTransportError';
    this.code = code;
    this.status = status;
    this.field = field;
    this.retryable = retryable;
    this.details = boundedObject(details);
    this.failureKind = 'artifact_transport';
  }
}

function boundedText(value, max = 1000) {
  const clean = value === undefined || value === null ? '' : String(value).trim();
  return clean.length > max ? clean.slice(0, max) : clean;
}

function boundedObject(value, depth = 0) {
  if (depth > 4) return '[bounded]';
  if (Array.isArray(value)) return value.slice(0, 50).map((item) => boundedObject(item, depth + 1));
  if (!value || typeof value !== 'object') return typeof value === 'string' ? boundedText(value, 500) : value;
  const out = {};
  for (const key of Object.keys(value).sort().slice(0, 50)) {
    if (/token|secret|password|authorization|uploadurl|signedurl|base64|bytes|body/i.test(key)) continue;
    out[boundedText(key, 80)] = boundedObject(value[key], depth + 1);
  }
  return out;
}

function structuredArtifactError(error, fallbackField = '') {
  const err = error instanceof ArtifactTransportError ? error : new ArtifactTransportError(
    boundedText(error && (error.code || error.failureKind), 120) || 'ARTIFACT_TRANSPORT_FAILED',
    boundedText(error && error.message, 1000) || 'Artifact transport failed.',
    {status: Number(error && error.status) || 500, field: fallbackField, retryable: false},
  );
  return {
    code: err.code,
    message: boundedText(err.message, 1000),
    field: boundedText(err.field || fallbackField, 240),
    status: Number(err.status) || 500,
    retryable: err.retryable === true,
    details: boundedObject(err.details),
  };
}

function sha256Bytes(bytes) {
  return createHash('sha256').update(Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes || '')).digest('hex');
}

function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}';
  return JSON.stringify(value);
}

function sha256Json(value) { return sha256Bytes(Buffer.from(stableJson(value), 'utf8')); }

function logicalFileName(value, field = 'identity.fileName') {
  const clean = boundedText(value, 240).replace(/\\/g, '/').split('/').pop().replace(/[\u0000-\u001f\u007f]/g, '').trim();
  if (!clean) throw new ArtifactTransportError('ARTIFACT_FILENAME_REQUIRED', 'A stable logical filename is required.', {field});
  return clean;
}

function mediaType(value, field = 'identity.mediaType') {
  const clean = boundedText(value, 160).toLowerCase();
  if (!/^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(clean)) {
    throw new ArtifactTransportError('ARTIFACT_MEDIA_TYPE_INVALID', 'mediaType must be a valid MIME type.', {field});
  }
  return clean;
}

function sha256Identity(value, field = 'identity.sha256') {
  const clean = boundedText(value, 64).toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(clean)) {
    throw new ArtifactTransportError('ARTIFACT_SHA256_INVALID', 'sha256 must be a 64-character hexadecimal digest.', {field});
  }
  return clean;
}

function byteLength(value, field = 'identity.byteLength') {
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < 0) {
    throw new ArtifactTransportError('ARTIFACT_BYTE_LENGTH_INVALID', 'byteLength must be a non-negative safe integer.', {field});
  }
  return number;
}

function normalizeArtifactIdentity(value = {}, field = 'identity') {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  return {
    sha256: sha256Identity(source.sha256 || source.digest, field + '.sha256'),
    byteLength: byteLength(source.byteLength ?? source.byteCount ?? source.size, field + '.byteLength'),
    mediaType: mediaType(source.mediaType || source.mimeType || 'application/octet-stream', field + '.mediaType'),
    fileName: logicalFileName(source.fileName || source.name, field + '.fileName'),
  };
}

function normalizeArtifactLocation(value = {}, field = 'locations[0]') {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const kind = boundedText(source.kind || source.type, 80).toLowerCase();
  if (!LOCATION_KINDS.includes(kind)) {
    throw new ArtifactTransportError('ARTIFACT_REFERENCE_KIND_UNSUPPORTED', 'Unsupported artifact location kind: ' + (kind || '(missing)') + '.', {field: field + '.kind', details: {supportedKinds: LOCATION_KINDS}});
  }
  const expiresAt = boundedText(source.expiresAt, 80);
  const location = {kind};
  if (expiresAt) location.expiresAt = expiresAt;
  if (kind === 'gcs') {
    const uri = boundedText(source.uri || source.ref || source.storageRef, 1600);
    if (!/^gs:\/\/[^/]+\/.+/.test(uri)) throw new ArtifactTransportError('ARTIFACT_GCS_URI_INVALID', 'GCS location uri must use gs://bucket/object.', {field: field + '.uri'});
    location.uri = uri;
    if (source.generation !== undefined && source.generation !== null && source.generation !== '') location.generation = boundedText(source.generation, 80);
  } else if (kind === 'drive') {
    const fileId = boundedText(source.fileId || String(source.uri || source.ref || '').replace(/^drive:\/\//i, '').split(/[?#/]/).filter(Boolean).pop(), 240);
    if (!fileId) throw new ArtifactTransportError('ARTIFACT_DRIVE_ID_REQUIRED', 'Drive location fileId is required.', {field: field + '.fileId'});
    location.fileId = fileId;
  } else if (kind === 'github') {
    location.repository = boundedText(source.repository || source.repo, 240);
    location.ref = boundedText(source.ref || source.sha || source.branch, 240);
    location.path = boundedText(source.path || source.filePath, 1000).replace(/^\/+/, '');
    if (!/^[^/]+\/[^/]+$/.test(location.repository)) throw new ArtifactTransportError('ARTIFACT_GITHUB_REPOSITORY_INVALID', 'GitHub repository must use owner/name.', {field: field + '.repository'});
    if (!location.ref) throw new ArtifactTransportError('ARTIFACT_GITHUB_REF_REQUIRED', 'GitHub ref must be immutable or explicitly versioned.', {field: field + '.ref'});
    if (!location.path || location.path.includes('..')) throw new ArtifactTransportError('ARTIFACT_GITHUB_PATH_INVALID', 'GitHub path is required and must not traverse directories.', {field: field + '.path'});
  } else if (kind === 'host_upload') {
    location.field = boundedText(source.field, 120);
    if (!location.field) throw new ArtifactTransportError('ARTIFACT_HOST_UPLOAD_FIELD_REQUIRED', 'Host upload location field is required.', {field: field + '.field'});
  } else if (kind === 'command_center_bucket') {
    location.objectId = boundedText(source.objectId || String(source.uri || source.ref || '').replace(/^bucket:\/\//i, '').split(/[?#/]/).filter(Boolean).pop(), 240);
    if (!location.objectId) throw new ArtifactTransportError('ARTIFACT_BUCKET_OBJECT_REQUIRED', 'Command Center bucket objectId is required.', {field: field + '.objectId'});
  } else {
    location.key = boundedText(source.key || source.name, 160);
    if (!location.key) throw new ArtifactTransportError('ARTIFACT_INLINE_METADATA_KEY_REQUIRED', 'Inline metadata location key is required.', {field: field + '.key'});
  }
  return location;
}

function normalizeArtifactReference(value = {}, field = 'artifacts[0]') {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const identity = normalizeArtifactIdentity(source.identity || source, field + '.identity');
  const locationsRaw = Array.isArray(source.locations) ? source.locations : source.location ? [source.location] : [];
  if (!locationsRaw.length) throw new ArtifactTransportError('ARTIFACT_LOCATION_REQUIRED', 'At least one transport location is required.', {field: field + '.locations'});
  const locations = locationsRaw.map((location, index) => normalizeArtifactLocation(location, field + '.locations[' + index + ']'));
  const role = boundedText(source.role, 120);
  return {
    schemaVersion: ARTIFACT_REFERENCE_VERSION,
    ...(role ? {role} : {}),
    identity,
    locations,
    provenance: boundedObject(source.provenance || {}),
  };
}

function adaptLegacyArtifactReference(value, identity, role = '') {
  if (value && typeof value === 'object' && value.schemaVersion === ARTIFACT_REFERENCE_VERSION) return normalizeArtifactReference(value);
  const ref = boundedText(value, 1600);
  let location;
  if (/^gs:\/\//i.test(ref)) location = {kind: 'gcs', uri: ref};
  else if (/^drive:\/\//i.test(ref)) location = {kind: 'drive', fileId: ref.replace(/^drive:\/\//i, '').split(/[?#/]/).filter(Boolean).pop()};
  else if (/^bucket:\/\//i.test(ref)) location = {kind: 'command_center_bucket', objectId: ref.replace(/^bucket:\/\//i, '').split(/[?#/]/).filter(Boolean).pop()};
  else throw new ArtifactTransportError('ARTIFACT_LEGACY_REFERENCE_UNSUPPORTED', 'Legacy artifact reference must use gs://, drive://, or bucket://.', {field: role ? role + 'Ref' : 'ref'});
  return normalizeArtifactReference({role, identity, locations: [location]}, role || 'artifact');
}

function referenceIdentityKey(reference) {
  const ref = normalizeArtifactReference(reference);
  return ref.identity.sha256 + ':' + ref.identity.byteLength + ':' + ref.identity.mediaType + ':' + ref.identity.fileName;
}

function isExpired(location, now = Date.now()) {
  if (!location.expiresAt) return false;
  const time = Date.parse(location.expiresAt);
  return Number.isFinite(time) && time <= now;
}

function planArtifactLocation(reference, consumer = {}, now = Date.now()) {
  const ref = normalizeArtifactReference(reference);
  const supported = Array.isArray(consumer.supportedLocationKinds) && consumer.supportedLocationKinds.length ? consumer.supportedLocationKinds : ['gcs'];
  const priority = Array.isArray(consumer.locationPriority) && consumer.locationPriority.length ? consumer.locationPriority : supported;
  const available = ref.locations.filter((location) => !isExpired(location, now) && supported.includes(location.kind));
  const chosen = priority.map((kind) => available.find((location) => location.kind === kind)).find(Boolean) || available[0];
  if (!chosen) {
    const expiredKinds = ref.locations.filter((location) => isExpired(location, now)).map((location) => location.kind);
    throw new ArtifactTransportError(expiredKinds.length ? 'ARTIFACT_REFERENCE_EXPIRED' : 'ARTIFACT_REFERENCE_UNRESOLVABLE', expiredKinds.length ? 'Every compatible artifact location is expired.' : 'No artifact location is compatible with the consumer.', {field: 'locations', status: expiredKinds.length ? 410 : 422, details: {supportedKinds: supported, availableKinds: ref.locations.map((location) => location.kind), expiredKinds}});
  }
  const direct = consumer.directLocationKinds && consumer.directLocationKinds.includes(chosen.kind);
  return {reference: ref, location: chosen, action: direct ? 'reuse' : 'stage', transferPath: direct ? 'server-side-reference-reuse' : chosen.kind + '-to-content-addressed-gcs'};
}

async function boundedMap(values, concurrency, mapper) {
  const items = Array.from(values || []);
  const limit = Math.max(1, Math.min(Number(concurrency) || DEFAULT_STAGE_CONCURRENCY, MAX_STAGE_CONCURRENCY, Math.max(1, items.length)));
  const results = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (true) {
      const index = cursor++;
      if (index >= items.length) return;
      results[index] = await mapper(items[index], index);
    }
  }
  await Promise.all(Array.from({length: limit}, () => worker()));
  return results;
}

function rendererSettingsJsonSchema() {
  return {
    type: 'object',
    additionalProperties: false,
    properties: {
      width: {type: 'integer', minimum: 64, maximum: 4096},
      height: {type: 'integer', minimum: 64, maximum: 4096},
      camera: {type: 'string'},
      outputName: {type: 'string'},
      samples: {type: 'integer', minimum: 1, maximum: 128},
      fixedCameras: {type: 'array', items: {type: 'string'}, maxItems: 12},
      diagnosticViews: {type: 'array', items: {type: 'string'}, maxItems: 12},
      action: {type: 'string'},
      expectedAction: {type: 'string'},
      authoredKeys: {type: 'array', items: {type: 'integer', minimum: 0}, maxItems: 160},
      evidenceFrames: {type: 'array', items: {type: 'integer', minimum: 0}, maxItems: 160},
      gifFrames: {type: 'array', items: {type: 'integer', minimum: 0}, minItems: 1, maxItems: 160},
      gifTimingMs: {type: 'array', items: {type: 'number', exclusiveMinimum: 0}, minItems: 1, maxItems: 160},
      allowRepeatedGifFrames: {type: 'boolean'},
      includeBlend: {type: 'boolean'},
      includeDiagnostics: {type: 'boolean'},
    },
  };
}

function normalizeNumberList(value, field, max = 160) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) throw new ArtifactTransportError('RENDER_FIELD_TYPE_INVALID', field + ' must be an array.', {field});
  if (value.length > max) throw new ArtifactTransportError('RENDER_FIELD_TOO_LARGE', field + ' exceeds ' + max + ' entries.', {field});
  return value.map((item, index) => {
    const number = Number(item);
    if (!Number.isFinite(number)) throw new ArtifactTransportError('RENDER_FIELD_VALUE_INVALID', field + '[' + index + '] must be finite.', {field: field + '[' + index + ']'});
    return number;
  });
}

function normalizeRendererSettings(value = {}) {
  const src = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const evidenceFrames = normalizeNumberList(src.evidenceFrames, 'settings.evidenceFrames').map((value, index) => {
    if (!Number.isInteger(value) || value < 0) throw new ArtifactTransportError('RENDER_FRAME_INVALID', 'settings.evidenceFrames[' + index + '] must be a non-negative integer.', {field: 'settings.evidenceFrames[' + index + ']'});
    return value;
  });
  const gifFrames = normalizeNumberList(src.gifFrames, 'settings.gifFrames').map((value, index) => {
    if (!Number.isInteger(value) || value < 0) throw new ArtifactTransportError('RENDER_FRAME_INVALID', 'settings.gifFrames[' + index + '] must be a non-negative integer.', {field: 'settings.gifFrames[' + index + ']'});
    return value;
  });
  const gifTimingMs = normalizeNumberList(src.gifTimingMs, 'settings.gifTimingMs');
  if (src.gifFrames !== undefined && !gifFrames.length) throw new ArtifactTransportError('RENDER_GIF_FRAMES_EMPTY', 'settings.gifFrames must not be empty.', {field: 'settings.gifFrames'});
  if (gifFrames.length && gifTimingMs.length !== gifFrames.length) throw new ArtifactTransportError('RENDER_GIF_TIMING_LENGTH_MISMATCH', 'settings.gifTimingMs length must equal settings.gifFrames length.', {field: 'settings.gifTimingMs', details: {gifFrames: gifFrames.length, gifTimingMs: gifTimingMs.length}});
  for (let index = 0; index < gifTimingMs.length; index += 1) if (gifTimingMs[index] <= 0) throw new ArtifactTransportError('RENDER_GIF_TIMING_INVALID', 'settings.gifTimingMs[' + index + '] must be positive.', {field: 'settings.gifTimingMs[' + index + ']'});
  if (gifFrames.length && src.allowRepeatedGifFrames !== true && new Set(gifFrames).size !== gifFrames.length) throw new ArtifactTransportError('RENDER_GIF_FRAME_DUPLICATE', 'settings.gifFrames contains a duplicate index.', {field: 'settings.gifFrames'});
  return {
    width: Math.max(64, Math.min(Number(src.width || 1280) || 1280, 4096)),
    height: Math.max(64, Math.min(Number(src.height || 960) || 960, 4096)),
    camera: boundedText(src.camera, 120) || 'front_3q',
    outputName: boundedText(src.outputName, 180) || 'render.png',
    samples: Math.max(1, Math.min(Number(src.samples || src.renderSamples || 64) || 64, 128)),
    fixedCameras: (Array.isArray(src.fixedCameras) ? src.fixedCameras : ['front_3q']).slice(0, 12).map((item) => boundedText(item, 120)).filter(Boolean),
    diagnosticViews: (Array.isArray(src.diagnosticViews) ? src.diagnosticViews : ['front', 'side', 'top']).slice(0, 12).map((item) => boundedText(item, 120)).filter(Boolean),
    action: boundedText(src.action, 120),
    expectedAction: boundedText(src.expectedAction, 120),
    authoredKeys: normalizeNumberList(src.authoredKeys, 'settings.authoredKeys').filter((item) => Number.isInteger(item) && item >= 0),
    evidenceFrames,
    gifFrames,
    gifTimingMs,
    allowRepeatedGifFrames: src.allowRepeatedGifFrames === true,
    includeBlend: src.includeBlend !== false,
    includeDiagnostics: src.includeDiagnostics !== false,
  };
}

function renderCompatibility({settings = {}, contractVersion = BLENDER_RENDER_CONTRACT_VERSION, backend = {}} = {}) {
  const supportedVersions = Array.isArray(backend.contractVersions) && backend.contractVersions.length ? backend.contractVersions : [BLENDER_RENDER_CONTRACT_VERSION];
  if (!supportedVersions.includes(contractVersion)) throw new ArtifactTransportError('ARTIFACT_CONTRACT_VERSION_UNSUPPORTED', 'Renderer contractVersion is not supported by the backend.', {field: 'contractVersion', status: 409, details: {requested: contractVersion, supported: supportedVersions}});
  const normalized = normalizeRendererSettings(settings);
  return {compatible: true, contractVersion, settings: normalized, backendVersion: boundedText(backend.backendVersion, 120)};
}

async function preflightArtifactEnvelope({requestId, operation = 'artifact_transport.preflight', artifacts = [], consumer = {}, concurrency = DEFAULT_STAGE_CONCURRENCY, resolver = async (plan) => ({...plan, resolvable: true})} = {}) {
  const stableRequestId = boundedText(requestId, 180);
  if (!stableRequestId) throw new ArtifactTransportError('ARTIFACT_REQUEST_ID_REQUIRED', 'requestId is required.', {field: 'requestId'});
  if (!Array.isArray(artifacts) || !artifacts.length) throw new ArtifactTransportError('ARTIFACT_ENVELOPE_EMPTY', 'artifacts must contain at least one artifact reference.', {field: 'artifacts'});
  if (artifacts.length > 50) throw new ArtifactTransportError('ARTIFACT_ENVELOPE_TOO_LARGE', 'artifacts exceeds 50 entries.', {field: 'artifacts'});
  const normalized = artifacts.map((artifact, index) => normalizeArtifactReference(artifact, 'artifacts[' + index + ']'));
  const inputHash = sha256Json({operation, artifacts: normalized, consumer: boundedObject(consumer)});
  const startedAtMs = Date.now();
  const results = await boundedMap(normalized, concurrency, async (reference, index) => {
    const itemStartedAtMs = Date.now();
    try {
      const plan = planArtifactLocation(reference, consumer);
      const resolved = await resolver(plan, index);
      return {index, role: reference.role || '', identity: reference.identity, location: plan.location, action: plan.action, transferPath: plan.transferPath, resolvable: resolved.resolvable !== false, verification: boundedObject(resolved.verification || {}), reusedBytes: Number(resolved.reusedBytes || 0), transferredBytes: Number(resolved.transferredBytes || 0), timingMs: Math.max(0, Date.now() - itemStartedAtMs), details: boundedObject(resolved.details || {})};
    } catch (error) {
      return {index, role: reference.role || '', identity: reference.identity, resolvable: false, error: structuredArtifactError(error, 'artifacts[' + index + ']'), timingMs: Math.max(0, Date.now() - itemStartedAtMs)};
    }
  });
  const errors = results.filter((item) => !item.resolvable).map((item) => item.error);
  return {
    schemaVersion: ARTIFACT_TRANSPORT_VERSION,
    contractVersion: ARTIFACT_REFERENCE_VERSION,
    requestId: stableRequestId,
    inputHash,
    state: errors.length ? 'failed' : 'accepted',
    acceptedAt: new Date(startedAtMs).toISOString(),
    statusResource: {operation: 'artifact_transport.status', requestId: stableRequestId},
    concurrencyPlan: {requested: Number(concurrency) || DEFAULT_STAGE_CONCURRENCY, applied: Math.max(1, Math.min(Number(concurrency) || DEFAULT_STAGE_CONCURRENCY, MAX_STAGE_CONCURRENCY, normalized.length)), deterministicManifestOrder: true},
    artifacts: results,
    totals: {artifactCount: results.length, resolvableCount: results.length - errors.length, transferredBytes: results.reduce((sum, item) => sum + Number(item.transferredBytes || 0), 0), reusedBytes: results.reduce((sum, item) => sum + Number(item.reusedBytes || 0), 0), preflightMs: Math.max(0, Date.now() - startedAtMs)},
    errors,
  };
}

function artifactReferenceJsonSchema() {
  const identity = {type: 'object', additionalProperties: false, required: ['sha256', 'byteLength', 'mediaType', 'fileName'], properties: {sha256: {type: 'string', pattern: '^[a-fA-F0-9]{64}$'}, byteLength: {type: 'integer', minimum: 0}, mediaType: {type: 'string'}, fileName: {type: 'string'}}};
  return {
    type: 'object', additionalProperties: false, required: ['schemaVersion', 'identity', 'locations'],
    properties: {
      schemaVersion: {type: 'string', enum: [ARTIFACT_REFERENCE_VERSION]}, role: {type: 'string'}, identity,
      locations: {type: 'array', minItems: 1, maxItems: 12, items: {type: 'object', required: ['kind'], properties: {kind: {type: 'string', enum: LOCATION_KINDS}, uri: {type: 'string'}, generation: {type: 'string'}, fileId: {type: 'string'}, repository: {type: 'string'}, ref: {type: 'string'}, path: {type: 'string'}, field: {type: 'string'}, objectId: {type: 'string'}, key: {type: 'string'}, expiresAt: {type: 'string'}}}},
      provenance: {type: 'object'},
    },
  };
}

module.exports = {
  ARTIFACT_TRANSPORT_VERSION,
  ARTIFACT_REFERENCE_VERSION,
  BLENDER_RENDER_CONTRACT_VERSION,
  DEFAULT_STAGE_CONCURRENCY,
  MAX_STAGE_CONCURRENCY,
  LEGACY_BASE64_MAX_BYTES,
  LOCATION_KINDS,
  TRANSFER_STATES,
  ArtifactTransportError,
  structuredArtifactError,
  boundedObject,
  sha256Bytes,
  stableJson,
  sha256Json,
  normalizeArtifactIdentity,
  normalizeArtifactLocation,
  normalizeArtifactReference,
  adaptLegacyArtifactReference,
  referenceIdentityKey,
  planArtifactLocation,
  boundedMap,
  rendererSettingsJsonSchema,
  normalizeRendererSettings,
  renderCompatibility,
  preflightArtifactEnvelope,
  artifactReferenceJsonSchema,
};
