const {createHash, randomBytes, randomUUID, createSign, createVerify} = require('node:crypto');
const {Readable, Transform} = require('node:stream');
const {pipeline} = require('node:stream/promises');
const {Storage} = require('@google-cloud/storage');
const fs = require('node:fs');
const path = require('node:path');
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {SSEServerTransport} = require('@modelcontextprotocol/sdk/server/sse.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');
const {ListToolsRequestSchema} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/types.js');
const {normalizeObjectSchema} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/server/zod-compat.js');
const {toJsonSchemaCompat} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/server/zod-json-schema-compat.js');
const express = require('express');
const {z} = require('zod/v4');
const {CARTESIA_DEFAULT_MODEL_ID, CARTESIA_DEFAULT_VOICE_NAME, listCartesiaVoiceCatalog, listCartesiaVoices, normalizeCartesiaVoice, openCartesiaStream} = require('./hosted_speech_provider');
const {renderBlenderGlb: commandCenterRenderBlenderGlb} = require('./command_center_mcp');
const cartesiaPitchShift = require('./cartesia_pitch_shift');
const {renderAudioOperation, inspectAudioArtifactsOperation, uploadVerified: uploadVerifiedArtifact} = require('./audio_render_service');
const {GENERATED_ARTIFACT_BUCKET, uploadGeneratedArtifact, publishGeneratedArtifactToDrive} = require('./artifact_bucket');

const DEFAULT_MCP_PUBLIC_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
const MCP_PUBLIC_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || DEFAULT_MCP_PUBLIC_BASE;
const HOME_CENTER_MCP_SERVER_VERSION = '0.1.1';
const HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-07-25.blender-direct-file-catalog-v2';
const HOME_CENTER_REGISTRY_VERSION = HOME_CENTER_CONNECTOR_SCHEMA_REVISION;
const HOME_CENTER_DIRECT_FILE_TOOLS = Object.freeze(['render_blender_glb']);
const MCP_RESOURCE = `${MCP_PUBLIC_BASE}/mcp`;
const MCP_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/.well-known/oauth-protected-resource`;
const MCP_LEGACY_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/oauth-protected-resource`;
const MCP_COMPAT_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/oauth-protected-resource-v2`;
const MCP_AUTHORIZATION_SERVER_METADATA = `${MCP_PUBLIC_BASE}/.well-known/oauth-authorization-server`;
const MCP_GOOGLE_CALLBACK = process.env.HOME_CENTER_MCP_GOOGLE_CALLBACK || `${MCP_PUBLIC_BASE}/oauth/google-callback`;
const COMMAND_CENTER_MCP_URL = process.env.COMMAND_CENTER_MCP_URL || 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const COMMAND_CENTER_RENDER_BUCKET = process.env.COMMAND_CENTER_RENDER_BUCKET || process.env.HOME_CENTER_GENERATED_BUCKET || process.env.COMMAND_CENTER_GENERATED_BUCKET || process.env.RENDER_CACHE_BUCKET || process.env.COMMAND_CENTER_BUCKET || 'home-center-generated';
const HOME_CENTER_RENDER_MAX_GLB_BYTES = Number(process.env.COMMAND_CENTER_RENDER_MAX_GLB_BYTES || 250 * 1024 * 1024);
const HOME_CENTER_RENDER_MAX_SCRIPT_BYTES = Number(process.env.COMMAND_CENTER_RENDER_MAX_SCRIPT_BYTES || 1024 * 1024);
const HOME_CENTER_DIRECT_RENDER_TEXT_LIMIT = 1024 * 1024;
const HOME_CENTER_RENDER_INLINE_GIF_MAX_BYTES = Number(process.env.HOME_CENTER_RENDER_INLINE_GIF_MAX_BYTES || 2 * 1024 * 1024);
const MCP_REQUIRED_SCOPES = [
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/spreadsheets',
];
const MCP_OAUTH_SECURITY_SCHEMES = [{type: 'oauth2', scopes: MCP_REQUIRED_SCOPES}];
const CREDIT_GATED_EMAILS = Object.freeze([
  'dclarke1005@gmail.com',
  'junewren28@gmail.com',
  'timothypomeroy07@gmail.com',
]);
const CREDIT_GATED_EMAIL_SET = new Set(CREDIT_GATED_EMAILS);

function requireCreditGatedEmail(email, surface = 'credit-backed operation') {
  const clean = safeText(email, 320).toLowerCase();
  if (CREDIT_GATED_EMAIL_SET.has(clean)) return clean;
  const err = new Error(surface + ' is restricted to approved Home Center accounts.');
  err.status = 403;
  err.failureKind = 'credit_gated_forbidden_email';
  throw err;
}

async function requireCreditGatedContext({google, admin, googleClientId, googleClientSecret, extra, user = null, auth = null, surface = 'credit-backed operation'}) {
  let context = user && auth ? {user, auth} : null;
  if (!context) context = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
  requireCreditGatedEmail(context.user && context.user.email, surface);
  return context;
}

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function boundedText(value, max = 12000) {
  const text = typeof value === 'string' ? value : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function driveQueryLiteral(value, max = 300) {
  return safeText(value, max).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function safeDriveFileId(value) {
  const fileId = safeText(value, 220);
  if (!/^[A-Za-z0-9_.-]{8,220}$/.test(fileId)) {
    const err = new Error('A valid Google Drive fileId is required.');
    err.status = 400;
    throw err;
  }
  return fileId;
}

function chatGptLimit(value, fallback = 20, max = 50) {
  const limit = Math.floor(safeNumber(value, fallback));
  return Math.max(1, Math.min(max, limit || fallback));
}

function chatGptDriveFile(file = {}) {
  return {
    id: file.id || '',
    name: file.name || '',
    mimeType: file.mimeType || '',
    webViewLink: file.webViewLink || '',
    modifiedTime: file.modifiedTime || '',
    parents: file.parents || [],
  };
}

function chatGptDriveSearchQuery(body = {}) {
  const clauses = ['trashed=false'];
  const query = driveQueryLiteral(body.query || '', 300);
  if (query) {
    clauses.push(`(name contains '${query}' or fullText contains '${query}')`);
  }
  const folderId = safeText(body.folderId, 220);
  if (folderId) {
    clauses.push(`'${driveQueryLiteral(folderId, 220)}' in parents`);
  }
  const mimeTypes = Array.isArray(body.mimeTypes) ? body.mimeTypes : [];
  const cleanMimeTypes = mimeTypes.map((mime) => safeText(mime, 160)).filter((mime) => /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(mime));
  if (cleanMimeTypes.length) {
    clauses.push(`(${cleanMimeTypes.map((mime) => `mimeType='${driveQueryLiteral(mime, 160)}'`).join(' or ')})`);
  }
  return clauses.join(' and ');
}

function headerValue(headers, name) {
  if (!headers) return '';
  if (typeof headers.get === 'function') return headers.get(name) || headers.get(name.toLowerCase()) || '';
  return headers[name] || headers[name.toLowerCase()] || '';
}

function bearerTokenFromExtra(extra) {
  const header = headerValue(extra && extra.requestInfo && extra.requestInfo.headers, 'authorization');
  const match = String(header || '').match(/^Bearer\s+(.+)$/i);
  if (!match) {
    const err = new Error('Missing Google OAuth bearer token. Connect this app with Google OAuth before using Drive tools.');
    err.status = 401;
    err.wwwAuthenticate = oauthChallenge();
    throw err;
  }
  return match[1];
}

function hasBearerAuthorization(req) {
  const header = req && typeof req.get === 'function' ? req.get('Authorization') : '';
  return /^Bearer\s+.+/i.test(String(header || ''));
}

function rejectMissingTransportAuth(req, res) {
  if (hasBearerAuthorization(req)) return false;
  res.set('WWW-Authenticate', oauthChallenge());
  res.status(401).json({
    error: 'authorization_required',
    error_description: 'Connect Home Center with Google OAuth before using the MCP transport.',
    resource_metadata: MCP_RESOURCE_METADATA,
    scopes: MCP_REQUIRED_SCOPES,
  });
  return true;
}

function googleDirectAuth(google, accessToken) {
  const auth = new google.auth.OAuth2();
  auth.setCredentials({access_token: accessToken});
  return auth;
}

function googleOAuthClient(google, clientId, clientSecret, redirectUri = MCP_GOOGLE_CALLBACK) {
  return new google.auth.OAuth2(clientId || '', clientSecret || '', redirectUri);
}

function randomToken(bytes = 32) {
  return randomBytes(bytes).toString('base64url');
}

function tokenHash(token) {
  return createHash('sha256').update(String(token || '')).digest('hex');
}

function tokenHashPrefix(value, length = 12) {
  const text = String(value || '');
  return text ? tokenHash(text).slice(0, length) : '';
}

function connectorAttemptId(req, fallback = '') {
  const state = safeText((req.query && req.query.state) || (req.body && req.body.state), 160);
  if (state) return tokenHashPrefix(state);
  const clientId = safeText((req.query && req.query.client_id) || (req.body && req.body.client_id), 800);
  if (clientId) return tokenHashPrefix(clientId);
  const auth = req.get && req.get('Authorization');
  if (auth) return tokenHashPrefix(auth);
  return fallback || randomUUID().slice(0, 12);
}

function redirectHost(value) {
  try {
    const url = new URL(String(value || ''));
    return url.host;
  } catch (_) {
    return '';
  }
}

function redirectPath(value) {
  try {
    const url = new URL(String(value || ''));
    return url.pathname || '';
  } catch (_) {
    return '';
  }
}

function userAgentClass(userAgent) {
  const ua = String(userAgent || '').toLowerCase();
  if (!ua) return 'unknown';
  if (ua.includes('chatgpt')) return 'chatgpt';
  if (likelyEmbeddedOAuthUserAgent(ua)) return 'embedded';
  if (ua.includes('android') && ua.includes('chrome/')) return 'android_chrome';
  if (ua.includes('mobile')) return 'mobile_browser';
  return 'browser';
}

function connectorLog(event, req, fields = {}) {
  const redirectUri = (req.query && req.query.redirect_uri) || (req.body && req.body.redirect_uri);
  const payload = {
    event: `mcp_connector_${event}`,
    attemptId: connectorAttemptId(req),
    method: req && req.method,
    path: req && req.path,
    clientIdPrefix: safeText((req.query && req.query.client_id) || (req.body && req.body.client_id), 80).slice(0, 28),
    redirectHost: redirectHost(redirectUri),
    redirectPath: redirectPath(redirectUri),
    userAgentClass: userAgentClass(req && req.get ? req.get('User-Agent') : ''),
    ...fields,
  };
  console.log(JSON.stringify(payload));
}

function pkceChallenge(verifier) {
  return createHash('sha256').update(String(verifier || '')).digest('base64url');
}

function redirectWithParams(base, params) {
  const url = new URL(base);
  if (url.hostname === 'chatgpt.com' && url.hash && url.hash.includes('Connectors')) {
    const hash = url.hash.slice(1);
    const question = hash.indexOf('?');
    const route = question >= 0 ? hash.slice(0, question) : hash;
    const search = new URLSearchParams(question >= 0 ? hash.slice(question + 1) : '');
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
    }
    url.hash = `${route}?${search.toString()}`;
    return url.toString();
  }
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
  }
  return url.toString();
}

function htmlEscape(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function likelyEmbeddedOAuthUserAgent(userAgent) {
  const ua = String(userAgent || '').toLowerCase();
  if (!ua) return false;
  const embeddedMarkers = [
    '; wv)',
    '; wv ',
    ' wv;',
    'version/4.0 chrome/',
    'fbav/',
    'fban/',
    'instagram',
    'line/',
    'twitter',
    'linkedinapp',
    'electron',
    'chatgpt',
  ];
  return embeddedMarkers.some((marker) => ua.includes(marker));
}

function isChatgptConnectorRedirectUri(redirectUri) {
  try {
    const url = new URL(String(redirectUri || ''));
    return url.hostname === 'chatgpt.com' && url.pathname.startsWith('/connector/oauth/');
  } catch (_) {
    return false;
  }
}

function shouldUseConnectorHandoff(req, redirectUri) {
  const ua = String(req && req.get ? req.get('User-Agent') : '').toLowerCase();
  if (!isChatgptConnectorRedirectUri(redirectUri)) return likelyEmbeddedOAuthUserAgent(ua);
  if (likelyEmbeddedOAuthUserAgent(ua)) return true;
  return ua.includes('android') || ua.includes('mobile');
}

function mcpMountedPath(pathname) {
  const cleanPath = String(pathname || '').startsWith('/') ? String(pathname || '') : `/${pathname || ''}`;
  try {
    const basePath = new URL(MCP_PUBLIC_BASE).pathname.replace(/\/$/, '');
    return `${basePath}${cleanPath}`;
  } catch (_) {
    return cleanPath;
  }
}

function renderSecureBrowserOAuthHandoff(googleAuthUrl, flowState, mode = 'secure-browser') {
  const safeUrl = htmlEscape(googleAuthUrl);
  const chatgptMobile = mode === 'chatgpt-mobile';
  const title = chatgptMobile ? 'Complete Home Center sign-in' : 'Open Home Center sign-in in a secure browser';
  const body = chatgptMobile
    ? 'Keep this page open. Complete Google sign-in in the browser tab that opens, then return here if ChatGPT does not resume automatically. This page will finish the ChatGPT connector.'
    : 'Google blocked this sign-in surface because it looks like an embedded browser. Open Google sign-in in Chrome or another system browser, then return here. This page will finish the ChatGPT connector automatically.';
  const button = chatgptMobile ? 'Continue with Google' : 'Continue in secure browser';
  const handoffStatusPath = mcpMountedPath('/oauth/handoff-status');
  const handoffCompletePath = mcpMountedPath('/oauth/handoff-complete');
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Open Home Center Sign-In</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; padding: 32px; line-height: 1.5; color: #17212b; background: #f7f8fa; }
    main { max-width: 680px; margin: 0 auto; background: #fff; border: 1px solid #d8dee4; border-radius: 8px; padding: 24px; }
    a.button { display: inline-block; margin: 12px 0; padding: 12px 16px; border-radius: 6px; background: #0969da; color: #fff; text-decoration: none; font-weight: 700; }
    code { display: block; overflow-wrap: anywhere; white-space: normal; background: #f6f8fa; padding: 12px; border-radius: 6px; }
  </style>
</head>
<body>
  <main>
    <h1>${htmlEscape(title)}</h1>
    <p>${htmlEscape(body)}</p>
    <p><a class="button" href="${safeUrl}" target="_blank" rel="noopener noreferrer">${htmlEscape(button)}</a></p>
    <p>If the button stays inside this app, copy this link into Chrome:</p>
    <code>${safeUrl}</code>
    <p id="handoff-status">Waiting for secure-browser sign-in...</p>
  </main>
  <script>
    const flowState = ${JSON.stringify(flowState)};
    const handoffStatusPath = ${JSON.stringify(handoffStatusPath)};
    const handoffCompletePath = ${JSON.stringify(handoffCompletePath)};
    async function pollHandoff() {
      try {
        const response = await fetch(handoffStatusPath + '?state=' + encodeURIComponent(flowState), {cache: 'no-store'});
        const data = await response.json();
        const status = document.getElementById('handoff-status');
        if (data.status === 'complete') {
          status.textContent = 'Sign-in approved. Returning to ChatGPT...';
          window.location.href = handoffCompletePath + '?state=' + encodeURIComponent(flowState);
          return;
        }
        if (data.status === 'error' || data.status === 'expired') {
          status.textContent = data.message || 'Sign-in could not be completed. Reconnect the connector and try again.';
          return;
        }
      } catch (_) {}
      setTimeout(pollHandoff, 2000);
    }
    setTimeout(pollHandoff, 1000);
  </script>
</body>
</html>`;
}

