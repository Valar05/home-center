import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {detectPageBlockers, normalizeStartUrl, redactText, safeText, snapshotPage} from './browser_worker.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..');
const DEFAULT_VIEWPORT = {width: 1366, height: 900};
const DEFAULT_ARGS = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'];

const HELLO_WORLD_PROMPT = `Use the connected Home Center or Command Center MCP app. If command_center_operation is available, call it with operation bucket.put_object. If it is not available, call namespaced tool command_center.bucket.put_object directly. Args: {"kind":"note.cross_repo","objectId":"chatgpt_hello_world_noop_20260711_v1","path":"notes/cross-repo/chatgpt-hello-world-noop-20260711-v1.md","title":"ChatGPT hello world no-op acceptance","summary":"End-to-end ChatGPT to Home Center to Command Center mutation proof.","body":"hello world","projectId":"home-center","repository":"Valar05/home-center","tags":["chatgpt-acceptance","hello-world","effective-no-op"],"idempotencyKey":"chatgpt-hello-world-noop-20260711-v1"}. Then read the same object back using command_center_operation operation bucket.get_object or namespaced command_center.bucket.get_object with objectId chatgpt_hello_world_noop_20260711_v1. Reply with only the objectId, path, and whether the readback body equals hello world.`;

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

function classifySnapshot(snapshot) {
  const text = `${snapshot.title || ''}\n${snapshot.url || ''}\n${snapshot.visibleTextSummary || ''}`;
  const blockers = detectPageBlockers(snapshot);
  const hasTurnstile = Array.isArray(snapshot.landmarks) && snapshot.landmarks.some((item) => /cf-turnstile|turnstile/i.test(`${item.name || ''} ${item.role || ''} ${item.text || ''}`));
  if (/cloudflare|checking your browser|verify you are human|captcha|not a robot|just a moment/i.test(text) || hasTurnstile) {
    return {status: 'blocked_chatgpt_auth', reason: 'ChatGPT page is behind human/browser verification.', blockers: [...blockers, 'ChatGPT requires human/browser verification.']};
  }
  if (/\b(log in|login|sign up|sign in|continue with google|continue with apple)\b/i.test(text)) {
    return {status: 'blocked_chatgpt_auth', reason: 'ChatGPT browser profile is not signed in.', blockers};
  }
  if (/message chatgpt|ask anything|send message|chatgpt/i.test(text)) {
    return {status: 'ready', reason: 'ChatGPT page appears usable.', blockers};
  }
  return {status: 'blocked_chatgpt_ui', reason: 'ChatGPT did not expose a recognizable composer.', blockers};
}

async function findComposer(page) {
  const selectors = [
    'textarea[placeholder*="Message"]',
    'textarea',
    '[contenteditable="true"]',
    '[role="textbox"]',
  ];
  for (const selector of selectors) {
    const locator = page.locator(selector).last();
    if (await locator.count().catch(() => 0)) {
      try {
        await locator.waitFor({state: 'visible', timeout: 3000});
        return {selector, locator};
      } catch (_) {}
    }
  }
  return null;
}

async function clickLikelyToolApproval(page) {
  const approvalTexts = [/^allow$/i, /^run$/i, /^continue$/i, /^approve$/i, /use.*home center/i, /command_center_operation/i];
  for (const pattern of approvalTexts) {
    const button = page.getByRole('button', {name: pattern}).first();
    if (await button.count().catch(() => 0)) {
      try {
        await button.click({timeout: 4000});
        return {clicked: true, label: String(pattern)};
      } catch (_) {}
    }
  }
  return {clicked: false};
}

