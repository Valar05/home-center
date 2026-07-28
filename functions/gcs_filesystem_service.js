'use strict';

const {createHash} = require('node:crypto');
const {Storage} = require('@google-cloud/storage');
const {ARTIFACT_BUCKET, readArtifactOperation} = require('./artifact_ingest_service');

const FILESYSTEM_VERSION = 'home-center.gcs-filesystem.v1';
const FILES = 'gcsFilesystemFiles';
const PATHS = 'gcsFilesystemPaths';
const VERSIONS = 'gcsFilesystemVersions';
const MUTATIONS = 'gcsFilesystemMutations';
const TRASH = 'gcsFilesystemTrashEntries';
const MAX_FILE_BYTES = Number(process.env.HOME_CENTER_FILESYSTEM_MAX_BYTES || 256 * 1024 * 1024);
const TRASH_RETENTION_DAYS = Number(process.env.HOME_CENTER_FILESYSTEM_TRASH_DAYS || 30);
const PUBLIC_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
let client = null;

function storageClient() { if (!client) client = new Storage(); return client; }
function sha256(bytes) { return createHash('sha256').update(bytes).digest('hex'); }
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object' && !(value instanceof Date)) return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}
function hashJson(value) { return sha256(Buffer.from(JSON.stringify(stable(value)))); }
function text(value, max = 1200) { const out = typeof value === 'string' ? value.trim() : ''; return out.slice(0, max); }
function fail(code, message, status = 400, details = {}) { const error = new Error(message); error.code = code; error.failureKind = code; error.status = status; error.details = details; return error; }
function ownerEmail(user) { const value = text(user && user.email, 320).toLowerCase(); if (!value) throw fail('storage.filesystem.owner_required', 'Authenticated owner identity is required.', 401); return value; }
function ownerHash(owner) { return sha256(Buffer.from(owner)).slice(0, 24); }
function requestId(value) { const out = text(value, 180).toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, ''); if (!out) throw fail('storage.filesystem.request_id_required', 'requestId is required.'); return out; }
function digest(value, field = 'sha256') { const out = text(value, 64).toLowerCase(); if (!/^[a-f0-9]{64}$/.test(out)) throw fail('storage.filesystem.invalid_digest', field + ' must be a SHA-256 digest.', 400, {field}); return out; }
function byteLength(value, field = 'byteLength', allowZero = true) { const out = Number(value); if (!Number.isSafeInteger(out) || out < (allowZero ? 0 : 1) || out > MAX_FILE_BYTES) throw fail('storage.filesystem.invalid_length', field + ' is outside the filesystem byte limit.', 400, {field, max: MAX_FILE_BYTES}); return out; }
function mediaType(value) { const out = text(value, 160).toLowerCase(); return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(out) ? out : 'application/octet-stream'; }
function fileName(value) { const out = text(value, 240).normalize('NFC').replace(/[\u0000-\u001f\u007f]/g, '').replace(/\//g, '-'); if (!out || out === '.' || out === '..') throw fail('storage.filesystem.invalid_filename', 'A valid logical filename is required.'); return out; }
function normalizePath(value) {
  const raw = text(value, 2000).normalize('NFC').replace(/\\/g, '/');
  if (!raw || !raw.startsWith('/')) throw fail('storage.filesystem.invalid_path', 'Filesystem paths must be absolute POSIX paths.');
  const parts = raw.split('/').filter(Boolean);
  if (!parts.length || parts.some((part) => part === '.' || part === '..' || /[\u0000-\u001f\u007f]/.test(part) || part.length > 240)) throw fail('storage.filesystem.invalid_path', 'Filesystem path contains an invalid component.');
  const out = '/' + parts.join('/');
  if (out.length > 1600) throw fail('storage.filesystem.invalid_path', 'Filesystem path exceeds 1600 characters.');
  return out;
}
function parentPath(value) { const index = value.lastIndexOf('/'); return index <= 0 ? '/' : value.slice(0, index); }
function baseName(value) { return value.slice(value.lastIndexOf('/') + 1); }
function pathId(ownerKey, value) { return ownerKey + '-' + sha256(Buffer.from(value)).slice(0, 40); }
function fileDocId(ownerKey, fileId) { return ownerKey + '-' + fileId; }
function versionDocId(ownerKey, versionId) { return ownerKey + '-' + versionId; }
function mutationDocId(ownerKey, id) { return ownerKey + '-' + sha256(Buffer.from(id)).slice(0, 40); }
function refs(admin, ownerKey, fileId, pathValue, versionId, id) {
  const db = admin.firestore();
  return {
    db,
    file: fileId ? db.collection(FILES).doc(fileDocId(ownerKey, fileId)) : null,
    path: pathValue ? db.collection(PATHS).doc(pathId(ownerKey, pathValue)) : null,
    version: versionId ? db.collection(VERSIONS).doc(versionDocId(ownerKey, versionId)) : null,
    mutation: id ? db.collection(MUTATIONS).doc(mutationDocId(ownerKey, id)) : null,
    trash: fileId ? db.collection(TRASH).doc(fileDocId(ownerKey, fileId)) : null,
  };
}
function assertApproved(args) { if (args.approved !== true) throw fail('storage.filesystem.authorization_required', 'Filesystem mutation requires approved=true as execution authorization.', 409); }
function publicVersion(record) {
  if (!record) return null;
  return {versionId: record.versionId, fileId: record.fileId, ordinal: Number(record.ordinal || 0), sha256: record.sha256, byteLength: Number(record.byteLength || 0), mediaType: record.mediaType, filename: record.filename, parentVersionId: record.parentVersionId || null, operation: record.operation, provenance: record.provenance || {}, createdAt: record.createdAt, immutable: true};
}
function publicFile(record) {
  if (!record) return null;
  const expires = record.expiresAt && typeof record.expiresAt.toDate === 'function' ? record.expiresAt.toDate().toISOString() : record.expiresAt instanceof Date ? record.expiresAt.toISOString() : record.expiresAt || null;
  return {fileId: record.fileId, path: record.path, state: record.state, currentVersionId: record.currentVersionId, name: record.name, mediaType: record.mediaType, byteLength: Number(record.byteLength || 0), sha256: record.sha256, createdAt: record.createdAt, updatedAt: record.updatedAt, originalPath: record.originalPath || null, expiresAt: expires, authorizationState: 'owner_scoped', humanAcceptance: record.humanAcceptance || 'unreviewed'};
}
async function streamDigest(file) { const hash = createHash('sha256'); let count = 0; for await (const chunk of file.createReadStream()) { const bytes = Buffer.from(chunk); hash.update(bytes); count += bytes.length; } return {sha256: hash.digest('hex'), byteLength: count}; }
async function verifyLocation(storage, location, expected) {
  if (!location || location.bucket !== ARTIFACT_BUCKET || !text(location.objectName, 1800)) throw fail('storage.filesystem.invalid_location', 'File version does not reference canonical Home Center storage.', 409);
  const file = storage.bucket(location.bucket).file(location.objectName);
  const actual = await streamDigest(file);
  if (actual.sha256 !== expected.sha256 || actual.byteLength !== expected.byteLength) throw fail('storage.filesystem.readback_mismatch', 'Stored bytes do not match the immutable file version.', 409, {expected: {sha256: expected.sha256, byteLength: expected.byteLength}, actual});
  let generation = '';
  if (typeof file.getMetadata === 'function') { const [metadata] = await file.getMetadata(); generation = String(metadata && metadata.generation || ''); }
  return {...actual, generation, file};
}
async function ensureEmptyObject(storage, ownerKey) {
  const objectName = 'filesystem/v1/blobs/' + ownerKey + '/' + 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
  const file = storage.bucket(ARTIFACT_BUCKET).file(objectName);
  try { await file.save(Buffer.alloc(0), {resumable: false, validation: false, contentType: 'application/octet-stream', preconditionOpts: {ifGenerationMatch: 0}, metadata: {metadata: {ownerHash: ownerKey, sha256: sha256(Buffer.alloc(0)), byteLength: '0', filesystem: 'true'}}}); }
  catch (error) { if (![409, 412].includes(Number(error && error.code)) && !/condition|exists/i.test(String(error && error.message))) throw error; }
  return {bucket: ARTIFACT_BUCKET, objectName, storageRef: 'gs://' + ARTIFACT_BUCKET + '/' + objectName, sha256: sha256(Buffer.alloc(0)), byteLength: 0, mediaType: 'application/octet-stream', filename: 'empty.bin', provenance: {sourceKind: 'empty'}};
}
async function loadVersion({admin, ownerKey, versionId}) {
  const snap = await refs(admin, ownerKey, '', '', versionId, '').version.get();
  if (!snap.exists) throw fail('storage.filesystem.version_not_found', 'Filesystem version was not found.', 404);
  const value = snap.data() || {};
  if (value.ownerHash !== ownerKey) throw fail('storage.filesystem.forbidden', 'Filesystem version is not owned by this caller.', 403);
  return value;
}
async function resolveSource({admin, storage, user, source, ownerKey}) {
  if (!source || source.kind === 'empty') return ensureEmptyObject(storage, ownerKey);
  if (source.kind === 'home_center_artifact') {
    const artifactId = text(source.artifactId, 180);
    if (!artifactId) throw fail('storage.filesystem.artifact_required', 'source.artifactId is required.');
    const {manifest} = await readArtifactOperation({storage, user, args: {artifactId}});
    const destination = manifest && manifest.destination || {};
    const expected = {sha256: digest(source.sha256, 'source.sha256'), byteLength: byteLength(source.byteLength, 'source.byteLength')};
    if (destination.sha256 !== expected.sha256 || Number(destination.byteCount) !== expected.byteLength) throw fail('storage.filesystem.source_conflict', 'Artifact source identity does not match its immutable manifest.', 409);
    const location = {bucket: destination.bucket || ARTIFACT_BUCKET, objectName: destination.objectName, storageRef: destination.storageRef};
    const verified = await verifyLocation(storage, location, expected);
    return {...location, ...expected, generation: verified.generation, mediaType: mediaType(manifest.source && manifest.source.mimeType), filename: fileName(manifest.source && manifest.source.name || artifactId), provenance: {sourceKind: 'home_center_artifact', artifactId, artifactManifest: 'home-center://artifacts/' + artifactId, source: manifest.source && manifest.source.provenance || {}}};
  }
  if (source.kind === 'filesystem_version') {
    const version = await loadVersion({admin, ownerKey, versionId: text(source.versionId, 64)});
    if (source.fileId && source.fileId !== version.fileId) throw fail('storage.filesystem.source_conflict', 'Filesystem source fileId does not match version.', 409);
    if (source.sha256 && digest(source.sha256, 'source.sha256') !== version.sha256) throw fail('storage.filesystem.source_conflict', 'Filesystem source digest does not match version.', 409);
    await verifyLocation(storage, version.location, version);
    return {...version.location, sha256: version.sha256, byteLength: version.byteLength, mediaType: version.mediaType, filename: version.filename, generation: version.generation || '', provenance: {sourceKind: 'filesystem_version', fileId: version.fileId, versionId: version.versionId}};
  }
  throw fail('storage.filesystem.unsupported_source', 'Source must be empty, home_center_artifact, or filesystem_version.', 400, {kind: source.kind});
}
async function existingMutation(admin, ownerKey, id, inputHash) {
  const ref = refs(admin, ownerKey, '', '', '', id).mutation;
  const snap = await ref.get();
  if (!snap.exists) return {ref, receipt: null};
  const value = snap.data() || {};
  if (value.inputHash !== inputHash) throw fail('storage.filesystem.idempotency_conflict', 'requestId is already bound to different filesystem inputs.', 409);
  return {ref, receipt: value.receipt || value};
}
async function saveReceipt(storage, ownerKey, id, receipt) {
  const objectName = 'indexes/filesystem/v1/receipts/' + ownerKey + '/' + sha256(Buffer.from(id)) + '.json';
  const payload = Buffer.from(JSON.stringify(receipt, null, 2) + '\n');
  const file = storage.bucket(ARTIFACT_BUCKET).file(objectName);
  try { await file.save(payload, {resumable: false, validation: false, contentType: 'application/json', preconditionOpts: {ifGenerationMatch: 0}, metadata: {metadata: {ownerHash: ownerKey, requestId: id, inputHash: receipt.inputHash, schemaVersion: FILESYSTEM_VERSION}}}); }
  catch (error) {
    if (![409, 412].includes(Number(error && error.code)) && !/condition|exists/i.test(String(error && error.message))) throw error;
    const [current] = await file.download();
    const parsed = JSON.parse(Buffer.from(current).toString('utf8'));
    if (parsed.inputHash !== receipt.inputHash) throw fail('storage.filesystem.receipt_conflict', 'Filesystem receipt object conflicts with the idempotent mutation.', 409);
  }
  const [readback] = await file.download();
  if (sha256(Buffer.from(readback)) !== sha256(payload)) throw fail('storage.filesystem.receipt_readback_mismatch', 'Filesystem receipt failed immutable readback verification.', 502);
  return {storageRef: 'gs://' + ARTIFACT_BUCKET + '/' + objectName, sha256: sha256(payload), byteLength: payload.length};
}
async function finalizeMutation({admin, storage, ownerKey, mutationRef, receipt}) {
  const receiptObject = await saveReceipt(storage, ownerKey, receipt.requestId, receipt);
  const final = {...receipt, receiptObject, discovery: {...receipt.discovery, receiptReadback: true}};
  await mutationRef.set({...final, receipt: final}, {merge: true});
  return final;
}
function mutationBase(operation, id, inputHash, file, version = null) {
  return {schemaVersion: FILESYSTEM_VERSION, operation, requestId: id, inputHash, status: 'completed', file: publicFile(file), version: publicVersion(version), authorization: {state: 'owner_scoped', derivedFrom: 'authenticated_principal'}, humanAcceptance: file.humanAcceptance || 'unreviewed', transport: {binaryInJson: false, copiedBytes: 0}, discovery: {ok: true, stat: true, list: true}, completedAt: new Date().toISOString()};
}
async function createFileOperation({admin, storage = storageClient(), user, args = {}, internalProjection = false, internalOperation = 'storage.filesystem.create'}) {
  if (!internalProjection) assertApproved(args);
  const owner = ownerEmail(user), ownerKey = ownerHash(owner), id = requestId(args.requestId), pathValue = normalizePath(args.path);
  const logical = {operation: internalOperation, path: pathValue, source: args.source || {kind: 'empty'}, humanAcceptance: text(args.humanAcceptance, 40) || 'unreviewed'};
  const inputHash = hashJson(logical), existing = await existingMutation(admin, ownerKey, id, inputHash); if (existing.receipt) return {...existing.receipt, attached: true};
  const source = await resolveSource({admin, storage, user, source: logical.source, ownerKey});
  const now = new Date().toISOString(), fileId = sha256(Buffer.from(ownerKey + ':file:' + id + ':' + pathValue)).slice(0, 40), versionId = hashJson({fileId, ordinal: 1, source: {sha256: source.sha256, byteLength: source.byteLength, mediaType: source.mediaType}, operation: logical.operation});
  const file = {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, ownerEmail: owner, fileId, path: pathValue, pathHash: sha256(Buffer.from(pathValue)), state: 'active', currentVersionId: versionId, versionCount: 1, name: baseName(pathValue), mediaType: source.mediaType, byteLength: source.byteLength, sha256: source.sha256, humanAcceptance: logical.humanAcceptance, createdAt: now, updatedAt: now};
  const version = {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, fileId, versionId, ordinal: 1, sha256: source.sha256, byteLength: source.byteLength, mediaType: source.mediaType, filename: fileName(source.filename || baseName(pathValue)), location: {bucket: source.bucket, objectName: source.objectName, storageRef: source.storageRef}, generation: source.generation || '', parentVersionId: null, operation: logical.operation, provenance: source.provenance || {}, createdAt: now};
  const r = refs(admin, ownerKey, fileId, pathValue, versionId, id);
  await r.db.runTransaction(async (tx) => {
    const [idem, occupied] = await Promise.all([tx.get(r.mutation), tx.get(r.path)]);
    if (idem.exists) { if ((idem.data() || {}).inputHash !== inputHash) throw fail('storage.filesystem.idempotency_conflict', 'requestId is already bound to different filesystem inputs.', 409); return; }
    if (occupied.exists) throw fail('storage.filesystem.path_exists', 'Filesystem path already exists.', 409, {path: pathValue});
    tx.create(r.file, file); tx.create(r.path, file); tx.create(r.version, version); tx.create(r.mutation, {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, requestId: id, inputHash, status: 'committing', operation: logical.operation, createdAt: now});
  });
  return finalizeMutation({admin, storage, ownerKey, mutationRef: r.mutation, receipt: mutationBase(logical.operation, id, inputHash, file, version)});
}
async function loadFile({admin, ownerKey, fileId, allowTrash = false}) {
  const snap = await refs(admin, ownerKey, fileId, '', '', '').file.get();
  if (!snap.exists) throw fail('storage.filesystem.file_not_found', 'Filesystem file was not found.', 404);
  const value = snap.data() || {};
  if (value.ownerHash !== ownerKey) throw fail('storage.filesystem.forbidden', 'Filesystem file is not owned by this caller.', 403);
  if (!allowTrash && value.state !== 'active') throw fail('storage.filesystem.file_trashed', 'Filesystem file is in trash.', 409);
  return value;
}
function assertExpectedVersion(file, args) {
  const expected = text(args.expectedVersionId, 64);
  if (!expected) throw fail('storage.filesystem.expected_version_required', 'expectedVersionId is required for mutation of an existing file.');
  if (file.currentVersionId !== expected) throw fail('storage.filesystem.version_conflict', 'Filesystem head changed since the caller read it.', 409, {expected, actual: file.currentVersionId});
}
async function installNewHead({admin, storage, user, args, operation, sourceResolver}) {
  assertApproved(args);
  const owner = ownerEmail(user), ownerKey = ownerHash(owner), id = requestId(args.requestId), fileId = text(args.fileId, 64);
  const file = await loadFile({admin, ownerKey, fileId}); assertExpectedVersion(file, args);
  const logical = {operation, fileId, expectedVersionId: args.expectedVersionId, source: args.source || null, versionId: args.versionId || null};
  const inputHash = hashJson(logical), existing = await existingMutation(admin, ownerKey, id, inputHash); if (existing.receipt) return {...existing.receipt, attached: true};
  const previous = await loadVersion({admin, ownerKey, versionId: file.currentVersionId});
  const source = await sourceResolver({admin, storage, user, ownerKey, file, previous});
  const ordinal = Number(file.versionCount || 1) + 1, now = new Date().toISOString(), versionId = hashJson({fileId, ordinal, parentVersionId: previous.versionId, operation, source: {sha256: source.sha256, byteLength: source.byteLength, mediaType: source.mediaType}});
  const version = {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, fileId, versionId, ordinal, sha256: source.sha256, byteLength: source.byteLength, mediaType: source.mediaType, filename: fileName(source.filename || file.name), location: {bucket: source.bucket, objectName: source.objectName, storageRef: source.storageRef}, generation: source.generation || '', parentVersionId: previous.versionId, operation, provenance: source.provenance || {}, createdAt: now};
  const next = {...file, currentVersionId: versionId, versionCount: ordinal, mediaType: version.mediaType, byteLength: version.byteLength, sha256: version.sha256, updatedAt: now};
  const r = refs(admin, ownerKey, fileId, file.path, versionId, id);
  await r.db.runTransaction(async (tx) => {
    const [idem, live] = await Promise.all([tx.get(r.mutation), tx.get(r.file)]);
    if (idem.exists) return;
    const current = live.data() || {}; if (current.currentVersionId !== args.expectedVersionId) throw fail('storage.filesystem.version_conflict', 'Filesystem head changed during mutation.', 409);
    tx.create(r.version, version); tx.set(r.file, next); tx.set(r.path, next); tx.create(r.mutation, {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, requestId: id, inputHash, status: 'committing', operation, createdAt: now});
  });
  return finalizeMutation({admin, storage, ownerKey, mutationRef: r.mutation, receipt: mutationBase(operation, id, inputHash, next, version)});
}
async function overwriteFileOperation(context) {
  return installNewHead({...context, operation: 'storage.filesystem.overwrite', sourceResolver: ({admin, storage, user, ownerKey}) => resolveSource({admin, storage, user, source: context.args.source, ownerKey})});
}
async function composeAppend({storage, ownerKey, id, previous, suffix}) {
  if (previous.byteLength === 0) return {...suffix, provenance: {operation: 'append', previousVersionId: previous.versionId, suffix: suffix.provenance}};
  if (suffix.byteLength === 0) return {...previous.location, sha256: previous.sha256, byteLength: previous.byteLength, mediaType: previous.mediaType, filename: previous.filename, generation: previous.generation || '', provenance: {operation: 'append_empty', previousVersionId: previous.versionId}};
  const total = byteLength(Number(previous.byteLength) + Number(suffix.byteLength), 'append.totalByteLength');
  const bucket = storage.bucket(ARTIFACT_BUCKET), tempName = 'temp/filesystem/' + ownerKey + '/' + sha256(Buffer.from(id)) + '/append.part', temp = bucket.file(tempName);
  if (typeof bucket.combine !== 'function') throw fail('storage.filesystem.compose_unsupported', 'Storage adapter does not support server-side binary append.', 501);
  await bucket.combine([bucket.file(previous.location.objectName), bucket.file(suffix.objectName)], temp);
  const actual = await streamDigest(temp); if (actual.byteLength !== total) throw fail('storage.filesystem.append_length_mismatch', 'Server-side append produced an incorrect byte length.', 502);
  const objectName = 'filesystem/v1/blobs/' + ownerKey + '/' + actual.sha256, destination = bucket.file(objectName);
  try { await temp.copy(destination, {preconditionOpts: {ifGenerationMatch: 0}, metadata: {contentType: previous.mediaType || suffix.mediaType, metadata: {ownerHash: ownerKey, sha256: actual.sha256, byteLength: String(actual.byteLength), filesystem: 'true'}}}); }
  catch (error) { if (![409, 412].includes(Number(error && error.code)) && !/condition|exists/i.test(String(error && error.message))) throw error; }
  await temp.delete({ignoreNotFound: true});
  const verified = await verifyLocation(storage, {bucket: ARTIFACT_BUCKET, objectName}, actual);
  return {bucket: ARTIFACT_BUCKET, objectName, storageRef: 'gs://' + ARTIFACT_BUCKET + '/' + objectName, ...actual, generation: verified.generation, mediaType: previous.mediaType || suffix.mediaType, filename: previous.filename, provenance: {operation: 'append', previousVersionId: previous.versionId, suffix: suffix.provenance}};
}
async function appendFileOperation(context) {
  return installNewHead({...context, operation: 'storage.filesystem.append', sourceResolver: async ({admin, storage, user, ownerKey, previous}) => {
    const suffix = await resolveSource({admin, storage, user, source: context.args.source, ownerKey});
    return composeAppend({storage, ownerKey, id: context.args.requestId, previous, suffix});
  }});
}
async function copyFileOperation({admin, storage = storageClient(), user, args = {}}) {
  assertApproved(args);
  const owner = ownerEmail(user), ownerKey = ownerHash(owner), sourceFile = await loadFile({admin, ownerKey, fileId: text(args.fileId, 64)}); assertExpectedVersion(sourceFile, args);
  const version = await loadVersion({admin, ownerKey, versionId: sourceFile.currentVersionId});
  return createFileOperation({admin, storage, user, internalProjection: true, internalOperation: 'storage.filesystem.copy', args: {approved: true, requestId: args.requestId, path: args.path, humanAcceptance: sourceFile.humanAcceptance, source: {kind: 'filesystem_version', fileId: sourceFile.fileId, versionId: version.versionId, sha256: version.sha256}}});
}
async function relocateFileOperation({admin, storage = storageClient(), user, args = {}, operation = 'storage.filesystem.move'}) {
  assertApproved(args);
  const owner = ownerEmail(user), ownerKey = ownerHash(owner), id = requestId(args.requestId), fileId = text(args.fileId, 64), file = await loadFile({admin, ownerKey, fileId}); assertExpectedVersion(file, args);
  let destination;
  if (operation === 'storage.filesystem.rename') destination = normalizePath(parentPath(file.path) + '/' + fileName(args.name)); else destination = normalizePath(args.path);
  const logical = {operation, fileId, expectedVersionId: args.expectedVersionId, sourcePath: file.path, destination};
  const inputHash = hashJson(logical), existing = await existingMutation(admin, ownerKey, id, inputHash); if (existing.receipt) return {...existing.receipt, attached: true};
  if (destination === file.path) throw fail('storage.filesystem.path_unchanged', 'Destination path is unchanged.', 409);
  const now = new Date().toISOString(), next = {...file, path: destination, pathHash: sha256(Buffer.from(destination)), name: baseName(destination), updatedAt: now};
  const db = admin.firestore(), sourcePathRef = db.collection(PATHS).doc(pathId(ownerKey, file.path)), destinationRef = db.collection(PATHS).doc(pathId(ownerKey, destination)), mutationRef = db.collection(MUTATIONS).doc(mutationDocId(ownerKey, id)), fileRef = db.collection(FILES).doc(fileDocId(ownerKey, fileId));
  await db.runTransaction(async (tx) => {
    const [idem, current, occupied] = await Promise.all([tx.get(mutationRef), tx.get(fileRef), tx.get(destinationRef)]); if (idem.exists) return;
    if (occupied.exists) throw fail('storage.filesystem.path_exists', 'Destination path already exists.', 409, {path: destination});
    if ((current.data() || {}).currentVersionId !== args.expectedVersionId) throw fail('storage.filesystem.version_conflict', 'Filesystem head changed during relocation.', 409);
    tx.delete(sourcePathRef); tx.set(destinationRef, next); tx.set(fileRef, next); tx.create(mutationRef, {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, requestId: id, inputHash, status: 'committing', operation, createdAt: now});
  });
  const version = await loadVersion({admin, ownerKey, versionId: next.currentVersionId});
  return finalizeMutation({admin, storage, ownerKey, mutationRef, receipt: mutationBase(operation, id, inputHash, next, version)});
}
async function moveFileOperation(context) { return relocateFileOperation({...context, operation: 'storage.filesystem.move'}); }
async function renameFileOperation(context) { return relocateFileOperation({...context, operation: 'storage.filesystem.rename'}); }
async function trashFileOperation({admin, storage = storageClient(), user, args = {}}) {
  assertApproved(args);
  const owner = ownerEmail(user), ownerKey = ownerHash(owner), id = requestId(args.requestId), fileId = text(args.fileId, 64), file = await loadFile({admin, ownerKey, fileId}); assertExpectedVersion(file, args);
  const logical = {operation: 'storage.filesystem.trash', fileId, expectedVersionId: args.expectedVersionId, path: file.path}, inputHash = hashJson(logical), existing = await existingMutation(admin, ownerKey, id, inputHash); if (existing.receipt) return {...existing.receipt, attached: true};
  const nowDate = new Date(), now = nowDate.toISOString(), expiresAt = new Date(nowDate.getTime() + TRASH_RETENTION_DAYS * 86400000), trashPath = '/.trash/' + now.slice(0, 10) + '/' + fileId + '/' + file.name;
  const next = {...file, state: 'trash', originalPath: file.path, path: trashPath, pathHash: sha256(Buffer.from(trashPath)), trashedAt: now, expiresAt, updatedAt: now};
  const r = refs(admin, ownerKey, fileId, file.path, '', id), trashRef = r.db.collection(TRASH).doc(fileDocId(ownerKey, fileId));
  await r.db.runTransaction(async (tx) => { const [idem, current] = await Promise.all([tx.get(r.mutation), tx.get(r.file)]); if (idem.exists) return; if ((current.data() || {}).currentVersionId !== args.expectedVersionId) throw fail('storage.filesystem.version_conflict', 'Filesystem head changed during trash.', 409); tx.delete(r.path); tx.set(r.file, next); tx.set(trashRef, next); tx.create(r.mutation, {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, requestId: id, inputHash, status: 'committing', operation: logical.operation, createdAt: now}); });
  const version = await loadVersion({admin, ownerKey, versionId: next.currentVersionId});
  const trashPointerName = 'indexes/filesystem/v1/trash/' + ownerKey + '/' + sha256(Buffer.from(id)) + '.json';
  const trashPointerBytes = Buffer.from(JSON.stringify({schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, fileId, versionId: version.versionId, originalPath: file.path, trashPath, trashedAt: now, expiresAt: expiresAt.toISOString()}, null, 2) + '\n');
  const trashPointer = storage.bucket(ARTIFACT_BUCKET).file(trashPointerName);
  try { await trashPointer.save(trashPointerBytes, {resumable: false, validation: false, contentType: 'application/json', preconditionOpts: {ifGenerationMatch: 0}, metadata: {metadata: {ownerHash: ownerKey, fileId, expiresAt: expiresAt.toISOString(), filesystemTrash: 'true'}}}); }
  catch (error) { if (![409, 412].includes(Number(error && error.code)) && !/condition|exists/i.test(String(error && error.message))) throw error; }
  const [trashReadback] = await trashPointer.download();
  if (sha256(Buffer.from(trashReadback)) !== sha256(trashPointerBytes)) throw fail('storage.filesystem.trash_pointer_mismatch', 'Trash pointer failed immutable readback verification.', 502);
  const receipt = mutationBase(logical.operation, id, inputHash, next, version);
  receipt.trash = {retentionDays: TRASH_RETENTION_DAYS, expiresAt: expiresAt.toISOString(), pointer: {storageRef: 'gs://' + ARTIFACT_BUCKET + '/' + trashPointerName, sha256: sha256(trashPointerBytes), byteLength: trashPointerBytes.length}};
  return finalizeMutation({admin, storage, ownerKey, mutationRef: r.mutation, receipt});
}
async function restoreFileOperation({admin, storage = storageClient(), user, args = {}}) {
  assertApproved(args);
  const owner = ownerEmail(user), ownerKey = ownerHash(owner), id = requestId(args.requestId), fileId = text(args.fileId, 64), file = await loadFile({admin, ownerKey, fileId, allowTrash: true}); assertExpectedVersion(file, args);
  if (file.state === 'active' && args.versionId) return installNewHead({admin, storage, user, args, operation: 'storage.filesystem.restore', sourceResolver: async () => {
    const version = await loadVersion({admin, ownerKey, versionId: text(args.versionId, 64)}); if (version.fileId !== fileId) throw fail('storage.filesystem.version_conflict', 'Historical version belongs to a different file.', 409); await verifyLocation(storage, version.location, version); return {...version.location, sha256: version.sha256, byteLength: version.byteLength, mediaType: version.mediaType, filename: version.filename, generation: version.generation, provenance: {operation: 'restore_version', restoredVersionId: version.versionId}};
  }});
  if (file.state !== 'trash') throw fail('storage.filesystem.restore_invalid_state', 'File is not in trash and no historical version was requested.', 409);
  const expiresAt = file.expiresAt && typeof file.expiresAt.toDate === 'function' ? file.expiresAt.toDate() : new Date(file.expiresAt);
  if (expiresAt.getTime() <= Date.now()) throw fail('storage.filesystem.trash_expired', 'Trash retention expired and this file is no longer restorable.', 410);
  const destination = normalizePath(args.path || file.originalPath), logical = {operation: 'storage.filesystem.restore', fileId, expectedVersionId: args.expectedVersionId, destination}, inputHash = hashJson(logical), existing = await existingMutation(admin, ownerKey, id, inputHash); if (existing.receipt) return {...existing.receipt, attached: true};
  const now = new Date().toISOString(), next = {...file, state: 'active', path: destination, pathHash: sha256(Buffer.from(destination)), name: baseName(destination), originalPath: null, expiresAt: null, restoredAt: now, updatedAt: now};
  delete next.trashedAt;
  const r = refs(admin, ownerKey, fileId, destination, '', id), trashRef = r.db.collection(TRASH).doc(fileDocId(ownerKey, fileId));
  await r.db.runTransaction(async (tx) => { const [idem, occupied, current] = await Promise.all([tx.get(r.mutation), tx.get(r.path), tx.get(r.file)]); if (idem.exists) return; if (occupied.exists) throw fail('storage.filesystem.path_exists', 'Restore destination already exists.', 409); if ((current.data() || {}).state !== 'trash') throw fail('storage.filesystem.restore_invalid_state', 'File left trash during restore.', 409); tx.set(r.path, next); tx.set(r.file, next); tx.delete(trashRef); tx.create(r.mutation, {schemaVersion: FILESYSTEM_VERSION, ownerHash: ownerKey, requestId: id, inputHash, status: 'committing', operation: logical.operation, createdAt: now}); });
  const version = await loadVersion({admin, ownerKey, versionId: next.currentVersionId});
  return finalizeMutation({admin, storage, ownerKey, mutationRef: r.mutation, receipt: mutationBase(logical.operation, id, inputHash, next, version)});
}
async function statFileOperation({admin, user, args = {}}) {
  const ownerKey = ownerHash(ownerEmail(user)); let file;
  if (args.fileId) file = await loadFile({admin, ownerKey, fileId: text(args.fileId, 64), allowTrash: true});
  else { const pathValue = normalizePath(args.path), snap = await refs(admin, ownerKey, '', pathValue, '', '').path.get(); if (!snap.exists) throw fail('storage.filesystem.file_not_found', 'Filesystem path was not found.', 404); file = snap.data() || {}; }
  const version = await loadVersion({admin, ownerKey, versionId: file.currentVersionId});
  return {schemaVersion: FILESYSTEM_VERSION, file: publicFile(file), version: publicVersion(version), authorization: {state: 'owner_scoped'}, humanAcceptance: file.humanAcceptance || 'unreviewed'};
}
async function listFilesOperation({admin, user, args = {}}) {
  const ownerKey = ownerHash(ownerEmail(user)), state = args.state === 'trash' ? 'trash' : 'active', limit = Math.max(1, Math.min(100, Number(args.limit || 50)));
  const collection = state === 'trash' ? TRASH : PATHS;
  let query = admin.firestore().collection(collection).where('ownerHash', '==', ownerKey).where('state', '==', state).orderBy('path').limit(limit + 1);
  if (args.cursor) query = query.startAfter(String(args.cursor));
  const snap = await query.get(), now = Date.now();
  const values = snap.docs.map((doc) => doc.data() || {}).filter((file) => state !== 'trash' || !file.expiresAt || new Date(file.expiresAt.toDate ? file.expiresAt.toDate() : file.expiresAt).getTime() > now);
  const page = values.slice(0, limit);
  return {schemaVersion: FILESYSTEM_VERSION, state, count: page.length, items: page.map(publicFile), nextCursor: values.length > limit ? page.at(-1).path : null, authorization: {state: 'owner_scoped'}, bounded: true};
}
async function listVersionsOperation({admin, user, args = {}}) {
  const ownerKey = ownerHash(ownerEmail(user)), file = await loadFile({admin, ownerKey, fileId: text(args.fileId, 64), allowTrash: true}), limit = Math.max(1, Math.min(100, Number(args.limit || 50)));
  let query = admin.firestore().collection(VERSIONS).where('ownerHash', '==', ownerKey).where('fileId', '==', file.fileId).orderBy('ordinal', 'desc').limit(limit + 1);
  if (args.cursor !== undefined && args.cursor !== null) query = query.startAfter(Number(args.cursor));
  const snap = await query.get(), values = snap.docs.map((doc) => doc.data() || {}), page = values.slice(0, limit);
  return {schemaVersion: FILESYSTEM_VERSION, file: publicFile(file), count: page.length, versions: page.map(publicVersion), nextCursor: values.length > limit ? page.at(-1).ordinal : null, bounded: true};
}
async function downloadFileOperation({admin, storage = storageClient(), user, args = {}}) {
  const ownerKey = ownerHash(ownerEmail(user)), file = await loadFile({admin, ownerKey, fileId: text(args.fileId, 64), allowTrash: args.allowTrash === true}), version = await loadVersion({admin, ownerKey, versionId: text(args.versionId, 64) || file.currentVersionId});
  if (version.fileId !== file.fileId) throw fail('storage.filesystem.version_conflict', 'Requested version belongs to a different file.', 409);
  const verified = await verifyLocation(storage, version.location, version);
  const url = PUBLIC_BASE + '/filesystem/files/' + encodeURIComponent(file.fileId) + '/versions/' + encodeURIComponent(version.versionId) + '/content';
  return {schemaVersion: FILESYSTEM_VERSION, file: publicFile(file), version: publicVersion(version), verification: {ok: true, sha256: verified.sha256, byteLength: verified.byteLength, generation: verified.generation}, authorization: {state: 'owner_scoped', requiredOnFetch: true}, resourceLink: {type: 'resource_link', uri: url, name: file.name, mimeType: version.mediaType, size: version.byteLength}, public: false};
}
async function projectArtifactOperation({admin, storage = storageClient(), user, artifactId, requestId: projectionRequestId = ''}) {
  const {manifest} = await readArtifactOperation({storage, user, args: {artifactId}}), source = manifest.source || {}, destination = manifest.destination || {};
  const pathValue = normalizePath('/artifacts/' + text(manifest.project, 120).replace(/[^A-Za-z0-9._-]+/g, '-') + '/' + text(manifest.artifactKind, 120).replace(/[^A-Za-z0-9._-]+/g, '-') + '/' + text(manifest.artifactId, 180).replace(/[^A-Za-z0-9._-]+/g, '-') + '/' + fileName(source.name || artifactId));
  try { return await createFileOperation({admin, storage, user, internalProjection: true, args: {approved: true, requestId: projectionRequestId || 'project-' + artifactId + '-' + destination.sha256.slice(0, 16), path: pathValue, source: {kind: 'home_center_artifact', artifactId, sha256: destination.sha256, byteLength: destination.byteCount}, humanAcceptance: manifest.humanAcceptance || 'unreviewed'}}); }
  catch (error) { if (error.code !== 'storage.filesystem.path_exists') throw error; return statFileOperation({admin, user, args: {path: pathValue}}); }
}
function filesystemOperationEntries() {
  const write = (summary, input) => ({summary, write: true, requiresRequestId: true, input: {approved: 'must be true; execution authorization only', requestId: 'stable idempotency key', ...input}});
  return {
    'storage.filesystem.create': write('Create an empty file or owner-scoped logical file from verified immutable bytes.', {path: 'absolute POSIX path', source: 'empty|home_center_artifact|filesystem_version'}),
    'storage.filesystem.append': write('Append verified binary bytes by server-side GCS composition and publish a new immutable version.', {fileId: 'string', expectedVersionId: 'required', source: 'home_center_artifact|filesystem_version'}),
    'storage.filesystem.copy': write('Create an owner-scoped logical copy that reuses immutable bytes.', {fileId: 'string', expectedVersionId: 'required', path: 'destination path'}),
    'storage.filesystem.move': write('Move an owner-scoped file to a new logical path without copying bytes.', {fileId: 'string', expectedVersionId: 'required', path: 'destination path'}),
    'storage.filesystem.rename': write('Rename an owner-scoped file in its current directory without copying bytes.', {fileId: 'string', expectedVersionId: 'required', name: 'new basename'}),
    'storage.filesystem.overwrite': write('Install verified replacement bytes as a new immutable head while retaining history.', {fileId: 'string', expectedVersionId: 'required', source: 'home_center_artifact|filesystem_version'}),
    'storage.filesystem.trash': write('Move an owner-scoped file into 30-day restorable trash; permanent deletion is unavailable.', {fileId: 'string', expectedVersionId: 'required'}),
    'storage.filesystem.restore': write('Restore a trash entry or historical version as the current head.', {fileId: 'string', expectedVersionId: 'required', path: 'optional restore destination', versionId: 'optional historical version'}),
    'storage.filesystem.list': {summary: 'List bounded owner-scoped active or trash filesystem entries.', write: false, input: {state: 'active|trash', limit: '1-100', cursor: 'opaque path cursor'}},
    'storage.filesystem.stat': {summary: 'Read one owner-scoped file and current immutable version.', write: false, input: {fileId: 'string or use path', path: 'absolute path or use fileId'}},
    'storage.filesystem.versions': {summary: 'List bounded immutable version history for one owner-scoped file.', write: false, input: {fileId: 'string', limit: '1-100', cursor: 'ordinal cursor'}},
    'storage.filesystem.download': {summary: 'Verify one owner-scoped file version and return an authenticated binary resource link.', write: false, input: {fileId: 'string', versionId: 'optional exact version', allowTrash: 'optional boolean'}},
  };
}
async function runFilesystemOperation({operation, admin, storage = storageClient(), user, args = {}}) {
  const context = {admin, storage, user, args};
  if (operation === 'storage.filesystem.create') return createFileOperation(context);
  if (operation === 'storage.filesystem.append') return appendFileOperation(context);
  if (operation === 'storage.filesystem.copy') return copyFileOperation(context);
  if (operation === 'storage.filesystem.move') return moveFileOperation(context);
  if (operation === 'storage.filesystem.rename') return renameFileOperation(context);
  if (operation === 'storage.filesystem.overwrite') return overwriteFileOperation(context);
  if (operation === 'storage.filesystem.trash') return trashFileOperation(context);
  if (operation === 'storage.filesystem.restore') return restoreFileOperation(context);
  if (operation === 'storage.filesystem.list') return listFilesOperation(context);
  if (operation === 'storage.filesystem.stat') return statFileOperation(context);
  if (operation === 'storage.filesystem.versions') return listVersionsOperation(context);
  if (operation === 'storage.filesystem.download') return downloadFileOperation(context);
  throw fail('storage.filesystem.unsupported_operation', 'Unsupported filesystem operation: ' + operation);
}
async function streamFilesystemContent({admin, storage = storageClient(), user, fileId, versionId, req, res}) {
  const ownerKey = ownerHash(ownerEmail(user)), file = await loadFile({admin, ownerKey, fileId, allowTrash: false}), version = await loadVersion({admin, ownerKey, versionId});
  if (version.fileId !== file.fileId) throw fail('storage.filesystem.version_conflict', 'Requested version belongs to a different file.', 409);
  const verified = await verifyLocation(storage, version.location, version), source = verified.file;
  let start = 0, end = version.byteLength ? version.byteLength - 1 : -1, partial = false;
  const range = text(req && req.get && req.get('Range'), 120);
  if (range) { const match = range.match(/^bytes=(\d+)-(\d*)$/); if (!match) throw fail('storage.filesystem.invalid_range', 'Only one explicit byte range is supported.', 416); start = Number(match[1]); end = match[2] ? Number(match[2]) : end; if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || end < start || end >= version.byteLength) throw fail('storage.filesystem.invalid_range', 'Requested byte range is outside the file.', 416); partial = true; }
  res.set('Cache-Control', 'private, no-store'); res.set('Accept-Ranges', 'bytes'); res.set('Content-Type', version.mediaType); res.set('Content-Disposition', 'attachment; filename="' + file.name.replace(/["\\]/g, '-') + '"'); res.set('ETag', '"' + version.sha256 + '"'); res.set('X-Content-SHA256', version.sha256); res.set('X-Content-Type-Options', 'nosniff');
  const length = end >= start ? end - start + 1 : 0; res.set('Content-Length', String(length)); if (partial) { res.status(206); res.set('Content-Range', 'bytes ' + start + '-' + end + '/' + version.byteLength); }
  if (req.method === 'HEAD' || length === 0) { res.end(); return; }
  source.createReadStream({start, end}).on('error', (error) => res.destroy(error)).pipe(res);
}

module.exports = {FILESYSTEM_VERSION, FILES, PATHS, VERSIONS, MUTATIONS, TRASH, MAX_FILE_BYTES, TRASH_RETENTION_DAYS, filesystemOperationEntries, runFilesystemOperation, createFileOperation, appendFileOperation, copyFileOperation, moveFileOperation, renameFileOperation, overwriteFileOperation, trashFileOperation, restoreFileOperation, listFilesOperation, statFileOperation, listVersionsOperation, downloadFileOperation, projectArtifactOperation, streamFilesystemContent, normalizePath, ownerHash, hashJson};
