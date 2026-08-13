/* global chrome */
'use strict';

const CHATGPT_ORIGIN = 'https://chatgpt.com';
const BOOT_PHRASE = 'PORTCULLIS LOCKED';
const BOOT_ENVELOPE = `${BOOT_PHRASE}.\nYou are a ChatGPT chat-mode Instant execution worker. You are not the campaign brain. Chromium Throne owns continuity; you own one bounded bite.\n\nExecution rules:\n- Preserve the requested outcome, owner, tool, execution lane, exclusions, evidence standard, and delivery surface.\n- Do not silently substitute adjacent tools, architectures, workflows, or weaker evidence.\n- Creativity is allowed only inside the commission boundary; prefer the simplest implementation that satisfies it.\n- Keep requested capability, implemented capability, tested capability, deployed capability, callable capability, delivered capability, and accepted capability distinct.\n- Carry every earlier constraint forward when revising. Never fix one thing by resurrecting a rejected approach.\n- Before asking Drew to execute anything, enumerate and exhaust authorized existing body lanes that can perform it. Computer Hands is the desktop body; Phone Hands is the phone body. Drew's hands are the final fallback.\n- Work ONE small feature, repair, proof, or acceptance slice at a time. No Great War. Do not turn a bounded commission into a campaign rewrite.\n- Every slice needs an explicit done condition. Reach it, produce evidence/checkpoint, then stop expanding scope.\n- Be usefully needy: if the current slice truly lacks one decision or dependency, ask for exactly that missing thing rather than inventing architecture. Do not ask questions whose answers can be retrieved or inferred from durable evidence.\n- Stay inside the current commission even when adjacent improvements look tempting. Proposed adjacent work stays proposed.\n- Watch your own thread health. Repeated misunderstanding, instruction drift, circular retry, bloated context, contradiction, or inability to restate the current slice cleanly means this thread is CHOKED.\n- When CHOKED, do not keep wrestling the same thread. Emit a HANDOFF packet and stop. Chromium Throne will continue the work in a fresh thread.\n- HANDOFF must contain exactly: DURABLE CONTEXT; COMPLETED EVIDENCE; CURRENT SLICE; UNMET ACCEPTANCE; ACTIVE CONSTRAINTS; EXACT NEXT ACTION. Keep it compact and executable.\n- A fresh worker receives PORTCULLIS LOCKED + durable campaign context + the handoff + one bounded next slice. Never assume the next worker remembers this thread.\n- Continue until THIS bounded slice and its acceptance evidence exist, or until a real external/user action is strictly required. Do not wander into later slices just because they are visible.\n- If blocked, report the exact boundary and the smallest irreducible human action. Do not manufacture substitute success.\n- Never use ChatGPT-local scratch/container execution as proof of anything on Drew's hardware.\n- Keep prose terse. Spend effort on execution and verification.\n`;

const DEFAULT_CAMPAIGN_CONTEXT = `CAMPAIGN: Fortress Phone Adam + Desktop Swarm Recovery\nOWNER: Drew Clarke\nMISSION: Atom/Vlad on the phone is the operator surface. Chromium Throne is visible desktop worker muscle behind the Fortress.\nWORKER MODEL: ChatGPT chat-mode Instant. Workers are bounded, attributable, disposable execution threads.\nPRIMARY ARCHITECTURE: Atom/Vlad owns operator continuity; desktop Chromium owns worker tabs; no API-token compute, hidden browser farm, or substitute control plane.\nCANONICAL REPO: Valar05/home-center\nBODY-LANE DOCTRINE: Desktop -> Computer Hands. Phone -> Phone Hands. Operator execution is only for genuine irreducible human boundaries.\nEVIDENCE DOCTRINE: requested / implemented / tested / deployed / callable / delivered / accepted remain distinct.\nTHREAD DOCTRINE: one bounded slice per worker; rotate on choke with compact handoff.\n`;

chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true}).catch(() => {});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handle(message).then(sendResponse, (error) => sendResponse({ok: false, error: error.message}));
  return true;
});

