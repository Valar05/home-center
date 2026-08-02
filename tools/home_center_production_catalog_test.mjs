#!/usr/bin/env node
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';
import {execFileSync} from 'node:child_process';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const manifestPath = process.env.HOME_CENTER_PUBLIC_MANIFEST_PATH || path.join(root, 'contracts/home-center-public-tool-manifest.v1.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const mcpUrl = process.env.HOME_CENTER_MCP_URL || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const expectedCommit = process.env.HOME_CENTER_EXPECTED_SOURCE_COMMIT || execFileSync('git', ['rev-parse', 'HEAD'], {cwd: root, encoding: 'utf8'}).trim();
const tokenConfig = process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json');

function parseJson(text, label) {
  try { return JSON.parse(text); } catch { throw new Error(label + ' did not return JSON: ' + String(text || '').slice(0, 500)); }
}
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}
function canonicalHash(value) { return crypto.createHash('sha256').update(JSON.stringify(stable(value))).digest('hex'); }
function parseMcp(text, label) {
  const data = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  return parseJson(data.length ? data.join('\n') : text, label);
}
function textToolJson(payload, label) {
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '';
  return parseJson(text, label);
}
async function refreshAccessToken(refreshToken, gatewayBase, source) {
  const response = await fetch((gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net') + '/termuxTokenRefresh', {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({refreshToken})});
  const body = parseJson(await response.text(), 'termuxTokenRefresh');
  if (!response.ok || !body.ok || !body.access_token) throw new Error('Home Center token refresh failed with HTTP ' + response.status);
  return {token: body.access_token, refreshed: true, source, tokenType: body.token_type || 'Bearer', expiresIn: Number(body.expires_in || 0)};
}
async function bearerToken() {
  if (process.env.HOME_CENTER_MCP_BEARER_TOKEN) return {token: process.env.HOME_CENTER_MCP_BEARER_TOKEN, refreshed: false, source: 'environment'};
  if (process.env.HOME_CENTER_MCP_REFRESH_TOKEN) return refreshAccessToken(process.env.HOME_CENTER_MCP_REFRESH_TOKEN, process.env.HOME_CENTER_GATEWAY_BASE, 'environment-refresh-token');
  if (!fs.existsSync(tokenConfig)) throw new Error('Authenticated tools/list requires HOME_CENTER_MCP_BEARER_TOKEN, HOME_CENTER_MCP_REFRESH_TOKEN, or ' + tokenConfig);
  const current = parseJson(fs.readFileSync(tokenConfig, 'utf8'), tokenConfig);
  if (current.accessToken && Number(current.expiresAtMs || 0) > Date.now() + 60000) return {token: current.accessToken, refreshed: false, source: tokenConfig};
  if (!current.refreshToken) throw new Error('Home Center token config has no usable access or refresh token.');
  const refreshed = await refreshAccessToken(current.refreshToken, current.gatewayBase, tokenConfig);
  const next = {...current, accessToken: refreshed.token, tokenType: refreshed.tokenType, expiresAtMs: Date.now() + refreshed.expiresIn * 1000, refreshedAt: new Date().toISOString()};
  fs.writeFileSync(tokenConfig, JSON.stringify(next, null, 2) + '\n', {mode: 0o600});
  return refreshed;
}
async function post(token, body) {
  const response = await fetch(mcpUrl, {method: 'POST', headers: {authorization: 'Bearer ' + token, 'content-type': 'application/json', accept: 'application/json, text/event-stream'}, body: JSON.stringify(body)});
  const text = await response.text();
  assert.equal(response.status, 200, 'MCP HTTP ' + response.status + ': ' + text.slice(0, 500));
  return parseMcp(text, body.method || 'MCP response');
}

const auth = await bearerToken();
await post(auth.token, {jsonrpc: '2.0', id: 'init', method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'home-center-production-catalog-test', version: '1'}}});
const readiness = textToolJson(await post(auth.token, {jsonrpc: '2.0', id: 'ready', method: 'tools/call', params: {name: 'readiness', arguments: {}}}), 'readiness');
assert.equal(readiness.ready, true);
assert.equal(readiness.releaseIdentity?.sourceCommit, expectedCommit);
assert.equal(readiness.releaseIdentity?.sourceRef, 'refs/heads/main');
assert.equal(readiness.releaseIdentity?.publicManifestSha256, manifest.manifestSha256);
const capabilities = textToolJson(await post(auth.token, {jsonrpc: '2.0', id: 'caps', method: 'tools/call', params: {name: 'capabilities', arguments: {}}}), 'capabilities');
const retiredCall = textToolJson(await post(auth.token, {jsonrpc: '2.0', id: 'retired-foundry', method: 'tools/call', params: {name: 'drive_operation', arguments: {operation: 'foundry.asset.run', args: {}}}}), 'retired Foundry call');
assert.equal(retiredCall.completed, false); assert.equal(retiredCall.error?.code, 'CAPABILITY_RETIRED'); assert.equal(retiredCall.error?.dispatched, false); assert.ok(retiredCall.error?.replacement?.includes('blender.workspace.mutate'));
assert.equal(capabilities.registryVersion, manifest.registryRevision);
assert.deepEqual(capabilities.releaseIdentity, readiness.releaseIdentity);
const listed = await post(auth.token, {jsonrpc: '2.0', id: 'tools', method: 'tools/list', params: {}});
const tools = [...(listed.result?.tools || [])].sort((a, b) => a.name.localeCompare(b.name));
assert.deepEqual(stable(tools), stable(manifest.entries.map((entry) => entry.tool)));
assert.equal(canonicalHash(tools), manifest.canonicalToolsSha256);
assert.equal(tools.length, manifest.toolCount);
assert.equal(tools.some((tool) => tool.name === 'render_blender_glb'), false);
assert.equal(tools.some((tool) => /foundry/i.test(tool.name)), false);
for (const name of ['drive_operation', 'drive_ingest_file', 'storage_ingest_artifact']) assert(tools.some((tool) => tool.name === name), 'missing production tool ' + name);
const capabilityText = JSON.stringify(capabilities);
for (const operation of ['blender.workspace.create','blender.workspace.inspect','blender.workspace.history','blender.workspace.mutate','blender.workspace.restore','blender.workspace.render','blender.workspace.export','blender.workspace.status']) assert(capabilityText.includes(operation), 'dynamic Blender workspace operation missing: ' + operation);
const renderCapability=capabilities.operationSurfaces?.drive?.deprecatedOperations?.['blender.workspace.render'];assert.equal(renderCapability?.deprecated,true);assert.equal(renderCapability?.status,'deprecated');assert.equal(renderCapability?.retainedForCompatibility,true);assert.match(renderCapability?.agentPolicy || '',/Do not select/);
for (const retired of ['foundry.asset.inspect','foundry.asset.run','foundry.asset.status','foundry.asset.promote']) assert.equal(capabilityText.includes(retired), false, 'retired Foundry operation advertised: ' + retired);
for (const retired of ['command_center.jobs.', 'command_center.workers.', 'command_center.agents.', 'render_blender_glb']) assert.equal(capabilityText.includes(retired), false, 'retired capability advertised: ' + retired);
console.log(JSON.stringify({ok: true, mcpUrl, tokenSource: auth.source, tokenRefreshed: auth.refreshed, releaseIdentity: readiness.releaseIdentity, registryRevision: capabilities.registryVersion, toolCount: tools.length, canonicalToolsSha256: canonicalHash(tools), publicManifestSha256: manifest.manifestSha256, dynamicBlenderWorkspace: true, retiredExecutionAbsent: true}, null, 2));
