#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';

const DEFAULT_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const DEFAULT_EVIDENCE_DIR = 'tools/command_center_invokability_evidence';
const EXPECTED_TOOLS = [
  'command_center.health',
  'command_center.projects.resolve',
  'command_center.projects.get',
  'command_center.jobs.create',
  'command_center.jobs.get',
  'command_center.jobs.list',
  'command_center.jobs.cancel',
  'command_center.jobs.resume',
  'command_center.jobs.revise',
  'command_center.jobs.answer_question',
  'command_center.jobs.authorize_mutation',
  'command_center.jobs.get_summary',
  'command_center.jobs.get_events',
  'command_center.jobs.get_logs',
  'command_center.jobs.get_artifacts',
  'command_center.bucket.get_layout',
  'command_center.bucket.put_object',
  'command_center.bucket.get_object',
  'command_center.bucket.list_objects',
  'command_center.bucket.promote_skill',
  'command_center.workers.register_oneshot',
  'command_center.workers.list',
  'command_center.workers.get_capabilities',
];

function parseArgs(argv) {
  const args = {
    mcpUrl: DEFAULT_MCP_URL,
    evidenceDir: DEFAULT_EVIDENCE_DIR,
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    bearerToken: process.env.HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN || process.env.HOME_CENTER_MCP_BEARER_TOKEN || '',
    requireRealToken: false,
    createJob: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--require-real-token') args.requireRealToken = true;
    else if (arg === '--create-job') args.createJob = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_chatgpt_invokability_gate.mjs [--mcp-url URL] [--bearer-token TOKEN] [--require-real-token] [--create-job] [--run-id ID]');
      process.exit(0);
    }
  }
  return args;
}

function serviceBaseFromMcpUrl(mcpUrl) {
  const url = new URL(mcpUrl);
  if (!url.pathname.endsWith('/mcp')) throw new Error(`MCP URL must end with /mcp: ${mcpUrl}`);
  url.pathname = url.pathname.slice(0, -4).replace(/\/$/, '');
  url.search = '';
  url.hash = '';
  return url.toString();
}

async function fetchText(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  return {status: response.status, headers: Object.fromEntries(response.headers.entries()), text};
}

function parseJson(text, label) {
  try { return JSON.parse(text); } catch (err) { throw new Error(`${label} did not return JSON: ${String(text).slice(0, 300)}`); }
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  const payload = dataLines.length ? dataLines.join('\n') : text;
  return parseJson(payload, label);
}

