const {createHash} = require('node:crypto');
const {Readable, Transform} = require('node:stream');
const {pipeline} = require('node:stream/promises');

const DEFAULT_GENERATED_BUCKET = 'home-center-generated';
const GENERATED_ARTIFACT_BUCKET = process.env.HOME_CENTER_GENERATED_BUCKET || process.env.COMMAND_CENTER_GENERATED_BUCKET || DEFAULT_GENERATED_BUCKET;
const TEST_FAKE = process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE === '1';
const fakeObjects = globalThis.__homeCenterArtifactBucketObjects || (globalThis.__homeCenterArtifactBucketObjects = new Map());
let storageClient = null;

function storage() {
  if (!storageClient) {
    const {Storage} = require('@google-cloud/storage');
    storageClient = new Storage();
  }
  return storageClient;
}

function sha256Hex(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

function safeText(value, max = 240) {
  const text = typeof value === 'string' ? value.trim() : value === undefined || value === null ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}

function safeSegment(value, fallback = 'artifact') {
  return safeText(value, 120).replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 120) || fallback;
}

function timestampId(value = new Date()) {
  return value.toISOString().replace(/[:.]/g, '').replace('T', 't').replace('Z', 'z');
}

function boolMetadata(value) {
  return value === true || value === 'true' ? 'true' : 'false';
}

function metadataValue(value, max = 500) {
  if (value === undefined || value === null) return '';
  if (typeof value === 'boolean') return boolMetadata(value);
  return safeText(String(value), max);
}

