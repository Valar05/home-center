#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const DEFAULT_HOME_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const DEFAULT_EVIDENCE_DIR = 'tools/command_center_invokability_evidence';

function parseArgs(argv) {
  const args = {
    mcpUrl: DEFAULT_HOME_MCP_URL,
    evidenceDir: DEFAULT_EVIDENCE_DIR,
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    bearerToken: process.env.HOME_CENTER_MCP_BEARER_TOKEN || process.env.HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN || 'home-center-command-center-bridge-protocol-token',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_home_bridge_invokability_gate.mjs [--mcp-url URL] [--run-id ID] [--evidence-dir DIR] [--bearer-token TOKEN]');
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

function toolContentJson(payload, label) {
  if (payload?.error) return {mcpError: payload.error};
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '';
  if (/^MCP error\b/.test(text)) return {mcpErrorText: text};
  return parseJson(text, label);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const evidenceDir = path.resolve(args.evidenceDir);
  fs.mkdirSync(evidenceDir, {recursive: true});
  const checks = [];
  const add = (name, ok, detail = {}) => checks.push({name, ok: !!ok, ...detail});

  const unauth = await fetch(args.mcpUrl, {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'initialize', params: {}})});
  add('home_mcp_requires_auth', unauth.status === 401, {status: unauth.status, wwwAuthenticate: unauth.headers.get('www-authenticate') || ''});

  const init = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 10,
    method: 'initialize',
    params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'command-center-home-bridge-gate', version: '1'}},
  });
  add('home_mcp_initialize_200', init.status === 200, {status: init.status, contentType: init.headers['content-type'] || ''});
  await postMcp(args.mcpUrl, args.bearerToken, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}}).catch(() => null);

  const listed = await postMcp(args.mcpUrl, args.bearerToken, {jsonrpc: '2.0', id: 11, method: 'tools/list', params: {}});
  const listJson = parseMcpResponse(listed.text, 'home tools/list');
  const toolNames = (listJson.result?.tools || []).map((tool) => tool.name).sort();
  add('home_tools_list_contains_command_center_operation', listed.status === 200 && toolNames.includes('command_center_operation'), {status: listed.status, count: toolNames.length, toolNames});
  add('home_tools_list_contains_drive_operation', listed.status === 200 && toolNames.includes('drive_operation'), {status: listed.status});

  const capabilities = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 14,
    method: 'tools/call',
    params: {name: 'capabilities', arguments: {}},
  });
  const capabilitiesJson = parseMcpResponse(capabilities.text, 'home capabilities');
  const capabilitiesContent = toolContentJson(capabilitiesJson, 'home capabilities content');
  const driveOps = capabilitiesContent.operationRegistry?.operations || {};
  add('drive_operation_registry_contains_command_center_followup', capabilities.status === 200 && !!driveOps['command_center.jobs.create_followup'] && !!driveOps['command_center.jobs.get_handoff'], {status: capabilities.status, registryVersion: capabilitiesContent.operationRegistry?.version || ''});

  const health = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 12,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation: 'health', args: {}}},
  });
  const healthJson = parseMcpResponse(health.text, 'command_center_operation health');
  const healthContent = toolContentJson(healthJson, 'command_center_operation health content');
  add('command_center_operation_health_invokable', health.status === 200 && healthContent.result?.ok === true && healthContent.result?.invokable === true, {status: health.status, content: healthContent});

  const driveHealth = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 15,
    method: 'tools/call',
    params: {name: 'drive_operation', arguments: {operation: 'command_center.health', args: {}}},
  });
  const driveHealthJson = parseMcpResponse(driveHealth.text, 'drive_operation command_center.health');
  const driveHealthContent = toolContentJson(driveHealthJson, 'drive_operation command_center.health content');
  add('drive_operation_command_center_health_invokable', driveHealth.status === 200 && driveHealthContent.result?.result?.ok === true && driveHealthContent.result?.result?.invokable === true, {status: driveHealth.status, content: driveHealthContent});

  const bucket = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 13,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation: 'bucket.get_layout', args: {}}},
  });
  const bucketJson = parseMcpResponse(bucket.text, 'command_center_operation bucket layout');
  const bucketContent = toolContentJson(bucketJson, 'command_center_operation bucket layout content');
  const lanes = Object.keys(bucketContent.result?.layout?.lanes || {});
  add('command_center_operation_bucket_layout_invokable', bucket.status === 200 && lanes.includes('memory/current-condensed') && lanes.includes('skills/promoted') && lanes.includes('notes/cross-repo'), {status: bucket.status, lanes});

  const result = {
    ok: checks.every((check) => check.ok),
    mcpUrl: args.mcpUrl,
    checks,
    toolNames,
    generatedAt: new Date().toISOString(),
  };
  const evidencePath = path.join(evidenceDir, `command_center_home_bridge_invokability_${args.runId}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ok: result.ok, evidencePath, failed: checks.filter((check) => !check.ok)}, null, 2));
  if (!result.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
