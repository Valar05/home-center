import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {homedir} from 'node:os';
import {chromium} from 'playwright';
import {detectPageBlockers, normalizeStartUrl, redactText, safeText, snapshotPage} from './browser_worker.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..');
const DEFAULT_VIEWPORT = {width: 1366, height: 900};
const DEFAULT_ARGS = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'];
const DEFAULT_HOME_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const DEFAULT_COMMAND_CENTER_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const SETTINGS_URL = 'https://chatgpt.com/#settings/Plugins';
const PLUGINS_URL = 'https://chatgpt.com/plugins';
const CHAT_URL = 'https://chatgpt.com/';

function arg(name, fallback = '') {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function hasFlag(name) {
  return process.argv.includes(`--${name}`);
}

function runId() {
  return safeText(arg('run-id', `clean_slate_${Date.now()}`), 120).replace(/[^a-zA-Z0-9_-]/g, '_');
}

function classifySnapshot(snapshot, expectedUrls = []) {
  const text = `${snapshot.title || ''}\n${snapshot.url || ''}\n${snapshot.visibleTextSummary || ''}`;
  const blockers = detectPageBlockers(snapshot);
  const hasTurnstile = Array.isArray(snapshot.landmarks) && snapshot.landmarks.some((item) => /cf-turnstile|turnstile/i.test(`${item.name || ''} ${item.type || ''} ${item.text || ''}`));
  if (/cloudflare|checking your browser|verify you are human|captcha|not a robot|just a moment/i.test(text) || hasTurnstile) {
    return {status: 'blocked_chatgpt_auth', reason: 'ChatGPT web is behind human/browser verification.', blockers: [...blockers, 'human verification']};
  }
  if (/\b(log in|login|sign up|sign in|continue with google|continue with apple)\b/i.test(text)) {
    return {status: 'blocked_chatgpt_auth', reason: 'Playwright reached ChatGPT, but the Chromium profile is not signed in.', blockers};
  }
  const mentionsConnectorSurface = /plugins|connectors|developer mode|settings|mcp|actions|apps/i.test(text);
  const mentionsExpected = expectedUrls.some((url) => text.includes(url)) || /home center|homecenter|command center|commandcenter/i.test(text);
  const disconnected = /disconnected|couldn'?t connect|could not connect|problem connecting|connection failed|reconnect|oauth error|authorization failed/i.test(text);
  const connected = /connected|enabled|installed|added|configured/i.test(text);
  if (mentionsExpected && disconnected) return {status: 'blocked_chatgpt_ui', reason: 'ChatGPT shows Home Center or Command Center but reports disconnected state.', blockers};
  if (mentionsExpected && connected && !disconnected) return {status: 'connectors_visible_connected', reason: 'Expected connector labels or URLs appear connected.', blockers};
  if (mentionsConnectorSurface) return {status: 'connector_surface_unknown', reason: 'ChatGPT connector settings loaded, but expected connector connected state is not visible.', blockers};
  return {status: 'unknown', reason: 'ChatGPT loaded, but verifier did not recognize auth, connector settings, or connector state.', blockers};
}

function connectorEvidence(snapshot, urls = []) {
  const text = `${snapshot.visibleTextSummary || ''}`;
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const labels = ['Home Center', 'Command Center', 'homeCenterMcp', 'commandCenterMcp', ...urls];
  const matches = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (labels.some((label) => line.toLowerCase().includes(String(label).toLowerCase()))) {
      matches.push({line: redactText(line), before: redactText(lines[i - 1] || ''), after: redactText(lines[i + 1] || '')});
    }
  }
  const landmarks = (snapshot.landmarks || [])
    .filter((item) => labels.some((label) => `${item.text} ${item.name} ${item.href} ${item.id}`.toLowerCase().includes(String(label).toLowerCase())))
    .slice(0, 30)
    .map((item) => ({tag: item.tag, role: item.role, text: redactText(item.text || ''), name: redactText(item.name || ''), href: item.href || '', id: item.id || '', bounds: item.bounds || []}));
  return {matches, landmarks};
}

