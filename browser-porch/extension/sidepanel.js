/* global chrome */
'use strict';

const $ = (id) => document.getElementById(id);
const context = $('context');
const commission = $('commission');
const newWorker = $('newWorker');
const status = $('status');
const queueNode = $('queue');
const output = $('output');
const MAX_SWARM_SLICES = 12;
const HANDOFF_FIELDS = [
  'DURABLE CONTEXT',
  'COMPLETED EVIDENCE',
  'CURRENT SLICE',
  'UNMET ACCEPTANCE',
  'ACTIVE CONSTRAINTS',
  'EXACT NEXT ACTION',
];

let swarmRunning = false;

$('enqueue').addEventListener('click', enqueue);
$('run').addEventListener('click', () => dispatch(commission.value, newWorker.checked, context.value));
$('runNext').addEventListener('click', () => runNext(false));
$('runSwarm').addEventListener('click', runSwarm);
$('capture').addEventListener('click', capture);
$('resetContext').addEventListener('click', resetContext);
$('stop').addEventListener('click', async () => {
  swarmRunning = false;
  await message({type: 'throne.stop'});
});
$('resume').addEventListener('click', () => message({type: 'throne.resume'}));

init();

async function init() {
  const saved = await chrome.storage.local.get(['throneQueue', 'throneDraft', 'throneContext']);
  commission.value = saved.throneDraft || '';
  commission.addEventListener('input', () => chrome.storage.local.set({throneDraft: commission.value}));
  context.addEventListener('input', () => chrome.storage.local.set({throneContext: context.value}));
  await renderQueue(saved.throneQueue || []);
  const result = await message({type: 'throne.status'}, false);
  if (result?.ok) {
    context.value = saved.throneContext || result.context || result.defaultContext || '';
    if (!saved.throneContext && context.value) await chrome.storage.local.set({throneContext: context.value});
    status.textContent = result.tab?.usable ? `${result.bootPhrase} · tab ready` : 'Open chatgpt.com in this tab';
  }
}

async function resetContext() {
  const result = await message({type: 'throne.resetContext'});
  if (result?.ok) context.value = result.context || '';
}

async function enqueue() {
  const text = commission.value.trim();
  if (!text) return show('Commission is empty.');
  const campaignContext = context.value.trim();
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  throneQueue.push(newJob(text, campaignContext, newWorker.checked, 'manual'));
  await chrome.storage.local.set({throneQueue, throneDraft: '', throneContext: campaignContext});
  commission.value = '';
  await renderQueue(throneQueue);
}

function newJob(text, campaignContext, fresh = true, source = 'manual') {
  return {
    id: crypto.randomUUID(),
    commission: String(text || '').trim(),
    context: String(campaignContext || '').trim(),
    newWorker: fresh !== false,
    source,
    state: 'queued',
    queuedAt: new Date().toISOString(),
  };
}

async function runNext(fromSwarm = false) {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const index = throneQueue.findIndex((job) => job.state === 'queued');
  if (index < 0) {
    if (!fromSwarm) show('Queue is empty.');
    return null;
  }
  const job = throneQueue[index];
  throneQueue[index] = {...job, state: 'dispatching', startedAt: new Date().toISOString()};
  await chrome.storage.local.set({throneQueue});
  await renderQueue(throneQueue);

  const result = await dispatch(job.commission, job.newWorker, job.context || context.value, false);
  const refreshed = (await chrome.storage.local.get('throneQueue')).throneQueue || throneQueue;
  const row = refreshed.findIndex((x) => x.id === job.id);
  if (row >= 0) {
    refreshed[row] = {
      ...refreshed[row],
      state: result?.ok ? 'sent' : 'failed',
      dispatchReceipt: result?.receipt || null,
      finishedAt: new Date().toISOString(),
      error: result?.error || '',
    };
  }
  await chrome.storage.local.set({throneQueue: refreshed});
  await renderQueue(refreshed);
  return result?.ok ? {job: refreshed[row], receipt: result.receipt} : null;
}

