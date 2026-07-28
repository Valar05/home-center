'use strict';

const {Storage} = require('@google-cloud/storage');
const {
  GENERATED_ARTIFACT_BUCKET,
  inspectGeneratedArtifact,
  verifyGeneratedArtifact,
  replaceGeneratedArtifactMetadata,
  readGeneratedJsonObject,
  writeGeneratedJsonObject,
} = require('./artifact_bucket');
const {browseAudio, authorizedFile, indexAudioMetadata} = require('./audio_library_api');

const CATALOG_ROOT = 'indexes/audio/v1/catalog';
const REGISTRATION_SCHEMA = 'home-center.audio-catalog-registration.v2';
const AUDIO_TYPES = /^audio\//i;
const AUDIO_EXTENSIONS = /\.(wav|mp3|ogg|flac|m4a|aac|opus)$/i;
let storageClient = null;

function storage() {
  if (!storageClient) storageClient = new Storage();
  return storageClient;
}

function safeText(value, max = 1200) {
  const text = typeof value === 'string' ? value.trim() : value === undefined || value === null ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}

function safeEmail(value) {
  const email = safeText(value, 320).toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : '';
}

function segment(value, fallback = '') {
  const clean = safeText(value, 240).replace(/[^A-Za-z0-9_.@-]+/g, '_').replace(/^_+|_+$/g, '');
  return clean || fallback;
}

function fail(code, message, status = 400) {
  const err = new Error(message);
  err.code = code;
  err.failureKind = code;
  err.status = status;
  return err;
}

function artifactRef(output = {}) {
  const ref = safeText(output.storageRef || output.durableRef, 1400);
  const prefix = 'gs://' + GENERATED_ARTIFACT_BUCKET + '/';
  if (!ref.startsWith(prefix)) throw fail('audio_catalog.invalid_artifact_ref', 'The producer receipt does not name a canonical Home Center GCS audio artifact.', 409);
  return ref;
}

function primaryAudioOutput(result = {}) {
  const outputs = Array.isArray(result.outputs) ? result.outputs : [];
  const primary = result.primaryOutput && typeof result.primaryOutput === 'object' ? result.primaryOutput : null;
  const candidates = [primary, ...outputs].filter(Boolean);
  return candidates.find((item) => safeText(item.mimeType, 160) === 'audio/ogg')
    || candidates.find((item) => AUDIO_TYPES.test(safeText(item.mimeType, 160)) || AUDIO_EXTENSIONS.test(safeText(item.name, 500)))
    || null;
}

function headerProbe(bytes, mimeType, name) {
  const head = Buffer.from(bytes || Buffer.alloc(0));
  const kind = head.subarray(0, 4).toString('ascii');
  const lower = safeText(name, 500).toLowerCase();
  const valid = kind === 'OggS'
    || (kind === 'RIFF' && head.subarray(8, 12).toString('ascii') === 'WAVE')
    || kind === 'fLaC'
    || head.subarray(0, 3).toString('ascii') === 'ID3'
    || (/mpeg|mp3/i.test(mimeType) && head.length >= 2 && head[0] === 0xff && (head[1] & 0xe0) === 0xe0);
  if (!valid) throw fail('audio_catalog.playback_probe_failed', 'The registered audio failed its bounded playback header probe.', 422);
  return {ok: true, byteCount: head.length, container: kind === 'RIFF' ? 'wav' : kind === 'OggS' ? 'ogg' : kind === 'fLaC' ? 'flac' : lower.endsWith('.mp3') ? 'mp3' : 'audio'};
}

function catalogObjectName(ownerEmail, project, stage, sha256) {
  return [CATALOG_ROOT, segment(ownerEmail), segment(project, 'unclassified'), segment(stage, 'review'), sha256 + '.json'].join('/');
}

