#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const CONNECTOR_URL = 'https://chatgpt.com/#settings/Plugins';

function stamp() {
  return new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
}

function parseArgs(argv) {
  const args = {
    runId: `shizuku-it-chatgpt-${stamp()}`,
    launchFrame: true,
    verifyPrompt: false,
    waitMs: '7000',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--no-launch-frame') args.launchFrame = false;
    else if (arg === '--verify-prompt') args.verifyPrompt = true;
    else if (arg === '--wait-ms') args.waitMs = argv[++i];
    else if (arg === '--help') {
      console.log('Usage: node tools/shizuku_it_chatgpt_web_connectors.mjs [--run-id ID] [--verify-prompt] [--no-launch-frame] [--wait-ms N]');
      process.exit(0);
    } else {
      throw new Error(`Unknown arg: ${arg}`);
    }
  }
  args.runId = args.runId.replace(/[^A-Za-z0-9_.-]+/g, '-').slice(0, 160);
  return args;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, {recursive: true});
}

function runStep(name, command, args, outDir, options = {}) {
  const startedAt = new Date().toISOString();
  const proc = spawnSync(command, args, {
    cwd: ROOT,
    encoding: 'utf8',
    timeout: options.timeoutMs || 180000,
    env: {...process.env, ...(options.env || {})},
  });
  const finishedAt = new Date().toISOString();
  const record = {
    name,
    command,
    args,
    status: proc.status,
    signal: proc.signal || '',
    error: proc.error ? String(proc.error.message || proc.error) : '',
    startedAt,
    finishedAt,
    stdout: proc.stdout || '',
    stderr: proc.stderr || '',
  };
  fs.writeFileSync(path.join(outDir, `${name}.json`), JSON.stringify(record, null, 2) + '\n');
  return record;
}

function parseLastJson(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed) return null;
  const lines = trimmed.split(/\r?\n/).reverse();
  for (const line of lines) {
    const candidate = line.trim();
    if (!candidate.startsWith('{')) continue;
    try { return JSON.parse(candidate); } catch (_) {}
  }
  try { return JSON.parse(trimmed); } catch (_) { return null; }
}

function resultSummary(step) {
  const json = parseLastJson(step.stdout);
  return {
    name: step.name,
    ok: step.status === 0 && (json ? json.ok !== false : true),
    status: step.status,
    parsed: json,
    stderrSample: step.stderr.slice(0, 600),
  };
}

