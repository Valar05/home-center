#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';

const DEFAULT_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const DEFAULT_EVIDENCE_DIR = 'tools/command_center_invokability_evidence';
const EXPECTED_TOOLS = [
  'command_center_operation',
  'command_center.health',
  'command_center.readiness',
  'command_center.capabilities',
  'command_center.projects.resolve',
  'command_center.projects.get',
  'command_center.render.blender_glb',
  'command_center.projects.upsert',
  'command_center.jobs.create',
  'command_center.jobs.create_followup',
  'command_center.jobs.get',
  'command_center.jobs.list',
  'command_center.jobs.cancel',
  'command_center.jobs.resume',
  'command_center.jobs.revise',
  'command_center.jobs.answer_question',
  'command_center.jobs.authorize_mutation',
  'command_center.jobs.get_summary',
  'command_center.jobs.get_handoff',
  'command_center.jobs.get_events',
  'command_center.jobs.get_logs',
  'command_center.jobs.get_artifacts',
  'command_center.bucket.get_layout',
  'command_center.bucket.put_object',
  'command_center.bucket.get_object',
  'command_center.bucket.list_objects',
  'command_center.bucket.promote_skill',
  'command_center.app_control.seed_profiles',
  'command_center.app_control.put_profile',
  'command_center.app_control.get_profile',
  'command_center.app_control.list_profiles',
  'command_center.app_control.record_run',
  'command_center.browser_sessions.create',
  'command_center.browser_sessions.observe',
  'command_center.browser_sessions.act',
  'command_center.browser_sessions.record_episode',
  'command_center.browser_discoveries.list',
  'command_center.browser_discoveries.promote',
  'command_center.browser_playbooks.lookup',
  'command_center.workers.register_oneshot',
  'command_center.workers.list',
  'command_center.workers.get_capabilities',
  'command_center.agents.upsert_repo_agent',
  'command_center.agents.create_activation',
  'command_center.agents.get_resume_packet',
  'command_center.agents.record_codex_cloud_ref',
  'command_center.agents.record_artifact',
  'command_center.agents.complete_activation',
  'command_center.agents.get_handoff',
];

