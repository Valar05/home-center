import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import puppeteer from 'puppeteer-core';

const DEBUG_PORT = Number.parseInt(process.env.BROWSER_NERVE_DEBUG_PORT || '9223', 10);
const ROOT = process.env.BROWSER_NERVE_ROOT || path.join(process.env.LOCALAPPDATA || process.cwd(), 'HomeCenter', 'BrowserNerve');
const PROFILE = process.env.BROWSER_NERVE_PROFILE || path.join(ROOT, 'chrome-profile');
const BROWSER_URL = `http://127.0.0.1:${DEBUG_PORT}`;
const MAX_ATTEMPTS = 2;

function fail(message) { throw new Error(message); }
function httpUrl(raw) {
  const url = new URL(String(raw || ''));
  if (!['http:', 'https:'].includes(url.protocol)) fail('login URL must be http/https');
  return url;
}
function selector(value, label) {
  const text = String(value || '').trim();
  if (!text || text.length > 1000) fail(`${label} selector required`);
  return text;
}
async function exists(file) { try { await fs.access(file); return true; } catch { return false; } }
async function executable() {
  const candidates = [
    process.env.BROWSER_NERVE_CHROME_PATH,
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
  ].filter(Boolean);
  for (const item of candidates) if (await exists(item)) return item;
  fail('supported Chrome/Edge executable not found');
}
async function cdpAlive() {
  try { const r = await fetch(`${BROWSER_URL}/json/version`, {signal: AbortSignal.timeout(1200)}); return r.ok; }
  catch { return false; }
}
async function ensureBrowser() {
  await fs.mkdir(PROFILE, {recursive: true});
  if (await cdpAlive()) return;
  const bin = await executable();
  const child = spawn(bin, [
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
  while (Date.now() < deadline && !(await cdpAlive())) await new Promise((r) => setTimeout(r, 250));
  if (!(await cdpAlive())) fail('Adam browser profile did not become reachable');
}
function validateLease(lease, origin) {
  if (!lease || lease.schema !== 'adam-login-lease-v1') fail('explicit login lease required');
  if (lease.permission !== 'login_with_autofill') fail('wrong login lease permission');
  if (String(lease.origin || '') !== origin) fail('login lease origin mismatch');
  if (!lease.explicitUserAuthorization) fail('login lease lacks explicit user authorization');
  if (Number(lease.expiresAtMs || 0) <= Date.now()) fail('login lease expired');
  const attempts = Number(lease.maxAttempts || 1);
  if (!Number.isInteger(attempts) || attempts < 1 || attempts > MAX_ATTEMPTS) fail('login lease attempts out of bounds');
  return attempts;
}
async function nonEmpty(page, css) {
  return page.$eval(css, (el) => !!('value' in el && String(el.value || '').length));
}
async function focusAndOfferAutofill(page, css) {
  await page.click(css);
  // Browser/password-manager UI remains native. Keyboard selection asks the browser to use its own saved credential.
  await page.keyboard.press('ArrowDown').catch(() => {});
  await page.keyboard.press('Enter').catch(() => {});
  await new Promise((r) => setTimeout(r, 450));
}
async function execute(input) {
  const url = httpUrl(input.url);
  const attempts = validateLease(input.lease, url.origin);
  const userSelector = selector(input.usernameSelector, 'username');
  const passSelector = selector(input.passwordSelector, 'password');
  const submitSelector = selector(input.submitSelector, 'submit');
  await ensureBrowser();
  const browser = await puppeteer.connect({browserURL: BROWSER_URL, defaultViewport: null});
  try {
    const pages = await browser.pages();
    const page = pages.find((p) => p.url() === url.toString()) || await browser.newPage();
    page.setDefaultTimeout(12000);
    await page.goto(url.toString(), {waitUntil: 'domcontentloaded', timeout: 30000});
    const beforeUrl = page.url();
    let userFilled = false, passFilled = false, usedAttempt = 0;
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      usedAttempt = attempt;
      await page.waitForSelector(userSelector, {visible: true});
      await page.waitForSelector(passSelector, {visible: true});
      await focusAndOfferAutofill(page, userSelector);
      userFilled = await nonEmpty(page, userSelector);
      await focusAndOfferAutofill(page, passSelector);
      passFilled = await nonEmpty(page, passSelector);
      if (userFilled && passFilled) break;
    }
    if (!userFilled || !passFilled) fail('browser autofill did not populate both credential fields');
    await page.click(submitSelector);
    await page.waitForNetworkIdle({idleTime: 300, timeout: 5000}).catch(() => {});
    const afterUrl = page.url();
    const passwordStillPresent = await page.$(passSelector).then(Boolean).catch(() => false);
    return {
      ok: true,
      schema: 'adam-autofill-login-receipt-v1',
      origin: url.origin,
      explicitUserAuthorization: true,
      usedAttempt,
      credentialFieldNonEmpty: {username: userFilled, password: passFilled},
      submitted: true,
      urlChanged: beforeUrl !== afterUrl,
      passwordFieldStillPresent: passwordStillPresent,
      finalOrigin: httpUrl(afterUrl).origin,
      secretsReturned: false,
      cookiesReturned: false,
      valuesReturned: false,
    };
  } finally { browser.disconnect(); }
}

const inputPath = process.argv[2];
if (!inputPath) fail('usage: node adam-autofill-login.mjs input.json');
try {
  const input = JSON.parse(await fs.readFile(inputPath, 'utf8'));
  process.stdout.write(`${JSON.stringify(await execute(input))}\n`);
} catch (error) {
  process.stdout.write(`${JSON.stringify({ok:false,schema:'adam-autofill-login-receipt-v1',error:String(error?.message || error).slice(0,1200),secretsReturned:false,valuesReturned:false})}\n`);
  process.exitCode = 2;
}
