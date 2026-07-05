#!/usr/bin/env node
import {execFileSync} from 'node:child_process';
import {mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {join, resolve} from 'node:path';

const ROOT = resolve(new URL('..', import.meta.url).pathname);
const EVIDENCE_DIR = join(ROOT, 'tools', 'metal_prompt_evidence');
const GATEWAY_BASE = process.env.HOME_CENTER_GATEWAY_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net';
const SANDBOX_ROOT_NAME = 'Home Center Smoke Sandbox';
const DRIVE_FILES_URL = 'https://www.googleapis.com/drive/v3/files';
const DOCS_URL = 'https://docs.googleapis.com/v1/documents';
const DRIVE_FOLDER_MIME = 'application/vnd.google-apps.folder';
const DOC_MIME = 'application/vnd.google-apps.document';

const REQUIRED_SCOPES = [
  'openid',
  'email',
  'profile',
  'https://www.googleapis.com/auth/cloud-platform',
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
];

const TOOL_DEFINITIONS = [
  tool('drive.search', 'Search or list Google Drive files.', 'drive', false, false, ['https://www.googleapis.com/auth/drive'], ['query', 'folderName', 'mimeType', 'pageSize']),
  tool('drive.read_metadata', 'Read Google Drive file or folder metadata by fileId.', 'drive', false, false, ['https://www.googleapis.com/auth/drive'], ['fileId']),
  tool('drive.create_folder', 'Create a Google Drive folder.', 'drive', true, true, ['https://www.googleapis.com/auth/drive'], ['name', 'parentId']),
  tool('drive.update_metadata', 'Rename or move a Google Drive file or folder.', 'drive', true, true, ['https://www.googleapis.com/auth/drive'], ['fileId', 'name', 'addParentId', 'removeParentId']),
  tool('docs.search', 'Search Google Docs in Drive.', 'docs', false, false, ['https://www.googleapis.com/auth/drive'], ['query', 'folderName', 'pageSize']),
  tool('docs.read', 'Read text content from a Google Doc by fileId.', 'docs', false, false, ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'], ['fileId', 'name']),
  tool('docs.create', 'Create a Google Doc and optionally insert body text.', 'docs', true, true, ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'], ['title', 'body', 'folderId']),
  tool('docs.update', 'Update a Google Doc by appending, replacing, or replacing the body.', 'docs', true, true, ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'], ['fileId', 'name', 'appendText', 'replaceText', 'body']),
];

function tool(name, description, group, write, confirmationRequired, requiredScopes, args) {
  return {name, description, group, write, confirmationRequired, doubleConfirmationRequired: false, requiredScopes, arguments: args};
}

function parseArgs(argv) {
  const args = {scenario: 'docs-create-update-read', keepSandbox: false, timeoutMs: 130000};
  for (let i = 2; i < argv.length; i++) {
    const value = argv[i];
    if (value === '--keep-sandbox') args.keepSandbox = true;
    else if (value === '--scenario') args.scenario = argv[++i] || args.scenario;
    else if (value === '--timeout-ms') args.timeoutMs = Number(argv[++i] || args.timeoutMs);
    else if (value === '--help') {
      console.log('Usage: node tools/home_center_metal_prompt_smoke.mjs [--scenario docs-create-update-read] [--keep-sandbox] [--timeout-ms 130000]');
      process.exit(0);
    }
  }
  return args;
}

function firebaseApiKey() {
  const config = JSON.parse(readFileSync(join(ROOT, 'app', 'google-services.json'), 'utf8'));
  const key = config?.client?.[0]?.api_key?.[0]?.current_key || '';
  if (!key) throw new Error('Firebase web API key missing from app/google-services.json.');
  return key;
}

function googleAccessToken() {
  if (process.env.GOOGLE_ACCESS_TOKEN) return process.env.GOOGLE_ACCESS_TOKEN.trim();
  const errors = [];
  try {
    return execFileSync('gcloud', ['auth', 'application-default', 'print-access-token'], {encoding: 'utf8'}).trim();
  } catch (err) {
    errors.push(String(err.message || err));
  }
  try {
    return execFileSync('gcloud', ['auth', 'print-access-token'], {encoding: 'utf8'}).trim();
  } catch (err) {
    errors.push(String(err.message || err));
  }
  throw new Error([
    'Could not get a Google access token.',
    'Run once:',
    `gcloud auth application-default login --scopes=${REQUIRED_SCOPES.join(',')}`,
    'Or set GOOGLE_ACCESS_TOKEN to a token with Drive, Docs, openid, email, and profile scopes.',
    ...errors,
  ].join('\n'));
}

async function firebaseIdToken(accessToken, apiKey) {
  const body = {
    postBody: `access_token=${encodeURIComponent(accessToken)}&providerId=google.com`,
    requestUri: 'http://localhost',
    returnSecureToken: true,
    returnIdpCredential: true,
  };
  const json = await postJson(`https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=${encodeURIComponent(apiKey)}`, body, null, 'Firebase sign-in');
  if (!json.idToken) {
    throw new Error(`Firebase sign-in did not return idToken: ${JSON.stringify(redact(json)).slice(0, 500)}`);
  }
  return {idToken: json.idToken, email: json.email || '', localId: json.localId || ''};
}

async function verifyGoogleScopes(accessToken) {
  const response = await fetch(`https://oauth2.googleapis.com/tokeninfo?access_token=${encodeURIComponent(accessToken)}`);
  const json = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`Could not verify Google token scopes: ${JSON.stringify(redact(json)).slice(0, 500)}`);
  const granted = new Set(String(json.scope || '').split(/\s+/).filter(Boolean));
  const missing = REQUIRED_SCOPES.filter((scope) => !granted.has(scope));
  if (missing.length) {
    throw new Error([
      `Google token is missing required scopes: ${missing.join(', ')}`,
      'Run:',
      `gcloud auth application-default login --scopes=${REQUIRED_SCOPES.join(',')}`,
    ].join('\n'));
  }
  return {email: json.email || '', scopes: [...granted].sort()};
}

async function postJson(url, body, bearer, label) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 130000);
  try {
    const headers = {'Content-Type': 'application/json'};
    if (bearer) headers.Authorization = `Bearer ${bearer}`;
    const response = await fetch(url, {method: 'POST', headers, body: JSON.stringify(body || {}), signal: controller.signal});
    const text = await response.text();
    const json = text ? JSON.parse(text) : {};
    if (!response.ok) throw new Error(`${label || 'POST'} HTTP ${response.status}: ${text.slice(0, 1000)}`);
    return json;
  } finally {
    clearTimeout(timeout);
  }
}

async function googleJson(method, url, accessToken, body = null) {
  const headers = {Authorization: `Bearer ${accessToken}`, Accept: 'application/json'};
  const options = {method, headers};
  if (body) {
    headers['Content-Type'] = 'application/json; charset=utf-8';
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  const text = await response.text();
  if (!response.ok) throw new Error(`Google ${method} ${url} HTTP ${response.status}: ${text.slice(0, 1000)}`);
  return text ? JSON.parse(text) : {};
}

async function googleText(method, url, accessToken) {
  const response = await fetch(url, {method, headers: {Authorization: `Bearer ${accessToken}`, Accept: 'text/plain'}});
  const text = await response.text();
  if (!response.ok) throw new Error(`Google ${method} ${url} HTTP ${response.status}: ${text.slice(0, 1000)}`);
  return text;
}

function driveUrl(params = {}) {
  const url = new URL(DRIVE_FILES_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && String(value) !== '') url.searchParams.set(key, String(value));
  }
  return url.toString();
}

function escapeQuery(value) {
  return String(value || '').replaceAll("'", "\\'").trim();
}

class MetalToolHost {
  constructor(accessToken, evidence) {
    this.accessToken = accessToken;
    this.evidence = evidence;
    this.sandboxRoot = null;
    this.sandboxFolder = null;
  }

  async prepareSandbox(runId) {
    this.sandboxRoot = await this.findFolder(SANDBOX_ROOT_NAME);
    if (!this.sandboxRoot) this.sandboxRoot = await this.createFolder(SANDBOX_ROOT_NAME, '');
    await this.trashExistingRuns();
    this.sandboxFolder = await this.createFolder(`HC_SMOKE_RUN_${runId}`, this.sandboxRoot.id);
    this.evidence.sandbox = {rootId: this.sandboxRoot.id, folderId: this.sandboxFolder.id, folderName: this.sandboxFolder.name};
    return this.sandboxFolder;
  }

  async cleanup() {
    if (!this.sandboxFolder?.id) return {ok: false, skipped: true};
    await googleJson('PATCH', driveUrl({fields: 'id,trashed'}).replace('/files?', `/files/${encodeURIComponent(this.sandboxFolder.id)}?`), this.accessToken, {trashed: true});
    return {ok: true, folderId: this.sandboxFolder.id};
  }

  async findFolder(name, parentId = '') {
    const clauses = [`mimeType='${DRIVE_FOLDER_MIME}'`, `name='${escapeQuery(name)}'`, 'trashed=false'];
    if (parentId) clauses.push(`'${escapeQuery(parentId)}' in parents`);
    const result = await this.listDrive(clauses.join(' and '), 10);
    return result.files[0] || null;
  }

  async createFolder(name, parentId) {
    const metadata = {name, mimeType: DRIVE_FOLDER_MIME};
    if (parentId) metadata.parents = [parentId];
    return googleJson('POST', driveUrl({fields: 'id,name,mimeType,webViewLink,parents'}), this.accessToken, metadata);
  }

  async trashExistingRuns() {
    const q = [`mimeType='${DRIVE_FOLDER_MIME}'`, "name contains 'HC_SMOKE_RUN_'", `'${escapeQuery(this.sandboxRoot.id)}' in parents`, 'trashed=false'].join(' and ');
    const result = await this.listDrive(q, 20);
    for (const file of result.files) {
      await googleJson('PATCH', driveUrl({fields: 'id,trashed'}).replace('/files?', `/files/${encodeURIComponent(file.id)}?`), this.accessToken, {trashed: true});
    }
  }

  async listDrive(q, pageSize = 10) {
    return googleJson('GET', driveUrl({
      q,
      pageSize,
      fields: 'files(id,name,mimeType,modifiedTime,webViewLink,parents,trashed)',
      orderBy: 'modifiedTime desc',
      supportsAllDrives: 'true',
      includeItemsFromAllDrives: 'true',
    }), this.accessToken);
  }

  async fileMetadata(fileId) {
    return googleJson('GET', driveUrl({fields: 'id,name,mimeType,webViewLink,parents,trashed', supportsAllDrives: 'true'}).replace('/files?', `/files/${encodeURIComponent(fileId)}?`), this.accessToken);
  }

  async assertInSandbox(fileId, toolName) {
    const file = await this.fileMetadata(fileId);
    if (file.trashed || !Array.isArray(file.parents) || !file.parents.includes(this.sandboxFolder.id)) {
      throw new Error(`sandbox_violation: ${toolName} tried to use ${file.name || fileId} outside ${this.sandboxFolder.name}`);
    }
    return file;
  }

  sandboxQuery(args, fixedMimeType = '') {
    const clauses = [`'${escapeQuery(this.sandboxFolder.id)}' in parents`, 'trashed=false'];
    const mimeType = fixedMimeType || cleanArg(args, 'mimeType');
    const query = cleanArg(args, 'query') || cleanArg(args, 'name') || cleanArg(args, 'title');
    if (mimeType) clauses.push(`mimeType='${escapeQuery(mimeType)}'`);
    if (query) clauses.push(`name contains '${escapeQuery(query)}'`);
    return clauses.join(' and ');
  }

  async execute(toolName, args) {
    this.evidence.toolExecutions.push({toolName, arguments: redact(args)});
    if (toolName === 'drive.search') return this.driveSearch(toolName, args, '');
    if (toolName === 'drive.read_metadata') return this.driveReadMetadata(args);
    if (toolName === 'drive.create_folder') return this.driveCreateFolder(args);
    if (toolName === 'drive.update_metadata') return this.driveUpdateMetadata(args);
    if (toolName === 'docs.search') return this.driveSearch(toolName, args, DOC_MIME);
    if (toolName === 'docs.read') return this.docsRead(args);
    if (toolName === 'docs.create') return this.docsCreate(args);
    if (toolName === 'docs.update') return this.docsUpdate(args);
    throw new Error(`metal tool host does not implement ${toolName}`);
  }

  async driveSearch(toolName, args, fixedMimeType) {
    const result = await this.listDrive(this.sandboxQuery(args, fixedMimeType), clamp(Number(args?.pageSize || 5), 1, 10));
    return {tool: toolName, ok: true, error: '', detail: '', files: result.files || [], content: ''};
  }

  async driveReadMetadata(args) {
    const fileId = cleanArg(args, 'fileId');
    if (!fileId) return toolError('drive.read_metadata', 'missing_file_id', 'drive.read_metadata requires fileId.');
    const file = await this.assertInSandbox(fileId, 'drive.read_metadata');
    return {tool: 'drive.read_metadata', ok: true, error: '', detail: '', file, files: [], content: ''};
  }

  async driveCreateFolder(args) {
    const parentId = cleanArg(args, 'parentId') || this.sandboxFolder.id;
    if (parentId !== this.sandboxFolder.id) throw new Error('sandbox_violation: drive.create_folder parentId outside sandbox');
    const name = cleanArg(args, 'name') || `Smoke Child ${Date.now()}`;
    const file = await this.createFolder(name, parentId);
    return {tool: 'drive.create_folder', ok: true, error: '', detail: 'drive_folder_created', status: 'drive_folder_created', file, title: file.name, files: [], content: ''};
  }

  async driveUpdateMetadata(args) {
    const fileId = cleanArg(args, 'fileId');
    if (!fileId) return toolError('drive.update_metadata', 'missing_file_id', 'drive.update_metadata requires fileId.');
    await this.assertInSandbox(fileId, 'drive.update_metadata');
    const body = {};
    if (cleanArg(args, 'name')) body.name = cleanArg(args, 'name');
    const params = {fields: 'id,name,mimeType,webViewLink,parents'};
    if (cleanArg(args, 'addParentId')) params.addParents = cleanArg(args, 'addParentId');
    if (cleanArg(args, 'removeParentId')) params.removeParents = cleanArg(args, 'removeParentId');
    if (params.addParents && params.addParents !== this.sandboxFolder.id) throw new Error('sandbox_violation: drive.update_metadata addParentId outside sandbox');
    const file = await googleJson('PATCH', driveUrl(params).replace('/files?', `/files/${encodeURIComponent(fileId)}?`), this.accessToken, body);
    return {tool: 'drive.update_metadata', ok: true, error: '', detail: 'drive_metadata_updated', status: 'drive_metadata_updated', file, title: file.name, files: [], content: ''};
  }

  async docsCreate(args) {
    const folderId = cleanArg(args, 'folderId') || this.sandboxFolder.id;
    if (folderId !== this.sandboxFolder.id) throw new Error('sandbox_violation: docs.create folderId outside sandbox');
    const title = cleanArg(args, 'title') || 'Home Center Metal Smoke';
    const body = cleanArg(args, 'body');
    const created = await googleJson('POST', DOCS_URL, this.accessToken, {title});
    const documentId = created.documentId;
    if (!documentId) throw new Error('docs.create did not return documentId');
    if (body) {
      await googleJson('POST', `${DOCS_URL}/${encodeURIComponent(documentId)}:batchUpdate`, this.accessToken, {
        requests: [{insertText: {location: {index: 1}, text: body}}],
      });
    }
    await googleJson('PATCH', driveUrl({addParents: folderId, fields: 'id,parents'}).replace('/files?', `/files/${encodeURIComponent(documentId)}?`), this.accessToken, {});
    const file = await this.assertInSandbox(documentId, 'docs.create');
    return {tool: 'docs.create', ok: true, error: '', detail: 'google_doc_created', status: 'google_doc_created', file, title: file.name || title, webViewLink: file.webViewLink || '', files: [], content: ''};
  }

  async docsRead(args) {
    const fileId = cleanArg(args, 'fileId');
    if (!fileId) return toolError('docs.read', 'missing_file_id', 'docs.read requires fileId.');
    const file = await this.assertInSandbox(fileId, 'docs.read');
    const content = await googleText('GET', `${DRIVE_FILES_URL}/${encodeURIComponent(fileId)}/export?mimeType=text/plain`, this.accessToken);
    return {tool: 'docs.read', ok: true, error: '', detail: '', file, files: [], content};
  }

  async docsUpdate(args) {
    const fileId = cleanArg(args, 'fileId');
    if (!fileId) return toolError('docs.update', 'missing_file_id', 'docs.update requires fileId.');
    await this.assertInSandbox(fileId, 'docs.update');
    const appendText = cleanArg(args, 'appendText');
    const replaceText = cleanArg(args, 'replaceText');
    const body = cleanArg(args, 'body');
    if (!appendText && !replaceText && !body) return toolError('docs.update', 'missing_update', 'Provide appendText, replaceText, or body.');
    const endIndex = await this.documentEndIndex(fileId);
    const requests = [];
    if (body) {
      if (endIndex > 2) requests.push({deleteContentRange: {range: {startIndex: 1, endIndex: endIndex - 1}}});
      requests.push({insertText: {location: {index: 1}, text: body}});
    } else if (replaceText) {
      requests.push({replaceAllText: {containsText: {text: replaceText, matchCase: true}, replaceText: appendText}});
    } else {
      requests.push({insertText: {location: {index: Math.max(1, endIndex - 1)}, text: appendText.startsWith('\n') ? appendText : `\n${appendText}`}});
    }
    await googleJson('POST', `${DOCS_URL}/${encodeURIComponent(fileId)}:batchUpdate`, this.accessToken, {requests});
    const file = await this.assertInSandbox(fileId, 'docs.update');
    return {tool: 'docs.update', ok: true, error: '', detail: 'google_doc_updated', status: 'google_doc_updated', file, title: file.name || '', webViewLink: file.webViewLink || '', files: [], content: ''};
  }

  async documentEndIndex(fileId) {
    const doc = await googleJson('GET', `${DOCS_URL}/${encodeURIComponent(fileId)}?fields=body(content(endIndex))`, this.accessToken);
    const content = doc?.body?.content || [];
    return Math.max(1, ...content.map((entry) => Number(entry.endIndex || 1)));
  }
}

class GatewayLoop {
  constructor(firebaseToken, host, evidence) {
    this.firebaseToken = firebaseToken;
    this.host = host;
    this.evidence = evidence;
    this.pendingConfirmation = null;
    this.workingMemory = {};
    this.transcript = '';
  }

  async send(message, expectations = {}) {
    const toolResults = [];
    const turnEvidence = {message, responses: [], toolResults: []};
    this.evidence.turns.push(turnEvidence);
    for (let step = 0; step < 8; step++) {
      const body = this.body(message, toolResults);
      const response = await postJson(`${GATEWAY_BASE}/agentToolTurn`, body, this.firebaseToken, 'agentToolTurn');
      turnEvidence.responses.push(redact(response));
      if (response.type === 'tool_call' && response.toolName) {
        const result = await this.host.execute(response.toolName, response.arguments || {});
        this.updateWorkingMemory(response.toolName, response.arguments || {}, result);
        toolResults.push({name: response.toolName, arguments: response.arguments || {}, result});
        turnEvidence.toolResults.push(redact({name: response.toolName, result}));
        continue;
      }
      if (response.pendingConfirmation) this.pendingConfirmation = response.pendingConfirmation;
      else if (response.status !== 'confirmation_required') this.pendingConfirmation = null;
      const reply = response.reply || response.text || '';
      this.recordTranscript(message, reply);
      this.assertResponse(message, response, expectations);
      return {response, toolResults, turnEvidence};
    }
    throw new Error(`agentToolTurn did not converge for ${message}`);
  }

  body(message, toolResults) {
    return {
      message,
      transcript: this.transcript,
      summary: '',
      toolResults,
      tools: TOOL_DEFINITIONS,
      unavailableToolGroups: [],
      workingMemory: this.workingMemory,
      timeContext: timeContext(),
      evidenceContext: {latestUserReport: message, recentConversationEvidence: this.transcript},
      attachmentImages: [],
      debugTrace: true,
      ...(this.pendingConfirmation ? {pendingConfirmation: this.pendingConfirmation} : {}),
    };
  }

  recordTranscript(user, assistant) {
    this.transcript = `${this.transcript}\nUser: ${user}\nAssistant: ${assistant}`.trim().slice(-8000);
  }

  updateWorkingMemory(toolName, args, result) {
    if (!result?.ok) return;
    if (['docs.create', 'docs.update', 'docs.read'].includes(toolName)) {
      const file = result.file || {};
      this.workingMemory.lastDocument = {
        fileId: file.id || cleanArg(args, 'fileId'),
        name: result.title || file.name || cleanArg(args, 'name') || cleanArg(args, 'title'),
        webViewLink: result.webViewLink || file.webViewLink || '',
        sourceTool: toolName,
      };
    }
    if (toolName === 'docs.search' && Array.isArray(result.files) && result.files.length === 1) {
      const file = result.files[0];
      this.workingMemory.lastDocument = {fileId: file.id || '', name: file.name || '', webViewLink: file.webViewLink || '', sourceTool: toolName};
    }
  }

  assertResponse(message, response, expectations) {
    const text = JSON.stringify(response);
    for (const forbidden of [
      'I did not get a valid GPT-5.5 response',
      'I did not get a useful GPT-5.5 response',
      'tell me the main ingredient',
      'second constraint',
      'second ingredient',
      'name":"that document"',
      'title":"that document"',
    ]) {
      if (text.includes(forbidden)) throw new Error(`forbidden response for ${message}: ${forbidden}`);
    }
    if (expectations.status && response.status !== expectations.status) {
      throw new Error(`expected status ${expectations.status} for ${message}, got ${response.status}: ${text.slice(0, 1000)}`);
    }
    if (expectations.pendingTool && response?.pendingConfirmation?.toolName !== expectations.pendingTool) {
      throw new Error(`expected pending ${expectations.pendingTool} for ${message}, got ${response?.pendingConfirmation?.toolName || 'none'}`);
    }
    if (expectations.contains) {
      const reply = response.reply || response.text || '';
      for (const needle of expectations.contains) {
        if (!reply.includes(needle)) throw new Error(`expected final reply to contain ${needle}`);
      }
    }
  }
}

async function runDocsScenario() {
  const runId = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
  const evidence = {ok: false, runId, gatewayBase: GATEWAY_BASE, turns: [], toolExecutions: [], sandbox: {}, auth: {}, cleanup: null};
  mkdirSync(EVIDENCE_DIR, {recursive: true});
  const evidencePath = join(EVIDENCE_DIR, `metal_prompt_smoke_${runId}.json`);
  const title = `Home Center Metal Smoke ${runId}`;
  const firstLine = `First metal smoke line ${runId}.`;
  const secondLine = `Second metal smoke line ${runId}.`;
  const args = parseArgs(process.argv);
  let host;
  let failed = false;
  try {
    const accessToken = googleAccessToken();
    const scopeInfo = await verifyGoogleScopes(accessToken);
    const firebase = await firebaseIdToken(accessToken, firebaseApiKey());
    evidence.auth = {firebaseSignedIn: true, email: firebase.email || scopeInfo.email, localId: firebase.localId, scopes: scopeInfo.scopes};
    host = new MetalToolHost(accessToken, evidence);
    await host.prepareSandbox(runId);
    const loop = new GatewayLoop(firebase.idToken, host, evidence);

    await loop.send(`Create a Google Doc titled ${title} with body ${firstLine}`, {status: 'confirmation_required', pendingTool: 'docs.create'});
    await loop.send('confirm create');
    if (loop.workingMemory?.lastDocument?.name !== title) throw new Error(`lastDocument was not ${title}`);

    await loop.send(`Append "${secondLine}" to that document.`, {status: 'confirmation_required', pendingTool: 'docs.update'});
    await loop.send('confirm edit');

    const read = await loop.send('Read that document and tell me the full text.', {contains: [firstLine, secondLine]});
    const fileId = loop.workingMemory?.lastDocument?.fileId;
    const direct = await host.docsRead({fileId});
    if (!direct.content.includes(firstLine) || !direct.content.includes(secondLine)) {
      throw new Error('Direct Docs verification did not find both smoke lines.');
    }
    evidence.finalReply = read.response.reply || '';
    evidence.directDocText = direct.content;
    evidence.ok = true;
  } catch (err) {
    failed = true;
    evidence.error = String(err && err.stack ? err.stack : err);
    console.error(`Home Center metal prompt smoke failed. Evidence: ${evidencePath}`);
    console.error(String(err && err.message ? err.message : err));
  } finally {
    if (host && !parseArgs(process.argv).keepSandbox) {
      try {
        evidence.cleanup = await host.cleanup();
      } catch (err) {
        evidence.cleanup = {ok: false, error: String(err.message || err)};
      }
    }
  }
  writeFileSync(evidencePath, JSON.stringify(redact(evidence), null, 2));
  if (failed) {
    process.exitCode = 1;
    return;
  }
  console.log(`Home Center metal prompt smoke: OK evidence=${evidencePath} folderId=${evidence.sandbox.folderId}`);
}

function cleanArg(args, name) {
  const value = args && typeof args[name] === 'string' ? args[name].trim() : '';
  return value;
}

function toolError(toolName, error, detail) {
  return {tool: toolName, ok: false, error, detail, files: [], content: ''};
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number.isFinite(value) ? value : min));
}

function timeContext() {
  const now = new Date();
  return {nowEpochMillis: now.getTime(), timeZoneId: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', nowIso: now.toISOString()};
}

function redact(value) {
  const json = JSON.parse(JSON.stringify(value || {}));
  const scrub = (node) => {
    if (!node || typeof node !== 'object') return;
    for (const key of Object.keys(node)) {
      if (/token|authorization|secret|key/i.test(key)) node[key] = '[redacted]';
      else scrub(node[key]);
    }
  };
  scrub(json);
  return json;
}

const args = parseArgs(process.argv);
if (args.scenario !== 'docs-create-update-read') {
  console.error(`Unknown scenario: ${args.scenario}`);
  process.exit(2);
}
await runDocsScenario();