function connectorStateFromSnapshot(snapshot, homeMcpUrl) {
  const text = `${snapshot.title || ''}\n${snapshot.url || ''}\n${snapshot.visibleTextSummary || ''}`;
  const lower = text.toLowerCase();
  const mentionsHome = lower.includes('home center') || lower.includes('homecentermcp') || lower.includes(homeMcpUrl.toLowerCase());
  const disconnected = /disconnected|couldn'?t connect|could not connect|problem connecting|connection failed|reconnect|oauth error|authorization failed/i.test(text);
  const connected = /connected|enabled|installed|added|configured/i.test(text);
  if (mentionsHome && connected && !disconnected) return {status: 'connected', reason: 'Home Center appears connected in ChatGPT connector UI.'};
  if (mentionsHome && disconnected) return {status: 'disconnected', reason: 'Home Center appears present but disconnected in ChatGPT connector UI.'};
  if (mentionsHome) return {status: 'present_unknown', reason: 'Home Center appears in ChatGPT connector UI, but connected state is not explicit.'};
  return {status: 'missing', reason: 'Home Center is not visible in ChatGPT connector UI.'};
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

function toolContentJson(payload, label) {
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '';
  return parseJson(text, label);
}

async function readPairingToken(configPath) {
  try {
    const raw = parseJson(await fs.readFile(configPath, 'utf8'), configPath);
    if (raw.accessToken && Number(raw.expiresAtMs || 0) > Date.now() + 60000) return {token: raw.accessToken, configPath, refreshed: false};
    if (!raw.refreshToken) return {token: raw.accessToken || raw.bearerToken || raw.token || '', configPath, refreshed: false, reason: 'refresh token missing'};
    const gatewayBase = raw.gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net';
    const response = await fetch(`${gatewayBase}/termuxTokenRefresh`, {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({refreshToken: raw.refreshToken}),
    });
    const json = parseJson(await response.text(), 'termuxTokenRefresh');
    if (!response.ok || !json.ok || !json.access_token) return {token: raw.accessToken || '', configPath, refreshed: false, reason: `refresh failed status=${response.status}`};
    const next = {
      ...raw,
      accessToken: json.access_token,
      tokenType: json.token_type || raw.tokenType || 'Bearer',
      expiresAtMs: Date.now() + Number(json.expires_in || 0) * 1000,
      allowedGroups: json.allowedGroups || raw.allowedGroups || [],
      refreshedAt: new Date().toISOString(),
    };
    await fs.writeFile(configPath, JSON.stringify(next, null, 2) + '\n', {mode: 0o600});
    return {token: next.accessToken, configPath, refreshed: true};
  } catch (err) {
    return {token: '', configPath, refreshed: false, reason: err.message || String(err)};
  }
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
  return {status: response.status, text: await response.text(), headers: Object.fromEntries(response.headers.entries())};
}

async function callMcpTool(mcpUrl, token, id, name, toolArgs = {}) {
  const response = await postMcp(mcpUrl, token, {jsonrpc: '2.0', id, method: 'tools/call', params: {name, arguments: toolArgs}});
  const json = parseMcpResponse(response.text, `tools/call ${name}`);
  return {status: response.status, result: toolContentJson(json, `tools/call ${name}`)};
}

async function commandCenterBucketReadback({mcpUrl, token, objectId}) {
  if (!token) return {ok: false, status: 'blocked_local_setup', reason: 'No Home Center paired token is available for bucket readback.'};
  const init = await postMcp(mcpUrl, token, {jsonrpc: '2.0', id: 800, method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'chatgpt-clean-slate-bucket-readback', version: '1'}}});
  if (init.status !== 200) return {ok: false, status: 'blocked_backend_readback', reason: `MCP initialize failed with ${init.status}`, body: init.text.slice(0, 500)};
  await postMcp(mcpUrl, token, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}}).catch(() => null);
  const read = await callMcpTool(mcpUrl, token, 801, 'command_center_operation', {operation: 'bucket.get_object', args: {objectId}});
  const object = read.result?.result?.object || read.result?.object || null;
  return {
    ok: read.status === 200 && object?.objectId === objectId && object?.body === 'hello world',
    status: read.status === 200 ? 'bucket_readback_complete' : 'blocked_backend_readback',
    objectId,
    bodyMatches: object?.body === 'hello world',
    path: object?.path || '',
    readback: read.result,
  };
}

