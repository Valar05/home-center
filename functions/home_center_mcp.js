const {createHash, randomBytes, randomUUID, createSign} = require('node:crypto');
const {Readable, Transform} = require('node:stream');
const {pipeline} = require('node:stream/promises');
const {Storage} = require('@google-cloud/storage');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const isoGit = require('isomorphic-git');
const isoGitHttp = require('isomorphic-git/http/node');
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {SSEServerTransport} = require('@modelcontextprotocol/sdk/server/sse.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');
const {ListToolsRequestSchema} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/types.js');
const {normalizeObjectSchema} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/server/zod-compat.js');
const {toJsonSchemaCompat} = require('./node_modules/@modelcontextprotocol/sdk/dist/cjs/server/zod-json-schema-compat.js');
const express = require('express');
const {z} = require('zod/v4');
const {CARTESIA_DEFAULT_MODEL_ID, CARTESIA_DEFAULT_VOICE_NAME, listCartesiaVoiceCatalog, listCartesiaVoices, normalizeCartesiaVoice, openCartesiaStream} = require('./hosted_speech_provider');
const {refreshGeminiCatalog} = require('./gemini_speech_provider');
const {synthesizeGeminiArtifact} = require('./gemini_tts_artifact_service');
const voiceTierPolicy = require('./voice_tier_policy');
const {preflightArtifactEnvelope} = require('./artifact_transport');
const {openAiFileParamJsonSchema, openAiFileParamZodSchema, materializeOpenAiHostFile, materializeOpenAiHostFileToTemp} = require('./host_file_ingress');
const {
  beginDriveBinaryReadOperation,
  readDriveBinarySessionChunkOperation,
  driveBinaryReadStatusOperation,
  completeDriveBinaryReadOperation,
} = require('./drive_binary_read_service');
const {driveTextPatchOperation} = require('./drive_text_patch_service');
const cartesiaPitchShift = require('./cartesia_pitch_shift');
const {renderAudioOperation, audioRenderStatusOperation, inspectAudioArtifactsOperation, uploadVerified: uploadVerifiedArtifact} = require('./audio_render_service');
const {recoverAudioRenderRegistrationOperation, linkDriveAudioToReaderStageOperation} = require('./audio_catalog_service');
const {localVoiceOperationEntries, localVoiceOperationRunOperation} = require('./local_voice_farm_api');
const {computerHandsOperationEntries, computerHandsOperationRunOperation} = require('./computer_hands_api');
const {entryList: ritsuVoiceOperationEntries, runOperation: ritsuVoiceOperationRunOperation} = require('./ritsu_voice_api');
const {entryList: ritsuChatCallbackOperationEntries, runOperation: ritsuChatCallbackRunOperation} = require('./ritsu_chat_callback_api');
const {enqueuePhoneCommand, getPhoneCommand, listPhoneDevices} = require('./phone_hands_relay');
const {browserNerveOperationEntries, browserNerveOperationRunOperation} = require('./browser_nerve_api');
const {veniceBodyOperationEntries, veniceBodyOperationRunOperation} = require('./venice_body_router');
const {veniceNerveOperationEntries, veniceNerveOperationRunOperation} = require('./venice_nerve_api');
const {materializeReceiptArtifactsOperation, recordArtifactReviewOperation, linkArtifactReviewSuccessorOperation} = require('./artifact_delivery_service');
const {
  analyzeSourceOperation,
  transcribeSlateOperation,
  segmentSourceOperation,
  renderSourceConditionedOperation,
  sfxForgeStatusOperation,
} = require('./sfx_forge_service');
const {armoryReceiptOperation, armoryRecountOperation, armoryCasingOperation} = require('./armory_range_service');
const {
  ARTIFACT_INGEST_MAX_BYTES,
  artifactOperationEntries,
  ingestArtifactUploadOperation,
  beginArtifactIngestOperation,
  beginResumableArtifactIngestOperation,
  resumableArtifactStatusOperation,
  resumeResumableArtifactIngestOperation,
  commitResumableArtifactIngestOperation,
  appendArtifactChunkOperation,
  commitArtifactIngestOperation,
  abortArtifactIngestOperation,
  readArtifactOperation,
  findArtifactBySha256Operation,
} = require('./artifact_ingest_service');
const {
  operationEntries: blenderWorkspaceOperationEntries,
  runOperation: runBlenderWorkspaceOperation,
  retiredFoundryError,
} = require('./blender_workspace_capability');
const {installLegacyFoundryArtifactRoutes} = require('./legacy_foundry_artifacts');
const {
  filesystemOperationEntries,
  runFilesystemOperation,
  projectArtifactOperation,
  streamFilesystemContent,
} = require('./gcs_filesystem_service');
const {
  callerFromHomeCenterUser,
  fortressOnlineOperation,
  homeCenterSessionStatusOperation,
  homeCenterSessionUpdateOperation,
  homeCenterWorkRequestOperation,
  homeCenterWorkStatusOperation,
} = require('./home_center_fortress');
const {
  CALENDAR_SCOPE: SMS_CALENDAR_SCOPE,
  GMAIL_SCOPE: SMS_GMAIL_SCOPE,
  registry: smsCalendarOperationRegistry,
  runOperation: smsCalendarOperationRunOperation,
} = require('./sms_calendar_intake');
const {assertHomeCenterIdentityAllowed} = require('./home_center_access_policy');
const {registerHeadcrabReminderTools} = require('./headcrab_reminder_store');
const {homeCenterIdentityStatusOperation, homeCenterIdentityRevokeOperation} = require('./home_center_identity_security');

const DEFAULT_MCP_PUBLIC_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
const DEFAULT_MCP_AUTHORIZATION_SERVER_BASE = 'https://homecentermcp-vxybsaualq-uc.a.run.app';
const MCP_PUBLIC_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || DEFAULT_MCP_PUBLIC_BASE;
const MCP_AUTHORIZATION_SERVER_BASE = process.env.HOME_CENTER_MCP_AUTHORIZATION_SERVER_BASE || DEFAULT_MCP_AUTHORIZATION_SERVER_BASE;
const HOME_CENTER_MCP_SERVER_VERSION = '0.3.1';
const HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-10-02.headcrab-durable-reminders-v1';
const HOME_CENTER_REGISTRY_VERSION = HOME_CENTER_CONNECTOR_SCHEMA_REVISION;
const HOME_CENTER_DIRECT_FILE_TOOLS = Object.freeze(['drive_ingest_file', 'storage_ingest_artifact']);
const MCP_RESOURCE = `${MCP_AUTHORIZATION_SERVER_BASE}/mcp`;
const MCP_LEGACY_RESOURCE = `${MCP_PUBLIC_BASE}/mcp`;
const MCP_RESOURCE_METADATA = `${MCP_AUTHORIZATION_SERVER_BASE}/.well-known/oauth-protected-resource`;
const MCP_PATH_RESOURCE_METADATA = `${MCP_RESOURCE_METADATA}/mcp`;
const MCP_LEGACY_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/.well-known/oauth-protected-resource`;
const MCP_LEGACY_RESOURCE_METADATA_ALIAS = `${MCP_PUBLIC_BASE}/oauth-protected-resource`;
const MCP_COMPAT_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/oauth-protected-resource-v2`;
const MCP_AUTHORIZATION_SERVER_METADATA = `${MCP_AUTHORIZATION_SERVER_BASE}/.well-known/oauth-authorization-server`;
// Keep Google's already-registered callback stable while moving MCP discovery and token exchange
// to a path-free issuer that clean OAuth clients can discover according to RFC 8414.
const MCP_GOOGLE_CALLBACK = process.env.HOME_CENTER_MCP_GOOGLE_CALLBACK || `${MCP_PUBLIC_BASE}/oauth/google-callback`;
const COMMAND_CENTER_MCP_URL = process.env.COMMAND_CENTER_MCP_URL || 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const TVTROPER_RETRIEVAL_URL = process.env.TVTROPER_RETRIEVAL_URL || '';
const TVTROPER_OPERATION_REGISTRY_VERSION = 'tvtroper-gcs-retrieval-v1';
const HOME_CENTER_GENERATED_ARTIFACT_BUCKET = process.env.GENERATED_ARTIFACT_BUCKET || process.env.HOME_CENTER_ARTIFACT_BUCKET || 'home-center-generated';
const HOME_CENTER_DRIVE_INGEST_MAX_BYTES = Number(process.env.HOME_CENTER_DRIVE_INGEST_MAX_BYTES || 256 * 1024 * 1024);
const HOME_CENTER_SITES_SOURCE_MAX_FILES = Number(process.env.HOME_CENTER_SITES_SOURCE_MAX_FILES || 2000);
const HOME_CENTER_SITES_SOURCE_MAX_BYTES = Number(process.env.HOME_CENTER_SITES_SOURCE_MAX_BYTES || 256 * 1024 * 1024);
const MCP_REQUIRED_SCOPES = [
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/spreadsheets',
  SMS_GMAIL_SCOPE,
  SMS_CALENDAR_SCOPE,
];
const GROUNDED_MOTION_MCP_RESOURCE = process.env.GROUNDED_MOTION_MCP_RESOURCE || 'https://grounded-motion-mcp-220218838446.us-central1.run.app/mcp';
const GROUNDED_MOTION_MCP_SCOPE = 'grounded-motion:vanguard-canary';
const GROUNDED_MOTION_ALLOWED_EMAIL = 'dclarke1005@gmail.com';
const OAUTH_OFFLINE_ACCESS_SCOPE = 'offline_access';
const MCP_OAUTH_SECURITY_SCHEMES = [{type: 'oauth2', scopes: MCP_REQUIRED_SCOPES}];
const OAUTH_RESOURCE_GRANTS = Object.freeze({
  [MCP_RESOURCE]: Object.freeze({
    resource: MCP_RESOURCE,
    scopes: Object.freeze([...MCP_REQUIRED_SCOPES]),
    googleScopes: Object.freeze(['openid', 'email', ...MCP_REQUIRED_SCOPES]),
    allowedEmails: null,
  }),
  [MCP_LEGACY_RESOURCE]: Object.freeze({
    resource: MCP_LEGACY_RESOURCE,
    scopes: Object.freeze([...MCP_REQUIRED_SCOPES]),
    googleScopes: Object.freeze(['openid', 'email', ...MCP_REQUIRED_SCOPES]),
    allowedEmails: null,
  }),
  [GROUNDED_MOTION_MCP_RESOURCE]: Object.freeze({
    resource: GROUNDED_MOTION_MCP_RESOURCE,
    scopes: Object.freeze([GROUNDED_MOTION_MCP_SCOPE]),
    googleScopes: Object.freeze(['openid', 'email']),
    allowedEmails: Object.freeze([GROUNDED_MOTION_ALLOWED_EMAIL]),
  }),
});

function resolveOAuthGrant(resourceValue, scopeValue) {
  const resource = String(resourceValue || MCP_RESOURCE).trim();
  const grant = OAUTH_RESOURCE_GRANTS[resource];
  if (!grant) {
    const err = new Error('invalid_target');
    err.status = 400;
    throw err;
  }
  const requested = String(scopeValue || '').trim().split(/\s+/).filter(Boolean);
  const scopes = requested.length ? requested : [...grant.scopes];
  const allowedScopes = [...grant.scopes, OAUTH_OFFLINE_ACCESS_SCOPE];
  if (scopes.some((scope) => !allowedScopes.includes(scope))) {
    const err = new Error('invalid_scope');
    err.status = 400;
    throw err;
  }
  return {...grant, scopes};
}
const CREDIT_GATED_EMAILS = Object.freeze([
  'dclarke1005@gmail.com',
  'timothypomeroy07@gmail.com',
]);
const CREDIT_GATED_EMAIL_SET = new Set(CREDIT_GATED_EMAILS);

const GITHUB_ADMIN_ALLOWED_EMAILS = Object.freeze([
  'dclarke1005@gmail.com',
  'timothypomeroy07@gmail.com',
]);
const GITHUB_ADMIN_ALLOWED_EMAIL_SET = new Set(GITHUB_ADMIN_ALLOWED_EMAILS);
const GITHUB_ADMIN_LEGACY_EMAIL = 'dclarke1005@gmail.com';

