const crypto = require('node:crypto');
const {
  createHomeCenterMcpServer,
  createDelegatedHomeCenterAuthContext,
  registeredHomeCenterTools,
  callRegisteredHomeCenterTool,
} = require('./home_center_mcp');

const VENICE_MAX_TOOL_ROUNDS = 8;
const VENICE_ALLOWED_RUNTIME_SERVICE_ACCOUNT = 'venice-discord-runtime@home-center-dclar.iam.gserviceaccount.com';
const HOME_CENTER_MCP_URL = process.env.HOME_CENTER_MCP_URL || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const VENICE_SESSION_CONTROL_TOOLS = new Set(['fortress_online', 'home_center_session_update']);

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function safeList(value, maxItems = 20, maxText = 400) {
  return Array.isArray(value) ? value.slice(0, maxItems).map((item) => safeText(item, maxText)).filter(Boolean) : [];
}

function deepCloneJson(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function tokenHash(value) {
  return crypto.createHash('sha256').update(String(value || '')).digest('hex');
}

function randomToken(bytes = 32) {
  return crypto.randomBytes(bytes).toString('base64url');
}

function toolDefinitionByName(tools, name) {
  return tools.find((tool) => tool && tool.name === name) || null;
}

function toolIsReadOnly(tool) {
  return !!(tool && tool.annotations && tool.annotations.readOnlyHint === true);
}

function usesHttpMcpTransport(context) {
  return !!safeText(context && context.mcpUrl, 2000);
}

function promptDeniesMutation(prompt = '') {
  return /\b(do not change|do not modify|do not edit|do not create|do not write|read only|read-only|inspect only|tell me how|how would you|explain how|propose|plan only|without changing|make (?:a )?plan|draft (?:a )?plan)\b/.test(prompt);
}

function promptDirectlyAuthorizesMutation(prompt = '') {
  return /\b(fix|repair|patch|change|modify|edit|update|create|write|add|commit|branch|pull request|pr|merge|save|upsert|start|begin|initialize|initialise|bootstrap|set up|setup)\b/.test(prompt)
    || /\bmake\s+(?:the|a|an)\b/.test(prompt)
    || /\b(make|build|open|ship|launch)\b/.test(prompt) && /\b(project|repo|repository|branch|pull request|pr|file|patch|fix)\b/.test(prompt);
}

function promptLooksLikeMutationFollowThrough(prompt = '') {
  return /^(make|do|start|begin|create|build|ship|open|run)\s+(it|that|this)\b/.test(prompt)
    || /^go ahead\b/.test(prompt)
    || /^yes[, ]+(make|do|start|begin|create|build|ship|open|run)\b/.test(prompt);
}

function promptAuthorizesMutation(promptValue, recentTranscriptValue = '') {
  const prompt = safeText(promptValue, 4000).toLowerCase();
  if (!prompt) return false;
  if (promptDeniesMutation(prompt)) return false;
  if (promptDirectlyAuthorizesMutation(prompt)) return true;
  if (!promptLooksLikeMutationFollowThrough(prompt)) return false;
  const recentTranscript = safeText(recentTranscriptValue, 6000).toLowerCase();
  if (!recentTranscript) return false;
  const recentUserTurns = recentTranscript
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !/^venice\s*:/i.test(line))
    .slice(-6)
    .map((line) => line.replace(/^[^:]+:\s*/, ''));
  return recentUserTurns.some((line) => !promptDeniesMutation(line) && promptDirectlyAuthorizesMutation(line));
}

