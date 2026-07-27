#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import Module from 'node:module';

const saves = [];
const objects = new Map();
const originalLoad = Module._load;
Module._load = function patchedLoad(request, parent, isMain) {
  if (request === '@google-cloud/storage') {
    return {
      Storage: class FakeStorage {
        bucket(bucketId) {
          return {
            file(objectName) {
              return {
                async save(bytes, options) {
                  if (objects.has(objectName) && options?.preconditionOpts?.ifGenerationMatch === 0) { const error = new Error('precondition failed'); error.code = 412; throw error; }
                  const copy=Buffer.from(bytes); objects.set(objectName,copy); saves.push({bucketId, objectName, bytes: copy, options});
                },
                async download() { return [Buffer.from(objects.get(objectName))]; },
              };
            },
          };
        }
      },
    };
  }
  return originalLoad.call(this, request, parent, isMain);
};

const require = createRequire(import.meta.url);
const {resolveRenderSources} = require('../functions/command_center_mcp.js');

function minimalGlb(extraJson = '') {
  const json = Buffer.from('{"asset":{"version":"2.0"}' + extraJson + '}', 'utf8');
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

const glbBytes = minimalGlb(',"generator":"byte-preservation"');
const scriptBytes = Buffer.from('print("pose is god")\n', 'utf8');
const result = await resolveRenderSources(
  {actor: 'byte-test@example.com', ownerKey: 'owner_byte_test'},
  {glbFile: new File([glbBytes], 'vanguard.glb', {type: 'model/gltf-binary'}), scriptFile: new File([scriptBytes], 'render.py', {type: 'text/x-python'})},
  'render_byte_preservation',
);
assert.equal(saves.length, 2, 'both uploads must be staged by the upload handler');
assert.deepEqual(saves.map((save) => createHash('sha256').update(save.bytes).digest('hex')).sort(), [createHash('sha256').update(glbBytes).digest('hex'), createHash('sha256').update(scriptBytes).digest('hex')].sort());
assert.equal(Buffer.compare(saves.find((save) => save.objectName.includes('artifacts/sha256/') && save.objectName.endsWith('/vanguard.glb')).bytes, glbBytes), 0, 'GLB bytes must be preserved exactly');
assert.equal(Buffer.compare(saves.find((save) => save.objectName.includes('artifacts/sha256/') && save.objectName.endsWith('/render.py')).bytes, scriptBytes), 0, 'script bytes must be preserved exactly');
assert.equal(result.stagedInputs.length, 2);
const replay = await resolveRenderSources({actor: 'byte-test@example.com', ownerKey: 'owner_byte_test'}, {glbFile: new File([glbBytes], 'vanguard.glb', {type: 'model/gltf-binary'}), scriptFile: new File([scriptBytes], 'render.py', {type: 'text/x-python'})}, 'render_replay');
assert.equal(saves.length, 2, 'digest replay must not upload duplicate bytes');
assert.equal(replay.stagedInputs.every((item) => item.reused && item.transferredBytes === 0), true);
assert(result.glbRef.startsWith('gs://'));
assert(result.scriptRef.startsWith('gs://'));
console.log('Command Center Blender upload byte-preservation test: OK');
