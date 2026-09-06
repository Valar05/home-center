'use strict';

const {createHash} = require('node:crypto');
const {Readable} = require('node:stream');

const MAX_TEXT_BYTES = 8 * 1024 * 1024;
const MAX_PATCHES = 32;
const MAX_PROTECTED_REGIONS = 16;

function fail(message, status, code) {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  return error;
}

function text(value, max = 12000) {
  const clean = typeof value === 'string' ? value : '';
  return clean.length > max ? clean.slice(0, max) : clean;
}

function trimmed(value, max = 320) {
  return text(value, max).trim();
}

function safeRequestId(value) {
  const id = trimmed(value, 160);
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(id)) throw fail('requestId must be 6-160 safe characters.', 400, 'drive_text_patch_request_id_invalid');
  return id;
}

function safeFileId(value) {
  const id = trimmed(value, 220);
  if (!/^[A-Za-z0-9_.-]{8,220}$/.test(id)) throw fail('A valid Google Drive fileId is required.', 400, 'drive_text_patch_file_id_invalid');
  return id;
}

function sha256Hex(value) {
  return createHash('sha256').update(value).digest('hex');
}

function normalizeSha256(value, label = 'expectedSha256') {
  const digest = trimmed(value, 64).toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(digest)) throw fail(label + ' must be a 64-character hexadecimal SHA-256 digest.', 400, 'drive_text_patch_sha256_invalid');
  return digest;
}

function mediaBuffer(data) {
  if (Buffer.isBuffer(data)) return data;
  if (data instanceof ArrayBuffer) return Buffer.from(data);
  if (ArrayBuffer.isView(data)) return Buffer.from(data.buffer, data.byteOffset, data.byteLength);
  return Buffer.from(data || []);
}

function countExact(haystack, needle) {
  if (!needle) return 0;
  let count = 0;
  let offset = 0;
  while (true) {
    const index = haystack.indexOf(needle, offset);
    if (index < 0) return count;
    count += 1;
    offset = index + needle.length;
  }
}

function uniqueRegion(source, startMarker, endMarker, label = 'region') {
  if (!startMarker || !endMarker) throw fail(label + ' requires non-empty startMarker and endMarker.', 400, 'drive_text_patch_region_marker_required');
  const startCount = countExact(source, startMarker);
  const endCount = countExact(source, endMarker);
  if (startCount !== 1 || endCount !== 1) {
    throw fail(label + ' markers must each occur exactly once; saw start=' + startCount + ' end=' + endCount + '.', 409, 'drive_text_patch_region_not_unique');
  }
  const start = source.indexOf(startMarker);
  const bodyStart = start + startMarker.length;
  const endStart = source.indexOf(endMarker, bodyStart);
  if (endStart < bodyStart) throw fail(label + ' endMarker must follow startMarker.', 409, 'drive_text_patch_region_order_invalid');
  const end = endStart + endMarker.length;
  return {start, bodyStart, endStart, end, value: source.slice(start, end)};
}

function normalizePatch(raw, index) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw fail('replacement ' + (index + 1) + ' must be an object.', 400, 'drive_text_patch_replacement_invalid');
  const mode = trimmed(raw.mode || 'exact', 40).toLowerCase();
  const label = trimmed(raw.label || 'replacement-' + (index + 1), 160);
  if (!['exact', 'between'].includes(mode)) throw fail(label + ' mode must be exact or between.', 400, 'drive_text_patch_mode_invalid');
  if (mode === 'exact') {
    const find = text(raw.find, 500000);
    if (!find) throw fail(label + ' exact replacement requires find.', 400, 'drive_text_patch_find_required');
    const expectedCount = raw.expectedCount === undefined ? 1 : Number(raw.expectedCount);
    if (!Number.isSafeInteger(expectedCount) || expectedCount < 1 || expectedCount > 1000) throw fail(label + ' expectedCount must be an integer from 1 to 1000.', 400, 'drive_text_patch_expected_count_invalid');
    return {mode, label, find, replace: text(raw.replace, 1000000), expectedCount};
  }
  return {
    mode,
    label,
    startMarker: text(raw.startMarker, 20000),
    endMarker: text(raw.endMarker, 20000),
    replace: text(raw.replace, 1000000),
  };
}

