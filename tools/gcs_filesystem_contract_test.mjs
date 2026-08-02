import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {Readable, Writable} from 'node:stream';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'functions/package.json'));
const service = require('../functions/gcs_filesystem_service.js');
const {ARTIFACT_BUCKET} = require('../functions/artifact_ingest_service.js');
const {driveOperationRegistry} = require('../functions/home_center_mcp.js');

function sha(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }

class Snapshot {
  constructor(ref, value) { this.ref = ref; this.exists = value !== undefined; this.value = value; }
  data() { return this.exists ? structuredClone(this.value) : undefined; }
}
class DocRef {
  constructor(db, collection, id) { this.db = db; this.collectionName = collection; this.id = id; this.key = collection + '/' + id; }
  async get() { return new Snapshot(this, this.db.store.get(this.key)); }
  async create(value) { if (this.db.store.has(this.key)) { const error = new Error('already exists'); error.code = 6; throw error; } this.db.store.set(this.key, structuredClone(value)); }
  async set(value, options = {}) { const next = structuredClone(value); this.db.store.set(this.key, options.merge ? {...(this.db.store.get(this.key) || {}), ...next} : next); }
  async delete() { this.db.store.delete(this.key); }
}
class Query {
  constructor(db, collection) { this.db = db; this.collectionName = collection; this.filters = []; this.order = null; this.direction = 'asc'; this.pageLimit = Infinity; this.cursor = undefined; }
  where(field, operator, value) { assert.equal(operator, '=='); this.filters.push([field, value]); return this; }
  orderBy(field, direction = 'asc') { this.order = field; this.direction = direction; return this; }
  limit(value) { this.pageLimit = value; return this; }
  startAfter(value) { this.cursor = value; return this; }
  async get() {
    let values = [...this.db.store.entries()].filter(([key]) => key.startsWith(this.collectionName + '/')).map(([key, value]) => ({ref: new DocRef(this.db, this.collectionName, key.slice(this.collectionName.length + 1)), value}));
    for (const [field, expected] of this.filters) values = values.filter(({value}) => value[field] === expected);
    if (this.order) {
      const factor = this.direction === 'desc' ? -1 : 1;
      values.sort((left, right) => factor * (left.value[this.order] < right.value[this.order] ? -1 : left.value[this.order] > right.value[this.order] ? 1 : 0));
      if (this.cursor !== undefined) values = values.filter(({value}) => this.direction === 'desc' ? value[this.order] < this.cursor : value[this.order] > this.cursor);
    }
    return {docs: values.slice(0, this.pageLimit).map(({ref, value}) => new Snapshot(ref, value))};
  }
}
class Firestore {
  constructor() { this.store = new Map(); this.tail = Promise.resolve(); }
  collection(name) { const query = new Query(this, name); query.doc = (id) => new DocRef(this, name, id); return query; }
  async runTransaction(callback) {
    const run = this.tail.then(() => callback({get: (ref) => ref.get(), create: (ref, value) => ref.create(value), set: (ref, value, options) => ref.set(value, options), delete: (ref) => ref.delete()}));
    this.tail = run.catch(() => {}); return run;
  }
}
class FakeFile {
  constructor(bucket, objectName) { this.bucket = bucket; this.objectName = objectName; }
  key() { return this.bucket.name + '/' + this.objectName; }
  entry() { const entry = this.bucket.storage.objects.get(this.key()); if (!entry) { const error = new Error('not found: ' + this.objectName); error.code = 404; throw error; } return entry; }
  async save(bytes, options = {}) {
    if (this.bucket.storage.objects.has(this.key()) && options.preconditionOpts?.ifGenerationMatch === 0) { const error = new Error('precondition failed'); error.code = 412; throw error; }
    const generation = String(++this.bucket.storage.generation);
    this.bucket.storage.objects.set(this.key(), {bytes: Buffer.from(bytes), metadata: options.metadata || {}, generation}); this.bucket.storage.writeCalls += 1;
  }
  async download() { return [Buffer.from(this.entry().bytes)]; }
  createReadStream(options = {}) { const bytes = this.entry().bytes; const start = options.start === undefined ? 0 : options.start; const end = options.end === undefined ? bytes.length - 1 : options.end; return Readable.from([bytes.subarray(start, end + 1)]); }
  async getMetadata() { const entry = this.entry(); return [{generation: entry.generation, size: String(entry.bytes.length), ...entry.metadata}]; }
  async copy(destination, options = {}) { await destination.save(this.entry().bytes, options); return [destination]; }
  async delete() { this.bucket.storage.objects.delete(this.key()); }
}
class FakeBucket {
  constructor(storage, name) { this.storage = storage; this.name = name; }
  file(name) { return new FakeFile(this, name); }
  async combine(sources, destination, options = {}) { await destination.save(Buffer.concat(sources.map((source) => source.entry().bytes)), options); this.storage.combineCalls += 1; return [destination]; }
}
class FakeStorage {
  constructor() { this.objects = new Map(); this.generation = 0; this.writeCalls = 0; this.combineCalls = 0; }
  bucket(name) { return new FakeBucket(this, name); }
  seed(name, bytes, metadata = {}) { this.objects.set(ARTIFACT_BUCKET + '/' + name, {bytes: Buffer.from(bytes), metadata, generation: String(++this.generation)}); }
}
function seedArtifact(storage, owner, artifactId, name, mediaType, bytes) {
  const ownerSegment = owner.toLowerCase(); const objectName = `rotoscoping/${ownerSegment}/fixture/${artifactId}/${name}`; const digest = sha(bytes);
  const manifest = {schemaVersion: 'home-center.artifact.v1', artifactId, artifactKind: 'fixture', project: 'filesystem-contract', lifecycleState: 'proposed', ownerEmail: ownerSegment, source: {name, mimeType: mediaType, provenance: {sourceAuthority: 'contract-fixture'}}, destination: {bucket: ARTIFACT_BUCKET, objectName, storageRef: `gs://${ARTIFACT_BUCKET}/${objectName}`, byteCount: bytes.length, sha256: digest}};
  storage.seed(objectName, bytes, {contentType: mediaType}); storage.seed(`indexes/artifacts/v1/by-id/${ownerSegment}/${artifactId}.json`, Buffer.from(JSON.stringify(manifest)));
  return {artifactId, digest, bytes, manifest};
}
class ResponseSink extends Writable {
  constructor() { const chunks = []; super({write(chunk, encoding, callback) { chunks.push(Buffer.from(chunk)); callback(); }}); this.chunks = chunks; this.headers = {}; this.statusCode = 200; }
  set(name, value) { this.headers[name] = String(value); return this; }
  status(value) { this.statusCode = value; return this; }
  bytes() { return Buffer.concat(this.chunks); }
}