function requireCreditGatedEmail(email, surface = 'credit-backed operation') {
  const clean = safeText(email, 320).toLowerCase();
  assertHomeCenterIdentityAllowed(clean, surface);
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

function requireGitHubAdminUser(user) {
  const email = safeText(user && user.email, 320).toLowerCase();
  assertHomeCenterIdentityAllowed(email, 'GitHub Admin');
  if (GITHUB_ADMIN_ALLOWED_EMAIL_SET.has(email)) return email;
  const err = new Error('GitHub Admin is restricted to approved Home Center accounts.');
  err.status = 403;
  err.code = 'github_admin_forbidden_email';
  err.failureKind = 'github_admin_forbidden_email';
  throw err;
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

function internalHomeCenterAuthFromExtra(extra) {
  if (!extra || typeof extra !== 'object' || Array.isArray(extra)) return null;
  const context = extra.homeCenterAuth;
  if (!context) return null;
  if (typeof context !== 'object' || Array.isArray(context)) {
    const err = new Error('Internal Home Center auth context must be an object.');
    err.status = 500;
    throw err;
  }
  const user = safeObject(context.user);
  if (!user.email || !context.auth) {
    const err = new Error('Internal Home Center auth context requires user.email and auth.');
    err.status = 500;
    throw err;
  }
  return {
    ...context,
    user: {
      ...user,
      email: safeText(user.email, 320).toLowerCase(),
      authKind: safeText(user.authKind, 80) || 'internal_delegation',
      actorKind: safeText(user.actorKind, 80),
      actorId: safeText(user.actorId, 120),
      runtimeServiceAccount: safeText(user.runtimeServiceAccount, 320),
      delegatingUser: safeText(user.delegatingUser || user.email, 320).toLowerCase(),
      discordUserId: safeText(user.discordUserId, 80),
      discordInteractionId: safeText(user.discordInteractionId, 80),
    },
  };
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

function mcpRequestMountedPath(req, pathname) {
  const cleanPath = String(pathname || '').startsWith('/') ? String(pathname || '') : `/${pathname || ''}`;
  try {
    const publicBase = new URL(MCP_PUBLIC_BASE);
    const authorizationBase = new URL(MCP_AUTHORIZATION_SERVER_BASE);
    const forwardedHost = safeText(req && req.get && req.get('X-Forwarded-Host'), 300).split(',')[0].trim().split(':')[0].toLowerCase();
    const requestHost = safeText(req && req.get && req.get('Host'), 300).trim().split(':')[0].toLowerCase();
    const base = forwardedHost === publicBase.hostname.toLowerCase() || requestHost === publicBase.hostname.toLowerCase()
      ? publicBase
      : authorizationBase;
    const basePath = base.pathname.replace(/\/$/, '');
    return `${basePath}${cleanPath}`;
  } catch (_) {
    return cleanPath;
  }
}

function renderSecureBrowserOAuthHandoff(req, googleAuthUrl, flowState, mode = 'secure-browser') {
  const safeUrl = htmlEscape(googleAuthUrl);
  const chatgptMobile = mode === 'chatgpt-mobile';
  const title = chatgptMobile ? 'Complete Home Center sign-in' : 'Open Home Center sign-in in a secure browser';
  const body = chatgptMobile
    ? 'Keep this page open. Complete Google sign-in in the browser tab that opens, then return here if ChatGPT does not resume automatically. This page will finish the ChatGPT connector.'
    : 'Google blocked this sign-in surface because it looks like an embedded browser. Open Google sign-in in Chrome or another system browser, then return here. This page will finish the ChatGPT connector automatically.';
  const button = chatgptMobile ? 'Continue with Google' : 'Continue in secure browser';
  const handoffStatusPath = mcpRequestMountedPath(req, '/oauth/handoff-status');
  const handoffCompletePath = mcpRequestMountedPath(req, '/oauth/handoff-complete');
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

function oauthResourceMatches(resource, requiredResource) {
  if (!requiredResource) return true;
  if (resource === requiredResource) return true;
  const homeCenterResources = new Set([MCP_RESOURCE, MCP_LEGACY_RESOURCE]);
  return homeCenterResources.has(resource) && homeCenterResources.has(requiredResource);
}

function isFullHomeCenterGoogleGrant(resource, tokens) {
  if (!oauthResourceMatches(resource, MCP_RESOURCE)) return false;
  const scopes = new Set(safeText(tokens && tokens.scope, 4096).split(/\s+/).filter(Boolean));
  return !!(tokens && tokens.refresh_token) && MCP_REQUIRED_SCOPES.every((scope) => scopes.has(scope));
}

function selectHomeCenterGoogleTokens(embeddedTokens, canonicalData, resource = MCP_RESOURCE) {
  const canonical = safeObject(canonicalData);
  if (canonical.source === 'home_center_mcp_oauth' &&
      isFullHomeCenterGoogleGrant(resource, canonical.tokens)) {
    return safeObject(canonical.tokens);
  }
  return safeObject(embeddedTokens);
}

async function storeHomeCenterGoogleGrant(admin, email, resource, tokens) {
  if (!isFullHomeCenterGoogleGrant(resource, tokens)) return false;
  const fields = {
    tokens,
    email,
    source: 'home_center_mcp_oauth',
    authorizedAtMs: Date.now(),
    updatedAt: admin.firestore.FieldValue.serverTimestamp(),
  };
  await admin.firestore().collection('mcpGoogleGrants').doc(email).set(fields, {merge: true});
  await admin.firestore().collection('googleToolTokens').doc(email).set(fields, {merge: true});
  return true;
}

async function loadMcpAccessContext(admin, google, googleClientId, googleClientSecret, accessToken, requiredResource = MCP_RESOURCE) {
  const snap = await oauthCollection(admin, 'mcpOAuthAccessTokens').doc(tokenHash(accessToken)).get();
  if (!snap.exists) return null;
  const data = snap.data() || {};
  assertHomeCenterIdentityAllowed(data.email, 'Home Center OAuth token');
  if (data.revokedAtMs || safeNumber(data.expiresAtMs, 0) <= Date.now()) {
    const err = new Error(data.revokedAtMs ? 'Home Center OAuth token was revoked. Reconnect the client.' : 'Home Center OAuth token expired. Reconnect the ChatGPT app.');
    err.status = 401;
    err.wwwAuthenticate = oauthChallenge();
    throw err;
  }
  const resource = safeText(data.resource, 1200) || MCP_RESOURCE;
  const scopes = Array.isArray(data.scopes) && data.scopes.length ? data.scopes.map((scope) => safeText(scope, 500)).filter(Boolean) : [...MCP_REQUIRED_SCOPES];
  if (!oauthResourceMatches(resource, requiredResource)) {
    const err = new Error('Home Center OAuth token is bound to a different MCP resource. Reconnect this client.');
    err.status = 401;
    err.wwwAuthenticate = oauthChallenge();
    throw err;
  }
  const email = safeText(data.email, 320).toLowerCase();
  const canonicalRef = admin.firestore().collection('mcpGoogleGrants').doc(email);
  const canonicalSnap = await canonicalRef.get();
  let canonicalData = canonicalSnap.exists ? canonicalSnap.data() : null;
  if (!canonicalData) {
    const legacySnap = await admin.firestore().collection('googleToolTokens').doc(email).get();
    canonicalData = legacySnap.exists ? legacySnap.data() : null;
  }
  let currentTokens = selectHomeCenterGoogleTokens(data.googleTokens, canonicalData, resource);
  const auth = googleOAuthClient(google, providerValue(googleClientId), providerValue(googleClientSecret));
  auth.setCredentials(currentTokens);
  auth.on('tokens', (tokens) => {
    const priorRefreshToken = currentTokens.refresh_token;
    currentTokens = {...currentTokens, ...tokens};
    void (async () => {
      await snap.ref.set({googleTokens: currentTokens, updatedAtMs: Date.now()}, {merge: true});
      if (!isFullHomeCenterGoogleGrant(resource, currentTokens)) return;
      await admin.firestore().runTransaction(async (transaction) => {
        const legacyRef = admin.firestore().collection('googleToolTokens').doc(email);
        const [latest, legacy] = await Promise.all([
          transaction.get(canonicalRef), transaction.get(legacyRef),
        ]);
        const canonical = latest.exists ? latest.data() || {} : {};
        if (canonical.source !== 'home_center_mcp_oauth' ||
            !canonical.tokens || canonical.tokens.refresh_token !== priorRefreshToken) return;
        const update = {tokens: currentTokens, updatedAt: admin.firestore.FieldValue.serverTimestamp()};
        transaction.set(canonicalRef, update, {merge: true});
        const legacyData = legacy.exists ? legacy.data() || {} : {};
        if (legacyData.source === 'home_center_mcp_oauth' &&
            legacyData.tokens && legacyData.tokens.refresh_token === priorRefreshToken) {
          transaction.set(legacyRef, update, {merge: true});
        }
      });
    })().catch((err) => connectorLog('google_token_persist_failed', null, {error: safeText(err.message || String(err), 120)}));
  });
  return {
    user: {
      email: safeText(data.email, 320).toLowerCase(),
      authKind: safeText(data.authKind, 80) || 'home_center_mcp_oauth',
      actorKind: safeText(data.actorKind, 80),
      actorId: safeText(data.actorId, 120),
      runtimeServiceAccount: safeText(data.runtimeServiceAccount, 320),
      delegatingUser: safeText(data.delegatingUser || data.email, 320).toLowerCase(),
      discordUserId: safeText(data.discordUserId, 80),
      discordInteractionId: safeText(data.discordInteractionId, 80),
    },
    auth,
    accessToken,
    oauth: {
      clientId: safeText(data.clientId, 800),
      resource,
      scopes,
      issuer: MCP_AUTHORIZATION_SERVER_BASE,
      expiresAtMs: safeNumber(data.expiresAtMs, 0),
    },
  };
}

async function createDelegatedHomeCenterAuthContext({
  admin,
  google,
  googleClientId,
  googleClientSecret,
  delegatingUser,
  authKind = 'venice_home_center_delegation',
  actorKind = '',
  actorId = '',
  runtimeServiceAccount = '',
  discordUserId = '',
  discordInteractionId = '',
} = {}) {
  const email = safeText(delegatingUser, 320).toLowerCase();
  if (!email) {
    const err = new Error('delegatingUser is required for delegated Home Center auth.');
    err.status = 500;
    throw err;
  }
  assertHomeCenterIdentityAllowed(email, 'delegated Home Center auth');
  const snap = await admin.firestore().collection('googleToolTokens').doc(email).get();
  if (!snap.exists) {
    const err = new Error('Google tools are not connected for the delegated Home Center account.');
    err.status = 409;
    err.code = 'google_tools_not_connected';
    throw err;
  }
  const data = snap.data() || {};
  if (!data.tokens || typeof data.tokens !== 'object') {
    const err = new Error('Delegated Home Center account is missing renewable Google tool tokens.');
    err.status = 409;
    err.code = 'google_tools_not_connected';
    throw err;
  }
  const auth = googleOAuthClient(google, providerValue(googleClientId), providerValue(googleClientSecret));
  let currentTokens = {...safeObject(data.tokens)};
  auth.setCredentials(currentTokens);
  auth.on('tokens', async (tokens) => {
    currentTokens = {...currentTokens, ...safeObject(tokens)};
    await snap.ref.set({
      tokens: currentTokens,
      email,
      source: safeText(data.source, 80) || 'venice_home_center_delegation',
      updatedAt: admin.firestore.FieldValue.serverTimestamp(),
    }, {merge: true});
  });
  return {
    user: {
      email,
      authKind: safeText(authKind, 80) || 'venice_home_center_delegation',
      actorKind: safeText(actorKind, 80),
      actorId: safeText(actorId, 120),
      runtimeServiceAccount: safeText(runtimeServiceAccount, 320),
      delegatingUser: email,
      discordUserId: safeText(discordUserId, 80),
      discordInteractionId: safeText(discordInteractionId, 80),
    },
    auth,
    oauth: {
      resource: MCP_RESOURCE,
      scopes: [...MCP_REQUIRED_SCOPES],
      issuer: MCP_AUTHORIZATION_SERVER_BASE,
      delegated: true,
      tokenSource: 'googleToolTokens',
    },
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
  assertHomeCenterIdentityAllowed(email, 'Google OAuth bearer');
  return {email, authKind: 'google_oauth_bearer'};
}

async function requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret) {
  const internal = internalHomeCenterAuthFromExtra(extra);
  if (internal) {
    assertHomeCenterIdentityAllowed(internal.user && internal.user.email, 'internal Home Center delegation');
    return internal;
  }
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
    purpose: 'Expose retained Command Center project operations, managed knowledge-bucket operations, app-control, and browser operations through the already-installed Home Center MCP connector.',
    operations: {
      health: {summary: 'Check Command Center MCP health and tool exposure.', readOnly: true, input: {}},
      'projects.resolve': {summary: 'Resolve an active project before invoking a retained capability.', readOnly: false, input: {repository: 'optional string', capability: 'optional string', projectId: 'optional string', idempotencyKey: 'string'}},
      'projects.get': {summary: 'Read one persisted Command Center project packet.', readOnly: true, input: {projectId: 'string'}},
      'projects.upsert': {summary: 'Create or update a durable Command Center project binding.', readOnly: false, input: {projectId: 'string', repository: 'optional string', capability: 'optional string', repositoryBinding: 'optional object', idempotencyKey: 'string'}},
      'bucket.get_layout': {summary: 'Read Command Center managed knowledge bucket lanes and storage policy.', readOnly: true, input: {}},
      'bucket.put_object': {summary: 'Write durable execution memory, scratch/promoted skills, or cross-repo notes. Secrets are rejected.', readOnly: false, input: {kind: 'memory.past_log|memory.current_condensed|skill.scratch|skill.promoted|note.cross_repo', title: 'string', summary: 'optional string', body: 'optional string', objectUri: 'optional string', projectId: 'optional string', repository: 'optional string', tags: 'optional string[]', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'bucket.get_object': {summary: 'Read one Command Center bucket object by id.', readOnly: true, input: {objectId: 'string'}},
      'bucket.list_objects': {summary: 'List Command Center bucket objects by kind, project, repository, or tag.', readOnly: true, input: {kind: 'optional string', projectId: 'optional string', repository: 'optional string', tag: 'optional string', limit: 'optional number'}},
      'bucket.promote_skill': {summary: 'Promote a scratch skill bucket object into the promoted skill lane with provenance.', readOnly: false, input: {objectId: 'string', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'app_control.seed_profiles': {summary: 'Publish built-in app-control seed profiles into Home Center cloud Firestore and managed bucket.', readOnly: false, input: {idempotencyKey: 'string'}},
      'app_control.put_profile': {summary: 'Create or update a cloud app-control profile versioned by Android package and app version.', readOnly: false, input: {profile: 'object', idempotencyKey: 'string'}},
      'app_control.get_profile': {summary: 'Read one cloud app-control profile by profileId.', readOnly: true, input: {profileId: 'string'}},
      'app_control.list_profiles': {summary: 'List cloud app-control profiles by package, workflow, or status.', readOnly: true, input: {packageName: 'optional string', workflow: 'optional string', status: 'optional string', limit: 'optional number'}},
      'app_control.record_run': {summary: 'Record redacted app-control execution evidence, timings, frame-lane status, and learned fixes.', readOnly: false, input: {profileId: 'string', workflow: 'string', status: 'optional string', elapsedMs: 'optional number', uiActionCount: 'optional number', frameLane: 'optional object', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'phone_hands.devices': {summary: 'List owner-scoped Android Phone Hands relay devices and last-seen state.', readOnly: true, input: {}},
      'phone_hands.enqueue': {summary: 'Enqueue a bounded Android Phone Hands action for an owner-scoped device.', readOnly: false, input: {idempotencyKey: 'string', deviceId: 'optional string default primary-phone', commandId: 'optional string', action: 'object', ttlMs: 'optional number'}},
      'phone_hands.get': {summary: 'Read status, result, or failure for one owner-scoped Phone Hands command.', readOnly: true, input: {commandId: 'string'}},
      'browser_sessions.create': {summary: 'Create a Playwright desktop Chromium browser-hands session.', readOnly: false, input: {intent: 'string', startUrl: 'optional string', surface: 'optional object', idempotencyKey: 'string'}},
      'browser_sessions.observe': {summary: 'Read browser-hands session state and recent episodes.', readOnly: true, input: {sessionId: 'string', limit: 'optional number'}},
      'browser_sessions.act': {summary: 'Request or record a constrained browser action; sensitive actions are human-blocked.', readOnly: false, input: {sessionId: 'string', action: 'string', target: 'optional object', reason: 'optional string', idempotencyKey: 'string'}},
      'browser_sessions.record_episode': {summary: 'Record a redacted browser-hands invocation and candidate discoveries.', readOnly: false, input: {sessionId: 'string', origin: 'optional string', outcome: 'optional string', actions: 'optional object[]', discoveryCandidates: 'optional object[]', idempotencyKey: 'string'}},
      'browser_discoveries.list': {summary: 'List browser discoveries by origin, task, or state.', readOnly: true, input: {origin: 'optional string', task: 'optional string', state: 'optional string', limit: 'optional number'}},
      'browser_discoveries.promote': {summary: 'Promote a validated browser discovery into trusted household playbook guidance.', readOnly: false, input: {discoveryId: 'string', guidance: 'optional string', playbook: 'optional object', evidenceRefs: 'optional string[]', idempotencyKey: 'string'}},
      'browser_playbooks.lookup': {summary: 'Lookup a trusted Playwright DOM/accessibility browser playbook by origin, taskKey, shareScope, or replayAudience.', readOnly: true, input: {origin: 'optional string', taskKey: 'optional string', task: 'optional string', shareScope: 'optional string', replayAudience: 'optional string', limit: 'optional number'}},
    },
  };
}

function supportedCommandCenterOperationTypes() {
  return Object.keys(commandCenterOperationRegistry().operations);
}

function commandCenterToolName(operation) {
  const raw = safeText(operation, 120);
  const op = raw.startsWith('command_center.') ? raw.slice('command_center.'.length) : raw;
  if (['agents.', 'workers.', 'hosts.', 'jobs.', 'machine_images.', 'provisioning.', 'codex_sessions.', 'routing.', 'proof.'].some((prefix) => op.startsWith(prefix))) {
    const error = new Error('Command Center Codex agents, jobs, sessions, and workers are permanently retired and are not a Home Center capability.');
    error.status = 410;
    error.code = 'capability_retired.command_center_codex';
    throw error;
  }
  if (new Set(['render.blender_glb', 'render.blender_build', 'render.status', 'render.reconcile']).has(op)) {
    const error = new Error('This legacy rendering capability is retired. Use drive_operation with blender.workspace.create, blender.workspace.mutate, blender.workspace.inspect, or blender.workspace.export. blender.workspace.render is deprecated and retained only for compatibility.');
    error.status = 410;
    error.code = 'capability_retired.use_blender_workspace';
    throw error;
  }
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

async function requireTopLevelDriveIngestUpload(args = {}) {
  try {
    return await materializeOpenAiHostFileToTemp(args.file, {maxBytes: HOME_CENTER_DRIVE_INGEST_MAX_BYTES});
  } catch (error) {
    if (error && error.code === 'host_file_required') error.code = 'drive_ingest_file_required';
    throw error;
  }
}

function cleanDriveIngestFileName(value) {
  const base = safeText(value, 240)
    .replace(/\\/g, '/')
    .split('/')
    .pop()
    .replace(/[\u0000-\u001f\u007f]/g, '')
    .trim();
  return base || 'upload.bin';
}

function driveIngestMimeType(value) {
  const mimeType = safeText(value, 160).toLowerCase();
  return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(mimeType) ? mimeType : 'application/octet-stream';
}

function driveIngestConflict(message) {
  const err = new Error(message);
  err.status = 409;
  err.code = 'drive_ingest_idempotency_conflict';
  return err;
}

function assertDriveIngestIdentity(result = {}, identity = {}) {
  if (safeText(result.sha256, 128).toLowerCase() !== identity.sha256) {
    throw driveIngestConflict('requestId was reused with different file bytes.');
  }
  if (safeText(result.name, 240) !== identity.name) {
    throw driveIngestConflict('requestId was reused with a different Drive filename.');
  }
  if (safeText(result.mimeType, 160).toLowerCase() !== identity.mimeType) {
    throw driveIngestConflict('requestId was reused with a different MIME type.');
  }
  if (identity.parentFolderId && safeText(result.parentFolderId, 220) !== identity.parentFolderId) {
    throw driveIngestConflict('requestId was reused with a different destination folder.');
  }
}

async function driveIngestFileOperationWithUpload({google, admin, auth, user, args = {}, uploaded}) {
  const requestId = stableRequestId(args.requestId);
  const declaredSize = Number(uploaded.size || 0);
  if (!Number.isSafeInteger(declaredSize) || declaredSize < 1) {
    const err = new Error('file is empty.');
    err.status = 400;
    err.code = 'drive_ingest_file_empty';
    throw err;
  }
  if (declaredSize > HOME_CENTER_DRIVE_INGEST_MAX_BYTES) {
    const err = new Error('file exceeds the Home Center Drive ingest ceiling of ' + HOME_CENTER_DRIVE_INGEST_MAX_BYTES + ' bytes.');
    err.status = 413;
    err.code = 'drive_ingest_file_too_large';
    throw err;
  }

  const name = cleanDriveIngestFileName(args.name || args.fileName || uploaded.name);
  const mimeType = driveIngestMimeType(args.mimeType || uploaded.type);
  const parentFolderId = safeText(args.parentFolderId, 220) ? safeDriveFileId(args.parentFolderId) : '';
  const sha256 = safeText(uploaded.sha256, 64).toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(sha256) || typeof uploaded.createReadStream !== 'function') {
    const err = new Error('Streamed host-file materialization did not produce a valid SHA-256 receipt.');
    err.status = 502;
    err.code = 'drive_ingest_materialization_invalid';
    throw err;
  }
  const expectedSha256 = safeText(args.expectedSha256, 128).toLowerCase();
  if (expectedSha256 && !/^[a-f0-9]{64}$/.test(expectedSha256)) {
    const err = new Error('expectedSha256 must be a lowercase or uppercase 64-character hexadecimal SHA-256 digest.');
    err.status = 400;
    err.code = 'drive_ingest_expected_sha256_invalid';
    throw err;
  }
  if (expectedSha256 && expectedSha256 !== sha256) {
    const err = new Error('Uploaded file SHA-256 did not match expectedSha256.');
    err.status = 400;
    err.code = 'drive_ingest_expected_sha256_mismatch';
    throw err;
  }

  const identity = {name, mimeType, parentFolderId, sha256};
  const existing = await existingAudit(admin, requestId);
  if (existing && ['success', 'completed'].includes(safeText(existing.status, 80)) && existing.result) {
    assertDriveIngestIdentity(existing.result, identity);
    return {...existing.result, idempotent: true, audit: existing};
  }

  const drive = google.drive({version: 'v3', auth});
  const markerQuery = "trashed=false and appProperties has { key='homeCenterRequestId' and value='" + driveQueryLiteral(requestId, 160) + "' }";
  const marked = await drive.files.list({
    q: markerQuery,
    pageSize: 3,
    fields: 'files(' + driveFields('appProperties') + ')',
    supportsAllDrives: true,
    includeItemsFromAllDrives: true,
  });
  const matches = marked.data && marked.data.files || [];
  if (matches.length > 1) throw driveIngestConflict('Multiple Drive files carry this Home Center requestId; mutation is quarantined.');
  let rawMetadata = matches[0] || null;
  if (rawMetadata) {
    const markerSha256 = safeText(rawMetadata.appProperties && rawMetadata.appProperties.homeCenterSha256, 128).toLowerCase();
    if (markerSha256 && markerSha256 !== sha256) throw driveIngestConflict('requestId was reused with different file bytes.');
    const markerParent = (rawMetadata.parents || [])[0] || '';
    if (safeText(rawMetadata.name, 240) !== name || safeText(rawMetadata.mimeType, 160).toLowerCase() !== mimeType || (parentFolderId && markerParent !== parentFolderId)) {
      throw driveIngestConflict('requestId was reused with different Drive metadata.');
    }
  } else {
    const created = await drive.files.create({
      requestBody: {
        name,
        mimeType,
        ...(parentFolderId ? {parents: [parentFolderId]} : {}),
        appProperties: {
          homeCenterRequestId: requestId,
          homeCenterSha256: sha256,
          homeCenterOperation: 'drive.ingestFile',
        },
      },
      media: {mimeType, body: uploaded.createReadStream()},
      fields: driveFields('appProperties'),
      supportsAllDrives: true,
    });
    rawMetadata = created.data || {};
  }

  const metadata = cleanDriveFile(rawMetadata);
  const fileId = safeDriveFileId(metadata.id);
  const readback = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'stream'});
  if (!readback.data || typeof readback.data.on !== 'function') {
    const err = new Error('Drive did not return a readable stream for ingest verification.');
    err.status = 502;
    err.code = 'drive_ingest_readback_unavailable';
    throw err;
  }
  const readbackDigest = await hashReadableStream(readback.data);
  const readbackSha256 = readbackDigest.sha256;
  const verified = readbackDigest.byteCount === declaredSize && readbackSha256 === sha256;
  if (!verified) {
    const err = new Error('Drive readback verification failed after ingest.');
    err.status = 502;
    err.code = 'drive_ingest_readback_mismatch';
    throw err;
  }

  const result = {
    operation: 'drive.ingestFile',
    fileId,
    id: fileId,
    name: metadata.name || name,
    mimeType: metadata.mimeType || mimeType,
    webViewLink: metadata.webViewLink || '',
    durableRef: 'drive://' + fileId,
    parentFolderId: (metadata.parents || [])[0] || parentFolderId,
    byteCount: declaredSize,
    sha256,
    readbackByteCount: readbackDigest.byteCount,
    readbackSha256,
    verified: true,
    auditRequestId: requestId,
  };
  assertDriveIngestIdentity(result, identity);
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'drive_ingest_file',
    operation: 'drive.ingestFile',
    requestId,
    fileId,
    affectedFileIds: [fileId],
    oldMetadata: null,
    newMetadata: metadata,
    oldParents: [],
    newParents: metadata.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || ('Ingested and verified Drive file ' + result.name + ' (' + result.byteCount + ' bytes).'),
    result,
    inputSha256: sha256,
  });
  await recordActionAudit(admin, user, 'drive.ingestFile', fileId, safeText(args.callerNote, 400) || ('Ingested and verified Drive file ' + result.name + ' (' + result.byteCount + ' bytes).'), requestId).catch(() => {});
  return {...result, audit: audit.audit};
}

async function driveIngestFileOperation(context) {
  const uploaded = await requireTopLevelDriveIngestUpload(context.args || {});
  try {
    return await driveIngestFileOperationWithUpload({...context, uploaded});
  } finally {
    await uploaded.cleanup();
  }
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

  // Phone Hands is a Home Center-owned Firestore relay. Keep the legacy operation
  // names for clients, but never route these calls through Command Center MCP.
  const phoneOperation = operation.startsWith('command_center.') ? operation.slice('command_center.'.length) : operation;
  if (['phone_hands.devices', 'phone_hands.enqueue', 'phone_hands.get'].includes(phoneOperation)) {
    const email = safeText(context.user && context.user.email, 320).toLowerCase();
    assertHomeCenterIdentityAllowed(email, 'Phone Hands');
    const caller = {actor: email, ownerKey: 'owner_' + createHash('sha256').update(email).digest('hex').slice(0, 32)};
    const result = phoneOperation === 'phone_hands.devices'
      ? await listPhoneDevices(admin, caller)
      : phoneOperation === 'phone_hands.enqueue'
        ? await enqueuePhoneCommand(admin, caller, operationArgs)
        : await getPhoneCommand(admin, caller, operationArgs);
    return {operation, toolName, commandCenterMcpUrl: null, result};
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

function openAiFileCatalogDefinition() {
  return openAiFileParamJsonSchema('ChatGPT host file supplied through openai/fileParams.');
}

function hostFileUploadInputSchema() {
  return {$ref: '#/$defs/OpenAIFile'};
}

function storageIngestArtifactCatalogInputSchema() {
  return {
    type: 'object',
    $defs: {OpenAIFile: openAiFileCatalogDefinition()},
    properties: {
      requestId: {type: 'string', description: 'Stable idempotency and audit request id.'},
      file: hostFileUploadInputSchema({
        contentMediaType: 'application/octet-stream',
        description: 'Required top-level host-file upload for canonical Cloud Storage artifact ingress.',
      }),
      artifactId: {type: 'string', description: 'Stable artifact identity.'},
      artifactKind: {type: 'string', description: 'Artifact class such as source-motion.'},
      project: {type: 'string', description: 'Owning project or factory lane.'},
      name: {type: 'string', description: 'Optional canonical filename override.'},
      mimeType: {type: 'string', description: 'Optional MIME type override.'},
      expectedByteCount: {type: 'integer', description: 'Optional expected byte count.'},
      expectedSha256: {type: 'string', description: 'Required caller-side SHA-256 provenance lock.'},
      provenance: {type: 'object', description: 'Bounded source identity and curation provenance.'},
      callerNote: {type: 'string', description: 'Optional audit summary.'},
    },
    required: ['requestId', 'file', 'artifactId', 'artifactKind', 'project', 'expectedSha256'],
    additionalProperties: false,
  };
}

function driveIngestFileCatalogInputSchema() {
  return {
    type: 'object',
    $defs: {OpenAIFile: openAiFileCatalogDefinition()},
    properties: {
      requestId: {type: 'string', description: 'Stable idempotency and audit request id.'},
      file: hostFileUploadInputSchema({
        contentMediaType: 'application/octet-stream',
        description: 'Required top-level host-file upload. Do not pass a path, URL, Base64 string, ref, or nested JSON descriptor.',
      }),
      name: {type: 'string', description: 'Optional Drive filename override.'},
      mimeType: {type: 'string', description: 'Optional MIME type override.'},
      parentFolderId: {type: 'string', description: 'Optional destination Drive folder id.'},
      expectedSha256: {type: 'string', description: 'Optional expected hexadecimal SHA-256 digest for caller-side provenance locking.'},
      callerNote: {type: 'string', description: 'Optional human-readable audit summary.'},
    },
    required: ['requestId', 'file'],
    additionalProperties: false,
  };
}

function publishedToolInputSchema(name, schema, pipeStrategy = 'input') {
  if (name === 'drive_ingest_file') return driveIngestFileCatalogInputSchema();
  if (name === 'storage_ingest_artifact') return storageIngestArtifactCatalogInputSchema();
  return mcpToolJsonSchema(schema, pipeStrategy);
}

function registeredHomeCenterTools(server) {
  return Object.entries(server._registeredTools)
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
    });
}

async function callRegisteredHomeCenterTool(server, name, args = {}, extra = {}) {
  const cleanName = safeText(name, 160);
  const tool = cleanName ? server._registeredTools[cleanName] : null;
  if (!tool) throw Object.assign(new Error('Unknown Home Center MCP tool.'), {status: 404, code: 'home_center_mcp_tool_not_found'});
  if (!tool.enabled) throw Object.assign(new Error('Home Center MCP tool is disabled.'), {status: 403, code: 'home_center_mcp_tool_disabled'});
  if (!args || typeof args !== 'object' || Array.isArray(args)) {
    throw Object.assign(new Error('Tool arguments must be a JSON object.'), {status: 400, code: 'home_center_mcp_invalid_arguments'});
  }
  return tool.handler(args, extra);
}

function installAuthenticatedToolsListHandler(server) {
  server.server.setRequestHandler(ListToolsRequestSchema, () => ({
    tools: registeredHomeCenterTools(server),
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
    authorization_servers: [MCP_AUTHORIZATION_SERVER_BASE],
    scopes_supported: MCP_REQUIRED_SCOPES,
    bearer_methods_supported: ['header'],
    resource_documentation: `${MCP_PUBLIC_BASE}/`,
    metadata_aliases: [MCP_PATH_RESOURCE_METADATA, MCP_LEGACY_RESOURCE_METADATA, MCP_LEGACY_RESOURCE_METADATA_ALIAS, MCP_COMPAT_RESOURCE_METADATA],
  };
}

function oauthChallenge() {
  return `Bearer resource_metadata="${MCP_RESOURCE_METADATA}", scope="${MCP_REQUIRED_SCOPES.join(' ')}"`;
}

function authorizationServerMetadata() {
  return {
    issuer: MCP_AUTHORIZATION_SERVER_BASE,
    service_version: HOME_CENTER_MCP_SERVER_VERSION,
    registry_version: HOME_CENTER_REGISTRY_VERSION,
    connector_schema_revision: HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
    authorization_endpoint: `${MCP_AUTHORIZATION_SERVER_BASE}/oauth/authorize`,
    token_endpoint: `${MCP_AUTHORIZATION_SERVER_BASE}/oauth/token`,
    registration_endpoint: `${MCP_AUTHORIZATION_SERVER_BASE}/oauth/register`,
    response_types_supported: ['code'],
    grant_types_supported: ['authorization_code', 'refresh_token'],
    code_challenge_methods_supported: ['S256'],
    token_endpoint_auth_methods_supported: ['none'],
    scopes_supported: [...new Set([...MCP_REQUIRED_SCOPES, GROUNDED_MOTION_MCP_SCOPE, OAUTH_OFFLINE_ACCESS_SCOPE])],
  };
}

function openIdConfigurationMetadata() {
  return {
    ...authorizationServerMetadata(),
    userinfo_endpoint: `${MCP_AUTHORIZATION_SERVER_BASE}/oauth/userinfo`,
    jwks_uri: `${MCP_AUTHORIZATION_SERVER_BASE}/oauth/jwks`,
    claims_supported: ['sub', 'email', 'email_verified', 'client_id', 'resource', 'scopes', 'issuer', 'expires_at'],
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
  if (existing.exists && ['success', 'completed'].includes(existing.data().status)) {
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
    affectedStorageRefs: Array.isArray(entry.affectedStorageRefs) ? entry.affectedStorageRefs.map((v) => safeText(v, 1200)).filter(Boolean) : [],
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
    audioRenderJob: entry.audioRenderJob || null,
    sfxForgeJob: entry.sfxForgeJob || null,
    progress: entry.progress || null,
    lease: entry.lease || null,
    submittedAtMs: Math.floor(safeNumber(entry.submittedAtMs, 0)) || null,
    updatedAtMs: Math.floor(safeNumber(entry.updatedAtMs, nowMs())) || nowMs(),
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

function safeSitesSourceRepositoryUrl(value) {
  let parsed;
  try {
    parsed = new URL(safeText(value, 2000));
  } catch (_) {
    throw Object.assign(new Error('repositoryUrl must be a valid HTTPS Sites source repository URL.'), {status: 400});
  }
  if (parsed.protocol !== 'https:' || parsed.hostname !== 'git.chatgpt-team.site' || !parsed.pathname.endsWith('.git') || parsed.username || parsed.password) {
    throw Object.assign(new Error('repositoryUrl must be an uncredentialed git.chatgpt-team.site HTTPS URL ending in .git.'), {status: 400});
  }
  return parsed.toString();
}

function safeSitesSourceCommit(value) {
  const commit = safeText(value, 80).toLowerCase();
  if (!/^[a-f0-9]{40}$/.test(commit)) throw Object.assign(new Error('sourceCommit must be an exact 40-character Git commit SHA.'), {status: 400});
  return commit;
}

function safeSitesSourceBranch(value) {
  const branch = safeText(value || 'main', 240);
  if (!branch || branch.startsWith('-') || branch.includes('..') || /[~^:?*[\\\s]/.test(branch)) {
    throw Object.assign(new Error('sourceBranch is not a safe Git branch name.'), {status: 400});
  }
  return branch;
}

function safeSitesSourcePath(value) {
  const sourcePath = String(value || '').replace(/\\\\/g, '/');
  if (!sourcePath || sourcePath.startsWith('/') || sourcePath.split('/').some((part) => !part || part === '.' || part === '..') || /[\u0000-\u001f\u007f]/.test(sourcePath)) {
    throw Object.assign(new Error('Sites source repository returned an unsafe path.'), {status: 502});
  }
  return sourcePath;
}

function sourcePathMarker(sourcePath) {
  return createHash('sha256').update(String(sourcePath), 'utf8').digest('hex');
}

function sourceMimeType(sourcePath) {
  const extension = path.extname(sourcePath).toLowerCase();
  const known = {
    '.css': 'text/css', '.csv': 'text/csv', '.gif': 'image/gif', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json',
    '.htm': 'text/html', '.html': 'text/html', '.ico': 'image/x-icon', '.jpeg': 'image/jpeg', '.jpg': 'image/jpeg',
    '.js': 'text/javascript', '.json': 'application/json', '.md': 'text/markdown', '.mjs': 'text/javascript', '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg', '.png': 'image/png', '.svg': 'image/svg+xml', '.toml': 'application/toml', '.ts': 'text/typescript',
    '.tsx': 'text/tsx', '.txt': 'text/plain', '.wasm': 'application/wasm', '.wav': 'audio/wav', '.webm': 'video/webm',
    '.webp': 'image/webp', '.xml': 'application/xml', '.yaml': 'application/yaml', '.yml': 'application/yaml', '.zip': 'application/zip',
  };
  return known[extension] || 'application/octet-stream';
}

async function findMaterializedDriveNode(drive, requestId, sourcePath) {
  const request = driveQueryLiteral(requestId, 160);
  const marker = driveQueryLiteral(sourcePathMarker(sourcePath), 128);
  const result = await drive.files.list({
    q: `trashed=false and appProperties has { key='homeCenterRequestId' and value='${request}' } and appProperties has { key='homeCenterSourcePathSha256' and value='${marker}' }`,
    pageSize: 2,
    fields: `files(${driveFields('appProperties')})`,
    supportsAllDrives: true,
    includeItemsFromAllDrives: true,
  });
  const files = result.data && result.data.files || [];
  if (files.length > 1) throw Object.assign(new Error('Materialization marker resolved to multiple Drive nodes.'), {status: 409});
  return files[0] || null;
}

function sourceNodeProperties(requestId, sourcePath, sourceCommit, nodeKind) {
  return {
    homeCenterOperation: 'sites.source_version.materialize_drive',
    homeCenterRequestId: requestId,
    homeCenterSourcePathSha256: sourcePathMarker(sourcePath),
    homeCenterSourceCommit: sourceCommit,
    homeCenterSourceNodeKind: nodeKind,
  };
}

async function ensureMaterializedDriveFolder({drive, requestId, sourcePath, name, parentFolderId, sourceCommit}) {
  const existing = await findMaterializedDriveNode(drive, requestId, sourcePath);
  if (existing) {
    if (existing.mimeType !== 'application/vnd.google-apps.folder' || existing.name !== name || !(existing.parents || []).includes(parentFolderId)) {
      throw Object.assign(new Error('Existing materialization folder marker conflicts with the requested source tree.'), {status: 409});
    }
    return cleanDriveFile(existing, sourcePath);
  }
  const created = await drive.files.create({
    requestBody: {
      name,
      mimeType: 'application/vnd.google-apps.folder',
      parents: [parentFolderId],
      appProperties: sourceNodeProperties(requestId, sourcePath, sourceCommit, 'folder'),
    },
    fields: driveFields('appProperties'),
    supportsAllDrives: true,
  });
  return cleanDriveFile(created.data || {}, sourcePath);
}

async function ensureMaterializedDriveFile({drive, requestId, sourcePath, name, parentFolderId, sourceCommit, bytes, mimeType, nodeKind = 'file'}) {
  const expectedSha256 = sha256Hex(bytes);
  let metadata = await findMaterializedDriveNode(drive, requestId, sourcePath);
  if (metadata) {
    if (metadata.mimeType !== mimeType || metadata.name !== name || !(metadata.parents || []).includes(parentFolderId)) {
      throw Object.assign(new Error('Existing materialization file marker conflicts with the requested source tree.'), {status: 409});
    }
  } else {
    metadata = (await drive.files.create({
      requestBody: {
        name,
        mimeType,
        parents: [parentFolderId],
        appProperties: sourceNodeProperties(requestId, sourcePath, sourceCommit, nodeKind),
      },
      media: {mimeType, body: Readable.from([bytes])},
      fields: driveFields('appProperties'),
      supportsAllDrives: true,
    })).data || {};
  }
  const fileId = safeDriveFileId(metadata.id);
  const readback = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
  const readbackBytes = mediaBuffer(readback.data);
  const readbackSha256 = sha256Hex(readbackBytes);
  if (readbackBytes.length !== bytes.length || readbackSha256 !== expectedSha256) {
    throw Object.assign(new Error('Drive source-file readback verification failed for ' + sourcePath + '.'), {status: 502});
  }
  const clean = cleanDriveFile(metadata, sourcePath);
  return {...clean, byteCount: bytes.length, sha256: expectedSha256, readbackByteCount: readbackBytes.length, readbackSha256, verified: true};
}

async function materializeSitesSourceVersionOperation({google, admin, auth, user, args = {}}) {
  if (args.approved !== true) throw Object.assign(new Error('sites.source_version.materialize_drive requires approved=true.'), {status: 409});
  const requestId = createRequestId(args.requestId);
  const existingAuditRecord = await existingAudit(admin, requestId);
  if (existingAuditRecord && existingAuditRecord.status === 'success' && existingAuditRecord.result) return {...existingAuditRecord.result, idempotent: true, audit: existingAuditRecord};
  const repositoryUrl = safeSitesSourceRepositoryUrl(args.repositoryUrl);
  const repositoryToken = typeof args.repositoryToken === 'string' ? args.repositoryToken.trim() : '';
  if (repositoryToken.length < 20 || repositoryToken.length > 8192) throw Object.assign(new Error('A valid short-lived Sites repositoryToken is required.'), {status: 400});
  const sourceCommit = safeSitesSourceCommit(args.sourceCommit);
  const sourceBranch = safeSitesSourceBranch(args.sourceBranch || 'main');
  const parentFolderId = safeDriveFileId(args.parentFolderId);
  const folderName = safeText(args.folderName || 'Sites Source ' + sourceCommit.slice(0, 12), 240);
  if (!folderName) throw Object.assign(new Error('folderName is required.'), {status: 400});
  const expectedSourceFileCount = args.expectedSourceFileCount === undefined ? null : Math.floor(safeNumber(args.expectedSourceFileCount, -1));
  const projectId = safeText(args.projectId, 240);
  const versionId = safeText(args.versionId, 320);
  const versionNumber = Math.floor(safeNumber(args.versionNumber, 0));
  const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'home-center-sites-source-'));
  const drive = google.drive({version: 'v3', auth});
  try {
    try {
      await isoGit.clone({
        fs,
        http: isoGitHttp,
        dir: tempDir,
        url: repositoryUrl,
        ref: sourceBranch,
        singleBranch: true,
        depth: 1,
        headers: {Authorization: 'Bearer ' + repositoryToken},
        onAuth: () => ({username: 'oauth2', password: repositoryToken}),
      });
    } catch (_) {
      throw Object.assign(new Error('Sites source repository clone failed. Obtain a fresh short-lived credential and retry with the same requestId.'), {status: 502, code: 'sites_source_clone_failed'});
    }
    const resolvedCommit = safeSitesSourceCommit(await isoGit.resolveRef({fs, dir: tempDir, ref: 'HEAD'}));
    if (resolvedCommit !== sourceCommit) throw Object.assign(new Error('Sites repository HEAD does not match sourceCommit.'), {status: 409});
    const trackedPaths = (await isoGit.listFiles({fs, dir: tempDir})).map(safeSitesSourcePath).sort();
    if (!trackedPaths.length || trackedPaths.length > HOME_CENTER_SITES_SOURCE_MAX_FILES) throw Object.assign(new Error('Sites source file count is empty or exceeds the configured materialization limit.'), {status: 413});
    if (expectedSourceFileCount !== null && expectedSourceFileCount !== trackedPaths.length) throw Object.assign(new Error('Sites source file count does not match expectedSourceFileCount.'), {status: 409});

    const sourceFiles = [];
    let totalSourceBytes = 0;
    for (const sourcePath of trackedPaths) {
      const absolutePath = path.join(tempDir, ...sourcePath.split('/'));
      const bytes = await fs.promises.readFile(absolutePath);
      const stat = await fs.promises.lstat(absolutePath);
      totalSourceBytes += bytes.length;
      if (totalSourceBytes > HOME_CENTER_SITES_SOURCE_MAX_BYTES) throw Object.assign(new Error('Sites source bytes exceed the configured materialization limit.'), {status: 413});
      sourceFiles.push({path: sourcePath, name: path.posix.basename(sourcePath), bytes, byteCount: bytes.length, sha256: sha256Hex(bytes), mode: stat.mode & 0o777, mimeType: sourceMimeType(sourcePath)});
    }

    const parent = await getDriveMetadata(drive, parentFolderId);
    if (parent.mimeType !== 'application/vnd.google-apps.folder') throw Object.assign(new Error('parentFolderId must identify a Google Drive folder.'), {status: 400});
    const root = await ensureMaterializedDriveFolder({drive, requestId, sourcePath: '.', name: folderName, parentFolderId, sourceCommit});
    const folderIds = {'': root.id};
    const folderReceipts = [];
    const directoryPaths = [...new Set(sourceFiles.flatMap((sourceFile) => {
      const parts = sourceFile.path.split('/').slice(0, -1);
      return parts.map((_, index) => parts.slice(0, index + 1).join('/'));
    }))].sort((a, b) => {
      const depth = a.split('/').length - b.split('/').length;
      return depth || a.localeCompare(b);
    });
    for (const directoryPath of directoryPaths) {
      const parts = directoryPath.split('/');
      const parentPath = parts.slice(0, -1).join('/');
      const directoryName = parts[parts.length - 1];
      const folder = await ensureMaterializedDriveFolder({drive, requestId, sourcePath: directoryPath, name: directoryName, parentFolderId: folderIds[parentPath], sourceCommit});
      folderIds[directoryPath] = folder.id;
      folderReceipts.push({path: directoryPath, folderId: folder.id, verified: true});
    }
    const fileReceipts = [];
    const verificationConcurrency = Math.max(1, Math.min(8, Math.floor(safeNumber(args.verificationConcurrency, 8))));
    for (let offset = 0; offset < sourceFiles.length; offset += verificationConcurrency) {
      const batch = sourceFiles.slice(offset, offset + verificationConcurrency);
      const batchReceipts = await Promise.all(batch.map(async (sourceFile) => {
        const parentPath = sourceFile.path.split('/').slice(0, -1).join('/');
        const uploaded = await ensureMaterializedDriveFile({drive, requestId, sourcePath: sourceFile.path, name: sourceFile.name, parentFolderId: folderIds[parentPath], sourceCommit, bytes: sourceFile.bytes, mimeType: sourceFile.mimeType});
        return {path: sourceFile.path, fileId: uploaded.id, byteCount: uploaded.byteCount, sha256: uploaded.sha256, readbackByteCount: uploaded.readbackByteCount, readbackSha256: uploaded.readbackSha256, verified: true, mode: sourceFile.mode};
      }));
      fileReceipts.push(...batchReceipts);
    }

    const aggregateSha256 = sha256Hex(Buffer.from(sourceFiles.map((file) => `${file.mode.toString(8)} ${file.sha256} ${file.path}\n`).join(''), 'utf8'));
    const manifestPayload = {
      schemaVersion: 'home-center.sites-source-drive.v1',
      createdAt: new Date().toISOString(),
      ownerEmail: safeText(user && user.email, 320).toLowerCase(),
      source: {projectId, versionId, versionNumber, repositoryUrl, sourceBranch, sourceCommit, sourceFileCount: sourceFiles.length, sourceByteCount: totalSourceBytes, aggregateSha256},
      savedArchiveProvenance: {
        archiveFormat: safeText(args.archiveFormat, 40),
        sedimentFileId: safeText(args.sedimentFileId, 240),
        contentHash: safeText(args.archiveContentHash, 160),
        fileCount: Math.floor(safeNumber(args.archiveFileCount, 0)) || null,
        sizeBytes: Math.floor(safeNumber(args.archiveSizeBytes, 0)) || null,
        note: 'Provider-reported saved deployment archive provenance; source tree verification is recorded separately.',
      },
      drive: {rootFolderId: root.id, rootFolderName: root.name, parentFolderId, sourceFileCount: fileReceipts.length, createdSubfolderCount: folderReceipts.length, everyFileReadbackVerified: fileReceipts.every((file) => file.verified && file.sha256 === file.readbackSha256 && file.byteCount === file.readbackByteCount)},
      files: fileReceipts.map((file) => ({path: file.path, fileId: file.fileId, byteCount: file.byteCount, sha256: file.sha256, mode: file.mode})),
    };
    const manifestBytes = Buffer.from(JSON.stringify(manifestPayload, null, 2) + '\n', 'utf8');
    const manifest = await ensureMaterializedDriveFile({drive, requestId, sourcePath: '__home_center_source_manifest__', name: 'SOURCE_PROVENANCE.json', parentFolderId: root.id, sourceCommit, bytes: manifestBytes, mimeType: 'application/json', nodeKind: 'manifest'});
    const result = {
      operation: 'sites.source_version.materialize_drive',
      projectId,
      versionId,
      versionNumber,
      sourceCommit,
      sourceBranch,
      sourceFileCount: sourceFiles.length,
      sourceByteCount: totalSourceBytes,
      aggregateSha256,
      savedArchiveFileCount: manifestPayload.savedArchiveProvenance.fileCount,
      savedArchiveSizeBytes: manifestPayload.savedArchiveProvenance.sizeBytes,
      rootFolderId: root.id,
      rootFolderName: root.name,
      webViewLink: root.webViewLink,
      parentFolderId,
      createdSubfolderCount: folderReceipts.length,
      verifiedSourceFileCount: fileReceipts.length,
      manifestFileId: manifest.id,
      manifestSha256: manifest.sha256,
      everyFileReadbackVerified: manifestPayload.drive.everyFileReadbackVerified,
      credentialPersisted: false,
      credentialReturned: false,
      auditRequestId: requestId,
    };
    const audit = await auditWrite(admin, {
      actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'drive_operation', operation: 'sites.source_version.materialize_drive', requestId,
      fileId: root.id, affectedFileIds: [root.id, manifest.id, ...fileReceipts.map((file) => file.fileId)], oldMetadata: null, newMetadata: root,
      oldParents: [], newParents: root.parents || [], reversible: false, rollback: null, callerNote: args.callerNote,
      providerSummary: `Materialized Sites source version ${versionNumber || versionId || sourceCommit} into Drive folder ${root.name}; ${fileReceipts.length} source files passed byte/SHA-256 readback.`, result,
    });
    return {...result, audit: audit.audit};
  } finally {
    await fs.promises.rm(tempDir, {recursive: true, force: true}).catch(() => {});
  }
}

function normalizedDriveShareRole(value) {
  const role = safeText(value || 'reader', 40).toLowerCase();
  if (!['reader', 'commenter', 'writer'].includes(role)) throw Object.assign(new Error('role must be reader, commenter, or writer.'), {status: 400});
  return role;
}

function safeShareEmail(value) {
  const email = safeText(value, 320).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw Object.assign(new Error('email must be a valid recipient email address.'), {status: 400});
  return email;
}

function shareRoleSatisfies(actual, requested) {
  const rank = {reader: 1, commenter: 2, writer: 3, owner: 4};
  return (rank[actual] || 0) >= (rank[requested] || 0);
}

async function shareDriveFolderOperation({google, admin, auth, user, args = {}}) {
  if (args.approved !== true) throw Object.assign(new Error('drive.share_folder requires approved=true.'), {status: 409});
  const requestId = createRequestId(args.requestId);
  const existingAuditRecord = await existingAudit(admin, requestId);
  if (existingAuditRecord && existingAuditRecord.status === 'success' && existingAuditRecord.result) return {...existingAuditRecord.result, idempotent: true, audit: existingAuditRecord};
  const folderId = safeDriveFileId(args.folderId);
  const email = safeShareEmail(args.email);
  const role = normalizedDriveShareRole(args.role);
  const drive = google.drive({version: 'v3', auth});
  const folder = await getDriveMetadata(drive, folderId);
  if (folder.mimeType !== 'application/vnd.google-apps.folder') throw Object.assign(new Error('folderId must identify a Google Drive folder.'), {status: 400});
  const permissionFields = 'permissions(id,type,role,emailAddress,displayName,pendingOwner)';
  const beforeList = (await drive.permissions.list({fileId: folderId, fields: permissionFields, supportsAllDrives: true})).data.permissions || [];
  let permission = beforeList.find((item) => safeText(item.emailAddress, 320).toLowerCase() === email) || null;
  let reused = false;
  let upgraded = false;
  if (permission && shareRoleSatisfies(permission.role, role)) {
    reused = true;
  } else if (permission) {
    permission = (await drive.permissions.update({fileId: folderId, permissionId: permission.id, requestBody: {role}, fields: 'id,type,role,emailAddress,displayName,pendingOwner', supportsAllDrives: true})).data || permission;
    upgraded = true;
  } else {
    permission = (await drive.permissions.create({
      fileId: folderId,
      requestBody: {type: 'user', role, emailAddress: email},
      sendNotificationEmail: args.sendNotificationEmail !== false,
      emailMessage: safeText(args.emailMessage, 1000) || undefined,
      fields: 'id,type,role,emailAddress,displayName,pendingOwner',
      supportsAllDrives: true,
    })).data || {};
  }
  const afterList = (await drive.permissions.list({fileId: folderId, fields: permissionFields, supportsAllDrives: true})).data.permissions || [];
  const verifiedPermission = afterList.find((item) => safeText(item.emailAddress, 320).toLowerCase() === email && shareRoleSatisfies(item.role, role));
  if (!verifiedPermission) throw Object.assign(new Error('Drive permission readback did not confirm the requested recipient and role.'), {status: 502});
  const result = {
    operation: 'drive.share_folder', folderId, folderName: folder.name, webViewLink: folder.webViewLink, email, requestedRole: role,
    permission: {id: verifiedPermission.id, type: verifiedPermission.type, role: verifiedPermission.role, emailAddress: verifiedPermission.emailAddress, displayName: verifiedPermission.displayName || ''},
    verified: true, reused, upgraded, notificationRequested: args.sendNotificationEmail !== false && !reused, auditRequestId: requestId,
  };
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'drive_operation', operation: 'drive.share_folder', requestId,
    fileId: folderId, affectedFileIds: [folderId], oldMetadata: {permissions: beforeList.map((item) => ({id: item.id, type: item.type, role: item.role, emailAddress: item.emailAddress || ''}))},
    newMetadata: {permission: result.permission}, oldParents: folder.parents || [], newParents: folder.parents || [], reversible: true,
    rollback: {operation: 'drive.permissions.delete', fileId: folderId, permissionId: verifiedPermission.id}, callerNote: args.callerNote,
    providerSummary: `Shared Drive folder ${folder.name || folderId} with ${email} as ${verifiedPermission.role} and verified the permission by readback.`, result,
  });
  return {...result, audit: audit.audit};
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

const GITHUB_TRANSIENT_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504]);

function githubRetryDelayMs(response, attempt) {
  const retryAfter = response && response.headers && typeof response.headers.get === 'function' ?
    Number(response.headers.get('retry-after')) : NaN;
  if (Number.isFinite(retryAfter) && retryAfter >= 0) return Math.min(5000, Math.max(0, retryAfter * 1000));
  return Math.min(2000, 200 * (2 ** Math.max(0, attempt - 1)));
}

async function githubFetchWithRetry(url, requestOptions = {}, retryOptions = {}) {
  const method = safeText(requestOptions.method || 'GET', 16).toUpperCase();
  const retrySafe = ['GET', 'HEAD'].includes(method) || retryOptions.retryUnsafe === true;
  const maxAttempts = retrySafe ? Math.max(1, Math.min(4, Math.floor(safeNumber(retryOptions.maxAttempts, 3)))) : 1;
  let lastError = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    let response;
    try {
      response = await fetch(url, requestOptions);
    } catch (err) {
      lastError = err;
      if (attempt >= maxAttempts) throw err;
      await new Promise((resolve) => setTimeout(resolve, githubRetryDelayMs(null, attempt)));
      continue;
    }
    if (!GITHUB_TRANSIENT_STATUS_CODES.has(response.status) || attempt >= maxAttempts) return response;
    await new Promise((resolve) => setTimeout(resolve, githubRetryDelayMs(response, attempt)));
  }
  throw lastError || new Error('GitHub request exhausted retry attempts.');
}

async function githubRequest(githubToken, route, options = {}) {
  const token = githubTokenValue(githubToken);
  if (!token) {
    const err = new Error('GITHUB_TOKEN secret is not configured for Home Center GitHub tools.');
    err.status = 503;
    throw err;
  }
  const response = await githubFetchWithRetry(`https://api.github.com${route}`, {
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

function githubAdminLegacyOwners(githubAdmin = {}) {
  const raw = githubAdminSecretValue(githubAdmin, 'allowedOwners', 'HOME_CENTER_GITHUB_ADMIN_OWNERS', 2000) || 'Valar05';
  return raw.split(',').map((owner) => safeText(owner, 120)).filter((owner) => /^[A-Za-z0-9_.-]{1,120}$/.test(owner));
}

function githubAdminUserProfiles(githubAdmin = {}) {
  let supplied = githubAdmin && typeof githubAdmin.userProfiles === 'function' ? githubAdmin.userProfiles() : githubAdmin && githubAdmin.userProfiles;
  if (supplied === undefined || supplied === null || supplied === '') supplied = process.env.HOME_CENTER_GITHUB_ADMIN_USER_PROFILES_B64 || '';
  if (!supplied) return {};
  let parsed = supplied;
  try {
    if (typeof supplied === 'string') {
      const raw = safeText(supplied, 24000);
      const json = raw.startsWith('{') ? raw : Buffer.from(raw, 'base64').toString('utf8');
      parsed = JSON.parse(json);
    }
  } catch (_) {
    throw Object.assign(new Error('HOME_CENTER_GITHUB_ADMIN_USER_PROFILES_B64 must be Base64-encoded JSON.'), {status: 503, code: 'github_admin_user_profiles_invalid'});
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw Object.assign(new Error('GitHub Admin user profiles must be an object keyed by Home Center email.'), {status: 503, code: 'github_admin_user_profiles_invalid'});
  }
  const profiles = {};
  for (const [rawEmail, rawProfile] of Object.entries(parsed)) {
    const email = safeText(rawEmail, 320).toLowerCase();
    if (!GITHUB_ADMIN_ALLOWED_EMAIL_SET.has(email) || !rawProfile || typeof rawProfile !== 'object' || Array.isArray(rawProfile)) continue;
    const ownerValues = Array.isArray(rawProfile.owners) ? rawProfile.owners : safeText(rawProfile.owner, 120) ? [rawProfile.owner] : [];
    const owners = Array.from(new Set(ownerValues.map((owner) => safeText(owner, 120)).filter((owner) => /^[A-Za-z0-9_.-]{1,120}$/.test(owner))));
    const installationId = safeText(rawProfile.installationId, 120);
    if (installationId && !/^\d{1,30}$/.test(installationId)) {
      throw Object.assign(new Error(`GitHub Admin installationId is invalid for ${email}.`), {status: 503, code: 'github_admin_user_profile_invalid'});
    }
    profiles[email] = {owners, installationId};
  }
  return profiles;
}

function githubAdminUserProfile(user, githubAdmin = {}) {
  const email = requireGitHubAdminUser(user);
  const explicit = githubAdminUserProfiles(githubAdmin)[email];
  if (explicit) {
    return {
      email,
      configured: explicit.owners.length > 0 && !!explicit.installationId,
      owners: explicit.owners,
      installationId: explicit.installationId,
      credentialScope: 'user_profile',
      allowLegacyBootstrap: false,
    };
  }
  if (email === GITHUB_ADMIN_LEGACY_EMAIL) {
    const installationId = githubAdminSecretValue(githubAdmin, 'installationId', 'GITHUB_APP_INSTALLATION_ID', 120);
    const owners = githubAdminLegacyOwners(githubAdmin);
    return {email, configured: owners.length > 0 && !!installationId, owners, installationId, credentialScope: 'legacy_drew', allowLegacyBootstrap: true};
  }
  return {email, configured: false, owners: [], installationId: '', credentialScope: 'user_profile_missing', allowLegacyBootstrap: false};
}

function requireGitHubAdminProfile(user, githubAdmin = {}) {
  const profile = githubAdminUserProfile(user, githubAdmin);
  if (profile.configured) return profile;
  throw Object.assign(new Error("GitHub Admin is not connected for this Home Center user. Install the Home Center GitHub App on that user's GitHub account and configure the matching owner and installation ID."), {status: 403, code: 'github_admin_user_profile_missing'});
}

function githubAdminOwners(githubAdmin = {}, user = null) {
  return githubAdminUserProfile(user, githubAdmin).owners;
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

function requireGitHubAdminOwner(githubAdmin, user, owner) {
  const profile = requireGitHubAdminProfile(user, githubAdmin);
  const clean = safeGitHubOwner(owner);
  if (!profile.owners.includes(clean)) {
    throw Object.assign(new Error(`GitHub owner ${clean} is outside this Home Center user's GitHub Admin profile.`), {status: 403, code: 'github_admin_owner_not_allowed', allowedOwners: profile.owners});
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

async function githubAdminInstallationToken(githubAdmin = {}, user = null) {
  const profile = requireGitHubAdminProfile(user, githubAdmin);
  const appId = githubAdminSecretValue(githubAdmin, 'appId', 'GITHUB_APP_ID', 120);
  const installationId = profile.installationId;
  const privateKey = githubAdminSecretValue(githubAdmin, 'privateKey', 'GITHUB_APP_PRIVATE_KEY', 12000);
  if (!appId || !installationId || !privateKey) {
    const err = new Error("GitHub App credentials are not configured for this Home Center user's GitHub Admin profile.");
    err.status = 503;
    err.code = 'github_admin_app_credentials_missing';
    throw err;
  }
  const jwt = createGitHubAppJwt(appId, privateKey);
  const response = await githubFetchWithRetry(`https://api.github.com/app/installations/${encodeURIComponent(installationId)}/access_tokens`, {
    method: 'POST',
    headers: githubHeaders(jwt),
  }, {retryUnsafe: true});
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

async function githubAdminToken(githubAdmin = {}, user = null, options = {}) {
  const profile = requireGitHubAdminProfile(user, githubAdmin);
  const preferBootstrap = !!options.preferBootstrap;
  const bootstrap = profile.allowLegacyBootstrap
    ? githubAdminSecretValue(githubAdmin, 'bootstrapToken', 'GITHUB_BOOTSTRAP_TOKEN', 4096) || githubAdminSecretValue(githubAdmin, 'adminToken', 'GITHUB_ADMIN_TOKEN', 4096)
    : '';
  if (preferBootstrap) {
    if (!bootstrap) throw Object.assign(new Error("Creating a repository under a personal GitHub account requires that user's GitHub user authorization; Home Center will not borrow another user's bootstrap token."), {status: 403, code: 'github_admin_user_token_missing'});
    return {token: bootstrap, mode: 'bootstrap_token'};
  }
  try {
    return {token: await githubAdminInstallationToken(githubAdmin, user), mode: 'github_app_installation'};
  } catch (err) {
    if (bootstrap) return {token: bootstrap, mode: 'bootstrap_token_fallback', appError: {code: err.code || '', status: err.status || 0, message: safeText(err.message, 400)}};
    throw err;
  }
}

async function githubAdminRequest(githubAdmin, user, route, options = {}) {
  const tokenInfo = await githubAdminToken(githubAdmin, user, options);
  const response = await githubFetchWithRetry(`https://api.github.com${route}`, {
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


async function verifyGitHubDeliveryCandidate(githubAdmin, user, candidate) {
  const repository = safeText(candidate && candidate.repository, 240);
  const ref = safeText(candidate && candidate.ref, 80).toLowerCase();
  const artifactPath = safeText(candidate && candidate.path, 1000).replace(/^\/+/, '');
  if (!/^[^/]+\/[^/]+$/.test(repository) || !/^[a-f0-9]{40}$/.test(ref) || !artifactPath || artifactPath.includes('..')) {
    throw Object.assign(new Error('GitHub delivery candidate must use an immutable commit and safe repository path.'), {status: 400, failureKind: 'artifact_delivery.github_reference_invalid'});
  }
  const tokenInfo = await githubAdminToken(githubAdmin, user);
  const route = githubAdminRouteForRepo(repository, '/contents/' + artifactPath.split('/').map(encodeURIComponent).join('/') + '?ref=' + encodeURIComponent(ref));
  const response = await fetch('https://api.github.com' + route, {
    headers: githubHeaders(tokenInfo.token, {Accept: 'application/vnd.github.raw+json'}),
  });
  if (!response.ok) {
    throw Object.assign(new Error('GitHub artifact read failed with status ' + response.status + '.'), {status: response.status === 404 ? 404 : 502, failureKind: 'artifact_delivery.github_read_failed'});
  }
  const bytes = Buffer.from(await response.arrayBuffer());
  const digest = createHash('sha256').update(bytes).digest('hex');
  if (bytes.length !== candidate.byteLength) {
    throw Object.assign(new Error('GitHub artifact byte length does not match the receipt identity.'), {status: 409, failureKind: 'artifact_delivery.github_length_mismatch'});
  }
  if (digest !== candidate.sha256) {
    throw Object.assign(new Error('GitHub artifact SHA-256 does not match the receipt identity.'), {status: 409, failureKind: 'artifact_delivery.github_sha256_mismatch'});
  }
  return {
    file: {createReadStream: () => Readable.from([bytes])},
    generation: ref,
    byteLength: bytes.length,
    sha256: digest,
    authMode: tokenInfo.mode,
  };
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

function githubRulesetLegacyRepos(args = {}) {
  const configured = safeText(process.env.HOME_CENTER_GITHUB_RULESET_LEGACY_REPOS || '', 12000).split(',');
  const supplied = Array.isArray(args.legacyRepos) ? args.legacyRepos : [];
  return new Set(configured.concat(supplied).map((value) => safeText(value, 240).toLowerCase()).filter(Boolean));
}

function cleanGitHubRulesetRepository(repo = {}, args = {}) {
  const fullName = safeText(repo.full_name || `${repo.owner && repo.owner.login || ''}/${repo.name || ''}`, 240);
  const reasons = [];
  if (repo.private || safeText(repo.visibility, 20).toLowerCase() === 'private') reasons.push('not_public');
  if (repo.archived) reasons.push('archived');
  if (repo.fork || repo.parent || repo.source || repo.mirror_url) reasons.push('fork_shaped');
  if (!repo.default_branch || (Number(repo.size || 0) === 0 && !repo.pushed_at)) reasons.push('empty');
  const topics = Array.isArray(repo.topics) ? repo.topics.map((topic) => safeText(topic, 80).toLowerCase()) : [];
  if (githubRulesetLegacyRepos(args).has(fullName.toLowerCase()) || topics.includes('legacy')) reasons.push('legacy');
  return {
    id: repo.id || 0,
    name: repo.name || '',
    fullName,
    visibility: repo.private ? 'private' : safeText(repo.visibility || 'public', 20),
    defaultBranch: repo.default_branch || '',
    archived: !!repo.archived,
    forkShaped: !!(repo.fork || repo.parent || repo.source || repo.mirror_url),
    empty: !repo.default_branch || (Number(repo.size || 0) === 0 && !repo.pushed_at),
    legacy: reasons.includes('legacy'),
    eligible: reasons.length === 0,
    exceptionReasons: reasons,
    htmlUrl: repo.html_url || '',
  };
}

function requireEligibleGitHubRulesetRepository(repo, args = {}) {
  const repository = cleanGitHubRulesetRepository(repo, args);
  if (!repository.eligible) {
    throw Object.assign(new Error(`Repository ${repository.fullName} is excluded from Home Center ruleset changes: ${repository.exceptionReasons.join(', ')}.`), {status: 409, code: 'github_admin_ruleset_repository_excluded', repository});
  }
  return repository;
}

function cleanGitHubRuleset(ruleset = {}) {
  return {
    id: Number(ruleset.id || 0), name: ruleset.name || '', target: ruleset.target || '', sourceType: ruleset.source_type || '', source: ruleset.source || '', enforcement: ruleset.enforcement || '',
    bypassActors: Array.isArray(ruleset.bypass_actors) ? ruleset.bypass_actors.map((actor) => ({actorId: actor.actor_id === null ? null : Number(actor.actor_id || 0), actorType: actor.actor_type || '', bypassMode: actor.bypass_mode || ''})) : [],
    conditions: ruleset.conditions || null, rules: Array.isArray(ruleset.rules) ? ruleset.rules : [],
    htmlUrl: ruleset._links && ruleset._links.html && ruleset._links.html.href || '', createdAt: ruleset.created_at || '', updatedAt: ruleset.updated_at || '',
  };
}

function normalizeGitHubRulesetRules(value) {
  if (!Array.isArray(value) || !value.length || value.length > 50) throw Object.assign(new Error('rules must contain between 1 and 50 GitHub ruleset rules.'), {status: 400, code: 'github_admin_ruleset_rules_required'});
  const rules = value.map((rule) => {
    if (!rule || typeof rule !== 'object' || Array.isArray(rule)) throw Object.assign(new Error('each ruleset rule must be an object.'), {status: 400, code: 'github_admin_ruleset_invalid_rule'});
    const type = safeText(rule.type, 120);
    if (!/^[a-z][a-z0-9_]{1,119}$/.test(type)) throw Object.assign(new Error('each ruleset rule requires a valid type.'), {status: 400, code: 'github_admin_ruleset_invalid_rule_type'});
    if (['required_status_checks', 'required_workflows'].includes(type)) throw Object.assign(new Error(`Home Center rulesets must not require unstable CI checks (${type}).`), {status: 400, code: 'github_admin_ruleset_ci_checks_forbidden'});
    return rule.parameters === undefined ? {type} : {type, parameters: rule.parameters};
  });
  if (Buffer.byteLength(JSON.stringify(rules), 'utf8') > 100000) throw Object.assign(new Error('ruleset rules payload is too large.'), {status: 413, code: 'github_admin_ruleset_rules_too_large'});
  return rules;
}

function normalizeGitHubRulesetBypassActors(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > 50) throw Object.assign(new Error('bypassActors must be an array of at most 50 actors.'), {status: 400, code: 'github_admin_ruleset_invalid_bypass_actors'});
  return value.map((actor) => {
    const actorType = safeText(actor && (actor.actorType || actor.actor_type), 40);
    const bypassMode = safeText(actor && (actor.bypassMode || actor.bypass_mode) || 'always', 40);
    if (!['Integration', 'OrganizationAdmin', 'RepositoryRole', 'Team', 'DeployKey', 'User'].includes(actorType)) throw Object.assign(new Error('bypass actor type is invalid.'), {status: 400, code: 'github_admin_ruleset_invalid_bypass_actor'});
    if (!['always', 'pull_request', 'exempt'].includes(bypassMode)) throw Object.assign(new Error('bypass mode is invalid.'), {status: 400, code: 'github_admin_ruleset_invalid_bypass_mode'});
    const actorId = actor && (actor.actorId !== undefined ? actor.actorId : actor.actor_id);
    if (!['DeployKey', 'OrganizationAdmin'].includes(actorType) && (!Number.isInteger(Number(actorId)) || Number(actorId) < 1)) throw Object.assign(new Error(`actorId is required for ${actorType} bypass actors.`), {status: 400, code: 'github_admin_ruleset_bypass_actor_id_required'});
    const normalized = {actor_type: actorType, bypass_mode: bypassMode};
    if (actorType === 'DeployKey') normalized.actor_id = null;
    else if (actorType !== 'OrganizationAdmin') normalized.actor_id = Number(actorId);
    return normalized;
  });
}

async function githubAdminRulesetRepository(githubAdmin, user, repo, args = {}) {
  const cleanRepo = safeGitHubRepo(repo);
  requireGitHubAdminOwner(githubAdmin, user, cleanRepo.split('/')[0]);
  const response = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(cleanRepo));
  return {repo: cleanRepo, repository: requireEligibleGitHubRulesetRepository(response.json || {}, args), authMode: response.authMode};
}

async function githubAdminInventoryRulesetsOperation({user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  const owner = requireGitHubAdminOwner(githubAdmin, user, args.owner || githubAdminOwners(githubAdmin, user)[0]);
  const limit = Math.max(1, Math.min(500, Math.floor(Number(args.limit || 200)) || 200));
  const repositories = [];
  let authMode = '';
  for (let page = 1; repositories.length < limit; page += 1) {
    const perPage = Math.min(100, limit - repositories.length);
    const response = await githubAdminRequest(githubAdmin, user, `/users/${encodeURIComponent(owner)}/repos${githubQuery({type: 'owner', sort: 'full_name', direction: 'asc', per_page: perPage, page})}`);
    authMode = response.authMode;
    const batch = Array.isArray(response.json) ? response.json : [];
    repositories.push(...batch);
    if (batch.length < perPage) break;
  }
  const inventory = [];
  for (const rawRepo of repositories.slice(0, limit)) {
    const repository = cleanGitHubRulesetRepository(rawRepo, args);
    let rulesets = [];
    if (repository.visibility === 'public') {
      const response = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repository.fullName, `/rulesets${githubQuery({includes_parents: false, targets: 'branch', per_page: 100})}`));
      rulesets = (Array.isArray(response.json) ? response.json : []).map(cleanGitHubRuleset);
    }
    inventory.push({...repository, rulesetCount: rulesets.length, rulesets});
  }
  const publicRepositories = inventory.filter((repo) => repo.visibility === 'public');
  return {ok: true, owner, authMode, scope: {visibility: 'public', target: 'branch', ref: '~DEFAULT_BRANCH'}, repositories: publicRepositories, eligibleCount: publicRepositories.filter((repo) => repo.eligible).length, exceptionCount: publicRepositories.filter((repo) => !repo.eligible).length, mutationPerformed: false};
}

function githubRulesetMutationBody(args = {}, before = null) {
  const enforcement = safeText(args.enforcement || before && before.enforcement || 'active', 20);
  if (!['disabled', 'active', 'evaluate'].includes(enforcement)) throw Object.assign(new Error('enforcement must be disabled, active, or evaluate.'), {status: 400, code: 'github_admin_ruleset_invalid_enforcement'});
  const name = safeText(args.name || before && before.name, 120);
  if (!name) throw Object.assign(new Error('ruleset name is required.'), {status: 400, code: 'github_admin_ruleset_name_required'});
  return {name, target: 'branch', enforcement, bypass_actors: normalizeGitHubRulesetBypassActors(args.bypassActors !== undefined ? args.bypassActors : before && before.bypassActors || []), conditions: {ref_name: {include: ['~DEFAULT_BRANCH'], exclude: []}}, rules: normalizeGitHubRulesetRules(args.rules !== undefined ? args.rules : before && before.rules)};
}

async function githubAdminCreateRulesetOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user); requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const checked = await githubAdminRulesetRepository(githubAdmin, user, args.repo, args);
  const response = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(checked.repo, '/rulesets'), {method: 'POST', body: githubRulesetMutationBody(args)});
  const ruleset = cleanGitHubRuleset(response.json || {});
  const result = {repo: checked.repo, repository: checked.repository, ruleset, rulesetId: ruleset.id, status: response.status, authMode: response.authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.create_ruleset', operation: 'github.admin.create_ruleset', requestId, fileId: `github:${checked.repo}:ruleset:${ruleset.id}`, affectedFileIds: [`github:${checked.repo}:ruleset:${ruleset.id}`], oldMetadata: null, newMetadata: ruleset, oldParents: [], newParents: [checked.repository.defaultBranch], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Created default-branch ruleset ${ruleset.name} in ${checked.repo}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminUpdateRulesetOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user); requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const checked = await githubAdminRulesetRepository(githubAdmin, user, args.repo, args);
  const rulesetId = Number(args.rulesetId);
  if (!Number.isInteger(rulesetId) || rulesetId < 1) throw Object.assign(new Error('rulesetId must be a positive integer.'), {status: 400, code: 'github_admin_ruleset_id_required'});
  const route = githubAdminRouteForRepo(checked.repo, `/rulesets/${rulesetId}`);
  const before = cleanGitHubRuleset((await githubAdminRequest(githubAdmin, user, `${route}${githubQuery({includes_parents: false})}`)).json || {});
  if (before.sourceType && before.sourceType !== 'Repository') throw Object.assign(new Error('Only repository-owned rulesets may be updated.'), {status: 409, code: 'github_admin_ruleset_not_repository_owned'});
  const response = await githubAdminRequest(githubAdmin, user, route, {method: 'PUT', body: githubRulesetMutationBody(args, before)});
  const ruleset = cleanGitHubRuleset(response.json || {});
  const result = {repo: checked.repo, repository: checked.repository, ruleset, rulesetId, before, status: response.status, authMode: response.authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.update_ruleset', operation: 'github.admin.update_ruleset', requestId, fileId: `github:${checked.repo}:ruleset:${rulesetId}`, affectedFileIds: [`github:${checked.repo}:ruleset:${rulesetId}`], oldMetadata: before, newMetadata: ruleset, oldParents: [checked.repository.defaultBranch], newParents: [checked.repository.defaultBranch], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Updated default-branch ruleset ${ruleset.name} in ${checked.repo}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminVerifyRulesetReadbackOperation({user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  const checked = await githubAdminRulesetRepository(githubAdmin, user, args.repo, args);
  const rulesetId = Number(args.rulesetId);
  if (!Number.isInteger(rulesetId) || rulesetId < 1) throw Object.assign(new Error('rulesetId must be a positive integer.'), {status: 400, code: 'github_admin_ruleset_id_required'});
  const response = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(checked.repo, `/rulesets/${rulesetId}${githubQuery({includes_parents: false})}`));
  const ruleset = cleanGitHubRuleset(response.json || {});
  const checks = {idMatches: ruleset.id === rulesetId, repositoryOwned: !ruleset.sourceType || ruleset.sourceType === 'Repository', branchTarget: ruleset.target === 'branch', defaultBranchOnly: !!(ruleset.conditions && ruleset.conditions.ref_name && Array.isArray(ruleset.conditions.ref_name.include) && ruleset.conditions.ref_name.include.length === 1 && ruleset.conditions.ref_name.include[0] === '~DEFAULT_BRANCH' && Array.isArray(ruleset.conditions.ref_name.exclude) && ruleset.conditions.ref_name.exclude.length === 0), noCiRequirements: !ruleset.rules.some((rule) => ['required_status_checks', 'required_workflows'].includes(rule && rule.type)), expectedNameMatches: !safeText(args.expectedName, 120) || ruleset.name === safeText(args.expectedName, 120), expectedEnforcementMatches: !safeText(args.expectedEnforcement, 20) || ruleset.enforcement === safeText(args.expectedEnforcement, 20)};
  const verified = Object.values(checks).every(Boolean);
  return {ok: verified, verified, repo: checked.repo, repository: checked.repository, rulesetId, ruleset, checks, status: response.status, authMode: response.authMode, mutationPerformed: false, verifiedAt: new Date().toISOString()};
}

function safeGitHubAdminStatusSecret(githubAdmin, key, envKey, max = 12000) {
  try {
    return {value: githubAdminSecretValue(githubAdmin, key, envKey, max), error: null};
  } catch (err) {
    return {value: '', error: {code: 'github_admin_secret_inaccessible', message: envKey + ' could not be read.'}};
  }
}

async function existingGitHubAdminAudit(admin, user, requestId) {
  const existing = await existingAudit(admin, requestId);
  if (!existing) return null;
  const actor = requireGitHubAdminUser(user);
  if (safeText(existing.actor, 320).toLowerCase() !== actor) {
    throw Object.assign(new Error('GitHub Admin requestId is already owned by another Home Center user.'), {status: 409, code: 'github_admin_request_id_owner_conflict'});
  }
  return existing;
}

async function githubAdminAuthStatusOperation({user, githubAdmin = {}}) {
  const actor = requireGitHubAdminUser(user);
  const profile = githubAdminUserProfile(user, githubAdmin);
  const owners = profile.owners;
  const runtimeEnabled = githubAdminEnabled();
  const appIdSecret = safeGitHubAdminStatusSecret(githubAdmin, 'appId', 'GITHUB_APP_ID', 120);
  const privateKeySecret = safeGitHubAdminStatusSecret(githubAdmin, 'privateKey', 'GITHUB_APP_PRIVATE_KEY', 12000);
  const bootstrapSecret = profile.allowLegacyBootstrap ? safeGitHubAdminStatusSecret(githubAdmin, 'bootstrapToken', 'GITHUB_BOOTSTRAP_TOKEN', 4096) : {value: '', error: null};
  const adminTokenSecret = profile.allowLegacyBootstrap ? safeGitHubAdminStatusSecret(githubAdmin, 'adminToken', 'GITHUB_ADMIN_TOKEN', 4096) : {value: '', error: null};
  const appId = appIdSecret.value;
  const privateKeyConfigured = !!privateKeySecret.value;
  const bootstrapConfigured = !!(bootstrapSecret.value || adminTokenSecret.value);
  const appConfigured = !!(appId && profile.installationId && privateKeyConfigured);
  const disabledReasons = [];
  let installationProbe = {code: 'not_applicable'};
  let authenticated = false;
  let providerReachable = false;
  for (const secret of [appIdSecret, privateKeySecret, bootstrapSecret, adminTokenSecret]) {
    if (secret.error) disabledReasons.push(secret.error);
  }
  if (!profile.configured) disabledReasons.push({code: 'github_admin_user_profile_missing', message: 'No owner and GitHub App installation are bound to this Home Center user.'});
  if (!runtimeEnabled) disabledReasons.push({code: 'runtime_flag_disabled', message: 'HOME_CENTER_GITHUB_ADMIN_ENABLED is not true.'});
  if (profile.configured && !appConfigured) disabledReasons.push({code: 'github_app_credentials_missing', message: 'GitHub App id, user installation id, or private key is missing.'});
  if (runtimeEnabled && appConfigured) {
    try {
      await githubAdminInstallationToken(githubAdmin, user);
      authenticated = true;
      providerReachable = true;
      installationProbe = {ok: true, code: 'ok', providerStatus: 201};
    } catch (err) {
      installationProbe = {ok: false, code: safeText(err && err.code, 120) || 'github_admin_installation_probe_failed', providerStatus: Number(err && err.providerStatus || err && err.status || 0) || 0, message: safeText(err && err.message, 300)};
      disabledReasons.push({code: installationProbe.code, message: installationProbe.message || 'GitHub App installation authority probe failed.', providerStatus: installationProbe.providerStatus});
    }
  }
  return {
    ok: true,
    enabled: runtimeEnabled && profile.configured && appConfigured && authenticated,
    authority: 'home_center_github_admin_v2_user_scoped',
    actor,
    profileConfigured: profile.configured,
    credentialScope: profile.credentialScope,
    installationBound: !!profile.installationId,
    primaryCredential: appConfigured ? 'github_app_installation' : '',
    fallbackCredentialConfigured: bootstrapConfigured,
    appConfigured,
    authenticated,
    providerReachable,
    allowedOwners: owners,
    mutationRequiresRequestId: true,
    requestIdOwnershipEnforced: true,
    disabledReasons,
    diagnostics: {installationProbe},
    secretsExposed: false,
    supportedOperations: ['github_admin.auth_status', 'github_admin.repos.create', 'github_admin.repos.configure', 'github_admin.branches.create', 'github_admin.files.upsert', 'github_admin.pull_requests.create', 'github_admin.pull_requests.merge', 'github_admin.workflows.dispatch', 'github_admin.inventory_rulesets', 'github_admin.create_ruleset', 'github_admin.update_ruleset', 'github_admin.verify_ruleset_readback'],
  };
}
async function githubAdminCreateRepoOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const owner = requireGitHubAdminOwner(githubAdmin, user, args.owner || githubAdminOwners(githubAdmin, user)[0]);
  const name = safeGitHubRepoName(args.name);
  const ownerType = safeText(args.ownerType || args.scope || 'org', 20).toLowerCase();
  if (!['org', 'user'].includes(ownerType)) throw Object.assign(new Error('ownerType must be org or user.'), {status: 400, code: 'github_admin_invalid_owner_type'});
  const visibility = safeText(args.visibility || 'private', 20).toLowerCase();
  if (!['private', 'public', 'internal'].includes(visibility)) throw Object.assign(new Error('visibility must be private, public, or internal.'), {status: 400, code: 'github_admin_invalid_visibility'});
  const body = {name, description: safeText(args.description, 1000), private: visibility === 'private', visibility, auto_init: args.autoInit === true};
  if (safeText(args.homepage, 1000)) body.homepage = safeText(args.homepage, 1000);
  const route = ownerType === 'user' ? '/user/repos' : `/orgs/${encodeURIComponent(owner)}/repos`;
  const repoFullName = `${owner}/${name}`;
  let repo;
  let authMode = '';
  let status = 0;
  let alreadyExisted = false;
  try {
    const created = await githubAdminRequest(githubAdmin, user, route, {method: 'POST', body, preferBootstrap: ownerType === 'user'});
    repo = cleanGitHubAdminRepo(created.json || {});
    authMode = created.authMode;
    status = created.status;
  } catch (err) {
    const message = safeText(err && err.message, 1000).toLowerCase();
    const existingRepoConflict = [409, 422].includes(Number(err && err.status))
      && /already exists|name already exists|repository creation failed/.test(message);
    if (!existingRepoConflict) throw err;
    const resolved = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repoFullName));
    repo = cleanGitHubAdminRepo(resolved.json || {});
    authMode = resolved.authMode;
    status = resolved.status;
    alreadyExisted = true;
  }
  const result = {repo, repoFullName: repo.fullName || repoFullName, htmlUrl: repo.htmlUrl, status, authMode, auditRequestId: requestId, alreadyExisted};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.repos.create', operation: 'github.admin.repos.create', requestId, fileId: `github:${repo.fullName || repoFullName}`, affectedFileIds: [`github:${repo.fullName || repoFullName}`], oldMetadata: alreadyExisted ? repo : null, newMetadata: repo, oldParents: [], newParents: [owner], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: alreadyExisted ? `GitHub repository ${repo.fullName || repoFullName} already existed; returned existing metadata.` : `Created GitHub repository ${repo.fullName || repoFullName}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminConfigureRepoOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, user, repo.split('/')[0]);
  const body = {};
  ['description', 'homepage', 'default_branch'].forEach((key) => { if (safeText(args[key], 1000)) body[key] = safeText(args[key], 1000); });
  ['has_issues', 'has_projects', 'has_wiki', 'allow_squash_merge', 'allow_merge_commit', 'allow_rebase_merge', 'delete_branch_on_merge', 'allow_auto_merge'].forEach((key) => { if (typeof args[key] === 'boolean') body[key] = args[key]; });
  if (!Object.keys(body).length) throw Object.assign(new Error('at least one repository setting is required.'), {status: 400, code: 'github_admin_no_repo_settings'});
  const before = cleanGitHubAdminRepo((await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo))).json || {});
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo), {method: 'PATCH', body});
  const after = cleanGitHubAdminRepo(json || {});
  const result = {repo, before, after, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.repos.configure', operation: 'github.admin.repos.configure', requestId, fileId: `github:${repo}`, affectedFileIds: [`github:${repo}`], oldMetadata: before, newMetadata: after, oldParents: [], newParents: [], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Configured GitHub repository ${repo}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminCreateBranchOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, user, repo.split('/')[0]);
  const branch = safeGitHubRef(args.branch);
  const fromBranch = safeGitHubRef(args.fromBranch || args.base || 'main');
  if (!branch) throw Object.assign(new Error('branch is required.'), {status: 400, code: 'github_admin_branch_required'});
  const base = (await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, `/git/ref/heads/${encodeURIComponent(fromBranch)}`))).json || {};
  const sha = safeText(args.sha, 80) || base.object && base.object.sha;
  if (!sha) throw Object.assign(new Error('base branch did not resolve to a commit SHA.'), {status: 404, code: 'github_admin_base_branch_missing'});
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, '/git/refs'), {method: 'POST', body: {ref: `refs/heads/${branch}`, sha}});
  const created = cleanGitHubAdminBranch(json || {});
  const result = {repo, branch, fromBranch, sha, ref: created, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.branches.create', operation: 'github.admin.branches.create', requestId, fileId: `github:${repo}:refs/heads/${branch}`, affectedFileIds: [`github:${repo}:refs/heads/${branch}`], oldMetadata: null, newMetadata: created, oldParents: [], newParents: [repo], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Created GitHub branch ${repo}:${branch}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminUpsertFileOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, user, repo.split('/')[0]);
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
      before = (await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, `/contents/${filePath.split('/').map(encodeURIComponent).join('/')}${githubQuery({ref: branch})}`))).json;
      sha = before && before.sha || '';
    } catch (err) {
      if (err.status !== 404) throw err;
    }
  }
  const body = {message, content: contentBase64, branch};
  if (sha) body.sha = sha;
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, `/contents/${filePath.split('/').map(encodeURIComponent).join('/')}`), {method: 'PUT', body});
  const commit = cleanGitHubAdminCommit(json && json.commit || {});
  const result = {repo, path: filePath, branch, commit, contentSha: json && json.content && json.content.sha || '', status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.files.upsert', operation: 'github.admin.files.upsert', requestId, fileId: `github:${repo}/${filePath}`, affectedFileIds: [`github:${repo}/${filePath}`, `github:${repo}@${commit.sha}`], oldMetadata: before ? {sha: before.sha || ''} : null, newMetadata: {sha: result.contentSha, commit}, oldParents: [branch], newParents: [branch], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Upserted ${repo}/${filePath} on ${branch}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminCreatePullRequestOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, user, repo.split('/')[0]);
  const title = safeText(args.title, 240);
  const head = safeGitHubRef(args.head);
  const base = safeGitHubRef(args.base || 'main');
  if (!title || !head || !base) throw Object.assign(new Error('title, head, and base are required.'), {status: 400, code: 'github_admin_pr_input_required'});
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, '/pulls'), {method: 'POST', body: {title, head, base, body: safeText(args.body, 60000), draft: args.draft === true}});
  const pullRequest = cleanGitHubPullRequest(json || {});
  const result = {repo, pullRequest, number: pullRequest.number, htmlUrl: pullRequest.htmlUrl, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.pull_requests.create', operation: 'github.admin.pull_requests.create', requestId, fileId: `github:${repo}#${pullRequest.number}`, affectedFileIds: [`github:${repo}#${pullRequest.number}`], oldMetadata: null, newMetadata: pullRequest, oldParents: [base], newParents: [head], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Created GitHub PR ${repo}#${pullRequest.number}: ${title}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminCheckMergePreconditions(githubAdmin, user, repo, number, args = {}) {
  const pullRequest = cleanGitHubPullRequest((await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, `/pulls/${number}`))).json || {});
  const expectedHeadSha = safeText(args.expectedHeadSha || args.headSha, 80);
  if (!expectedHeadSha) throw Object.assign(new Error('expectedHeadSha is required for PR merge.'), {status: 400, code: 'github_admin_expected_head_sha_required'});
  if (!pullRequest.head || pullRequest.head.sha !== expectedHeadSha) throw Object.assign(new Error('PR head SHA changed; refusing to merge stale review.'), {status: 409, code: 'github_admin_head_sha_mismatch', currentHeadSha: pullRequest.head && pullRequest.head.sha || '', expectedHeadSha});
  if (pullRequest.draft) throw Object.assign(new Error('Draft pull requests cannot be merged by Home Center.'), {status: 409, code: 'github_admin_pr_is_draft'});
  if (args.requireGreenChecks === false) return {pullRequest, combinedStatus: null};
  const status = (await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, `/commits/${expectedHeadSha}/status`))).json || {};
  if (status.state !== 'success' && !(args.allowNoChecks === true && Array.isArray(status.statuses) && !status.statuses.length)) {
    throw Object.assign(new Error(`Required commit statuses are not green: ${status.state || 'unknown'}.`), {status: 409, code: 'github_admin_checks_not_green', combinedState: status.state || 'unknown'});
  }
  return {pullRequest, combinedStatus: {state: status.state || '', totalCount: status.total_count || 0}};}

async function githubAdminMergePullRequestOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  requireGitHubAdminEnabled();
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, user, repo.split('/')[0]);
  const number = safeGitHubNumber(args.number || args.pullNumber, 'pullNumber');
  const method = safeText(args.mergeMethod || 'squash', 20).toLowerCase();
  if (!['merge', 'squash', 'rebase'].includes(method)) throw Object.assign(new Error('mergeMethod must be merge, squash, or rebase.'), {status: 400, code: 'github_admin_invalid_merge_method'});
  const preflight = await githubAdminCheckMergePreconditions(githubAdmin, user, repo, number, args);
  const body = {merge_method: method, sha: safeText(args.expectedHeadSha || args.headSha, 80)};
  if (safeText(args.commitTitle, 240)) body.commit_title = safeText(args.commitTitle, 240);
  if (safeText(args.commitMessage, 60000)) body.commit_message = safeText(args.commitMessage, 60000);
  const {json, authMode, status} = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, `/pulls/${number}/merge`), {method: 'PUT', body});
  const result = {repo, number, mergeMethod: method, merged: !!(json && json.merged), sha: json && json.sha || '', message: json && json.message || '', preflight, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.pull_requests.merge', operation: 'github.admin.pull_requests.merge', requestId, fileId: `github:${repo}#${number}`, affectedFileIds: [`github:${repo}#${number}`, `github:${repo}@${result.sha}`], oldMetadata: preflight.pullRequest, newMetadata: result, oldParents: [preflight.pullRequest.head && preflight.pullRequest.head.ref || ''], newParents: [preflight.pullRequest.base && preflight.pullRequest.base.ref || ''], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Merged GitHub PR ${repo}#${number} with ${method}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminDispatchWorkflowOperation({admin, user, githubAdmin, args = {}}) {
  requireGitHubAdminUser(user);
  requireGitHubAdminEnabled();
  if (!safeText(args.requestId, 180)) throw Object.assign(new Error('requestId is required for github_admin.workflows.dispatch.'), {status: 400, code: 'github_admin_request_id_required'});
  const requestId = createRequestId(args.requestId);
  const existing = await existingGitHubAdminAudit(admin, user, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};
  const repo = safeGitHubRepo(args.repo);
  requireGitHubAdminOwner(githubAdmin, user, repo.split('/')[0]);
  const workflowId = safeText(args.workflowId || args.workflowFile, 240);
  const ref = safeGitHubRef(args.ref || 'main');
  if (!workflowId || /[\\?#]/.test(workflowId)) throw Object.assign(new Error('workflowId is required and must be a workflow file name or numeric workflow id.'), {status: 400, code: 'github_admin_invalid_workflow_id'});
  const inputs = args.inputs && typeof args.inputs === 'object' && !Array.isArray(args.inputs) ? args.inputs : {};
  const {authMode, status} = await githubAdminRequest(githubAdmin, user, githubAdminRouteForRepo(repo, `/actions/workflows/${encodeURIComponent(workflowId)}/dispatches`), {method: 'POST', body: {ref, inputs}});
  const result = {repo, workflowId, ref, dispatched: true, status, authMode, auditRequestId: requestId};
  const audit = await auditWrite(admin, {actor: user.email || user.uid || 'unknown', authKind: user.authKind, tool: 'github_admin.workflows.dispatch', operation: 'github.admin.workflows.dispatch', requestId, fileId: `github:${repo}:workflow:${workflowId}`, affectedFileIds: [`github:${repo}:workflow:${workflowId}`], oldMetadata: null, newMetadata: result, oldParents: [repo], newParents: [ref], reversible: false, rollback: null, callerNote: args.callerNote, providerSummary: `Dispatched GitHub workflow ${workflowId} in ${repo} at ${ref}.`, result});
  return {...result, audit: audit.audit};
}

async function githubAdminOperationRunOperation({admin, user, githubAdmin = {}, args = {}}) {
  requireGitHubAdminUser(user);
  const operation = safeText(args.operation || args.type || args.toolName, 120);
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {...args};
  delete operationArgs.operation;
  delete operationArgs.type;
  delete operationArgs.toolName;
  delete operationArgs.args;
  if (operation === 'github_admin.auth_status') return githubAdminAuthStatusOperation({user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.repos.create') return githubAdminCreateRepoOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.repos.configure') return githubAdminConfigureRepoOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.branches.create') return githubAdminCreateBranchOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.files.upsert') return githubAdminUpsertFileOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.pull_requests.create') return githubAdminCreatePullRequestOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.pull_requests.merge') return githubAdminMergePullRequestOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.workflows.dispatch') return githubAdminDispatchWorkflowOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.inventory_rulesets') return githubAdminInventoryRulesetsOperation({user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.create_ruleset') return githubAdminCreateRulesetOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.update_ruleset') return githubAdminUpdateRulesetOperation({admin, user, githubAdmin, args: operationArgs});
  if (operation === 'github_admin.verify_ruleset_readback') return githubAdminVerifyRulesetReadbackOperation({user, githubAdmin, args: operationArgs});
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
    'github_admin.inventory_rulesets': {summary: 'Inventory branch rulesets for public owner repositories and classify empty, legacy, archived, and fork-shaped exceptions.', write: false, requiredPermissions: ['Metadata: read'], input: {owner: 'string default profile owner', legacyRepos: 'optional owner/name[]', limit: 'optional number'}},
    'github_admin.create_ruleset': {summary: 'Create an audited repository ruleset scoped only to the public repository default branch, excluding legacy repository shapes and CI requirements.', write: true, requiresRequestId: true, requiredPermissions: ['Administration: write'], input: {repo: 'owner/name', name: 'string', enforcement: 'disabled|active|evaluate', bypassActors: 'optional actor[]', rules: 'rule[] excluding required_status_checks and required_workflows', legacyRepos: 'optional owner/name[]', requestId: 'string'}},
    'github_admin.update_ruleset': {summary: 'Update an audited repository ruleset while preserving public/default-branch scope, repository exceptions, and the no-CI-check boundary.', write: true, requiresRequestId: true, requiredPermissions: ['Administration: write'], input: {repo: 'owner/name', rulesetId: 'number', name: 'optional string', enforcement: 'optional disabled|active|evaluate', bypassActors: 'optional actor[]', rules: 'optional rule[] excluding required_status_checks and required_workflows', legacyRepos: 'optional owner/name[]', requestId: 'string'}},
    'github_admin.verify_ruleset_readback': {summary: 'Read one repository ruleset back and verify its id, ownership, default-branch scope, and no-CI-check boundary.', write: false, requiredPermissions: ['Metadata: read'], input: {repo: 'owner/name', rulesetId: 'number', expectedName: 'optional string', expectedEnforcement: 'optional string', legacyRepos: 'optional owner/name[]'}},
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
    segments: synthesized.map((segment) => ({index: segment.index, speaker: segment.speaker, voiceName: segment.voiceName, voiceId: segment.voiceId, modelId: segment.modelId, textCharCount: segment.textCharCount, byteCount: segment.pcm.length, inputByteCount: segment.inputByteCount, pitchSemitones: segment.pitchSemitones, pitchScale: segment.pitchScale, pitchProcessor: segment.pitchProcessor, pitchBypassed: segment.pitchBypassed, inputFrameCount: segment.inputFrameCount, outputFrameCount: segment.outputFrameCount, durationRatio: segment.durationRatio})),
  };
}

