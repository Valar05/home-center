#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

function parseArgs(argv) {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
  const args = {
    runId: `cloud-run-two-dispatch-${stamp}`,
    evidenceDir: 'tools/command_center_invokability_evidence',
    timeoutMs: '',
    pollMs: '',
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = argv[++i];
    else if (arg === '--poll-ms') args.pollMs = argv[++i];
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_two_dispatch_acceptance.mjs --run-id RUN_ID [--json]');
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

function runAcceptance(label, args) {
  const runId = `${args.runId}-${label}`;
  const cmd = [
    'tools/command_center_cloud_run_live_acceptance.mjs',
    '--run-id',
    runId,
    '--evidence-dir',
    args.evidenceDir,
    '--json',
  ];
  if (args.timeoutMs) cmd.push('--timeout-ms', args.timeoutMs);
  if (args.pollMs) cmd.push('--poll-ms', args.pollMs);
  const result = spawnSync('node', cmd, {encoding: 'utf8', maxBuffer: 20 * 1024 * 1024});
  const evidencePath = path.join(args.evidenceDir, `cloud_run_live_acceptance_${runId.replace(/[^A-Za-z0-9_.-]/g, '-')}.json`);
  return {
    label,
    runId,
    command: ['node', ...cmd].join(' '),
    exitCode: result.status ?? 1,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
    evidencePath,
    evidence: fs.existsSync(evidencePath) ? readJson(evidencePath) : null,
  };
}

function assertRun(run) {
  if (run.exitCode !== 0) return `dispatch ${run.label} exited ${run.exitCode}`;
  if (!run.evidence || run.evidence.ok !== true) return `dispatch ${run.label} did not produce ok evidence`;
  if (run.evidence.finalStatus !== 'completed') return `dispatch ${run.label} finalStatus was ${run.evidence.finalStatus}`;
  if (!String(run.evidence.snapshotRef || '').startsWith('gs://')) return `dispatch ${run.label} did not record a GCS snapshot`;
  if (!Array.isArray(run.evidence.artifactRefs) || !run.evidence.artifactRefs.length) return `dispatch ${run.label} did not record artifacts`;
  if (run.evidence.helloText !== run.evidence.nonce) return `dispatch ${run.label} nonce file did not match`;
  if (Array.isArray(run.evidence.authStateFiles) && run.evidence.authStateFiles.length) return `dispatch ${run.label} snapshot included auth state`;
  return '';
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const combinedPath = path.join(args.evidenceDir, `two_dispatch_acceptance_${args.runId.replace(/[^A-Za-z0-9_.-]/g, '-')}.json`);
  const startedAt = new Date().toISOString();
  const first = runAcceptance('a', args);
  const second = first.exitCode === 0 ? runAcceptance('b', args) : null;
  const failures = [first, second].filter(Boolean).map(assertRun).filter(Boolean);
  if (second && first.evidence && second.evidence && first.evidence.activationId === second.evidence.activationId) failures.push('dispatches reused the same activationId');
  if (second && first.evidence && second.evidence && first.evidence.snapshotRef === second.evidence.snapshotRef) failures.push('dispatches reused the same snapshotRef');
  const combined = {
    ok: failures.length === 0,
    runId: args.runId,
    startedAt,
    completedAt: new Date().toISOString(),
    acceptance: 'two sequential real Cloud Run dispatches; the second run is mandatory',
    failures,
    dispatches: [first, second].filter(Boolean).map((run) => ({
      label: run.label,
      runId: run.runId,
      command: run.command,
      exitCode: run.exitCode,
      evidencePath: run.evidencePath,
      activationId: run.evidence && run.evidence.activationId || '',
      sessionId: run.evidence && run.evidence.sessionId || '',
      finalStatus: run.evidence && run.evidence.finalStatus || '',
      snapshotRef: run.evidence && run.evidence.snapshotRef || '',
      artifactRefs: run.evidence && run.evidence.artifactRefs || [],
      nonce: run.evidence && run.evidence.nonce || '',
    })),
  };
  writeJson(combinedPath, combined);
  console.log(JSON.stringify({ok: combined.ok, evidencePath: combinedPath, failures: combined.failures, dispatches: combined.dispatches}, null, args.json ? 0 : 2));
  if (!combined.ok) process.exit(1);
}

main();