async function commandCenterReadback({mcpUrl, token, activationId}) {
  if (!token) return {ok: false, status: 'blocked_local_setup', reason: 'No Home Center paired token is available for backend readback.'};
  const init = await postMcp(mcpUrl, token, {jsonrpc: '2.0', id: 900, method: 'initialize', params: {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'chatgpt-clean-slate-readback', version: '1'}}});
  if (init.status !== 200) return {ok: false, status: 'blocked_backend_readback', reason: `MCP initialize failed with ${init.status}`, body: init.text.slice(0, 500)};
  await postMcp(mcpUrl, token, {jsonrpc: '2.0', method: 'notifications/initialized', params: {}}).catch(() => null);
  const read = await callMcpTool(mcpUrl, token, 901, 'command_center_operation', {operation: 'agents.get_resume_packet', args: {activationId}});
  const packet = read.result?.result?.resumePacket || read.result?.resumePacket || null;
  return {
    ok: read.status === 200 && packet?.packetVersion === 'command-center-codex-cloud-resume-v1',
    status: read.status === 200 ? 'readback_complete' : 'blocked_backend_readback',
    activationId,
    packetVersion: packet?.packetVersion || '',
    sessionId: packet?.session?.sessionId || '',
    agentId: packet?.agent?.agentId || '',
    readback: read.result,
  };
}

async function firstVisible(locators) {
  for (const locator of locators) {
    try {
      const count = await locator.count();
      for (let i = 0; i < Math.min(count, 8); i += 1) {
        const item = locator.nth(i);
        if (await item.isVisible({timeout: 500}).catch(() => false)) return item;
      }
    } catch (_) {}
  }
  return null;
}

async function fillComposer(page, prompt) {
  const composer = await firstVisible([
    page.getByRole('textbox'),
    page.locator('textarea'),
    page.locator('[contenteditable="true"]'),
    page.locator('[data-testid="composer-text-input"]'),
    page.locator('#prompt-textarea'),
  ]);
  if (!composer) return {ok: false, reason: 'No visible ChatGPT composer textbox was found.'};
  await composer.click({timeout: 5000});
  await composer.fill(prompt, {timeout: 10000}).catch(async () => {
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
    await page.keyboard.type(prompt, {delay: 0});
  });
  return {ok: true};
}

async function clickSend(page) {
  const send = await firstVisible([
    page.getByRole('button', {name: /^send/i}),
    page.locator('[data-testid="send-button"]'),
    page.locator('button[aria-label*="Send" i]'),
    page.locator('button:has(svg)').last(),
  ]);
  if (!send) return {ok: false, reason: 'No visible ChatGPT send button was found.'};
  await send.click({timeout: 5000});
  return {ok: true};
}

async function clickFirstVisible(page, locators, timeoutMs = 2500) {
  const target = await firstVisible(locators);
  if (!target) return {ok: false, reason: 'No matching visible control found.'};
  await target.click({timeout: timeoutMs});
  return {ok: true};
}

async function fillFirstVisible(page, locators, value, timeoutMs = 5000) {
  const target = await firstVisible(locators);
  if (!target) return {ok: false, reason: 'No matching visible input found.'};
  await target.click({timeout: timeoutMs});
  await target.fill(value, {timeout: timeoutMs}).catch(async () => {
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
    await page.keyboard.type(value, {delay: 0});
  });
  return {ok: true};
}

async function waitForNoopResult(page, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastText = '';
  while (Date.now() < deadline) {
    await page.waitForTimeout(3000);
    lastText = await page.locator('body').innerText({timeout: 3000}).catch(() => '');
    if (/hello world/i.test(lastText) && /(objectId|object id|bucket|path)/i.test(lastText)) {
      const objectId = (lastText.match(/(?:objectId|object id)\s*[:=]?\s*([A-Za-z0-9_-]{12,})/i) || [])[1] || '';
      return {ok: true, objectId, textSample: redactText(lastText).slice(-4000)};
    }
    if (/cloudflare|verify you are human|captcha|not a robot/i.test(lastText)) {
      return {ok: false, status: 'blocked_chatgpt_auth', reason: 'ChatGPT verification appeared during tool-call proof.', textSample: redactText(lastText).slice(-4000)};
    }
  }
  return {ok: false, status: 'blocked_chatgpt_ui', reason: 'Timed out waiting for ChatGPT no-op readback.', textSample: redactText(lastText).slice(-4000)};
}