function applyTextPatches(source, replacements) {
  if (!Array.isArray(replacements) || !replacements.length || replacements.length > MAX_PATCHES) {
    throw fail('replacements must contain between 1 and ' + MAX_PATCHES + ' entries.', 400, 'drive_text_patch_replacements_required');
  }
  let output = source;
  const receipts = [];
  replacements.map(normalizePatch).forEach((patch) => {
    if (patch.mode === 'exact') {
      const actualCount = countExact(output, patch.find);
      if (actualCount !== patch.expectedCount) {
        throw fail(patch.label + ' expected ' + patch.expectedCount + ' exact matches but found ' + actualCount + '.', 409, 'drive_text_patch_exact_count_mismatch');
      }
      output = output.split(patch.find).join(patch.replace);
      receipts.push({label: patch.label, mode: patch.mode, expectedCount: patch.expectedCount, actualCount});
      return;
    }
    const region = uniqueRegion(output, patch.startMarker, patch.endMarker, patch.label);
    output = output.slice(0, region.bodyStart) + patch.replace + output.slice(region.endStart);
    receipts.push({label: patch.label, mode: patch.mode, actualCount: 1});
  });
  return {text: output, receipts};
}

function protectedRegionDigests(source, regions) {
  if (regions === undefined || regions === null) return [];
  if (!Array.isArray(regions) || regions.length > MAX_PROTECTED_REGIONS) throw fail('protectedRegions must be an array of at most ' + MAX_PROTECTED_REGIONS + ' entries.', 400, 'drive_text_patch_protected_regions_invalid');
  return regions.map((raw, index) => {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw fail('protected region ' + (index + 1) + ' must be an object.', 400, 'drive_text_patch_protected_region_invalid');
    const label = trimmed(raw.label || 'protected-' + (index + 1), 160);
    const startMarker = text(raw.startMarker, 20000);
    const endMarker = text(raw.endMarker, 20000);
    const region = uniqueRegion(source, startMarker, endMarker, label);
    return {label, sha256: sha256Hex(Buffer.from(region.value, 'utf8')), byteCount: Buffer.byteLength(region.value, 'utf8')};
  });
}

function cleanMetadata(data = {}) {
  return {
    id: data.id || '',
    name: data.name || '',
    mimeType: data.mimeType || '',
    modifiedTime: data.modifiedTime || '',
    createdTime: data.createdTime || '',
    webViewLink: data.webViewLink || '',
    parents: Array.isArray(data.parents) ? data.parents : [],
    size: data.size || '',
    md5Checksum: data.md5Checksum || '',
  };
}

function sameSnapshot(left = {}, right = {}) {
  return left.id === right.id && left.mimeType === right.mimeType && String(left.size || '') === String(right.size || '') && left.md5Checksum === right.md5Checksum && left.modifiedTime === right.modifiedTime;
}

async function metadata(drive, fileId) {
  const response = await drive.files.get({fileId, fields: 'id,name,mimeType,modifiedTime,createdTime,webViewLink,parents,size,md5Checksum', supportsAllDrives: true});
  return cleanMetadata(response.data || {});
}

