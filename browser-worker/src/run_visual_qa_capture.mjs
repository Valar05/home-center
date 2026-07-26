#!/usr/bin/env node

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--url' || arg === '--start-url') args.startUrl = argv[++i] || '';
    else if (arg.startsWith('--url=')) args.startUrl = arg.slice('--url='.length);
    else if (arg === '--target') args.target = argv[++i] || '';
    else if (arg === '--job-id') args.jobId = argv[++i] || '';
    else if (arg === '--session-id') args.sessionId = argv[++i] || '';
    else if (arg === '--episode-id') args.episodeId = argv[++i] || '';
    else if (arg === '--worker-id') args.workerId = argv[++i] || '';
    else if (arg === '--out-dir') args.outDir = argv[++i] || '';
    else if (arg === '--wait-for-selector') args.waitForSelector = argv[++i] || '';
    else if (arg === '--settle-ms') args.settleMs = Number(argv[++i] || 0);
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i] || 0);
    else if (arg === '--viewport') {
      const [width, height] = String(argv[++i] || '').split('x').map(Number);
      args.viewport = {width, height};
    } else if (arg === '--headed') args.headless = false;
    else if (arg === '--help' || arg === '-h') {
      console.log('usage: node src/run_visual_qa_capture.mjs --url URL [--target crimson-sword] [--out-dir DIR] [--job-id ID] [--session-id ID] [--episode-id ID]');
      process.exit(0);
    } else {
      throw new Error('unknown argument: ' + arg);
    }
  }
  if (!args.startUrl) throw new Error('--url is required');
  return args;
}

const options = parseArgs(process.argv);
if (process.platform === 'android' && process.env.HOME_CENTER_ALLOW_ANDROID_PLAYWRIGHT !== '1') {
  console.error(JSON.stringify({
    ok: false,
    status: 'blocked_browser_worker_host',
    reason: 'Playwright desktop Chromium is not supported by Android/Termux Node. Run this browser-worker command in Debian/proot or on a registered cloud browser worker.',
    command: 'proot-distro login debian -- sh -lc \"cd /storage/emulated/0/Documents/GodotProjects/home-center/browser-worker && npm run visual-qa -- --url HOSTED_URL --target crimson-sword\"',
  }, null, 2));
  process.exit(1);
}
const {runVisualQaCapture, commandCenterArtifactsForVisualQa} = await import('./visual_qa_capture.mjs');
const result = await runVisualQaCapture(options);
const artifacts = commandCenterArtifactsForVisualQa(result, options);
console.log(JSON.stringify({
  ok: result.ok,
  status: result.status,
  outDir: result.outDir,
  manifestPath: result.manifestPath,
  screenshotPath: result.screenshotPath,
  screenshotSha256: result.screenshotSha256,
  artifacts,
}, null, 2));
