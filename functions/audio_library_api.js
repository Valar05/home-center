'use strict';

const {createVerify, createHash, randomBytes} = require('node:crypto');
const admin = require('firebase-admin');
const {Storage} = require('@google-cloud/storage');

const GENERATED_BUCKET = process.env.HOME_CENTER_GENERATED_BUCKET || 'home-center-generated';
const PLAYER_PUBLIC_KEY_DER = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAiZrb3ujS1+1SW7qG/sYbwo2vOYuZCnpRdl+uOJdVQuzpjp9TZLWjEQSUNPnYo7naQR7NskirOkApErZa89usWTKR2hutLzXxB7+286cF5bPJZn53p4YvfBZqae3i7iZNjMYenB9RD6jM0QMydzcdGfNQi2pTwmG5++QgXunzgbaUFdP7bwohhGbS+piYWbz5XFWDkT8DOBcr4YsSNrCl5n8Yhifa2YzdHQpMFjfzev9m9veNikmJZFcyRo2zAD8rPRxj9s9KFSz0AzZDCu8nFN+vTN9aK16xkLdxvhw1ipA3aLjpwoNR7m11HvT1cs0z0EfEuaPUZoyBS3x5qFslJwIDAQAB';
const PLAYER_PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----\n${PLAYER_PUBLIC_KEY_DER.match(/.{1,64}/g).join('\n')}\n-----END PUBLIC KEY-----`;
const LEGACY_STEWARD = 'dclarke1005@gmail.com';
const PUBLIC_BASE = process.env.HOME_CENTER_AUDIO_LIBRARY_PUBLIC_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/audioLibraryApi';
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
  const token = randomBytes(32).toString('base64url');
  const tokenHash = createHash('sha256').update(token).digest('hex');
  const expiresAtMs = Date.now() + 15 * 60 * 1000;
  await admin.firestore().collection('audioLibraryStreamTokens').doc(tokenHash).set({
    objectName: file.name,
    email,
    expiresAtMs,
    createdAtMs: Date.now(),
  });
  return {ok: true, url: PUBLIC_BASE + '?token=' + encodeURIComponent(token), expiresAtMs, object: audioMetadata(file, metadata, email)};
}

async function streamAudio(req, res) {
  const token = safeText(req.query && req.query.token, 300);
  if (!token) {
    res.status(401).json({ok: false, error: 'stream_token_required'});
    return;
  }
  const tokenHash = createHash('sha256').update(token).digest('hex');
  const ref = admin.firestore().collection('audioLibraryStreamTokens').doc(tokenHash);
  const snap = await ref.get();
  const grant = snap.exists ? snap.data() || {} : {};
  if (!snap.exists || Number(grant.expiresAtMs || 0) <= Date.now()) {
    res.status(401).json({ok: false, error: 'stream_token_expired'});
    return;
  }
  const bucket = storage.bucket(GENERATED_BUCKET);
  const {file, metadata} = await authorizedFile(bucket, grant.objectName, safeEmail(grant.email));
  const size = Number(metadata.size || 0);
  const range = safeText(req.get('range'), 120);
  let start = 0;
  let end = Math.max(0, size - 1);
  let status = 200;
  if (range) {
    const match = range.match(/^bytes=(\d*)-(\d*)$/);
    if (!match) {
      res.status(416).set('Content-Range', 'bytes */' + size).end();
      return;
    }
    if (match[1]) start = Number(match[1]);
    if (match[2]) end = Math.min(end, Number(match[2]));
    if (!match[1] && match[2]) start = Math.max(0, size - Number(match[2]));
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end < start || start >= size) {
      res.status(416).set('Content-Range', 'bytes */' + size).end();
      return;
    }
    status = 206;
  }
  res.status(status);
  res.set('Content-Type', metadata.contentType || 'application/octet-stream');
  res.set('Accept-Ranges', 'bytes');
  res.set('Content-Length', String(end - start + 1));
  res.set('Cache-Control', 'private, no-store');
  if (status === 206) res.set('Content-Range', 'bytes ' + start + '-' + end + '/' + size);
  file.createReadStream({start, end}).on('error', (err) => {
    console.error(JSON.stringify({event: 'audio_library_stream_failed', error: safeText(err && err.message, 300)}));
    if (!res.headersSent) res.status(502).end();
    else res.destroy(err);
  }).pipe(res);
}

async function audioLibraryHandler(req, res) {
  res.set('Cache-Control', 'private, no-store');
  try {
    if (req.method === 'GET') {
      await streamAudio(req, res);
      return;
    }
    if (req.method !== 'POST') {
      res.status(405).json({ok: false, error: 'method_not_allowed'});
      return;
    }
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
