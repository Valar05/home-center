import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {detectPageBlockers, normalizeStartUrl, redactText, safeText, snapshotPage} from './browser_worker.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..');
const DEFAULT_VIEWPORT = {width: 1366, height: 900};
const DEFAULT_ARGS = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'];

function arg(name, fallback = '') {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function hasFlag(name) {
  return process.argv.includes(`--${name}`);
}

function failSetup(reason, nextAction = '') {
  console.error(JSON.stringify({ok: false, status: 'blocked_local_setup', reason, nextAction}));
  process.exit(1);
}

function classifyChatGptSnapshot(snapshot) {
  const text = `${snapshot.title || ''}\n${snapshot.url || ''}\n${snapshot.visibleTextSummary || ''}`;
  const lower = text.toLowerCase();
  const blockers = detectPageBlockers(snapshot);
  const hasTurnstile = Array.isArray(snapshot.landmarks) && snapshot.landmarks.some((item) => /cf-turnstile|turnstile/i.test(`${item.name || ''} ${item.type || ''} ${item.text || ''}`));
  if (/cloudflare|checking your browser|verify you are human|captcha|not a robot|just a moment/i.test(text) || hasTurnstile) {
    return {status: 'blocked_chatgpt_auth', reason: 'ChatGPT page is behind human/browser verification.', blockers: [...blockers, 'ChatGPT requires human/browser verification.']};
  }
  if (/\b(log in|login|sign up|sign in|continue with google|continue with apple)\b/i.test(text)) {
    return {status: 'blocked_chatgpt_auth', reason: 'Playwright reached ChatGPT, but this browser profile is not signed in.', blockers};
  }
  const mentionsHomeCenter = /home center|homecentermcp|command center|home bridge|drive bridge/i.test(text);
  const disconnected = /disconnected|couldn'?t connect|could not connect|problem connecting|connection failed|reconnect|oauth error|authorization failed/i.test(text);
  const connected = /connected|enabled|installed|added|configured/i.test(text);
  if (mentionsHomeCenter && disconnected) {
    return {status: 'blocked_chatgpt_ui', reason: 'ChatGPT mentions Home Center but reports a connection problem.', blockers};
  }
  if (mentionsHomeCenter && connected && !disconnected) {
    return {status: 'ok', reason: 'ChatGPT mentions Home Center and appears connected or installed.', blockers};
  }
  if (/gpts|apps|connectors|developer mode|mcp|tools|settings/i.test(text)) {
    return {status: 'unknown', reason: 'ChatGPT loaded in desktop Chromium, but Home Center install state was not visible in the captured page.', blockers};
  }
  if (lower.includes('chatgpt')) {
    return {status: 'unknown', reason: 'ChatGPT loaded, but the page did not expose plugin installation state.', blockers};
  }
  return {status: 'blocked_chatgpt_ui', reason: 'Playwright did not capture a recognizable ChatGPT page.', blockers};
}

async function main() {
  const runId = safeText(arg('run-id', `chatgpt_plugin_${Date.now()}`), 120).replace(/[^a-zA-Z0-9_-]/g, '_');
  const startUrl = normalizeStartUrl(arg('url', process.env.HOME_CENTER_CHATGPT_DEBUG_URL || 'https://chatgpt.com/'));
  const waitMs = Math.max(0, Math.min(Number(arg('wait-ms', '5000')), 60000));
  const outDir = path.resolve(arg('out-dir', path.join(repoRoot, 'generated', 'chatgpt-plugin-debug')));
  const executablePath = safeText(arg('executable-path', process.env.HOME_CENTER_CHROMIUM_EXECUTABLE || ''), 1000);
  const headless = !hasFlag('headed') && process.env.HEADLESS !== '0';
  if (!headless && !process.env.DISPLAY) {
    failSetup(
      'Headed Playwright Chromium requires an X display, but DISPLAY is not set in Debian/proot.',
      'Install/start Termux:X11 and rerun with DISPLAY exported, or run the debugger headless to collect non-interactive evidence.'
    );
  }
  await fs.mkdir(outDir, {recursive: true});

  const launchOptions = {headless, args: DEFAULT_ARGS};
  if (executablePath) launchOptions.executablePath = executablePath;
  const browser = await chromium.launch(launchOptions);
  let screenshotPath = '';
  try {
    const context = await browser.newContext({viewport: DEFAULT_VIEWPORT, isMobile: false, hasTouch: false, locale: 'en-US'});
    const page = await context.newPage();
    await page.goto(startUrl, {waitUntil: 'domcontentloaded', timeout: Number(arg('timeout-ms', '45000'))});
    if (waitMs) await page.waitForTimeout(waitMs);
    const snapshot = await snapshotPage(page);
    screenshotPath = path.join(outDir, `${runId}.png`);
    await page.screenshot({path: screenshotPath, fullPage: true}).catch(() => { screenshotPath = ''; });
    const classification = classifyChatGptSnapshot(snapshot);
    const result = {
      ok: classification.status === 'ok',
      status: classification.status,
      reason: classification.reason,
      runId,
      url: snapshot.url,
      title: redactText(snapshot.title),
      startUrl,
      surface: {runtime: 'playwright', browser: 'chromium', mode: 'desktop', executablePath: executablePath || 'playwright-managed', viewport: DEFAULT_VIEWPORT, headless},
      visibleTextSummary: snapshot.visibleTextSummary,
      accessibilitySummary: snapshot.accessibilitySummary,
      landmarks: snapshot.landmarks,
      blockers: classification.blockers,
      screenshotPath,
      generatedAt: new Date().toISOString(),
    };
    const artifactPath = path.join(outDir, `${runId}.json`);
    await fs.writeFile(artifactPath, JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify({ok: result.ok, status: result.status, reason: result.reason, artifactPath, screenshotPath}));
    process.exit(result.ok ? 0 : 2);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(JSON.stringify({ok: false, status: 'blocked_local_setup', reason: err.message || String(err)}));
  process.exit(1);
});