const owner = 'dclarke1005@gmail.com'; const user = {email: owner}; const otherUser = {email: 'other@example.com'};
const storage = new FakeStorage(); const db = new Firestore(); const admin = {firestore: () => db};
const alpha = seedArtifact(storage, owner, 'alpha-source', 'alpha.bin', 'application/octet-stream', Buffer.from('alpha'));
const beta = seedArtifact(storage, owner, 'beta-source', 'beta.bin', 'application/octet-stream', Buffer.from('-beta'));
const gamma = seedArtifact(storage, owner, 'gamma-source', 'gamma.bin', 'application/octet-stream', Buffer.from('gamma'));

const operationNames = Object.keys(service.filesystemOperationEntries());
assert.deepEqual(operationNames.sort(), ['storage.filesystem.append', 'storage.filesystem.copy', 'storage.filesystem.create', 'storage.filesystem.download', 'storage.filesystem.list', 'storage.filesystem.move', 'storage.filesystem.overwrite', 'storage.filesystem.rename', 'storage.filesystem.restore', 'storage.filesystem.stat', 'storage.filesystem.trash', 'storage.filesystem.versions']);
for (const name of operationNames) assert.ok(driveOperationRegistry().operations[name], `${name} missing from dynamic registry`);
const topLevel = JSON.parse(fs.readFileSync(path.join(root, 'contracts/home-center-top-level-mcp.v1.json'), 'utf8'));
assert.equal(topLevel.some((tool) => /foundry|storage\.filesystem/i.test(tool.name)), false, 'dynamic capability leaked into top-level MCP');
assert.equal(sha(Buffer.from(JSON.stringify(topLevel))), '218fc0b22087642b6e05c743022fd8454113aa183b30818d20c54f4da69b5734');