async function dispatch(text, fresh, campaignContext, clear = true) {
  const value = String(text || '').trim();
  if (!value) {
    show('Commission is empty.');
    return {ok: false, error: 'Commission is empty'};
  }
  const result = await message({
    type: 'throne.run',
    commission: value,
    context: String(campaignContext || '').trim(),
    newWorker: fresh,
  });
  if (result?.ok && clear) {
    commission.value = '';
    await chrome.storage.local.set({throneDraft: '', throneContext: context.value});
  }
  return result;
}

async function nextQueuedJob() {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  return throneQueue.find((job) => job.state === 'queued') || null;
}

async function runSwarm() {
  if (swarmRunning) return show('Swarm already running.');
  swarmRunning = true;
  status.textContent = 'swarm running · bounded Instant slices';
  const receipts = [];
  try {
    for (let slice = 1; slice <= MAX_SWARM_SLICES && swarmRunning; slice += 1) {
      const queued = await nextQueuedJob();
      if (!queued) {
        receipts.push({slice, state: 'queue_empty'});
        break;
      }
      const before = queued.newWorker ? {assistantCount: 0} : await inspectConversation();
      const dispatched = await runNext(true);
      if (!dispatched) {
        receipts.push({slice, state: 'dispatch_failed'});
        break;
      }

      const baseline = Number(before.assistantCount || 0);
      const checkpoint = await waitForCompletedAssistant(baseline);
      if (!checkpoint.ok) {
        await markJob(dispatched.job.id, 'choked_unreadable', {error: checkpoint.error});
        receipts.push({slice, state: 'choked_unreadable', error: checkpoint.error});
        break;
      }

      const handoff = parseHandoff(checkpoint.text);
      await recordSwarmReceipt({
        type: 'swarm_checkpoint',
        slice,
        jobId: dispatched.job.id,
        at: new Date().toISOString(),
        text: checkpoint.text,
        handoff,
      });

      if (handoff) {
        const nextContext = mergeHandoffContext(dispatched.job.context || context.value, handoff);
        context.value = nextContext;
        const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
        throneQueue.push(newJob(handoff['EXACT NEXT ACTION'], nextContext, true, 'handoff'));
        await chrome.storage.local.set({throneQueue, throneContext: nextContext});
        await markJob(dispatched.job.id, 'handed_off', {handoff});
        await renderQueue(throneQueue);
        receipts.push({slice, state: 'handed_off', next: handoff['EXACT NEXT ACTION']});
        continue;
      }

      await markJob(dispatched.job.id, 'completed', {checkpoint: checkpoint.text});
      receipts.push({slice, state: 'completed'});
    }
  } finally {
    swarmRunning = false;
    const ready = await message({type: 'throne.status'}, false);
    status.textContent = ready?.tab?.usable ? `${ready.bootPhrase} · tab ready` : 'Open chatgpt.com in this tab';
    show({ok: true, swarm: receipts});
  }
}

async function markJob(jobId, state, extra = {}) {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const index = throneQueue.findIndex((job) => job.id === jobId);
  if (index >= 0) throneQueue[index] = {...throneQueue[index], state, ...extra, updatedAt: new Date().toISOString()};
  await chrome.storage.local.set({throneQueue});
  await renderQueue(throneQueue);
}

async function capture() {
  const result = await message({type: 'throne.capture'});
  if (result?.ok) {
    const handoff = parseHandoff(result.receipt?.text || '');
    if (handoff) show({ok: true, checkpoint: result.receipt, handoff});
  }
  return result;
}

async function waitForCompletedAssistant(baselineCount, timeoutMs = 10 * 60 * 1000) {
  const started = Date.now();
  let lastText = '';
  let stablePolls = 0;
  while (Date.now() - started < timeoutMs && swarmRunning) {
    const peek = await inspectConversation();
    if (peek.ok && peek.assistantCount > baselineCount && peek.text) {
      if (!peek.generating && peek.text === lastText) stablePolls += 1;
      else stablePolls = 0;
      lastText = peek.text;
      if (!peek.generating && stablePolls >= 1) return {ok: true, text: peek.text, assistantCount: peek.assistantCount};
    }
    await sleep(1800);
  }
  return {ok: false, error: swarmRunning ? 'assistant_completion_timeout' : 'swarm_stopped'};
}