function renderSecureBrowserOAuthComplete(message, finishPath = '') {
  const safeFinishPath = finishPath ? htmlEscape(finishPath) : '';
  const finishLink = safeFinishPath ? `<p><a href="${safeFinishPath}" style="display:inline-block;margin:12px 0;padding:12px 16px;border-radius:6px;background:#0969da;color:#fff;text-decoration:none;font-weight:700;">Finish connector</a></p>` : '';
  const autoFinish = finishPath ? `<script>setTimeout(function(){ window.location.href = ${JSON.stringify(finishPath)}; }, 1500);</script>` : '';
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Home Center Sign-In Complete</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; padding: 32px; line-height: 1.5; color: #17212b; background: #f7f8fa; }
    main { max-width: 680px; margin: 0 auto; background: #fff; border: 1px solid #d8dee4; border-radius: 8px; padding: 24px; }
  </style>
</head>
<body>
  <main>
    <h1>Home Center sign-in complete</h1>
    <p>${htmlEscape(message || 'Return to ChatGPT to finish connecting the connector.')}</p>
    ${finishLink}
  </main>
  ${autoFinish}
</body>
</html>`;
}

function oauthCollection(admin, name) {
  return admin.firestore().collection(name);
}

function providerValue(value) {
  return typeof value === 'function' ? value() : value;
}

async function loadMcpAccessContext(admin, google, googleClientId, googleClientSecret, accessToken) {
  const snap = await oauthCollection(admin, 'mcpOAuthAccessTokens').doc(tokenHash(accessToken)).get();
  if (!snap.exists) return null;
  const data = snap.data() || {};
  if (data.revokedAtMs || safeNumber(data.expiresAtMs, 0) <= Date.now()) {
    const err = new Error(data.revokedAtMs ? 'Home Center OAuth token was revoked. Reconnect the client.' : 'Home Center OAuth token expired. Reconnect the ChatGPT app.');
    err.status = 401;
    err.wwwAuthenticate = oauthChallenge();
    throw err;
  }
  const auth = googleOAuthClient(google, providerValue(googleClientId), providerValue(googleClientSecret));
  auth.setCredentials(data.googleTokens || {});
  auth.on('tokens', async (tokens) => {
    const merged = {...(data.googleTokens || {}), ...tokens};
    await snap.ref.set({googleTokens: merged, updatedAtMs: Date.now()}, {merge: true});
  });
  return {
    user: {email: safeText(data.email, 320).toLowerCase(), authKind: 'home_center_mcp_oauth'},
    auth,
    accessToken,
  };
}

async function googleIdentityFromToken(accessToken) {
  const response = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
    headers: {Authorization: `Bearer ${accessToken}`},
  });
  const text = await response.text();
  let profile = {};
  try {
    profile = text ? JSON.parse(text) : {};
  } catch (_) {
    profile = {};
  }
  if (!response.ok) {
    const err = new Error(`Google OAuth token verification failed: HTTP ${response.status} ${text.slice(0, 300)}`);
    err.status = 401;
    throw err;
  }
  const email = safeText(profile.email, 320).toLowerCase();
  if (!email || profile.email_verified === false) {
    const err = new Error('Google OAuth token did not include a verified email.');
    err.status = 401;
    throw err;
  }
  return {email, authKind: 'google_oauth_bearer'};
}

async function requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret) {
  const accessToken = bearerTokenFromExtra(extra);
  const proxied = await loadMcpAccessContext(admin, google, googleClientId, googleClientSecret, accessToken);
  if (proxied) return proxied;
  const user = await googleIdentityFromToken(accessToken);
  const auth = googleDirectAuth(google, accessToken);
  return {user, auth, accessToken};
}

function jsonText(value) {
  return JSON.stringify(value, null, 2);
}

function textResult(value) {
  return {content: [{type: 'text', text: typeof value === 'string' ? value : jsonText(value)}]};
}

function mcpToolResult(value) {
  if (value && value._mcpContent && Array.isArray(value._mcpContent.content)) return value._mcpContent;
  if (value && typeof value === 'object' && !Array.isArray(value) && value._mcpContent) {
    const clean = {...value};
    delete clean._mcpContent;
    return textResult(clean);
  }
  return textResult(value);
}

function parseJsonPayload(text, label) {
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`${label} did not return JSON: ${String(text || '').slice(0, 500)}`);
  }
}

function parseMcpPayload(text, label) {
  const dataLines = String(text || '').split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim());
  return parseJsonPayload(dataLines.length ? dataLines.join('\n') : text, label);
}

function commandCenterOperationRegistry() {
  return {
    version: HOME_CENTER_REGISTRY_VERSION,
    invocationTool: 'command_center_operation',
    commandCenterMcpUrl: COMMAND_CENTER_MCP_URL,
    purpose: 'Expose Command Center dispatch and managed knowledge-bucket operations through the already-installed Home Center MCP connector so ChatGPT can create, inspect, resume, revise, authorize, and preserve worker knowledge without discovering a second MCP app.',
    operations: {
      health: {summary: 'Check Command Center MCP health and tool exposure.', readOnly: true, input: {}},
      'projects.resolve': {summary: 'Resolve an active project before creating a job.', readOnly: false, input: {repository: 'optional string', capability: 'optional string', projectId: 'optional string', idempotencyKey: 'string'}},
      'projects.get': {summary: 'Read one persisted Command Center project packet.', readOnly: true, input: {projectId: 'string'}},
      'projects.upsert': {summary: 'Create or update a durable Command Center project binding.', readOnly: false, input: {projectId: 'string', repository: 'optional string', capability: 'optional string', repositoryBinding: 'optional object', availableWorkers: 'optional string[]', idempotencyKey: 'string'}},
      'render.blender_glb': {summary: 'Run non-agent Blender execution from durable refs, authenticated GitHub sources, or inline script. Prefer glbSource.provider=github for private repository GLBs when ChatGPT cannot expose the top-level binary upload tool; nested command_center_operation args cannot activate host file upload slots.', readOnly: false, topLevelFileTool: 'render_blender_glb', input: {glbRef: 'drive:// | bucket:// | gs:// GLB ref for dispatcher calls', glbSource: '{provider: github, repository: owner/name, ref: commit-or-branch, path: path/to/file.glb}', scriptRef: 'optional drive:// | bucket:// | gs:// Blender Python ref', scriptSource: 'optional authenticated GitHub Python descriptor', scriptText: 'optional inline Python script alternative', settings: 'optional object', executionContract: 'optional object', cache: 'optional boolean', idempotencyKey: 'string'}},
      'jobs.create': {summary: 'Create a durable worker ticket/job.', readOnly: false, input: {projectId: 'string', title: 'string', objective: 'string', acceptanceCriteria: 'string[]', workerRequirements: 'string[]', mutationPolicy: 'object', idempotencyKey: 'string'}},
      'jobs.create_followup': {summary: 'Create a new linked invocation from a source job handoff without rewriting the old job.', readOnly: false, input: {sourceJobId: 'string', title: 'string', objective: 'string', acceptanceCriteria: 'optional string[]', constraints: 'optional string[]', mutationPolicy: 'optional object', idempotencyKey: 'string'}},
      'jobs.get': {summary: 'Read one Command Center job packet.', readOnly: true, input: {jobId: 'string'}},
      'jobs.list': {summary: 'List recent Command Center jobs.', readOnly: true, input: {projectId: 'optional string', status: 'optional string', limit: 'optional number'}},
      'jobs.reconcile_stale': {summary: 'Dry-run or expire stale nonterminal Command Center jobs and leases.', readOnly: false, input: {dryRun: 'optional boolean', olderThanMs: 'optional number', statuses: 'optional string[]', limit: 'optional number', idempotencyKey: 'required when dryRun=false'}},
      'jobs.dispatch_queued': {summary: 'Dry-run or lease queued recoverable jobs to the least-loaded compatible worker; retry expired jobs only when requested.', readOnly: false, input: {dryRun: 'optional boolean', retryExpired: 'optional boolean', limit: 'optional number', maxDispatch: 'optional number', idempotencyKey: 'required when dryRun=false'}},
      'jobs.cancel': {summary: 'Cancel a job with an audit event.', readOnly: false, input: {jobId: 'string', reason: 'optional string', idempotencyKey: 'string'}},
      'jobs.resume': {summary: 'Resume a job from checkpoint.', readOnly: false, input: {jobId: 'string', reason: 'optional string', idempotencyKey: 'string'}},
      'jobs.revise': {summary: 'Revise a job packet with new constraints or acceptance criteria.', readOnly: false, input: {jobId: 'string', revision: 'object', idempotencyKey: 'string'}},
      'jobs.answer_question': {summary: 'Answer a worker question and let the job continue when policy allows.', readOnly: false, input: {jobId: 'string', questionId: 'optional string', answer: 'string', decision: 'optional string', idempotencyKey: 'string'}},
      'jobs.authorize_mutation': {summary: 'Approve or reject a requested worker mutation.', readOnly: false, input: {jobId: 'string', action: 'string', approved: 'boolean', reason: 'optional string', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'jobs.get_summary': {summary: 'Read compact resumable job summary/checkpoint.', readOnly: true, input: {jobId: 'string'}},
      'jobs.get_handoff': {summary: 'Read review/correction handoff synthesized from job state, events, logs, artifacts, checkpoints, and bucket objects.', readOnly: true, input: {jobId: 'string'}},
      'jobs.get_events': {summary: 'Read structured job events.', readOnly: true, input: {jobId: 'string', limit: 'optional number'}},
      'jobs.get_logs': {summary: 'Read job log metadata.', readOnly: true, input: {jobId: 'string', limit: 'optional number'}},
      'jobs.get_artifacts': {summary: 'Read job artifact metadata.', readOnly: true, input: {jobId: 'string', limit: 'optional number'}},
      'agents.upsert_repo_agent': {summary: 'Create or update a durable repo/project agent identity for real OpenAI Codex cloud activations.', readOnly: false, input: {projectId: 'string', agentId: 'optional string', repository: 'optional string', contextRefs: 'optional string[]', idempotencyKey: 'string'}},
      'agents.create_activation': {summary: 'Create a dormant-to-active packet for a durable Codex worker session. Repo binding is optional; Cloud Run Debian workers restore/write GCS workspace snapshots.', readOnly: false, input: {agentId: 'optional string', projectId: 'optional string', repository: 'optional string', sessionId: 'optional string', prompt: 'string', workerRequirements: 'optional string[]', currentWorkspaceSnapshotRef: 'optional string', acceptanceCriteria: 'optional string[]', artifactRequirements: 'optional string[]', idempotencyKey: 'string'}},
      'agents.get_resume_packet': {summary: 'Read the durable packet a bridge uses to start or resume the real Codex cloud surface.', readOnly: true, input: {activationId: 'string'}},
      'agents.record_codex_cloud_ref': {summary: 'Record the real ChatGPT/OpenAI Codex cloud task URL or resume handle for an activation.', readOnly: false, input: {activationId: 'string', url: 'optional string', status: 'optional string', idempotencyKey: 'string'}},
      'agents.record_artifact': {summary: 'Record a redacted artifact from a real Codex cloud activation.', readOnly: false, input: {activationId: 'string', name: 'string', uri: 'optional string', body: 'optional string', idempotencyKey: 'string'}},
      'agents.complete_activation': {summary: 'Mark a durable Codex worker activation terminal and write Command Center memory. Completed durable sessions require artifact evidence and next snapshot when requested.', readOnly: false, input: {activationId: 'string', status: 'completed|failed|canceled|needs_human', finalSummary: 'optional string', nextWorkspaceSnapshotRef: 'optional string', idempotencyKey: 'string'}},
      'agents.get_handoff': {summary: 'Read a ChatGPT-reviewable handoff for a real Codex cloud activation.', readOnly: true, input: {activationId: 'string'}},
      'bucket.get_layout': {summary: 'Read Command Center managed knowledge bucket lanes and storage policy.', readOnly: true, input: {}},
      'bucket.put_object': {summary: 'Write durable execution memory, scratch/promoted skills, or cross-repo notes. Secrets are rejected.', readOnly: false, input: {kind: 'memory.past_log|memory.current_condensed|skill.scratch|skill.promoted|note.cross_repo', title: 'string', summary: 'optional string', body: 'optional string', objectUri: 'optional string', projectId: 'optional string', repository: 'optional string', jobId: 'optional string', tags: 'optional string[]', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'bucket.get_object': {summary: 'Read one Command Center bucket object by id.', readOnly: true, input: {objectId: 'string'}},
      'bucket.list_objects': {summary: 'List Command Center bucket objects by kind, project, repository, job, or tag.', readOnly: true, input: {kind: 'optional string', projectId: 'optional string', repository: 'optional string', jobId: 'optional string', tag: 'optional string', limit: 'optional number'}},
      'bucket.promote_skill': {summary: 'Promote a scratch skill bucket object into the promoted skill lane with provenance.', readOnly: false, input: {objectId: 'string', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'app_control.seed_profiles': {summary: 'Publish built-in app-control seed profiles into Home Center cloud Firestore and managed bucket.', readOnly: false, input: {idempotencyKey: 'string'}},
      'app_control.put_profile': {summary: 'Create or update a cloud app-control profile versioned by Android package and app version.', readOnly: false, input: {profile: 'object', idempotencyKey: 'string'}},
      'app_control.get_profile': {summary: 'Read one cloud app-control profile by profileId.', readOnly: true, input: {profileId: 'string'}},
      'app_control.list_profiles': {summary: 'List cloud app-control profiles by package, workflow, or status.', readOnly: true, input: {packageName: 'optional string', workflow: 'optional string', status: 'optional string', limit: 'optional number'}},
      'app_control.record_run': {summary: 'Record redacted app-control execution evidence, timings, frame-lane status, and learned fixes.', readOnly: false, input: {profileId: 'string', workflow: 'string', status: 'optional string', elapsedMs: 'optional number', uiActionCount: 'optional number', frameLane: 'optional object', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'browser_sessions.create': {summary: 'Create a Playwright desktop Chromium browser-hands session.', readOnly: false, input: {intent: 'string', startUrl: 'optional string', surface: 'optional object', idempotencyKey: 'string'}},
      'browser_sessions.observe': {summary: 'Read browser-hands session state and recent episodes.', readOnly: true, input: {sessionId: 'string', limit: 'optional number'}},
      'browser_sessions.act': {summary: 'Request or record a constrained browser action; sensitive actions are human-blocked.', readOnly: false, input: {sessionId: 'string', action: 'string', target: 'optional object', reason: 'optional string', idempotencyKey: 'string'}},
      'browser_sessions.record_episode': {summary: 'Record a redacted browser-hands invocation and candidate discoveries.', readOnly: false, input: {sessionId: 'string', origin: 'optional string', outcome: 'optional string', actions: 'optional object[]', discoveryCandidates: 'optional object[]', idempotencyKey: 'string'}},
      'browser_discoveries.list': {summary: 'List browser discoveries by origin, task, or state.', readOnly: true, input: {origin: 'optional string', task: 'optional string', state: 'optional string', limit: 'optional number'}},
      'browser_discoveries.promote': {summary: 'Promote a validated browser discovery into trusted household playbook guidance.', readOnly: false, input: {discoveryId: 'string', guidance: 'optional string', playbook: 'optional object', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'browser_playbooks.lookup': {summary: 'Lookup a trusted Playwright DOM/accessibility browser playbook by origin, taskKey, shareScope, or replayAudience.', readOnly: true, input: {origin: 'optional string', taskKey: 'optional string', task: 'optional string', shareScope: 'optional string', replayAudience: 'optional string', limit: 'optional number'}},
      'workers.list': {summary: 'List registered Command Center workers.', readOnly: true, input: {}},
      'workers.get_capabilities': {summary: 'Read one worker capability packet.', readOnly: true, input: {workerId: 'string'}},
      'workers.wake': {summary: 'Invoke a configured real Cloud Run worker so liveness can be proven by heartbeat.', readOnly: false, input: {workerId: 'string', activationId: 'optional string', sessionId: 'optional string', projectId: 'optional string', reason: 'optional string', runLabel: 'optional string', idempotencyKey: 'string'}},
      'workers.register_oneshot': {summary: 'Register a prepared one-shot Codex worker.', readOnly: false, input: {worker: 'object', idempotencyKey: 'string'}},
    },
  };
}

function supportedCommandCenterOperationTypes() {
  return Object.keys(commandCenterOperationRegistry().operations);
}

function commandCenterToolName(operation) {
  const raw = safeText(operation, 120);
  const op = raw.startsWith('command_center.') ? raw.slice('command_center.'.length) : raw;
  if (!commandCenterOperationRegistry().operations[op]) throw Object.assign(new Error('Unsupported command_center_operation operation: ' + op), {status: 400});
  return op.startsWith('command_center.') ? op : `command_center.${op}`;
}

async function postCommandCenterMcp(body, bearerToken) {
  const response = await fetch(COMMAND_CENTER_MCP_URL, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${bearerToken}`,
      'content-type': 'application/json',
      accept: 'application/json, text/event-stream',
    },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  if (response.status >= 400) {
    const err = new Error(`Command Center MCP HTTP ${response.status}: ${text.slice(0, 800)}`);
    err.status = response.status;
    throw err;
  }
  return parseMcpPayload(text, 'Command Center MCP response');
}

function homeCenterRenderInputError(message, status = 400, failureKind = 'input_validation') {
  const err = new Error(message);
  err.status = status;
  err.failureKind = failureKind;
  return err;
}

function isMcpFileLike(value) {
  return value && typeof value === 'object' && typeof value.arrayBuffer === 'function' && typeof value.name === 'string';
}

function homeCenterRenderOwnerKey(user = {}) {
  return safeText(user.email || user.sub || user.uid || 'unknown', 320).replace(/[^A-Za-z0-9_.@-]+/g, '_') || 'unknown';
}

function generatedArtifactOwnerKey(user = {}) {
  const email = safeText(user.email, 320).toLowerCase();
  if (email === 'dclarke1005@gmail.com') return 'drew';
  if (email === 'junewren28@gmail.com') return 'june';
  return homeCenterRenderOwnerKey(user).toLowerCase();
}

function driveRenderFileId(ref) {
  const raw = safeText(ref, 1200).replace(/^drive:\/\//i, '');
  const id = raw.split(/[?#/]/).filter(Boolean).pop() || raw;
  if (!/^[A-Za-z0-9_-]{8,220}$/.test(id)) throw homeCenterRenderInputError('drive input ref has an invalid file id.', 400, 'input_validation');
  return id;
}

function renderInputRoleFromField(fieldName) {
  return fieldName === 'glbRef' || fieldName === 'glbFile' ? 'glb' : 'script';
}

function renderContentType(role) {
  return role === 'glb' ? 'model/gltf-binary' : 'text/x-python';
}

function renderFallbackName(role) {
  return role === 'glb' ? 'input.glb' : 'render.py';
}

function cleanRenderUploadName(value, fallback) {
  const clean = safeText(value, 240).replace(/\\/g, '/').split('/').pop().replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '');
  return clean || fallback;
}

function sha256RenderBytes(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function parseRenderGsRef(ref) {
  const text = safeText(ref, 1600);
  const match = text.match(/^gs:\/\/([^/]+)\/(.+)$/i);
  if (!match) throw homeCenterRenderInputError('Inline render delivery requires a private gs:// artifact ref.', 400, 'render_inline_artifact_ref_invalid');
  const privateRenderBuckets = new Set([COMMAND_CENTER_RENDER_BUCKET, 'home-center-generated']);
  if (!privateRenderBuckets.has(match[1])) throw homeCenterRenderInputError('Inline render delivery refused artifact outside the configured private render bucket.', 403, 'render_inline_artifact_owner_scope_failed');
  if (!match[2].startsWith('renders/gifs/') && !match[2].startsWith('command-center-renders/')) throw homeCenterRenderInputError('Inline render delivery refused artifact outside the render artifact prefix.', 403, 'render_inline_artifact_owner_scope_failed');
  return {bucket: match[1], name: match[2], ref: text};
}

function renderArtifactHashEntry(result = {}, rel = 'walk-loop.gif') {
  const direct = safeObject(result.artifactHashes);
  const bundle = safeObject(result.bundle);
  const bundled = safeObject(bundle.artifactHashes);
  return safeObject(direct[rel] || bundled[rel]);
}

function renderReceiptWithoutInlinePayload(operationResult = {}, delivery = null) {
  const clean = JSON.parse(JSON.stringify(operationResult || {}));
  if (clean && clean.result) {
    clean.result.inlineMediaDelivery = delivery ? {...delivery, data: undefined, base64: undefined} : null;
  }
  return clean;
}

async function verifiedRenderGifMcpContent(result = {}, {storage = null, google = null, auth = null, parentFolderId = ''} = {}) {
  const renderResult = safeObject(result);
  const loopingGifRef = safeText(renderResult.loopingGifRef, 1600);
  const expected = renderArtifactHashEntry(renderResult, 'walk-loop.gif');
  const expectedSha256 = safeText(expected.sha256, 128).toLowerCase();
  const expectedByteCount = Number(expected.byteCount || 0) || 0;
  const deliveryBase = {
    ok: false,
    type: 'mcp_resource_link',
    mimeType: 'image/gif',
    artifactRef: loopingGifRef,
    durableRef: '',
    byteCount: 0,
    sha256: '',
    expectedByteCount,
    expectedSha256,
    ceilingBytes: HOME_CENTER_RENDER_INLINE_GIF_MAX_BYTES,
    contentBlockType: '',
    errorCode: '',
    message: '',
  };
  if (!loopingGifRef) return {contentBlock: null, delivery: {...deliveryBase, errorCode: 'render_gif_resource_link_missing_ref', message: 'Renderer did not return loopingGifRef.'}};
  if (!expectedSha256 || !expectedByteCount) return {contentBlock: null, delivery: {...deliveryBase, errorCode: 'render_gif_resource_link_missing_hash', message: 'Renderer did not return walk-loop.gif byte count and SHA-256.'}};
  const parsed = parseRenderGsRef(loopingGifRef);
  const client = storage || new Storage();
  const [bytes] = await client.bucket(parsed.bucket).file(parsed.name).download();
  const buffer = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes);
  const readbackSha256 = sha256RenderBytes(buffer);
  if (buffer.length !== expectedByteCount || readbackSha256 !== expectedSha256) {
    return {contentBlock: null, delivery: {...deliveryBase, byteCount: buffer.length, sha256: readbackSha256, errorCode: 'render_gif_resource_link_readback_mismatch', message: 'Private GCS GIF readback did not match renderer hash metadata.'}};
  }
  if (!google || !auth) return {contentBlock: null, delivery: {...deliveryBase, ok: false, byteCount: buffer.length, sha256: readbackSha256, errorCode: 'render_gif_resource_link_auth_missing', message: 'Verified GIF readback succeeded, but authenticated Drive context was unavailable for resource_link creation.'}};
  const uploaded = await uploadVerifiedArtifact({google, auth, parentFolderId, item: {name: 'walk-loop.gif', format: 'gif', mimeType: 'image/gif', bytes: buffer, byteCount: buffer.length, sha256: readbackSha256, clipMetrics: {}}});
  const contentBlock = uploaded.chatGptFileRef;
  return {contentBlock, delivery: {...deliveryBase, ok: true, durableRef: uploaded.durableRef, storageRef: uploaded.storageRef || uploaded.durableRef, driveDurableRef: uploaded.driveDurableRef || (uploaded.fileId ? 'drive://' + uploaded.fileId : ''), byteCount: uploaded.byteCount, sha256: uploaded.sha256, readbackByteCount: uploaded.readbackByteCount, readbackSha256: uploaded.readbackSha256, fileId: uploaded.fileId || '', contentBlockType: contentBlock.type, message: 'Private GCS GIF readback verified and attached as authenticated resource_link.'}};
}

async function attachRenderGifMcpContent(operationResult = {}, options = {}) {
  const cleanResult = JSON.parse(JSON.stringify(operationResult || {}));
  if (!cleanResult || cleanResult.operation !== 'render.blender_glb' || !cleanResult.result) return cleanResult;
  const inline = await verifiedRenderGifMcpContent(cleanResult.result, options).catch((err) => ({contentBlock: null, delivery: {ok: false, type: 'mcp_resource_link', mimeType: 'image/gif', artifactRef: safeText(cleanResult.result && cleanResult.result.loopingGifRef, 1600), durableRef: '', byteCount: 0, sha256: '', expectedByteCount: 0, expectedSha256: '', ceilingBytes: HOME_CENTER_RENDER_INLINE_GIF_MAX_BYTES, contentBlockType: '', errorCode: safeText(err && err.failureKind, 120) || 'render_gif_resource_link_failed', message: safeText(err && err.message, 500)}}));
  cleanResult.result.inlineMediaDelivery = inline.delivery;
  const receipt = renderReceiptWithoutInlinePayload(cleanResult, inline.delivery);
  const content = [{type: 'text', text: jsonText(receipt)}];
  if (inline.contentBlock) content.push(inline.contentBlock);
  cleanResult._mcpContent = {content};
  return cleanResult;
}

function validateHomeCenterRenderBytes(bytes, role, label) {
  if (role === 'glb') {
    if (!Buffer.isBuffer(bytes) || bytes.length < 12) throw homeCenterRenderInputError(label + ' is too small to be a GLB file.');
    if (bytes.length > HOME_CENTER_RENDER_MAX_GLB_BYTES) throw homeCenterRenderInputError(label + ' exceeds max GLB size ' + HOME_CENTER_RENDER_MAX_GLB_BYTES + ' bytes.', 413, 'input_validation');
    if (bytes.slice(0, 4).toString('ascii') !== 'glTF') throw homeCenterRenderInputError(label + ' is not a GLB: missing glTF magic.');
    if (bytes.readUInt32LE(4) !== 2) throw homeCenterRenderInputError(label + ' must be GLB version 2.');
    if (bytes.readUInt32LE(8) > bytes.length) throw homeCenterRenderInputError(label + ' declares more bytes than were downloaded.');
    return;
  }
  if (!Buffer.isBuffer(bytes) || bytes.length === 0) throw homeCenterRenderInputError(label + ' is empty.');
  if (bytes.length > HOME_CENTER_RENDER_MAX_SCRIPT_BYTES) throw homeCenterRenderInputError(label + ' exceeds max script size ' + HOME_CENTER_RENDER_MAX_SCRIPT_BYTES + ' bytes.', 413, 'input_validation');
  if (bytes.includes(0)) throw homeCenterRenderInputError(label + ' must be a text Python script, not binary data.');
}

function renderStreamValidator(role, label) {
  const hash = createHash('sha256');
  let byteCount = 0;
  let header = Buffer.alloc(0);
  let sawNul = false;
  const maxBytes = role === 'glb' ? HOME_CENTER_RENDER_MAX_GLB_BYTES : HOME_CENTER_RENDER_MAX_SCRIPT_BYTES;
  const stream = new Transform({
    transform(chunk, _encoding, callback) {
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      byteCount += bytes.length;
      if (byteCount > maxBytes) return callback(homeCenterRenderInputError(label + ' exceeds max ' + role + ' size ' + maxBytes + ' bytes.', 413, 'input_validation'));
      if (header.length < 12) header = Buffer.concat([header, bytes.slice(0, 12 - header.length)]);
      if (role === 'script' && bytes.includes(0)) sawNul = true;
      hash.update(bytes);
      callback(null, bytes);
    },
    flush(callback) {
      if (role === 'glb') {
        if (byteCount < 12 || header.length < 12) return callback(homeCenterRenderInputError(label + ' is too small to be a GLB file.'));
        if (header.slice(0, 4).toString('ascii') !== 'glTF') return callback(homeCenterRenderInputError(label + ' is not a GLB: missing glTF magic.'));
        if (header.readUInt32LE(4) !== 2) return callback(homeCenterRenderInputError(label + ' must be GLB version 2.'));
        if (header.readUInt32LE(8) !== byteCount) return callback(homeCenterRenderInputError(label + ' GLB length header does not match downloaded byte count.'));
      } else {
        if (byteCount === 0) return callback(homeCenterRenderInputError(label + ' is empty.'));
        if (sawNul) return callback(homeCenterRenderInputError(label + ' must be a text Python script, not binary data.'));
      }
      callback();
    },
  });
  stream.digest = () => ({sha256: hash.digest('hex'), byteCount});
  return stream;
}

function renderReadableFromMedia(media) {
  const data = media && media.data;
  if (data && typeof data.pipe === 'function') return data;
  return Readable.from([mediaBuffer(data)]);
}

function validateRenderMediaSize(size, role, label) {
  const declared = Number(size || 0);
  if (!Number.isFinite(declared) || declared <= 0) return;
  const maxBytes = role === 'glb' ? HOME_CENTER_RENDER_MAX_GLB_BYTES : HOME_CENTER_RENDER_MAX_SCRIPT_BYTES;
  if (declared > maxBytes) throw homeCenterRenderInputError(label + ' exceeds max ' + role + ' size ' + maxBytes + ' bytes.', 413, 'input_validation');
}

async function downloadDriveRenderInput({google, auth, ref, role}) {
  try {
    const drive = google.drive({version: 'v3', auth});
    const fileId = driveRenderFileId(ref);
    const meta = await drive.files.get({fileId, fields: 'id,name,mimeType,size,modifiedTime', supportsAllDrives: true});
    const media = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
    const bytes = mediaBuffer(media.data);
    validateHomeCenterRenderBytes(bytes, role, 'drive://' + fileId);
    return {fileId, name: safeText(meta.data && meta.data.name, 240) || renderFallbackName(role), mimeType: safeText(meta.data && meta.data.mimeType, 160), bytes};
  } catch (err) {
    const wrapped = homeCenterRenderInputError('drive_input_download_auth_failed: Home Center could not download authorized Drive render input for ' + role + '.', err.status || err.code === 404 ? 404 : 401, 'drive_input_download_auth_failed');
    wrapped.cause = err;
    throw wrapped;
  }
}

async function stageHomeCenterDriveRenderInput({google, auth, user, renderId, role, sourceRef}) {
  if (!COMMAND_CENTER_RENDER_BUCKET) throw homeCenterRenderInputError('COMMAND_CENTER_RENDER_BUCKET is not configured for render input staging.', 503, 'transport');
  const fileId = driveRenderFileId(sourceRef);
  const label = 'drive://' + fileId;
  try {
    const drive = google.drive({version: 'v3', auth});
    const meta = await drive.files.get({fileId, fields: 'id,name,mimeType,size,modifiedTime', supportsAllDrives: true});
    validateRenderMediaSize(meta.data && meta.data.size, role, label);
    const media = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'stream'});
    const safeFile = cleanRenderUploadName(meta.data && meta.data.name, renderFallbackName(role));
    const ownerKey = homeCenterRenderOwnerKey(user);
    const basePrefix = 'temp/render-inputs/home-center-bridge/' + ownerKey + '/' + (safeText(renderId, 180) || 'render') + '/';
    const tempName = basePrefix + '.tmp-' + role + '-' + randomUUID() + '-' + safeFile;
    const bucket = new Storage().bucket(COMMAND_CENTER_RENDER_BUCKET);
    const tempFile = bucket.file(tempName);
    const validator = renderStreamValidator(role, label);
    try {
      await pipeline(renderReadableFromMedia(media), validator, tempFile.createWriteStream({
        resumable: false,
        metadata: {contentType: safeText(meta.data && meta.data.mimeType, 160) || renderContentType(role)},
      }));
    } catch (err) {
      await tempFile.delete({ignoreNotFound: true}).catch(() => null);
      throw err;
    }
    const digest = validator.digest();
    const finalName = basePrefix + role + '-' + digest.sha256 + '-' + safeFile;
    await tempFile.move(finalName);
    const finalFile = bucket.file(finalName);
    await finalFile.setMetadata({
      contentType: safeText(meta.data && meta.data.mimeType, 160) || renderContentType(role),
      metadata: {sha256: digest.sha256, byteCount: String(digest.byteCount), role, materializedBy: 'home_center_mcp.command_center_operation', sourceKind: 'drive'},
    });
    return {ref: 'gs://' + COMMAND_CENTER_RENDER_BUCKET + '/' + finalName, sha256: digest.sha256, byteCount: digest.byteCount, fileName: safeFile, materializedFrom: role + 'DriveRef', sourceRef: label, materializedBy: 'home_center_mcp.command_center_operation'};
  } catch (err) {
    if (err && err.phase === 'input_validation') throw err;
    const wrapped = homeCenterRenderInputError('drive_input_download_auth_failed: Home Center could not stream authorized Drive render input for ' + role + '.', err.status || err.code === 404 ? 404 : 401, 'drive_input_download_auth_failed');
    wrapped.cause = err;
    throw wrapped;
  }
}