function bucketProofSpec(id) {
  const compact = id.toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/_+/g, '-').slice(0, 48) || 'bucket-proof';
  const objectId = `chatgpt_hello_world_${compact}`.replace(/-+/g, '-').slice(0, 120);
  const bucketPath = `notes/cross-repo/chatgpt-hello-world-${compact}.md`;
  return {runKey: compact, objectId, bucketPath};
}

function bucketProofPrompt(spec) {
  return [
    'Use connected Home Center MCP tools now. Do not answer from memory and do not simulate tool output.',
    'Call command_center_operation with operation bucket.put_object and args ' + JSON.stringify({
      kind: 'note.cross_repo',
      objectId: spec.objectId,
      path: spec.bucketPath,
      title: 'ChatGPT clean slate hello world',
      summary: 'ChatGPT clean slate verifier no-op',
      body: 'hello world',
      projectId: 'home-center',
      repository: 'Valar05/home-center',
      tags: ['chatgpt-clean-slate', 'hello-world', 'effective-no-op'],
      idempotencyKey: `chatgpt-clean-slate-${spec.runKey}`,
    }) + '.',
    `Then call command_center_operation with operation bucket.get_object and args {"objectId":"${spec.objectId}"}.`,
    `Reply only JSON: {"objectId":"${spec.objectId}","path":"${spec.bucketPath}","bodyMatches":true}.`,
  ].join(' ');
}

async function waitForBucketProof({page, timeoutMs, readbackConfig}) {
  const deadline = Date.now() + timeoutMs;
  let lastText = '';
  let lastReadback = null;
  while (Date.now() < deadline) {
    await page.waitForTimeout(3000);
    lastReadback = await commandCenterBucketReadback(readbackConfig).catch((err) => ({ok: false, status: 'blocked_backend_readback', reason: err.message || String(err)}));
    if (lastReadback.ok) return {ok: true, status: 'ok', reason: 'Backend bucket readback succeeded.', readback: lastReadback};
    lastText = await page.locator('body').innerText({timeout: 3000}).catch(() => '');
    if (/does not expose command_center_operation|tool unavailable|no available tool|can't access|not available in the attached/i.test(lastText)) {
      return {ok: false, status: 'chatgpt_answered_without_tool_call', reason: 'ChatGPT answered without invoking the required Home Center MCP tool.', textSample: redactText(lastText).slice(-4000), readback: lastReadback};
    }
    if (/cloudflare|verify you are human|captcha|not a robot/i.test(lastText)) {
      return {ok: false, status: 'blocked_chatgpt_auth', reason: 'ChatGPT verification appeared during bucket proof.', textSample: redactText(lastText).slice(-4000), readback: lastReadback};
    }
  }
  return {ok: false, status: 'blocked_chatgpt_ui', reason: 'Timed out waiting for backend bucket readback.', textSample: redactText(lastText).slice(-4000), readback: lastReadback};
}