async function auditSuccess(admin, user, args, before, after, result) {
  const payload = {
    timestampMs: Date.now(),
    actor: trimmed(user && (user.email || user.uid), 320),
    authKind: trimmed(user && user.authKind, 80),
    tool: 'drive_operation',
    operation: 'drive_text_patch',
    requestId: result.requestId,
    fileId: result.fileId,
    affectedFileIds: [result.fileId],
    affectedStorageRefs: [],
    oldMetadata: before,
    newMetadata: after,
    oldParents: before.parents || [],
    newParents: after.parents || [],
    reversible: false,
    rollback: null,
    callerNote: trimmed(args.callerNote, 800),
    dryRun: false,
    status: 'success',
    providerSummary: trimmed(args.callerNote, 1000) || ('Patched and verified Drive text file ' + (after.name || result.fileId) + ' in place.'),
    result,
    updatedAtMs: Date.now(),
    inputSha256: result.oldSha256,
    error: '',
  };
  await admin.firestore().collection('driveBridgeAudit').doc(result.requestId).set(payload, {merge: false});
  await admin.firestore().collection('actionAudit').add({
    timestampMs: Date.now(),
    caller: payload.actor,
    operation: 'drive_text_patch',
    targetFileOrFolderId: result.fileId,
    summary: payload.providerSummary,
    requestId: result.requestId,
    authKind: payload.authKind,
    source: 'home_center_mcp',
  }).catch(() => {});
  return payload;
}

