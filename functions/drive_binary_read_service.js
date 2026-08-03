'use strict';

const {createHash} = require('node:crypto');

const SESSION_COLLECTION = 'driveBinaryReadSessions';
const DEFAULT_CHUNK_SIZE = 131072;
const MAX_CHUNK_SIZE = 262144;
const DEFAULT_MAX_BYTES = 256 * 1024 * 1024;

function fail(message, status, code) {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  return error;
}

function text(value, max = 320) {
  return String(value || '').trim().slice(0, max);
}

function requestId(value) {
  const id = text(value, 160);
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(id)) throw fail('requestId must be 6-160 safe characters.', 400, 'drive_binary_read_request_id_invalid');
  return id;
}

function fileId(value) {
  const id = text(value, 220);
  if (!/^[A-Za-z0-9_.-]{8,220}$/.test(id)) throw fail('A valid Google Drive fileId is required.', 400, 'drive_binary_read_file_id_invalid');
  return id;
}

function sessionOwner(user = {}) {
  const owner = text(user.email || user.uid, 320).toLowerCase();
  if (!owner) throw fail('An authenticated owner is required.', 401, 'drive_binary_read_owner_required');
  return owner;
}

function normalizeChunkSize(value) {
  const size = value === undefined ? DEFAULT_CHUNK_SIZE : Number(value);
  if (!Number.isSafeInteger(size) || size < 1 || size > MAX_CHUNK_SIZE) {
    throw fail('chunkSize must be an integer between 1 and 262144 bytes.', 400, 'drive_binary_read_chunk_size_invalid');
  }
  return size;
}

function normalizeMetadata(data = {}, maxBytes = DEFAULT_MAX_BYTES) {
  const mimeType = text(data.mimeType, 160) || 'application/octet-stream';
  if (mimeType.startsWith('application/vnd.google-apps.')) {
    throw fail('Binary read sessions only support stored Drive files; export Google-native files with drive_read.', 415, 'drive_binary_read_google_native_unsupported');
  }
  const byteCount = Number(data.size || 0);
  if (!Number.isSafeInteger(byteCount) || byteCount < 1) {
    throw fail('Drive binary files must be non-empty and report a safe byte count.', 415, 'drive_binary_read_empty_or_unknown_size');
  }
  if (byteCount > maxBytes) throw fail('Drive binary file exceeds the configured 256 MiB read ceiling.', 413, 'drive_binary_read_too_large');
  return {
    fileId: fileId(data.id),
    name: text(data.name, 500),
    mimeType,
    byteCount,
    md5Checksum: text(data.md5Checksum, 64).toLowerCase(),
    modifiedTime: text(data.modifiedTime, 80),
    webViewLink: text(data.webViewLink, 1200),
    parents: Array.isArray(data.parents) ? data.parents.map((item) => text(item, 220)).filter(Boolean) : [],
  };
}

function sameSnapshot(left = {}, right = {}) {
  return left.fileId === right.fileId &&
    left.name === right.name &&
    left.mimeType === right.mimeType &&
    left.byteCount === right.byteCount &&
    left.md5Checksum === right.md5Checksum &&
    left.modifiedTime === right.modifiedTime;
}

async function driveMetadata(drive, id, maxBytes) {
  const response = await drive.files.get({
    fileId: id,
    fields: 'id,name,mimeType,size,md5Checksum,modifiedTime,webViewLink,parents',
    supportsAllDrives: true,
  });
  return normalizeMetadata(response.data || {}, maxBytes);
}

async function hashDriveFile(drive, id) {
  const response = await drive.files.get({fileId: id, alt: 'media', supportsAllDrives: true}, {responseType: 'stream'});
  if (!response.data || typeof response.data[Symbol.asyncIterator] !== 'function') {
    throw fail('Drive did not return a readable binary stream.', 502, 'drive_binary_read_stream_unavailable');
  }
  const hash = createHash('sha256');
  let byteCount = 0;
  for await (const chunk of response.data) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    byteCount += bytes.length;
    hash.update(bytes);
  }
  return {byteCount, sha256: hash.digest('hex')};
}

function sessionRef(admin, id) {
  if (!admin || typeof admin.firestore !== 'function') throw fail('Drive binary sessions require Firestore.', 503, 'drive_binary_read_store_required');
  return admin.firestore().collection(SESSION_COLLECTION).doc(id);
}

