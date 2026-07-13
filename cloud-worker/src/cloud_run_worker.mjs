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
const codexHomeArchive = env.COMMAND_CENTER_CODEX_HOME_TGZ_PATH || '/var/secrets/command-center-codex-home/codex-home.tgz';

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

function processEnv(overrides = {}, options = {}) {
  const merged = {...process.env, ...overrides};
  for (const name of options.omit || []) delete merged[name];
  return merged;
}

function run(command, cwd = workspaceRoot, options = {}) {
  const result = spawnSync(command, {
    cwd,
    shell: true,
    encoding: 'utf8',
    env: processEnv(options.env || {}, options),
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

function prepareCodexHome() {
  fs.mkdirSync(codexHome, {recursive: true});
  if (fs.existsSync(codexHomeArchive)) {
    const before = run(`find ${JSON.stringify(codexHome)} -mindepth 1 -maxdepth 1 | head -n 1`, '/', {omit: ['OPENAI_API_KEY']});
    if (!before.stdout.trim()) {
      const unpack = run(`tar -xzf ${JSON.stringify(codexHomeArchive)} -C ${JSON.stringify(codexHome)}`, '/', {omit: ['OPENAI_API_KEY']});
      if (unpack.exitCode !== 0) throw new Error(`Codex home restore failed: ${unpack.stderr || unpack.stdout}`);
    }
    return {mode: 'codex_home_archive', codexHome};
  }
  if (!env.OPENAI_API_KEY) return {mode: 'missing', codexHome};
  const login = run('sh -lc \'printf %s "$OPENAI_API_KEY" | codex login --with-api-key\'', workspaceRoot, {env: {CODEX_HOME: codexHome}});
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stdout.txt'), login.stdout);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-login-stderr.txt'), login.stderr);
  if (login.exitCode !== 0) return {mode: 'api_key_login_failed', codexHome, login};
  return {mode: 'api_key_login', codexHome};
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

function repositoryFromGithubRef(ref) {
  const raw = String(ref || '')
    .replace(/^github:\/\//i, '')
    .replace(/^https:\/\/github\.com\//i, '')
    .split(/[?#]/)[0]
    .replace(/\.git$/i, '');
  const parts = raw.split('/').filter(Boolean);
  return parts.length >= 2 ? `${parts[0]}/${parts[1]}` : '';
}

function repositoryFromJob(job = {}) {
  const direct = job.repository || job.inputs?.repository || job.baseWorkspace?.repository || '';
  if (direct) return repositoryFromGithubRef(direct) || direct;
  const snapshotRef = String(job.baseWorkspace?.snapshotRef || '');
  if (snapshotRef.startsWith('github://') || /^https:\/\/github\.com\//i.test(snapshotRef)) return repositoryFromGithubRef(snapshotRef);
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
  const codexAuth = prepareCodexHome();
  if (codexAuth.login && codexAuth.login.exitCode !== 0) {
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report

Codex login failed with exit code ${codexAuth.login.exitCode}.

See codex-login-stderr.txt.
`);
    return codexAuth.login;
  }
  if (codexAuth.mode === 'missing') {
    const result = {command: 'codex auth preflight', cwd: workspaceRoot, exitCode: 78, stdout: '', stderr: 'No Codex home archive or OPENAI_API_KEY was configured.'};
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), '# Final Report\n\nCodex authentication was not configured.\n');
    return result;
  }
  fs.writeFileSync(path.join(workspaceRoot, 'codex-auth-mode.txt'), `${codexAuth.mode}\n`);
  fs.writeFileSync(path.join(workspaceRoot, 'codex-prompt.md'), prompt);
  const result = run(`codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox --output-last-message ${JSON.stringify(path.join(workspaceRoot, 'codex-last-message.md'))} - < ${JSON.stringify(path.join(workspaceRoot, 'codex-prompt.md'))}`, workspaceRoot, {env: {CODEX_HOME: codexHome}, omit: codexAuth.mode === 'codex_home_archive' ? ['OPENAI_API_KEY'] : []});
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
  const codexAuth = prepareCodexHome();
  if (codexAuth.login && codexAuth.login.exitCode !== 0) {
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report

Codex login failed with exit code ${codexAuth.login.exitCode}.

See codex-login-stderr.txt.
`);
    return codexAuth.login;
  }
  if (codexAuth.mode === 'missing') {
    const result = {command: 'codex auth preflight', cwd: workspaceRoot, exitCode: 78, stdout: '', stderr: 'No Codex home archive or OPENAI_API_KEY was configured.'};
    fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), '# Final Report\n\nCodex authentication was not configured.\n');
    return result;
  }
  fs.writeFileSync(path.join(workspaceRoot, 'codex-auth-mode.txt'), `${codexAuth.mode}\n`);
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
    omit: codexAuth.mode === 'codex_home_archive' ? ['OPENAI_API_KEY'] : [],
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
  ].join('\n');
  return /pull request|\bPR\b|draft PR|push/i.test(text);
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
  const usageSummary = parseCodexUsageSummary(transcript);
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

async function runOneShotJob() {
  required('COMMAND_CENTER_WORKER_TOKEN', workerToken);
  required('COMMAND_CENTER_JOB_ID', jobId);
  ensureWorkspace();
  const executorId = `${os.hostname() || 'cloud-run'}:${process.env.CLOUD_RUN_EXECUTION || process.pid}`;
  const leased = await post('/worker/lease', {jobId, executorId});
  if (!leased.leased) throw new Error(`job was not leased to this worker: ${jobId}`);
  const packet = leased.packet || {};
  const job = packet.job || {};
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
