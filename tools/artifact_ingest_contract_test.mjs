import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const service = require('../functions/artifact_ingest_service.js');
const bridge = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');

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
const replay = await service.ingestArtifactUploadOperation({admin, storage, user, args: uploadArgs});
assert.equal(replay.reused, true);
assert.equal(replay.indexes.byId.reused, true);

const chunkPayload = Buffer.from('chunked-motion-packet');
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
const chunks = [chunkPayload.subarray(0, 7), chunkPayload.subarray(7)];
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
assert.equal([...storage.bucket(service.ARTIFACT_BUCKET).objects.keys()].some((name) => name.includes('/chunks/')), false);

const markers = [
  "const HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-07-27.storage-artifact-ingest-v1'",
  "'storage_ingest_artifact'",
  "server.registerTool('storage_ingest_artifact'",
  "file: z.file()",
  "artifactOperationEntries()",
  "operation === 'storage.artifact.begin'",
  "operation === 'storage.artifact.append_chunk'",
  "operation === 'storage.artifact.commit'",
  "operation === 'storage.artifact.get'",
  "operation === 'storage.artifact.find_by_sha256'",
  "ingestArtifactUploadOperation",
  "storageIngestArtifactCatalogInputSchema",
];
for (const marker of markers) assert.equal(bridge.includes(marker), true, 'missing bridge marker: ' + marker);

console.log('Storage artifact ingest contract passed.');
