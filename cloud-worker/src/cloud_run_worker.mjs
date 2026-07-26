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
const codexBin = env.CODEX_BIN || 'codex';

function required(name, value) {
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function redact(text) {
  return String(text || '')
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]')
    .replace(/\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/g, '[REDACTED_WORKER_TOKEN]')
    .replace(/\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_JWT]')
    .replace(/(OPENAI_API_KEY|CODEX_API_KEY|CODEX_ACCESS_TOKEN|GITHUB_TOKEN|GH_TOKEN)=\\S+/g, '$1=[REDACTED]');
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

function runWithStdin(command, args, stdin, cwd = workspaceRoot, options = {}) {
  const result = spawnSync(command, args, {
    cwd,
    shell: false,
    input: stdin,
    encoding: 'utf8',
    env: {...process.env, ...(options.env || {})},
    maxBuffer: 20 * 1024 * 1024,
    timeout: Number(options.timeoutMs || 120000),
  });
  return {
    command: [command, ...args].join(' '),
    cwd,
    exitCode: result.status ?? (result.signal ? 124 : 1),
    signal: result.signal || '',
    stdout: redact(result.stdout || ''),
    stderr: redact(result.stderr || ''),
    error: result.error ? redact(result.error.message || String(result.error)) : '',
  };
}

function codexAuthCredential() {
  if (env.CODEX_ACCESS_TOKEN) {
    return {mode: 'access_token', envName: 'CODEX_ACCESS_TOKEN', loginArgs: ['login', '--with-access-token'], value: String(env.CODEX_ACCESS_TOKEN || ''), missingFailureKind: 'access_token_missing'};
  }
  return {mode: 'api_key', envName: 'OPENAI_API_KEY', loginArgs: ['login', '--with-api-key'], value: String(env.OPENAI_API_KEY || ''), missingFailureKind: 'secret_missing'};
}

function codexLoginWithConfiguredAuth(timeoutMs = 120000) {
  const auth = codexAuthCredential();
  if (!auth.value) {
    return {auth, result: {exitCode: 1, signal: '', stdout: '', stderr: `${auth.envName} was not present in the Cloud Run worker environment.`, error: ''}};
  }
  return {auth, result: runWithStdin(codexBin, auth.loginArgs, auth.value, workspaceRoot, {env: {CODEX_HOME: codexHome}, timeoutMs})};
}

function codexApiKeyProbe() {
  const checkedAtMs = Date.now();
  const auth = codexAuthCredential();
  if (!auth.value) {
    return {ok: false, status: 'failed', failureKind: auth.missingFailureKind, checkedAtMs, authMode: auth.mode, stage: 'credential', summary: `${auth.envName} was not present in the Cloud Run worker environment.`};
  }
  ensureWorkspace();
  fs.mkdirSync(codexHome, {recursive: true});
  const login = runWithStdin(codexBin, auth.loginArgs, auth.value, workspaceRoot, {env: {CODEX_HOME: codexHome}, timeoutMs: 120000});
  writeText('codex-probe-login-stdout.txt', login.stdout || '');
  writeText('codex-probe-login-stderr.txt', login.stderr || login.error || '');
  if (login.exitCode !== 0) {
    const failure = classifyCodexFailure(`${login.stdout}\n${login.stderr}\n${login.error}`);
    const failureKind = failure.code || (login.signal ? 'codex_login_timeout' : 'codex_login_failed');
    return {ok: false, status: 'failed', failureKind, checkedAtMs, authMode: auth.mode, stage: 'login', exitCode: login.exitCode, signal: login.signal, summary: (failure.message || login.stderr || login.error || login.stdout || `codex ${auth.loginArgs.join(' ')} failed.`).slice(0, 1000), evidenceRefs: ['codex-probe-login-stdout.txt', 'codex-probe-login-stderr.txt']};
  }
  const execProbe = runWithStdin(codexBin, ['exec', '--json', '--skip-git-repo-check', '--dangerously-bypass-approvals-and-sandbox', '-'], 'Reply with exactly COMMAND_CENTER_CODEX_PROBE_OK and do not edit files.\n', workspaceRoot, {env: {CODEX_HOME: codexHome}, timeoutMs: 180000});
  writeText('codex-probe-exec-stdout.jsonl', execProbe.stdout || '');
  writeText('codex-probe-exec-stderr.txt', execProbe.stderr || execProbe.error || '');
  if (execProbe.exitCode === 0 && /COMMAND_CENTER_CODEX_PROBE_OK/.test(`${execProbe.stdout}\n${execProbe.stderr}`)) {
    return {ok: true, status: 'ok', failureKind: '', checkedAtMs, authMode: auth.mode, stage: 'exec', exitCode: 0, summary: `codex exec ${auth.mode} capability probe succeeded.`};
  }
  const failure = classifyCodexFailure(`${execProbe.stdout}\n${execProbe.stderr}\n${execProbe.error}`);
  const failureKind = failure.code || (execProbe.signal ? 'codex_exec_probe_timeout' : 'codex_exec_probe_failed');
  return {ok: false, status: 'failed', failureKind, checkedAtMs, authMode: auth.mode, stage: 'exec', exitCode: execProbe.exitCode, signal: execProbe.signal, summary: (failure.message || execProbe.stderr || execProbe.error || execProbe.stdout || 'codex exec capability probe failed.').slice(0, 1000), evidenceRefs: ['codex-probe-login-stdout.txt', 'codex-probe-login-stderr.txt', 'codex-probe-exec-stdout.jsonl', 'codex-probe-exec-stderr.txt']};
}

async function reportActivationRuntimeProbe(activationIdValue, phase) {
  const probe = codexApiKeyProbe();
  await post('/agent/heartbeat', {
    activationId: activationIdValue,
    currentPhase: phase || 'api_key_probe',
    summary: `Codex capability probe ${probe.status}.`,
    runtime: {codexAuth: probe.authMode || 'api_key', apiKeyCapabilityProbe: probe, codexCapabilityProbe: probe},
  });
  return probe;
}

async function reportJobRuntimeProbe(jobIdValue, phase) {
  const probe = codexApiKeyProbe();
  await post('/worker/heartbeat', {
    jobId: jobIdValue,
    phase: phase || 'api_key_probe',
    runtime: {codexAuth: probe.authMode || 'api_key', apiKeyCapabilityProbe: probe, codexCapabilityProbe: probe},
  });
  return probe;
}

function ensureWorkspace() {
  fs.mkdirSync(workspaceRoot, {recursive: true});
}

function resetWorkspace() {
  const resolved = path.resolve(workspaceRoot);
  if (!resolved || resolved === '/' || resolved === os.homedir() || resolved.length < 8) {
    throw new Error(`refusing to reset unsafe workspace directory: ${workspaceRoot}`);
  }
  fs.rmSync(resolved, {recursive: true, force: true});
  fs.mkdirSync(resolved, {recursive: true});
}

function restoreWorkspace(ref, repository) {
  resetWorkspace();
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
  resetWorkspace();
  fs.writeFileSync(path.join(workspaceRoot, 'SESSION.md'), '# Durable repo-less worker session\n');
  return {mode: 'empty_workspace'};
}

function repositoryFromGithubRef(ref) {
  const text = String(ref || '').trim();
  if (!text || /^(worker-local|gs|file):\/\//i.test(text)) return '';
  let raw = text.split(/[?#]/)[0].replace(/\.git$/i, '');
  if (/^github:\/\//i.test(raw)) raw = raw.replace(/^github:\/\//i, '');
  else if (/^https:\/\/github\.com\//i.test(raw)) raw = raw.replace(/^https:\/\/github\.com\//i, '');
  else if (/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)) return '';
  const parts = raw.split('/').filter(Boolean);
  if (parts.length < 2) return '';
  if (!/^[A-Za-z0-9_.-]+$/.test(parts[0]) || !/^[A-Za-z0-9_.-]+$/.test(parts[1])) return '';
  return `${parts[0]}/${parts[1]}`;
}

function repositoryFromJob(job = {}) {
  const direct = job.repository || job.inputs?.repository || job.baseWorkspace?.repository || env.COMMAND_CENTER_REPOSITORY || '';
  if (direct) return repositoryFromGithubRef(direct);
  const snapshotRef = String(job.baseWorkspace?.snapshotRef || '');
  if (snapshotRef.startsWith('github://') || /^https:\/\/github\.com\//i.test(snapshotRef)) return repositoryFromGithubRef(snapshotRef);
  return '';
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
  const ref = job.baseWorkspace?.snapshotRef || env.COMMAND_CENTER_RESTORE_WORKSPACE_SNAPSHOT_REF || '';
  const repository = repositoryFromJob(job);
  if (ref && ref.startsWith('gs://')) return restoreWorkspace(ref, repository);
  if (ref && ref.startsWith('worker-local://')) {
    resetWorkspace();
    if (repository) throw new Error(`worker-local workspace must not enter GitHub restore logic for ${repository}`);
    fs.writeFileSync(path.join(workspaceRoot, 'SESSION.md'), `# Command Center worker-local session

Source: ${ref}
`);
    return {mode: 'worker_local_empty_workspace', ref};
  }
  if (repository) {
    resetWorkspace();
    const auth = setupGithubAuth(repository);
    if (!auth.configured) throw new Error(`GitHub auth preflight failed for ${repository}: gh=${auth.ghExitCode} git=${auth.gitExitCode} ${auth.ghStderr || auth.gitStderr || auth.reason || ''}`);
    const cloneUrl = `https://github.com/${repository}.git`;
    const clone = run(`git clone ${JSON.stringify(cloneUrl)} ${JSON.stringify(workspaceRoot)}`, '/', {env: {GIT_ASKPASS: auth.askpass, GIT_TERMINAL_PROMPT: '0'}});
    if (clone.exitCode !== 0) throw new Error(`git restore failed: ${clone.stderr || clone.stdout}`);
    return {mode: 'git_clean_clone', repository};
  }
  fs.writeFileSync(path.join(workspaceRoot, 'SESSION.md'), '# Durable repo-less worker session\n');
  return {mode: 'empty_workspace'};
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
  const {auth: codexAuth, result: login} = codexLoginWithConfiguredAuth(120000);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stdout.txt'), login.stdout);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stderr.txt'), login.stderr);
  if (login.exitCode !== 0) {
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\nCodex login using ${codexAuth.mode} failed with exit code ${login.exitCode}.\n\nSee codex-login-stderr.txt.\n`);
    return login;
  }
  fs.writeFileSync(path.join(workspaceRoot, 'codex-prompt.md'), prompt);
  const result = run(`${JSON.stringify(codexBin)} exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox --output-last-message ${JSON.stringify(path.join(workspaceRoot, 'codex-last-message.md'))} - < ${JSON.stringify(path.join(workspaceRoot, 'codex-prompt.md'))}`, workspaceRoot, {env: {CODEX_HOME: codexHome}});
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
  const {auth: codexAuth, result: login} = codexLoginWithConfiguredAuth(120000);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stdout.txt'), login.stdout);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stderr.txt'), login.stderr);
  if (login.exitCode !== 0) {
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\nCodex login using ${codexAuth.mode} failed with exit code ${login.exitCode}.\n\nSee codex-login-stderr.txt.\n`);
    return login;
  }
  fs.writeFileSync(path.join(workspaceRoot, 'codex-prompt.md'), prompt);
  fs.writeFileSync(path.join(workspaceRoot, 'stdout-transcript.txt'), '');
  fs.writeFileSync(path.join(workspaceRoot, 'stderr-transcript.txt'), '');
  const jobIdValue = options.jobIdValue || jobId;
  const executorId = options.executorId || '';
  const outputLastMessage = path.join(workspaceRoot, 'codex-last-message.md');
  const result = await runStreamingProcess(codexBin, [
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
  const text = [
    job.objective || '',
    ...(job.acceptanceCriteria || []),
    ...(job.requiredArtifacts || []),
  ].join('\n');
  return /fix|repair|implement|add red|red test|patch|changed-file|commit|push|pull request|\bPR\b|draft PR|build|readback/i.test(text);
}

function requiresPullRequest(job = {}) {
  const text = [
    job.objective || '',
    ...(job.acceptanceCriteria || []),
    ...(job.requiredArtifacts || []),
    ...(job.constraints || []),
  ].join('\n');
  if (policyDenies(job, ['createPullRequest', 'push'])) return false;
  if (negatesPullRequestRequirement(text)) return false;
  return /(?:open|create|file|publish|produce|provide|include|link|return|require|required|must|should)\s+(?:a\s+)?(?:draft\s+)?(?:pull request|\bPR\b)|(?:pull request|\bPR\b)\s+(?:url|link|evidence|required)|\bpush\b/i.test(text);
}

function policyDenies(job = {}, names = []) {
  const policy = job.mutationPolicy || {};
  return names.some((name) => /^(deny|denied|forbid|forbidden|disallow|disallowed)$/i.test(String(policy[name] || '').trim()));
}

function negatesPullRequestRequirement(text) {
  const source = String(text || '');
  return /(?:do not|don't|must not|never|no)\s+(?:push|open|create|file|publish|produce|provide|include|require)[^\n.]{0,80}(?:pull request|\bPR\b|push)/i.test(source)
    || /(?:pull request|\bPR\b|push)[^\n.]{0,80}(?:forbidden|not required|not allowed|disallowed|denied|must not|do not|don't|never)/i.test(source)
    || /(?:push|PR creation|pull request creation)\s+(?:is\s+)?forbidden/i.test(source)
    || /no\s+github\s+pull\s+request\s+url\s+is\s+required/i.test(source);
}

function classifyCodexFailure(transcript) {
  const source = String(transcript || '');
  if (/quota exceeded|insufficient[_ -]?quota|check your plan and billing details|billing details/i.test(source)) {
    return {
      code: 'worker_openai_quota_exceeded',
      message: 'Cloud Run worker Codex API key quota was exceeded before implementation could run.',
      preMutation: true,
    };
  }
  if (/codex login failed/i.test(source)) {
    return {
      code: 'codex_login_failed',
      message: 'Cloud Run worker could not authenticate Codex before implementation could run.',
      preMutation: true,
    };
  }
  return {code: '', message: '', preMutation: false};
}

function parseCodexUsageSummary(text) {
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
  return {
    inputTokens,
    cachedInputTokens,
    outputTokens,
    cachedInputRatio: inputTokens > 0 ? cachedInputTokens / inputTokens : 0,
    warnings: inputTokens > 500000 ? [`High Codex input token usage: ${inputTokens}.`] : [],
  };
}

function buildAcceptanceMatrix(job, acceptance, verificationResults, gitEvidence) {
  const criteria = Array.isArray(job.acceptanceCriteria) ? job.acceptanceCriteria : [];
  if (!criteria.length) return [];
  const evidenceRefs = ['acceptance.json', 'verification.json', 'changed-files.json', 'implementation.patch', 'final-report.md'];
  return criteria.map((criterion) => {
    const text = String(criterion || '');
    let status = acceptance.accepted ? 'passed' : 'manual_review_required';
    const notes = [];
    if (/test|verification|build|smoke/i.test(text)) {
      status = verificationResults.every((result) => result.exitCode === 0) ? 'passed' : 'failed';
      notes.push(status === 'passed' ? 'Verification commands passed.' : 'One or more verification commands failed.');
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
      notes.push('Overall worker acceptance passed; no narrower deterministic rule matched this criterion.');
    }
    return {criterion: text, status, evidenceRefs, notes: notes.join(' '), blockingReason: status === 'failed' ? acceptance.failures.join('; ') : ''};
  });
}

function assessJobAcceptance(packet, codex, verificationResults, gitEvidence) {
  const job = packet.job || {};
  const transcript = [
    codex.stdout || '',
    codex.stderr || '',
    readFileIfExists('codex-last-message.md'),
    readFileIfExists('final-report.md'),
  ].join('\n');
  const codexFailure = classifyCodexFailure(transcript);
  const failures = [];
  if (codex.exitCode !== 0) failures.push(codexFailure.message || `Codex exited ${codex.exitCode}.`);
  if (codex.acceptanceError) failures.push(codex.acceptanceError);
  for (const result of verificationResults) {
    if (result.exitCode !== 0) failures.push(`Verification failed: ${result.command} exited ${result.exitCode}.`);
  }
  if (!codexFailure.preMutation && /blocked by|blocked:|cannot push|cannot open|invalid\s+GH_TOKEN|token .*invalid|authentication failed|auth status.*failed/i.test(transcript)) {
    failures.push('Codex reported a blocker or authentication failure instead of completing the mutation.');
  }
  if (!codexFailure.preMutation && isMutationTicket(job) && !gitEvidence.diffHasContent && !gitEvidence.newCommitCreated) {
    failures.push('Mutation ticket produced no uncommitted diff and no new commit relative to the restored base commit.');
  }
  if (!codexFailure.preMutation && requiresPullRequest(job) && !/https:\/\/github\.com\/[^\s)]+\/pull\/\d+/i.test(transcript)) {
    failures.push('Ticket required push/PR evidence but no GitHub pull request URL was produced.');
  }
  const accepted = failures.length === 0;
  const usageSummary = parseCodexUsageSummary(transcript);
  const result = {accepted, failures};
  const acceptanceMatrix = buildAcceptanceMatrix(job, result, verificationResults, gitEvidence);
  writeJsonFile('acceptance.json', {
    accepted,
    failures,
    mutationTicket: isMutationTicket(job),
    requiresPullRequest: requiresPullRequest(job),
    gitEvidence,
    codexFailure,
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

function repositoryFreeArtifactList() {
  return [
    {name: 'job-intake.json', kind: 'job_intake', uri: path.join(workspaceRoot, 'job-intake.json'), workspacePath: 'job-intake.json', origin: 'executor_workspace', required: true, summary: 'One-shot job packet claimed by Cloud Run worker.'},
    artifactFor('orientation.md', 'orientation', true, 'Repo-free orientation and restore evidence.'),
    artifactFor('reasoning-summary.md', 'reasoning_summary', true, 'Repo-free command execution summary.'),
    artifactFor('command-log.jsonl', 'command_log', true, 'Verification command transcript.'),
    artifactFor('acceptance.json', 'acceptance', true, 'Worker-side acceptance verdict.'),
    artifactFor('acceptance-matrix.json', 'acceptance_matrix', true, 'Criterion-level worker acceptance verdicts.'),
    artifactFor('usage-summary.json', 'usage_summary', false, 'No Codex usage for repo-free command probe.'),
    artifactFor('implementation.patch', 'implementation_patch', true, 'No repository patch for repo-free job.'),
    artifactFor('changed-files.json', 'changed_files', true, 'Repo-free changed-file evidence.'),
    artifactFor('verification.json', 'verification', true, 'Verification command results.'),
    artifactFor('mutation-requests.jsonl', 'mutation_requests', true, 'Mutation policy and follow-up authorization notes.'),
    artifactFor('final-report.md', 'final_report', true, 'Cloud Run repo-free final report.'),
  ];
}

async function runRepositoryFreeJob(packet, job, restore, executorId) {
  const commands = (job.verificationCommands && job.verificationCommands.length ? job.verificationCommands : ['node --version', 'python3 --version', 'date -u']).slice(0, 12);
  writeText('job-intake.json', JSON.stringify(packet, null, 2) + '\n');
  writeText('orientation.md', [
    '# Worker Orientation',
    '',
    `Restore: ${JSON.stringify(restore)}`,
    'Repository: none',
    '',
    'The worker intentionally used a repository-free workspace and did not invoke GitHub clone or repository restore logic.',
  ].join('\n') + '\n');
  const verificationResults = runVerificationCommands(commands);
  appendCommandLog(verificationResults);
  const commandEvidence = verificationResults.map((result) => `${result.command} -> ${result.exitCode}\n${result.stdout || result.stderr || ''}`).join('\n---\n');
  await workerEvent(job.jobId || jobId, 'executor_stdout', 'Repository-free command evidence.', {executorId, text: commandEvidence.slice(-4000), commandCount: verificationResults.length});
  const failures = verificationResults.filter((result) => result.exitCode !== 0).map((result) => `${result.command} exited ${result.exitCode}`);
  const accepted = failures.length === 0;
  writeText('implementation.patch', 'No implementation patch was produced for this repository-free job.\n');
  writeJsonFile('changed-files.json', {repository: '', restore, changedFiles: [], gitStatus: '', currentBranch: '', baseCommit: '', headCommit: '', newCommitCreated: false});
  writeJsonFile('verification.json', {verificationResults: verificationResults.map((item) => ({command: item.command, exitCode: item.exitCode, stdoutTail: item.stdout.slice(-4000), stderrTail: item.stderr.slice(-4000)})), allVerificationPassed: accepted});
  const usageSummary = {inputTokens: 0, cachedInputTokens: 0, outputTokens: 0, cachedInputRatio: 0, warnings: []};
  writeJsonFile('acceptance.json', {accepted, failures, repositoryFree: true, verificationPassed: accepted, usageSummary});
  const criteria = (job.acceptanceCriteria || []).map((criterion) => ({criterion, status: accepted ? 'passed' : 'failed', evidenceRefs: ['command-log.jsonl', 'verification.json', 'final-report.md'], notes: accepted ? 'All repo-free verification commands exited 0.' : 'One or more repo-free verification commands failed.', blockingReason: failures.join('; ')}));
  writeJsonFile('acceptance-matrix.json', {statusPolicy: 'Repository-free command probe acceptance is based on requested command exit codes.', criteria, usageSummary});
  writeJsonFile('usage-summary.json', usageSummary);
  writeText('reasoning-summary.md', `Repository-free worker command probe ${accepted ? 'completed' : 'failed'}.\n`);
  writeText('mutation-requests.jsonl', JSON.stringify({mutationPolicy: job.mutationPolicy || {}, note: 'No repository mutation was attempted.'}) + '\n');
  const finalReport = ['# Final Report', '', `Repository-free Command Center worker probe ${accepted ? 'completed' : 'failed'}.`, '', ...verificationResults.map((result) => `- ${result.command}: ${result.exitCode}`), ...(failures.length ? ['', 'Failures:', ...failures.map((failure) => `- ${failure}`)] : [])].join('\n') + '\n';
  writeText('final-report.md', finalReport);
  const artifacts = repositoryFreeArtifactList();
  await post('/worker/artifacts', {jobId: job.jobId || jobId, artifacts});
  await post('/worker/checkpoint', {
    jobId: job.jobId || jobId,
    currentPhase: accepted ? 'completed_repository_free_commands' : 'failed_repository_free_commands',
    decisionsMade: ['Claimed a specific Command Center job by COMMAND_CENTER_JOB_ID.', 'Restored a repository-free workspace.', 'Skipped GitHub clone and Codex mutation execution.', 'Ran bounded verification commands.'],
    testsRun: ['worker lease', 'executor events', 'artifact record', 'checkpoint write', ...verificationResults.map((result) => `${result.command} -> ${result.exitCode}`)],
    evidenceRefs: artifacts.map((artifact) => artifact.workspacePath),
    acceptanceCriteriaStatus: criteria,
    usageSummary,
    failedApproaches: failures,
    nextAction: accepted ? 'Inspect job events, logs, artifacts, checkpoint, and completion status.' : 'Fix the failed repo-free command evidence before claiming worker health.',
  });
  const status = accepted ? 'completed' : 'failed';
  await workerEvent(job.jobId || jobId, accepted ? 'executor_finished' : 'executor_failed', 'Cloud Run Debian worker finished repository-free command job mode.', {executorId, artifactCount: artifacts.length, failures});
  await post('/worker/complete', {jobId: job.jobId || jobId, status, finalReport, artifacts: []});
}

async function workerEvent(jobIdValue, type, summary, data = {}) {
  return post('/worker/events', {jobId: jobIdValue, type, summary, data});
}

async function failJobBeforeExecution(packet, job, executorId, probe) {
  const jobIdValue = job.jobId || jobId;
  ensureWorkspace();
  writeText('job-intake.json', JSON.stringify(packet, null, 2) + '\n');
  const failure = probe.summary || probe.failureKind || 'Codex API-key capability probe failed.';
  writeJsonFile('acceptance.json', {accepted: false, failures: [failure], preExecutionFailure: true, codexFailure: probe});
  writeJsonFile('acceptance-matrix.json', {statusPolicy: 'Pre-execution Codex capability failures fail closed before repository mutation.', criteria: (job.acceptanceCriteria || []).map((criterion) => ({criterion, status: 'failed', evidenceRefs: ['acceptance.json', 'final-report.md'], notes: 'Codex capability probe failed before executor start.', blockingReason: failure})), usageSummary: {inputTokens: 0, cachedInputTokens: 0, outputTokens: 0, cachedInputRatio: 0, warnings: ['pre_execution_codex_probe_failed']}});
  writeJsonFile('verification.json', {verificationResults: [], allVerificationPassed: false, skipped: true, reason: 'pre_execution_codex_probe_failed'});
  writeText('implementation.patch', 'No implementation patch was produced because Codex capability probing failed before execution.\n');
  writeJsonFile('changed-files.json', {repository: repositoryFromJob(job), changedFiles: [], gitStatus: '', currentBranch: '', baseCommit: '', headCommit: '', newCommitCreated: false, skipped: true});
  writeText('command-log.jsonl', JSON.stringify({command: 'codex capability probe', exitCode: probe.exitCode || 1, failureKind: probe.failureKind || '', stage: probe.stage || '', summary: failure}) + '\n');
  writeText('reasoning-summary.md', 'Cloud Run worker failed before Codex execution because the API-key capability probe failed.\n');
  writeText('mutation-requests.jsonl', JSON.stringify({mutationPolicy: job.mutationPolicy || {}, note: 'No repository mutation was attempted because Codex capability probing failed.'}) + '\n');
  const finalReport = ['# Final Report', '', 'Cloud Run worker failed before Codex execution.', '', `Failure kind: ${probe.failureKind || 'codex_capability_probe_failed'}`, `Stage: ${probe.stage || 'unknown'}`, '', failure].join('\n') + '\n';
  writeText('final-report.md', finalReport);
  const artifacts = [
    {name: 'job-intake.json', kind: 'job_intake', uri: path.join(workspaceRoot, 'job-intake.json'), workspacePath: 'job-intake.json', origin: 'executor_workspace', required: true, summary: 'One-shot job packet claimed by Cloud Run worker.'},
    artifactFor('command-log.jsonl', 'command_log', true, 'Pre-execution probe transcript.'),
    artifactFor('acceptance.json', 'acceptance', true, 'Worker-side pre-execution failure verdict.'),
    artifactFor('acceptance-matrix.json', 'acceptance_matrix', true, 'Criterion-level pre-execution verdict.'),
    artifactFor('implementation.patch', 'implementation_patch', true, 'Empty patch explanation.'),
    artifactFor('changed-files.json', 'changed_files', true, 'No-mutation repository evidence.'),
    artifactFor('verification.json', 'verification', true, 'Verification skipped evidence.'),
    artifactFor('mutation-requests.jsonl', 'mutation_requests', true, 'Mutation policy note.'),
    artifactFor('final-report.md', 'final_report', true, 'Cloud Run Codex capability failure report.'),
  ];
  await post('/worker/artifacts', {jobId: jobIdValue, artifacts});
  await post('/worker/checkpoint', {
    jobId: jobIdValue, currentPhase: 'failed_codex_capability_probe',
    decisionsMade: ['Claimed a specific Command Center job by COMMAND_CENTER_JOB_ID.', 'Ran Codex API-key capability probe.', 'Failed closed before repository mutation or verification.'],
    testsRun: ['worker lease', 'codex capability probe'], evidenceRefs: artifacts.map((artifact) => artifact.workspacePath),
    acceptanceCriteriaStatus: (job.acceptanceCriteria || []).map((criterion) => ({criterion, status: 'failed', evidenceRefs: ['acceptance.json', 'final-report.md'], notes: 'Codex capability probe failed before executor start.', blockingReason: failure})),
    usageSummary: {inputTokens: 0, cachedInputTokens: 0, outputTokens: 0, cachedInputRatio: 0, warnings: ['pre_execution_codex_probe_failed']}, failedApproaches: [failure],
    nextAction: 'Restore Codex execution quota or provide a non-API-key cloud Codex authentication lane before leasing Codex work.',
  });
  await workerEvent(jobIdValue, 'executor_failed', 'Cloud Run worker Codex capability probe failed before execution.', {executorId, preExecutionFailure: true, codexFailure: probe});
  await post('/worker/complete', {jobId: jobIdValue, status: 'failed', finalReport, artifacts: []});
}
async function runOneShotJob() {
  required('COMMAND_CENTER_WORKER_TOKEN', workerToken);
  required('COMMAND_CENTER_JOB_ID', jobId);
  ensureWorkspace();
  const executorId = `${os.hostname() || 'cloud-run'}:${process.env.CLOUD_RUN_EXECUTION || process.pid}`;
  const leased = await post('/worker/lease', {jobId, executorId});
  if (!leased.leased) throw new Error(`job was not leased to this worker: ${jobId}`);
  const packet = leased.packet || {};
  const job = packet.job || {};
  const runtimeProbe = await reportJobRuntimeProbe(job.jobId || jobId, 'api_key_probe');
  if (!runtimeProbe.ok) {
    await failJobBeforeExecution(packet, job, executorId, runtimeProbe);
    return;
  }
  await workerEvent(job.jobId || jobId, 'executor_started', 'Cloud Run Debian worker started real one-shot Codex job mode.', {executorId, objective: job.objective || ''});
  await workerEvent(job.jobId || jobId, 'executor_heartbeat', 'Cloud Run Debian worker restoring repository workspace.', {executorId, phase: 'restore_repository'});
  const restore = restoreJobWorkspace(job);
  if (!repositoryFromJob(job) && (restore.mode === 'empty_workspace' || restore.mode === 'worker_local_empty_workspace')) {
    await workerEvent(job.jobId || jobId, 'executor_heartbeat', 'Cloud Run Debian worker running repository-free command executor.', {executorId, phase: 'repository_free_commands', restore});
    await runRepositoryFreeJob(packet, job, restore, executorId);
    return;
  }
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
  const acceptance = assessJobAcceptance(packet, codex, verificationResults, gitEvidence);
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
    {name: 'job-intake.json', kind: 'job_intake', uri: path.join(workspaceRoot, 'job-intake.json'), workspacePath: 'job-intake.json', origin: 'executor_workspace', required: true, summary: 'One-shot job packet claimed by Cloud Run worker.'},
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
    failedApproaches: acceptance.failures,
    nextAction: status === 'completed' ? 'Inspect job events, logs, artifacts, checkpoint, and completion status.' : 'Fix the reported acceptance failures before claiming real cloud hands completion.',
  });
  await workerEvent(job.jobId || jobId, status === 'completed' ? 'executor_finished' : 'executor_failed', 'Cloud Run Debian worker finished real one-shot Codex job mode.', {executorId, artifactCount: artifacts.length, codexExitCode: codex.exitCode, acceptanceFailures: acceptance.failures});
  await post('/worker/complete', {jobId: job.jobId || jobId, status, finalReport, artifacts: []});
}

function assertWorkerSelfTest(condition, message) {
  if (!condition) throw new Error(message);
}

function runWorkerSelfTest() {
  const quotaTranscript = '{"type":"error","message":"Quota exceeded. Check your plan and billing details."}\n';
  const quotaFailure = classifyCodexFailure(quotaTranscript);
  assertWorkerSelfTest(quotaFailure.code === 'worker_openai_quota_exceeded', 'quota failure is classified explicitly');
  assertWorkerSelfTest(quotaFailure.preMutation === true, 'quota failure is a pre-mutation failure');

  const forbiddenPrJob = {
    objective: 'Implement the patch. Do not push, open a PR, or deploy.',
    acceptanceCriteria: ['Produce implementation.patch. No GitHub pull request URL is required or allowed for acceptance.'],
    constraints: ['push and PR creation are forbidden'],
    mutationPolicy: {createPullRequest: 'deny', push: 'deny'},
    requiredArtifacts: ['implementation.patch'],
  };
  assertWorkerSelfTest(!requiresPullRequest(forbiddenPrJob), 'negated PR/push text must not require PR evidence');

  const positivePrJob = {
    objective: 'Implement the fix and open a draft PR.',
    acceptanceCriteria: ['Return the pull request URL.'],
    mutationPolicy: {createPullRequest: 'allowed', push: 'allowed'},
    requiredArtifacts: ['implementation.patch'],
  };
  assertWorkerSelfTest(requiresPullRequest(positivePrJob), 'positive PR ticket must require PR evidence');

  const quotaAcceptance = (() => {
    const job = {objective: 'Implement the fix and produce implementation.patch.', acceptanceCriteria: ['Do not push or open a PR.'], mutationPolicy: {createPullRequest: 'deny', push: 'deny'}, requiredArtifacts: ['implementation.patch']};
    const transcript = quotaTranscript;
    const codexFailure = classifyCodexFailure(transcript);
    const failures = [];
    if (1 !== 0) failures.push(codexFailure.message || 'Codex exited 1.');
    if (!codexFailure.preMutation && isMutationTicket(job)) failures.push('Mutation ticket produced no uncommitted diff and no new commit relative to the restored base commit.');
    if (!codexFailure.preMutation && requiresPullRequest(job)) failures.push('Ticket required push/PR evidence but no GitHub pull request URL was produced.');
    return failures;
  })();
  assertWorkerSelfTest(quotaAcceptance.length === 1, 'quota failure should not add mutation or PR failures');
  assertWorkerSelfTest(/quota/i.test(quotaAcceptance[0]), 'quota acceptance failure names quota');
  const missingProbe = (() => {
    const old = process.env.OPENAI_API_KEY;
    delete process.env.OPENAI_API_KEY;
    const probe = codexApiKeyProbe();
    if (old) process.env.OPENAI_API_KEY = old;
    return probe;
  })();
  assertWorkerSelfTest(missingProbe.failureKind === 'secret_missing', 'API-key probe reports missing secret explicitly');
  const oldAccess = process.env.CODEX_ACCESS_TOKEN;
  process.env.CODEX_ACCESS_TOKEN = 'dummy-access-token';
  const accessAuth = codexAuthCredential();
  if (oldAccess) process.env.CODEX_ACCESS_TOKEN = oldAccess;
  else delete process.env.CODEX_ACCESS_TOKEN;
  assertWorkerSelfTest(accessAuth.mode === 'access_token', 'CODEX_ACCESS_TOKEN takes precedence over API-key auth');
  console.log('cloud_run_worker self-test: OK');
}

async function main() {
  if (process.argv.includes('--self-test')) {
    runWorkerSelfTest();
    return;
  }
  if (jobId) {
    await runOneShotJob();
    return;
  }
  required('COMMAND_CENTER_WORKER_TOKEN', workerToken);
  required('COMMAND_CENTER_ACTIVATION_ID', activationId);
  const claimed = await post('/agent/claim', {activationId});
  if (!claimed.claimed) throw new Error(`activation was not claimed: ${activationId}`);
  await reportActivationRuntimeProbe(activationId, 'api_key_probe');
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
    if (workerToken && jobId) {
      await post('/worker/events', {jobId, type: 'executor_failed', summary: `Cloud Run worker failed: ${message.slice(0, 1000)}`, data: {failed: true}});
      await post('/worker/complete', {jobId, status: 'failed', finalReport: `# Final Report\n\nCloud Run worker failed before completing lifecycle.\n\n${message}`});
    }
  } catch (_) {}
  console.error(message);
  process.exit(1);
});