function normalizeRenderGitHubSource(value, role) {
  const source = safeObject(value);
  const provider = safeText(source.provider, 40).toLowerCase();
  if (!provider && !Object.keys(source).length) return null;
  if (provider !== 'github') throw homeCenterRenderInputError(role + 'Source provider must be github.', 400, 'input_validation');
  const repository = safeGitHubRepo(source.repository || source.repo, 'Valar05/home-center');
  const ref = safeGitHubRef(source.ref || source.sha || source.branch);
  const filePath = safeGitHubPath(source.path || source.filePath);
  return {provider: 'github', repository, ref, path: filePath};
}

function renderGitHubSourceRef(source) {
  return 'github://' + source.repository + '@' + (source.ref || 'default') + '/' + source.path;
}

function renderNowMs() { return Date.now(); }
function renderSourceCacheKey(role, label) {
  return createHash('sha256').update(role + ':' + label).digest('hex');
}
function renderGitHubCacheManifestName(role, label) {
  return 'temp/render-inputs/github-cache/' + role + '/' + renderSourceCacheKey(role, label) + '.json';
}
function renderGitHubCacheObjectName(role, label, digest, safeFile) {
  return 'temp/render-inputs/github-cache/' + role + '/' + renderSourceCacheKey(role, label) + '-' + digest.sha256 + '-' + safeFile;
}
async function readCachedGitHubRenderInput(bucket, role, label) {
  const manifestFile = bucket.file(renderGitHubCacheManifestName(role, label));
  const [exists] = await manifestFile.exists();
  if (!exists) return null;
  try {
    const [bytes] = await manifestFile.download();
    const manifest = JSON.parse(bytes.toString('utf8'));
    if (manifest.sourceRef !== label || manifest.role !== role || !manifest.ref || !manifest.sha256 || !manifest.byteCount) return null;
    const cachedFile = bucket.file(String(manifest.ref).replace(/^gs:\/\/[^/]+\//, ''));
    const [objectExists] = await cachedFile.exists();
    if (!objectExists) return null;
    return manifest;
  } catch (_err) {
    return null;
  }
}
async function writeCachedGitHubRenderInput(bucket, role, label, digest, safeFile, tempFile, contentType, normalized) {
  const cacheObjectName = renderGitHubCacheObjectName(role, label, digest, safeFile);
  await tempFile.move(cacheObjectName);
  const cachedFile = bucket.file(cacheObjectName);
  await cachedFile.setMetadata({
    contentType: renderContentType(role),
    metadata: {sha256: digest.sha256, byteCount: String(digest.byteCount), role, materializedBy: 'home_center_mcp.command_center_operation', sourceKind: 'github-cache', repository: normalized.repository, ref: normalized.ref, path: normalized.path},
  });
  const manifest = {
    ref: 'gs://' + COMMAND_CENTER_RENDER_BUCKET + '/' + cacheObjectName,
    sha256: digest.sha256,
    byteCount: digest.byteCount,
    fileName: safeFile,
    role,
    sourceRef: label,
    contentType: contentType || renderContentType(role),
    materializedBy: 'home_center_mcp.command_center_operation',
    materializedFrom: role + 'GitHubSourceCache',
    source: normalized,
    cachedAtMs: Date.now(),
  };
  await bucket.file(renderGitHubCacheManifestName(role, label)).save(JSON.stringify(manifest, null, 2), {
    resumable: false,
    metadata: {contentType: 'application/json', metadata: {role, sourceKind: 'github-cache-manifest', sourceRefHash: renderSourceCacheKey(role, label)}},
  });
  return manifest;
}

async function stageHomeCenterGitHubRenderInput({githubToken, user, renderId, role, source}) {
  if (!COMMAND_CENTER_RENDER_BUCKET) throw homeCenterRenderInputError('COMMAND_CENTER_RENDER_BUCKET is not configured for render input staging.', 503, 'transport');
  const normalized = normalizeRenderGitHubSource(source, role);
  if (!normalized) throw homeCenterRenderInputError(role + 'Source is required.', 400, 'input_validation');
  const token = githubTokenValue(githubToken);
  if (!token) throw homeCenterRenderInputError('GITHUB_TOKEN secret is not configured for Home Center GitHub render sources.', 503, 'github_input_download_auth_failed');
  const label = renderGitHubSourceRef(normalized);
  const safeFile = cleanRenderUploadName(normalized.path.split('/').pop(), renderFallbackName(role));
  const timings = {startedAtMs: renderNowMs()};
  const bucket = new Storage().bucket(COMMAND_CENTER_RENDER_BUCKET);
  const cached = await readCachedGitHubRenderInput(bucket, role, label);
  timings.cacheLookupMs = Math.max(0, renderNowMs() - timings.startedAtMs);
  if (cached) {
    timings.totalMs = Math.max(0, renderNowMs() - timings.startedAtMs);
    return {
      ref: cached.ref,
      sha256: cached.sha256,
      byteCount: cached.byteCount,
      fileName: cached.fileName || safeFile,
      materializedFrom: role + 'GitHubSourceCache',
      sourceRef: label,
      materializedBy: 'home_center_mcp.command_center_operation',
      source: normalized,
      cacheHit: true,
      timings,
    };
  }
  const filePath = normalized.path.split('/').map(encodeURIComponent).join('/');
  const route = githubRepoRoute(normalized.repository, `/contents/${filePath}${githubQuery({ref: normalized.ref})}`);
  const fetchStartedAtMs = renderNowMs();
  const response = await fetch(`https://api.github.com${route}`, {
    method: 'GET',
    headers: {...githubHeaders(token), Accept: 'application/vnd.github.raw'},
    signal: AbortSignal.timeout(Number(process.env.HOME_CENTER_RENDER_GITHUB_TIMEOUT_MS || 120000)),
  });
  timings.githubOpenMs = Math.max(0, renderNowMs() - fetchStartedAtMs);
  if (!response.ok) {
    let message = response.statusText;
    try {
      const json = await response.json();
      message = safeText(json && json.message, 500) || message;
    } catch (_err) {}
    throw homeCenterRenderInputError('github_input_download_auth_failed: Home Center could not download authenticated GitHub render input for ' + role + ' (HTTP ' + response.status + ': ' + message + ').', response.status === 404 ? 404 : 401, 'github_input_download_auth_failed');
  }
  validateRenderMediaSize(response.headers.get('content-length'), role, label);
  if (!response.body) throw homeCenterRenderInputError('github_input_download_auth_failed: GitHub response did not include a readable body for ' + role + '.', 502, 'github_input_download_auth_failed');
  const tempName = 'temp/render-inputs/github-cache/' + role + '/.tmp-' + role + '-github-' + randomUUID() + '-' + safeFile;
  const tempFile = bucket.file(tempName);
  const validator = renderStreamValidator(role, label);
  const streamStartedAtMs = renderNowMs();
  try {
    await pipeline(Readable.fromWeb(response.body), validator, tempFile.createWriteStream({
      resumable: false,
      metadata: {contentType: response.headers.get('content-type') || renderContentType(role)},
    }));
  } catch (err) {
    await tempFile.delete({ignoreNotFound: true}).catch(() => null);
    throw err;
  }
  timings.githubStreamAndValidateMs = Math.max(0, renderNowMs() - streamStartedAtMs);
  const digest = validator.digest();
  const cacheWriteStartedAtMs = renderNowMs();
  const manifest = await writeCachedGitHubRenderInput(bucket, role, label, digest, safeFile, tempFile, response.headers.get('content-type') || renderContentType(role), normalized);
  timings.cacheWriteMs = Math.max(0, renderNowMs() - cacheWriteStartedAtMs);
  timings.totalMs = Math.max(0, renderNowMs() - timings.startedAtMs);
  return {
    ref: manifest.ref,
    sha256: manifest.sha256,
    byteCount: manifest.byteCount,
    fileName: manifest.fileName,
    materializedFrom: role + 'GitHubSource',
    sourceRef: label,
    materializedBy: 'home_center_mcp.command_center_operation',
    source: normalized,
    cacheHit: false,
    timings,
  };
}

async function stageHomeCenterRenderInput({user, renderId, role, sourceRef, fileName, bytes, contentType}) {
  if (!COMMAND_CENTER_RENDER_BUCKET) throw homeCenterRenderInputError('COMMAND_CENTER_RENDER_BUCKET is not configured for render input staging.', 503, 'transport');
  const hash = sha256RenderBytes(bytes);
  const safeFile = cleanRenderUploadName(fileName, renderFallbackName(role));
  const objectName = 'temp/render-inputs/home-center-bridge/' + homeCenterRenderOwnerKey(user) + '/' + (safeText(renderId, 180) || 'render') + '/' + role + '-' + hash + '-' + safeFile;
  await new Storage().bucket(COMMAND_CENTER_RENDER_BUCKET).file(objectName).save(bytes, {
    resumable: false,
    metadata: {
      contentType: contentType || renderContentType(role),
      metadata: {sha256: hash, role, materializedBy: 'home_center_mcp.command_center_operation', sourceKind: sourceRef && sourceRef.startsWith('drive://') ? 'drive' : 'uploaded'},
    },
  });
  return {ref: 'gs://' + COMMAND_CENTER_RENDER_BUCKET + '/' + objectName, sha256: hash, byteCount: bytes.length, fileName: safeFile, materializedFrom: sourceRef && sourceRef.startsWith('drive://') ? role + 'DriveRef' : role + 'File', sourceRef: sourceRef && sourceRef.startsWith('drive://') ? 'drive://' + driveRenderFileId(sourceRef) : '', materializedBy: 'home_center_mcp.command_center_operation'};
}

async function materializeHomeCenterRenderDriveRefs({google, admin, googleClientId, googleClientSecret, extra, githubToken = () => '', args = {}}) {
  return materializeHomeCenterRenderSources({google, admin, googleClientId, googleClientSecret, extra, githubToken, args});
}

function renderSourceProvided(args, field) {
  const value = args[field];
  if (field.endsWith('Source')) return !!normalizeRenderGitHubSource(value, field === 'glbSource' ? 'glb' : 'script');
  return safeText(value, 1200).length > 0;
}

function assertOneHomeCenterRenderSource(args, role) {
  const refField = role + 'Ref';
  const sourceField = role + 'Source';
  const fileField = role + 'File';
  const count = [renderSourceProvided(args, refField), renderSourceProvided(args, sourceField), isMcpFileLike(args[fileField])].filter(Boolean).length;
  if (count !== 1) throw homeCenterRenderInputError('Exactly one ' + role.toUpperCase() + ' source is required for render.blender_glb: provide ' + refField + ', ' + sourceField + ', or ' + fileField + ', but not more than one.', 400, 'input_validation');
}

async function materializeHomeCenterRenderSources({google, admin, googleClientId, googleClientSecret, extra, githubToken = () => '', args = {}}) {
  const operationArgs = {...args};
  const stagedInputs = Array.isArray(operationArgs.stagedInputs) ? operationArgs.stagedInputs.slice(0, 10) : [];
  assertOneHomeCenterRenderSource(operationArgs, 'glb');
  const scriptCount = [safeText(operationArgs.scriptRef, 1200).length > 0, !!normalizeRenderGitHubSource(operationArgs.scriptSource, 'script'), isMcpFileLike(operationArgs.scriptFile), safeText(operationArgs.scriptText || operationArgs.inlineScript || operationArgs.script, HOME_CENTER_DIRECT_RENDER_TEXT_LIMIT + 1).length > 0].filter(Boolean).length;
  if (scriptCount !== 1) throw homeCenterRenderInputError('Exactly one Blender script source is required: provide scriptRef, scriptSource, scriptFile, or scriptText.', 400, 'input_validation');
  const needsDrive = ['glbRef', 'scriptRef'].some((field) => safeText(operationArgs[field], 1200).toLowerCase().startsWith('drive://'));
  const needsGitHub = !!normalizeRenderGitHubSource(operationArgs.glbSource, 'glb') || !!normalizeRenderGitHubSource(operationArgs.scriptSource, 'script');
  if (!needsDrive && !needsGitHub) return operationArgs;
  const {auth, user} = needsDrive ? await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret) : {auth: null, user: (await loadMcpAccessContext(admin, google, googleClientId, googleClientSecret, bearerTokenFromExtra(extra))).user};
  const seed = safeText(operationArgs.idempotencyKey, 180) || randomUUID();
  const renderId = safeText(operationArgs.renderId, 180) || 'render_' + createHash('sha256').update(homeCenterRenderOwnerKey(user) + ':' + seed).digest('hex').slice(0, 32);
  operationArgs.renderId = renderId;
  for (const [field, role] of [['glbRef', 'glb'], ['scriptRef', 'script']]) {
    const ref = safeText(operationArgs[field], 1200);
    if (!ref.toLowerCase().startsWith('drive://')) continue;
    const staged = await stageHomeCenterDriveRenderInput({google, auth, user, renderId, role, sourceRef: ref});
    operationArgs[field] = staged.ref;
    stagedInputs.push(staged);
  }
  for (const [field, role, refField] of [['glbSource', 'glb', 'glbRef'], ['scriptSource', 'script', 'scriptRef']]) {
    const source = normalizeRenderGitHubSource(operationArgs[field], role);
    if (!source) continue;
    const staged = await stageHomeCenterGitHubRenderInput({githubToken, user, renderId, role, source});
    operationArgs[refField] = staged.ref;
    delete operationArgs[field];
    stagedInputs.push(staged);
  }
  operationArgs.stagedInputs = stagedInputs;
  return operationArgs;
}

function requireTopLevelRenderUpload(args = {}, fieldName) {
  const value = args[fieldName];
  if (!isMcpFileLike(value)) {
    throw homeCenterRenderInputError(fieldName + ' must be a top-level uploaded MCP file. Do not pass a string path, URL, Base64, ref, or nested JSON descriptor.');
  }
  return value;
}

function normalizeDirectRenderBlenderGlbArgs(args = {}) {
  requireTopLevelRenderUpload(args, 'glbFile');
  requireTopLevelRenderUpload(args, 'scriptFile');
  const forbidden = ['glbRef', 'scriptRef', 'scriptText', 'inlineScript', 'script'];
  const providedForbidden = forbidden.filter((key) => safeText(args[key], HOME_CENTER_DIRECT_RENDER_TEXT_LIMIT + 1).length > 0);
  if (providedForbidden.length) {
    throw homeCenterRenderInputError('render_blender_glb accepts only top-level glbFile and scriptFile uploads for model/script sources. Use command_center_operation operation=render.blender_glb for ' + providedForbidden.join(', ') + '.');
  }
  return {
    idempotencyKey: args.idempotencyKey,
    renderId: args.renderId,
    glbFile: args.glbFile,
    scriptFile: args.scriptFile,
    settings: safeObject(args.settings),
    executionContract: safeObject(args.executionContract),
    cache: args.cache,
  };
}

async function renderBlenderGlbBridge({admin, extra, args = {}}) {
  const operationArgs = normalizeDirectRenderBlenderGlbArgs(args);
  return commandCenterRenderBlenderGlb(admin, extra, operationArgs);
}

function mcpTextContentJson(result, label) {
  const text = (((result || {}).content || []).find((item) => item && item.type === 'text') || {}).text || '';
  if (!text) return result;
  return parseJsonPayload(text, label);
}

async function commandCenterOperationRunOperation({google = null, admin = null, googleClientId = '', googleClientSecret = '', githubToken = () => '', extra, args = {}}) {
  const operation = safeText(args.operation || args.type || args.toolName, 120);
  const toolName = commandCenterToolName(operation);
  if (!operation) throw Object.assign(new Error('operation is required.'), {status: 400});
  const context = await requireCreditGatedContext({google, admin, googleClientId, googleClientSecret, extra, surface: 'command_center_operation'});
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? {...args.args} : {...args};
  delete operationArgs.operation;
  delete operationArgs.type;
  delete operationArgs.toolName;
  delete operationArgs.args;
  if (operation === 'render.blender_glb' && google && admin) {
    const materializedArgs = await materializeHomeCenterRenderSources({google, admin, googleClientId, googleClientSecret, extra, githubToken, args: operationArgs});
    const rendered = {operation, toolName, commandCenterMcpUrl: COMMAND_CENTER_MCP_URL, result: await commandCenterRenderBlenderGlb(admin, extra, materializedArgs)};
    return attachRenderGifMcpContent(rendered, {google, auth: context.auth, parentFolderId: safeText(operationArgs.parentFolderId, 220)});
  }

  const bearerToken = bearerTokenFromExtra(extra);

  await postCommandCenterMcp({
    jsonrpc: '2.0',
    id: 'home-center-command-center-init',
    method: 'initialize',
    params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'home-center-command-center-bridge', version: '1'}},
  }, bearerToken);
  await postCommandCenterMcp({jsonrpc: '2.0', method: 'notifications/initialized', params: {}}, bearerToken).catch(() => null);

  const payload = await postCommandCenterMcp({
    jsonrpc: '2.0',
    id: 'home-center-command-center-call',
    method: 'tools/call',
    params: {name: toolName, arguments: operationArgs},
  }, bearerToken);
  if (payload.error) {
    const err = new Error(payload.error.message || `Command Center tool failed: ${toolName}`);
    err.status = 502;
    throw err;
  }
  return {
    operation,
    toolName,
    commandCenterMcpUrl: COMMAND_CENTER_MCP_URL,
    result: mcpTextContentJson(payload.result, `${toolName} result`),
  };
}

function mcpToolJsonSchema(schema, pipeStrategy = 'input') {
  const objectSchema = normalizeObjectSchema(schema);
  if (!objectSchema) return {$schema: 'http://json-schema.org/draft-07/schema#', type: 'object', properties: {}};
  return toJsonSchemaCompat(objectSchema, {strictUnions: true, pipeStrategy});
}

function hostFileUploadInputSchema({description, contentMediaType}) {
  return {
    type: 'string',
    format: 'binary',
    contentMediaType,
    description,
  };
}

function renderBlenderGlbCatalogInputSchema() {
  return {
    type: 'object',
    properties: {
      idempotencyKey: {
        type: 'string',
        description: 'Stable idempotency key for this render request.',
      },
      renderId: {
        type: 'string',
        description: 'Optional caller-provided render id.',
      },
      glbFile: hostFileUploadInputSchema({
        contentMediaType: 'model/gltf-binary',
        description: 'Required top-level host-file upload containing a binary GLB model. Do not pass a path, URL, Base64 string, ref, or JSON descriptor.',
      }),
      scriptFile: hostFileUploadInputSchema({
        contentMediaType: 'text/x-python',
        description: 'Required top-level host-file upload containing the Blender Python render script. Do not pass a path, URL, Base64 string, ref, or JSON descriptor.',
      }),
      cache: {
        type: 'boolean',
        description: 'Use cached render artifacts when the backend cache key already exists. Defaults to true.',
      },
    },
    required: ['idempotencyKey', 'glbFile', 'scriptFile'],
    additionalProperties: false,
  };
}

function publishedToolInputSchema(name, schema, pipeStrategy = 'input') {
  if (name === 'render_blender_glb') return renderBlenderGlbCatalogInputSchema();
  return mcpToolJsonSchema(schema, pipeStrategy);
}

function installAuthenticatedToolsListHandler(server) {
  server.server.setRequestHandler(ListToolsRequestSchema, () => ({
    tools: Object.entries(server._registeredTools)
      .filter(([, tool]) => tool.enabled)
      .map(([name, tool]) => {
        const securitySchemes = (tool._meta && tool._meta.securitySchemes) || MCP_OAUTH_SECURITY_SCHEMES;
        const definition = {
          name,
          title: tool.title,
          description: tool.description,
          inputSchema: publishedToolInputSchema(name, tool.inputSchema, 'input'),
          securitySchemes,
          annotations: tool.annotations,
          execution: tool.execution,
          _meta: {...(tool._meta || {}), securitySchemes},
        };
        if (tool.outputSchema) definition.outputSchema = mcpToolJsonSchema(tool.outputSchema, 'output');
        return definition;
      }),
  }));
}

function oauthProtectedResourceMetadata() {
  return {
    resource: MCP_RESOURCE,
    resource_name: 'Home Center Drive Bridge',
    service_version: HOME_CENTER_MCP_SERVER_VERSION,
    registry_version: HOME_CENTER_REGISTRY_VERSION,
    connector_schema_revision: HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
    catalog_cache_key: HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
    direct_file_tools: HOME_CENTER_DIRECT_FILE_TOOLS,
    authorization_servers: [MCP_PUBLIC_BASE],
    scopes_supported: MCP_REQUIRED_SCOPES,
    bearer_methods_supported: ['header'],
    resource_documentation: `${MCP_PUBLIC_BASE}/`,
    metadata_aliases: [MCP_LEGACY_RESOURCE_METADATA, MCP_COMPAT_RESOURCE_METADATA],
  };
}

function oauthChallenge() {
  return `Bearer resource_metadata="${MCP_RESOURCE_METADATA}", scope="${MCP_REQUIRED_SCOPES.join(' ')}"`;
}

function authorizationServerMetadata() {
  return {
    issuer: MCP_PUBLIC_BASE,
    service_version: HOME_CENTER_MCP_SERVER_VERSION,
    registry_version: HOME_CENTER_REGISTRY_VERSION,
    connector_schema_revision: HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
    authorization_endpoint: `${MCP_PUBLIC_BASE}/oauth/authorize`,
    token_endpoint: `${MCP_PUBLIC_BASE}/oauth/token`,
    registration_endpoint: `${MCP_PUBLIC_BASE}/oauth/register`,
    response_types_supported: ['code'],
    grant_types_supported: ['authorization_code', 'refresh_token'],
    code_challenge_methods_supported: ['S256'],
    token_endpoint_auth_methods_supported: ['none'],
    scopes_supported: MCP_REQUIRED_SCOPES,
  };
}

function openIdConfigurationMetadata() {
  return {
    ...authorizationServerMetadata(),
    userinfo_endpoint: `${MCP_PUBLIC_BASE}/oauth/userinfo`,
    jwks_uri: `${MCP_PUBLIC_BASE}/oauth/jwks`,
    claims_supported: ['sub', 'email', 'email_verified'],
    subject_types_supported: ['public'],
    id_token_signing_alg_values_supported: ['RS256'],
  };
}

async function recordActionAudit(admin, user, operation, targetId, summary, requestId) {
  await admin.firestore().collection('actionAudit').add({
    timestamp: admin.firestore.FieldValue.serverTimestamp(),
    caller: safeText(user.email || 'unknown', 320),
    operation: safeText(operation, 120),
    targetFileOrFolderId: safeText(targetId, 220),
    summary: safeText(summary, 800),
    requestId: safeText(requestId, 160) || randomUUID(),
    authKind: safeText(user.authKind, 80) || 'unknown',
    source: 'home_center_mcp',
  });
}

function mcpCollection(admin, name) {
  return admin.firestore().collection(name);
}

function nowMs() {
  return Date.now();
}

