import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import puppeteer from 'puppeteer-core';
import {executeAction, extractAction, resultPrompt, safeText, workerInstruction} from './protocol.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');
const stateRoot = process.env.CHROMIUM_THRONE_HOME || path.join(process.env.LOCALAPPDATA || process.cwd(), 'HomeCenter', 'ChromiumThrone');
const statePath = path.join(stateRoot, 'state.json');
const profilePath = path.join(stateRoot, 'chrome-profile');
const logPath = path.join(stateRoot, 'throne.log');
const debugPort = Number(process.env.CHROMIUM_THRONE_DEBUG_PORT || 9231);
const httpPort = Number(process.env.CHROMIUM_THRONE_HTTP_PORT || 17373);
const browserURL = `http://127.0.0.1:${debugPort}`;
const chatUrl = process.env.CHROMIUM_THRONE_CHAT_URL || 'https://chatgpt.com/';
const MAX_STEPS = Number(process.env.CHROMIUM_THRONE_MAX_STEPS || 80);

const state = {
  version: 1,
  startedAt: new Date().toISOString(),
  browser: {connected: false, debugPort, profilePath, executable: ''},
  tasks: [],
  activeTaskId: '',
  lastError: '',
};

async function persist() {
  await fs.mkdir(stateRoot, {recursive: true});
  const tmp = `${statePath}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(state, null, 2), 'utf8');
  await fs.rename(tmp, statePath);
}

async function log(message) {
  await fs.mkdir(stateRoot, {recursive: true});
  const line = `${new Date().toISOString()} ${message}\n`;
  await fs.appendFile(logPath, line, 'utf8').catch(() => {});
}

async function loadState() {
  try {
    const saved = JSON.parse(await fs.readFile(statePath, 'utf8'));
    if (Array.isArray(saved.tasks)) state.tasks = saved.tasks;
    for (const task of state.tasks) {
      if (task.status === 'running') task.status = 'queued';
    }
  } catch {}
}

async function exists(file) { try { await fs.access(file); return true; } catch { return false; } }

async function findBrowserExecutable() {
  const candidates = [
    process.env.CHROMIUM_THRONE_CHROME_PATH,
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
  ].filter(Boolean);
  for (const candidate of candidates) if (await exists(candidate)) return candidate;
  throw new Error('No Chrome or Edge executable found. Set CHROMIUM_THRONE_CHROME_PATH.');
}

async function cdpAlive() {
  try {
    const response = await fetch(`${browserURL}/json/version`, {signal: AbortSignal.timeout(1200)});
    return response.ok;
  } catch { return false; }
}

async function ensureBrowser() {
  await fs.mkdir(profilePath, {recursive: true});
  if (!(await cdpAlive())) {
    const executable = await findBrowserExecutable();
    state.browser.executable = executable;
    const child = spawn(executable, [
      `--remote-debugging-port=${debugPort}`,
      '--remote-debugging-address=127.0.0.1',
      `--user-data-dir=${profilePath}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--force-renderer-accessibility',
      chatUrl,
    ], {detached: true, stdio: 'ignore', windowsHide: false});
    child.unref();
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline && !(await cdpAlive())) await new Promise((r) => setTimeout(r, 250));
    if (!(await cdpAlive())) throw new Error('Chromium launched but CDP did not become reachable.');
  }
  state.browser.connected = true;
  await persist();
}

async function connectBrowser() {
  await ensureBrowser();
  return await puppeteer.connect({browserURL, defaultViewport: null});
}

async function getWorkerPage(browser, taskId) {
  const marker = `chromium-throne:${taskId}`;
  for (const page of await browser.pages()) {
    try { if (await page.evaluate(() => window.name) === marker) return page; } catch {}
  }
  const page = await browser.newPage();
  await page.goto(chatUrl, {waitUntil: 'domcontentloaded', timeout: 30000});
  await page.evaluate((name) => { window.name = name; }, marker);
  return page;
}

async function findComposer(page) {
  const selectors = ['#prompt-textarea', 'textarea[placeholder*="Message"]', 'textarea', '[contenteditable="true"][data-virtualkeyboard="true"]', 'div[contenteditable="true"]'];
  for (const selector of selectors) {
    const handle = await page.$(selector);
    if (handle) return {selector, handle};
  }
  throw new Error('ChatGPT composer not found. The dedicated Chromium profile may need login, or the page DOM changed.');
}

async function fillComposer(page, text) {
  const {handle} = await findComposer(page);
  await handle.evaluate((el, value) => {
    el.focus();
    if ('value' in el) {
      const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value')?.set;
      if (setter) setter.call(el, value); else el.value = value;
      el.dispatchEvent(new Event('input', {bubbles: true}));
      el.dispatchEvent(new Event('change', {bubbles: true}));
    } else {
      el.textContent = value;
      el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: value}));
    }
  }, text);
}

