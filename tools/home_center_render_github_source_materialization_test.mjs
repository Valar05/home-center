#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import Module from 'node:module';
import {Writable} from 'node:stream';

const saves = [];
const deletes = [];
const objects = new Map();
function fakeFile(bucketId, objectName) {
  return {
    createWriteStream(options) {
      const chunks = [];
      return new Writable({
        write(chunk, _encoding, callback) { chunks.push(Buffer.from(chunk)); callback(); },
        final(callback) { objects.set(objectName, {bucketId, objectName, bytes: Buffer.concat(chunks), options}); callback(); },
      });
    },
    async move(finalName) {
      const record = objects.get(objectName);
      if (!record) throw new Error('missing temp object ' + objectName);
      objects.delete(objectName);
      objects.set(finalName, {...record, objectName: finalName, movedFrom: objectName});
    },
    async setMetadata(metadata) {
      const record = objects.get(objectName);
      if (!record) throw new Error('missing object for metadata ' + objectName);
      record.metadata = metadata;
      saves.push(record);
    },
    async save(bytes, options = {}) {
      const record = {bucketId, objectName, bytes: Buffer.isBuffer(bytes) ? bytes : Buffer.from(String(bytes)), options};
      objects.set(objectName, record);
      saves.push(record);
    },
    async exists() { return [objects.has(objectName)]; },
    async download() {
      const record = objects.get(objectName);
      if (!record) throw new Error('missing object ' + objectName);
      return [record.bytes];
    },
    async delete() { deletes.push(objectName); objects.delete(objectName); },
  };
}
const originalLoad = Module._load;
Module._load = function patchedLoad(request, parent, isMain) {
  if (request === '@google-cloud/storage') {
    return {Storage: class FakeStorage { bucket(bucketId) { return {file(objectName) { return fakeFile(bucketId, objectName); }}; } }};
  }
  return originalLoad.call(this, request, parent, isMain);
};

const require = createRequire(import.meta.url);
const {materializeHomeCenterRenderSources} = require('../functions/home_center_mcp.js');

function minimalGlb() {
  const json = Buffer.from('{"asset":{"version":"2.0"}}', 'utf8');
  const paddedJson = Buffer.concat([json, Buffer.alloc((4 - (json.length % 4)) % 4, 0x20)]);
  const total = 12 + 8 + paddedJson.length;
  const out = Buffer.alloc(total);
  out.write('glTF', 0, 'ascii');
  out.writeUInt32LE(2, 4);
  out.writeUInt32LE(total, 8);
  out.writeUInt32LE(paddedJson.length, 12);
  out.write('JSON', 16, 'ascii');
  paddedJson.copy(out, 20);
  return out;
}
function tokenHash(value) { return createHash('sha256').update(String(value || '')).digest('hex'); }

const token = 'home-center-test-token';
const admin = {
  firestore() {
    return {
      collection(name) {
        assert.equal(name, 'mcpOAuthAccessTokens');
        return {doc(id) { assert.equal(id, tokenHash(token)); return {async get() { return {exists: true, data: () => ({email: 'drew@example.com', expiresAtMs: Date.now() + 60000, googleTokens: {access_token: 'google-access-token'}}), ref: {async set() {}}}; }}; }};
      },
    };
  },
};
const extra = {requestInfo: {headers: {authorization: 'Bearer ' + token}}};
const glbBytes = minimalGlb();
let fetched = null;
let fetchCount = 0;
global.fetch = async (url, options = {}) => {
  fetchCount += 1;
  fetched = {url, headers: options.headers || {}};
  assert.equal(options.headers.Authorization, 'Bearer github-secret-token');
  assert.equal(options.headers.Accept, 'application/vnd.github.raw');
  return new Response(glbBytes, {status: 200, headers: {'content-length': String(glbBytes.length), 'content-type': 'model/gltf-binary'}});
};

const google = {auth: {OAuth2: class FakeOAuth2 { setCredentials(credentials) { this.credentials = credentials; } on() {} }}};

