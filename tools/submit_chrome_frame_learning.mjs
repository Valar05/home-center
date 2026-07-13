#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';

const DEFAULT_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';

function parseArgs(argv) {
  const args = {
    envelope: '',
    mcpUrl: process.env.HOME_CENTER_MCP_URL || DEFAULT_MCP_URL,
    bearerToken: process.env.HOME_CENTER_MCP_BEARER_TOKEN || '',
    tokenConfig: process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json'),
    evidenceDir: 'tools/chatgpt_connector_evidence',
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    dryRun: false,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--envelope') args.envelope = argv[++i];
    else if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--token-config') args.tokenConfig = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--dry-run') args.dryRun = true;
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/submit_chrome_frame_learning.mjs --envelope PATH [--dry-run] [--mcp-url URL] [--bearer-token TOKEN] [--json]');
      process.exit(0);
    }
  }
  return args;
}

function readJson(file, label = file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (err) {
    throw new Error(`${label} is not readable JSON: ${err.message}`);
  }
}

function loadToken(args) {
  if (args.bearerToken) return args.bearerToken;
  if (!fs.existsSync(args.tokenConfig)) return '';
  const config = readJson(args.tokenConfig, args.tokenConfig);
  return config.accessToken || config.bearerToken || config.token || '';
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  const payload = dataLines.length ? dataLines.join('\n') : text;
  try {
    return JSON.parse(payload);
  } catch (err) {
    throw new Error(`${label} did not return JSON: ${String(payload).slice(0, 600)}`);
  }
}

function contentJson(toolResult, label) {
  const text = toolResult?.result?.content?.find((item) => item.type === 'text')?.text || '';
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`${label} content was not JSON: ${String(text).slice(0, 600)}`);
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
  const text = await response.text();
  return {status: response.status, text, headers: Object.fromEntries(response.headers.entries())};
}

async function callCommandCenterOperation(mcpUrl, token, id, operation, opArgs) {
  const response = await postMcp(mcpUrl, token, {
    jsonrpc: '2.0',
    id,
    method: 'tools/call',
    params: {name: 'command_center_operation', arguments: {operation, args: opArgs}},
  });
  const json = parseMcpResponse(response.text, `command_center_operation ${operation}`);
  return {status: response.status, result: contentJson(json, `command_center_operation ${operation}`)};
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.envelope) throw new Error('--envelope is required.');
  const envelopePath = path.resolve(args.envelope);
  const envelope = readJson(envelopePath, envelopePath);
  if (!Array.isArray(envelope.operations) || envelope.operations.length === 0) throw new Error('Envelope has no operations.');
  const checks = [];
  const submitted = [];
  if (args.dryRun) {
    for (const op of envelope.operations) submitted.push({operation: op.operation, dryRun: true});
  } else {
    const token = loadToken(args);
    if (!token) throw new Error(`No Home Center MCP token found. Pair with node tools/home_center_codex_pair.mjs or set HOME_CENTER_MCP_BEARER_TOKEN.`);
    let id = 100;
    for (const op of envelope.operations) {
      if (op.tool !== 'command_center_operation') throw new Error(`Unsupported envelope tool ${op.tool}`);
      const result = await callCommandCenterOperation(args.mcpUrl, token, id++, op.operation, op.args || {});
      checks.push({operation: op.operation, ok: result.status === 200, status: result.status});
      submitted.push({operation: op.operation, status: result.status, result: result.result});
    }
  }
  const report = {
    ok: args.dryRun ? true : checks.every((check) => check.ok),
    dryRun: args.dryRun,
    envelopePath,
    mcpUrl: args.mcpUrl,
    submitted,
    generatedAt: new Date().toISOString(),
  };
  const outDir = path.resolve(args.evidenceDir);
  fs.mkdirSync(outDir, {recursive: true});
  const outPath = path.join(outDir, `chrome_frame_learning_submit_${args.runId}.json`);
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ok: report.ok, dryRun: report.dryRun, outPath, operations: submitted.map((item) => item.operation)}, null, args.json ? 0 : 2));
  if (!report.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
