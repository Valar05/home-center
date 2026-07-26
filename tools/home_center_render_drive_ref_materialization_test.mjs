#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import Module from 'node:module';
import {Writable} from 'node:stream';

const saves = [];
const objects = new Map();
const originalLoad = Module._load;
Module._load = function patchedLoad(request, parent, isMain) {
  if (request === '@google-cloud/storage') {
    return {Storage: class FakeStorage { bucket(bucketId) { return {file(objectName) { return {
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
      async delete() { objects.delete(objectName); },
    }; }}; } }};
  }
  return originalLoad.call(this, request, parent, isMain);
};
const require = createRequire(import.meta.url);
const {materializeHomeCenterRenderDriveRefs} = require('../functions/home_center_mcp.js');

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
const glbBytes = minimalGlb();
let driveMediaRequested = false;
const google = {
  auth: {OAuth2: class FakeOAuth2 { setCredentials(credentials) { this.credentials = credentials; } on() {} }},
  drive() {
    return {files: {async get(params, opts) {
      if (params.alt === 'media') { driveMediaRequested = true; return {data: glbBytes.buffer.slice(glbBytes.byteOffset, glbBytes.byteOffset + glbBytes.byteLength)}; }
      return {data: {id: params.fileId, name: 'KnightOfGold.glb', mimeType: 'model/gltf-binary'}};
    }}};
  },
};
const admin = {
  firestore() {
    return {
      collection(name) {
        assert.equal(name, 'mcpOAuthAccessTokens');
        return {
          doc(id) {
            assert.equal(id, tokenHash(token));
            return {
              async get() {
                return {
                  exists: true,
                  data: () => ({
                    email: 'drew@example.com',
                    expiresAtMs: Date.now() + 60000,
                    googleTokens: {access_token: 'google-access-token'},
                  }),
                  ref: {async set() {}},
                };
              },
            };
          },
        };
      },
    };
  },
};
const extra = {requestInfo: {headers: {authorization: 'Bearer ' + token}}};
const out = await materializeHomeCenterRenderDriveRefs({google, admin, googleClientId: 'client', googleClientSecret: 'secret', extra, args: {idempotencyKey: 'drive-ref-test', glbRef: 'drive://1I6GSxDLZaJXvZyej-oTJ9cUbG7YZYK3I', scriptText: 'print(1)'}});
assert.equal(driveMediaRequested, true, 'Drive media must be downloaded with the connected OAuth context');
assert.equal(saves.length, 1, 'GLB drive ref must be staged once');
assert.equal(Buffer.compare(saves[0].bytes, glbBytes), 0, 'staged GLB bytes must match Drive media bytes');
assert(out.glbRef.startsWith('gs://home-center-dclar-command-center-renders/command-center-render-inputs/home-center-bridge/drew@example.com/'));
assert.equal(out.scriptText, 'print(1)');
assert.equal(out.stagedInputs.length, 1);
assert.equal(out.stagedInputs[0].sha256, createHash('sha256').update(glbBytes).digest('hex'));
assert.equal(out.stagedInputs[0].byteCount, glbBytes.length);
assert.equal(out.stagedInputs[0].materializedFrom, 'glbDriveRef');
console.log('Home Center render Drive-ref materialization test: OK');
