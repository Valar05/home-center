import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const service = require('../functions/artifact_ingest_service.js');
const bridge = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const {HOME_CENTER_CONNECTOR_SCHEMA_REVISION} = require('../functions/home_center_mcp.js');
const publicManifest = JSON.parse(fs.readFileSync(new URL('../contracts/home-center-public-tool-manifest.v1.json', import.meta.url), 'utf8'));

class FakeFile {
  constructor(bucket, name) {
    this.bucket = bucket;
    this.name = name;
  }
  async save(bytes, options = {}) {
    if (this.bucket.objects.has(this.name) && options.preconditionOpts?.ifGenerationMatch === 0) {
      const error = new Error('precondition failed');
      error.code = 412;
      throw error;
    }
    this.bucket.objects.set(this.name, {bytes: Buffer.from(bytes), metadata: options.metadata || {}});
  }
  async download() {
    const entry = this.bucket.objects.get(this.name);
    if (!entry) throw new Error('not found: ' + this.name);
    return [Buffer.from(entry.bytes)];
  }
  async copy(destination, options = {}) {
    const [bytes] = await this.download();
    await destination.save(bytes, options);
    return [destination];
  }
  async delete() {
    this.bucket.objects.delete(this.name);
  }
}

class FakeBucket {
  constructor(name) {
    this.name = name;
    this.objects = new Map();
  }
  file(name) {
    return new FakeFile(this, name);
  }
  async getFiles({prefix}) {
    return [[...this.objects.keys()].filter((name) => name.startsWith(prefix)).sort().map((name) => this.file(name))];
  }
  async combine(sources, destination, options = {}) {
    const buffers = [];
    for (const source of sources) buffers.push((await source.download())[0]);
    await destination.save(Buffer.concat(buffers), options);
    return [destination];
  }
}

class FakeStorage {
  constructor() {
    this.buckets = new Map();
  }
  bucket(name) {
    if (!this.buckets.has(name)) this.buckets.set(name, new FakeBucket(name));
    return this.buckets.get(name);
  }
}

class FakeDoc {
  constructor(map, id) {
    this.map = map;
    this.id = id;
  }
  async get() {
    const value = this.map.get(this.id);
    return {exists: value !== undefined, data: () => value};
  }
  async create(value) {
    if (this.map.has(this.id)) throw new Error('already exists');
    this.map.set(this.id, structuredClone(value));
  }
  async set(value) {
    this.map.set(this.id, structuredClone(value));
  }
}

class FakeFirestore {
  constructor() {
    this.collections = new Map();
  }
  collection(name) {
    if (!this.collections.has(name)) this.collections.set(name, new Map());
    const map = this.collections.get(name);
    return {doc: (id) => new FakeDoc(map, id)};
  }
}

const identity = service.normalizeIdentity(
  {email: 'dclarke1005@gmail.com'},
  {
    requestId: 'rotoscoping-heavy-bag-motion-packet-v1',
    artifactId: 'heavy-bag-combination-8cbb9ac8b17a',
    artifactKind: 'source-motion',
    project: 'rotoscoping',
    name: 'heavy-bag-combination-8cbb9ac8b17a-motion-packet.zip',
    mimeType: 'application/zip',
    expectedByteCount: 3,
    expectedSha256: createHash('sha256').update(Buffer.from('abc')).digest('hex'),
    provenance: {sourceAuthority: 'immutable-original-capture', sourceStartSeconds: 1.1, sourceEndSeconds: 9.15},
  },
);
assert.equal(identity.objectName, 'rotoscoping/dclarke1005@gmail.com/source-motion/heavy-bag-combination-8cbb9ac8b17a/heavy-bag-combination-8cbb9ac8b17a-motion-packet.zip');
assert.equal(identity.lifecycleState, 'proposed');
assert.equal(service.assertExpected(identity, Buffer.from('abc')).byteCount, 3);
assert.throws(() => service.normalizeIdentity({email: 'dclarke1005@gmail.com'}, {...identity, requestId: 'x', lifecycleState: 'accepted'}), /separate human promotion/);
assert.throws(() => service.assertExpected(identity, Buffer.from('abd')), /SHA-256/);

