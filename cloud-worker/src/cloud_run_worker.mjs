#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const env = process.env;
const commandCenterBase = env.COMMAND_CENTER_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp';
const workerToken = env.COMMAND_CENTER_WORKER_TOKEN || '';
const activationId = env.COMMAND_CENTER_ACTIVATION_ID || '';
const jobId = env.COMMAND_CENTER_JOB_ID || '';
const snapshotBucket = env.COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET || '';
const workspaceRoot = env.COMMAND_CENTER_WORKSPACE_DIR || '/workspace/session';
const codexHome = env.CODEX_HOME || path.join(os.homedir(), '.command-center-codex-home');

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

function writeResumePacket(resumePacket) {
  fs.writeFileSync(path.join(workspaceRoot, 'codex-resume-packet.json'), JSON.stringify(resumePacket, null, 2) + '\n');
}

function expectedNonce(resumePacket) {
  const prompt = String(resumePacket.activation?.task?.prompt || '');
  const match = prompt.match(/\bNONCE_[A-Za-z0-9_.-]+\b/);
  return match ? match[0] : '';
}

function runCodex(resumePacket) {
  const prompt = [
    'You are executing a Command Center durable worker session.',
    'Use codex-resume-packet.json in the current workspace as the durable context.',
    'Produce a concise final report and do not expose secrets.',
    '',
    resumePacket.activation?.task?.prompt || '',
  ].join('\n');
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
  const nonce = expectedNonce(resumePacket);
  const helloPath = path.join(workspaceRoot, 'hello-world.txt');
  const helloText = fs.existsSync(helloPath) ? fs.readFileSync(helloPath, 'utf8').trim() : '';
  const acceptanceError = nonce && helloText !== nonce ? `Acceptance failed: hello-world.txt was ${helloText ? 'present with unexpected content' : 'not created'}. Expected ${nonce}.` : '';
  const exitCode = result.exitCode === 0 && acceptanceError ? 70 : result.exitCode;
  fs.writeFileSync(path.join(workspaceRoot, 'final-report.md'), `# Final Report\n\nExit code: ${exitCode}\n\n${acceptanceError || 'Worker acceptance checks passed.'}\n\nSee codex-stdout.jsonl and codex-stderr.txt.\n`);
  return {...result, exitCode, acceptanceError};
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
  writeText('job-intake.json', JSON.stringify(packet, null, 2) + '\n');
  await workerEvent(job.jobId || jobId, 'executor_started', 'Cloud Run Debian worker started one-shot job mode.', {executorId, objective: job.objective || ''});
  await workerEvent(job.jobId || jobId, 'executor_heartbeat', 'Cloud Run Debian worker heartbeat in one-shot job mode.', {executorId, phase: 'write_noop_artifacts'});
  const proof = {
    ok: true,
    jobId: job.jobId || jobId,
    workerId: env.COMMAND_CENTER_SELECTED_WORKER_ID || '',
    executorId,
    objective: job.objective || '',
    completedAt: new Date().toISOString(),
    mode: 'cloud_run_one_shot_noop',
  };
  writeText('noop-proof.txt', JSON.stringify(proof, null, 2) + '\n');
  const finalReport = [
    '# Final Report',
    '',
    'Cloud Run Debian worker completed the bounded no-op Command Center job.',
    '',
    `Job: ${job.jobId || jobId}`,
    `Executor: ${executorId}`,
  ].join('\n') + '\n';
  writeText('final-report.md', finalReport);
  const artifacts = [
    {name: 'job-intake.json', kind: 'job_intake', uri: path.join(workspaceRoot, 'job-intake.json'), workspacePath: 'job-intake.json', origin: 'executor_workspace', required: true, summary: 'One-shot job packet claimed by Cloud Run worker.'},
    {name: 'noop-proof.txt', kind: 'acceptance_proof', uri: path.join(workspaceRoot, 'noop-proof.txt'), workspacePath: 'noop-proof.txt', origin: 'executor_workspace', required: true, summary: 'Bounded no-op proof written by Cloud Run worker.'},
    {name: 'final-report.md', kind: 'final_report', uri: path.join(workspaceRoot, 'final-report.md'), workspacePath: 'final-report.md', origin: 'executor_workspace', required: true, summary: 'Cloud Run one-shot final report.'},
  ];
  await post('/worker/artifacts', {jobId: job.jobId || jobId, artifacts});
  await post('/worker/checkpoint', {
    jobId: job.jobId || jobId,
    currentPhase: 'completed_noop',
    decisionsMade: ['Claimed a specific Command Center job by COMMAND_CENTER_JOB_ID.', 'Wrote no-op proof artifacts from the Cloud Run worker container.'],
    testsRun: ['worker lease', 'executor events', 'artifact record', 'checkpoint write'],
    evidenceRefs: artifacts.map((artifact) => artifact.workspacePath),
    nextAction: 'Inspect job events, logs, artifacts, checkpoint, and completion status.',
  });
  await workerEvent(job.jobId || jobId, 'executor_finished', 'Cloud Run Debian worker finished one-shot no-op job mode.', {executorId, artifactCount: artifacts.length});
  await post('/worker/complete', {jobId: job.jobId || jobId, status: 'completed', finalReport, artifacts: []});
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