const out = await materializeHomeCenterRenderSources({
  google, admin, googleClientId: 'client', googleClientSecret: 'secret', extra,
  githubToken: () => 'github-secret-token',
  args: {
    idempotencyKey: 'github-source-test',
    glbSource: {provider: 'github', repository: 'Valar05/pose-lab-v2', ref: '605e8f128c9be8f586526517945e6747db44df7a', path: 'public/assets/vanguard/vanguard_rigged_animations.glb'},
    scriptText: 'print(1)',
  },
});
assert.match(fetched.url, /\/repos\/Valar05\/pose-lab-v2\/contents\/public\/assets\/vanguard\/vanguard_rigged_animations\.glb\?ref=605e8f128c9be8f586526517945e6747db44df7a$/);
assert.equal(fetchCount, 1, 'GitHub GLB source must be fetched once on first materialization');
const cachedObject = saves.find((record) => /github-cache\/glb\/.+vanguard_rigged_animations\.glb$/.test(record.objectName));
assert(cachedObject, 'GitHub GLB source must be staged into durable cache');
assert.equal(Buffer.compare(cachedObject.bytes, glbBytes), 0, 'staged GLB bytes must match GitHub response bytes');
assert(out.glbRef.startsWith('gs://home-center-dclar-command-center-renders/command-center-render-inputs/github-cache/glb/'));
assert.equal(out.scriptText, 'print(1)');
assert.equal(out.stagedInputs.length, 1);
assert.equal(out.stagedInputs[0].sha256, createHash('sha256').update(glbBytes).digest('hex'));
assert.equal(out.stagedInputs[0].byteCount, glbBytes.length);
assert.equal(out.stagedInputs[0].materializedFrom, 'glbGitHubSource');
assert.equal(out.stagedInputs[0].cacheHit, false);
assert(out.stagedInputs[0].timings.githubStreamAndValidateMs >= 0);
assert.equal(out.stagedInputs[0].sourceRef, 'github://Valar05/pose-lab-v2@605e8f128c9be8f586526517945e6747db44df7a/public/assets/vanguard/vanguard_rigged_animations.glb');
assert.deepEqual(out.stagedInputs[0].source, {provider: 'github', repository: 'Valar05/pose-lab-v2', ref: '605e8f128c9be8f586526517945e6747db44df7a', path: 'public/assets/vanguard/vanguard_rigged_animations.glb'});

const cachedOut = await materializeHomeCenterRenderSources({
  google, admin, googleClientId: 'client', googleClientSecret: 'secret', extra,
  githubToken: () => 'github-secret-token',
  args: {
    idempotencyKey: 'github-source-test-cached',
    glbSource: {provider: 'github', repository: 'Valar05/pose-lab-v2', ref: '605e8f128c9be8f586526517945e6747db44df7a', path: 'public/assets/vanguard/vanguard_rigged_animations.glb'},
    scriptText: 'print(1)',
  },
});
assert.equal(fetchCount, 1, 'cached GitHub GLB materialization must not refetch source bytes');
assert.equal(cachedOut.stagedInputs[0].materializedFrom, 'glbGitHubSourceCache');
assert.equal(cachedOut.stagedInputs[0].cacheHit, true);
assert.equal(cachedOut.glbRef, out.glbRef);

await assert.rejects(() => materializeHomeCenterRenderSources({google, admin, googleClientId: 'client', googleClientSecret: 'secret', extra, githubToken: () => 'github-secret-token', args: {idempotencyKey: 'ambiguous', glbRef: 'gs://bucket/file.glb', glbSource: {provider: 'github', repository: 'Valar05/pose-lab-v2', ref: 'main', path: 'a.glb'}, scriptText: 'print(1)'}}), /Exactly one GLB source/);
await assert.rejects(() => materializeHomeCenterRenderSources({google, admin, googleClientId: 'client', googleClientSecret: 'secret', extra, githubToken: () => 'github-secret-token', args: {idempotencyKey: 'missing', scriptText: 'print(1)'}}), /Exactly one GLB source/);

global.fetch = async () => new Response(Buffer.from('not a glb file payload'), {status: 200, headers: {'content-length': '22', 'content-type': 'application/octet-stream'}});
await assert.rejects(() => materializeHomeCenterRenderSources({google, admin, googleClientId: 'client', googleClientSecret: 'secret', extra, githubToken: () => 'github-secret-token', args: {idempotencyKey: 'invalid-glb', glbSource: {provider: 'github', repository: 'Valar05/pose-lab-v2', ref: 'main', path: 'bad.glb'}, scriptText: 'print(1)'}}), /missing glTF magic/);
assert(deletes.length >= 1, 'invalid streamed GLB must delete the temp object');
console.log('Home Center render GitHub-source materialization test: OK');
