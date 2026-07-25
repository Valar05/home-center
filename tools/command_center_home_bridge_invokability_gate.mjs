#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';

const DEFAULT_HOME_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const DEFAULT_EVIDENCE_DIR = 'tools/command_center_invokability_evidence';

function parseArgs(argv) {
  const args = {
    mcpUrl: DEFAULT_HOME_MCP_URL,
    evidenceDir: DEFAULT_EVIDENCE_DIR,
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    bearerToken: process.env.HOME_CENTER_MCP_BEARER_TOKEN || process.env.HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN || '',
    tokenConfig: process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json'),
    json: false,
    catalogOnly: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--token-config') args.tokenConfig = argv[++i];
    else if (arg === '--json') args.json = true;
    else if (arg === '--catalog-only') args.catalogOnly = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_home_bridge_invokability_gate.mjs [--mcp-url URL] [--run-id ID] [--evidence-dir DIR] [--bearer-token TOKEN] [--json]');
      process.exit(0);
    }
  }
  return args;
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
  if (!fs.existsSync(args.tokenConfig)) return 'home-center-command-center-bridge-protocol-token';
  const refreshed = await refreshTokenConfig(args.tokenConfig);
  return {
    token: refreshed.token || 'home-center-command-center-bridge-protocol-token',
    source: args.tokenConfig,
    refreshed: refreshed.refreshed,
    reason: refreshed.reason,
  };
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

function hasBinaryFileSchema(field) {
  if (!field || typeof field !== 'object') return false;
  const markers = [field.format, field.contentEncoding, field.contentMediaType, field.description, field.type].filter(Boolean).join(' ').toLowerCase();
  return /binary|file|octet|gltf|python|uploaded/.test(markers);
}

function renderBlenderGlbToolFileContract(tool) {
  const schema = tool?.inputSchema || tool?.input_schema || {};
  const props = schema.properties || {};
  const required = Array.isArray(schema.required) ? schema.required : [];
  return {
    ok: hasBinaryFileSchema(props.glbFile) && hasBinaryFileSchema(props.scriptFile) && required.includes('glbFile') && required.includes('scriptFile') && required.includes('idempotencyKey') && !props.glbRef && !props.scriptRef && !props.scriptText,
    properties: Object.fromEntries(['glbFile', 'scriptFile', 'glbRef', 'scriptRef', 'scriptText', 'idempotencyKey'].map((key) => [key, props[key] || null])),
    required,
  };
}

