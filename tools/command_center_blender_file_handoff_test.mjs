#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {decodeUploadObject, validateGlbBytes, validateScriptBytes, sha256Buffer} from '../cloud-render/src/render_bundle.mjs';

const require = createRequire(import.meta.url);
const {resolveRenderSources} = require('../functions/command_center_mcp.js');

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

const glb = minimalGlb();
const script = Buffer.from('print("pose is god")\n', 'utf8');
assert.doesNotThrow(() => validateGlbBytes(glb, 'fixture'));
assert.doesNotThrow(() => validateScriptBytes(script, 'script'));
assert.equal(sha256Buffer(decodeUploadObject({base64: glb.toString('base64')}, 'glb')), createHash('sha256').update(glb).digest('hex'));
assert.equal(sha256Buffer(decodeUploadObject({data: glb.toString('base64')}, 'glb')), createHash('sha256').update(glb).digest('hex'));
assert.equal(sha256Buffer(decodeUploadObject({contentBase64: script.toString('base64')}, 'script')), createHash('sha256').update(script).digest('hex'));
assert.throws(() => validateGlbBytes(Buffer.from('not-glb'), 'bad'), /too small|missing glTF magic/);
assert.throws(() => validateScriptBytes(Buffer.from([0, 1, 2]), 'bad-script'), /text Python script/);
await assert.rejects(() => resolveRenderSources({actor: 'test', ownerKey: 'owner_test'}, {}, 'render_test'), /Exactly one GLB source is required/);
await assert.rejects(() => resolveRenderSources({actor: 'test', ownerKey: 'owner_test'}, {glbRef: 'gs://bucket/a.glb', glbFile: new File([glb], 'a.glb'), scriptRef: 'gs://bucket/render.py'}, 'render_test'), /Exactly one GLB source is required/);
await assert.rejects(() => resolveRenderSources({actor: 'test', ownerKey: 'owner_test'}, {glbFile: new File([Buffer.from('no')], '../bad.glb'), scriptRef: 'gs://bucket/render.py'}, 'render_test'), /too small|missing glTF magic/);
await assert.rejects(() => resolveRenderSources({actor: 'test', ownerKey: 'owner_test'}, {glbRef: 'gs://bucket/a.glb', scriptRef: 'gs://bucket/render.py', scriptText: 'print(1)'}, 'render_test'), /Exactly one Blender script source is required/);
console.log('Command Center Blender file handoff test: OK');
