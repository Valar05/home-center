import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE = '1';
process.env.HOME_CENTER_GENERATED_BUCKET = 'home-center-generated';
const require = createRequire(import.meta.url);
const artifactBucket = require('../functions/artifact_bucket.js');
const {recoverAudioRenderRegistrationOperation, registerPrimaryAudioFromReceipt, linkDriveAudioToReaderStageOperation} = require('../functions/audio_catalog_service.js');
const {driveOperationRunOperation, createHomeCenterMcpServer} = require('../functions/home_center_mcp.js');

function fakeAdmin() {
  const collections = new Map();
  const collection = (name) => {
    if (!collections.has(name)) collections.set(name, new Map());
    const store = collections.get(name);
    return {
      doc(id) {
        return {
          async get() { return {exists: store.has(id), data: () => store.get(id)}; },
          async set(value, options = {}) {
            if (options.merge && store.has(id)) store.set(id, {...store.get(id), ...value});
            else store.set(id, value);
          },
        };
      },
    };
  };
  return {firestore: () => ({collection}), collections};
}

const ownerEmail = 'dclarke1005@gmail.com';
const oggBytes = Buffer.concat([Buffer.from('OggS', 'ascii'), Buffer.alloc(512, 7)]);
const legacy = await artifactBucket.uploadGeneratedArtifact({
  bytes: oggBytes,
  name: 'Vacation-of-a-Lifetime-Day-1-Part-6-Royal-Cove-Final-Soundscape.ogg',
  mimeType: 'audio/ogg',
  owner: 'drew',
  ownerEmail: 'drew',
  project: 'vacation-of-a-lifetime',
  stage: 'review',
  approved: true,
  requestId: 'vacation-day1-part6-contract',
  artifactType: 'audio',
});
const before = await artifactBucket.verifyGeneratedArtifact(legacy.storageRef, legacy);
const admin = fakeAdmin();
const receipt = {
  actor: ownerEmail,
  operation: 'audio.render',
  requestId: 'vacation-day1-part6-contract',
  status: 'completed',
  result: {
    primaryOutput: {name: legacy.name, mimeType: legacy.mimeType, byteCount: legacy.byteCount, sha256: legacy.sha256, durableRef: legacy.storageRef, storageRef: legacy.storageRef, metadata: legacy.metadata},
    outputs: [],
  },
};
admin.collections.set('driveBridgeAudit', new Map([[receipt.requestId, receipt]]));

const routed = await driveOperationRunOperation({admin, user: {email: ownerEmail}, args: {operation: 'audio.render_register', args: {requestId: receipt.requestId}}});
assert.equal(routed.operation, 'audio.render_register');
assert.equal(routed.completed, true);
const recovered = routed.result;
assert.equal(recovered.execution, 'registration_only');
assert.equal(recovered.humanAcceptance, 'unreviewed');
assert.equal(recovered.registration.authorization.state, 'owner_scoped');
assert.equal(recovered.registration.discovery.ok, true);
assert.equal(recovered.registration.playback.ok, true);
assert.equal(recovered.registration.playback.probe.container, 'ogg');
assert.deepEqual(recovered.registration.transport, {copiedBytes: 0, rerendered: false, resynthesized: false, public: false, driveCopy: false});
assert.equal(recovered.registration.bytePreservation.unchanged, true);
assert.equal(recovered.registration.artifact.sha256, legacy.sha256);
const after = await artifactBucket.verifyGeneratedArtifact(legacy.storageRef, legacy);
assert.equal(after.sha256, before.sha256);
assert.equal(after.byteCount, before.byteCount);
assert.equal(after.generation, before.generation);
assert.equal(after.metadata.ownerEmail, ownerEmail);
assert.equal(after.metadata.humanAcceptance, 'unreviewed');
assert.equal(after.metadata.authorizationState, 'owner_scoped');
assert.equal(Object.hasOwn(after.metadata, 'approved'), false, 'legacy false approved:true metadata must be removed');

const replay = await recoverAudioRenderRegistrationOperation({admin, user: {email: ownerEmail}, args: {requestId: receipt.requestId}});
assert.equal(replay.idempotent, true);
assert.equal(replay.registration.catalog.storageRef, recovered.registration.catalog.storageRef);
assert.equal(replay.registration.artifact.sha256, recovered.registration.artifact.sha256);
await assert.rejects(() => recoverAudioRenderRegistrationOperation({admin, user: {email: 'junewren28@gmail.com'}, args: {requestId: receipt.requestId}}), /not owned/);
admin.collections.get('driveBridgeAudit').set('running-receipt', {...receipt, requestId: 'running-receipt', status: 'running'});
await assert.rejects(() => recoverAudioRenderRegistrationOperation({admin, user: {email: ownerEmail}, args: {requestId: 'running-receipt'}}), /terminal successful/);

