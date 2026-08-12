#!/usr/bin/env node
import assert from 'node:assert/strict';

const mcpUrl = process.env.HOME_CENTER_MCP_URL || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const token = process.env.HOME_CENTER_MCP_BEARER_TOKEN;
if (!token) throw new Error('HOME_CENTER_MCP_BEARER_TOKEN is required for live verification.');

function parseJson(text, label) {
  try { return JSON.parse(text); } catch { throw new Error(label + ' did not return JSON: ' + String(text || '').slice(0, 500)); }
}
function parseMcp(text, label) {
  const data = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  return parseJson(data.length ? data.join('\n') : text, label);
}
function textToolJson(payload, label) {
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '';
  return parseJson(text, label);
}
async function post(body) {
  const response = await fetch(mcpUrl, {
    method: 'POST',
    headers: {authorization: 'Bearer ' + token, 'content-type': 'application/json', accept: 'application/json, text/event-stream'},
    body: JSON.stringify(body),
  });
  const text = await response.text();
  assert.equal(response.status, 200, 'MCP HTTP ' + response.status + ': ' + text.slice(0, 500));
  return parseMcp(text, body.method || 'MCP response');
}

await post({jsonrpc: '2.0', id: 'init', method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'time-now-live-test', version: '1'}}});
const caps = textToolJson(await post({jsonrpc: '2.0', id: 'caps', method: 'tools/call', params: {name: 'capabilities', arguments: {}}}), 'capabilities');
const ops = caps?.operationSurfaces?.drive?.operations || [];
assert(ops.includes('time.now'), 'live drive_operation registry does not advertise time.now');

const first = textToolJson(await post({jsonrpc: '2.0', id: 'time-1', method: 'tools/call', params: {name: 'drive_operation', arguments: {operation: 'time.now', args: {}}}}), 'time.now #1');
await new Promise((resolve) => setTimeout(resolve, 25));
const second = textToolJson(await post({jsonrpc: '2.0', id: 'time-2', method: 'tools/call', params: {name: 'drive_operation', arguments: {operation: 'time.now', args: {}}}}), 'time.now #2');

assert.equal(first.operation, 'time.now');
assert.equal(first.completed, true);
assert.equal(second.operation, 'time.now');
assert.equal(second.completed, true);
assert.match(first.result?.utcIso || '', /^\d{4}-\d{2}-\d{2}T/);
assert(Number.isFinite(first.result?.unixMs));
assert(Number.isFinite(second.result?.unixMs));
assert(second.result.unixMs > first.result.unixMs, 'time.now did not return a fresh later sample');

console.log(JSON.stringify({ok: true, mcpUrl, operation: 'time.now', registryAdvertised: true, first: first.result, second: second.result}, null, 2));
