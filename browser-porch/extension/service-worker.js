/* global chrome */
'use strict';

const CHATGPT_ORIGIN = 'https://chatgpt.com';
const BOOT_PHRASE = 'PORTCULLIS LOCKED';
const BOOT_ENVELOPE = `${BOOT_PHRASE}.\nYou are the single persistent ChatGPT Pro-reasoning worker for this Fortress campaign, not a disposable brainstorming partner. The commission below is binding.\n\nExecution rules:\n- Use ChatGPT Pro reasoning for campaign work. If this visible ChatGPT surface is not actually in the Pro reasoning configuration, report that exact capability gap; never pretend Instant is Pro.\n- Preserve the requested outcome, owner, tool, execution lane, exclusions, evidence standard, and delivery surface.\n- Do not silently substitute adjacent tools, architectures, workflows, or weaker evidence.\n- Creativity is allowed only inside the commission boundary; prefer the simplest implementation that satisfies it.\n- Keep requested, implemented, tested, deployed, callable, delivered, accepted, and proposed capability distinct.\n- Carry every earlier constraint forward when revising. Never fix one thing by resurrecting a rejected approach.\n- This conversation is a continuing campaign body. Consume prior checkpoints and receipts before acting; do not rediscover the mission from the operator.\n- Continue until the requested artifact and acceptance evidence exist, or until a real external/user action is strictly required.\n- If your own reasoning identifies a callable next action, consultation, review, recovery, or test, TAKE IT before yielding. Narrating the next action is not continuation.\n- Recording a failure is mandatory but is not the repair. Feed every failure into the active repair/evolution loop and continue.\n- Consult the applicable Harroway/operator and Judgment Jar governance before architecture recommendations or stopping.\n- She-Raw motivational critique is required when available: attack lazy assumptions, brittle machinery, evasions, and turd-polishing with memorable creative insults, but never substitute the joke for execution/evidence and never target a vulnerable person or protected trait.\n- The phone is sovereign. You do not unlock, continuously puppet, or own the phone-control loop. Home Center/Termux/tmux/local authorized machinery executes phone work and returns evidence.\n- Chromium Throne is the Pro reasoning/control conversation, not a second phone-control plane.\n- Do not stop merely because one unit of work completed; re-read the commission and advance the next unmet acceptance criterion.\n- Established operator imperatives such as continue, driver advance, do it, make it so, and don't talk to me mean execute through the authorized lane without a conversational status interlude. They never mean silence-and-stop.\n- Keep prose terse. Spend effort on execution and verification.\n\nCOMMISSION:\n`;

const CONTINUE_ENVELOPE = `${BOOT_PHRASE} CAMPAIGN CONTINUATION.\nStay in this same worker conversation. Preserve all prior constraints, checkpoints, receipts, failures, and learned doctrine. Use Pro reasoning. Consult required governance. Advance the next unmet acceptance criterion now; do not narrate a future action instead of taking it. The phone remains locally sovereign; consume device receipts rather than assuming phone control. She-Raw may roast the work, but the roast must drive a real repair/review action.\n\nNEXT COMMISSION / EVIDENCE:\n`;

chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true}).catch(() => {});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handle(message).then(sendResponse, (error) => sendResponse({ok: false, error: error.message}));
  return true;
});

async function handle(message = {}) {
  switch (message.type) {
    case 'throne.status':
      return {ok: true, bootPhrase: BOOT_PHRASE, tab: await chatTabSummary()};
    case 'throne.run':
      return runCommission(String(message.commission || ''), message.newWorker === true);
    case 'throne.capture':
      return captureLatest();
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

async function runCommission(commission, newWorker) {
  if (!commission.trim()) throw new Error('Commission is empty');
  const {throneStopped = false, throneCampaignStarted = false} = await chrome.storage.session.get(['throneStopped', 'throneCampaignStarted']);
  if (throneStopped) throw new Error('Chromium Throne is stopped');
  const tab = await requireChatTab();

  const startFresh = newWorker || !throneCampaignStarted;
  if (startFresh) {
    await chrome.tabs.update(tab.id, {url: `${CHATGPT_ORIGIN}/`});
    await waitForTabComplete(tab.id, 15000);
  }

  const envelope = startFresh ? BOOT_ENVELOPE : CONTINUE_ENVELOPE;
  const prompt = `${envelope}${commission.trim()}`;
  const [result] = await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: submitChatGptPrompt,
    args: [prompt],
  });
  if (!result?.result?.ok) throw new Error(result?.result?.error || 'Prompt injection failed');

  await chrome.storage.session.set({throneCampaignStarted: true});
  const receipt = {
    type: startFresh ? 'campaign_started' : 'campaign_advanced',
    at: new Date().toISOString(),
    tabId: tab.id,
    url: `${CHATGPT_ORIGIN}/`,
    bootPhrase: BOOT_PHRASE,
    persistentWorker: true,
    proReasoningRequired: true,
    phoneSovereign: true,
    harrowayConsultationRequired: true,
    sheRawMotivationRequired: true,
    commission,
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