function cartesiaVoiceMetadataFilterMatch(voice, args = {}) {
  const country = safeText(args.country, 80).toLowerCase();
  const accent = safeText(args.accent, 80).toLowerCase();
  const locale = safeText(args.locale, 40).toLowerCase();
  if (country && safeText(voice.country, 80).toLowerCase() !== country) return false;
  if (accent && !safeText(voice.accent, 80).toLowerCase().includes(accent)) return false;
  if (locale && safeText(voice.locale || voice.language, 40).toLowerCase().replace('_', '-') !== locale.replace('_', '-')) return false;
  return true;
}

async function cartesiaVoicesOperation({cartesiaApiKey = () => '', geminiApiKey = () => '', args = {}}) {
  const query = safeText(args.query || args.q, 240);
  const limit = chatGptLimit(args.limit, 100, 100);
  const catalog = await listCartesiaVoiceCatalog({
    apiKeyGetter: cartesiaApiKey,
    query,
    limit,
    pageToken: args.pageToken || args.cursor,
    startingAfter: args.startingAfter || args.starting_after,
    endingBefore: args.endingBefore || args.ending_before,
    language: args.language || args.locale,
    locale: args.locale,
    gender: args.gender,
    isOwner: args.isOwner || args.is_owner,
    includePreviewUrl: args.includePreviewUrl !== false,
  });
  const voices = catalog.voices.map(normalizeCartesiaVoice).filter((voice) => cartesiaVoiceMetadataFilterMatch(voice, args));
  const metadataFilters = {
    accent: safeText(args.accent, 80),
    country: safeText(args.country, 80),
    locale: safeText(args.locale, 40),
  };
  return {
    provider: 'cartesia',
    catalog: catalog.catalog,
    query,
    filters: {...catalog.filters, ...metadataFilters},
    supportedFilters: catalog.supportedFilters,
    pagination: catalog.pagination,
    limit,
    voices,
  };
}

async function synthesizeCartesiaAudioArtifactOperation({google, admin, auth, user, cartesiaApiKey = () => '', args = {}}) {
  const requestId = createRequestId(args.requestId);
  const existing = await existingAudit(admin, requestId);
  if (existing && existing.status === 'success' && existing.result) return {...existing.result, idempotent: true, audit: existing};

  const audioFormat = cartesiaAudioArtifactFormat(args);
  const sampleRate = Math.max(8000, Math.min(48000, Math.floor(safeNumber(args.sampleRate, 24000)) || 24000));
  const parentFolderId = safeText(args.parentFolderId, 220) ? safeDriveFileId(args.parentFolderId) : '';
  const fallbackName = 'cartesia-tts-' + requestId + '.' + audioFormat.extension;
  const suppliedName = safeText(args.name || args.fileName || args.title, 240);
  const baseName = safeArtifactName(suppliedName || fallbackName, fallbackName).replace(new RegExp('\\.' + audioFormat.extension + '$', 'i'), '');
  const name = baseName + '.' + audioFormat.extension;
  const synthesis = await synthesizeCartesiaAudioBytes({cartesiaApiKey, args, audioFormat, sampleRate});
  const audio = synthesis.audio;
  const digest = {byteCount: audio.length, sha256: sha256Hex(audio)};
  const drive = google.drive({version: 'v3', auth});
  const media = {mimeType: audioFormat.mimeType, body: Readable.from([audio])};
  const created = await drive.files.create({
    requestBody: {name, mimeType: audioFormat.mimeType, ...(parentFolderId ? {parents: [parentFolderId]} : {})},
    media,
    fields: driveFields(),
    supportsAllDrives: true,
  });
  const metadata = cleanDriveFile(created.data || {});
  const fileId = safeDriveFileId(metadata.id);
  const after = await getDriveMetadata(drive, fileId).catch(() => metadata);
  const readback = await drive.files.get({fileId, alt: 'media', supportsAllDrives: true}, {responseType: 'arraybuffer'});
  const readbackBuffer = mediaBuffer(readback.data);
  const readbackDigest = {byteCount: readbackBuffer.length, sha256: sha256Hex(readbackBuffer)};
  if (readbackDigest.byteCount !== digest.byteCount || readbackDigest.sha256 !== digest.sha256) {
    const err = new Error('Drive readback verification failed for ' + name + ': wrote ' + digest.byteCount + '/' + digest.sha256 + ', read ' + readbackDigest.byteCount + '/' + readbackDigest.sha256 + '.');
    err.status = 502;
    throw err;
  }
  const result = {
    provider: 'cartesia',
    fileId,
    id: fileId,
    name: after.name || metadata.name || name,
    mimeType: after.mimeType || metadata.mimeType || audioFormat.mimeType,
    webViewLink: after.webViewLink || metadata.webViewLink || '',
    parentFolderId: ((after.parents || metadata.parents || [])[0]) || parentFolderId,
    byteCount: digest.byteCount,
    sha256: digest.sha256,
    readbackByteCount: readbackDigest.byteCount,
    readbackSha256: readbackDigest.sha256,
    verified: true,
    audioFormat: audioFormat.format,
    sampleRate,
    channelCount: 1,
    pcmFormat: 'pcm_s16le',
    pitchSemitones: synthesis.defaultPitchSemitones || 0,
    pitchProcessor: synthesis.segments.some((segment) => !segment.pitchBypassed) ? 'rubberband-wasm' : 'none',
    voiceName: synthesis.segments[0] ? synthesis.segments[0].voiceName : CARTESIA_DEFAULT_VOICE_NAME,
    voiceId: synthesis.segments[0] ? synthesis.segments[0].voiceId : '',
    modelId: synthesis.segments[0] ? synthesis.segments[0].modelId : CARTESIA_DEFAULT_MODEL_ID,
    textCharCount: synthesis.segments.reduce((sum, segment) => sum + (segment.textCharCount || 0), 0),
    segmentCount: synthesis.segmentCount,
    stitched: Boolean(synthesis.stitched),
    segmentPauseMs: synthesis.segmentPauseMs || 0,
    segments: synthesis.segments,
    metadata: after,
    auditRequestId: requestId,
  };
  const audit = await auditWrite(admin, {
    actor: user.email || user.uid || 'unknown',
    authKind: user.authKind,
    tool: 'tts.synthesize',
    operation: 'tts.synthesize',
    requestId,
    fileId,
    affectedFileIds: [fileId],
    oldMetadata: null,
    newMetadata: after,
    oldParents: [],
    newParents: after.parents || [],
    reversible: false,
    rollback: null,
    callerNote: args.callerNote,
    providerSummary: safeText(args.callerNote, 400) || 'Synthesized Cartesia audio artifact ' + name + ' (' + digest.byteCount + ' bytes, sha256 ' + digest.sha256 + ').',
    result,
  });
  await recordActionAudit(admin, user, 'tts.synthesize', fileId, safeText(args.callerNote, 400) || 'Synthesized Cartesia audio artifact ' + name + ' (' + digest.byteCount + ' bytes).', requestId);
  return {...result, audit: audit.audit};
}

function speechProviderSelection(args = {}) {
  const requested = safeText(args.provider || 'auto', 40).toLowerCase() || 'auto';
  if (!['auto', 'cartesia', 'gemini'].includes(requested)) throw Object.assign(new Error('provider must be auto, cartesia, or gemini.'), {status: 400, failureKind: 'tts_provider_invalid'});
  const segments = Array.isArray(args.segments) ? args.segments : [];
  const requiresGemini = Boolean(safeText(args.direction || args.naturalLanguageDirection, 2000)) || /\[[^\]\r\n]+\]/.test(String(args.text || args.transcript || '')) || segments.some((segment) => Boolean(safeText(segment && (segment.direction || segment.naturalLanguageDirection), 2000)) || /\[[^\]\r\n]+\]/.test(String(segment && (segment.text || segment.transcript) || '')));
  return {requested, selected: requested === 'auto' ? (requiresGemini ? 'gemini' : 'cartesia') : requested, reason: requested === 'auto' ? (requiresGemini ? 'required_features' : 'backward_compatible_default') : 'explicit_provider'};
}

async function synthesizeSpeechAudioArtifactOperation(context) {
  const tierConfig = voiceTierPolicy.loadVoiceTierConfig();
  const tier = voiceTierPolicy.requestedTier(context.args || {}, tierConfig);
  if (tier) return synthesizeTieredSpeechAudioArtifactOperation(context, tier, tierConfig);
  const routing = speechProviderSelection(context.args || {});
  if (routing.selected === 'gemini') {
    try {
      return {...await synthesizeGeminiArtifact({...context, helpers: {createRequestId, existingAudit, auditWrite, recordActionAudit, safeDriveFileId}}), routing};
    } catch (error) {
      const policy = context.args && context.args.fallbackPolicy && typeof context.args.fallbackPolicy === 'object' ? context.args.fallbackPolicy : {};
      const allowed = Array.isArray(policy.allowedProviders) ? policy.allowedProviders.map((value) => safeText(value, 40).toLowerCase()) : [];
      if (policy.allowFallback !== true || !allowed.includes('cartesia')) throw error;
      const fallback = await synthesizeCartesiaAudioArtifactOperation({...context, args: {...context.args, provider: 'cartesia'}});
      return {...fallback, routing: {...routing, fallback: {authorized: true, from: 'gemini', to: 'cartesia', triggerCode: safeText(error && (error.failureKind || error.code), 120)}}};
    }
  }
  return {...await synthesizeCartesiaAudioArtifactOperation(context), routing};
}

function degradedVoiceArtifactName(args, tier, requestId) {
  const requested = safeText(args.name || args.fileName || args.title, 220) || ('voice-' + requestId + '.wav');
  const at = requested.lastIndexOf('.');
  const base = at > 0 ? requested.slice(0, at) : requested;
  const extension = at > 0 ? requested.slice(at) : '.wav';
  return base + '.degraded-' + tier + extension;
}

function tierRouteArgs(args, route, requestedTier, degraded, requestId) {
  return {
    ...args,
    provider: route.provider,
    modelId: route.modelId,
    voiceTier: undefined,
    tier: undefined,
    qualityTier: undefined,
    useCase: undefined,
    voiceUseCase: undefined,
    purpose: undefined,
    ...(degraded ? {name: degradedVoiceArtifactName(args, route.tier, requestId)} : {}),
    _voiceTierRequested: requestedTier,
    _voiceTierRendered: route.tier,
  };
}

function safeCanonRerenderRequest(args = {}) {
  return {
    text: typeof args.text === 'string' ? args.text : typeof args.transcript === 'string' ? args.transcript : '',
    segments: Array.isArray(args.segments) ? args.segments : [],
    voiceName: safeText(args.voiceName, 160),
    voiceId: safeText(args.voiceId, 200),
    direction: safeText(args.direction || args.naturalLanguageDirection, 2000),
    acceptedVoice: args.acceptedVoice === true || args.voiceAccepted === true || args.humanAcceptance === 'accepted',
    lockVoice: args.lockVoice === true,
    lockDirection: args.lockDirection === true,
    name: safeText(args.name || args.fileName || args.title, 220),
    parentFolderId: safeText(args.parentFolderId, 220),
    format: safeText(args.format || args.container || 'wav', 20),
    sampleRate: Number(args.sampleRate || 24000),
    pauseMs: Number(args.pauseMs || 0),
  };
}

async function queueCanonRerender(admin, user, args, requestId, degradedResult, reasonCode, tierConfig) {
  const actor = safeText(user && (user.email || user.uid), 320) || 'unknown';
  const queueId = createHash('sha256').update(actor + '\n' + requestId).digest('hex');
  const rerenderRequestId = requestId + '-canon-rerender-v1';
  const entry = {
    schemaVersion: 'home-center.canon-rerender-queue.v1',
    queueId,
    status: 'queued',
    owner: actor,
    originalRequestId: requestId,
    rerenderRequestId,
    requestedTier: 'canon',
    targetProvider: 'gemini',
    targetModelId: voiceTierPolicy.primaryRoute('canon', tierConfig).modelId,
    reasonCode: safeText(reasonCode, 160) || 'canon_quota_fallback',
    preservedRequest: safeCanonRerenderRequest(args),
    preservedVoiceAndDirection: true,
    degradedArtifact: degradedResult ? {fileId: degradedResult.fileId || '', durableRef: degradedResult.durableRef || '', renderedTier: degradedResult.renderedTier || degradedResult.qualityTier || '', byteCount: degradedResult.byteCount || 0, sha256: degradedResult.sha256 || ''} : null,
    overwriteExistingCanon: false,
    nextOperation: {operation: 'tts.synthesize', args: {requestId: rerenderRequestId, voiceTier: 'canon', rerenderQueueId: queueId}},
    createdAtMs: Date.now(),
    updatedAtMs: Date.now(),
  };
  await admin.firestore().collection('voiceCanonRerenderQueue').doc(queueId).set(entry, {merge: true});
  return {queueId, status: 'queued', rerenderRequestId, targetModelId: entry.targetModelId, preservedVoiceAndDirection: true, overwriteExistingCanon: false, statusOperation: {operation: 'tts.canon_rerender_status', args: {queueId}}};
}

async function recordVoiceTierTelemetry(admin, user, requestId, receipt, result) {
  const actor = safeText(user && (user.email || user.uid), 320) || 'unknown';
  const telemetryId = createHash('sha256').update(actor + '\n' + requestId).digest('hex');
  const record = {
    schemaVersion: 'home-center.voice-render-telemetry.v1',
    requestId,
    owner: actor,
    requestedTier: receipt.requestedTier,
    renderedTier: receipt.renderedTier,
    degraded: receipt.degraded,
    canon: receipt.canon,
    provider: safeText(result && result.provider, 40),
    modelId: safeText(result && result.modelId, 160),
    byteCount: Number(result && result.byteCount || 0),
    durationSeconds: Number(result && result.duration || 0),
    attempts: receipt.attempts,
    totalLatencyMs: receipt.attempts.reduce((sum, item) => sum + Number(item.latencyMs || 0), 0),
    estimatedCostUsd: Number(receipt.attempts.reduce((sum, item) => sum + Number(item.estimatedCostUsd || 0), 0).toFixed(8)),
    quotaFallbackCount: receipt.attempts.filter((item) => item.quotaError === true).length,
    transcriptSha256: safeText(result && result.transcriptSha256, 64),
    updatedAtMs: Date.now(),
  };
  await admin.firestore().collection('voiceRenderTelemetry').doc(telemetryId).set(record, {merge: true});
  const {owner: _owner, ...publicRecord} = record;
  return {...publicRecord, telemetryId};
}

async function replaceSuccessfulTierAuditResult(admin, requestId, result, providerSummary) {
  const ref = mcpCollection(admin, 'driveBridgeAudit').doc(stableRequestId(requestId));
  const snap = await ref.get();
  const stored = snap.exists ? snap.data() || {} : {};
  if (!snap.exists || !['success', 'completed'].includes(stored.status)) throw Object.assign(new Error('Tier receipt could not bind to a terminal provider audit.'), {status: 502, failureKind: 'voice_tier_audit_missing'});
  const prior = stored.result || {};
  if ((prior.fileId && prior.fileId !== result.fileId) || (prior.sha256 && prior.sha256 !== result.sha256)) throw Object.assign(new Error('Tier receipt identity did not match the terminal provider audit.'), {status: 502, failureKind: 'voice_tier_audit_identity_mismatch'});
  await ref.set({result, providerSummary: safeText(providerSummary, 1000), updatedAtMs: nowMs()}, {merge: true});
  return {...stored, result: null, providerSummary: safeText(providerSummary, 1000)};
}

async function synthesizeTieredSpeechAudioArtifactOperation(context, tier, tierConfig) {
  const requestId = createRequestId(context.args && context.args.requestId);
  const routes = voiceTierPolicy.downwardRoutes(tier, tierConfig);
  const existing = await existingAudit(context.admin, requestId);
  if (existing && existing.status === 'success' && existing.result) {
    if (existing.result.voiceTier && existing.result.requestedTier) return {...existing.result, idempotent: true, audit: {...existing, result: null}};
    const renderedRoute = routes.find((route) => route.provider === existing.result.provider && route.modelId === existing.result.modelId);
    if (!renderedRoute) throw Object.assign(new Error('Stored provider receipt does not match an authorized route for this voice tier.'), {status: 409, failureKind: 'voice_tier_idempotency_route_mismatch'});
    const attempts = [{tier: renderedRoute.tier, provider: renderedRoute.provider, modelId: renderedRoute.modelId, status: 'reused', code: '', quotaError: false, latencyMs: 0, estimatedCostUsd: 0, costBasis: 'idempotent_replay'}];
    let queue = null;
    const provisional = voiceTierPolicy.tierReceipt({requested: tier, rendered: renderedRoute.tier, config: tierConfig, attempts});
    const decorated = {...existing.result, requestedTier: tier, renderedTier: renderedRoute.tier, qualityTier: renderedRoute.tier, degraded: provisional.degraded, canon: provisional.canon, canonEligible: provisional.canonEligible, overwriteCanonAllowed: false};
    if (tier === 'canon' && renderedRoute.tier !== 'canon') queue = await queueCanonRerender(context.admin, context.user, context.args || {}, requestId, decorated, 'idempotent_degraded_receipt_recovery', tierConfig);
    const receipt = voiceTierPolicy.tierReceipt({requested: tier, rendered: renderedRoute.tier, config: tierConfig, attempts, queue});
    const telemetry = await recordVoiceTierTelemetry(context.admin, context.user, requestId, receipt, decorated);
    const finalResult = {...decorated, voiceTier: receipt, telemetry, routing: {requested: 'tier', selected: renderedRoute.provider, reason: 'voice_tier_policy', tier, modelId: renderedRoute.modelId, fallback: receipt.degraded ? {authorized: true, reason: 'quota_only', downward: true} : null}};
    const audit = await replaceSuccessfulTierAuditResult(context.admin, requestId, finalResult, 'Recovered tier labels for an idempotent verified provider receipt; no provider call was made.');
    return {...finalResult, idempotent: true, audit};
  }
  const locks = voiceTierPolicy.acceptedLocks(context.args || {});
  const attempts = [];
  let lastQuotaError = null;
  for (let index = 0; index < routes.length; index += 1) {
    const route = routes[index];
    if (index > 0) {
      const preservation = voiceTierPolicy.routePreservesLocks(routes[0], route, locks);
      if (!preservation.ok) {
        attempts.push({tier: route.tier, provider: route.provider, modelId: route.modelId, status: 'blocked', code: preservation.reason, quotaError: false, latencyMs: 0, estimatedCostUsd: 0});
        continue;
      }
    }
    const startedAtMs = Date.now();
    try {
      const routeArgs = tierRouteArgs(context.args || {}, route, tier, index > 0, requestId);
      const result = route.provider === 'gemini'
        ? await synthesizeGeminiArtifact({...context, args: routeArgs, helpers: {createRequestId, existingAudit, auditWrite, recordActionAudit, safeDriveFileId}})
        : await synthesizeCartesiaAudioArtifactOperation({...context, args: routeArgs});
      const cost = voiceTierPolicy.estimateCost(route, {duration: result.duration, usage: result.usageEvidence && result.usageEvidence.providerReported && result.usageEvidence.providerReported[0], text: context.args && (context.args.text || context.args.transcript) || ''});
      attempts.push({tier: route.tier, provider: route.provider, modelId: route.modelId, status: 'success', code: '', quotaError: false, latencyMs: Date.now() - startedAtMs, estimatedCostUsd: cost.estimatedUsd, costBasis: cost.basis});
      let queue = null;
      const provisional = voiceTierPolicy.tierReceipt({requested: tier, rendered: route.tier, config: tierConfig, attempts});
      const decorated = {...result, requestedTier: tier, renderedTier: route.tier, qualityTier: route.tier, degraded: provisional.degraded, canon: provisional.canon, canonEligible: provisional.canonEligible, overwriteCanonAllowed: false};
      if (tier === 'canon' && route.tier !== 'canon') queue = await queueCanonRerender(context.admin, context.user, context.args || {}, requestId, decorated, lastQuotaError && (lastQuotaError.failureKind || lastQuotaError.code), tierConfig);
      const receipt = voiceTierPolicy.tierReceipt({requested: tier, rendered: route.tier, config: tierConfig, attempts, queue});
      const telemetry = await recordVoiceTierTelemetry(context.admin, context.user, requestId, receipt, decorated);
      const finalResult = {...decorated, voiceTier: receipt, telemetry, routing: {requested: 'tier', selected: route.provider, reason: 'voice_tier_policy', tier, modelId: route.modelId, fallback: receipt.degraded ? {authorized: true, reason: 'quota_only', downward: true} : null}};
      const providerSummary = 'Synthesized verified ' + route.tier + ' voice artifact through ' + route.provider + '; degraded=' + receipt.degraded + '.';
      await auditWrite(context.admin, {actor: context.user.email || context.user.uid || 'unknown', authKind: context.user.authKind, tool: 'tts.synthesize', operation: 'tts.synthesize', requestId, status: 'success', fileId: finalResult.fileId || '', affectedFileIds: [finalResult.fileId, ...(finalResult.segmentCheckpoints || []).map((item) => item.fileId)].filter(Boolean), callerNote: context.args && context.args.callerNote, providerSummary, result: finalResult, inputSha256: finalResult.transcriptSha256 || '', lease: null});
      await replaceSuccessfulTierAuditResult(context.admin, requestId, finalResult, providerSummary);
      return finalResult;
    } catch (error) {
      const quotaError = voiceTierPolicy.isQuotaError(error);
      attempts.push({tier: route.tier, provider: route.provider, modelId: route.modelId, status: 'failed', code: safeText(error && (error.failureKind || error.code), 160) || 'voice_provider_failed', quotaError, latencyMs: Date.now() - startedAtMs, estimatedCostUsd: 0});
      if (!quotaError) throw error;
      lastQuotaError = error;
    }
  }
  if (tier === 'canon' && lastQuotaError) {
    const queue = await queueCanonRerender(context.admin, context.user, context.args || {}, requestId, null, lastQuotaError.failureKind || lastQuotaError.code, tierConfig);
    lastQuotaError.providerFailure = {...(lastQuotaError.providerFailure || {}), preservedProgress: 'No fallback could preserve accepted voice and direction.', recoveryReference: queue.queueId, safeNextAction: 'Inspect tts.canon_rerender_status and retry the queued canon request later.'};
  }
  throw lastQuotaError || Object.assign(new Error('No configured voice tier route could preserve the accepted voice and direction.'), {status: 503, failureKind: 'voice_tier_no_compatible_route'});
}

