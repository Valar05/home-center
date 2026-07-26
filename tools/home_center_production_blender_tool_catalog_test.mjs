#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';

const DEFAULT_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const EXPECTED_REVISION = '2026-07-26.integrated-capabilities-security-v1';

function parseArgs(argv) {
  const args = {
    mcpUrl: process.env.HOME_CENTER_MCP_URL || DEFAULT_MCP_URL,
    bearerToken: process.env.HOME_CENTER_MCP_BEARER_TOKEN || '',
    tokenConfig: process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json'),
    evidencePath: process.env.HOME_CENTER_BLENDER_CATALOG_EVIDENCE || '',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--token-config') args.tokenConfig = argv[++i];
    else if (arg === '--evidence-path') args.evidencePath = argv[++i];
    else if (arg === '--help') {
      console.log('Usage: node tools/home_center_production_blender_tool_catalog_test.mjs [--mcp-url URL] [--bearer-token TOKEN] [--token-config PATH] [--evidence-path PATH]');
      process.exit(0);
    }
  }
  return args;
}

function parseJson(text, label) {
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`${label} did not return JSON: ${String(text || '').slice(0, 500)}`);
  }
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim());
  return parseJson(dataLines.length ? dataLines.join('\n') : text, label);
}

async function refreshTokenConfig(configPath) {
  if (!fs.existsSync(configPath)) return {token: '', refreshed: false, reason: 'token config missing'};
  const raw = parseJson(fs.readFileSync(configPath, 'utf8'), configPath);
  if (raw.accessToken && Number(raw.expiresAtMs || 0) > Date.now() + 60000) {
    return {token: raw.accessToken, refreshed: false, reason: 'token still fresh'};
  }
  if (!raw.refreshToken) return {token: raw.accessToken || raw.bearerToken || raw.token || '', refreshed: false, reason: 'refresh token missing'};
  const gatewayBase = raw.gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net';
  const response = await fetch(`${gatewayBase}/termuxTokenRefresh`, {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({refreshToken: raw.refreshToken}),
  });
  const text = await response.text();
  const json = parseJson(text, 'termuxTokenRefresh');
  if (!response.ok || !json.ok || !json.access_token) {
    return {token: raw.accessToken || raw.bearerToken || raw.token || '', refreshed: false, reason: `refresh failed status=${response.status}`};
  }
  const next = {
    ...raw,
    accessToken: json.access_token,
    tokenType: json.token_type || raw.tokenType || 'Bearer',
    expiresAtMs: Date.now() + Number(json.expires_in || 0) * 1000,
    allowedGroups: json.allowedGroups || raw.allowedGroups || [],
    refreshedAt: new Date().toISOString(),
  };
  fs.writeFileSync(configPath, JSON.stringify(next, null, 2) + '\n', {mode: 0o600});
  try { fs.chmodSync(configPath, 0o600); } catch (_) {}
  return {token: next.accessToken, refreshed: true, reason: 'refreshed'};
}

async function loadToken(args) {
  if (args.bearerToken) return {token: args.bearerToken, source: 'env_or_arg', refreshed: false, reason: 'explicit bearer token'};
  const refreshed = await refreshTokenConfig(args.tokenConfig);
  return {token: refreshed.token, source: args.tokenConfig, refreshed: refreshed.refreshed, reason: refreshed.reason};
}

async function postMcp(mcpUrl, token, body) {
  const response = await fetch(mcpUrl, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json',
      accept: 'application/json, text/event-stream',
    },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  return {status: response.status, headers: Object.fromEntries(response.headers.entries()), text};
}

function textToolJson(payload, label) {
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '';
  return parseJson(text, label);
}

function assertHostFileSchema(schema, name, mediaType) {
  assert.equal(schema?.type, 'string', `${name} must be a string binary host-file slot`);
  assert.equal(schema?.format, 'binary', `${name} must use format=binary`);
  assert.equal(schema?.contentMediaType, mediaType, `${name} must publish a concrete MIME hint`);
  assert.equal(schema?.contentEncoding, undefined, `${name} must not publish JSON contentEncoding for host file uploads`);
  assert.match(schema?.description || '', /host-file upload|uploaded/i, `${name} description must identify a host-file upload`);
}

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).map(([key, item]) => /token|authorization|secret/i.test(key) ? [key, item ? '[redacted]' : item] : [key, redact(item)]));
}