async function clickSend(page) {
  const selectors = ['button[data-testid="send-button"]', 'button[aria-label*="Send"]', 'button[aria-label*="send"]'];
  for (const selector of selectors) {
    const button = await page.$(selector);
    if (button) { await button.click(); return; }
  }
  await page.keyboard.press('Enter');
}

async function assistantMessages(page) {
  return await page.evaluate(() => {
    const direct = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
    if (direct.length) return direct.map((el) => (el.innerText || el.textContent || '').trim()).filter(Boolean);
    const turns = [...document.querySelectorAll('article')];
    return turns.map((el) => (el.innerText || el.textContent || '').trim()).filter(Boolean);
  });
}

async function sendAndWait(page, text, timeoutMs = 8 * 60 * 1000) {
  const before = (await assistantMessages(page)).length;
  await fillComposer(page, text);
  await clickSend(page);
  const deadline = Date.now() + timeoutMs;
  let last = '';
  let stable = 0;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1500));
    const messages = await assistantMessages(page);
    const candidate = messages.length > before ? messages.at(-1) || '' : '';
    const stopVisible = await page.$('button[aria-label*="Stop"], button[data-testid="stop-button"]');
    if (candidate && candidate === last && !stopVisible) stable += 1; else stable = 0;
    last = candidate || last;
    if (last && stable >= 2) return last;
  }
  throw new Error('Timed out waiting for ChatGPT worker response.');
}

function taskById(id) { return state.tasks.find((task) => task.id === id); }

async function executeTask(task) {
  task.status = 'running';
  task.startedAt = task.startedAt || new Date().toISOString();
  task.updatedAt = new Date().toISOString();
  task.steps = Array.isArray(task.steps) ? task.steps : [];
  state.activeTaskId = task.id;
  await persist();
  const browser = await connectBrowser();
  try {
    const page = await getWorkerPage(browser, task.id);
    if (!page.url().startsWith('https://chatgpt.com/')) await page.goto(chatUrl, {waitUntil: 'domcontentloaded', timeout: 30000});
    let response = await sendAndWait(page, workerInstruction({task: task.prompt, repoRoot: task.repoRoot}));
    for (let index = task.steps.length; index < MAX_STEPS; index += 1) {
      const action = extractAction(response);
      if (!action) {
        response = await sendAndWait(page, 'Your previous response did not end with a valid <THRONE_ACTION> JSON envelope. Continue the task and end with exactly one valid action.');
        continue;
      }
      let result;
      try {
        result = await executeAction(task.repoRoot, action);
      } catch (error) {
        result = {ok: false, type: action.type || '', error: safeText(error?.stack || error)};
      }
      task.steps.push({index, at: new Date().toISOString(), action: {...action, content: action.type === 'write_file' ? `[${Buffer.byteLength(String(action.content || ''), 'utf8')} bytes]` : action.content}, result});
      task.updatedAt = new Date().toISOString();
      await persist();
      if (result.finished) {
        task.status = String(result.summary || '').startsWith('HUMAN_GATE:') ? 'human_gate' : 'done';
        task.summary = result.summary;
        task.completedAt = new Date().toISOString();
        await persist();
        return;
      }
      response = await sendAndWait(page, resultPrompt(result));
    }
    throw new Error(`Task exceeded ${MAX_STEPS} throne actions.`);
  } finally {
    state.activeTaskId = '';
    await persist();
    await browser.disconnect().catch(() => {});
  }
}

let pumping = false;
async function pump() {
  if (pumping) return;
  pumping = true;
  try {
    while (true) {
      const task = state.tasks.find((item) => item.status === 'queued');
      if (!task) break;
      try {
        await executeTask(task);
      } catch (error) {
        task.status = 'failed';
        task.error = safeText(error?.stack || error);
        task.updatedAt = new Date().toISOString();
        state.lastError = task.error;
        await log(`task ${task.id} failed: ${task.error}`);
        await persist();
      }
    }
  } finally { pumping = false; }
}

function json(res, status, body) {
  const payload = Buffer.from(JSON.stringify(body, null, 2));
  res.writeHead(status, {'content-type': 'application/json; charset=utf-8', 'content-length': payload.length, 'cache-control': 'no-store'});
  res.end(payload);
}

async function bodyJson(req) {
  let data = '';
  for await (const chunk of req) {
    data += chunk;
    if (data.length > 1024 * 1024) throw new Error('Request body too large.');
  }
  return data ? JSON.parse(data) : {};
}