function frameStatus(step) {
  const text = step.stdout + '\n' + step.stderr;
  if (/Chrome bounded frame is active|bounded_frame_active/.test(text)) return 'bounded_frame_active';
  if (/not_verified_bounded/.test(text)) return 'not_verified_bounded';
  return step.status === 0 ? 'unknown_frame_result' : 'frame_launch_failed';
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = path.join(ROOT, 'tools', 'chatgpt_connector_evidence', args.runId);
  ensureDir(outDir);

  const steps = [];
  const add = (name, command, stepArgs, options) => {
    const step = runStep(name, command, stepArgs, outDir, options);
    steps.push(step);
    return step;
  };

  add('contract_chrome_frame_learning', 'node', ['tools/chrome_frame_learning_contract_test.mjs']);
  add('contract_chatgpt_connector_learning', 'node', ['tools/chatgpt_connector_frame_learning_contract_test.mjs']);
  add('cloud_seed_app_control_profile', 'node', ['tools/app_control_seed_cloud.mjs', '--rest']);
  add('submit_chatgpt_connector_learning', 'sh', ['tools/learn_chatgpt_connector_frame_lane.sh', '--submit', '--run-id', `${args.runId}-learning`, '--json']);
  add('backend_home_center_bridge', 'node', ['tools/command_center_home_bridge_invokability_gate.mjs', '--json', '--run-id', `${args.runId}-home`]);
  add('backend_command_center_direct', 'node', ['tools/command_center_chatgpt_invokability_gate.mjs', '--json', '--run-id', `${args.runId}-direct`]);

  const cleanArgs = ['tools/run_chatgpt_clean_slate_verify.sh', '--run-id', `${args.runId}-clean`, '--wait-ms', args.waitMs, '--ensure-home-center-connected'];
  if (args.verifyPrompt) cleanArgs.push('--verify-prompt');
  const clean = add('chatgpt_playwright_clean_slate', 'sh', cleanArgs, {timeoutMs: args.verifyPrompt ? 240000 : 120000});
  const cleanJson = parseLastJson(clean.stdout);
  let frame = null;
  let frameLearning = null;
  if (args.launchFrame && cleanJson && cleanJson.status === 'blocked_chatgpt_auth') {
    frame = add('bounded_chrome_frame_for_human_verification', 'sh', ['tools/launch_chatgpt_chrome_frame.sh', CONNECTOR_URL], {
      env: {RUN_ID: `${args.runId}-human-frame`},
      timeoutMs: 90000,
    });
    const learningPath = path.join(ROOT, 'tools', 'chatgpt_connector_evidence', `chrome_frame_${args.runId}-human-frame.learning.json`);
    if (fs.existsSync(learningPath)) {
      frameLearning = add('submit_current_bounded_frame_learning', 'node', [
        'tools/submit_chrome_frame_learning.mjs',
        '--envelope',
        learningPath,
        '--run-id',
        `${args.runId}-human-frame`,
        '--json',
      ]);
    }
  }

  const summaries = steps.map(resultSummary);
  const backendOk = summaries
    .filter((item) => ['backend_home_center_bridge', 'backend_command_center_direct'].includes(item.name))
    .every((item) => item.ok);
  const learningOk = summaries
    .filter((item) => ['contract_chrome_frame_learning', 'contract_chatgpt_connector_learning', 'cloud_seed_app_control_profile', 'submit_chatgpt_connector_learning'].includes(item.name))
    .every((item) => item.ok);
  const cleanStatus = cleanJson?.status || (clean.status === 0 ? 'unknown' : 'local_check_failed');
  const frameResult = frame ? frameStatus(frame) : 'not_launched';
  const needsHuman = cleanStatus === 'blocked_chatgpt_auth';

  const report = {
    ok: backendOk && learningOk && (cleanJson?.ok === true || (needsHuman && frameResult === 'bounded_frame_active')),
    runId: args.runId,
    generatedAt: new Date().toISOString(),
    command: 'shizuku it: make Command Center and Home Center usable in ChatGPT web without whole-phone takeover',
    stalePremiseForbidden: 'Do not use full-screen slow foreground clicking as fallback.',
    mutation: 'Seed and submit Home Center cloud app-control/browser learning; run backend and Playwright checks; launch only a bounded Chrome frame if human ChatGPT verification is required.',
    backendOk,
    learningOk,
    cleanSlateStatus: cleanStatus,
    frameResult,
    frameLearningSubmitted: !!frameLearning && frameLearning.status === 0,
    needsHumanVerification: needsHuman,
    humanVerificationUrl: needsHuman ? CONNECTOR_URL : '',
    nextHumanCheck: needsHuman
      ? 'Use the bounded Chrome frame only. Complete ChatGPT/Cloudflare verification and connector connect state there, then rerun this script with --verify-prompt.'
      : (cleanJson?.ok ? 'Rerun with --verify-prompt if a no-op tool-call proof is still needed.' : 'Inspect step JSON files in this evidence directory.'),
    evidenceDir: outDir,
    steps: summaries,
  };
  const reportPath = path.join(outDir, 'summary.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ok: report.ok, status: cleanStatus, frameResult, evidenceDir: outDir, summaryPath: reportPath, nextHumanCheck: report.nextHumanCheck}, null, 2));
  process.exit(report.ok ? 0 : 2);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
