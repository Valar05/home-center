import assert from 'node:assert/strict';
import {Readable} from 'node:stream';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import fs from 'node:fs';

const require = createRequire(import.meta.url);
const functionsIndexSource = fs.readFileSync(new URL('../functions/index.js', import.meta.url), 'utf8');
assert(functionsIndexSource.includes('HOSTED_TTS_ALLOWED_EMAILS'));
assert(functionsIndexSource.includes('requireHostedTtsAllowedUser(req)'));
assert(functionsIndexSource.includes("'dclarke1005@gmail.com'"));
assert(functionsIndexSource.includes("'junewren28@gmail.com'"));
assert(functionsIndexSource.includes("'timothypomeroy07@gmail.com'"));
const {synthesizeCartesiaAudioArtifactOperation, driveOperationRunOperation} = require('../functions/home_center_mcp.js');

const singleAudioBytes = Buffer.from('RIFF....WAVEfmt cartesia contract audio bytes');
const segmentOnePcm = Buffer.from([1, 0, 2, 0, 3, 0, 4, 0]);
const segmentTwoPcm = Buffer.from([5, 0, 6, 0, 7, 0, 8, 0, 9, 0, 10, 0]);
const stores = new Map();
const createdFiles = new Map();
let createCount = 0;
const fetchCalls = [];

function collectionStore(name) {
  if (!stores.has(name)) stores.set(name, new Map());
  return stores.get(name);
}

async function readableToBuffer(readable) {
  const chunks = [];
  for await (const chunk of readable) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  return Buffer.concat(chunks);
}

function collectionDocStore(name) {
  const store = collectionStore(name);
  return {
    doc(id) {
      return {
        async get() {
          return {exists: store.has(id), data: () => store.get(id)};
        },
        async set(value) {
          store.set(id, value);
        },
      };
    },
    async add(value) {
      const id = 'add-' + (store.size + 1);
      store.set(id, value);
      return {id};
    },
  };
}

function fakeAdmin() {
  function firestore() {
    return {collection: collectionDocStore};
  }
  firestore.FieldValue = {serverTimestamp: () => 'server-timestamp'};
  return {firestore};
}

function fakeGoogle() {
  return {
    drive() {
      return {
        files: {
          async create({requestBody, media}) {
            assert.equal(requestBody.mimeType, 'audio/wav');
            if (requestBody.parents) assert.equal(requestBody.parents[0], 'folder12345');
            assert.equal(media.mimeType, 'audio/wav');
            assert.ok(media.body instanceof Readable);
            const id = 'audioFile' + (++createCount);
            const bytes = await readableToBuffer(media.body);
            const metadata = {
              id,
              name: requestBody.name,
              mimeType: requestBody.mimeType,
              webViewLink: 'https://drive.google.com/file/d/' + id + '/view',
              parents: requestBody.parents || ['folder12345'],
            };
            createdFiles.set(id, {metadata, bytes});
            return {data: metadata};
          },
          async get(args) {
            const stored = createdFiles.get(args.fileId) || [...createdFiles.values()].at(-1);
            if (args.alt === 'media') {
              return {data: stored.bytes.buffer.slice(stored.bytes.byteOffset, stored.bytes.byteOffset + stored.bytes.byteLength)};
            }
            return {data: stored.metadata};
          },
        },
      };
    },
  };
}

const oldFetch = globalThis.fetch;
globalThis.fetch = async (url, options = {}) => {
  assert.equal(url, 'https://api.cartesia.ai/tts/bytes');
  assert.equal(options.headers['X-API-Key'], 'test-cartesia-key');
  assert.equal(options.headers['Cartesia-Version'], '2026-03-01');
  const body = JSON.parse(options.body);
  fetchCalls.push(body);
  assert.equal(body.model_id, 'sonic-3.5');
  if (body.transcript === 'Home Center MCP Cartesia contract.') {
    assert.equal(body.voice.id, 'f786b574-daa5-4673-aa0c-cbe3e8534c02');
    assert.equal(body.output_format.container, 'wav');
    return new Response(singleAudioBytes, {status: 200, headers: {'content-type': 'audio/wav'}});
  }
  if (body.transcript === 'Speaker one line.') {
    assert.equal(body.voice.id, 'voice-one');
    assert.equal(body.output_format.container, 'raw');
    return new Response(segmentOnePcm, {status: 200, headers: {'content-type': 'application/octet-stream'}});
  }
  if (body.transcript === 'Speaker two line.') {
    assert.equal(body.voice.id, 'voice-two');
    assert.equal(body.output_format.container, 'raw');
    return new Response(segmentTwoPcm, {status: 200, headers: {'content-type': 'application/octet-stream'}});
  }
  throw new Error('unexpected transcript: ' + body.transcript);
};