async function canonRerenderStatusOperation({admin, user, args = {}}) {
  const queueId = safeText(args.queueId, 160);
  if (!/^[a-f0-9]{64}$/.test(queueId)) throw Object.assign(new Error('queueId must be a 64-character hexadecimal identifier.'), {status: 400, failureKind: 'canon_rerender_queue_id_invalid'});
  const snap = await admin.firestore().collection('voiceCanonRerenderQueue').doc(queueId).get();
  if (!snap.exists) return {ok: false, status: 'missing', queueId};
  const entry = snap.data() || {};
  const actor = safeText(user && (user.email || user.uid), 320);
  if (!actor || safeText(entry.owner, 320).toLowerCase() !== actor.toLowerCase()) throw Object.assign(new Error('Canon rerender queue entry is not owned by this caller.'), {status: 403, failureKind: 'canon_rerender_forbidden'});
  const {preservedRequest, owner, ...publicEntry} = entry;
  return {ok: true, ...publicEntry, preserved: {voiceName: safeText(preservedRequest && preservedRequest.voiceName, 160), voiceId: safeText(preservedRequest && preservedRequest.voiceId, 200), directionSha256: createHash('sha256').update(String(preservedRequest && preservedRequest.direction || '')).digest('hex'), acceptedVoice: Boolean(preservedRequest && preservedRequest.acceptedVoice)}, dialogueStoredPrivately: true};
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


const DROOBIEDOO_CONTEXT_INDEX_PATH = path.join(__dirname, 'context_sources', 'droobiedoo_context_index.json');
const DROOBIEDOO_CONTEXT_OPERATIONS = Object.freeze({
  'droobiedoo.context_health': {summary: 'Read Droobiedoo index health, freshness, relationship, and read-only boundary metadata.', write: false, input: {maxAgeDays: 'optional number'}},
  'droobiedoo.context_search': {summary: 'Search Droobiedoo projects, skills, doctrine, reports, artifacts, and provenance.', write: false, input: {query: 'string', kinds: 'optional string[]', limit: 'optional number', maxAgeDays: 'optional number'}},
  'droobiedoo.project_resolve': {summary: 'Resolve a project or workspace context name to Droobiedoo evidence and related entries.', write: false, input: {query: 'string', limit: 'optional number', maxAgeDays: 'optional number'}},
  'droobiedoo.task_context_packet': {summary: 'Build a bounded read-only task context packet from Droobiedoo evidence with provenance and invention guards.', write: false, input: {query: 'string', limit: 'optional number', maxChars: 'optional number', maxAgeDays: 'optional number'}},
  'droobiedoo.skill_match': {summary: 'Find Droobiedoo skills that match a task or project query.', write: false, input: {query: 'string', limit: 'optional number', maxAgeDays: 'optional number'}},
  'droobiedoo.artifact_search': {summary: 'Search Droobiedoo reports, generated artifacts, backups, and tool artifacts.', write: false, input: {query: 'string', limit: 'optional number', maxAgeDays: 'optional number'}},
  'droobiedoo.provenance_lookup': {summary: 'Look up Droobiedoo provenance by path, id, or lexical query.', write: false, input: {path: 'optional string', id: 'optional string', query: 'optional string', limit: 'optional number', maxAgeDays: 'optional number'}},
});

function droobiedooContextOperationEntries() {
  return DROOBIEDOO_CONTEXT_OPERATIONS;
}

function loadDroobiedooContextIndex() {
  const raw = fs.readFileSync(DROOBIEDOO_CONTEXT_INDEX_PATH, 'utf8');
  const index = JSON.parse(raw);
  if (index.schemaVersion !== 'droobiedoo.context-index.v1') {
    throw Object.assign(new Error('Unsupported Droobiedoo context index schema.'), {status: 500});
  }
  return index;
}

function droobiedooNowMs(args = {}) {
  const override = safeNumber(args.nowMs, 0);
  return override > 0 ? override : Date.now();
}

function droobiedooFreshness(index, args = {}) {
  const generatedAt = safeText(index.generatedAt || (index.freshness && index.freshness.generatedAt), 80);
  const generatedMs = generatedAt ? Date.parse(generatedAt) : 0;
  const maxAgeDays = Math.max(0, Math.min(3650, safeNumber(args.maxAgeDays, index.freshness && index.freshness.maxAgeDays ? index.freshness.maxAgeDays : 14)));
  const ageMs = generatedMs ? Math.max(0, droobiedooNowMs(args) - generatedMs) : Number.POSITIVE_INFINITY;
  const maxAgeMs = maxAgeDays * 24 * 60 * 60 * 1000;
  const staleReasons = [];
  if (!generatedMs) staleReasons.push('missing-generatedAt');
  if (ageMs > maxAgeMs) staleReasons.push('generatedAt-older-than-maxAgeDays');
  const warnings = Array.isArray(index.freshness && index.freshness.warnings) ? index.freshness.warnings.map((w) => safeText(w, 500)).filter(Boolean) : [];
  if (index.git && index.git.dirty) warnings.push('Droobiedoo source had local changes when indexed.');
  return {
    generatedAt,
    ageDays: Number.isFinite(ageMs) ? Number((ageMs / (24 * 60 * 60 * 1000)).toFixed(4)) : null,
    maxAgeDays,
    isStale: staleReasons.length > 0,
    staleReasons,
    sourceHead: safeText(index.git && index.git.head, 120) || safeText(index.freshness && index.freshness.sourceHead, 120),
    sourceBranch: safeText(index.git && index.git.branch, 120),
    sourceDirty: !!(index.git && index.git.dirty),
    warnings: [...new Set(warnings)].slice(0, 20),
  };
}

function droobiedooTokens(value) {
  return safeText(value, 20000).toLowerCase().split(/[^a-z0-9_.-]+/).filter((token) => token.length >= 2);
}

function droobiedooEntryHaystack(entry) {
  return [entry.id, entry.kind, entry.title, entry.path, entry.skillName, entry.summary, ...(Array.isArray(entry.tags) ? entry.tags : [])].map((part) => safeText(part, 3000).toLowerCase()).join(' ');
}

function droobiedooScoreEntry(entry, queryTokens) {
  if (!queryTokens.length) return 1;
  const haystack = droobiedooEntryHaystack(entry);
  let score = 0;
  for (const token of queryTokens) {
    if (!haystack.includes(token)) continue;
    score += 1;
    const title = safeText(entry.title, 300).toLowerCase();
    const entryPath = safeText(entry.path, 500).toLowerCase();
    if (title.includes(token)) score += 3;
    if (entryPath.includes(token)) score += 2;
    if ((entry.kind || '') === token) score += 2;
  }
  return score;
}

function droobiedooResultEntry(entry) {
  return {
    id: entry.id,
    kind: entry.kind,
    title: entry.title,
    path: entry.path,
    tags: entry.tags || [],
    skillName: entry.skillName || '',
    summary: safeText(entry.summary, 900),
    sha256: entry.sha256,
    sizeBytes: entry.sizeBytes,
    modifiedTime: entry.modifiedTime,
    readOnly: entry.readOnly !== false,
    remoteCallable: entry.remoteCallable !== false,
    provenance: entry.provenance || null,
    remoteExposure: entry.remoteExposure || null,
  };
}

function searchDroobiedooContextIndex(index, args = {}) {
  const query = safeText(args.query || args.project || args.task || '', 1200);
  const queryTokens = droobiedooTokens(query);
  const kinds = Array.isArray(args.kinds) ? new Set(args.kinds.map((kind) => safeText(kind, 80)).filter(Boolean)) : null;
  const limit = chatGptLimit(args.limit, 10, 50);
  return (Array.isArray(index.entries) ? index.entries : [])
    .filter((entry) => !kinds || kinds.has(entry.kind))
    .map((entry) => ({entry, score: droobiedooScoreEntry(entry, queryTokens)}))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || safeText(a.entry.path, 500).localeCompare(safeText(b.entry.path, 500)))
    .slice(0, limit)
    .map((item) => ({score: item.score, ...droobiedooResultEntry(item.entry)}));
}

function droobiedooContextHealth(index, args = {}) {
  return {
    schemaVersion: index.schemaVersion,
    sourceRepo: index.sourceRepo,
    generatedAt: index.generatedAt,
    counts: index.counts || {},
    readOnly: index.readOnly !== false,
    remoteMutationAllowed: !!index.remoteMutationAllowed,
    forbiddenRemoteTools: Array.isArray(index.forbiddenRemoteTools) ? index.forbiddenRemoteTools : [],
    freshness: droobiedooFreshness(index, args),
    relationships: index.relationships || {},
    operationPrefix: 'droobiedoo.',
  };
}

function droobiedooTaskContextPacket(index, args = {}) {
  const maxChars = Math.max(1000, Math.min(24000, safeNumber(args.maxChars, 8000)));
  const query = safeText(args.query || args.task || args.prompt || '', 1200);
  const matches = searchDroobiedooContextIndex(index, {...args, query, limit: chatGptLimit(args.limit, 12, 30)});
  const grouped = {};
  let usedChars = 0;
  const selected = [];
  for (const match of matches) {
    const cost = JSON.stringify(match).length;
    if (usedChars + cost > maxChars && selected.length) continue;
    usedChars += cost;
    selected.push(match);
    if (!grouped[match.kind]) grouped[match.kind] = [];
    grouped[match.kind].push(match);
  }
  return {
    source: 'droobiedoo',
    query,
    readOnly: true,
    remoteMutationAllowed: false,
    freshness: droobiedooFreshness(index, args),
    relationships: index.relationships || {},
    guards: [
      'Use Droobiedoo as context and provenance only.',
      'Do not expose or call scripts/sync_workspace_artifacts.py as a remote mutation tool.',
      'Use Home Center or Command Center for execution; Droobiedoo does not dispatch work.',
      'Use She-Raw as the consultative runtime/default voice when a voice is needed.',
    ],
    groupedEntries: grouped,
    entries: selected,
    provenance: selected.map((entry) => ({path: entry.path, sha256: entry.sha256, sourceRepo: entry.provenance && entry.provenance.sourceRepo})),
  };
}

function runDroobiedooContextOperation(operation, args = {}) {
  const index = loadDroobiedooContextIndex();
  if (operation === 'droobiedoo.context_health') return droobiedooContextHealth(index, args);
  if (operation === 'droobiedoo.context_search') return {query: safeText(args.query, 1200), freshness: droobiedooFreshness(index, args), results: searchDroobiedooContextIndex(index, args)};
  if (operation === 'droobiedoo.project_resolve') return {query: safeText(args.query || args.project, 1200), freshness: droobiedooFreshness(index, args), results: searchDroobiedooContextIndex(index, {...args, query: args.query || args.project, kinds: ['project', 'doctrine', 'report', 'artifact']})};
  if (operation === 'droobiedoo.task_context_packet') return droobiedooTaskContextPacket(index, args);
  if (operation === 'droobiedoo.skill_match') return {query: safeText(args.query || args.task, 1200), freshness: droobiedooFreshness(index, args), results: searchDroobiedooContextIndex(index, {...args, query: args.query || args.task, kinds: ['skill']})};
  if (operation === 'droobiedoo.artifact_search') return {query: safeText(args.query, 1200), freshness: droobiedooFreshness(index, args), results: searchDroobiedooContextIndex(index, {...args, kinds: ['artifact', 'report', 'provenance', 'tool']})};
  if (operation === 'droobiedoo.provenance_lookup') {
    const entries = Array.isArray(index.entries) ? index.entries : [];
    const id = safeText(args.id, 300);
    const requestedPath = safeText(args.path, 1000);
    let results = [];
    if (id || requestedPath) {
      results = entries.filter((entry) => (!id || entry.id === id) && (!requestedPath || entry.path === requestedPath)).slice(0, chatGptLimit(args.limit, 10, 50)).map(droobiedooResultEntry);
    } else {
      results = searchDroobiedooContextIndex(index, {...args, kinds: null});
    }
    return {query: safeText(args.query || requestedPath || id, 1200), freshness: droobiedooFreshness(index, args), results};
  }
  throw Object.assign(new Error('Unsupported Droobiedoo context operation: ' + operation), {status: 400});
}

function tvtroperOperationEntries() {
  return {
    tvtroper_operation: {
      summary: 'Search the deployed GCS-backed RyokoExtra/TvTroper corpus or fetch one exact full record through the stable drive_operation dispatcher.',
      write: false,
      requiresRequestId: false,
      input: {operation: 'status|search|get', args: 'search: {query, limit?}; get: {record_id returned by search}'},
      output: {operation: 'status|search|get', registryVersion: TVTROPER_OPERATION_REGISTRY_VERSION, gcsOnly: true, result: 'provider health, search results, or exact full HTML record with archive provenance'},
      agentRecipe: {
        whenUserSays: 'Search TV Tropes or read a complete TVTroper corpus record.',
        prefer: 'Call drive_operation with operation=tvtroper_operation and nested args.operation=search, then call it again with nested args.operation=get and the exact returned record_id.',
        verification: 'A search snippet is not record-level proof. Fetch the exact returned record_id and verify the full HTML and archive provenance.',
      },
    },
  };
}

