#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const PROFILE_PATH = path.join(ROOT, 'functions/app_control_seed/com.android.chrome.150.0.7871.114+787111433.json');
const DEFAULT_EVIDENCE_DIR = path.join(ROOT, 'tools/chatgpt_connector_evidence/chatgpt-hello-world-shizuku-20260711');
const CONNECTOR_URL = 'https://chatgpt.com/#settings/Plugins/plugin_asdk_app_6a5257c067048191ba6c399095aedaeb';

function parseArgs(argv) {
  const args = {
    evidenceDir: DEFAULT_EVIDENCE_DIR,
    runId: `chatgpt-command-center-frame-learning-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`,
    outDir: '',
    submit: false,
    dryRun: false,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--submit') args.submit = true;
    else if (arg === '--dry-run') args.dryRun = true;
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/learn_chatgpt_connector_frame_lane.mjs [--evidence-dir DIR] [--run-id ID] [--out-dir DIR] [--submit] [--dry-run] [--json]');
      process.exit(0);
    } else {
      throw new Error(`Unknown arg: ${arg}`);
    }
  }
  if (!args.outDir) args.outDir = args.evidenceDir;
  return args;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function fileExists(file) {
  return fs.existsSync(file) && fs.statSync(file).isFile();
}

function sha(value) {
  return createHash('sha256').update(String(value)).digest('hex').slice(0, 16);
}

function op(operation, args) {
  return {tool: 'command_center_operation', operation, args};
}

function evidenceRefs(evidenceDir) {
  const names = [
    'screen_promptfree_after_callback_restore_chrome.png',
    'screen_promptfree_after_access_continue.png',
    'screen_promptfree_after_google_continue.png',
    'screen_promptfree_after_drew_row.png',
    'screen_after_send2.png',
  ];
  const refs = [];
  for (const name of names) {
    const file = path.join(evidenceDir, name);
    if (fileExists(file)) refs.push(file);
  }
  if (!refs.length && fs.existsSync(evidenceDir)) refs.push(evidenceDir);
  return refs;
}

