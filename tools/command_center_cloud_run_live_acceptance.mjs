#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const TOKEN_CONFIG = path.join(os.homedir(), '.config', 'home-center', 'codex-hub.json');
const DEFAULT_TMP = '/data/data/com.termux/files/usr/tmp';

function parseArgs(argv) {
  const args = {
    runId: `cloud-run-live-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`,
    evidenceDir: 'tools/command_center_invokability_evidence',
    activationId: '',
    sessionId: '',
    agentId: 'cloud-run-debian-codex-acceptance',
    projectId: 'command-center-cloud-workers',
    timeoutMs: 12 * 60 * 1000,
    pollMs: 15000,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--activation-id') args.activationId = argv[++i];
    else if (arg === '--session-id') args.sessionId = argv[++i];
    else if (arg === '--agent-id') args.agentId = argv[++i];
    else if (arg === '--project-id') args.projectId = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i]) || args.timeoutMs;
    else if (arg === '--poll-ms') args.pollMs = Number(argv[++i]) || args.pollMs;
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_cloud_run_live_acceptance.mjs --run-id RUN_ID [--json]');
      process.exit(0);
    }
  }
  return args;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
}

function redact(value) {
  return JSON.parse(JSON.stringify(value).replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]').replace(/\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/g, '[REDACTED_WORKER_TOKEN]').replace(/\bya29\.[A-Za-z0-9._-]{20,}/g, '[REDACTED_GOOGLE_TOKEN]'));
}