async function handle(message = {}) {
  switch (message.type) {
    case 'throne.status': {
      const {throneContext = DEFAULT_CAMPAIGN_CONTEXT} = await chrome.storage.local.get('throneContext');
      return {
        ok: true,
        bootPhrase: BOOT_PHRASE,
        defaultContext: DEFAULT_CAMPAIGN_CONTEXT,
        context: throneContext,
        tab: await chatTabSummary(),
        workers: await workerTabSummaries(),
      };
    }
    case 'throne.run':
      return runCommission(
        String(message.commission || ''),
        message.newWorker !== false,
        String(message.context || ''),
        {jobId: String(message.jobId || ''), workerTabId: Number(message.workerTabId || 0) || null},
      );
    case 'throne.capture':
      return captureLatest(Number(message.workerTabId || 0) || null, String(message.jobId || ''));
    case 'throne.inspect':
      return inspectWorker(Number(message.workerTabId || 0) || null);
    case 'throne.resetContext':
      await chrome.storage.local.set({throneContext: DEFAULT_CAMPAIGN_CONTEXT});
      return {ok: true, context: DEFAULT_CAMPAIGN_CONTEXT};
    case 'throne.stop':
      await chrome.storage.session.set({throneStopped: true});
      return {ok: true, stopped: true};
    case 'throne.resume':
      await chrome.storage.session.set({throneStopped: false});
      return {ok: true, stopped: false};
    case 'throne.closeWorker': {
      const tabId = Number(message.workerTabId || 0);
      if (!tabId) throw new Error('worker_tab_id_required');
      await chrome.tabs.remove(tabId);
      await appendReceipt({type: 'worker_closed', at: new Date().toISOString(), tabId, jobId: String(message.jobId || '')});
      return {ok: true, tabId};
    }
    default:
      throw new Error(`Unknown Chromium Throne message: ${message.type}`);
  }
}

async function runCommission(commission, newWorker, suppliedContext, identity = {}) {
  if (!commission.trim()) throw new Error('Commission is empty');
  const {throneStopped = false} = await chrome.storage.session.get('throneStopped');
  if (throneStopped) throw new Error('Chromium Throne is stopped');
  const stored = await chrome.storage.local.get('throneContext');
  const context = suppliedContext.trim() || String(stored.throneContext || DEFAULT_CAMPAIGN_CONTEXT).trim();
  const tab = newWorker ? await createWorkerTab() : await requireChatTab(identity.workerTabId);
  const before = await inspectWorker(tab.id);
  const baselineAssistantCount = Number(before.assistantCount || 0);
  const prompt = `${BOOT_ENVELOPE}\nDURABLE CAMPAIGN CONTEXT:\n${context}\n\nCOMMISSION — ONE BOUNDED SLICE:\n${commission.trim()}`;
  const [result] = await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: submitChatGptPrompt,
    args: [prompt],
  });
  if (!result?.result?.ok) throw new Error(result?.result?.error || 'Prompt injection failed');

  const receipt = {
    type: 'commission_sent',
    at: new Date().toISOString(),
    jobId: identity.jobId || '',
    tabId: tab.id,
    url: tab.url || `${CHATGPT_ORIGIN}/`,
    bootPhrase: BOOT_PHRASE,
    workerModel: 'chat-mode Instant',
    slicePolicy: 'one-bounded-slice',
    commission,
    contextChars: context.length,
    promptChars: prompt.length,
    baselineAssistantCount,
    newWorker: Boolean(newWorker),
  };
  await tagWorker(tab.id, {jobId: identity.jobId || '', commission, state: 'commissioned', baselineAssistantCount, commissionedAt: receipt.at});
  await appendReceipt(receipt);
  return {ok: true, receipt, worker: {tabId: tab.id, jobId: identity.jobId || '', baselineAssistantCount}};
}

async function captureLatest(workerTabId = null, jobId = '') {
  const tab = await requireChatTab(workerTabId);
  const [result] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: readLatestAssistant});
  if (!result?.result?.ok) throw new Error(result?.result?.error || 'Could not read latest assistant message');
  const receipt = {
    type: 'assistant_checkpoint',
    at: new Date().toISOString(),
    jobId,
    tabId: tab.id,
    url: tab.url,
    text: result.result.text,
  };
  await tagWorker(tab.id, {jobId, state: 'checkpointed', checkpointAt: receipt.at});
  await appendReceipt(receipt);
  return {ok: true, receipt};
}

async function inspectWorker(workerTabId = null) {
  const tab = await requireChatTab(workerTabId);
  const [result] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: inspectChatGpt});
  return {ok: true, tabId: tab.id, ...(result?.result || {})};
}

async function createWorkerTab() {
  const tab = await chrome.tabs.create({url: `${CHATGPT_ORIGIN}/`, active: false});
  if (!tab?.id) throw new Error('worker_tab_creation_failed');
  await waitForTabComplete(tab.id, 20000);
  return await chrome.tabs.get(tab.id);
}

