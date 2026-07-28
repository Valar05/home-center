import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {normalizeStartUrl, redactText, safeText, snapshotPage} from './browser_worker.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..');
const DEFAULT_VIEWPORT = {width: 1366, height: 900};
const DEFAULT_CHROMIUM_ARGS = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'];

function isoNow() {
  return new Date().toISOString();
}

function sha256Bytes(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function outputDir(options = {}) {
  return options.outDir
    ? path.resolve(options.outDir)
    : path.join(repoRoot, 'generated', 'visual-qa', String(Date.now()));
}

function normalizeViewport(value = {}) {
  const width = Math.max(320, Math.min(Number(value.width || DEFAULT_VIEWPORT.width), 3840));
  const height = Math.max(240, Math.min(Number(value.height || DEFAULT_VIEWPORT.height), 2160));
  return {width, height};
}

async function collectDebugPayload(page, debugKeys = []) {
  return page.evaluate((keys) => {
    const dataset = {...document.body.dataset};
    const globals = {};
    for (const key of keys || []) {
      if (!key || typeof key !== 'string') continue;
      try {
        globals[key] = window[key] ?? null;
      } catch (_) {
        globals[key] = null;
      }
    }
    const canvases = Array.from(document.querySelectorAll('canvas')).map((canvas) => {
      const rect = canvas.getBoundingClientRect();
      return {
        width: canvas.width,
        height: canvas.height,
        clientWidth: canvas.clientWidth,
        clientHeight: canvas.clientHeight,
        bounds: [rect.left, rect.top, rect.right, rect.bottom].map((n) => Math.round(n)),
      };
    });
    return {
      dataset,
      globals,
      canvases,
      readyState: document.readyState,
      locationHref: location.href,
      title: document.title,
    };
  }, debugKeys).catch((error) => ({error: String(error && error.message || error)}));
}

function extractCrimsonSocketProof(debugPayload = {}) {
  const dataset = debugPayload.dataset || {};
  const raw = dataset.crimsonSocketProof || dataset.poseLabSocketProof || '';
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch (error) {
    return {status: 'invalid-json', parseError: String(error && error.message || error), raw: raw.slice(0, 1000)};
  }
}

async function waitForTargetReady(page, options = {}) {
  if (options.target !== 'crimson-sword') return;
  const timeout = Math.max(15000, Math.min(Number(options.targetReadyTimeoutMs || options.timeoutMs || 90000), 180000));
  await page.waitForFunction(() => {
    const dataset = document.body?.dataset || {};
    return dataset.bootReady === '1'
      && dataset.saberAttachmentStatus === 'attached'
      && dataset.saberVisibleInViewport === 'true';
  }, null, {timeout});
}

function classifyVisualQa(manifest) {
  const errors = [];
  if (!manifest.screenshotPath || !manifest.screenshotSha256) errors.push('missing screenshot artifact');
  if (!manifest.browserEpisode?.episodeId) errors.push('missing completed browser episode id');
  if (!manifest.debugPayload || manifest.debugPayload.error) errors.push('missing page debug payload');
  if (manifest.target === 'crimson-sword') {
    const proof = manifest.browserSocketProof || {};
    if (proof.status !== 'attached') errors.push('Crimson socket proof is not attached');
    if (proof.parentBone !== 'RightHand') errors.push('Crimson socket proof parent is not RightHand');
    if (proof.visibleInViewport !== true) errors.push('Crimson sword is not visible in viewport proof');
    if (!(Number(proof.screenLengthPx) >= 12)) errors.push('Crimson sword screen length is too small');
  }
  return {
    status: errors.length ? 'needs_visual_read' : 'evidence_ready',
    errors,
  };
}

export async function runVisualQaCapture(options = {}) {
  const startUrl = normalizeStartUrl(options.startUrl || options.url);
  const target = safeText(options.target, 120) || 'browser-final-render';
  const sessionId = safeText(options.sessionId, 180) || 'browser_session_' + Date.now();
  const jobId = safeText(options.jobId, 180);
  const episodeId = safeText(options.episodeId, 180) || 'browser_episode_' + Date.now();
  const viewport = normalizeViewport(options.viewport);
  const dir = outputDir(options);
  const executablePath = safeText(options.executablePath || process.env.HOME_CENTER_CHROMIUM_EXECUTABLE, 1000);
  const consoleEvents = [];
  const pageErrors = [];
  const networkFailures = [];
  const responseStatuses = [];
  const launchOptions = {
    headless: options.headless !== false,
    args: Array.from(new Set([...DEFAULT_CHROMIUM_ARGS, ...(Array.isArray(options.chromiumArgs) ? options.chromiumArgs.map(String) : [])])),
  };
  if (executablePath) launchOptions.executablePath = executablePath;

  await fs.mkdir(dir, {recursive: true});
  const browser = await chromium.launch(launchOptions);
  try {
    const context = await browser.newContext({viewport, isMobile: false, hasTouch: false, locale: 'en-US'});
    const page = await context.newPage();
    page.on('console', (msg) => {
      consoleEvents.push({type: msg.type(), text: redactText(msg.text()).slice(0, 1000)});
    });
    page.on('pageerror', (error) => pageErrors.push(redactText(error.message || String(error)).slice(0, 1000)));
    page.on('requestfailed', (request) => networkFailures.push({
      url: request.url(),
      method: request.method(),
      failure: safeText(request.failure()?.errorText, 500),
    }));
    page.on('response', (response) => {
      const status = response.status();
      if (status >= 400) responseStatuses.push({url: response.url(), status});
    });

    await page.goto(startUrl, {waitUntil: safeText(options.waitUntil, 80) || 'domcontentloaded', timeout: Number(options.timeoutMs || 45000)});
    await waitForTargetReady(page, {target, timeoutMs: options.timeoutMs, targetReadyTimeoutMs: options.targetReadyTimeoutMs});
    if (options.waitForSelector) {
      await page.locator(String(options.waitForSelector)).first().waitFor({state: 'visible', timeout: Number(options.waitForSelectorTimeoutMs || 15000)});
    }
    await page.waitForTimeout(Math.max(0, Math.min(Number(options.settleMs || 1500), 120000)));

    const screenshotPath = path.join(dir, 'screenshot.png');
    const screenshotBytes = await page.screenshot({path: screenshotPath, fullPage: false});
    const screenshotSha256 = sha256Bytes(screenshotBytes);
    const snapshot = await snapshotPage(page);
    const debugPayload = await collectDebugPayload(page, options.debugGlobals || ['__POSE_LAB_VISUAL_QA__']);
    const browserSocketProof = options.browserSocketProof || extractCrimsonSocketProof(debugPayload);
    const capturedAt = isoNow();
    const episode = {
      episodeId,
      sessionId,
      intent: safeText(options.intent, 2000) || 'Home Center visual QA capture for ' + target,
      origin: new URL(page.url()).origin,
      url: page.url(),
      title: snapshot.title,
      surface: {runtime: 'playwright', browser: 'chromium', mode: 'desktop', userAgentMode: 'desktop', viewport, workerId: safeText(options.workerId, 120)},
      outcome: 'visual_qa_captured',
      accessibilitySummary: snapshot.accessibilitySummary,
      visibleTextSummary: snapshot.visibleTextSummary,
      focusedElement: {},
      actions: [{type: 'goto', url: startUrl, status: 'ok'}, {type: 'screenshot', path: screenshotPath, sha256: screenshotSha256, status: 'ok'}],
      blockers: [],
      redactionReport: {formValues: 'redacted', secretsStored: false},
      discoveryCandidates: [],
      evidenceRefs: [screenshotPath],
      createdAt: capturedAt,
    };
    const manifest = {
      schema: 'command-center-visual-qa-evidence-v1',
      target,
      captureKind: 'home-center-cloud-review',
      jobId,
      sessionId,
      browserEpisode: {episodeId, outcome: episode.outcome},
      startUrl,
      finalUrl: page.url(),
      capturedAt,
      screenshotPath,
      screenshotSha256,
      surface: episode.surface,
      browserSocketProof,
      debugPayload,
      consoleEvents,
      pageErrors,
      networkFailures,
      responseStatuses,
      visualRead: safeText(options.visualRead, 4000),
      assertions: options.assertions && typeof options.assertions === 'object' ? options.assertions : {},
    };
    manifest.review = classifyVisualQa(manifest);
    const episodePath = path.join(dir, 'browser_episode.json');
    const manifestPath = path.join(dir, 'visual_qa_manifest.json');
    const consolePath = path.join(dir, 'console_network.json');
    await fs.writeFile(episodePath, JSON.stringify(episode, null, 2) + '\n');
    await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
    await fs.writeFile(consolePath, JSON.stringify({consoleEvents, pageErrors, networkFailures, responseStatuses}, null, 2) + '\n');
    return {ok: true, status: manifest.review.status, outDir: dir, screenshotPath, screenshotSha256, manifestPath, episodePath, consolePath, manifest, episode};
  } finally {
    await browser.close();
  }
}

export function commandCenterArtifactsForVisualQa(result, options = {}) {
  const origin = 'browser_worker_visual_qa';
  const jobId = safeText(options.jobId || result.manifest?.jobId, 180);
  const episodeId = safeText(result.episode?.episodeId || result.manifest?.browserEpisode?.episodeId, 180);
  return [
    {
      name: 'visual_qa_manifest.json',
      kind: 'visual_qa_manifest',
      uri: result.manifestPath,
      required: true,
      origin,
      workspacePath: result.manifestPath,
      metadata: {origin, jobId, episodeId, captureKind: 'home-center-cloud-review', target: result.manifest?.target || ''},
    },
    {
      name: 'screenshot.png',
      kind: 'screenshot',
      uri: result.screenshotPath,
      sha256: result.screenshotSha256,
      required: true,
      origin,
      workspacePath: result.screenshotPath,
      metadata: {origin, jobId, episodeId, captureKind: 'command-center-cloud-screenshot', target: result.manifest?.target || ''},
    },
    {
      name: 'browser_episode.json',
      kind: 'browser_episode',
      uri: result.episodePath,
      required: true,
      origin,
      workspacePath: result.episodePath,
      metadata: {origin, jobId, episodeId},
    },
    {
      name: 'console_network.json',
      kind: 'debug_log',
      uri: result.consolePath,
      required: false,
      origin,
      workspacePath: result.consolePath,
      metadata: {origin, jobId, episodeId},
    },
  ];
}
