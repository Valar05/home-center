const assert = require('node:assert/strict');
const {inspectArtifactHeader, decodeStrictBase64} = require('../functions/artifact_ingest_service');

const glb = Buffer.alloc(12);
glb.write('glTF', 0, 'ascii');
glb.writeUInt32LE(2, 4);
glb.writeUInt32LE(12, 8);
assert.equal(inspectArtifactHeader(glb, {name: 'model.glb', mimeType: 'model/gltf-binary'}).detectedKind, 'glb');
assert.throws(() => inspectArtifactHeader(Buffer.from('version https://git-lfs.github.com/spec/v1\noid sha256:' + '0'.repeat(64) + '\nsize 12\n'), {name: 'model.glb'}), /Git LFS pointer/);
assert.throws(() => inspectArtifactHeader(Buffer.from('{"file":"model.glb"}'), {name: 'model.glb'}), /text descriptor/);
assert.throws(() => inspectArtifactHeader(Buffer.from('not a png'), {name: 'image.png', mimeType: 'image/png'}), /do not match/);
assert.deepEqual(decodeStrictBase64(Buffer.from('binary').toString('base64')), Buffer.from('binary'));
assert.throws(() => decodeStrictBase64('!!!!'), /canonical Base64/);
console.log('artifact ingest binary contract: pass');
