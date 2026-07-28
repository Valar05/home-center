#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Readable} from 'node:stream';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  linkArtifactReviewSuccessorOperation,
  materializeReceiptArtifactsOperation,
  recordArtifactReviewOperation,
  uniqueCandidates,
} = require('../functions/artifact_delivery_service.js');
const {
  createHomeCenterMcpServer,
  driveOperationRegistry,
} = require('../functions/home_center_mcp.js');

const ownerEmail = 'dclarke1005@gmail.com';
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');

class Snapshot {
  constructor(value) { this.value = value; this.exists = value !== undefined; }
  data() { return this.value; }
}
class Doc {
  constructor(store, path) { this.store = store; this.path = path; }
  async get() { return new Snapshot(this.store.get(this.path)); }
  async set(value, options = {}) {
    const prior = this.store.get(this.path) || {};
    this.store.set(this.path, options.merge ? {...prior, ...value} : value);
  }
  async create(value) {
    if (this.store.has(this.path)) throw Object.assign(new Error('already exists'), {code: 6});
    this.store.set(this.path, value);
  }
}
function fakeAdmin(initial = new Map()) {
  return {
    store: initial,
    firestore() {
      return {collection: (name) => ({doc: (id) => new Doc(initial, name + '/' + id)})};
    },
  };
}

function delayedReadable(bytes, tracker) {
  return Readable.from((async function* () {
    tracker.active += 1;
    tracker.max = Math.max(tracker.max, tracker.active);
    await new Promise((resolve) => setTimeout(resolve, 8));
    yield bytes;
    tracker.active -= 1;
  })());
}

function fakeStorage(objects) {
  const tracker = {active: 0, max: 0, reads: 0};
  return {
    tracker,
    bucket(bucket) {
      return {
        file(objectName) {
          const key = 'gs://' + bucket + '/' + objectName;
          const value = objects.get(key);
          if (!value) throw Object.assign(new Error('missing object'), {code: 404});
          return {
            async getMetadata() {
              return [{size: String(value.bytes.length), generation: value.generation || '1', metadata: {sha256: value.metadataSha || sha(value.bytes)}}];
            },
            createReadStream() {
              tracker.reads += 1;
              return delayedReadable(value.bytes, tracker);
            },
          };
        },
      };
    },
  };
}

async function streamBytes(stream) {
  const chunks = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}

function fakeGoogle() {
  const files = new Map();
  let createCount = 0;
  return {
    get createCount() { return createCount; },
    files,
    drive() {
      return {
        files: {
          async list({q}) {
            const match = /value='([^']+)'/.exec(q);
            const key = match ? match[1] : '';
            return {data: {files: [...files.values()].filter((item) => item.appProperties.homeCenterArtifactDeliveryDigestKey === key)}};
          },
          async create({requestBody, media}) {
            const bytes = await streamBytes(media.body);
            createCount += 1;
            const id = 'drive-artifact-' + createCount;
            const value = {id, name: requestBody.name, mimeType: requestBody.mimeType, webViewLink: 'https://drive.google.test/file/d/' + id + '/view', appProperties: requestBody.appProperties, bytes};
            files.set(id, value);
            return {data: value};
          },
          async get({fileId}) {
            const value = files.get(fileId);
            if (!value) throw Object.assign(new Error('missing drive file'), {code: 404});
            return {data: Readable.from([value.bytes])};
          },
        },
      };
    },
  };
}

function artifact(name, mimeType, bytes, role) {
  const storageRef = 'gs://home-center-generated/proof/' + name;
  return {role, name, mimeType, byteCount: bytes.length, sha256: sha(bytes), storageRef};
}

