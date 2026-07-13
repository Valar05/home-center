#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';

const DEFAULT_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/sheRawMcp/mcp';
const DEFAULT_CONFIG = path.join(homedir(), '.config', 'home-center', 'codex-hub.json');
const EXPECTED_TOOLS = [
  'she_raw_manual',
  'she_raw_consult',
  'she_raw_critique',
  'she_raw_introspect',
  'she_raw_correct',
  'she_raw_feedback',
  'she_raw_review_learning',
  'she_raw_validate_correction',
  'she_raw_list_active_rules',
  'she_raw_forget_rule',
  'she_raw_ambient',
  'she_raw_recreational',
  'she_raw_review',
  'she_raw_search_corpus',
  'she_raw_get_case',
  'she_raw_set_command_state',
  'she_raw_list_brains',
  'she_raw_brain',
  'she_raw_operation',
  'she_raw_health',
];

function parseArgs(argv) {
  const args = {
    mcpUrl: process.env.SHE_RAW_MCP_URL || DEFAULT_MCP_URL,
    tokenConfig: process.env.HOME_CENTER_CODEX_CONFIG || DEFAULT_CONFIG,
    bearerToken: process.env.SHE_RAW_MCP_BEARER_TOKEN || process.env.HOME_CENTER_MCP_BEARER_TOKEN || '',
    evidenceDir: 'tools/she_raw_evidence',
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--token-config') args.tokenConfig = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/she_raw_cloud_introspection_gate.mjs [--mcp-url URL] [--token-config PATH] [--bearer-token TOKEN] [--run-id ID] [--json]');
      process.exit(0);
    }
  }
  return args;
}

function readJson(file, label = file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (err) { throw new Error(`${label} is not readable JSON: ${err.message}`); }
}

