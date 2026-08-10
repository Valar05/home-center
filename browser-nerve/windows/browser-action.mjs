import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import puppeteer from 'puppeteer-core';

const VERSION = '1.0.0';
const DEBUG_PORT = Number.parseInt(process.env.BROWSER_NERVE_DEBUG_PORT || '9223', 10);
const ROOT = process.env.BROWSER_NERVE_ROOT || path.join(process.env.LOCALAPPDATA || process.cwd(), 'HomeCenter', 'BrowserNerve');
const PROFILE = process.env.BROWSER_NERVE_PROFILE || path.join(ROOT, 'chrome-profile');
const BROWSER_URL = `http://127.0.0.1:${DEBUG_PORT}`;

function safeText(value, max = 12000) {
  const text = value == null ? '' : String(value);
  return text.length > max ? text.slice(0, max) : text;
}
function escapeAttribute(value) { return String(value || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"'); }
function escapeTextSelector(value) { return JSON.stringify(String(value || '')).slice(1, -1); }
function hashText(value) { return createHash('sha256').update(String(value || '')).digest('hex').slice(0, 16); }
function encodeRef(selector) { return `bn1.${Buffer.from(selector, 'utf8').toString('base64url')}`; }
function decodeRef(ref) {
  const value = String(ref || '');
  if (!value.startsWith('bn1.')) return '';
  try { return Buffer.from(value.slice(4), 'base64url').toString('utf8'); } catch { return ''; }
}
function requireHttpUrl(value) {
  const url = new URL(String(value || ''));
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Browser Nerve navigation only accepts http/https URLs.');
  return url.toString();
}

async function exists(file) { try { await fs.access(file); return true; } catch { return false; } }
async function findBrowserExecutable() {
  const candidates = [
    process.env.BROWSER_NERVE_CHROME_PATH,
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
  ].filter(Boolean);
  for (const candidate of candidates) if (await exists(candidate)) return candidate;
  throw new Error('No supported Chrome/Edge executable was found. Set BROWSER_NERVE_CHROME_PATH.');
}

async function cdpAlive() {
  try {
    const response = await fetch(`${BROWSER_URL}/json/version`, {signal: AbortSignal.timeout(1200)});
    return response.ok;
  } catch { return false; }
}
async function ensureBrowser() {
  await fs.mkdir(PROFILE, {recursive: true});
  let executable = '';
  if (!(await cdpAlive())) {
    executable = await findBrowserExecutable();
    const child = spawn(executable, [
      `--remote-debugging-port=${DEBUG_PORT}`,
      '--remote-debugging-address=127.0.0.1',
      `--user-data-dir=${PROFILE}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--force-renderer-accessibility',
      'about:blank',
    ], {detached: true, stdio: 'ignore', windowsHide: false});
    child.unref();
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline && !(await cdpAlive())) await new Promise((resolve) => setTimeout(resolve, 250));
    if (!(await cdpAlive())) throw new Error('Chrome started but its loopback DevTools endpoint did not become reachable.');
  }
  return {executable};
}

function selectorForTarget(target = {}) {
  const fromRef = decodeRef(target.ref);
  if (fromRef) return {selector: fromRef, strategy: 'ref'};
  if (target.role && target.name) return {selector: `::-p-aria([name="${escapeAttribute(target.name)}"][role="${escapeAttribute(target.role)}"])`, strategy: 'aria-role-name'};
  if (target.testId) return {selector: `[data-testid="${escapeAttribute(target.testId)}"]`, strategy: 'data-testid'};
  if (target.id) return {selector: `[id="${escapeAttribute(target.id)}"]`, strategy: 'id'};
  if (target.selector) return {selector: String(target.selector), strategy: 'css-or-puppeteer-selector'};
  if (target.name) return {selector: `::-p-aria(${escapeTextSelector(target.name)})`, strategy: 'aria-name'};
  if (target.text) return {selector: `::-p-text("${escapeTextSelector(target.text)}")`, strategy: 'text'};
  return {selector: '', strategy: ''};
}

function implicitRole(row) {
  if (row.role) return row.role;
  if (row.tag === 'button') return 'button';
  if (row.tag === 'a' && row.href) return 'link';
  if (row.tag === 'select') return 'combobox';
  if (row.tag === 'textarea') return 'textbox';
  if (row.tag === 'input') {
    if (['button', 'submit', 'reset'].includes(row.type)) return 'button';
    if (row.type === 'checkbox') return 'checkbox';
    if (row.type === 'radio') return 'radio';
    return 'textbox';
  }
  return '';
}
function selectorForObserved(row) {
  if (row.id) return `[id="${escapeAttribute(row.id)}"]`;
  if (row.testId) return `[data-testid="${escapeAttribute(row.testId)}"]`;
  const role = implicitRole(row);
  const name = row.accessibleName;
  if (role && name) return `::-p-aria([name="${escapeAttribute(name)}"][role="${escapeAttribute(role)}"])`;
  if (row.nameAttr) return `[name="${escapeAttribute(row.nameAttr)}"]`;
  if (name) return `::-p-aria(${escapeTextSelector(name)})`;
  if (row.text) return `::-p-text("${escapeTextSelector(row.text.slice(0, 120))}")`;
  return '';
}

async function rawSnapshot(page) {
  const data = await page.evaluate(() => {
    const visible = (el) => {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
    };
    const labelFor = (el) => {
      const labelled = el.getAttribute('aria-label');
      if (labelled) return labelled.trim();
      const labelledBy = el.getAttribute('aria-labelledby');
      if (labelledBy) {
        const text = labelledBy.split(/\s+/).map((id) => document.getElementById(id)?.textContent || '').join(' ').trim();
        if (text) return text;
      }
      if (el.labels?.length) {
        const text = [...el.labels].map((x) => x.textContent || '').join(' ').trim();
        if (text) return text;
      }
      return (el.getAttribute('alt') || el.getAttribute('title') || el.getAttribute('placeholder') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 240);
    };
    const candidates = [...document.querySelectorAll('button,a[href],input,textarea,select,[role],[contenteditable="true"],[data-testid]')]
      .filter(visible).slice(0, 160).map((el) => ({
        tag: el.tagName.toLowerCase(),
        type: (el.getAttribute('type') || '').toLowerCase(),
        role: el.getAttribute('role') || '',
        id: el.id || '',
        testId: el.getAttribute('data-testid') || '',
        nameAttr: el.getAttribute('name') || '',
        href: el.getAttribute('href') || '',
        accessibleName: labelFor(el),
        text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 240),
        disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      }));
    const active = document.activeElement;
    const focused = active && active !== document.body ? {
      tag: active.tagName?.toLowerCase() || '', id: active.id || '', role: active.getAttribute?.('role') || '',
      name: labelFor(active), testId: active.getAttribute?.('data-testid') || '',
    } : {};
    return {
      title: document.title || '', url: location.href,
      visibleText: (document.body?.innerText || '').replace(/\n{3,}/g, '\n\n').slice(0, 12000),
      candidates, focused,
    };
  });
  const elements = data.candidates.map((row) => {
    const selector = selectorForObserved(row);
    const role = implicitRole(row);
    return selector ? {ref: encodeRef(selector), role, name: row.accessibleName, disabled: row.disabled, selectorStrategy: row.id ? 'id' : row.testId ? 'data-testid' : role && row.accessibleName ? 'aria-role-name' : row.nameAttr ? 'name' : 'text'} : null;
  }).filter(Boolean);
  let focusedElement = data.focused || {};
  if (focusedElement && Object.keys(focusedElement).length) {
    const selector = focusedElement.id ? `[id="${escapeAttribute(focusedElement.id)}"]` : focusedElement.testId ? `[data-testid="${escapeAttribute(focusedElement.testId)}"]` : focusedElement.role && focusedElement.name ? `::-p-aria([name="${escapeAttribute(focusedElement.name)}"][role="${escapeAttribute(focusedElement.role)}"])` : '';
    if (selector) focusedElement = {...focusedElement, ref: encodeRef(selector)};
  }
  return {
    title: safeText(data.title, 500), url: safeText(data.url, 1000), visibleTextSummary: safeText(data.visibleText, 12000),
    accessibilitySummary: JSON.stringify({elementCount: elements.length, elements: elements.slice(0, 120)}), focusedElement,
    semanticHash: hashText(`${data.url}\n${data.title}\n${data.visibleText}`), elements,
  };
}

async function pageForSession(browser, sessionId) {
  const marker = `home-center-browser-nerve:${sessionId}`;
  const pages = await browser.pages();
  for (const page of pages) {
    try { if (await page.evaluate(() => window.name) === marker) return page; } catch {}
  }
  const page = await browser.newPage();
  await page.evaluate((name) => { window.name = name; }, marker);
  return page;
}

async function locatedHandle(page, target) {
  const resolved = selectorForTarget(target);
  if (!resolved.selector) throw new Error('This browser action requires a structured target: ref, role+name, testId, id, selector, name, or text.');
  const locator = page.locator(resolved.selector).setTimeout(12000);
  const handle = await locator.waitHandle();
  if (!handle) throw new Error(`Browser target not found using ${resolved.strategy}.`);
  return {locator, handle, resolved};
}

async function execute(ticket) {
  await ensureBrowser();
  const browser = await puppeteer.connect({browserURL: BROWSER_URL, defaultViewport: null});
  try {
    const page = await pageForSession(browser, ticket.sessionId);
    page.setDefaultTimeout(12000);
    page.setDefaultNavigationTimeout(30000);
    const before = await rawSnapshot(page);
    let locatorUsed = '';
    let actionResult = {};
    const target = ticket.target || {};
    const action = String(ticket.action || '').toLowerCase();

    if (action === 'navigate') {
      const url = requireHttpUrl(target.url);
      await page.goto(url, {waitUntil: 'domcontentloaded', timeout: 30000});
      locatorUsed = `url:${url}`;
      actionResult = {navigated: true};
    } else if (action === 'observe') {
      actionResult = {observed: true};
    } else if (action === 'scroll') {
      const resolved = selectorForTarget(target);
      if (resolved.selector) {
        const {handle} = await locatedHandle(page, target);
        await handle.evaluate((el) => el.scrollIntoView({block: 'center', inline: 'nearest'}));
        await handle.dispose();
        locatorUsed = `${resolved.strategy}:${resolved.selector}`;
      }
      const x = Number(target.x || 0); const y = Number(target.y || target.deltaY || 600);
      await page.evaluate(({x, y}) => window.scrollBy(x, y), {x, y});
      actionResult = {scrolled: true};
    } else if (action === 'wait_for') {
      const {handle, resolved} = await locatedHandle(page, target);
      locatorUsed = `${resolved.strategy}:${resolved.selector}`;
      await handle.dispose();
      actionResult = {found: true};
    } else if (action === 'find' || action === 'read') {
      const {handle, resolved} = await locatedHandle(page, target);
      locatorUsed = `${resolved.strategy}:${resolved.selector}`;
      const read = await handle.evaluate((el) => ({text: (el.innerText || el.textContent || '').trim().slice(0, 8000), value: 'value' in el ? String(el.value || '').slice(0, 8000) : ''}));
      await handle.dispose();
      actionResult = action === 'find' ? {found: true, hasText: !!read.text, hasValue: !!read.value} : {readText: read.text, readValue: read.value};
    } else if (action === 'click') {
      const {locator, handle, resolved} = await locatedHandle(page, target);
      locatorUsed = `${resolved.strategy}:${resolved.selector}`;
      await handle.dispose();
      await locator.click();
      await page.waitForNetworkIdle({idleTime: 250, timeout: 1500}).catch(() => {});
      actionResult = {clicked: true};
    } else if (action === 'type') {
      const {locator, handle, resolved} = await locatedHandle(page, target);
      locatorUsed = `${resolved.strategy}:${resolved.selector}`;
      await handle.dispose();
      await locator.fill(String(ticket.value || ''));
      const verifyHandle = await page.locator(resolved.selector).setTimeout(5000).waitHandle();
      const matches = await verifyHandle.evaluate((el, expected) => 'value' in el ? String(el.value) === expected : String(el.textContent || '') === expected, String(ticket.value || ''));
      await verifyHandle.dispose();
      actionResult = {typed: true, valueMatches: !!matches};
      if (!matches) throw new Error('Browser Nerve typed into the target but value readback did not match.');
    } else if (action === 'select') {
      const resolved = selectorForTarget(target);
      if (!resolved.selector) throw new Error('select requires a structured target.');
      locatorUsed = `${resolved.strategy}:${resolved.selector}`;
      const values = Array.isArray(target.values) ? target.values.map(String) : [String(ticket.value || target.value || '')].filter(Boolean);
      const selected = await page.select(resolved.selector, ...values);
      actionResult = {selectedCount: selected.length};
    } else if (action === 'submit') {
      const {handle, resolved} = await locatedHandle(page, target);
      locatorUsed = `${resolved.strategy}:${resolved.selector}`;
      const submitted = await handle.evaluate((el) => {
        const form = el.form || el.closest?.('form');
        if (form) { if (form.requestSubmit) form.requestSubmit(); else form.submit(); return true; }
        if (typeof el.click === 'function') { el.click(); return true; }
        return false;
      });
      await handle.dispose();
      if (!submitted) throw new Error('Target had no form or submit action.');
      await page.waitForNetworkIdle({idleTime: 250, timeout: 2000}).catch(() => {});
      actionResult = {submitted: true};
    } else {
      throw new Error(`Unsupported Browser Nerve action: ${action}`);
    }

    await new Promise((resolve) => setTimeout(resolve, 120));
    const after = await rawSnapshot(page);
    const postcondition = {
      action,
      observedAfter: true,
      urlChanged: before.url !== after.url,
      titleChanged: before.title !== after.title,
      semanticChanged: before.semanticHash !== after.semanticHash,
      ...actionResult,
    };
    if (action === 'navigate') {
      const expected = new URL(requireHttpUrl(target.url));
      const actual = new URL(after.url);
      postcondition.urlMatches = actual.origin === expected.origin && actual.pathname === expected.pathname;
      if (!postcondition.urlMatches) throw new Error(`Navigation postcondition mismatch: expected ${expected.origin}${expected.pathname}, got ${actual.origin}${actual.pathname}.`);
    }
    return {
      ok: true, workerVersion: VERSION, browser: 'chrome-cdp', url: after.url, title: after.title,
      locatorUsed, postcondition, accessibilitySummary: after.accessibilitySummary,
      visibleTextSummary: after.visibleTextSummary, focusedElement: after.focusedElement,
    };
  } finally {
    browser.disconnect();
  }
}

async function main() {
  const inputPath = process.argv[2];
  if (!inputPath) throw new Error('Usage: node browser-action.mjs <ticket.json>');
  const ticket = JSON.parse(await fs.readFile(inputPath, 'utf8'));
  try {
    const result = await execute(ticket);
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({ok: false, workerVersion: VERSION, error: safeText(error?.message || error, 2000)})}\n`);
    process.exitCode = 2;
  }
}

await main();