function publicSession(data = {}, extra = {}) {
  return {
    requestId: data.requestId,
    state: data.state,
    source: data.source,
    fileSha256: data.fileSha256,
    chunkSize: data.chunkSize,
    chunkCount: data.chunkCount,
    createdAt: data.createdAt,
    ...extra,
  };
}

async function loadOwnedSession({admin, user, args = {}}) {
  const id = requestId(args.requestId);
  const ref = sessionRef(admin, id);
  const snap = await ref.get();
  if (!snap.exists) throw fail('Drive binary read session was not found.', 404, 'drive_binary_read_session_not_found');
  const data = snap.data() || {};
  if (data.owner !== sessionOwner(user)) throw fail('Drive binary read session belongs to another owner.', 403, 'drive_binary_read_session_forbidden');
  return {id, ref, data};
}

async function assertSourceUnchanged(drive, data, maxBytes) {
  const current = await driveMetadata(drive, data.source.fileId, maxBytes);
  if (!sameSnapshot(current, data.source)) throw fail('Drive binary source changed after the read session began.', 409, 'drive_binary_read_source_changed');
  return current;
}

async function beginDriveBinaryReadOperation({google, admin, auth, user, args = {}, maxBytes = DEFAULT_MAX_BYTES}) {
  const id = requestId(args.requestId);
  const owner = sessionOwner(user);
  const sourceFileId = fileId(args.fileId);
  const chunkSize = normalizeChunkSize(args.chunkSize);
  const drive = google.drive({version: 'v3', auth});
  const ref = sessionRef(admin, id);
  const existing = await ref.get();
  if (existing.exists) {
    const data = existing.data() || {};
    if (data.owner !== owner) throw fail('requestId is already owned by another binary read session.', 403, 'drive_binary_read_session_forbidden');
    if (!data.source || data.source.fileId !== sourceFileId || data.chunkSize !== chunkSize) {
      throw fail('requestId is already bound to different binary read inputs.', 409, 'drive_binary_read_idempotency_conflict');
    }
    await assertSourceUnchanged(drive, data, maxBytes);
    return publicSession(data, {resumed: true, verifiedSource: true});
  }

  const before = await driveMetadata(drive, sourceFileId, maxBytes);
  const digest = await hashDriveFile(drive, sourceFileId);
  if (digest.byteCount !== before.byteCount) throw fail('Drive binary stream byte count did not match metadata.', 502, 'drive_binary_read_size_mismatch');
  const after = await driveMetadata(drive, sourceFileId, maxBytes);
  if (!sameSnapshot(before, after)) throw fail('Drive binary source changed while the read session was opening.', 409, 'drive_binary_read_source_changed');
  const data = {
    requestId: id,
    owner,
    state: 'ready',
    source: before,
    fileSha256: digest.sha256,
    chunkSize,
    chunkCount: Math.ceil(before.byteCount / chunkSize),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  await ref.set(data, {merge: false});
  return publicSession(data, {resumed: false, verifiedSource: true});
}

async function readDriveBinarySessionChunkOperation({google, admin, auth, user, args = {}, maxBytes = DEFAULT_MAX_BYTES}) {
  const {ref, data} = await loadOwnedSession({admin, user, args});
  const index = Number(args.chunkIndex);
  if (!Number.isSafeInteger(index) || index < 0 || index >= data.chunkCount) {
    throw fail('chunkIndex is outside this binary read session.', 400, 'drive_binary_read_chunk_index_invalid');
  }
  const drive = google.drive({version: 'v3', auth});
  await assertSourceUnchanged(drive, data, maxBytes);
  const offset = index * data.chunkSize;
  const end = Math.min(data.source.byteCount - 1, offset + data.chunkSize - 1);
  const downloaded = await drive.files.get(
    {fileId: data.source.fileId, alt: 'media', supportsAllDrives: true},
    {responseType: 'arraybuffer', headers: {Range: 'bytes=' + offset + '-' + end}},
  );
  const bytes = Buffer.isBuffer(downloaded.data) ? downloaded.data : Buffer.from(downloaded.data || []);
  const expected = end - offset + 1;
  if (bytes.length !== expected) throw fail('Drive binary range read returned an unexpected byte count.', 502, 'drive_binary_read_chunk_size_mismatch');
  const receipt = {chunkIndex: index, offset, byteCount: bytes.length, chunkSha256: createHash('sha256').update(bytes).digest('hex'), servedAt: new Date().toISOString()};
  const chunkRef = ref.collection('chunks').doc(String(index).padStart(6, '0'));
  const previous = await chunkRef.get();
  if (previous.exists) {
    const old = previous.data() || {};
    if (old.byteCount !== receipt.byteCount || old.chunkSha256 !== receipt.chunkSha256) {
      throw fail('A retried Drive binary chunk no longer matches its prior receipt.', 409, 'drive_binary_read_chunk_changed');
    }
  } else {
    await chunkRef.set(receipt, {merge: false});
    await ref.set({updatedAt: receipt.servedAt}, {merge: true});
  }
  return {
    requestId: data.requestId,
    ...receipt,
    totalSize: data.source.byteCount,
    chunkCount: data.chunkCount,
    nextChunkIndex: index + 1 < data.chunkCount ? index + 1 : null,
    eof: index + 1 >= data.chunkCount,
    chunkBase64: bytes.toString('base64'),
  };
}

async function binaryReadProgress(ref, data) {
  const snapshot = await ref.collection('chunks').get();
  const servedChunks = snapshot.docs.map((doc) => Number((doc.data() || {}).chunkIndex)).filter(Number.isSafeInteger).sort((a, b) => a - b);
  const servedSet = new Set(servedChunks);
  const missingChunks = [];
  for (let index = 0; index < data.chunkCount; index += 1) if (!servedSet.has(index)) missingChunks.push(index);
  return {servedChunks, missingChunks, servedCount: servedChunks.length, remainingCount: missingChunks.length};
}

async function driveBinaryReadStatusOperation({google, admin, auth, user, args = {}, maxBytes = DEFAULT_MAX_BYTES}) {
  const {ref, data} = await loadOwnedSession({admin, user, args});
  const drive = google.drive({version: 'v3', auth});
  await assertSourceUnchanged(drive, data, maxBytes);
  return publicSession(data, {...await binaryReadProgress(ref, data), verifiedSource: true});
}

async function completeDriveBinaryReadOperation({google, admin, auth, user, args = {}, maxBytes = DEFAULT_MAX_BYTES}) {
  const {ref, data} = await loadOwnedSession({admin, user, args});
  const reconstructedByteCount = Number(args.reconstructedByteCount);
  const reconstructedSha256 = text(args.reconstructedSha256, 64).toLowerCase();
  if (!Number.isSafeInteger(reconstructedByteCount) || !/^[a-f0-9]{64}$/.test(reconstructedSha256)) {
    throw fail('Completion requires reconstructedByteCount and reconstructedSha256.', 400, 'drive_binary_read_completion_identity_required');
  }
  const progress = await binaryReadProgress(ref, data);
  if (progress.missingChunks.length) throw fail('Binary read session still has unserved chunks.', 409, 'drive_binary_read_incomplete');
  if (reconstructedByteCount !== data.source.byteCount || reconstructedSha256 !== data.fileSha256) {
    throw fail('Reconstructed binary identity does not match the source receipt.', 409, 'drive_binary_read_reconstruction_mismatch');
  }
  const drive = google.drive({version: 'v3', auth});
  await assertSourceUnchanged(drive, data, maxBytes);
  const finalDigest = await hashDriveFile(drive, data.source.fileId);
  if (finalDigest.byteCount !== data.source.byteCount || finalDigest.sha256 !== data.fileSha256) {
    throw fail('Drive binary source failed final whole-file verification.', 409, 'drive_binary_read_source_changed');
  }
  const completedAt = new Date().toISOString();
  await ref.set({state: 'completed', completedAt, updatedAt: completedAt, reconstructedByteCount, reconstructedSha256}, {merge: true});
  return publicSession({...data, state: 'completed'}, {...progress, reconstructedByteCount, reconstructedSha256, readbackByteCount: finalDigest.byteCount, readbackSha256: finalDigest.sha256, completedAt, verified: true});
}

module.exports = {
  SESSION_COLLECTION,
  DEFAULT_CHUNK_SIZE,
  MAX_CHUNK_SIZE,
  DEFAULT_MAX_BYTES,
  beginDriveBinaryReadOperation,
  readDriveBinarySessionChunkOperation,
  driveBinaryReadStatusOperation,
  completeDriveBinaryReadOperation,
};
