#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const DEFAULT_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeBridgeMcp/mcp';
const EXPECTED_TOOLS = [
  'health', 'drive_search', 'drive_read', 'docs_append',
  'capabilities', 'auth_status', 'storage_status', 'audit_status',
  'drive_list_folder', 'drive_get_metadata', 'drive_create_folder', 'docs_create',
  'drive_move', 'drive_rename', 'drive_plan_organize', 'drive_execute_plan',
  'index_folder', 'index_status', 'drive_workflow_run', 'recovery_checkpoint', 'recovery_status', 'audit_log', 'audit_get',
];

function parseArgs(argv) {
  const args = {url: DEFAULT_URL, ui: true, uiWaitMs: 90000, runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--url') args.url = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--ui') args.ui = true;
    else if (arg === '--no-ui') args.ui = false;
    else if (arg === '--ui-wait-ms') args.uiWaitMs = Number(argv[++i]);
    else if (arg === '--help') {
      console.log('Usage: node tools/chatgpt_connector_acceptance_gate.mjs [--url MCP_URL] [--ui|--no-ui] [--ui-wait-ms N] [--run-id ID]');
      process.exit(0);
    }
  }
  return args;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, {recursive: true});
}

async function fetchText(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  return {status: response.status, headers: Object.fromEntries(response.headers.entries()), text};
}

function parseJson(text, label) {
  try { return JSON.parse(text); } catch (err) { throw new Error(`${label} did not return JSON: ${String(text).slice(0, 300)}`); }
}

function parseSse(text) {
  const data = text.split(/\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim()).join('\n');
  return parseJson(data || text, 'MCP SSE');
}

function serviceBaseFromMcpUrl(mcpUrl) {
  const url = new URL(mcpUrl);
  if (!url.pathname.endsWith('/mcp')) throw new Error(`MCP URL must end with /mcp: ${mcpUrl}`);
  url.pathname = url.pathname.slice(0, -4).replace(/\/$/, '');
  url.search = '';
  url.hash = '';
  return url.toString();
}

async function postMcp(mcpUrl, body, token = 'acceptance-probe-token') {
  return fetchText(mcpUrl, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json',
      accept: 'application/json, text/event-stream',
    },
    body: JSON.stringify(body),
  });
}

// Protocol preflight: backend checks that are necessary but not sufficient for ChatGPT acceptance.
async function protocolPreflight(mcpUrl) {
  const base = serviceBaseFromMcpUrl(mcpUrl);
  const checks = [];
  const add = (name, ok, detail = {}) => checks.push({name, ok: !!ok, ...detail});

  const root = await fetchText(`${base}/`);
  add('root_ok', root.status === 200, {status: root.status});

  const resource = parseJson((await fetchText(`${base}/oauth-protected-resource-v2`)).text, 'resource metadata');
  add('resource_matches_mcp_url', resource.resource === mcpUrl, {resource: resource.resource});
  add('resource_auth_server_matches_base', Array.isArray(resource.authorization_servers) && resource.authorization_servers.includes(base), {authorization_servers: resource.authorization_servers});

  const authMeta = parseJson((await fetchText(`${base}/.well-known/oauth-authorization-server`)).text, 'authorization metadata');
  add('issuer_matches_base', authMeta.issuer === base, {issuer: authMeta.issuer});
  add('registration_endpoint_present', typeof authMeta.registration_endpoint === 'string' && authMeta.registration_endpoint.includes('/oauth/register'), {registration_endpoint: authMeta.registration_endpoint});
  add('pkce_s256_supported', Array.isArray(authMeta.code_challenge_methods_supported) && authMeta.code_challenge_methods_supported.includes('S256'));
  add('refresh_token_supported', Array.isArray(authMeta.grant_types_supported) && authMeta.grant_types_supported.includes('refresh_token'), {grant_types_supported: authMeta.grant_types_supported});

  const openid = parseJson((await fetchText(`${base}/.well-known/openid-configuration`)).text, 'openid metadata');
  add('openid_userinfo_present', typeof openid.userinfo_endpoint === 'string' && openid.userinfo_endpoint.includes('/oauth/userinfo'), {userinfo_endpoint: openid.userinfo_endpoint});

  const unauth = await fetchText(mcpUrl, {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'initialize', params: {}})});
  add('mcp_unauth_challenges', unauth.status === 401 && /resource_metadata=/.test(unauth.headers['www-authenticate'] || ''), {status: unauth.status, wwwAuthenticate: unauth.headers['www-authenticate'] || ''});

  const init = await postMcp(mcpUrl, {jsonrpc: '2.0', id: 1, method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'home-bridge-acceptance-gate', version: '1'}}});
  add('mcp_initialize_200', init.status === 200, {status: init.status, contentType: init.headers['content-type']});
  await postMcp(mcpUrl, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}});
  const listed = await postMcp(mcpUrl, {jsonrpc: '2.0', id: 2, method: 'tools/list', params: {}});
  add('tools_list_200', listed.status === 200, {status: listed.status, contentType: listed.headers['content-type']});
  const listJson = parseSse(listed.text);
  const tools = listJson.result?.tools || [];
  const names = tools.map((tool) => tool.name);
  const missingTools = EXPECTED_TOOLS.filter((name) => !names.includes(name));
  const extraTools = names.filter((name) => !EXPECTED_TOOLS.includes(name));
  add('tool_names_exact_expected_count', missingTools.length === 0 && extraTools.length === 0 && names.length === EXPECTED_TOOLS.length, {count: names.length, missingTools, extraTools});
  const missingSecurity = tools.filter((tool) => !tool.securitySchemes || !(tool._meta && tool._meta.securitySchemes)).map((tool) => tool.name);
  add('all_tools_declare_security', missingSecurity.length === 0, {missingSecurity});
  const badSchemas = tools.filter((tool) => !tool.inputSchema || tool.inputSchema.type !== 'object').map((tool) => tool.name);
  add('all_tools_have_object_schema', badSchemas.length === 0, {badSchemas});

  return {base, checks, ok: checks.every((check) => check.ok), toolNames: names, toolCount: names.length, sampleTool: tools.find((tool) => tool.name === 'drive_search') || null};
}