async function ensureHomeCenterConnected(page, {homeMcpUrl, outDir, artifacts, events}) {
  await page.goto(SETTINGS_URL, {waitUntil: 'domcontentloaded', timeout: 45000});
  await page.waitForTimeout(5000);
  let snapshot = await snapshotPage(page);
  artifacts.push({name: 'ensure_settings', screenshotPath: await screenshot(page, outDir, 'ensure_settings'), snapshot});
  let state = connectorStateFromSnapshot(snapshot, homeMcpUrl);
  events.push({phase: 'ensure_home_center_settings', state});
  if (state.status === 'connected' || state.status === 'present_unknown') return {ok: true, state, installedByGate: false};

  await page.goto(PLUGINS_URL, {waitUntil: 'domcontentloaded', timeout: 45000}).catch(async () => {
    await page.goto(SETTINGS_URL, {waitUntil: 'domcontentloaded', timeout: 45000});
  });
  await page.waitForTimeout(3000);
  snapshot = await snapshotPage(page);
  artifacts.push({name: 'ensure_plugins_start', screenshotPath: await screenshot(page, outDir, 'ensure_plugins_start'), snapshot});

  const search = await fillFirstVisible(page, [
    page.getByRole('searchbox'),
    page.getByPlaceholder(/search/i),
    page.locator('input[type="search"]'),
    page.locator('input').filter({hasText: /search/i}),
  ], 'Home Center', 5000).catch((err) => ({ok: false, reason: err.message || String(err)}));
  events.push({phase: 'ensure_home_center_search', search});
  if (search.ok) {
    await page.keyboard.press('Enter').catch(() => {});
    await page.waitForTimeout(3000);
    const clickedHome = await clickFirstVisible(page, [
      page.getByRole('button', {name: /home center/i}),
      page.getByRole('link', {name: /home center/i}),
      page.getByText(/home center/i).first(),
    ], 5000).catch((err) => ({ok: false, reason: err.message || String(err)}));
    events.push({phase: 'ensure_home_center_select_existing', clickedHome});
    await page.waitForTimeout(2000);
  }

  await clickFirstVisible(page, [
    page.getByRole('button', {name: /create app|new app|add app|create/i}),
    page.getByLabel(/create app|new app|add app/i),
    page.locator('button[aria-label*="Create" i]'),
    page.locator('button').filter({hasText: /^\+$/}).first(),
  ], 5000).catch((err) => events.push({phase: 'ensure_home_center_create_app_not_clicked', reason: err.message || String(err)}));
  await page.waitForTimeout(2000);

  const filledName = await fillFirstVisible(page, [
    page.getByLabel(/name/i),
    page.getByPlaceholder(/name/i),
    page.locator('input[name*="name" i]'),
    page.locator('input').first(),
  ], 'Home Center', 5000).catch((err) => ({ok: false, reason: err.message || String(err)}));
  const filledUrl = await fillFirstVisible(page, [
    page.getByLabel(/mcp|server|url/i),
    page.getByPlaceholder(/mcp|server|url|https/i),
    page.locator('input[type="url"]'),
    page.locator('input').nth(1),
  ], homeMcpUrl, 5000).catch((err) => ({ok: false, reason: err.message || String(err)}));
  events.push({phase: 'ensure_home_center_fill_create_app', filledName, filledUrl});

  const connect = await clickFirstVisible(page, [
    page.getByRole('button', {name: /connect|create|add|save|install|continue|authorize/i}),
    page.locator('button').filter({hasText: /connect|create|add|save|install|continue|authorize/i}).first(),
  ], 5000).catch((err) => ({ok: false, reason: err.message || String(err)}));
  events.push({phase: 'ensure_home_center_connect_clicked', connect});
  await page.waitForTimeout(8000);

  for (let i = 0; i < 6; i += 1) {
    await clickFirstVisible(page, [
      page.getByRole('button', {name: /continue|authorize|allow|connect|approve|use home center/i}),
      page.locator('button').filter({hasText: /continue|authorize|allow|connect|approve|use home center/i}).first(),
    ], 3000).catch(() => null);
    await page.waitForTimeout(3000);
    snapshot = await snapshotPage(page);
    state = connectorStateFromSnapshot(snapshot, homeMcpUrl);
    events.push({phase: `ensure_home_center_after_connect_${i + 1}`, state, url: snapshot.url});
    if (state.status === 'connected' || /chatgpt\.com/.test(snapshot.url) && state.status === 'present_unknown') {
      artifacts.push({name: 'ensure_home_center_done', screenshotPath: await screenshot(page, outDir, 'ensure_home_center_done'), snapshot});
      return {ok: true, state, installedByGate: true};
    }
    const classified = classifySnapshot(snapshot, [homeMcpUrl]);
    if (classified.status === 'blocked_chatgpt_auth') {
      artifacts.push({name: 'ensure_home_center_blocked_auth', screenshotPath: await screenshot(page, outDir, 'ensure_home_center_blocked_auth'), snapshot});
      return {ok: false, status: 'blocked_chatgpt_auth', reason: classified.reason, state};
    }
  }
  artifacts.push({name: 'ensure_home_center_failed', screenshotPath: await screenshot(page, outDir, 'ensure_home_center_failed'), snapshot});
  return {ok: false, status: 'blocked_chatgpt_ui', reason: 'Home Center connector install/connect flow did not reach connected state.', state};
}