try {
  const admin = fakeAdmin();
  const user = {email: 'junewren28@gmail.com', authKind: 'google_oauth_bearer'};
  const result = await synthesizeCartesiaAudioArtifactOperation({
    google: fakeGoogle(),
    admin,
    auth: {},
    user,
    cartesiaApiKey: () => 'test-cartesia-key',
    args: {
      text: 'Home Center MCP Cartesia contract.',
      parentFolderId: 'folder12345',
      name: 'contract-audio',
      requestId: 'cartesia-contract-001',
    },
  });
  assert.equal(result.provider, 'cartesia');
  assert.equal(result.verified, true);
  assert.equal(result.byteCount, singleAudioBytes.length);
  assert.equal(result.sha256, createHash('sha256').update(singleAudioBytes).digest('hex'));
  assert.equal(result.readbackSha256, result.sha256);
  assert.equal(result.segmentCount, 1);
  assert.equal(collectionStore('driveBridgeAudit').get('cartesia-contract-001').operation, 'tts.synthesize');

  const routed = await driveOperationRunOperation({
    google: fakeGoogle(),
    admin,
    auth: {},
    user,
    cartesiaApiKey: () => 'test-cartesia-key',
    args: {operation: 'tts.synthesize', args: {text: 'Home Center MCP Cartesia contract.', parentFolderId: 'folder12345', requestId: 'cartesia-contract-002'}},
  });
  assert.equal(routed.operation, 'tts.synthesize');
  assert.equal(routed.completed, true);
  assert.notEqual(routed.compatibilityRoute, 'drive_operation.command_center');
  assert.equal(routed.result.verified, true);

  const stitched = await driveOperationRunOperation({
    google: fakeGoogle(),
    admin,
    auth: {},
    user,
    cartesiaApiKey: () => 'test-cartesia-key',
    args: {
      operation: 'tts.synthesize',
      args: {
        segments: [
          {speaker: 'One', text: 'Speaker one line.', voiceName: 'Voice One', voiceId: 'voice-one'},
          {speaker: 'Two', text: 'Speaker two line.', voiceName: 'Voice Two', voiceId: 'voice-two'},
        ],
        pauseMs: 10,
        parentFolderId: 'folder12345',
        name: 'stitched-speakers',
        requestId: 'cartesia-contract-003',
      },
    },
  });
  assert.equal(stitched.operation, 'tts.synthesize');
  assert.equal(stitched.completed, true);
  assert.notEqual(stitched.compatibilityRoute, 'drive_operation.command_center');
  assert.equal(stitched.result.provider, 'cartesia');
  assert.equal(stitched.result.verified, true);
  assert.equal(stitched.result.segmentCount, 2);
  assert.equal(stitched.result.stitched, true);
  assert.equal(stitched.result.segments[0].speaker, 'One');
  assert.equal(stitched.result.segments[1].speaker, 'Two');
  assert.equal(stitched.result.segments[0].voiceId, 'voice-one');
  assert.equal(stitched.result.segments[1].voiceId, 'voice-two');


  await assert.rejects(
    () => driveOperationRunOperation({
      google: fakeGoogle(),
      admin,
      auth: {},
      user: {email: 'tester@example.com', authKind: 'google_oauth_bearer'},
      cartesiaApiKey: () => 'test-cartesia-key',
      args: {operation: 'tts.synthesize', args: {text: 'Home Center MCP Cartesia contract.', parentFolderId: 'folder12345', requestId: 'cartesia-contract-denied'}},
    }),
    (err) => err && err.status === 403 && err.failureKind === 'credit_gated_forbidden_email'
  );
  const stitchedBytes = createdFiles.get(stitched.result.fileId).bytes;
  assert.equal(stitchedBytes.slice(0, 4).toString('ascii'), 'RIFF');
  assert.equal(stitchedBytes.slice(8, 12).toString('ascii'), 'WAVE');
  assert.equal(stitchedBytes.readUInt32LE(40), stitchedBytes.length - 44);
  assert.equal(stitched.result.byteCount, stitchedBytes.length);
  assert.equal(stitched.result.sha256, createHash('sha256').update(stitchedBytes).digest('hex'));
  assert.deepEqual(fetchCalls.map((call) => call.transcript), [
    'Home Center MCP Cartesia contract.',
    'Home Center MCP Cartesia contract.',
    'Speaker one line.',
    'Speaker two line.',
  ]);
  console.log('Cartesia MCP artifact contract: OK');
} finally {
  globalThis.fetch = oldFetch;
}