function driveOperationRegistry() {
  return {
    version: HOME_CENTER_REGISTRY_VERSION,
    invocationTool: 'drive_operation',
    cachePolicy: 'New bridge and simulation operations should be invokable through drive_operation so ChatGPT does not need a top-level MCP tool refresh for every backend code change. Cartesia TTS is a direct Home Center MCP provider operation; it must not be routed through Command Center jobs or workers.',
    operations: {
      'time.now': {summary: 'Return the current Home Center runtime time.', write: false, requiredScopes: [], input: {}},
      'security.identity_status': {summary: 'Read owner-only revocation status for an identity explicitly blocked by Home Center policy.', write: false, requiredScopes: [], input: {email: 'blocked Home Center email'}},
      'security.revoke_identity': {summary: 'Owner-only fail-closed revocation of every Home Center credential, membership, delegated token, and paired phone device for an identity explicitly blocked by policy.', write: true, requiresRequestId: true, requiredScopes: [], input: {email: 'blocked Home Center email', approved: 'boolean true', requestId: 'string'}},
      ...artifactOperationEntries(),
      ...tvtroperOperationEntries(),
      ...blenderWorkspaceOperationEntries(),
      ...filesystemOperationEntries(),
      'artifact.delivery.materialize_receipt': {
        summary: 'Materialize supported artifacts named by one owner-scoped terminal producer receipt as hash-verified private Drive resource links without rerendering or changing human acceptance.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {producerReceiptId: 'string; receipt only, never a GCS path or URL', producerKind: 'optional artifact_transport|storage_ingest|drive_audit|blender_workspace|foundry_historical', artifactNames: 'optional artifact role or filename array', artifactMetadata: 'optional exact SHA-256/name/MIME entries; required only when a verified receipt preserved generic artifact.bin metadata', parentFolderId: 'optional string', requestId: 'string'},
        output: {status: 'review_ready after source and Drive readback verification', transportState: 'bytes transferred/reused, concurrency, and no-rerender evidence', authorization: 'owner_scoped', humanAcceptance: 'preserved separately and never changed', artifacts: 'bounded private Drive resource links with SHA-256 and byte length'},
      },
      'artifact.review.record': {
        summary: 'Record an owner-scoped human verdict for one review-ready delivery while preserving the candidate and requiring a concrete fix-forward plan for rejection.',
        write: true,
        requiresRequestId: true,
        input: {deliveryRequestId: 'string', verdict: 'accepted|rejected|revision_requested|unreviewed', reason: 'required for rejection or revision', successorPlan: 'required operation, idempotencyKey, and concrete changes for rejection or revision', simplificationEvidence: 'optional 1-64 validated remove_or_merge comparisons; required by hard-surface promotion', requestId: 'string'},
      },
      'artifact.review.link_successor': {
        summary: 'Link a rejected or revision-requested review record to a distinct owner-scoped terminal corrective producer receipt.',
        write: true,
        requiresRequestId: true,
        input: {reviewRequestId: 'string', successorReceiptId: 'string', producerKind: 'optional artifact_transport|storage_ingest|drive_audit|blender_workspace|foundry_historical', artifactNames: 'optional artifact selectors', requestId: 'string'},
      },
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
      drive_read_binary_chunk: {
        summary: 'Read one bounded byte range from a non-Google Drive file without coercing binary bytes to text.',
        write: false,
        requiresRequestId: false,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {fileId: 'string', offset: 'optional nonnegative integer, default 0', length: 'optional integer 1-262144, default 131072'},
        output: {fileId: 'string', name: 'string', mimeType: 'string', offset: 'number', byteCount: 'number', totalSize: 'number', nextOffset: 'number or null', eof: 'boolean', chunkBase64: 'string', chunkSha256: 'string'},
        agentRecipe: {
          whenUserSays: 'Recover, download, mux, inspect, or locally materialize a Drive-hosted binary artifact such as Cartesia audio.',
          prefer: 'Call drive_operation repeatedly with operation=drive_read_binary_chunk, preserving nextOffset until eof=true, then decode and concatenate the bounded Base64 chunks in order.',
          verification: 'Verify every chunkSha256 before append and verify final byte count against totalSize. Never substitute another synthesis provider because binary transfer failed.',
        },
      },
      drive_text_patch: {
        summary: 'Patch bounded UTF-8 bytes in place on an existing stored Drive file with expected SHA-256, exact or marker-bounded replacements, protected-region invariants, audit, and whole-file readback verification.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {fileId: 'string', expectedSha256: '64-char SHA-256', expectedMimeType: 'optional MIME type', approved: 'boolean true', replacements: 'array of exact|between patch objects', protectedRegions: 'optional marker-region array', requestId: 'string', callerNote: 'optional string'},
      },
      drive_binary_read_begin: {
        summary: 'Open an owner-bound, hash-verified read session for one stored Drive binary without changing the top-level MCP catalog.',
        write: false,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {fileId: 'string', requestId: 'stable session id', chunkSize: 'optional integer 1-262144, default 131072'},
        output: {requestId: 'string', source: 'immutable Drive metadata snapshot', fileSha256: 'whole-file SHA-256', chunkSize: 'number', chunkCount: 'number', verifiedSource: 'true'},
      },
      drive_binary_read_chunk: {
        summary: 'Read one indexed chunk from a verified Drive binary session and persist its bounded progress receipt.',
        write: false,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {requestId: 'binary read session id', chunkIndex: 'integer from 0 to chunkCount-1'},
        output: {requestId: 'string', chunkIndex: 'number', offset: 'number', byteCount: 'number', chunkSha256: 'string', chunkBase64: 'string', nextChunkIndex: 'number or null', eof: 'boolean'},
      },
      drive_binary_read_status: {
        summary: 'Resume a Drive binary read by reporting served and missing chunk indexes after verifying the source snapshot is unchanged.',
        write: false,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {requestId: 'binary read session id'},
        output: {servedChunks: 'ordered integer array', missingChunks: 'ordered integer array', servedCount: 'number', remainingCount: 'number', verifiedSource: 'true'},
      },
      drive_binary_read_complete: {
        summary: 'Complete a Drive binary read only after every chunk was served and reconstructed byte count/SHA-256 match a fresh whole-file readback.',
        write: false,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {requestId: 'binary read session id', reconstructedByteCount: 'integer', reconstructedSha256: '64-character SHA-256 hex'},
        output: {verified: 'true', reconstructedByteCount: 'number', reconstructedSha256: 'string', readbackByteCount: 'number', readbackSha256: 'string', completedAt: 'ISO timestamp'},
        agentRecipe: {
          whenUserSays: 'Download, recover, or locally reconstruct a complete stored Drive binary.',
          prefer: 'Begin once, fetch missing chunk indexes in order, verify each chunk SHA-256 before append, resume from status after interruption, then complete with the reconstructed whole-file identity.',
          verification: 'Accept only complete.verified=true with matching reconstructed and final Drive readback byte counts and SHA-256 values.',
        },
      },
      'sites.source_version.materialize_drive': {
        summary: 'Clone one exact saved Sites source commit through its short-lived repository credential, materialize the complete editable tree into a Drive folder, verify every file by byte-count/SHA-256 readback, and write a provenance manifest without retaining the credential.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {projectId: 'opaque Sites project id', versionId: 'opaque saved Sites version id', versionNumber: 'user-facing version number', repositoryUrl: 'uncredentialed git.chatgpt-team.site HTTPS URL', repositoryToken: 'short-lived Sites source repository token; never persisted or returned', sourceBranch: 'optional branch, default main', sourceCommit: 'exact 40-character commit SHA', expectedSourceFileCount: 'optional exact tracked source file count', parentFolderId: 'Drive destination parent folder id', folderName: 'Drive source-folder name', archiveFormat: 'optional provider-reported saved archive format', sedimentFileId: 'optional opaque provider archive id', archiveContentHash: 'optional provider-reported saved archive hash', archiveFileCount: 'optional provider-reported saved archive file count', archiveSizeBytes: 'optional provider-reported saved archive bytes', approved: 'must be true', requestId: 'stable idempotency key', callerNote: 'optional string'},
        output: {rootFolderId: 'Drive folder id', sourceCommit: 'verified commit', sourceFileCount: 'tracked source files', verifiedSourceFileCount: 'files passing Drive byte/SHA-256 readback', aggregateSha256: 'canonical path/mode/file-hash manifest digest', manifestFileId: 'SOURCE_PROVENANCE.json Drive id', credentialPersisted: 'always false', credentialReturned: 'always false'},
        agentRecipe: {
          whenUserSays: 'Export, recover, or materialize an exact Sites source version into Drive.',
          prefer: 'Resolve the exact project/version through Sites, obtain a fresh short-lived source repository credential, then call this operation once with its exact commit and Drive destination. Never copy or log the credential elsewhere.',
          verification: 'Require exact commit match, expected source count when known, everyFileReadbackVerified=true, matching verifiedSourceFileCount/sourceFileCount, and a readable SOURCE_PROVENANCE.json manifest.',
        },
      },
      'drive.share_folder': {
        summary: 'Share one existing Google Drive folder with one explicit email recipient, then verify the recipient and effective role by permission-list readback.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {folderId: 'Google Drive folder id', email: 'explicit recipient email', role: 'optional reader|commenter|writer, default reader', sendNotificationEmail: 'optional boolean, default true', emailMessage: 'optional notification message', approved: 'must be true', requestId: 'stable idempotency key', callerNote: 'optional string'},
        output: {folderId: 'string', email: 'normalized recipient', requestedRole: 'string', permission: 'verified Drive permission', verified: 'boolean', reused: 'boolean', upgraded: 'boolean'},
        agentRecipe: {
          whenUserSays: 'Share a Drive folder with a named email recipient.',
          prefer: 'Resolve and verify the exact folder first, preserve the explicit recipient address, use the least role that fulfills the request, and call with approved=true.',
          verification: 'Require verified=true and a permission readback whose emailAddress and role satisfy the request. A successful create response without list readback is not delivery.',
        },
      },
      'audio.ingest_drive': {
        summary: 'Stream one Drive-hosted audio file into canonical generated storage, verify source and GCS readback bytes/SHA-256, and write append-safe bucket indexes without mutating Drive.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {fileId: 'string', batchId: 'required stable migration batch id', requestId: 'string', approved: 'must be true', objectName: 'optional deterministic audio/ object name', project: 'optional string', stage: 'optional sources|finals|parts|probes|rejected|unclassified', sourcePath: 'optional original Drive path', expectedSize: 'optional integer', expectedDriveMd5: 'optional Drive MD5 hex', ownerEmail: 'optional owner override; defaults authenticated user', sharedWith: 'optional email array', sourceKind: 'required for sources: foley_recording|generated|licensed|public_domain|unknown', creator: 'required for sources', rightsBasis: 'required for sources: self_recorded|commissioned|licensed|public_domain|unknown', captureDevice: 'optional string', captureApp: 'optional string', recordedAt: 'optional ISO timestamp', annotationStatus: 'optional embedded_spoken_labels_unparsed|unlabeled|partial|cataloged', semanticAuthority: 'optional source_audio|creator_notes|catalog_review|unknown', sourceNotes: 'optional bounded string'},
        output: {verified: 'boolean', reused: 'boolean', source: 'Drive id/name/size/MD5/path', destination: 'bucket/object/gs URI/size/SHA-256/metadata', sourceMetadata: 'immutable provenance and annotation state for source-stage audio', indexes: 'immutable by-drive-id, owner/project/stage catalog, and batch-item JSON receipts', readback: 'byte count/SHA-256', driveMutated: 'false'},
        agentRecipe: {
          whenUserSays: 'Ingest, backfill, or migrate an existing Drive audio artifact into the canonical generated-audio bucket.',
          prefer: 'Call drive_operation once per file with operation=audio.ingest_drive, approved=true, a stable batchId/requestId, and explicit project/stage/sourcePath metadata. Keep Drive untouched until the batch is sealed and a later human-approved cleanup manifest exists.',
          verification: 'Require verified=true, matching source and GCS byte counts/SHA-256, a canonical gs:// receipt, and all three bucket index receipts. Never trash Drive in the ingest call.',
        },
      },
      'audio.finalize_ingest_batch': {
        summary: 'Seal a migration batch from its verified bucket item indexes and fail closed unless expected file IDs, count, and bytes match exactly.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {batchId: 'stable migration batch id', requestId: 'string', approved: 'must be true', expectedFileIds: 'exact nonempty Drive file id array', expectedCount: 'exact positive integer', expectedBytes: 'exact positive integer'},
        output: {sealed: 'boolean', verified: 'boolean', batchId: 'string', itemCount: 'number', byteCount: 'number', manifest: 'immutable bucket JSON receipt', driveTrashEligible: 'false'},
        agentRecipe: {
          whenUserSays: 'Verify, reconcile, or seal a Drive-to-bucket audio migration batch.',
          prefer: 'Call only after every audio.ingest_drive receipt is verified. Pass the exact Drive inventory IDs, count, and bytes.',
          verification: 'Treat a sealed manifest as load-integrity evidence only. Playback acceptance and explicit human approval are still required before any Drive trash action.',
        },
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
      'armory.receipt': {
        summary: 'Record one or more immutable, owner-scoped Armory Range casings. The tracked item needs no pre-existing cloud key, and every casing receives a mandatory ISO timestamp.',
        write: true,
        requiresRequestId: false,
        requiredScopes: [],
        input: {ammunition: 'required label; item or subject aliases accepted', count: 'optional integer 1-500, default 1', action: 'optional string, default fired', unit: 'optional string, default round', timestamp: 'optional explicit timestamp shared by every casing', timestamps: 'optional array containing one timestamp or exactly one per casing', timezone: 'optional IANA timezone, default America/Chicago', attributes: 'optional object', note: 'optional string', requestId: 'optional exact-replay receipt; generated when omitted'},
        output: {receiptId: 'string', requestId: 'string', count: 'number', casingIds: 'one immutable event id per unit', timestamps: 'mandatory ISO timestamp per casing', timestampSources: 'explicit, explicit_shared, or server_receipt', recordedAt: 'ISO server receipt time', inputSha256: 'exact replay binding'},
        agentRecipe: {
          whenUserSays: 'Armory receipt, record in the armory, or describes a count of items or rounds to record.',
          prefer: 'Call drive_operation with operation=armory.receipt. Parse ammunition/item, count, action, and any explicitly spoken times. If no time is spoken, omit timestamps so the server records the mandatory receipt time honestly.',
          verification: 'Read back count, timestamps, timestampSources, and idempotent. Never invent spacing between events.',
        },
      },
      'armory.recount': {
        summary: 'Aggregate owner-scoped Armory Range casings by item, action, and unit.',
        write: false,
        requiresRequestId: false,
        requiredScopes: [],
        input: {ammunition: 'optional exact item filter; item or subject aliases accepted', action: 'optional exact action filter', since: 'optional timestamp', until: 'optional timestamp'},
        output: {totalCasings: 'number', recount: 'grouped counts', lastCasing: 'latest matching immutable event or null'},
        agentRecipe: {
          whenUserSays: 'Armory recount or asks how many matching things have been recorded.',
          prefer: 'Call drive_operation with operation=armory.recount and only the filters the user supplied.',
          verification: 'Report the aggregate and the matching time boundary without guessing missing filters.',
        },
      },
      'armory.casing': {
        summary: 'Retrieve recent owner-scoped Armory Range casings, including the last matching event.',
        write: false,
        requiresRequestId: false,
        requiredScopes: [],
        input: {ammunition: 'optional exact item filter; item or subject aliases accepted', action: 'optional exact action filter', since: 'optional timestamp', until: 'optional timestamp', lastOnly: 'optional boolean', limit: 'optional integer 1-100, default 10'},
        output: {count: 'number', lastCasing: 'latest matching immutable event or null', casings: 'newest-first matching events'},
        agentRecipe: {
          whenUserSays: 'Armory casing, what was my last shot fired in the range, or asks for recent matching events.',
          prefer: 'Call drive_operation with operation=armory.casing. For last-shot questions use action=fired and lastOnly=true.',
          verification: 'Read back ammunition/item, action, occurredAt, and timestampSource.',
        },
      },
      'tts.voices': {
        summary: 'List or search Cartesia and Gemini TTS voices through Home Center MCP with TTL, cache age, and visibly stale provider state; no Command Center job or worker is involved.',
        write: false,
        requiredScopes: [],
        input: {provider: 'optional auto, cartesia, or gemini; auto returns both provider catalogs', forceRefresh: 'optional boolean to refresh live capability state', query: 'optional string passed to Cartesia q', q: 'optional alias for query', limit: 'optional number, 1-100 per Cartesia page', pageToken: 'optional alias for starting_after', startingAfter: 'optional Cartesia pagination cursor', endingBefore: 'optional Cartesia pagination cursor', language: 'optional Cartesia language or locale filter such as ru or en_GB', locale: 'optional language-locale alias passed as language', gender: 'optional masculine, feminine, or gender_neutral', isOwner: 'optional boolean', accent: 'optional metadata filter applied to returned provider page', country: 'optional metadata filter applied to returned provider page', includePreviewUrl: 'optional boolean, defaults true'},
        output: {provider: 'auto|cartesia|gemini', catalog: 'provider_live or official_voice_catalog_plus_live_model_probe', filters: 'object', supportedFilters: 'object', pagination: 'object', voices: 'array with id/name/language/locale/gender/accent/country/metadata'},
      },
      'tts.tier_policy': {
        summary: 'Read the deployed config-driven utility, draft, and canon voice-render policy, model routes, cost assumptions, and downward-only safeguards.',
        write: false,
        requiredScopes: [],
        input: {},
        output: {schemaVersion: 'string', revision: 'string', configSha256: 'string', hierarchy: 'utility,draft,canon', tiers: 'resolved provider/model routes', safeguards: 'quota-only downward fallback, degraded/canon and voice-lock rules'},
      },
      'tts.canon_rerender_status': {
        summary: 'Inspect one owner-scoped queued canon rerender without exposing stored dialogue or starting a paid provider call.',
        write: false,
        requiredScopes: [],
        input: {queueId: '64-character queue receipt id'},
        output: {ok: 'boolean', status: 'queued|completed|missing', targetProvider: 'gemini', targetModelId: 'configured Gemini Pro TTS model', preserved: 'voice and direction hash evidence'},
      },
      'audio.render': {
        summary: 'Render deterministic procedural, source-backed, or direct Cartesia or Gemini speech audio inside Home Center MCP through a declarative JSON recipe. Completion requires verified GCS bytes, server-derived owner registration, authenticated Audio Reader discovery, and a bounded playback probe; human acceptance remains unreviewed. It never creates a Command Center job, Codex execution, LLM prompt, GitHub Actions renderer, or Termux runtime process.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {scriptText: 'required JSON audio recipe DSL; no imports, network, shell, process, filesystem, or arbitrary code execution; supports speech, audition, speech_sequence, and block_mix nodes; speech nodes accept voiceTier=utility|draft|canon or useCase=ui|captions|audition|dialogue|final_performance plus acceptedVoice/lockDirection; legacy provider-explicit callers remain supported', sources: 'optional object binding friendly names to inline contentBase64 or drive:// refs; WAV sources decode to clips', settings: 'optional deterministic renderer settings including seed, sampleRate, timeoutMs, allowClipping, speechDefaults, speechConcurrency', returnInlineAudio: 'optional boolean; defaults true for small audio, set false for long-form responses so durable resource links remain authoritative', idempotencyKey: 'string alias for requestId', requestId: 'string', parentFolderId: 'optional Drive folder id', callerNote: 'optional string'},
        output: {ok: 'true only after canonical Reader registration', status: 'completed|registration_required', renderer: 'home-center-deterministic-audio-v1', primaryOutput: 'verified canonical GCS audio identity', readerRegistration: 'owner-scoped catalog, discovery, playback probe, and byte-preservation evidence', humanAcceptance: 'unreviewed until a separate human verdict', speech: 'bounded provider-explicit Cartesia or Gemini provenance when speech nodes exist', outputs: 'verified artifact identities', manifest: 'verified JSON manifest artifact', noAgentRuntime: 'true'},
        agentRecipe: {
          whenUserSays: 'Render procedural sound effects, ambience, foley, layered audio beds, stems, waveform, or spectrogram directly from ChatGPT.',
          prefer: 'Call drive_operation with operation=audio.render. Keep scriptText as the Home Center JSON audio DSL; use voiceTier or useCase for utility, draft, and canon policy routing, or an explicit provider for legacy-compatible direct routing. Do not use Command Center, Codex, workers, GitHub Actions, or a newly exposed top-level MCP tool.',
          verification: 'Treat success as authoritative only when ok=true/status=completed and readerRegistration proves unchanged bytes, owner-scoped discovery, and playback. Mechanical completion never means human approval.',
        },
      },
      'audio.reader_link': {
        summary: 'Link one verified owner-scoped Drive audio index into an existing Audio Reader project/stage without copying bytes, mutating Drive, rerendering, changing human acceptance, or removing the original catalog record.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {fileId: 'required existing verified Drive audio file id', requestId: 'stable idempotency/audit id', approved: 'must be true', project: 'target existing Reader project', stage: 'target existing Reader stage'},
        output: {status: 'linked', catalog: 'owner-scoped target catalog projection and reuse state', discovery: 'authenticated Reader folder/item proof', playback: 'bounded header proof', transport: 'zero-copy/no-render/no-Drive-mutation evidence', bytePreservation: 'unchanged immutable identity'},
      },
      'audio.render_register': {
        summary: 'Recover authenticated Audio Reader registration for the primary playable output of an owner-scoped terminal audio.render receipt. This operation never rerenders, calls Cartesia, copies to Drive, exposes the object publicly, or changes human acceptance.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {requestId: 'required owner-scoped terminal audio.render receipt id; arbitrary GCS paths and URLs are forbidden'},
        output: {status: 'completed', execution: 'registration_only', registration: 'byte-preserving owner-scoped catalog, discovery, and playback evidence', humanAcceptance: 'unreviewed', idempotent: 'true on exact replay'},
      },
      'audio.render_artifacts': {
        summary: 'Read back audio.render durable artifact refs through Home Center MCP Google OAuth, verify byte count/SHA-256 against expected receipt metadata, and return redacted container/header evidence. This is the direct verifier for ChatGPT-side acceptance and does not expose Drive OAuth tokens or signed URLs.',
        write: false,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {artifactRefs: 'array of drive:// refs returned by audio.render', expected: 'optional array with durableRef/ref, byteCount, and sha256 values from the render receipt', decodeCheck: 'optional boolean; when true Home Center decodes WAV directly and encoded audio with deployed FFmpeg after authorized Drive readback'},
        output: {ok: 'boolean', artifactCount: 'number', decodeCheck: 'boolean', artifacts: 'array with name, MIME, byteCount, sha256, match booleans, WAV/OGG/PNG header evidence, and optional decodeCheck evidence'},
      },
      'audio.render_status': {
        summary: 'Read the idempotency/audit status for an audio.render request without invoking Cartesia, writing Drive, Command Center, Codex, workers, or agents. Use after a client timeout before retrying long-form speech.',
        write: false,
        requiredScopes: [],
        input: {requestId: 'audio.render idempotency key / requestId'},
        output: {ok: 'boolean', status: 'missing|running|completed|failed', requestId: 'string', result: 'completed receipt when available'},
      },
      'sfx.analyze_source': {
        summary: 'Verify one immutable canonical SFX source, decode a hashed PCM working descendant, measure EBU R128/BS.1770 loudness and true peak, detect transient candidates, and publish waveform/spectrogram/analysis evidence without replacing the source or calling a speech provider.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {sourceRef: 'immutable canonical gs:// audio ref', expectedSha256: 'required immutable parent SHA-256', requestId: 'stable idempotency key', approved: 'must be true for execution authorization; never artistic acceptance', family: 'SFX family name'},
        output: {source: 'verified immutable parent receipt', decode: 'hashed PCM16 WAV working descendant', measurements: 'sample metrics plus EBU R128/ITU-R BS.1770 evidence', transientAnalysis: 'ordered mechanical candidates', artifacts: 'verified GCS descendants', humanAcceptance: 'always unreviewed'},
      },
      'sfx.transcribe_slate': {
        summary: 'Create a hashed 16 kHz mono FLAC descendant and use Google Cloud Speech-to-Text through project identity to return word-timestamped spoken-slate evidence without rerunning mechanical analysis.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {sourceRef: 'immutable canonical gs:// audio ref', expectedSha256: 'required immutable parent SHA-256', requestId: 'stable idempotency key', approved: 'execution authorization only', family: 'SFX family name', transcription: 'optional object with languageCode, model, and explicit phrase hints'},
        output: {source: 'verified immutable parent receipt', recognitionInput: 'hashed FLAC working descendant and recipe', transcription: 'Google Cloud segments, words, confidence, timestamps, and provenance', artifacts: 'verified descendants', humanAcceptance: 'always unreviewed'},
      },
      'sfx.segment': {
        summary: 'Turn an ordered human-readable event manifest into immutable-parent raw cuts, conservative cleaned dry cuts, rejected cuts, component categories, and separate impact-only and bag-movement review reels.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {sourceRef: 'immutable canonical gs:// audio ref', expectedSha256: 'required immutable parent SHA-256', requestId: 'stable idempotency key', approved: 'execution authorization only', family: 'SFX family name', sourceMechanism: 'fixtureType/floorCoupled evidence; floor-standing sources reject hanging-bag semantics', events: 'ordered event manifest with spokenLabelTimeRange, impactTimeRange, and explicit impact or bag-movement eventType'},
        output: {parent: 'immutable source lineage', sourceMechanism: 'normalized fixture evidence', events: 'per-event raw/clean/rejected receipts, domains, and recipes', eventManifest: 'verified manifest', artifacts: 'verified descendants including separate impact and bag-rocking reels', humanAcceptance: 'always unreviewed'},
      },
      'sfx.render': {
        summary: 'Render deterministic impact-only, bag-movement, or explicit composite SFX candidates from named physical source regions and semantic controls. Reject fixture-incompatible layers and clone families.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {sourceRef: 'immutable canonical gs:// audio ref', expectedSha256: 'required immutable parent SHA-256', requestId: 'stable idempotency key', approved: 'execution authorization only', family: 'SFX family name', sourceMechanism: 'fixtureType/floorCoupled evidence', recipe: 'versioned candidate recipe; every candidate declares outputKind and named layer source regions'},
        output: {recipeSha256: 'canonical deterministic recipe hash', sourceMechanism: 'normalized fixture evidence', candidates: 'domain-labeled candidate receipts and lineage', renderManifest: 'verified manifest', humanAcceptance: 'always unreviewed'},
      },
      'sfx.status': {
        summary: 'Read an SFX Forge request audit/status without retrying a provider or starting work.',
        write: false,
        requiredScopes: [],
        input: {requestId: 'SFX Forge request id'},
        output: {ok: 'boolean', status: 'missing|running|completed|failed', result: 'completed receipt when available', humanAcceptance: 'unreviewed unless separately recorded by Drew'},
      },
      'sfx.artifacts': {
        summary: 'Read back and verify SFX Forge artifact byte counts, hashes, headers, and optional decode evidence through the canonical generated artifact store.',
        write: false,
        requiredScopes: [],
        input: {artifactRefs: 'verified gs:// refs returned by SFX Forge', expected: 'optional expected byteCount/SHA-256 entries', decodeCheck: 'optional boolean'},
        output: {ok: 'boolean', artifacts: 'readback and decode evidence'},
      },
      'tts.synthesize': {
        summary: 'Synthesize one or more speaker segments with Cartesia directly, stitch them into one audio file, save it as a private Drive artifact, verify readback byte count and SHA-256, and audit the write. No Command Center job or worker is involved. Explicit provider=gemini adds Gemini 3.1 Flash TTS through the same contract; provider=auto remains backward-compatible.',
        write: true,
        requiresRequestId: true,
        requiredScopes: ['https://www.googleapis.com/auth/drive'],
        input: {voiceTier: 'optional utility, draft, or canon; config routes utility to cheapest configured TTS, draft to Gemini Flash TTS, canon to Gemini Pro TTS', useCase: 'optional ui, captions, audition, dialogue, or final_performance alias for voiceTier', provider: 'optional legacy gemini, cartesia, or auto when voiceTier is omitted', direction: 'optional natural-language direction; preserved across compatible downward fallback', text: 'exact string for single-speaker synthesis, or omit when segments is supplied', segments: 'optional array of {speaker,text,voiceName,voiceId,modelId,pitchSemitones}; segments are synthesized separately and stitched in order', voiceName: 'optional named voice', voiceId: 'optional provider voice id', acceptedVoice: 'optional boolean locking accepted casting against incompatible provider fallback', lockDirection: 'optional boolean preventing fallback to a provider that cannot preserve direction', modelId: 'optional legacy direct-provider model id; tier policy overrides it', pitchSemitones: 'optional tempo-preserving pitch shift default, finite number -12 through 12, default 0', format: 'optional wav or raw, default wav', sampleRate: 'optional number, default 24000', pauseMs: 'optional silence between stitched segments, default 0', name: 'optional Drive filename; degraded fallback receives an explicit degraded-tier suffix', parentFolderId: 'optional Drive folder id', requestId: 'string', callerNote: 'optional string'},
        output: {provider: 'gemini|cartesia', fileId: 'string', webViewLink: 'string', byteCount: 'number', sha256: 'string', readbackByteCount: 'number', readbackSha256: 'string', verified: 'boolean', segmentCount: 'number', segments: 'array', voiceName: 'string', modelId: 'string', audit: 'object'},
        agentRecipe: {
          whenUserSays: 'Generate TTS, make speech, narrate text, produce a Gemini or Cartesia audio file, or render multiple speakers into one stitched audio artifact from ChatGPT.',
          prefer: 'Call drive_operation with operation=tts.synthesize and provider=gemini for directed or expressive Gemini speech; existing Cartesia callers remain compatible. Return the Drive link and verification metadata to the user; do not inline Base64 audio in chat. Do not create a Command Center job for Cartesia synthesis.',
          verification: 'Treat verified=true with matching byteCount/SHA-256 readback and the returned segmentCount/segments as the acceptance signal.',
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

    ...computerHandsOperationEntries(),
    ...ritsuVoiceOperationEntries(),
    ...ritsuChatCallbackOperationEntries(),
    ...browserNerveOperationEntries(),
    ...veniceBodyOperationEntries(),
    ...veniceNerveOperationEntries(),
      ...smsCalendarOperationRegistry().operations,
      ...githubAdminOperationEntries(),
      ...droobiedooContextOperationEntries(),
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

async function readDriveBinaryChunkOperation({google, auth, args = {}}) {
  const drive = google.drive({version: 'v3', auth});
  const fileId = safeDriveFileId(args.fileId);
  const metadata = (await drive.files.get({
    fileId,
    fields: 'id,name,mimeType,size,md5Checksum,modifiedTime,webViewLink,parents',
    supportsAllDrives: true,
  })).data || {};
  if (String(metadata.mimeType || '').startsWith('application/vnd.google-apps.')) {
    throw Object.assign(new Error('drive_read_binary_chunk only supports stored binary files; export Google-native files with drive_read.'), {status: 415});
  }
  const totalSize = Number(metadata.size || 0);
  if (!Number.isSafeInteger(totalSize) || totalSize < 0) {
    throw Object.assign(new Error('Drive did not provide a safe binary file size.'), {status: 502});
  }
  const offset = args.offset === undefined ? 0 : Number(args.offset);
  const length = args.length === undefined ? 131072 : Number(args.length);
  if (!Number.isSafeInteger(offset) || offset < 0) {
    throw Object.assign(new Error('offset must be a nonnegative integer.'), {status: 400});
  }
  if (!Number.isSafeInteger(length) || length < 1 || length > 262144) {
    throw Object.assign(new Error('length must be an integer between 1 and 262144 bytes.'), {status: 400});
  }
  if (offset >= totalSize) {
    return {fileId, name: metadata.name || '', mimeType: metadata.mimeType || 'application/octet-stream', offset, byteCount: 0, totalSize, nextOffset: null, eof: true, chunkBase64: '', chunkSha256: createHash('sha256').update(Buffer.alloc(0)).digest('hex'), metadata: chatGptDriveFile(metadata)};
  }
  const end = Math.min(totalSize - 1, offset + length - 1);
  const downloaded = await drive.files.get(
    {fileId, alt: 'media', supportsAllDrives: true},
    {responseType: 'arraybuffer', headers: {Range: 'bytes=' + offset + '-' + end}},
  );
  const chunk = Buffer.isBuffer(downloaded.data) ? downloaded.data : Buffer.from(downloaded.data || []);
  const expectedBytes = end - offset + 1;
  if (chunk.length !== expectedBytes) {
    throw Object.assign(new Error('Drive binary range read returned ' + chunk.length + ' bytes; expected ' + expectedBytes + '.'), {status: 502});
  }
  const nextOffset = offset + chunk.length;
  return {fileId, name: metadata.name || '', mimeType: metadata.mimeType || 'application/octet-stream', offset, byteCount: chunk.length, totalSize, nextOffset: nextOffset < totalSize ? nextOffset : null, eof: nextOffset >= totalSize, chunkBase64: chunk.toString('base64'), chunkSha256: createHash('sha256').update(chunk).digest('hex'), driveMd5Checksum: metadata.md5Checksum || '', metadata: chatGptDriveFile(metadata)};
}

const AUDIO_INGEST_BUCKET = process.env.HOME_CENTER_GENERATED_BUCKET || 'home-center-generated';
const AUDIO_INGEST_EXTENSIONS = /\.(wav|mp3|ogg|flac|m4a|aac|opus)$/i;
const AUDIO_INGEST_MAX_BYTES = Number(process.env.HOME_CENTER_AUDIO_INGEST_MAX_BYTES || 512 * 1024 * 1024);
const audioIngestStorage = new Storage();

function sanitizeAudioIngestSegment(value, fallback = 'item') {
  const clean = safeText(String(value || ''), 240).replace(/[^A-Za-z0-9_.@-]+/g, '_').replace(/^_+|_+$/g, '');
  return clean || fallback;
}

function normalizedAudioIngestStage(value) {
  const stage = safeText(value, 80).toLowerCase() || 'unclassified';
  if (!['sources', 'finals', 'parts', 'probes', 'rejected', 'unclassified'].includes(stage)) {
    throw Object.assign(new Error('stage must be sources, finals, parts, probes, rejected, or unclassified.'), {status: 400});
  }
  return stage;
}

function normalizedAudioSourceMetadata(args = {}, stage = 'unclassified') {
  const sourceKind = safeText(args.sourceKind, 80).toLowerCase();
  const creator = safeText(args.creator, 320);
  const rightsBasis = safeText(args.rightsBasis, 80).toLowerCase();
  const captureDevice = safeText(args.captureDevice, 320);
  const captureApp = safeText(args.captureApp, 320);
  const recordedAt = safeText(args.recordedAt, 80);
  const annotationStatus = safeText(args.annotationStatus, 80).toLowerCase();
  const semanticAuthority = safeText(args.semanticAuthority, 80).toLowerCase();
  const notes = safeText(args.sourceNotes, 1600);
  const supplied = [sourceKind, creator, rightsBasis, captureDevice, captureApp, recordedAt, annotationStatus, semanticAuthority, notes].some(Boolean);
  if (stage !== 'sources' && !supplied) return null;

  const allowedSourceKinds = ['foley_recording', 'generated', 'licensed', 'public_domain', 'unknown'];
  const allowedRights = ['self_recorded', 'commissioned', 'licensed', 'public_domain', 'unknown'];
  const allowedAnnotationStatuses = ['embedded_spoken_labels_unparsed', 'unlabeled', 'partial', 'cataloged'];
  const allowedAuthorities = ['source_audio', 'creator_notes', 'catalog_review', 'unknown'];
  if (sourceKind && !allowedSourceKinds.includes(sourceKind)) {
    throw Object.assign(new Error('sourceKind is not supported.'), {status: 400});
  }
  if (rightsBasis && !allowedRights.includes(rightsBasis)) {
    throw Object.assign(new Error('rightsBasis is not supported.'), {status: 400});
  }
  if (annotationStatus && !allowedAnnotationStatuses.includes(annotationStatus)) {
    throw Object.assign(new Error('annotationStatus is not supported.'), {status: 400});
  }
  if (semanticAuthority && !allowedAuthorities.includes(semanticAuthority)) {
    throw Object.assign(new Error('semanticAuthority is not supported.'), {status: 400});
  }
  if (recordedAt && Number.isNaN(Date.parse(recordedAt))) {
    throw Object.assign(new Error('recordedAt must be an ISO-compatible timestamp.'), {status: 400});
  }
  if (stage === 'sources' && (!sourceKind || !creator || !rightsBasis)) {
    throw Object.assign(new Error('sources stage requires sourceKind, creator, and rightsBasis.'), {status: 400});
  }
  return {
    sourceKind: sourceKind || 'unknown',
    creator,
    rightsBasis: rightsBasis || 'unknown',
    captureDevice,
    captureApp,
    recordedAt,
    annotationStatus: annotationStatus || (stage === 'sources' ? 'unlabeled' : 'unlabeled'),
    semanticAuthority: semanticAuthority || (stage === 'sources' ? 'source_audio' : 'unknown'),
    notes,
  };
}

function validatedAudioIngestObjectName(value) {
  const name = safeText(value, 1024);
  if (!name.startsWith('audio/') || name.includes('\0') || name.split('/').some((part) => part === '.' || part === '..')) {
    throw Object.assign(new Error('objectName must be a safe path under audio/.'), {status: 400});
  }
  return name;
}

function hashReadableStream(stream) {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha256');
    let byteCount = 0;
    stream.on('data', (chunk) => {
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      byteCount += bytes.length;
      hash.update(bytes);
    });
    stream.on('end', () => resolve({byteCount, sha256: hash.digest('hex')}));
    stream.on('error', reject);
  });
}

function compareAudioIngestFileIds(left, right) {
  const a = safeText(left, 220);
  const b = safeText(right, 220);
  return a < b ? -1 : a > b ? 1 : 0;
}

function normalizedAudioIngestBatchId(value) {
  const raw = safeText(value, 180);
  if (!raw) throw Object.assign(new Error('batchId is required for indexed audio ingestion.'), {status: 400});
  return sanitizeAudioIngestSegment(raw, 'batch');
}

async function readAudioIndexJson(file) {
  const chunks = [];
  for await (const chunk of file.createReadStream()) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  const bytes = Buffer.concat(chunks);
  if (bytes.length > 8 * 1024 * 1024) throw Object.assign(new Error('Audio index object exceeds the 8 MiB safety limit.'), {status: 502});
  let parsed;
  try {
    parsed = JSON.parse(bytes.toString('utf8'));
  } catch (err) {
    throw Object.assign(new Error('Audio index object is not valid JSON.'), {status: 502, cause: err});
  }
  return {bytes, parsed, sha256: createHash('sha256').update(bytes).digest('hex')};
}

function sameAudioIndexIdentity(existing, expected) {
  return existing && expected &&
    existing.source && expected.source &&
    existing.destination && expected.destination &&
    safeText(existing.source.fileId, 220) === safeText(expected.source.fileId, 220) &&
    safeText(existing.destination.objectName, 1024) === safeText(expected.destination.objectName, 1024) &&
    safeText(existing.destination.sha256, 64).toLowerCase() === safeText(expected.destination.sha256, 64).toLowerCase() &&
    Number(existing.destination.byteCount || 0) === Number(expected.destination.byteCount || 0) &&
    JSON.stringify(existing.sourceMetadata || null) === JSON.stringify(expected.sourceMetadata || null);
}

async function writeImmutableAudioIndex(bucket, objectName, payload, createdFiles, identityCheck = sameAudioIndexIdentity) {
  const file = bucket.file(objectName);
  const [exists] = await file.exists();
  if (exists) {
    const existing = await readAudioIndexJson(file);
    if (!identityCheck(existing.parsed, payload)) {
      throw Object.assign(new Error('Audio bucket index already exists with conflicting provenance: ' + objectName), {status: 409});
    }
    return {objectName, storageRef: 'gs://' + AUDIO_INGEST_BUCKET + '/' + objectName, byteCount: existing.bytes.length, sha256: existing.sha256, reused: true};
  }
  const bytes = Buffer.from(JSON.stringify(payload, null, 2) + '\n', 'utf8');
  await pipeline(
    Readable.from([bytes]),
    file.createWriteStream({
      resumable: false,
      validation: false,
      preconditionOpts: {ifGenerationMatch: 0},
      metadata: {contentType: 'application/json', metadata: {indexSchema: safeText(payload.schemaVersion, 80), sourceDriveFileId: safeText(payload.source && payload.source.fileId, 220)}},
    }),
  );
  createdFiles.push(file);
  const readback = await readAudioIndexJson(file);
  if (readback.bytes.length !== bytes.length || readback.sha256 !== createHash('sha256').update(bytes).digest('hex')) {
    throw Object.assign(new Error('Audio bucket index failed readback verification: ' + objectName), {status: 502});
  }
  return {objectName, storageRef: 'gs://' + AUDIO_INGEST_BUCKET + '/' + objectName, byteCount: readback.bytes.length, sha256: readback.sha256, reused: false};
}

async function writeAudioIngestIndexes({bucket, batchId, fileId, ownerSegment, project, stage, source, destination, sourceMetadata = null}) {
  const createdFiles = [];
  const base = {
    schemaVersion: sourceMetadata ? 'home-center.audio-index.v2' : 'home-center.audio-index.v1',
    indexedAt: new Date().toISOString(),
    source,
    destination,
    sourceMetadata,
    classification: {ownerEmail: destination.ownerEmail, project, stage},
    verification: {verified: true, byteCountMatch: source.byteCount === destination.byteCount, sha256Match: source.sha256 === destination.sha256},
    retention: {driveMutated: false, driveTrashEligible: false, status: 'preserved-pending-sealed-batch-playback-and-explicit-approval'},
  };
  const names = {
    byDriveId: 'indexes/audio/v1/by-drive-id/' + sanitizeAudioIngestSegment(fileId, 'drive-file') + '.json',
    catalog: ['indexes/audio/v1/catalog', ownerSegment, project, stage, sanitizeAudioIngestSegment(fileId, 'drive-file') + '.json'].join('/'),
    batchItem: ['indexes/audio/v1/batches', batchId, 'items', sanitizeAudioIngestSegment(fileId, 'drive-file') + '.json'].join('/'),
  };
  try {
    const byDriveId = await writeImmutableAudioIndex(bucket, names.byDriveId, base, createdFiles);
    const catalog = await writeImmutableAudioIndex(bucket, names.catalog, base, createdFiles);
    const batchItem = await writeImmutableAudioIndex(bucket, names.batchItem, {...base, batchId}, createdFiles);
    return {byDriveId, catalog, batchItem};
  } catch (err) {
    await Promise.allSettled(createdFiles.map((file) => file.delete({ignoreNotFound: true})));
    throw err;
  }
}

async function finalizeDriveAudioIngestBatchOperation({admin, user, args = {}, storage = audioIngestStorage, recordAudit = recordActionAudit}) {
  if (args.approved !== true) {
    throw Object.assign(new Error('audio.finalize_ingest_batch requires approved=true.'), {status: 409});
  }
  const requestId = createRequestId(args.requestId || args.idempotencyKey);
  const batchId = normalizedAudioIngestBatchId(args.batchId);
  const expectedCount = Number(args.expectedCount);
  const expectedBytes = Number(args.expectedBytes);
  const expectedFileIds = Array.isArray(args.expectedFileIds) ? [...new Set(args.expectedFileIds.map(safeDriveFileId))].sort(compareAudioIngestFileIds) : [];
  if (!Number.isSafeInteger(expectedCount) || expectedCount < 1 || expectedFileIds.length !== expectedCount) {
    throw Object.assign(new Error('expectedFileIds must contain exactly expectedCount unique Drive file IDs.'), {status: 400});
  }
  if (!Number.isSafeInteger(expectedBytes) || expectedBytes < 1) {
    throw Object.assign(new Error('expectedBytes must be a positive safe integer.'), {status: 400});
  }
  const bucketName = AUDIO_INGEST_BUCKET;
  const bucket = storage.bucket(bucketName);
  const prefix = 'indexes/audio/v1/batches/' + batchId + '/items/';
  const [files] = await bucket.getFiles({prefix});
  const entries = [];
  for (const file of files) {
    if (!file.name.endsWith('.json')) continue;
    const item = (await readAudioIndexJson(file)).parsed;
    if (safeText(item.batchId, 180) !== batchId || !item.verification || item.verification.verified !== true || !sameAudioIndexIdentity(item, item)) {
      throw Object.assign(new Error('Batch contains an invalid or unverified item index: ' + file.name), {status: 502});
    }
    if (!item.verification.byteCountMatch || !item.verification.sha256Match) {
      throw Object.assign(new Error('Batch item hash/byte verification flags are not true: ' + file.name), {status: 502});
    }
    entries.push(item);
  }
  entries.sort((a, b) => compareAudioIngestFileIds(a.source.fileId, b.source.fileId));
  const actualFileIds = entries.map((entry) => safeText(entry.source.fileId, 220));
  const actualBytes = entries.reduce((sum, entry) => sum + Number(entry.destination.byteCount || 0), 0);
  if (entries.length !== expectedCount || actualBytes !== expectedBytes || JSON.stringify(actualFileIds) !== JSON.stringify(expectedFileIds)) {
    throw Object.assign(new Error('Batch index does not exactly match expected Drive IDs, count, and bytes.'), {status: 409});
  }
  const manifestPayload = {
    schemaVersion: 'home-center.audio-ingest-batch.v1',
    batchId,
    sealedAt: new Date().toISOString(),
    ownerEmail: safeText(user && user.email, 320).toLowerCase(),
    expected: {fileIds: expectedFileIds, itemCount: expectedCount, byteCount: expectedBytes},
    actual: {fileIds: actualFileIds, itemCount: entries.length, byteCount: actualBytes},
    verification: {verified: true, exactFileIds: true, exactItemCount: true, exactByteCount: true, everyItemReadbackVerified: true},
    driveCleanup: {driveTrashEligible: false, status: 'blocked-pending-player-range-playback-and-explicit-human-approval'},
    entries,
  };
  const manifestName = 'indexes/audio/v1/batches/' + batchId + '/manifest.json';
  const createdFiles = [];
  let manifest;
  try {
    manifest = await writeImmutableAudioIndex(bucket, manifestName, manifestPayload, createdFiles, (existing, expected) =>
      safeText(existing && existing.batchId, 180) === expected.batchId &&
      existing && existing.verification && existing.verification.verified === true &&
      JSON.stringify(existing.actual || {}) === JSON.stringify(expected.actual || {}) &&
      JSON.stringify(existing.expected || {}) === JSON.stringify(expected.expected || {}));
  } catch (err) {
    await Promise.allSettled(createdFiles.map((file) => file.delete({ignoreNotFound: true})));
    throw err;
  }
  await recordAudit(admin, user, 'audio.finalize_ingest_batch', batchId, 'Sealed verified audio ingest batch index at ' + manifest.storageRef + '; Drive remains preserved.', requestId);
  return {ok: true, sealed: true, verified: true, requestId, batchId, itemCount: entries.length, byteCount: actualBytes, manifest, driveTrashEligible: false, driveMutated: false};
}

async function ingestDriveAudioOperation({google, admin, auth, user, args = {}, storage = audioIngestStorage, recordAudit = recordActionAudit}) {
  if (args.approved !== true) {
    throw Object.assign(new Error('audio.ingest_drive requires approved=true. Drive remains untouched.'), {status: 409});
  }
  const requestId = createRequestId(args.requestId || args.idempotencyKey);
  const batchId = normalizedAudioIngestBatchId(args.batchId);
  const fileId = safeDriveFileId(args.fileId);
  const ownerEmail = safeText((user && user.email) || args.ownerEmail, 320).toLowerCase();
  if (!ownerEmail) throw Object.assign(new Error('An authenticated owner email is required.'), {status: 401});
  const drive = google.drive({version: 'v3', auth});
  const metadata = (await drive.files.get({
    fileId,
    fields: 'id,name,mimeType,size,md5Checksum,modifiedTime,webViewLink,parents',
    supportsAllDrives: true,
  })).data || {};
  const mimeType = safeText(metadata.mimeType, 160) || 'application/octet-stream';
  const sourceName = safeText(metadata.name, 500) || fileId;
  if (!/^audio\//i.test(mimeType) && !AUDIO_INGEST_EXTENSIONS.test(sourceName)) {
    throw Object.assign(new Error('audio.ingest_drive only accepts stored audio files.'), {status: 415});
  }
  const totalSize = Number(metadata.size || 0);
  if (!Number.isSafeInteger(totalSize) || totalSize < 1 || totalSize > AUDIO_INGEST_MAX_BYTES) {
    throw Object.assign(new Error('Drive audio size is missing, empty, or exceeds the ingest limit.'), {status: 413});
  }
  if (args.expectedSize !== undefined && Number(args.expectedSize) !== totalSize) {
    throw Object.assign(new Error('Drive byte count does not match expectedSize.'), {status: 409});
  }
  const driveMd5 = safeText(metadata.md5Checksum, 64).toLowerCase();
  const expectedDriveMd5 = safeText(args.expectedDriveMd5, 64).toLowerCase();
  if (expectedDriveMd5 && driveMd5 !== expectedDriveMd5) {
    throw Object.assign(new Error('Drive MD5 does not match expectedDriveMd5.'), {status: 409});
  }
  const project = sanitizeAudioIngestSegment(args.project, 'unclassified');
  const stage = normalizedAudioIngestStage(args.stage);
  const sourceMetadata = normalizedAudioSourceMetadata(args, stage);
  const sourcePath = safeText(args.sourcePath, 1000);
  const sharedWith = Array.isArray(args.sharedWith) ? args.sharedWith.map((email) => safeText(email, 320).toLowerCase()).filter(Boolean) : [];
  const ownerSegment = sanitizeAudioIngestSegment(ownerEmail, 'legacy');
  const nameSegment = sanitizeAudioIngestSegment(sourceName, 'audio.bin');
  const defaultObjectName = ['audio', ownerSegment, 'drive-import', project, stage, fileId + '-' + nameSegment].join('/');
  const objectName = validatedAudioIngestObjectName(args.objectName || defaultObjectName);
  const bucketName = AUDIO_INGEST_BUCKET;
  const bucket = storage.bucket(bucketName);
  const destination = bucket.file(objectName);
  const [destinationExists] = await destination.exists();
  if (destinationExists) {
    const [existingMetadata] = await destination.getMetadata();
    const custom = existingMetadata && existingMetadata.metadata || {};
    const sameSource = safeText(custom.sourceDriveFileId, 220) === fileId;
    const sameSize = Number(existingMetadata && existingMetadata.size || 0) === totalSize;
    const sameMd5 = !driveMd5 || !safeText(custom.sourceDriveMd5, 64) || safeText(custom.sourceDriveMd5, 64).toLowerCase() === driveMd5;
    if (!sameSource || !sameSize || !sameMd5) {
      throw Object.assign(new Error('Canonical destination already exists with different Drive provenance.'), {status: 409});
    }
    const readback = await hashReadableStream(destination.createReadStream());
    const expectedSha256 = safeText(custom.sha256, 64).toLowerCase();
    if (!expectedSha256 || readback.byteCount !== totalSize || readback.sha256 !== expectedSha256) {
      throw Object.assign(new Error('Existing canonical destination failed readback verification.'), {status: 502});
    }
    const sourceReceipt = {fileId, name: sourceName, mimeType, byteCount: totalSize, sha256: readback.sha256, driveMd5Checksum: driveMd5, sourcePath, webViewLink: metadata.webViewLink || ''};
    const destinationReceipt = {bucket: bucketName, objectName, storageRef: 'gs://' + bucketName + '/' + objectName, byteCount: readback.byteCount, sha256: readback.sha256, ownerEmail, project, stage, sourceMetadata};
    const indexes = await writeAudioIngestIndexes({bucket, batchId, fileId, ownerSegment, project, stage, source: sourceReceipt, destination: destinationReceipt, sourceMetadata});
    return {
      ok: true,
      verified: true,
      reused: true,
      requestId,
      batchId,
      source: sourceReceipt,
      destination: destinationReceipt,
      sourceMetadata,
      indexes,
      readback,
      driveMutated: false,
    };
  }

  const tempObjectName = ['temp', 'audio-ingest', sanitizeAudioIngestSegment(requestId, 'request'), randomUUID() + '.part'].join('/');
  const tempFile = bucket.file(tempObjectName);
  let destinationCreated = false;
  try {
    const sourceHash = createHash('sha256');
    let sourceByteCount = 0;
    const hashTap = new Transform({
      transform(chunk, encoding, callback) {
        const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, encoding);
        sourceByteCount += bytes.length;
        sourceHash.update(bytes);
        callback(null, bytes);
      },
    });
    const downloaded = await drive.files.get(
      {fileId, alt: 'media', supportsAllDrives: true},
      {responseType: 'stream'},
    );
    if (!downloaded.data || typeof downloaded.data.pipe !== 'function') {
      throw Object.assign(new Error('Drive did not return a readable audio stream.'), {status: 502});
    }
    await pipeline(
      downloaded.data,
      hashTap,
      tempFile.createWriteStream({
        resumable: false,
        validation: false,
        metadata: {contentType: 'application/octet-stream', metadata: {ingestStatus: 'staging', requestId, sourceDriveFileId: fileId}},
      }),
    );
    const sourceSha256 = sourceHash.digest('hex');
    if (sourceByteCount !== totalSize) {
      throw Object.assign(new Error('Drive stream byte count did not match Drive metadata.'), {status: 502});
    }
    const stagedReadback = await hashReadableStream(tempFile.createReadStream());
    if (stagedReadback.byteCount !== sourceByteCount || stagedReadback.sha256 !== sourceSha256) {
      throw Object.assign(new Error('Staged GCS object failed byte-count/SHA-256 verification.'), {status: 502});
    }

    await tempFile.copy(destination, {preconditionOpts: {ifGenerationMatch: 0}});
    destinationCreated = true;
    const customMetadata = {
      ownerEmail,
      sharedWith: JSON.stringify(sharedWith),
      requestId,
      project,
      stage,
      sha256: sourceSha256,
      sourceDriveFileId: fileId,
      sourceDriveMd5: driveMd5,
      sourceDrivePath: sourcePath,
      sourceDriveName: sourceName,
      sourceKind: sourceMetadata ? sourceMetadata.sourceKind : '',
      sourceCreator: sourceMetadata ? sourceMetadata.creator : '',
      rightsBasis: sourceMetadata ? sourceMetadata.rightsBasis : '',
      captureDevice: sourceMetadata ? sourceMetadata.captureDevice : '',
      captureApp: sourceMetadata ? sourceMetadata.captureApp : '',
      annotationStatus: sourceMetadata ? sourceMetadata.annotationStatus : '',
      semanticAuthority: sourceMetadata ? sourceMetadata.semanticAuthority : '',
      ingestStatus: 'verified',
      migrationPolicy: 'drive-preserved-pending-explicit-cleanup',
    };
    await destination.setMetadata({contentType: mimeType, metadata: customMetadata});
    const readback = await hashReadableStream(destination.createReadStream());
    if (readback.byteCount !== sourceByteCount || readback.sha256 !== sourceSha256) {
      throw Object.assign(new Error('Canonical GCS destination failed readback verification.'), {status: 502});
    }
    const sourceReceipt = {fileId, name: sourceName, mimeType, byteCount: sourceByteCount, sha256: sourceSha256, driveMd5Checksum: driveMd5, sourcePath, webViewLink: metadata.webViewLink || ''};
    const destinationReceipt = {bucket: bucketName, objectName, storageRef: 'gs://' + bucketName + '/' + objectName, byteCount: readback.byteCount, sha256: readback.sha256, ownerEmail, project, stage, sourceMetadata, metadata: customMetadata};
    const indexes = await writeAudioIngestIndexes({bucket, batchId, fileId, ownerSegment, project, stage, source: sourceReceipt, destination: destinationReceipt, sourceMetadata});
    destinationCreated = false;
    await recordAudit(admin, user, 'audio.ingest_drive', fileId, 'Ingested verified Drive audio to gs://' + bucketName + '/' + objectName + ' and wrote bucket indexes without mutating Drive.', requestId);
    return {
      ok: true,
      verified: true,
      reused: false,
      requestId,
      batchId,
      source: sourceReceipt,
      destination: destinationReceipt,
      sourceMetadata,
      indexes,
      readback,
      driveMutated: false,
    };
  } catch (err) {
    if (destinationCreated) await destination.delete({ignoreNotFound: true}).catch(() => {});
    throw err;
  } finally {
    await tempFile.delete({ignoreNotFound: true}).catch(() => {});
  }
}

function artifactTransportOperationError(message, status, code) {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  error.failureKind = 'artifact_transport';
  return error;
}

async function artifactTransportPreflightOperation({google, admin, auth, user, args = {}}) {
  const requestId = safeText(args.requestId, 180);
  if (!requestId) throw artifactTransportOperationError('requestId is required.', 400, 'ARTIFACT_REQUEST_ID_REQUIRED');
  const artifacts = Array.isArray(args.artifacts) ? args.artifacts : [];
  const consumer = safeObject(args.consumer);
  const storage = new Storage();
  const drive = google && auth ? google.drive({version: 'v3', auth}) : null;
  const receipt = await preflightArtifactEnvelope({
    requestId,
    operation: safeText(args.targetOperation, 120) || 'artifact_transport.preflight',
    artifacts,
    consumer,
    concurrency: Number(args.concurrency || 4),
    resolver: async (plan) => {
      const identity = plan.reference.identity;
      if (plan.location.kind === 'gcs') {
        const match = /^gs:\/\/([^/]+)\/(.+)$/.exec(plan.location.uri);
        if (!match) throw artifactTransportOperationError('Invalid GCS URI.', 400, 'ARTIFACT_GCS_URI_INVALID');
        const [metadata] = await storage.bucket(match[1]).file(match[2]).getMetadata();
        const actualBytes = Number(metadata.size || 0);
        const actualSha = safeText(metadata.metadata && metadata.metadata.sha256, 64).toLowerCase();
        if (actualBytes !== identity.byteLength) throw artifactTransportOperationError('GCS object byte length does not match artifact identity.', 409, 'ARTIFACT_BYTE_LENGTH_MISMATCH');
        if (!actualSha) throw artifactTransportOperationError('GCS object lacks verified sha256 metadata.', 409, 'ARTIFACT_SHA256_METADATA_MISSING');
        if (actualSha !== identity.sha256) throw artifactTransportOperationError('GCS object sha256 metadata does not match artifact identity.', 409, 'ARTIFACT_SHA256_MISMATCH');
        return {resolvable: true, reusedBytes: plan.action === 'reuse' ? actualBytes : 0, transferredBytes: 0, verification: {sha256Match: true, byteLengthMatch: true, generation: safeText(metadata.generation, 80)}};
      }
      if (plan.location.kind === 'drive') {
        if (!drive) throw artifactTransportOperationError('Drive reference requires authenticated Google Drive access.', 401, 'ARTIFACT_DRIVE_AUTH_REQUIRED');
        const response = await drive.files.get({fileId: plan.location.fileId, supportsAllDrives: true, fields: 'id,name,mimeType,size,md5Checksum,modifiedTime'});
        const actualBytes = Number(response.data && response.data.size || 0);
        if (actualBytes !== identity.byteLength) throw artifactTransportOperationError('Drive file byte length does not match artifact identity.', 409, 'ARTIFACT_BYTE_LENGTH_MISMATCH');
        return {resolvable: true, reusedBytes: plan.action === 'reuse' ? actualBytes : 0, transferredBytes: 0, verification: {byteLengthMatch: true, expectedSha256: identity.sha256, providerSha256Available: false, providerMd5: safeText(response.data && response.data.md5Checksum, 64), fileId: safeText(response.data && response.data.id, 240)}};
      }
      if (plan.location.kind === 'github') return {resolvable: true, reusedBytes: plan.action === 'reuse' ? identity.byteLength : 0, transferredBytes: 0, verification: {expectedSha256: identity.sha256, immutableRef: plan.location.ref}};
      if (plan.location.kind === 'inline_metadata') return {resolvable: true, reusedBytes: 0, transferredBytes: 0, verification: {metadataOnly: true}};
      throw artifactTransportOperationError('Reference kind requires staging and cannot be proven by preflight alone: ' + plan.location.kind + '.', 422, 'ARTIFACT_STAGING_REQUIRED');
    },
  });
  if (admin && typeof admin.firestore === 'function') {
    const ref = admin.firestore().collection('artifactTransportReceipts').doc(requestId);
    const snapshot = await ref.get();
    const owner = safeText(user && user.email, 320).toLowerCase();
    if (snapshot.exists) {
      const existing = snapshot.data() || {};
      if (existing.inputHash !== receipt.inputHash) throw artifactTransportOperationError('requestId is already bound to different artifact identities.', 409, 'ARTIFACT_IDEMPOTENCY_CONFLICT');
      return {...existing.receipt, attached: true};
    }
    await ref.create({requestId, inputHash: receipt.inputHash, owner, receipt, createdAt: new Date().toISOString()});
  }
  return {...receipt, attached: false};
}

async function artifactTransportStatusOperation({admin, user, args = {}}) {
  const requestId = safeText(args.requestId, 180);
  if (!requestId) throw artifactTransportOperationError('requestId is required.', 400, 'ARTIFACT_REQUEST_ID_REQUIRED');
  const snapshot = await admin.firestore().collection('artifactTransportReceipts').doc(requestId).get();
  if (!snapshot.exists) throw artifactTransportOperationError('Artifact transport receipt not found.', 404, 'ARTIFACT_RECEIPT_NOT_FOUND');
  const data = snapshot.data() || {};
  if (safeText(data.owner, 320).toLowerCase() !== safeText(user && user.email, 320).toLowerCase()) throw artifactTransportOperationError('Artifact transport receipt is not owned by this caller.', 403, 'ARTIFACT_RECEIPT_FORBIDDEN');
  return data.receipt;
}

async function tvTroperRetrievalOperation({google, args = {}}) {
  const operation = safeText(args.operation, 80);
  const operationArgs = safeObject(args.args);
  const entries = {status: {method: 'GET', path: '/health'}, search: {method: 'POST', path: '/search'}, get: {method: 'POST', path: '/get'}};
  const entry = entries[operation];
  if (!entry) throw Object.assign(new Error('tvtroper operation must be one of: status, search, get.'), {status: 400});
  if (!TVTROPER_RETRIEVAL_URL) throw Object.assign(new Error('TVTROPER_RETRIEVAL_URL is not configured.'), {status: 503});
  const auth = new google.auth.GoogleAuth();
  const client = await auth.getIdTokenClient(TVTROPER_RETRIEVAL_URL);
  try {
    const response = await client.request({url: TVTROPER_RETRIEVAL_URL + entry.path, method: entry.method, data: entry.method === 'POST' ? operationArgs : undefined, timeout: 120000});
    return {operation, registryVersion: TVTROPER_OPERATION_REGISTRY_VERSION, gcsOnly: true, result: response.data};
  } catch (err) {
    const status = safeNumber(err && err.response && err.response.status, 0) || safeNumber(err && err.code, 0) || 502;
    const providerMessage = safeText(err && err.response && err.response.data && (err.response.data.error || err.response.data.message), 500) || safeText(err.message || String(err), 500);
    throw Object.assign(new Error('TvTroper retrieval failed: ' + providerMessage), {status});
  }
}

async function driveOperationRunOperation({google, admin, auth, user, extra = null, googleClientId = '', googleClientSecret = '', githubToken = () => '', githubAdmin = {}, cartesiaApiKey = () => '', geminiApiKey = () => '', args = {}}) {
  const operation = safeText(args.operation || args.type || args.toolName, 120);
  if (!operation) throw Object.assign(new Error('operation is required.'), {status: 400});
  if (operation.startsWith('foundry.')) {
    const retired = retiredFoundryError(operation);
    return {operation, registryVersion: driveOperationRegistry().version, completed: false, error: {code: retired.code, message: retired.message, status: retired.status, ...retired.details}};
  }
  const registry = driveOperationRegistry();
  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported drive_operation operation: ' + operation), {status: 400});
  if (operation === 'time.now') {
    const now = new Date();
    return {operation, registryVersion: registry.version, completed: true, result: {utcIso: now.toISOString(), unixMs: now.getTime()}};
  }
  if (operation === 'security.identity_status') {
    const result = await homeCenterIdentityStatusOperation({admin, user, args: safeObject(args.args)});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'security.revoke_identity') {
    const result = await homeCenterIdentityRevokeOperation({admin, user, args: safeObject(args.args)});
    return {operation, registryVersion: registry.version, completed: result.fullyRevoked === true, result};
  }
  if (tvtroperOperationEntries()[operation]) {
    const result = await tvTroperRetrievalOperation({google, args: safeObject(args.args)});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {...args};
  delete operationArgs.operation;
  delete operationArgs.type;
  delete operationArgs.toolName;
  delete operationArgs.args;
  if (ritsuVoiceOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await ritsuVoiceOperationRunOperation({admin, user, operation, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (ritsuChatCallbackOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await ritsuChatCallbackRunOperation({admin, user, operation, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (computerHandsOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await computerHandsOperationRunOperation({admin, user, operation, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (browserNerveOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await browserNerveOperationRunOperation({admin, user, operation, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (veniceBodyOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await veniceBodyOperationRunOperation({extra, admin, user, operation, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (veniceNerveOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await veniceNerveOperationRunOperation({admin, user, operation, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'drive_text_patch') {
    const result = await driveTextPatchOperation({google, admin, auth, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'drive_binary_read_begin') {
    const result = await beginDriveBinaryReadOperation({google, admin, auth, user, args: operationArgs, maxBytes: HOME_CENTER_DRIVE_INGEST_MAX_BYTES});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'drive_binary_read_chunk') {
    const result = await readDriveBinarySessionChunkOperation({google, admin, auth, user, args: operationArgs, maxBytes: HOME_CENTER_DRIVE_INGEST_MAX_BYTES});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'drive_binary_read_status') {
    const result = await driveBinaryReadStatusOperation({google, admin, auth, user, args: operationArgs, maxBytes: HOME_CENTER_DRIVE_INGEST_MAX_BYTES});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'drive_binary_read_complete') {
    const result = await completeDriveBinaryReadOperation({google, admin, auth, user, args: operationArgs, maxBytes: HOME_CENTER_DRIVE_INGEST_MAX_BYTES});
    return {operation, registryVersion: registry.version, completed: result.verified === true, result};
  }
  if (operation === 'sites.source_version.materialize_drive') {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await materializeSitesSourceVersionOperation({google, admin, auth, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: result.everyFileReadbackVerified === true && result.verifiedSourceFileCount === result.sourceFileCount, result};
  }
  if (operation === 'drive.share_folder') {
    const result = await shareDriveFolderOperation({google, admin, auth, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: result.verified === true, result};
  }
  const compatCommandCenterOperation = commandCenterCompatOperation(args);
  if (compatCommandCenterOperation) {
    delete operationArgs.commandCenterOperation;
    delete operationArgs.command_center_operation;
    delete operationArgs.commandCenterTool;
    delete operationArgs.command_center_tool;
    const result = await commandCenterOperationRunOperation({google, admin, googleClientId, googleClientSecret, githubToken, extra, args: {operation: compatCommandCenterOperation, args: operationArgs}});
    return {operation, compatibilityRoute: 'drive_operation.command_center', commandCenterOperation: compatCommandCenterOperation, registryVersion: registry.version, completed: true, result: result.result};
  }
  if (blenderWorkspaceOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await runBlenderWorkspaceOperation({operation, admin, user, args: operationArgs});
    const completed = ['blender.workspace.inspect', 'blender.workspace.history', 'blender.workspace.status'].includes(operation) ? result.state !== 'queued' && result.state !== 'running' : false;
    return {operation, registryVersion: registry.version, completed, result};
  }
  if (filesystemOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await runFilesystemOperation({operation, admin, user, args: operationArgs});
    const wrapped = {operation, registryVersion: registry.version, completed: true, result};
    if (operation === 'storage.filesystem.download' && result.resourceLink) wrapped._mcpContent = {content: [{type: 'text', text: jsonText(wrapped)}, result.resourceLink]};
    return wrapped;
  }
  if (operation === 'artifact.delivery.materialize_receipt') {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await materializeReceiptArtifactsOperation(
      {google, admin, auth, user, args: operationArgs},
      {verifyGithubCandidate: (candidate) => verifyGitHubDeliveryCandidate(githubAdmin, user, candidate)},
    );
    const wrapped = {operation, registryVersion: registry.version, completed: result.status === 'review_ready', result};
    wrapped._mcpContent = {content: [{type: 'text', text: jsonText(wrapped)}, ...result.artifacts.map((item) => item.delivery && item.delivery.resourceLink).filter(Boolean)]};
    return wrapped;
  }
  if (operation === 'artifact.review.record') {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await recordArtifactReviewOperation({admin, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'artifact.review.link_successor') {
    requireCreditGatedEmail(user && user.email, operation);
    const result = await linkArtifactReviewSuccessorOperation({admin, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation.startsWith('droobiedoo.')) {
    const result = runDroobiedooContextOperation(operation, operationArgs);
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation.startsWith('command_center.')) {
    const result = await commandCenterOperationRunOperation({google, admin, googleClientId, googleClientSecret, githubToken, extra, args: {operation, args: operationArgs}});
    return {operation, registryVersion: registry.version, completed: true, result: result.result};
  }
  if (smsCalendarOperationRegistry().operations[operation]) {
    const result = await smsCalendarOperationRunOperation({google, admin, auth, user, args: {operation, args: operationArgs}});
    return {operation, registryVersion: registry.version, completed: true, result: result.result};
  }
  if (githubAdminOperationEntries()[operation]) {
    const result = await githubAdminOperationRunOperation({admin, user, githubAdmin, args: {operation, args: operationArgs}});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (simulationOperationRegistry().operations[operation]) {
    const result = await simulationOperationRunOperation({admin, user, args: {operation, args: operationArgs}});
    return {operation, registryVersion: registry.version, completed: true, result: result.result};
  }
  if (artifactOperationEntries()[operation]) {
    requireCreditGatedEmail(user && user.email, operation);
    if (operation === 'artifact_transport.preflight') {
      const result = await artifactTransportPreflightOperation({google, admin, auth, user, args: operationArgs});
      return {operation, registryVersion: registry.version, completed: result.state === 'accepted', result};
    }
    if (operation === 'artifact_transport.status') {
      const result = await artifactTransportStatusOperation({admin, user, args: operationArgs});
      return {operation, registryVersion: registry.version, completed: result.state === 'accepted', result};
    }
    const common = {admin, user, args: operationArgs, recordAudit: recordActionAudit};
    let result;
    if (operation === 'storage.artifact.resumable_begin') result = await beginResumableArtifactIngestOperation(common);
    if (operation === 'storage.artifact.resumable_status') result = await resumableArtifactStatusOperation(common);
    if (operation === 'storage.artifact.resumable_resume') result = await resumeResumableArtifactIngestOperation(common);
    if (operation === 'storage.artifact.resumable_commit') result = await commitResumableArtifactIngestOperation(common);
    if (operation === 'storage.artifact.begin') result = await beginArtifactIngestOperation(common);
    if (operation === 'storage.artifact.append_chunk') result = await appendArtifactChunkOperation(common);
    if (operation === 'storage.artifact.commit') result = await commitArtifactIngestOperation(common);
    if (operation === 'storage.artifact.abort') result = await abortArtifactIngestOperation(common);
    if (operation === 'storage.artifact.get') result = await readArtifactOperation(common);
    if (operation === 'storage.artifact.find_by_sha256') result = await findArtifactBySha256Operation(common);
    if (result && result.artifactId && ['storage.artifact.resumable_commit', 'storage.artifact.commit', 'storage.artifact.get', 'storage.artifact.find_by_sha256'].includes(operation)) {
      result.filesystem = await projectArtifactOperation({admin, user, artifactId: result.artifactId, requestId: 'project-' + result.artifactId + '-' + String(result.destination && result.destination.sha256 || result.manifest && result.manifest.destination && result.manifest.destination.sha256 || '').slice(0, 16)});
    } else if (result && result.manifest && result.manifest.artifactId && ['storage.artifact.get', 'storage.artifact.find_by_sha256'].includes(operation)) {
      result.filesystem = await projectArtifactOperation({admin, user, artifactId: result.manifest.artifactId});
    }
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'armory.receipt') {
    const result = await armoryReceiptOperation({admin, user, args: operationArgs});
    await recordActionAudit(admin, user, 'armory.receipt', result.receiptId, 'Recorded ' + result.count + ' immutable Armory Range casing(s) for ' + result.item + '.', result.requestId);
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'armory.recount') {
    const result = await armoryRecountOperation({admin, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'armory.casing') {
    const result = await armoryCasingOperation({admin, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'tts.voices') {
    await requireCreditGatedContext({google, admin, googleClientId, googleClientSecret, extra, user, auth, surface: 'tts.voices'});
    const provider = operationArgs.provider === undefined ? 'cartesia' : (safeText(operationArgs.provider || 'auto', 40).toLowerCase() || 'auto');
    if (!['auto', 'cartesia', 'gemini'].includes(provider)) throw Object.assign(new Error('provider must be auto, cartesia, or gemini.'), {status: 400});
    const cartesia = provider === 'gemini' ? null : await cartesiaVoicesOperation({cartesiaApiKey, args: operationArgs});
    const gemini = provider === 'cartesia' ? null : await refreshGeminiCatalog({apiKeyGetter: geminiApiKey, force: operationArgs.forceRefresh === true});
    const result = provider === 'cartesia' ? cartesia : provider === 'gemini' ? gemini : {provider: 'auto', providers: {cartesia, gemini}, routing: {backwardCompatibleDefault: 'cartesia', featureRequiredProvider: {naturalLanguageDirection: 'gemini', expressiveTags: 'gemini'}, silentFallback: false}};
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'tts.tier_policy') {
    return {operation, registryVersion: registry.version, completed: true, result: voiceTierPolicy.publicPolicy()};
  }
  if (operation === 'tts.canon_rerender_status') {
    const result = await canonRerenderStatusOperation({admin, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'audio.render') {
    requireCreditGatedEmail(user && user.email, 'audio.render');
    const result = await renderAudioOperation({google, admin, auth, user, cartesiaApiKey, geminiApiKey, args: operationArgs, helpers: {createRequestId, existingAudit, auditWrite, recordActionAudit, safeDriveFileId}});
    const cleanResult = {...result};
    const mcpContent = cleanResult._mcpContent;
    delete cleanResult._mcpContent;
    return {operation, registryVersion: registry.version, completed: cleanResult.status === 'completed', result: cleanResult, _mcpContent: mcpContent};
  }
  if (operation === 'audio.reader_link') {
    requireCreditGatedEmail(user && user.email, 'audio.reader_link');
    const result = await linkDriveAudioToReaderStageOperation({user, args: operationArgs});
    await recordActionAudit(admin, user, 'audio.reader_link', result.fileId, 'Linked verified audio into Reader folder ' + result.discovery.folder + ' without copying bytes or mutating Drive.', result.requestId);
    return {operation, registryVersion: registry.version, completed: result.status === 'linked', result};
  }
  if (operation === 'audio.render_register') {
    requireCreditGatedEmail(user && user.email, 'audio.render_register');
    const result = await recoverAudioRenderRegistrationOperation({admin, user, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: result.status === 'completed', result};
  }
  if (operation === 'audio.render_artifacts') {
    const result = await inspectAudioArtifactsOperation({google, auth, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'audio.render_status') {
    const requestId = createRequestId(operationArgs.requestId || operationArgs.idempotencyKey);
    const result = await audioRenderStatusOperation({admin, user, requestId, helpers: {existingAudit, auditWrite}});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'sfx.analyze_source') {
    requireCreditGatedEmail(user && user.email, 'sfx.analyze_source');
    const result = await analyzeSourceOperation({google, auth, admin, user, args: operationArgs, helpers: {createRequestId, existingAudit, auditWrite}});
    return {operation, registryVersion: registry.version, completed: result.status === 'completed', result};
  }
  if (operation === 'sfx.transcribe_slate') {
    requireCreditGatedEmail(user && user.email, 'sfx.transcribe_slate');
    const result = await transcribeSlateOperation({google, auth, admin, user, args: operationArgs, helpers: {createRequestId, existingAudit, auditWrite}});
    return {operation, registryVersion: registry.version, completed: result.status === 'completed', result};
  }
  if (operation === 'sfx.segment') {
    requireCreditGatedEmail(user && user.email, 'sfx.segment');
    const result = await segmentSourceOperation({google, auth, admin, user, args: operationArgs, helpers: {createRequestId, existingAudit, auditWrite}});
    return {operation, registryVersion: registry.version, completed: result.status === 'completed', result};
  }
  if (operation === 'sfx.render') {
    requireCreditGatedEmail(user && user.email, 'sfx.render');
    const result = await renderSourceConditionedOperation({google, auth, admin, user, args: operationArgs, helpers: {createRequestId, existingAudit, auditWrite}});
    return {operation, registryVersion: registry.version, completed: result.status === 'completed', result};
  }
  if (operation === 'sfx.status') {
    const requestId = createRequestId(operationArgs.requestId || operationArgs.idempotencyKey);
    const result = await sfxForgeStatusOperation({admin, requestId, helpers: {existingAudit}});
    return {operation, registryVersion: registry.version, completed: true, result};
  }
  if (operation === 'sfx.artifacts') {
    const result = await inspectAudioArtifactsOperation({google, auth, args: operationArgs});
    return {operation, registryVersion: registry.version, completed: true, result: {...result, operation: 'sfx.artifacts'}};
  }
  const workflowId = safeOperationBatchId(args.operationBatchId || operationArgs.operationBatchId || operationArgs.requestId || ('drive-operation-' + randomUUID()));
  const outputs = {};
  const result = await runDriveWorkflowOperation({google, admin, auth, user, workflowId, operation: {type: operation, ...operationArgs}, index: 0, outputs, cartesiaApiKey, geminiApiKey});
  return {operation, registryVersion: registry.version, workflowId, completed: result.status === 'completed', outputKey: result.outputKey || '', result: result.result, outputs};
}

async function runDriveWorkflowOperation({google, admin, auth, user, workflowId, operation, index, outputs, cartesiaApiKey = () => '', geminiApiKey = () => ''}) {
  const type = safeText(operation.type || operation.toolName || operation.tool, 120);
  const requestId = workflowOperationRequestId(workflowId, operation, index);
  const callerNote = safeText(operation.callerNote, 800) || ('Workflow ' + workflowId + ' step ' + (index + 1) + ': ' + type);
  if (type === 'drive_read_binary_chunk') {
    const result = await readDriveBinaryChunkOperation({google, auth, args: operation});
    return {index, type, requestId, status: 'completed', result};
  }
  if (type === 'audio.ingest_drive') {
    const result = await ingestDriveAudioOperation({google, admin, auth, user, args: {...operation, requestId}});
    return {index, type, requestId, status: 'completed', result};
  }
  if (type === 'audio.finalize_ingest_batch') {
    const result = await finalizeDriveAudioIngestBatchOperation({admin, user, args: {...operation, requestId}});
    return {index, type, requestId, status: 'completed', result};
  }
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
  if (type === 'tts.synthesize') {
    requireCreditGatedEmail(user && user.email, 'tts.synthesize');
    const result = await synthesizeSpeechAudioArtifactOperation({google, admin, auth, user, cartesiaApiKey, geminiApiKey, args: {...operation, requestId, callerNote, parentFolderId: workflowResolvedId(operation.parentFolderId || operation.parentFolderKey, outputs)}});
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

async function driveWorkflowRunOperation({google, admin, auth, user, cartesiaApiKey = () => '', geminiApiKey = () => '', args = {}}) {
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
      const result = await runDriveWorkflowOperation({google, admin, auth, user, workflowId, operation: operations[index] || {}, index, outputs, cartesiaApiKey, geminiApiKey});
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

function configuredValue(getter) {
  try {
    return typeof getter === 'function' && String(getter() || '').trim().length > 0;
  } catch (_err) {
    return false;
  }
}

function homeCenterReleaseIdentity() {
  return {
    sourceRepository: safeText(process.env.HOME_CENTER_SOURCE_REPOSITORY, 240) || 'unknown',
    sourceCommit: safeText(process.env.HOME_CENTER_SOURCE_COMMIT, 80) || 'unknown',
    sourceRef: safeText(process.env.HOME_CENTER_SOURCE_REF, 240) || 'unknown',
    registrySchemaRevision: HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
    publicManifestSha256: safeText(process.env.HOME_CENTER_PUBLIC_MANIFEST_SHA256, 64) || 'unknown',
    deployedServiceRevision: safeText(process.env.K_REVISION, 160) || 'unknown',
  };
}

function homeCenterHealthPayload() {
  return {ok: true, service: 'home-center-drive-bridge', version: HOME_CENTER_MCP_SERVER_VERSION};
}

function homeCenterReadinessPayload({admin, googleClientId, googleClientSecret}) {
  const releaseIdentity = homeCenterReleaseIdentity();
  const checks = [
    {name: 'main_release_identity', required: true, ok: releaseIdentity.sourceRepository === 'Valar05/home-center' && releaseIdentity.sourceRef === 'refs/heads/main' && /^[a-f0-9]{40}$/.test(releaseIdentity.sourceCommit) && /^[a-f0-9]{64}$/.test(releaseIdentity.publicManifestSha256)},
    {name: 'firebase_admin', required: true, ok: !!(admin && typeof admin.firestore === 'function')},
    {name: 'google_oauth_client_id', required: true, ok: configuredValue(googleClientId)},
    {name: 'google_oauth_client_secret', required: true, ok: configuredValue(googleClientSecret)},
    {name: 'command_center_endpoint', required: false, ok: Boolean(COMMAND_CENTER_MCP_URL)},
    {name: 'artifact_bucket', required: false, ok: Boolean(HOME_CENTER_GENERATED_ARTIFACT_BUCKET)},
  ];
  const ready = checks.every((check) => !check.required || check.ok);
  return {
    ready,
    status: ready ? 'ready' : 'not_ready',
    service: 'home-center-drive-bridge',
    version: HOME_CENTER_MCP_SERVER_VERSION,
    releaseIdentity,
    checks,
  };
}

function operationRegistrySummary(registry, limit = 200) {
  const operations = registry && registry.operations && typeof registry.operations === 'object' ? registry.operations : {};
  const names = Object.keys(operations).sort();
  const boundedNames = names.slice(0, limit);
  const deprecatedOperations = Object.fromEntries(boundedNames.filter((name) => operations[name] && operations[name].deprecated === true).map((name) => {
    const entry = operations[name];
    return [name, {
      deprecated: true,
      status: String(entry.status || 'deprecated'),
      retainedForCompatibility: entry.retainedForCompatibility === true,
      agentPolicy: String(entry.agentPolicy || ''),
      alternatives: Array.isArray(entry.alternatives) ? entry.alternatives.map((value) => String(value)).slice(0, 12) : [],
    }];
  }));
  return {
    version: String(registry && registry.version || ''),
    invocationTool: String(registry && registry.invocationTool || ''),
    operationCount: names.length,
    operations: boundedNames,
    writeOperations: boundedNames.filter((name) => operations[name] && (operations[name].write === true || operations[name].readOnly === false)),
    deprecatedOperations,
    truncated: names.length > boundedNames.length,
  };
}

function registeredToolNames(server) {
  return Object.keys(server && server._registeredTools || {}).sort();
}

function homeCenterCapabilitiesPayload(server) {
  return {
    service: 'home-center-drive-bridge',
    version: HOME_CENTER_MCP_SERVER_VERSION,
    registryVersion: HOME_CENTER_REGISTRY_VERSION,
    connectorSchemaRevision: HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
    releaseIdentity: homeCenterReleaseIdentity(),
    summaryKind: 'names_and_deprecations',
    topLevelTools: registeredToolNames(server),
    operationSurfaces: {
      drive: operationRegistrySummary(driveOperationRegistry()),
      simulation: operationRegistrySummary(simulationOperationRegistry()),
      commandCenter: operationRegistrySummary(commandCenterOperationRegistry()),
      smsCalendar: operationRegistrySummary(smsCalendarOperationRegistry()),
    },
    fileUploadTools: [
      {
        name: 'drive_ingest_file',
        required: ['requestId', 'file'],
        inputs: {
          file: {binding: 'openai/fileParams', type: 'object', required: ['download_url', 'file_id'], optional: ['mime_type', 'file_name']},
        },
        maxBytes: HOME_CENTER_DRIVE_INGEST_MAX_BYTES,
        verification: ['expectedSha256', 'Drive readback byte count', 'Drive readback SHA-256'],
      },
      {
        name: 'storage_ingest_artifact',
        required: ['requestId', 'file', 'artifactId', 'artifactKind', 'project', 'expectedSha256'],
        inputs: {
          file: {binding: 'openai/fileParams', type: 'object', required: ['download_url', 'file_id'], optional: ['mime_type', 'file_name']},
        },
        maxBytes: ARTIFACT_INGEST_MAX_BYTES,
        verification: ['expectedSha256', 'GCS readback byte count', 'GCS readback SHA-256', 'immutable indexes', 'Command Center artifact receipt'],
      },
    ],
    safety: {
      writesRequireRequestId: true,
      writesRequireApprovedTrue: true,
      permanentDeleteAvailable: false,
      batchOperationLimit: 25,
    },
  };
}

function createHomeCenterMcpServer({google, admin, googleClientId, googleClientSecret, githubToken = () => '', githubAdmin = {}, cartesiaApiKey = () => '', geminiApiKey = () => ''}) {
  const server = new McpServer({
    name: 'home-center-drive-bridge',
    version: HOME_CENTER_MCP_SERVER_VERSION,
  });

  registerHeadcrabReminderTools(server, {
    admin,
    google,
    z,
    textResult,
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    requestUserContext: async (extra) => requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret),
  });

  server.registerTool('health', {
    title: 'Health',
    description: 'Check whether the Home Center MCP process is alive.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async () => textResult(homeCenterHealthPayload()));

  server.registerTool('readiness', {
    title: 'Readiness',
    description: 'Check whether required local configuration is present to accept Home Center work. Does not call providers.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async () => textResult(homeCenterReadinessPayload({admin, googleClientId, googleClientSecret})));

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
      const mimeType = String(metadata.mimeType || '');
      const textLike = mimeType.startsWith('text/') || /^(application\/(json|xml|javascript|x-javascript|yaml|x-yaml))$/i.test(mimeType);
      if (!textLike) {
        throw Object.assign(new Error('drive_read does not coerce binary files to text. Use drive_operation with operation=drive_read_binary_chunk.'), {status: 415});
      }
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
      operation: z.string().describe('Operation name from capabilities.operationSurfaces.simulation.operations. Runtime registry validation rejects unsupported names.'),
      args: z.record(z.string(), z.any()).optional().describe('Operation-specific arguments. Write operations require requestId inside args.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await simulationOperationRunOperation({admin, user, args: args || {}}));
  });


  server.registerTool('storage_ingest_artifact', {
    title: 'Ingest artifact to Storage',
    description: 'Upload one top-level Work Mode file to canonical private Cloud Storage, verify SHA-256 and byte count by readback, write immutable indexes, and record a Command Center artifact receipt. This never writes Google Drive.',
    inputSchema: {
      requestId: z.string().describe('Stable idempotency and audit request id.'),
      file: openAiFileParamZodSchema(z, 'Required top-level ChatGPT host file. Paths, handles, raw URLs, Base64 values, refs, and nested descriptors are rejected.'),
      artifactId: z.string().describe('Stable artifact identity.'),
      artifactKind: z.string().describe('Artifact class such as source-motion.'),
      project: z.string().describe('Owning project or factory lane.'),
      name: z.string().optional().describe('Optional canonical filename override.'),
      mimeType: z.string().optional().describe('Optional MIME type override.'),
      expectedByteCount: z.number().int().positive().optional().describe('Optional expected byte count.'),
      expectedSha256: z.string().describe('Required caller-side SHA-256 provenance lock.'),
      provenance: z.record(z.string(), z.any()).optional().describe('Bounded source identity and curation provenance.'),
      callerNote: z.string().optional().describe('Optional audit summary.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES, 'openai/fileParams': ['file']},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const context = await requireCreditGatedContext({google, admin, googleClientId, googleClientSecret, extra, surface: 'storage_ingest_artifact'});
    const uploaded = await materializeOpenAiHostFile(args && args.file, {maxBytes: ARTIFACT_INGEST_MAX_BYTES});
    const result = await ingestArtifactUploadOperation({admin, user: context.user, args: {...(args || {}), file: uploaded}, recordAudit: recordActionAudit});
    result.filesystem = await projectArtifactOperation({admin, user: context.user, artifactId: result.artifactId, requestId: 'project-' + result.artifactId + '-' + result.destination.sha256.slice(0, 16)});
    return textResult(result);
  });

  server.registerTool('drive_ingest_file', {
    title: 'Ingest file to Drive',
    description: 'Upload one top-level ChatGPT Work Mode file to private Google Drive, verify byte count and SHA-256 by readback, and audit the write. Use this reusable ingress for ZIPs and other files that are not already in Drive.',
    inputSchema: {
      requestId: z.string().describe('Stable idempotency and audit request id.'),
      file: openAiFileParamZodSchema(z, 'Required top-level ChatGPT Work Mode host file. Paths, handles, raw URLs, Base64 values, refs, and nested descriptors are rejected.'),
      name: z.string().optional().describe('Optional Drive filename override.'),
      mimeType: z.string().optional().describe('Optional MIME type override.'),
      parentFolderId: z.string().optional().describe('Optional destination Drive folder id.'),
      expectedSha256: z.string().optional().describe('Optional expected hexadecimal SHA-256 digest for caller-side provenance locking.'),
      callerNote: z.string().optional().describe('Optional human-readable audit summary.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES, 'openai/fileParams': ['file']},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const context = await requireCreditGatedContext({google, admin, googleClientId, googleClientSecret, extra, surface: 'drive_ingest_file'});
    return textResult(await driveIngestFileOperation({google, admin, auth: context.auth, user: context.user, args: args || {}}));
  });
  server.registerTool('cartesia_voices', {
    title: 'Cartesia voices',
    description: 'List or search Cartesia voices by calling the hosted Cartesia provider directly from Home Center MCP. This does not create or inspect Command Center jobs, workers, leases, or Codex sessions.',
    inputSchema: {
      query: z.string().optional().describe('Optional text passed to Cartesia as q to search voice names, descriptions, and voice IDs.'),
      q: z.string().optional().describe('Alias for query.'),
      limit: z.number().int().min(1).max(100).default(100).describe('Cartesia provider page size, 1-100.'),
      pageToken: z.string().optional().describe('Alias for Cartesia starting_after pagination cursor.'),
      startingAfter: z.string().optional().describe('Cartesia starting_after voice ID cursor.'),
      endingBefore: z.string().optional().describe('Cartesia ending_before voice ID cursor.'),
      language: z.string().optional().describe('Cartesia language or language-locale filter such as ru, en, or en_GB.'),
      locale: z.string().optional().describe('Language-locale alias passed to Cartesia as language when language is not supplied.'),
      gender: z.enum(['masculine', 'feminine', 'gender_neutral']).optional().describe('Cartesia gender presentation filter.'),
      isOwner: z.boolean().optional().describe('When true, return only voices owned by the Cartesia organization.'),
      accent: z.string().optional().describe('Optional accent metadata filter applied to the returned Cartesia page when accent metadata is present.'),
      country: z.string().optional().describe('Optional country metadata filter applied to the returned Cartesia page when country metadata is present.'),
      includePreviewUrl: z.boolean().optional().describe('Include Cartesia preview_file_url expansion when available. Defaults to true.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (args, extra) => {
    await requireCreditGatedContext({google, admin, googleClientId, googleClientSecret, extra, surface: 'cartesia_voices'});
    return textResult(await cartesiaVoicesOperation({cartesiaApiKey, args: args || {}}));
  });

  server.registerTool('cartesia_synthesize', {
    title: 'Cartesia synthesize',
    description: 'Synthesize one or more speaker segments with Cartesia directly, stitch them into one audio file, save it as a private Drive artifact, verify readback byte count and SHA-256, and audit the write. This does not use Command Center jobs or workers.',
    inputSchema: {
      text: z.string().optional().describe('Single-speaker text. Omit when segments is supplied.'),
      segments: z.array(z.object({
        speaker: z.string().optional(),
        text: z.string(),
        voiceName: z.string().optional(),
        voiceId: z.string().optional(),
        modelId: z.string().optional(),
        pitchSemitones: z.number().min(-12).max(12).optional().describe('Optional per-segment tempo-preserving pitch shift override in semitones, finite JSON number from -12 to 12.'),
      })).optional().describe('Ordered speaker segments. Each segment is synthesized separately with its own optional Cartesia voice and pitch shift, then stitched into one output file.'),
      voiceName: z.string().optional().describe('Default Cartesia voice name for segments that do not specify one.'),
      voiceId: z.string().optional().describe('Default Cartesia voice id for segments that do not specify one.'),
      modelId: z.string().optional().describe('Default Cartesia model id.'),
      pitchSemitones: z.number().min(-12).max(12).optional().default(0).describe('Optional tempo-preserving pitch shift in semitones for all segments unless a segment overrides it. Must be a finite JSON number from -12 to 12.'),
      format: z.enum(['wav', 'raw']).optional().default('wav'),
      sampleRate: z.number().int().min(8000).max(48000).default(24000),
      pauseMs: z.number().int().min(0).max(5000).optional().describe('Optional silence inserted between stitched segments. Defaults to 0.'),
      name: z.string().optional().describe('Optional Drive filename.'),
      parentFolderId: z.string().optional().describe('Optional Drive folder ID for the audio artifact.'),
      callerNote: z.string().optional().describe('Human-readable summary for the audit log.'),
      requestId: z.string().describe('Stable idempotency/audit request id. Required.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {auth, user} = await requireCreditGatedContext({google, admin, googleClientId, googleClientSecret, extra, surface: 'cartesia_synthesize'});
    return textResult(await synthesizeCartesiaAudioArtifactOperation({google, admin, auth, user, cartesiaApiKey, args: args || {}}));
  });

  server.registerTool('fortress_online', {
    title: 'Fortress Online',
    description: 'Resolve or create the active Home Center project/workspace session for the authenticated owner and return a compact orientation packet for Venice.',
    inputSchema: {
      requestId: z.string().optional().describe('Optional stable request id for provenance.'),
      projectId: z.string().optional().describe('Optional Home Center project id hint.'),
      repository: z.string().optional().describe('Optional repository hint when the project must be resolved or created.'),
      workspaceId: z.string().optional().describe('Optional workspace id hint.'),
      workspaceLabel: z.string().optional().describe('Optional workspace label override.'),
      currentObjective: z.string().optional().describe('Optional objective to seed when creating a fresh session.'),
      checkpointRef: z.string().optional().describe('Optional checkpoint reference to seed when creating a fresh session.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const caller = callerFromHomeCenterUser(user, 'Venice');
    return textResult(await fortressOnlineOperation({admin, caller, args: args || {}}));
  });

  server.registerTool('home_center_session_status', {
    title: 'Home Center session status',
    description: 'Read the active Home Center project/workspace session orientation for the authenticated owner and Venice.',
    inputSchema: {
      agentId: z.string().optional().describe('Optional agent id override. Defaults to Venice.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const caller = callerFromHomeCenterUser(user, safeText((args || {}).agentId, 80) || 'Venice');
    return textResult(await homeCenterSessionStatusOperation({admin, caller, args: args || {}}));
  });

  server.registerTool('home_center_session_update', {
    title: 'Home Center session update',
    description: 'Update durable Home Center working-session state such as current objective, workspace, blockers, checkpoint reference, or artifact references.',
    inputSchema: {
      requestId: z.string().optional().describe('Optional stable request id for provenance.'),
      projectId: z.string().optional().describe('Optional project id hint when creating a fresh session.'),
      repository: z.string().optional().describe('Optional repository hint when creating a fresh session.'),
      workspaceId: z.string().optional().describe('Optional workspace id override.'),
      workspaceLabel: z.string().optional().describe('Optional workspace label override.'),
      currentObjective: z.string().optional().describe('Durable current objective text.'),
      objectiveStatement: z.string().optional().describe('Optional original user phrasing for provenance.'),
      checkpointRef: z.string().optional().describe('Optional durable checkpoint reference.'),
      blockers: z.array(z.string()).optional().describe('Optional blocker strings.'),
      artifactRefs: z.array(z.string()).optional().describe('Optional artifact or receipt references to associate with the active session.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const caller = callerFromHomeCenterUser(user, 'Venice');
    return textResult(await homeCenterSessionUpdateOperation({admin, caller, args: args || {}}));
  });

  server.registerTool('home_center_work_request', {
    title: 'Home Center work request',
    description: 'Record the basic durable unit of commissioned Home Center work. First invocation records exactly one Punnett-routed She-Raw interrogation question and must stop in AWAITING_ANSWER without executing. Resume the same taskId with interrogationAnswer to permit execution. Use route=fortress_session_probe for the continuity test capability path.',
    inputSchema: {
      requestId: z.string().optional().describe('Optional stable request id for provenance.'),
      projectId: z.string().optional().describe('Optional project id hint when creating a fresh session.'),
      repository: z.string().optional().describe('Optional repository hint when creating a fresh session.'),
      workspaceId: z.string().optional().describe('Optional workspace id override.'),
      taskId: z.string().optional().describe('Optional stable task id override.'),
      taskKind: z.string().optional().describe('Optional task kind label.'),
      route: z.string().optional().describe('Optional execution route. Use fortress_session_probe for the supported continuity test lane; unrouted work remains durably requested.'),
      requestText: z.string().describe('The work request to record and route. Repeat the unchanged commission when resuming an existing taskId.'),
      interrogationQuestion: z.string().optional().describe('Exactly one pre-execution question selected through She-Raw with requestedPerspective=Punnett. Required on first task creation by the operation. It may ask only for user-owned intent, constraint, acceptance, authority, or taste.'),
      interrogationDomain: z.enum(['intent', 'constraint', 'acceptance', 'authority', 'taste']).optional().describe('User-owned domain for the one interrogation question. Failure modes, implementation, regressions, and verification strategy are intentionally excluded.'),
      interrogationAnswer: z.string().optional().describe('The user answer when resuming the same taskId. An answer supplied on first creation cannot bypass the required turn boundary.'),
      artifactRefs: z.array(z.string()).optional().describe('Optional artifact or receipt refs already associated with this request.'),
      subsystemRefs: z.array(z.string()).optional().describe('Optional subsystem-specific refs or receipt ids.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const caller = callerFromHomeCenterUser(user, 'Venice');
    return textResult(await homeCenterWorkRequestOperation({admin, caller, args: args || {}}));
  });

  server.registerTool('home_center_work_status', {
    title: 'Home Center work status',
    description: 'Read the durable status and receipt for one Home Center work request. Defaults to the active session\'s most recent work item.',
    inputSchema: {
      taskId: z.string().optional().describe('Optional Home Center work task id. Defaults to the active session\'s last work item.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    const caller = callerFromHomeCenterUser(user, 'Venice');
    return textResult(await homeCenterWorkStatusOperation({admin, caller, args: args || {}}));
  });

  server.registerTool('command_center_operation', {
    title: 'Command Center operation',
    description: 'Invoke retained Command Center project, managed knowledge-bucket, app-control, and browser operations through the already-connected Home Center MCP app.',
    inputSchema: {
      operation: z.string().describe('Operation name from the retained Command Center registry: health, projects.*, bucket.*, app_control.*, browser_sessions.*, browser_discoveries.*, or browser_playbooks.*. Retired execution names are rejected permanently.'),
      args: z.record(z.string(), z.any()).optional().describe('Operation-specific arguments. Mutating operations require idempotencyKey inside args.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => mcpToolResult(await commandCenterOperationRunOperation({google, admin, googleClientId, googleClientSecret, githubToken, extra, args: args || {}})));



  if (process.env.HOME_CENTER_MCP_EXTENDED_TOOLS === 'true') {

  server.registerTool('capabilities', {
    title: 'Capabilities',
    description: 'Return a bounded, deterministic summary of callable tools and operation names for this deployed revision.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async () => textResult(homeCenterCapabilitiesPayload(server)));


  server.registerTool('drive_operation', {
    title: 'Drive operation',
    description: 'Run a named Home Drive, Simulation, or command_center.* operation from the runtime operation registry. Prefer this stable tool for new bridge capabilities so ChatGPT does not need a connector reinstall when backend operations are added.',
    inputSchema: {
      operation: z.string().describe('Operation name from capabilities.operationSurfaces.drive.operations, including simulation_* frame operations and command_center.* compatibility operations. Runtime registry validation rejects unsupported names.'),
      args: z.record(z.string(), z.any()).optional().describe('Operation-specific arguments. Writes require requestId inside args.'),
      operationBatchId: z.string().optional().describe('Optional stable batch/workflow id for recovery tracking.'),
    },
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const operation = safeText((args || {}).operation || (args || {}).type || (args || {}).toolName, 120);
    if (operation.startsWith('command_center.') || commandCenterCompatOperation(args || {})) {
      return mcpToolResult(await driveOperationRunOperation({google, admin, auth: null, user: null, extra, googleClientId, googleClientSecret, githubAdmin, cartesiaApiKey, geminiApiKey, args: args || {}}));
    }
    const {auth, user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return mcpToolResult(await driveOperationRunOperation({google, admin, auth, user, extra, googleClientId, googleClientSecret, githubAdmin, cartesiaApiKey, geminiApiKey, args: args || {}}));
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



  server.registerTool('github_admin_auth_status', {
    title: 'GitHub admin auth status',
    description: 'Inspect Home Center GitHub admin authority without exposing secrets.',
    inputSchema: {},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: true, openWorldHint: true},
  }, async (_args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult({actor: user.email || '', result: await githubAdminAuthStatusOperation({user, githubAdmin})});
  });

  server.registerTool('github_admin_create_repo', {
    title: 'GitHub admin create repo',
    description: 'Create a GitHub repository through the configured Home Center GitHub admin authority and audit the mutation.',
    inputSchema: {owner: z.string(), ownerType: z.enum(['org', 'user']).optional().default('org'), name: z.string(), visibility: z.enum(['private', 'public', 'internal']).optional().default('private'), description: z.string().optional(), autoInit: z.boolean().optional(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await githubAdminCreateRepoOperation({admin, user, githubAdmin, args: args || {}}));
  });


  server.registerTool('github_admin_configure_repo', {
    title: 'GitHub admin configure repo',
    description: 'Update safe repository settings through GitHub admin authority and audit the mutation.',
    inputSchema: {repo: z.string(), description: z.string().optional(), homepage: z.string().optional(), default_branch: z.string().optional(), has_issues: z.boolean().optional(), has_projects: z.boolean().optional(), has_wiki: z.boolean().optional(), allow_squash_merge: z.boolean().optional(), allow_merge_commit: z.boolean().optional(), allow_rebase_merge: z.boolean().optional(), delete_branch_on_merge: z.boolean().optional(), allow_auto_merge: z.boolean().optional(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await githubAdminConfigureRepoOperation({admin, user, githubAdmin, args: args || {}}));
  });

  server.registerTool('github_admin_create_branch', {
    title: 'GitHub admin create branch',
    description: 'Create a branch from an existing branch or explicit SHA and audit the mutation.',
    inputSchema: {repo: z.string(), branch: z.string(), fromBranch: z.string().optional(), sha: z.string().optional(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await githubAdminCreateBranchOperation({admin, user, githubAdmin, args: args || {}}));
  });

  server.registerTool('github_admin_upsert_file', {
    title: 'GitHub admin upsert file',
    description: 'Create or update one repository file on a branch and audit the commit.',
    inputSchema: {repo: z.string(), path: z.string(), branch: z.string().optional(), message: z.string().optional(), content: z.string().optional(), contentBase64: z.string().optional(), sha: z.string().optional(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await githubAdminUpsertFileOperation({admin, user, githubAdmin, args: args || {}}));
  });

  server.registerTool('github_admin_create_pull_request', {
    title: 'GitHub admin create pull request',
    description: 'Open a pull request and audit the mutation.',
    inputSchema: {repo: z.string(), title: z.string(), head: z.string(), base: z.string().optional(), body: z.string().optional(), draft: z.boolean().optional(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await githubAdminCreatePullRequestOperation({admin, user, githubAdmin, args: args || {}}));
  });

  server.registerTool('github_admin_merge_pull_request', {
    title: 'GitHub admin merge pull request',
    description: 'Merge a pull request only when expectedHeadSha matches and required checks are green, then audit the mutation.',
    inputSchema: {repo: z.string(), pullNumber: z.number().int().min(1), expectedHeadSha: z.string(), mergeMethod: z.enum(['merge', 'squash', 'rebase']).optional().default('squash'), requireGreenChecks: z.boolean().optional(), allowNoChecks: z.boolean().optional(), commitTitle: z.string().optional(), commitMessage: z.string().optional(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await githubAdminMergePullRequestOperation({admin, user, githubAdmin, args: args || {}}));
  });

  server.registerTool('github_admin_dispatch_workflow', {
    title: 'GitHub admin dispatch workflow',
    description: 'Dispatch a GitHub Actions workflow by workflow id/file and ref, then audit the mutation.',
    inputSchema: {repo: z.string(), workflowId: z.string(), ref: z.string().optional(), inputs: z.record(z.string(), z.any()).optional(), requestId: z.string(), callerNote: z.string().optional()},
    securitySchemes: MCP_OAUTH_SECURITY_SCHEMES,
    _meta: {securitySchemes: MCP_OAUTH_SECURITY_SCHEMES},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true},
  }, async (args, extra) => {
    const {user} = await requestGoogleContext(extra, google, admin, googleClientId, googleClientSecret);
    return textResult(await githubAdminDispatchWorkflowOperation({admin, user, githubAdmin, args: args || {}}));
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
    return textResult(await driveWorkflowRunOperation({google, admin, auth, user, cartesiaApiKey, geminiApiKey, args: args || {}}));
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

function createHomeCenterMcpApp({google, admin, googleClientId = () => '', googleClientSecret = () => '', githubToken = () => '', githubAdmin = {}, cartesiaApiKey = () => '', geminiApiKey = () => ''}) {
  const app = express();
  app.use(express.json({limit: '80mb'}));
  app.use(express.urlencoded({extended: false, limit: '256kb'}));
  installLegacyFoundryArtifactRoutes(app, {admin});
  const transports = {};

  app.all('/filesystem/files/:fileId/versions/:versionId/content', async (req, res) => {
    try {
      if (!['GET', 'HEAD'].includes(req.method)) throw Object.assign(new Error('GET or HEAD required.'), {status: 405, code: 'storage.filesystem.method_not_allowed'});
      if (rejectMissingTransportAuth(req, res)) return;
      const match = String(req.get('Authorization') || '').match(/^Bearer\s+(.+)$/i);
      const accessToken = match && match[1];
      let context = await loadMcpAccessContext(admin, google, googleClientId, googleClientSecret, accessToken);
      if (!context) context = {user: await googleIdentityFromToken(accessToken)};
      requireCreditGatedEmail(context.user && context.user.email, 'storage.filesystem.download');
      await streamFilesystemContent({admin, user: context.user, fileId: safeText(req.params.fileId, 80), versionId: safeText(req.params.versionId, 80), req, res});
    } catch (error) {
      if (res.headersSent) { res.destroy(error); return; }
      if (error.wwwAuthenticate) res.set('WWW-Authenticate', error.wwwAuthenticate);
      res.status(error.status || 500).json({error: error.code || error.failureKind || 'storage.filesystem.download_failed', message: safeText(error.message || String(error), 800), details: error.details || {}});
    }
  });

  app.get('/', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(homeCenterHealthPayload());
  });

  app.get('/ready', (_req, res) => {
    const readiness = homeCenterReadinessPayload({admin, googleClientId, googleClientSecret});
    res.set('Cache-Control', 'no-store');
    res.status(readiness.ready ? 200 : 503).json(readiness);
  });

  app.get('/oauth-protected-resource', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(oauthProtectedResourceMetadata());
  });

  app.get('/oauth-protected-resource-v2', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(oauthProtectedResourceMetadata());
  });

  const sendOAuthProtectedResourceMetadata = (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(oauthProtectedResourceMetadata());
  };
  app.get('/.well-known/oauth-protected-resource', sendOAuthProtectedResourceMetadata);
  // Some OAuth clients derive the RFC 9728 metadata path from the /mcp resource path
  // before they receive the explicit WWW-Authenticate resource_metadata URL.
  app.get('/.well-known/oauth-protected-resource/mcp', sendOAuthProtectedResourceMetadata);

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
      const context = await loadMcpAccessContext(admin, google, googleClientId(), googleClientSecret(), accessToken, null);
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
        client_id: context.oauth.clientId,
        resource: context.oauth.resource,
        scopes: context.oauth.scopes,
        issuer: context.oauth.issuer,
        expires_at: Math.floor(context.oauth.expiresAtMs / 1000),
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
      const grant = resolveOAuthGrant(req.query.resource, req.query.scope);
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
        resource: grant.resource,
        scopes: grant.scopes,
        googleScopes: grant.googleScopes,
        allowedEmails: grant.allowedEmails,
        createdAtMs: Date.now(),
        expiresAtMs: Date.now() + 10 * 60 * 1000,
      });
      const client = googleOAuthClient(google, googleClientId(), googleClientSecret(), MCP_GOOGLE_CALLBACK);
      const url = client.generateAuthUrl({
        access_type: 'offline',
        prompt: 'consent',
        scope: grant.googleScopes,
        state: flowState,
      });
      if (browserHandoff) {
        const redirectMode = chatgptConnector ? 'chatgpt_mobile_handoff' : 'secure_browser_handoff';
        connectorLog('authorize_secure_browser_handoff', req, {googleCallbackHost: redirectHost(MCP_GOOGLE_CALLBACK), redirectMode, chatgptConnector, oauthFlowId});
        res.set('Cache-Control', 'no-store');
        res.status(200).type('html').send(renderSecureBrowserOAuthHandoff(req, url, flowState, chatgptConnector ? 'chatgpt-mobile' : 'secure-browser'));
        return;
      }
      connectorLog('authorize_redirect_google', req, {googleCallbackHost: redirectHost(MCP_GOOGLE_CALLBACK), redirectMode: 'direct', chatgptConnector, oauthFlowId});
      res.redirect(url);
    } catch (err) {
      connectorLog('authorize_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(err.status || 500).send(err.message || String(err));
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
      assertHomeCenterIdentityAllowed(email, 'Home Center OAuth sign-in');
      const allowedEmails = Array.isArray(stateData.allowedEmails) ? stateData.allowedEmails.map((value) => safeText(value, 320).toLowerCase()) : null;
      if (allowedEmails && !allowedEmails.includes(email)) {
        await stateSnap.ref.delete();
        res.redirect(redirectWithParams(stateData.redirectUri, {error: 'access_denied', error_description: 'grounded_motion_email_not_allowed', state: stateData.state}));
        return;
      }
      await storeHomeCenterGoogleGrant(admin, email, safeText(stateData.resource, 1200) || MCP_RESOURCE, tokens);
      if (stateData.browserHandoff) {
        await stateSnap.ref.set({
          googleTokens: tokens,
          email,
          googleCompletedAtMs: Date.now(),
          updatedAtMs: Date.now(),
        }, {merge: true});
        connectorLog('google_callback_handoff_ready', req, {clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector, emailHash: tokenHashPrefix(email)});
        res.set('Cache-Control', 'no-store');
        res.status(200).type('html').send(renderSecureBrowserOAuthComplete('Home Center approved Google sign-in. Finishing the ChatGPT connector now...', `${mcpRequestMountedPath(req, '/oauth/handoff-complete')}?state=${encodeURIComponent(flowState)}`));
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
        resource: safeText(stateData.resource, 1200) || MCP_RESOURCE,
        scopes: Array.isArray(stateData.scopes) ? stateData.scopes : [...MCP_REQUIRED_SCOPES],
        createdAtMs: Date.now(),
        expiresAtMs: Date.now() + 10 * 60 * 1000,
      });
      await stateSnap.ref.delete();
      connectorLog('google_callback_success', req, {clientIdPrefix: safeText(stateData.clientId, 80).slice(0, 28), redirectHost: redirectHost(stateData.redirectUri), oauthFlowId: stateData.oauthFlowId || '', chatgptConnector: !!stateData.chatgptConnector, emailHash: tokenHashPrefix(email)});
      res.redirect(redirectWithParams(stateData.redirectUri, {code, state: stateData.state}));
    } catch (err) {
      connectorLog('google_callback_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(err.status || 500).send(err.message || String(err));
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
      assertHomeCenterIdentityAllowed(stateData.email, 'Home Center OAuth handoff');
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
        resource: safeText(stateData.resource, 1200) || MCP_RESOURCE,
        scopes: Array.isArray(stateData.scopes) ? stateData.scopes : [...MCP_REQUIRED_SCOPES],
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
      res.status(err.status || 500).send(err.message || String(err));
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
        assertHomeCenterIdentityAllowed(refreshData.email, 'Home Center OAuth refresh');
        const refreshResource = safeText(req.body && req.body.resource, 1200);
        const boundRefreshResource = safeText(refreshData.resource, 1200) || MCP_RESOURCE;
        if (refreshData.clientId !== clientId || refreshData.revokedAtMs) {
          res.status(400).json({error: 'invalid_grant'});
          return;
        }
        if (refreshResource && !oauthResourceMatches(boundRefreshResource, refreshResource)) {
          connectorLog('token_invalid_target', req, {clientIdPrefix: safeText(clientId, 80).slice(0, 28), reason: 'refresh_resource_mismatch'});
          res.status(400).json({error: 'invalid_target', error_description: 'resource_not_bound_to_refresh_grant'});
          return;
        }
        const accessToken = randomToken(32);
        const expiresAtMs = Date.now() + 55 * 60 * 1000;
        await oauthCollection(admin, 'mcpOAuthAccessTokens').doc(tokenHash(accessToken)).set({
          clientId,
          email: refreshData.email,
          googleTokens: refreshData.googleTokens,
          refreshTokenHash: tokenHash(refreshToken),
          resource: safeText(refreshData.resource, 1200) || MCP_RESOURCE,
          scopes: Array.isArray(refreshData.scopes) ? refreshData.scopes : [...MCP_REQUIRED_SCOPES],
          createdAtMs: Date.now(),
          expiresAtMs,
        });
        connectorLog('token_refresh_success', req, {emailHash: tokenHashPrefix(refreshData.email), expiresIn: 3300});
        const refreshScopes = Array.isArray(refreshData.scopes) ? refreshData.scopes : [...MCP_REQUIRED_SCOPES];
        res.json({access_token: accessToken, token_type: 'Bearer', expires_in: 3300, scope: refreshScopes.join(' ')});
        return;
      }

      const code = safeText(req.body && req.body.code, 4096);
      const redirectUri = safeText(req.body && req.body.redirect_uri, 1200);
      const verifier = safeText(req.body && req.body.code_verifier, 300);
      const tokenResource = safeText(req.body && req.body.resource, 1200);
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
      assertHomeCenterIdentityAllowed(data.email, 'Home Center OAuth token exchange');
      await codeSnap.ref.delete();
      if (safeNumber(data.expiresAtMs, 0) <= Date.now() || data.clientId !== clientId || data.redirectUri !== redirectUri) {
        connectorLog('token_invalid_grant', req, {clientIdPrefix: safeText(data.clientId || clientId, 80).slice(0, 28), redirectHost: redirectHost(redirectUri), oauthFlowId: data.oauthFlowId || '', chatgptConnector: !!data.chatgptConnector, reason: 'expired_client_or_redirect_mismatch'});
        res.status(400).json({error: 'invalid_grant'});
        return;
      }
      const boundResource = safeText(data.resource, 1200) || MCP_RESOURCE;
      if (tokenResource && !oauthResourceMatches(boundResource, tokenResource)) {
        connectorLog('token_invalid_target', req, {clientIdPrefix: safeText(data.clientId || clientId, 80).slice(0, 28), redirectHost: redirectHost(redirectUri), oauthFlowId: data.oauthFlowId || '', chatgptConnector: !!data.chatgptConnector, reason: 'authorization_code_resource_mismatch'});
        res.status(400).json({error: 'invalid_target', error_description: 'resource_not_bound_to_authorization_grant'});
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
        resource: boundResource,
        scopes: Array.isArray(data.scopes) ? data.scopes : [...MCP_REQUIRED_SCOPES],
        createdAtMs: Date.now(),
        updatedAtMs: Date.now(),
      });
      await oauthCollection(admin, 'mcpOAuthAccessTokens').doc(tokenHash(accessToken)).set({
        clientId,
        email: data.email,
        googleTokens: data.googleTokens,
        refreshTokenHash,
        resource: boundResource,
        scopes: Array.isArray(data.scopes) ? data.scopes : [...MCP_REQUIRED_SCOPES],
        createdAtMs: Date.now(),
        expiresAtMs,
      });
      if (data.flowState) {
        await oauthCollection(admin, 'mcpOAuthStates').doc(safeText(data.flowState, 300)).delete().catch(() => {});
      }
      connectorLog('token_success', req, {clientIdPrefix: safeText(data.clientId || clientId, 80).slice(0, 28), redirectHost: redirectHost(redirectUri), oauthFlowId: data.oauthFlowId || '', chatgptConnector: !!data.chatgptConnector, emailHash: tokenHashPrefix(data.email), expiresIn: 3300, issuedRefreshToken: true});
      const issuedScopes = Array.isArray(data.scopes) ? data.scopes : [...MCP_REQUIRED_SCOPES];
      res.json({access_token: accessToken, refresh_token: refreshToken, token_type: 'Bearer', expires_in: 3300, scope: issuedScopes.join(' ')});
    } catch (err) {
      connectorLog('token_error', req, {error: safeText(err.message || String(err), 300)});
      res.status(err.status || 500).json({error: err.status === 403 ? 'access_denied' : 'server_error', error_description: err.message || String(err)});
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
    const server = createHomeCenterMcpServer({google, admin, googleClientId, googleClientSecret, githubToken, githubAdmin, cartesiaApiKey, geminiApiKey});
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
      const server = createHomeCenterMcpServer({google, admin, googleClientId, googleClientSecret, githubToken, githubAdmin, cartesiaApiKey, geminiApiKey});
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

module.exports = {isFullHomeCenterGoogleGrant, selectHomeCenterGoogleTokens, storeHomeCenterGoogleGrant, mcpRequestMountedPath, oauthResourceMatches, TVTROPER_OPERATION_REGISTRY_VERSION, tvtroperOperationEntries, tvTroperRetrievalOperation, resolveOAuthGrant, GROUNDED_MOTION_MCP_RESOURCE, GROUNDED_MOTION_MCP_SCOPE, linkArtifactReviewSuccessorOperation, recordArtifactReviewOperation, materializeReceiptArtifactsOperation, artifactTransportPreflightOperation, homeCenterReleaseIdentity, artifactTransportStatusOperation, homeCenterHealthPayload, homeCenterReadinessPayload, homeCenterCapabilitiesPayload, operationRegistrySummary, CREDIT_GATED_EMAILS, requireCreditGatedEmail, GITHUB_ADMIN_ALLOWED_EMAILS, requireGitHubAdminUser, HOME_CENTER_MCP_SERVER_VERSION, HOME_CENTER_CONNECTOR_SCHEMA_REVISION, HOME_CENTER_REGISTRY_VERSION, HOME_CENTER_DIRECT_FILE_TOOLS, driveOperationRegistry, uploadVerifiedArtifact, createHomeCenterMcpApp, createHomeCenterMcpServer, createDriveFolderOperation, createGoogleDocOperation, appendGoogleDocOperation, publishContextSnapshotOperation, driveIngestFileOperation, driveIngestFileOperationWithUpload, synthesizeCartesiaAudioArtifactOperation, cartesiaVoicesOperation, createSheetOperation, updateSheetValuesOperation, importXlsxWorkbookOperation, readDriveBinaryChunkOperation, materializeSitesSourceVersionOperation, shareDriveFolderOperation, safeSitesSourceRepositoryUrl, safeSitesSourceCommit, safeSitesSourceBranch, safeShareEmail, compareAudioIngestFileIds, ingestDriveAudioOperation, finalizeDriveAudioIngestBatchOperation, driveOperationRunOperation, driveWorkflowRunOperation, simulationOperationRunOperation, simulationOperationRegistry, droobiedooContextOperationEntries, loadDroobiedooContextIndex, searchDroobiedooContextIndex, runDroobiedooContextOperation, normalizeRecoveryOperation, summarizeRecoveryOperations, loadMcpAccessContext, createDelegatedHomeCenterAuthContext, registeredHomeCenterTools, callRegisteredHomeCenterTool, armoryReceiptOperation, armoryRecountOperation, armoryCasingOperation, renderAudioOperation, inspectAudioArtifactsOperation, githubAdminOperationEntries, githubAdminOperationRunOperation, createGitHubAppJwt};