async function inspectConversation() {
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab?.id) return {ok: false, error: 'active_tab_missing'};
    const [result] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: inspectChatGpt});
    return result?.result || {ok: false, error: 'conversation_probe_failed'};
  } catch (error) {
    return {ok: false, error: error.message};
  }
}

function inspectChatGpt() {
  const selectors = [
    '[data-message-author-role="assistant"]',
    'article[data-turn="assistant"]',
  ];
  let nodes = [];
  for (const selector of selectors) {
    nodes = [...document.querySelectorAll(selector)];
    if (nodes.length) break;
  }
  const node = nodes.at(-1);
  const text = (node?.innerText || node?.textContent || '').trim();
  const generating = Boolean(
    document.querySelector('button[data-testid="stop-button"], button[aria-label*="stop generating" i], button[aria-label*="stop streaming" i]')
  );
  return {ok: true, assistantCount: nodes.length, text: text.slice(0, 120000), generating};
}

function parseHandoff(text) {
  const source = String(text || '');
  const values = {};
  for (let i = 0; i < HANDOFF_FIELDS.length; i += 1) {
    const field = HANDOFF_FIELDS[i];
    const next = HANDOFF_FIELDS[i + 1];
    const startPattern = new RegExp(`(?:^|\\n)\\s*(?:#{1,6}\\s*)?${escapeRegex(field)}\\s*:?\\s*\\n?`, 'i');
    const start = startPattern.exec(source);
    if (!start) return null;
    const bodyStart = start.index + start[0].length;
    let bodyEnd = source.length;
    if (next) {
      const tail = source.slice(bodyStart);
      const nextPattern = new RegExp(`(?:^|\\n)\\s*(?:#{1,6}\\s*)?${escapeRegex(next)}\\s*:?\\s*\\n?`, 'i');
      const found = nextPattern.exec(tail);
      if (!found) return null;
      bodyEnd = bodyStart + found.index;
    }
    const value = source.slice(bodyStart, bodyEnd).trim();
    if (!value) return null;
    values[field] = value;
  }
  return Object.keys(values).length === HANDOFF_FIELDS.length ? values : null;
}

function mergeHandoffContext(base, handoff) {
  const packet = HANDOFF_FIELDS.slice(0, 5).map((field) => `${field}: ${handoff[field]}`).join('\n');
  const combined = `${String(base || '').trim()}\n\nLATEST WORKER HANDOFF:\n${packet}`.trim();
  return combined.length > 24000 ? combined.slice(combined.length - 24000) : combined;
}

async function recordSwarmReceipt(receipt) {
  const {throneSwarmReceipts = []} = await chrome.storage.local.get('throneSwarmReceipts');
  throneSwarmReceipts.push(receipt);
  if (throneSwarmReceipts.length > 200) throneSwarmReceipts.splice(0, throneSwarmReceipts.length - 200);
  await chrome.storage.local.set({throneSwarmReceipts});
}

async function message(payload, render = true) {
  try {
    const result = await chrome.runtime.sendMessage(payload);
    if (render) show(result);
    return result;
  } catch (error) {
    const result = {ok: false, error: error.message};
    if (render) show(result);
    return result;
  }
}

function show(value) {
  output.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

async function renderQueue(queue) {
  queueNode.replaceChildren();
  for (const [index, job] of queue.entries()) {
    const row = document.createElement('div');
    row.className = 'job';
    const title = document.createElement('strong');
    title.textContent = `${index + 1}. ${job.state}${job.context ? ' · context locked' : ''}${job.source === 'handoff' ? ' · rotated' : ''}`;
    const body = document.createElement('div');
    body.textContent = job.commission.length > 220 ? `${job.commission.slice(0, 220)}…` : job.commission;
    row.append(title, body);
    queueNode.append(row);
  }
  if (!queue.length) queueNode.textContent = 'No queued commissions.';
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