function sameRegistration(existing, expected) {
  return existing && expected
    && existing.schemaVersion === REGISTRATION_SCHEMA
    && safeText(existing.destination && existing.destination.objectName, 1400) === safeText(expected.destination && expected.destination.objectName, 1400)
    && safeText(existing.destination && existing.destination.sha256, 80) === safeText(expected.destination && expected.destination.sha256, 80)
    && Number(existing.destination && existing.destination.byteCount || 0) === Number(expected.destination && expected.destination.byteCount || 0)
    && safeEmail(existing.authorization && existing.authorization.ownerEmail) === safeEmail(expected.authorization && expected.authorization.ownerEmail)
    && safeText(existing.humanAcceptance && existing.humanAcceptance.state, 80) === 'unreviewed';
}

async function playbackProbe(ref, mimeType, name, bucket = null) {
  if (bucket) {
    const parsedObject = ref.slice(('gs://' + GENERATED_ARTIFACT_BUCKET + '/').length);
    const [bytes] = await bucket.file(parsedObject).download({start: 0, end: 63});
    return headerProbe(bytes, mimeType, name);
  }
  if (process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE === '1') {
    const artifact = await inspectGeneratedArtifact(ref);
    return headerProbe(artifact.bytes.subarray(0, 64), mimeType, name);
  }
  const parsedObject = ref.slice(('gs://' + GENERATED_ARTIFACT_BUCKET + '/').length);
  const [bytes] = await storage().bucket(GENERATED_ARTIFACT_BUCKET).file(parsedObject).download({start: 0, end: 63});
  return headerProbe(bytes, mimeType, name);
}

