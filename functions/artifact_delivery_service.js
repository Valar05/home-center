'use strict';

const {createHash} = require('node:crypto');
const {Readable} = require('node:stream');
const {Storage} = require('@google-cloud/storage');

const CONTRACT_VERSION = 'home-center.artifact-delivery.v1';
const DELIVERY_COLLECTION = 'artifactDeliveryReceipts';
const MAX_ARTIFACTS = Number(process.env.HOME_CENTER_ARTIFACT_DELIVERY_MAX_ARTIFACTS || 24);
const MAX_ARTIFACT_BYTES = Number(process.env.HOME_CENTER_ARTIFACT_DELIVERY_MAX_ARTIFACT_BYTES || 256 * 1024 * 1024);
const MAX_TOTAL_BYTES = Number(process.env.HOME_CENTER_ARTIFACT_DELIVERY_MAX_TOTAL_BYTES || 512 * 1024 * 1024);
const CONCURRENCY = Math.max(1, Math.min(Number(process.env.HOME_CENTER_ARTIFACT_DELIVERY_CONCURRENCY || 3), 6));

function text(value, max = 1200) {
  const clean = typeof value === 'string' ? value.trim() : '';
  return clean.length > max ? clean.slice(0, max) : clean;
}

function fail(code, message, status = 400, details = {}) {
  const error = new Error(message);
  error.code = code;
  error.failureKind = code;
  error.status = status;
  error.details = details;
  return error;
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function hashJson(value) {
  return sha256(Buffer.from(JSON.stringify(stable(value)), 'utf8'));
}

function ownerKey(ownerEmail) {
  return 'owner_' + sha256(Buffer.from(ownerEmail.toLowerCase(), 'utf8')).slice(0, 32);
}

function filename(value, fallback = 'artifact.bin') {
  const clean = text(value, 240).replace(/\\/g, '/').split('/').pop().replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
  return clean || fallback;
}

const MIME_BY_EXTENSION = Object.freeze({
  '.glb': 'model/gltf-binary',
  '.png': 'image/png',
  '.gif': 'image/gif',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.mp4': 'video/mp4',
  '.wav': 'audio/wav',
  '.ogg': 'audio/ogg',
  '.mp3': 'audio/mpeg',
  '.flac': 'audio/flac',
  '.json': 'application/json',
  '.pdf': 'application/pdf',
  '.txt': 'text/plain',
  '.md': 'text/markdown',
  '.py': 'text/x-python',
  '.log': 'text/plain',
});

const SUPPORTED_MIME = new Set(Object.values(MIME_BY_EXTENSION));

function inferredMime(name, value) {
  const explicit = text(value, 160).toLowerCase();
  if (SUPPORTED_MIME.has(explicit)) return explicit;
  const lower = name.toLowerCase();
  const extension = Object.keys(MIME_BY_EXTENSION).find((suffix) => lower.endsWith(suffix));
  const inferred = extension ? MIME_BY_EXTENSION[extension] : '';
  if (!inferred) throw fail('artifact_delivery.mime_unsupported', 'Receipt artifact has an unsupported or missing MIME type: ' + name, 422, {name, mimeType: explicit});
  return inferred;
}

function configuredBuckets() {
  return new Set([
    process.env.GENERATED_ARTIFACT_BUCKET,
    process.env.HOME_CENTER_GENERATED_BUCKET,
    process.env.HOME_CENTER_ARTIFACT_BUCKET,
    process.env.ARTIFACT_BUCKET,
    process.env.RENDER_CACHE_BUCKET,
    process.env.COMMAND_CENTER_RENDER_BUCKET,
    'home-center-generated',
  ].map((value) => text(value, 240)).filter(Boolean));
}

function parseReceiptGsRef(ref) {
  const clean = text(ref, 1600);
  const match = /^gs:\/\/([^/]+)\/(.+)$/.exec(clean);
  if (!match) throw fail('artifact_delivery.reference_invalid', 'Receipt artifact must use a canonical private gs:// reference.', 422);
  if (!configuredBuckets().has(match[1])) throw fail('artifact_delivery.reference_forbidden', 'Receipt artifact is outside configured Home Center artifact buckets.', 403);
  return {ref: clean, bucket: match[1], objectName: match[2]};
}

function normalizedCandidate(value, context = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const ref = text(value.storageRef || value.durableRef || value.artifactRef, 1600);
  if (!ref.startsWith('gs://')) return null;
  const digest = text(value.sha256 || value.expectedSha256 || value.readbackSha256, 64).toLowerCase();
  const byteLength = Number(value.byteCount || value.byteLength || value.expectedByteCount || value.readbackByteCount || 0);
  if (!/^[a-f0-9]{64}$/.test(digest) || !Number.isSafeInteger(byteLength) || byteLength < 1) return null;
  const parsed = parseReceiptGsRef(ref);
  const explicitName = text(value.name || value.filename, 240);
  const contextName = text(context.name, 240);
  const contextHasKnownExtension = Object.keys(MIME_BY_EXTENSION).some((suffix) => contextName.toLowerCase().endsWith(suffix));
  const name = filename(explicitName || (contextHasKnownExtension ? contextName : parsed.objectName.split('/').pop()));
  const mediaType = inferredMime(name, value.mimeType || value.mediaType || value.contentType);
  return {
    role: text(value.role || value.kind || context.role || context.name, 120) || 'artifact',
    name,
    mediaType,
    byteLength,
    sha256: digest,
    storageRef: parsed.ref,
    bucket: parsed.bucket,
    objectName: parsed.objectName,
  };
}


function normalizedGitHubCandidate(value, context = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const identity = value.identity && typeof value.identity === 'object' ? value.identity : null;
  const locations = [
    value.location,
    ...(Array.isArray(value.locations) ? value.locations : []),
  ].filter(Boolean);
  const location = locations.find((item) => item && item.kind === 'github');
  if (!identity || !location) return null;
  const digest = text(identity.sha256 || identity.digest, 64).toLowerCase();
  const byteLength = Number(identity.byteLength || identity.byteCount || identity.size || 0);
  const repository = text(location.repository || location.repo, 240);
  const ref = text(location.ref || location.sha, 80).toLowerCase();
  const artifactPath = text(location.path || location.filePath, 1000).replace(/^\/+/, '');
  if (!/^[a-f0-9]{64}$/.test(digest) || !Number.isSafeInteger(byteLength) || byteLength < 1) return null;
  if (!/^[^/]+\/[^/]+$/.test(repository) || !/^[a-f0-9]{40}$/.test(ref)) return null;
  if (!artifactPath || artifactPath.includes('..')) return null;
  const name = filename(identity.fileName || identity.name || artifactPath.split('/').pop());
  return {
    role: text(value.role || context.role || context.name, 120) || 'artifact',
    name,
    mediaType: inferredMime(name, identity.mediaType || identity.mimeType),
    byteLength,
    sha256: digest,
    sourceKind: 'github',
    repository,
    ref,
    path: artifactPath,
    storageRef: 'github://' + repository + '@' + ref + '/' + artifactPath,
  };
}

function recursivelyExtractArtifacts(root) {
  const candidates = [];
  const seenObjects = new Set();
  function visit(value, context, depth) {
    if (depth > 10 || value === null || value === undefined) return;
    if (Array.isArray(value)) {
      value.slice(0, 128).forEach((item, index) => visit(item, {...context, name: context.name || 'artifact-' + (index + 1)}, depth + 1));
      return;
    }
    if (typeof value !== 'object') return;
    if (seenObjects.has(value)) return;
    seenObjects.add(value);
    const candidate = normalizedCandidate(value, context) || normalizedGitHubCandidate(value, context);
    if (candidate) candidates.push(candidate);
    Object.entries(value).slice(0, 256).forEach(([key, child]) => visit(child, {name: key, role: context.role || key}, depth + 1));
  }
  visit(root, {}, 0);
  return candidates;
}

function renderHashEntry(output, name) {
  const hashes = output && output.artifactHashes && typeof output.artifactHashes === 'object' ? output.artifactHashes : {};
  const base = filename(name);
  const stripped = base.replace(/^\d+-/, '');
  return hashes[base] || hashes[stripped] || null;
}

function renderReferenceCandidates(output = {}) {
  const candidates = [];
  const add = (role, ref, expectedName) => {
    const storageRef = text(ref, 1600);
    if (!storageRef) return;
    const parsed = parseReceiptGsRef(storageRef);
    const name = filename(expectedName || parsed.objectName.split('/').pop());
    const expected = renderHashEntry(output, name);
    if (!expected) return;
    const candidate = normalizedCandidate({
      role,
      name,
      mimeType: inferredMime(name, ''),
      byteCount: expected.byteCount,
      sha256: expected.sha256,
      storageRef,
    });
    if (candidate) candidates.push(candidate);
  };
  const one = [
    ['contact_sheet', output.contactSheetRef, 'contact-sheet.png'],
    ['looping_gif', output.loopingGifRef, 'walk-loop.gif'],
    ['validation_manifest', output.validationManifestRef, ''],
    ['animated_glb', output.animatedGlbRef, ''],
    ['original_script', output.originalScriptRef, ''],
    ['script_input_hashes', output.scriptInputHashesRef, ''],
    ['producer_version_settings', output.blenderVersionSettingsRef, ''],
    ['stdout', output.stdoutRef, ''],
    ['stderr', output.stderrRef, ''],
  ];
  one.forEach((entry) => add(...entry));
  const many = [
    ['render', output.renderRefs],
    ['fixed_camera', output.fixedCameraRenderRefs],
    ['orthogonal', output.diagnosticRenderRefs],
    ['three_d_artifact', output.threeDArtifactRefs],
    ['native_data', output.nativeDataRefs],
  ];
  many.forEach(([role, refs]) => (Array.isArray(refs) ? refs : []).slice(0, 64).forEach((ref) => add(role, ref, '')));
  return candidates;
}

function uniqueCandidates(receipt, artifactNames = []) {
  const output = receipt && receipt.result && typeof receipt.result === 'object' ? receipt.result : receipt;
  const all = [...recursivelyExtractArtifacts(output), ...renderReferenceCandidates(output)];
  const byIdentity = new Map();
  all.forEach((candidate) => {
    const key = [candidate.sha256, candidate.byteLength, candidate.mediaType, candidate.name].join(':');
    if (!byIdentity.has(key)) byIdentity.set(key, candidate);
  });
  let candidates = [...byIdentity.values()].sort((a, b) => (a.role + '\n' + a.name + '\n' + a.sha256).localeCompare(b.role + '\n' + b.name + '\n' + b.sha256));
  const selectors = (Array.isArray(artifactNames) ? artifactNames : []).map((value) => text(value, 240)).filter(Boolean);
  if (selectors.length) {
    const selected = new Set(selectors);
    candidates = candidates.filter((item) => selected.has(item.name) || selected.has(item.role));
    const matched = new Set(candidates.flatMap((item) => [item.name, item.role]).filter((value) => selected.has(value)));
    const missing = selectors.filter((value) => !matched.has(value));
    if (missing.length) throw fail('artifact_delivery.selector_missing', 'Producer receipt does not contain requested artifact selectors: ' + missing.join(', '), 404, {missing});
  }
  if (!candidates.length) throw fail('artifact_delivery.artifacts_missing', 'Terminal producer receipt contains no supported hash-bound GCS artifacts.', 404);
  if (candidates.length > MAX_ARTIFACTS) throw fail('artifact_delivery.too_many_artifacts', 'Receipt delivery exceeds max artifact count ' + MAX_ARTIFACTS + '.', 413);
  candidates.forEach((candidate) => {
    if (candidate.byteLength > MAX_ARTIFACT_BYTES) throw fail('artifact_delivery.artifact_too_large', candidate.name + ' exceeds delivery byte limit ' + MAX_ARTIFACT_BYTES + '.', 413);
  });
  const totalBytes = candidates.reduce((sum, item) => sum + item.byteLength, 0);
  if (totalBytes > MAX_TOTAL_BYTES) throw fail('artifact_delivery.total_too_large', 'Receipt delivery exceeds total byte limit ' + MAX_TOTAL_BYTES + '.', 413);
  return {candidates, totalBytes};
}

const RECEIPT_SOURCES = Object.freeze([
  {kind: 'artifact_transport', collection: 'artifactTransportReceipts', terminal: (record) => text(record.receipt && record.receipt.state, 80) === 'accepted', owner: (record) => text(record.owner, 320).toLowerCase()},
  {kind: 'storage_ingest', collection: 'commandCenterArtifactCatalog', terminal: (record) => record && record.verification && record.verification.verified === true && text(record.lifecycleState, 40) === 'proposed', owner: (record) => text(record.ownerEmail, 320).toLowerCase()},
  {kind: 'drive_audit', collection: 'driveBridgeAudit', terminal: (record) => ['completed', 'success', 'failed', 'stalled', 'needs_reconciliation', 'registration_required'].includes(text(record.status || record.result && record.result.status, 80)), owner: (record) => text(record.actor || record.ownerEmail || record.result && record.result.ownerEmail, 320).toLowerCase()},
  {kind: 'blender_workspace', collection: 'blenderWorkspaceOperations', terminal: (record) => text(record.state, 80) === 'completed', owner: (record) => text(record.owner, 320).toLowerCase()},
  {kind: 'foundry_historical', collection: 'foundryAssetJobs', terminal: (record) => text(record.state, 80) === 'completed', owner: (record) => text(record.owner, 320).toLowerCase()},
  {kind: 'archived_receipt', public: false, collection: 'commandCenterRenderRequests', terminal: (record) => text(record.status, 80) === 'completed', owner: (record) => text(record.requestedBy, 320).toLowerCase(), legacyOwnerKey: true},
]);

async function resolveProducerReceipt({admin, ownerEmail, producerReceiptId, producerKind = ''}) {
  const publicSources = RECEIPT_SOURCES.filter((source) => source.public !== false);
  const sources = producerKind ? publicSources.filter((source) => source.kind === producerKind) : RECEIPT_SOURCES;
  if (!sources.length) throw fail('artifact_delivery.producer_kind_unsupported', 'Unsupported producerKind.', 400, {supported: publicSources.map((source) => source.kind)});
  const snapshots = await Promise.all(sources.map(async (source) => ({source, snapshot: await admin.firestore().collection(source.collection).doc(producerReceiptId).get()})));
  const found = snapshots.filter((item) => item.snapshot.exists);
  if (!found.length) throw fail('artifact_delivery.receipt_not_found', 'Producer receipt was not found.', 404);
  if (found.length > 1) throw fail('artifact_delivery.receipt_ambiguous', 'Producer receipt ID exists in multiple owned producer stores; specify producerKind.', 409);
  const source = found[0].source;
  const receipt = found[0].snapshot.data() || {};
  const recordedOwner = source.owner(receipt);
  const expectedOwnerKey = ownerKey(ownerEmail);
  const renderOwnerKey = text(receipt.ownerKey, 80);
  if (recordedOwner ? recordedOwner !== ownerEmail : !source.legacyOwnerKey || renderOwnerKey !== expectedOwnerKey) {
    throw fail('artifact_delivery.receipt_forbidden', 'Producer receipt is not owned by the authenticated caller.', 403);
  }
  if (!source.terminal(receipt)) throw fail('artifact_delivery.receipt_not_terminal', 'Producer receipt is not terminal or recoverable.', 409);
  const receiptState = text(receipt.status || receipt.result && receipt.result.status, 80);
  if (!['completed', 'success'].includes(receiptState)) {
    try { uniqueCandidates(receipt, []); }
    catch (_error) { throw fail('artifact_delivery.failed_receipt_has_no_verified_candidate', 'Failed or stalled producer receipts are recoverable only when they already contain hash-bound artifact bytes.', 409); }
  }
  return {producerKind: source.kind, collection: source.collection, receipt, receiptState};
}

function humanAcceptance(receipt) {
  const value = receipt && receipt.result && receipt.result.humanAcceptance !== undefined ? receipt.result.humanAcceptance : receipt && receipt.humanAcceptance;
  return text(value && typeof value === 'object' ? value.state : value, 80) || 'unreviewed';
}

function readable(value) {
  if (value && typeof value[Symbol.asyncIterator] === 'function') return value;
  if (value && typeof value.pipe === 'function') return value;
  return Readable.from([Buffer.isBuffer(value) ? value : Buffer.from(value || [])]);
}

async function digestStream(stream) {
  const hash = createHash('sha256');
  let byteLength = 0;
  for await (const chunk of readable(stream)) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    byteLength += bytes.length;
    hash.update(bytes);
  }
  return {byteLength, sha256: hash.digest('hex')};
}

