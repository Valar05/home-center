import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Readable} from 'node:stream';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const homeCenter = require('../functions/home_center_mcp.js');
const publicManifest = require('../contracts/home-center-public-tool-manifest.v1.json');

class Document {
  constructor(store, key) { this.store = store; this.key = key; }
  async get() { return {exists: this.store.has(this.key), data: () => this.store.get(this.key)}; }
  async set(value) { this.store.set(this.key, structuredClone(value)); }
}

function fakeAdmin() {
  const stores = new Map();
  const firestore = () => ({
    collection(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const store = stores.get(name);
      return {
        doc(id) { return new Document(store, id); },
        async add(value) { store.set('auto-' + store.size, structuredClone(value)); },
      };
    },
  });
  firestore.FieldValue = {serverTimestamp: () => 'server-time'};
  return {firestore, stores};
}

function fakeGoogle({readbackTransform = (bytes) => bytes} = {}) {
  const state = {created: 0, uploaded: Buffer.alloc(0), responseTypes: []};
  return {
    state,
    drive() {
      return {files: {
        async list() { return {data: {files: []}}; },
        async create(params) {
          state.created += 1;
          const chunks = [];
          for await (const chunk of params.media.body) chunks.push(Buffer.from(chunk));
          state.uploaded = Buffer.concat(chunks);
          return {data: {id: 'file-12345678', name: params.requestBody.name, mimeType: params.requestBody.mimeType, parents: params.requestBody.parents || [], appProperties: params.requestBody.appProperties, webViewLink: 'https://drive.google.test/file-12345678'}};
        },
        async get(_params, options = {}) {
          state.responseTypes.push(options.responseType);
          return {data: Readable.from([readbackTransform(state.uploaded)])};
        },
      }};
    },
  };
}

const bytes = Buffer.from([0, 255, 1, 2, 3, 10, 13, 128, 42]);
const sha256 = createHash('sha256').update(bytes).digest('hex');
const user = {email: 'dclarke1005@gmail.com', uid: 'owner', authKind: 'oauth'};
function upload() {
  return {name: 'fixture.bin', type: 'application/octet-stream', size: bytes.length, sha256, createReadStream: () => Readable.from([bytes.subarray(0, 3), bytes.subarray(3)])};
}

const admin = fakeAdmin();
const google = fakeGoogle();
const result = await homeCenter.driveIngestFileOperationWithUpload({
  google,
  admin,
  auth: {},
  user,
  args: {requestId: 'drive-binary-write-proof', expectedSha256: sha256},
  uploaded: upload(),
});

assert.equal(result.verified, true);
assert.equal(result.byteCount, bytes.length);
assert.equal(result.readbackByteCount, bytes.length);
assert.equal(result.sha256, sha256);
assert.equal(result.readbackSha256, sha256);
assert.deepEqual(google.state.uploaded, bytes);
assert.deepEqual(google.state.responseTypes, ['stream']);
assert.equal(google.state.created, 1);

const replay = await homeCenter.driveIngestFileOperationWithUpload({google, admin, auth: {}, user, args: {requestId: 'drive-binary-write-proof', expectedSha256: sha256}, uploaded: upload()});
assert.equal(replay.idempotent, true);
assert.equal(google.state.created, 1);

await assert.rejects(
  () => homeCenter.driveIngestFileOperationWithUpload({google: fakeGoogle(), admin: fakeAdmin(), auth: {}, user, args: {requestId: 'drive-binary-write-bad-hash', expectedSha256: '0'.repeat(64)}, uploaded: upload()}),
  (error) => error.code === 'drive_ingest_expected_sha256_mismatch',
);
await assert.rejects(
  () => homeCenter.driveIngestFileOperationWithUpload({google: fakeGoogle({readbackTransform: (value) => Buffer.concat([value, Buffer.from([9])])}), admin: fakeAdmin(), auth: {}, user, args: {requestId: 'drive-binary-write-bad-readback'}, uploaded: upload()}),
  (error) => error.code === 'drive_ingest_readback_mismatch',
);

assert.equal(homeCenter.HOME_CENTER_DIRECT_FILE_TOOLS.join(','), 'drive_ingest_file,storage_ingest_artifact');
assert.equal(homeCenter.HOME_CENTER_CONNECTOR_SCHEMA_REVISION, publicManifest.registryRevision, 'public manifest must be regenerated with the same registry revision');
console.log(JSON.stringify({ok: true, byteCount: result.byteCount, sha256: result.sha256, streamedUpload: true, streamedReadback: true, topLevelToolsUnchanged: true}, null, 2));
