'use strict';

const {createVerify, createHash} = require('node:crypto');
const {Storage} = require('@google-cloud/storage');

const GENERATED_BUCKET = process.env.HOME_CENTER_GENERATED_BUCKET || 'home-center-generated';
const PLAYER_PUBLIC_KEY_DER = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAiZrb3ujS1+1SW7qG/sYbwo2vOYuZCnpRdl+uOJdVQuzpjp9TZLWjEQSUNPnYo7naQR7NskirOkApErZa89usWTKR2hutLzXxB7+286cF5bPJZn53p4YvfBZqae3i7iZNjMYenB9RD6jM0QMydzcdGfNQi2pTwmG5++QgXunzgbaUFdP7bwohhGbS+piYWbz5XFWDkT8DOBcr4YsSNrCl5n8Yhifa2YzdHQpMFjfzev9m9veNikmJZFcyRo2zAD8rPRxj9s9KFSz0AzZDCu8nFN+vTN9aK16xkLdxvhw1ipA3aLjpwoNR7m11HvT1cs0z0EfEuaPUZoyBS3x5qFslJwIDAQAB';
const PLAYER_PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----\n${PLAYER_PUBLIC_KEY_DER.match(/.{1,64}/g).join('\n')}\n-----END PUBLIC KEY-----`;
const LEGACY_STEWARD = 'dclarke1005@gmail.com';
const MAX_CLOCK_SKEW_MS = 5 * 60 * 1000;
const AUDIO_EXTENSIONS = /\.(wav|mp3|ogg|flac|m4a|aac|opus)$/i;
const AUDIO_TYPES = /^audio\//i;
const storage = new Storage();

function safeText(value, max = 1200) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeEmail(value) {
  const email = safeText(value, 320).toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : '';
}

function base64Url(value) {
  return Buffer.from(String(value || ''), 'utf8').toString('base64url');
}

function parseSharedWith(value) {
  if (Array.isArray(value)) return value.map(safeEmail).filter(Boolean);
  const text = safeText(value, 4000);
  if (!text) return [];
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed.map(safeEmail).filter(Boolean);
  } catch (_) {}
  return text.split(/[;,\s]+/).map(safeEmail).filter(Boolean);
}

function customMetadata(metadata = {}) {
  return metadata && typeof metadata.metadata === 'object' && metadata.metadata ? metadata.metadata : {};
}

function ownerFor(metadata = {}) {
  const custom = customMetadata(metadata);
  return safeEmail(custom.ownerEmail || custom.owner || custom.createdBy);
}

function sharedWithFor(metadata = {}) {
  const custom = customMetadata(metadata);
  return parseSharedWith(custom.sharedWith || custom.sharedWithEmails);
}

function accessFor(metadata, email) {
  const ownerEmail = ownerFor(metadata);
  if (ownerEmail && ownerEmail === email) return 'owned';
  if (sharedWithFor(metadata).includes(email)) return 'shared';
  if (!ownerEmail && email === LEGACY_STEWARD) return 'legacy';
  return '';
}

function verifyRequest(req) {
  const timestamp = safeText(req.get('x-audio-library-timestamp'), 40);
  const signature = safeText(req.get('x-audio-library-signature'), 8192);
  const keyId = safeText(req.get('x-audio-library-key-id'), 120);
  const timestampMs = Number(timestamp);
  if (keyId !== 'shell-shock-player-v1' || !Number.isFinite(timestampMs) || Math.abs(Date.now() - timestampMs) > MAX_CLOCK_SKEW_MS || !signature) {
    const err = new Error('Audio library request authentication failed.');
    err.status = 401;
    throw err;
  }
  const rawBody = Buffer.isBuffer(req.rawBody) ? req.rawBody : Buffer.from(JSON.stringify(req.body || {}), 'utf8');
  const verifier = createVerify('RSA-SHA256');
  verifier.update(timestamp + '\n');
  verifier.update(rawBody);
  verifier.end();
  if (!verifier.verify(PLAYER_PUBLIC_KEY, signature, 'base64')) {
    const err = new Error('Audio library request signature was invalid.');
    err.status = 401;
    throw err;
  }
  return req.body && typeof req.body === 'object' ? req.body : {};
}

function audioMetadata(file, metadata, email) {
  const custom = customMetadata(metadata);
  const ownerEmail = ownerFor(metadata);
  const parts = file.name.split('/');
  return {
    id: base64Url(file.name),
    name: file.name,
    displayName: parts.pop() || file.name,
    path: parts.join('/'),
    contentType: safeText(metadata.contentType, 160) || 'application/octet-stream',
    size: Number(metadata.size || 0),
    updated: safeText(metadata.updated || metadata.timeCreated, 80),
    ownerEmail: ownerEmail || (email === LEGACY_STEWARD ? LEGACY_STEWARD : ''),
    access: accessFor(metadata, email),
    duration: Number(custom.duration || custom.durationSeconds || 0) || null,
    sampleRate: Number(custom.sampleRate || 0) || null,
    requestId: safeText(custom.requestId, 180),
    project: safeText(custom.project, 180),
    stage: safeText(custom.stage, 120),
    manifestObject: safeText(custom.manifestObject, 1000),
    sha256: safeText(custom.sha256, 128),
  };
}

async function authorizedFile(bucket, objectName, email) {
  const name = safeText(objectName, 1024);
  if (!name || name.includes('\0')) {
    const err = new Error('A valid bucket object name is required.');
    err.status = 400;
    throw err;
  }
  const file = bucket.file(name);
  const [metadata] = await file.getMetadata();
  if (!AUDIO_TYPES.test(metadata.contentType || '') && !AUDIO_EXTENSIONS.test(name)) {
    const err = new Error('The requested object is not audio.');
    err.status = 415;
    throw err;
  }
  if (!accessFor(metadata, email)) {
    const err = new Error('You do not have access to this audio object.');
    err.status = 403;
    throw err;
  }
  return {file, metadata};
}

async function listAudio(bucket, body, email) {
  const pageToken = safeText(body.pageToken, 1000) || undefined;
  const prefix = safeText(body.prefix, 600) || undefined;
  const [files, nextQuery] = await bucket.getFiles({autoPaginate: false, maxResults: 500, pageToken, prefix});
  const items = [];
  for (const file of files) {
    const [metadata] = await file.getMetadata();
    if (!AUDIO_TYPES.test(metadata.contentType || '') && !AUDIO_EXTENSIONS.test(file.name)) continue;
    if (!accessFor(metadata, email)) continue;
    items.push(audioMetadata(file, metadata, email));
  }
  items.sort((a, b) => String(b.updated).localeCompare(String(a.updated)));
  return {ok: true, bucket: GENERATED_BUCKET, items, nextPageToken: nextQuery && nextQuery.pageToken || null};
}

async function playAudio(bucket, body, email) {
  const {file, metadata} = await authorizedFile(bucket, body.objectName, email);
  const [url] = await file.getSignedUrl({version: 'v4', action: 'read', expires: Date.now() + 15 * 60 * 1000, responseType: metadata.contentType || 'application/octet-stream'});
  return {ok: true, url, expiresAtMs: Date.now() + 15 * 60 * 1000, object: audioMetadata(file, metadata, email)};
}

async function audioLibraryHandler(req, res) {
  res.set('Cache-Control', 'private, no-store');
  if (req.method !== 'POST') {
    res.status(405).json({ok: false, error: 'method_not_allowed'});
    return;
  }
  try {
    const body = verifyRequest(req);
    const email = safeEmail(body.email);
    if (!email) {
      res.status(400).json({ok: false, error: 'email_required'});
      return;
    }
    const bucket = storage.bucket(GENERATED_BUCKET);
    const action = safeText(body.action, 40);
    const result = action === 'list'
      ? await listAudio(bucket, body, email)
      : action === 'play'
        ? await playAudio(bucket, body, email)
        : null;
    if (!result) {
      res.status(400).json({ok: false, error: 'unsupported_action'});
      return;
    }
    res.status(200).json(result);
  } catch (err) {
    const status = Number(err && (err.status || err.code)) || 500;
    const safeStatus = status >= 400 && status < 600 ? status : 500;
    console.error(JSON.stringify({event: 'audio_library_failed', status: safeStatus, error: safeText(err && err.message, 300), requestHash: createHash('sha256').update(String(req.rawBody || '')).digest('hex').slice(0, 12)}));
    res.status(safeStatus).json({ok: false, error: 'audio_library_failed', detail: safeText(err && err.message, 300)});
  }
}

module.exports = {audioLibraryHandler, verifyRequest, accessFor, parseSharedWith, audioMetadata};