const args = parseArgs(process.argv.slice(2));
const tokenInfo = await loadToken(args);
assert.ok(tokenInfo.token, `Missing MCP bearer token: ${tokenInfo.reason}`);

const init = await postMcp(args.mcpUrl, tokenInfo.token, {
  jsonrpc: '2.0',
  id: 'init',
  method: 'initialize',
  params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'home-center-production-blender-tool-catalog-test', version: '1'}},
});
assert.equal(init.status, 200, `initialize failed HTTP ${init.status}: ${init.text.slice(0, 500)}`);
await postMcp(args.mcpUrl, tokenInfo.token, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}}).catch(() => null);

const healthResponse = await postMcp(args.mcpUrl, tokenInfo.token, {jsonrpc: '2.0', id: 'health', method: 'tools/call', params: {name: 'health', arguments: {}}});
assert.equal(healthResponse.status, 200, `health failed HTTP ${healthResponse.status}`);
const healthPayload = parseMcpResponse(healthResponse.text, 'health response');
const health = textToolJson(healthPayload, 'health text receipt');

const listResponse = await postMcp(args.mcpUrl, tokenInfo.token, {jsonrpc: '2.0', id: 'tools', method: 'tools/list', params: {}});
assert.equal(listResponse.status, 200, `tools/list failed HTTP ${listResponse.status}: ${listResponse.text.slice(0, 500)}`);
const listed = parseMcpResponse(listResponse.text, 'tools/list response');
const tools = listed.result?.tools || [];
const renderTools = tools.filter((tool) => tool.name === 'render_blender_glb');
assert.equal(renderTools.length, 1, 'production tools/list must expose exactly one render_blender_glb tool');
const tool = renderTools[0];
const schema = tool.inputSchema || tool.input_schema || {};
const props = schema.properties || {};
assert.deepEqual(schema.required, ['idempotencyKey', 'glbFile', 'scriptFile'], 'render_blender_glb required inputs changed');
assertHostFileSchema(props.glbFile, 'glbFile', 'model/gltf-binary');
assertHostFileSchema(props.scriptFile, 'scriptFile', 'text/x-python');
assert.equal(props.idempotencyKey?.type, 'string');
assert.equal(props.glbRef, undefined, 'direct host-file tool must not advertise glbRef');
assert.equal(props.scriptRef, undefined, 'direct host-file tool must not advertise scriptRef');
assert.equal(props.scriptText, undefined, 'direct host-file tool must not advertise scriptText');
assert.equal(tool.annotations?.idempotentHint, true, 'direct render tool must remain idempotent');
assert.equal(tool.annotations?.openWorldHint, false, 'direct render tool must not advertise open-world execution');
assert.equal(health.registryVersion, EXPECTED_REVISION, 'health registry revision must match deployed catalog revision');
assert.equal(health.connectorSchemaRevision, EXPECTED_REVISION, 'health schema revision must match deployed catalog revision');

const evidence = {
  ok: true,
  mcpUrl: args.mcpUrl,
  tokenSource: tokenInfo.source,
  tokenRefreshed: tokenInfo.refreshed,
  tokenLoadReason: tokenInfo.reason,
  registryVersion: health.registryVersion,
  connectorSchemaRevision: health.connectorSchemaRevision,
  toolCount: tools.length,
  renderBlenderGlb: {
    title: tool.title,
    description: tool.description,
    inputSchema: schema,
    annotations: tool.annotations || {},
    hasSecuritySchemes: Array.isArray(tool.securitySchemes) && tool.securitySchemes.length > 0,
  },
  checkedAt: new Date().toISOString(),
};
if (args.evidencePath) {
  fs.mkdirSync(path.dirname(args.evidencePath), {recursive: true});
  fs.writeFileSync(args.evidencePath, JSON.stringify(redact(evidence), null, 2) + '\n');
}
console.log(JSON.stringify(redact(evidence), null, 2));