const bytes = {
  glb: Buffer.from('glTF-fixture-binary'),
  png: Buffer.from([0x89, 0x50, 0x4e, 0x47, 1, 2, 3]),
  gif: Buffer.from('GIF89a-fixture'),
  json: Buffer.from('{"ok":true}\n'),
  wav: Buffer.from('RIFFfixtureWAVE'),
  mp4: Buffer.from('....ftypisom-fixture'),
};
const artifacts = [
  artifact('specimen.glb', 'model/gltf-binary', bytes.glb, 'model'),
  artifact('contact-sheet.png', 'image/png', bytes.png, 'contact_sheet'),
  artifact('preview.gif', 'image/gif', bytes.gif, 'animation_preview'),
  artifact('manifest.json', 'application/json', bytes.json, 'manifest'),
  artifact('review.wav', 'audio/wav', bytes.wav, 'playable_audio'),
  artifact('review.mp4', 'video/mp4', bytes.mp4, 'video_preview'),
];
const objects = new Map(artifacts.map((item) => [item.storageRef, {bytes: bytes[Object.keys(bytes).find((key) => item.name.endsWith(key === 'json' ? '.json' : '.' + key))] || Buffer.alloc(0)}]));
for (const item of artifacts) objects.set(item.storageRef, {bytes: item.name.endsWith('.glb') ? bytes.glb : item.name.endsWith('.png') ? bytes.png : item.name.endsWith('.gif') ? bytes.gif : item.name.endsWith('.json') ? bytes.json : item.name.endsWith('.wav') ? bytes.wav : bytes.mp4});

const producerReceiptId = 'receipt-delivery-contract-001';
const receipt = {
  actor: ownerEmail,
  operation: 'audio.render',
  status: 'completed',
  humanAcceptance: 'unreviewed',
  result: {status: 'completed', humanAcceptance: 'unreviewed', outputs: artifacts},
};
const initial = new Map([['driveBridgeAudit/' + producerReceiptId, receipt]]);
const admin = fakeAdmin(initial);
const storage = fakeStorage(objects);
const google = fakeGoogle();
const base = {google, admin, auth: {}, user: {email: ownerEmail}, args: {requestId: 'delivery-request-001', producerReceiptId, producerKind: 'drive_audit'}};

const result = await materializeReceiptArtifactsOperation(base, {storage});
assert.equal(result.status, 'review_ready');
assert.equal(result.transportState.artifactCount, artifacts.length);
assert.equal(result.transportState.transferredBytes, artifacts.reduce((sum, item) => sum + item.byteCount, 0));
assert.equal(result.transportState.reusedBytes, 0);
assert.equal(result.transportState.concurrency, 3);
assert.equal(result.transportState.rerendered, false);
assert.equal(result.transportState.resynthesized, false);
assert.equal(result.transportState.public, false);
assert.equal(result.authorization.state, 'owner_scoped');
assert.deepEqual(result.humanAcceptance, {state: 'unreviewed', changed: false});
assert.equal(result.artifacts.every((item) => item.delivery.verified && item.delivery.resourceLink.type === 'resource_link'), true);
assert.equal(result.artifacts.every((item) => item.delivery.readbackSha256 === item.sha256), true);
assert.ok(storage.tracker.max >= 2 && storage.tracker.max <= 3, 'independent source verification must use bounded parallelism');
assert.equal(google.createCount, artifacts.length);

const readsBeforeReplay = storage.tracker.reads;
const replay = await materializeReceiptArtifactsOperation(base, {storage});
assert.equal(replay.idempotent, true);
assert.equal(storage.tracker.reads, readsBeforeReplay, 'exact replay must not restage verified source bytes');
const exactReplayReads = storage.tracker.reads - readsBeforeReplay;
assert.equal(google.createCount, artifacts.length, 'exact replay must not create Drive duplicates');

const digestReuse = await materializeReceiptArtifactsOperation({...base, args: {...base.args, requestId: 'delivery-request-002'}}, {storage});
assert.equal(digestReuse.transportState.transferredBytes, 0);
assert.equal(digestReuse.transportState.reusedBytes, result.transportState.expectedBytes);
assert.equal(google.createCount, artifacts.length, 'new delivery request for identical bytes must reuse digest-addressed Drive files');
assert.equal(digestReuse.artifacts.every((item) => item.delivery.reused), true);
const duplicateCreates = google.createCount - artifacts.length;
assert.equal(duplicateCreates, 0);