function driveQueryValue(value) {
  return text(value, 180).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function deliveryDigestKey(ownerEmail, candidate) {
  return hashJson({ownerEmail: ownerEmail.toLowerCase(), sha256: candidate.sha256, byteLength: candidate.byteLength, mediaType: candidate.mediaType, name: candidate.name});
}

async function verifyGcsCandidate(storage, candidate) {
  const file = storage.bucket(candidate.bucket).file(candidate.objectName);
  const [metadata] = await file.getMetadata();
  const metadataBytes = Number(metadata && metadata.size || 0);
  const metadataSha = text(metadata && metadata.metadata && metadata.metadata.sha256, 64).toLowerCase();
  if (metadataBytes !== candidate.byteLength) throw fail('artifact_delivery.gcs_length_mismatch', 'GCS byte length does not match producer receipt for ' + candidate.name + '.', 409);
  if (metadataSha && metadataSha !== candidate.sha256) throw fail('artifact_delivery.gcs_metadata_digest_mismatch', 'GCS digest metadata does not match producer receipt for ' + candidate.name + '.', 409);
  const verified = await digestStream(file.createReadStream());
  if (verified.byteLength !== candidate.byteLength || verified.sha256 !== candidate.sha256) throw fail('artifact_delivery.gcs_readback_mismatch', 'GCS readback does not match producer receipt for ' + candidate.name + '.', 409);
  return {file, generation: text(metadata && metadata.generation, 100), ...verified};
}

async function publishToDrive({google, auth, ownerEmail, parentFolderId, candidate, verified}) {
  const drive = google.drive({version: 'v3', auth});
  const digestKey = deliveryDigestKey(ownerEmail, candidate);
  const query = "trashed=false and appProperties has { key='homeCenterArtifactDeliveryDigestKey' and value='" + driveQueryValue(digestKey) + "' }";
  const found = await drive.files.list({q: query, pageSize: 10, orderBy: 'createdTime asc', fields: 'files(id,name,mimeType,webViewLink,parents,size,appProperties,createdTime)', spaces: 'drive'});
  let existing = Array.isArray(found.data && found.data.files) ? found.data.files[0] : null;
  let adoptedReadback = null;
  if (!existing && parentFolderId) {
    const existingQuery = "trashed=false and name='" + driveQueryValue(candidate.name) + "' and '" + driveQueryValue(parentFolderId) + "' in parents";
    const sameFolder = await drive.files.list({q: existingQuery, pageSize: 25, orderBy: 'createdTime asc', fields: 'files(id,name,mimeType,webViewLink,parents,size,appProperties,createdTime)', spaces: 'drive'});
    const possible = (Array.isArray(sameFolder.data && sameFolder.data.files) ? sameFolder.data.files : []).filter((item) =>
      text(item && item.name, 240) === candidate.name &&
      text(item && item.mimeType, 160) === candidate.mediaType &&
      Number(item && item.size || 0) === candidate.byteLength &&
      Array.isArray(item && item.parents) && item.parents.includes(parentFolderId)
    );
    for (const item of possible) {
      const response = await drive.files.get({fileId: item.id, alt: 'media', supportsAllDrives: true}, {responseType: 'stream'});
      const readback = await digestStream(response.data);
      if (readback.byteLength === candidate.byteLength && readback.sha256 === candidate.sha256) {
        existing = item;
        adoptedReadback = readback;
        break;
      }
    }
  }
  let metadata = existing;
  if (!metadata) {
    const created = await drive.files.create({
      requestBody: {
        name: candidate.name,
        mimeType: candidate.mediaType,
        ...(parentFolderId ? {parents: [parentFolderId]} : {}),
        appProperties: {
          homeCenterArtifactDeliveryDigestKey: digestKey,
          homeCenterSha256: candidate.sha256,
          homeCenterByteLength: String(candidate.byteLength),
          homeCenterArtifactRole: candidate.role,
        },
      },
      media: {mimeType: candidate.mediaType, body: verified.file.createReadStream()},
      fields: 'id,name,mimeType,webViewLink,parents,size,appProperties,createdTime',
      supportsAllDrives: true,
    });
    metadata = created.data || {};
  }
  const fileId = text(metadata && metadata.id, 240);
  if (!fileId) throw fail('artifact_delivery.drive_file_id_missing', 'Drive did not return a delivery file ID.', 502);
  let readback = adoptedReadback;
  if (!readback) {
    const response = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'stream'});
    readback = await digestStream(response.data);
  }
  if (readback.byteLength !== candidate.byteLength || readback.sha256 !== candidate.sha256) throw fail('artifact_delivery.drive_readback_mismatch', 'Drive delivery readback does not match producer receipt for ' + candidate.name + '.', 502);
  return {
    role: candidate.role,
    name: candidate.name,
    mimeType: candidate.mediaType,
    byteLength: candidate.byteLength,
    sha256: candidate.sha256,
    source: {storageRef: candidate.storageRef, generation: verified.generation},
    delivery: {
      kind: 'private_drive_resource',
      fileId,
      durableRef: 'drive://' + fileId,
      webViewLink: text(metadata.webViewLink, 1400),
      reused: !!existing,
      verified: true,
      readbackByteLength: readback.byteLength,
      readbackSha256: readback.sha256,
      resourceLink: {type: 'resource_link', uri: 'drive://' + fileId, name: candidate.name, mimeType: candidate.mediaType, size: candidate.byteLength},
    },
  };
}