async function registerAudioArtifactForReader({ownerEmail, output, producerReceiptId, project, stage = 'review', bucket = null}) {
  const owner = safeEmail(ownerEmail);
  if (!owner) throw fail('audio_catalog.owner_required', 'Authenticated owner email is required.', 401);
  const ref = artifactRef(output);
  const name = safeText(output.name, 500);
  const mimeType = safeText(output.mimeType, 160);
  if (!AUDIO_TYPES.test(mimeType) && !AUDIO_EXTENSIONS.test(name)) throw fail('audio_catalog.not_audio', 'The producer primary output is not audio.', 415);
  const expected = {byteCount: Number(output.byteCount), sha256: safeText(output.sha256, 80).toLowerCase()};
  if (!Number.isSafeInteger(expected.byteCount) || expected.byteCount <= 0 || !/^[a-f0-9]{64}$/.test(expected.sha256)) throw fail('audio_catalog.identity_required', 'The producer receipt must include exact audio byte length and SHA-256.', 409);
  const verifiedBefore = await verifyGeneratedArtifact(ref, expected);
  const previousMetadata = verifiedBefore.metadata || {};
  const correctedMetadata = {...previousMetadata};
  delete correctedMetadata.approved;
  correctedMetadata.owner = owner;
  correctedMetadata.ownerEmail = owner;
  correctedMetadata.project = segment(project, 'home-center');
  correctedMetadata.stage = segment(stage, 'review');
  correctedMetadata.executionAuthorized = 'true';
  correctedMetadata.authorizationState = 'owner_scoped';
  correctedMetadata.humanAcceptance = 'unreviewed';
  correctedMetadata.sha256 = expected.sha256;
  correctedMetadata.byteCount = String(expected.byteCount);
  correctedMetadata.mimeType = mimeType;
  correctedMetadata.requestId = safeText(producerReceiptId, 180);
  await replaceGeneratedArtifactMetadata(ref, correctedMetadata);
  const verifiedAfter = await verifyGeneratedArtifact(ref, expected);
  if (verifiedAfter.generation !== verifiedBefore.generation || verifiedAfter.sha256 !== verifiedBefore.sha256 || verifiedAfter.byteCount !== verifiedBefore.byteCount) throw fail('audio_catalog.byte_preservation_failed', 'Artifact identity changed during Reader registration.', 502);

  const objectName = verifiedAfter.object;
  const cleanProject = segment(project, 'home-center');
  const cleanStage = segment(stage, 'review');
  const indexObject = catalogObjectName(owner, cleanProject, cleanStage, expected.sha256);
  const indexedAt = new Date().toISOString();
  const registration = {
    schemaVersion: REGISTRATION_SCHEMA,
    indexedAt,
    source: {receiptId: safeText(producerReceiptId, 180), requestId: safeText(producerReceiptId, 180), name, mimeType, sourcePath: objectName},
    destination: {bucket: GENERATED_ARTIFACT_BUCKET, objectName, storageRef: ref, byteCount: expected.byteCount, sha256: expected.sha256, contentType: mimeType, ownerEmail: owner, project: cleanProject, stage: cleanStage, generation: verifiedAfter.generation, metadata: {requestId: safeText(producerReceiptId, 180), project: cleanProject, stage: cleanStage, ownerEmail: owner, authorizationState: 'owner_scoped', humanAcceptance: 'unreviewed', sha256: expected.sha256, byteCount: String(expected.byteCount)}},
    classification: {ownerEmail: owner, project: cleanProject, stage: cleanStage},
    authorization: {state: 'owner_scoped', ownerEmail: owner, derivedFrom: 'authenticated_principal'},
    humanAcceptance: {state: 'unreviewed', approved: false},
    transport: {copiedBytes: 0, rerendered: false, resynthesized: false, public: false, driveCopy: false},
  };
  const existing = await readGeneratedJsonObject(indexObject, GENERATED_ARTIFACT_BUCKET);
  if (existing && !sameRegistration(existing.value, registration)) throw fail('audio_catalog.registration_conflict', 'A catalog registration already exists with different immutable identity or ownership.', 409);
  const written = existing
    ? {object: indexObject, storageRef: 'gs://' + GENERATED_ARTIFACT_BUCKET + '/' + indexObject, byteCount: existing.bytes.length, reused: true}
    : await writeGeneratedJsonObject(indexObject, registration, {metadata: {ownerEmail: owner, sha256: expected.sha256, schemaVersion: REGISTRATION_SCHEMA, humanAcceptance: 'unreviewed'}, ifAbsent: true});
  const readback = await readGeneratedJsonObject(indexObject, GENERATED_ARTIFACT_BUCKET);
  if (!readback || !sameRegistration(readback.value, registration)) throw fail('audio_catalog.registration_readback_failed', 'Reader catalog registration failed readback validation.', 502);

  let discovery;
  let authorization;
  const effectiveBucket = bucket || (process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE === '1' ? null : storage().bucket(GENERATED_ARTIFACT_BUCKET));
  if (effectiveBucket) {
    const folder = cleanProject + '/' + cleanStage;
    const browsed = await browseAudio(effectiveBucket, {folder}, owner);
    const item = browsed.items.find((candidate) => candidate.sha256 === expected.sha256 && candidate.name === objectName);
    if (!item) throw fail('audio_catalog.discovery_failed', 'The registered audio was not discoverable through the authenticated Reader catalog.', 502);
    discovery = {ok: true, folder, item: {id: item.id, name: item.name, displayName: item.displayName, contentType: item.contentType, size: item.size, sha256: item.sha256, ownerEmail: item.ownerEmail, access: item.access, project: item.project, stage: item.stage, humanAcceptance: item.humanAcceptance || 'unreviewed'}};
    await authorizedFile(effectiveBucket, objectName, owner);
    authorization = {ok: true, state: 'owner_scoped'};
  } else {
    const item = indexAudioMetadata(readback.value, owner);
    if (!item) throw fail('audio_catalog.discovery_failed', 'The registered audio was not discoverable through the authenticated Reader catalog.', 502);
    discovery = {ok: true, folder: cleanProject + '/' + cleanStage, item};
    authorization = {ok: true, state: 'owner_scoped'};
  }
  const probe = await playbackProbe(ref, mimeType, name, effectiveBucket);
  return {
    ok: true,
    status: 'registered',
    producerReceiptId: safeText(producerReceiptId, 180),
    artifact: {name, mimeType, byteCount: expected.byteCount, sha256: expected.sha256, storageRef: ref, generation: verifiedAfter.generation},
    catalog: {schemaVersion: REGISTRATION_SCHEMA, objectName: indexObject, storageRef: written.storageRef, reused: written.reused === true},
    authorization,
    humanAcceptance: 'unreviewed',
    discovery,
    playback: {ok: true, authenticatedReader: true, probe},
    transport: {copiedBytes: 0, rerendered: false, resynthesized: false, public: false, driveCopy: false},
    bytePreservation: {before: {byteCount: verifiedBefore.byteCount, sha256: verifiedBefore.sha256, generation: verifiedBefore.generation}, after: {byteCount: verifiedAfter.byteCount, sha256: verifiedAfter.sha256, generation: verifiedAfter.generation}, unchanged: true},
  };
}