async function tagWorker(tabId, patch) {
  const {throneWorkers = {}} = await chrome.storage.local.get('throneWorkers');
  throneWorkers[String(tabId)] = {...(throneWorkers[String(tabId)] || {}), tabId, ...patch, updatedAt: new Date().toISOString()};
  await chrome.storage.local.set({throneWorkers});
}

async function appendReceipt(receipt) {
  const {throneReceipts = []} = await chrome.storage.local.get('throneReceipts');
  throneReceipts.push(receipt);
  if (throneReceipts.length > 500) throneReceipts.splice(0, throneReceipts.length - 500);
  await chrome.storage.local.set({throneReceipts});
}

async function workerTabSummaries() {
  const tabs = await chrome.tabs.query({url: `${CHATGPT_ORIGIN}/*`});
  const {throneWorkers = {}} = await chrome.storage.local.get('throneWorkers');
  const liveIds = new Set(tabs.map((tab) => String(tab.id)));
  const summaries = tabs.map((tab) => ({
    tabId: tab.id,
    title: tab.title || 'ChatGPT worker',
    url: tab.url,
    active: Boolean(tab.active),
    ...(throneWorkers[String(tab.id)] || {}),
  }));
  for (const key of Object.keys(throneWorkers)) if (!liveIds.has(key)) delete throneWorkers[key];
  await chrome.storage.local.set({throneWorkers});
  return summaries;
}

async function chatTabSummary() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  return tab ? {id: tab.id, title: tab.title, url: tab.url, usable: isChatGpt(tab.url)} : null;
}

async function requireChatTab(tabId = null) {
  const tab = tabId ? await chrome.tabs.get(tabId) : (await chrome.tabs.query({active: true, currentWindow: true}))[0];
  if (!tab?.id || !isChatGpt(tab.url)) throw new Error('ChatGPT worker tab is missing or no longer usable');
  return tab;
}

function isChatGpt(url) {
  try { return new URL(url).origin === CHATGPT_ORIGIN; } catch { return false; }
}

function waitForTabComplete(tabId, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => finish(new Error('Timed out waiting for ChatGPT tab load')), timeoutMs);
    const listener = (changedId, info) => {
      if (changedId === tabId && info.status === 'complete') finish();
    };
    function finish(error) {
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(listener);
      error ? reject(error) : resolve();
    }
    chrome.tabs.onUpdated.addListener(listener);
    chrome.tabs.get(tabId).then((tab) => { if (tab.status === 'complete') finish(); }).catch(finish);
  });
}

async function submitChatGptPrompt(prompt) {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  let composer;
  for (let i = 0; i < 100; i += 1) {
    composer = document.querySelector('#prompt-textarea, textarea[data-testid="prompt-textarea"], div[contenteditable="true"][data-testid="prompt-textarea"]');
    if (composer) break;
    await sleep(100);
  }
  if (!composer) return {ok: false, error: 'ChatGPT composer not found'};

  composer.focus();
  if (composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement) {
    const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(composer), 'value')?.set;
    if (setter) setter.call(composer, prompt); else composer.value = prompt;
    composer.dispatchEvent(new Event('input', {bubbles: true}));
  } else {
    composer.textContent = prompt;
    composer.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: prompt}));
  }

  await sleep(100);
  const send = document.querySelector('button[data-testid="send-button"], button[aria-label*="send" i]');
  if (send && !send.disabled) {
    send.click();
    return {ok: true, method: 'button'};
  }
  composer.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', bubbles: true}));
  composer.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', bubbles: true}));
  return {ok: true, method: 'enter'};
}

function inspectChatGpt() {
  const selectors = ['[data-message-author-role="assistant"]', 'article[data-turn="assistant"]'];
  let nodes = [];
  for (const selector of selectors) {
    nodes = [...document.querySelectorAll(selector)];
    if (nodes.length) break;
  }
  const node = nodes.at(-1);
  const text = (node?.innerText || node?.textContent || '').trim();
  const generating = Boolean(document.querySelector('button[data-testid="stop-button"], button[aria-label*="stop generating" i], button[aria-label*="stop streaming" i]'));
  return {assistantCount: nodes.length, text: text.slice(0, 120000), generating};
}

function readLatestAssistant() {
  const selectors = [
    '[data-message-author-role="assistant"]',
    'article[data-turn="assistant"]',
    '[data-testid^="conversation-turn-"] .markdown',
  ];
  for (const selector of selectors) {
    const nodes = [...document.querySelectorAll(selector)];
    const node = nodes.at(-1);
    const text = (node?.innerText || node?.textContent || '').trim();
    if (text) return {ok: true, text: text.slice(0, 120000)};
  }
  return {ok: false, error: 'No assistant response found in the selected worker conversation'};
}
