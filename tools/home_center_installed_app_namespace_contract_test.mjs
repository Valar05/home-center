#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
const {createHomeCenterMcpApp} = require('../functions/home_center_mcp.js');

const app = createHomeCenterMcpApp({
  google: {},
  admin: {firestore() { return {}; }},
  googleClientId: () => 'configured',
  googleClientSecret: () => 'configured',
});
const server = await new Promise((resolve) => {
  const listening = app.listen(0, '127.0.0.1', () => resolve(listening));
});
const close = () => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
const {port} = server.address();
const url = `http://127.0.0.1:${port}/mcp`;
const headers = {
  authorization: 'Bearer installed-app-contract-test',
  'content-type': 'application/json',
  accept: 'application/json, text/event-stream',
};

async function post(body) {
  const response = await fetch(url, {method: 'POST', headers, body: JSON.stringify(body)});
  const text = await response.text();
  assert.equal(response.status, 200, text);
  return text;
}

try {
  await post({jsonrpc: '2.0', id: 1, method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'installed-app-contract-test', version: '1'}}});
  const prefixedHealth = await post({jsonrpc: '2.0', id: 2, method: 'tools/call', params: {name: 'home_center_drive.health', arguments: {}}});
  assert.match(prefixedHealth, /home-center-drive-bridge/);
  const prefixedCapabilities = await post({jsonrpc: '2.0', id: 3, method: 'tools/call', params: {name: 'home_center_drive.capabilities', arguments: {}}});
  assert.match(prefixedCapabilities, /foundry\.asset\.run/);
  const canonicalHealth = await post({jsonrpc: '2.0', id: 4, method: 'tools/call', params: {name: 'health', arguments: {}}});
  assert.match(canonicalHealth, /home-center-drive-bridge/);
  const foreignPrefix = await post({jsonrpc: '2.0', id: 5, method: 'tools/call', params: {name: 'other_app.health', arguments: {}}});
  assert.match(foreignPrefix, /Tool other_app\.health not found/);
  console.log(JSON.stringify({ok: true, normalized: ['home_center_drive.health', 'home_center_drive.capabilities'], canonicalPreserved: true, foreignPrefixRejected: true}));
} finally {
  await close();
  delete process.env.HOME_CENTER_MCP_EXTENDED_TOOLS;
}