function stableRequestId(value) {
  const id = safeText(value, 160);
  if (!id) {
    const err = new Error('requestId is required for executed writes. Use dryRun=true to preview without requestId.');
    err.status = 400;
    throw err;
  }
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(id)) {
    const err = new Error('requestId must be 6-160 chars using letters, numbers, dot, underscore, colon, or dash.');
    err.status = 400;
    throw err;
  }
  return id;
}

function safeOperationBatchId(value) {
  const id = safeText(value, 160);
  if (!id || !/^[A-Za-z0-9_.:-]{6,160}$/.test(id)) {
    const err = new Error('A valid operationBatchId is required. Use 6-160 chars: letters, numbers, dot, underscore, colon, or dash.');
    err.status = 400;
    throw err;
  }
  return id;
}

function safePlanId(value) {
  const id = safeText(value, 180);
  if (!/^[A-Za-z0-9_.:-]{8,180}$/.test(id)) {
    const err = new Error('A valid planId is required.');
    err.status = 400;
    throw err;
  }
  return id;
}

function ensureWriteAllowed(args = {}) {
  if (args.dryRun === true) return '';
  return stableRequestId(args.requestId);
}

function boolArg(value, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

function driveFields(extra = '') {
  const base = 'id,name,mimeType,modifiedTime,createdTime,webViewLink,parents,trashed,size,md5Checksum,shortcutDetails';
  return extra ? `${base},${extra}` : base;
}

function cleanDriveFile(file = {}, pathHint = '') {
  return {
    id: file.id || '',
    name: file.name || '',
    mimeType: file.mimeType || '',
    modifiedTime: file.modifiedTime || '',
    createdTime: file.createdTime || '',
    webViewLink: file.webViewLink || '',
    parents: file.parents || [],
    trashed: !!file.trashed,
    size: file.size || '',
    md5Checksum: file.md5Checksum || '',
    pathHint,
  };
}

async function getDriveMetadata(drive, fileId) {
  const result = await drive.files.get({fileId: safeDriveFileId(fileId), fields: driveFields(), supportsAllDrives: true});
  return cleanDriveFile(result.data || {});
}

async function listFolderChildren(drive, folderId, limit = 100, includeTrashed = false) {
  const cleanFolder = safeDriveFileId(folderId);
  const pageSize = Math.max(1, Math.min(1000, Math.floor(safeNumber(limit, 100)) || 100));
  const q = `'${driveQueryLiteral(cleanFolder, 220)}' in parents${includeTrashed ? '' : ' and trashed=false'}`;
  const result = await drive.files.list({
    q,
    pageSize,
    fields: `files(${driveFields()})`,
    orderBy: 'folder,name_natural',
    supportsAllDrives: true,
    includeItemsFromAllDrives: true,
  });
  return (result.data.files || []).map((file) => cleanDriveFile(file));
}

async function resolveParentNames(drive, parents = []) {
  const names = [];
  for (const parentId of parents.slice(0, 6)) {
    try {
      const parent = await getDriveMetadata(drive, parentId);
      names.push({id: parent.id, name: parent.name});
    } catch (_) {
      names.push({id: parentId, name: ''});
    }
  }
  return names;
}

async function auditWrite(admin, entry) {
  const requestId = stableRequestId(entry.requestId);
  const ref = mcpCollection(admin, 'driveBridgeAudit').doc(requestId);
  const existing = await ref.get();
  if (existing.exists && existing.data().status === 'success') {
    return {idempotent: true, audit: existing.data()};
  }
  const payload = {
    timestampMs: nowMs(),
    actor: safeText(entry.actor, 320),
    authKind: safeText(entry.authKind, 80),
    tool: safeText(entry.tool, 120),
    operation: safeText(entry.operation, 120),
    requestId,
    fileId: safeText(entry.fileId, 220),
    affectedFileIds: Array.isArray(entry.affectedFileIds) ? entry.affectedFileIds.map((v) => safeText(v, 220)).filter(Boolean) : [],
    oldMetadata: entry.oldMetadata || null,
    newMetadata: entry.newMetadata || null,
    oldParents: entry.oldParents || [],
    newParents: entry.newParents || [],
    reversible: !!entry.reversible,
    rollback: entry.rollback || null,
    callerNote: safeText(entry.callerNote, 800),
    dryRun: !!entry.dryRun,
    status: safeText(entry.status, 80) || 'success',
    providerSummary: safeText(entry.providerSummary, 1000),
    result: entry.result || null,
    inputSha256: safeText(entry.inputSha256, 128),
    error: safeText(entry.error, 1000),
  };
  await ref.set(payload, {merge: false});
  return {idempotent: false, audit: payload};
}

async function existingAudit(admin, requestId) {
  const id = safeText(requestId, 160);
  if (!id) return null;
  const snap = await mcpCollection(admin, 'driveBridgeAudit').doc(id).get();
  return snap.exists ? snap.data() : null;
}

async function existingActionAudit(admin, requestId) {
  const id = safeText(requestId, 160);
  if (!id) return null;
  const snap = await admin.firestore().collection('actionAudit').where('requestId', '==', id).limit(1).get();
  return snap.empty ? null : snap.docs[0].data();
}

function normalizeRecoveryOperation(operation = {}, index = 0) {
  const requestId = safeText(operation.requestId, 160);
  const operationId = safeText(operation.operationId, 160) || requestId || `operation-${index + 1}`;
  return {
    operationId: safeText(operationId, 160),
    toolName: safeText(operation.toolName || operation.tool, 120),
    requestId,
    targetId: safeText(operation.targetId || operation.fileId || operation.documentId || operation.spreadsheetId || operation.folderId, 220),
    targetName: safeText(operation.targetName || operation.name || operation.title, 240),
    summary: safeText(operation.summary || operation.intent || operation.callerNote, 1000),
  };
}

function recoveryAuditStatus(operation, driveAudit, actionAudit) {
  const audit = driveAudit || actionAudit || null;
  if (!audit) return {status: 'missing', audit: null};
  const status = safeText(audit.status, 80) || 'success';
  return {status: status === 'success' ? 'completed' : status, audit};
}

function summarizeRecoveryOperations(intendedOperations = [], auditByRequestId = {}) {
  const operations = intendedOperations.map((raw, index) => {
    const operation = normalizeRecoveryOperation(raw, index);
    const audits = operation.requestId ? auditByRequestId[operation.requestId] || {} : {};
    const classified = recoveryAuditStatus(operation, audits.driveAudit, audits.actionAudit);
    return {...operation, status: classified.status, audit: classified.audit};
  });
  const completed = operations.filter((operation) => operation.status === 'completed');
  const missing = operations.filter((operation) => operation.status === 'missing');
  const failed = operations.filter((operation) => !['completed', 'missing'].includes(operation.status));
  return {operations, completed, missing, failed, nextOperation: missing[0] || null, complete: missing.length === 0 && failed.length === 0};
}

function mcpToolCallFields(req) {
  const body = req && req.body && typeof req.body === 'object' ? req.body : {};
  const params = body.params && typeof body.params === 'object' ? body.params : {};
  const args = params.arguments && typeof params.arguments === 'object' ? params.arguments : {};
  const toolName = body.method === 'tools/call' ? safeText(params.name, 120) : '';
  const targetLabel = safeText(args.name || args.title || args.newName || args.heading || args.callerNote, 240);
  const targetId = safeText(args.fileId || args.documentId || args.spreadsheetId || args.folderId || args.targetFolderId || args.parentFolderId || args.planId, 220);
  return {
    mcpMethod: safeText(body.method, 120),
    toolName,
    requestId: safeText(args.requestId, 160),
    operationBatchId: safeText(args.operationBatchId, 160),
    targetId,
    targetLabel,
  };
}

function dryRunResult(operation, fileId, oldMetadata, proposed, args = {}) {
  return {
    dryRun: true,
    operation,
    fileId: fileId || '',
    oldMetadata: oldMetadata || null,
    proposed,
    callerNote: safeText(args.callerNote, 800),
    reversible: true,
  };
}

async function exportIndexableText(drive, file) {
  const mime = file.mimeType || '';
  try {
    if (mime === 'application/vnd.google-apps.document') {
      const exported = await drive.files.export({fileId: file.id, mimeType: 'text/plain'}, {responseType: 'text'});
      return String(exported.data || '').slice(0, 200000);
    }
    if (mime.startsWith('text/') || mime === 'application/json' || mime === 'text/markdown') {
      const downloaded = await drive.files.get({fileId: file.id, alt: 'media', supportsAllDrives: true}, {responseType: 'text'});
      return String(downloaded.data || '').slice(0, 200000);
    }
  } catch (_) {
    return '';
  }
  return '';
}

function contentHash(text) {
  return createHash('sha256').update(String(text || '')).digest('hex');
}

async function indexOneFile(admin, drive, file) {
  const metadata = file.id ? file : await getDriveMetadata(drive, file);
  const ref = mcpCollection(admin, 'driveBridgeIndex').doc(metadata.id);
  const previous = await ref.get();
  const prev = previous.exists ? previous.data() : null;
  const unchanged = prev && prev.modifiedTime === metadata.modifiedTime && String(prev.size || '') === String(metadata.size || '') && prev.md5Checksum === metadata.md5Checksum;
  if (unchanged) return {fileId: metadata.id, skipped: true, updated: false, metadata};
  const text = await exportIndexableText(drive, metadata);
  const payload = {
    fileId: metadata.id,
    name: metadata.name,
    mimeType: metadata.mimeType,
    modifiedTime: metadata.modifiedTime,
    createdTime: metadata.createdTime,
    parents: metadata.parents || [],
    webViewLink: metadata.webViewLink || '',
    trashed: !!metadata.trashed,
    size: metadata.size || '',
    md5Checksum: metadata.md5Checksum || '',
    textPreview: text.slice(0, 12000),
    textHash: contentHash(text),
    indexedAtMs: nowMs(),
  };
  await ref.set(payload, {merge: false});
  return {fileId: metadata.id, skipped: false, updated: true, metadata: payload};
}


function simulationId(prefix, value) {
  const supplied = safeText(value, 160);
  if (supplied) {
    if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(supplied)) throw Object.assign(new Error(`${prefix} id must be 6-160 chars using letters, numbers, dot, underscore, colon, or dash.`), {status: 400});
    return supplied;
  }
  return `${prefix}-${randomUUID()}`;
}

function simulationSequence(value) {
  const sequence = Math.floor(safeNumber(value, -1));
  if (sequence < 0 || sequence > 1000000) throw Object.assign(new Error('sequence must be an integer from 0 to 1000000.'), {status: 400});
  return sequence;
}

function simulationConfidence(value) {
  const confidence = safeText(value, 40).toLowerCase();
  return ['high', 'medium', 'low', 'unknown'].includes(confidence) ? confidence : 'unknown';
}

function simulationTrustLevel(value) {
  const trust = safeText(value, 80).toLowerCase();
  return trust || 'unspecified';
}

function simulationRecordTypeFromHeading(heading, metadata = {}) {
  const explicit = safeText(metadata.type || metadata.record_type || metadata.recordType, 80).toLowerCase();
  if (explicit) return explicit.replace(/[^a-z0-9_.:-]/g, '_').slice(0, 80);
  const h = safeText(heading, 240).toLowerCase();
  if (/^(entity|character|person|location|organization|object)\b/.test(h)) return 'entity';
  if (/^(relationship|relation)\b/.test(h)) return 'relationship';
  if (/^(event|chronology|timeline|historical rail)\b/.test(h)) return 'event';
  if (/^(rule|constraint|canon|doctrine|prohibited invention)\b/.test(h)) return 'rule';
  if (/^(conflict|contradictory evidence|contradiction)\b/.test(h)) return 'contradiction';
  if (/^(unresolved|unknown|question|confidence note)\b/.test(h)) return 'uncertainty';
  if (/^(source|excerpt|summary)\b/.test(h)) return 'source_note';
  if (/^(seed|simulation seed|prior outcome)\b/.test(h)) return 'simulation_seed';
  return 'passage';
}

function parseMetadataLines(lines) {
  const metadata = {};
  let consumed = 0;
  for (const line of lines) {
    const match = String(line || '').match(/^([A-Za-z][A-Za-z0-9_. -]{0,80}):\s*(.+)$/);
    if (!match) break;
    const key = match[1].trim().toLowerCase().replace(/[ -]+/g, '_');
    metadata[key] = match[2].trim();
    consumed += 1;
  }
  return {metadata, consumed};
}

function extractSourceRefs(lines) {
  const refs = [];
  let inSources = false;
  for (const raw of lines) {
    const line = String(raw || '').trim();
    if (/^sources?:\s*$/i.test(line)) {
      inSources = true;
      continue;
    }
    if (inSources && /^-\s+/.test(line)) {
      refs.push(line.replace(/^-\s+/, '').slice(0, 800));
      continue;
    }
    if (inSources && line && !/^\s/.test(raw || '')) inSources = false;
  }
  const inline = lines.join('\n').match(/\[(drive|github|url|doc|source):([^\]]+)\]/gi) || [];
  for (const item of inline) refs.push(item.slice(1, -1));
  return Array.from(new Set(refs)).slice(0, 40);
}

