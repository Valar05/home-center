import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Readable, Writable} from 'node:stream';
import homeCenter from '../functions/home_center_mcp.js';

const {ingestDriveAudioOperation} = homeCenter;
const source = Buffer.from('verified audio bytes');
const objectStore = new Map();

class FakeFile {
  constructor(name) { this.name = name; }
  async exists() { return [objectStore.has(this.name)]; }
  createWriteStream(options = {}) {
    const chunks = [];
    return new Writable({
      write(chunk, _encoding, callback) { chunks.push(Buffer.from(chunk)); callback(); },
      final(callback) {
        objectStore.set(this.fileName, {bytes: Buffer.concat(chunks), metadata: options.metadata || {}});
        callback();
      },
    }).on('pipe', function() { this.fileName = this.fileName || ''; }).on('newListener', function() {});
  }
  createReadStream() {
    const item = objectStore.get(this.name);
    if (!item) return Readable.from((async function* () { throw new Error('missing fake object'); })());
    return Readable.from([item.bytes]);
  }
  async copy(destination) {
    const item = objectStore.get(this.name);
    if (!item) throw new Error('missing staged object');
    if (objectStore.has(destination.name)) throw new Error('destination exists');
    objectStore.set(destination.name, {bytes: Buffer.from(item.bytes), metadata: JSON.parse(JSON.stringify(item.metadata || {}))});
    return [destination];
  }
  async setMetadata(metadata) {
    const item = objectStore.get(this.name);
    item.metadata = {...item.metadata, ...metadata, metadata: {...(item.metadata && item.metadata.metadata || {}), ...(metadata.metadata || {})}};
    return [item.metadata];
  }
  async getMetadata() {
    const item = objectStore.get(this.name);
    return [{size: String(item.bytes.length), contentType: item.metadata.contentType || '', metadata: item.metadata.metadata || {}}];
  }
  async delete() { objectStore.delete(this.name); return [{}]; }
}

class FakeBucket {
  file(name) {
    const file = new FakeFile(name);
    const originalCreate = file.createWriteStream.bind(file);
    file.createWriteStream = (options = {}) => {
      const stream = originalCreate(options);
      stream.fileName = name;
      return stream;
    };
    return file;
  }
}

const storage = {bucket(name) { assert.equal(name, 'home-center-generated'); return new FakeBucket(); }};
const calls = [];
const google = {
  drive() {
    return {files: {async get(params, options = {}) {
      calls.push({params, options});
      if (params.alt === 'media') {
        assert.equal(options.responseType, 'stream');
        return {data: Readable.from([source])};
      }
      return {data: {
        id: 'drive-file-1234',
        name: 'Vacation Final.ogg',
        mimeType: 'audio/ogg',
        size: String(source.length),
        md5Checksum: 'drive-md5',
        webViewLink: 'https://drive.example/file',
      }};
    }}};
  },
};
const audit = [];
const args = {
  fileId: 'drive-file-1234',
  requestId: 'audio-ingest-contract-20260726',
  approved: true,
  project: 'vacation-of-a-lifetime',
  stage: 'finals',
  sourcePath: 'Generated/Vacation of a Lifetime/Audio/Day 3/Finals/Vacation Final.ogg',
  expectedSize: source.length,
  expectedDriveMd5: 'drive-md5',
};
const result = await ingestDriveAudioOperation({
  google,
  admin: {},
  auth: {},
  user: {email: 'dclarke1005@gmail.com'},
  args,
  storage,
  recordAudit: async (...entry) => audit.push(entry),
});
assert.equal(result.verified, true);
assert.equal(result.reused, false);
assert.equal(result.driveMutated, false);
assert.equal(result.source.byteCount, source.length);
assert.equal(result.source.sha256, createHash('sha256').update(source).digest('hex'));
assert.match(result.destination.storageRef, /^gs:\/\/home-center-generated\/audio\//);
assert.equal(result.destination.byteCount, source.length);
assert.equal(result.destination.sha256, result.source.sha256);
assert.equal(audit.length, 1);
assert.equal([...objectStore.keys()].some((name) => name.startsWith('temp/')), false);
const reused = await ingestDriveAudioOperation({
  google,
  admin: {},
  auth: {},
  user: {email: 'dclarke1005@gmail.com'},
  args,
  storage,
  recordAudit: async () => {},
});
assert.equal(reused.verified, true);
assert.equal(reused.reused, true);
await assert.rejects(() => ingestDriveAudioOperation({
  google,
  admin: {},
  auth: {},
  user: {email: 'dclarke1005@gmail.com'},
  args: {...args, approved: false},
  storage,
  recordAudit: async () => {},
}), /approved=true/);
await assert.rejects(() => ingestDriveAudioOperation({
  google,
  admin: {},
  auth: {},
  user: {email: 'dclarke1005@gmail.com'},
  args: {...args, requestId: 'audio-ingest-wrong-md5', expectedDriveMd5: 'wrong'},
  storage,
  recordAudit: async () => {},
}), /MD5/);
console.log(JSON.stringify({ok: true, storageRef: result.destination.storageRef, sha256: result.destination.sha256, reused: reused.reused}, null, 2));
