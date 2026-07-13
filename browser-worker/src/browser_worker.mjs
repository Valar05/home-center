import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..');
const DEFAULT_VIEWPORT = {width: 1366, height: 900};
const DEFAULT_CHROMIUM_ARGS = [
  '--no-sandbox',
  '--disable-dev-shm-usage',
  '--disable-gpu',
];
const BLOCKED_ACTIONS = new Set(['purchase', 'submit_payment', 'place_order', 'solve_captcha', 'bypass_verification', 'change_password', 'delete_account', 'login_verification', 'submit_sensitive_form', 'account_security']);

export function safeText(value, max = 4000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

export function redactText(value) {
  return safeText(value, 4000)
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[redacted-email]')
    .replace(/\b(?:\d[ -]*?){13,19}\b/g, '[redacted-card]')
    .replace(/\b(?:password|passcode|security code|cvv|cvc)\b\s*[:=]?\s*\S+/gi, '$1 [redacted]');
}

export function normalizeStartUrl(raw) {
  const text = safeText(raw, 1000) || 'https://www.google.com/';
  return /^[a-z][a-z0-9+.-]*:/i.test(text) ? text : `https://${text}`;
}


export function originFromUrl(raw) {
  try {
    return new URL(normalizeStartUrl(raw)).origin;
  } catch (_) {
    return '';
  }
}

export function normalizeTaskKey(value, fallback = 'general.web_task') {
  const text = safeText(value, 160).toLowerCase().replace(/[^a-z0-9_.-]+/g, '.').replace(/^\.+|\.+$/g, '');
  return text || fallback;
}

function cssString(value) {
  return String(value || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

export function buildSelectorLadderFromElementMeta(meta = {}) {
  const tag = safeText(meta.tag, 40).toLowerCase() || '*';
  const role = safeText(meta.role, 80);
  const text = safeText(meta.text, 120);
  const candidates = [];
  const add = (kind, selector, confidence, reason) => {
    if (!selector || candidates.some((item) => item.selector === selector)) return;
    candidates.push({kind, selector, confidence, reason});
  };
  if (meta.testId) add('data-testid', `[data-testid="${cssString(meta.testId)}"]`, 0.98, 'Stable test id attribute.');
  if (meta.id) add('id', `#${String(meta.id).replace(/([^a-zA-Z0-9_-])/g, '\\$1')}`, 0.95, 'HTML id attribute.');
  if (meta.name) add('name', `${tag}[name="${cssString(meta.name)}"]`, 0.9, 'Named form/control attribute.');
  if (meta.ariaLabel) add('aria-label', `${tag}[aria-label="${cssString(meta.ariaLabel)}"]`, 0.84, 'Accessible aria-label.');
  if (role && (meta.accessibleName || text)) add('role-name', `role=${role}[name="${cssString(meta.accessibleName || text)}"]`, 0.8, 'Accessibility role/name pair.');
  if (meta.labelText && meta.id) add('label-for', `label[for="${cssString(meta.id)}"]`, 0.76, 'Associated label for the control.');
  if (meta.href) add('href', `${tag}[href="${cssString(meta.href)}"]`, 0.7, 'Stable link href.');
  if (text && text.length <= 80) add('text', `text=${text}`, 0.52, 'Visible text fallback.');
  return candidates;
}

function pageSignatureFromSnapshot(snapshot = {}) {
  const headings = Array.isArray(snapshot.landmarks)
    ? snapshot.landmarks.filter((item) => /^h[1-3]$/.test(item.tag || '')).map((item) => safeText(item.text, 120)).filter(Boolean).slice(0, 8)
    : [];
  return {
    origin: originFromUrl(snapshot.url || ''),
    title: safeText(snapshot.title, 180),
    headings,
  };
}

async function elementMeta(locator) {
  return locator.evaluate((node) => {
    const tag = node.tagName.toLowerCase();
    const doc = node.ownerDocument;
    const id = node.getAttribute('id') || '';
    const label = id ? doc.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
    return {
      tag,
      id,
      name: node.getAttribute('name') || '',
      testId: node.getAttribute('data-testid') || node.getAttribute('data-test-id') || node.getAttribute('data-test') || '',
      ariaLabel: node.getAttribute('aria-label') || '',
      role: node.getAttribute('role') || '',
      accessibleName: node.getAttribute('aria-label') || node.getAttribute('title') || '',
      labelText: label ? (label.textContent || '').trim() : '',
      href: tag === 'a' ? node.getAttribute('href') || '' : '',
      text: (node.innerText || node.textContent || '').trim().slice(0, 120),
    };
  }).catch(() => ({}));
}

async function selectorLadderForLocator(locator) {
  const meta = await elementMeta(locator);
  return buildSelectorLadderFromElementMeta(meta);
}

async function locatorFromSelectorLadder(page, ladder = []) {
  for (const candidate of Array.isArray(ladder) ? ladder : []) {
    try {
      let locator;
      if (String(candidate.selector || '').startsWith('role=')) {
        const match = String(candidate.selector).match(/^role=([^[]+)\[name="(.*)"\]$/);
        if (!match) continue;
        locator = page.getByRole(match[1], {name: match[2]}).first();
      } else if (String(candidate.selector || '').startsWith('text=')) {
        locator = page.getByText(String(candidate.selector).slice(5), {exact: true}).first();
      } else {
        locator = page.locator(candidate.selector).first();
      }
      if (await locator.count().catch(() => 0)) {
        await locator.waitFor({state: 'visible', timeout: 1500});
        return {locator, selector: candidate.selector, kind: candidate.kind};
      }
    } catch (_) {}
  }
  return null;
}

export function blockUnsafeAction(action) {
  const type = safeText(action && action.type, 80).toLowerCase();
  if (BLOCKED_ACTIONS.has(type)) {
    return {blocked: true, reason: 'Sensitive browser action requires human control.'};
  }
  return {blocked: false, reason: ''};
}

export function detectPageBlockers(snapshot) {
  const text = `${snapshot.title || ''}\n${snapshot.url || ''}\n${snapshot.visibleTextSummary || ''}`;
  const blockers = [];
  if (/captcha|not a robot|unusual traffic|automated queries|verify you are human/i.test(text)) {
    blockers.push('Page is asking for human verification or bot-check handling.');
  }
  return blockers;
}

export async function snapshotPage(page) {
  const title = await page.title().catch(() => '');
  const url = page.url();
  const visibleText = await page.locator('body').innerText({timeout: 3000}).catch(() => '');
  const accessibility = page.accessibility && typeof page.accessibility.snapshot === 'function'
    ? await page.accessibility.snapshot({interestingOnly: true}).catch(() => null)
    : null;
  const landmarks = await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll('main, nav, header, footer, h1, h2, h3, button, a, input, textarea, select, [role]')).slice(0, 160);
    return nodes.map((node) => {
      const rect = node.getBoundingClientRect();
      const tag = node.tagName.toLowerCase();
      const input = tag === 'input' || tag === 'textarea';
      return {
        tag,
        role: node.getAttribute('role') || '',
        text: input ? '[redacted-input]' : (node.innerText || node.getAttribute('aria-label') || node.getAttribute('title') || '').trim().slice(0, 180),
        name: node.getAttribute('aria-label') || node.getAttribute('name') || '',
        type: node.getAttribute('type') || '',
        href: tag === 'a' ? node.getAttribute('href') || '' : '',
        id: node.getAttribute('id') || '',
        testId: node.getAttribute('data-testid') || node.getAttribute('data-test-id') || node.getAttribute('data-test') || '',
        selectorLadder: [],
        bounds: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
      };
    });
  }).catch(() => []);
  return {
    title: redactText(title),
    url,
    visibleTextSummary: redactText(visibleText).slice(0, 3000),
    accessibilitySummary: JSON.stringify(accessibility || {}).slice(0, 4000),
    landmarks,
  };
}

export async function runBrowserEpisode(options = {}) {
  const intent = safeText(options.intent, 2000) || 'Open a page and record accessible browser state.';
  const startUrl = normalizeStartUrl(options.startUrl);
  const taskKey = normalizeTaskKey(options.taskKey || options.intent);
  const headless = options.headless !== false;
  const executablePath = safeText(options.executablePath || process.env.HOME_CENTER_CHROMIUM_EXECUTABLE, 1000);
  const actions = [];
  const launchOptions = {
    headless,
    args: Array.from(new Set([...DEFAULT_CHROMIUM_ARGS, ...(
      Array.isArray(options.chromiumArgs) ? options.chromiumArgs.map((item) => String(item)) : []
    )])),
  };
  if (executablePath) {
    launchOptions.executablePath = executablePath;
  }
  const browser = await chromium.launch(launchOptions);
  try {
    const context = await browser.newContext({viewport: DEFAULT_VIEWPORT, isMobile: false, hasTouch: false, locale: 'en-US'});
    const page = await context.newPage();
    await page.goto(startUrl, {waitUntil: 'domcontentloaded', timeout: Number(options.timeoutMs || 30000)});
    actions.push({type: 'goto', url: startUrl, status: 'ok'});

    for (const action of Array.isArray(options.actions) ? options.actions : []) {
      const blocked = blockUnsafeAction(action);
      if (blocked.blocked) {
        actions.push({type: safeText(action.type, 80), status: 'blocked_human_required', reason: blocked.reason, safetyGate: true});
        continue;
      }
      if (action.type === 'fill') {
        const locator = page.locator(action.selector).first();
        const selectorLadder = await selectorLadderForLocator(locator);
        await locator.fill(String(action.value || ''), {timeout: 5000});
        actions.push({type: 'fill', selector: action.selector, selectorLadder, valueKey: safeText(action.valueKey, 80), valueRedacted: '[redacted]', status: 'ok'});
      } else if (action.type === 'click') {
        const locator = page.locator(action.selector).first();
        const selectorLadder = await selectorLadderForLocator(locator);
        await locator.click({timeout: 5000});
        actions.push({type: 'click', selector: action.selector, selectorLadder, status: 'ok'});
      } else if (action.type === 'press') {
        await page.keyboard.press(String(action.key || 'Enter'));
        actions.push({type: 'press', key: action.key || 'Enter', status: 'ok'});
      } else if (action.type === 'wait') {
        await page.waitForTimeout(Math.max(0, Math.min(Number(action.ms || 1000), 10000)));
        actions.push({type: 'wait', ms: Number(action.ms || 1000), status: 'ok'});
      }
    }

    const snap = await snapshotPage(page);
    const pageBlockers = detectPageBlockers(snap);
    const origin = new URL(page.url()).origin;
    const discoveryCandidates = [];
    if (snap.landmarks.some((item) => /cookie|privacy|consent/i.test(`${item.text} ${item.name}`))) {
      discoveryCandidates.push({task: 'accessibility_repair', safetyClass: 'normal', claim: 'Page exposes a cookie/privacy/consent control that should be identified before task automation.'});
    }
    if (snap.landmarks.some((item) => item.tag === 'input')) {
      discoveryCandidates.push({task: 'form_navigation', safetyClass: 'normal', claim: 'Page has form controls; preserve labels, roles, and focused-element narration for manual web-hands mode.'});
    }
    const successfulSelectorActions = actions.filter((item) => item.status === 'ok' && Array.isArray(item.selectorLadder) && item.selectorLadder.length);
    if (successfulSelectorActions.length && !pageBlockers.length) {
      discoveryCandidates.push({
        discoveryId: `browser_discovery_${taskKey}_${Date.now()}`.replace(/[^A-Za-z0-9_-]+/g, '_'),
        task: taskKey,
        taskKey,
        safetyClass: 'normal',
        claim: `Successful Playwright DOM selector playbook candidate for ${origin} ${taskKey}.`,
        playbook: {
          taskKey,
          origin,
          learnedBy: safeText(options.learnedBy, 120) || 'drew',
          shareScope: safeText(options.shareScope, 80) || 'household',
          replayAudience: safeText(options.replayAudience, 120) || 'june',
          startUrl,
          pageSignature: pageSignatureFromSnapshot(snap),
          actions: successfulSelectorActions.map((item) => ({type: item.type, selectorLadder: item.selectorLadder, valueKey: item.valueKey || '', key: item.key || ''})),
          successAssertions: [{type: 'origin_matches', value: origin}],
          safetyGates: Array.from(BLOCKED_ACTIONS),
          selectorPolicy: 'html_id_data_testid_aria_role_label_first_no_pixel_coordinates',
          householdLearningContract: 'Drew first-use discovery can become June second-use automation after verified success and promotion.',
        },
      });
    }
    return {
      sessionId: safeText(options.sessionId, 180) || `local_browser_session_${Date.now()}`,
      intent,
      taskKey,
      origin,
      url: page.url(),
      title: snap.title,
      surface: {runtime: 'playwright', browser: 'chromium', mode: 'desktop', userAgentMode: 'desktop', viewport: DEFAULT_VIEWPORT, executablePath: executablePath || 'playwright-managed'},
      outcome: actions.some((item) => item.status === 'blocked_human_required') || pageBlockers.length ? 'blocked_human_required' : 'observed',
      accessibilitySummary: snap.accessibilitySummary,
      visibleTextSummary: snap.visibleTextSummary,
      focusedElement: {},
      actions,
      blockers: [
        ...actions.filter((item) => item.status === 'blocked_human_required').map((item) => item.reason),
        ...pageBlockers,
      ],
      redactionReport: {formValues: 'redacted', secretsStored: false},
      discoveryCandidates,
      evidenceRefs: [],
    };
  } finally {
    await browser.close();
  }
}



export async function runBrowserReplay(options = {}) {
  const playbook = options.playbook || {};
  const startUrl = normalizeStartUrl(options.startUrl || playbook.startUrl || playbook.url || 'https://www.google.com/');
  const expectedOrigin = safeText(playbook.origin, 300) || originFromUrl(startUrl);
  const values = options.values || {};
  const actions = [];
  const launchOptions = {headless: options.headless !== false, args: DEFAULT_CHROMIUM_ARGS};
  const executablePath = safeText(options.executablePath || process.env.HOME_CENTER_CHROMIUM_EXECUTABLE, 1000);
  if (executablePath) launchOptions.executablePath = executablePath;
  const browser = await chromium.launch(launchOptions);
  try {
    const context = await browser.newContext({viewport: DEFAULT_VIEWPORT, isMobile: false, hasTouch: false, locale: 'en-US'});
    const page = await context.newPage();
    await page.goto(startUrl, {waitUntil: 'domcontentloaded', timeout: Number(options.timeoutMs || 30000)});
    const actualOrigin = originFromUrl(page.url());
    if (expectedOrigin && actualOrigin !== expectedOrigin) {
      return {ok: false, status: 'origin_drift', reason: `Expected ${expectedOrigin}, got ${actualOrigin}.`, actions};
    }
    for (const action of Array.isArray(playbook.actions) ? playbook.actions : []) {
      const blocked = blockUnsafeAction(action);
      if (blocked.blocked) {
        actions.push({type: safeText(action.type, 80), status: 'blocked_human_required', reason: blocked.reason, safetyGate: true});
        continue;
      }
      if (action.type === 'wait') {
        await page.waitForTimeout(Math.max(0, Math.min(Number(action.ms || 1000), 10000)));
        actions.push({type: 'wait', ms: Number(action.ms || 1000), status: 'ok'});
        continue;
      }
      if (action.type === 'press') {
        await page.keyboard.press(String(action.key || 'Enter'));
        actions.push({type: 'press', key: action.key || 'Enter', status: 'ok'});
        continue;
      }
      const found = await locatorFromSelectorLadder(page, action.selectorLadder);
      if (!found) {
        actions.push({type: safeText(action.type, 80), status: 'selector_drift', reason: 'No selector in ladder matched a visible element.'});
        return {ok: false, status: 'selector_drift', actions};
      }
      if (action.type === 'fill') {
        const value = action.valueKey ? values[action.valueKey] : action.value;
        await found.locator.fill(String(value || ''), {timeout: 5000});
        actions.push({type: 'fill', selectedBy: found.selector, selectorKind: found.kind, valueRedacted: '[redacted]', status: 'ok'});
      } else if (action.type === 'click') {
        await found.locator.click({timeout: 5000});
        actions.push({type: 'click', selectedBy: found.selector, selectorKind: found.kind, status: 'ok'});
      }
    }
    const snap = await snapshotPage(page);
    return {
      ok: !actions.some((item) => item.status === 'selector_drift' || item.status === 'blocked_human_required') && !detectPageBlockers(snap).length,
      status: actions.some((item) => item.status === 'blocked_human_required') ? 'blocked_human_required' : 'replayed',
      taskKey: normalizeTaskKey(playbook.taskKey || options.taskKey),
      origin: originFromUrl(page.url()),
      url: page.url(),
      title: snap.title,
      actions,
      visibleTextSummary: snap.visibleTextSummary,
      blockers: detectPageBlockers(snap),
    };
  } finally {
    await browser.close();
  }
}

export async function writeEpisodeArtifact(episode, outDir = '') {
  const dir = outDir || path.join(repoRoot, 'generated', 'browser-worker');
  await fs.mkdir(dir, {recursive: true});
  const file = path.join(dir, `${episode.sessionId}.json`);
  await fs.writeFile(file, JSON.stringify(episode, null, 2) + '\n');
  return file;
}