function parseSimulationReference(content) {
  const text = boundedText(content, 750000);
  const lines = text.split(/\r?\n/);
  const sections = [];
  const stack = [];
  let current = {heading: 'Root', level: 0, startLine: 1, lines: []};
  const flush = (endLine) => {
    const body = current.lines.join('\n').trim();
    if (!body && current.heading === 'Root') return;
    const parsed = parseMetadataLines(current.lines.map((line) => String(line || '').trim()).filter(Boolean));
    const sectionPath = stack.slice(0, current.level ? current.level - 1 : 0).concat(current.heading).filter(Boolean).join(' > ');
    sections.push({
      heading: current.heading,
      level: current.level,
      sectionPath: sectionPath || current.heading,
      startLine: current.startLine,
      endLine,
      metadata: parsed.metadata,
      body,
      sources: extractSourceRefs(current.lines),
    });
  };
  lines.forEach((line, index) => {
    const match = line.match(/^(#{1,6})\s+(.+)$/);
    if (match) {
      flush(index);
      const level = match[1].length;
      stack[level - 1] = match[2].trim();
      stack.length = level;
      current = {heading: match[2].trim(), level, startLine: index + 1, lines: []};
    } else {
      current.lines.push(line);
    }
  });
  flush(lines.length);
  if (!sections.length && text.trim()) {
    sections.push({heading: 'Reference', level: 1, sectionPath: 'Reference', startLine: 1, endLine: lines.length, metadata: {}, body: text.trim(), sources: extractSourceRefs(lines)});
  }
  return sections;
}

function tokenizeSimulationText(text, maxTerms = 80) {
  const stop = new Set(['the', 'and', 'for', 'that', 'with', 'from', 'this', 'into', 'about', 'known', 'there', 'their', 'shall', 'must', 'have', 'been', 'were', 'will', 'would', 'could', 'should']);
  const counts = new Map();
  String(text || '').toLowerCase().replace(/[^a-z0-9_ -]/g, ' ').split(/\s+/).forEach((term) => {
    if (term.length < 3 || stop.has(term)) return;
    counts.set(term, (counts.get(term) || 0) + 1);
  });
  return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, maxTerms).map(([term, count]) => ({term, count}));
}

function simulationSourceRefKey(ref) {
  return contentHash(String(ref || '')).slice(0, 32);
}

function normalizeSimulationSourceRef(ref) {
  const text = safeText(ref, 800);
  const match = text.match(/^([A-Za-z0-9_.-]+):(.+)$/);
  return {raw: text, sourceType: match ? match[1].toLowerCase() : 'reference', externalId: match ? match[2].trim().slice(0, 500) : text};
}

function simulationOperationRegistry() {
  return {
    version: '2026-07-10.simulation-frame-mcp-v1',
    invocationTool: 'simulation_operation',
    cachePolicy: 'Use simulation_operation plus this registry for Simulation features so ChatGPT does not need a connector reinstall for each new simulation operation.',
    operations: {
      simulation_project_create: {summary: 'Create or idempotently return a simulation project.', write: true, requiresRequestId: true, input: {title: 'string', description: 'optional string', doctrine: 'optional string', projectId: 'optional stable id', requestId: 'string'}},
      simulation_source_register: {summary: 'Attach a source reference to a simulation project without copying all content.', write: true, requiresRequestId: true, input: {projectId: 'string', sourceType: 'string', externalId: 'optional string', location: 'optional string', title: 'optional string', trustLevel: 'optional string', requestId: 'string'}},
      simulation_reference_begin: {summary: 'Begin a resumable agent-assembled reference compilation.', write: true, requiresRequestId: true, input: {projectId: 'string', title: 'optional string', format: 'markdown|text|json', requestId: 'string'}},
      simulation_reference_append: {summary: 'Append one idempotent reference chunk by sequence and hash.', write: true, requiresRequestId: true, input: {compilationId: 'string', sequence: 'number', content: 'string', requestId: 'string'}},
      simulation_reference_finalize: {summary: 'Finalize a reference compilation and freeze its content hash.', write: true, requiresRequestId: true, input: {compilationId: 'string', requestId: 'string'}},
      build_simulation_frame: {summary: 'Compile a finalized reference into an immutable indexed simulation frame.', write: true, requiresRequestId: true, input: {projectId: 'string', compilationId: 'string', activate: 'optional boolean', requestId: 'string'}},
      simulation_frame_status: {summary: 'Read project, compilation, or frame compilation status.', write: false, input: {projectId: 'optional string', compilationId: 'optional string', frameId: 'optional string'}},
      simulation_frame_query: {summary: 'Retrieve evidence-backed frame records by lexical query and structured filters.', write: false, input: {projectId: 'optional string', frameId: 'optional string', query: 'string', recordTypes: 'optional string[]', limit: 'optional number'}},
      simulation_frame_get: {summary: 'Read a frame manifest and a bounded record sample.', write: false, input: {frameId: 'string', limit: 'optional number'}},
      simulation_frame_versions: {summary: 'List immutable frame versions for a project.', write: false, input: {projectId: 'string'}},
      simulation_context_packet: {summary: 'Package query results into a bounded agent-ready context packet with provenance and invention guards.', write: false, input: {projectId: 'optional string', frameId: 'optional string', query: 'string', maxChars: 'optional number'}},
      run_simulation_frame: {summary: 'Run a deterministic frame-grounded simulation handoff: retrieve context, conflicts, unknowns, and next-step constraints for an agent continuation.', write: false, input: {projectId: 'optional string', frameId: 'optional string', prompt: 'string', maxChars: 'optional number'}},
    },
  };
}

function supportedSimulationOperationTypes() {
  return Object.keys(simulationOperationRegistry().operations);
}

async function existingSimulationAudit(admin, requestId) {
  const id = safeText(requestId, 160);
  if (!id) return null;
  const snap = await mcpCollection(admin, 'simulationAudit').doc(id).get();
  return snap.exists ? snap.data() : null;
}

async function simulationAuditWrite(admin, entry) {
  const requestId = stableRequestId(entry.requestId);
  const ref = mcpCollection(admin, 'simulationAudit').doc(requestId);
  const existing = await ref.get();
  if (existing.exists && existing.data().status === 'success') return {idempotent: true, audit: existing.data()};
  const payload = {
    timestampMs: nowMs(),
    actor: safeText(entry.actor, 320),
    authKind: safeText(entry.authKind, 80),
    tool: 'simulation_operation',
    operation: safeText(entry.operation, 120),
    requestId,
    projectId: safeText(entry.projectId, 160),
    compilationId: safeText(entry.compilationId, 160),
    frameId: safeText(entry.frameId, 160),
    contentHash: safeText(entry.contentHash, 160),
    status: safeText(entry.status, 80) || 'success',
    warnings: Array.isArray(entry.warnings) ? entry.warnings.map((w) => safeText(w, 500)).filter(Boolean).slice(0, 50) : [],
    outcome: entry.outcome || null,
    error: safeText(entry.error, 1000),
  };
  await ref.set(payload, {merge: false});
  return {idempotent: false, audit: payload};
}

async function requireSimulationProject(admin, projectId) {
  const id = simulationId('sim-project', projectId);
  const snap = await mcpCollection(admin, 'simulationProjects').doc(id).get();
  if (!snap.exists) throw Object.assign(new Error('simulation project not found.'), {status: 404});
  return snap.data() || {};
}

async function readCompilationContent(admin, compilationId) {
  const snap = await mcpCollection(admin, 'simulationReferenceCompilations').doc(simulationId('sim-compilation', compilationId)).get();
  if (!snap.exists) throw Object.assign(new Error('reference compilation not found.'), {status: 404});
  const compilation = snap.data() || {};
  const chunkSnap = await mcpCollection(admin, 'simulationReferenceChunks').where('compilationId', '==', compilation.compilationId).get();
  const chunks = chunkSnap.docs.map((doc) => doc.data() || {}).sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
  const content = chunks.map((chunk) => chunk.content || '').join('');
  return {compilation, chunks, content, contentHash: contentHash(content)};
}

async function activeSimulationFrameId(admin, projectId) {
  const project = await requireSimulationProject(admin, projectId);
  if (!project.activeFrameId) throw Object.assign(new Error('project has no active simulation frame.'), {status: 404});
  return project.activeFrameId;
}

async function resolveSimulationFrameId(admin, args = {}) {
  const frameId = safeText(args.frameId, 160);
  if (frameId) return simulationId('sim-frame', frameId);
  const projectId = safeText(args.projectId, 160);
  if (!projectId) throw Object.assign(new Error('frameId or projectId is required.'), {status: 400});
  return activeSimulationFrameId(admin, projectId);
}

async function simulationProjectCreate({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const existing = await existingSimulationAudit(admin, requestId);
  if (existing && existing.status === 'success') return {idempotent: true, audit: existing};
  const title = safeText(args.title, 240);
  if (!title) throw Object.assign(new Error('title is required.'), {status: 400});
  const projectId = simulationId('sim-project', args.projectId);
  const now = nowMs();
  const ref = mcpCollection(admin, 'simulationProjects').doc(projectId);
  const snap = await ref.get();
  const payload = {
    projectId,
    title,
    description: safeText(args.description, 4000),
    doctrine: safeText(args.doctrine, 12000),
    sourceRoots: Array.isArray(args.sourceRoots) ? args.sourceRoots.map((v) => safeText(v, 1000)).filter(Boolean).slice(0, 100) : [],
    activeFrameId: snap.exists ? safeText(snap.data().activeFrameId, 160) : '',
    status: safeText(args.status, 80) || 'active',
    createdAtMs: snap.exists ? snap.data().createdAtMs || now : now,
    updatedAtMs: now,
  };
  await ref.set(payload, {merge: false});
  const audit = await simulationAuditWrite(admin, {actor: user.email, authKind: user.authKind, operation: 'simulation_project_create', requestId, projectId, outcome: {projectId, title}});
  return {project: payload, audit: audit.audit};
}

async function simulationSourceRegister({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const existing = await existingSimulationAudit(admin, requestId);
  if (existing && existing.status === 'success') return {idempotent: true, audit: existing};
  const projectId = simulationId('sim-project', args.projectId);
  await requireSimulationProject(admin, projectId);
  const sourceType = safeText(args.sourceType || args.type, 80).toLowerCase();
  if (!sourceType) throw Object.assign(new Error('sourceType is required.'), {status: 400});
  const sourceId = simulationId('sim-source', args.sourceId);
  const payload = {
    sourceId,
    projectId,
    sourceType,
    externalId: safeText(args.externalId, 1000),
    location: safeText(args.location || args.url, 2000),
    title: safeText(args.title, 500),
    contentHash: safeText(args.contentHash, 160),
    sourceOwner: safeText(args.sourceOwner, 320),
    sourceModifiedAt: safeText(args.sourceModifiedAt, 120),
    retrievedAtMs: nowMs(),
    trustLevel: simulationTrustLevel(args.trustLevel || args.trustClassification),
    userNotes: safeText(args.userNotes || args.notes, 4000),
    ingestionStatus: 'registered',
    metadata: args.metadata && typeof args.metadata === 'object' && !Array.isArray(args.metadata) ? args.metadata : {},
  };
  await mcpCollection(admin, 'simulationSources').doc(sourceId).set(payload, {merge: false});
  const audit = await simulationAuditWrite(admin, {actor: user.email, authKind: user.authKind, operation: 'simulation_source_register', requestId, projectId, contentHash: payload.contentHash, outcome: {sourceId, sourceType}});
  return {source: payload, audit: audit.audit};
}

async function simulationReferenceBegin({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const existing = await existingSimulationAudit(admin, requestId);
  if (existing && existing.status === 'success') return {idempotent: true, audit: existing};
  const projectId = simulationId('sim-project', args.projectId);
  await requireSimulationProject(admin, projectId);
  const compilationId = simulationId('sim-compilation', args.compilationId);
  const payload = {
    compilationId,
    projectId,
    status: 'open',
    title: safeText(args.title, 500) || 'Agent Reference Compilation',
    format: safeText(args.format, 80) || 'markdown',
    contentHash: '',
    createdBy: user.email || '',
    createdAtMs: nowMs(),
    finalizedAtMs: 0,
    chunkCount: 0,
    totalChars: 0,
  };
  await mcpCollection(admin, 'simulationReferenceCompilations').doc(compilationId).set(payload, {merge: false});
  const audit = await simulationAuditWrite(admin, {actor: user.email, authKind: user.authKind, operation: 'simulation_reference_begin', requestId, projectId, compilationId, outcome: {compilationId}});
  return {compilation: payload, audit: audit.audit};
}

async function simulationReferenceAppend({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const compilationId = simulationId('sim-compilation', args.compilationId);
  const sequence = simulationSequence(args.sequence);
  const content = boundedText(args.content, 250000);
  if (!content) throw Object.assign(new Error('content is required.'), {status: 400});
  const hash = contentHash(content);
  const compRef = mcpCollection(admin, 'simulationReferenceCompilations').doc(compilationId);
  const compSnap = await compRef.get();
  if (!compSnap.exists) throw Object.assign(new Error('reference compilation not found.'), {status: 404});
  const compilation = compSnap.data() || {};
  if (compilation.status !== 'open') throw Object.assign(new Error('reference compilation is not open for appends.'), {status: 400});
  const chunkId = `${compilationId}:chunk:${sequence}`;
  const chunkRef = mcpCollection(admin, 'simulationReferenceChunks').doc(chunkId);
  const existingChunk = await chunkRef.get();
  if (existingChunk.exists) {
    const old = existingChunk.data() || {};
    if (old.contentHash !== hash) throw Object.assign(new Error('chunk sequence already exists with a different content hash.'), {status: 409});
    const audit = await simulationAuditWrite(admin, {actor: user.email, authKind: user.authKind, operation: 'simulation_reference_append', requestId, projectId: compilation.projectId, compilationId, contentHash: hash, outcome: {chunkId, idempotentChunk: true}});
    return {chunk: old, idempotent: true, audit: audit.audit};
  }
  const payload = {chunkId, compilationId, projectId: compilation.projectId || '', sequence, content, contentHash: hash, createdAtMs: nowMs(), charCount: content.length};
  await chunkRef.set(payload, {merge: false});
  await compRef.set({chunkCount: (compilation.chunkCount || 0) + 1, totalChars: (compilation.totalChars || 0) + content.length, updatedAtMs: nowMs()}, {merge: true});
  const audit = await simulationAuditWrite(admin, {actor: user.email, authKind: user.authKind, operation: 'simulation_reference_append', requestId, projectId: compilation.projectId, compilationId, contentHash: hash, outcome: {chunkId, sequence}});
  return {chunk: {...payload, content: ''}, audit: audit.audit};
}

async function simulationReferenceFinalize({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const existing = await existingSimulationAudit(admin, requestId);
  if (existing && existing.status === 'success') return {idempotent: true, audit: existing};
  const compilationId = simulationId('sim-compilation', args.compilationId);
  const {compilation, chunks, contentHash: hash} = await readCompilationContent(admin, compilationId);
  if (!chunks.length) throw Object.assign(new Error('cannot finalize an empty reference compilation.'), {status: 400});
  const payload = {status: 'finalized', contentHash: hash, finalizedAtMs: nowMs(), chunkCount: chunks.length, totalChars: chunks.reduce((sum, c) => sum + safeText(c.content, 250000).length, 0)};
  await mcpCollection(admin, 'simulationReferenceCompilations').doc(compilationId).set(payload, {merge: true});
  const audit = await simulationAuditWrite(admin, {actor: user.email, authKind: user.authKind, operation: 'simulation_reference_finalize', requestId, projectId: compilation.projectId, compilationId, contentHash: hash, outcome: payload});
  return {compilation: {...compilation, ...payload}, audit: audit.audit};
}

async function nextSimulationFrameVersion(admin, projectId) {
  const snap = await mcpCollection(admin, 'simulationFrames').where('projectId', '==', projectId).get();
  let max = 0;
  snap.docs.forEach((doc) => { max = Math.max(max, Math.floor(safeNumber((doc.data() || {}).version, 0))); });
  return max + 1;
}

async function buildSimulationFrame({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const existing = await existingSimulationAudit(admin, requestId);
  if (existing && existing.status === 'success') return {idempotent: true, audit: existing};
  const projectId = simulationId('sim-project', args.projectId);
  await requireSimulationProject(admin, projectId);
  const compilationId = simulationId('sim-compilation', args.compilationId);
  const {compilation, content, contentHash: hash} = await readCompilationContent(admin, compilationId);
  if (compilation.status !== 'finalized') throw Object.assign(new Error('reference compilation must be finalized before building a frame.'), {status: 400});
  if (compilation.projectId !== projectId) throw Object.assign(new Error('compilation does not belong to projectId.'), {status: 400});
  const frameId = simulationId('sim-frame', args.frameId);
  const version = await nextSimulationFrameVersion(admin, projectId);
  const sections = parseSimulationReference(content);
  const sourceRefs = new Map();
  const records = [];
  const conflicts = [];
  const claimIndex = new Map();
  sections.forEach((section, index) => {
    const canonicalKey = safeText(section.metadata.id || section.metadata.canonical_key || section.heading.toLowerCase().replace(/[^a-z0-9]+/g, '.').replace(/^\.|\.$/g, ''), 160) || `section.${index + 1}`;
    const recordType = simulationRecordTypeFromHeading(section.heading, section.metadata);
    const recordId = `${frameId}:record:${index + 1}`;
    const record = {
      recordId,
      frameId,
      projectId,
      recordType,
      canonicalKey,
      title: safeText(section.heading, 500),
      body: boundedText(section.body, 60000),
      confidence: simulationConfidence(section.metadata.confidence),
      structuredData: section.metadata,
      sectionPath: safeText(section.sectionPath, 1000),
      sourceSpan: {startLine: section.startLine, endLine: section.endLine},
      sourceRefs: section.sources,
      createdAtMs: nowMs(),
    };
    records.push(record);
    section.sources.forEach((ref) => sourceRefs.set(simulationSourceRefKey(ref), normalizeSimulationSourceRef(ref)));
    Object.entries(section.metadata || {}).forEach(([field, value]) => {
      if (['id', 'type', 'confidence', 'canonical_key'].includes(field)) return;
      const key = `${canonicalKey}:${field}`;
      const arr = claimIndex.get(key) || [];
      arr.push({recordId, value: String(value), sourceRefs: section.sources, sectionPath: section.sectionPath});
      claimIndex.set(key, arr);
    });
  });
  for (const [key, claims] of claimIndex.entries()) {
    const values = Array.from(new Set(claims.map((claim) => claim.value)));
    if (values.length > 1) {
      const [subjectKey, fieldKey] = key.split(':');
      conflicts.push({conflictId: `${frameId}:conflict:${conflicts.length + 1}`, frameId, projectId, subjectKey, fieldKey, claims, resolutionStatus: 'unresolved', resolvedValue: '', resolutionNote: '', createdAtMs: nowMs()});
    }
  }
  const warnings = [];
  if (!records.length) warnings.push('No frame records were parsed from the reference.');
  const batch = admin.firestore().batch();
  sourceRefs.forEach((source, key) => {
    batch.set(mcpCollection(admin, 'simulationSources').doc(`inline-${key}`), {sourceId: `inline-${key}`, projectId, sourceType: source.sourceType, externalId: source.externalId, location: source.raw, title: source.raw, trustLevel: 'compiled_reference', ingestionStatus: 'referenced', retrievedAtMs: nowMs(), metadata: {inlineReference: true}}, {merge: true});
  });
  records.forEach((record) => {
    batch.set(mcpCollection(admin, 'simulationFrameRecords').doc(record.recordId), record, {merge: false});
    record.sourceRefs.forEach((ref) => {
      const key = simulationSourceRefKey(ref);
      batch.set(mcpCollection(admin, 'simulationFrameRecordSources').doc(`${record.recordId}:source:${key}`), {recordId: record.recordId, frameId, projectId, sourceId: `inline-${key}`, compilationId, citationData: normalizeSimulationSourceRef(ref), sectionPath: record.sectionPath, sourceSpan: record.sourceSpan}, {merge: false});
    });
    tokenizeSimulationText(`${record.title}\n${record.body}\n${record.canonicalKey}`, 50).forEach(({term, count}) => {
      batch.set(mcpCollection(admin, 'simulationFrameTerms').doc(`${frameId}:term:${contentHash(term + record.recordId).slice(0, 32)}`), {frameId, projectId, recordId: record.recordId, term, count}, {merge: false});
    });
  });
  conflicts.forEach((conflict) => batch.set(mcpCollection(admin, 'simulationFrameConflicts').doc(conflict.conflictId), conflict, {merge: false}));
  const manifest = {frameId, projectId, version, sourceCompilationIds: [compilationId], sourceCount: sourceRefs.size, compilationHash: hash, compilerVersion: simulationOperationRegistry().version, recordCountsByType: records.reduce((acc, r) => { acc[r.recordType] = (acc[r.recordType] || 0) + 1; return acc; }, {}), unresolvedConflictCount: conflicts.length, unresolvedIdentityCount: 0, warnings, compileTimestampMs: nowMs(), active: !!args.activate};
  const frame = {frameId, projectId, version, compilationHash: hash, compilerVersion: simulationOperationRegistry().version, manifest, createdAtMs: nowMs(), activatedAtMs: args.activate ? nowMs() : 0, status: 'compiled'};
  batch.set(mcpCollection(admin, 'simulationFrames').doc(frameId), frame, {merge: false});
  if (args.activate === true) batch.set(mcpCollection(admin, 'simulationProjects').doc(projectId), {activeFrameId: frameId, updatedAtMs: nowMs()}, {merge: true});
  await batch.commit();
  const audit = await simulationAuditWrite(admin, {actor: user.email, authKind: user.authKind, operation: 'build_simulation_frame', requestId, projectId, compilationId, frameId, contentHash: hash, warnings, outcome: {frameId, version, recordCount: records.length, conflictCount: conflicts.length}});
  return {frame, manifest, audit: audit.audit};
}

async function simulationFrameStatus({admin, args = {}}) {
  const result = {ok: true};
  const projectId = safeText(args.projectId, 160);
  const compilationId = safeText(args.compilationId, 160);
  const frameId = safeText(args.frameId, 160);
  if (projectId) {
    const snap = await mcpCollection(admin, 'simulationProjects').doc(simulationId('sim-project', projectId)).get();
    result.project = snap.exists ? snap.data() : null;
  }
  if (compilationId) {
    const snap = await mcpCollection(admin, 'simulationReferenceCompilations').doc(simulationId('sim-compilation', compilationId)).get();
    result.compilation = snap.exists ? snap.data() : null;
  }
  if (frameId) {
    const snap = await mcpCollection(admin, 'simulationFrames').doc(simulationId('sim-frame', frameId)).get();
    result.frame = snap.exists ? snap.data() : null;
  }
  return result;
}

async function querySimulationFrame({admin, args = {}}) {
  const frameId = await resolveSimulationFrameId(admin, args);
  const frameSnap = await mcpCollection(admin, 'simulationFrames').doc(frameId).get();
  if (!frameSnap.exists) throw Object.assign(new Error('simulation frame not found.'), {status: 404});
  const frame = frameSnap.data() || {};
  const query = safeText(args.query || args.prompt, 2000).toLowerCase();
  const queryTerms = tokenizeSimulationText(query, 20).map((item) => item.term);
  const allowedTypes = Array.isArray(args.recordTypes) ? new Set(args.recordTypes.map((v) => safeText(v, 80)).filter(Boolean)) : null;
  const limit = chatGptLimit(args.limit, 12, 50);
  const recordSnap = await mcpCollection(admin, 'simulationFrameRecords').where('frameId', '==', frameId).get();
  let records = recordSnap.docs.map((doc) => doc.data() || {});
  if (allowedTypes && allowedTypes.size) records = records.filter((record) => allowedTypes.has(record.recordType));
  records = records.map((record) => {
    const haystack = `${record.title || ''}\n${record.body || ''}\n${record.canonicalKey || ''}`.toLowerCase();
    const matchedTerms = queryTerms.filter((term) => haystack.includes(term));
    const score = matchedTerms.length * 10 + (query && haystack.includes(query) ? 25 : 0) + (record.recordType === 'rule' ? 1 : 0);
    return {...record, matchedTerms, score};
  }).filter((record) => !queryTerms.length || record.score > 0).sort((a, b) => b.score - a.score).slice(0, limit);
  const conflictSnap = await mcpCollection(admin, 'simulationFrameConflicts').where('frameId', '==', frameId).get();
  const conflicts = conflictSnap.docs.map((doc) => doc.data() || {}).filter((conflict) => records.some((record) => record.canonicalKey === conflict.subjectKey || record.recordId === conflict.subjectRecordId)).slice(0, 20);
  return {frameId, projectId: frame.projectId || '', version: frame.version || 0, query, count: records.length, records, conflicts, retrievalExplanation: {matchedTerms: queryTerms, method: 'lexical_firestore_scan_v1'}};
}

async function simulationFrameGet({admin, args = {}}) {
  const frameId = simulationId('sim-frame', args.frameId);
  const frameSnap = await mcpCollection(admin, 'simulationFrames').doc(frameId).get();
  if (!frameSnap.exists) throw Object.assign(new Error('simulation frame not found.'), {status: 404});
  const recordsSnap = await mcpCollection(admin, 'simulationFrameRecords').where('frameId', '==', frameId).get();
  const limit = chatGptLimit(args.limit, 20, 100);
  return {frame: frameSnap.data(), records: recordsSnap.docs.map((doc) => doc.data()).slice(0, limit)};
}

async function simulationFrameVersions({admin, args = {}}) {
  const projectId = simulationId('sim-project', args.projectId);
  const snap = await mcpCollection(admin, 'simulationFrames').where('projectId', '==', projectId).get();
  const frames = snap.docs.map((doc) => doc.data() || {}).sort((a, b) => (a.version || 0) - (b.version || 0));
  return {projectId, count: frames.length, frames: frames.map((frame) => ({frameId: frame.frameId, version: frame.version, status: frame.status, manifest: frame.manifest, createdAtMs: frame.createdAtMs, activatedAtMs: frame.activatedAtMs}))};
}

async function simulationContextPacket({admin, args = {}}) {
  const maxChars = Math.max(1000, Math.min(60000, Math.floor(safeNumber(args.maxChars, 12000)) || 12000));
  const query = await querySimulationFrame({admin, args: {...args, limit: args.limit || 20}});
  let body = `# Simulation Context Packet\n\nproject_id: ${query.projectId}\nframe_id: ${query.frameId}\nframe_version: ${query.version}\nquery: ${query.query}\n\n## Invention Guard\nUse only cited frame evidence for canon. Preserve conflicts and unknowns; do not silently reconcile contradictions.\n\n`;
  const groups = {canon: [], entities: [], timeline: [], doctrine: [], other: []};
  query.records.forEach((record) => {
    if (record.recordType === 'rule') groups.doctrine.push(record);
    else if (record.recordType === 'entity') groups.entities.push(record);
    else if (record.recordType === 'event') groups.timeline.push(record);
    else groups.other.push(record);
  });
  const appendGroup = (title, records) => {
    if (!records.length || body.length >= maxChars) return;
    body += `## ${title}\n`;
    for (const record of records) {
      if (body.length >= maxChars) break;
      body += `- ${record.title} (${record.recordType}, ${record.confidence}, ${record.sectionPath})\n  ${safeText(record.body, 1200).replace(/\n/g, ' ')}\n  sources: ${(record.sourceRefs || []).join('; ') || 'compiled reference'}\n`;
    }
    body += '\n';
  };
  appendGroup('Doctrine And Constraints', groups.doctrine);
  appendGroup('Entities', groups.entities);
  appendGroup('Timeline', groups.timeline);
  appendGroup('Other Evidence', groups.other);
  if (query.conflicts.length && body.length < maxChars) {
    body += '## Conflicts\n';
    query.conflicts.forEach((conflict) => { body += `- ${conflict.subjectKey}.${conflict.fieldKey}: unresolved (${(conflict.claims || []).map((c) => c.value).join(' vs ')})\n`; });
  }
  return {...query, maxChars, packet: body.slice(0, maxChars)};
}

async function runSimulationFrame({admin, args = {}}) {
  const prompt = safeText(args.prompt || args.query, 4000);
  if (!prompt) throw Object.assign(new Error('prompt is required.'), {status: 400});
  const packet = await simulationContextPacket({admin, args: {...args, query: prompt, maxChars: args.maxChars || 16000}});
  return {
    runMode: 'deterministic_context_handoff_v1',
    frameId: packet.frameId,
    frameVersion: packet.version,
    prompt,
    contextPacket: packet.packet,
    conflictWarnings: packet.conflicts || [],
    nextAgentInstruction: 'Continue the simulation using the context packet only. If evidence is missing, state the unknown instead of inventing canon. Preserve unresolved conflicts unless the user explicitly resolves them.',
  };
}

async function simulationOperationRunOperation({admin, user, args = {}}) {
  const operation = safeText(args.operation || args.type || args.toolName, 120);
  if (!operation) throw Object.assign(new Error('operation is required.'), {status: 400});
  const registry = simulationOperationRegistry();
  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported simulation_operation operation: ' + operation), {status: 400});
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {...args};
  delete operationArgs.operation;
  delete operationArgs.type;
  delete operationArgs.toolName;
  delete operationArgs.args;
  if (operation === 'simulation_project_create') return {operation, registryVersion: registry.version, result: await simulationProjectCreate({admin, user, args: operationArgs})};
  if (operation === 'simulation_source_register') return {operation, registryVersion: registry.version, result: await simulationSourceRegister({admin, user, args: operationArgs})};
  if (operation === 'simulation_reference_begin') return {operation, registryVersion: registry.version, result: await simulationReferenceBegin({admin, user, args: operationArgs})};
  if (operation === 'simulation_reference_append') return {operation, registryVersion: registry.version, result: await simulationReferenceAppend({admin, user, args: operationArgs})};
  if (operation === 'simulation_reference_finalize') return {operation, registryVersion: registry.version, result: await simulationReferenceFinalize({admin, user, args: operationArgs})};
  if (operation === 'build_simulation_frame') return {operation, registryVersion: registry.version, result: await buildSimulationFrame({admin, user, args: operationArgs})};
  if (operation === 'simulation_frame_status') return {operation, registryVersion: registry.version, result: await simulationFrameStatus({admin, args: operationArgs})};
  if (operation === 'simulation_frame_query') return {operation, registryVersion: registry.version, result: await querySimulationFrame({admin, args: operationArgs})};
  if (operation === 'simulation_frame_get') return {operation, registryVersion: registry.version, result: await simulationFrameGet({admin, args: operationArgs})};
  if (operation === 'simulation_frame_versions') return {operation, registryVersion: registry.version, result: await simulationFrameVersions({admin, args: operationArgs})};
  if (operation === 'simulation_context_packet') return {operation, registryVersion: registry.version, result: await simulationContextPacket({admin, args: operationArgs})};
  if (operation === 'run_simulation_frame') return {operation, registryVersion: registry.version, result: await runSimulationFrame({admin, args: operationArgs})};
  throw Object.assign(new Error('Unsupported simulation operation.'), {status: 400});
}


function createRequestId(value) {
  const supplied = safeText(value, 160);
  return supplied ? stableRequestId(supplied) : randomUUID();
}

function driveBridgeWriteSummary(kind, metadata, parentFolderId = '') {
  if (kind === 'drive.createFolder') return `Created Drive folder ${metadata.name || metadata.id}.`;
  if (kind === 'docs.create') return `Created Google Doc ${metadata.name || metadata.id}.`;
  return `Wrote ${metadata.name || metadata.id}${parentFolderId ? ` in ${parentFolderId}` : ''}.`;
}

function bridgeStageError(code, message, stage, status = 400, extra = {}) {
  const err = new Error(message);
  err.code = code;
  err.stage = stage;
  err.status = status;
  Object.assign(err, extra);
  return err;
}

function providerStatus(err) {
  return err && (err.status || err.code || (err.response && err.response.status)) || 500;
}

function providerMessage(err, max = 800) {
  const responseData = err && err.response && err.response.data;
  if (responseData && responseData.error && responseData.error.message) return safeText(responseData.error.message, max);
  if (responseData && responseData.error_description) return safeText(responseData.error_description, max);
  if (responseData && responseData.error) return safeText(String(responseData.error), max);
  return safeText(err && err.message || String(err || 'unknown error'), max);
}

function docsCreateErrorPayload(err, args = {}, partial = null) {
  const code = safeText(err && err.code, 80) || 'DOCS_CREATE_INTERNAL_ERROR';
  return {
    ok: false,
    error: {
      code,
      message: providerMessage(err, 800),
      stage: safeText(err && err.stage, 120) || 'internal',
      requestId: safeText(args && args.requestId, 160),
      googleStatus: err && err.googleStatus || undefined,
    },
    partial: partial || err && err.partial || undefined,
    recoverable: !!(partial || err && err.partial),
  };
}

function docsCreateDiagnostic(args = {}, extra = {}) {
  return {
    toolName: 'docs_create',
    requestId: safeText(args.requestId, 160),
    titleLength: safeText(args.title, 2000).length,
    initialTextLength: boundedText(args.initialText, 1000000).length,
    hasParentFolderId: !!safeText(args.parentFolderId, 220),
    ...extra,
  };
}

function logDocsCreate(stage, args = {}, extra = {}) {
  console.log(JSON.stringify({
    event: 'docs_create_diagnostic',
    stage,
    ...docsCreateDiagnostic(args, extra),
  }));
}

function safeGitHubRepo(value, fallback = 'Valar05/home-center') {
  const repo = safeText(value, 160) || fallback;
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) {
    const err = new Error('repo must look like owner/name.');
    err.status = 400;
    throw err;
  }
  return repo;
}

function safeGitHubNumber(value, label = 'number') {
  const number = Math.floor(safeNumber(value, 0));
  if (!number || number < 1) {
    const err = new Error(`${label} must be a positive GitHub issue or pull request number.`);
    err.status = 400;
    throw err;
  }
  return number;
}

function safeGitHubRef(value) {
  const ref = safeText(value, 240);
  if (!ref) return '';
  if (!/^[A-Za-z0-9_./-]{1,240}$/.test(ref) || ref.includes('..')) {
    const err = new Error('ref contains unsupported characters.');
    err.status = 400;
    throw err;
  }
  return ref;
}

function safeGitHubPath(value) {
  const filePath = safeText(value, 1000).replace(/^\/+/, '');
  if (!filePath || filePath.includes('..')) {
    const err = new Error('path is required and must not contain parent-directory traversal.');
    err.status = 400;
    throw err;
  }
  return filePath;
}

function githubTokenValue(githubToken) {
  return safeText(typeof githubToken === 'function' ? githubToken() : githubToken, 4096) || safeText(process.env.GITHUB_TOKEN, 4096);
}

function githubHeaders(token, extra = {}) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'User-Agent': 'home-center-mcp',
    'X-GitHub-Api-Version': '2022-11-28',
    ...extra,
  };
}

async function githubRequest(githubToken, route, options = {}) {
  const token = githubTokenValue(githubToken);
  if (!token) {
    const err = new Error('GITHUB_TOKEN secret is not configured for Home Center GitHub tools.');
    err.status = 503;
    throw err;
  }
  const response = await fetch(`https://api.github.com${route}`, {
    method: options.method || 'GET',
    headers: githubHeaders(token),
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const text = await response.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch (_) {
    json = text;
  }
  if (!response.ok) {
    const err = new Error(safeText(json && json.message ? json.message : response.statusText, 1000));
    err.status = response.status;
    err.github = json;
    throw err;
  }
  return json;
}

function githubRepoRoute(repo, suffix = '') {
  const [owner, name] = safeGitHubRepo(repo).split('/');
  return `/repos/${encodeURIComponent(owner)}/${encodeURIComponent(name)}${suffix}`;
}

function cleanGitHubUser(user = {}) {
  return user && typeof user === 'object' ? {login: user.login || '', htmlUrl: user.html_url || ''} : null;
}

function cleanGitHubRepo(repo = {}) {
  return {
    id: repo.id || 0,
    name: repo.name || '',
    fullName: repo.full_name || '',
    private: !!repo.private,
    description: repo.description || '',
    defaultBranch: repo.default_branch || '',
    htmlUrl: repo.html_url || '',
    updatedAt: repo.updated_at || '',
    pushedAt: repo.pushed_at || '',
    openIssuesCount: repo.open_issues_count || 0,
  };
}

function cleanGitHubIssue(issue = {}) {
  return {
    number: issue.number || 0,
    title: issue.title || '',
    state: issue.state || '',
    htmlUrl: issue.html_url || '',
    url: issue.html_url || '',
    user: cleanGitHubUser(issue.user),
    labels: Array.isArray(issue.labels) ? issue.labels.map((label) => typeof label === 'string' ? label : label.name).filter(Boolean) : [],
    createdAt: issue.created_at || '',
    updatedAt: issue.updated_at || '',
    closedAt: issue.closed_at || '',
    commentCount: issue.comments || 0,
    body: safeText(issue.body, 12000),
    isPullRequest: !!issue.pull_request,
  };
}

function cleanGitHubPullRequest(pr = {}) {
  return {
    number: pr.number || 0,
    title: pr.title || '',
    state: pr.state || '',
    htmlUrl: pr.html_url || '',
    url: pr.html_url || '',
    user: cleanGitHubUser(pr.user),
    draft: !!pr.draft,
    merged: !!pr.merged,
    mergeable: pr.mergeable === null ? null : !!pr.mergeable,
    base: pr.base ? {ref: pr.base.ref || '', sha: pr.base.sha || ''} : null,
    head: pr.head ? {ref: pr.head.ref || '', sha: pr.head.sha || ''} : null,
    createdAt: pr.created_at || '',
    updatedAt: pr.updated_at || '',
    body: safeText(pr.body, 12000),
  };
}

function cleanGitHubComment(comment = {}) {
  return {
    id: comment.id || 0,
    htmlUrl: comment.html_url || '',
    user: cleanGitHubUser(comment.user),
    createdAt: comment.created_at || '',
    updatedAt: comment.updated_at || '',
    body: safeText(comment.body, 12000),
  };
}

function cleanGitHubPullRequestFile(file = {}) {
  return {
    filename: file.filename || '',
    status: file.status || '',
    additions: file.additions || 0,
    deletions: file.deletions || 0,
    changes: file.changes || 0,
    blobUrl: file.blob_url || '',
    rawUrl: file.raw_url || '',
    patch: safeText(file.patch, 12000),
  };
}

function cleanGitHubWorkflowRun(run = {}) {
  return {
    id: run.id || 0,
    name: run.name || '',
    displayTitle: run.display_title || '',
    status: run.status || '',
    conclusion: run.conclusion || '',
    event: run.event || '',
    branch: run.head_branch || '',
    sha: run.head_sha || '',
    htmlUrl: run.html_url || '',
    createdAt: run.created_at || '',
    updatedAt: run.updated_at || '',
  };
}

function githubQuery(params = {}) {
  const pairs = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '');
  return pairs.length ? `?${pairs.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`).join('&')}` : '';
}


function githubAdminEnabled() {
  return process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED === 'true';
}

function githubAdminSecretValue(githubAdmin = {}, key, envKey, max = 12000) {
  const value = githubAdmin && typeof githubAdmin[key] === 'function' ? githubAdmin[key]() : githubAdmin && githubAdmin[key];
  return safeText(value, max) || safeText(process.env[envKey] || '', max);
}

function githubAdminOwners(githubAdmin = {}) {
  const raw = githubAdminSecretValue(githubAdmin, 'allowedOwners', 'HOME_CENTER_GITHUB_ADMIN_OWNERS', 2000) || 'Valar05';
  return raw.split(',').map((owner) => safeText(owner, 120)).filter((owner) => /^[A-Za-z0-9_.-]{1,120}$/.test(owner));
}

function safeGitHubOwner(value) {
  const owner = safeText(value, 120);
  if (!/^[A-Za-z0-9_.-]{1,120}$/.test(owner)) throw Object.assign(new Error('owner must be a GitHub owner/login.'), {status: 400, code: 'github_admin_invalid_owner'});
  return owner;
}

function safeGitHubRepoName(value) {
  const name = safeText(value, 120);
  if (!/^[A-Za-z0-9_.-]{1,120}$/.test(name)) throw Object.assign(new Error('name must be a GitHub repository name.'), {status: 400, code: 'github_admin_invalid_repo_name'});
  return name;
}

function requireGitHubAdminEnabled() {
  if (githubAdminEnabled()) return;
  throw Object.assign(new Error('GitHub admin mutations are disabled. Set HOME_CENTER_GITHUB_ADMIN_ENABLED=true and configure the GitHub App secrets.'), {status: 403, code: 'github_admin_disabled'});
}

function requireGitHubAdminOwner(githubAdmin, owner) {
  const clean = safeGitHubOwner(owner);
  const allowed = githubAdminOwners(githubAdmin);
  if (!allowed.includes(clean)) {
    throw Object.assign(new Error(`GitHub owner ${clean} is outside the Home Center GitHub admin allowlist.`), {status: 403, code: 'github_admin_owner_not_allowed', allowedOwners: allowed});
  }
  return clean;
}

function base64UrlJson(value) {
  return Buffer.from(JSON.stringify(value)).toString('base64url');
}

function normalizeGithubPrivateKey(value) {
  return safeText(value, 12000).replace(/\\n/g, '\n');
}

function createGitHubAppJwt(appId, privateKey) {
  const now = Math.floor(Date.now() / 1000);
  const header = base64UrlJson({alg: 'RS256', typ: 'JWT'});
  const payload = base64UrlJson({iat: now - 60, exp: now + 540, iss: String(appId)});
  const signingInput = `${header}.${payload}`;
  const signer = createSign('RSA-SHA256');
  signer.update(signingInput);
  signer.end();
  return `${signingInput}.${signer.sign(normalizeGithubPrivateKey(privateKey), 'base64url')}`;
}

async function githubAdminInstallationToken(githubAdmin = {}) {
  const appId = githubAdminSecretValue(githubAdmin, 'appId', 'GITHUB_APP_ID', 120);
  const installationId = githubAdminSecretValue(githubAdmin, 'installationId', 'GITHUB_APP_INSTALLATION_ID', 120);
  const privateKey = githubAdminSecretValue(githubAdmin, 'privateKey', 'GITHUB_APP_PRIVATE_KEY', 12000);
  if (!appId || !installationId || !privateKey) {
    const err = new Error('GitHub App credentials are not configured for Home Center GitHub admin tools. Required: GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY.');
    err.status = 503;
    err.code = 'github_admin_app_credentials_missing';
    throw err;
  }
  const jwt = createGitHubAppJwt(appId, privateKey);
  const response = await fetch(`https://api.github.com/app/installations/${encodeURIComponent(installationId)}/access_tokens`, {
    method: 'POST',
    headers: githubHeaders(jwt),
  });
  const text = await response.text();
  const json = text ? JSON.parse(text) : null;
  if (!response.ok || !json || !json.token) {
    const err = new Error(safeText(json && json.message || response.statusText, 1000));
    err.status = response.status || 502;
    err.code = 'github_admin_installation_token_failed';
    err.github = json;
    throw err;
  }
  return json.token;
}

async function githubAdminToken(githubAdmin = {}, options = {}) {
  const preferBootstrap = !!options.preferBootstrap;
  const bootstrap = githubAdminSecretValue(githubAdmin, 'bootstrapToken', 'GITHUB_BOOTSTRAP_TOKEN', 4096) || githubAdminSecretValue(githubAdmin, 'adminToken', 'GITHUB_ADMIN_TOKEN', 4096);
  if (preferBootstrap) {
    if (!bootstrap) throw Object.assign(new Error('This GitHub admin operation requires GITHUB_BOOTSTRAP_TOKEN or GITHUB_ADMIN_TOKEN.'), {status: 503, code: 'github_admin_bootstrap_token_missing'});
    return {token: bootstrap, mode: 'bootstrap_token'};
  }
  try {
    return {token: await githubAdminInstallationToken(githubAdmin), mode: 'github_app_installation'};
  } catch (err) {
    if (bootstrap) return {token: bootstrap, mode: 'bootstrap_token_fallback', appError: {code: err.code || '', status: err.status || 0, message: safeText(err.message, 400)}};
    throw err;
  }
}

async function githubAdminRequest(githubAdmin, route, options = {}) {
  const tokenInfo = await githubAdminToken(githubAdmin, options);
  const response = await fetch(`https://api.github.com${route}`, {
    method: options.method || 'GET',
    headers: githubHeaders(tokenInfo.token, options.accept ? {Accept: options.accept} : {}),
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const text = await response.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch (_) { json = text; }
  if (!response.ok) {
    const err = new Error(safeText(json && json.message ? json.message : response.statusText, 1000));
    err.status = response.status;
    err.code = response.status === 403 ? 'github_admin_permission_denied' : response.status === 404 ? 'github_admin_not_found' : `github_admin_http_${response.status}`;
    err.github = json;
    err.authMode = tokenInfo.mode;
    throw err;
  }
  return {json, status: response.status, authMode: tokenInfo.mode, appError: tokenInfo.appError || null};
}

function githubAdminRouteForRepo(repo, suffix = '') {
  return githubRepoRoute(repo, suffix);
}

function cleanGitHubAdminRepo(repo = {}) {
  return cleanGitHubRepo(repo);
}

function cleanGitHubAdminCommit(commit = {}) {
  return {sha: commit.sha || '', htmlUrl: commit.html_url || '', message: commit.commit && commit.commit.message || ''};
}

function cleanGitHubAdminBranch(branch = {}) {
  return {ref: branch.ref || '', sha: branch.object && branch.object.sha || '', url: branch.url || ''};
}

async function githubAdminAuthStatusOperation({githubAdmin = {}}) {
  const owners = githubAdminOwners(githubAdmin);
  const appId = githubAdminSecretValue(githubAdmin, 'appId', 'GITHUB_APP_ID', 120);
  const installationId = githubAdminSecretValue(githubAdmin, 'installationId', 'GITHUB_APP_INSTALLATION_ID', 120);
  const privateKeyConfigured = !!githubAdminSecretValue(githubAdmin, 'privateKey', 'GITHUB_APP_PRIVATE_KEY', 12000);
  const bootstrapConfigured = !!(githubAdminSecretValue(githubAdmin, 'bootstrapToken', 'GITHUB_BOOTSTRAP_TOKEN', 4096) || githubAdminSecretValue(githubAdmin, 'adminToken', 'GITHUB_ADMIN_TOKEN', 4096));
  return {
    ok: true,
    enabled: githubAdminEnabled(),
    authority: 'home_center_github_admin_v1',
    primaryCredential: appId && installationId && privateKeyConfigured ? 'github_app_installation' : '',
    fallbackCredentialConfigured: bootstrapConfigured,
    appConfigured: !!(appId && installationId && privateKeyConfigured),
    allowedOwners: owners,
    mutationRequiresRequestId: true,
    secretsExposed: false,
    supportedOperations: ['github_admin.auth_status', 'github_admin.repos.create', 'github_admin.repos.configure', 'github_admin.branches.create', 'github_admin.files.upsert', 'github_admin.pull_requests.create', 'github_admin.pull_requests.merge', 'github_admin.workflows.dispatch'],
  };
}

async function githubAdminCreateRepoOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const owner = requireGitHubAdminOwner(githubAdmin, args.owner || 'Valar05');
  const name = safeGitHubRepoName(args.name);
  const ownerType = safeText(args.ownerType || args.scope || 'org', 20).toLowerCase();
  if (!['org', 'user'].includes(ownerType)) throw Object.assign(new Error('ownerType must be org or user.'), {status: 400, code: 'github_admin_invalid_owner_type'});
  const visibility = safeText(args.visibility || 'private', 20).toLowerCase();
  if (!['private', 'public', 'internal'].includes(visibility)) throw Object.assign(new Error('visibility must be private, public, or internal.'), {status: 400, code: 'github_admin_invalid_visibility'});
  const body = {name, description: safeText(args.description, 1000), private: visibility === 'private', visibility, auto_init: args.autoInit === true};
  if (safeText(args.homepage, 1000)) body.homepage = safeText(args.homepage, 1000);
  const route = ownerType === 'user' ? '/user/repos' : `/orgs/${encodeURIComponent(owner)}/repos`;
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, route, {method: 'POST', body, preferBootstrap: ownerType === 'user'});
  const repo = cleanGitHubAdminRepo(json || {});
  const result = {repo, repoFullName: repo.fullName, htmlUrl: repo.htmlUrl, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.repos.create', operation: 'github.admin.repos.create', requestId, fileId: `github:${repo.fullName || owner + '/' + name}`, affectedFileIds: [`github:${repo.fullName || owner + '/' + name}`], oldMetadata: null, newMetadata: repo, oldParents: [], newParents: [owner], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Created GitHub repository ${repo.fullName || owner + '/' + name}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminConfigureRepoOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, repo.split('/')[0]);
  const body = {};
  ['description', 'homepage', 'default_branch'].forEach((key) => { if (safeText(args[key], 1000)) body[key] = safeText(args[key], 1000); });
  ['has_issues', 'has_projects', 'has_wiki', 'allow_squash_merge', 'allow_merge_commit', 'allow_rebase_merge', 'delete_branch_on_merge', 'allow_auto_merge'].forEach((key) => { if (typeof args[key] === 'boolean') body[key] = args[key]; });
  if (!Object.keys(body).length) throw Object.assign(new Error('at least one repository setting is required.'), {status: 400, code: 'github_admin_no_repo_settings'});
  const before = cleanGitHubAdminRepo((await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo))).json || {});
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo), {method: 'PATCH', body});
  const after = cleanGitHubAdminRepo(json || {});
  const result = {repo, before, after, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.repos.configure', operation: 'github.admin.repos.configure', requestId, fileId: `github:${repo}`, affectedFileIds: [`github:${repo}`], oldMetadata: before, newMetadata: after, oldParents: [], newParents: [], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Configured GitHub repository ${repo}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminCreateBranchOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, repo.split('/')[0]);
  const branch = safeGitHubRef(args.branch);
  const fromBranch = safeGitHubRef(args.fromBranch || args.base || 'main');
  if (!branch) throw Object.assign(new Error('branch is required.'), {status: 400, code: 'github_admin_branch_required'});
  const base = (await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, `/git/ref/heads/${encodeURIComponent(fromBranch)}`))).json || {};
  const sha = safeText(args.sha, 80) || base.object && base.object.sha;
  if (!sha) throw Object.assign(new Error('base branch did not resolve to a commit SHA.'), {status: 404, code: 'github_admin_base_branch_missing'});
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, '/git/refs'), {method: 'POST', body: {ref: `refs/heads/${branch}`, sha}});
  const created = cleanGitHubAdminBranch(json || {});
  const result = {repo, branch, fromBranch, sha, ref: created, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.branches.create', operation: 'github.admin.branches.create', requestId, fileId: `github:${repo}:refs/heads/${branch}`, affectedFileIds: [`github:${repo}:refs/heads/${branch}`], oldMetadata: null, newMetadata: created, oldParents: [], newParents: [repo], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Created GitHub branch ${repo}:${branch}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminUpsertFileOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, repo.split('/')[0]);
  const filePath = safeGitHubPath(args.path);
  const branch = safeGitHubRef(args.branch || 'main');
  const message = safeText(args.message || `Home Center update ${filePath}`, 240);
  const content = boundedText(args.content, 2000000);
  const contentBase64 = safeText(args.contentBase64, 3000000) || Buffer.from(content, 'utf8').toString('base64');
  if (!contentBase64) throw Object.assign(new Error('content or contentBase64 is required.'), {status: 400, code: 'github_admin_file_content_required'});
  let sha = safeText(args.sha, 120);
  let before = null;
  if (!sha) {
    try {
      before = (await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, `/contents/${filePath.split('/').map(encodeURIComponent).join('/')}${githubQuery({ref: branch})}`))).json;
      sha = before && before.sha || '';
    } catch (err) {
      if (err.status !== 404) throw err;
    }
  }
  const body = {message, content: contentBase64, branch};
  if (sha) body.sha = sha;
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, `/contents/${filePath.split('/').map(encodeURIComponent).join('/')}`), {method: 'PUT', body});
  const commit = cleanGitHubAdminCommit(json && json.commit || {});
  const result = {repo, path: filePath, branch, commit, contentSha: json && json.content && json.content.sha || '', status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.files.upsert', operation: 'github.admin.files.upsert', requestId, fileId: `github:${repo}/${filePath}`, affectedFileIds: [`github:${repo}/${filePath}`, `github:${repo}@${commit.sha}`], oldMetadata: before ? {sha: before.sha || ''} : null, newMetadata: {sha: result.contentSha, commit}, oldParents: [branch], newParents: [branch], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Upserted ${repo}/${filePath} on ${branch}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminCreatePullRequestOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, repo.split('/')[0]);
  const title = safeText(args.title, 240);
  const head = safeGitHubRef(args.head);
  const base = safeGitHubRef(args.base || 'main');
  if (!title || !head || !base) throw Object.assign(new Error('title, head, and base are required.'), {status: 400, code: 'github_admin_pr_input_required'});
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, '/pulls'), {method: 'POST', body: {title, head, base, body: safeText(args.body, 60000), draft: args.draft === true}});
  const pullRequest = cleanGitHubPullRequest(json || {});
  const result = {repo, pullRequest, number: pullRequest.number, htmlUrl: pullRequest.htmlUrl, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.pull_requests.create', operation: 'github.admin.pull_requests.create', requestId, fileId: `github:${repo}#${pullRequest.number}`, affectedFileIds: [`github:${repo}#${pullRequest.number}`], oldMetadata: null, newMetadata: pullRequest, oldParents: [base], newParents: [head], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Created GitHub PR ${repo}#${pullRequest.number}: ${title}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminCheckMergePreconditions(githubAdmin, repo, number, args = {}) {
  const pullRequest = cleanGitHubPullRequest((await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, `/pulls/${number}`))).json || {});
  const expectedHeadSha = safeText(args.expectedHeadSha || args.headSha, 80);
  if (!expectedHeadSha) throw Object.assign(new Error('expectedHeadSha is required for PR merge.'), {status: 400, code: 'github_admin_expected_head_sha_required'});
  if (!pullRequest.head || pullRequest.head.sha !== expectedHeadSha) throw Object.assign(new Error('PR head SHA changed; refusing to merge stale review.'), {status: 409, code: 'github_admin_head_sha_mismatch', currentHeadSha: pullRequest.head && pullRequest.head.sha || '', expectedHeadSha});
  if (pullRequest.draft) throw Object.assign(new Error('Draft pull requests cannot be merged by Home Center.'), {status: 409, code: 'github_admin_pr_is_draft'});
  if (args.requireGreenChecks === false) return {pullRequest, combinedStatus: null};
  const status = (await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, `/commits/${expectedHeadSha}/status`))).json || {};
  if (status.state !== 'success' && !(args.allowNoChecks === true && Array.isArray(status.statuses) && !status.statuses.length)) {
    throw Object.assign(new Error(`Required commit statuses are not green: ${status.state || 'unknown'}.`), {status: 409, code: 'github_admin_checks_not_green', combinedState: status.state || 'unknown'});
  }
  return {pullRequest, combinedStatus: {state: status.state || '', totalCount: status.total_count || 0}};
}

async function githubAdminMergePullRequestOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, repo.split('/')[0]);
  const number = safeGitHubNumber(args.number || args.pullNumber, 'pullNumber');
  const method = safeText(args.mergeMethod || 'squash', 20).toLowerCase();
  if (!['merge', 'squash', 'rebase'].includes(method)) throw Object.assign(new Error('mergeMethod must be merge, squash, or rebase.'), {status: 400, code: 'github_admin_invalid_merge_method'});
  const preflight = await githubAdminCheckMergePreconditions(githubAdmin, repo, number, args);
  const body = {merge_method: method, sha: safeText(args.expectedHeadSha || args.headSha, 80)};
  if (safeText(args.commitTitle, 240)) body.commit_title = safeText(args.commitTitle, 240);
  if (safeText(args.commitMessage, 60000)) body.commit_message = safeText(args.commitMessage, 60000);
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, `/pulls/${number}/merge`), {method: 'PUT', body});
  const result = {repo, number, mergeMethod: method, merged: !!(json && json.merged), sha: json && json.sha || '', message: json && json.message || '', preflight, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.pull_requests.merge', operation: 'github.admin.pull_requests.merge', requestId, fileId: `github:${repo}#${number}`, affectedFileIds: [`github:${repo}#${number}`, `github:${repo}@${result.sha}`], oldMetadata: preflight.pullRequest, newMetadata: result, oldParents: [preflight.pullRequest.head && preflight.pullRequest.head.ref || ''], newParents: [preflight.pullRequest.base && preflight.pullRequest.base.ref || ''], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Merged GitHub PR ${repo}#${number} with ${method}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminDispatchWorkflowOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, repo.split('/')[0]);
  const workflowId = safeText(args.workflowId || args.workflowFile, 240);
  const ref = safeGitHubRef(args.ref || 'main');
  if (!workflowId || /[\\?#]/.test(workflowId)) throw Object.assign(new Error('workflowId is required and must be a workflow file name or numeric workflow id.'), {status: 400, code: 'github_admin_invalid_workflow_id'});
  const inputs = args.inputs && typeof args.inputs === 'object' && !Array.isArray(args.inputs) ? args.inputs : {};
  const {authMode, status} = await githubAdminRequest(githubAdmin, githubAdminRouteForRepo(repo, `/actions/workflows/${encodeURIComponent(workflowId)}/dispatches`), {method: 'POST', body: {ref, inputs}});
  const result = {repo, workflowId, ref, dispatched: true, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.workflows.dispatch', operation: 'github.admin.workflows.dispatch', requestId, fileId: `github:${repo}:workflow:${workflowId}`, affectedFileIds: [`github:${repo}:workflow:${workflowId}`], oldMetadata: null, newMetadata: result, oldParents: [repo], newParents: [ref], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Dispatched GitHub workflow ${workflowId} in ${repo} at ${ref}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminOperationRunOperation({admin, user, githubAdmin = {}, args = {}}) {
  const operation = safeText(args.operation || args.type || args.toolName, 120);
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {...args};
  delete operationArgs.operation;
  delete operationArgs.type;
  delete operationArgs.toolName;
  delete operationArgs.args;
  if (operation === 'github_admin.auth_status') return githubAdminAuthStatusOperation({githubAdmin, args: operationArgs});
  if (operation === 'github_admin.repos.create') return githubAdminCreateRepoOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.repos.configure') return githubAdminConfigureRepoOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.branches.create') return githubAdminCreateBranchOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.files.upsert') return githubAdminUpsertFileOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.pull_requests.create') return githubAdminCreatePullRequestOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.pull_requests.merge') return githubAdminMergePullRequestOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.workflows.dispatch') return githubAdminDispatchWorkflowOperation({admin, user, githubAdmin, args: operationArgs});
  throw Object.assign(new Error('Unsupported GitHub admin operation: ' + operation), {status: 400, code: 'github_admin_unsupported_operation'});
}

