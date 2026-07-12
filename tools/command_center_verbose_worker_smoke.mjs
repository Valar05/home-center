#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn, spawnSync} from 'node:child_process';

const DEFAULT_COMMAND_CENTER_MCP = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const DEFAULT_COMMAND_CENTER_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp';
const DEFAULT_EVIDENCE_DIR = 'tools/command_center_invokability_evidence';

function parseArgs(argv) {
  const args = {
    mcpUrl: DEFAULT_COMMAND_CENTER_MCP,
    commandCenterBase: DEFAULT_COMMAND_CENTER_BASE,
    evidenceDir: DEFAULT_EVIDENCE_DIR,
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    token: process.env.HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN || process.env.HOME_CENTER_MCP_BEARER_TOKEN || '',
    requireCodexCloud: false,
    executorCommand: '',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--command-center-base') args.commandCenterBase = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--token') args.token = argv[++i];
    else if (arg === '--require-codex-cloud') args.requireCodexCloud = true;
    else if (arg === '--executor-command') args.executorCommand = argv[++i];
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_verbose_worker_smoke.mjs [--run-id ID] [--token TOKEN] [--evidence-dir DIR] [--require-codex-cloud] [--executor-command CMD]');
      process.exit(0);
    }
  }
  return args;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readTokenFromCodexHub() {
  const configPath = path.join(os.homedir(), '.config', 'home-center', 'codex-hub.json');
  if (!fs.existsSync(configPath)) return '';
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  return config.accessToken || config.bearerToken || '';
}

function redact(value) {
  return String(value ?? '')
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]')
    .replace(/\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/g, '[REDACTED_WORKER_TOKEN]')
    .replace(/\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_JWT]');
}

async function fetchText(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  return {response, text};
}

function parseMcp(text) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  return JSON.parse(dataLines.length ? dataLines.join('\n') : text);
}

function contentJson(payload) {
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '{}';
  return JSON.parse(text);
}

async function callMcpTool(mcpUrl, token, name, args = {}) {
  const {response, text} = await fetchText(mcpUrl, {
    method: 'POST',
    headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json', accept: 'application/json, text/event-stream'},
    body: JSON.stringify({jsonrpc: '2.0', id: Date.now(), method: 'tools/call', params: {name, arguments: args}}),
  });
  const payload = parseMcp(text);
  if (!response.ok || payload.error) throw new Error(`${name} failed: ${redact(text.slice(0, 1200))}`);
  return contentJson(payload);
}

