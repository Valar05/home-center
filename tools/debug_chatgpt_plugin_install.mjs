#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {homedir} from 'node:os';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const DEFAULT_HOME_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const DEFAULT_COMMAND_CENTER_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const DEFAULT_CHATGPT_URL = 'https://chatgpt.com/';
const EVIDENCE_DIR = path.join(ROOT, 'tools', 'chatgpt_connector_evidence');

function parseArgs(argv) {
  const args = {
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    homeMcpUrl: DEFAULT_HOME_MCP_URL,
    commandCenterMcpUrl: DEFAULT_COMMAND_CENTER_MCP_URL,
    chatgptUrl: DEFAULT_CHATGPT_URL,
    skipPlaywright: false,
    skipBackend: false,
    sinceMinutes: 30,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--home-mcp-url') args.homeMcpUrl = argv[++i];
    else if (arg === '--command-center-mcp-url') args.commandCenterMcpUrl = argv[++i];
    else if (arg === '--chatgpt-url') args.chatgptUrl = argv[++i];
    else if (arg === '--skip-playwright') args.skipPlaywright = true;
    else if (arg === '--skip-backend') args.skipBackend = true;
    else if (arg === '--since-minutes') args.sinceMinutes = Number(argv[++i]);
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/debug_chatgpt_plugin_install.mjs [--chatgpt-url URL] [--skip-playwright] [--skip-backend] [--since-minutes N] [--run-id ID] [--json]');
      process.exit(0);
    }
  }
  return args;
}

function commandExists(command) {
  const proc = spawnSync('sh', ['-lc', `command -v ${command}`], {encoding: 'utf8', timeout: 5000});
  return {ok: proc.status === 0, path: (proc.stdout || '').trim(), error: (proc.stderr || '').trim()};
}

function run(command, args, options = {}) {
  const proc = spawnSync(command, args, {
    cwd: ROOT,
    env: {...process.env, ...(options.env || {})},
    encoding: 'utf8',
    timeout: options.timeout || 90000,
  });
  return {
    command: [command, ...args].join(' '),
    status: proc.status,
    ok: proc.status === 0,
    stdout: proc.stdout || '',
    stderr: proc.stderr || '',
    error: proc.error ? String(proc.error.message || proc.error) : '',
  };
}

function parseJson(text, fallback = {}) {
  try { return JSON.parse(String(text || '').trim()); } catch (_) { return fallback; }
}

function latestJsonLine(text) {
  const lines = String(text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    if (lines[i].startsWith('{') && lines[i].endsWith('}')) return parseJson(lines[i], {});
  }
  return {};
}

function safeConfigSummary(configPath) {
  if (!fs.existsSync(configPath)) return {exists: false, configPath, expired: true, nextAction: 'Run node tools/home_center_codex_pair.mjs and approve pairing in Home Center.'};
  const raw = parseJson(fs.readFileSync(configPath, 'utf8'), {});
  const expiresAtMs = Number(raw.expiresAtMs || 0);
  return {
    exists: true,
    configPath,
    email: raw.email || '',
    mcpUrl: raw.mcpUrl || '',
    allowedGroups: Array.isArray(raw.allowedGroups) ? raw.allowedGroups : [],
    toolsCount: Array.isArray(raw.tools) ? raw.tools.length : 0,
    expiresAtMs,
    expired: expiresAtMs > 0 ? expiresAtMs <= Date.now() + 60000 : false,
    hasAccessToken: !!raw.accessToken,
    hasRefreshToken: !!raw.refreshToken,
  };
}

function readAccessToken(configPath) {
  if (!fs.existsSync(configPath)) return '';
  const raw = parseJson(fs.readFileSync(configPath, 'utf8'), {});
  return raw.accessToken || '';
}