async function driveTextPatchOperation({google, admin, auth, user, args = {}}) {
  if (args.approved !== true) throw fail('drive_text_patch requires approved=true.', 409, 'drive_text_patch_approval_required');
  if (!google || !admin || !auth) throw fail('drive_text_patch requires Home Center Google and Firestore context.', 503, 'drive_text_patch_context_required');
  const requestId = safeRequestId(args.requestId);
  const fileId = safeFileId(args.fileId);
  const expectedSha256 = normalizeSha256(args.expectedSha256);
  const expectedMimeType = trimmed(args.expectedMimeType, 160);
  const drive = google.drive({version: 'v3', auth});

  const existing = await admin.firestore().collection('driveBridgeAudit').doc(requestId).get();
  if (existing.exists) {
    const audit = existing.data() || {};
    if (audit.status === 'success' && audit.result) {
      if (audit.result.fileId !== fileId || audit.result.oldSha256 !== expectedSha256) throw fail('requestId is already bound to different patch inputs.', 409, 'drive_text_patch_idempotency_conflict');
      return {...audit.result, idempotent: true, audit};
    }
  }

  const before = await metadata(drive, fileId);
  if (!before.id) throw fail('Drive file was not found.', 404, 'drive_text_patch_file_not_found');
  if (before.mimeType.startsWith('application/vnd.google-apps.')) throw fail('drive_text_patch only supports stored non-Google text files.', 415, 'drive_text_patch_google_native_unsupported');
  if (expectedMimeType && before.mimeType !== expectedMimeType) throw fail('Drive MIME type did not match expectedMimeType.', 409, 'drive_text_patch_mime_mismatch');
  if (!before.mimeType.startsWith('text/') && !['application/json', 'application/javascript', 'application/xml'].includes(before.mimeType)) {
    throw fail('drive_text_patch only supports text-like stored Drive files.', 415, 'drive_text_patch_mime_unsupported');
  }
  const declaredSize = Number(before.size || 0);
  if (!Number.isSafeInteger(declaredSize) || declaredSize < 1 || declaredSize > MAX_TEXT_BYTES) throw fail('Drive text file is empty, has unknown size, or exceeds the 8 MiB patch ceiling.', 413, 'drive_text_patch_size_invalid');

  const downloaded = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
  const oldBytes = mediaBuffer(downloaded.data);
  if (oldBytes.length !== declaredSize) throw fail('Drive download byte count did not match metadata.', 409, 'drive_text_patch_download_size_mismatch');
  const oldSha256 = sha256Hex(oldBytes);
  if (oldSha256 !== expectedSha256) throw fail('Drive file SHA-256 does not match expectedSha256; refusing stale patch.', 409, 'drive_text_patch_source_sha_mismatch');
  const oldText = oldBytes.toString('utf8');
  if (!Buffer.from(oldText, 'utf8').equals(oldBytes)) throw fail('Drive file is not lossless UTF-8 text.', 415, 'drive_text_patch_utf8_required');

  const afterDownload = await metadata(drive, fileId);
  if (!sameSnapshot(before, afterDownload)) throw fail('Drive source changed while opening the patch transaction.', 409, 'drive_text_patch_source_changed');

  const protectedBefore = protectedRegionDigests(oldText, args.protectedRegions);
  const patched = applyTextPatches(oldText, args.replacements);
  if (patched.text === oldText) throw fail('Patch produced no content change.', 409, 'drive_text_patch_no_change');
  const protectedAfterCandidate = protectedRegionDigests(patched.text, args.protectedRegions);
  for (let i = 0; i < protectedBefore.length; i += 1) {
    if (protectedBefore[i].sha256 !== protectedAfterCandidate[i].sha256 || protectedBefore[i].byteCount !== protectedAfterCandidate[i].byteCount) {
      throw fail('Protected region changed before upload: ' + protectedBefore[i].label + '.', 409, 'drive_text_patch_protected_region_changed');
    }
  }

  const newBytes = Buffer.from(patched.text, 'utf8');
  if (newBytes.length > MAX_TEXT_BYTES) throw fail('Patched file exceeds the 8 MiB patch ceiling.', 413, 'drive_text_patch_result_too_large');
  const newSha256 = sha256Hex(newBytes);

  const updated = await drive.files.update({
    fileId,
    media: {mimeType: before.mimeType, body: Readable.from([newBytes])},
    fields: 'id,name,mimeType,modifiedTime,createdTime,webViewLink,parents,size,md5Checksum',
    supportsAllDrives: true,
  });
  const after = cleanMetadata(updated.data || {});
  if (after.id !== fileId) throw fail('Drive update did not preserve file identity.', 502, 'drive_text_patch_file_identity_changed');

  const readbackResponse = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
  const readbackBytes = mediaBuffer(readbackResponse.data);
  const readbackSha256 = sha256Hex(readbackBytes);
  if (readbackBytes.length !== newBytes.length || readbackSha256 !== newSha256 || !readbackBytes.equals(newBytes)) {
    throw fail('Drive readback verification failed after in-place text patch.', 502, 'drive_text_patch_readback_mismatch');
  }
  const readbackText = readbackBytes.toString('utf8');
  const protectedReadback = protectedRegionDigests(readbackText, args.protectedRegions);
  for (let i = 0; i < protectedBefore.length; i += 1) {
    if (protectedBefore[i].sha256 !== protectedReadback[i].sha256 || protectedBefore[i].byteCount !== protectedReadback[i].byteCount) {
      throw fail('Protected region failed Drive readback: ' + protectedBefore[i].label + '.', 502, 'drive_text_patch_protected_readback_changed');
    }
  }

  const finalMetadata = await metadata(drive, fileId);
  const result = {
    operation: 'drive_text_patch',
    requestId,
    fileId,
    name: finalMetadata.name || before.name,
    mimeType: finalMetadata.mimeType || before.mimeType,
    webViewLink: finalMetadata.webViewLink || before.webViewLink,
    oldByteCount: oldBytes.length,
    newByteCount: newBytes.length,
    oldSha256,
    newSha256,
    readbackByteCount: readbackBytes.length,
    readbackSha256,
    replacementReceipts: patched.receipts,
    protectedRegions: protectedBefore.map((entry, index) => ({...entry, readbackSha256: protectedReadback[index].sha256, verified: entry.sha256 === protectedReadback[index].sha256})),
    sameFileId: finalMetadata.id === fileId,
    verified: finalMetadata.id === fileId && readbackSha256 === newSha256 && readbackBytes.length === newBytes.length,
  };
  const audit = await auditSuccess(admin, user, args, before, finalMetadata, result);
  return {...result, audit};
}

module.exports = {
  MAX_TEXT_BYTES,
  MAX_PATCHES,
  MAX_PROTECTED_REGIONS,
  applyTextPatches,
  protectedRegionDigests,
  driveTextPatchOperation,
};