function run(command, cwd, env = {}) {
  const result = spawnSync(command, {cwd, shell: true, encoding: 'utf8', env: {...process.env, ...env}});
  if (result.status !== 0) throw new Error(`Command failed: ${command}\n${redact(result.stderr || result.stdout || '')}`);
  return result.stdout || '';
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const token = args.token || readTokenFromCodexHub();
  if (!token) throw new Error('No Home Center/Command Center bearer token available. Pair Home Center or set HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN.');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), `cc-verbose-worker-${args.runId}-`));
  const base = path.join(root, 'base');
  const configPath = path.join(root, 'worker-config.json');
  const manifestPath = path.join(root, 'manifest.json');
  const runOut = path.join(root, 'run');
  fs.mkdirSync(base, {recursive: true});
  run('git init >/dev/null && git config user.email smoke@example.invalid && git config user.name Smoke && printf base > README.md && git add README.md && git commit -m base >/dev/null', base);

  const uniqueCapability = `verbose-worker-smoke-${args.runId}`;
  const workerId = `verbose-worker-${args.runId}`;
  const nonce = `CLOUD_CODEX_NONCE_${args.runId.replace(/[^A-Za-z0-9_]/g, '_')}`;
  const capabilities = ['codex', 'one-shot-worker', 'prepared-workspace', uniqueCapability];
  if (args.requireCodexCloud) capabilities.push('codex-cloud');
  const manifest = {
    projectId: 'home-center',
    workerId,
    repoPath: base,
    orientationFiles: ['README.md'],
    toolChecks: [{name: 'node', command: 'node --version'}],
    capabilities,
    baseWorkspaceId: `verbose-base-${args.runId}`,
  };
  writeJson(manifestPath, manifest);

  const executorScript = [
    "console.log('verbose smoke stdout start')",
    "setTimeout(()=>console.error('verbose smoke stderr after one second'), 1000)",
    "setTimeout(()=>console.log('verbose smoke stdout after quiet period'), 30000)",
    "setTimeout(()=>process.exit(0), 32000)",
  ].join('; ');
  const cloudPrompt = [
    `Print exactly this nonce in your final answer: ${nonce}`,
    'This is a read-only Command Center live acceptance smoke.',
    'Do not edit files, do not call external mutation tools, and do not register workers.',
  ].join('\n');
  const codexCommand = `echo ${JSON.stringify(`codex cloud smoke stderr ${nonce}`)} >&2; codex exec --json --sandbox read-only --skip-git-repo-check -C ${JSON.stringify(base)} ${JSON.stringify(cloudPrompt)}`;
  const executorCommand = args.executorCommand || (args.requireCodexCloud
    ? `sh -c ${JSON.stringify(codexCommand)}`
    : `node -e ${JSON.stringify(executorScript)}`);

  run(`node tools/command_center_oneshot_worker.mjs register --manifest ${JSON.stringify(manifestPath)} --config ${JSON.stringify(configPath)} --worker-id ${JSON.stringify(workerId)} --executor-command ${JSON.stringify(executorCommand)}`, process.cwd(), {HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN: token});

  const created = await callMcpTool(args.mcpUrl, token, 'command_center.jobs.create', {
    idempotencyKey: `verbose-worker-smoke-${args.runId}`,
    projectId: 'home-center',
    title: 'Verbose worker streaming smoke',
    objective: 'Prove Command Center worker executor output streams to cloud events before child exit.',
    acceptanceCriteria: [
      ...(args.requireCodexCloud ? [`real Codex executor stdout includes ${nonce}`] : []),
      'executor_started is visible through jobs.get_events',
      'stdout appears before executor_finished',
      'stderr appears before executor_finished',
      'heartbeat appears before executor_finished',
      'artifacts upload after completion',
    ],
    workerRequirements: args.requireCodexCloud ? ['codex-cloud', uniqueCapability] : [uniqueCapability],
    mutationPolicy: {editFiles: 'deny', runTests: 'deny', commit: 'deny', push: 'deny', merge: 'deny', externalProviderWrite: 'deny', destructive: 'deny'},
  });
  const jobId = created.job.jobId;

  const child = spawn('node', ['tools/command_center_oneshot_worker.mjs', 'run-once', '--config', configPath, '--output-dir', runOut], {
    cwd: process.cwd(),
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {...process.env, ...(args.requireCodexCloud ? {COMMAND_CENTER_EXECUTOR_HEARTBEAT_MS: '2000'} : {})},
  });
  let childStdout = '';
  let childStderr = '';
  child.stdout.on('data', (chunk) => { childStdout += redact(chunk.toString('utf8')); });
  child.stderr.on('data', (chunk) => { childStderr += redact(chunk.toString('utf8')); });

  const snapshots = [];
  let sawStreamingBeforeExit = false;
  let childExited = false;
  let childExit = null;
  child.on('close', (code, signal) => {
    childExited = true;
    childExit = {code, signal};
  });

  const deadline = Date.now() + 70000;
  while (Date.now() < deadline) {
    const events = (await callMcpTool(args.mcpUrl, token, 'command_center.jobs.get_events', {jobId, limit: 100})).events || [];
    const types = events.map((event) => event.type);
    const hasStreaming = types.includes('executor_started') && types.includes('executor_stdout') && types.includes('executor_stderr') && types.includes('executor_heartbeat') && !types.includes('executor_finished');
    snapshots.push({atMs: Date.now(), childExited, eventCount: events.length, types});
    if (hasStreaming) sawStreamingBeforeExit = true;
    if (childExited && types.includes('executor_finished')) break;
    await sleep(3000);
  }

  if (!childExited) {
    child.kill('SIGTERM');
    await sleep(1500);
  }

  const finalEvents = (await callMcpTool(args.mcpUrl, token, 'command_center.jobs.get_events', {jobId, limit: 100})).events || [];
  const artifacts = (await callMcpTool(args.mcpUrl, token, 'command_center.jobs.get_artifacts', {jobId, limit: 100})).artifacts || [];
  const summary = await callMcpTool(args.mcpUrl, token, 'command_center.jobs.get_summary', {jobId});
  const finalTypes = finalEvents.map((event) => event.type);
  const finished = finalEvents.find((event) => event.type === 'executor_finished');
  const finishedAt = Number(finished?.createdAtMs || Number.MAX_SAFE_INTEGER);
  const beforeFinish = (type) => finalEvents.some((event) => event.type === type && Number(event.createdAtMs || 0) < finishedAt);
  const requiredBeforeFinish = ['executor_started', 'executor_stdout', 'executor_stderr', 'executor_heartbeat'];
  const missingBeforeFinish = requiredBeforeFinish.filter((type) => !beforeFinish(type));
  const stdoutText = finalEvents.filter((event) => event.type === 'executor_stdout').map((event) => JSON.stringify(event.data || {})).join('\n');
  const nonceSeen = !args.requireCodexCloud || stdoutText.includes(nonce);
  const artifactNames = artifacts.map((artifact) => artifact.name).sort();
  const requiredArtifacts = ['command-log.jsonl', 'stdout-transcript.txt', 'stderr-transcript.txt', 'event-transcript.jsonl', 'executor-status.json', 'artifact-upload-summary.json'];
  const missingArtifacts = requiredArtifacts.filter((name) => !artifactNames.includes(name));
  const evidence = {
    ok: sawStreamingBeforeExit && childExit?.code === 0 && summary.status === 'completed' && missingBeforeFinish.length === 0 && missingArtifacts.length === 0 && nonceSeen,
    generatedAt: new Date().toISOString(),
    runId: args.runId,
    jobId,
    workerId,
    uniqueCapability,
    requireCodexCloud: args.requireCodexCloud,
    nonce,
    childExit,
    serviceReadback: {
      status: summary.status,
      eventCount: finalEvents.length,
      artifactCount: artifacts.length,
      finalTypes,
      missingBeforeFinish,
      missingArtifacts,
      nonceSeen,
      sawStreamingBeforeExit,
    },
    pollingSnapshots: snapshots,
    localRun: {
      outputDir: runOut,
      childStdout: childStdout.slice(0, 2000),
      childStderr: childStderr.slice(0, 2000),
    },
  };
  const evidenceText = JSON.stringify(evidence, null, 2);
  if (/(ccw_|Bearer\s+[A-Za-z0-9._~+/=-]{12,}|ya29\.|gh[pousr]_)/.test(evidenceText)) throw new Error('Evidence contains token-like secret material.');
  const evidencePath = path.join(args.evidenceDir, `command_center_verbose_worker_${args.runId}.json`);
  writeJson(evidencePath, evidence);
  console.log(JSON.stringify({ok: evidence.ok, evidencePath, jobId, failed: evidence.ok ? [] : {missingBeforeFinish, missingArtifacts, childExit, summaryStatus: summary.status}}, null, 2));
  if (!evidence.ok) process.exit(1);
}

main().catch((err) => {
  console.error(redact(err.stack || err.message || String(err)));
  process.exit(1);
});
