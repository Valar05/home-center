#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawn, spawnSync} from 'node:child_process';

const env = process.env;
const commandCenterBase = env.COMMAND_CENTER_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp';
const workerToken = env.COMMAND_CENTER_WORKER_TOKEN || '';
const activationId = env.COMMAND_CENTER_ACTIVATION_ID || '';
const jobId = env.COMMAND_CENTER_JOB_ID || '';
const snapshotBucket = env.COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET || '';
const workspaceRoot = env.COMMAND_CENTER_WORKSPACE_DIR || '/workspace/session';
const codexHome = env.CODEX_HOME || path.join(os.homedir(), '.command-center-codex-home');
const OPENAI_AUTH_MODES = ['chatgpt_subscription', 'api_key_metered', 'unknown'];

function required(name, value) {
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function redact(text) {
  return String(text || '')
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]')
    .replace(/\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/g, '[REDACTED_WORKER_TOKEN]')
    .replace(/\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_JWT]')
    .replace(/(OPENAI_API_KEY|GITHUB_TOKEN|GH_TOKEN)=\\S+/g, '$1=[REDACTED]');
}

function normalizeOpenAiAuthMode(value) {
  const mode = String(value || '').trim().toLowerCase();
  return OPENAI_AUTH_MODES.includes(mode) ? mode : 'unknown';
}

function detectOpenAiAuthMode() {
  const explicit = normalizeOpenAiAuthMode(env.COMMAND_CENTER_OPENAI_AUTH_MODE || env.OPENAI_AUTH_MODE);
  if (explicit !== 'unknown') return explicit;
  if (String(env.OPENAI_API_KEY || '').trim()) return 'api_key_metered';
  for (const rel of ['auth.json', 'codex.json', 'config.json']) {
    if (fs.existsSync(path.join(codexHome, rel))) return 'chatgpt_subscription';
  }
  return 'unknown';
}

function budgetPolicyFromJob(job = {}) {
  const policy = job.budgetPolicy && typeof job.budgetPolicy === 'object' ? job.budgetPolicy : {};
  const budgetClass = String(policy.budgetClass || job.budgetClass || 'small').trim() || 'small';
  const defaults = {
    small: {wallClockMs: 45 * 60 * 1000, maxRetries: 0, maxFollowups: 0, maxConcurrency: 1, inputWarningTokens: 100000, inputAnomalyTokens: 500000, approvalRequiredAtInputTokens: 500000, hardStopInputTokens: 900000, extendedExecutionAuthorized: false},
    medium: {wallClockMs: 2 * 60 * 60 * 1000, maxRetries: 1, maxFollowups: 1, maxConcurrency: 1, inputWarningTokens: 250000, inputAnomalyTokens: 750000, approvalRequiredAtInputTokens: 750000, hardStopInputTokens: 1500000, extendedExecutionAuthorized: false},
    large: {wallClockMs: 6 * 60 * 60 * 1000, maxRetries: 1, maxFollowups: 2, maxConcurrency: 1, inputWarningTokens: 500000, inputAnomalyTokens: 1500000, approvalRequiredAtInputTokens: 1500000, hardStopInputTokens: 3000000, extendedExecutionAuthorized: true},
    long_running_authorized: {wallClockMs: 12 * 60 * 60 * 1000, maxRetries: 1, maxFollowups: 3, maxConcurrency: 1, inputWarningTokens: 750000, inputAnomalyTokens: 2000000, approvalRequiredAtInputTokens: 2000000, hardStopInputTokens: 5000000, extendedExecutionAuthorized: true},
  };
  return {budgetClass, ...(defaults[budgetClass] || defaults.small), ...policy};
}

function evaluateBudgetUsage(usage, job = {}, authMeter = {}) {
  const policy = budgetPolicyFromJob(job);
  const inputTokens = Number(usage.inputTokens || 0);
  const cachedInputTokens = Number(usage.cachedInputTokens || 0);
  const elapsedMs = Number(usage.elapsedMs || 0);
  const warnings = Array.isArray(usage.warnings) ? [...usage.warnings] : [];
  const states = [];
  const wallClockMs = Number(policy.wallClockMs || 0);
  if (inputTokens >= Number(policy.inputWarningTokens || 0)) warnings.push(`Input token warning threshold crossed: ${inputTokens}/${policy.inputWarningTokens}.`);
  if (elapsedMs > 0 && wallClockMs > 0 && elapsedMs >= wallClockMs) {
    warnings.push(`Wall-clock budget crossed: ${elapsedMs}/${wallClockMs} ms.`);
    states.push('wall_clock_over_budget');
  }
  if (inputTokens >= Number(policy.inputAnomalyTokens || 0)) states.push('budget_anomalous');
  if (inputTokens >= Number(policy.approvalRequiredAtInputTokens || 0)) states.push('requires_authorization_before_retry_or_followup');
  if (normalizeOpenAiAuthMode(authMeter.openAiAuthMode) === 'unknown') states.push('auth_meter_unknown');
  if (normalizeOpenAiAuthMode(authMeter.openAiAuthMode) === 'api_key_metered') states.push('api_key_metered');
  return {
    ...usage,
    inputTokens,
    cachedInputTokens,
    uncachedInputTokens: Math.max(0, inputTokens - cachedInputTokens),
    elapsedMs,
    cachedInputRatio: inputTokens > 0 ? cachedInputTokens / inputTokens : 0,
    budgetPolicy: policy,
    authMeter,
    warnings: Array.from(new Set(warnings)),
    states: Array.from(new Set(states)),
    budgetAnomalous: states.includes('budget_anomalous'),
    requiresAuthorizationBeforeRetryOrFollowup: states.includes('requires_authorization_before_retry_or_followup') || states.includes('auth_meter_unknown'),
  };
}

