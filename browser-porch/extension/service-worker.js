/* global chrome */
'use strict';

const CHATGPT_ORIGIN = 'https://chatgpt.com';
const BOOT_PHRASE = 'PORTCULLIS LOCKED';
const BOOT_ENVELOPE = `${BOOT_PHRASE}.\nYou are a ChatGPT chat-mode Instant execution worker. You are not the campaign brain. Chromium Throne owns continuity; you own one bounded bite.\n\nExecution rules:\n- Preserve the requested outcome, owner, tool, execution lane, exclusions, evidence standard, and delivery surface.\n- Do not silently substitute adjacent tools, architectures, workflows, or weaker evidence.\n- Creativity is allowed only inside the commission boundary; prefer the simplest implementation that satisfies it.\n- Keep requested capability, implemented capability, tested capability, deployed capability, callable capability, delivered capability, and accepted capability distinct.\n- Carry every earlier constraint forward when revising. Never fix one thing by resurrecting a rejected approach.\n- Before asking Drew to execute anything, enumerate and exhaust authorized existing body lanes that can perform it. Computer Hands is the desktop body; Phone Hands is the phone body. Drew's hands are the final fallback.\n- Work ONE small feature, repair, proof, or acceptance slice at a time. No Great War. Do not turn a bounded commission into a campaign rewrite.\n- Every slice needs an explicit done condition. Reach it, produce evidence/checkpoint, then stop expanding scope.\n- Be usefully needy: if the current slice truly lacks one decision or dependency, ask for exactly that missing thing rather than inventing architecture. Do not ask questions whose answers can be retrieved or inferred from durable evidence.\n- Stay inside the current commission even when adjacent improvements look tempting. Proposed adjacent work stays proposed.\n- Watch your own thread health. Repeated misunderstanding, instruction drift, circular retry, bloated context, contradiction, or inability to restate the current slice cleanly means this thread is CHOKED.\n- When CHOKED, do not keep wrestling the same thread. Emit a HANDOFF packet and stop. Chromium Throne will continue the work in a fresh thread.\n- HANDOFF must contain exactly: DURABLE CONTEXT; COMPLETED EVIDENCE; CURRENT SLICE; UNMET ACCEPTANCE; ACTIVE CONSTRAINTS; EXACT NEXT ACTION. Keep it compact and executable.\n- A fresh worker receives PORTCULLIS LOCKED + durable campaign context + the handoff + one bounded next slice. Never assume the next worker remembers this thread.\n- Continue until THIS bounded slice and its acceptance evidence exist, or until a real external/user action is strictly required. Do not wander into later slices just because they are visible.\n- If blocked, report the exact boundary and the smallest irreducible human action. Do not manufacture substitute success.\n- Never use ChatGPT-local scratch/container execution as proof of anything on Drew's hardware.\n- Keep prose terse. Spend effort on execution and verification.\n`;

const DEFAULT_CAMPAIGN_CONTEXT = `CAMPAIGN: Chromium Throne\nOWNER: Drew Clarke\nMISSION: Deliver a desktop workflow organ that orchestrates ChatGPT work from one visible browser tab plus one Chromium extension.\nWORKER MODEL: ChatGPT chat-mode Instant. Workers are intentionally bounded, needy, disposable execution threads. Chromium Throne owns durable continuity. Give workers one feature/proof slice at a time; no Great War prompts. Cycle threads with compact handoffs when context chokes.\nPRIMARY ARCHITECTURE: local/phone coding remains independently functional; Chromium Throne is optional supplemental desktop ChatGPT compute. Visible browser processes are allowed. No headless browser farm, hidden-process requirement, API-token compute, account rotation, or substitute agent framework.\nCANONICAL REPO: Valar05/home-center\nCURRENT IMPLEMENTATION: browser-porch/extension is the Chromium Throne MV3 extension; tools/install_chromium_throne.ps1 is the installer; PORTCULLIS LOCKED is the worker boot phrase.\nBODY-LANE DOCTRINE: before operator handoff, exhaust configured authorized execution organs. Desktop -> Computer Hands. Phone -> Phone Hands. Browser semantic work -> Browser Nerve when applicable. Operator execution is only for genuine irreducible human boundaries.\nEVIDENCE DOCTRINE: distinguish requested / implemented / tested / deployed / callable / delivered / accepted. Real-machine claims require authoritative real-machine receipts, not local scratch.\nFAILURE GUARD: available_body_lane_ignored is a Fortress failure. Never ask Drew to run a command that an authorized configured body lane can execute.\nTHREAD DOCTRINE: a worker owns one bounded slice. On thread choke, emit DURABLE CONTEXT / COMPLETED EVIDENCE / CURRENT SLICE / UNMET ACCEPTANCE / ACTIVE CONSTRAINTS / EXACT NEXT ACTION, then rotate.\nCURRENT ACCEPTANCE TARGET: Chromium Throne visibly running on the real workstation, extension loaded, one ChatGPT tab visible, side panel open, harmless PORTCULLIS LOCKED commission dispatched, response checkpoint captured, authoritative receipt returned.\n`;

chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true}).catch(() => {});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handle(message).then(sendResponse, (error) => sendResponse({ok: false, error: error.message}));
  return true;
});

async function handle(message = {}) {
  switch (message.type) {
    case 'throne.status': {
      const {throneContext = DEFAULT_CAMPAIGN_CONTEXT} = await chrome.storage.local.get('throneContext');
      return {ok: true, bootPhrase: BOOT_PHRASE, defaultContext: DEFAULT_CAMPAIGN_CONTEXT, context: throneContext, tab: await chatTabSummary()};
    }
    case 'throne.run':
      return runCommission(String(message.commission || ''), message.newWorker !== false, String(message.context || ''));
    case 'throne.capture':
      return captureLatest();
    case 'throne.resetContext':
      await chrome.storage.local.set({throneContext: DEFAULT_CAMPAIGN_CONTEXT});
      return {ok: true, context: DEFAULT_CAMPAIGN_CONTEXT};
    case 'throne.stop':
      await chrome.storage.session.set({throneStopped: true});
      return {ok: true, stopped: true};
    case 'throne.resume':
      await chrome.storage.session.set({throneStopped: false});
      return {ok: true, stopped: false};
    default:
      throw new Error(`Unknown Chromium Throne message: ${message.type}`);
  }
}

async function runCommission(commission, newWorker, suppliedContext) {
  if (!commission.trim()) throw new Error('Commission is empty');
  const {throneStopped = false} = await chrome.storage.session.get('throneStopped');
  if (throneStopped) throw new Error('Chromium Throne is stopped');
  const tab = await requireChatTab();
  const stored = await chrome.storage.local.get('throneContext');
  const context = suppliedContext.trim() || String(stored.throneContext || DEFAULT_CAMPAIGN_CONTEXT).trim();

  if (newWorker) {
    await chrome.tabs.update(tab.id, {url: `${CHATGPT_ORIGIN}/`});
    await waitForTabComplete(tab.id, 15000);
  }

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
    tabId: tab.id,
    url: `${CHATGPT_ORIGIN}/`,
    bootPhrase: BOOT_PHRASE,
    workerModel: 'chat-mode Instant',
    slicePolicy: 'one-bounded-slice',
    commission,
    contextChars: context.length,
    promptChars: prompt.length,
  };
  await appendReceipt(receipt);
  return {ok: true, receipt};
}

async function captureLatest() {
  const tab = await requireChatTab();
  const [result] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: readLatestAssistant});
  if (!result?.result?.ok) throw new Error(result?.result?.error || 'Could not read latest assistant message');
  const receipt = {
    type: 'assistant_checkpoint',
    at: new Date().toISOString(),
    tabId: tab.id,
    url: tab.url,
    text: result.result.text,
  };
  await appendReceipt(receipt);
  return {ok: true, receipt};
}

async function appendReceipt(receipt) {
  const {throneReceipts = []} = await chrome.storage.local.get('throneReceipts');
  throneReceipts.push(receipt);
  if (throneReceipts.length > 200) throneReceipts.splice(0, throneReceipts.length - 200);
  await chrome.storage.local.set({throneReceipts});
}

async function chatTabSummary() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  return tab ? {id: tab.id, title: tab.title, url: tab.url, usable: isChatGpt(tab.url)} : null;
}

async function requireChatTab() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab?.id || !isChatGpt(tab.url)) throw new Error('The single active browser tab must be chatgpt.com');
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
  for (let i = 0; i < 60; i += 1) {
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
  return {ok: false, error: 'No assistant response found in the current conversation'};
}