await assert.rejects(
  () => materializeReceiptArtifactsOperation({...base, args: {...base.args, artifactNames: ['manifest.json']}}, {storage}),
  (error) => error.failureKind === 'artifact_delivery.idempotency_conflict',
);
await assert.rejects(
  () => materializeReceiptArtifactsOperation({...base, args: {...base.args, requestId: 'direct-ref-rejected', storageRef: artifacts[0].storageRef}}, {storage}),
  (error) => error.failureKind === 'artifact_delivery.receipt_only',
);
await assert.rejects(
  () => materializeReceiptArtifactsOperation({...base, user: {email: 'junewren28@gmail.com'}, args: {...base.args, requestId: 'unauthorized'}}, {storage}),
  (error) => error.failureKind === 'artifact_delivery.receipt_forbidden',
);
initial.set('driveBridgeAudit/running-receipt', {...receipt, status: 'running'});
await assert.rejects(
  () => materializeReceiptArtifactsOperation({...base, args: {...base.args, requestId: 'running-delivery', producerReceiptId: 'running-receipt'}}, {storage}),
  (error) => error.failureKind === 'artifact_delivery.receipt_not_terminal',
);

const partialCorrect = [Buffer.from('partial-a'), Buffer.from('partial-b'), Buffer.from('partial-c')];
const partialArtifacts = partialCorrect.map((value, index) => artifact('partial-' + (index + 1) + '.json', 'application/json', value, 'partial-' + (index + 1)));
partialArtifacts.forEach((item, index) => objects.set(item.storageRef, {bytes: index === 1 ? Buffer.from('corrupt-b') : partialCorrect[index], metadataSha: item.sha256}));
initial.set('driveBridgeAudit/partial-producer-001', {actor: ownerEmail, operation: 'sfx.render', status: 'completed', result: {status: 'completed', outputs: partialArtifacts, humanAcceptance: 'unreviewed'}});
const createsBeforePartial = google.createCount;
await assert.rejects(
  () => materializeReceiptArtifactsOperation({...base, args: {requestId: 'partial-delivery-001', producerReceiptId: 'partial-producer-001', producerKind: 'drive_audit'}}, {storage}),
  (error) => error.failureKind === 'artifact_delivery.gcs_readback_mismatch' && error.details.completedSiblingIndexes.length === 2,
);
assert.equal(google.createCount, createsBeforePartial + 2, 'verified siblings must finish safely before a failed envelope returns');
objects.set(partialArtifacts[1].storageRef, {bytes: partialCorrect[1], metadataSha: partialArtifacts[1].sha256});
const partialRetry = await materializeReceiptArtifactsOperation({...base, args: {requestId: 'partial-delivery-001', producerReceiptId: 'partial-producer-001', producerKind: 'drive_audit'}}, {storage});
assert.equal(partialRetry.transportState.transferredBytes, partialArtifacts[1].byteCount, 'retry must copy only the previously failed artifact');
assert.equal(partialRetry.transportState.reusedBytes, partialArtifacts[0].byteCount + partialArtifacts[2].byteCount);
assert.equal(google.createCount, createsBeforePartial + 3);

const reviewArgs = {requestId: 'review-rejected-001', deliveryRequestId: base.args.requestId, verdict: 'revision_requested', reason: 'Front silhouette is correct but the attachment is reversed.', successorPlan: {operation: 'foundry.asset.run', idempotencyKey: 'corrective-foundry-001', changes: 'Reverse the attachment and preserve the accepted body.'}};
const review = await recordArtifactReviewOperation({admin, user: {email: ownerEmail}, args: reviewArgs});
assert.equal(review.humanAcceptance.state, 'revision_requested');
assert.equal(review.candidatePreserved, true);
assert.equal(review.promotionAllowed, false);
assert.equal(review.successor.state, 'planned');
assert.equal(review.successor.priorCandidateChanged, true);
const reviewReplay = await recordArtifactReviewOperation({admin, user: {email: ownerEmail}, args: reviewArgs});
assert.equal(reviewReplay.idempotent, true);
await assert.rejects(
  () => recordArtifactReviewOperation({admin, user: {email: ownerEmail}, args: {...reviewArgs, requestId: 'review-missing-plan', successorPlan: undefined}}),
  (error) => error.failureKind === 'artifact_review.successor_plan_incomplete',
);
await assert.rejects(
  () => recordArtifactReviewOperation({admin, user: {email: ownerEmail}, args: {...reviewArgs, reason: 'Changed verdict details.'}}),
  (error) => error.failureKind === 'artifact_review.idempotency_conflict',
);
const successorArtifact = artifact('specimen-successor.glb', 'model/gltf-binary', Buffer.from('glTF-corrected-successor'), 'model');
initial.set('driveBridgeAudit/successor-producer-001', {actor: ownerEmail, operation: 'foundry.asset.run', status: 'completed', result: {status: 'completed', humanAcceptance: 'unreviewed', outputs: [successorArtifact]}});
const successor = await linkArtifactReviewSuccessorOperation({admin, user: {email: ownerEmail}, args: {requestId: 'review-link-001', reviewRequestId: reviewArgs.requestId, successorReceiptId: 'successor-producer-001', producerKind: 'drive_audit'}});
assert.equal(successor.prior.receiptId, producerReceiptId);
assert.equal(successor.successor.receiptId, 'successor-producer-001');
assert.equal(successor.successor.state, 'producer_completed');
assert.equal(successor.successor.nextOperation.operation, 'artifact.delivery.materialize_receipt');
assert.equal(successor.priorCandidatePreserved, true);
const successorReplay = await linkArtifactReviewSuccessorOperation({admin, user: {email: ownerEmail}, args: {requestId: 'review-link-001', reviewRequestId: reviewArgs.requestId, successorReceiptId: 'successor-producer-001', producerKind: 'drive_audit'}});
assert.equal(successorReplay.idempotent, true);
await assert.rejects(
  () => linkArtifactReviewSuccessorOperation({admin, user: {email: ownerEmail}, args: {requestId: 'review-link-same', reviewRequestId: reviewArgs.requestId, successorReceiptId: producerReceiptId, producerKind: 'drive_audit'}}),
  (error) => error.failureKind === 'artifact_review.successor_unchanged',
);