async function post(endpoint, body) {
  const response = await fetch(`${commandCenterBase}${endpoint}`, {
    method: 'POST',
    headers: {authorization: `Bearer ${workerToken}`, 'content-type': 'application/json'},
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let json = {};
  try { json = text ? JSON.parse(text) : {}; } catch (_) { json = {raw: redact(text.slice(0, 1000))}; }
  if (!response.ok) throw new Error(`${endpoint} failed: ${response.status} ${redact(JSON.stringify(json).slice(0, 1000))}`);
  return json;
}

function run(command, cwd = workspaceRoot, options = {}) {
  const result = spawnSync(command, {
    cwd,
    shell: true,
    encoding: 'utf8',
    env: {...process.env, ...(options.env || {})},
    maxBuffer: 20 * 1024 * 1024,
  });
  return {
    command,
    cwd,
    exitCode: result.status ?? 1,
    stdout: redact(result.stdout || ''),
    stderr: redact(result.stderr || ''),
  };
}

function ensureWorkspace() {
  fs.mkdirSync(workspaceRoot, {recursive: true});
}

function restoreWorkspace(ref, repository) {
  ensureWorkspace();
  if (ref && ref.startsWith('gs://')) {
    const archive = path.join(os.tmpdir(), 'workspace-restore.tgz');
    const copy = run(`gcloud storage cp ${JSON.stringify(ref)} ${JSON.stringify(archive)}`, '/');
    if (copy.exitCode !== 0) throw new Error(`workspace restore failed: ${copy.stderr || copy.stdout}`);
    const untar = run(`tar -xzf ${JSON.stringify(archive)} -C ${JSON.stringify(workspaceRoot)}`, '/');
    if (untar.exitCode !== 0) throw new Error(`workspace unpack failed: ${untar.stderr || untar.stdout}`);
    return {mode: 'gcs_snapshot', ref};
  }
  if (repository) {
    const clone = run(`git clone ${JSON.stringify(`https://github.com/${repository}.git`)} ${JSON.stringify(workspaceRoot)}`, '/');
    if (clone.exitCode !== 0) throw new Error(`git restore failed: ${clone.stderr || clone.stdout}`);
    return {mode: 'git_clean_clone', repository};
  }
  fs.writeFileSync(path.join(workspaceRoot, 'SESSION.md'), '# Durable repo-less worker session\n');
  return {mode: 'empty_workspace'};
}

function repositoryFromText(text) {
  const match = String(text || '').match(/\b([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)\b/);
  return match ? match[1] : '';
}

function repositoryFromJob(job = {}) {
  const direct = job.repository || job.inputs?.repository || job.baseWorkspace?.repository || '';
  if (direct) return direct;
  const snapshotRef = String(job.baseWorkspace?.snapshotRef || '');
  if (snapshotRef.startsWith('github://')) return snapshotRef.replace(/^github:\/\//, '').replace(/\/.*$/, '');
  return repositoryFromText([job.objective, job.title, ...(job.constraints || []), ...(job.acceptanceCriteria || [])].join('\n'));
}

function setupGithubAuth(repository) {
  if (!env.GH_TOKEN && !env.GITHUB_TOKEN) return {configured: false, reason: 'GH_TOKEN is not configured.'};
  const token = String(env.GH_TOKEN || env.GITHUB_TOKEN).trim();
  const home = os.homedir();
  const ghConfig = path.join(home, '.config', 'gh');
  fs.mkdirSync(ghConfig, {recursive: true});
  fs.mkdirSync(path.join(home, '.local', 'bin'), {recursive: true});
  fs.writeFileSync(path.join(home, '.git-credentials'), `https://x-access-token:${token}@github.com\n`, {mode: 0o600});
  fs.writeFileSync(path.join(ghConfig, 'hosts.yml'), [
    'github.com:',
    '    oauth_token: ' + token,
    '    user: Valar05',
    '    git_protocol: https',
    '',
  ].join('\n'), {mode: 0o600});
  const askpass = path.join(home, '.local', 'bin', 'command-center-git-askpass.sh');
  fs.writeFileSync(askpass, [
    '#!/bin/sh',
    'case "$1" in',
    '  *Username*) printf %s x-access-token ;;',
    '  *Password*) printf %s "${GH_TOKEN:-$GITHUB_TOKEN}" ;;',
    '  *) printf %s "${GH_TOKEN:-$GITHUB_TOKEN}" ;;',
    'esac',
    '',
  ].join('\n'), {mode: 0o700});
  run('git config --global credential.helper store', '/');
  run('git config --global credential.useHttpPath false', '/');
  run(`git config --global core.askPass ${JSON.stringify(askpass)}`, '/');
  run('git config --global user.email "command-center-worker@home-center.local"', '/');
  run('git config --global user.name "Command Center Worker"', '/');
  process.env.GH_TOKEN = token;
  process.env.GITHUB_TOKEN = token;
  process.env.GIT_ASKPASS = askpass;
  process.env.GIT_TERMINAL_PROMPT = '0';
  const gh = run('gh auth status -h github.com', '/', {env: {GH_TOKEN: token, GITHUB_TOKEN: token, GIT_ASKPASS: askpass, GIT_TERMINAL_PROMPT: '0'}});
  const git = repository ? run(`git ls-remote ${JSON.stringify(`https://github.com/${repository}.git`)} HEAD`, '/', {env: {GH_TOKEN: token, GITHUB_TOKEN: token, GIT_ASKPASS: askpass, GIT_TERMINAL_PROMPT: '0'}}) : {exitCode: 0, stderr: ''};
  return {configured: gh.exitCode === 0 && git.exitCode === 0, repository, ghExitCode: gh.exitCode, gitExitCode: git.exitCode, ghStderr: gh.stderr.slice(0, 500), gitStderr: git.stderr.slice(0, 500), askpass};
}

function restoreJobWorkspace(job = {}) {
  ensureWorkspace();
  const ref = job.baseWorkspace?.snapshotRef || env.COMMAND_CENTER_RESTORE_WORKSPACE_SNAPSHOT_REF || '';
  const repository = repositoryFromJob(job);
  if (ref && ref.startsWith('gs://')) return restoreWorkspace(ref, repository);
  if (repository) {
    const auth = setupGithubAuth(repository);
    if (!auth.configured) throw new Error(`GitHub auth preflight failed for ${repository}: gh=${auth.ghExitCode} git=${auth.gitExitCode} ${auth.ghStderr || auth.gitStderr || auth.reason || ''}`);
    const cloneUrl = `https://github.com/${repository}.git`;
    const clone = run(`git clone ${JSON.stringify(cloneUrl)} ${JSON.stringify(workspaceRoot)}`, '/', {env: {GIT_ASKPASS: auth.askpass, GIT_TERMINAL_PROMPT: '0'}});
    if (clone.exitCode !== 0) throw new Error(`git restore failed: ${clone.stderr || clone.stdout}`);
    return {mode: 'git_clean_clone', repository};
  }
  throw new Error('Repository job did not include a repository binding, github:// base workspace, or owner/repo mention.');
}

function writeResumePacket(resumePacket) {
  fs.writeFileSync(path.join(workspaceRoot, 'codex-resume-packet.json'), JSON.stringify(resumePacket, null, 2) + '\n');
}

function expectedNonce(resumePacket) {
  const prompt = String(resumePacket.activation?.task?.prompt || '');
  const match = prompt.match(/\bNONCE_[A-Za-z0-9_.-]+\b/);
  return match ? match[0] : '';
}

function runCodexPrompt(prompt, options = {}) {
  if (env.COMMAND_CENTER_CODEX_EXECUTOR_DRY_RUN === '1') {
    const report = 'Dry-run durable Cloud Run Debian worker completed without invoking Codex.';
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\n${report}\n`);
    return {exitCode: 0, stdout: report, stderr: '', command: 'dry-run'};
  }
  fs.mkdirSync(codexHome, {recursive: true});
  const login = run('sh -lc \'printf %s "$OPENAI_API_KEY" | codex login --with-api-key\'', workspaceRoot, {env: {CODEX_HOME: codexHome}});
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stdout.txt'), login.stdout);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stderr.txt'), login.stderr);
  if (login.exitCode !== 0) {
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\nCodex login failed with exit code ${login.exitCode}.\n\nSee codex-login-stderr.txt.\n`);
    return login;
  }
  fs.writeFileSync(path.join(workspaceRoot, 'codex-prompt.md'), prompt);
  const result = run(`codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox --output-last-message ${JSON.stringify(path.join(workspaceRoot, 'codex-last-message.md'))} - < ${JSON.stringify(path.join(workspaceRoot, 'codex-prompt.md'))}`, workspaceRoot, {env: {CODEX_HOME: codexHome}});
  fs.writeFileSync(path.join(workspaceRoot, 'codex-stdout.jsonl'), result.stdout);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-stderr.txt'), result.stderr);
  const nonce = options.nonce || '';
  const helloPath = path.join(workspaceRoot, 'hello-world.txt');
  const helloText = fs.existsSync(helloPath) ? fs.readFileSync(helloPath, 'utf8').trim() : '';
  const acceptanceError = nonce && helloText !== nonce ? `Acceptance failed: hello-world.txt was ${helloText ? 'present with unexpected content' : 'not created'}. Expected ${nonce}.` : '';
  const exitCode = result.exitCode === 0 && acceptanceError ? 70 : result.exitCode;
  fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\nExit code: ${exitCode}\n\n${acceptanceError || 'Worker acceptance checks passed.'}\n\nSee codex-stdout.jsonl and codex-stderr.txt.\n`);
  return {...result, exitCode, acceptanceError};
}

function runCodex(resumePacket) {
  const prompt = [
    'You are executing a Command Center durable worker session.',
    'Use codex-resume-packet.json in the current workspace as the durable context.',
    'Produce a concise final report and do not expose secrets.',
    '',
    resumePacket.activation?.task?.prompt || '',
  ].join('\n');
  return runCodexPrompt(prompt, {nonce: expectedNonce(resumePacket)});
}

async function streamEvent(jobIdValue, type, summary, data = {}) {
  try {
    await workerEvent(jobIdValue, type, summary, data);
  } catch (err) {
    const line = JSON.stringify({type: 'stream_event_failed', eventType: type, error: redact(err.message || String(err))}) + '\n';
    fs.appendFileSync(path.join(workspaceRoot, 'worker-stream-errors.jsonl'), line);
  }
}

function runStreamingProcess(command, args, options = {}) {
  return new Promise((resolve) => {
    const cwd = options.cwd || workspaceRoot;
    const proc = spawn(command, args, {
      cwd,
      env: {...process.env, ...(options.env || {})},
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    const startedAt = Date.now();
    if (options.stdin) {
      proc.stdin.write(options.stdin);
      proc.stdin.end();
    }
    const onData = (streamName, chunk) => {
      const text = redact(chunk.toString('utf8'));
      if (streamName === 'stdout') stdout += text;
      else stderr += text;
      if (options.transcriptPath) {
        fs.appendFileSync(path.join(workspaceRoot, `${streamName}-${options.transcriptPath}`), text);
      }
      if (options.onChunk) {
        options.onChunk(streamName, text, {pid: proc.pid || 0, elapsedMs: Date.now() - startedAt});
      }
    };
    proc.stdout.on('data', (chunk) => onData('stdout', chunk));
    proc.stderr.on('data', (chunk) => onData('stderr', chunk));
    proc.on('error', (err) => {
      stderr += redact(err.message || String(err));
    });
    proc.on('close', (code, signal) => {
      resolve({
        command: [command, ...args].join(' '),
        cwd,
        exitCode: code ?? 1,
        signal: signal || '',
        stdout,
        stderr,
        pid: proc.pid || 0,
        elapsedMs: Date.now() - startedAt,
      });
    });
  });
}

async function runCodexPromptStreaming(prompt, options = {}) {
  if (env.COMMAND_CENTER_CODEX_EXECUTOR_DRY_RUN === '1') {
    const report = 'Dry-run durable Cloud Run Debian worker completed without invoking Codex.';
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\n${report}\n`);
    return {exitCode: 0, stdout: report, stderr: '', command: 'dry-run'};
  }
  fs.mkdirSync(codexHome, {recursive: true});
  const login = run('sh -lc \'printf %s "$OPENAI_API_KEY" | codex login --with-api-key\'', workspaceRoot, {env: {CODEX_HOME: codexHome}});
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stdout.txt'), login.stdout);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stderr.txt'), login.stderr);
  if (login.exitCode !== 0) {
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\nCodex login failed with exit code ${login.exitCode}.\n\nSee codex-login-stderr.txt.\n`);
    return login;
  }
  fs.writeFileSync(path.join(workspaceRoot, 'codex-prompt.md'), prompt);
  fs.writeFileSync(path.join(workspaceRoot, 'stdout-transcript.txt'), '');
  fs.writeFileSync(path.join(workspaceRoot, 'stderr-transcript.txt'), '');
  const jobIdValue = options.jobIdValue || jobId;
  const executorId = options.executorId || '';
  const outputLastMessage = path.join(workspaceRoot, 'codex-last-message.md');
  const result = await runStreamingProcess('codex', [
    'exec',
    '--json',
    '--skip-git-repo-check',
    '--dangerously-bypass-approvals-and-sandbox',
    '--output-last-message',
    outputLastMessage,
    '-',
  ], {
    cwd: workspaceRoot,
    env: {CODEX_HOME: codexHome},
    stdin: prompt,
    transcriptPath: 'transcript.txt',
    onChunk: (streamName, text, meta) => {
      const eventType = streamName === 'stdout' ? 'executor_stdout' : 'executor_stderr';
      void streamEvent(jobIdValue, eventType, `Codex ${streamName} stream chunk.`, {
        executorId,
        pid: meta.pid,
        elapsedMs: meta.elapsedMs,
        chars: text.length,
        text: text.slice(-4000),
      });
    },
  });
  fs.writeFileSync(path.join(workspaceRoot, 'codex-stdout.jsonl'), result.stdout);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-stderr.txt'), result.stderr);
  const nonce = options.nonce || '';
  const helloPath = path.join(workspaceRoot, 'hello-world.txt');
  const helloText = fs.existsSync(helloPath) ? fs.readFileSync(helloPath, 'utf8').trim() : '';
  const acceptanceError = nonce && helloText !== nonce ? `Acceptance failed: hello-world.txt was ${helloText ? 'present with unexpected content' : 'not created'}. Expected ${nonce}.` : '';
  const exitCode = result.exitCode === 0 && acceptanceError ? 70 : result.exitCode;
  fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\nExit code: ${exitCode}\n\n${acceptanceError || 'Worker acceptance checks passed.'}\n\nSee codex-stdout.jsonl, codex-stderr.txt, stdout-transcript.txt, and stderr-transcript.txt.\n`);
  return {...result, exitCode, acceptanceError};
}

function jobPrompt(packet, restore) {
  const job = packet.job || {};
  return [
    'You are executing a Command Center one-shot repository job in a real Cloud Run Debian worker.',
    'This is not an activation smoke test. Do not complete a bounded no-op.',
    'Read job-intake.json before changing files.',
    'Follow repository truth first: inspect orientation docs, tests, package scripts, and existing parser/state conventions.',
    'If the job asks for red tests, add or run the red test before implementing the fix and preserve evidence in final-report.md.',
    'When mutation policy allows commit/PR, create a focused branch, commit, push, and open a draft PR if credentials and tools allow it.',
    'Do not merge. Do not expose secrets.',
    '',
    `Workspace restore: ${JSON.stringify(restore)}`,
    '',
    `Title: ${job.title || ''}`,
    '',
    `Objective:\n${job.objective || ''}`,
    '',
    `Acceptance criteria:\n${(job.acceptanceCriteria || []).map((item) => `- ${item}`).join('\n')}`,
    '',
    `Constraints:\n${(job.constraints || []).map((item) => `- ${item}`).join('\n')}`,
    '',
    `Budget policy:\n${JSON.stringify(job.budgetPolicy || {budgetClass: job.budgetClass || 'small'}, null, 2)}`,
    '',
    `Authentication meter:\n${JSON.stringify(job.authMeter || {openAiAuthMode: 'unknown', credentialExposed: false}, null, 2)}`,
    '',
    'If token usage crosses a warning or approval threshold, finish the current safe turn when possible, checkpoint evidence, and do not start a retry or follow-up yourself.',
    '',
    `Verification commands requested:\n${(job.verificationCommands || []).map((item) => `- ${item}`).join('\n')}`,
    '',
    'Required final artifacts are generated by the worker after Codex exits: implementation.patch, changed-files.json, verification.json, command-log.jsonl, final-report.md, mutation-requests.jsonl, and job-intake.json.',
  ].join('\n');
}

function fileSha256(file) {
  if (!fs.existsSync(file)) return '';
  return createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function readFileIfExists(rel) {
  const file = path.join(workspaceRoot, rel);
  return fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
}

function writeJsonFile(rel, value) {
  writeText(rel, JSON.stringify(value, null, 2) + '\n');
}

function appendCommandLog(entries) {
  writeText('command-log.jsonl', entries.map((entry) => JSON.stringify({
    ...entry,
    stdout: redact(entry.stdout || ''),
    stderr: redact(entry.stderr || ''),
  })).join('\n') + '\n');
}

function runVerificationCommands(commands = []) {
  const results = [];
  for (const command of commands.slice(0, 12)) {
    if (!command || /^run repository-defined /i.test(command)) continue;
    const result = run(command, workspaceRoot);
    results.push({...result, ranAt: new Date().toISOString()});
  }
  return results;
}

function isMutationTicket(job = {}) {
  const text = stripNegativeMutationLanguage([
    job.objective || '',
    ...(job.acceptanceCriteria || []),
  ].join('\n'));
  return /fix|repair|implement|add red|red test|patch|changed-file|commit|push|pull request|\bPR\b|draft PR|build|readback/i.test(text);
}

function requiresPullRequest(job = {}) {
  const text = stripNegativeMutationLanguage([
    job.objective || '',
    ...(job.acceptanceCriteria || []),
  ].join('\n'));
  return /pull request|\bPR\b|draft PR|push/i.test(text);
}

function stripNegativeMutationLanguage(text) {
  return String(text || '')
    .replace(/\b(do not|don't|no|without|must not)\b[^.\n;]*(commit|push|pull request|\bPR\b|draft PR|deploy|deployment|external mutation|external provider)[^.\n;]*/gi, '')
    .replace(/\b(no|without)\s+(GitHub mutation|Drive mutation|deployment mutation|worker-registration|project-registration mutation|external mutations?)[^.\n;]*/gi, '');
}

function parseCodexUsageSummary(text, job = {}, authMeter = {}) {
  const source = String(text || '');
  const pick = (patterns) => {
    for (const pattern of patterns) {
      const match = source.match(pattern);
      if (match) return Number(String(match[1]).replace(/,/g, '')) || 0;
    }
    return 0;
  };
  const inputTokens = pick([/\binput tokens?\D+([0-9][0-9,]*)/i, /\binput_tokens["'\s:]+([0-9][0-9,]*)/i]);
  const cachedInputTokens = pick([/\bcached input tokens?\D+([0-9][0-9,]*)/i, /\bcached_input_tokens["'\s:]+([0-9][0-9,]*)/i]);
  const outputTokens = pick([/\boutput tokens?\D+([0-9][0-9,]*)/i, /\boutput_tokens["'\s:]+([0-9][0-9,]*)/i]);
  return evaluateBudgetUsage({
    inputTokens,
    cachedInputTokens,
    outputTokens,
    warnings: inputTokens > 500000 ? [`High Codex input token usage: ${inputTokens}.`] : [],
  }, job, authMeter);
}

function buildAcceptanceMatrix(job, acceptance, verificationResults, gitEvidence) {
  const criteria = Array.isArray(job.acceptanceCriteria) ? job.acceptanceCriteria : [];
  if (!criteria.length) return [];
  const refsForCriterion = (text) => {
    if (/nonce|hello-world|hello world|file contains|output/i.test(text)) {
      return ['pulse-proof.json', 'verification.json', 'stdout-transcript.txt', 'final-report.md'];
    }
    if (/worker|non-simulated|cloud run|executor|pid|identity|start|finish|heartbeat|stdout|stderr|stream/i.test(text)) {
      return ['job-intake.json', 'command-log.jsonl', 'stdout-transcript.txt', 'stderr-transcript.txt'];
    }
    if (/acceptance[- ]matrix|criterion|criteria/i.test(text)) {
      return ['acceptance-matrix.json'];
    }
    if (/usage|token|cost/i.test(text)) {
      return ['usage-summary.json'];
    }
    if (/artifact|hash|sha256|workspace|cloud-readable|object/i.test(text)) {
      return ['changed-files.json', 'verification.json', 'final-report.md'];
    }
    if (/test|verification|build|smoke/i.test(text)) {
      return ['verification.json', 'command-log.jsonl'];
    }
    if (/patch|diff|change|implement|fix|commit/i.test(text)) {
      return ['implementation.patch', 'changed-files.json'];
    }
    if (/pull request|\bPR\b|push/i.test(text)) {
      return ['final-report.md'];
    }
    return ['acceptance.json'];
  };
  return criteria.map((criterion) => {
    const text = String(criterion || '');
    let status = acceptance.accepted ? 'not_evaluated' : 'manual_review_required';
    const notes = [];
    const evidenceRefs = refsForCriterion(text);
    if (/nonce|hello-world|hello world|file contains|output/i.test(text)) {
      status = acceptance.accepted ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Nonce-bearing output is covered by verification and final report evidence.' : 'Nonce output was missing or invalid.');
    } else if (/test|verification|build|smoke/i.test(text)) {
      status = verificationResults.every((result) => result.exitCode === 0) ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Verification commands passed.' : 'One or more verification commands failed.');
    } else if (/worker|non-simulated|cloud run|executor|pid|identity|start|finish|heartbeat|stdout|stderr|stream/i.test(text)) {
      status = acceptance.accepted ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Executor lifecycle evidence is recorded in worker events and transcripts.' : 'Executor lifecycle evidence did not satisfy acceptance.');
    } else if (/acceptance[- ]matrix|criterion|criteria/i.test(text)) {
      status = acceptance.accepted ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Criterion-level acceptance matrix was emitted.' : 'Acceptance matrix was not sufficient.');
    } else if (/usage|token|cost/i.test(text)) {
      status = acceptance.accepted ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Usage summary artifact was emitted.' : 'Usage summary artifact was not sufficient.');
    } else if (/artifact|hash|sha256|workspace|cloud-readable|object/i.test(text)) {
      status = acceptance.accepted ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Workspace artifact metadata and hashes were recorded.' : 'Workspace artifact evidence was not sufficient.');
    } else if (/patch|diff|change|implement|fix|commit/i.test(text)) {
      status = gitEvidence.diffHasContent || gitEvidence.newCommitCreated ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Repository mutation evidence exists.' : 'No diff or new commit was produced.');
    } else if (/pull request|\bPR\b|push/i.test(text)) {
      const transcript = [readFileIfExists('codex-last-message.md'), readFileIfExists('final-report.md')].join('\n');
      status = /https:\/\/github\.com\/[^\s)]+\/pull\/\d+/i.test(transcript) ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Pull request URL was found in worker report.' : 'No pull request URL was found in worker report.');
    } else if (!acceptance.accepted) {
      notes.push('Overall acceptance failed; this criterion needs reviewer judgment.');
    } else {
      notes.push('No deterministic evidence rule matched this criterion; reviewer judgment is required.');
    }
    return {criterion: text, status, evidenceRefs, notes: notes.join(' '), blockingReason: status === 'failed' || status === 'not_evaluated' ? (status === 'not_evaluated' ? 'manual review required' : acceptance.failures.join('; ')) : ''};
  });
}

function assessJobAcceptance(packet, codex, verificationResults, gitEvidence, authMeter = {}) {
  const job = packet.job || {};
  const transcript = [
    codex.stdout || '',
    codex.stderr || '',
    readFileIfExists('codex-last-message.md'),
    readFileIfExists('final-report.md'),
  ].join('\n');
  const failures = [];
  if (codex.exitCode !== 0) failures.push(`Codex exited ${codex.exitCode}.`);
  if (codex.acceptanceError) failures.push(codex.acceptanceError);
  for (const result of verificationResults) {
    if (result.exitCode !== 0) failures.push(`Verification failed: ${result.command} exited ${result.exitCode}.`);
  }
  if (/blocked by|blocked:|cannot push|cannot open|invalid\s+GH_TOKEN|token .*invalid|authentication failed|auth status.*failed/i.test(transcript)) {
    failures.push('Codex reported a blocker or authentication failure instead of completing the mutation.');
  }
  if (isMutationTicket(job) && !gitEvidence.diffHasContent && !gitEvidence.newCommitCreated) {
    failures.push('Mutation ticket produced no uncommitted diff and no new commit relative to the restored base commit.');
  }
  if (requiresPullRequest(job) && !/https:\/\/github\.com\/[^\s)]+\/pull\/\d+/i.test(transcript)) {
    failures.push('Ticket required push/PR evidence but no GitHub pull request URL was produced.');
  }
  const accepted = failures.length === 0;
  const usageSummary = parseCodexUsageSummary(transcript, job, authMeter);
  const result = {accepted, failures};
  const acceptanceMatrix = buildAcceptanceMatrix(job, result, verificationResults, gitEvidence);
  writeJsonFile('acceptance.json', {
    accepted,
    failures,
    mutationTicket: isMutationTicket(job),
    requiresPullRequest: requiresPullRequest(job),
    gitEvidence,
    codexExitCode: codex.exitCode,
    verificationPassed: verificationResults.every((result) => result.exitCode === 0),
    usageSummary,
  });
  writeJsonFile('acceptance-matrix.json', {
    statusPolicy: 'Every job acceptance criterion receives an explicit worker verdict when criteria are present.',
    criteria: acceptanceMatrix,
    usageSummary,
  });
  writeJsonFile('usage-summary.json', usageSummary);
  return {accepted, failures, acceptanceMatrix, usageSummary};
}

function captureRepositoryArtifacts(packet, codex, restore, verificationResults, baseCommit = '') {
  const status = run('git status --short', workspaceRoot);
  const diff = run('git diff --binary', workspaceRoot);
  const show = run('git show --stat --patch --max-count=1 --format=fuller', workspaceRoot);
  const branch = run('git branch --show-current', workspaceRoot);
  const remote = run('git remote -v', workspaceRoot);
  const head = run('git rev-parse HEAD', workspaceRoot).stdout.trim();
  const changedFiles = status.stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const diffHasContent = Boolean(diff.stdout.trim());
  const newCommitCreated = Boolean(baseCommit && head && head !== baseCommit);
  const patchText = diffHasContent ? diff.stdout : (newCommitCreated ? show.stdout : '');
  writeText('implementation.patch', patchText || 'No implementation patch was produced.\n');
  writeJsonFile('changed-files.json', {
    changedFiles,
    gitStatus: status.stdout,
    currentBranch: branch.stdout.trim(),
    baseCommit,
    headCommit: head,
    newCommitCreated,
    latestCommit: run('git log -1 --oneline', workspaceRoot).stdout.trim(),
    remote: remote.stdout,
  });
  writeJsonFile('verification.json', {
    codexExitCode: codex.exitCode,
    codexAcceptanceError: codex.acceptanceError || '',
    verificationResults: verificationResults.map((item) => ({command: item.command, exitCode: item.exitCode, stdoutTail: item.stdout.slice(-4000), stderrTail: item.stderr.slice(-4000)})),
    allVerificationPassed: verificationResults.every((item) => item.exitCode === 0),
  });
  writeText('reasoning-summary.md', readFileIfExists('codex-last-message.md') || `Codex exit code: ${codex.exitCode}\n`);
  writeText('orientation.md', [
    '# Worker Orientation',
    '',
    `Restore: ${JSON.stringify(restore)}`,
    `Repository: ${repositoryFromJob(packet.job || {}) || 'unknown'}`,
    `Branch: ${branch.stdout.trim()}`,
    '',
    'The worker restored the repository workspace and invoked real Codex against job-intake.json.',
  ].join('\n') + '\n');
  writeText('mutation-requests.jsonl', JSON.stringify({mutationPolicy: packet.job?.mutationPolicy || {}, note: 'Consequential merge/deploy/destructive actions require separate authorization.'}) + '\n');
  return {changedFiles, diffHasContent, newCommitCreated, baseCommit, headCommit: head, branch: branch.stdout.trim()};
}

function artifactFor(rel, kind, required = true, summary = '') {
  const file = path.join(workspaceRoot, rel);
  return {
    name: rel,
    kind,
    uri: file,
    workspacePath: rel,
    origin: 'executor_workspace',
    required,
    sha256: fileSha256(file),
    summary,
  };
}

function uploadSnapshot(sessionId, activationIdValue) {
  required('COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET', snapshotBucket);
  const archive = path.join(os.tmpdir(), `${activationIdValue}-workspace.tgz`);
  const ref = `gs://${snapshotBucket}/sessions/${sessionId}/${activationIdValue}/workspace.tgz`;
  const tar = run(`tar -czf ${JSON.stringify(archive)} -C ${JSON.stringify(workspaceRoot)} .`, '/');
  if (tar.exitCode !== 0) throw new Error(`workspace snapshot pack failed: ${tar.stderr || tar.stdout}`);
  const copy = run(`gcloud storage cp ${JSON.stringify(archive)} ${JSON.stringify(ref)}`, '/');
  if (copy.exitCode !== 0) throw new Error(`workspace snapshot upload failed: ${copy.stderr || copy.stdout}`);
  return ref;
}


function writeText(rel, body) {
  const file = path.join(workspaceRoot, rel);
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, body);
  return file;
}

async function workerEvent(jobIdValue, type, summary, data = {}) {
  return post('/worker/events', {jobId: jobIdValue, type, summary, data});
}

function executionModeFromJob(job = {}) {
  const mode = String(job.executionMode || 'one_shot');
  return ['one_shot', 'executor_pulse', 'codex_smoke'].includes(mode) ? mode : 'one_shot';
}

function nonceFromJob(job = {}, prefix = 'nonce') {
  const text = [job.objective || '', job.title || '', ...(job.acceptanceCriteria || [])].join('\n');
  const explicit = text.match(/\b(?:nonce|marker)\s*[:=]\s*([A-Za-z0-9_.:-]{6,120})/i);
  if (explicit) return explicit[1].replace(/[.。,:;!?]+$/g, '');
  return `${prefix}_${String(job.jobId || jobId).replace(/[^A-Za-z0-9_-]/g, '').slice(-16)}`;
}

function writeAcceptanceArtifacts(job, acceptance, verificationResults = [], gitEvidence = {}, authMeter = {}) {
  const usageSummary = acceptance.usageSummary || evaluateBudgetUsage({inputTokens: 0, cachedInputTokens: 0, outputTokens: 0, warnings: []}, job, authMeter);
  const matrix = buildAcceptanceMatrix(job, acceptance, verificationResults, gitEvidence);
  writeJsonFile('acceptance.json', {
    accepted: acceptance.accepted,
    failures: acceptance.failures || [],
    mutationTicket: false,
    requiresPullRequest: false,
    gitEvidence,
    verificationPassed: verificationResults.every((result) => result.exitCode === 0),
    usageSummary,
  });
  writeJsonFile('acceptance-matrix.json', {
    statusPolicy: 'Every job acceptance criterion receives an explicit worker verdict when criteria are present.',
    criteria: matrix,
    usageSummary,
  });
  writeJsonFile('usage-summary.json', usageSummary);
  return {acceptanceMatrix: matrix, usageSummary};
}

async function runExecutorPulseJob(packet, executorId) {
  const startedAtMs = Date.now();
  const job = packet.job || {};
  const authMeter = {openAiAuthMode: detectOpenAiAuthMode(), source: 'worker_runtime', credentialExposed: false};
  const jobIdValue = job.jobId || jobId;
  const nonce = nonceFromJob(job, 'pulse');
  writeText('job-intake.json', JSON.stringify(packet, null, 2) + '\n');
  await workerEvent(jobIdValue, 'executor_started', 'Cloud Run Debian worker started deterministic executor pulse mode.', {executorId, executionMode: 'executor_pulse', pid: process.pid});
  await workerEvent(jobIdValue, 'executor_heartbeat', 'Cloud Run Debian worker pulse heartbeat.', {executorId, phase: 'executor_pulse'});
  const stdout = `executor_pulse ${nonce}\n`;
  writeText('stdout-transcript.txt', stdout);
  appendCommandLog([{command: 'executor_pulse', exitCode: 0, stdout, stderr: ''}]);
  await workerEvent(jobIdValue, 'executor_stdout', 'Executor pulse stdout stream chunk.', {executorId, pid: process.pid, text: stdout.trim(), chars: stdout.length});
  const proof = {jobId: jobIdValue, nonce, executorId, pid: process.pid, executionMode: 'executor_pulse', generatedAt: new Date().toISOString()};
  writeJsonFile('pulse-proof.json', proof);
  writeJsonFile('verification.json', {
    allVerificationPassed: true,
    verificationResults: [{command: 'executor_pulse', exitCode: 0, stdoutTail: stdout, stderrTail: ''}],
    nonce,
  });
  const gitEvidence = {changedFiles: [], diffHasContent: false, newCommitCreated: false, baseCommit: '', headCommit: '', branch: ''};
  const acceptance = {accepted: true, failures: [], usageSummary: evaluateBudgetUsage({inputTokens: 0, cachedInputTokens: 0, outputTokens: 0, warnings: []}, job, authMeter)};
  acceptance.usageSummary.elapsedMs = Date.now() - startedAtMs;
  acceptance.usageSummary = evaluateBudgetUsage(acceptance.usageSummary, job, authMeter);
  const review = writeAcceptanceArtifacts(job, acceptance, [{command: 'executor_pulse', exitCode: 0, stdout, stderr: ''}], gitEvidence, authMeter);
  const finalReport = `# Final Report\n\nExecutor pulse completed without invoking Codex.\n\nNonce: ${nonce}\n`;
  writeText('final-report.md', finalReport);
  const artifacts = [
    artifactFor('job-intake.json', 'job_intake', true, 'Job packet claimed by Cloud Run worker.'),
    artifactFor('pulse-proof.json', 'pulse_proof', true, 'Deterministic no-model executor pulse proof.'),
    artifactFor('stdout-transcript.txt', 'stdout_transcript', true, 'Nonce-bearing executor pulse stdout transcript.'),
    artifactFor('command-log.jsonl', 'command_log', true, 'Executor pulse command transcript.'),
    artifactFor('acceptance.json', 'acceptance', true, 'Pulse acceptance verdict.'),
    artifactFor('acceptance-matrix.json', 'acceptance_matrix', true, 'Criterion-level pulse acceptance verdicts.'),
    artifactFor('usage-summary.json', 'usage_summary', true, 'Zero-token usage summary for pulse mode.'),
    artifactFor('verification.json', 'verification', true, 'Pulse verification results.'),
    artifactFor('final-report.md', 'final_report', true, 'Pulse final report.'),
  ];
  await post('/worker/artifacts', {jobId: jobIdValue, artifacts});
  await post('/worker/checkpoint', {
    jobId: jobIdValue,
    currentPhase: 'completed_executor_pulse',
    decisionsMade: ['Claimed a specific Command Center job by COMMAND_CENTER_JOB_ID.', 'Ran deterministic executor pulse without Codex.'],
    testsRun: ['worker lease', 'executor events', 'artifact record', 'checkpoint write', 'executor_pulse -> 0'],
    evidenceRefs: artifacts.map((artifact) => artifact.workspacePath),
    acceptanceCriteriaStatus: review.acceptanceMatrix,
    usageSummary: review.usageSummary,
    authMeter,
    failedApproaches: [],
    nextAction: 'Use this as a cheap executor heartbeat. Run Codex smoke only after deployment or worker-image changes.',
  });
  await workerEvent(jobIdValue, 'executor_finished', 'Cloud Run Debian worker finished deterministic executor pulse mode.', {executorId, artifactCount: artifacts.length});
  await post('/worker/complete', {jobId: jobIdValue, status: 'completed', finalReport, artifacts: []});
}

async function runCodexSmokeJob(packet, executorId) {
  const startedAtMs = Date.now();
  const job = packet.job || {};
  const authMeter = {openAiAuthMode: detectOpenAiAuthMode(), source: 'worker_runtime', credentialExposed: false};
  const jobIdValue = job.jobId || jobId;
  const nonce = nonceFromJob(job, 'codex_smoke');
  writeText('job-intake.json', JSON.stringify(packet, null, 2) + '\n');
  writeText('SESSION.md', '# Command Center Codex smoke workspace\n');
  await workerEvent(jobIdValue, 'executor_started', 'Cloud Run Debian worker started repo-less Codex smoke mode.', {executorId, executionMode: 'codex_smoke', pid: process.pid});
  await workerEvent(jobIdValue, 'executor_heartbeat', 'Cloud Run Debian worker invoking Codex smoke prompt.', {executorId, phase: 'codex_smoke'});
  const prompt = [
    'You are executing a tiny Command Center Codex smoke in an empty prepared workspace.',
    'Do not inspect or clone any repository.',
    `Write exactly this nonce to hello-world.txt: ${nonce}`,
    'Then finish with a concise final message.',
  ].join('\n');
  const codex = await runCodexPromptStreaming(prompt, {jobIdValue, executorId, nonce});
  await workerEvent(jobIdValue, 'executor_heartbeat', 'Cloud Run Debian worker verifying Codex smoke output.', {executorId, phase: 'verification'});
  const verificationResults = runVerificationCommands(job.verificationCommands?.length ? job.verificationCommands : ['cat hello-world.txt']);
  appendCommandLog([{command: 'codex exec smoke', exitCode: codex.exitCode, stdout: codex.stdout, stderr: codex.stderr}, ...verificationResults]);
  writeJsonFile('verification.json', {
    codexExitCode: codex.exitCode,
    codexAcceptanceError: codex.acceptanceError || '',
    verificationResults: verificationResults.map((item) => ({command: item.command, exitCode: item.exitCode, stdoutTail: item.stdout.slice(-4000), stderrTail: item.stderr.slice(-4000)})),
    allVerificationPassed: verificationResults.every((item) => item.exitCode === 0),
    nonce,
  });
  const failures = [];
  if (codex.exitCode !== 0) failures.push(`Codex exited ${codex.exitCode}.`);
  if (codex.acceptanceError) failures.push(codex.acceptanceError);
  for (const result of verificationResults) {
    if (result.exitCode !== 0) failures.push(`Verification failed: ${result.command} exited ${result.exitCode}.`);
  }
  const acceptance = {accepted: failures.length === 0, failures, usageSummary: parseCodexUsageSummary([codex.stdout, codex.stderr, readFileIfExists('final-report.md')].join('\n'), job, authMeter)};
  acceptance.usageSummary.elapsedMs = Date.now() - startedAtMs;
  acceptance.usageSummary = evaluateBudgetUsage(acceptance.usageSummary, job, authMeter);
  const gitEvidence = {changedFiles: ['hello-world.txt'], diffHasContent: false, newCommitCreated: false, baseCommit: '', headCommit: '', branch: ''};
  const review = writeAcceptanceArtifacts(job, acceptance, verificationResults, gitEvidence, authMeter);
  const status = acceptance.accepted ? 'completed' : 'failed';
  const finalReport = `${readFileIfExists('final-report.md').trim()}\n\n## Command Center Smoke\n\nNonce: ${nonce}\nStatus: ${status}\n`;
  writeText('final-report.md', finalReport);
  const artifacts = [
    artifactFor('job-intake.json', 'job_intake', true, 'Codex smoke job packet claimed by Cloud Run worker.'),
    artifactFor('stdout-transcript.txt', 'stdout_transcript', true, 'Streamed Codex stdout transcript.'),
    artifactFor('stderr-transcript.txt', 'stderr_transcript', true, 'Streamed Codex stderr transcript.'),
    artifactFor('command-log.jsonl', 'command_log', true, 'Codex smoke and verification command transcript.'),
    artifactFor('acceptance.json', 'acceptance', true, 'Codex smoke acceptance verdict.'),
    artifactFor('acceptance-matrix.json', 'acceptance_matrix', true, 'Criterion-level Codex smoke acceptance verdicts.'),
    artifactFor('usage-summary.json', 'usage_summary', true, 'Codex smoke token usage summary.'),
    artifactFor('verification.json', 'verification', true, 'Codex smoke verification results.'),
    artifactFor('final-report.md', 'final_report', true, 'Codex smoke final report.'),
  ];
  await post('/worker/artifacts', {jobId: jobIdValue, artifacts});
  await post('/worker/checkpoint', {
    jobId: jobIdValue,
    currentPhase: status === 'completed' ? 'completed_codex_smoke' : 'failed_codex_smoke',
    decisionsMade: ['Claimed a specific Command Center job by COMMAND_CENTER_JOB_ID.', 'Invoked real Codex in an empty prepared workspace.', 'Verified nonce-bearing hello-world.txt.'],
    testsRun: ['worker lease', 'executor events', 'artifact record', 'checkpoint write', ...verificationResults.map((result) => `${result.command} -> ${result.exitCode}`)],
    evidenceRefs: artifacts.map((artifact) => artifact.workspacePath),
    acceptanceCriteriaStatus: review.acceptanceMatrix,
    usageSummary: review.usageSummary,
    authMeter,
    failedApproaches: acceptance.failures,
    nextAction: status === 'completed' ? 'Use full repository acceptance only for consequential releases.' : 'Fix the reported smoke failures before running full repository acceptance.',
  });
  await workerEvent(jobIdValue, status === 'completed' ? 'executor_finished' : 'executor_failed', 'Cloud Run Debian worker finished repo-less Codex smoke mode.', {executorId, artifactCount: artifacts.length, codexExitCode: codex.exitCode, acceptanceFailures: acceptance.failures});
  await post('/worker/complete', {jobId: jobIdValue, status, finalReport, artifacts: []});
}

async function runOneShotJob() {
  const startedAtMs = Date.now();
  required('COMMAND_CENTER_WORKER_TOKEN', workerToken);
  required('COMMAND_CENTER_JOB_ID', jobId);
  ensureWorkspace();
  const executorId = `${os.hostname() || 'cloud-run'}:${process.env.CLOUD_RUN_EXECUTION || process.pid}`;
  const authMeter = {openAiAuthMode: detectOpenAiAuthMode(), source: 'worker_runtime', credentialExposed: false};
  const leased = await post('/worker/lease', {jobId, executorId, openAiAuthMode: authMeter.openAiAuthMode});
  if (!leased.leased) throw new Error(`job was not leased to this worker: ${jobId}`);
  const packet = leased.packet || {};
  const job = packet.job || {};
  const executionMode = executionModeFromJob(job);
  if (executionMode === 'executor_pulse') {
    await runExecutorPulseJob(packet, executorId);
    return;
  }
  if (executionMode === 'codex_smoke') {
    await runCodexSmokeJob(packet, executorId);
    return;
  }
  await workerEvent(job.jobId || jobId, 'executor_started', 'Cloud Run Debian worker started real one-shot Codex job mode.', {executorId, objective: job.objective || ''});
  await workerEvent(job.jobId || jobId, 'executor_heartbeat', 'Cloud Run Debian worker restoring repository workspace.', {executorId, phase: 'restore_repository'});
  const restore = restoreJobWorkspace(job);
  const baseCommit = run('git rev-parse HEAD', workspaceRoot).stdout.trim();
  writeText('job-intake.json', JSON.stringify(packet, null, 2) + '\n');
  await workerEvent(job.jobId || jobId, 'executor_heartbeat', 'Cloud Run Debian worker invoking real Codex executor.', {executorId, phase: 'codex_execution', restore});
  writeText('codex-prompt.md', jobPrompt(packet, restore));
  const codex = await runCodexPromptStreaming(readFileIfExists('codex-prompt.md'), {jobIdValue: job.jobId || jobId, executorId});
  await workerEvent(job.jobId || jobId, 'executor_heartbeat', 'Cloud Run Debian worker running requested verification commands.', {executorId, phase: 'verification'});
  const verificationResults = runVerificationCommands(job.verificationCommands || []);
  appendCommandLog([
    {command: 'codex exec', exitCode: codex.exitCode, stdout: codex.stdout, stderr: codex.stderr},
    ...verificationResults,
  ]);
  const gitEvidence = captureRepositoryArtifacts(packet, codex, restore, verificationResults, baseCommit);
  const acceptance = assessJobAcceptance(packet, codex, verificationResults, gitEvidence, authMeter);
  acceptance.usageSummary.elapsedMs = Date.now() - startedAtMs;
  acceptance.usageSummary = evaluateBudgetUsage(acceptance.usageSummary, job, authMeter);
  const status = acceptance.accepted ? 'completed' : 'failed';
  const codexFinalMessage = readFileIfExists('codex-last-message.md').trim();
  const existingFinalReport = readFileIfExists('final-report.md').trim();
  const baseFinalReport = [
    '# Final Report',
    '',
    codexFinalMessage || existingFinalReport || `Codex exit code: ${codex.exitCode}`,
    '',
    `Codex exit code: ${codex.exitCode}`,
  ].join('\n') + '\n';
  const finalReport = acceptance.accepted ? baseFinalReport : `${baseFinalReport}\n\n## Command Center Acceptance Failures\n\n${acceptance.failures.map((failure) => `- ${failure}`).join('\n')}\n`;
  writeText('final-report.md', finalReport);
  const artifacts = [
    artifactFor('job-intake.json', 'job_intake', true, 'One-shot job packet claimed by Cloud Run worker.'),
    artifactFor('orientation.md', 'orientation', true, 'Repository orientation and restore evidence.'),
    artifactFor('reasoning-summary.md', 'reasoning_summary', true, 'Codex final message or execution summary.'),
    artifactFor('command-log.jsonl', 'command_log', true, 'Codex and verification command transcript.'),
    artifactFor('stdout-transcript.txt', 'stdout_transcript', false, 'Streamed Codex stdout transcript.'),
    artifactFor('stderr-transcript.txt', 'stderr_transcript', false, 'Streamed Codex stderr transcript.'),
    artifactFor('acceptance.json', 'acceptance', true, 'Worker-side acceptance verdict for real mutation completion.'),
    artifactFor('acceptance-matrix.json', 'acceptance_matrix', true, 'Criterion-level worker acceptance verdicts.'),
    artifactFor('usage-summary.json', 'usage_summary', false, 'Codex token usage summary parsed from executor output when available.'),
    artifactFor('implementation.patch', 'implementation_patch', true, 'Repository diff or latest commit patch evidence.'),
    artifactFor('changed-files.json', 'changed_files', true, 'Git status, branch, commit, and remote evidence.'),
    artifactFor('verification.json', 'verification', true, 'Verification command results.'),
    artifactFor('mutation-requests.jsonl', 'mutation_requests', true, 'Mutation policy and follow-up authorization notes.'),
    artifactFor('final-report.md', 'final_report', true, 'Cloud Run real Codex final report.'),
  ];
  await post('/worker/artifacts', {jobId: job.jobId || jobId, artifacts});
  await post('/worker/checkpoint', {
    jobId: job.jobId || jobId,
    currentPhase: status === 'completed' ? 'completed_real_codex' : 'failed_real_codex',
    decisionsMade: ['Claimed a specific Command Center job by COMMAND_CENTER_JOB_ID.', 'Restored a repository workspace.', 'Invoked real Codex executor.', 'Captured patch/status/verification artifacts.'],
    testsRun: ['worker lease', 'executor events', 'artifact record', 'checkpoint write', ...verificationResults.map((result) => `${result.command} -> ${result.exitCode}`)],
    evidenceRefs: artifacts.map((artifact) => artifact.workspacePath),
    acceptanceCriteriaStatus: acceptance.acceptanceMatrix,
    usageSummary: acceptance.usageSummary,
    authMeter,
    failedApproaches: acceptance.failures,
    nextAction: status === 'completed' ? 'Inspect job events, logs, artifacts, checkpoint, and completion status.' : 'Fix the reported acceptance failures before claiming real cloud hands completion.',
  });
  await workerEvent(job.jobId || jobId, status === 'completed' ? 'executor_finished' : 'executor_failed', 'Cloud Run Debian worker finished real one-shot Codex job mode.', {executorId, artifactCount: artifacts.length, codexExitCode: codex.exitCode, acceptanceFailures: acceptance.failures});
  await post('/worker/complete', {jobId: job.jobId || jobId, status, finalReport, artifacts: []});
}

async function main() {
  if (jobId) {
    await runOneShotJob();
    return;
  }
  required('COMMAND_CENTER_WORKER_TOKEN', workerToken);
  required('COMMAND_CENTER_ACTIVATION_ID', activationId);
  const claimed = await post('/agent/claim', {activationId});
  if (!claimed.claimed) throw new Error(`activation was not claimed: ${activationId}`);
  const resumePacket = claimed.resumePacket || {};
  const sessionId = resumePacket.session?.sessionId || claimed.activation?.sessionId || activationId;
  const repository = resumePacket.session?.repository || claimed.activation?.repository || env.COMMAND_CENTER_REPOSITORY || '';
  const restoreRef = resumePacket.workspaceSnapshot?.restoreRef || env.COMMAND_CENTER_RESTORE_WORKSPACE_SNAPSHOT_REF || '';
  await post('/agent/heartbeat', {activationId, currentPhase: 'restore_workspace', summary: 'Restoring durable worker session workspace.'});
  const restore = restoreWorkspace(restoreRef, repository);
  writeResumePacket(resumePacket);
  await post('/agent/heartbeat', {activationId, currentPhase: 'codex_execution', summary: `Workspace restored by ${restore.mode}.`});
  const codex = runCodex(resumePacket);
  await post('/agent/artifacts', {activationId, artifact: {name: 'final-report.md', kind: 'final_report', uri: path.join(workspaceRoot, 'final-report.md'), body: fs.readFileSync(path.join(workspaceRoot, 'final-report.md'), 'utf8'), required: true, summary: `Codex exit code ${codex.exitCode}.`}});
  await post('/agent/heartbeat', {activationId, currentPhase: 'snapshot_workspace', summary: 'Uploading next durable workspace snapshot.'});
  const nextRef = uploadSnapshot(sessionId, activationId);
  await post('/agent/complete', {
    activationId,
    status: codex.exitCode === 0 ? 'completed' : 'failed',
    finalSummary: `Cloud Run Debian worker finished with exit code ${codex.exitCode}.`,
    nextWorkspaceSnapshotRef: nextRef,
  });
}

main().catch(async (err) => {
  const message = redact(err && err.stack || err && err.message || String(err)).slice(0, 4000);
  try {
    if (workerToken && activationId && !jobId) await post('/agent/complete', {activationId, status: 'failed', finalSummary: message});
    if (workerToken && jobId) await post('/worker/events', {jobId, type: 'executor_finished', summary: `Cloud Run worker failed: ${message.slice(0, 1000)}`, data: {failed: true}});
  } catch (_) {}
  console.error(message);
  process.exit(1);
});