await assert.rejects(service.createFileOperation({admin, storage, user, args: {requestId: 'not-approved', path: '/work/no.bin', source: {kind: 'empty'}}}), (error) => error.code === 'storage.filesystem.authorization_required');
const createArgs = {approved: true, requestId: 'create-alpha-v1', path: '/work/input.bin', humanAcceptance: 'unreviewed', source: {kind: 'home_center_artifact', artifactId: alpha.artifactId, sha256: alpha.digest, byteLength: alpha.bytes.length}};
const created = await service.createFileOperation({admin, storage, user, args: createArgs});
assert.equal(created.operation, 'storage.filesystem.create'); assert.equal(created.file.path, '/work/input.bin'); assert.equal(created.file.sha256, alpha.digest); assert.equal(created.humanAcceptance, 'unreviewed'); assert.equal(created.transport.binaryInJson, false); assert.ok(Buffer.byteLength(JSON.stringify(created)) < 16 * 1024);
const writesAfterCreate = storage.writeCalls; const createReplay = await service.createFileOperation({admin, storage, user, args: createArgs});
assert.equal(createReplay.attached, true); assert.equal(createReplay.file.fileId, created.file.fileId); assert.equal(storage.writeCalls, writesAfterCreate, 'exact replay must not restage bytes or rewrite receipts');
await assert.rejects(service.createFileOperation({admin, storage, user, args: {...createArgs, path: '/work/conflict.bin'}}), (error) => error.code === 'storage.filesystem.idempotency_conflict');
await assert.rejects(service.statFileOperation({admin, user: otherUser, args: {fileId: created.file.fileId}}), (error) => error.code === 'storage.filesystem.file_not_found');

const appended = await service.appendFileOperation({admin, storage, user, args: {approved: true, requestId: 'append-beta-v1', fileId: created.file.fileId, expectedVersionId: created.version.versionId, source: {kind: 'home_center_artifact', artifactId: beta.artifactId, sha256: beta.digest, byteLength: beta.bytes.length}}});
const appendedBytes = Buffer.concat([alpha.bytes, beta.bytes]);
assert.equal(appended.operation, 'storage.filesystem.append'); assert.equal(appended.file.sha256, sha(appendedBytes)); assert.equal(appended.file.byteLength, appendedBytes.length); assert.equal(storage.combineCalls, 1);