const direct = await registerPrimaryAudioFromReceipt({ownerEmail, receipt: {...receipt, result: {...receipt.result, readerRegistration: undefined}}});
assert.equal(direct.catalog.reused, true);
assert.equal(direct.transport.copiedBytes, 0);
const readerLinkFileId = 'drive-file-reader-link-123';
const readerLinkSourceObject = 'indexes/audio/v1/by-drive-id/' + readerLinkFileId + '.json';
const readerLinkSource = {
  schemaVersion: 'home-center.audio-index.v1',
  indexedAt: '2026-07-30T00:00:00.000Z',
  source: {fileId: readerLinkFileId, name: legacy.name, mimeType: 'audio/ogg', sourcePath: 'Generated/' + legacy.name},
  destination: {
    bucket: 'home-center-generated',
    objectName: legacy.storageRef.slice('gs://home-center-generated/'.length),
    storageRef: legacy.storageRef,
    byteCount: legacy.byteCount,
    sha256: legacy.sha256,
    contentType: 'audio/ogg',
    ownerEmail,
    project: 'vacation-of-a-lifetime',
    stage: 'chapter-2-complete',
  },
  classification: {ownerEmail, project: 'vacation-of-a-lifetime', stage: 'chapter-2-complete'},
  authorization: {state: 'owner_scoped', ownerEmail},
  humanAcceptance: {state: 'unreviewed', approved: false},
};
await artifactBucket.writeGeneratedJsonObject(readerLinkSourceObject, readerLinkSource, {ifAbsent: true});
const linkBefore = await artifactBucket.verifyGeneratedArtifact(legacy.storageRef, legacy);
const linkArgs = {
  approved: true,
  requestId: 'vacation-day2-reader-finals-link-contract',
  fileId: readerLinkFileId,
  project: 'vacation-of-a-lifetime',
  stage: 'finals',
};
const linked = await linkDriveAudioToReaderStageOperation({user: {email: ownerEmail}, args: linkArgs});
assert.equal(linked.status, 'linked');
assert.equal(linked.discovery.ok, true);
assert.equal(linked.discovery.folder, 'vacation-of-a-lifetime/finals');
assert.equal(linked.discovery.item.sha256, legacy.sha256);
assert.equal(linked.playback.ok, true);
assert.equal(linked.playback.probe.container, 'ogg');
assert.deepEqual(linked.transport, {copiedBytes: 0, rerendered: false, resynthesized: false, public: false, driveCopy: false, driveMutated: false});
assert.equal(linked.bytePreservation.unchanged, true);
assert.equal(linked.catalog.objectName, 'indexes/audio/v1/catalog/dclarke1005@gmail.com/vacation-of-a-lifetime/finals/' + readerLinkFileId + '.json');
assert.equal(linked.catalog.originalCatalogPreserved, true);
const linkAfter = await artifactBucket.verifyGeneratedArtifact(legacy.storageRef, legacy);
assert.equal(linkAfter.sha256, linkBefore.sha256);
assert.equal(linkAfter.byteCount, linkBefore.byteCount);
assert.equal(linkAfter.generation, linkBefore.generation);
const linkedReplay = await linkDriveAudioToReaderStageOperation({user: {email: ownerEmail}, args: linkArgs});
assert.equal(linkedReplay.catalog.reused, true);
await assert.rejects(() => linkDriveAudioToReaderStageOperation({user: {email: 'junewren28@gmail.com'}, args: linkArgs}), /not owned/);
const routedLink = await driveOperationRunOperation({
  admin,
  user: {email: ownerEmail},
  args: {operation: 'audio.reader_link', args: {...linkArgs, requestId: 'vacation-day2-reader-finals-link-routed-contract'}},
});
assert.equal(routedLink.operation, 'audio.reader_link');
assert.equal(routedLink.completed, true);
assert.equal(routedLink.result.catalog.reused, true);
assert.equal(routedLink.result.transport.copiedBytes, 0);

const server = createHomeCenterMcpServer({google: {}, admin});
assert.ok(!server._registeredTools.audio_render_register, 'registration recovery must remain below drive_operation');
console.log('Home Center audio Reader registration contract: OK');
