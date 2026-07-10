const {createHash, randomBytes, randomUUID} = require('node:crypto');
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
const MCP_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/oauth-protected-resource-v2`;
const MCP_LEGACY_RESOURCE_METADATA = `${MCP_PUBLIC_BASE}/oauth-protected-resource`;
const MCP_AUTHORIZATION_SERVER_METADATA = `${MCP_PUBLIC_BASE}/.well-known/oauth-authorization-server`;
const MCP_GOOGLE_CALLBACK = process.env.HOME_CENTER_MCP_GOOGLE_CALLBACK || `${MCP_PUBLIC_BASE}/oauth/google-callback`;
const MCP_REQUIRED_SCOPES = [
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
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

function connectorLog(event, req, fields = {}) {
  const payload = {
    event: `mcp_connector_${event}`,
    attemptId: connectorAttemptId(req),
    method: req && req.method,
    path: req && req.path,
    clientIdPrefix: safeText((req.query && req.query.client_id) || (req.body && req.body.client_id), 80).slice(0, 28),
    redirectHost: redirectHost((req.query && req.query.redirect_uri) || (req.body && req.body.redirect_uri)),
    ...fields,
  };
  console.log(JSON.stringify(payload));
}

function pkceChallenge(verifier) {
  return createHash('sha256').update(String(verifier || '')).digest('base64url');
}

function redirectWithParams(base, params) {
  const url = new URL(base);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
  }
  return url.toString();
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
  if (safeNumber(data.expiresAtMs, 0) <= Date.now()) {
    const err = new Error('Home Center OAuth token expired. Reconnect the ChatGPT app.');
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
    targetId: safeText(operation.targetId || operation.fileId || operation.documentId || operation.folderId, 220),
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
  const targetId = safeText(args.fileId || args.documentId || args.folderId || args.targetFolderId || args.parentFolderId || args.planId, 220);
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
    targetId: operation.fileId || operation.documentId || operation.folderId || operation.targetFolderId || operation.parentFolderId,
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
  }, async () => textResult({ok: true, service: 'home-center-drive-bridge', version: '0.1.0'}));

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
    transport: 'stateless-streamable-http',
    safety: {
      writesRequireRequestId: true,
      writesRequireApprovedTrue: true,
      dryRunAvailable: ['drive_move', 'drive_rename', 'drive_plan_organize'],
      permanentDeleteAvailable: false,
      batchOperationLimit: 25,
    },
    homeDriveManual: {
      purpose: 'Home Drive is the durable Google Drive and Docs operating layer. Use it instead of ad hoc Google connector calls when the user wants files found, read, created, moved, renamed, appended, indexed, audited, or organized.',
      thingProperty: {
        meaning: 'thing is the human named target or subject of the request, such as a project name, folder name, document title, file label, or remembered workflow target. It is not proof of identity by itself.',
        rule: 'Resolve a thing to concrete Drive IDs before writes. Search/list/read metadata first unless the request already supplies a fileId, folderId, or documentId.',
        examples: [
          {thing: 'Lexen WWII folder', resolveWith: 'drive_search or drive_list_folder', thenUse: 'folderId or parentFolderId'},
          {thing: 'Story Bible', resolveWith: 'drive_search plus drive_get_metadata', thenUse: 'documentId for docs_append'},
          {thing: 'all notes in this project', resolveWith: 'drive_list_folder and optional index_folder', thenUse: 'dry-run plan before any move or rename'},
        ],
      },
      normalFlow: [
        'Call capabilities when orientation is needed.',
        'Call auth_status when the user asks whether the bridge is connected.',
        'For discovery, use drive_search for names/text and drive_list_folder for folder contents.',
        'For identity, use drive_get_metadata and parent folders; do not trust names alone for writes.',
        'For reading, use drive_read for one file or index_folder/index_status for reusable local search state.',
        'For single writes, use drive_create_folder, docs_create, docs_append, drive_move, or drive_rename with stable requestId values.',
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
      'drive_search', 'drive_read', 'drive_list_folder', 'drive_get_metadata',
      'drive_create_folder', 'docs_create', 'drive_move', 'drive_rename',
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
    collections: ['driveBridgeAudit', 'driveBridgePlans', 'driveBridgeIndex', 'actionAudit', 'mcpOAuthAccessTokens'],
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
        type: z.enum(['drive_create_folder', 'docs_create', 'docs_append', 'drive_move', 'drive_rename']),
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
  app.use(express.json({limit: '2mb'}));
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
      connectorLog('authorize_redirect_google', req, {googleCallbackHost: redirectHost(MCP_GOOGLE_CALLBACK)});
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
      await stateSnap.ref.delete();
      if (error) {
        res.redirect(redirectWithParams(stateData.redirectUri, {error, state: stateData.state}));
        return;
      }
      if (!googleCode || safeNumber(stateData.expiresAtMs, 0) <= Date.now()) {
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
        res.redirect(redirectWithParams(stateData.redirectUri, {error: 'access_denied', error_description: 'verified_google_email_required', state: stateData.state}));
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
        createdAtMs: Date.now(),
        expiresAtMs: Date.now() + 10 * 60 * 1000,
      });
      connectorLog('google_callback_success', req, {redirectHost: redirectHost(stateData.redirectUri), emailHash: tokenHashPrefix(email)});
      res.redirect(redirectWithParams(stateData.redirectUri, {code, state: stateData.state}));
    } catch (err) {
      connectorLog('google_callback_error', req, {error: safeText(err.message || String(err), 300)});
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
        res.status(400).json({error: 'invalid_grant'});
        return;
      }
      if (data.codeChallenge) {
        const validPkce = data.codeChallengeMethod === 'S256' ? pkceChallenge(verifier) === data.codeChallenge : verifier === data.codeChallenge;
        if (!validPkce) {
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
      connectorLog('token_success', req, {emailHash: tokenHashPrefix(data.email), expiresIn: 3300, issuedRefreshToken: true});
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

module.exports = {createHomeCenterMcpApp, createHomeCenterMcpServer, createDriveFolderOperation, createGoogleDocOperation, appendGoogleDocOperation, driveWorkflowRunOperation, normalizeRecoveryOperation, summarizeRecoveryOperations, loadMcpAccessContext};