function githubAdminOperationEntries() {
  return {
    'github_admin.auth_status': {summary: 'Inspect Home Center GitHub admin authority without exposing secrets.', write: false, input: {}},
    'github_admin.repos.create': {summary: 'Create a repository through the configured GitHub App/admin authority and audit the mutation.', write: true, requiresRequestId: true, requiredPermissions: ['Administration: write'], input: {owner: 'string', ownerType: 'org|user', name: 'string', visibility: 'private|public|internal', description: 'optional string', autoInit: 'optional boolean', requestId: 'string'}},
    'github_admin.repos.configure': {summary: 'Update safe repository settings through GitHub admin authority and audit the mutation.', write: true, requiresRequestId: true, requiredPermissions: ['Administration: write'], input: {repo: 'owner/name', description: 'optional string', default_branch: 'optional string', mergeSettings: 'optional booleans', requestId: 'string'}},
    'github_admin.branches.create': {summary: 'Create a branch from an existing branch or explicit SHA.', write: true, requiresRequestId: true, requiredPermissions: ['Contents: write'], input: {repo: 'owner/name', branch: 'string', fromBranch: 'optional string', sha: 'optional commit SHA', requestId: 'string'}},
    'github_admin.files.upsert': {summary: 'Create or update one repository file on a branch.', write: true, requiresRequestId: true, requiredPermissions: ['Contents: write', 'Workflows: write when path is .github/workflows/*'], input: {repo: 'owner/name', path: 'string', branch: 'string', message: 'string', content: 'string or contentBase64', sha: 'optional expected blob SHA', requestId: 'string'}},
    'github_admin.pull_requests.create': {summary: 'Open a pull request from head to base.', write: true, requiresRequestId: true, requiredPermissions: ['Pull requests: write'], input: {repo: 'owner/name', title: 'string', head: 'branch', base: 'branch', body: 'optional string', draft: 'optional boolean', requestId: 'string'}},
    'github_admin.pull_requests.merge': {summary: 'Merge a pull request only when expectedHeadSha matches and required checks are green.', write: true, requiresRequestId: true, requiredPermissions: ['Contents: write'], input: {repo: 'owner/name', pullNumber: 'number', expectedHeadSha: 'required SHA', mergeMethod: 'merge|squash|rebase', requireGreenChecks: 'optional boolean default true', allowNoChecks: 'optional boolean', requestId: 'string'}},
    'github_admin.workflows.dispatch': {summary: 'Dispatch a GitHub Actions workflow by workflow id/file and ref.', write: true, requiresRequestId: true, requiredPermissions: ['Actions: write'], input: {repo: 'owner/name', workflowId: 'string or number', ref: 'branch/tag/SHA', inputs: 'optional object', requestId: 'string'}},
  };
}

async function createGitHubIssueOperation({admin, user, githubToken, args = {}}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  const title = safeText(args.title, 240);
  const body = safeText(args.body, 60000);
  if (!title || !body) throw Object.assign(new Error('title and body are required.'), {status: 400});
  const labels = Array.isArray(args.labels) ? args.labels.map((label) => safeText(label, 60)).filter(Boolean).slice(0, 12) : [];
  let created;
  try {
    created = await githubRequest(githubToken, githubRepoRoute(repo, '/issues'), {method: 'POST', body: {title, body, ...(labels.length ? {labels} : {})}});
  } catch (err) {
    if (err.status !== 422 || !labels.length) throw err;
    created = await githubRequest(githubToken, githubRepoRoute(repo, '/issues'), {method: 'POST', body: {title, body}});
  }
  const issue = cleanGitHubIssue(created || {});
  const result = {repo, issue, issueNumber: issue.number, htmlUrl: issue.htmlUrl, url: issue.htmlUrl, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_create_issue', operation: 'github.createIssue', requestId, fileId: `github:${repo}#${issue.number}`, affectedFileIds: [`github:${repo}#${issue.number}`], oldMetadata: null, newMetadata: issue, oldParents: [], newParents: [repo], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: safeText(args.callerNote, 400) || `Created GitHub issue ${repo}#${issue.number}: ${title}.`, result});
  return {...result, audit: audit.audit};
}

async function commentGitHubIssueOperation({admin, user, githubToken, args = {}, tool = 'github_comment_issue', operation = 'github.commentIssue'}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  const number = safeGitHubNumber(args.number);
  const body = safeText(args.body, 60000);
  if (!body) throw Object.assign(new Error('body is required.'), {status: 400});
  const created = await githubRequest(githubToken, githubRepoRoute(repo, `/issues/${number}/comments`), {method: 'POST', body: {body}});
  const comment = cleanGitHubComment(created || {});
  const result = {repo, number, comment, htmlUrl: comment.htmlUrl, url: comment.htmlUrl, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool, operation, requestId, fileId: `github:${repo}#${number}`, affectedFileIds: [`github:${repo}#${number}`, `github-comment:${comment.id}`], oldMetadata: null, newMetadata: comment, oldParents: [], newParents: [repo], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: safeText(args.callerNote, 400) || `Commented on ${repo}#${number}.`, result});
  return {...result, audit: audit.audit};
}

function safeSheetRange(value, fallback = 'A1:Z100') {
  const range = safeText(value, 240) || fallback;
  if (!range || /[\r\n{}<>]/.test(range)) {
    const err = new Error('range contains unsupported characters.');
    err.status = 400;
    throw err;
  }
  return range;
}

function safeSheetTitle(value, fallback = 'Sheet1') {
  const title = safeText(value, 100) || fallback;
  if (!title || /[\[\]*?:/\\]/.test(title)) {
    const err = new Error('sheetTitle contains unsupported characters.');
    err.status = 400;
    throw err;
  }
  return title;
}

function normalizeSheetCell(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'boolean') return value;
  return boundedText(String(value), 2000);
}

function safeSheetValues(values, maxRows = 200, maxColumns = 50) {
  if (!Array.isArray(values)) return [];
  return values.slice(0, maxRows).map((row) => {
    const cells = Array.isArray(row) ? row : [row];
    return cells.slice(0, maxColumns).map(normalizeSheetCell);
  });
}

function cleanSpreadsheet(data = {}) {
  return {
    spreadsheetId: data.spreadsheetId || '',
    spreadsheetUrl: data.spreadsheetUrl || '',
    title: data.properties && data.properties.title || '',
    sheets: Array.isArray(data.sheets) ? data.sheets.map((sheet) => ({
      sheetId: sheet.properties && sheet.properties.sheetId || 0,
      title: sheet.properties && sheet.properties.title || '',
      index: sheet.properties && sheet.properties.index || 0,
      rowCount: sheet.properties && sheet.properties.gridProperties && sheet.properties.gridProperties.rowCount || 0,
      columnCount: sheet.properties && sheet.properties.gridProperties && sheet.properties.gridProperties.columnCount || 0,
    })) : [],
  };
}


function safeWorkbookTitle(value, fallback = 'Imported Workbook') {
  const title = safeText(value, 240) || fallback;
  if (!title) throw Object.assign(new Error('title is required.'), {status: 400});
  return title.replace(/\.xlsx$/i, '') || fallback;
}

function workbookFileName(value, fallback = 'workbook.xlsx') {
  const name = safeText(value, 240) || fallback;
  return /\.xlsx$/i.test(name) ? name : `${name}.xlsx`;
}

function workbookBufferFromBase64(value) {
  const raw = safeText(value, 80 * 1024 * 1024);
  if (!raw) return null;
  if (!/^[A-Za-z0-9+/=_-]+$/.test(raw)) throw Object.assign(new Error('workbookBase64 must be base64 encoded .xlsx bytes.'), {status: 400});
  const normalized = raw.replace(/-/g, '+').replace(/_/g, '/');
  const buffer = Buffer.from(normalized, 'base64');
  if (!buffer.length) throw Object.assign(new Error('workbookBase64 decoded to an empty file.'), {status: 400});
  if (buffer.length > 50 * 1024 * 1024) throw Object.assign(new Error('workbookBase64 exceeds the 50 MB bridge import limit.'), {status: 413});
  return buffer;
}

function sheetA1Name(title) {
  return `'${String(title || '').replace(/'/g, "''")}'`;
}

function populatedCellCount(values = []) {
  if (!Array.isArray(values)) return 0;
  let count = 0;
  for (const row of values) {
    if (!Array.isArray(row)) continue;
    for (const cell of row) {
      if (cell !== null && cell !== undefined && String(cell) !== '') count += 1;
    }
  }
  return count;
}

function normalizeExpectedCellCounts(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  const result = {};
  for (const [key, raw] of Object.entries(value)) {
    const title = safeText(key, 100);
    const count = Math.max(0, Math.floor(safeNumber(raw, 0)));
    if (title) result[title] = count;
  }
  return result;
}

async function destinationWorkbookCellCounts(sheetsApi, spreadsheetId, sheetNames) {
  const counts = {};
  const warnings = [];
  for (const name of sheetNames) {
    try {
      const result = await sheetsApi.spreadsheets.values.get({spreadsheetId, range: sheetA1Name(name)});
      counts[name] = populatedCellCount(result.data && result.data.values || []);
    } catch (err) {
      counts[name] = null;
      warnings.push(`Could not count populated destination cells for worksheet ${name}: ${safeText(err.message || String(err), 200)}`);
    }
  }
  return {counts, warnings};
}

async function searchSheetsOperation({google, auth, args = {}}) {
  const drive = google.drive({version: 'v3', auth});
  const result = await drive.files.list({
    q: chatGptDriveSearchQuery({
      query: args.query || '',
      folderId: args.folderId || '',
      mimeTypes: ['application/vnd.google-apps.spreadsheet'],
    }),
    pageSize: chatGptLimit(args && args.limit, 20, 50),
    fields: 'files(id,name,mimeType,modifiedTime,webViewLink,parents)',
    orderBy: 'modifiedTime desc',
    supportsAllDrives: true,
    includeItemsFromAllDrives: true,
  });
  return {results: (result.data.files || []).map(chatGptDriveFile)};
}

async function readSheetOperation({google, auth, args = {}}) {
  const spreadsheetId = safeDriveFileId(args.spreadsheetId);
  const range = safeSheetRange(args.range, 'A1:Z100');
  const sheets = google.sheets({version: 'v4', auth});
  const values = await sheets.spreadsheets.values.get({spreadsheetId, range});
  const metadata = await sheets.spreadsheets.get({spreadsheetId, fields: 'spreadsheetId,spreadsheetUrl,properties(title),sheets(properties(sheetId,title,index,gridProperties(rowCount,columnCount)))'});
  return {
    spreadsheetId,
    range: values.data.range || range,
    majorDimension: values.data.majorDimension || 'ROWS',
    values: values.data.values || [],
    spreadsheet: cleanSpreadsheet(metadata.data || {}),
  };
}



async function resolveWorkbookSourceFile(drive, args = {}) {
  const explicit = safeText(args.sourceFileId || args.fileId, 220);
  if (explicit) return safeDriveFileId(explicit);
  const sourceFolderId = safeText(args.sourceFolderId || args.searchFolderId, 220) ? safeDriveFileId(args.sourceFolderId || args.searchFolderId) : '';
  const fileName = safeText(args.sourceFileName || args.fileName || args.name, 240);
  const query = safeText(args.sourceQuery || args.query, 240);
  if (!fileName && !query) return '';
  const clauses = ['trashed=false'];
  clauses.push("mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'");
  if (sourceFolderId) clauses.push(`'${driveQueryLiteral(sourceFolderId, 220)}' in parents`);
  if (fileName) clauses.push(`name='${driveQueryLiteral(workbookFileName(fileName), 240)}'`);
  else if (query) clauses.push(`name contains '${driveQueryLiteral(query, 240)}'`);
  const result = await drive.files.list({
    q: clauses.join(' and '),
    pageSize: 10,
    fields: 'files(id,name,mimeType,modifiedTime,webViewLink,parents)',
    orderBy: 'modifiedTime desc',
    supportsAllDrives: true,
    includeItemsFromAllDrives: true,
  });
  const files = result.data && result.data.files || [];
  if (!files.length) throw Object.assign(new Error('No .xlsx source workbook matched the supplied sourceFileName/sourceQuery.'), {status: 404});
  if (files.length > 1 && !fileName) throw Object.assign(new Error('Multiple .xlsx workbooks matched sourceQuery. Provide sourceFileId or a more specific sourceFileName.'), {status: 409, matches: files.map(chatGptDriveFile)});
  return safeDriveFileId(files[0].id);
}

async function importXlsxWorkbookOperation({google, admin, auth, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const drive = google.drive({version: 'v3', auth});
  const sheetsApi = google.sheets({version: 'v4', auth});
  const parentFolderId = safeText(args.parentFolderId || args.folderId, 220) ? safeDriveFileId(args.parentFolderId || args.folderId) : '';
  let sourceFileId = safeText(args.sourceFileId || args.fileId, 220);
  const warnings = [];
  let workbookBuffer = workbookBufferFromBase64(args.workbookBase64 || args.uploadedWorkbookBase64 || args.fileBase64);
  let sourceMetadata = null;
  let sourceName = workbookFileName(args.fileName || args.name || args.title || 'workbook.xlsx');
  if (!sourceFileId && !workbookBuffer) sourceFileId = await resolveWorkbookSourceFile(drive, args);
  if (sourceFileId) {
    const sourceId = safeDriveFileId(sourceFileId);
    sourceMetadata = cleanDriveFile((await drive.files.get({fileId: sourceId, fields: driveFields(), supportsAllDrives: true})).data || {});
    sourceName = workbookFileName(args.fileName || sourceMetadata.name || sourceName);
    if (!workbookBuffer) {
      const downloaded = await drive.files.get({fileId: sourceId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
      workbookBuffer = Buffer.from(downloaded.data || []);
    }
  }
  if (!workbookBuffer) throw Object.assign(new Error('workbook_import_xlsx requires workbookBase64 or sourceFileId.'), {status: 400});
  const title = safeWorkbookTitle(args.title || args.titleOverride || sourceName, sourceName.replace(/\.xlsx$/i, ''));
  const expectedSheetNames = Array.isArray(args.expectedSheetNames) ? args.expectedSheetNames.map((name) => safeSheetTitle(name)).filter(Boolean) : [];
  const expectedCellCounts = normalizeExpectedCellCounts(args.expectedPopulatedCellCounts || args.sourcePopulatedCellCounts);
  const created = await drive.files.create({
    requestBody: {
      name: title,
      mimeType: 'application/vnd.google-apps.spreadsheet',
      ...(parentFolderId ? {parents: [parentFolderId]} : {}),
    },
    media: {
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      body: Readable.from(workbookBuffer),
    },
    fields: driveFields(),
    supportsAllDrives: true,
  });
  const metadata = cleanDriveFile(created.data || {});
  const spreadsheetId = safeDriveFileId(metadata.id);
  let spreadsheet = null;
  try {
    spreadsheet = cleanSpreadsheet((await sheetsApi.spreadsheets.get({
      spreadsheetId,
      fields: 'spreadsheetId,spreadsheetUrl,properties(title),sheets(properties(sheetId,title,index,gridProperties(rowCount,columnCount,frozenRowCount,frozenColumnCount)))',
    })).data || {});
  } catch (err) {
    warnings.push(`Converted workbook was created, but spreadsheet metadata could not be read: ${safeText(err.message || String(err), 240)}`);
    spreadsheet = {spreadsheetId, spreadsheetUrl: '', title, sheets: []};
  }
  const sheetNames = (spreadsheet.sheets || []).sort((a, b) => a.index - b.index).map((sheet) => sheet.title).filter(Boolean);
  if (expectedSheetNames.length) {
    const found = new Set(sheetNames);
    for (const expected of expectedSheetNames) {
      if (!found.has(expected)) warnings.push(`Expected worksheet was not found after Drive conversion: ${expected}`);
    }
  }
  const countResult = await destinationWorkbookCellCounts(sheetsApi, spreadsheetId, sheetNames);
  warnings.push(...countResult.warnings);
  const populatedCellCounts = countResult.counts;
  const populatedCellCountDiffs = [];
  for (const [name, sourceCount] of Object.entries(expectedCellCounts)) {
    if (!Object.prototype.hasOwnProperty.call(populatedCellCounts, name)) {
      populatedCellCountDiffs.push({sheetName: name, sourcePopulatedCells: sourceCount, destinationPopulatedCells: null, difference: null, status: 'missing_destination_sheet'});
      continue;
    }
    const destinationCount = populatedCellCounts[name];
    const difference = destinationCount === null ? null : destinationCount - sourceCount;
    if (difference !== 0) warnings.push(`Populated cell count differs for ${name}: source=${sourceCount} destination=${destinationCount}`);
    populatedCellCountDiffs.push({sheetName: name, sourcePopulatedCells: sourceCount, destinationPopulatedCells: destinationCount, difference, status: difference === 0 ? 'matched' : 'different'});
  }
  const result = {
    spreadsheetId,
    id: spreadsheetId,
    title,
    sourceFileId: sourceMetadata && sourceMetadata.id || sourceFileId || '',
    sourceName,
    sheetNames,
    sheetCount: sheetNames.length,
    populatedCellCounts,
    populatedCellCountDiffs,
    warnings,
    webViewLink: metadata.webViewLink || spreadsheet.spreadsheetUrl || '',
    spreadsheet,
    metadata,
    auditRequestId: requestId,
  };
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'workbook_import_xlsx',
    operation: 'workbook.importXlsx',
    requestId,
    fileId: spreadsheetId,
    affectedFileIds: [spreadsheetId],
    oldMetadata: sourceMetadata,
    newMetadata: metadata,
    oldParents: sourceMetadata && sourceMetadata.parents || [],
    newParents: metadata.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || `Imported Excel workbook ${sourceName} into native Google Sheet ${metadata.name || title}.`,
    result,
  });
  await recordActionAudit(admin, user, 'workbook.importXlsx', spreadsheetId, safeText(args.callerNote, 400) || `Imported Excel workbook ${sourceName} into native Google Sheet ${metadata.name || title}.`, requestId);
  return {...result, audit: audit.audit};
}

async function createSheetOperation({google, admin, auth, user, args = {}}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const title = safeText(args.title, 240) || 'Home Center Sheet';
  const sheetTitle = safeSheetTitle(args.sheetTitle, 'Sheet1');
  const parentFolderId = safeText(args.parentFolderId || args.folderId, 220) ? safeDriveFileId(args.parentFolderId || args.folderId) : '';
  const initialValues = safeSheetValues(args.values || args.initialValues || [], 200, 50);
  const sheets = google.sheets({version: 'v4', auth});
  const drive = google.drive({version: 'v3', auth});
  const created = await sheets.spreadsheets.create({
    requestBody: {
      properties: {title},
      sheets: [{properties: {title: sheetTitle}}],
    },
    fields: 'spreadsheetId,spreadsheetUrl,properties(title),sheets(properties(sheetId,title,index,gridProperties(rowCount,columnCount)))',
  });
  const spreadsheetId = safeDriveFileId(created.data && created.data.spreadsheetId);
  if (initialValues.length) {
    await sheets.spreadsheets.values.update({
      spreadsheetId,
      range: `${sheetTitle}!A1`,
      valueInputOption: 'USER_ENTERED',
      requestBody: {range: `${sheetTitle}!A1`, majorDimension: 'ROWS', values: initialValues},
    });
  }
  const beforeMove = await getDriveMetadata(drive, spreadsheetId);
  let metadata = beforeMove;
  if (parentFolderId) {
    metadata = cleanDriveFile((await drive.files.update({
      fileId: spreadsheetId,
      addParents: parentFolderId,
      removeParents: (beforeMove.parents || []).join(','),
      fields: driveFields(),
      supportsAllDrives: true,
    })).data || {});
  }
  const spreadsheet = cleanSpreadsheet(created.data || {});
  const result = {
    spreadsheetId,
    id: spreadsheetId,
    title,
    sheetTitle,
    spreadsheetUrl: spreadsheet.spreadsheetUrl || '',
    webViewLink: metadata.webViewLink || spreadsheet.spreadsheetUrl || '',
    parentFolderId: (metadata.parents || [])[0] || parentFolderId,
    spreadsheet,
    metadata,
    auditRequestId: requestId,
  };
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'sheets_create',
    operation: 'sheets.create',
    requestId,
    fileId: spreadsheetId,
    affectedFileIds: [spreadsheetId],
    oldMetadata: null,
    newMetadata: metadata,
    oldParents: [],
    newParents: metadata.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || `Created Google Sheet ${metadata.name || title}.`,
    result,
  });
  await recordActionAudit(admin, user, 'sheets.create', spreadsheetId, safeText(args.callerNote, 400) || `Created Google Sheet ${metadata.name || title}.`, requestId);
  return {...result, audit: audit.audit};
}

async function updateSheetValuesOperation({google, admin, auth, user, args = {}}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const spreadsheetId = safeDriveFileId(args.spreadsheetId);
  const range = safeSheetRange(args.range, '');
  if (!range) throw Object.assign(new Error('range is required for sheets_update_values.'), {status: 400});
  const values = safeSheetValues(args.values || [], 500, 50);
  if (!values.length) throw Object.assign(new Error('values must include at least one row.'), {status: 400});
  const sheets = google.sheets({version: 'v4', auth});
  const drive = google.drive({version: 'v3', auth});
  const before = await getDriveMetadata(drive, spreadsheetId);
  const updated = await sheets.spreadsheets.values.update({
    spreadsheetId,
    range,
    valueInputOption: safeText(args.valueInputOption, 40) === 'RAW' ? 'RAW' : 'USER_ENTERED',
    requestBody: {range, majorDimension: 'ROWS', values},
  });
  const after = await getDriveMetadata(drive, spreadsheetId);
  const result = {
    spreadsheetId,
    range,
    updated: updated.data || {},
    metadata: after,
    auditRequestId: requestId,
  };
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'sheets_update_values',
    operation: 'sheets.updateValues',
    requestId,
    fileId: spreadsheetId,
    affectedFileIds: [spreadsheetId],
    oldMetadata: before,
    newMetadata: after,
    oldParents: before.parents || [],
    newParents: after.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || `Updated ${range} in Google Sheet ${after.name || spreadsheetId}.`,
    result,
  });
  await recordActionAudit(admin, user, 'sheets.updateValues', spreadsheetId, safeText(args.callerNote, 400) || `Updated ${range} in Google Sheet ${after.name || spreadsheetId}.`, requestId);
  return {...result, audit: audit.audit};
}