async function boundedMap(items, limit, mapper) {
  const results = new Array(items.length);
  const failures = [];
  let next = 0;
  async function worker() {
    while (true) {
      const index = next++;
      if (index >= items.length) return;
      try {
        results[index] = await mapper(items[index], index);
      } catch (error) {
        failures.push({index, error});
      }
    }
  }
  await Promise.all(Array.from({length: Math.min(limit, items.length)}, () => worker()));
  if (failures.length) {
    failures.sort((left, right) => left.index - right.index);
    const first = failures[0];
    first.error.details = {...(first.error.details || {}), failedArtifactIndexes: failures.map((item) => item.index), completedSiblingIndexes: results.map((item, index) => item ? index : -1).filter((index) => index >= 0)};
    throw first.error;
  }
  return results;
}

async function materializeReceiptArtifactsOperation({google, admin, auth, user, args = {}}, helpers = {}) {
  const requestId = text(args.requestId, 180);
  const producerReceiptId = text(args.producerReceiptId, 180);
  const producerKind = text(args.producerKind, 80);
  const ownerEmail = text(user && user.email, 320).toLowerCase();
  const forbiddenReferenceFields = ['storageRef', 'durableRef', 'artifactRef', 'artifactRefs', 'gcsPath', 'url', 'uri'].filter((field) => args[field] !== undefined);
  if (forbiddenReferenceFields.length) throw fail('artifact_delivery.receipt_only', 'Artifact delivery accepts only a producerReceiptId; arbitrary paths, references, and URLs are forbidden.', 400, {rejectedFields: forbiddenReferenceFields});
  if (!requestId) throw fail('artifact_delivery.request_id_required', 'requestId is required.');
  if (!producerReceiptId) throw fail('artifact_delivery.receipt_id_required', 'producerReceiptId is required.');
  if (!ownerEmail) throw fail('artifact_delivery.owner_required', 'Authenticated owner is required.', 401);
  if (!google || !auth) throw fail('artifact_delivery.drive_auth_required', 'Authenticated Drive context is required for private review materialization.', 401);
  const parentFolderId = text(args.parentFolderId, 220);
  if (parentFolderId && !/^[A-Za-z0-9_-]{8,220}$/.test(parentFolderId)) throw fail('artifact_delivery.parent_invalid', 'parentFolderId is invalid.', 400);
  const lookup = helpers.resolveReceipt || resolveProducerReceipt;
  const resolved = await lookup({admin, ownerEmail, producerReceiptId, producerKind});
  const selection = uniqueCandidates(resolved.receipt, args.artifactNames);
  const inputHash = hashJson({
    contractVersion: CONTRACT_VERSION,
    producerKind: resolved.producerKind,
    producerReceiptId,
    parentFolderId,
    artifacts: selection.candidates.map((item) => ({role: item.role, name: item.name, mediaType: item.mediaType, byteLength: item.byteLength, sha256: item.sha256, sourceKind: item.sourceKind || 'gcs'})),
  });
  const receiptRef = admin.firestore().collection(DELIVERY_COLLECTION).doc(requestId);
  const prior = await receiptRef.get();
  if (prior.exists) {
    const existing = prior.data() || {};
    if (existing.ownerEmail !== ownerEmail) throw fail('artifact_delivery.request_forbidden', 'Delivery request is not owned by the authenticated caller.', 403);
    if (existing.inputHash !== inputHash) throw fail('artifact_delivery.idempotency_conflict', 'requestId is already bound to different producer artifacts.', 409);
    return {...existing.result, idempotent: true};
  }
  const storage = helpers.storage || new Storage();
  const publisher = helpers.publish || publishToDrive;
  const map = helpers.boundedMap || boundedMap;
  const artifacts = await map(selection.candidates, CONCURRENCY, async (candidate) => {
    let verified;
    if (candidate.sourceKind === 'github') {
      if (typeof helpers.verifyGithubCandidate !== 'function') {
        throw fail('artifact_delivery.github_verifier_missing', 'GitHub artifact delivery requires the authenticated GitHub verifier.', 503);
      }
      verified = await helpers.verifyGithubCandidate(candidate);
    } else {
      verified = await verifyGcsCandidate(storage, candidate);
    }
    return publisher({google, auth, ownerEmail, parentFolderId, candidate, verified});
  });
  const reusedBytes = artifacts.filter((item) => item.delivery.reused).reduce((sum, item) => sum + item.byteLength, 0);
  const transferredBytes = artifacts.filter((item) => !item.delivery.reused).reduce((sum, item) => sum + item.byteLength, 0);
  const result = {
    ok: true,
    contractVersion: CONTRACT_VERSION,
    operation: 'artifact.delivery.materialize_receipt',
    requestId,
    producer: {kind: resolved.producerKind, receiptId: producerReceiptId, receiptState: resolved.receiptState || 'completed', producerSuccessRequired: false},
    status: 'review_ready',
    transportState: {state: 'completed', artifactCount: artifacts.length, expectedBytes: selection.totalBytes, transferredBytes, reusedBytes, concurrency: CONCURRENCY, rerendered: false, resynthesized: false, public: false},
    authorization: {state: 'owner_scoped', ownerEmail},
    humanAcceptance: {state: humanAcceptance(resolved.receipt), changed: false},
    artifacts,
  };
  const record = {contractVersion: CONTRACT_VERSION, requestId, ownerEmail, inputHash, producerKind: resolved.producerKind, producerReceiptId, status: 'completed', result, createdAtMs: Date.now()};
  if (typeof receiptRef.create === 'function') {
    try {
      await receiptRef.create(record);
    } catch (error) {
      if (!/already|exists|condition/i.test(String(error && (error.message || error.code)))) throw error;
      const raced = await receiptRef.get();
      const existing = raced.exists ? raced.data() || {} : {};
      if (existing.ownerEmail !== ownerEmail || existing.inputHash !== inputHash) throw fail('artifact_delivery.idempotency_conflict', 'Concurrent requestId reuse changed producer artifacts.', 409);
      return {...existing.result, idempotent: true};
    }
  } else {
    await receiptRef.set(record, {merge: false});
  }
  return {...result, idempotent: false};
}


