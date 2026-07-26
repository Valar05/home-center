#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn, spawnSync} from 'node:child_process';

const DEFAULT_COMMAND_CENTER_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp';
const DEFAULT_CONFIG_PATH = path.join(os.homedir(), '.config', 'home-center', 'command-center-worker.json');
const REQUIRED_ARTIFACTS = [
  'job-intake.json',
  'orientation.md',
  'reasoning-summary.md',
  'command-log.jsonl',
  'acceptance.json',
  'implementation.patch',
  'changed-files.json',
  'verification.json',
  'final-report.md',
  'mutation-requests.jsonl',
];
const OPTIONAL_POSTMORTEM_ARTIFACTS = [
  'stdout-transcript.txt',
  'stderr-transcript.txt',
  'event-transcript.jsonl',
  'executor-status.json',
  'artifact-upload-summary.json',
  'acceptance-matrix.json',
  'handoff-packet.json',
];
const DEFAULT_EXECUTOR_HEARTBEAT_MS = 25000;
const DEFAULT_EXECUTOR_BATCH_MS = 5000;
const DEFAULT_EXECUTOR_BATCH_LINES = 20;
const DEFAULT_SUPERVISOR_POLL_MS = 15000;
const WORKER_PROTOCOL_VERSION = 'command-center-worker-v2';
const RUNNER_VERSION = 'command-center-runner-v2';
const CODEX_ENV_DENYLIST = new Set(['OPENAI_API_KEY', 'CODEX_API_KEY']);

function parseArgs(argv) {
  const args = {mode: '', outputDir: '', baseWorkspace: '', jobPacket: '', command: '', executorCommand: '', manifest: '', config: DEFAULT_CONFIG_PATH, mcpUrl: DEFAULT_COMMAND_CENTER_BASE + '/mcp', commandCenterBase: DEFAULT_COMMAND_CENTER_BASE, workerId: '', mcpToken: process.env.HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN || '', selfTest: false, deep: false, pollMs: DEFAULT_SUPERVISOR_POLL_MS, maxIdlePolls: 0};
  const rest = [...argv];
  if (rest[0] && !rest[0].startsWith('--')) args.mode = rest.shift();
  for (let i = 0; i < rest.length; i += 1) {
    const arg = rest[i];
    if (arg === '--output-dir') args.outputDir = rest[++i];
    else if (arg === '--base-workspace') args.baseWorkspace = rest[++i];
    else if (arg === '--job-packet') args.jobPacket = rest[++i];
    else if (arg === '--command') args.command = rest[++i];
    else if (arg === '--executor-command') args.executorCommand = rest[++i];
    else if (arg === '--manifest') args.manifest = rest[++i];
    else if (arg === '--config') args.config = rest[++i];
    else if (arg === '--mcp-url') args.mcpUrl = rest[++i];
    else if (arg === '--command-center-base') args.commandCenterBase = rest[++i];
    else if (arg === '--worker-id') args.workerId = rest[++i];
    else if (arg === '--mcp-token') args.mcpToken = rest[++i];
    else if (arg === '--poll-ms') args.pollMs = Number(rest[++i]) || DEFAULT_SUPERVISOR_POLL_MS;
    else if (arg === '--max-idle-polls') args.maxIdlePolls = Number(rest[++i]) || 0;
    else if (arg === '--deep') args.deep = true;
    else if (arg === '--self-test') args.selfTest = true;
    else if (arg === '--help') {
      printHelp();
      process.exit(0);
    }
  }
  if (!args.mode) args.mode = args.selfTest ? 'self-test' : 'run-local';
  if (args.mode === 'run-local' && args.selfTest) args.mode = 'self-test';
  return args;
}

function printHelp() {
  console.log([
    'Usage:',
    '  node tools/command_center_oneshot_worker.mjs register --manifest FILE --mcp-token TOKEN [--config FILE]',
    '  node tools/command_center_oneshot_worker.mjs prepare-base --manifest FILE [--output-dir DIR] [--deep]',
    '  node tools/command_center_oneshot_worker.mjs run-once --config FILE [--executor-command CMD] [--output-dir DIR]',
    '  node tools/command_center_oneshot_worker.mjs heartbeat --config FILE',
    '  node tools/command_center_oneshot_worker.mjs supervise --config FILE [--poll-ms MS]',
    '  node tools/command_center_oneshot_worker.mjs run-local --base-workspace PATH --job-packet FILE --output-dir DIR [--command CMD]',
    '  node tools/command_center_oneshot_worker.mjs --self-test',
  ].join('\n'));
}

function readJson(file, fallback = {}) {
  if (!file || !fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function readText(file, fallback = '') {
  if (!file || !fs.existsSync(file)) return fallback;
  return fs.readFileSync(file, 'utf8');
}

function writeFile(file, data) {
  const text = String(data || '');
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, text.endsWith('\n') ? text : text + '\n');
}

function writeJson(file, data) {
  writeFile(file, JSON.stringify(data, null, 2));
}

function appendFile(file, data) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.appendFileSync(file, String(data || ''));
}

