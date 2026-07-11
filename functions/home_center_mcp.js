const {createHash, randomBytes, randomUUID} = require('node:crypto');
const {Readable} = require('node:stream');
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {SSEServerTransport} = require('@modelcontextprotocol/sdk/server/sse.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');
const {ListToolsRequestSchema} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/types.js');
const {normalizeObjectSchema} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/server/zod-compat.js');
const {toJsonSchemaCompat} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/server/zod-json-schema-compat.js');
const express = require('express');
const {z} = require('zod/v4');

const DEFAULT_MCP_PUBLIC_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
const MCP_PUBLIC_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || DEFAULT_MCP_PUBLIC_BASE;
const MCP_RESOURCE = `${MCP_PUBLIC_BASE}/mcp`;
const MCP_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/.well-known/oauth-protected-resource`;
const MCP_LEGACY_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/oauth-protected-resource`;
const MCP_COMPAT_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/oauth-protected-resource-v2`;
const MCP_AUTHORIZATION_SERVER_METADATA = `${MCP_PUBLIC_BASE}/.well-known/oauth-authorization-server`;
const MCP_GOOGLE_CALLBACK = process.env.HOME_CENTER_MCP_GOOGLE_CALLBACK || `${MCP_PUBLIC_BASE}/oauth/google-callback`;
const COMMAND_CENTER_MCP_URL = process.env.COMMAND_CENTER_MCP_URL || 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const MCP_REQUIRED_SCOPES = [
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/spreadsheets',
];
const MCP_OAUTH_SECURITY_SCHEMES = [{type: 'oauth2', scopes: MCP_REQUIRED_SCOPES}];

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
    version: '2026-07-11.home-center-command-center-handoff-v2',
    invocationTool: 'command_center_operation',
    commandCenterMcpUrl: COMMAND_CENTER_MCP_URL,
    purpose: 'Expose Command Center dispatch and managed knowledge-bucket operations through the already-installed Home Center MCP connector so ChatGPT can create, inspect, resume, revise, authorize, and preserve worker knowledge without discovering a second MCP app.',
    operations: {
      health: {summary: 'Check Command Center MCP health and tool exposure.', readOnly: true, input: {}},
      'projects.resolve': {summary: 'Resolve an active project before creating a job.', readOnly: false, input: {repository: 'optional string', capability: 'optional string', projectId: 'optional string', idempotencyKey: 'string'}},
      'projects.get': {summary: 'Read one persisted Command Center project packet.', readOnly: true, input: {projectId: 'string'}},
      'projects.upsert': {summary: 'Create or update a durable Command Center project binding.', readOnly: false, input: {projectId: 'string', repository: 'optional string', capability: 'optional string', repositoryBinding: 'optional object', availableWorkers: 'optional string[]', idempotencyKey: 'string'}},
      'jobs.create': {summary: 'Create a durable worker ticket/job.', readOnly: false, input: {projectId: 'string', title: 'string', objective: 'string', acceptanceCriteria: 'string[]', workerRequirements: 'string[]', mutationPolicy: 'object', idempotencyKey: 'string'}},
      'jobs.create_followup': {summary: 'Create a new linked invocation from a source job handoff without rewriting the old job.', readOnly: false, input: {sourceJobId: 'string', title: 'string', objective: 'string', acceptanceCriteria: 'optional string[]', constraints: 'optional string[]', mutationPolicy: 'optional object', idempotencyKey: 'string'}},
      'jobs.get': {summary: 'Read one Command Center job packet.', readOnly: true, input: {jobId: 'string'}},
      'jobs.list': {summary: 'List recent Command Center jobs.', readOnly: true, input: {projectId: 'optional string', status: 'optional string', limit: 'optional number'}},
      'jobs.reconcile_stale': {summary: 'Dry-run or expire stale nonterminal Command Center jobs and leases.', readOnly: false, input: {dryRun: 'optional boolean', olderThanMs: 'optional number', statuses: 'optional string[]', limit: 'optional number', idempotencyKey: 'required when dryRun=false'}},
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
      'bucket.get_layout': {summary: 'Read Command Center managed knowledge bucket lanes and storage policy.', readOnly: true, input: {}},
      'bucket.put_object': {summary: 'Write durable execution memory, scratch/promoted skills, or cross-repo notes. Secrets are rejected.', readOnly: false, input: {kind: 'memory.past_log|memory.current_condensed|skill.scratch|skill.promoted|note.cross_repo', title: 'string', summary: 'optional string', body: 'optional string', objectUri: 'optional string', projectId: 'optional string', repository: 'optional string', jobId: 'optional string', tags: 'optional string[]', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'bucket.get_object': {summary: 'Read one Command Center bucket object by id.', readOnly: true, input: {objectId: 'string'}},
      'bucket.list_objects': {summary: 'List Command Center bucket objects by kind, project, repository, job, or tag.', readOnly: true, input: {kind: 'optional string', projectId: 'optional string', repository: 'optional string', jobId: 'optional string', tag: 'optional string', limit: 'optional number'}},
      'bucket.promote_skill': {summary: 'Promote a scratch skill bucket object into the promoted skill lane with provenance.', readOnly: false, input: {objectId: 'string', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
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

function mcpTextContentJson(result, label) {
  const text = (((result || {}).content || []).find((item) => item && item.type === 'text') || {}).text || '';
  if (!text) return result;
  return parseJsonPayload(text, label);
}

async function commandCenterOperationRunOperation({extra, args = {}}) {
  const operation = safeText(args.operation || args.type || args.toolName, 120);
  const toolName = commandCenterToolName(operation);
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? {...args.args} : {...args};
  delete operationArgs.operation;
  delete operationArgs.type;
  delete operationArgs.toolName;
  delete operationArgs.args;
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
          inputSchema: mcpToolJsonSchema(tool.inputSchema, 'input'),
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

function githubHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'User-Agent': 'home-center-mcp',
    'X-GitHub-Api-Version': '2022-11-28',
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

async function appendGoogleDocOperation({google, admin, auth, user, args = {}}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const docs = google.docs({version: 'v1', auth});
  const drive = google.drive({version: 'v3', auth});
  const documentId = safeDriveFileId(args.documentId);
  const heading = safeText(args.heading, 180);
  const bodyText = safeText(args.text, 12000);
  if (!bodyText) {
    const err = new Error('text is required');
    err.status = 400;
    throw err;
  }
  const before = await getDriveMetadata(drive, documentId);
  const doc = await docs.documents.get({documentId, fields: 'body(content(endIndex))'});
  const content = (((doc.data || {}).body || {}).content || []);
  const last = content.length ? content[content.length - 1] : {};
  const endIndex = Math.max(1, safeNumber(last.endIndex, 1) - 1);
  const appendText = (heading ? '\n\n' + heading + '\n' : '\n\n') + bodyText + '\n';
  await docs.documents.batchUpdate({
    documentId,
    requestBody: {requests: [{insertText: {location: {index: endIndex}, text: appendText}}]},
  });
  const file = await drive.files.get({fileId: documentId, fields: driveFields(), supportsAllDrives: true});
  const after = cleanDriveFile(file.data || {});
  const result = {documentId, revisionSummary: 'Appended ' + bodyText.length + ' characters.', webViewLink: after.webViewLink || '', metadata: after, auditRequestId: requestId};
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'docs_append',
    operation: 'docs.append',
    requestId,
    fileId: documentId,
    affectedFileIds: [documentId],
    oldMetadata: before,
    newMetadata: after,
    oldParents: before.parents || [],
    newParents: after.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || ('Appended ' + bodyText.length + ' characters' + (heading ? ' under ' + heading : '') + '.'),
    result,
  });
  await recordActionAudit(admin, user, 'docs.append', documentId, safeText(args.callerNote, 400) || ('Appended ' + bodyText.length + ' characters' + (heading ? ' under ' + heading : '') + '.'), requestId);
  return {...result, audit: audit.audit};
}

function workflowOperationRequestId(workflowId, operation = {}, index = 0) {
  const supplied = safeText(operation.requestId, 160);
  return supplied ? stableRequestId(supplied) : stableRequestId(workflowId + ':' + (index + 1));
}

function workflowOutputKey(operation = {}, index = 0) {
  return safeText(operation.saveAs || operation.outputKey || operation.operationId, 80) || ('step' + (index + 1));
}

function workflowResolvedId(value, outputs = {}) {
  const raw = safeText(value, 220);
  if (!raw) return '';
  if (raw.charAt(0) === '$') return safeText(outputs[raw.slice(1)], 220);
  if (Object.prototype.hasOwnProperty.call(outputs, raw)) return safeText(outputs[raw], 220);
  return raw;
}

function workflowOperationSummary(operation = {}, index = 0) {
  const type = safeText(operation.type || operation.toolName || operation.tool, 120);
  const targetName = safeText(operation.targetName || operation.name || operation.title || operation.newName || operation.heading, 240);
  return String(index + 1) + '. ' + type + (targetName ? ': ' + targetName : '');
}

function commandCenterDriveOperationEntries() {
  return Object.fromEntries(Object.entries(commandCenterOperationRegistry().operations).map(([operation, meta]) => {
    const prefixed = `command_center.${operation}`;
    return [prefixed, {
      ...meta,
      summary: 'Command Center bridge: ' + meta.summary,
      commandCenterOperation: operation,
      invocationTool: 'drive_operation',
      preferredNativeTool: 'command_center_operation',
    }];
  }));
}

function driveOperationRegistry() {
  return {
    version: '2026-07-11.command-center-drive-operation-v1',
    invocationTool: 'drive_operation',
    cachePolicy: 'New bridge, simulation, and Command Center operations should be invokable through drive_operation so ChatGPT does not need a top-level MCP tool refresh for every backend code change. Agents should rediscover this registry through capabilities or health before claiming an operation is unavailable.',
    operations: {
      drive_create_folder: {
        summary: 'Create a Google Drive folder and audit the write.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {name: 'string', parentFolderId: 'optional string', requestId: 'string', callerNote: 'optional string'},
      },
      docs_create: {
        summary: 'Create a Google Doc, optionally seed text and parent folder, then audit the write.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'],
        input: {title: 'string', parentFolderId: 'optional string', initialText: 'optional string', requestId: 'string', callerNote: 'optional string'},
      },
      docs_append: {
        summary: 'Append text to an existing Google Doc and audit the write.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'],
        input: {documentId: 'string', heading: 'optional string', text: 'string', requestId: 'string', callerNote: 'optional string'},
      },
      'context_sync.publish_snapshot': {
        summary: 'Publish a durable text/Markdown snapshot file to Drive, verify byte count and SHA-256 by media readback, and audit the write.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {name: 'string', parentFolderId: 'optional string', fileId: 'optional existing Drive file id to replace', content: 'optional UTF-8 text content', contentBase64: 'optional Base64 bytes; use instead of content', mimeType: 'optional MIME type, default text/markdown', byteCount: 'optional expected byte count', sha256: 'optional expected SHA-256 hex', requestId: 'string', callerNote: 'optional string'},
        output: {fileId: 'string', byteCount: 'number', sha256: 'string', readbackByteCount: 'number', readbackSha256: 'string', verified: 'boolean', audit: 'object'},
        agentRecipe: {
          whenUserSays: 'Back up or sync Codex context, AGENTS.md, skills, memories, manifests, or other local text snapshots to Drive.',
          prefer: 'Call drive_operation with operation=context_sync.publish_snapshot. Use Home Center MCP only; do not use rclone for this workflow.',
          verification: 'Pass byteCount and sha256 from the local manifest. Treat verified=true as the acceptance signal because the operation reads the Drive media back and hashes it.',
        },
      },
      workbook_import_xlsx: {
        summary: 'Migrate a Drive-hosted or client-supplied .xlsx workbook into a native Google Sheets workbook using Google Drive conversion.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'],
        input: {workbookBase64: 'optional complete base64 .xlsx bytes; use only when the client can provide the full file payload', sourceFileId: 'preferred Drive file id for an existing .xlsx', sourceFileName: 'preferred Drive .xlsx filename to resolve when sourceFileId is not known', sourceQuery: 'optional Drive filename query', sourceFolderId: 'optional source folder id for resolving sourceFileName/sourceQuery', fileName: 'optional original filename', title: 'optional native Sheet title override', parentFolderId: 'optional destination folder id', expectedSheetNames: 'optional string[]', expectedPopulatedCellCounts: 'optional object', requestId: 'string', callerNote: 'optional string'},
        output: {spreadsheetId: 'string', sheetNames: 'string[]', warnings: 'string[]', populatedCellCountDiffs: 'array', audit: 'object'},
        agentRecipe: {
          whenUserSays: 'Import or migrate an Excel workbook into Google Sheets.',
          prefer: 'If the workbook is already in Drive, call drive_operation with operation=workbook_import_xlsx and args.sourceFileId, or args.sourceFileName plus optional sourceFolderId. Do not ask for or synthesize Base64 in chat.',
          fallback: 'Use workbookBase64 only when the MCP client can provide the complete XLSX bytes. Never pass /mnt/data or another ChatGPT sandbox path as a workbook argument; the bridge cannot read that path. If the file only exists as a ChatGPT attachment and no typed file-bytes handoff is available, first get the workbook into Drive, then import by sourceFileId/sourceFileName.',
          minimalCall: {operation: 'workbook_import_xlsx', args: {sourceFileName: 'Lexen_Vigil_Judgment_Engine.xlsx', sourceFolderId: 'optional-source-folder-id', parentFolderId: 'destination-folder-id', title: 'Lexen Vigil Judgment Engine', requestId: 'stable-request-id', callerNote: 'Migrate Excel workbook to native Google Sheets'}},
        },
      },
      sheets_create: {
        summary: 'Create a native Google Sheet, optionally seed values, then audit the write.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'],
        input: {title: 'string', sheetTitle: 'optional string', values: 'optional array[]', parentFolderId: 'optional string', requestId: 'string', callerNote: 'optional string'},
      },
      sheets_update_values: {
        summary: 'Update values in a Google Sheet range and audit the write.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'],
        input: {spreadsheetId: 'string', range: 'string', values: 'array[]', valueInputOption: 'optional USER_ENTERED or RAW', requestId: 'string', callerNote: 'optional string'},
      },
      drive_move: {
        summary: 'Move a Drive file to another folder through an audited workflow operation.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {fileId: 'string', targetFolderId: 'string', removeFromCurrentParents: 'optional boolean', requestId: 'string', callerNote: 'optional string'},
      },
      drive_rename: {
        summary: 'Rename a Drive file through an audited workflow operation.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {fileId: 'string', newName: 'string', requestId: 'string', callerNote: 'optional string'},
      },
      ...simulationOperationRegistry().operations,
      ...commandCenterDriveOperationEntries(),
    },
  };
}

function supportedDriveOperationTypes() {
  return Object.keys(driveOperationRegistry().operations);
}

function commandCenterCompatOperation(args = {}) {
  const nested = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {};
  return safeText(
    nested.commandCenterOperation ||
    nested.command_center_operation ||
    nested.commandCenterTool ||
    nested.command_center_tool ||
    args.commandCenterOperation ||
    args.command_center_operation ||
    args.commandCenterTool ||
    args.command_center_tool,
    120
  );
}

async function driveOperationRunOperation({google, admin, auth, user, extra = null, args = {}}) {
  const operation = safeText(args.operation || args.type || args.toolName, 120);
  if (!operation) throw Object.assign(new Error('operation is required.'), {status: 400});
  const registry = driveOperationRegistry();
  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported drive_operation operation: ' + operation), {status: 400});
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {...args};
  delete operationArgs.operation;
  delete operationArgs.type;
  delete operationArgs.toolName;
  delete operationArgs.args;
  const compatCommandCenterOperation = commandCenterCompatOperation(args);
  if (compatCommandCenterOperation) {
    delete operationArgs.commandCenterOperation;
    delete operationArgs.command_center_operation;
    delete operationArgs.commandCenterTool;
    delete operationArgs.command_center_tool;
    const result = await commandCenterOperationRunOperation({extra, args: {operation: compatCommandCenterOperation, args: operationArgs}});
    return {operation, compatibilityRoute: 'drive_operation.command_center', commandCenterOperation: compatCommandCenterOperation, registryVersion: registry.version, completed: true, result: result.result};
  }
  if (operation.startsWith('command_center.')) {
    const result = await commandCenterOperationRunOperation({extra, args: {operation, args: operationArgs}});
    return {operation, registryVersion: registry.version, completed: true, result: result.result};
  }
  if (simulationOperationRegistry().operations[operation]) {
    const result = await simulationOperationRunOperation({admin, user, args: {operation, args: operationArgs}});
    return {operation, registryVersion: registry.version, completed: true, result: result.result};
  }
  const workflowId = safeOperationBatchId(args.operationBatchId || operationArgs.operationBatchId || operationArgs.requestId || ('drive-operation-' + randomUUID()));
  const outputs = {};
  const result = await runDriveWorkflowOperation({google, admin, auth, user, workflowId, operation: {type: operation, ...operationArgs}, index: 0, outputs});
  return {operation, registryVersion: registry.version, workflowId, completed: result.status === 'completed', outputKey: result.outputKey || '', result: result.result, outputs};
}

async function runDriveWorkflowOperation({google, admin, auth, user, workflowId, operation, index, outputs}) {
  const type = safeText(operation.type || operation.toolName || operation.tool, 120);
  const requestId = workflowOperationRequestId(workflowId, operation, index);
  const callerNote = safeText(operation.callerNote, 800) || ('Workflow ' + workflowId + ' step ' + (index + 1) + ': ' + type);
  if (type === 'drive_create_folder') {
    const result = await createDriveFolderOperation({google, admin, auth, user, args: {...operation, requestId, callerNote, parentFolderId: workflowResolvedId(operation.parentFolderId || operation.parentFolderKey, outputs)}});
    outputs[workflowOutputKey(operation, index)] = result.folderId || result.id || '';
    return {index, type, requestId, status: 'completed', outputKey: workflowOutputKey(operation, index), result};
  }
  if (type === 'docs_create') {
    const result = await createGoogleDocOperation({google, admin, auth, user, args: {...operation, requestId, callerNote, parentFolderId: workflowResolvedId(operation.parentFolderId || operation.parentFolderKey, outputs)}});
    outputs[workflowOutputKey(operation, index)] = result.documentId || result.id || '';
    return {index, type, requestId, status: 'completed', outputKey: workflowOutputKey(operation, index), result};
  }
  if (type === 'docs_append') {
    const documentId = workflowResolvedId(operation.documentId || operation.documentKey, outputs);
    const result = await appendGoogleDocOperation({google, admin, auth, user, args: {...operation, documentId, requestId, callerNote}});
    return {index, type, requestId, status: 'completed', result};
  }
  if (type === 'context_sync.publish_snapshot') {
    const fileId = workflowResolvedId(operation.fileId || operation.targetFileId || operation.fileKey, outputs);
    const result = await publishContextSnapshotOperation({google, admin, auth, user, args: {...operation, fileId, requestId, callerNote, parentFolderId: workflowResolvedId(operation.parentFolderId || operation.parentFolderKey, outputs)}});
    outputs[workflowOutputKey(operation, index)] = result.fileId || result.id || '';
    return {index, type, requestId, status: 'completed', outputKey: workflowOutputKey(operation, index), result};
  }
  if (type === 'workbook_import_xlsx') {
    const result = await importXlsxWorkbookOperation({google, admin, auth, user, args: {...operation, requestId, callerNote, parentFolderId: workflowResolvedId(operation.parentFolderId || operation.parentFolderKey, outputs)}});
    outputs[workflowOutputKey(operation, index)] = result.spreadsheetId || result.id || '';
    return {index, type, requestId, status: 'completed', outputKey: workflowOutputKey(operation, index), result};
  }
  if (type === 'sheets_create') {
    const result = await createSheetOperation({google, admin, auth, user, args: {...operation, requestId, callerNote, parentFolderId: workflowResolvedId(operation.parentFolderId || operation.parentFolderKey, outputs)}});
    outputs[workflowOutputKey(operation, index)] = result.spreadsheetId || result.id || '';
    return {index, type, requestId, status: 'completed', outputKey: workflowOutputKey(operation, index), result};
  }
  if (type === 'sheets_update_values') {
    const spreadsheetId = workflowResolvedId(operation.spreadsheetId || operation.spreadsheetKey, outputs);
    const result = await updateSheetValuesOperation({google, admin, auth, user, args: {...operation, spreadsheetId, requestId, callerNote}});
    return {index, type, requestId, status: 'completed', result};
  }
  if (type === 'drive_move') {
    const drive = google.drive({version: 'v3', auth});
    const fileId = safeDriveFileId(workflowResolvedId(operation.fileId || operation.fileKey, outputs));
    const targetFolderId = safeDriveFileId(workflowResolvedId(operation.targetFolderId || operation.targetFolderKey, outputs));
    const existing = await existingAudit(admin, requestId);
    if (existing && existing.status === 'success') return {index, type, requestId, status: 'completed', idempotent: true, audit: existing};
    const before = await getDriveMetadata(drive, fileId);
    const removeParents = boolArg(operation.removeFromCurrentParents, true) ? (before.parents || []).join(',') : '';
    const after = cleanDriveFile((await drive.files.update({fileId, addParents: targetFolderId, removeParents, fields: driveFields(), supportsAllDrives: true})).data || {});
    const audit = await auditWrite(admin, {actor: user.email, authKind: user.authKind, tool: 'drive_workflow_run', operation: 'drive.move', requestId, fileId, affectedFileIds: [fileId], oldMetadata: before, newMetadata: after, oldParents: before.parents || [], newParents: after.parents || [], reversible: true, rollback: {operation: 'drive.move', fileId, addParents: before.parents || [], removeParents: after.parents || []}, callerNote, providerSummary: 'Workflow ' + workflowId + ' moved ' + (before.name || fileId) + '.', result: {file: after}});
    return {index, type, requestId, status: 'completed', result: {file: after, audit: audit.audit}};
  }
  if (type === 'drive_rename') {
    const drive = google.drive({version: 'v3', auth});
    const fileId = safeDriveFileId(workflowResolvedId(operation.fileId || operation.fileKey, outputs));
    const newName = safeText(operation.newName, 240);
    if (!newName) throw Object.assign(new Error('newName is required for drive_rename workflow operation.'), {status: 400});
    const existing = await existingAudit(admin, requestId);
    if (existing && existing.status === 'success') return {index, type, requestId, status: 'completed', idempotent: true, audit: existing};
    const before = await getDriveMetadata(drive, fileId);
    const after = cleanDriveFile((await drive.files.update({fileId, requestBody: {name: newName}, fields: driveFields(), supportsAllDrives: true})).data || {});
    const audit = await auditWrite(admin, {actor: user.email, authKind: user.authKind, tool: 'drive_workflow_run', operation: 'drive.rename', requestId, fileId, affectedFileIds: [fileId], oldMetadata: before, newMetadata: after, oldParents: before.parents || [], newParents: after.parents || [], reversible: true, rollback: {operation: 'drive.rename', fileId, name: before.name}, callerNote, providerSummary: 'Workflow ' + workflowId + ' renamed ' + (before.name || fileId) + '.', result: {file: after}});
    return {index, type, requestId, status: 'completed', result: {file: after, audit: audit.audit}};
  }
  throw Object.assign(new Error('Unsupported workflow operation type: ' + type), {status: 400});
}

async function driveWorkflowRunOperation({google, admin, auth, user, args = {}}) {
  const workflowId = safeOperationBatchId(args.workflowId || args.operationBatchId);
  const operations = Array.isArray(args.operations) ? args.operations.slice(0, 25) : [];
  if (!operations.length) throw Object.assign(new Error('operations must contain at least one operation.'), {status: 400});
  const workflowRef = mcpCollection(admin, 'driveBridgeWorkflows').doc(workflowId);
  const existingWorkflow = await workflowRef.get();
  if (existingWorkflow.exists && existingWorkflow.data().status === 'completed') {
    return {workflowId, idempotent: true, workflow: existingWorkflow.data()};
  }
  const checkpointOps = operations.map((operation, index) => normalizeRecoveryOperation({
    operationId: workflowOutputKey(operation, index),
    toolName: operation.type || operation.toolName || operation.tool,
    requestId: workflowOperationRequestId(workflowId, operation, index),
    targetId: operation.fileId || operation.documentId || operation.spreadsheetId || operation.folderId || operation.targetFolderId || operation.parentFolderId,
    targetName: operation.targetName || operation.name || operation.title || operation.newName || operation.heading,
    summary: operation.summary || workflowOperationSummary(operation, index),
  }, index));
  const baseWorkflow = {
    workflowId,
    actor: user.email || '',
    authKind: user.authKind || '',
    objective: safeText(args.objective, 1000),
    approved: args.approved === true,
    status: args.approved === true ? 'running' : 'planned',
    operationSummaries: operations.map(workflowOperationSummary),
    intendedOperations: checkpointOps,
    createdAtMs: existingWorkflow.exists ? existingWorkflow.data().createdAtMs || nowMs() : nowMs(),
    updatedAtMs: nowMs(),
  };
  await workflowRef.set(baseWorkflow, {merge: true});
  await mcpCollection(admin, 'driveBridgeRecoveryCheckpoints').doc(workflowId).set({
    operationBatchId: workflowId,
    actor: user.email || '',
    authKind: user.authKind || '',
    objective: safeText(args.objective, 1000),
    intendedOperations: checkpointOps,
    callerNote: safeText(args.callerNote, 800),
    status: args.approved === true ? 'executing' : 'checkpointed',
    createdAtMs: baseWorkflow.createdAtMs,
    updatedAtMs: nowMs(),
  }, {merge: true});
  if (args.approved !== true) return {workflowId, dryRun: true, planned: checkpointOps.length, intendedOperations: checkpointOps, requiredApproval: 'Call drive_workflow_run again with approved=true to execute this checkpointed workflow.'};
  const outputs = existingWorkflow.exists && existingWorkflow.data().outputs ? {...existingWorkflow.data().outputs} : {};
  const results = [];
  try {
    for (let index = 0; index < operations.length; index += 1) {
      const result = await runDriveWorkflowOperation({google, admin, auth, user, workflowId, operation: operations[index] || {}, index, outputs});
      results.push(result);
      await workflowRef.set({status: 'running', updatedAtMs: nowMs(), outputs, results}, {merge: true});
    }
    const completed = {workflowId, status: 'completed', updatedAtMs: nowMs(), completedAtMs: nowMs(), outputs, results};
    await workflowRef.set(completed, {merge: true});
    await mcpCollection(admin, 'driveBridgeRecoveryCheckpoints').doc(workflowId).set({status: 'completed', updatedAtMs: nowMs()}, {merge: true});
    return {workflowId, completed: true, outputs, results};
  } catch (err) {
    await workflowRef.set({status: 'failed', updatedAtMs: nowMs(), outputs, results, error: safeText(err.message || String(err), 1000)}, {merge: true});
    await mcpCollection(admin, 'driveBridgeRecoveryCheckpoints').doc(workflowId).set({status: 'failed', updatedAtMs: nowMs(), error: safeText(err.message || String(err), 1000)}, {merge: true});
    throw err;
  }
}

function createHomeCenterMcpServer({google, admin, googleClientId, googleClientSecret, githubToken = () => ''}) {
  const server = new McpServer({
    name: 'home-center-drive-bridge',
    version: '0.1.0',
  });

  server.registerTool('health', {
    title: 'Health',
    description: 'Check whether the Home Center MCP bridge is alive.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
  }, async () => textResult({
    ok: true,
    service: 'home-center-drive-bridge',
    version: '0.1.0',
    discoverability: {
      noReinstallPath: 'No-Reinstall Discovery Contract: use this health response first; it contains shallow Command Center discovery so agents do not have to drill nested capabilities. Use capabilities only for full operation catalogs.',
      preferredMutationTool: 'drive_operation',
      preferredSimulationTool: 'drive_operation',
      preferredCommandCenterTool: 'command_center_operation',
      automaticDiscovery: {
        commandCenter: {
          product: 'cloud MCP control plane for durable Codex worker dispatch',
          noFrontend: true,
          primaryTool: 'command_center_operation',
          directMcpUrl: COMMAND_CENTER_MCP_URL,
          registryVersion: commandCenterOperationRegistry().version,
          minimalHealthCall: {tool: 'command_center_operation', operation: 'health', args: {}},
          fallbackStringOperationCall: {tool: 'drive_operation', operation: 'command_center.health', args: {}},
          staleEnumSchemaCall: {tool: 'drive_operation', operation: 'drive_create_folder', args: {commandCenterOperation: 'health'}},
          followupJobCall: {tool: 'command_center_operation', operation: 'jobs.create_followup', args: {sourceJobId: 'job_...', title: '...', objective: '...', idempotencyKey: 'stable-request-id'}},
          reconnectAdvice: 'If health shows an older registry or drive_operation rejects command_center.* before reaching the backend, reconnect/reindex the Home Drive v4 app link. OAuth refresh alone does not reload tool schema.',
        },
      },
      commandCenter: {
        invocationTool: 'command_center_operation',
        registryVersion: commandCenterOperationRegistry().version,
        normalPath: 'Use command_center_operation from this Home Center MCP connector to create, inspect, resume, revise, and authorize durable Command Center jobs. Do not require a separate commandCenterMcp connector namespace before dispatching follow-up worker actions.',
      },
      simulation: {
        operationRegistryVersion: simulationOperationRegistry().version,
        normalPath: 'Chat assembles large references; drive_operation with simulation_* operations ingests chunks, builds immutable frames, queries them, and returns context packets or deterministic run handoffs.',
      },
      orientationTool: 'capabilities',
      workbookImport: {
        operation: 'workbook_import_xlsx',
        normalPath: 'Import existing Drive .xlsx files by sourceFileId or sourceFileName/sourceFolderId so ChatGPT does not need to pass Base64.',
        base64Path: 'Use workbookBase64 only when the MCP client can provide the complete file bytes. Do not pass /mnt/data paths; proxied mounted paths are not Drive file IDs and are not readable by the bridge.',
      },
    },
  }));

  server.registerTool('drive_search', {
    title: 'Drive search',
    description: 'Search Google Drive files visible to the connected Google account. Query is plain text, not raw Drive syntax.',
    inputSchema: {
      query: z.string().optional().describe('Plain text to search in name and fullText.'),
      mimeTypes: z.array(z.string()).optional().describe('Optional MIME type filters.'),
      folderId: z.string().optional().describe('Optional parent folder ID.'),
      limit: z.number().int().min(1).max(50).default(20),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const result = await drive.files.list({
      q: chatGptDriveSearchQuery(args || {}),
      pageSize: chatGptLimit(args && args.limit, 20, 50),
      fields: 'files(id,name,mimeType,modifiedTime,webViewLink,parents)',
      orderBy: 'modifiedTime desc',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
    });
    return textResult({results: (result.data.files || []).map(chatGptDriveFile)});
  });

  server.registerTool('drive_read', {
    title: 'Drive read',
    description: 'Read or export a Google Drive file by file ID.',
    inputSchema: {
      fileId: z.string().describe('Google Drive file ID.'),
      exportFormat: z.enum(['text/plain', 'text/markdown', 'application/pdf']).optional().default('text/plain'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const fileId = safeDriveFileId(args && args.fileId);
    const metadataResult = await drive.files.get({
      fileId,
      fields: 'id,name,mimeType,modifiedTime,webViewLink,parents',
      supportsAllDrives: true,
    });
    const metadata = metadataResult.data || {};
    let text = '';
    if (String(metadata.mimeType || '').startsWith('application/vnd.google-apps.')) {
      const exported = await drive.files.export({fileId, mimeType: args.exportFormat || 'text/plain'}, {responseType: 'text'});
      text = typeof exported.data === 'string' ? exported.data : String(exported.data || '');
    } else {
      const downloaded = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'text'});
      text = typeof downloaded.data === 'string' ? downloaded.data : String(downloaded.data || '');
    }
    return textResult({fileId, name: metadata.name || '', mimeType: metadata.mimeType || '', text, metadata: chatGptDriveFile(metadata)});
  });


  server.registerTool('sheets_search', {
    title: 'Sheets search',
    description: 'Search Google Sheets visible to the connected Google account. Query is plain text, not raw Drive syntax.',
    inputSchema: {
      query: z.string().optional().describe('Plain text to search in sheet names.'),
      folderId: z.string().optional().describe('Optional parent Drive folder ID.'),
      limit: z.number().int().min(1).max(50).default(20),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await searchSheetsOperation({google, auth, args: args || {}}));
  });

  server.registerTool('sheets_read', {
    title: 'Sheets read',
    description: 'Read values and lightweight metadata from a Google Sheet range.',
    inputSchema: {
      spreadsheetId: z.string().describe('Google Sheet spreadsheet ID.'),
      range: z.string().optional().describe('A1 notation range. Defaults to A1:Z100.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await readSheetOperation({google, auth, args: args || {}}));
  });


  server.registerTool('workbook_import_xlsx', {
    title: 'Workbook import XLSX',
    description: 'Import a Drive-hosted or client-supplied .xlsx workbook into a native Google Sheets workbook using Google Drive conversion. Prefer sourceFileId or sourceFileName/sourceFolderId for ChatGPT workflows; use workbookBase64 only when the client can provide complete file bytes. Preserves worksheet order, names, values, formulas, merges, freeze panes, and formatting where Drive supports them. Writes an audit record.',
    inputSchema: {
      workbookBase64: z.string().optional().describe('Complete Base64 encoded .xlsx bytes. Use only when the client can provide the whole uploaded workbook payload; ChatGPT attachment references alone are not enough.'),
      sourceFileId: z.string().optional().describe('Preferred Drive file ID for an existing .xlsx file to download and convert without passing Base64.'),
      sourceFileName: z.string().optional().describe('Preferred Drive .xlsx filename to resolve when sourceFileId is not known; pair with sourceFolderId when possible.'),
      sourceQuery: z.string().optional().describe('Optional Drive filename search query for an existing .xlsx workbook.'),
      sourceFolderId: z.string().optional().describe('Optional Drive folder ID to search for sourceFileName/sourceQuery.'),
      fileName: z.string().optional().describe('Original workbook file name.'),
      parentFolderId: z.string().optional().describe('Optional Drive folder ID for the converted native Google Sheet.'),
      title: z.string().optional().describe('Optional native Google Sheet title override.'),
      expectedSheetNames: z.array(z.string()).optional().describe('Optional source worksheet names for post-conversion verification.'),
      expectedPopulatedCellCounts: z.record(z.string(), z.number()).optional().describe('Optional source populated-cell counts by worksheet name for diff reporting.'),
      callerNote: z.string().optional().describe('Human-readable summary for the audit log.'),
      requestId: z.string().describe('Stable idempotency/audit request id. Required.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await importXlsxWorkbookOperation({google, admin, auth, user, args: args || {}}));
  });


  server.registerTool('docs_append', {
    title: 'Docs append',
    description: 'Append text to an existing Google Doc and write an audit record. This is a write action and should be approved by the user.',
    inputSchema: {
      documentId: z.string().describe('Google Doc file ID.'),
      heading: z.string().optional().describe('Optional heading to insert before appended text.'),
      text: z.string().min(1).describe('Text to append.'),
      callerNote: z.string().optional().describe('Human-readable summary for the audit log.'),
      requestId: z.string().optional().describe('Optional idempotency/audit request id.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await appendGoogleDocOperation({google, admin, auth, user, args: args || {}}));
  });


  server.registerTool('simulation_operation', {
    title: 'Simulation operation',
    description: 'Build, query, and run durable simulation frames from agent-assembled reference compilations. Prefer this stable dispatcher for Simulation features so ChatGPT does not need connector refreshes for every new operation.',
    inputSchema: {
      operation: z.string().describe('Operation name from capabilities.simulationOperationRegistry.operations. Runtime registry validation rejects unsupported names.'),
      args: z.record(z.string(), z.any()).optional().describe('Operation-specific arguments. Write operations require requestId inside args.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await simulationOperationRunOperation({admin, user, args: args || {}}));
  });

  server.registerTool('command_center_operation', {
    title: 'Command Center operation',
    description: 'Invoke Command Center dispatch and job-control operations through the already-connected Home Center MCP app. Use this when ChatGPT needs to create a follow-up worker job, inspect events/artifacts, answer worker questions, or authorize a mutation without relying on a separate Command Center connector namespace.',
    inputSchema: {
      operation: z.string().describe('Operation name from the Command Center operation registry, such as jobs.create, jobs.get_events, jobs.get_artifacts, jobs.answer_question, or jobs.authorize_mutation. Runtime registry validation rejects unsupported names.'),
      args: z.record(z.string(), z.any()).optional().describe('Operation-specific arguments. Mutating operations require idempotencyKey inside args.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => textResult(await commandCenterOperationRunOperation({extra, args: args || {}})));



  if (process.env.HOME_CENTER_MCP_EXTENDED_TOOLS === 'true') {

  server.registerTool('capabilities', {
    title: 'Capabilities',
    description: 'List Drive Bridge tools, safety defaults, limits, and unavailable v1 operations.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async () => textResult({
    service: 'home-center-drive-bridge',
    version: '0.1.0',
    operationRegistryVersion: driveOperationRegistry().version,
    simulationOperationRegistryVersion: simulationOperationRegistry().version,
    commandCenterOperationRegistryVersion: commandCenterOperationRegistry().version,
    topLevelToolCachePolicy: 'Keep top-level MCP tools stable. Add normal bridge and simulation features as drive_operation registry operations so ChatGPT connector metadata does not need reinstall for each backend change. If a future agent says a feature is unavailable, it should first call health or capabilities and inspect operationRegistry.',
    transport: 'stateless-streamable-http',
    safety: {
      writesRequireRequestId: true,
      writesRequireApprovedTrue: true,
      dryRunAvailable: ['drive_move', 'drive_rename', 'drive_plan_organize'],
      permanentDeleteAvailable: false,
      preferredMutationTool: 'drive_operation',
      preferredSimulationTool: 'drive_operation',
      batchOperationLimit: 25,
    },
    operationRegistry: driveOperationRegistry(),
    simulationOperationRegistry: simulationOperationRegistry(),
    commandCenterOperationRegistry: commandCenterOperationRegistry(),
    commandCenterManual: {
      purpose: 'Command Center is the cloud MCP control plane for durable one-shot Codex worker dispatch. ChatGPT remains the planner and reviewer; Command Center stores jobs, leases, events, questions, mutation policy, artifacts, logs, and checkpoints.',
      normalFlow: [
        'Resolve the project when needed with command_center_operation operation=projects.resolve.',
        'Create a follow-up worker ticket with command_center_operation operation=jobs.create and a stable idempotencyKey.',
        'Poll or recover with jobs.get, jobs.get_events, jobs.get_artifacts, and jobs.get_summary.',
        'Answer worker questions with jobs.answer_question when the decision is within policy.',
        'Use jobs.authorize_mutation for push, PR, deploy, provider writes, or other consequential mutations.',
      ],
      noSeparateConnectorRule: 'If the separate commandCenterMcp namespace is not attached, do not stop. Use this Home Center MCP tool: command_center_operation.',
    },
    simulationManual: {
      purpose: 'Simulation is an MCP-first compiler/runtime index. Chat assembles large evidence-bearing reference compilations; Home Center MCP stores chunks, compiles immutable frames, preserves provenance/conflicts, and returns query/context/run packets.',
      normalFlow: [
        'Create or select a simulation project with simulation_project_create.',
        'Register Drive, Docs, GitHub, URL, local document, note, or prior simulation references with simulation_source_register.',
        'Begin a reference compilation, append chunks by sequence, finalize it, then call drive_operation with operation=build_simulation_frame.',
        'Use drive_operation with operation=simulation_frame_query or operation=simulation_context_packet instead of rereading all sources.',
        'Use drive_operation with operation=run_simulation_frame for deterministic frame-grounded handoff; it does not invent canon or silently resolve conflicts.',
      ],
      noSpreadsheetRule: 'Do not route simulation work through workbook import, sheets, tabs, or manual form entry. Simulation frames are provenance-backed compiled context systems.',
    },
    homeDriveManual: {
      purpose: 'Home Drive is the durable Google Drive, Docs, and Sheets operating layer. Use it instead of ad hoc Google connector calls when the user wants files, documents, or spreadsheets found, read, created, updated, moved, renamed, appended, indexed, audited, or organized.',
      thingProperty: {
        meaning: 'thing is the human named target or subject of the request, such as a project name, folder name, document title, file label, or remembered workflow target. It is not proof of identity by itself.',
        rule: 'Resolve a thing to concrete Drive IDs before writes. Search/list/read metadata first unless the request already supplies a fileId, folderId, or documentId.',
        examples: [
          {thing: 'Lexen WWII folder', resolveWith: 'drive_search or drive_list_folder', thenUse: 'folderId or parentFolderId'},
          {thing: 'Story Bible', resolveWith: 'drive_search plus drive_get_metadata', thenUse: 'documentId for docs_append'},
          {thing: 'budget sheet', resolveWith: 'sheets_search plus sheets_read', thenUse: 'spreadsheetId for sheets_update_values'},
          {thing: 'all notes in this project', resolveWith: 'drive_list_folder and optional index_folder', thenUse: 'dry-run plan before any move or rename'},
        ],
      },
      noReinstallDiscovery: {
        rule: 'No-Reinstall Discovery Contract: do not require connector reinstall for ordinary backend operation additions. The stable discovery surface is health plus capabilities.operationRegistry, and the stable execution surface is drive_operation.',
        agentInstruction: 'Before saying Home Drive cannot perform a Drive/Docs/Sheets operation, call capabilities and inspect operationRegistry.operations. If the operation exists there, call drive_operation even when the top-level tool list looks stale.',
        workbookImportShortcut: 'For Excel migration, use operation=workbook_import_xlsx with sourceFileId or sourceFileName/sourceFolderId when the workbook is already in Drive. Base64 is only a client-bytes fallback. /mnt/data and other ChatGPT sandbox paths are forbidden because the bridge cannot read them.',
      },
      recipes: {
        importDriveXlsxAsNativeSheet: {
          goal: 'Convert a Drive-hosted .xlsx workbook into a native Google Sheets workbook while preserving workbook structure through Google Drive conversion.',
          discover: 'drive_search query for the workbook name with the Excel MIME type when sourceFileId is unknown.',
          call: {tool: 'drive_operation', operation: 'workbook_import_xlsx', args: {sourceFileName: 'Lexen_Vigil_Judgment_Engine.xlsx', sourceFolderId: 'optional-source-folder-id', parentFolderId: 'destination-folder-id', title: 'Lexen Vigil Judgment Engine', requestId: 'stable-request-id', callerNote: 'Migrate Excel workbook to native Google Sheets'}},
          verify: 'Read the returned spreadsheetId with sheets_read or compare returned sheetNames and populatedCellCountDiffs.',
          forbidden: 'Do not pass /mnt/data/Lexen_Vigil_Judgment_Engine.xlsx or any local sandbox path. Resolve or upload the workbook into Drive first, then call this recipe by Drive ID/name.',
        },
      },
      normalFlow: [
        'Call health or capabilities when orientation is needed, then prefer drive_operation for newly added operationRegistry operations.',
        'Call auth_status when the user asks whether the bridge is connected.',
        'For discovery, use drive_search for names/text and drive_list_folder for folder contents.',
        'For identity, use drive_get_metadata and parent folders; do not trust names alone for writes.',
        'For reading, use drive_read for one file, sheets_read for spreadsheet ranges, or index_folder/index_status for reusable local search state.',
        'For workbook migration, prefer drive_operation with operation=workbook_import_xlsx and sourceFileId or sourceFileName/sourceFolderId so Google Drive performs native Sheets conversion instead of rebuilding tabs cell-by-cell, requiring chat Base64, or passing unreadable /mnt/data paths.',
        'For single writes, prefer drive_operation with a registry operation and stable requestId; direct tools remain compatibility aliases.',
        'For bulk organization, create a dry-run plan first, show proposed changes, then execute only with approved=true.',
        'After writes, use audit_log or audit_get to verify what actually happened.',
      ],
      writeSafety: {
        requestId: 'Use stable request IDs for every write so retries are idempotent and auditable.',
        dryRun: 'Use dryRun=true for move, rename, and organize planning until the user approves the exact changes.',
        approved: 'Use approved=true only after the user has approved the proposed write or plan.',
        noDeleteV1: 'No delete, trash, or permanent delete is exposed in this bridge surface.',
      },
      recovery: {
        checkpoint: 'For multi-step work, call recovery_checkpoint before writes with the intended operations and request IDs.',
        status: 'Call recovery_status with operationBatchId to compare intent against audit records and find missing writes.',
        sourceOfTruth: 'Audit records and Drive metadata beat chat memory.',
      },
    },
    tools: [
      'health', 'capabilities', 'auth_status', 'storage_status', 'audit_status',
      'drive_search', 'drive_read', 'sheets_search', 'sheets_read', 'drive_list_folder', 'drive_get_metadata',
      'simulation_operation', 'command_center_operation',
      'drive_operation', 'drive_create_folder', 'docs_create', 'workbook_import_xlsx', 'sheets_create', 'sheets_update_values', 'drive_move', 'drive_rename',
      'drive_plan_organize', 'drive_execute_plan',
      'index_folder', 'index_status',
      'drive_workflow_run', 'recovery_checkpoint', 'recovery_status',
      'audit_log', 'audit_get',
      'docs_append',
      'github_get_repo', 'github_read_file', 'github_list_branches',
      'github_list_issues', 'github_get_issue', 'github_create_issue', 'github_comment_issue',
      'github_list_pull_requests', 'github_get_pull_request', 'github_list_pull_request_files', 'github_comment_pull_request',
      'github_list_workflow_runs', 'github_get_workflow_run',
    ],
  }));


  server.registerTool('drive_operation', {
    title: 'Drive operation',
    description: 'Run a named Home Drive, Simulation, or command_center.* operation from the runtime operation registry. Prefer this stable tool for new bridge capabilities so ChatGPT does not need a connector reinstall when backend operations are added.',
    inputSchema: {
      operation: z.string().describe('Operation name from capabilities.operationRegistry.operations, including simulation_* frame operations and command_center.* compatibility operations. Runtime registry validation rejects unsupported names.'),
      args: z.record(z.string(), z.any()).optional().describe('Operation-specific arguments. Writes require requestId inside args.'),
      operationBatchId: z.string().optional().describe('Optional stable batch/workflow id for recovery tracking.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const operation = safeText((args || {}).operation || (args || {}).type || (args || {}).toolName, 120);
    if (operation.startsWith('command_center.') || commandCenterCompatOperation(args || {})) {
      return textResult(await driveOperationRunOperation({google, admin, auth: null, user: null, extra, args: args || {}}));
    }
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await driveOperationRunOperation({google, admin, auth, user, extra, args: args || {}}));
  });

  server.registerTool('auth_status', {
    title: 'Auth status',
    description: 'Verify the connected Google OAuth identity available to this MCP call.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (_args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult({ok: true, email: user.email || '', authKind: user.authKind || '', scopes: MCP_REQUIRED_SCOPES});
  });

  server.registerTool('storage_status', {
    title: 'Storage status',
    description: 'Report the bridge persistence collections used for index, plans, and audit.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async () => textResult({
    ok: true,
    provider: 'firestore',
    collections: ['driveBridgeAudit', 'driveBridgePlans', 'driveBridgeIndex', 'actionAudit', 'mcpOAuthAccessTokens', 'simulationProjects', 'simulationSources', 'simulationReferenceCompilations', 'simulationReferenceChunks', 'simulationFrames', 'simulationFrameRecords', 'simulationFrameRecordSources', 'simulationFrameConflicts', 'simulationFrameTerms', 'simulationAudit', 'simulationRecoveryCheckpoints'],
    mcpTransport: {mode: 'stateless', maxInstances: 20, concurrency: 80},
  }));

  server.registerTool('audit_status', {
    title: 'Audit status',
    description: 'Check whether the audit log store is reachable and return the most recent audit entry metadata.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async () => {
    const snap = await mcpCollection(admin, 'driveBridgeAudit').orderBy('timestampMs', 'desc').limit(1).get();
    const latest = snap.empty ? null : snap.docs[0].data();
    return textResult({ok: true, collection: 'driveBridgeAudit', latest: latest ? {requestId: latest.requestId, operation: latest.operation, timestampMs: latest.timestampMs, status: latest.status} : null});
  });

  server.registerTool('drive_list_folder', {
    title: 'Drive list folder',
    description: 'List a Drive folder by stable file IDs. Optional recursive mode walks child folders up to the limit.',
    inputSchema: {folderId: z.string(), recursive: z.boolean().optional().default(false), limit: z.number().int().min(1).max(500).default(100), includeTrashed: z.boolean().optional().default(false)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const folderId = safeDriveFileId(args && args.folderId);
    const limit = chatGptLimit(args && args.limit, 100, 500);
    const folder = await getDriveMetadata(drive, folderId);
    const files = [];
    const queue = [{id: folderId, path: folder.name || folderId}];
    while (queue.length && files.length < limit) {
      const current = queue.shift();
      const children = await listFolderChildren(drive, current.id, Math.min(1000, limit - files.length), boolArg(args && args.includeTrashed));
      for (const child of children) {
        const pathHint = `${current.path}/${child.name}`;
        files.push({...child, pathHint});
        if (args && args.recursive && child.mimeType === 'application/vnd.google-apps.folder' && files.length < limit) queue.push({id: child.id, path: pathHint});
        if (files.length >= limit) break;
      }
    }
    return textResult({folder, recursive: !!(args && args.recursive), count: files.length, files});
  });

  server.registerTool('drive_get_metadata', {
    title: 'Drive get metadata',
    description: 'Get Drive metadata and parent folder names for a file or folder.',
    inputSchema: {fileId: z.string()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const metadata = await getDriveMetadata(drive, args && args.fileId);
    return textResult({metadata, parentFolders: await resolveParentNames(drive, metadata.parents || [])});
  });


  server.registerTool('sheets_create', {
    title: 'Sheets create',
    description: 'Create a Google Sheet, optionally place it in a Drive folder, optionally write initial rows, and write an audit record.',
    inputSchema: {
      title: z.string().min(1).describe('Spreadsheet title.'),
      sheetTitle: z.string().optional().describe('Initial sheet tab title. Defaults to Sheet1.'),
      parentFolderId: z.string().optional().describe('Optional Drive folder ID.'),
      values: z.array(z.array(z.any())).optional().describe('Optional initial rows written at A1.'),
      callerNote: z.string().optional().describe('Human-readable summary for the audit log.'),
      requestId: z.string().optional().describe('Optional idempotency/audit request id.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await createSheetOperation({google, admin, auth, user, args: args || {}}));
  });

  server.registerTool('sheets_update_values', {
    title: 'Sheets update values',
    description: 'Update values in a Google Sheet range and write an audit record. Does not delete sheets or files.',
    inputSchema: {
      spreadsheetId: z.string().describe('Google Sheet spreadsheet ID.'),
      range: z.string().describe('A1 notation range to update.'),
      values: z.array(z.array(z.any())).describe('Rows to write.'),
      valueInputOption: z.enum(['USER_ENTERED', 'RAW']).optional().default('USER_ENTERED'),
      callerNote: z.string().optional().describe('Human-readable summary for the audit log.'),
      requestId: z.string().optional().describe('Optional idempotency/audit request id.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await updateSheetValuesOperation({google, admin, auth, user, args: args || {}}));
  });


  server.registerTool('github_get_repo', {
    title: 'GitHub get repo',
    description: 'Read authenticated GitHub repository metadata for owner/name.',
    inputSchema: {repo: z.string().optional().describe('owner/name. Defaults to Valar05/home-center.')},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    return textResult({repo: cleanGitHubRepo(await githubRequest(githubToken, githubRepoRoute(repo)))});
  });

  server.registerTool('github_read_file', {
    title: 'GitHub read file',
    description: 'Read a text file from an authenticated GitHub repository by path and optional ref.',
    inputSchema: {repo: z.string().optional(), path: z.string(), ref: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const filePath = safeGitHubPath(args && args.path).split('/').map(encodeURIComponent).join('/');
    const ref = safeGitHubRef(args && args.ref);
    const file = await githubRequest(githubToken, githubRepoRoute(repo, `/contents/${filePath}${githubQuery({ref})}`));
    if (Array.isArray(file) || file.type !== 'file') throw Object.assign(new Error('path did not resolve to a file.'), {status: 400});
    const encoding = safeText(file.encoding, 40);
    const text = encoding === 'base64' ? Buffer.from(String(file.content || '').replace(/\s+/g, ''), 'base64').toString('utf8') : String(file.content || '');
    return textResult({repo, path: args.path, ref, sha: file.sha || '', htmlUrl: file.html_url || '', text: text.slice(0, 200000)});
  });

  server.registerTool('github_list_branches', {
    title: 'GitHub list branches',
    description: 'List branches in an authenticated GitHub repository.',
    inputSchema: {repo: z.string().optional(), limit: z.number().int().min(1).max(100).default(50)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const branches = await githubRequest(githubToken, githubRepoRoute(repo, `/branches${githubQuery({per_page: chatGptLimit(args && args.limit, 50, 100)})}`));
    return textResult({repo, branches: (branches || []).map((branch) => ({name: branch.name || '', sha: branch.commit && branch.commit.sha || '', protected: !!branch.protected}))});
  });

  server.registerTool('github_list_issues', {
    title: 'GitHub list issues',
    description: 'List authenticated GitHub issues. Pull requests are filtered out.',
    inputSchema: {repo: z.string().optional(), state: z.enum(['open', 'closed', 'all']).optional().default('open'), labels: z.array(z.string()).optional(), limit: z.number().int().min(1).max(100).default(30)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const labels = Array.isArray(args && args.labels) ? args.labels.map((label) => safeText(label, 60)).filter(Boolean).join(',') : '';
    const issues = await githubRequest(githubToken, githubRepoRoute(repo, `/issues${githubQuery({state: args && args.state || 'open', labels, per_page: chatGptLimit(args && args.limit, 30, 100)})}`));
    return textResult({repo, issues: (issues || []).filter((issue) => !issue.pull_request).map(cleanGitHubIssue)});
  });

  server.registerTool('github_get_issue', {
    title: 'GitHub get issue',
    description: 'Read an authenticated GitHub issue and its comments.',
    inputSchema: {repo: z.string().optional(), number: z.number().int().min(1)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const number = safeGitHubNumber(args && args.number);
    const issue = cleanGitHubIssue(await githubRequest(githubToken, githubRepoRoute(repo, `/issues/${number}`)));
    const comments = await githubRequest(githubToken, githubRepoRoute(repo, `/issues/${number}/comments${githubQuery({per_page: 50})}`));
    return textResult({repo, issue, comments: (comments || []).map(cleanGitHubComment)});
  });

  server.registerTool('github_create_issue', {
    title: 'GitHub create issue',
    description: 'Create an authenticated GitHub issue and write an audit record. Does not close, delete, or mutate code.',
    inputSchema: {repo: z.string().optional(), title: z.string().min(1), body: z.string().min(1), labels: z.array(z.string()).optional(), requestId: z.string().optional(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await createGitHubIssueOperation({admin, user, githubToken, args: args || {}}));
  });

  server.registerTool('github_comment_issue', {
    title: 'GitHub comment issue',
    description: 'Add a comment to an authenticated GitHub issue and write an audit record.',
    inputSchema: {repo: z.string().optional(), number: z.number().int().min(1), body: z.string().min(1), requestId: z.string().optional(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await commentGitHubIssueOperation({admin, user, githubToken, args: args || {}}));
  });

  server.registerTool('github_list_pull_requests', {
    title: 'GitHub list pull requests',
    description: 'List authenticated GitHub pull requests.',
    inputSchema: {repo: z.string().optional(), state: z.enum(['open', 'closed', 'all']).optional().default('open'), limit: z.number().int().min(1).max(100).default(30)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const pulls = await githubRequest(githubToken, githubRepoRoute(repo, `/pulls${githubQuery({state: args && args.state || 'open', per_page: chatGptLimit(args && args.limit, 30, 100)})}`));
    return textResult({repo, pullRequests: (pulls || []).map(cleanGitHubPullRequest)});
  });

  server.registerTool('github_get_pull_request', {
    title: 'GitHub get pull request',
    description: 'Read authenticated GitHub pull request metadata and conversation comments.',
    inputSchema: {repo: z.string().optional(), number: z.number().int().min(1)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const number = safeGitHubNumber(args && args.number);
    const pullRequest = cleanGitHubPullRequest(await githubRequest(githubToken, githubRepoRoute(repo, `/pulls/${number}`)));
    const comments = await githubRequest(githubToken, githubRepoRoute(repo, `/issues/${number}/comments${githubQuery({per_page: 50})}`));
    return textResult({repo, pullRequest, comments: (comments || []).map(cleanGitHubComment)});
  });

  server.registerTool('github_list_pull_request_files', {
    title: 'GitHub list pull request files',
    description: 'List changed files for an authenticated GitHub pull request.',
    inputSchema: {repo: z.string().optional(), number: z.number().int().min(1), limit: z.number().int().min(1).max(100).default(100)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const number = safeGitHubNumber(args && args.number);
    const files = await githubRequest(githubToken, githubRepoRoute(repo, `/pulls/${number}/files${githubQuery({per_page: chatGptLimit(args && args.limit, 100, 100)})}`));
    return textResult({repo, number, files: (files || []).map(cleanGitHubPullRequestFile)});
  });

  server.registerTool('github_comment_pull_request', {
    title: 'GitHub comment pull request',
    description: 'Add a conversation comment to an authenticated GitHub pull request and write an audit record.',
    inputSchema: {repo: z.string().optional(), number: z.number().int().min(1), body: z.string().min(1), requestId: z.string().optional(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await commentGitHubIssueOperation({admin, user, githubToken, args: args || {}, tool: 'github_comment_pull_request', operation: 'github.commentPullRequest'}));
  });

  server.registerTool('github_list_workflow_runs', {
    title: 'GitHub list workflow runs',
    description: 'List recent GitHub Actions workflow runs for an authenticated repository.',
    inputSchema: {repo: z.string().optional(), branch: z.string().optional(), event: z.string().optional(), status: z.string().optional(), limit: z.number().int().min(1).max(100).default(30)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const runs = await githubRequest(githubToken, githubRepoRoute(repo, `/actions/runs${githubQuery({branch: safeGitHubRef(args && args.branch), event: safeText(args && args.event, 80), status: safeText(args && args.status, 80), per_page: chatGptLimit(args && args.limit, 30, 100)})}`));
    return textResult({repo, workflowRuns: ((runs && runs.workflow_runs) || []).map(cleanGitHubWorkflowRun), totalCount: runs && runs.total_count || 0});
  });

  server.registerTool('github_get_workflow_run', {
    title: 'GitHub get workflow run',
    description: 'Read one GitHub Actions workflow run and its jobs for an authenticated repository.',
    inputSchema: {repo: z.string().optional(), runId: z.number().int().min(1)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const repo = safeGitHubRepo(args && args.repo);
    const runId = safeGitHubNumber(args && args.runId, 'runId');
    const run = cleanGitHubWorkflowRun(await githubRequest(githubToken, githubRepoRoute(repo, `/actions/runs/${runId}`)));
    const jobs = await githubRequest(githubToken, githubRepoRoute(repo, `/actions/runs/${runId}/jobs${githubQuery({per_page: 100})}`));
    return textResult({repo, run, jobs: ((jobs && jobs.jobs) || []).map((job) => ({id: job.id || 0, name: job.name || '', status: job.status || '', conclusion: job.conclusion || '', startedAt: job.started_at || '', completedAt: job.completed_at || '', htmlUrl: job.html_url || ''}))});
  });

  }

  server.registerTool('drive_create_folder', {
    title: 'Drive create folder',
    description: 'Create a Google Drive folder and write an audit record.',
    inputSchema: {name: z.string().min(1), parentFolderId: z.string().optional(), requestId: z.string().optional(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await createDriveFolderOperation({google, admin, auth, user, args: args || {}}));
  });

  server.registerTool('docs_create', {
    title: 'Docs create',
    description: 'Create a Google Doc, optionally place it in a Drive folder, optionally insert initial text, and write an audit record.',
    inputSchema: {title: z.string().min(1), parentFolderId: z.string().optional(), initialText: z.string().optional(), requestId: z.string().optional(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const cleanArgs = args || {};
    try {
      const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
      return textResult(await createGoogleDocOperation({google, admin, auth, user, args: cleanArgs}));
    } catch (err) {
      logDocsCreate('handler_failed', cleanArgs, {errorCode: safeText(err && err.code, 80) || 'DOCS_CREATE_INTERNAL_ERROR', providerStatus: providerStatus(err)});
      return textResult(docsCreateErrorPayload(err, cleanArgs));
    }
  });


  if (process.env.HOME_CENTER_MCP_EXTENDED_TOOLS === 'true') {
  server.registerTool('drive_move', {
    title: 'Drive move',
    description: 'Move a Drive file or folder. dryRun=true previews; execution requires requestId and approved=true.',
    inputSchema: {fileId: z.string(), targetFolderId: z.string(), removeFromCurrentParents: z.boolean().optional().default(true), dryRun: z.boolean().optional().default(true), requestId: z.string().optional(), approved: z.boolean().optional().default(false), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const fileId = safeDriveFileId(args && args.fileId);
    const targetFolderId = safeDriveFileId(args && args.targetFolderId);
    const oldMetadata = await getDriveMetadata(drive, fileId);
    const oldParents = oldMetadata.parents || [];
    if (args && args.dryRun !== false) return textResult(dryRunResult('drive.move', fileId, oldMetadata, {targetFolderId, removeParents: boolArg(args.removeFromCurrentParents, true) ? oldParents : []}, args));
    const requestId = ensureWriteAllowed(args || {});
    const existing = await existingAudit(admin, requestId);
    if (existing && existing.status === 'success') return textResult({idempotent: true, audit: existing});
    if (!(args && args.approved === true)) throw Object.assign(new Error('approved=true is required to move a file.'), {status: 400});
    const removeParents = boolArg(args.removeFromCurrentParents, true) ? oldParents.join(',') : '';
    const updated = await drive.files.update({fileId, addParents: targetFolderId, removeParents, fields: driveFields(), supportsAllDrives: true});
    const newMetadata = cleanDriveFile(updated.data || {});
    const audit = await auditWrite(admin, {actor: user.email, authKind: user.authKind, tool: 'drive_move', operation: 'drive.move', requestId, fileId, affectedFileIds: [fileId], oldMetadata, newMetadata, oldParents, newParents: newMetadata.parents || [], reversible: true, rollback: {operation: 'drive.move', fileId, addParents: oldParents, removeParents: newMetadata.parents || []}, callerNote: args && args.callerNote, providerSummary: `Moved ${oldMetadata.name} to ${targetFolderId}.`});
    return textResult({file: newMetadata, audit: audit.audit});
  });

  server.registerTool('drive_rename', {
    title: 'Drive rename',
    description: 'Rename a Drive file or folder. dryRun=true previews; execution requires requestId and approved=true.',
    inputSchema: {fileId: z.string(), newName: z.string().min(1), dryRun: z.boolean().optional().default(true), requestId: z.string().optional(), approved: z.boolean().optional().default(false), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const fileId = safeDriveFileId(args && args.fileId);
    const newName = safeText(args && args.newName, 240);
    const oldMetadata = await getDriveMetadata(drive, fileId);
    if (args && args.dryRun !== false) return textResult(dryRunResult('drive.rename', fileId, oldMetadata, {newName}, args));
    const requestId = ensureWriteAllowed(args || {});
    const existing = await existingAudit(admin, requestId);
    if (existing && existing.status === 'success') return textResult({idempotent: true, audit: existing});
    if (!(args && args.approved === true)) throw Object.assign(new Error('approved=true is required to rename a file.'), {status: 400});
    const updated = await drive.files.update({fileId, requestBody: {name: newName}, fields: driveFields(), supportsAllDrives: true});
    const newMetadata = cleanDriveFile(updated.data || {});
    const audit = await auditWrite(admin, {actor: user.email, authKind: user.authKind, tool: 'drive_rename', operation: 'drive.rename', requestId, fileId, affectedFileIds: [fileId], oldMetadata, newMetadata, oldParents: oldMetadata.parents || [], newParents: newMetadata.parents || [], reversible: true, rollback: {operation: 'drive.rename', fileId, name: oldMetadata.name}, callerNote: args && args.callerNote, providerSummary: `Renamed ${oldMetadata.name} to ${newName}.`});
    return textResult({file: newMetadata, audit: audit.audit});
  });





  server.registerTool('drive_plan_organize', {
    title: 'Drive plan organize',
    description: 'Build a staged organize plan from folder children and simple name-match rules. Does not mutate Drive.',
    inputSchema: {folderId: z.string(), rules: z.array(z.object({match: z.string(), targetFolderId: z.string(), renamePattern: z.string().optional()})).optional(), goal: z.string().optional(), limit: z.number().int().min(1).max(100).default(50), dryRun: z.boolean().optional().default(true)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const folderId = safeDriveFileId(args && args.folderId);
    const children = await listFolderChildren(drive, folderId, chatGptLimit(args && args.limit, 50, 100), false);
    const rules = Array.isArray(args && args.rules) ? args.rules : [];
    const operations = [];
    for (const file of children) {
      for (const rule of rules) {
        const match = safeText(rule && rule.match, 160).toLowerCase();
        const targetFolderId = safeText(rule && rule.targetFolderId, 220);
        if (!match || !targetFolderId) continue;
        if ((file.name || '').toLowerCase().includes(match)) {
          const renamePattern = safeText(rule && rule.renamePattern, 240);
          const newName = renamePattern ? renamePattern.replace(/\{name\}/g, file.name || '').replace(/\{id\}/g, file.id || '') : '';
          operations.push({type: 'move', fileId: file.id, name: file.name, oldParents: file.parents || [], targetFolderId: safeDriveFileId(targetFolderId), reversible: true});
          if (newName && newName !== file.name) operations.push({type: 'rename', fileId: file.id, oldName: file.name, newName, reversible: true});
          break;
        }
      }
      if (operations.length >= 25) break;
    }
    const planId = `plan-${randomUUID()}`;
    const plan = {planId, status: 'planned', actor: user.email || '', folderId, goal: safeText(args && args.goal, 1000), riskLevel: operations.length > 10 ? 'medium' : 'low', reversible: true, operations, createdAtMs: nowMs(), expectedResult: `${operations.length} proposed operation(s).`, requiredConfirmationLevel: 'approved=true on drive_execute_plan'};
    await mcpCollection(admin, 'driveBridgePlans').doc(planId).set(plan, {merge: false});
    return textResult(plan);
  });

  server.registerTool('drive_execute_plan', {
    title: 'Drive execute plan',
    description: 'Execute an approved staged Drive organize plan. Requires approved=true and requestId.',
    inputSchema: {planId: z.string(), approved: z.boolean(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const requestId = stableRequestId(args && args.requestId);
    if (!(args && args.approved === true)) throw Object.assign(new Error('approved=true is required to execute a plan.'), {status: 400});
    const existing = await existingAudit(admin, requestId);
    if (existing && existing.status === 'success') return textResult({idempotent: true, audit: existing});
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const planRef = mcpCollection(admin, 'driveBridgePlans').doc(safePlanId(args && args.planId));
    const planSnap = await planRef.get();
    if (!planSnap.exists) throw Object.assign(new Error('planId not found.'), {status: 404});
    const plan = planSnap.data() || {};
    if (plan.status === 'executed') return textResult({idempotent: true, plan});
    if (plan.status !== 'planned') throw Object.assign(new Error(`Plan status ${plan.status || 'unknown'} cannot be executed.`), {status: 400});
    const operations = Array.isArray(plan.operations) ? plan.operations.slice(0, 25) : [];
    const results = [];
    for (let i = 0; i < operations.length; i += 1) {
      const op = operations[i];
      const fileId = safeDriveFileId(op.fileId);
      const before = await getDriveMetadata(drive, fileId);
      let after = before;
      if (op.type === 'move') {
        after = cleanDriveFile((await drive.files.update({fileId, addParents: safeDriveFileId(op.targetFolderId), removeParents: (before.parents || []).join(','), fields: driveFields(), supportsAllDrives: true})).data || {});
      } else if (op.type === 'rename') {
        after = cleanDriveFile((await drive.files.update({fileId, requestBody: {name: safeText(op.newName, 240)}, fields: driveFields(), supportsAllDrives: true})).data || {});
      } else {
        results.push({operation: op, skipped: true, reason: 'unsupported operation type'});
        continue;
      }
      const childRequestId = `${requestId}:${i}`;
      await auditWrite(admin, {actor: user.email, authKind: user.authKind, tool: 'drive_execute_plan', operation: `plan.${op.type}`, requestId: childRequestId, fileId, affectedFileIds: [fileId], oldMetadata: before, newMetadata: after, oldParents: before.parents || [], newParents: after.parents || [], reversible: true, rollback: op.type === 'rename' ? {operation: 'drive.rename', fileId, name: before.name} : {operation: 'drive.move', fileId, addParents: before.parents || [], removeParents: after.parents || []}, callerNote: args && args.callerNote, providerSummary: `Executed ${op.type} from ${plan.planId}.`});
      results.push({operation: op, file: after, requestId: childRequestId});
    }
    await planRef.set({status: 'executed', executedAtMs: nowMs(), executedBy: user.email || '', executionRequestId: requestId, results}, {merge: true});
    const audit = await auditWrite(admin, {actor: user.email, authKind: user.authKind, tool: 'drive_execute_plan', operation: 'drive.executePlan', requestId, affectedFileIds: results.map((r) => r.file && r.file.id).filter(Boolean), oldMetadata: {plan}, newMetadata: {results}, reversible: results.every((r) => r.file), rollback: {operation: 'audit.rollbackChildren', requestIds: results.map((r) => r.requestId).filter(Boolean).reverse()}, callerNote: args && args.callerNote, providerSummary: `Executed plan ${plan.planId} with ${results.length} result(s).`});
    return textResult({planId: plan.planId, executed: results.length, results, audit: audit.audit});
  });

  server.registerTool('index_folder', {
    title: 'Index folder',
    description: 'Index folder contents into Firestore for later search/status. Idempotent; unchanged files are skipped.',
    inputSchema: {folderId: z.string(), recursive: z.boolean().optional().default(false), limit: z.number().int().min(1).max(200).default(50), mimeTypes: z.array(z.string()).optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const drive = google.drive({version: 'v3', auth});
    const folderId = safeDriveFileId(args && args.folderId);
    const limit = chatGptLimit(args && args.limit, 50, 200);
    const allowed = Array.isArray(args && args.mimeTypes) ? args.mimeTypes.map((m) => safeText(m, 160)).filter(Boolean) : [];
    const queue = [folderId];
    const indexed = [];
    while (queue.length && indexed.length < limit) {
      const current = queue.shift();
      const children = await listFolderChildren(drive, current, Math.min(1000, limit - indexed.length), false);
      for (const child of children) {
        if (args && args.recursive && child.mimeType === 'application/vnd.google-apps.folder') queue.push(child.id);
        if (child.mimeType === 'application/vnd.google-apps.folder') continue;
        if (allowed.length && !allowed.includes(child.mimeType)) continue;
        indexed.push(await indexOneFile(admin, drive, child));
        if (indexed.length >= limit) break;
      }
    }
    return textResult({folderId, count: indexed.length, updated: indexed.filter((item) => item.updated).length, skipped: indexed.filter((item) => item.skipped).length, files: indexed});
  });

  server.registerTool('index_status', {
    title: 'Index status',
    description: 'Return recent indexed Drive records.',
    inputSchema: {limit: z.number().int().min(1).max(50).default(20)},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args) => {
    const snap = await mcpCollection(admin, 'driveBridgeIndex').orderBy('indexedAtMs', 'desc').limit(chatGptLimit(args && args.limit, 20, 50)).get();
    return textResult({count: snap.size, files: snap.docs.map((doc) => doc.data())});
  });

  server.registerTool('drive_workflow_run', {
    title: 'Drive workflow run',
    description: 'Checkpoint and optionally execute an approved multi-step Drive/Docs workflow in one bridge-owned call. This reduces ChatGPT connector fragility by keeping workflow state server-side.',
    inputSchema: {
      workflowId: z.string().describe('Stable workflow id. Also used as the recovery operationBatchId.'),
      objective: z.string().optional().describe('Human-readable workflow objective.'),
      approved: z.boolean().optional().default(false).describe('Must be true to execute writes. False stores the checkpoint only.'),
      operations: z.array(z.object({
        type: z.enum(['drive_create_folder', 'docs_create', 'docs_append', 'workbook_import_xlsx', 'sheets_create', 'sheets_update_values', 'drive_move', 'drive_rename']),
        requestId: z.string().optional(),
        saveAs: z.string().optional().describe('Output key for created folder/doc ids.'),
        parentFolderId: z.string().optional(),
        parentFolderKey: z.string().optional().describe('Use a previous operation output key.'),
        documentId: z.string().optional(),
        documentKey: z.string().optional().describe('Use a previous docs_create output key.'),
        fileId: z.string().optional(),
        fileKey: z.string().optional(),
        targetFolderId: z.string().optional(),
        targetFolderKey: z.string().optional(),
        name: z.string().optional(),
        title: z.string().optional(),
        heading: z.string().optional(),
        text: z.string().optional(),
        initialText: z.string().optional(),
        workbookBase64: z.string().optional(),
        sourceFileId: z.string().optional(),
        sourceFileName: z.string().optional(),
        sourceQuery: z.string().optional(),
        sourceFolderId: z.string().optional(),
        fileName: z.string().optional(),
        expectedSheetNames: z.array(z.string()).optional(),
        expectedPopulatedCellCounts: z.record(z.string(), z.number()).optional(),
        newName: z.string().optional(),
        removeFromCurrentParents: z.boolean().optional(),
        callerNote: z.string().optional(),
        summary: z.string().optional(),
      })).min(1).max(25),
      callerNote: z.string().optional(),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await driveWorkflowRunOperation({google, admin, auth, user, args: args || {}}));
  });

  server.registerTool('recovery_checkpoint', {
    title: 'Recovery checkpoint',
    description: 'Record intended write operations before executing a multi-step workflow. This does not mutate Drive.',
    inputSchema: {
      operationBatchId: z.string().describe('Stable id for this batch of intended writes.'),
      objective: z.string().describe('Human-readable workflow objective.'),
      intendedOperations: z.array(z.object({
        operationId: z.string().optional(),
        toolName: z.string(),
        requestId: z.string().optional(),
        targetId: z.string().optional(),
        targetName: z.string().optional(),
        summary: z.string().optional(),
      })).min(1).max(50),
      callerNote: z.string().optional(),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const operationBatchId = safeOperationBatchId(args && args.operationBatchId);
    const intendedOperations = Array.isArray(args && args.intendedOperations) ? args.intendedOperations.map(normalizeRecoveryOperation) : [];
    if (!intendedOperations.length) throw Object.assign(new Error('intendedOperations must contain at least one operation.'), {status: 400});
    const ref = mcpCollection(admin, 'driveBridgeRecoveryCheckpoints').doc(operationBatchId);
    const existing = await ref.get();
    const payload = {
      operationBatchId,
      actor: user.email || '',
      authKind: user.authKind || '',
      objective: safeText(args && args.objective, 1000),
      intendedOperations,
      callerNote: safeText(args && args.callerNote, 800),
      status: 'checkpointed',
      createdAtMs: existing.exists ? existing.data().createdAtMs || nowMs() : nowMs(),
      updatedAtMs: nowMs(),
    };
    await ref.set(payload, {merge: false});
    return textResult({ok: true, checkpoint: payload});
  });

  server.registerTool('recovery_status', {
    title: 'Recovery status',
    description: 'Compare a recovery checkpoint against Drive Bridge and action audit records to identify completed and missing writes.',
    inputSchema: {operationBatchId: z.string()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args, extra) => {
    await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const operationBatchId = safeOperationBatchId(args && args.operationBatchId);
    const snap = await mcpCollection(admin, 'driveBridgeRecoveryCheckpoints').doc(operationBatchId).get();
    if (!snap.exists) throw Object.assign(new Error('operationBatchId not found in recovery checkpoints.'), {status: 404});
    const checkpoint = snap.data() || {};
    const auditByRequestId = {};
    const operations = Array.isArray(checkpoint.intendedOperations) ? checkpoint.intendedOperations : [];
    for (const operation of operations) {
      const requestId = safeText(operation && operation.requestId, 160);
      if (!requestId) continue;
      auditByRequestId[requestId] = {
        driveAudit: await existingAudit(admin, requestId),
        actionAudit: await existingActionAudit(admin, requestId),
      };
    }
    const status = summarizeRecoveryOperations(operations, auditByRequestId);
    return textResult({operationBatchId, objective: checkpoint.objective || '', complete: status.complete, counts: {completed: status.completed.length, missing: status.missing.length, failed: status.failed.length, total: status.operations.length}, operations: status.operations, nextOperation: status.nextOperation});
  });

  server.registerTool('audit_log', {
    title: 'Audit log',
    description: 'Read recent Drive Bridge write audit entries, optionally filtered by fileId or requestId.',
    inputSchema: {limit: z.number().int().min(1).max(50).default(20), fileId: z.string().optional(), requestId: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args) => {
    if (safeText(args && args.requestId, 160)) {
      const audit = await existingAudit(admin, args.requestId);
      return textResult({count: audit ? 1 : 0, entries: audit ? [audit] : []});
    }
    const snap = await mcpCollection(admin, 'driveBridgeAudit').orderBy('timestampMs', 'desc').limit(chatGptLimit(args && args.limit, 20, 50)).get();
    const fileId = safeText(args && args.fileId, 220);
    const entries = snap.docs.map((doc) => doc.data()).filter((entry) => !fileId || entry.fileId === fileId || (Array.isArray(entry.affectedFileIds) && entry.affectedFileIds.includes(fileId)));
    return textResult({count: entries.length, entries});
  });

  server.registerTool('audit_get', {
    title: 'Audit get',
    description: 'Read one audit entry by requestId.',
    inputSchema: {requestId: z.string()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args) => {
    const audit = await existingAudit(admin, stableRequestId(args && args.requestId));
    if (!audit) throw Object.assign(new Error('requestId not found in audit log.'), {status: 404});
    return textResult({audit});
  });
  }

  installAuthenticatedToolsListHandler(server);
  return server;
}

function createHomeCenterMcpApp({google, admin, googleClientId = () => '', googleClientSecret = () => '', githubToken = () => ''}) {
  const app = express();
  app.use(express.json({limit: '80mb'}));
  app.use(express.urlencoded({extended: false, limit: '256kb'}));
  const transports = {};

  app.get('/', (_req, res) => {
    res.json({ok: true, service: 'home-center-drive-bridge', endpoints: ['/sse', '/messages', '/mcp'], oauthProtectedResource: MCP_RESOURCE_METADATA});
  });

  app.get('/oauth-protected-resource', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(oauthProtectedResourceMetadata());
  });

  app.get('/oauth-protected-resource-v2', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(oauthProtectedResourceMetadata());
  });

  app.get('/.well-known/oauth-protected-resource', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(oauthProtectedResourceMetadata());
  });

  app.get('/.well-known/oauth-authorization-server', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(authorizationServerMetadata());
  });

  app.get('/.well-known/openid-configuration', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(openIdConfigurationMetadata());
  });

  app.get('/oauth/jwks', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json({keys: []});
  });

  app.get('/oauth/userinfo', async (req, res) => {
    try {
      connectorLog('userinfo_start', req);
      if (rejectMissingTransportAuth(req, res)) return;
      const accessToken = String(req.get('Authorization') || '').replace(/^Bearer\s+/i, '');
      const context = await loadMcpAccessContext(admin, google, googleClientId(), googleClientSecret(), accessToken);
      if (!context || !context.user || !context.user.email) {
        res.set('WWW-Authenticate', oauthChallenge());
        res.status(401).json({error: 'invalid_token'});
        return;
      }
      connectorLog('userinfo_success', req, {emailHash: tokenHashPrefix(context.user.email)});
      res.json({
        sub: tokenHash(context.user.email),
        email: context.user.email,
        email_verified: true,
      });
    } catch (err) {
      if (err.wwwAuthenticate) res.set('WWW-Authenticate', err.wwwAuthenticate);
      res.status(err.status || 500).json({error: err.status === 401 ? 'invalid_token' : 'server_error', error_description: err.message || String(err)});
    }
  });

  app.post('/oauth/register', async (req, res) => {
    connectorLog('register_start', req, {redirectUriCount: Array.isArray(req.body && req.body.redirect_uris) ? req.body.redirect_uris.length : 0});
    const clientId = `home_center_mcp_${randomUUID()}`;
    const redirectUris = Array.isArray(req.body && req.body.redirect_uris) ? req.body.redirect_uris.map((uri) => safeText(uri, 800)).filter(Boolean) : [];
    await oauthCollection(admin, 'mcpOAuthClients').doc(clientId).set({
      clientId,
      redirectUris,
      clientName: safeText(req.body && req.body.client_name, 200) || 'ChatGPT',
      createdAtMs: Date.now(),
    });
    connectorLog('register_success', req, {issuedClientIdPrefix: clientId.slice(0, 28), redirectUriCount: redirectUris.length});
    res.status(201).json({
      client_id: clientId,
      client_id_issued_at: Math.floor(Date.now() / 1000),
      redirect_uris: redirectUris,
      grant_types: ['authorization_code', 'refresh_token'],
      response_types: ['code'],
      token_endpoint_auth_method: 'none',
    });
  });

  app.get('/oauth/authorize', async (req, res) => {
    try {
      connectorLog('authorize_start', req, {resource: safeText(req.query.resource, 240), scope: safeText(req.query.scope, 400)});
      if (!googleClientId() || !googleClientSecret()) {
        res.status(503).send('Home Center Google OAuth is not configured.');
        return;
      }
      const clientId = safeText(req.query.client_id, 800);
      const redirectUri = safeText(req.query.redirect_uri, 1200);
      const responseType = safeText(req.query.response_type, 40);
      const state = safeText(req.query.state, 1200);
      const codeChallenge = safeText(req.query.code_challenge, 300);
      const method = safeText(req.query.code_challenge_method, 20) || 'plain';
      const browserHandoff = shouldUseConnectorHandoff(req, redirectUri);
      const chatgptConnector = isChatgptConnectorRedirectUri(redirectUri);
      const oauthFlowId = tokenHashPrefix(`${clientId}:${state}:${Date.now()}:${randomUUID()}`);
      if (responseType !== 'code' || !clientId || !redirectUri) {
        res.status(400).send('invalid_request');
        return;
      }
      const clientSnap = await oauthCollection(admin, 'mcpOAuthClients').doc(clientId).get();
      if (clientSnap.exists) {
        const allowed = clientSnap.data().redirectUris || [];
        if (allowed.length && !allowed.includes(redirectUri)) {
          res.redirect(redirectWithParams(redirectUri, {error: 'invalid_request', error_description: 'redirect_uri_not_registered', state}));
          return;
        }
      }
      const flowState = randomToken(24);
      await oauthCollection(admin, 'mcpOAuthStates').doc(flowState).set({
        clientId,
        redirectUri,
        state,
        codeChallenge,
        codeChallengeMethod: method,
        browserHandoff,
        chatgptConnector,
        oauthFlowId,
        createdAtMs: Date.now(),
        expiresAtMs: Date.now() + 10 * 60 * 1000,
      });
      const client = googleOAuthClient(google, googleClientId(), googleClientSecret(), MCP_GOOGLE_CALLBACK);
      const url = client.generateAuthUrl({
        access_type: 'offline',
        prompt: 'consent',
        scope: ['openid', 'email', ...MCP_REQUIRED_SCOPES],
        state: flowState,
      });
      if (browserHandoff) {
        const redirectMode = chatgptConnector ? 'chatgpt_mobile_handoff' : 'secure_browser_handoff';
        connectorLog('authorize_secure_browser_handoff', req, {googleCallbackHost: redirectHost(MCP_GOOGLE_CALLBACK), redirectMode, chatgptConnector, oauthFlowId});
        res.set('Cache-Control', 'no-store');
        res.status(200).type('html').send(renderSecureBrowserOAuthHandoff(url, flowState, chatgptConnector ? 'chatgpt-mobile' : 'secure-browser'));
        return;
      }
      connectorLog('authorize_redirect_google', req, {googleCallbackHost: redirectHost(MCP_GOOGLE_CALLBACK), redirectMode: 'direct', chatgptConnector, oauthFlowId});
      res.redirect(url);
    } catch (err) {
      connectorLog('authorize_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(500).send(err.message || String(err));
    }
  });

  app.get('/oauth/google-callback', async (req, res) => {
    try {
      connectorLog('google_callback_start', req, {hasCode: !!safeText(req.query.code, 32), googleError: safeText(req.query.error, 120)});
      const flowState = safeText(req.query.state, 300);
      const googleCode = safeText(req.query.code, 4096);
      const error = safeText(req.query.error, 300);
      const stateSnap = flowState ? await oauthCollection(admin, 'mcpOAuthStates').doc(flowState).get() : null;
      if (!stateSnap || !stateSnap.exists) {
        res.status(400).send('invalid_oauth_state');
        return;
      }
      const stateData = stateSnap.data() || {};
      if (error) {
        if (stateData.browserHandoff) {
          await stateSnap.ref.set({handoffError: error, updatedAtMs: Date.now()}, {merge: true});
          connectorLog('google_callback_handoff_error', req, {googleError: error, clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector});
          res.set('Cache-Control', 'no-store');
          res.status(200).type('html').send(renderSecureBrowserOAuthComplete('Google sign-in did not complete. Return to ChatGPT and reconnect the connector.'));
          return;
        }
        await stateSnap.ref.delete();
        res.redirect(redirectWithParams(stateData.redirectUri, {error, state: stateData.state}));
        return;
      }
      if (!googleCode || safeNumber(stateData.expiresAtMs, 0) <= Date.now()) {
        if (stateData.browserHandoff) {
          await stateSnap.ref.set({handoffError: 'invalid_grant', updatedAtMs: Date.now()}, {merge: true});
          connectorLog('google_callback_handoff_invalid', req, {expired: safeNumber(stateData.expiresAtMs, 0) <= Date.now(), clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector});
          res.set('Cache-Control', 'no-store');
          res.status(200).type('html').send(renderSecureBrowserOAuthComplete('This sign-in attempt expired. Return to ChatGPT and reconnect the connector.'));
          return;
        }
        await stateSnap.ref.delete();
        res.redirect(redirectWithParams(stateData.redirectUri, {error: 'invalid_grant', state: stateData.state}));
        return;
      }
      const client = googleOAuthClient(google, googleClientId(), googleClientSecret(), MCP_GOOGLE_CALLBACK);
      const {tokens} = await client.getToken(googleCode);
      client.setCredentials(tokens);
      const oauth2 = google.oauth2({version: 'v2', auth: client});
      const profile = await oauth2.userinfo.get();
      const email = safeText(profile.data && profile.data.email, 320).toLowerCase();
      if (!email || profile.data.verified_email === false) {
        if (stateData.browserHandoff) {
          await stateSnap.ref.set({handoffError: 'verified_google_email_required', updatedAtMs: Date.now()}, {merge: true});
          connectorLog('google_callback_handoff_unverified_email', req, {clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector});
          res.set('Cache-Control', 'no-store');
          res.status(200).type('html').send(renderSecureBrowserOAuthComplete('Google sign-in requires a verified email. Return to ChatGPT and reconnect the connector.'));
          return;
        }
        await stateSnap.ref.delete();
        res.redirect(redirectWithParams(stateData.redirectUri, {error: 'access_denied', error_description: 'verified_google_email_required', state: stateData.state}));
        return;
      }
      if (stateData.browserHandoff) {
        await stateSnap.ref.set({
          googleTokens: tokens,
          email,
          googleCompletedAtMs: Date.now(),
          updatedAtMs: Date.now(),
        }, {merge: true});
        connectorLog('google_callback_handoff_ready', req, {clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector, emailHash: tokenHashPrefix(email)});
        res.set('Cache-Control', 'no-store');
        res.status(200).type('html').send(renderSecureBrowserOAuthComplete('Home Center approved Google sign-in. Finishing the ChatGPT connector now...', `${mcpMountedPath('/oauth/handoff-complete')}?state=${encodeURIComponent(flowState)}`));
        return;
      }
      const code = randomToken(32);
      await oauthCollection(admin, 'mcpOAuthCodes').doc(tokenHash(code)).set({
        clientId: stateData.clientId,
        redirectUri: stateData.redirectUri,
        state: stateData.state,
        codeChallenge: stateData.codeChallenge || '',
        codeChallengeMethod: stateData.codeChallengeMethod || '',
        googleTokens: tokens,
        email,
        oauthFlowId: stateData.oauthFlowId || '',
        chatgptConnector: !!stateData.chatgptConnector,
        createdAtMs: Date.now(),
        expiresAtMs: Date.now() + 10 * 60 * 1000,
      });
      await stateSnap.ref.delete();
      connectorLog('google_callback_success', req, {clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector, emailHash: tokenHashPrefix(email)});
      res.redirect(redirectWithParams(stateData.redirectUri, {code, state: stateData.state}));
    } catch (err) {
      connectorLog('google_callback_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(500).send(err.message || String(err));
    }
  });

  app.get('/oauth/handoff-status', async (req, res) => {
    try {
      const flowState = safeText(req.query.state, 300);
      const stateSnap = flowState ? await oauthCollection(admin, 'mcpOAuthStates').doc(flowState).get() : null;
      res.set('Cache-Control', 'no-store');
      if (!stateSnap || !stateSnap.exists) {
        res.status(404).json({status: 'error', message: 'Sign-in state was not found. Reconnect the connector and try again.'});
        return;
      }
      const stateData = stateSnap.data() || {};
      if (!stateData.browserHandoff) {
        res.status(400).json({status: 'error', message: 'This sign-in flow is not a browser handoff.'});
        return;
      }
      if (safeNumber(stateData.expiresAtMs, 0) <= Date.now()) {
        res.json({status: 'expired', message: 'This sign-in attempt expired. Reconnect the connector and try again.'});
        return;
      }
      if (stateData.handoffError) {
        res.json({status: 'error', message: 'Google sign-in did not complete. Reconnect the connector and try again.'});
        return;
      }
      if (stateData.googleTokens && stateData.email) {
        res.json({status: 'complete'});
        return;
      }
      if (stateData.handoffRedirectUrl) {
        res.json({status: 'complete'});
        return;
      }
      res.json({status: 'pending'});
    } catch (err) {
      connectorLog('handoff_status_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(500).json({status: 'error', message: 'Home Center could not read sign-in status.'});
    }
  });

  app.get('/oauth/handoff-complete', async (req, res) => {
    try {
      const flowState = safeText(req.query.state, 300);
      const stateSnap = flowState ? await oauthCollection(admin, 'mcpOAuthStates').doc(flowState).get() : null;
      if (!stateSnap || !stateSnap.exists) {
        res.status(400).send('invalid_oauth_state');
        return;
      }
      const stateData = stateSnap.data() || {};
      if (stateData.handoffRedirectUrl && safeNumber(stateData.expiresAtMs, 0) > Date.now()) {
        connectorLog('handoff_complete_replay_redirect', req, {clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector, emailHash: tokenHashPrefix(stateData.email)});
        res.redirect(stateData.handoffRedirectUrl);
        return;
      }
      if (!stateData.browserHandoff || !stateData.googleTokens || !stateData.email || safeNumber(stateData.expiresAtMs, 0) <= Date.now()) {
        res.status(400).send('invalid_oauth_state');
        return;
      }
      const code = randomToken(32);
      await oauthCollection(admin, 'mcpOAuthCodes').doc(tokenHash(code)).set({
        clientId: stateData.clientId,
        redirectUri: stateData.redirectUri,
        state: stateData.state,
        codeChallenge: stateData.codeChallenge || '',
        codeChallengeMethod: stateData.codeChallengeMethod || '',
        googleTokens: stateData.googleTokens,
        email: safeText(stateData.email, 320).toLowerCase(),
        oauthFlowId: stateData.oauthFlowId || '',
        chatgptConnector: !!stateData.chatgptConnector,
        flowState,
        createdAtMs: Date.now(),
        expiresAtMs: Date.now() + 10 * 60 * 1000,
      });
      const handoffRedirectUrl = redirectWithParams(stateData.redirectUri, {code, state: stateData.state});
      await stateSnap.ref.set({
        handoffCompletedAtMs: Date.now(),
        handoffRedirectUrl,
        googleTokens: stateData.googleTokens,
        email: stateData.email,
        updatedAtMs: Date.now(),
      }, {merge: true});
      connectorLog('handoff_complete_redirect', req, {clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector, emailHash: tokenHashPrefix(stateData.email)});
      res.redirect(handoffRedirectUrl);
    } catch (err) {
      connectorLog('handoff_complete_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(500).send(err.message || String(err));
    }
  });

  app.post('/oauth/token', async (req, res) => {
    try {
      connectorLog('token_start', req, {grantType: safeText(req.body && req.body.grant_type, 80)});
      const grantType = safeText(req.body && req.body.grant_type, 80);
      const clientId = safeText(req.body && req.body.client_id, 800);

      if (grantType === 'refresh_token') {
        const refreshToken = safeText(req.body && req.body.refresh_token, 4096);
        if (!refreshToken || !clientId) {
          res.status(400).json({error: 'invalid_request'});
          return;
        }
        const refreshSnap = await oauthCollection(admin, 'mcpOAuthRefreshTokens').doc(tokenHash(refreshToken)).get();
        if (!refreshSnap.exists) {
          res.status(400).json({error: 'invalid_grant'});
          return;
        }
        const refreshData = refreshSnap.data() || {};
        if (refreshData.clientId !== clientId || refreshData.revokedAtMs) {
          res.status(400).json({error: 'invalid_grant'});
          return;
        }
        const accessToken = randomToken(32);
        const expiresAtMs = Date.now() + 55 * 60 * 1000;
        await oauthCollection(admin, 'mcpOAuthAccessTokens').doc(tokenHash(accessToken)).set({
          clientId,
          email: refreshData.email,
          googleTokens: refreshData.googleTokens,
          refreshTokenHash: tokenHash(refreshToken),
          createdAtMs: Date.now(),
          expiresAtMs,
        });
        connectorLog('token_refresh_success', req, {emailHash: tokenHashPrefix(refreshData.email), expiresIn: 3300});
        res.json({access_token: accessToken, token_type: 'Bearer', expires_in: 3300, scope: MCP_REQUIRED_SCOPES.join(' ')});
        return;
      }

      const code = safeText(req.body && req.body.code, 4096);
      const redirectUri = safeText(req.body && req.body.redirect_uri, 1200);
      const verifier = safeText(req.body && req.body.code_verifier, 300);
      if (grantType !== 'authorization_code' || !code || !clientId || !redirectUri) {
        res.status(400).json({error: 'invalid_request'});
        return;
      }
      const codeSnap = await oauthCollection(admin, 'mcpOAuthCodes').doc(tokenHash(code)).get();
      if (!codeSnap.exists) {
        res.status(400).json({error: 'invalid_grant'});
        return;
      }
      const data = codeSnap.data() || {};
      await codeSnap.ref.delete();
      if (safeNumber(data.expiresAtMs, 0) <= Date.now() || data.clientId !== clientId || data.redirectUri !== redirectUri) {
        connectorLog('token_invalid_grant', req, {clientIdPrefix: safeText(data.clientId || clientId, 80).slice(0, 28), redirectHost: redirectHost(redirectUri), oauthFlowId: data.oauthFlowId || '', chatgptConnector: !!data.chatgptConnector, reason: 'expired_client_or_redirect_mismatch'});
        res.status(400).json({error: 'invalid_grant'});
        return;
      }
      if (data.codeChallenge) {
        const validPkce = data.codeChallengeMethod === 'S256' ? pkceChallenge(verifier) === data.codeChallenge : verifier === data.codeChallenge;
        if (!validPkce) {
          connectorLog('token_invalid_grant', req, {clientIdPrefix: safeText(data.clientId || clientId, 80).slice(0, 28), redirectHost: redirectHost(redirectUri), oauthFlowId: data.oauthFlowId || '', chatgptConnector: !!data.chatgptConnector, reason: 'pkce_verification_failed'});
          res.status(400).json({error: 'invalid_grant', error_description: 'pkce_verification_failed'});
          return;
        }
      }
      const accessToken = randomToken(32);
      const refreshToken = randomToken(40);
      const refreshTokenHash = tokenHash(refreshToken);
      const expiresAtMs = Date.now() + 55 * 60 * 1000;
      await oauthCollection(admin, 'mcpOAuthRefreshTokens').doc(refreshTokenHash).set({
        clientId,
        email: data.email,
        googleTokens: data.googleTokens,
        createdAtMs: Date.now(),
        updatedAtMs: Date.now(),
      });
      await oauthCollection(admin, 'mcpOAuthAccessTokens').doc(tokenHash(accessToken)).set({
        clientId,
        email: data.email,
        googleTokens: data.googleTokens,
        refreshTokenHash,
        createdAtMs: Date.now(),
        expiresAtMs,
      });
      if (data.flowState) {
        await oauthCollection(admin, 'mcpOAuthStates').doc(safeText(data.flowState, 300)).delete().catch(() => {});
      }
      connectorLog('token_success', req, {clientIdPrefix: safeText(data.clientId || clientId, 80).slice(0, 28), redirectHost: redirectHost(redirectUri), oauthFlowId: data.oauthFlowId || '', chatgptConnector: !!data.chatgptConnector, emailHash: tokenHashPrefix(data.email), expiresIn: 3300, issuedRefreshToken: true});
      res.json({access_token: accessToken, refresh_token: refreshToken, token_type: 'Bearer', expires_in: 3300, scope: MCP_REQUIRED_SCOPES.join(' ')});
    } catch (err) {
      connectorLog('token_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(500).json({error: 'server_error', error_description: err.message || String(err)});
    }
  });

  app.get('/auth-challenge', (_req, res) => {
    res.set('WWW-Authenticate', oauthChallenge());
    res.status(401).json({error: 'authorization_required', resource_metadata: MCP_RESOURCE_METADATA, scopes: MCP_REQUIRED_SCOPES});
  });

  app.get('/sse', async (req, res) => {
    if (rejectMissingTransportAuth(req, res)) return;
    const transport = new SSEServerTransport('/homeCenterMcp/messages', res);
    transports[transport.sessionId] = transport;
    res.on('close', () => {
      delete transports[transport.sessionId];
    });
    const server = createHomeCenterMcpServer({google, admin, googleClientId, googleClientSecret, githubToken});
    await server.connect(transport);
  });

  app.post('/messages', async (req, res) => {
    if (rejectMissingTransportAuth(req, res)) return;
    const sessionId = req.query.sessionId;
    const transport = transports[sessionId];
    if (!(transport instanceof SSEServerTransport)) {
      res.status(400).json({jsonrpc: '2.0', error: {code: -32000, message: 'No SSE transport found for sessionId'}, id: null});
      return;
    }
    await transport.handlePostMessage(req, res, req.body);
  });

  app.all('/mcp', async (req, res) => {
    const toolCallFields = mcpToolCallFields(req);
    if (rejectMissingTransportAuth(req, res)) {
      connectorLog('mcp_reject_missing_auth', req, toolCallFields);
      return;
    }
    connectorLog('mcp_start', req, toolCallFields);
    if (req.method !== 'POST') {
      res.status(405).json({jsonrpc: '2.0', error: {code: -32000, message: 'Method not allowed.'}, id: null});
      return;
    }
      const server = createHomeCenterMcpServer({google, admin, googleClientId, googleClientSecret, githubToken});
    const transport = new StreamableHTTPServerTransport({sessionIdGenerator: undefined});
    let closed = false;
    const closeTransport = async () => {
      if (closed) return;
      closed = true;
      await Promise.allSettled([transport.close(), server.close()]);
    };
    try {
      res.on('close', () => {
        closeTransport().catch(() => {});
      });
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
      connectorLog('mcp_success', req, toolCallFields);
    } catch (err) {
      connectorLog('mcp_error', req, {...toolCallFields, error: safeText(err.message || String(err), 300)});
      if (!res.headersSent) {
        if (err.wwwAuthenticate) res.set('WWW-Authenticate', err.wwwAuthenticate);
        res.status(err.status || 500).json({jsonrpc: '2.0', error: {code: -32603, message: err.message || String(err)}, id: null});
      }
    } finally {
      await closeTransport();
    }
  });

  return app;
}

module.exports = {createHomeCenterMcpApp, createHomeCenterMcpServer, createDriveFolderOperation, createGoogleDocOperation, appendGoogleDocOperation, publishContextSnapshotOperation, createSheetOperation, updateSheetValuesOperation, importXlsxWorkbookOperation, driveOperationRunOperation, driveWorkflowRunOperation, simulationOperationRunOperation, simulationOperationRegistry, normalizeRecoveryOperation, summarizeRecoveryOperations, loadMcpAccessContext};