const REVIEW_COLLECTION = 'artifactReviewRecords';
const REVIEW_LINK_COLLECTION = 'artifactReviewSuccessorLinks';
const REVIEW_VERDICTS = new Set(['accepted', 'rejected', 'revision_requested', 'unreviewed']);

function normalizedSuccessorPlan(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const operation = text(value.operation, 120);
  const idempotencyKey = text(value.idempotencyKey, 180);
  const changes = text(value.changes || value.changeSummary, 1200);
  if (!operation || !idempotencyKey || !changes) throw fail('artifact_review.successor_plan_incomplete', 'Rejected or revision-requested work requires a successorPlan with operation, idempotencyKey, and concrete changes.', 400);
  return {operation, idempotencyKey, changes};
}

const REVIEW_EVIDENCE_VIEWS = new Set(['front', 'back', 'left', 'right', 'side', 'top', 'perspective']);

function normalizedSimplificationEvidence(value) {
  if (value == null) return [];
  if (!Array.isArray(value) || !value.length || value.length > 64) {
    throw fail('artifact_review.simplification_evidence_invalid', 'simplificationEvidence must contain 1-64 remove-or-merge comparisons.', 400);
  }
  return value.map((entry, index) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw fail('artifact_review.simplification_evidence_invalid', 'Every simplification comparison must be an object.', 400, {index});
    const component = text(entry.component, 240);
    const method = text(entry.method, 80);
    const status = text(entry.status, 80);
    const views = Array.from(new Set((Array.isArray(entry.views) ? entry.views : []).map((view) => text(view, 80).toLowerCase()).filter(Boolean)));
    const maxVisibleErrorPx = Number(entry.maxVisibleErrorPx);
    const comparison = text(entry.comparison || entry.reason, 1600);
    if (!component || method !== 'remove_or_merge' || status !== 'passed' || !views.length || views.some((view) => !REVIEW_EVIDENCE_VIEWS.has(view)) || !Number.isFinite(maxVisibleErrorPx) || maxVisibleErrorPx <= 0 || maxVisibleErrorPx > 64) {
      throw fail('artifact_review.simplification_evidence_invalid', 'Each comparison requires a component, method=remove_or_merge, status=passed, supported views, and maxVisibleErrorPx from 0-64.', 400, {index});
    }
    return {component, method, status, views, maxVisibleErrorPx, ...(comparison ? {comparison} : {})};
  });
}