async function token() {
  const config = readJson(TOKEN_CONFIG);
  if (!config.accessToken || Number(config.expiresAtMs || 0) < Date.now() + 120000) {
    if (!config.refreshToken) throw new Error(`${TOKEN_CONFIG} has no usable accessToken or refreshToken`);
    const response = await fetch(`${config.gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net'}/termuxTokenRefresh`, {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({refreshToken: config.refreshToken}),
    });
    const text = await response.text();
    let json = {};
    try { json = JSON.parse(text); } catch (_) {}
    if (!response.ok || !json.ok || !json.access_token) throw new Error(`token refresh failed: ${response.status} ${text.slice(0, 300)}`);
    config.accessToken = json.access_token;
    config.tokenType = json.token_type || config.tokenType || 'Bearer';
    config.expiresAtMs = Date.now() + Number(json.expires_in || 0) * 1000;
    config.allowedGroups = json.allowedGroups || config.allowedGroups || [];
    config.refreshedAt = new Date().toISOString();
    fs.writeFileSync(TOKEN_CONFIG, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
  }
  return config.accessToken;
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  const payload = dataLines.length ? dataLines.join('\n') : text;
  try { return JSON.parse(payload); } catch (err) { throw new Error(`${label} did not return JSON: ${String(text).slice(0, 500)}`); }
}

function toolContentJson(result, label) {
  const text = result?.result?.content?.find((item) => item.type === 'text')?.text || '';
  try { return JSON.parse(text); } catch (err) { throw new Error(`${label} content was not JSON: ${text.slice(0, 500)}`); }
}

async function callTool(accessToken, id, name, args = {}) {
  const response = await fetch(MCP_URL, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${accessToken}`,
      'content-type': 'application/json',
      accept: 'application/json, text/event-stream',
    },
    body: JSON.stringify({jsonrpc: '2.0', id, method: 'tools/call', params: {name, arguments: args}}),
  });
  const text = await response.text();
  const json = parseMcpResponse(text, name);
  if (!response.ok || json.error) throw new Error(`${name} failed: ${response.status} ${JSON.stringify(json.error || json).slice(0, 700)}`);
  return toolContentJson(json, name);
}

function run(command, cwd = process.cwd()) {
  const result = spawnSync(command, {cwd, shell: true, encoding: 'utf8', maxBuffer: 20 * 1024 * 1024});
  return {command, exitCode: result.status ?? 1, stdout: result.stdout || '', stderr: result.stderr || ''};
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function snapshotRefFromPacket(packet) {
  return packet?.session?.currentWorkspaceSnapshotRef || packet?.activation?.nextWorkspaceSnapshotRef || '';
}

function listFiles(root) {
  const files = [];
  const walk = (dir) => {
    for (const name of fs.readdirSync(dir)) {
      const full = path.join(dir, name);
      const rel = path.relative(root, full);
      const stat = fs.statSync(full);
      if (stat.isDirectory()) walk(full);
      else files.push(rel);
    }
  };
  walk(root);
  return files.sort();
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const accessToken = await token();
  const runSafe = args.runId.replace(/[^A-Za-z0-9_.-]/g, '-');
  const activationId = args.activationId || `activation_${runSafe.replace(/[^A-Za-z0-9_-]/g, '_')}`;
  const sessionId = args.sessionId || `session_${runSafe.replace(/[^A-Za-z0-9_-]/g, '_')}`;
  const nonce = `NONCE_${runSafe}`;
  const evidencePath = path.join(args.evidenceDir, `cloud_run_live_acceptance_${runSafe}.json`);
  const evidence = {ok: false, runId: runSafe, activationId, sessionId, nonce, startedAt: new Date().toISOString(), steps: []};

  const upsert = await callTool(accessToken, 1, 'command_center_operation', {operation: 'agents.upsert_repo_agent', args: {
    idempotencyKey: `cloud-run-live-upsert-${runSafe}`,
    agentId: args.agentId,
    projectId: args.projectId,
    name: 'Cloud Run Debian Codex acceptance worker',
    purpose: 'Device-independent durable Command Center worker acceptance.',
    sessionId,
    sessionTitle: `Cloud Run live acceptance ${runSafe}`,
    sessionPurpose: 'Verify real Codex writes a nonce artifact and uploads a clean GCS workspace snapshot.',
    contextRefs: ['docs/COMMAND_CENTER_MCP.md', 'cloud-worker/src/cloud_run_worker.mjs'],
  }});
  evidence.steps.push({name: 'upsert_repo_agent', agentId: upsert.result?.agent?.agentId || '', sessionId: upsert.result?.session?.sessionId || ''});

  const prompt = [
    'This is a live Command Center Cloud Run Debian Codex acceptance run.',
    `Create a file named hello-world.txt in the current workspace containing exactly this nonce and nothing else: ${nonce}`,
    'Do not access external services. Do not print secrets. Keep the final answer concise.',
  ].join('\n');
  const activation = await callTool(accessToken, 2, 'command_center_operation', {operation: 'agents.create_activation', args: {
    idempotencyKey: `cloud-run-live-activation-${runSafe}`,
    activationId,
    agentId: args.agentId,
    sessionId,
    title: `Cloud Run Debian Codex live acceptance ${runSafe}`,
    prompt,
    workerRequirements: ['codex', 'cloud-run-debian', 'durable-session', 'gcs-workspace-snapshot'],
    acceptanceCriteria: [
      'A non-simulated Cloud Run Debian worker is selected.',
      'A real Cloud Run execution claims the activation.',
      `hello-world.txt contains ${nonce}.`,
      'A final artifact is recorded.',
      'A GCS workspace snapshot is uploaded.',
      'The snapshot contains no Codex auth state.',
    ],
    artifactRequirements: ['final-report.md', 'hello-world.txt', 'workspace.tgz'],
  }});
  evidence.steps.push({name: 'create_activation', selectedWorkerId: activation.result?.activation?.selectedWorkerId || '', status: activation.result?.activation?.status || '', cloudRunOperationName: activation.result?.activation?.cloudRunOperationName || ''});

  const deadline = Date.now() + args.timeoutMs;
  let packet = null;
  while (Date.now() < deadline) {
    const resume = await callTool(accessToken, 3, 'command_center_operation', {operation: 'agents.get_resume_packet', args: {activationId}});
    packet = resume.result?.resumePacket || null;
    const status = packet?.activation?.status || '';
    evidence.steps.push({name: 'poll_resume_packet', status, artifactRefs: packet?.activation?.artifactRefs || [], snapshotRef: snapshotRefFromPacket(packet)});
    if (['completed', 'failed', 'canceled', 'needs_human'].includes(status)) break;
    await sleep(args.pollMs);
  }
  if (!packet) throw new Error('No resume packet returned.');
  const finalStatus = packet.activation?.status || '';
  const snapshotRef = snapshotRefFromPacket(packet);
  evidence.finalStatus = finalStatus;
  evidence.artifactRefs = packet.activation?.artifactRefs || [];
  evidence.snapshotRef = snapshotRef;

  if (!snapshotRef.startsWith('gs://')) {
    evidence.ok = false;
    writeJson(evidencePath, redact(evidence));
    throw new Error(`Activation did not produce a GCS snapshot: status=${finalStatus}`);
  }

  const extractDir = path.join(DEFAULT_TMP, runSafe);
  const archive = path.join(extractDir, 'workspace.tgz');
  run(`rm -rf ${JSON.stringify(extractDir)}`, '/');
  fs.mkdirSync(extractDir, {recursive: true});
  const cp = run(`gcloud storage cp ${JSON.stringify(snapshotRef)} ${JSON.stringify(archive)} --project home-center-dclar`, '/');
  if (cp.exitCode !== 0) throw new Error(`snapshot download failed: ${cp.stderr || cp.stdout}`);
  const untar = run(`tar -xzf ${JSON.stringify(archive)} -C ${JSON.stringify(extractDir)}`, '/');
  if (untar.exitCode !== 0) throw new Error(`snapshot extract failed: ${untar.stderr || untar.stdout}`);
  const files = listFiles(extractDir).filter((file) => file !== 'workspace.tgz');
  const helloPath = path.join(extractDir, 'hello-world.txt');
  const helloText = fs.existsSync(helloPath) ? fs.readFileSync(helloPath, 'utf8').trim() : '';
  const authStateFiles = files.filter((file) => /(^|\/)(auth\.json|credentials?\.json|.*token.*|.*oauth.*|.*session.*\.(sqlite|db))$/i.test(file) || file.includes('.codex-home/') || file.includes('.command-center-codex-home/'));
  evidence.extractDir = extractDir;
  evidence.files = files;
  evidence.helloText = helloText;
  evidence.authStateFiles = authStateFiles;
  evidence.ok = finalStatus === 'completed' && helloText === nonce && authStateFiles.length === 0 && evidence.artifactRefs.length > 0;
  evidence.completedAt = new Date().toISOString();
  writeJson(evidencePath, redact(evidence));
  console.log(JSON.stringify({ok: evidence.ok, evidencePath, activationId, sessionId, finalStatus, snapshotRef, artifactRefs: evidence.artifactRefs, extractDir, helloTextMatches: helloText === nonce, authStateFiles}, null, args.json ? 0 : 2));
  if (!evidence.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