function agentActivationSpec(id) {
  const compact = id.toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/_+/g, '-').slice(0, 48) || 'agent-proof';
  const activationId = `activation_${id.replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 96)}`;
  const agentId = `hc-cgpt-${compact}`.replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 120);
  return {activationId, agentId, runKey: compact};
}

function agentActivationPrompt({agentId, activationId, runKey}) {
  return `Use MCP tool command_center_operation now; do not answer from memory. Call operation agents.upsert_repo_agent with args {"idempotencyKey":"up-${runKey}","agentId":"${agentId}","projectId":"home-center","name":"Home Center MCP proof","repository":"Valar05/home-center"}. Then call operation agents.create_activation with args {"idempotencyKey":"act-${runKey}","activationId":"${activationId}","agentId":"${agentId}","title":"ChatGPT MCP proof","prompt":"Return next action.","acceptanceCriteria":["created by ChatGPT"],"artifactRequirements":["final-report.md"]}. Then call operation agents.get_resume_packet with args {"activationId":"${activationId}"}. Reply JSON with agentId, sessionId, activationId, packetVersion.`;
}

async function waitForAgentActivationResult(page, timeoutMs, readbackConfig) {
  const deadline = Date.now() + timeoutMs;
  let lastText = '';
  let lastReadback = null;
  while (Date.now() < deadline) {
    await page.waitForTimeout(4000);
    lastReadback = await commandCenterReadback(readbackConfig).catch((err) => ({ok: false, status: 'blocked_backend_readback', reason: err.message || String(err)}));
    if (lastReadback.ok) return {ok: true, status: 'ok', reason: 'Command Center activation readback succeeded.', readback: lastReadback};
    lastText = await page.locator('body').innerText({timeout: 3000}).catch(() => '');
    if (/"agentId"\s*:\s*null[\s\S]*"activationId"\s*:\s*null|does not expose command_center_operation|does not expose.*agents\.create_activation|tool unavailable|no available tool|can't access/i.test(lastText)) {
      return {ok: false, status: 'chatgpt_answered_without_tool_call', reason: 'ChatGPT answered without invoking the required MCP tool.', textSample: redactText(lastText).slice(-4000), readback: lastReadback};
    }
    if (/cloudflare|verify you are human|captcha|not a robot/i.test(lastText)) {
      return {ok: false, status: 'blocked_chatgpt_auth', reason: 'ChatGPT verification appeared during agent activation proof.', textSample: redactText(lastText).slice(-4000), readback: lastReadback};
    }
  }
  return {ok: false, status: 'blocked_chatgpt_ui', reason: 'Timed out waiting for ChatGPT-created agent activation readback.', textSample: redactText(lastText).slice(-4000), readback: lastReadback};
}

async function screenshot(page, outDir, name) {
  const screenshotPath = path.join(outDir, `${name}.png`);
  await page.screenshot({path: screenshotPath, fullPage: true}).catch(() => {});
  return screenshotPath;
}