async function refreshPairing(configPath) {
  if (!fs.existsSync(configPath)) return {attempted: false, ok: false, reason: 'pairing config missing'};
  const raw = parseJson(fs.readFileSync(configPath, 'utf8'), {});
  if (!raw.refreshToken) return {attempted: false, ok: false, reason: 'refresh token missing'};
  const gatewayBase = raw.gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net';
  try {
    const response = await fetch(`${gatewayBase}/termuxTokenRefresh`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({refreshToken: raw.refreshToken}),
    });
    const text = await response.text();
    const json = parseJson(text, {});
    if (!response.ok || !json.ok || !json.access_token) {
      return {attempted: true, ok: false, status: response.status, reason: text.slice(0, 500)};
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
    return {attempted: true, ok: true, status: response.status, expiresAtMs: next.expiresAtMs, allowedGroups: next.allowedGroups};
  } catch (err) {
    return {attempted: true, ok: false, reason: err.message || String(err)};
  }
}

function serviceNameFromMcpUrl(mcpUrl) {
  return new URL(mcpUrl).pathname.split('/').filter(Boolean)[0].toLowerCase();
}

function cloudLogs(serviceName, sinceMinutes) {
  if (!commandExists('gcloud').ok) return {ok: false, unavailable: true, reason: 'gcloud is not installed or not on PATH.', count: 0, state: {}};
  const sinceIso = new Date(Date.now() - Math.max(1, sinceMinutes) * 60 * 1000).toISOString();
  const filter = `resource.type="cloud_run_revision" AND resource.labels.service_name="${serviceName}" AND timestamp>="${sinceIso}" AND ("mcp_connector_" OR jsonPayload.message:"mcp_connector_" OR jsonPayload.event:"mcp_connector_")`;
  const proc = run('gcloud', ['logging', 'read', filter, '--project=home-center-dclar', '--limit=120', '--format=json'], {timeout: 45000});
  const entries = proc.ok ? parseJson(proc.stdout, []) : [];
  const events = entries.map((entry) => String(entry?.jsonPayload?.event || entry?.jsonPayload?.message || entry?.textPayload || ''));
  const methods = entries.map((entry) => String(entry?.jsonPayload?.mcpMethod || ''));
  const state = {
    tokenSuccess: events.includes('mcp_connector_token_success') || events.includes('mcp_connector_token_refresh_success'),
    userinfoSuccess: events.includes('mcp_connector_userinfo_success'),
    mcpActive: events.includes('mcp_connector_mcp_success') || methods.includes('initialize') || methods.includes('tools/call'),
    errors: entries.filter((entry) => /_error|error/i.test(String(entry?.jsonPayload?.event || entry?.jsonPayload?.message || entry?.textPayload || ''))).slice(0, 8).map((entry) => ({
      event: entry?.jsonPayload?.event || '',
      message: entry?.jsonPayload?.message || entry?.textPayload || '',
      error: entry?.jsonPayload?.error || '',
    })),
  };
  return {ok: proc.ok, count: entries.length, filter, state, error: proc.ok ? '' : proc.stderr || proc.error};
}

