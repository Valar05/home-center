#!/usr/bin/env node
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
const {createHomeCenterMcpServer, HOME_CENTER_CONNECTOR_SCHEMA_REVISION} = require('../functions/home_center_mcp.js');

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}
function canonicalBytes(value) { return Buffer.from(JSON.stringify(stable(value))); }
function sha256(value) { return crypto.createHash('sha256').update(Buffer.isBuffer(value) ? value : canonicalBytes(value)).digest('hex'); }
function pretty(value) { return JSON.stringify(stable(value), null, 2) + '\n'; }
function resolveLocalSchema(root, schema) {
  const ref = schema?.$ref;
  if (typeof ref !== 'string' || !ref.startsWith('#/$defs/')) return schema || {};
  const key = decodeURIComponent(ref.slice('#/$defs/'.length).replace(/~1/g, '/').replace(/~0/g, '~'));
  return root?.$defs?.[key] || schema || {};
}
function fileBearingFields(tool) {
  const inputSchema = tool?.inputSchema || {};
  const properties = inputSchema.properties || {};
  const openAiFileParams = new Set(tool?._meta?.['openai/fileParams'] || []);
  return Object.entries(properties)
    .filter(([field, schema]) => {
      const resolved = resolveLocalSchema(inputSchema, schema);
      return openAiFileParams.has(field) || (resolved && (resolved.format === 'binary' || resolved.contentMediaType || resolved.contentEncoding));
    })
    .map(([field, schema]) => {
      const resolved = resolveLocalSchema(inputSchema, schema);
      return {
        field,
        binding: openAiFileParams.has(field) ? 'openai/fileParams' : 'legacy-binary-schema',
        schemaType: resolved?.type || '',
        requiredProperties: resolved?.required || [],
      };
    });
}

const server = createHomeCenterMcpServer({google: {}, admin: {firestore() { return {}; }}, googleClientId: () => 'configured', googleClientSecret: () => 'configured'});
const handler = server.server._requestHandlers.get('tools/list');
assert.equal(typeof handler, 'function');
const response = await handler({method: 'tools/list', params: {}}, {});
const tools = stable([...(response?.tools || [])].sort((a, b) => a.name.localeCompare(b.name)));
const body = {
  schemaVersion: 'home-center.public-tool-manifest.v1',
  registryRevision: HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
  toolCount: tools.length,
  canonicalToolsSha256: sha256(tools),
  entries: tools.map((tool) => ({
    name: tool.name,
    description: tool.description || '',
    annotations: tool.annotations || {},
    inputSchema: tool.inputSchema || {},
    fileBearingFields: fileBearingFields(tool),
    schemaHash: sha256(tool.inputSchema || {}),
    tool,
  })),
};
const manifest = {...body, manifestSha256: sha256(body)};
const baselinePath = path.join(root, 'contracts/home-center-top-level-mcp.v1.json');
const manifestPath = path.join(root, 'contracts/home-center-public-tool-manifest.v1.json');
const expectedBaseline = pretty(tools);
const expectedManifest = pretty(manifest);
const check = process.argv.includes('--check');
if (check) {
  assert.equal(fs.readFileSync(baselinePath, 'utf8'), expectedBaseline, 'top-level MCP baseline is stale; run the manifest generator intentionally');
  assert.equal(fs.readFileSync(manifestPath, 'utf8'), expectedManifest, 'public tool manifest is stale; run the manifest generator intentionally');
} else {
  fs.writeFileSync(baselinePath, expectedBaseline);
  fs.writeFileSync(manifestPath, expectedManifest);
}
console.log(JSON.stringify({ok: true, check, registryRevision: manifest.registryRevision, toolCount: manifest.toolCount, canonicalToolsSha256: manifest.canonicalToolsSha256, manifestSha256: manifest.manifestSha256}));