async function main() {
  const runId = safeText(arg('run-id', `chatgpt_hello_world_${Date.now()}`), 120).replace(/[^a-zA-Z0-9_-]/g, '_');
  const startUrl = normalizeStartUrl(arg('url', process.env.HOME_CENTER_CHATGPT_DEBUG_URL || 'https://chatgpt.com/'));
  const outDir = path.resolve(arg('out-dir', path.join(repoRoot, 'generated', 'chatgpt-plugin-debug')));
  const executablePath = safeText(arg('executable-path', process.env.HOME_CENTER_CHROMIUM_EXECUTABLE || ''), 1000);
  const headless = !hasFlag('headed') && process.env.HEADLESS !== '0';
  const autoApproveTool = hasFlag('auto-approve-tool');
  const waitMs = Math.max(5000, Math.min(Number(arg('wait-ms', '30000')), 120000));
  if (!headless && !process.env.DISPLAY) {
    failSetup('Headed Playwright Chromium requires an X display, but DISPLAY is not set in Debian/proot.', 'Use the bounded Chrome frame helper for human-visible verification on this phone.');
  }
  await fs.mkdir(outDir, {recursive: true});
  const launchOptions = {headless, args: DEFAULT_ARGS};
  if (executablePath) launchOptions.executablePath = executablePath;
  const browser = await chromium.launch(launchOptions);
  let screenshotPath = '';
  let artifactPath = '';
  try {
    const context = await browser.newContext({viewport: DEFAULT_VIEWPORT, isMobile: false, hasTouch: false, locale: 'en-US'});
    const page = await context.newPage();
    await page.goto(startUrl, {waitUntil: 'domcontentloaded', timeout: Number(arg('timeout-ms', '45000'))});
    await page.waitForTimeout(5000);
    const before = await snapshotPage(page);
    const classification = classifySnapshot(before);
    const actions = [{type: 'goto', url: startUrl, status: 'ok'}];
    let after = before;
    let status = classification.status;
    let reason = classification.reason;
    let approval = {clicked: false};
    if (classification.status === 'ready') {
      const composer = await findComposer(page);
      if (!composer) {
        status = 'blocked_chatgpt_ui';
        reason = 'ChatGPT composer was not found.';
      } else {
        await composer.locator.click({timeout: 5000});
        await page.keyboard.insertText(HELLO_WORLD_PROMPT);
        await page.keyboard.press('Enter');
        actions.push({type: 'submit_prompt', selector: composer.selector, status: 'ok', promptRedacted: 'fixed hello-world Command Center no-op prompt'});
        await page.waitForTimeout(Math.min(waitMs, 20000));
        if (autoApproveTool) {
          approval = await clickLikelyToolApproval(page);
          if (approval.clicked) {
            actions.push({type: 'click_tool_approval', status: 'ok', label: approval.label});
            await page.waitForTimeout(Math.max(10000, waitMs - 20000));
          }
        }
        after = await snapshotPage(page);
        const responseText = `${after.visibleTextSummary || ''}\n${after.accessibilitySummary || ''}`;
        if (/objectId|bucket|hello world|readback/i.test(responseText)) {
          status = 'chatgpt_prompt_submitted';
          reason = 'ChatGPT accepted the fixed prompt and produced a response mentioning bucket/readback evidence.';
        } else if (/connect|enable|install|tool|app|permission|allow|approve/i.test(responseText)) {
          status = 'blocked_chatgpt_ui';
          reason = 'ChatGPT likely needs connector/tool permission or the app is not attached.';
        } else {
          status = 'unknown';
          reason = 'Prompt was submitted, but the response did not expose recognizable Command Center evidence.';
        }
      }
    }
    screenshotPath = path.join(outDir, `${runId}.png`);
    await page.screenshot({path: screenshotPath, fullPage: true}).catch(() => { screenshotPath = ''; });
    const result = {
      ok: status === 'chatgpt_prompt_submitted',
      status,
      reason,
      runId,
      startUrl,
      url: after.url,
      title: redactText(after.title),
      surface: {runtime: 'playwright', browser: 'chromium', mode: 'desktop', executablePath: executablePath || 'playwright-managed', viewport: DEFAULT_VIEWPORT, headless},
      autoApproveTool,
      approval,
      prompt: {fixed: true, idempotencyKey: 'chatgpt-hello-world-noop-20260711-v1'},
      actions,
      before: {visibleTextSummary: before.visibleTextSummary, landmarks: before.landmarks},
      after: {visibleTextSummary: after.visibleTextSummary, accessibilitySummary: after.accessibilitySummary, landmarks: after.landmarks},
      blockers: classification.blockers || [],
      screenshotPath,
      generatedAt: new Date().toISOString(),
    };
    artifactPath = path.join(outDir, `${runId}.json`);
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