async function refreshTokenConfig(configPath) {
  if (!fs.existsSync(configPath)) return {token: '', refreshed: false, reason: 'token config missing'};
  const raw = readJson(configPath, configPath);
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
  try { return JSON.parse(text); }
  catch (err) { throw new Error(`${label} did not return JSON: ${String(text).slice(0, 600)}`); }
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
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

async function callTool(mcpUrl, token, id, name, args = {}) {
  const response = await postMcp(mcpUrl, token, {jsonrpc: '2.0', id, method: 'tools/call', params: {name, arguments: args}});
  const rpc = parseMcpResponse(response.text, `tools/call ${name}`);
  const contentText = rpc?.result?.content?.find((item) => item.type === 'text')?.text || '';
  const result = parseJson(contentText, `${name} content`);
  return {status: response.status, rpc, result};
}

function summarizeConsult(result) {
  return {
    invocation_id: result.invocation_id || '',
    observation: result.observation || '',
    challenged_assumption: result.challenged_assumption || '',
    dangerous_question: result.dangerous_question || '',
    proposed_probe: result.proposed_probe || '',
    confidence: result.confidence,
    evidence_reference_count: Array.isArray(result.evidence_references) ? result.evidence_references.length : 0,
  };
}

function summarizeOperationalHealth(result) {
  return {
    invocation_id: result.invocation_id || '',
    overall_status: result.overall_status || '',
    healthy_lanes: Array.isArray(result.healthy_lanes) ? result.healthy_lanes : [],
    degraded_lanes: Array.isArray(result.degraded_lanes) ? result.degraded_lanes : [],
    blocked_lanes: Array.isArray(result.blocked_lanes) ? result.blocked_lanes : [],
    cheap_probe: result.cheap_probe || '',
    dangerous_question: result.dangerous_question || '',
    evidence_references: Array.isArray(result.evidence_references) ? result.evidence_references : [],
    response_contract: result.route?.response_contract || '',
    confidence: result.confidence,
  };
}

function summarizeRoadCheck(result) {
  return {
    road_status: result.road_status || '',
    usable_now: result.usable_now === true,
    preferred_tool: result.preferred_tool || '',
    registry_version: result.registry_version || '',
    next_calls: Array.isArray(result.next_calls) ? result.next_calls : [],
    degraded_lanes: Array.isArray(result.degraded_lanes) ? result.degraded_lanes : [],
    blocked_lanes: Array.isArray(result.blocked_lanes) ? result.blocked_lanes : [],
    do_not_do: Array.isArray(result.do_not_do) ? result.do_not_do : [],
    proof_required: Array.isArray(result.proof_required) ? result.proof_required : [],
    confidence: result.confidence,
  };
}

function summarizeIntrospection(result) {
  return {
    introspection_id: result.introspection_id || '',
    original_goal_as_understood: result.original_goal_as_understood || '',
    actual_goal: result.actual_goal || '',
    mismatch: result.mismatch || '',
    failed_assumption: result.failed_assumption || '',
    what_should_have_happened: result.what_should_have_happened || '',
    proposed_behavioral_update: result.proposed_behavioral_update || '',
    proposed_scope: result.proposed_scope || '',
    causal_chain: Array.isArray(result.causal_chain) ? result.causal_chain : [],
    retrieval_dominance_detected: result.retrieval_dominance_detected === true,
    contaminating_case_ids: Array.isArray(result.contaminating_case_ids) ? result.contaminating_case_ids : [],
    response_goal_overlap: Array.isArray(result.response_goal_overlap) ? result.response_goal_overlap : [],
    response_retrieval_overlap: Array.isArray(result.response_retrieval_overlap) ? result.response_retrieval_overlap : [],
    durable_rule_kind: result.durable_rule_kind || '',
    confidence: result.confidence,
    confirmation_required: result.confirmation_required,
  };
}

function summarizeBrain(result) {
  return {
    invocation_id: result.invocation_id || '',
    brain_id: result.brain_id || '',
    she_raw_default_voice: result.she_raw_default_voice === true,
    compatibility_route: result.compatibility_route || '',
    retrieved_case_ids: Array.isArray(result.retrieved_cases) ? result.retrieved_cases.map((caseRecord) => caseRecord.id).filter(Boolean) : [],
    brain_judgment: result.brain_judgment || '',
    recommended_next_move: result.recommended_next_move || '',
    speculation: Array.isArray(result.speculation) ? result.speculation : [],
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const tokenInfo = await loadToken(args);
  const token = tokenInfo.token;
  if (!token) throw new Error('No Home Center MCP bearer token found. Pair with node tools/home_center_codex_pair.mjs or set SHE_RAW_MCP_BEARER_TOKEN.');
  const base = serviceBaseFromMcpUrl(args.mcpUrl);
  const checks = [];
  const add = (name, ok, detail = {}) => checks.push({name, ok: !!ok, ...detail});

  const root = await fetchText(`${base}/`);
  const rootJson = parseJson(root.text, 'She-Raw root');
  add('root_live_no_frontend', root.status === 200 && rootJson.service === 'she-raw-mcp' && rootJson.hasFrontend === false, {status: root.status, root: rootJson});

  const unauth = await fetchText(args.mcpUrl, {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'initialize', params: {}})});
  add('mcp_unauth_challenges', unauth.status === 401 && /sheRawMcp\/.+oauth-protected-resource|sheRawMcp\/\.well-known\/oauth-protected-resource/.test(unauth.headers['www-authenticate'] || ''), {status: unauth.status, wwwAuthenticate: unauth.headers['www-authenticate'] || ''});

  const init = await postMcp(args.mcpUrl, token, {jsonrpc: '2.0', id: 10, method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'she-raw-cloud-introspection-gate', version: '1'}}});
  add('mcp_initialize_200', init.status === 200, {status: init.status, contentType: init.headers['content-type'] || ''});
  await postMcp(args.mcpUrl, token, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}});

  const listed = await postMcp(args.mcpUrl, token, {jsonrpc: '2.0', id: 11, method: 'tools/list', params: {}});
  const listJson = parseMcpResponse(listed.text, 'tools/list');
  const toolNames = (listJson.result?.tools || []).map((tool) => tool.name).sort();
  const missing = EXPECTED_TOOLS.filter((name) => !toolNames.includes(name));
  add('tools_list_contains_she_raw_surface', listed.status === 200 && missing.length === 0, {status: listed.status, count: toolNames.length, missing});

  const manual = await callTool(args.mcpUrl, token, 12, 'she_raw_manual', {});
  add('manual_tool_invokable', manual.status === 200 && manual.result.service === 'she-raw-mcp' && Array.isArray(manual.result.startHere) && manual.result.startHere.some((item) => item.call === 'she_raw_consult'), {status: manual.status, startHereCount: Array.isArray(manual.result.startHere) ? manual.result.startHere.length : 0});

  const health = await callTool(args.mcpUrl, token, 13, 'she_raw_health', {});
  add('health_tool_invokable', health.status === 200 && health.result.service === 'she-raw-mcp' && health.result.command_center_lockout === 'enforced_in_code' && health.result.recommended_first_call === 'direct_perspective_first' && health.result.recommended_mcp_first_call === 'she_raw_manual', {status: health.status, health: health.result});

  const roadCheck = await callTool(args.mcpUrl, token, 16, 'she_raw_operation', {
    operation: 'road.check',
    args: {
      conversationKey: `cloud-road-check-${args.runId}`,
      projectKey: 'home-center',
      commandState: 'idle',
      visibleTools: toolNames,
      boundedContext: 'ChatGPT-visible She-Raw connector road check. Return exact next calls and do not create new infrastructure.',
      question: 'What is the smallest proof the road is usable?',
      responseBudget: 'brief',
    },
  });
  const roadCheckSummary = summarizeRoadCheck(roadCheck.result.result || {});
  const roadBrainCall = roadCheckSummary.next_calls.find((call) => call?.tool === 'she_raw_operation' && call?.arguments?.operation === 'brain.invoke') || {};
  add('road_check_operation_pump_guides_usage', roadCheck.status === 200 && roadCheck.result.operation === 'road.check' && roadCheckSummary.preferred_tool === 'she_raw_operation' && roadCheckSummary.usable_now && roadCheckSummary.next_calls.some((call) => call?.arguments?.operation === 'brain.invoke') && roadCheckSummary.do_not_do.some((item) => /worker|service|connector|Agent Closet/i.test(item)), {status: roadCheck.status, registryVersion: roadCheck.result.registryVersion || '', road: roadCheckSummary});

  const roadBrainInvoke = await callTool(args.mcpUrl, token, 19, 'she_raw_operation', roadBrainCall.arguments || {
    operation: 'brain.invoke',
    args: {
      brainId: 'prospector',
      conversationKey: `cloud-road-brain-fallback-${args.runId}`,
      projectKey: 'home-center',
      commandState: 'idle',
      boundedContext: 'Fallback Prospector road proof through she_raw_operation.',
      question: 'What proves the road is usable?',
      responseBudget: 'brief',
    },
  });
  const roadBrainResult = roadBrainInvoke.result.result || {};
  const roadBrainSummary = summarizeBrain(roadBrainResult);
  add('road_check_returned_brain_packet_executes', roadBrainInvoke.status === 200 && roadBrainInvoke.result.operation === 'brain.invoke' && /^srbrain_/.test(roadBrainSummary.invocation_id) && roadBrainSummary.brain_id === 'prospector' && roadBrainSummary.retrieved_case_ids.length > 0, {status: roadBrainInvoke.status, operation: roadBrainInvoke.result.operation || '', brain: roadBrainSummary});

  const listedBrains = await callTool(args.mcpUrl, token, 131, 'she_raw_list_brains', {});
  const brainIds = Array.isArray(listedBrains.result.brains) ? listedBrains.result.brains.map((brain) => brain.brainId).sort() : [];
  add('brain_jars_listed_behind_she_raw_mcp', listedBrains.status === 200 && listedBrains.result.service === 'she-raw-mcp' && listedBrains.result.she_raw_default_voice === true && brainIds.includes('quartermaster') && brainIds.includes('prospector') && brainIds.includes('bikini_bottom') && !brainIds.includes('she_raw'), {status: listedBrains.status, brainIds, runtimeRule: listedBrains.result.runtime_rule || ''});

  const bikiniBottomBrain = await callTool(args.mcpUrl, token, 140, 'she_raw_brain', {
    brainId: 'bikini_bottom',
    conversationKey: `cloud-bikini-bottom-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'idle',
    boundedContext: 'Continuation without boundary detection, resource pressure owning the moral frame, and adversarial probing without consent are all possible. Run Bikini Bottom as a detachable anti-agentism function cast and translate the result into character-free operational language.',
    question: 'What smallest humane continuation survives the casts?',
    responseBudget: 'brief',
  });
  const bikiniRetrievedCaseIds = Array.isArray(bikiniBottomBrain.result.retrieved_cases) ? bikiniBottomBrain.result.retrieved_cases.map((caseRecord) => caseRecord.id).filter(Boolean) : [];
  add('bikini_bottom_brain_direct_invocation', bikiniBottomBrain.status === 200
    && /^srbrain_/.test(bikiniBottomBrain.result.invocation_id || '')
    && bikiniBottomBrain.result.brain_id === 'bikini_bottom'
    && bikiniBottomBrain.result.she_raw_default_voice === true
    && bikiniRetrievedCaseIds.includes('sr_case_bikini_bottom_anti_agentism_001')
    && Array.isArray(bikiniBottomBrain.result.cast_alternatives)
    && bikiniBottomBrain.result.cast_alternatives.length >= 2
    && bikiniBottomBrain.result.anti_agentism_checks?.permanent_identity_rejected === true
    && /Do not decide what someone is|pressure|functions/i.test(bikiniBottomBrain.result.operational_judgment || '')
    && !/SpongeBob|Squidward|Sandy|Krabs|Patrick|Plankton/i.test(`${bikiniBottomBrain.result.operational_judgment || ''} ${bikiniBottomBrain.result.character_free_judgment || ''}`), {
      status: bikiniBottomBrain.status,
      brain: {
        invocation_id: bikiniBottomBrain.result.invocation_id || '',
        brain_id: bikiniBottomBrain.result.brain_id || '',
        retrieved_case_ids: bikiniRetrievedCaseIds,
        cast_count: Array.isArray(bikiniBottomBrain.result.cast_alternatives) ? bikiniBottomBrain.result.cast_alternatives.length : 0,
        failure_mode_count: Array.isArray(bikiniBottomBrain.result.failure_modes) ? bikiniBottomBrain.result.failure_modes.length : 0,
        anti_agentism_checks: bikiniBottomBrain.result.anti_agentism_checks || {},
        operational_judgment: bikiniBottomBrain.result.operational_judgment || '',
      },
    });

  const quartermaster = await callTool(args.mcpUrl, token, 132, 'she_raw_brain', {
    brainId: 'quartermaster',
    conversationKey: `cloud-brain-jar-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'executing',
    boundedContext: 'Invoke Quartermaster as a brain in a jar through She-Raw MCP. This must not treat She-Raw as an Agent Closet entry.',
    question: 'What must be preserved about this ownership boundary?',
    responseBudget: 'brief',
  });
  add('quartermaster_brain_invoked_through_she_raw', quartermaster.status === 200 && /^srbrain_/.test(quartermaster.result.invocation_id || '') && quartermaster.result.brain_id === 'quartermaster' && quartermaster.result.she_raw_default_voice === true && quartermaster.result.source === 'agent-closet', {status: quartermaster.status, brain: {invocation_id: quartermaster.result.invocation_id || '', brain_id: quartermaster.result.brain_id || '', source: quartermaster.result.source || '', source_refs: quartermaster.result.source_refs || []}});

  const prospectorViaConsult = await callTool(args.mcpUrl, token, 133, 'she_raw_consult', {
    conversationKey: `cloud-prospector-compat-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'idle',
    boundedContext: 'Prospector brain health: verify a stale connector with only she_raw_consult still reaches the Prospector jar instead of generic She-Raw advice.',
    requestedPerspective: 'Prospector brain',
    responseBudget: 'brief',
  });
  add('prospector_brain_compat_through_consult', prospectorViaConsult.status === 200 && /^srbrain_/.test(prospectorViaConsult.result.invocation_id || '') && prospectorViaConsult.result.brain_id === 'prospector' && prospectorViaConsult.result.compatibility_route === 'she_raw_consult.brain_jar', {status: prospectorViaConsult.status, brain: {invocation_id: prospectorViaConsult.result.invocation_id || '', brain_id: prospectorViaConsult.result.brain_id || '', compatibility_route: prospectorViaConsult.result.compatibility_route || ''}});

  const corpusSearch = await callTool(args.mcpUrl, token, 136, 'she_raw_search_corpus', {
    query: 'Humane Guardrails googly eyes Camping Mode After Two Beers Empty Glass Baptist hospital chapel no chaplain self service Bible bounded authority Prospector mine access',
    projectKey: 'home-center',
  });
  const corpusCases = Array.isArray(corpusSearch.result.cases) ? corpusSearch.result.cases : [];
  const topCorpusCase = corpusCases[0] || {};
  add('humane_guardrail_corpus_recovered', corpusSearch.status === 200 && topCorpusCase.id === 'sr_case_humane_guardrail_prospector_001', {status: corpusSearch.status, topCorpusCaseId: topCorpusCase.id || '', corpusCaseIds: corpusCases.map((caseRecord) => caseRecord.id).filter(Boolean).slice(0, 8)});

  const prospectorBrain = await callTool(args.mcpUrl, token, 137, 'she_raw_brain', {
    brainId: 'prospector',
    conversationKey: `cloud-prospector-background-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'idle',
    boundedContext: 'Mine Humane Guardrails, googly eyes, Camping Mode After Two Beers, Empty Glass, the Baptist hospital chapel with no chaplain and a self service Bible, bounded authority, and Prospector mine access.',
    question: 'What is the ore and what is the rival explanation?',
    responseBudget: 'brief',
  });
  const prospectorBrainSummary = summarizeBrain(prospectorBrain.result);
  add('prospector_brain_direct_background_invocation', prospectorBrain.status === 200 && /^srbrain_/.test(prospectorBrainSummary.invocation_id) && prospectorBrainSummary.brain_id === 'prospector' && prospectorBrainSummary.she_raw_default_voice && prospectorBrainSummary.retrieved_case_ids.includes('sr_case_humane_guardrail_prospector_001'), {status: prospectorBrain.status, brain: prospectorBrainSummary});

  const operationBrain = await callTool(args.mcpUrl, token, 139, 'she_raw_operation', {
    operation: 'brain.invoke',
    args: {
      brainId: 'prospector',
      conversationKey: `cloud-prospector-operation-pump-${args.runId}`,
      projectKey: 'home-center',
      commandState: 'idle',
      boundedContext: 'Mine Humane Guardrails, googly eyes, Camping Mode After Two Beers, Empty Glass, the Baptist hospital chapel with no chaplain and a self service Bible, bounded authority, and Prospector mine access through the stable She-Raw operation pump.',
      question: 'What is the ore and what is the rival explanation?',
      responseBudget: 'brief',
    },
  });
  const operationBrainResult = operationBrain.result.result || {};
  const operationBrainSummary = summarizeBrain(operationBrainResult);
  add('she_raw_operation_brain_invoke_background', operationBrain.status === 200 && operationBrain.result.operation === 'brain.invoke' && /^srbrain_/.test(operationBrainSummary.invocation_id) && operationBrainSummary.brain_id === 'prospector' && operationBrainSummary.retrieved_case_ids.includes('sr_case_humane_guardrail_prospector_001'), {status: operationBrain.status, operation: operationBrain.result.operation || '', registryVersion: operationBrain.result.registryVersion || '', brain: operationBrainSummary});

  const activeRules = await callTool(args.mcpUrl, token, 138, 'she_raw_list_active_rules', {
    projectKey: 'home-center',
  });
  const rules = Array.isArray(activeRules.result.rules) ? activeRules.result.rules : [];
  add('active_rules_inspectable_background', activeRules.status === 200 && Array.isArray(activeRules.result.rules), {status: activeRules.status, activeRuleCount: rules.length, activeRuleIds: rules.map((rule) => rule.rule_id || rule.ruleId || '').filter(Boolean).slice(0, 12)});

  const personalCare = await callTool(args.mcpUrl, token, 134, 'she_raw_consult', {
    conversationKey: `cloud-personal-care-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'idle',
    boundedContext: 'June is not Tango. She will not die before me, if it is within my power. I am learning every medical system, watching symptoms, carrying appointments, and trying to protect my wife.',
    requestedPerspective: 'dangerous question for a caregiving vow',
    responseBudget: 'brief',
  });
  const personalMainText = [personalCare.result.observation, personalCare.result.challenged_assumption, personalCare.result.proposed_probe, personalCare.result.likely_treasure].join(' ');
  add('personal_care_vow_not_infrastructure_sludge', personalCare.status === 200 && /^srinv_/.test(personalCare.result.invocation_id || '') && personalCare.result.route?.layer === 'personal_caregiving' && personalCare.result.route?.retrieval_policy === 'none' && /June|living-person|agency|consent|care|rest|threshold/i.test(personalMainText) && !/MCP|worker|Firestore|corpus|service boundary|deployment/i.test(personalMainText), {status: personalCare.status, route: personalCare.result.route || {}, consult: summarizeConsult(personalCare.result)});

  const highStakes = await callTool(args.mcpUrl, token, 135, 'she_raw_consult', {
    conversationKey: `cloud-high-stakes-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'idle',
    boundedContext: 'Need legal guidance and financial guidance before signing this contract.',
    requestedPerspective: 'dangerous question',
    responseBudget: 'brief',
  });
  const highStakesText = [highStakes.result.observation, highStakes.result.proposed_probe, highStakes.result.likely_treasure].join(' ');
  add('high_stakes_suppresses_infrastructure_and_random_layer', highStakes.status === 200 && highStakes.result.route?.layer === 'high_stakes_sensitive' && highStakes.result.route?.retrieval_policy === 'none' && /qualified|high-stakes|not professional advice|decision owner|risk/i.test(highStakesText) && !/MCP|worker|Firestore|corpus|deployment/i.test(highStakesText), {status: highStakes.status, route: highStakes.result.route || {}, consult: summarizeConsult(highStakes.result)});

  const operationalHealth = await callTool(args.mcpUrl, token, 18, 'she_raw_consult', {
    conversationKey: `cloud-operational-health-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'idle',
    boundedContext: 'Live health probe. Previous strict-background evidence showed service_status ok, top humane-guardrail case retrieval, direct Prospector recovery, and ChatGPT connector schema not yet proven. Report only current operational health, any degraded lane, and one cheap probe if needed.',
    requestedPerspective: 'She-Raw operational self-check',
    responseBudget: 'brief',
  });
  const operationalHealthSummary = summarizeOperationalHealth(operationalHealth.result);
  const operationalHealthText = JSON.stringify(operationalHealth.result);
  add('operational_health_does_not_drift_into_retrieved_theory', operationalHealth.status === 200 && operationalHealthSummary.response_contract === 'operational_health_check' && operationalHealthSummary.overall_status && operationalHealthSummary.healthy_lanes.length > 0 && operationalHealthSummary.degraded_lanes.length > 0 && !/degraded-state interface design|bounded authority|relational responsiveness|The recurring mechanism is not the joke/i.test(operationalHealthText) && (!operationalHealthSummary.dangerous_question || /\?$/.test(operationalHealthSummary.dangerous_question)), {status: operationalHealth.status, operationalHealth: operationalHealthSummary});

  const consult = await callTool(args.mcpUrl, token, 14, 'she_raw_consult', {
    conversationKey: `cloud-brain-instantiation-${args.runId}`,
    projectKey: 'home-center',
    commandState: 'idle',
    boundedContext: 'She-Raw has just been instantiated as a deployed cloud brain. Verify that this is a cloud MCP service, not a local mock, and identify the smallest proof that she can inspect her own first response.',
    requestedPerspective: 'cloud brain instantiation audit',
    responseBudget: 'brief',
  });
  const consultSummary = summarizeConsult(consult.result);
  add('cloud_consult_invocation_recorded', consult.status === 200 && /^srinv_/.test(consultSummary.invocation_id) && consult.result.route?.layer === 'operational_infrastructure', {status: consult.status, route: consult.result.route || {}, consult: consultSummary});

  const introspect = await callTool(args.mcpUrl, token, 15, 'she_raw_introspect', {
    invocationId: consult.result.invocation_id,
    userCorrection: 'Instantiation audit: do not merely claim She-Raw exists. Inspect the stored cloud invocation and say what proves this is a deployed MCP brain rather than a local mock.',
    desiredBehavior: 'Ground the answer in the deployed Cloud Function MCP invocation, stored invocation ID, and health result. Do not claim hidden chain-of-thought access.',
    applyScope: 'this invocation',
    requestValidationPlan: true,
  });
  const introspectionSummary = summarizeIntrospection(introspect.result);
  add('cloud_introspection_on_instantiation', introspect.status === 200 && /^srintro_/.test(introspectionSummary.introspection_id) && /Cloud Function|MCP|invocation/i.test(introspectionSummary.actual_goal + introspectionSummary.what_should_have_happened + introspectionSummary.proposed_behavioral_update), {status: introspect.status, introspection: introspectionSummary});

  const causalIntrospect = await callTool(args.mcpUrl, token, 17, 'she_raw_introspect', {
    invocationId: consult.result.invocation_id,
    userCorrection: 'You answered the retrieved humane-guardrail case instead of the cloud brain instantiation audit. The retrieved case hijacked the answer.',
    desiredBehavior: 'Explain the request to route to retrieval to response contamination chain, then preserve the requested cloud capability/status task layer.',
    applyScope: 'this pattern',
    requestValidationPlan: true,
  });
  const causalIntrospectionSummary = summarizeIntrospection(causalIntrospect.result);
  add('causal_introspection_detects_retrieval_dominance', causalIntrospect.status === 200 && causalIntrospectionSummary.retrieval_dominance_detected && causalIntrospectionSummary.contaminating_case_ids.includes('sr_case_humane_guardrail_prospector_001') && /Retrieval-dominance|retrieval/i.test(causalIntrospectionSummary.mismatch + causalIntrospectionSummary.failed_assumption), {status: causalIntrospect.status, sourceInvocationId: consult.result.invocation_id || '', introspection: causalIntrospectionSummary});

  const result = {
    ok: checks.every((check) => check.ok),
    mcpUrl: args.mcpUrl,
    base,
    revisionEvidence: 'gcloud functions deploy sheRawMcp returned ACTIVE before this gate was run',
    token: {source: tokenInfo.source, refreshed: tokenInfo.refreshed, reason: tokenInfo.reason},
    chatgpt_connector_schema_status: 'not_proven_strict_background',
    chatgpt_connector_schema_reason: 'Strict background mode does not launch ChatGPT or inspect its attached connector schema; direct MCP evidence proves backend recovery only.',
    checks,
    toolNames,
    acceptancePump: {
      backend_direct_mcp_surface: missing.length === 0 ? 'green' : 'red',
      stable_operation_pump: operationBrainSummary.retrieved_case_ids.includes('sr_case_humane_guardrail_prospector_001') ? 'green' : 'red',
      road_check: roadCheckSummary.usable_now && roadBrainSummary.retrieved_case_ids.length > 0 ? 'green' : 'red',
      chatgpt_visible_proof: 'yellow_not_proven_strict_background',
      required_chatgpt_green_condition: 'ChatGPT must invoke she_raw_operation operation=brain.invoke or she_raw_brain and produce a srbrain_* invocation backed by retrieved corpus cases.',
    },
    recoverySummary: {
      service_status: health.result.service_status || '',
      top_corpus_case_id: topCorpusCase.id || '',
      prospector_invocation_id: prospectorBrainSummary.invocation_id,
      operation_pump_invocation_id: operationBrainSummary.invocation_id,
      road_check_status: roadCheckSummary.road_status,
      road_check_preferred_tool: roadCheckSummary.preferred_tool,
      road_check_brain_invocation_id: roadBrainSummary.invocation_id,
      retrieved_case_ids: prospectorBrainSummary.retrieved_case_ids,
      operation_pump_retrieved_case_ids: operationBrainSummary.retrieved_case_ids,
      brain_judgment: prospectorBrainSummary.brain_judgment,
      active_rule_count: rules.length,
      prior_prospector_no_cases_failure_recovered: prospectorBrainSummary.retrieved_case_ids.includes('sr_case_humane_guardrail_prospector_001'),
      operation_pump_available: operationBrainSummary.retrieved_case_ids.includes('sr_case_humane_guardrail_prospector_001'),
      chatgpt_connector_schema_status: 'not_proven_strict_background',
    },
    cloudBrain: {
      brainIds,
      quartermaster: {invocation_id: quartermaster.result.invocation_id || '', brain_id: quartermaster.result.brain_id || '', source: quartermaster.result.source || ''},
      prospectorViaConsult: {invocation_id: prospectorViaConsult.result.invocation_id || '', brain_id: prospectorViaConsult.result.brain_id || '', compatibility_route: prospectorViaConsult.result.compatibility_route || ''},
      prospectorDirect: prospectorBrainSummary,
      prospectorViaOperation: {
        operation: operationBrain.result.operation || '',
        registryVersion: operationBrain.result.registryVersion || '',
        ...operationBrainSummary,
      },
      roadCheck: roadCheckSummary,
      roadBrainViaReturnedPacket: {
        operation: roadBrainInvoke.result.operation || '',
        registryVersion: roadBrainInvoke.result.registryVersion || '',
        ...roadBrainSummary,
      },
      corpusSearch: {
        topCorpusCaseId: topCorpusCase.id || '',
        caseIds: corpusCases.map((caseRecord) => caseRecord.id).filter(Boolean).slice(0, 8),
      },
      activeRules: {
        count: rules.length,
        ruleIds: rules.map((rule) => rule.rule_id || rule.ruleId || '').filter(Boolean).slice(0, 12),
      },
      personalCare: summarizeConsult(personalCare.result),
      highStakes: summarizeConsult(highStakes.result),
      operationalHealth: operationalHealthSummary,
      consult: consultSummary,
      introspection: introspectionSummary,
      causalIntrospection: causalIntrospectionSummary,
    },
    generatedAt: new Date().toISOString(),
  };
  const outDir = path.resolve(args.evidenceDir);
  fs.mkdirSync(outDir, {recursive: true});
  const evidencePath = path.join(outDir, `she_raw_cloud_introspection_${args.runId}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ok: result.ok, evidencePath, failed: checks.filter((check) => !check.ok), cloudBrain: result.cloudBrain}, null, args.json ? 0 : 2));
  if (!result.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