const renderReceipt = {
  requestedBy: ownerEmail,
  ownerKey: 'owner_' + sha(Buffer.from(ownerEmail)).slice(0, 32),
  status: 'completed',
  result: {
    contactSheetRef: 'gs://home-center-generated/renders/contact-sheets/test/contact-sheet.png',
    fixedCameraRenderRefs: ['gs://home-center-generated/renders/blender/test/fixed/0-front.png'],
    loopingGifRef: 'gs://home-center-generated/renders/gifs/test/walk-loop.gif',
    artifactHashes: {
      'contact-sheet.png': {sha256: '1'.repeat(64), byteCount: 100},
      'front.png': {sha256: '2'.repeat(64), byteCount: 90},
      'walk-loop.gif': {sha256: '3'.repeat(64), byteCount: 80},
    },
  },
};
assert.deepEqual(uniqueCandidates(renderReceipt).candidates.map((item) => item.role), ['contact_sheet', 'fixed_camera', 'looping_gif']);
const foundryReceipt = {owner: ownerEmail, state: 'completed', result: {artifacts: [{kind: 'model', name: 'foundry.glb', mediaType: 'model/gltf-binary', byteLength: 99, sha256: '4'.repeat(64), storageRef: 'gs://home-center-generated/foundry/foundry.glb'}]}};
assert.equal(uniqueCandidates(foundryReceipt).candidates[0].name, 'foundry.glb');

const registry = driveOperationRegistry();
assert.ok(registry.operations['artifact.delivery.materialize_receipt']);
assert.ok(registry.operations['artifact.review.record']);
assert.ok(registry.operations['artifact.review.link_successor']);
assert.equal(registry.operations['artifact.delivery.materialize_receipt'].input.storageRef, undefined);
assert.equal(registry.operations['artifact.delivery.materialize_receipt'].input.url, undefined);
const server = createHomeCenterMcpServer({google: {}, admin});
assert.equal(server._registeredTools.artifact_delivery_materialize_receipt, undefined, 'receipt delivery must remain below drive_operation');
assert.ok(JSON.stringify(result).length < 50000, 'receipt must remain bounded');
assert.equal(JSON.stringify(result).includes('approved'), false, 'delivery must not fabricate approved metadata');

console.log(JSON.stringify({ok: true, artifactCount: result.artifacts.length, transferredBytes: result.transportState.transferredBytes, exactReplayReads, duplicateCreates, maxConcurrency: storage.tracker.max, humanAcceptance: result.humanAcceptance.state, reviewVerdict: review.humanAcceptance.state, successorReceiptId: successor.successor.receiptId, partialRetryTransferredBytes: partialRetry.transportState.transferredBytes}, null, 2));