function classify(report) {
  if (!report.local.node.ok || !report.local.prootDistro.ok) {
    return {status: 'blocked_local_setup', nextAction: 'Install/repair Termux Node and proot-distro before running the debugger.'};
  }
  if (!report.pairing.exists || report.pairing.expired || !report.pairing.hasAccessToken) {
    return {status: 'blocked_user_action', nextAction: 'Run node tools/home_center_codex_pair.mjs and approve pairing in the Home Center app.'};
  }
  if (report.backend.homeBridge && report.backend.homeBridge.ok === false) {
    return {status: 'blocked_backend', nextAction: 'Inspect the Home Center MCP evidence path and redeploy only if the backend tool surface is stale.'};
  }
  if (report.playwright && report.playwright.status) {
    if (report.playwright.status === 'ok') return {status: 'ok', nextAction: 'ChatGPT Playwright evidence and Home Center backend checks are green.'};
    if (report.playwright.status === 'blocked_chatgpt_auth') return {status: 'blocked_chatgpt_auth', nextAction: 'Sign in or complete verification in the Playwright/Chrome profile, then rerun this debugger.'};
    if (report.playwright.status === 'blocked_chatgpt_ui') return {status: 'blocked_chatgpt_ui', nextAction: 'Open the Playwright evidence artifact and fix the visible ChatGPT connector/install state.'};
  }
  if (report.logs?.state?.tokenSuccess && report.logs?.state?.userinfoSuccess && !report.logs?.state?.mcpActive) {
    return {status: 'blocked_chatgpt_ui', nextAction: 'ChatGPT completed OAuth but did not call MCP; reconnect or reindex the ChatGPT app.'};
  }
  return {status: 'unknown', nextAction: 'Open the generated evidence report and inspect backend, logs, and Playwright artifacts.'};
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  fs.mkdirSync(EVIDENCE_DIR, {recursive: true});
  const configPath = process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json');
  let pairing = safeConfigSummary(configPath);
  let pairingRefresh = {attempted: false, ok: false};
  if (pairing.exists && pairing.expired && pairing.hasRefreshToken) {
    pairingRefresh = await refreshPairing(configPath);
    pairing = safeConfigSummary(configPath);
  }
  const token = readAccessToken(configPath);
  const envWithToken = token ? {HOME_CENTER_MCP_BEARER_TOKEN: token, HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN: token} : {};
  const report = {
    runId: args.runId,
    generatedAt: new Date().toISOString(),
    target: {homeMcpUrl: args.homeMcpUrl, commandCenterMcpUrl: args.commandCenterMcpUrl, chatgptUrl: args.chatgptUrl},
    local: {
      node: commandExists('node'),
      prootDistro: commandExists('proot-distro'),
      gcloud: commandExists('gcloud'),
      termuxOpenUrl: commandExists('termux-open-url'),
      shizukuRish: {ok: fs.existsSync(path.join(homedir(), 'bin/rish')) || fs.existsSync('/sdcard/rish') || fs.existsSync('/storage/emulated/0/rish')},
    },
    pairing,
    pairingRefresh,
    backend: {},
    playwright: null,
    logs: null,
  };

  if (!args.skipBackend) {
    const home = run('node', ['tools/command_center_home_bridge_invokability_gate.mjs', '--json', '--run-id', `${args.runId}-home`], {env: envWithToken});
    report.backend.homeBridge = {...latestJsonLine(home.stdout), exitCode: home.status, ok: home.ok, stderr: home.stderr.slice(0, 2000)};
  }

  if (!args.skipPlaywright) {
    const pw = run('sh', ['tools/run_chatgpt_plugin_playwright_check.sh', '--run-id', args.runId, '--url', args.chatgptUrl], {timeout: 120000});
    report.playwright = {...latestJsonLine(pw.stdout), exitCode: pw.status, ok: pw.ok, stderr: pw.stderr.slice(0, 2000)};
  }

  report.logs = cloudLogs(serviceNameFromMcpUrl(args.homeMcpUrl), args.sinceMinutes);
  const decision = classify(report);
  report.status = decision.status;
  report.nextAction = decision.nextAction;
  report.ok = decision.status === 'ok';
  const evidencePath = path.join(EVIDENCE_DIR, `plugin_install_debug_${args.runId}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(report, null, 2) + '\n');
  const summary = {ok: report.ok, status: report.status, nextAction: report.nextAction, evidencePath, playwright: report.playwright, backend: report.backend, logs: {ok: report.logs?.ok, count: report.logs?.count, state: report.logs?.state}};
  console.log(JSON.stringify(summary, null, args.json ? 0 : 2));
  process.exit(report.ok ? 0 : 2);
}

main().catch((err) => {
  console.error(JSON.stringify({ok: false, status: 'blocked_local_setup', nextAction: err.message || String(err)}));
  process.exit(1);
});