function parseArgs(argv) {
  const args = {
    mcpUrl: DEFAULT_MCP_URL,
    evidenceDir: DEFAULT_EVIDENCE_DIR,
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    bearerToken: process.env.HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN || process.env.HOME_CENTER_MCP_BEARER_TOKEN || '',
    requireRealToken: false,
    createJob: false,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--require-real-token') args.requireRealToken = true;
    else if (arg === '--create-job') args.createJob = true;
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_chatgpt_invokability_gate.mjs [--mcp-url URL] [--bearer-token TOKEN] [--require-real-token] [--create-job] [--run-id ID] [--json]');
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

function hasBinaryFileSchema(field) {
  if (!field || typeof field !== 'object') return false;
  const markers = [field.format, field.contentEncoding, field.contentMediaType, field.description, field.type].filter(Boolean).join(' ').toLowerCase();
  return /binary|file|octet|gltf|python/.test(markers);
}

function renderToolFileContract(tool) {
  const schema = tool?.inputSchema || tool?.input_schema || {};
  const props = schema.properties || {};
  const required = Array.isArray(schema.required) ? schema.required : [];
  return {
    ok: hasBinaryFileSchema(props.glbFile) && hasBinaryFileSchema(props.scriptFile) && !!props.glbRef && !!props.scriptRef && !!props.scriptText && !required.includes('glbRef') && !required.includes('glbFile'),
    properties: Object.fromEntries(['glbFile', 'scriptFile', 'glbRef', 'scriptRef', 'scriptText'].map((key) => [key, props[key] || null])),
    required,
  };
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
  const renderTool = (listJson.result?.tools || []).find((tool) => tool.name === 'command_center.render.blender_glb');
  const renderContract = renderToolFileContract(renderTool);
  add('render_blender_glb_file_contract_discoverable', listed.status === 200 && renderContract.ok, {contract: renderContract});

  const health = await callTool(args.mcpUrl, protocolToken, 12, 'command_center.health', {});
  const healthJson = contentJson(health.json, 'command_center.health result');
  add('health_tool_alive', health.response.status === 200 && healthJson.ok === true && Object.keys(healthJson).sort().join(',') === 'ok,service,version', {status: health.response.status, health: healthJson});

  const readiness = await callTool(args.mcpUrl, protocolToken, 16, 'command_center.readiness', {});
  const readinessJson = contentJson(readiness.json, 'command_center.readiness result');
  add('readiness_tool_ready', readiness.response.status === 200 && readinessJson.ready === true, {status: readiness.response.status, readiness: readinessJson});

  const dispatcherHealth = await callTool(args.mcpUrl, protocolToken, 15, 'command_center_operation', {operation: 'health', args: {}});
  const dispatcherHealthJson = contentJson(dispatcherHealth.json, 'command_center_operation health result');
  const dispatcherInvokable = dispatcherHealthJson.result?.invokable === true || dispatcherHealthJson.result?.controlPlane?.invokable === true;
  add('command_center_operation_dispatcher_invokable', dispatcherHealth.response.status === 200 && dispatcherHealthJson.result?.ok === true && dispatcherInvokable, {status: dispatcherHealth.response.status, dispatcherHealth: dispatcherHealthJson});

  const bucketLayout = await callTool(args.mcpUrl, protocolToken, 13, 'command_center.bucket.get_layout', {});
  const bucketLayoutJson = contentJson(bucketLayout.json, 'command_center.bucket.get_layout result');
  const lanes = Object.keys(bucketLayoutJson.layout?.lanes || {});
  add('bucket_layout_invokable', bucketLayout.response.status === 200 && lanes.includes('memory/current-condensed') && lanes.includes('skills/promoted') && lanes.includes('notes/cross-repo') && lanes.includes('browser/playbooks'), {status: bucketLayout.response.status, lanes});

  const lookup = await callTool(args.mcpUrl, protocolToken, 14, 'command_center.browser_playbooks.lookup', {origin: 'https://chatgpt.com', taskKey: 'chatgpt.command_center_connector.verify', replayAudience: 'june'});
  const lookupJson = contentJson(lookup.json, 'command_center.browser_playbooks.lookup result');
  add('browser_playbooks_lookup_invokable', lookup.response.status === 200 && typeof lookupJson.found === 'boolean' && lookupJson.collection === 'browserPlaybooks', {status: lookup.response.status, lookup: lookupJson});

  const agentToolNames = [
    'command_center.agents.upsert_repo_agent',
    'command_center.agents.create_activation',
    'command_center.agents.get_resume_packet',
  ];
  add('codex_cloud_agent_tools_discoverable', agentToolNames.every((name) => names.includes(name)), {agentToolNames, missing: agentToolNames.filter((name) => !names.includes(name))});

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
    const handoff = await callTool(args.mcpUrl, realToken, 23, 'command_center.jobs.get_handoff', {jobId});
    const followup = await callTool(args.mcpUrl, realToken, 24, 'command_center.jobs.create_followup', {
      idempotencyKey: `invokability-followup-${runId}`,
      sourceJobId: jobId,
      title: 'Command Center follow-up invokability smoke',
      objective: 'Prove linked follow-up job creation from a source handoff.',
      acceptanceCriteria: ['Follow-up job records sourceJobId'],
      mutationPolicy: {editFiles: 'deny', runTests: 'deny', commit: 'deny', push: 'deny', merge: 'deny'},
    });
    liveJob = {jobId, create: contentJson(create.json, 'jobs.create result'), get: contentJson(get.json, 'jobs.get result'), summary: contentJson(summary.json, 'jobs.get_summary result'), handoff: contentJson(handoff.json, 'jobs.get_handoff result'), followup: contentJson(followup.json, 'jobs.create_followup result')};
    add('live_job_create_readback', !!jobId && liveJob.get.job?.jobId === jobId && liveJob.summary.jobId === jobId && liveJob.handoff.handoff?.job?.jobId === jobId, {jobId});
    add('live_followup_create_readback', liveJob.followup.job?.sourceJobId === jobId && liveJob.followup.job?.followupOf?.jobId === jobId, {sourceJobId: jobId, followupJobId: liveJob.followup.job?.jobId || ''});
  } else if (args.createJob) {
    add('live_job_create_readback', false, {detail: 'No real Home Center MCP OAuth bearer token was available.'});
  }

  const result = {ok: checks.every((check) => check.ok), mcpUrl: args.mcpUrl, base, checks, toolNames: names, liveJob, generatedAt: new Date().toISOString()};
  const evidencePath = path.join(evidenceDir, `command_center_invokability_${args.runId}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(result, null, 2) + '\n');
  const summary = {ok: result.ok, evidencePath, failed: checks.filter((check) => !check.ok)};
  console.log(JSON.stringify(summary, null, args.json ? 0 : 2));
  if (!result.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