const storage = new FakeStorage();
const firestore = new FakeFirestore();
const admin = {firestore: () => firestore};
const user = {email: 'dclarke1005@gmail.com'};
const payload = Buffer.from('motion-packet');
const digest = createHash('sha256').update(payload).digest('hex');
const uploadArgs = {
  requestId: 'motion-packet-direct-v1',
  artifactId: 'motion-packet-direct',
  artifactKind: 'source-motion',
  project: 'rotoscoping',
  expectedByteCount: payload.length,
  expectedSha256: digest,
  provenance: {sourceAuthority: 'immutable-original-capture'},
  file: {
    name: 'motion.zip',
    type: 'application/zip',
    size: payload.length,
    arrayBuffer: async () => payload,
  },
};
const direct = await service.ingestArtifactUploadOperation({admin, storage, user, args: uploadArgs});
assert.equal(direct.verified, true);
assert.equal(direct.lifecycleState, 'proposed');
assert.equal(direct.destination.sha256, digest);
assert.equal(direct.commandCenter.recorded, true);
assert.equal(direct.commandCenter.documentId, 'dclarke1005@gmail.com--motion-packet-direct');
assert.equal(direct.indexes.byId.reused, false);
for (const index of Object.values(direct.indexes)) {
  assert.equal("bytes" in index, false, "ingest receipts must not serialize immutable index bodies");
  assert.match(index.sha256, /^[a-f0-9]{64}$/);
  assert.ok(index.byteCount > 0);
}
assert.ok(Buffer.byteLength(JSON.stringify(direct)) < 16 * 1024, "ingest receipt must remain bounded");
const replay = await service.ingestArtifactUploadOperation({admin, storage, user, args: uploadArgs});
assert.equal(replay.reused, true);
assert.equal(replay.indexes.byId.reused, true);
assert.match(direct.indexes.bySha256.objectName, /^indexes\/artifacts\/v2\/by-owner-sha256\/dclarke1005@gmail\.com\//);
const foundForOwner = await service.findArtifactBySha256Operation({storage, user, args: {sha256: digest}});
assert.equal(foundForOwner.manifest.artifactId, direct.artifactId);
await assert.rejects(
  service.findArtifactBySha256Operation({storage, user: {email: 'someone@example.com'}, args: {sha256: digest}}),
  (error) => error.code === 'artifact_digest_not_found' && error.status === 404,
  'legacy digest compatibility must not expose another owner',
);

const replaySessionId = "resumable-completed-replay-v1";
const directManifest = JSON.parse(storage.bucket(service.ARTIFACT_BUCKET).objects.get("indexes/artifacts/v1/by-id/dclarke1005@gmail.com/motion-packet-direct.json").bytes.toString("utf8"));
await firestore.collection("artifactTransportUploadSessions").doc(replaySessionId).create({
  requestId: replaySessionId,
  state: "completed",
  ownerEmail: user.email,
  identity: {...identity, requestId: replaySessionId, artifactId: directManifest.artifactId},
  artifact: {sha256: directManifest.destination.sha256, byteLength: directManifest.destination.byteCount},
  chunks: [{index: 0, offset: 0, byteCount: directManifest.destination.byteCount, sha256: directManifest.destination.sha256}],
  objectName: "deleted-staging-object",
  uploadUrl: "",
});
const completedReplay = await service.commitResumableArtifactIngestOperation({admin, storage, user, args: {approved: true, requestId: replaySessionId}});
assert.equal(completedReplay.transport.exactReplay, true);
assert.equal(completedReplay.transport.transferredBytes, 0);
assert.equal(completedReplay.destination.sha256, directManifest.destination.sha256);
assert.equal(completedReplay.reused, true);
assert.equal(storage.bucket(service.ARTIFACT_BUCKET).objects.has("deleted-staging-object"), false);

const chunkPayload = Buffer.from('abcdefghijklmnopqrstuvwxyz0123456789-CHUNKED-MOTION-PACKET');
const chunkDigest = createHash('sha256').update(chunkPayload).digest('hex');
const chunkArgs = {
  approved: true,
  requestId: 'motion-packet-chunked-v1',
  artifactId: 'motion-packet-chunked',
  artifactKind: 'source-motion',
  project: 'rotoscoping',
  name: 'motion-chunked.zip',
  mimeType: 'application/zip',
  expectedByteCount: chunkPayload.length,
  expectedSha256: chunkDigest,
  provenance: {sourceAuthority: 'immutable-original-capture'},
};
await service.beginArtifactIngestOperation({admin, user, args: chunkArgs});
const chunks = [...chunkPayload].map((byte) => Buffer.from([byte]));
for (const [chunkIndex, chunk] of chunks.entries()) {
  await service.appendArtifactChunkOperation({
    storage,
    user,
    args: {
      ...chunkArgs,
      chunkIndex,
      chunkBase64: chunk.toString('base64'),
      chunkSha256: createHash('sha256').update(chunk).digest('hex'),
    },
  });
}
const committed = await service.commitArtifactIngestOperation({
  admin,
  storage,
  user,
  args: {...chunkArgs, expectedChunks: chunks.length},
});
assert.equal(committed.verified, true);
assert.equal(committed.destination.sha256, chunkDigest);
assert.equal(committed.transport.stagedObjectsDisposed, true);
assert.ok(Object.values(committed.indexes).every((index) => !("bytes" in index)), "chunked commit leaked index bytes");
assert.ok(Buffer.byteLength(JSON.stringify(committed)) < 16 * 1024, "chunked commit receipt must remain bounded");
assert.equal([...storage.bucket(service.ARTIFACT_BUCKET).objects.keys()].some((name) => name.includes('/chunks/')), false);

const abortArgs = {...chunkArgs, requestId: 'motion-packet-abort-v1', artifactId: 'motion-packet-abort'};
await service.beginArtifactIngestOperation({admin, user, args: abortArgs});
await service.appendArtifactChunkOperation({
  storage,
  user,
  args: {...abortArgs, chunkIndex: 0, chunkBase64: Buffer.from('waste').toString('base64')},
});
const aborted = await service.abortArtifactIngestOperation({admin, storage, user, args: abortArgs});
assert.equal(aborted.aborted, true);
assert.equal(aborted.disposedObjectCount, 1);
assert.equal(aborted.canonicalArtifactMutated, false);

const markers = [
  "'storage_ingest_artifact'",
  "server.registerTool('storage_ingest_artifact'",
  "file: z.file()",
  "artifactOperationEntries()",
  "operation === 'storage.artifact.begin'",
  "operation === 'storage.artifact.append_chunk'",
  "operation === 'storage.artifact.commit'",
  "operation === 'storage.artifact.abort'",
  "operation === 'storage.artifact.get'",
  "operation === 'storage.artifact.find_by_sha256'",
  "ingestArtifactUploadOperation",
  "storageIngestArtifactCatalogInputSchema",
];
for (const marker of markers) assert.equal(bridge.includes(marker), true, 'missing bridge marker: ' + marker);
assert.equal(HOME_CENTER_CONNECTOR_SCHEMA_REVISION, publicManifest.registryRevision, 'ingest must inherit the generated Home MCP registry revision');
assert.match(bridge, /function driveOperationRegistry\(\)[\s\S]*?version: '2026-07-30\.audio-reader-link-v1'/);

console.log('Storage artifact ingest contract passed.');
