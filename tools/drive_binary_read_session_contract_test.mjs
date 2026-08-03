import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Readable} from 'node:stream';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const service = require('../functions/drive_binary_read_service.js');

class DocRef {
  constructor(node) { this.node = node; }
  async get() { return {exists: this.node.value !== undefined, data: () => structuredClone(this.node.value)}; }
  async set(value, options = {}) { this.node.value = options.merge && this.node.value ? {...this.node.value, ...structuredClone(value)} : structuredClone(value); }
  collection(name) {
    if (!this.node.collections.has(name)) this.node.collections.set(name, new Map());
    return new CollectionRef(this.node.collections.get(name));
  }
}
class CollectionRef {
  constructor(nodes) { this.nodes = nodes; }
  doc(id) {
    if (!this.nodes.has(id)) this.nodes.set(id, {value: undefined, collections: new Map()});
    return new DocRef(this.nodes.get(id));
  }
  async get() {
    return {docs: [...this.nodes.entries()].filter(([, node]) => node.value !== undefined).map(([id, node]) => ({id, data: () => structuredClone(node.value)}))};
  }
}
function fakeAdmin() {
  const roots = new Map();
  return {firestore() { return {collection(name) { if (!roots.has(name)) roots.set(name, new Map()); return new CollectionRef(roots.get(name)); }}; }};
}

function fakeGoogle(initialBytes, overrides = {}) {
  const state = {
    bytes: Buffer.from(initialBytes),
    metadata: {id: 'binary-file-1234', name: 'proof.bin', mimeType: 'application/octet-stream', size: String(initialBytes.length), md5Checksum: 'fixture-md5', modifiedTime: '2026-08-02T12:00:00Z', ...overrides},
    ranges: [],
    fullReads: 0,
  };
  return {
    state,
    drive() {
      return {files: {async get(params, options = {}) {
        if (!params.alt) return {data: {...state.metadata, size: String(state.bytes.length)}};
        if (options.headers?.Range) {
          state.ranges.push(options.headers.Range);
          const match = options.headers.Range.match(/^bytes=(\d+)-(\d+)$/);
          return {data: state.bytes.subarray(Number(match[1]), Number(match[2]) + 1)};
        }
        state.fullReads += 1;
        return {data: Readable.from([state.bytes.subarray(0, 3), state.bytes.subarray(3)])};
      }}};
    },
  };
}

const bytes = Buffer.from([0, 255, 1, 2, 3, 4, 5, 128, 42]);
const wholeSha = createHash('sha256').update(bytes).digest('hex');
const admin = fakeAdmin();
const google = fakeGoogle(bytes);
const user = {email: 'owner@example.com'};
const requestId = 'binary-session-proof';

const begun = await service.beginDriveBinaryReadOperation({google, admin, auth: {}, user, args: {fileId: 'binary-file-1234', requestId, chunkSize: 4}});
assert.equal(begun.fileSha256, wholeSha);
assert.equal(begun.chunkCount, 3);
assert.equal(begun.verifiedSource, true);
const resumed = await service.beginDriveBinaryReadOperation({google, admin, auth: {}, user, args: {fileId: 'binary-file-1234', requestId, chunkSize: 4}});
assert.equal(resumed.resumed, true);

const first = await service.readDriveBinarySessionChunkOperation({google, admin, auth: {}, user, args: {requestId, chunkIndex: 0}});
assert.deepEqual(Buffer.from(first.chunkBase64, 'base64'), bytes.subarray(0, 4));
assert.equal(first.chunkSha256, createHash('sha256').update(bytes.subarray(0, 4)).digest('hex'));
const firstRetry = await service.readDriveBinarySessionChunkOperation({google, admin, auth: {}, user, args: {requestId, chunkIndex: 0}});
assert.equal(firstRetry.chunkSha256, first.chunkSha256);

const interrupted = await service.driveBinaryReadStatusOperation({google, admin, auth: {}, user, args: {requestId}});
assert.deepEqual(interrupted.servedChunks, [0]);
assert.deepEqual(interrupted.missingChunks, [1, 2]);
await assert.rejects(
  () => service.completeDriveBinaryReadOperation({google, admin, auth: {}, user, args: {requestId, reconstructedByteCount: bytes.length, reconstructedSha256: wholeSha}}),
  (error) => error.code === 'drive_binary_read_incomplete',
);

const chunks = [Buffer.from(first.chunkBase64, 'base64')];
for (const chunkIndex of interrupted.missingChunks) {
  const chunk = await service.readDriveBinarySessionChunkOperation({google, admin, auth: {}, user, args: {requestId, chunkIndex}});
  chunks.push(Buffer.from(chunk.chunkBase64, 'base64'));
}
const reconstructed = Buffer.concat(chunks);
assert.deepEqual(reconstructed, bytes);
await assert.rejects(
  () => service.completeDriveBinaryReadOperation({google, admin, auth: {}, user, args: {requestId, reconstructedByteCount: bytes.length, reconstructedSha256: '0'.repeat(64)}}),
  (error) => error.code === 'drive_binary_read_reconstruction_mismatch',
);
const completed = await service.completeDriveBinaryReadOperation({google, admin, auth: {}, user, args: {requestId, reconstructedByteCount: reconstructed.length, reconstructedSha256: wholeSha}});
assert.equal(completed.verified, true);
assert.equal(completed.readbackSha256, wholeSha);
assert.equal(completed.readbackByteCount, bytes.length);
assert.deepEqual(google.state.ranges, ['bytes=0-3', 'bytes=0-3', 'bytes=4-7', 'bytes=8-8']);
assert.equal(google.state.fullReads, 2);

await assert.rejects(
  () => service.driveBinaryReadStatusOperation({google, admin, auth: {}, user: {email: 'intruder@example.com'}, args: {requestId}}),
  (error) => error.code === 'drive_binary_read_session_forbidden',
);

const mutableGoogle = fakeGoogle(bytes);
const mutableAdmin = fakeAdmin();
await service.beginDriveBinaryReadOperation({google: mutableGoogle, admin: mutableAdmin, auth: {}, user, args: {fileId: 'binary-file-1234', requestId: 'binary-session-mutable'}});
mutableGoogle.state.metadata.modifiedTime = '2026-08-02T12:01:00Z';
await assert.rejects(
  () => service.driveBinaryReadStatusOperation({google: mutableGoogle, admin: mutableAdmin, auth: {}, user, args: {requestId: 'binary-session-mutable'}}),
  (error) => error.code === 'drive_binary_read_source_changed',
);

await assert.rejects(
  () => service.beginDriveBinaryReadOperation({google: fakeGoogle(bytes, {mimeType: 'application/vnd.google-apps.document'}), admin: fakeAdmin(), auth: {}, user, args: {fileId: 'binary-file-1234', requestId: 'binary-session-native'}}),
  (error) => error.code === 'drive_binary_read_google_native_unsupported',
);

console.log(JSON.stringify({ok: true, byteCount: completed.readbackByteCount, sha256: completed.readbackSha256, chunks: completed.chunkCount, resumed: true, ownerBound: true, sourceMutationRejected: true}, null, 2));