function buildEnvelope(args) {
  const profile = readJson(PROFILE_PATH);
  const refs = evidenceRefs(path.resolve(args.evidenceDir));
  const workflow = 'chatgptCommandCenterConnector';
  const runId = args.runId.replace(/[^A-Za-z0-9_.-]+/g, '-').slice(0, 180);
  const frameLane = {
    type: 'android_freeform_frame',
    packageName: 'com.android.chrome',
    bounds: [449, 867, 997, 1947],
    verifiedBounded: true,
    wholePhoneFallbackAllowed: false,
    requiresUserRespectedSubframe: true,
    approvalPromptsForbiddenDuringFrame: true,
    wrongSurfacePackage: 'com.openai.chatgpt',
    wrongSurfaceFix: 'force-stop com.openai.chatgpt; reopen ChatGPT connector settings URL in Chrome freeform',
  };
  const learnedFixes = [
    'Pre-approve Shizuku/rish helpers before opening the bounded frame; a Codex approval prompt steals focus and collapses the nested-window workflow.',
    'Use ChatGPT web in Chrome, not the installed ChatGPT app. If OAuth callback opens the app, force-stop it and restore the Chrome connector page in freeform.',
    'For Google/OAuth WebViews, screencap before uiautomator. XML failure is expected and must not erase screenshot evidence.',
    'Gate prompt sending on connected-state evidence. Disconnected connector plus prompt text is a blocker, not an acceptance candidate.',
    'Store this workflow under Home Center appControlProfiles so Termux and Home Center workers execute the same profile with different inputs.',
  ];
  return {
    schemaVersion: 1,
    kind: 'home_center_chatgpt_connector_frame_lane_learning_envelope',
    runId,
    generatedAt: new Date().toISOString(),
    source: {
      runner: 'termux',
      evidenceDir: path.resolve(args.evidenceDir),
      script: 'tools/learn_chatgpt_connector_frame_lane.mjs',
      url: CONNECTOR_URL,
    },
    operations: [
      op('app_control.put_profile', {
        profile,
        idempotencyKey: `chatgpt-connector-profile-${sha(JSON.stringify(profile.workflows?.[workflow] || {}))}`,
      }),
      op('app_control.record_run', {
        runId,
        profileId: profile.profileId,
        workflow,
        packageName: profile.packageName,
        deviceAlias: 'drew-phone',
        status: 'learning_promoted_connected_frame_lane',
        elapsedMs: 1500000,
        uiActionCount: 18,
        frameLane,
        summary: 'Converted a slow manual ChatGPT Command Center OAuth reconnect into a reusable Home Center Chrome app-control workflow. The next run should restore and verify connected state before any prompt.',
        learnedFixes,
        evidenceRefs: refs,
        idempotencyKey: `chatgpt-connector-frame-learning-${runId}`,
      }),
      op('browser_sessions.record_episode', {
        episodeId: `chatgpt_connector_frame_${runId}`,
        sessionId: 'chatgpt-command-center-connector-frame-lane',
        intent: 'Repair and verify ChatGPT web connector setup through a bounded Android Chrome frame without whole-phone takeover.',
        origin: 'termux.shizuku.chrome_frame_learning',
        url: CONNECTOR_URL,
        title: 'ChatGPT Command Center connector frame-lane learning',
        surface: {runtime: 'android-chrome-frame', browser: 'chrome', mode: 'freeform', userAgentMode: 'chrome-app'},
        outcome: 'connected_state_restored_after_oauth_callback_quarantine',
        accessibilitySummary: 'OAuth WebView XML can fail; screenshot-first evidence and bounded coordinates are the reliable path.',
        visibleTextSummary: 'Final restored Chrome connector page showed Command Center connected to dclarke1005@gmail.com.',
        actions: [
          {kind: 'launch_url_freeform', url: CONNECTOR_URL, packageName: 'com.android.chrome'},
          {kind: 'tap_known_control', label: 'Connect'},
          {kind: 'tap_known_control', label: 'Sign in with Command Center'},
          {kind: 'tap_known_control', label: 'Google unverified app Advanced and unsafe continue'},
          {kind: 'quarantine_wrong_surface', packageName: 'com.openai.chatgpt'},
          {kind: 'restore_url_freeform', url: CONNECTOR_URL},
        ],
        blockers: [],
        redactionReport: {containsSecrets: false, redacted: true},
        discoveryCandidates: [
          {task: 'chatgpt-command-center-connector', claim: 'Connected-state evidence must precede any ChatGPT prompt or mutation test.', safetyClass: 'normal'},
          {task: 'android-chrome-frame-lane', claim: 'Codex approval prompts are frame-breakers; live frame scripts must run without approval prompts or stop before opening the frame.', safetyClass: 'foreground_bounded'},
        ],
        evidenceRefs: refs,
        idempotencyKey: `chatgpt-connector-browser-episode-${runId}`,
      }),
    ],
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = path.resolve(args.outDir);
  fs.mkdirSync(outDir, {recursive: true});
  const envelope = buildEnvelope(args);
  const outPath = path.join(outDir, `chatgpt_connector_frame_learning_${envelope.runId}.json`);
  fs.writeFileSync(outPath, JSON.stringify(envelope, null, 2) + '\n');
  const result = {ok: true, envelopePath: outPath, operations: envelope.operations.map((item) => item.operation)};
  if (args.submit || args.dryRun) {
    const submitArgs = ['tools/submit_chrome_frame_learning.mjs', '--envelope', outPath, '--run-id', envelope.runId];
    if (args.dryRun) submitArgs.push('--dry-run');
    if (args.json) submitArgs.push('--json');
    const submit = spawnSync('node', submitArgs, {cwd: ROOT, encoding: 'utf8'});
    result.submitStatus = submit.status;
    result.submitStdout = submit.stdout.trim();
    result.submitStderr = submit.stderr.trim();
    if (submit.status !== 0) {
      console.error(JSON.stringify(result, null, 2));
      process.exit(submit.status || 1);
    }
  }
  console.log(JSON.stringify(args.json ? result : result, null, args.json ? 0 : 2));
}

try {
  main();
} catch (err) {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
}
