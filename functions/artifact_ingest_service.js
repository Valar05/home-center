'use strict';

const {createHash} = require('node:crypto');
const {boundedMap, sha256Json, LEGACY_BASE64_MAX_BYTES, ARTIFACT_TRANSPORT_VERSION} = require('./artifact_transport');

const ARTIFACT_BUCKET = process.env.HOME_CENTER_ARTIFACT_BUCKET || 'home-center-generated';
const ARTIFACT_INGEST_MAX_BYTES = Number(process.env.HOME_CENTER_ARTIFACT_INGEST_MAX_BYTES || 256 * 1024 * 1024);
const ARTIFACT_CHUNK_MAX_BYTES = Math.min(Number(process.env.HOME_CENTER_ARTIFACT_CHUNK_MAX_BYTES || LEGACY_BASE64_MAX_BYTES), LEGACY_BASE64_MAX_BYTES);
const ARTIFACT_RESUMABLE_CHUNK_MAX_BYTES = Number(process.env.HOME_CENTER_ARTIFACT_RESUMABLE_CHUNK_MAX_BYTES || 16 * 1024 * 1024);
let artifactStorage = null;

function defaultStorage() {
  if (!artifactStorage) {
    const {Storage} = require('@google-cloud/storage');
    artifactStorage = new Storage();
  }
  return artifactStorage;
}

function text(value, max = 1200) {
  const clean = typeof value === 'string' ? value.trim() : '';
  return clean.length > max ? clean.slice(0, max) : clean;
}

function fail(message, status = 400, code = 'artifact_ingest_invalid') {
  const err = new Error(message);
  err.status = status;
  err.code = code;
  return err;
}