const copied = await service.copyFileOperation({admin, storage, user, args: {approved: true, requestId: 'copy-v1', fileId: created.file.fileId, expectedVersionId: appended.version.versionId, path: '/copies/input.bin'}});
assert.equal(copied.operation, 'storage.filesystem.copy'); assert.equal(copied.file.sha256, appended.file.sha256); assert.equal(copied.transport.copiedBytes, 0);
const moved = await service.moveFileOperation({admin, storage, user, args: {approved: true, requestId: 'move-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId, path: '/archive/input.bin'}});
assert.equal(moved.file.path, '/archive/input.bin'); assert.equal(moved.version.versionId, copied.version.versionId);
const renamed = await service.renameFileOperation({admin, storage, user, args: {approved: true, requestId: 'rename-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId, name: 'renamed.bin'}});
assert.equal(renamed.file.path, '/archive/renamed.bin'); assert.equal(renamed.file.sha256, copied.file.sha256);

const overwritten = await service.overwriteFileOperation({admin, storage, user, args: {approved: true, requestId: 'overwrite-gamma-v1', fileId: created.file.fileId, expectedVersionId: appended.version.versionId, source: {kind: 'home_center_artifact', artifactId: gamma.artifactId, sha256: gamma.digest, byteLength: gamma.bytes.length}}});
assert.equal(overwritten.file.sha256, gamma.digest); assert.equal(overwritten.version.parentVersionId, appended.version.versionId);
const versions = await service.listVersionsOperation({admin, user, args: {fileId: created.file.fileId}});
assert.equal(versions.count, 3); assert.deepEqual(versions.versions.map((version) => version.ordinal), [3, 2, 1]);

const restoredVersion = await service.restoreFileOperation({admin, storage, user, args: {approved: true, requestId: 'restore-alpha-version-v1', fileId: created.file.fileId, expectedVersionId: overwritten.version.versionId, versionId: created.version.versionId}});
assert.equal(restoredVersion.operation, 'storage.filesystem.restore'); assert.equal(restoredVersion.file.sha256, alpha.digest); assert.equal(restoredVersion.version.parentVersionId, overwritten.version.versionId);
const download = await service.downloadFileOperation({admin, storage, user, args: {fileId: created.file.fileId}});
assert.equal(download.verification.ok, true); assert.equal(download.resourceLink.name, 'input.bin'); assert.equal(download.resourceLink.mimeType, 'application/octet-stream'); assert.equal(download.public, false); assert.match(download.resourceLink.uri, /\/filesystem\/files\/.+\/versions\/.+\/content$/);

const headResponse = new ResponseSink();
await service.streamFilesystemContent({admin, storage, user, fileId: created.file.fileId, versionId: restoredVersion.version.versionId, req: {method: 'HEAD', get: () => ''}, res: headResponse});
assert.equal(headResponse.headers['X-Content-SHA256'], alpha.digest); assert.equal(headResponse.headers['Content-Length'], String(alpha.bytes.length)); assert.equal(headResponse.headers['Content-Disposition'], 'attachment; filename="input.bin"'); assert.equal(headResponse.headers['Cache-Control'], 'private, no-store');
const rangeResponse = new ResponseSink(); const rangeDone = new Promise((resolve, reject) => rangeResponse.on('finish', resolve).on('error', reject));
await service.streamFilesystemContent({admin, storage, user, fileId: created.file.fileId, versionId: restoredVersion.version.versionId, req: {method: 'GET', get: (name) => name === 'Range' ? 'bytes=1-3' : ''}, res: rangeResponse});
await rangeDone; assert.equal(rangeResponse.statusCode, 206); assert.equal(rangeResponse.bytes().toString(), 'lph'); assert.equal(rangeResponse.headers['Content-Range'], 'bytes 1-3/5');

const activeList = await service.listFilesOperation({admin, user, args: {state: 'active'}});
assert.equal(activeList.count, 2); assert.deepEqual(activeList.items.map((file) => file.path), ['/archive/renamed.bin', '/work/input.bin']);
const trashed = await service.trashFileOperation({admin, storage, user, args: {approved: true, requestId: 'trash-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId}});
assert.equal(trashed.file.state, 'trash'); assert.equal(trashed.trash.retentionDays, 30); assert.match(trashed.trash.pointer.storageRef, /^gs:\/\/home-center-generated\/indexes\/filesystem\/v1\/trash\//);
const trashList = await service.listFilesOperation({admin, user, args: {state: 'trash'}}); assert.equal(trashList.count, 1); assert.equal(trashList.items[0].fileId, copied.file.fileId);
const restoredTrash = await service.restoreFileOperation({admin, storage, user, args: {approved: true, requestId: 'restore-trash-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId}});
assert.equal(restoredTrash.file.state, 'active'); assert.equal(restoredTrash.file.path, '/archive/renamed.bin'); assert.equal((await service.listFilesOperation({admin, user, args: {state: 'trash'}})).count, 0);

const lateReplays = await Promise.all([
  service.appendFileOperation({admin, storage, user, args: {approved: true, requestId: 'append-beta-v1', fileId: created.file.fileId, expectedVersionId: created.version.versionId, source: {kind: 'home_center_artifact', artifactId: beta.artifactId, sha256: beta.digest, byteLength: beta.bytes.length}}}),
  service.copyFileOperation({admin, storage, user, args: {approved: true, requestId: 'copy-v1', fileId: created.file.fileId, expectedVersionId: appended.version.versionId, path: '/copies/input.bin'}}),
  service.moveFileOperation({admin, storage, user, args: {approved: true, requestId: 'move-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId, path: '/archive/input.bin'}}),
  service.renameFileOperation({admin, storage, user, args: {approved: true, requestId: 'rename-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId, name: 'renamed.bin'}}),
  service.overwriteFileOperation({admin, storage, user, args: {approved: true, requestId: 'overwrite-gamma-v1', fileId: created.file.fileId, expectedVersionId: appended.version.versionId, source: {kind: 'home_center_artifact', artifactId: gamma.artifactId, sha256: gamma.digest, byteLength: gamma.bytes.length}}}),
  service.restoreFileOperation({admin, storage, user, args: {approved: true, requestId: 'restore-alpha-version-v1', fileId: created.file.fileId, expectedVersionId: overwritten.version.versionId, versionId: created.version.versionId}}),
  service.trashFileOperation({admin, storage, user, args: {approved: true, requestId: 'trash-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId}}),
  service.restoreFileOperation({admin, storage, user, args: {approved: true, requestId: 'restore-trash-v1', fileId: copied.file.fileId, expectedVersionId: copied.version.versionId}}),
]);
assert.equal(lateReplays.every((receipt) => receipt.attached === true), true, 'every mutation must attach on exact replay after later state changes');
await assert.rejects(
  service.appendFileOperation({admin, storage, user, args: {approved: true, requestId: 'append-beta-v1', fileId: created.file.fileId, expectedVersionId: created.version.versionId, source: {kind: 'home_center_artifact', artifactId: gamma.artifactId, sha256: gamma.digest, byteLength: gamma.bytes.length}}}),
  (error) => error.code === 'storage.filesystem.idempotency_conflict',
  'changed inputs must still conflict before current-head validation',
);

assert.equal([...storage.objects.keys()].some((key) => /base64|pty/i.test(key)), false);
assert.equal(JSON.stringify([...db.store.values()]).includes(owner), true, 'owner provenance must be retained in file records');
assert.equal(JSON.stringify(created).includes(alpha.bytes.toString('base64')), false, 'receipt must not contain source bytes');
console.log('Authenticated GCS filesystem contract passed.');