const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chromium Throne</title><style>body{font:16px system-ui;background:#111;color:#eee;max-width:1100px;margin:auto;padding:24px}textarea,input{width:100%;box-sizing:border-box;background:#1e1e1e;color:#fff;border:1px solid #555;border-radius:8px;padding:10px;margin:6px 0 14px}textarea{min-height:180px}button{background:#eee;color:#111;border:0;border-radius:8px;padding:10px 16px;font-weight:700;cursor:pointer}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:16px;margin:16px 0}.bad{color:#ff9d9d}.good{color:#a8ffb0}code,pre{white-space:pre-wrap;word-break:break-word}</style></head><body><h1>Chromium Throne</h1><p>Bare-metal Home Center worker. Ordinary ChatGPT tabs think; this daemon owns state, files, shell execution, verification, and recovery.</p><div class="card"><label>Repository path</label><input id="repo" placeholder="C:\\path\\to\\repo"><label>Task</label><textarea id="prompt" placeholder="Build the thing. Test it. Do not stop at a plan."></textarea><button id="run">Commission task</button> <button id="login">Open ChatGPT profile</button></div><div id="status"></div><script>async function api(p,o){const r=await fetch(p,o);return await r.json()}async function refresh(){const s=await api('/api/state');let h='<div class="card"><b>Browser:</b> '+(s.browser.connected?'<span class="good">connected</span>':'not connected')+' &nbsp; <b>Active:</b> '+(s.activeTaskId||'none')+'</div>';for(const t of [...s.tasks].reverse()){h+='<div class="card"><b>'+t.id+'</b> — '+t.status+'<br><code>'+esc(t.repoRoot)+'</code><p>'+esc(t.prompt)+'</p><pre>'+esc(t.summary||t.error||((t.steps||[]).length+' actions'))+'</pre></div>'}document.querySelector('#status').innerHTML=h}function esc(x){return String(x||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}document.querySelector('#run').onclick=async()=>{const repoRoot=document.querySelector('#repo').value,prompt=document.querySelector('#prompt').value;const r=await api('/api/tasks',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({repoRoot,prompt})});if(r.error)alert(r.error);refresh()};document.querySelector('#login').onclick=()=>fetch('/api/browser/open',{method:'POST'});refresh();setInterval(refresh,3000)</script></body></html>`;

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://127.0.0.1:${httpPort}`);
    if (req.method === 'GET' && url.pathname === '/') {
      const payload = Buffer.from(html); res.writeHead(200, {'content-type': 'text/html; charset=utf-8', 'content-length': payload.length}); res.end(payload); return;
    }
    if (req.method === 'GET' && url.pathname === '/health') return json(res, 200, {ok: true, contract: 'home-center.chromium-throne.v1', stateRoot, debugPort, httpPort});
    if (req.method === 'GET' && url.pathname === '/api/state') return json(res, 200, state);
    if (req.method === 'POST' && url.pathname === '/api/browser/open') {
      await ensureBrowser();
      const browser = await connectBrowser();
      const page = await browser.newPage();
      await page.goto(chatUrl, {waitUntil: 'domcontentloaded', timeout: 30000});
      await browser.disconnect();
      return json(res, 200, {ok: true});
    }
    if (req.method === 'POST' && url.pathname === '/api/tasks') {
      const input = await bodyJson(req);
      const repoRoot = path.resolve(String(input.repoRoot || ''));
      if (!input.repoRoot || !(await exists(repoRoot))) return json(res, 400, {error: 'Repository path does not exist.'});
      if (!safeText(input.prompt, 20000).trim()) return json(res, 400, {error: 'Task prompt is required.'});
      const task = {id: `task-${Date.now()}`, repoRoot, prompt: safeText(input.prompt, 20000), status: 'queued', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), steps: []};
      state.tasks.push(task); await persist(); setImmediate(() => pump()); return json(res, 202, task);
    }
    if (req.method === 'POST' && url.pathname.startsWith('/api/tasks/') && url.pathname.endsWith('/retry')) {
      const id = url.pathname.split('/')[3]; const task = taskById(id); if (!task) return json(res, 404, {error: 'Task not found.'});
      task.status = 'queued'; task.error = ''; task.updatedAt = new Date().toISOString(); await persist(); setImmediate(() => pump()); return json(res, 202, task);
    }
    return json(res, 404, {error: 'Not found'});
  } catch (error) {
    await log(error?.stack || String(error));
    return json(res, 500, {error: safeText(error?.message || error)});
  }
});

await loadState();
await persist();
server.listen(httpPort, '127.0.0.1', async () => {
  await log(`Chromium Throne listening on http://127.0.0.1:${httpPort}`);
  console.log(`Chromium Throne: http://127.0.0.1:${httpPort}`);
  setImmediate(() => pump());
});