async function main() {
  const id = runId();
  const homeMcpUrl = normalizeStartUrl(arg('home-mcp-url', DEFAULT_HOME_MCP_URL));
  const commandCenterMcpUrl = normalizeStartUrl(arg('command-center-mcp-url', DEFAULT_COMMAND_CENTER_MCP_URL));
  const startUrl = normalizeStartUrl(arg('url', SETTINGS_URL));
  const outDir = path.resolve(arg('out-dir', path.join(repoRoot, 'generated', 'chatgpt-plugin-debug', id)));
  const userDataDir = path.resolve(arg('user-data-dir', process.env.HOME_CENTER_CHATGPT_PROFILE_DIR || '/tmp/home-center-chatgpt-playwright-profile')); // Chromium profile must live on a Linux filesystem; Android shared storage cannot create SingletonLock.
  const executablePath = safeText(arg('executable-path', process.env.HOME_CENTER_CHROMIUM_EXECUTABLE || ''), 1000);
  const cdpUrl = safeText(arg('cdp-url', process.env.HOME_CENTER_CHROME_CDP_URL || ''), 1000);
  const headless = !hasFlag('headed') && process.env.HEADLESS !== '0';
  const verifyPrompt = hasFlag('verify-prompt');
  const ensureHomeCenter = hasFlag('ensure-home-center-connected');
  const promptMode = safeText(arg('prompt-mode', 'noop'), 80) || 'noop';
  const promptTimeoutMs = Math.max(10000, Math.min(Number(arg('prompt-timeout-ms', '90000')), 180000));
  const expectedUrls = [homeMcpUrl, commandCenterMcpUrl];
  const tokenConfig = path.resolve(arg('token-config', process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json')));

  if (!cdpUrl && !headless && !process.env.DISPLAY) {
    console.log(JSON.stringify({ok: false, status: 'blocked_local_setup', reason: 'Headed Playwright requires DISPLAY in Debian/proot.', nextAction: 'Start Termux:X11 or run headless for non-interactive classification.'}));
    process.exit(1);
  }

  await fs.mkdir(outDir, {recursive: true});
  let browser = null;
  let context = null;
  let page = null;
  if (cdpUrl) {
    browser = await chromium.connectOverCDP(cdpUrl, {timeout: Number(arg('timeout-ms', '45000'))});
    context = browser.contexts()[0] || await browser.newContext({viewport: DEFAULT_VIEWPORT, isMobile: false, hasTouch: false, locale: 'en-US'});
    page = context.pages()[0] || await context.newPage();
  } else {
    await fs.mkdir(userDataDir, {recursive: true});
    const launchOptions = {headless, viewport: DEFAULT_VIEWPORT, isMobile: false, hasTouch: false, locale: 'en-US', args: DEFAULT_ARGS};
    if (executablePath) launchOptions.executablePath = executablePath;
    context = await chromium.launchPersistentContext(userDataDir, launchOptions);
    page = context.pages()[0] || await context.newPage();
  }
  const artifacts = [];
  const events = [];
  let result;
  try {
    await page.goto(startUrl, {waitUntil: 'domcontentloaded', timeout: Number(arg('timeout-ms', '45000'))});
    await page.waitForTimeout(Math.max(0, Math.min(Number(arg('wait-ms', '7000')), 60000)));
    const settingsSnapshot = await snapshotPage(page);
    artifacts.push({name: 'settings', screenshotPath: await screenshot(page, outDir, 'settings'), snapshot: settingsSnapshot});
    const classification = classifySnapshot(settingsSnapshot, expectedUrls);
    const connectors = connectorEvidence(settingsSnapshot, expectedUrls);
    events.push({phase: 'settings_classification', classification, connectors});

    if (classification.status === 'blocked_chatgpt_auth') {
      result = {ok: false, status: 'blocked_chatgpt_auth', reason: classification.reason, nextAction: 'Complete ChatGPT sign-in/verification in the persistent Playwright profile, then rerun.'};
    } else if (ensureHomeCenter) {
      const ensured = await ensureHomeCenterConnected(page, {homeMcpUrl, outDir, artifacts, events});
      events.push({phase: 'ensure_home_center_result', ensured});
      if (!ensured.ok) {
        result = {...ensured, nextAction: ensured.status === 'blocked_chatgpt_auth' ? 'Complete ChatGPT or OAuth verification in the human-visible browser lane, then rerun.' : 'Inspect generated connector screenshots and update ChatGPT connector selector ladder.'};
      } else if (!verifyPrompt) {
        result = {ok: true, status: 'connectors_visible_connected', reason: ensured.state?.reason || 'Home Center connector is connected or present.', ensured, nextAction: 'Rerun with --verify-prompt for no-op tool-call readback.'};
      }
      if (result && !verifyPrompt) {
        // Final evidence is written below.
      }
    } else if (!verifyPrompt) {
      result = {
        ok: classification.status === 'connectors_visible_connected',
        status: classification.status,
        reason: classification.reason,
        nextAction: classification.status === 'connectors_visible_connected' ? 'Rerun with --verify-prompt for no-op tool-call readback.' : 'Reconnect Home Center and Command Center in ChatGPT web, then rerun.',
      };
    }

    if (!result && verifyPrompt) {
      await page.goto(CHAT_URL, {waitUntil: 'domcontentloaded', timeout: Number(arg('timeout-ms', '45000'))});
      await page.waitForTimeout(5000);
      artifacts.push({name: 'chat_before_prompt', screenshotPath: await screenshot(page, outDir, 'chat_before_prompt'), snapshot: await snapshotPage(page)});
      const agentSpec = agentActivationSpec(id);
      const bucketSpec = bucketProofSpec(id);
      const prompt = safeText(arg('prompt', ''), 4000) || (promptMode === 'agent-activation'
        ? agentActivationPrompt(agentSpec)
        : bucketProofPrompt(bucketSpec));
      const filled = await fillComposer(page, prompt);
      events.push({phase: 'fill_prompt', filled});
      if (!filled.ok) {
        result = {ok: false, status: 'blocked_chatgpt_ui', reason: filled.reason, nextAction: 'Open generated screenshot and update composer selectors.'};
      } else {
        artifacts.push({name: 'prompt_filled', screenshotPath: await screenshot(page, outDir, 'prompt_filled'), snapshot: await snapshotPage(page)});
        const sent = await clickSend(page);
        events.push({phase: 'send_prompt', sent});
        if (!sent.ok) {
          result = {ok: false, status: 'blocked_chatgpt_ui', reason: sent.reason, nextAction: 'Open generated screenshot and update send-button selectors.'};
        } else {
          const tokenInfo = await readPairingToken(tokenConfig);
          const proof = promptMode === 'agent-activation'
            ? await waitForAgentActivationResult(page, promptTimeoutMs, {mcpUrl: commandCenterMcpUrl, token: tokenInfo?.token || '', activationId: agentSpec.activationId})
            : await waitForBucketProof({page, timeoutMs: promptTimeoutMs, readbackConfig: {mcpUrl: homeMcpUrl, token: tokenInfo?.token || '', objectId: bucketSpec.objectId}});
          artifacts.push({name: 'after_prompt', screenshotPath: await screenshot(page, outDir, 'after_prompt'), snapshot: await snapshotPage(page)});
          result = proof.ok
            ? {ok: true, status: 'ok', reason: promptMode === 'agent-activation' ? 'ChatGPT web created a Command Center agent activation and backend readback succeeded.' : 'ChatGPT web created a Home Center bucket object and backend readback succeeded.', proof, promptMode, agentSpec, bucketSpec}
            : {ok: false, status: proof.status || 'blocked_chatgpt_ui', reason: proof.reason, proof, promptMode, agentSpec, bucketSpec, tokenReadback: tokenInfo ? {configPath: tokenInfo.configPath, refreshed: tokenInfo.refreshed, hasToken: !!tokenInfo.token, reason: tokenInfo.reason || ''} : null, nextAction: 'Inspect Playwright evidence and MCP logs for connector/tool-call failure.'};
        }
      }
    }

    const evidence = {
      ...result,
      runId: id,
      generatedAt: new Date().toISOString(),
      startUrl,
      expectedConnectors: {homeMcpUrl, commandCenterMcpUrl},
      surface: {runtime: 'playwright', browser: 'chromium', mode: 'desktop', persistentProfile: userDataDir, executablePath: executablePath || 'playwright-managed', viewport: DEFAULT_VIEWPORT, headless},
      liveAndroidChrome: !!cdpUrl,
      cdpUrl: cdpUrl || '',
      promptMode,
      cleanSlateScope: 'connector_state_only_no_cloud_bucket_deletion',
      events,
      artifacts: artifacts.map((artifact) => ({name: artifact.name, screenshotPath: artifact.screenshotPath, url: artifact.snapshot.url, title: artifact.snapshot.title, visibleTextSummary: artifact.snapshot.visibleTextSummary, landmarks: artifact.snapshot.landmarks})),
    };
    const evidencePath = path.join(outDir, 'clean_slate_result.json');
    await fs.writeFile(evidencePath, JSON.stringify(evidence, null, 2) + '\n');
    console.log(JSON.stringify({ok: evidence.ok, status: evidence.status, reason: evidence.reason, evidencePath, screenshotDir: outDir}));
    process.exit(evidence.ok ? 0 : 2);
  } finally {
    if (cdpUrl) {
      // Keep the user-owned Android Chrome session alive; process exit drops the CDP client.
    } else if (context) {
      await context.close();
    }
  }
}

main().catch((err) => {
  console.error(JSON.stringify({ok: false, status: 'blocked_local_setup', reason: err.message || String(err)}));
  process.exit(1);
});