async function recordArtifactReviewOperation({admin, user, args = {}}) {
  const requestId = text(args.requestId, 180);
  const deliveryRequestId = text(args.deliveryRequestId, 180);
  const ownerEmail = text(user && user.email, 320).toLowerCase();
  const verdict = text(args.verdict, 80);
  if (!requestId) throw fail('artifact_review.request_id_required', 'requestId is required.');
  if (!deliveryRequestId) throw fail('artifact_review.delivery_request_required', 'deliveryRequestId is required.');
  if (!ownerEmail) throw fail('artifact_review.owner_required', 'Authenticated owner is required.', 401);
  if (!REVIEW_VERDICTS.has(verdict)) throw fail('artifact_review.verdict_invalid', 'verdict must be accepted, rejected, revision_requested, or unreviewed.', 400);
  const deliverySnapshot = await admin.firestore().collection(DELIVERY_COLLECTION).doc(deliveryRequestId).get();
  if (!deliverySnapshot.exists) throw fail('artifact_review.delivery_not_found', 'Review-ready delivery receipt was not found.', 404);
  const delivery = deliverySnapshot.data() || {};
  if (delivery.ownerEmail !== ownerEmail) throw fail('artifact_review.delivery_forbidden', 'Delivery receipt is not owned by the authenticated caller.', 403);
  if (!delivery.result || delivery.result.status !== 'review_ready') throw fail('artifact_review.delivery_not_ready', 'Only review-ready delivery receipts can receive a human verdict.', 409);
  const needsSuccessor = ['rejected', 'revision_requested'].includes(verdict);
  const successorPlan = needsSuccessor ? normalizedSuccessorPlan(args.successorPlan) : null;
  if (needsSuccessor && !successorPlan) throw fail('artifact_review.successor_plan_incomplete', 'Rejected or revision-requested work requires a successorPlan with operation, idempotencyKey, and concrete changes.', 400);
  const reason = text(args.reason, 1600);
  if (['rejected', 'revision_requested'].includes(verdict) && !reason) throw fail('artifact_review.reason_required', 'Rejected or revision-requested work requires a bounded reason.', 400);
  const simplificationEvidence = normalizedSimplificationEvidence(args.simplificationEvidence);
  const purposeValid = verdict === 'accepted' && simplificationEvidence.length > 0;
  const inputHash = hashJson({contractVersion: CONTRACT_VERSION, deliveryRequestId, verdict, reason, successorPlan, simplificationEvidence});
  const ref = admin.firestore().collection(REVIEW_COLLECTION).doc(requestId);
  const prior = await ref.get();
  if (prior.exists) {
    const existing = prior.data() || {};
    if (existing.ownerEmail !== ownerEmail) throw fail('artifact_review.request_forbidden', 'Review request is not owned by the authenticated caller.', 403);
    if (existing.inputHash !== inputHash) throw fail('artifact_review.idempotency_conflict', 'requestId is already bound to a different human verdict.', 409);
    return {...existing.result, idempotent: true};
  }
  const result = {
    ok: true,
    contractVersion: CONTRACT_VERSION,
    operation: 'artifact.review.record',
    requestId,
    deliveryRequestId,
    producer: delivery.result.producer,
    transportState: delivery.result.transportState,
    humanAcceptance: {state: verdict, reviewedBy: ownerEmail, reviewedAtMs: Date.now(), reason},
    candidatePreserved: true,
    promotionAllowed: verdict === 'accepted',
    purposeValid,
    simplificationEvidence,
    successor: successorPlan ? {state: 'planned', plan: successorPlan, priorCandidateChanged: true} : null,
  };
  const record = {requestId, ownerEmail, inputHash, deliveryRequestId, verdict, status: 'completed', result, createdAtMs: result.humanAcceptance.reviewedAtMs};
  if (typeof ref.create === 'function') await ref.create(record); else await ref.set(record, {merge: false});
  return {...result, idempotent: false};
}

