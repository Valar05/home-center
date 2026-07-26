import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import homeCenter from '../functions/home_center_mcp.js';

const {readDriveBinaryChunkOperation} = homeCenter;
const source = Buffer.from([0, 1, 2, 3, 4, 5]);
const calls = [];
const google = {
  drive() {
    return {
      files: {
        async get(params, options = {}) {
          calls.push({params, options});
          if (params.alt === 'media') {
            assert.equal(options.responseType, 'arraybuffer');
            assert.equal(options.headers.Range, 'bytes=2-4');
            return {data: source.subarray(2, 5)};
          }
          return {data: {
            id: 'file-1234',
            name: 'cartesia-master.ogg',
            mimeType: 'audio/ogg',
            size: String(source.length),
            md5Checksum: 'fixture-md5',
          }};
        },
      },
    };
  },
};

const chunk = await readDriveBinaryChunkOperation({
  google,
  auth: {},
  args: {fileId: 'file-1234', offset: 2, length: 3},
});
assert.equal(chunk.offset, 2);
assert.equal(chunk.byteCount, 3);
assert.equal(chunk.totalSize, 6);
assert.equal(chunk.nextOffset, 5);
assert.equal(chunk.eof, false);
assert.equal(chunk.chunkBase64, source.subarray(2, 5).toString('base64'));
assert.equal(chunk.chunkSha256, createHash('sha256').update(source.subarray(2, 5)).digest('hex'));
assert.equal(calls.length, 2);

const eof = await readDriveBinaryChunkOperation({
  google: {
    drive() {
      return {files: {async get() { return {data: {id: 'file-1234', name: 'cartesia-master.ogg', mimeType: 'audio/ogg', size: '6'}}; }}};
    },
  },
  auth: {},
  args: {fileId: 'file-1234', offset: 6, length: 3},
});
assert.equal(eof.byteCount, 0);
assert.equal(eof.eof, true);
assert.equal(eof.nextOffset, null);

await assert.rejects(
  () => readDriveBinaryChunkOperation({google, auth: {}, args: {fileId: 'file-1234', offset: 0, length: 262145}}),
  /length must be an integer between 1 and 262144 bytes/,
);

console.log(JSON.stringify({ok: true, byteRange: '2-4', chunkSha256: chunk.chunkSha256, eof: eof.eof}, null, 2));
