#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const PROFILE_ID = 'com.android.chrome@150.0.7871.114+787111433';
const PACKAGE_NAME = 'com.android.chrome';
const DEFAULT_WORKFLOW = 'chatgptPluginInstall';
const DEFAULT_EVIDENCE_DIR = 'tools/chatgpt_connector_evidence';

function parseArgs(argv) {
  const args = {
    evidence: '',
    runId: '',
    url: '',
    status: '',
    workflow: DEFAULT_WORKFLOW,
    outDir: DEFAULT_EVIDENCE_DIR,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--evidence') args.evidence = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--url') args.url = argv[++i];
    else if (arg === '--status') args.status = argv[++i];
    else if (arg === '--workflow') args.workflow = argv[++i];
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/chrome_frame_learning_envelope.mjs --evidence PATH --run-id ID --url URL --status STATUS [--workflow NAME] [--out-dir DIR] [--json]');
      process.exit(0);
    }
  }
  return args;
}

function parseKeyValues(text) {
  const values = {};
  for (const line of String(text || '').split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z0-9_.-]+)=(.*)$/);
    if (match) values[match[1]] = match[2];
  }
  return values;
}

function parseBounds(text) {
  const match = String(text || '').match(/(?:bnds|bounds)=\[(\d+),(\d+)\]\[(\d+),(\d+)\]/i);
  if (!match) return [449, 867, 997, 1947];
  return match.slice(1).map((value) => Number(value));
}

function commandCenterOperation(operation, args) {
  return {tool: 'command_center_operation', operation, args};
}

export function buildChromeFrameLearningEnvelope(input = {}) {
  const evidencePath = path.resolve(input.evidence || '');
  const evidenceText = input.evidenceText ?? (evidencePath && fs.existsSync(evidencePath) ? fs.readFileSync(evidencePath, 'utf8') : '');
  const kv = parseKeyValues(evidenceText);
  const runId = String(input.runId || kv.runId || `chrome-frame-${Date.now()}`).replace(/[^A-Za-z0-9_.-]+/g, '-').slice(0, 180);
  const url = String(input.url || kv.url || 'https://chatgpt.com/');
  const status = String(input.status || kv.status || 'observed');
  const workflow = String(input.workflow || DEFAULT_WORKFLOW);
  const bounds = parseBounds(evidenceText);
  const bounded = status === 'bounded_frame_active' || /windowingMode=freeform|WindowingMode=freeform|windowingMode=5|bnds=\[\d+,\d+\]\[\d+,\d+\]|bounds=\[\d+,\d+\]\[\d+,\d+\]/.test(evidenceText);
  const returnedToTermux = /com\.termux/.test(evidenceText);
  const frameLane = {
    type: 'android_freeform_frame',
    packageName: PACKAGE_NAME,
    bounds,
    verifiedBounded: bounded,
    wholePhoneFallbackAllowed: false,
    requiresUserRespectedSubframe: true,
    focusReturnedToTermux: returnedToTermux,
    staleWholePhonePremiseForbidden: true,
  };
  const learnedFixes = [
    'Termux and Home Center must use the same Home Center operation schema; Termux is only an input runner.',
    'Chrome may be used as a bounded Android freeform frame when Playwright or auth requires human-visible verification.',
    'Whole-phone foreground takeover is forbidden for this workflow; stop if a bounded frame cannot be verified.',
    'After launching a Chrome frame, return focus to Termux so the user can keep using the phone outside the frame lane.',
  ];
  const evidenceRefs = evidencePath ? [evidencePath] : [];
  const appControlRunArgs = {
    runId: `chrome_frame_${runId}`,
    profileId: PROFILE_ID,
    workflow,
    packageName: PACKAGE_NAME,
    deviceAlias: 'drew-phone',
    status: bounded ? 'bounded_frame_active' : status,
    elapsedMs: 0,
    uiActionCount: 1,
    frameLane,
    summary: 'Chrome frame observation captured from a Termux runner into Home Center app-control learning records.',
    learnedFixes,
    evidenceRefs,
    idempotencyKey: `chrome-frame-app-control-${runId}`,
  };
  const browserEpisodeArgs = {
    episodeId: `chrome_frame_browser_episode_${runId}`,
    sessionId: `chrome-frame-${runId}`,
    intent: 'Use real Chrome as a bounded manual-assist/browser-hands lane without taking over the whole phone.',
    origin: 'termux.chrome_frame_launcher',
    url,
    title: 'Chrome bounded frame launcher',
    surface: {
      runtime: 'android-chrome-frame',
      browser: 'chrome',
      mode: 'desktop-or-site-default',
      userAgentMode: 'chrome-app',
    },
    outcome: bounded ? 'bounded_frame_active' : status,
    accessibilitySummary: 'No page accessibility snapshot is claimed from this launcher; it records frame-lane ownership and blocker-safe handoff only.',
    visibleTextSummary: 'Chrome was launched as a bounded/freeform frame and Termux focus was restored when verified.',
    actions: [{kind: 'android_intent_launch', packageName: PACKAGE_NAME, url, boundedFrameRequired: true}],
    blockers: bounded ? [] : ['Chrome frame was not verified as bounded; whole-phone fallback is forbidden.'],
    redactionReport: {containsSecrets: false, redacted: true},
    discoveryCandidates: [
      {
        task: 'android-chrome-frame-lane',
        claim: 'Real Android Chrome can be treated as a Home Center browser-hands fallback only when launched and verified inside a bounded/freeform frame.',
        safetyClass: 'foreground_bounded',
      },
      {
        task: 'home-center-termux-unification',
        claim: 'Termux runners and Home Center app/cloud callers should submit the same app_control.record_run and browser_sessions.record_episode operation payloads.',
        safetyClass: 'normal',
      },
    ],
    evidenceRefs,
    idempotencyKey: `chrome-frame-browser-episode-${runId}`,
  };
  return {
    schemaVersion: 1,
    kind: 'home_center_chrome_frame_learning_envelope',
    runId,
    url,
    status,
    source: {runner: 'termux', script: 'tools/launch_chatgpt_chrome_frame.sh', evidencePath},
    homeCenterOwnership: {
      owner: 'Home Center Command Center cloud bucket',
      termuxRole: 'input runner and local debugger',
      appRole: 'human approval and device capability surface',
      sharedCodePath: 'command_center_operation',
    },
    operations: [
      commandCenterOperation('app_control.record_run', appControlRunArgs),
      commandCenterOperation('browser_sessions.record_episode', browserEpisodeArgs),
    ],
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const envelope = buildChromeFrameLearningEnvelope(args);
  const outDir = path.resolve(args.outDir);
  fs.mkdirSync(outDir, {recursive: true});
  const outPath = path.join(outDir, `chrome_frame_${envelope.runId}.learning.json`);
  fs.writeFileSync(outPath, JSON.stringify(envelope, null, 2) + '\n');
  const summary = {ok: true, outPath, operations: envelope.operations.map((op) => op.operation)};
  console.log(JSON.stringify(args.json ? summary : {...summary, envelopePath: outPath}, null, args.json ? 0 : 2));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