function runCommand(command, args, options = {}) {
  const proc = spawnSync(command, args, {encoding: 'utf8', timeout: options.timeout || 20000});
  return {status: proc.status, stdout: proc.stdout || '', stderr: proc.stderr || '', error: proc.error ? String(proc.error.message || proc.error) : ''};
}

function findRish() {
  const candidates = [path.join(process.env.HOME || '', 'bin/rish'), '/sdcard/rish', '/storage/emulated/0/rish'];
  return candidates.find((candidate) => candidate && fs.existsSync(candidate)) || '';
}

function rish(command, timeout = 20000) {
  const bin = findRish();
  if (!bin) return {status: 127, stdout: '', stderr: 'missing Shizuku rish helper', error: ''};
  return runCommand(bin, ['-c', command], {timeout});
}

function extractUiText(xml) {
  const values = [];
  for (const attr of ['text', 'content-desc']) {
    const re = new RegExp(`${attr}=(['"])(.*?)\\1`, 'gs');
    for (const match of xml.matchAll(re)) {
      const value = String(match[2] || '').replace(/&quot;/g, '"').replace(/&amp;/g, '&').trim();
      if (value) values.push(value);
    }
  }
  return values.join('\n');
}

// Real ChatGPT UI gate: fails if the visible product still says disconnected.
async function uiGate(mcpUrl, waitMs, artifactDir, runId) {
  const checks = [];
  const add = (name, ok, detail = {}) => checks.push({name, ok: !!ok, ...detail});
  const opened = runCommand('termux-open-url', ['https://chatgpt.com/'], {timeout: 10000});
  add('opened_chatgpt_url', opened.status === 0, {status: opened.status, stderr: opened.stderr, error: opened.error});
  const deadline = Date.now() + Math.max(10000, waitMs || 90000);
  const dumps = [];
  let finalText = '';
  let finalXmlPath = '';
  while (Date.now() < deadline) {
    const stamp = `${runId}_${Date.now()}`;
    const shellPath = `/sdcard/Download/HomeCenter/chatgpt_connector_${stamp}.xml`;
    const readPath = `/storage/emulated/0/Download/HomeCenter/chatgpt_connector_${stamp}.xml`;
    const dump = rish(`uiautomator dump ${shellPath}`, 25000);
    let xml = '';
    if (dump.status === 0 && fs.existsSync(readPath)) xml = fs.readFileSync(readPath, 'utf8');
    const text = extractUiText(xml);
    dumps.push({path: readPath, status: dump.status, stderr: dump.stderr.slice(0, 300), textSample: text.slice(0, 2000)});
    finalText = text;
    finalXmlPath = readPath;
    const lower = text.toLowerCase();
    const mentionsBridge = /home bridge|home center drive bridge|drive bridge|homebridgemcp|home center bridge/i.test(text);
    const disconnected = /disconnected|couldn't connect|could not connect|problem connecting|connection failed|reconnect/i.test(text);
    const connected = /connected|enabled/i.test(text);
    if (mentionsBridge && disconnected) break;
    if (mentionsBridge && connected && !disconnected) break;
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  const lower = finalText.toLowerCase();
  const mentionsBridge = /home bridge|home center drive bridge|drive bridge|homebridgemcp|home center bridge/i.test(finalText);
  const disconnected = /disconnected|couldn't connect|could not connect|problem connecting|connection failed|reconnect/i.test(finalText);
  const connected = /connected|enabled/i.test(finalText);
  add('chatgpt_ui_mentions_bridge', mentionsBridge, {xmlPath: finalXmlPath});
  add('chatgpt_ui_not_disconnected', !disconnected, {xmlPath: finalXmlPath});
  add('chatgpt_ui_connected', mentionsBridge && connected && !disconnected, {xmlPath: finalXmlPath});
  fs.writeFileSync(path.join(artifactDir, `chatgpt_connector_ui_${runId}.json`), JSON.stringify({mcpUrl, waitMs, checks, ok: checks.every((check) => check.ok), dumps, finalText}, null, 2));
  return {ok: checks.every((check) => check.ok), checks, finalTextSample: finalText.slice(0, 4000), finalXmlPath, dumpCount: dumps.length};
}

function parseCloudLogOutput(proc) {
  if (proc.status !== 0) return {ok: false, error: proc.stderr || proc.error, entries: []};
  try { return {ok: true, entries: JSON.parse(proc.stdout || '[]'), error: ''}; }
  catch (err) { return {ok: false, error: String(err), raw: proc.stdout.slice(0, 2000), entries: []}; }
}

function connectorEventCount(entries) {
  return entries.filter((entry) => {
    const message = entry?.jsonPayload?.message || entry?.textPayload || '';
    const event = entry?.jsonPayload?.event || '';
    return /mcp_connector_/.test(String(message)) || /mcp_connector_/.test(String(event));
  }).length;
}

function connectorLogState(entries = []) {
  const events = entries.map((entry) => String(entry?.jsonPayload?.event || entry?.jsonPayload?.message || entry?.textPayload || ''));
  const methods = entries.map((entry) => String(entry?.jsonPayload?.mcpMethod || ''));
  const tokenSuccess = events.includes('mcp_connector_token_success') || events.includes('mcp_connector_token_refresh_success');
  const userinfoSuccess = events.includes('mcp_connector_userinfo_success');
  const mcpActive = events.includes('mcp_connector_mcp_success') || methods.includes('initialize') || methods.includes('tools/call');
  return {
    connected: mcpActive,
    mcpActive,
    oauthOnlyDead: tokenSuccess && userinfoSuccess && !mcpActive,
    tokenSuccess,
    userinfoSuccess,
    toolCalls: entries.filter((entry) => entry?.jsonPayload?.mcpMethod === 'tools/call').map((entry) => ({toolName: entry.jsonPayload.toolName || '', requestId: entry.jsonPayload.requestId || '', targetId: entry.jsonPayload.targetId || '', targetLabel: entry.jsonPayload.targetLabel || ''})),
  };
}

function cloudLogs(serviceName, sinceIso) {
  const baseFilter = `resource.type="cloud_run_revision" AND resource.labels.service_name="${serviceName}" AND timestamp>="${sinceIso}"`;
  const filters = [
    `${baseFilter} AND ("mcp_connector_" OR jsonPayload.message:"mcp_connector_" OR jsonPayload.event:"mcp_connector_")`,
    baseFilter,
  ];
  let best = {ok: false, error: 'not run', entries: []};
  for (let attempt = 0; attempt < 4; attempt += 1) {
    for (const filter of filters) {
      const proc = runCommand('gcloud', ['logging', 'read', filter, '--project=home-center-dclar', '--limit=120', '--format=json'], {timeout: 30000});
      const parsed = parseCloudLogOutput(proc);
      parsed.filter = filter;
      parsed.attempt = attempt + 1;
      if (parsed.ok && parsed.entries.length > (best.entries?.length || 0)) best = parsed;
      if (parsed.ok && connectorEventCount(parsed.entries) > 0) return {...parsed, connectorEventCount: connectorEventCount(parsed.entries)};
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1500);
  }
  return {...best, connectorEventCount: connectorEventCount(best.entries || [])};
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const artifactDir = path.join(ROOT, 'tools', 'chatgpt_connector_evidence');
  ensureDir(artifactDir);
  const startedAt = new Date().toISOString();
  const serviceName = new URL(args.url).pathname.split('/').filter(Boolean)[0].toLowerCase();
  const protocol = await protocolPreflight(args.url);
  const ui = args.ui ? await uiGate(args.url, args.uiWaitMs, artifactDir, args.runId) : {ok: null, skipped: true};
  const logs = cloudLogs(serviceName, startedAt);
  const logState = connectorLogState(logs.entries || []);
  const evidence = {runId: args.runId, startedAt, finishedAt: new Date().toISOString(), mcpUrl: args.url, serviceName, protocol, ui, logsSummary: {ok: logs.ok, count: logs.entries?.length || 0, error: logs.error || '', state: logState}, logs};
  const evidencePath = path.join(artifactDir, `chatgpt_connector_acceptance_${args.runId}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(evidence, null, 2));
  const ok = protocol.ok && (args.ui ? ui.ok : true);
  console.log(`ChatGPT connector acceptance gate: ${ok ? 'OK' : 'FAILED'} evidence=${evidencePath}`);
  if (!protocol.ok) console.log(`Protocol failures: ${protocol.checks.filter((check) => !check.ok).map((check) => check.name).join(', ')}`);
  if (args.ui && !ui.ok) console.log(`UI failures: ${ui.checks.filter((check) => !check.ok).map((check) => check.name).join(', ')}`);
  if (!ok) process.exit(1);
}

main().catch((err) => {
  console.error(`ChatGPT connector acceptance gate failed: ${err.stack || err}`);
  process.exit(1);
});