function slug(value, fallback, max = 180) {
  const clean = text(value, max)
    .toLowerCase()
    .replace(/[^a-z0-9._@+-]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return clean || fallback;
}

function fileName(value) {
  const clean = text(value, 240)
    .replace(/\\/g, '/')
    .split('/')
    .pop()
    .replace(/[\u0000-\u001f\u007f]/g, '')
    .trim();
  return clean || 'artifact.bin';
}

function mimeType(value) {
  const clean = text(value, 160).toLowerCase();
  return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(clean) ? clean : 'application/octet-stream';
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function expectedSha(value, field = 'expectedSha256') {
  const clean = text(value, 128).toLowerCase();
  if (clean && !/^[a-f0-9]{64}$/.test(clean)) throw fail(field + ' must be a 64-character hexadecimal SHA-256 digest.');
  return clean;
}

function requestId(value) {
  const clean = slug(value, '', 180);
  if (!clean) throw fail('requestId is required.');
  return clean;
}

function ownerEmail(user) {
  const email = text(user && user.email, 320).toLowerCase();
  if (!email) throw fail('An authenticated owner email is required.', 401, 'artifact_ingest_owner_required');
  return email;
}

function normalizeProvenance(value) {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const out = {};
  for (const key of [
    'sourceId',
    'sourceName',
    'sourceSha256',
    'sourceLibraryFileId',
    'sourceAuthority',
    'sourceStartSeconds',
    'sourceEndSeconds',
    'notes',
  ]) {
    if (source[key] === undefined || source[key] === null || source[key] === '') continue;
    out[key] = typeof source[key] === 'number' ? source[key] : text(String(source[key]), key === 'notes' ? 2000 : 500);
  }
  if (out.sourceSha256) expectedSha(out.sourceSha256, 'provenance.sourceSha256');
  return out;
}

function normalizeIdentity(user, args = {}) {
  const owner = ownerEmail(user);
  const id = slug(args.artifactId, '', 180);
  if (!id) throw fail('artifactId is required.');
  const kind = slug(args.artifactKind, 'artifact', 120);
  const project = slug(args.project, 'unclassified', 120);
  const state = text(args.lifecycleState || 'proposed', 40).toLowerCase();
  if (state !== 'proposed') {
    throw fail('New artifact ingress is lifecycleState=proposed. Acceptance is a separate human promotion.', 409, 'artifact_lifecycle_promotion_required');
  }
  const name = fileName(args.name || args.fileName || 'artifact.bin');
  const type = mimeType(args.mimeType);
  const ownerSegment = slug(owner, 'owner', 320);
  const objectName = ['rotoscoping', ownerSegment, kind, id, name].join('/');
  return {
    requestId: requestId(args.requestId || args.idempotencyKey),
    artifactId: id,
    artifactKind: kind,
    project,
    lifecycleState: state,
    name,
    mimeType: type,
    ownerEmail: owner,
    ownerSegment,
    objectName,
    expectedSha256: expectedSha(args.expectedSha256),
    expectedByteCount: args.expectedByteCount === undefined ? null : Number(args.expectedByteCount),
    provenance: normalizeProvenance(args.provenance),
    callerNote: text(args.callerNote, 800),
  };
}

function assertExpected(identity, bytes) {
  if (!Buffer.isBuffer(bytes)) bytes = Buffer.from(bytes);
  if (!bytes.length) throw fail('Artifact file is empty.', 400, 'artifact_ingest_empty');
  if (bytes.length > ARTIFACT_INGEST_MAX_BYTES) {
    throw fail('Artifact exceeds the configured ingest ceiling.', 413, 'artifact_ingest_too_large');
  }
  if (identity.expectedByteCount !== null &&
      (!Number.isSafeInteger(identity.expectedByteCount) || identity.expectedByteCount !== bytes.length)) {
    throw fail('Artifact byte count did not match expectedByteCount.', 409, 'artifact_ingest_byte_count_mismatch');
  }
  const digest = sha256(bytes);
  if (identity.expectedSha256 && identity.expectedSha256 !== digest) {
    throw fail('Artifact SHA-256 did not match expectedSha256.', 409, 'artifact_ingest_sha256_mismatch');
  }
  return {bytes, byteCount: bytes.length, sha256: digest};
}

async function readFile(file) {
  const [bytes] = await file.download();
  const buffer = Buffer.from(bytes);
  return {bytes: buffer, byteCount: buffer.length, sha256: sha256(buffer)};
}

async function digestFile(file, range = null) {
  if (typeof file.createReadStream !== 'function') return readFile(file);
  const hash = createHash('sha256');
  let count = 0;
  const options = range ? {start: range.start, end: range.end} : {};
  for await (const chunk of file.createReadStream(options)) { const bytes = Buffer.from(chunk); hash.update(bytes); count += bytes.length; }
  return {byteCount: count, sha256: hash.digest('hex')};
}

function assertExpectedDigest(identity, digest) {
  if (!digest || !Number.isSafeInteger(digest.byteCount) || digest.byteCount < 1) throw fail('Artifact file is empty.', 400, 'artifact_ingest_empty');
  if (identity.expectedByteCount !== null && identity.expectedByteCount !== digest.byteCount) throw fail('Artifact byte count did not match expectedByteCount.', 409, 'artifact_ingest_byte_count_mismatch');
  if (identity.expectedSha256 && identity.expectedSha256 !== digest.sha256) throw fail('Artifact SHA-256 did not match expectedSha256.', 409, 'artifact_ingest_sha256_mismatch');
  return digest;
}

async function saveImmutableJson(bucket, objectName, value, sameIdentity) {
  const file = bucket.file(objectName);
  const payload = Buffer.from(JSON.stringify(value, null, 2) + '\n');
  try {
    await file.save(payload, {
      resumable: false,
      validation: false,
      contentType: 'application/json',
      preconditionOpts: {ifGenerationMatch: 0},
    });
    const readback = await readFile(file);
    if (readback.byteCount !== payload.length || readback.sha256 !== sha256(payload)) {
      throw fail('Immutable artifact index failed readback verification.', 502, 'artifact_index_readback_mismatch');
    }
    return {objectName, storageRef: 'gs://' + bucket.name + '/' + objectName, reused: false, ...readback};
  } catch (err) {
    if (![409, 412].includes(Number(err && err.code)) && !/condition|already exists/i.test(String(err && err.message))) throw err;
    const existing = JSON.parse((await readFile(file)).bytes.toString('utf8'));
    if (!sameIdentity(existing, value)) {
      throw fail('Immutable artifact index already exists with different identity.', 409, 'artifact_index_conflict');
    }
    const readback = await readFile(file);
    return {objectName, storageRef: 'gs://' + bucket.name + '/' + objectName, reused: true, ...readback};
  }
}

function sameArtifact(existing, expected) {
  return text(existing && existing.artifactId, 180) === expected.artifactId &&
    text(existing && existing.destination && existing.destination.storageRef, 1400) === expected.destination.storageRef &&
    text(existing && existing.destination && existing.destination.sha256, 64).toLowerCase() === expected.destination.sha256 &&
    Number(existing && existing.destination && existing.destination.byteCount || 0) === expected.destination.byteCount &&
    text(existing && existing.lifecycleState, 40) === expected.lifecycleState;
}

async function writeCommandCenterReceipt(admin, manifest) {
  if (!admin || typeof admin.firestore !== 'function') return {recorded: false};
  const collection = admin.firestore().collection('commandCenterArtifactCatalog');
  const documentId = slug(manifest.ownerEmail, 'owner', 320) + '--' + manifest.artifactId;
  const ref = collection.doc(documentId);
  const snapshot = await ref.get();
  if (snapshot.exists) {
    const existing = snapshot.data() || {};
    if (!sameArtifact(existing, manifest)) {
      throw fail('Command Center already catalogs this artifactId with different immutable identity.', 409, 'command_center_artifact_conflict');
    }
    return {recorded: true, reused: true, documentId};
  }
  try {
    await ref.create(manifest);
  } catch (err) {
    if (![6, 409].includes(Number(err && err.code)) && !/already exists/i.test(String(err && err.message))) throw err;
    const raced = await ref.get();
    if (!raced.exists || !sameArtifact(raced.data() || {}, manifest)) {
      throw fail('Command Center artifact receipt raced with a different immutable identity.', 409, 'command_center_artifact_conflict');
    }
    return {recorded: true, reused: true, documentId};
  }
  const check = await ref.get();
  if (!check.exists || !sameArtifact(check.data() || {}, manifest)) {
    throw fail('Command Center artifact receipt failed readback verification.', 502, 'command_center_artifact_readback_mismatch');
  }
  return {recorded: true, reused: false, documentId};
}

function publicImmutableIndex(index) {
  return {
    objectName: index.objectName,
    storageRef: index.storageRef,
    reused: index.reused === true,
    byteCount: Number(index.byteCount || 0),
    sha256: text(index.sha256, 64).toLowerCase(),
  };
}

async function publishVerified({admin, storage = defaultStorage(), user, identity, verified, recordAudit = async () => {}}) {
  const bucket = storage.bucket(ARTIFACT_BUCKET);
  const destination = bucket.file(identity.objectName);
  let reused = false;
  try {
    const metadata = {
      contentType: identity.mimeType,
      metadata: {artifactId: identity.artifactId, artifactKind: identity.artifactKind, project: identity.project, ownerEmail: identity.ownerEmail, lifecycleState: identity.lifecycleState, requestId: identity.requestId, sha256: verified.sha256, byteCount: String(verified.byteCount), ingestStatus: 'verified'},
    };
    if (verified.sourceFile) await verified.sourceFile.copy(destination, {metadata, preconditionOpts: {ifGenerationMatch: 0}});
    else await destination.save(verified.bytes, {resumable: false, validation: false, contentType: identity.mimeType, metadata, preconditionOpts: {ifGenerationMatch: 0}});
  } catch (err) {
    if (![409, 412].includes(Number(err && err.code)) && !/condition|already exists/i.test(String(err && err.message))) throw err;
    reused = true;
  }
  const readback = await digestFile(destination);
  if (readback.byteCount !== verified.byteCount || readback.sha256 !== verified.sha256) {
    throw fail('Canonical GCS artifact failed byte-count/SHA-256 readback verification.', 502, 'artifact_ingest_readback_mismatch');
  }

  const storageRef = 'gs://' + ARTIFACT_BUCKET + '/' + identity.objectName;
  const manifest = {
    schemaVersion: 'home-center.artifact.v1',
    artifactId: identity.artifactId,
    artifactKind: identity.artifactKind,
    project: identity.project,
    lifecycleState: identity.lifecycleState,
    ownerEmail: identity.ownerEmail,
    createdAt: new Date().toISOString(),
    requestId: identity.requestId,
    source: {
      transport: 'chatgpt-work-mode',
      name: identity.name,
      mimeType: identity.mimeType,
      provenance: identity.provenance,
    },
    destination: {
      bucket: ARTIFACT_BUCKET,
      objectName: identity.objectName,
      storageRef,
      byteCount: readback.byteCount,
      sha256: readback.sha256,
      browserUrl: 'https://storage.cloud.google.com/' + ARTIFACT_BUCKET + '/' + identity.objectName.split('/').map(encodeURIComponent).join('/'),
    },
    verification: {
      verified: true,
      inputByteCount: verified.byteCount,
      inputSha256: verified.sha256,
      readbackByteCount: readback.byteCount,
      readbackSha256: readback.sha256,
      byteCountMatch: true,
      sha256Match: true,
    },
    retention: {
      canonical: true,
      immutable: true,
      sourceDeleted: false,
      promotionRequiredForAcceptance: true,
    },
  };
  const base = ['indexes', 'artifacts', 'v1'];
  const manifestName = identity.objectName.replace(/\/[^/]+$/, '/artifact-manifest.json');
  const indexes = {
    manifest: publicImmutableIndex(await saveImmutableJson(bucket, manifestName, manifest, sameArtifact)),
    byId: publicImmutableIndex(await saveImmutableJson(bucket, [...base, 'by-id', identity.ownerSegment, identity.artifactId + '.json'].join('/'), manifest, sameArtifact)),
    bySha256: publicImmutableIndex(await saveImmutableJson(bucket, [...base, 'by-sha256', verified.sha256 + '.json'].join('/'), manifest, sameArtifact)),
    catalog: publicImmutableIndex(await saveImmutableJson(bucket, [...base, 'catalog', identity.ownerSegment, identity.project, identity.artifactKind, identity.lifecycleState, identity.artifactId + '.json'].join('/'), manifest, sameArtifact)),
    request: publicImmutableIndex(await saveImmutableJson(bucket, [...base, 'requests', identity.ownerSegment, identity.requestId + '.json'].join('/'), manifest, sameArtifact)),
  };
  const commandCenter = await writeCommandCenterReceipt(admin, manifest);
  await recordAudit(admin, user, 'storage.ingest_artifact', identity.artifactId,
    'Published verified proposed artifact ' + storageRef + ' and recorded immutable catalog receipts.', identity.requestId);
  return {
    ok: true,
    verified: true,
    reused,
    requestId: identity.requestId,
    artifactId: identity.artifactId,
    lifecycleState: identity.lifecycleState,
    durableRef: 'home-center://artifacts/' + identity.artifactId,
    destination: manifest.destination,
    verification: manifest.verification,
    provenance: manifest.source.provenance,
    indexes,
    commandCenter,
  };
}

async function ingestArtifactUploadOperation({admin, storage = defaultStorage(), user, args = {}, recordAudit}) {
  const uploaded = args.file;
  if (!uploaded || typeof uploaded.arrayBuffer !== 'function') {
    throw fail('file must be a top-level uploaded MCP file.', 400, 'artifact_ingest_file_required');
  }
  const identity = normalizeIdentity(user, {
    ...args,
    name: args.name || uploaded.name,
    mimeType: args.mimeType || uploaded.type,
  });
  const declared = Number(uploaded.size || 0);
  if (declared > ARTIFACT_INGEST_MAX_BYTES) throw fail('Artifact exceeds the configured ingest ceiling.', 413, 'artifact_ingest_too_large');
  const verified = assertExpected(identity, Buffer.from(await uploaded.arrayBuffer()));
  return publishVerified({admin, storage, user, identity, verified, recordAudit});
}

function sessionPrefix(identity) {
  return ['temp', 'artifact-ingest', identity.ownerSegment, identity.requestId].join('/');
}

async function beginArtifactIngestOperation({admin, user, args = {}}) {
  if (args.approved !== true) throw fail('storage.artifact.begin requires approved=true.', 409, 'artifact_ingest_not_approved');
  const identity = normalizeIdentity(user, args);
  if (!Number.isSafeInteger(identity.expectedByteCount) || identity.expectedByteCount < 1 || !identity.expectedSha256) {
    throw fail('Chunked ingest requires expectedByteCount and expectedSha256.');
  }
  const receipt = {
    schemaVersion: 'home-center.artifact-ingest-session.v1',
    status: 'open',
    ...identity,
    sessionPrefix: sessionPrefix(identity),
    chunkMaxBytes: ARTIFACT_CHUNK_MAX_BYTES,
  };
  if (admin && typeof admin.firestore === 'function') {
    const ref = admin.firestore().collection('artifactIngestSessions').doc(identity.requestId);
    const existing = await ref.get();
    if (existing.exists) {
      const data = existing.data() || {};
      if (JSON.stringify({...data, openedAt: undefined}) !== JSON.stringify({...receipt, openedAt: undefined})) {
        throw fail('requestId is already bound to a different artifact ingest session.', 409, 'artifact_ingest_session_conflict');
      }
      return {...data, reused: true};
    }
    await ref.create({...receipt, openedAt: new Date().toISOString()});
  }
  return {...receipt, reused: false};
}

async function appendArtifactChunkOperation({storage = defaultStorage(), user, args = {}}) {
  if (args.approved !== true) throw fail('storage.artifact.append_chunk requires approved=true.', 409, 'artifact_ingest_not_approved');
  const identity = normalizeIdentity(user, args);
  const index = Number(args.chunkIndex);
  if (!Number.isSafeInteger(index) || index < 0 || index > 99999) throw fail('chunkIndex must be a non-negative safe integer.');
  const encoded = text(args.chunkBase64, ARTIFACT_CHUNK_MAX_BYTES * 2);
  if (!encoded) throw fail('chunkBase64 is required.');
  const bytes = Buffer.from(encoded, 'base64');
  if (!bytes.length || bytes.length > ARTIFACT_CHUNK_MAX_BYTES) throw fail('Chunk is empty or exceeds chunkMaxBytes.', 413, 'artifact_ingest_chunk_too_large');
  const digest = sha256(bytes);
  const expected = expectedSha(args.chunkSha256, 'chunkSha256');
  if (expected && expected !== digest) throw fail('Chunk SHA-256 mismatch.', 409, 'artifact_ingest_chunk_sha256_mismatch');
  const bucket = storage.bucket(ARTIFACT_BUCKET);
  const objectName = sessionPrefix(identity) + '/chunks/' + String(index).padStart(5, '0') + '.part';
  const file = bucket.file(objectName);
  let reused = false;
  try {
    await file.save(bytes, {
      resumable: false,
      validation: false,
      contentType: 'application/octet-stream',
      metadata: {metadata: {requestId: identity.requestId, chunkIndex: String(index), sha256: digest}},
      preconditionOpts: {ifGenerationMatch: 0},
    });
  } catch (err) {
    if (![409, 412].includes(Number(err && err.code)) && !/condition|already exists/i.test(String(err && err.message))) throw err;
    reused = true;
  }
  const readback = await readFile(file);
  if (readback.byteCount !== bytes.length || readback.sha256 !== digest) throw fail('Chunk readback verification failed.', 502, 'artifact_ingest_chunk_readback_mismatch');
  return {ok: true, requestId: identity.requestId, chunkIndex: index, objectName, byteCount: bytes.length, sha256: digest, verified: true, reused};
}

async function composeArtifactChunks(bucket, chunks, prefix, staging) {
  let level = 0;
  let current = chunks;
  const intermediates = [];
  while (current.length > 32) {
    const next = [];
    for (let start = 0; start < current.length; start += 32) {
      const group = current.slice(start, start + 32);
      const part = bucket.file(prefix + '/compose/level-' + String(level).padStart(2, '0') + '-' + String(start / 32).padStart(3, '0') + '.part');
      if (group.length === 1) {
        await group[0].copy(part, {preconditionOpts: {ifGenerationMatch: 0}});
      } else {
        await bucket.combine(group, part, {preconditionOpts: {ifGenerationMatch: 0}});
      }
      const readback = await readFile(part);
      if (!readback.byteCount) throw fail('Intermediate artifact composition was empty.', 502, 'artifact_ingest_compose_empty');
      intermediates.push(part);
      next.push(part);
    }
    current = next;
    level += 1;
  }
  if (current.length === 1) {
    await current[0].copy(staging, {preconditionOpts: {ifGenerationMatch: 0}});
  } else {
    await bucket.combine(current, staging, {preconditionOpts: {ifGenerationMatch: 0}});
  }
  return intermediates;
}

async function commitArtifactIngestOperation({admin, storage = defaultStorage(), user, args = {}, recordAudit}) {
  if (args.approved !== true) throw fail('storage.artifact.commit requires approved=true.', 409, 'artifact_ingest_not_approved');
  const identity = normalizeIdentity(user, args);
  if (!Number.isSafeInteger(identity.expectedByteCount) || identity.expectedByteCount < 1 || !identity.expectedSha256) {
    throw fail('Chunked ingest commit requires expectedByteCount and expectedSha256.');
  }
  const expectedChunks = Number(args.expectedChunks);
  if (!Number.isSafeInteger(expectedChunks) || expectedChunks < 1 || expectedChunks > 128) {
    throw fail('expectedChunks must be between 1 and 128.');
  }
  const bucket = storage.bucket(ARTIFACT_BUCKET);
  const prefix = sessionPrefix(identity) + '/chunks/';
  const [listed] = await bucket.getFiles({prefix});
  const chunks = listed.filter((file) => file.name.endsWith('.part')).sort((a, b) => a.name.localeCompare(b.name));
  if (chunks.length !== expectedChunks) throw fail('Chunk inventory does not match expectedChunks.', 409, 'artifact_ingest_chunk_inventory_mismatch');
  chunks.forEach((file, index) => {
    const suffix = '/' + String(index).padStart(5, '0') + '.part';
    if (!file.name.endsWith(suffix)) throw fail('Chunk indexes are not contiguous from zero.', 409, 'artifact_ingest_chunk_order_mismatch');
  });
  const staging = bucket.file(sessionPrefix(identity) + '/assembled.part');
  let intermediates = [];
  try {
    intermediates = await composeArtifactChunks(bucket, chunks, sessionPrefix(identity), staging);
  } catch (err) {
    if (![409, 412].includes(Number(err && err.code)) && !/condition|already exists/i.test(String(err && err.message))) throw err;
  }
  const assembled = assertExpectedDigest(identity, await digestFile(staging));
  const verified = {...assembled, sourceFile: staging};
  const result = await publishVerified({admin, storage, user, identity, verified, recordAudit});
  await Promise.allSettled([...chunks, ...intermediates, staging].map((file) => file.delete({ignoreNotFound: true})));
  return {...result, transport: {kind: 'chunked-mcp-fallback', expectedChunks, stagedObjectsDisposed: true}};
}

function normalizeResumableChunks(args, identity) {
  const chunks = Array.isArray(args.chunks) ? args.chunks : [];
  if (!chunks.length || chunks.length > 128) throw fail('chunks must contain 1-128 independently hashed ranges.', 400, 'artifact_resumable_chunks_required');
  let offset = 0;
  return chunks.map((chunk, index) => {
    const item = chunk && typeof chunk === 'object' ? chunk : {};
    const byteCount = Number(item.byteCount);
    const start = Number(item.offset);
    if (Number(item.index) !== index || start !== offset || !Number.isSafeInteger(byteCount) || byteCount < 1 || byteCount > ARTIFACT_RESUMABLE_CHUNK_MAX_BYTES) throw fail('chunks must be contiguous, ordered, and within the configured chunk ceiling.', 400, 'artifact_resumable_chunk_manifest_invalid');
    const digest = expectedSha(item.sha256, 'chunks[' + index + '].sha256');
    if (!digest) throw fail('Every resumable chunk requires sha256.', 400, 'artifact_resumable_chunk_sha256_required');
    offset += byteCount;
    return {index, offset: start, byteCount, sha256: digest};
  }).map((chunk, index, all) => {
    if (index === all.length - 1 && chunk.offset + chunk.byteCount !== identity.expectedByteCount) throw fail('Chunk ranges do not total expectedByteCount.', 409, 'artifact_resumable_chunk_total_mismatch');
    return chunk;
  });
}

function resumableObjectName(identity) { return sessionPrefix(identity) + '/resumable-upload.part'; }
function resumableSessionRef(admin, requestIdValue) { return admin.firestore().collection('artifactTransportUploadSessions').doc(requestIdValue); }
function publicResumableReceipt(data, uploadUrl = '') {
  const out = {schemaVersion: ARTIFACT_TRANSPORT_VERSION, requestId: data.requestId, inputHash: data.inputHash, state: data.state, acceptedAt: data.acceptedAt, artifact: data.artifact, chunks: data.chunks, progress: data.progress || {verifiedChunks: 0, totalChunks: data.chunks.length, verifiedBytes: 0, totalBytes: data.artifact.byteLength}, statusResource: {operation: 'storage.artifact.resumable_status', requestId: data.requestId}, contractVersion: 'gcs-resumable-raw-binary-v1'};
  if (uploadUrl) out.uploadTarget = {method: 'PUT', url: uploadUrl, protocol: 'gcs-resumable', contentRangeRequired: true};
  return out;
}

async function beginResumableArtifactIngestOperation({admin, storage = defaultStorage(), user, args = {}}) {
  if (args.approved !== true) throw fail('storage.artifact.resumable_begin requires approved=true.', 409, 'artifact_ingest_not_approved');
  if (!admin || typeof admin.firestore !== 'function') throw fail('Durable resumable sessions require Firestore.', 503, 'artifact_resumable_store_required');
  const identity = normalizeIdentity(user, args);
  if (!Number.isSafeInteger(identity.expectedByteCount) || identity.expectedByteCount < 1 || !identity.expectedSha256) throw fail('Resumable ingest requires expectedByteCount and expectedSha256.');
  const chunks = normalizeResumableChunks(args, identity);
  const artifact = {sha256: identity.expectedSha256, byteLength: identity.expectedByteCount, mediaType: identity.mimeType, fileName: identity.name};
  const inputHash = sha256Json({artifact, chunks, ownerEmail: identity.ownerEmail, artifactId: identity.artifactId});
  const ref = resumableSessionRef(admin, identity.requestId); const existing = await ref.get();
  if (existing.exists) { const data=existing.data()||{}; if(data.inputHash!==inputHash) throw fail('requestId is already bound to different resumable inputs.',409,'artifact_resumable_idempotency_conflict'); return {...publicResumableReceipt(data, data.uploadUrl), attached:true}; }
  const file = storage.bucket(ARTIFACT_BUCKET).file(resumableObjectName(identity));
  if (typeof file.createResumableUpload !== 'function') throw fail('Storage adapter does not support native resumable upload sessions.', 501, 'artifact_resumable_unsupported');
  const [uploadUrl] = await file.createResumableUpload({metadata: {contentType: identity.mimeType, metadata: {requestId: identity.requestId, expectedSha256: identity.expectedSha256, expectedByteCount: String(identity.expectedByteCount), transportVersion: ARTIFACT_TRANSPORT_VERSION}}});
  const data={requestId:identity.requestId,inputHash,state:'staging',acceptedAt:new Date().toISOString(),ownerEmail:identity.ownerEmail,identity,artifact,chunks,objectName:resumableObjectName(identity),uploadUrl,progress:{verifiedChunks:0,totalChunks:chunks.length,verifiedBytes:0,totalBytes:identity.expectedByteCount}};
  await ref.create(data); return {...publicResumableReceipt(data, uploadUrl), attached:false};
}

async function loadResumableSession(admin, user, args) {
  const id=requestId(args.requestId); const ref=resumableSessionRef(admin,id); const snap=await ref.get(); if(!snap.exists) throw fail('Resumable artifact session not found.',404,'artifact_resumable_not_found'); const data=snap.data()||{};
  if (data.ownerEmail !== ownerEmail(user)) throw fail('Resumable artifact session is not owned by this caller.',403,'artifact_resumable_forbidden'); return {ref,data};
}

async function resumableArtifactStatusOperation({admin, storage=defaultStorage(), user, args={}}) {
  const {data}=await loadResumableSession(admin,user,args); const file=storage.bucket(ARTIFACT_BUCKET).file(data.objectName); let progress=data.progress; let state=data.state;
  try { const digest=await digestFile(file); if(digest.byteCount===data.artifact.byteLength) {state='uploaded'; progress={...progress,uploadedBytes:digest.byteCount};} } catch (_err) {}
  return {...publicResumableReceipt({...data,state,progress}), attached:true};
}

async function resumeResumableArtifactIngestOperation({admin,user,args={}}) { const {data}=await loadResumableSession(admin,user,args); if(!data.uploadUrl) throw fail('Resumable upload target has expired and must be restarted.',410,'artifact_resumable_target_expired'); return {...publicResumableReceipt(data,data.uploadUrl),attached:true}; }

async function commitResumableArtifactIngestOperation({admin,storage=defaultStorage(),user,args={},recordAudit}) {
  if(args.approved!==true) throw fail('storage.artifact.resumable_commit requires approved=true.',409,'artifact_ingest_not_approved'); const {ref,data}=await loadResumableSession(admin,user,args); const file=storage.bucket(ARTIFACT_BUCKET).file(data.objectName);
  const verifiedChunks=await boundedMap(data.chunks,4,async(chunk)=>{const digest=await digestFile(file,{start:chunk.offset,end:chunk.offset+chunk.byteCount-1}); if(digest.byteCount!==chunk.byteCount) throw fail('Resumable chunk byte length mismatch at index '+chunk.index+'.',409,'artifact_resumable_chunk_length_mismatch'); if(digest.sha256!==chunk.sha256) throw fail('Resumable chunk SHA-256 mismatch at index '+chunk.index+'.',409,'artifact_resumable_chunk_sha256_mismatch'); return {...chunk,verified:true};});
  const whole=assertExpectedDigest(data.identity,await digestFile(file)); await ref.set({...data,state:'ready',progress:{verifiedChunks:verifiedChunks.length,totalChunks:verifiedChunks.length,verifiedBytes:whole.byteCount,totalBytes:whole.byteCount},verifiedAt:new Date().toISOString()});
  const result=await publishVerified({admin,storage,user,identity:data.identity,verified:{...whole,sourceFile:file},recordAudit}); await ref.set({...data,uploadUrl:'',state:'completed',progress:{verifiedChunks:verifiedChunks.length,totalChunks:verifiedChunks.length,verifiedBytes:whole.byteCount,totalBytes:whole.byteCount},result:{durableRef:result.durableRef,destination:result.destination},completedAt:new Date().toISOString()});
  await file.delete({ignoreNotFound:true}); return {...result,transport:{kind:'gcs-resumable-raw-binary-v1',verifiedChunks:verifiedChunks.length,transferredOutsideMcpJson:true}};
}

async function abortArtifactIngestOperation({admin, storage = defaultStorage(), user, args = {}, recordAudit = async () => {}}) {
  if (args.approved !== true) throw fail('storage.artifact.abort requires approved=true.', 409, 'artifact_ingest_not_approved');
  const identity = normalizeIdentity(user, args);
  const bucket = storage.bucket(ARTIFACT_BUCKET);
  const prefix = sessionPrefix(identity) + '/';
  const [files] = await bucket.getFiles({prefix});
  await Promise.all(files.map((file) => file.delete({ignoreNotFound: true})));
  if (admin && typeof admin.firestore === 'function') {
    const ref = admin.firestore().collection('artifactIngestSessions').doc(identity.requestId);
    const snapshot = await ref.get();
    if (snapshot.exists && typeof ref.set === 'function') {
      await ref.set({...snapshot.data(), status: 'aborted', abortedAt: new Date().toISOString(), disposedObjectCount: files.length});
    }
  }
  await recordAudit(admin, user, 'storage.artifact.abort', identity.artifactId,
    'Disposed ' + files.length + ' reproducible staging object(s) for failed artifact session ' + identity.requestId + '.', identity.requestId + '-abort');
  return {ok: true, aborted: true, requestId: identity.requestId, artifactId: identity.artifactId, disposedObjectCount: files.length, canonicalArtifactMutated: false};
}

async function readArtifactOperation({storage = defaultStorage(), user, args = {}}) {
  const ownerSegment = slug(ownerEmail(user), 'owner', 320);
  const artifactId = slug(args.artifactId, '', 180);
  if (!artifactId) throw fail('artifactId is required.');
  const file = storage.bucket(ARTIFACT_BUCKET).file(['indexes', 'artifacts', 'v1', 'by-id', ownerSegment, artifactId + '.json'].join('/'));
  const manifest = JSON.parse((await readFile(file)).bytes.toString('utf8'));
  return {ok: true, manifest};
}

async function findArtifactBySha256Operation({storage = defaultStorage(), args = {}}) {
  const digest = expectedSha(args.sha256, 'sha256');
  if (!digest) throw fail('sha256 is required.');
  const file = storage.bucket(ARTIFACT_BUCKET).file(['indexes', 'artifacts', 'v1', 'by-sha256', digest + '.json'].join('/'));
  const manifest = JSON.parse((await readFile(file)).bytes.toString('utf8'));
  return {ok: true, manifest};
}

function artifactOperationEntries() {
  return {
    'artifact_transport.preflight': {
      summary: 'Resolve and validate a versioned content-addressed artifact envelope before submission.',
      write: false,
      requiresRequestId: true,
      input: {requestId: 'string', artifacts: 'artifact-reference.v1 array', consumer: 'supported/direct location kinds', concurrency: 'integer 1-8'},
    },
    'artifact_transport.status': {
      summary: 'Read one bounded artifact transport preflight receipt by requestId.',
      write: false,
      requiresRequestId: true,
      input: {requestId: 'string'},
    },
    'storage.artifact.resumable_begin': {summary: 'Create a native GCS resumable raw-binary upload target with hash-bound chunk ranges.', write: true, requiresRequestId: true, input: {approved: 'must be true', requestId: 'string', artifactId: 'string', artifactKind: 'string', project: 'string', name: 'string', mimeType: 'string', expectedByteCount: 'integer', expectedSha256: 'hex', chunks: 'ordered index/offset/byteCount/sha256 array'}},
    'storage.artifact.resumable_status': {summary: 'Read bounded progress for a resumable artifact session without exposing its private upload URL.', write: false, requiresRequestId: true, input: {requestId: 'string'}},
    'storage.artifact.resumable_resume': {summary: 'Return the private raw-binary upload target to the authenticated session owner.', write: false, requiresRequestId: true, input: {requestId: 'string'}},
    'storage.artifact.resumable_commit': {summary: 'Range-hash every chunk, stream-hash the whole artifact, and publish by server-side copy.', write: true, requiresRequestId: true, input: {approved: 'must be true', requestId: 'string'}},
    'storage.artifact.begin': {
      summary: 'Begin a verified chunked artifact upload session for connector-refresh fallback.',
      write: true,
      requiresRequestId: true,
      input: {approved: 'must be true', requestId: 'string', artifactId: 'string', artifactKind: 'string', project: 'string', name: 'string', mimeType: 'string', expectedByteCount: 'integer', expectedSha256: 'hex', provenance: 'object'},
    },
    'storage.artifact.append_chunk': {
      summary: 'Deprecated small-file compatibility only: append one Base64 chunk no larger than 64 KiB.',
      write: true,
      requiresRequestId: true,
      input: {approved: 'must be true', requestId: 'string', artifactId: 'string', artifactKind: 'string', project: 'string', name: 'string', mimeType: 'string', chunkIndex: 'integer', chunkBase64: 'string', chunkSha256: 'hex'},
    },
    'storage.artifact.commit': {
      summary: 'Compose, verify, catalog, and commit a chunked artifact upload.',
      write: true,
      requiresRequestId: true,
      input: {approved: 'must be true', requestId: 'string', artifactId: 'string', artifactKind: 'string', project: 'string', name: 'string', mimeType: 'string', expectedByteCount: 'integer', expectedSha256: 'hex', expectedChunks: 'integer 1-128', provenance: 'object'},
    },
    'storage.artifact.abort': {
      summary: 'Dispose only reproducible staging objects for a failed artifact upload session.',
      write: true,
      requiresRequestId: true,
      input: {approved: 'must be true', requestId: 'string', artifactId: 'string', artifactKind: 'string', project: 'string', name: 'string', mimeType: 'string'},
    },
    'storage.artifact.get': {
      summary: 'Read one immutable artifact manifest by artifactId.',
      write: false,
      input: {artifactId: 'string'},
    },
    'storage.artifact.find_by_sha256': {
      summary: 'Read one immutable artifact manifest by SHA-256.',
      write: false,
      input: {sha256: 'hex'},
    },
  };
}

module.exports = {
  ARTIFACT_BUCKET,
  ARTIFACT_INGEST_MAX_BYTES,
  ARTIFACT_CHUNK_MAX_BYTES,
  ARTIFACT_RESUMABLE_CHUNK_MAX_BYTES,
  artifactOperationEntries,
  ingestArtifactUploadOperation,
  beginArtifactIngestOperation,
  beginResumableArtifactIngestOperation,
  resumableArtifactStatusOperation,
  resumeResumableArtifactIngestOperation,
  commitResumableArtifactIngestOperation,
  appendArtifactChunkOperation,
  commitArtifactIngestOperation,
  abortArtifactIngestOperation,
  readArtifactOperation,
  findArtifactBySha256Operation,
  normalizeIdentity,
  assertExpected,
};