function artifactPrefix({owner = 'drew', stage = 'temp', artifactType = '', mimeType = '', name = ''} = {}) {
  const ownerSegment = safeSegment(owner, 'drew').toLowerCase();
  const stageSegment = safeSegment(stage, 'temp').toLowerCase();
  const type = safeSegment(artifactType, 'artifact').toLowerCase();
  const lowerName = String(name || '').toLowerCase();
  if (/^audio\//.test(mimeType) || ['audio', 'narration', 'voice-test', 'voice-tests', 'characters', 'final'].includes(type) || ['narration', 'voice-test', 'voice-tests', 'characters', 'final'].includes(stageSegment)) {
    const audioStage = stageSegment === 'voice-test' ? 'voice-tests' : stageSegment;
    if (['narration', 'voice-tests', 'characters', 'final'].includes(audioStage)) return `audio/${ownerSegment}/${audioStage}`;
    return `audio/${ownerSegment}/${audioStage || 'shared'}`;
  }
  if (type === 'contact_sheet' || type === 'contact-sheet' || /contact-sheet/.test(lowerName)) return 'renders/contact-sheets';
  if (type === 'gif' || type === 'looping_gif' || lowerName.endsWith('.gif')) return 'renders/gifs';
  if (type === 'render' || type === 'rendered_frames' || type === 'frame' || type === 'blender') return 'renders/blender';
  if (type === 'image' || /^image\//.test(mimeType)) return 'images';
  if (type === 'glb' || lowerName.endsWith('.glb')) return 'glb';
  if (type === 'video' || /^video\//.test(mimeType)) return 'video';
  if (type === 'log' || type === 'logs' || lowerName.endsWith('.log') || lowerName.endsWith('.txt')) return 'logs';
  if (stageSegment === 'temp' || type === 'temp') return 'temp';
  return 'temp';
}

function artifactMetadata({owner = 'drew', ownerEmail = '', sharedWith = '', project = 'home-center', stage = 'temp', engine = 'home-center', createdBy = 'home-center', jobId = '', commit = '', timestamp = '', approved = false, executionAuthorized = false, authorizationState = '', humanAcceptance = 'unreviewed', requestId = '', sha256 = '', byteCount = 0, artifactType = '', mimeType = ''} = {}) {
  return {
    owner: metadataValue(owner, 120) || 'drew',
    ownerEmail: metadataValue(ownerEmail, 320),
    sharedWith: metadataValue(sharedWith, 4000),
    project: metadataValue(project, 160) || 'home-center',
    stage: metadataValue(stage, 120) || 'temp',
    engine: metadataValue(engine, 120) || 'home-center',
    createdBy: metadataValue(createdBy, 160) || 'home-center',
    jobId: metadataValue(jobId, 180),
    commit: metadataValue(commit, 80),
    timestamp: metadataValue(timestamp || new Date().toISOString(), 80),
    approved: boolMetadata(approved),
    executionAuthorized: boolMetadata(executionAuthorized),
    authorizationState: metadataValue(authorizationState, 80),
    humanAcceptance: metadataValue(humanAcceptance, 80) || 'unreviewed',
    requestId: metadataValue(requestId, 180),
    sha256: metadataValue(sha256, 80),
    byteCount: String(Number(byteCount) || 0),
    artifactType: metadataValue(artifactType, 120),
    mimeType: metadataValue(mimeType, 180),
  };
}

function parseGsRef(ref) {
  const match = String(ref || '').match(/^gs:\/\/([^/]+)\/(.+)$/i);
  if (!match) return null;
  return {bucket: match[1], object: match[2]};
}

async function saveObject({bucket, object, bytes, contentType, metadata}) {
  if (TEST_FAKE) {
    fakeObjects.set(`gs://${bucket}/${object}`, {bytes: Buffer.from(bytes), contentType, metadata: {...metadata}});
    return;
  }
  await storage().bucket(bucket).file(object).save(bytes, {resumable: false, metadata: {contentType, metadata}});
}

async function readObject(ref) {
  const parsed = parseGsRef(ref);
  if (!parsed) throw new Error('Invalid generated artifact ref: ' + ref);
  if (TEST_FAKE) {
    const stored = fakeObjects.get(`gs://${parsed.bucket}/${parsed.object}`);
    if (!stored) throw new Error('Generated artifact not found: ' + ref);
    return {bytes: Buffer.from(stored.bytes), bucket: parsed.bucket, object: parsed.object, contentType: stored.contentType || '', metadata: stored.metadata || {}};
  }
  const [bytes] = await storage().bucket(parsed.bucket).file(parsed.object).download();
  const [meta] = await storage().bucket(parsed.bucket).file(parsed.object).getMetadata();
  return {bytes, bucket: parsed.bucket, object: parsed.object, contentType: meta.contentType || '', metadata: meta.metadata || {}};
}


async function verifyGeneratedArtifact(ref, expected = {}) {
  const parsed = parseGsRef(ref);
  if (!parsed) throw new Error('Invalid generated artifact ref: ' + ref);
  const expectedSha256 = safeText(expected.sha256, 80).toLowerCase();
  const expectedByteCount = Number(expected.byteCount);
  if (TEST_FAKE) {
    const stored = fakeObjects.get('gs://' + parsed.bucket + '/' + parsed.object);
    if (!stored) throw new Error('Generated artifact not found: ' + ref);
    const byteCount = stored.bytes.length;
    const sha256 = sha256Hex(stored.bytes);
    if (Number.isFinite(expectedByteCount) && expectedByteCount >= 0 && byteCount !== expectedByteCount) throw new Error('Generated artifact byte count mismatch: ' + ref);
    if (expectedSha256 && sha256 !== expectedSha256) throw new Error('Generated artifact sha256 mismatch: ' + ref);
    return {ref, bucket: parsed.bucket, object: parsed.object, byteCount, sha256, contentType: stored.contentType || '', metadata: {...stored.metadata}, generation: 'test-generation'};
  }
  const file = storage().bucket(parsed.bucket).file(parsed.object);
  const [providerMetadata] = await file.getMetadata();
  const byteCount = Number(providerMetadata.size || 0);
  if (Number.isFinite(expectedByteCount) && expectedByteCount >= 0 && byteCount !== expectedByteCount) throw new Error('Generated artifact byte count mismatch: ' + ref);
  const digest = createHash('sha256');
  let streamedBytes = 0;
  await pipeline(file.createReadStream(), new Transform({
    transform(chunk, _encoding, callback) {
      streamedBytes += chunk.length;
      digest.update(chunk);
      callback();
    },
  }));
  const sha256 = digest.digest('hex');
  if (streamedBytes !== byteCount) throw new Error('Generated artifact stream length mismatch: ' + ref);
  if (expectedSha256 && sha256 !== expectedSha256) throw new Error('Generated artifact sha256 mismatch: ' + ref);
  return {ref, bucket: parsed.bucket, object: parsed.object, byteCount, sha256, contentType: providerMetadata.contentType || '', metadata: providerMetadata.metadata || {}, generation: safeText(providerMetadata.generation, 80), metageneration: safeText(providerMetadata.metageneration, 80)};
}

async function replaceGeneratedArtifactMetadata(ref, metadata = {}) {
  const parsed = parseGsRef(ref);
  if (!parsed) throw new Error('Invalid generated artifact ref: ' + ref);
  const cleanMetadata = Object.fromEntries(Object.entries(metadata || {}).map(([key, value]) => [key, metadataValue(value, 4000)]));
  if (TEST_FAKE) {
    const key = 'gs://' + parsed.bucket + '/' + parsed.object;
    const stored = fakeObjects.get(key);
    if (!stored) throw new Error('Generated artifact not found: ' + ref);
    stored.metadata = cleanMetadata;
    fakeObjects.set(key, stored);
    return {ref, generation: 'test-generation', metadata: {...cleanMetadata}};
  }
  const file = storage().bucket(parsed.bucket).file(parsed.object);
  const [before] = await file.getMetadata();
  const [after] = await file.setMetadata({metadata: cleanMetadata}, {preconditionOpts: {ifMetagenerationMatch: Number(before.metageneration || 0)}});
  if (safeText(after.generation, 80) !== safeText(before.generation, 80)) throw new Error('Generated artifact bytes changed while updating metadata: ' + ref);
  return {ref, generation: safeText(after.generation, 80), metageneration: safeText(after.metageneration, 80), metadata: after.metadata || cleanMetadata};
}

async function readGeneratedJsonObject(objectName, bucket = GENERATED_ARTIFACT_BUCKET) {
  const cleanObject = safeText(objectName, 1200).replace(/^\/+/, '');
  if (!cleanObject) throw new Error('Generated JSON object name is required.');
  if (TEST_FAKE) {
    const stored = fakeObjects.get('gs://' + bucket + '/' + cleanObject);
    if (!stored) return null;
    return {value: JSON.parse(stored.bytes.toString('utf8')), bytes: Buffer.from(stored.bytes), contentType: stored.contentType || '', metadata: {...stored.metadata}};
  }
  const file = storage().bucket(bucket).file(cleanObject);
  const [exists] = await file.exists();
  if (!exists) return null;
  const [bytes] = await file.download();
  const [providerMetadata] = await file.getMetadata();
  return {value: JSON.parse(bytes.toString('utf8')), bytes, contentType: providerMetadata.contentType || '', metadata: providerMetadata.metadata || {}, generation: safeText(providerMetadata.generation, 80)};
}

async function writeGeneratedJsonObject(objectName, value, {bucket = GENERATED_ARTIFACT_BUCKET, metadata = {}, ifAbsent = true} = {}) {
  const cleanObject = safeText(objectName, 1200).replace(/^\/+/, '');
  if (!cleanObject) throw new Error('Generated JSON object name is required.');
  const bytes = Buffer.from(JSON.stringify(value, null, 2), 'utf8');
  const cleanMetadata = Object.fromEntries(Object.entries(metadata || {}).map(([key, item]) => [key, metadataValue(item, 4000)]));
  if (TEST_FAKE) {
    const key = 'gs://' + bucket + '/' + cleanObject;
    if (ifAbsent && fakeObjects.has(key)) {
      const existing = fakeObjects.get(key);
      return {object: cleanObject, storageRef: key, byteCount: existing.bytes.length, sha256: sha256Hex(existing.bytes), reused: true};
    }
    fakeObjects.set(key, {bytes, contentType: 'application/json', metadata: cleanMetadata});
    return {object: cleanObject, storageRef: key, byteCount: bytes.length, sha256: sha256Hex(bytes), reused: false};
  }
  const file = storage().bucket(bucket).file(cleanObject);
  try {
    await file.save(bytes, {resumable: false, validation: 'crc32c', ...(ifAbsent ? {preconditionOpts: {ifGenerationMatch: 0}} : {}), metadata: {contentType: 'application/json', metadata: cleanMetadata}});
    return {object: cleanObject, storageRef: 'gs://' + bucket + '/' + cleanObject, byteCount: bytes.length, sha256: sha256Hex(bytes), reused: false};
  } catch (err) {
    if (!ifAbsent || Number(err && err.code) !== 412) throw err;
    const existing = await readGeneratedJsonObject(cleanObject, bucket);
    return {object: cleanObject, storageRef: 'gs://' + bucket + '/' + cleanObject, byteCount: existing.bytes.length, sha256: sha256Hex(existing.bytes), reused: true};
  }
}
async function uploadGeneratedArtifact({bucket = GENERATED_ARTIFACT_BUCKET, bytes, name, mimeType = 'application/octet-stream', owner = 'drew', ownerEmail = '', sharedWith = '', project = 'home-center', stage = 'temp', engine = 'home-center', createdBy = 'home-center', jobId = '', commit = '', approved = false, executionAuthorized = false, authorizationState = '', humanAcceptance = 'unreviewed', requestId = '', artifactType = 'artifact', prefix = ''} = {}) {
  if (!Buffer.isBuffer(bytes)) bytes = Buffer.from(bytes || '');
  const sha256 = sha256Hex(bytes);
  const byteCount = bytes.length;
  const cleanName = safeSegment(name, 'artifact.bin');
  const basePrefix = prefix ? safeText(prefix, 500).replace(/^\/+|\/+$/g, '') : artifactPrefix({owner, stage, artifactType, mimeType, name});
  const object = `${basePrefix}/${timestampId()}-${requestId ? safeSegment(requestId, 'request') + '-' : ''}${sha256.slice(0, 16)}-${cleanName}`;
  const metadata = artifactMetadata({owner, ownerEmail, sharedWith, project, stage, engine, createdBy, jobId, commit, timestamp: new Date().toISOString(), approved, executionAuthorized, authorizationState, humanAcceptance, requestId, sha256, byteCount, artifactType, mimeType});
  await saveObject({bucket, object, bytes, contentType: mimeType, metadata});
  const ref = `gs://${bucket}/${object}`;
  const readback = await readObject(ref);
  const readbackSha256 = sha256Hex(readback.bytes);
  if (readback.bytes.length !== byteCount || readbackSha256 !== sha256) {
    const err = new Error('Generated artifact GCS readback verification failed for ' + cleanName + '.');
    err.status = 502;
    err.failureKind = 'artifact_bucket_readback_failed';
    throw err;
  }
  return {name: cleanName, mimeType, bucket, object, storageRef: ref, durableRef: ref, byteCount, sha256, readbackByteCount: readback.bytes.length, readbackSha256, metadata, verified: true, primaryStore: 'gcs'};
}

async function publishGeneratedArtifactToDrive({google, auth, parentFolderId, artifact, bytes}) {
  if (!google || !auth) return null;
  const payload = Buffer.isBuffer(bytes) ? bytes : (await readObject(artifact.storageRef || artifact.durableRef)).bytes;
  const drive = google.drive({version: 'v3', auth});
  const created = await drive.files.create({
    requestBody: {name: artifact.name, mimeType: artifact.mimeType, ...(parentFolderId ? {parents: [parentFolderId]} : {})},
    media: {mimeType: artifact.mimeType, body: Readable.from([payload])},
    fields: 'id,name,mimeType,webViewLink,parents,size',
    supportsAllDrives: true,
  });
  const metadata = created.data || {};
  const fileId = metadata.id || '';
  const readback = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
  const readbackBuffer = Buffer.isBuffer(readback.data) ? readback.data : Buffer.from(readback.data);
  const readbackSha256 = sha256Hex(readbackBuffer);
  if (readbackBuffer.length !== artifact.byteCount || readbackSha256 !== artifact.sha256) {
    const err = new Error('Drive publish readback verification failed for ' + artifact.name + '.');
    err.status = 502;
    err.failureKind = 'drive_publish_readback_failed';
    throw err;
  }
  return {fileId, id: fileId, durableRef: 'drive://' + fileId, webViewLink: metadata.webViewLink || '', parentFolderId: ((metadata.parents || [])[0]) || parentFolderId || '', readbackByteCount: readbackBuffer.length, readbackSha256, chatGptFileRef: {type: 'resource_link', uri: 'drive://' + fileId, name: artifact.name, mimeType: artifact.mimeType, size: artifact.byteCount}};
}

async function inspectGeneratedArtifact(ref) {
  const parsed = parseGsRef(ref);
  if (!parsed) return null;
  const item = await readObject(ref);
  return {durableRef: ref, bucket: item.bucket, object: item.object, name: item.object.split('/').pop() || '', mimeType: item.contentType || item.metadata.mimeType || '', byteCount: item.bytes.length, sha256: sha256Hex(item.bytes), metadata: item.metadata || {}, bytes: item.bytes};
}

module.exports = {DEFAULT_GENERATED_BUCKET, GENERATED_ARTIFACT_BUCKET, artifactPrefix, artifactMetadata, parseGsRef, uploadGeneratedArtifact, publishGeneratedArtifactToDrive, inspectGeneratedArtifact, verifyGeneratedArtifact, replaceGeneratedArtifactMetadata, readGeneratedJsonObject, writeGeneratedJsonObject, sha256Hex};