async function linkArtifactReviewSuccessorOperation({admin, user, args = {}}, helpers = {}) {
  const requestId = text(args.requestId, 180);
  const reviewRequestId = text(args.reviewRequestId, 180);
  const successorReceiptId = text(args.successorReceiptId, 180);
  const producerKind = text(args.producerKind, 80);
  const ownerEmail = text(user && user.email, 320).toLowerCase();
  if (!requestId || !reviewRequestId || !successorReceiptId) throw fail('artifact_review.successor_link_fields_required', 'requestId, reviewRequestId, and successorReceiptId are required.');
  const reviewRef = admin.firestore().collection(REVIEW_COLLECTION).doc(reviewRequestId);
  const reviewSnapshot = await reviewRef.get();
  if (!reviewSnapshot.exists) throw fail('artifact_review.not_found', 'Review record was not found.', 404);
  const review = reviewSnapshot.data() || {};
  if (review.ownerEmail !== ownerEmail) throw fail('artifact_review.forbidden', 'Review record is not owned by the authenticated caller.', 403);
  if (!['rejected', 'revision_requested'].includes(review.verdict)) throw fail('artifact_review.successor_not_required', 'Only rejected or revision-requested candidates accept a corrective successor.', 409);
  if (review.result && review.result.producer && review.result.producer.receiptId === successorReceiptId) throw fail('artifact_review.successor_unchanged', 'A rejected candidate cannot be linked to the same producer receipt.', 409);
  const lookup = helpers.resolveReceipt || resolveProducerReceipt;
  const successor = await lookup({admin, ownerEmail, producerReceiptId: successorReceiptId, producerKind});
  const selection = uniqueCandidates(successor.receipt, args.artifactNames);
  const inputHash = hashJson({contractVersion: CONTRACT_VERSION, reviewRequestId, producerKind: successor.producerKind, successorReceiptId, artifacts: selection.candidates.map((item) => ({name: item.name, sha256: item.sha256, byteLength: item.byteLength}))});
  const linkRef = admin.firestore().collection(REVIEW_LINK_COLLECTION).doc(requestId);
  const prior = await linkRef.get();
  if (prior.exists) {
    const existing = prior.data() || {};
    if (existing.ownerEmail !== ownerEmail || existing.inputHash !== inputHash) throw fail('artifact_review.successor_idempotency_conflict', 'requestId is already bound to a different successor.', 409);
    return {...existing.result, idempotent: true};
  }
  const result = {
    ok: true,
    contractVersion: CONTRACT_VERSION,
    operation: 'artifact.review.link_successor',
    requestId,
    reviewRequestId,
    prior: review.result.producer,
    successor: {
      state: 'producer_completed',
      producerKind: successor.producerKind,
      receiptId: successorReceiptId,
      artifactCount: selection.candidates.length,
      artifactDigests: selection.candidates.map((item) => ({role: item.role, name: item.name, sha256: item.sha256, byteLength: item.byteLength})),
      nextOperation: {operation: 'artifact.delivery.materialize_receipt', args: {producerReceiptId: successorReceiptId, producerKind: successor.producerKind}},
    },
    priorCandidatePreserved: true,
  };
  const record = {requestId, ownerEmail, inputHash, reviewRequestId, successorReceiptId, status: 'completed', result, createdAtMs: Date.now()};
  if (typeof linkRef.create === 'function') await linkRef.create(record); else await linkRef.set(record, {merge: false});
  await reviewRef.set({successor: result.successor, successorLinkedAtMs: record.createdAtMs}, {merge: true});
  return {...result, idempotent: false};
}

module.exports = {
  CONTRACT_VERSION,
  DELIVERY_COLLECTION,
  RECEIPT_SOURCES,
  deliveryDigestKey,
  digestStream,
  humanAcceptance,
  linkArtifactReviewSuccessorOperation,
  recordArtifactReviewOperation,
  materializeReceiptArtifactsOperation,
  normalizedCandidate,
  parseReceiptGsRef,
  publishToDrive,
  resolveProducerReceipt,
  uniqueCandidates,
  verifyGcsCandidate,
};