async function createDriveFolderOperation({google, admin, auth, user, args = {}}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const name = safeText(args.name, 240);
  if (!name) {
    const err = new Error('name is required.');
    err.status = 400;
    throw err;
  }
  const parentFolderId = safeText(args.parentFolderId, 220) ? safeDriveFileId(args.parentFolderId) : '';
  const drive = google.drive({version: 'v3', auth});
  const created = await drive.files.create({
    requestBody: {name, mimeType: 'application/vnd.google-apps.folder', ...(parentFolderId ? {parents: [parentFolderId]} : {})},
    fields: driveFields(),
    supportsAllDrives: true,
  });
  const metadata = cleanDriveFile(created.data || {});
  const result = {
    folderId: metadata.id,
    id: metadata.id,
    name: metadata.name,
    webViewLink: metadata.webViewLink || '',
    parentFolderId: (metadata.parents || [])[0] || parentFolderId,
    metadata,
    auditRequestId: requestId,
  };
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'drive_create_folder',
    operation: 'drive.createFolder',
    requestId,
    fileId: metadata.id,
    affectedFileIds: [metadata.id],
    oldMetadata: null,
    newMetadata: metadata,
    oldParents: [],
    newParents: metadata.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || driveBridgeWriteSummary('drive.createFolder', metadata, parentFolderId),
    result,
  });
  return {...result, audit: audit.audit};
}

async function createGoogleDocOperation({google, admin, auth, user, args = {}}) {
  const requestId = createRequestId(args.requestId);
  const title = safeText(args.title, 240);
  if (!title) throw bridgeStageError('DOCS_CREATE_INVALID_INPUT', 'title is required.', 'request_validation', 400);
  const parentFolderId = safeText(args.parentFolderId, 220) ? safeDriveFileId(args.parentFolderId) : '';
  const initialText = boundedText(args.initialText, 200000);
  const docs = google.docs({version: 'v1', auth});
  const drive = google.drive({version: 'v3', auth});
  const stateRef = mcpCollection(admin, 'driveBridgeOperationState').doc(requestId);
  let state = null;

  logDocsCreate('request_accepted', {...args, requestId}, {parentFolderId});
  let existing;
  try {
    existing = await existingAudit(admin, requestId);
    const stateSnap = await stateRef.get();
    state = stateSnap.exists ? stateSnap.data() || {} : null;
  } catch (err) {
    logDocsCreate('audit_state_read_failed', {...args, requestId}, {errorCode: 'DOCS_CREATE_AUDIT_FAILED', providerStatus: providerStatus(err)});
    return docsCreateErrorPayload(bridgeStageError('DOCS_CREATE_AUDIT_FAILED', 'Could not read idempotency/audit state before creating the document.', 'idempotency_state_read', 503, {googleStatus: providerStatus(err)}), {...args, requestId});
  }
  if (existing && existing.status === 'success' && existing.result) {
    logDocsCreate('idempotent_success', {...args, requestId}, {documentId: existing.fileId || existing.result.documentId || ''});
    return {...existing.result, idempotent: true, audit: existing};
  }

  let documentId = safeText(state && state.documentId, 220);
  if (!documentId) {
    try {
      logDocsCreate('google_create_start', {...args, requestId});
      const created = await docs.documents.create({requestBody: {title}});
      documentId = safeDriveFileId(created.data && created.data.documentId);
      await stateRef.set({requestId, operation: 'docs.create', status: 'file_created', documentId, title, parentFolderId, initialTextLength: initialText.length, actor: user.email || user.uid || 'unknown', createdAtMs: nowMs(), updatedAtMs: nowMs()}, {merge: true});
      logDocsCreate('google_create_success', {...args, requestId}, {documentId});
    } catch (err) {
      logDocsCreate('google_create_failed', {...args, requestId}, {errorCode: 'DOCS_CREATE_GOOGLE_CREATE_FAILED', googleStatus: providerStatus(err)});
      throw bridgeStageError('DOCS_CREATE_GOOGLE_CREATE_FAILED', providerMessage(err), 'google_create', providerStatus(err), {googleStatus: providerStatus(err)});
    }
  } else {
    logDocsCreate('resume_existing_file', {...args, requestId}, {documentId, previousStatus: safeText(state && state.status, 120)});
  }

  const partial = {documentId, id: documentId, title, parentFolderId, auditRequestId: requestId};
  if (initialText && !(state && state.textInserted === true)) {
    try {
      logDocsCreate('text_insert_start', {...args, requestId}, {documentId});
      await docs.documents.batchUpdate({
        documentId,
        requestBody: {requests: [{insertText: {location: {index: 1}, text: initialText}}]},
      });
      await stateRef.set({status: 'text_inserted', textInserted: true, updatedAtMs: nowMs()}, {merge: true});
      logDocsCreate('text_insert_success', {...args, requestId}, {documentId});
    } catch (err) {
      await stateRef.set({status: 'text_insert_failed', textInserted: false, errorCode: 'DOCS_CREATE_TEXT_INSERT_FAILED', errorStage: 'text_insert', updatedAtMs: nowMs()}, {merge: true}).catch(() => {});
      logDocsCreate('text_insert_failed', {...args, requestId}, {documentId, errorCode: 'DOCS_CREATE_TEXT_INSERT_FAILED', googleStatus: providerStatus(err)});
      return docsCreateErrorPayload(bridgeStageError('DOCS_CREATE_TEXT_INSERT_FAILED', providerMessage(err), 'text_insert', providerStatus(err), {googleStatus: providerStatus(err), partial}), {...args, requestId}, partial);
    }
  }

  try {
    if (parentFolderId && !(state && state.parentApplied === true)) {
      logDocsCreate('parent_move_start', {...args, requestId}, {documentId, parentFolderId});
      await drive.files.update({fileId: documentId, addParents: parentFolderId, requestBody: {}, fields: 'id,parents', supportsAllDrives: true});
      await stateRef.set({status: 'parent_applied', parentApplied: true, updatedAtMs: nowMs()}, {merge: true});
      logDocsCreate('parent_move_success', {...args, requestId}, {documentId, parentFolderId});
    }
  } catch (err) {
    const code = providerStatus(err) === 404 ? 'DOCS_CREATE_PARENT_NOT_FOUND' : 'DOCS_CREATE_GOOGLE_CREATE_FAILED';
    await stateRef.set({status: 'parent_move_failed', errorCode: code, errorStage: 'parent_move', updatedAtMs: nowMs()}, {merge: true}).catch(() => {});
    logDocsCreate('parent_move_failed', {...args, requestId}, {documentId, parentFolderId, errorCode: code, googleStatus: providerStatus(err)});
    return docsCreateErrorPayload(bridgeStageError(code, providerMessage(err), 'parent_move', providerStatus(err), {googleStatus: providerStatus(err), partial}), {...args, requestId}, partial);
  }

  let metadata;
  try {
    logDocsCreate('metadata_read_start', {...args, requestId}, {documentId});
    const file = await drive.files.get({fileId: documentId, fields: driveFields(), supportsAllDrives: true});
    metadata = cleanDriveFile(file.data || {});
    await stateRef.set({status: 'metadata_read', metadata, updatedAtMs: nowMs()}, {merge: true});
    logDocsCreate('metadata_read_success', {...args, requestId}, {documentId});
  } catch (err) {
    await stateRef.set({status: 'metadata_read_failed', errorCode: 'DOCS_CREATE_GOOGLE_CREATE_FAILED', errorStage: 'metadata_read', updatedAtMs: nowMs()}, {merge: true}).catch(() => {});
    logDocsCreate('metadata_read_failed', {...args, requestId}, {documentId, errorCode: 'DOCS_CREATE_GOOGLE_CREATE_FAILED', googleStatus: providerStatus(err)});
    return docsCreateErrorPayload(bridgeStageError('DOCS_CREATE_GOOGLE_CREATE_FAILED', providerMessage(err), 'metadata_read', providerStatus(err), {googleStatus: providerStatus(err), partial}), {...args, requestId}, partial);
  }

  const result = {
    documentId,
    id: documentId,
    title: metadata.name || title,
    name: metadata.name || title,
    webViewLink: metadata.webViewLink || '',
    parentFolderId: (metadata.parents || [])[0] || parentFolderId,
    metadata,
    auditRequestId: requestId,
  };
  try {
    const audit = await auditWrite(admin, {
      actor: user.email || user.uid || 'unknown',
      authKind: user.authKind,
      tool: 'docs_create',
      operation: 'docs.create',
      requestId,
      fileId: documentId,
      affectedFileIds: [documentId],
      oldMetadata: null,
      newMetadata: metadata,
      oldParents: [],
      newParents: metadata.parents || [],
      reversible: false,
      rollback: null,
      callerNote: args.callerNote,
      providerSummary: safeText(args.callerNote, 400) || driveBridgeWriteSummary('docs.create', metadata, parentFolderId),
      result,
    });
    await stateRef.set({status: 'success', auditWritten: true, updatedAtMs: nowMs()}, {merge: true});
    logDocsCreate('audit_success', {...args, requestId}, {documentId});
    return {...result, audit: audit.audit};
  } catch (err) {
    await stateRef.set({status: 'audit_failed', auditWritten: false, errorCode: 'DOCS_CREATE_AUDIT_FAILED', errorStage: 'audit_write', updatedAtMs: nowMs()}, {merge: true}).catch(() => {});
    logDocsCreate('audit_failed', {...args, requestId}, {documentId, errorCode: 'DOCS_CREATE_AUDIT_FAILED', providerStatus: providerStatus(err)});
    return docsCreateErrorPayload(bridgeStageError('DOCS_CREATE_AUDIT_FAILED', providerMessage(err), 'audit_write', 503, {partial: result}), {...args, requestId}, result);
  }
}



function decodeSnapshotContent(args = {}) {
  const hasBase64 = typeof args.contentBase64 === 'string' && args.contentBase64.trim();
  const hasText = typeof args.content === 'string';
  if (hasBase64 && hasText) {
    const err = new Error('Provide either content or contentBase64, not both.');
    err.status = 400;
    throw err;
  }
  if (hasBase64) {
    try {
      return Buffer.from(String(args.contentBase64).trim(), 'base64');
    } catch (_) {
      const err = new Error('contentBase64 must be valid Base64.');
      err.status = 400;
      throw err;
    }
  }
  if (hasText) return Buffer.from(args.content, 'utf8');
  const err = new Error('content or contentBase64 is required.');
  err.status = 400;
  throw err;
}

function sha256Hex(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

function verifySnapshotDigest(buffer, args = {}) {
  const actualByteCount = buffer.length;
  const actualSha256 = sha256Hex(buffer);
  const expectedByteCount = args.byteCount === undefined || args.byteCount === null || args.byteCount === '' ? null : Math.floor(safeNumber(args.byteCount, -1));
  const expectedSha256 = safeText(args.sha256 || args.expectedSha256, 128).toLowerCase();
  if (expectedByteCount !== null && expectedByteCount !== actualByteCount) {
    const err = new Error(`byteCount mismatch: expected ${expectedByteCount}, got ${actualByteCount}.`);
    err.status = 400;
    throw err;
  }
  if (expectedSha256 && expectedSha256 !== actualSha256) {
    const err = new Error(`sha256 mismatch: expected ${expectedSha256}, got ${actualSha256}.`);
    err.status = 400;
    throw err;
  }
  return {byteCount: actualByteCount, sha256: actualSha256};
}

function mediaBuffer(data) {
  if (Buffer.isBuffer(data)) return data;
  if (data instanceof ArrayBuffer) return Buffer.from(data);
  if (ArrayBuffer.isView(data)) return Buffer.from(data.buffer, data.byteOffset, data.byteLength);
  return Buffer.from(String(data || ''), 'utf8');
}

async function publishContextSnapshotOperation({google, admin, auth, user, args = {}}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};

  const name = safeText(args.name || args.fileName || args.title, 240);
  if (!name) {
    const err = new Error('name is required.');
    err.status = 400;
    throw err;
  }
  const parentFolderId = safeText(args.parentFolderId, 220) ? safeDriveFileId(args.parentFolderId) : '';
  const targetFileId = safeText(args.fileId || args.targetFileId, 220) ? safeDriveFileId(args.fileId || args.targetFileId) : '';
  const mimeType = safeText(args.mimeType, 160) || 'text/markdown';
  if (!/^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(mimeType)) {
    const err = new Error('mimeType must be a valid MIME type.');
    err.status = 400;
    throw err;
  }

  const content = decodeSnapshotContent(args);
  const digest = verifySnapshotDigest(content, args);
  const drive = google.drive({version: 'v3', auth});
  const before = targetFileId ? await getDriveMetadata(drive, targetFileId) : null;
  const media = {mimeType, body: Readable.from([content])};
  const requestBody = {name, mimeType, ...(parentFolderId && !targetFileId ? {parents: [parentFolderId]} : {})};
  const writeResult = targetFileId
    ? await drive.files.update({fileId: targetFileId, requestBody: {name, mimeType}, media, fields: driveFields(), supportsAllDrives: true})
    : await drive.files.create({requestBody, media, fields: driveFields(), supportsAllDrives: true});
  const metadata = cleanDriveFile(writeResult.data || {});
  const fileId = safeDriveFileId(metadata.id || targetFileId);
  if (parentFolderId && targetFileId) {
    const parents = metadata.parents || [];
    if (!parents.includes(parentFolderId)) {
      await drive.files.update({fileId, addParents: parentFolderId, requestBody: {}, fields: 'id,parents', supportsAllDrives: true});
    }
  }
  const after = await getDriveMetadata(drive, fileId).catch(() => metadata);
  const readback = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
  const readbackBuffer = mediaBuffer(readback.data);
  const readbackDigest = {byteCount: readbackBuffer.length, sha256: sha256Hex(readbackBuffer)};
  const verified = readbackDigest.byteCount === digest.byteCount && readbackDigest.sha256 === digest.sha256;
  if (!verified) {
    const err = new Error(`Drive readback verification failed for ${name}: wrote ${digest.byteCount}/${digest.sha256}, read ${readbackDigest.byteCount}/${readbackDigest.sha256}.`);
    err.status = 502;
    throw err;
  }

  const result = {
    fileId,
    id: fileId,
    name: after.name || metadata.name || name,
    mimeType: after.mimeType || metadata.mimeType || mimeType,
    webViewLink: after.webViewLink || metadata.webViewLink || '',
    parentFolderId: ((after.parents || metadata.parents || [])[0]) || parentFolderId,
    byteCount: digest.byteCount,
    sha256: digest.sha256,
    readbackByteCount: readbackDigest.byteCount,
    readbackSha256: readbackDigest.sha256,
    verified: true,
    metadata: after,
    auditRequestId: requestId,
  };
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'context_sync.publish_snapshot',
    operation: 'contextSync.publishSnapshot',
    requestId,
    fileId,
    affectedFileIds: [fileId],
    oldMetadata: before,
    newMetadata: after,
    oldParents: before ? before.parents || [] : [],
    newParents: after.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || `Published ${name} (${digest.byteCount} bytes, sha256 ${digest.sha256}).`,
    result,
  });
  await recordActionAudit(admin, user, 'contextSync.publishSnapshot', fileId, safeText(args.callerNote, 400) || `Published ${name} (${digest.byteCount} bytes).`, requestId);
  return {...result, audit: audit.audit};
}


function cartesiaAudioArtifactFormat(args = {}) {
  const format = safeText(args.format || args.container || 'wav', 20).toLowerCase();
  if (format === 'wav' || format === 'wave') return {format: 'wav', extension: 'wav', mimeType: 'audio/wav'};
  if (format === 'raw' || format === 'pcm') return {format: 'raw', extension: 'pcm', mimeType: 'application/octet-stream'};
  const err = new Error('format must be wav or raw.');
  err.status = 400;
  throw err;
}

function safeArtifactName(value, fallback) {
  const name = safeText(value, 240) || fallback;
  return name.replace(/[\\/:*?"<>|]+/g, '-').replace(/\s+/g, ' ').trim().slice(0, 240) || fallback;
}

function normalizeCartesiaSegments(args = {}, defaultVoiceName = CARTESIA_DEFAULT_VOICE_NAME, defaultModelId = CARTESIA_DEFAULT_MODEL_ID, defaultVoiceId = '') {
  const defaultPitchSemitones = cartesiaPitchShift.safePitchSemitones(args.pitchSemitones, 'pitchSemitones');
  const rawSegments = Array.isArray(args.segments) ? args.segments : [];
  const segments = rawSegments.length ? rawSegments : [{
    text: args.text || args.transcript,
    speaker: args.speaker,
    voiceName: args.voiceName,
    voiceId: args.voiceId,
    modelId: args.modelId,
    pitchSemitones: args.pitchSemitones,
  }];
  if (!segments.length || segments.length > 80) {
    const err = new Error('segments must contain 1 to 80 items.');
    err.status = 400;
    throw err;
  }
  const normalized = segments.map((segment, index) => {
    const item = segment && typeof segment === 'object' && !Array.isArray(segment) ? segment : {};
    const text = safeText(item.text || item.transcript, 12000);
    if (!text) {
      const err = new Error('segments[' + index + '].text is required.');
      err.status = 400;
      throw err;
    }
    return {
      index,
      speaker: safeText(item.speaker || item.speakerName || item.character || item.characterId, 120),
      text,
      voiceName: safeText(item.voiceName, 120) || defaultVoiceName,
      voiceId: safeText(item.voiceId, 160) || defaultVoiceId,
      modelId: safeText(item.modelId, 120) || defaultModelId,
      pitchSemitones: item.pitchSemitones === undefined ? defaultPitchSemitones : cartesiaPitchShift.safePitchSemitones(item.pitchSemitones, 'segments[' + index + '].pitchSemitones'),
    };
  });
  const totalChars = normalized.reduce((sum, segment) => sum + segment.text.length, 0);
  if (totalChars > 48000) {
    const err = new Error('segments total text must be 48000 characters or less.');
    err.status = 400;
    throw err;
  }
  return normalized;
}

function pcmSilenceBytes(sampleRate, pauseMs) {
  const ms = Math.max(0, Math.min(5000, Math.floor(safeNumber(pauseMs, 0)) || 0));
  if (!ms) return Buffer.alloc(0);
  const sampleCount = Math.floor(sampleRate * ms / 1000);
  return Buffer.alloc(sampleCount * 2);
}

function wavHeader(byteCount, sampleRate) {
  const header = Buffer.alloc(44);
  const channels = 1;
  const bitsPerSample = 16;
  const byteRate = sampleRate * channels * bitsPerSample / 8;
  const blockAlign = channels * bitsPerSample / 8;
  header.write('RIFF', 0, 'ascii');
  header.writeUInt32LE(36 + byteCount, 4);
  header.write('WAVE', 8, 'ascii');
  header.write('fmt ', 12, 'ascii');
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(channels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(bitsPerSample, 34);
  header.write('data', 36, 'ascii');
  header.writeUInt32LE(byteCount, 40);
  return header;
}

function wrapPcmAsWav(pcm, sampleRate) {
  return Buffer.concat([wavHeader(pcm.length, sampleRate), pcm]);
}

async function synthesizeCartesiaSegmentPcm({cartesiaApiKey, segment, sampleRate}) {
  const speech = await openCartesiaStream(segment.text, {apiKeyGetter: cartesiaApiKey, voiceName: segment.voiceName, voiceId: segment.voiceId, modelId: segment.modelId, format: 'raw', sampleRate});
  const audioResponse = speech.response;
  if (!audioResponse.ok) {
    const detail = await audioResponse.text().catch(() => '');
    const err = new Error('Cartesia HTTP ' + audioResponse.status + (detail ? ': ' + safeText(detail, 500) : ''));
    err.status = audioResponse.status;
    throw err;
  }
  const pcm = mediaBuffer(await audioResponse.arrayBuffer());
  if (!pcm.length) {
    const err = new Error('Cartesia returned empty audio for segment ' + segment.index + '.');
    err.status = 502;
    throw err;
  }
  if ((pcm.length & 1) === 1) {
    const err = new Error('Cartesia returned odd-length PCM for segment ' + segment.index + '.');
    err.status = 502;
    throw err;
  }
  const shifted = segment.pitchSemitones === 0
    ? {pcm, bypassed: true, processor: 'none', pitchScale: 1, inputFrames: pcm.length / 2, outputFrames: pcm.length / 2, durationRatio: 1}
    : await cartesiaPitchShift.pitchShiftPcm16(pcm, {sampleRate, channels: 1, pitchSemitones: segment.pitchSemitones});
  return {
    pcm: shifted.pcm,
    voiceName: speech.voiceName,
    voiceId: speech.voiceId,
    modelId: speech.modelId,
    textCharCount: segment.text.length,
    speaker: segment.speaker,
    index: segment.index,
    pitchSemitones: segment.pitchSemitones,
    pitchScale: shifted.pitchScale,
    pitchProcessor: shifted.processor,
    pitchBypassed: Boolean(shifted.bypassed),
    inputByteCount: pcm.length,
    inputFrameCount: shifted.inputFrames || (pcm.length / 2),
    outputFrameCount: shifted.outputFrames || (shifted.pcm.length / 2),
    durationRatio: shifted.durationRatio || 1,
  };
}
async function synthesizeCartesiaAudioBytes({cartesiaApiKey, args, audioFormat, sampleRate}) {
  const defaultPitchSemitones = cartesiaPitchShift.safePitchSemitones(args.pitchSemitones, 'pitchSemitones');
  const segments = normalizeCartesiaSegments(args, safeText(args.voiceName, 120) || CARTESIA_DEFAULT_VOICE_NAME, safeText(args.modelId, 120) || CARTESIA_DEFAULT_MODEL_ID, safeText(args.voiceId, 160));
  const hasPitchShift = segments.some((segment) => segment.pitchSemitones !== 0);
  if (segments.length === 1 && !Array.isArray(args.segments) && !hasPitchShift) {
    const segment = segments[0];
    const speech = await openCartesiaStream(segment.text, {apiKeyGetter: cartesiaApiKey, voiceName: segment.voiceName, voiceId: segment.voiceId, modelId: segment.modelId, format: audioFormat.format, sampleRate});
    const audioResponse = speech.response;
    if (!audioResponse.ok) {
      const detail = await audioResponse.text().catch(() => '');
      const err = new Error('Cartesia HTTP ' + audioResponse.status + (detail ? ': ' + safeText(detail, 500) : ''));
      err.status = audioResponse.status;
      throw err;
    }
    const audio = mediaBuffer(await audioResponse.arrayBuffer());
    if (!audio.length) {
      const err = new Error('Cartesia returned empty audio.');
      err.status = 502;
      throw err;
    }
    return {audio, defaultPitchSemitones, segments: [{index: 0, speaker: segment.speaker, voiceName: speech.voiceName, voiceId: speech.voiceId, modelId: speech.modelId, textCharCount: segment.text.length, pitchSemitones: 0, pitchScale: 1, pitchProcessor: 'none', pitchBypassed: true}], segmentCount: 1};
  }

  const pause = pcmSilenceBytes(sampleRate, args.pauseMs);
  const synthesized = [];
  for (const segment of segments) {
    synthesized.push(await synthesizeCartesiaSegmentPcm({cartesiaApiKey, segment, sampleRate}));
  }
  const pcmParts = [];
  synthesized.forEach((segment, index) => {
    if (index > 0 && pause.length) pcmParts.push(pause);
    pcmParts.push(segment.pcm);
  });
  const pcm = Buffer.concat(pcmParts);
  const audio = audioFormat.format === 'wav' ? wrapPcmAsWav(pcm, sampleRate) : pcm;
  return {
    audio,
    segmentCount: synthesized.length,
    stitched: true,
    defaultPitchSemitones,
    segmentPauseMs: Math.max(0, Math.min(5000, Math.floor(safeNumber(args.pauseMs, 0)) || 0)),
    segments: synthesized.map((segment) => ({index: segment.index, speaker: segment.speaker, voiceName: segment.voiceName, voiceId: segment.voiceId, modelId: segment.modelId, textCharCoun