function fortressControlIntentFromPrompt(promptValue) {
  const prompt = safeText(promptValue, 4000).toLowerCase();
  if (!prompt) return '';
  if (
    /^(we('| a)?re)\s+(fixing|working on|patching|repairing|debugging|investigating)\b/.test(prompt)
    || /^(current objective|objective is|task is)\b/.test(prompt)
    || /\bfortress online\b[\s,:;-]+(?:the\s+)?(?:task|objective)\s+is\b/.test(prompt)
    || /\bfortress online\b[\s,:;-]+(we('| a)?re)\s+(fixing|working on|patching|repairing|debugging|investigating)\b/.test(prompt)
  ) {
    return 'objective_update';
  }
  if (/\bfortress online\b/.test(prompt)) return 'fortress_online';
  if (/\b(where were we|what were we (doing|fixing|working on)|what is the current objective|what were we working on|did that finish|did it finish|what happened to that)\b/.test(prompt)) {
    return 'session_status';
  }
  return '';
}

function veniceRequestId(context, toolName, callIndex = 0) {
  const interactionId = safeText(context.discordInteractionId || context.interactionId, 80) || 'unknown';
  const round = Number.isInteger(context.toolRound) ? context.toolRound + 1 : 1;
  return `venice:${interactionId}:${safeText(toolName, 80)}:${round}:${callIndex + 1}`;
}

function veniceCallerNote(context, toolName) {
  const prompt = safeText(context.originalPrompt || '', 240);
  const interactionId = safeText(context.discordInteractionId || context.interactionId, 80);
  return safeText(`Venice Discord delegated tool call via ${toolName}. interactionId=${interactionId}. userPrompt=${prompt}`, 800);
}

function prepareToolArguments(context, tool, toolName, args, callIndex = 0) {
  const cleanArgs = safeObject(args);
  const properties = safeObject(tool && tool.inputSchema && tool.inputSchema.properties);
  if (!toolIsReadOnly(tool)) {
    if (properties.requestId && !safeText(cleanArgs.requestId, 160)) cleanArgs.requestId = veniceRequestId(context, toolName, callIndex);
    if (properties.callerNote && !safeText(cleanArgs.callerNote, 800)) cleanArgs.callerNote = veniceCallerNote(context, toolName);
  }
  return cleanArgs;
}

function normalizeMcpToolResult(result) {
  if (!result || typeof result !== 'object' || !Array.isArray(result.content)) return result;
  const text = result.content
    .filter((item) => item && item.type === 'text' && typeof item.text === 'string')
    .map((item) => item.text)
    .join('\n')
    .trim();
  if (!text) return result;
  try {
    return JSON.parse(text);
  } catch (_) {
    return text;
  }
}

function summarizeFortressWorkItems(items = []) {
  const cleanItems = Array.isArray(items) ? items.slice(0, 2).map((item) => safeObject(item)) : [];
  if (!cleanItems.length) return '';
  return cleanItems
    .map((item) => {
      const state = safeText(item.normalizedState || item.status, 40).toUpperCase();
      const request = safeText(item.requestText, 140);
      const label = request || safeText(item.taskKind, 120) || safeText(item.taskId, 120) || 'work item';
      return state ? `${label} (${state})` : label;
    })
    .filter(Boolean)
    .join('; ');
}

function formatFortressOrientationReply(result = {}) {
  const orientation = safeObject(result.orientation);
  const project = safeObject(orientation.project);
  const workspace = safeObject(orientation.workspace);
  const projectLabel = safeText(project.name, 160) || safeText(project.projectId, 120);
  const workspaceLabel = safeText(workspace.label, 160) || safeText(workspace.workspaceId, 120);
  const objective = safeText(orientation.current_objective, 300);
  const checkpoint = safeText(orientation.last_checkpoint, 240);
  const blockers = safeList(orientation.blockers, 2, 140);
  const pending = summarizeFortressWorkItems(orientation.pending_work);
  const completed = summarizeFortressWorkItems(orientation.recent_completed_work);
  if (!projectLabel && !workspaceLabel && !objective && !checkpoint && !pending && !completed && !blockers.length) {
    return 'Fortress online. Home Center does not have an active project or checkpoint yet.';
  }
  const sentences = ['Fortress online.'];
  if (projectLabel || workspaceLabel) {
    const parts = [];
    if (projectLabel) parts.push(`project ${projectLabel}`);
    if (workspaceLabel) parts.push(`workspace ${workspaceLabel}`);
    sentences.push(`Home Center resolved ${parts.join(', ')}.`);
  }
  if (objective) {
    sentences.push(`Current objective: ${objective}`);
  } else {
    sentences.push('There is no active objective recorded yet.');
  }
  if (checkpoint) sentences.push(`Latest checkpoint: ${checkpoint}`);
  if (pending) sentences.push(`Pending work: ${pending}`);
  if (completed) sentences.push(`Recent completed work: ${completed}`);
  if (blockers.length) sentences.push(`Blockers: ${blockers.join('; ')}`);
  return safeText(sentences.join(' '), 1800);
}

function extractOpenAiFunctionCalls(json = {}) {
  return (Array.isArray(json.output) ? json.output : [])
    .filter((item) => item && item.type === 'function_call')
    .map((item) => ({
      callId: safeText(item.call_id, 160),
      name: safeText(item.name, 160),
      argumentsText: typeof item.arguments === 'string' ? item.arguments : JSON.stringify(item.arguments || {}),
    }))
    .filter((item) => item.callId && item.name);
}

function parseToolArguments(argumentsText) {
  const raw = safeText(argumentsText, 120000);
  if (!raw) return {};
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    const error = new Error(`Tool arguments must be valid JSON: ${err.message || String(err)}`);
    error.status = 400;
    error.code = 'venice_tool_arguments_invalid_json';
    throw error;
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    const error = new Error('Tool arguments must decode to a JSON object.');
    error.status = 400;
    error.code = 'venice_tool_arguments_invalid_shape';
    throw error;
  }
  return parsed;
}

async function recordVeniceToolAudit(context, entry) {
  if (!context || !context.admin || !context.admin.firestore || typeof context.admin.firestore !== 'function') return;
  const firestore = context.admin.firestore();
  const timestamp = context.admin.firestore.FieldValue && typeof context.admin.firestore.FieldValue.serverTimestamp === 'function'
    ? context.admin.firestore.FieldValue.serverTimestamp()
    : new Date().toISOString();
  await firestore.collection('veniceHomeCenterMcpAudit').add({
    timestamp,
    actorKind: 'venice',
    actorId: 'Venice',
    runtimeServiceAccount: safeText(context.runtimeServiceAccount, 320),
    delegatingUser: safeText(context.delegatingUser, 320).toLowerCase(),
    discordUserId: safeText(context.discordUserId, 80),
    discordInteractionId: safeText(context.discordInteractionId, 80),
    toolName: safeText(entry.toolName, 160),
    requestId: safeText(entry.requestId, 160),
    round: Number.isInteger(entry.round) ? entry.round : null,
    status: safeText(entry.status, 80),
    readOnly: entry.readOnly === true,
    requestArguments: deepCloneJson(entry.requestArguments) || {},
    result: deepCloneJson(entry.result) || null,
    error: safeText(entry.error, 1000),
    originalPrompt: safeText(context.originalPrompt, 4000),
  });
}

async function ensureVeniceRuntimeAuthorized(context) {
  const runtimeServiceAccount = safeText(context && context.runtimeServiceAccount, 320);
  if (runtimeServiceAccount !== VENICE_ALLOWED_RUNTIME_SERVICE_ACCOUNT) {
    const err = new Error('Venice MCP delegation is restricted to the approved runtime service account.');
    err.status = 403;
    err.code = 'venice_runtime_service_account_forbidden';
    throw err;
  }
}

async function ensureVeniceTaskCurrent(context) {
  if (context && typeof context.ensureTaskCurrent === 'function') await context.ensureTaskCurrent();
}

async function ensureVeniceHomeCenterAuth(context) {
  if (context.homeCenterAuth) return context.homeCenterAuth;
  await ensureVeniceRuntimeAuthorized(context);
  context.homeCenterAuth = await createDelegatedHomeCenterAuthContext({
    admin: context.admin,
    google: context.google,
    googleClientId: context.googleClientId,
    googleClientSecret: context.googleClientSecret,
    delegatingUser: context.delegatingUser,
    authKind: 'venice_home_center_delegation',
    actorKind: 'venice',
    actorId: 'Venice',
    runtimeServiceAccount: context.runtimeServiceAccount,
    discordUserId: context.discordUserId,
    discordInteractionId: context.discordInteractionId,
  });
  return context.homeCenterAuth;
}

async function ensureVeniceMcpAccessToken(context) {
  const now = Date.now();
  if (context.mcpAccessToken && Number(context.mcpAccessTokenExpiresAtMs || 0) > now + 30 * 1000) return context.mcpAccessToken;
  await ensureVeniceRuntimeAuthorized(context);
  const email = safeText(context.delegatingUser, 320).toLowerCase();
  if (!email) {
    const err = new Error('Venice delegated Home Center user is not configured.');
    err.status = 500;
    err.code = 'venice_delegating_user_missing';
    throw err;
  }
  const snap = await context.admin.firestore().collection('googleToolTokens').doc(email).get();
  if (!snap.exists) {
    const err = new Error('Google tools are not connected for the delegated Home Center account.');
    err.status = 409;
    err.code = 'google_tools_not_connected';
    throw err;
  }
  const data = snap.data() || {};
  if (!data.tokens || typeof data.tokens !== 'object') {
    const err = new Error('Delegated Home Center account is missing renewable Google tool tokens.');
    err.status = 409;
    err.code = 'google_tools_not_connected';
    throw err;
  }
  const accessToken = randomToken(32);
  const expiresAtMs = now + 55 * 60 * 1000;
  await context.admin.firestore().collection('mcpOAuthAccessTokens').doc(tokenHash(accessToken)).set({
    clientId: `venice-discord:${safeText(context.discordInteractionId, 80) || 'runtime'}`,
    email,
    googleTokens: data.tokens,
    source: 'venice_discord_runtime',
    authKind: 'venice_home_center_delegation',
    actorKind: 'venice',
    actorId: 'Venice',
    runtimeServiceAccount: safeText(context.runtimeServiceAccount, 320),
    delegatingUser: email,
    discordUserId: safeText(context.discordUserId, 80),
    discordInteractionId: safeText(context.discordInteractionId, 80),
    createdAtMs: now,
    expiresAtMs,
  }, {merge: false});
  context.mcpAccessToken = accessToken;
  context.mcpAccessTokenExpiresAtMs = expiresAtMs;
  context.mcpInitialized = false;
  return accessToken;
}

function parseMcpRpcPayload(text) {
  const raw = String(text || '');
  if (!raw.trim()) return {};
  if (/(^|\r?\n)data:\s*/.test(raw) || raw.trimStart().startsWith('event:')) {
    const dataText = raw.split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('\n');
    return JSON.parse(dataText || '{}');
  }
  return JSON.parse(raw);
}

async function postHomeCenterMcp(context, body) {
  const token = await ensureVeniceMcpAccessToken(context);
  const response = await fetch(safeText(context.mcpUrl, 2000) || HOME_CENTER_MCP_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
    },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let json = {};
  try {
    json = parseMcpRpcPayload(text);
  } catch (err) {
    const error = new Error(`Home Center MCP returned non-JSON payload: ${err.message || String(err)}`);
    error.status = 502;
    error.code = 'venice_mcp_invalid_response';
    throw error;
  }
  if (!response.ok) {
    const error = new Error((json.error && json.error.message) || `home_center_mcp_http_${response.status}`);
    error.status = response.status;
    error.code = `home_center_mcp_http_${response.status}`;
    throw error;
  }
  if (json.error) {
    const error = new Error(json.error.message || 'Home Center MCP request failed.');
    error.status = 502;
    error.code = 'venice_mcp_rpc_error';
    throw error;
  }
  return json.result || {};
}

async function initializeHomeCenterMcp(context) {
  if (context.mcpInitialized) return;
  await postHomeCenterMcp(context, {
    jsonrpc: '2.0',
    id: `venice-init-${safeText(context.discordInteractionId, 80) || 'runtime'}`,
    method: 'initialize',
    params: {
      protocolVersion: '2025-06-18',
      capabilities: {},
      clientInfo: {name: 'venice-discord-runtime', version: '1'},
    },
  });
  await postHomeCenterMcp(context, {
    jsonrpc: '2.0',
    method: 'notifications/initialized',
    params: {},
  });
  context.mcpInitialized = true;
}

function ensureVeniceMutationAllowed(context, tool, toolName) {
  if (toolIsReadOnly(tool)) return;
  if (context.allowMutations === true) return;
  if (context.allowSessionControl === true && VENICE_SESSION_CONTROL_TOOLS.has(toolName)) return;
  const err = new Error(`Venice may not execute mutating Home Center tool ${toolName} for this request.`);
  err.status = 403;
  err.code = 'venice_mutation_not_authorized';
  throw err;
}

function resolveHomeCenterServer(context) {
  if (context.homeCenterServer) return context.homeCenterServer;
  context.homeCenterServer = createHomeCenterMcpServer({
    google: context.google,
    admin: context.admin,
    googleClientId: context.googleClientId,
    googleClientSecret: context.googleClientSecret,
    githubToken: context.githubToken,
    githubAdmin: context.githubAdmin,
    cartesiaApiKey: context.cartesiaApiKey,
    geminiApiKey: context.geminiApiKey,
  });
  return context.homeCenterServer;
}

async function listVeniceHomeCenterTools(context) {
  await ensureVeniceRuntimeAuthorized(context);
  if (usesHttpMcpTransport(context)) {
    await initializeHomeCenterMcp(context);
    const result = await postHomeCenterMcp(context, {
      jsonrpc: '2.0',
      id: `venice-tools-${safeText(context.discordInteractionId, 80) || 'runtime'}`,
      method: 'tools/list',
      params: {},
    });
    return Array.isArray(result.tools) ? result.tools : [];
  }
  return registeredHomeCenterTools(resolveHomeCenterServer(context));
}

async function callVeniceHomeCenterTool(context, name, args, options = {}) {
  await ensureVeniceTaskCurrent(context);
  await ensureVeniceRuntimeAuthorized(context);
  const tools = options.tools || await listVeniceHomeCenterTools(context);
  const tool = toolDefinitionByName(tools, name);
  if (!tool) {
    const err = new Error(`Unknown Home Center MCP tool: ${name}`);
    err.status = 404;
    err.code = 'venice_tool_not_found';
    throw err;
  }
  ensureVeniceMutationAllowed(context, tool, name);
  const preparedArgs = prepareToolArguments(context, tool, name, args, Number(options.callIndex || 0));
  try {
    let rawResult;
    if (usesHttpMcpTransport(context)) {
      await initializeHomeCenterMcp(context);
      rawResult = await postHomeCenterMcp(context, {
        jsonrpc: '2.0',
        id: veniceRequestId(context, name, Number(options.callIndex || 0)),
        method: 'tools/call',
        params: {name, arguments: preparedArgs},
      });
    } else {
      const authContext = tool.name === 'health' || tool.name === 'readiness'
        ? null
        : await ensureVeniceHomeCenterAuth(context);
      rawResult = await callRegisteredHomeCenterTool(
        resolveHomeCenterServer(context),
        name,
        preparedArgs,
        authContext ? {homeCenterAuth: authContext} : {},
      );
    }
    const result = normalizeMcpToolResult(rawResult);
    await recordVeniceToolAudit(context, {
      toolName: name,
      requestId: safeText(preparedArgs.requestId, 160),
      round: Number.isInteger(context.toolRound) ? context.toolRound + 1 : null,
      status: 'success',
      readOnly: toolIsReadOnly(tool),
      requestArguments: preparedArgs,
      result,
    });
    return result;
  } catch (err) {
    await recordVeniceToolAudit(context, {
      toolName: name,
      requestId: safeText(preparedArgs.requestId, 160),
      round: Number.isInteger(context.toolRound) ? context.toolRound + 1 : null,
      status: 'error',
      readOnly: toolIsReadOnly(tool),
      requestArguments: preparedArgs,
      error: err && (err.stack || err.message || String(err)),
    });
    throw err;
  }
}

async function runVeniceFortressControlTurn({context, controlTurn} = {}) {
  const kind = safeText(controlTurn && controlTurn.kind, 80).toLowerCase();
  if (kind !== 'fortress_online') {
    const err = new Error('Unsupported Venice control turn.');
    err.status = 400;
    err.code = 'venice_control_turn_unsupported';
    throw err;
  }
  const result = await callVeniceHomeCenterTool(context, 'fortress_online', {});
  return formatFortressOrientationReply(result);
}

function homeCenterToolsToOpenAI(mcpTools) {
  return (Array.isArray(mcpTools) ? mcpTools : []).map((tool) => ({
    type: 'function',
    name: safeText(tool && tool.name, 160),
    description: safeText(tool && (tool.description || tool.title), 1200),
    parameters: deepCloneJson(tool && tool.inputSchema) || {type: 'object', properties: {}, additionalProperties: false},
  })).filter((tool) => tool.name);
}

async function runVeniceHomeCenterToolLoop({
  context,
  prompt,
  requestBody,
  fetchOpenAIResponses,
  extractOutputText,
  veniceReplyNeedsRepair,
  repairReply,
  geminiFallback = null,
  maxToolRounds = VENICE_MAX_TOOL_ROUNDS,
} = {}) {
  const tools = await listVeniceHomeCenterTools(context);
  const openAiTools = homeCenterToolsToOpenAI(tools);
  const baseRequest = {...safeObject(requestBody), tools: openAiTools};
  let input = prompt;
  let toolExecutionStarted = false;
  let emptyFinalRecoveryUsed = false;
  for (let round = 0; round < maxToolRounds; round += 1) {
    context.toolRound = round;
    const {response, json} = await fetchOpenAIResponses({...baseRequest, input});
    if (!response.ok) {
      if (response.status === 429 && !toolExecutionStarted && typeof geminiFallback === 'function') return geminiFallback();
      const err = new Error(`venice_openai_http_${response.status}`);
      err.code = `venice_openai_http_${response.status}`;
      throw err;
    }
    const calls = extractOpenAiFunctionCalls(json);
    if (!calls.length) {
      let reply = safeText(json.output_text || extractOutputText(json), 2000);
      if (!reply) {
        if (!toolExecutionStarted && !emptyFinalRecoveryUsed) {
          emptyFinalRecoveryUsed = true;
          input = `${prompt}\n\nRecovery rule: either call the appropriate Home Center tool now, or reply to Drew in one complete Discord-safe message. Do not return an empty response.`;
          continue;
        }
        const err = new Error('venice_openai_empty');
        err.code = 'venice_openai_empty';
        throw err;
      }
      if (veniceReplyNeedsRepair(reply, json)) {
        if (typeof repairReply !== 'function') throw new Error('venice_openai_incomplete');
        reply = await repairReply(reply);
      }
      return reply;
    }
    toolExecutionStarted = true;
    const outputs = [];
    for (let i = 0; i < calls.length; i += 1) {
      await ensureVeniceTaskCurrent(context);
      const call = calls[i];
      const parsedArgs = parseToolArguments(call.argumentsText);
      const result = await callVeniceHomeCenterTool(context, call.name, parsedArgs, {tools, callIndex: i});
      outputs.push({
        type: 'function_call_output',
        call_id: call.callId,
        output: typeof result === 'string' ? result : JSON.stringify(result),
      });
    }
    input = [...(Array.isArray(json.output) ? json.output : []), ...outputs];
  }
  const err = new Error('venice_tool_round_limit');
  err.code = 'venice_tool_round_limit';
  throw err;
}

module.exports = {
  VENICE_ALLOWED_RUNTIME_SERVICE_ACCOUNT,
  VENICE_MAX_TOOL_ROUNDS,
  extractOpenAiFunctionCalls,
  homeCenterToolsToOpenAI,
  listVeniceHomeCenterTools,
  callVeniceHomeCenterTool,
  runVeniceFortressControlTurn,
  runVeniceHomeCenterToolLoop,
  promptAuthorizesMutation,
  fortressControlIntentFromPrompt,
};