function redactForEvidence(value) {
  if (Array.isArray(value)) return value.map(redactForEvidence);
  if (!value || typeof value !== 'object') {
    if (typeof value === 'string' && /^ccw_[A-Za-z0-9_-]+/.test(value)) return '[redacted-worker-token]';
    return value;
  }
  const out = {};
  for (const [key, item] of Object.entries(value)) {
    if (/token/i.test(key)) out[key] = item ? '[redacted]' : item;
    else out[key] = redactForEvidence(item);
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const tokenInfo = await loadToken(args);
  args.bearerToken = typeof tokenInfo === 'string' ? tokenInfo : tokenInfo.token;
  const evidenceDir = path.resolve(args.evidenceDir);
  fs.mkdirSync(evidenceDir, {recursive: true});
  const checks = [];
  const add = (name, ok, detail = {}) => checks.push({name, ok: !!ok, ...detail});

  const unauth = await fetch(args.mcpUrl, {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'initialize', params: {}})});
  add('home_mcp_requires_auth', unauth.status === 401, {status: unauth.status, wwwAuthenticate: unauth.headers.get('www-authenticate') || ''});

  const base = args.mcpUrl.replace(/\/mcp(?:\?.*)?$/, '');
  const resourceMetadataResponse = await fetch(`${base}/.well-known/oauth-protected-resource`);
  const resourceMetadataText = await resourceMetadataResponse.text();
  const resourceMetadata = parseJson(resourceMetadataText, 'home protected resource metadata');
  add('protected_resource_metadata_exposes_catalog_revision', resourceMetadataResponse.status === 200 && resourceMetadata.connector_schema_revision === '2026-07-25.blender-direct-file-catalog-v1' && Array.isArray(resourceMetadata.direct_file_tools) && resourceMetadata.direct_file_tools.includes('render_blender_glb'), {status: resourceMetadataResponse.status, connector_schema_revision: resourceMetadata.connector_schema_revision || '', registry_version: resourceMetadata.registry_version || '', direct_file_tools: resourceMetadata.direct_file_tools || []});

  const init = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 10,
    method: 'initialize',
    params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'command-center-home-bridge-gate', version: '1'}},
  });
  add('home_mcp_initialize_200', init.status === 200, {status: init.status, contentType: init.headers['content-type'] || ''});
  await postMcp(args.mcpUrl, args.bearerToken, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}}).catch(() => null);

  const healthTool = await postMcp(args.mcpUrl, args.bearerToken, {jsonrpc: '2.0', id: 9, method: 'tools/call', params: {name: 'health', arguments: {}}});
  const healthToolJson = parseMcpResponse(healthTool.text, 'home health');
  const healthToolContent = toolContentJson(healthToolJson, 'home health content');
  add('home_health_reports_live_catalog_revision', healthTool.status === 200 && healthToolContent.registryVersion === '2026-07-25.blender-direct-file-catalog-v1' && healthToolContent.connectorSchemaRevision === '2026-07-25.blender-direct-file-catalog-v1' && Array.isArray(healthToolContent.directFileTools) && healthToolContent.directFileTools.includes('render_blender_glb'), {status: healthTool.status, registryVersion: healthToolContent.registryVersion || '', connectorSchemaRevision: healthToolContent.connectorSchemaRevision || '', directFileTools: healthToolContent.directFileTools || []});

  const listed = await postMcp(args.mcpUrl, args.bearerToken, {jsonrpc: '2.0', id: 11, method: 'tools/list', params: {}});
  const listJson = parseMcpResponse(listed.text, 'home tools/list');
  const toolNames = (listJson.result?.tools || []).map((tool) => tool.name).sort();
  add('home_tools_list_contains_command_center_operation', listed.status === 200 && toolNames.includes('command_center_operation'), {status: listed.status, count: toolNames.length, toolNames});
  add('home_tools_list_contains_drive_operation', listed.status === 200 && toolNames.includes('drive_operation'), {status: listed.status});
  const renderTool = (listJson.result?.tools || []).find((tool) => tool.name === 'render_blender_glb');
  const renderContract = renderBlenderGlbToolFileContract(renderTool);
  add('home_tools_list_contains_top_level_render_blender_glb', listed.status === 200 && toolNames.includes('render_blender_glb'), {status: listed.status});
  add('render_blender_glb_top_level_file_contract_discoverable', listed.status === 200 && renderContract.ok, {status: listed.status, renderContract});

  if (args.catalogOnly) {
    const result = {
      ok: checks.every((check) => check.ok),
      mcpUrl: args.mcpUrl,
      tokenSource: typeof tokenInfo === 'string' ? 'protocol-fallback' : tokenInfo.source,
      tokenRefreshed: typeof tokenInfo === 'string' ? false : tokenInfo.refreshed,
      tokenLoadReason: typeof tokenInfo === 'string' ? 'token config missing' : tokenInfo.reason,
      catalogOnly: true,
      checks,
      toolNames,
      renderContract,
      resourceMetadata: redactForEvidence(resourceMetadata),
      health: redactForEvidence(healthToolContent),
      generatedAt: new Date().toISOString(),
    };
    const evidencePath = path.join(evidenceDir, `command_center_home_bridge_invokability_${args.runId}.json`);
    fs.writeFileSync(evidencePath, JSON.stringify(redactForEvidence(result), null, 2) + '\n');
    const summary = {ok: result.ok, evidencePath, failed: checks.filter((check) => !check.ok), catalogOnly: true};
    console.log(JSON.stringify(summary, null, args.json ? 0 : 2));
    if (!result.ok) process.exit(1);
    return;
  }

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
  const commandCenterOps = capabilitiesContent.commandCenterOperationRegistry?.operations || {};
  const requiredAgentOps = ['agents.upsert_repo_agent', 'agents.create_activation', 'agents.get_resume_packet'];
  add('command_center_operation_registry_contains_codex_cloud_agents', capabilities.status === 200 && requiredAgentOps.every((op) => !!commandCenterOps[op]), {status: capabilities.status, registryVersion: capabilitiesContent.commandCenterOperationRegistry?.version || '', missing: requiredAgentOps.filter((op) => !commandCenterOps[op])});

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
  add('drive_operation_command_center_health_invokable', driveHealth.status === 200 && driveHealthContent.result?.ok === true && driveHealthContent.result?.invokable === true, {status: driveHealth.status, content: driveHealthContent});

  const staleSchemaHealth = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 16,
    method: 'tools/call',
    params: {name: 'drive_operation', arguments: {operation: 'drive_create_folder', args: {commandCenterOperation: 'health'}}},
  });
  const staleSchemaHealthJson = parseMcpResponse(staleSchemaHealth.text, 'drive_operation stale-schema command center health');
  const staleSchemaHealthContent = toolContentJson(staleSchemaHealthJson, 'drive_operation stale-schema command center health content');
  add('drive_operation_stale_schema_command_center_health_invokable', staleSchemaHealth.status === 200 && staleSchemaHealthContent.compatibilityRoute === 'drive_operation.command_center' && staleSchemaHealthContent.result?.ok === true && staleSchemaHealthContent.result?.invokable === true, {status: staleSchemaHealth.status, content: staleSchemaHealthContent});

  const bucket = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 13,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation: 'bucket.get_layout', args: {}}},
  });
  const bucketJson = parseMcpResponse(bucket.text, 'command_center_operation bucket layout');
  const bucketContent = toolContentJson(bucketJson, 'command_center_operation bucket layout content');
  const lanes = Object.keys(bucketContent.result?.layout?.lanes || {});
  add('command_center_operation_bucket_layout_invokable', bucket.status === 200 && lanes.includes('memory/current-condensed') && lanes.includes('skills/promoted') && lanes.includes('notes/cross-repo') && lanes.includes('browser/playbooks'), {status: bucket.status, lanes});

  const playbookLookup = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 17,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation: 'browser_playbooks.lookup', args: {origin: 'https://chatgpt.com', taskKey: 'chatgpt.command_center_connector.verify', replayAudience: 'june'}}},
  });
  const playbookLookupJson = parseMcpResponse(playbookLookup.text, 'command_center_operation browser_playbooks.lookup');
  const playbookLookupContent = toolContentJson(playbookLookupJson, 'command_center_operation browser_playbooks.lookup content');
  add('command_center_operation_browser_playbooks_lookup_invokable', playbookLookup.status === 200 && typeof playbookLookupContent.result?.found === 'boolean' && playbookLookupContent.result?.collection === 'browserPlaybooks', {status: playbookLookup.status, content: playbookLookupContent});

  const safeRun = args.runId.replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 60);
  const workerId = `home-bridge-real-worker-${safeRun}`.slice(0, 120);
  const workerRegistration = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 171,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation: 'workers.register_oneshot', args: {
      idempotencyKey: `home-bridge-real-worker-${safeRun}`,
      workerId,
      engine: 'codex',
      location: 'home-bridge-invokability-gate',
      capabilities: ['codex-cloud', 'codex', 'home-drive-mcp', 'playwright', 'browser-worker', 'prepared-workspace'],
      baseWorkspace: {baseWorkspaceId: 'home-bridge-real-worker-profile', kind: 'persistent_user_owned_browser_profile', snapshotRef: 'worker-local://home-bridge-profile', version: safeRun, restoreStrategy: 'persistent_profile'},
      limits: {concurrentActivations: 1},
    }}},
  });
  const workerRegistrationJson = parseMcpResponse(workerRegistration.text, 'command_center_operation workers.register_oneshot');
  const workerRegistrationContent = toolContentJson(workerRegistrationJson, 'command_center_operation workers.register_oneshot content');
  add('command_center_operation_workers_register_real_invokable', workerRegistration.status === 200 && workerRegistrationContent.result?.worker?.workerId === workerId && workerRegistrationContent.result?.worker?.simulated === false && workerRegistrationContent.result?.workerToken, {status: workerRegistration.status, workerId, content: workerRegistrationContent});

  const agentId = `home-center-chatgpt-bridge-${args.runId}`.replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 80);
  const upsert = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 18,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation: 'agents.upsert_repo_agent', args: {
      idempotencyKey: `home-bridge-agent-upsert-${args.runId}`,
      agentId,
      projectId: 'home-center',
      name: 'Home Center ChatGPT bridge proof',
      repository: 'Valar05/home-center',
      contextRefs: ['docs/COMMAND_CENTER_MCP.md'],
    }}},
  });
  const upsertJson = parseMcpResponse(upsert.text, 'command_center_operation agents.upsert_repo_agent');
  const upsertContent = toolContentJson(upsertJson, 'command_center_operation agents.upsert_repo_agent content');
  add('command_center_operation_agents_upsert_invokable', upsert.status === 200 && upsertContent.result?.agent?.agentId === agentId && upsertContent.result?.session?.sessionId, {status: upsert.status, agentId, content: upsertContent});

  const activation = await postMcp(args.mcpUrl, args.bearerToken, {
    jsonrpc: '2.0',
    id: 19,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation: 'agents.create_activation', args: {
      idempotencyKey: `home-bridge-agent-activation-${args.runId}`,
      agentId,
      title: 'Home Center ChatGPT bridge activation proof',
      prompt: 'Verify that ChatGPT can create a durable Command Center Codex cloud activation through Home Center command_center_operation.',
      workerRequirements: ['codex-cloud', 'home-drive-mcp', 'playwright'],
      acceptanceCriteria: ['Activation was created through Home Center MCP command_center_operation', 'Resume packet can be read back'],
      artifactRequirements: ['final-report.md'],
    }}},
  });
  const activationJson = parseMcpResponse(activation.text, 'command_center_operation agents.create_activation');
  const activationContent = toolContentJson(activationJson, 'command_center_operation agents.create_activation content');
  const activationId = activationContent.result?.activation?.activationId || '';
  add('command_center_operation_agents_create_activation_invokable', activation.status === 200 && /^activation_/.test(activationId) && activationContent.result?.activation?.selectedWorkerId === workerId, {status: activation.status, activationId, selectedWorkerId: activationContent.result?.activation?.selectedWorkerId || '', content: activationContent});

  if (activationId) {
    const resume = await postMcp(args.mcpUrl, args.bearerToken, {
      jsonrpc: '2.0',
      id: 20,
      method: 'tools/call',
      params: {name: 'command_center_operation', arguments: {operation: 'agents.get_resume_packet', args: {activationId}}},
    });
    const resumeJson = parseMcpResponse(resume.text, 'command_center_operation agents.get_resume_packet');
    const resumeContent = toolContentJson(resumeJson, 'command_center_operation agents.get_resume_packet content');
    add('command_center_operation_agents_resume_packet_invokable', resume.status === 200 && resumeContent.result?.resumePacket?.packetVersion === 'command-center-codex-cloud-resume-v1', {status: resume.status, activationId, content: resumeContent});
  } else {
    add('command_center_operation_agents_resume_packet_invokable', false, {detail: 'Activation was not created, so resume packet readback was skipped.'});
  }

  const result = {
    ok: checks.every((check) => check.ok),
    mcpUrl: args.mcpUrl,
    tokenSource: typeof tokenInfo === 'string' ? 'protocol-fallback' : tokenInfo.source,
    tokenRefreshed: typeof tokenInfo === 'string' ? false : tokenInfo.refreshed,
    tokenLoadReason: typeof tokenInfo === 'string' ? 'token config missing' : tokenInfo.reason,
    checks,
    toolNames,
    generatedAt: new Date().toISOString(),
  };
  const evidencePath = path.join(evidenceDir, `command_center_home_bridge_invokability_${args.runId}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(redactForEvidence(result), null, 2) + '\n');
  const summary = {ok: result.ok, evidencePath, failed: checks.filter((check) => !check.ok)};
  console.log(JSON.stringify(summary, null, args.json ? 0 : 2));
  if (!result.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
