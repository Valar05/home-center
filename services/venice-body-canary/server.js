'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const {LOCKED_PORTRAIT_SHA256, VeniceBodyState} = require('./core');

const PUBLIC_ROOT = path.join(__dirname, 'public');
const STATIC_FILES = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
]);

function sha256File(filePath) {
  if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return '';
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function asset(filePath, expectedSha256) {
  const actualSha256 = sha256File(filePath);
  return {
    filePath: actualSha256 && actualSha256 === expectedSha256 ? path.resolve(filePath) : '',
    expectedSha256,
    actualSha256,
    ready: Boolean(actualSha256 && actualSha256 === expectedSha256),
  };
}

function sameSecret(received, expected) {
  const left = Buffer.from(String(received || ''));
  const right = Buffer.from(String(expected || ''));
  return left.length === right.length && left.length > 0 && crypto.timingSafeEqual(left, right);
}

function json(res, statusCode, value) {
  const bytes = Buffer.from(JSON.stringify(value));
  res.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': bytes.length,
    'cache-control': 'no-store',
  });
  res.end(bytes);
}

function readJson(req, limit = 16384) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > limit) {
        reject(new Error('request too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); }
      catch { reject(new Error('invalid JSON')); }
    });
    req.on('error', reject);
  });
}

function createCanary(options = {}) {
  const portrait = asset(options.portraitPath || '', LOCKED_PORTRAIT_SHA256);
  const voiceExpectedSha256 = String(options.voiceSha256 || '').toLowerCase();
  const voice = asset(options.voicePath || '', voiceExpectedSha256);
  const token = String(options.controlToken || '');
  const state = new VeniceBodyState({portraitReady: portrait.ready, voiceReady: voice.ready});
  const clients = new Set();

  function publicSnapshot() {
    return {
      ...state.snapshot(),
      provenance: {
        portrait: {ready: portrait.ready, expectedSha256: portrait.expectedSha256, actualSha256: portrait.actualSha256},
        voice: {ready: voice.ready, expectedSha256: voice.expectedSha256, actualSha256: voice.actualSha256},
      },
    };
  }

  function broadcast() {
    const payload = `data: ${JSON.stringify(publicSnapshot())}\n\n`;
    for (const client of clients) client.write(payload);
  }

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    if (req.method === 'GET' && STATIC_FILES.has(url.pathname)) {
      const [name, contentType] = STATIC_FILES.get(url.pathname);
      const bytes = fs.readFileSync(path.join(PUBLIC_ROOT, name));
      res.writeHead(200, {'content-type': contentType, 'content-length': bytes.length, 'cache-control': 'no-store'});
      res.end(bytes);
      return;
    }
    if (req.method === 'GET' && url.pathname === '/status') {
      json(res, 200, publicSnapshot());
      return;
    }
    if (req.method === 'GET' && url.pathname === '/events') {
      res.writeHead(200, {
        'content-type': 'text/event-stream',
        'cache-control': 'no-store',
        connection: 'keep-alive',
      });
      clients.add(res);
      res.write(`data: ${JSON.stringify(publicSnapshot())}\n\n`);
      req.on('close', () => clients.delete(res));
      return;
    }
    if (req.method === 'GET' && url.pathname === '/portrait' && portrait.ready) {
      const bytes = fs.readFileSync(portrait.filePath);
      res.writeHead(200, {'content-type': 'image/jpeg', 'content-length': bytes.length, 'cache-control': 'no-store'});
      res.end(bytes);
      return;
    }
    if (req.method === 'GET' && url.pathname === '/voice' && voice.ready) {
      const bytes = fs.readFileSync(voice.filePath);
      res.writeHead(200, {'content-type': 'audio/wav', 'content-length': bytes.length, 'cache-control': 'no-store'});
      res.end(bytes);
      return;
    }
    if (req.method === 'POST' && url.pathname === '/cut') {
      const snapshot = state.apply({type: 'cut'});
      broadcast();
      json(res, 200, snapshot);
      return;
    }
    if (req.method === 'POST' && url.pathname === '/ended') {
      try {
        const body = await readJson(req);
        const snapshot = state.apply({type: 'ended', epoch: Number(body.epoch)});
        broadcast();
        json(res, 200, snapshot);
      } catch (error) {
        json(res, 409, {ok: false, error: error.message});
      }
      return;
    }
    if (req.method === 'POST' && url.pathname === '/control') {
      if (!sameSecret(req.headers['x-venice-control-token'], token)) {
        json(res, 403, {ok: false, error: 'control authorization failed'});
        return;
      }
      try {
        const snapshot = state.apply(await readJson(req));
        broadcast();
        json(res, 200, snapshot);
      } catch (error) {
        json(res, 409, {ok: false, error: error.message});
      }
      return;
    }
    json(res, 404, {ok: false, error: 'not found'});
  });

  return {server, state, publicSnapshot};
}

if (require.main === module) {
  const host = process.env.VENICE_BODY_HOST || '127.0.0.1';
  if (!['127.0.0.1', '::1', 'localhost'].includes(host)) throw new Error('Venice body canary is loopback-only');
  const port = Number(process.env.VENICE_BODY_PORT || 4317);
  const canary = createCanary({
    portraitPath: process.env.VENICE_PORTRAIT_PATH,
    voicePath: process.env.VENICE_VOICE_PATH,
    voiceSha256: process.env.VENICE_VOICE_SHA256,
    controlToken: process.env.VENICE_BODY_CONTROL_TOKEN,
  });
  canary.server.listen(port, host, () => {
    process.stdout.write(JSON.stringify({ok: true, service: 'venice-body-canary', host, port, ...canary.publicSnapshot().provenance}) + '\n');
  });
}

module.exports = {asset, createCanary, sha256File};