async function registerPrimaryAudioFromReceipt({ownerEmail, receipt, bucket = null}) {
  const result = receipt && receipt.result || {};
  const status = safeText(receipt && receipt.status, 80);
  if (!['completed', 'success'].includes(status) || safeText(receipt && receipt.operation, 120) !== 'audio.render') throw fail('audio_catalog.producer_not_terminal', 'Registration requires a terminal successful audio.render receipt.', 409);
  const output = primaryAudioOutput(result);
  if (!output) throw fail('audio_catalog.primary_output_missing', 'The audio.render receipt has no primary playable audio output.', 409);
  const project = safeText(output.metadata && output.metadata.project || result.project || 'home-center', 160);
  const stage = safeText(output.metadata && output.metadata.stage || result.stage || 'review', 120) || 'review';
  return registerAudioArtifactForReader({ownerEmail, output, producerReceiptId: receipt.requestId, project, stage, bucket});
}

async function recoverAudioRenderRegistrationOperation({admin, user, args = {}, bucket = null}) {
  const requestId = safeText(args.requestId || args.producerReceiptId, 180);
  if (!requestId) throw fail('audio_catalog.receipt_required', 'requestId is required.', 400);
  const ownerEmail = safeEmail(user && user.email);
  if (!ownerEmail) throw fail('audio_catalog.auth_required', 'Authenticated owner identity is required.', 401);
  const ref = admin.firestore().collection('driveBridgeAudit').doc(requestId);
  const snapshot = await ref.get();
  if (!snapshot.exists) throw fail('audio_catalog.receipt_not_found', 'The audio.render producer receipt was not found.', 404);
  const receipt = snapshot.data() || {};
  if (safeEmail(receipt.actor) !== ownerEmail) throw fail('audio_catalog.receipt_forbidden', 'The audio.render producer receipt is not owned by this caller.', 403);
  const registration = await registerPrimaryAudioFromReceipt({ownerEmail, receipt, bucket});
  const recovery = {operation: 'audio.render_register', requestId, status: 'completed', execution: 'registration_only', ownerEmail, authorizationState: 'owner_scoped', humanAcceptance: 'unreviewed', registration, idempotent: registration.catalog.reused === true, completedAtMs: Date.now()};
  await admin.firestore().collection('audioRenderRegistrations').doc(requestId).set(recovery, {merge: false});
  await ref.set({result: {...(receipt.result || {}), readerRegistration: registration, humanAcceptance: 'unreviewed'}, readerRegistration: registration, updatedAtMs: Date.now()}, {merge: true});
  return recovery;
}

module.exports = {
  CATALOG_ROOT,
  REGISTRATION_SCHEMA,
  primaryAudioOutput,
  registerAudioArtifactForReader,
  registerPrimaryAudioFromReceipt,
  recoverAudioRenderRegistrationOperation,
};