function redactSecrets(value) {
  let text = String(value ?? '');
  text = text.replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]');
  text = text.replace(/\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/g, '[REDACTED_WORKER_TOKEN]');
  text = text.replace(/\bgh[pousr]_[A-Za-z0-9_]{20,}\b/g, '[REDACTED_GITHUB_TOKEN]');
  text = text.replace(/\bya29\.[A-Za-z0-9._-]{20,}\b/g, '[REDACTED_GOOGLE_TOKEN]');
  text = text.replace(/\bAIza[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_GOOGLE_API_KEY]');
  text = text.replace(/\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_JWT]');
  text = text.replace(/((?:TOKEN|SECRET|KEY|AUTH|PASSWORD|CREDENTIAL)[A-Z0-9_ -]*\s*[=:]\s*)[^\s"'`]+/gi, '$1[REDACTED]');
  text = text.replace(/((?:token|secret|key|auth|password|credential)[A-Za-z0-9_ -]*["']?\s*:\s*["'])[^\n"']+(["'])/g, '$1[REDACTED]$2');
  return text;
}

function cleanLines(text, maxLineChars = 1200) {
  return String(text || '').split(/\r?\n/).map((line) => redactSecrets(line).slice(0, maxLineChars));
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}


function safeList(value, maxItems = 50) {
  return Array.isArray(value) ? value.slice(0, maxItems).map((item) => String(item || '').trim()).filter(Boolean) : [];
}

function machineImageRuntimePayload(manifest = {}) {
  const sessionCapacity = safeObject(manifest.sessionCapacity);
  const limits = safeObject(manifest.limits);
  const machineImages = Array.isArray(manifest.machineImages) ? manifest.machineImages.slice(0, 40) : [];
  const availableImageIds = safeList(manifest.availableImageIds || sessionCapacity.availableImageIds, 80);
  const materializedImageIds = safeList(manifest.materializedImageIds || sessionCapacity.materializedImageIds, 80);
  for (const image of machineImages) {
    const imageId = String(image.imageId || image.machineImageId || '').trim();
    if (imageId && !availableImageIds.includes(imageId)) availableImageIds.push(imageId);
    if (imageId && image.status !== 'missing' && image.status !== 'retired' && !materializedImageIds.includes(imageId)) materializedImageIds.push(imageId);
  }
  const maxConcurrentSessions = Math.max(1, Math.min(Number(manifest.maxConcurrentSessions || sessionCapacity.maxConcurrentSessions || limits.maxConcurrentSessions || limits.concurrentSessions || 1) || 1, 100));
  const activeSessionIds = safeList(manifest.activeSessionIds || sessionCapacity.activeSessionIds, 100);
  const sessionIsolationModes = safeList(manifest.sessionIsolationModes || sessionCapacity.sessionIsolationModes || ['session'], 10);
  const cacheState = {...safeObject(sessionCapacity.cacheState), ...safeObject(manifest.cacheState)};
  return {
    availableImageIds,
    materializedImageIds,
    machineImages,
    cacheState,
    maxConcurrentSessions,
    activeSessionIds,
    sessionIsolationModes,
    canMaterializeImages: manifest.canMaterializeImages === true || sessionCapacity.canMaterializeImages === true,
    sessionCapacity: {maxConcurrentSessions, activeSessionIds, availableImageIds, materializedImageIds, sessionIsolationModes, cacheState, canMaterializeImages: manifest.canMaterializeImages === true || sessionCapacity.canMaterializeImages === true},
  };
}

function readConfig(configPath) {
  const config = readJson(configPath, null);
  if (!config) throw new Error('Worker config not found: ' + configPath + '. Run register first or provide --config.');
  if (!config.workerToken) throw new Error('Worker config has no workerToken: ' + configPath);
  return config;
}

function writeConfig(configPath, config) {
  fs.mkdirSync(path.dirname(configPath), {recursive: true});
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
  try { fs.chmodSync(configPath, 0o600); } catch (_) {}
}


function durableIdentityPath(configPath) {
  return path.join(path.dirname(configPath), 'command-center-worker-installation.json');
}

function readOrCreateInstallationIdentity(configPath, manifest = {}, workerId = '') {
  const identityPath = durableIdentityPath(configPath);
  const existing = readJson(identityPath, null);
  if (existing && existing.workerInstallationId) return existing;
  const seed = `${os.hostname()}|${os.homedir()}|${manifest.location || 'termux'}|${manifest.stableWorkerIdentity || workerId || 'command-center-worker'}`;
  const identity = {
    workerInstallationId: 'winst_' + crypto.createHash('sha256').update(seed + '|' + crypto.randomUUID()).digest('hex').slice(0, 32),
    createdAt: new Date().toISOString(),
    hostLabel: os.hostname(),
    location: manifest.location || 'termux',
  };
  writeConfig(identityPath, identity);
  return identity;
}

function createWorkerInstanceId(workerId = '') {
  return 'winstproc_' + crypto.createHash('sha256').update(`${workerId}|${process.pid}|${Date.now()}|${crypto.randomUUID()}`).digest('hex').slice(0, 32);
}


function rotateWorkerInstance(configPath) {
  const raw = readConfig(configPath);
  const manifest = readJson(raw.manifestPath, {});
  const config = ensureRuntimeIdentity({...raw, configPath: path.resolve(configPath)}, manifest);
  config.workerInstanceId = createWorkerInstanceId(config.workerId || manifest.workerId || '');
  config.processStartAtMs = Date.now();
  config.heartbeatSeq = 0;
  config.runnerVersion = RUNNER_VERSION;
  config.protocolVersion = WORKER_PROTOCOL_VERSION;
  writeConfig(configPath, config);
  return config;
}

function ensureRuntimeIdentity(config, manifest = {}) {
  const identity = readOrCreateInstallationIdentity(config.configPath || DEFAULT_CONFIG_PATH, manifest, config.workerId || manifest.workerId || '');
  if (!config.workerInstallationId) config.workerInstallationId = identity.workerInstallationId;
  if (!config.workerInstanceId) config.workerInstanceId = createWorkerInstanceId(config.workerId || manifest.workerId || '');
  if (!config.processStartAtMs) config.processStartAtMs = Date.now();
  if (!config.runnerVersion) config.runnerVersion = RUNNER_VERSION;
  if (!config.protocolVersion) config.protocolVersion = WORKER_PROTOCOL_VERSION;
  config.heartbeatSeq = Number(config.heartbeatSeq || 0) || 0;
  return config;
}

function childEnv(extra = {}, options = {}) {
  const merged = {...process.env, ...extra};
  if (options.stripCodexApiKeys === true) {
    for (const key of CODEX_ENV_DENYLIST) delete merged[key];
  }
  return merged;
}

function commandUsesCodex(command = '') {
  return /(^|[\s;&|])codex\s+exec\b|command_center_codex_executor\.sh/.test(String(command || ''));
}

function run(command, cwd, env = {}) {
  const startedAt = new Date().toISOString();
  const result = spawnSync(command, {cwd, shell: true, encoding: 'utf8', maxBuffer: 8 * 1024 * 1024, env: childEnv(env, {stripCodexApiKeys: commandUsesCodex(command)})});
  return {
    command,
    cwd,
    startedAt,
    endedAt: new Date().toISOString(),
    exitCode: typeof result.status === 'number' ? result.status : 1,
    stdout: result.stdout || '',
    stderr: result.stderr || result.error?.message || '',
  };
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function artifactRecord(outputDir, name, kind = 'file', required = true) {
  const file = path.join(outputDir, name);
  return {name, kind, required, uri: file, sha256: fs.existsSync(file) ? sha256(file) : '', metadata: {localPath: file}};
}

function parseJsonLines(text) {
  return String(text || '').split(/\r?\n/).filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch (_) { return {raw: line}; }
  });
}

function summarizeCommandResult(item) {
  return {
    command: redactSecrets(item.command || ''),
    cwd: item.cwd || '',
    exitCode: typeof item.exitCode === 'number' ? item.exitCode : 1,
    startedAt: item.startedAt || '',
    endedAt: item.endedAt || '',
    durationMs: item.durationMs || 0,
    signal: item.signal || '',
    cancelled: item.cancelled === true,
    stdoutPath: item.stdoutPath || '',
    stderrPath: item.stderrPath || '',
    eventTranscriptPath: item.eventTranscriptPath || '',
    stats: item.stats || {},
  };
}

function buildAcceptanceMatrix(job, commandResults, artifacts) {
  const criteria = Array.isArray(job.acceptanceCriteria) ? job.acceptanceCriteria : [];
  return {
    generatedAt: new Date().toISOString(),
    statusPolicy: 'Criteria default to not_evaluated unless a worker emits explicit criterion evidence.',
    overallExecutorStatus: commandResults.every((item) => item.exitCode === 0) ? 'executor_completed' : 'executor_failed',
    criteria: criteria.map((criterion) => ({
      criterion,
      status: 'not_evaluated',
      evidenceRefs: artifacts.map((artifact) => artifact.uri).filter(Boolean).slice(0, 20),
      notes: 'Worker preserved evidence, but did not explicitly mark this criterion as pass/fail.',
      blockingReason: '',
    })),
  };
}

function buildHandoffPacket({outputDir, runWorkspace, jobPacket, manifest, commandResults, artifacts, status, gitStatus, changedFiles, verification}) {
  const job = jobPacket.job || jobPacket;
  const eventTranscript = parseJsonLines(readText(path.join(outputDir, 'event-transcript.jsonl')));
  const mutationRequests = parseJsonLines(readText(path.join(outputDir, 'mutation-requests.jsonl')));
  const executorStatus = readJson(path.join(outputDir, 'executor-status.json'), {});
  const acceptanceMatrix = readJson(path.join(outputDir, 'acceptance-matrix.json'), {});
  const latestEvent = eventTranscript[eventTranscript.length - 1] || null;
  const requiredArtifactNames = new Set(REQUIRED_ARTIFACTS);
  const presentNames = new Set(artifacts.map((artifact) => artifact.name));
  return {
    packetVersion: 'command-center-handoff-v1',
    generatedAt: new Date().toISOString(),
    job: {
      jobId: job.jobId || '',
      projectId: job.projectId || manifest.projectId || '',
      title: job.title || '',
      objective: job.objective || '',
      status,
      workerId: manifest.workerId || '',
      selectedWorkerId: job.selectedWorkerId || '',
      mutationPolicy: job.mutationPolicy || {},
      baseWorkspace: job.baseWorkspace || manifest.baseWorkspace || manifestBaseWorkspace(manifest),
      sourceJobId: job.sourceJobId || '',
      followupOf: job.followupOf || null,
    },
    review: {
      recommendedNextAction: status === 'completed' ? 'Review handoff evidence and authorize only policy-approved consequential mutations.' : 'Create a linked follow-up invocation after reviewing failure evidence.',
      residualRisks: [
        'Acceptance criteria are not automatically passed by executor exit code.',
        'Consequential mutations require separate authorization under the job mutation policy.',
      ],
      correctability: {
        preferredOperation: 'command_center.jobs.create_followup',
        sourceJobId: job.jobId || '',
        carryForwardEvidenceRefs: artifacts.map((artifact) => artifact.uri).filter(Boolean).slice(0, 40),
      },
    },
    execution: {
      runWorkspace,
      gitStatus,
      changedFiles,
      commandResults: commandResults.map(summarizeCommandResult),
      executorStatus,
      verification,
      acceptanceMatrix,
      mutationRequests,
    },
    observability: {
      eventCount: eventTranscript.length,
      latestEvent,
      artifactCount: artifacts.length,
      requiredArtifactsPresent: Array.from(requiredArtifactNames).filter((name) => presentNames.has(name)),
      missingRequiredArtifacts: Array.from(requiredArtifactNames).filter((name) => !presentNames.has(name)),
    },
    artifacts: artifacts.map((artifact) => ({
      name: artifact.name,
      kind: artifact.kind,
      required: artifact.required === true,
      uri: artifact.uri,
      sha256: artifact.sha256,
    })),
    bucket: {
      suggestedCurrentSummaryKind: 'memory.current_condensed',
      suggestedPastLogKind: 'memory.past_log',
      suggestedSkillCandidateKind: 'skill.scratch',
    },
  };
}

function copyBaseWorkspace(baseWorkspace, runWorkspace) {
  if (!baseWorkspace || !fs.existsSync(baseWorkspace)) throw new Error('Base workspace does not exist: ' + baseWorkspace);
  fs.rmSync(runWorkspace, {recursive: true, force: true});
  fs.mkdirSync(path.dirname(runWorkspace), {recursive: true});
  fs.cpSync(baseWorkspace, runWorkspace, {recursive: true, dereference: false, filter: (src) => {
    const rel = src.replace(baseWorkspace, '');
    return !rel.includes(path.sep + '.git' + path.sep + 'objects' + path.sep + 'pack' + path.sep + 'tmp_') && !rel.includes(path.sep + 'node_modules' + path.sep) && !rel.includes(path.sep + '.firebase' + path.sep);
  }});
}

function gitOutput(workspace, command) {
  const result = run(command, workspace);
  return result.exitCode === 0 ? result.stdout.trim() : '';
}

function manifestBaseWorkspace(manifest) {
  return manifest.baseWorkspace || {
    baseWorkspaceId: manifest.baseWorkspaceId || manifest.projectId || 'local-base',
    kind: 'prepared_workspace_snapshot',
    snapshotRef: 'worker-local://' + (manifest.repoPath || manifest.path || ''),
    version: manifest.version || 'local',
    restoreStrategy: 'copy_overlay',
    immutable: true,
    toolchains: (manifest.toolChecks || []).map((tool) => tool.name).filter(Boolean),
  };
}

function buildPromptPacket(jobPacket, manifest, outputDir) {
  const job = jobPacket.job || jobPacket;
  const lines = [
    '# Command Center One-Shot Job Packet',
    '',
    'You are a one-shot Codex worker. Do not depend on chat history. Produce durable artifacts before exiting.',
    '',
    '## Current User Command',
    job.objective || '',
    '',
    '## Forbidden Stale Premise',
    'Do not treat a simulated worker, a tool-list smoke, or a local-only check as completed implementation.',
    '',
    '## Intended Mutation',
    'Implement only the scoped job objective in the restored overlay workspace and preserve evidence.',
    '',
    '## Why This Satisfies The Command',
    'The job packet came from Command Center and includes acceptance criteria, mutation policy, and required artifacts.',
    '',
    '## Acceptance Criteria',
    ...(job.acceptanceCriteria || []).map((item) => '- ' + item),
    '',
    '## Mutation Policy JSON',
    JSON.stringify(job.mutationPolicy || {}, null, 2),
    '',
    '## Project Manifest JSON',
    JSON.stringify(manifest || {}, null, 2),
    '',
    '## Required Artifacts',
    ...REQUIRED_ARTIFACTS.map((name) => '- ' + name),
  ];
  const promptPath = path.join(outputDir, 'codex-prompt.md');
  writeFile(promptPath, lines.join('\n'));
  return promptPath;
}

function writeRequiredArtifacts({outputDir, runWorkspace, jobPacket, commandResults = [], manifest = {}, status = ''}) {
  const job = jobPacket.job || jobPacket;
  const gitStatus = gitOutput(runWorkspace, 'git status --short');
  const gitHead = gitOutput(runWorkspace, 'git rev-parse HEAD');
  const changedFiles = gitStatus.split(/\r?\n/).filter(Boolean).map((line) => ({status: line.slice(0, 2).trim(), path: line.slice(3)}));
  const verification = commandResults.map((item) => ({command: item.command, exitCode: item.exitCode}));
  const ok = status ? status === 'completed' : verification.every((item) => item.exitCode === 0);

  writeJson(path.join(outputDir, 'job-intake.json'), {jobPacket, manifest, runWorkspace, capturedAt: new Date().toISOString()});
  writeFile(path.join(outputDir, 'orientation.md'), ['# Orientation', '', 'Workspace: ' + runWorkspace, 'Git HEAD: ' + (gitHead || 'unknown'), 'Project: ' + (manifest.projectId || job.projectId || 'unknown'), 'Changed files: ' + changedFiles.length].join('\n'));
  writeFile(path.join(outputDir, 'reasoning-summary.md'), ['# Reasoning Summary', '', 'One-shot worker restored the prepared workspace, built a complete prompt packet, executed the configured one-shot command when available, and captured durable evidence for review.', 'Objective: ' + (job.objective || '')].join('\n'));
  writeFile(path.join(outputDir, 'command-log.jsonl'), commandResults.map((item) => JSON.stringify(item)).join('\n'));
  writeFile(path.join(outputDir, 'implementation.patch'), gitOutput(runWorkspace, 'git diff --binary') || '');
  writeJson(path.join(outputDir, 'changed-files.json'), {gitStatus, changedFiles});
  writeJson(path.join(outputDir, 'verification.json'), {ok, verification});
  writeJson(path.join(outputDir, 'acceptance.json'), {ok, status: ok ? 'completed' : 'failed', generatedAt: new Date().toISOString(), note: 'Executor exit status only; acceptance-matrix.json carries per-criterion review status.'});
  writeFile(path.join(outputDir, 'final-report.md'), ['# Final Report', '', 'Status: ' + (ok ? 'completed' : 'failed'), 'Artifacts: ' + REQUIRED_ARTIFACTS.length, 'Residual risk: review command output, patch, and mutation requests before consequential mutation.'].join('\n'));
  if (!fs.existsSync(path.join(outputDir, 'mutation-requests.jsonl'))) writeFile(path.join(outputDir, 'mutation-requests.jsonl'), '');
  const artifacts = REQUIRED_ARTIFACTS.map((name) => artifactRecord(outputDir, name));
  const acceptanceMatrix = buildAcceptanceMatrix(job, commandResults, artifacts);
  writeJson(path.join(outputDir, 'acceptance-matrix.json'), acceptanceMatrix);
  artifacts.push(artifactRecord(outputDir, 'acceptance-matrix.json', 'review', false));
  const handoffPacket = buildHandoffPacket({outputDir, runWorkspace, jobPacket, manifest, commandResults, artifacts, status: ok ? 'completed' : 'failed', gitStatus, changedFiles, verification});
  writeJson(path.join(outputDir, 'handoff-packet.json'), handoffPacket);
  artifacts.push(artifactRecord(outputDir, 'handoff-packet.json', 'handoff', false));
  for (const name of OPTIONAL_POSTMORTEM_ARTIFACTS) {
    if (name === 'acceptance-matrix.json' || name === 'handoff-packet.json') continue;
    if (fs.existsSync(path.join(outputDir, name))) artifacts.push(artifactRecord(outputDir, name, 'postmortem', false));
  }
  if (fs.existsSync(path.join(outputDir, 'codex-prompt.md'))) artifacts.push(artifactRecord(outputDir, 'codex-prompt.md', 'prompt', false));
  return artifacts;
}

function requireManifest(args) {
  const manifest = readJson(args.manifest, null);
  if (!manifest) throw new Error('Manifest is required: --manifest FILE');
  return manifest;
}

function checkTool(tool, cwd, deep) {
  const command = deep && tool.deepCommand ? tool.deepCommand : tool.command;
  if (!command) return {...tool, ok: false, detail: 'missing command'};
  const result = run(command, cwd || process.cwd());
  return {...tool, checkedCommand: command, ok: result.exitCode === 0, exitCode: result.exitCode, stdout: result.stdout.slice(0, 2000), stderr: result.stderr.slice(0, 2000)};
}

function prepareBase(args) {
  const manifest = requireManifest(args);
  const repoPath = manifest.repoPath || manifest.path;
  if (!repoPath || !fs.existsSync(repoPath)) throw new Error('Manifest repoPath does not exist: ' + repoPath);
  const orientationFiles = (manifest.orientationFiles || []).map((file) => ({file, exists: fs.existsSync(path.join(repoPath, file))}));
  const toolChecks = (manifest.toolChecks || []).map((tool) => checkTool(tool, repoPath, args.deep));
  const report = {
    ok: orientationFiles.every((item) => item.exists) && toolChecks.every((item) => item.ok || item.optional),
    projectId: manifest.projectId,
    repoPath,
    baseWorkspace: manifestBaseWorkspace(manifest),
    orientationFiles,
    toolChecks,
    generatedAt: new Date().toISOString(),
  };
  const outDir = args.outputDir ? path.resolve(args.outputDir) : '';
  if (outDir) writeJson(path.join(outDir, 'prepare-base-report.json'), report);
  console.log(JSON.stringify(report, null, 2));
  return report.ok ? 0 : 1;
}

async function fetchText(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  return {response, text};
}

function parseMcp(text) {
  const dataLines = text.split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  return JSON.parse(dataLines.length ? dataLines.join('\n') : text);
}

function contentJson(result) {
  const text = result.result?.content?.find((item) => item.type === 'text')?.text || '{}';
  return JSON.parse(text);
}

async function callMcpTool(mcpUrl, token, name, args = {}) {
  const {response, text} = await fetchText(mcpUrl, {method: 'POST', headers: {authorization: 'Bearer ' + token, 'content-type': 'application/json', accept: 'application/json, text/event-stream'}, body: JSON.stringify({jsonrpc: '2.0', id: Date.now(), method: 'tools/call', params: {name, arguments: args}})});
  const json = parseMcp(text);
  if (!response.ok || json.error) throw new Error(name + ' failed: ' + text.slice(0, 800));
  return contentJson(json);
}

async function registerWorker(args) {
  const manifest = requireManifest(args);
  if (!args.mcpToken) throw new Error('register requires --mcp-token or HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN');
  const workerId = args.workerId || manifest.workerId || (manifest.projectId + '-local-oneshot');
  const identity = readOrCreateInstallationIdentity(args.config, manifest, workerId);
  const workerInstanceId = createWorkerInstanceId(workerId);
  const processStartAtMs = Date.now();
  const registered = await callMcpTool(args.mcpUrl, args.mcpToken, 'command_center.workers.register_oneshot', {
    idempotencyKey: 'register-' + workerId + '-' + (manifest.version || 'v1'),
    workerId,
    workerInstallationId: identity.workerInstallationId,
    workerInstanceId,
    runnerVersion: RUNNER_VERSION,
    protocolVersion: WORKER_PROTOCOL_VERSION,
    processStartAtMs,
    heartbeatSeq: 0,
    engine: 'codex',
    location: manifest.location || 'termux',
    capabilities: manifest.capabilities || ['codex', 'one-shot-worker', 'prepared-workspace'],
    baseWorkspace: manifestBaseWorkspace(manifest),
    limits: manifest.limits || {concurrentJobs: 1},
    activation: manifest.activation || {mode: 'poll'},
    stableWorkerIdentity: manifest.stableWorkerIdentity || workerId,
    runtime: {...(manifest.runtime || {}), codexAuth: (manifest.runtime || {}).codexAuth || 'chatgpt_saved_login', authMode: (manifest.runtime || {}).authMode || 'chatgpt_saved_login'},
    ...machineImageRuntimePayload(manifest),
    cloudRunJob: manifest.cloudRunJob,
    sessionPolicy: manifest.sessionPolicy,
    repositoryAffinity: manifest.repositoryAffinity,
  });
  const config = {
    commandCenterBase: args.commandCenterBase,
    mcpUrl: args.mcpUrl,
    workerId: registered.worker?.workerId || workerId,
    workerInstallationId: identity.workerInstallationId,
    workerInstanceId,
    runnerVersion: RUNNER_VERSION,
    protocolVersion: WORKER_PROTOCOL_VERSION,
    processStartAtMs,
    heartbeatSeq: 0,
    workerToken: registered.workerToken,
    configPath: path.resolve(args.config),
    manifestPath: path.resolve(args.manifest),
    executorCommand: args.executorCommand || manifest.executorCommand || manifest.defaultExecutorCommand || '',
    createdAt: new Date().toISOString(),
    stableWorkerIdentity: manifest.stableWorkerIdentity || workerId,
  };
  writeConfig(args.config, config);
  console.log(JSON.stringify({ok: true, workerId, configPath: args.config, warning: 'Worker token saved locally with 0600 permissions. Do not commit this file.'}, null, 2));
  return 0;
}

async function workerPost(base, token, route, body = {}) {
  const {response, text} = await fetchText(base + route, {method: 'POST', headers: {authorization: 'Bearer ' + token, 'content-type': 'application/json'}, body: JSON.stringify(body)});
  const json = JSON.parse(text || '{}');
  if (!response.ok || json.ok === false) throw new Error(route + ' failed: ' + text.slice(0, 800));
  return json;
}

function executorCommandMetadata(command, cwd, outputDir) {
  return {
    command: redactSecrets(command),
    cwd,
    outputDir,
    shell: true,
    environmentPolicy: commandUsesCodex(command) ? {OPENAI_API_KEY: 'removed', CODEX_API_KEY: 'removed', authSource: 'saved_codex_login'} : {authSource: 'inherited_non_codex_executor'},
  };
}

async function runStreamingExecutor({command, cwd, env = {}, outputDir, jobPacket = {}, manifest = {}, eventPoster = null}) {
  const job = jobPacket.job || jobPacket;
  const jobId = job.jobId || '';
  const projectId = job.projectId || manifest.projectId || '';
  const workerId = manifest.workerId || '';
  const startedAt = new Date().toISOString();
  const startedAtMs = Date.now();
  const stdoutPath = path.join(outputDir, 'stdout-transcript.txt');
  const stderrPath = path.join(outputDir, 'stderr-transcript.txt');
  const eventTranscriptPath = path.join(outputDir, 'event-transcript.jsonl');
  const statusPath = path.join(outputDir, 'executor-status.json');
  const heartbeatMs = Math.max(1000, Number(process.env.COMMAND_CENTER_EXECUTOR_HEARTBEAT_MS || DEFAULT_EXECUTOR_HEARTBEAT_MS));
  const batchMs = Math.max(250, Number(process.env.COMMAND_CENTER_EXECUTOR_BATCH_MS || DEFAULT_EXECUTOR_BATCH_MS));
  const batchLines = Math.max(1, Number(process.env.COMMAND_CENTER_EXECUTOR_BATCH_LINES || DEFAULT_EXECUTOR_BATCH_LINES));
  const stats = {stdoutLines: 0, stderrLines: 0, stdoutBytes: 0, stderrBytes: 0, eventsPosted: 0, eventPostFailures: 0};
  let child = null;
  let lastOutputAtMs = Date.now();
  let cloudChain = Promise.resolve();

  const postCloud = (payload) => {
    if (!eventPoster) return;
    cloudChain = cloudChain.then(async () => {
      let lastError = null;
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        try {
          await eventPoster({...payload, data: {...safeObject(payload.data), postAttempt: attempt}});
          stats.eventsPosted += 1;
          return;
        } catch (err) {
          lastError = err;
          if (attempt < 3) await new Promise((resolve) => setTimeout(resolve, attempt * 750));
        }
      }
      stats.eventPostFailures += 1;
      appendFile(eventTranscriptPath, JSON.stringify({createdAt: new Date().toISOString(), type: 'event_post_failed', error: redactSecrets(lastError?.message || String(lastError)), failedType: payload.type}) + '\n');
    });
  };

  const emitEvent = (type, summary, data = {}) => {
    const event = {
      type,
      summary: redactSecrets(summary),
      data: JSON.parse(JSON.stringify(data, (_key, value) => typeof value === 'string' ? redactSecrets(value) : value)),
      createdAt: new Date().toISOString(),
      jobId,
      projectId,
    };
    appendFile(eventTranscriptPath, JSON.stringify(event) + '\n');
    postCloud({type, summary: event.summary, data: event.data});
  };

  const stdoutBatch = [];
  const stderrBatch = [];
  let stdoutRemainder = '';
  let stderrRemainder = '';

  const flushBatch = (stream, reason) => {
    const batch = stream === 'stdout' ? stdoutBatch : stderrBatch;
    if (!batch.length) return;
    const lines = batch.splice(0, batch.length);
    emitEvent(`executor_${stream}`, `${stream} ${lines.length} line(s)`, {stream, reason, lines, lineCount: lines.length});
  };

  const batchTimer = setInterval(() => {
    flushBatch('stdout', 'timer');
    flushBatch('stderr', 'timer');
  }, batchMs);

  const appendChunk = (stream, chunk) => {
    const raw = chunk.toString('utf8');
    const transcriptPath = stream === 'stdout' ? stdoutPath : stderrPath;
    appendFile(transcriptPath, redactSecrets(raw));
    if (stream === 'stdout') stats.stdoutBytes += Buffer.byteLength(raw);
    else stats.stderrBytes += Buffer.byteLength(raw);
    lastOutputAtMs = Date.now();
    const combined = (stream === 'stdout' ? stdoutRemainder : stderrRemainder) + raw;
    const parts = combined.split(/\r?\n/);
    const remainder = parts.pop() || '';
    if (stream === 'stdout') stdoutRemainder = remainder;
    else stderrRemainder = remainder;
    for (const line of cleanLines(parts.join('\n')).filter((item) => item.length || parts.length)) {
      if (stream === 'stdout') {
        stdoutBatch.push(line);
        stats.stdoutLines += 1;
        if (stdoutBatch.length >= batchLines) flushBatch('stdout', 'line_limit');
      } else {
        stderrBatch.push(line);
        stats.stderrLines += 1;
        if (stderrBatch.length >= batchLines) flushBatch('stderr', 'line_limit');
      }
    }
  };

  return await new Promise((resolve) => {
    let finished = false;
    let cancelled = false;
    const finish = async (status) => {
      if (finished) return;
      finished = true;
      clearInterval(batchTimer);
      clearInterval(heartbeatTimer);
      if (stdoutRemainder) {
        stdoutBatch.push(redactSecrets(stdoutRemainder).slice(0, 1200));
        stats.stdoutLines += 1;
        stdoutRemainder = '';
      }
      if (stderrRemainder) {
        stderrBatch.push(redactSecrets(stderrRemainder).slice(0, 1200));
        stats.stderrLines += 1;
        stderrRemainder = '';
      }
      flushBatch('stdout', 'finish');
      flushBatch('stderr', 'finish');
      const endedAtMs = Date.now();
      const payload = {
        command: redactSecrets(command),
        cwd,
        startedAt,
        endedAt: new Date(endedAtMs).toISOString(),
        exitCode: status.exitCode,
        signal: status.signal || '',
        cancelled,
        durationMs: endedAtMs - startedAtMs,
        stdout: '',
        stderr: status.error ? redactSecrets(status.error) : '',
        stdoutPath,
        stderrPath,
        eventTranscriptPath,
        stats,
      };
      writeJson(statusPath, payload);
      emitEvent(status.exitCode === 0 && !cancelled ? 'executor_finished' : (cancelled ? 'executor_cancelled' : 'executor_failed'), status.summary, {exitCode: status.exitCode, signal: status.signal || '', durationMs: payload.durationMs, stats});
      await cloudChain;
      resolve(payload);
    };

    const heartbeatTimer = setInterval(() => {
      emitEvent('executor_heartbeat', 'Executor heartbeat.', {elapsedMs: Date.now() - startedAtMs, lastOutputAgeMs: Date.now() - lastOutputAtMs, pid: child?.pid || 0, stats});
    }, heartbeatMs);

    const cancel = (signal) => {
      cancelled = true;
      emitEvent('executor_cancelled', `Worker received ${signal}; terminating executor.`, {signal, pid: child?.pid || 0, elapsedMs: Date.now() - startedAtMs});
      try { if (child && !child.killed) child.kill('SIGTERM'); } catch (_) {}
      setTimeout(() => {
        try { if (child && !child.killed) child.kill('SIGKILL'); } catch (_) {}
      }, 5000).unref?.();
    };
    process.once('SIGINT', cancel);
    process.once('SIGTERM', cancel);

    try {
      child = spawn(command, {cwd, shell: true, env: childEnv(env, {stripCodexApiKeys: commandUsesCodex(command)}), stdio: ['ignore', 'pipe', 'pipe']});
    } catch (err) {
      process.removeListener('SIGINT', cancel);
      process.removeListener('SIGTERM', cancel);
      finish({exitCode: 1, error: err.message || String(err), summary: 'Executor spawn failed.'});
      return;
    }

    emitEvent('executor_started', 'Executor started.', {...executorCommandMetadata(command, cwd, outputDir), pid: child.pid || 0, startedAt});
    child.stdout.on('data', (chunk) => appendChunk('stdout', chunk));
    child.stderr.on('data', (chunk) => appendChunk('stderr', chunk));
    child.on('error', (err) => {
      process.removeListener('SIGINT', cancel);
      process.removeListener('SIGTERM', cancel);
      finish({exitCode: 1, error: err.message || String(err), summary: 'Executor failed before exit.'});
    });
    child.on('close', (code, signal) => {
      process.removeListener('SIGINT', cancel);
      process.removeListener('SIGTERM', cancel);
      finish({exitCode: typeof code === 'number' ? code : (signal ? 130 : 1), signal, summary: `Executor exited with code ${typeof code === 'number' ? code : 'unknown'}${signal ? ` signal ${signal}` : ''}.`});
    });
  });
}

async function localRun({args, manifest = {}, jobPacket, outputDir, eventPoster = null}) {
  const baseWorkspace = args.baseWorkspace || manifest.repoPath || manifest.path;
  if (!baseWorkspace) throw new Error('No base workspace path was provided.');
  const runWorkspace = path.join(outputDir, 'workspace');
  fs.rmSync(outputDir, {recursive: true, force: true});
  fs.mkdirSync(outputDir, {recursive: true});
  copyBaseWorkspace(path.resolve(baseWorkspace), runWorkspace);
  const promptPath = buildPromptPacket(jobPacket, manifest, outputDir);
  writeJson(path.join(outputDir, 'job-intake.json'), {jobPacket, manifest, runWorkspace, capturedAt: new Date().toISOString()});
  const commandResults = [];
  const executor = args.executorCommand || args.command;
  if (executor) {
    commandResults.push(await runStreamingExecutor({command: executor, cwd: runWorkspace, env: {COMMAND_CENTER_JOB_PACKET: path.join(outputDir, 'job-intake.json'), COMMAND_CENTER_PROMPT_PACKET: promptPath, COMMAND_CENTER_ARTIFACT_DIR: outputDir}, outputDir, jobPacket, manifest, eventPoster}));
  } else {
    commandResults.push({command: 'NO_EXECUTOR_CONFIGURED', cwd: runWorkspace, startedAt: new Date().toISOString(), endedAt: new Date().toISOString(), exitCode: 78, stdout: '', stderr: 'No callable Codex executor command configured. Failing honestly instead of faking implementation.'});
  }
  const status = commandResults.every((item) => item.exitCode === 0) ? 'completed' : 'failed';
  const artifacts = writeRequiredArtifacts({outputDir, runWorkspace, jobPacket, commandResults, manifest, status});
  writeJson(path.join(outputDir, 'artifact-upload-summary.json'), {status: 'not_uploaded_local_run', artifactCount: artifacts.length, generatedAt: new Date().toISOString()});
  artifacts.push(artifactRecord(outputDir, 'artifact-upload-summary.json', 'upload-summary', false));
  writeJson(path.join(outputDir, 'artifacts.json'), {artifacts});
  console.log(JSON.stringify({ok: status === 'completed', status, outputDir, runWorkspace, artifacts: artifacts.length}, null, 2));
  return {status, artifacts, outputDir, runWorkspace, commandResults};
}

async function heartbeatOnce(args, phase = 'idle') {
  const config = ensureRuntimeIdentity({...readConfig(args.config), configPath: path.resolve(args.config)}, readJson(readConfig(args.config).manifestPath, {}));
  const manifest = readJson(config.manifestPath, {});
  config.heartbeatSeq = Number(config.heartbeatSeq || 0) + 1;
  writeConfig(args.config, config);
  const payload = {
    phase,
    supervisorPid: process.pid,
    workerInstallationId: config.workerInstallationId,
    workerInstanceId: config.workerInstanceId,
    runnerVersion: config.runnerVersion || RUNNER_VERSION,
    protocolVersion: config.protocolVersion || WORKER_PROTOCOL_VERSION,
    processStartAtMs: config.processStartAtMs,
    heartbeatSeq: config.heartbeatSeq,
    location: manifest.location || 'termux',
    capabilities: manifest.capabilities || [],
    runtime: {...(manifest.runtime || {}), codexAuth: 'chatgpt_saved_login', authMode: 'chatgpt_saved_login', runnerVersion: config.runnerVersion || RUNNER_VERSION, protocolVersion: config.protocolVersion || WORKER_PROTOCOL_VERSION},
    ...machineImageRuntimePayload(manifest),
    stableWorkerIdentity: config.stableWorkerIdentity || manifest.stableWorkerIdentity || config.workerId,
  };
  if (!payload.activeSessionIds.length) delete payload.activeSessionIds;
  if (payload.sessionCapacity && !payload.sessionCapacity.activeSessionIds.length) delete payload.sessionCapacity.activeSessionIds;
  const result = await workerPost(config.commandCenterBase || args.commandCenterBase, config.workerToken, '/worker/heartbeat', payload);
  console.log(JSON.stringify({ok: true, mode: 'heartbeat', workerId: result.workerId, heartbeatAtMs: result.heartbeatAtMs, routable: result.routable}, null, 2));
  return 0;
}

async function runOnce(args) {
  const config = ensureRuntimeIdentity({...readConfig(args.config), configPath: path.resolve(args.config)}, readJson(readConfig(args.config).manifestPath, {}));
  writeConfig(args.config, config);
  const manifest = readJson(config.manifestPath, {});
  const lease = await workerPost(config.commandCenterBase || args.commandCenterBase, config.workerToken, '/worker/lease', {workerInstallationId: config.workerInstallationId, workerInstanceId: config.workerInstanceId, runnerVersion: config.runnerVersion, protocolVersion: config.protocolVersion});
  if (!lease.leased) {
    console.log(JSON.stringify({ok: true, leased: false}, null, 2));
    return 0;
  }
  const jobId = lease.packet.job.jobId;
  const outputDir = path.resolve(args.outputDir || path.join(os.tmpdir(), 'command-center-worker', jobId));
  const commandCenterBase = config.commandCenterBase || args.commandCenterBase;
  const eventPoster = (event) => workerPost(commandCenterBase, config.workerToken, '/worker/events', {jobId, ...event});
  const result = await localRun({args: {...args, executorCommand: args.executorCommand || config.executorCommand}, manifest, jobPacket: lease.packet, outputDir, eventPoster});
  const uploaded = await workerPost(commandCenterBase, config.workerToken, '/worker/artifacts', {jobId, artifacts: result.artifacts});
  writeJson(path.join(outputDir, 'artifact-upload-summary.json'), {status: 'uploaded', artifactCount: result.artifacts.length, uploadedArtifactIds: (uploaded.artifacts || []).map((artifact) => artifact.artifactId), generatedAt: new Date().toISOString()});
  const uploadSummary = artifactRecord(outputDir, 'artifact-upload-summary.json', 'upload-summary', false);
  const uploadSummaryIndex = result.artifacts.findIndex((artifact) => artifact.name === 'artifact-upload-summary.json');
  if (uploadSummaryIndex >= 0) result.artifacts[uploadSummaryIndex] = uploadSummary;
  else result.artifacts.push(uploadSummary);
  await eventPoster({type: 'artifact_upload_summary', summary: `Uploaded ${result.artifacts.length} worker artifact(s).`, data: {artifactCount: result.artifacts.length, uploadedArtifactIds: (uploaded.artifacts || []).map((artifact) => artifact.artifactId)}});
  await workerPost(config.commandCenterBase || args.commandCenterBase, config.workerToken, '/worker/checkpoint', {jobId, currentPhase: result.status, workingTreeState: result.commandResults.every((item) => item.exitCode === 0) ? 'verified' : 'failed', filesChanged: readJson(path.join(outputDir, 'changed-files.json'), {}).changedFiles?.map((item) => item.path) || [], testsRun: result.commandResults.map((item) => item.command), evidenceRefs: result.artifacts.map((item) => item.uri), nextAction: result.status === 'completed' ? 'ChatGPT review completion evidence.' : 'Review failure report and revise job or worker configuration.'});
  await workerPost(config.commandCenterBase || args.commandCenterBase, config.workerToken, '/worker/complete', {jobId, status: result.status, finalReport: fs.readFileSync(path.join(outputDir, 'final-report.md'), 'utf8'), artifacts: result.artifacts});
  return result.status === 'completed' ? 0 : 1;
}

async function supervise(args) {
  let idlePolls = 0;
  rotateWorkerInstance(args.config);
  await heartbeatOnce(args, 'supervisor_start');
  while (true) {
    const code = await runOnce(args);
    if (code === 0) idlePolls += 1;
    else idlePolls = 0;
    if (args.maxIdlePolls > 0 && idlePolls >= args.maxIdlePolls) return 0;
    await new Promise((resolve) => setTimeout(resolve, Math.max(1000, args.pollMs || DEFAULT_SUPERVISOR_POLL_MS)));
    await heartbeatOnce(args, 'supervisor_idle');
  }
}

async function runSelfTest() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-oneshot-selftest-'));
  const base = path.join(root, 'base');
  const packet = path.join(root, 'packet.json');
  const manifestPath = path.join(root, 'manifest.json');
  const out = path.join(root, 'out');
  fs.mkdirSync(base, {recursive: true});
  const init = run('git init >/dev/null && git config user.email test@example.invalid && git config user.name Test && printf base > README.md && git add README.md && git commit -m base >/dev/null', base);
  if (init.exitCode !== 0) throw new Error('self-test git init failed: ' + init.stderr);
  writeJson(packet, {job: {jobId: 'job_selftest123456', projectId: 'home-center', objective: 'self test one-shot artifact contract', acceptanceCriteria: ['artifact contract'], requiredArtifacts: REQUIRED_ARTIFACTS, mutationPolicy: {editFiles: 'allowed'}}});
  writeJson(manifestPath, {projectId: 'self-test', repoPath: base, orientationFiles: ['README.md'], toolChecks: [{name: 'node', command: 'node --version'}], capabilities: ['codex', 'one-shot-worker', 'prepared-workspace']});
  const prepareCode = prepareBase({manifest: manifestPath, outputDir: path.join(root, 'prepare'), deep: false});
  if (prepareCode !== 0) throw new Error('self-test prepare-base failed');
  const result = await localRun({args: {baseWorkspace: base, command: 'printf changed > README.md'}, manifest: readJson(manifestPath), jobPacket: readJson(packet), outputDir: out});
  const missing = REQUIRED_ARTIFACTS.filter((name) => !fs.existsSync(path.join(out, name)));
  if (result.status !== 'completed' || missing.length) throw new Error('self-test failed; missing: ' + missing.join(', '));
  for (const reviewArtifact of ['acceptance-matrix.json', 'handoff-packet.json']) {
    if (!fs.existsSync(path.join(out, reviewArtifact))) throw new Error('self-test missing review artifact: ' + reviewArtifact);
  }
  const handoffPacket = readJson(path.join(out, 'handoff-packet.json'), {});
  if (handoffPacket.packetVersion !== 'command-center-handoff-v1') throw new Error('self-test handoff packet version mismatch');
  if (handoffPacket.review?.correctability?.preferredOperation !== 'command_center.jobs.create_followup') throw new Error('self-test handoff packet missing follow-up operation');
  const streamOut = path.join(root, 'stream-out');
  const oldHeartbeat = process.env.COMMAND_CENTER_EXECUTOR_HEARTBEAT_MS;
  const oldBatch = process.env.COMMAND_CENTER_EXECUTOR_BATCH_MS;
  process.env.COMMAND_CENTER_EXECUTOR_HEARTBEAT_MS = '700';
  process.env.COMMAND_CENTER_EXECUTOR_BATCH_MS = '250';
  const streamCommand = 'node -e "console.log(\'stream-one\'); setTimeout(()=>console.error(\'stream-two\'),300); setTimeout(()=>console.log(\'stream-three\'),1700); setTimeout(()=>process.exit(0),2400)"';
  const streamResult = await localRun({args: {baseWorkspace: base, command: streamCommand}, manifest: readJson(manifestPath), jobPacket: readJson(packet), outputDir: streamOut});
  if (oldHeartbeat === undefined) delete process.env.COMMAND_CENTER_EXECUTOR_HEARTBEAT_MS; else process.env.COMMAND_CENTER_EXECUTOR_HEARTBEAT_MS = oldHeartbeat;
  if (oldBatch === undefined) delete process.env.COMMAND_CENTER_EXECUTOR_BATCH_MS; else process.env.COMMAND_CENTER_EXECUTOR_BATCH_MS = oldBatch;
  if (streamResult.status !== 'completed') throw new Error('streaming self-test executor failed');
  const eventRows = fs.readFileSync(path.join(streamOut, 'event-transcript.jsonl'), 'utf8').trim().split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
  const eventTypes = eventRows.map((event) => event.type);
  for (const requiredType of ['executor_started', 'executor_stdout', 'executor_stderr', 'executor_heartbeat', 'executor_finished']) {
    if (!eventTypes.includes(requiredType)) throw new Error('streaming self-test missing event: ' + requiredType);
  }
  if (!fs.readFileSync(path.join(streamOut, 'stdout-transcript.txt'), 'utf8').includes('stream-one')) throw new Error('streaming self-test missing stdout transcript');
  if (!fs.readFileSync(path.join(streamOut, 'stderr-transcript.txt'), 'utf8').includes('stream-two')) throw new Error('streaming self-test missing stderr transcript');
  if (!fs.existsSync(path.join(streamOut, 'executor-status.json'))) throw new Error('streaming self-test missing executor status');
  if (!fs.existsSync(path.join(streamOut, 'handoff-packet.json'))) throw new Error('streaming self-test missing handoff packet');
  if (!fs.existsSync(path.join(streamOut, 'acceptance-matrix.json'))) throw new Error('streaming self-test missing acceptance matrix');
  const oldOpenAi = process.env.OPENAI_API_KEY;
  const oldCodex = process.env.CODEX_API_KEY;
  process.env.OPENAI_API_KEY = 'sk-test-should-not-reach-codex';
  process.env.CODEX_API_KEY = 'codex-test-should-not-reach-codex';
  const envOut = path.join(root, 'env-out');
  const envCommand = 'node -e "if (process.env.OPENAI_API_KEY || process.env.CODEX_API_KEY) { console.error(\'api key leaked\'); process.exit(23); } console.log(\'no api key env\')" # codex exec';
  const envResult = await localRun({args: {baseWorkspace: base, command: envCommand}, manifest: readJson(manifestPath), jobPacket: readJson(packet), outputDir: envOut});
  if (oldOpenAi === undefined) delete process.env.OPENAI_API_KEY; else process.env.OPENAI_API_KEY = oldOpenAi;
  if (oldCodex === undefined) delete process.env.CODEX_API_KEY; else process.env.CODEX_API_KEY = oldCodex;
  if (envResult.status !== 'completed') throw new Error('codex env denylist self-test failed');
  const envStatus = readJson(path.join(envOut, 'executor-status.json'), {});
  if (envStatus.command.includes('sk-test-should-not-reach-codex')) throw new Error('executor status leaked API key');
  if (envStatus.stats?.stderrBytes) throw new Error('codex env denylist produced stderr');
  console.log('Command Center one-shot worker self-test: OK (' + out + ', ' + streamOut + ')');
  return 0;
}

async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.mode === 'self-test') return await runSelfTest();
  if (args.mode === 'prepare-base') return prepareBase(args);
  if (args.mode === 'register') return registerWorker(args);
  if (args.mode === 'run-once') return runOnce(args);
  if (args.mode === 'heartbeat') return heartbeatOnce(args);
  if (args.mode === 'supervise') return supervise(args);
  if (args.mode === 'run-local') {
    if (!args.baseWorkspace || !args.jobPacket || !args.outputDir) throw new Error('run-local requires --base-workspace, --job-packet, and --output-dir');
    const result = await localRun({args, manifest: {}, jobPacket: readJson(args.jobPacket, {}), outputDir: path.resolve(args.outputDir)});
    return result.status === 'completed' ? 0 : 1;
  }
  throw new Error('Unknown mode: ' + args.mode);
}

main().then((code) => {
  if (code) process.exit(code);
}).catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