async function postMcp(mcpUrl, body, token) {
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

async function callTool(mcpUrl, token, id, name, args = {}) {
  const response = await postMcp(mcpUrl, {jsonrpc: '2.0', id, method: 'tools/call', params: {name, arguments: args}}, token);
  const json = parseMcpResponse(response.text, `tools/call ${name}`);
  return {response, json};
}

function contentJson(toolResult, label) {
  const text = toolResult?.result?.content?.find((item) => item.type === 'text')?.text || '';
  return parseJson(text, label);
}

async function maybeLoadTokenFromFile() {
  const configPath = process.env.HOME_CENTER_COMMAND_CENTER_TOKEN_CONFIG || path.join(homedir(), '.config', 'home-center', 'command-center-mcp.json');
  if (!fs.existsSync(configPath)) return '';
  const config = parseJson(fs.readFileSync(configPath, 'utf8'), configPath);
  return config.accessToken || config.bearerToken || '';
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const base = serviceBaseFromMcpUrl(args.mcpUrl);
  const evidenceDir = path.resolve(args.evidenceDir);
  fs.mkdirSync(evidenceDir, {recursive: true});
  const checks = [];
  const add = (name, ok, detail = {}) => checks.push({name, ok: !!ok, ...detail});

  const root = await fetchText(`${base}/`);
  const rootJson = parseJson(root.text, 'Command Center root');
  add('root_live_no_frontend', root.status === 200 && rootJson.service === 'command-center-mcp' && rootJson.hasFrontend === false, {status: root.status, root: rootJson});

  const resource = await fetchText(`${base}/.well-known/oauth-protected-resource`);
  const resourceJson = parseJson(resource.text, 'protected resource metadata');
  const authServer = Array.isArray(resourceJson.authorization_servers) ? resourceJson.authorization_servers[0] : '';
  add('protected_resource_matches_mcp_url', resource.status === 200 && resourceJson.resource === args.mcpUrl, {status: resource.status, resource: resourceJson.resource});
  add('protected_resource_delegates_to_home_center', /^https:\/\/.*\/homeCenterMcp$/.test(authServer), {authorization_servers: resourceJson.authorization_servers});

  const authMeta = await fetchText(`${authServer}/.well-known/oauth-authorization-server`);
  const authJson = parseJson(authMeta.text, 'Home Center authorization metadata');
  add('authorization_metadata_resolves', authMeta.status === 200 && authJson.issuer === authServer, {status: authMeta.status, issuer: authJson.issuer});
  add('dynamic_registration_available', typeof authJson.registration_endpoint === 'string' && authJson.registration_endpoint.endsWith('/oauth/register'), {registration_endpoint: authJson.registration_endpoint});
  add('pkce_s256_supported', Array.isArray(authJson.code_challenge_methods_supported) && authJson.code_challenge_methods_supported.includes('S256'));

  const unauth = await fetchText(args.mcpUrl, {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'initialize', params: {}})});
  add('mcp_unauth_challenges', unauth.status === 401 && /resource_metadata=/.test(unauth.headers['www-authenticate'] || ''), {status: unauth.status, wwwAuthenticate: unauth.headers['www-authenticate'] || ''});

  const protocolToken = args.bearerToken || await maybeLoadTokenFromFile() || 'command-center-invokability-protocol-token';
  const init = await postMcp(args.mcpUrl, {jsonrpc: '2.0', id: 10, method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'command-center-invokability-gate', version: '1'}}}, protocolToken);
  add('mcp_initialize_200', init.status === 200, {status: init.status, contentType: init.headers['content-type']});
  await postMcp(args.mcpUrl, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}}, protocolToken);

  const listed = await postMcp(args.mcpUrl, {jsonrpc: '2.0', id: 11, method: 'tools/list', params: {}}, protocolToken);
  const listJson = parseMcpResponse(listed.text, 'tools/list');
  const names = (listJson.result?.tools || []).map((tool) => tool.name).sort();
  const missing = EXPECTED_TOOLS.filter((name) => !names.includes(name));
  add('tools_list_contains_command_center_surface', listed.status === 200 && missing.length === 0, {status: listed.status, count: names.length, missing});

  const health = await callTool(args.mcpUrl, protocolToken, 12, 'command_center.health', {});
  const healthJson = contentJson(health.json, 'command_center.health result');
  add('health_tool_invokable', health.response.status === 200 && healthJson.ok === true && healthJson.invokable === true, {status: health.response.status, health: healthJson});

  const bucketLayout = await callTool(args.mcpUrl, protocolToken, 13, 'command_center.bucket.get_layout', {});
  const bucketLayoutJson = contentJson(bucketLayout.json, 'command_center.bucket.get_layout result');
  const lanes = Object.keys(bucketLayoutJson.layout?.lanes || {});
  add('bucket_layout_invokable', bucketLayout.response.status === 200 && lanes.includes('memory/current-condensed') && lanes.includes('skills/promoted') && lanes.includes('notes/cross-repo'), {status: bucketLayout.response.status, lanes});

  const realToken = args.bearerToken || await maybeLoadTokenFromFile();
  let liveJob = null;
  if (args.requireRealToken && !realToken) add('real_token_available', false, {detail: 'Set HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN to a Home Center MCP OAuth access token.'});
  if (args.createJob && realToken) {
    const runId = args.runId.replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 60);
    const create = await callTool(args.mcpUrl, realToken, 20, 'command_center.jobs.create', {
      idempotencyKey: `invokability-${runId}`,
      projectId: 'home-center',
      title: 'Command Center ChatGPT invokability smoke',
      objective: 'Prove ChatGPT-visible Command Center job creation and readback on the live MCP surface.',
      acceptanceCriteria: ['Job created through Command Center MCP', 'Job summary can be read back'],
      workerRequirements: ['codex'],
      mutationPolicy: {editFiles: 'deny', runTests: 'deny', commit: 'deny', push: 'deny', merge: 'deny'},
    });
    const created = contentJson(create.json, 'jobs.create result');
    const jobId = created.job?.jobId || '';
    const get = await callTool(args.mcpUrl, realToken, 21, 'command_center.jobs.get', {jobId});
    const summary = await callTool(args.mcpUrl, realToken, 22, 'command_center.jobs.get_summary', {jobId});
    liveJob = {jobId, create: contentJson(create.json, 'jobs.create result'), get: contentJson(get.json, 'jobs.get result'), summary: contentJson(summary.json, 'jobs.get_summary result')};
    add('live_job_create_readback', !!jobId && liveJob.get.job?.jobId === jobId && liveJob.summary.jobId === jobId, {jobId});
  } else if (args.createJob) {
    add('live_job_create_readback', false, {detail: 'No real Home Center MCP OAuth bearer token was available.'});
  }

  const result = {ok: checks.every((check) => check.ok), mcpUrl: args.mcpUrl, base, checks, toolNames: names, liveJob, generatedAt: new Date().toISOString()};
  const evidencePath = path.join(evidenceDir, `command_center_invokability_${args.runId}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ok: result.ok, evidencePath, failed: checks.filter((check) => !check.ok)}, null, 2));
  if (!result.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
