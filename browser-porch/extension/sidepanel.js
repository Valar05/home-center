/* global chrome */
'use strict';

const $ = (id) => document.getElementById(id);
const commission = $('commission');
const newWorker = $('newWorker');
const status = $('status');
const queueNode = $('queue');
const output = $('output');

$('enqueue').addEventListener('click', enqueue);
$('run').addEventListener('click', () => dispatch(commission.value, newWorker.checked));
$('runNext').addEventListener('click', runNext);
$('capture').addEventListener('click', capture);
$('stop').addEventListener('click', () => message({type: 'throne.stop'}));
$('resume').addEventListener('click', () => message({type: 'throne.resume'}));

init();

async function init() {
  const saved = await chrome.storage.local.get(['throneQueue', 'throneDraft']);
  commission.value = saved.throneDraft || '';
  commission.addEventListener('input', () => chrome.storage.local.set({throneDraft: commission.value}));
  await renderQueue(saved.throneQueue || []);
  const result = await message({type: 'throne.status'}, false);
  if (result?.ok) status.textContent = result.tab?.usable ? `${result.bootPhrase} · tab ready` : 'Open chatgpt.com in this tab';
}

async function enqueue() {
  const text = commission.value.trim();
  if (!text) return show('Commission is empty.');
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  throneQueue.push({id: crypto.randomUUID(), commission: text, newWorker: newWorker.checked, state: 'queued', queuedAt: new Date().toISOString()});
  await chrome.storage.local.set({throneQueue, throneDraft: ''});
  commission.value = '';
  await renderQueue(throneQueue);
}

async function runNext() {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const index = throneQueue.findIndex((job) => job.state === 'queued');
  if (index < 0) return show('Queue is empty.');
  const job = throneQueue[index];
  throneQueue[index] = {...job, state: 'dispatching', startedAt: new Date().toISOString()};
  await chrome.storage.local.set({throneQueue});
  await renderQueue(throneQueue);
  const result = await dispatch(job.commission, job.newWorker, false);
  const refreshed = (await chrome.storage.local.get('throneQueue')).throneQueue || throneQueue;
  const row = refreshed.findIndex((x) => x.id === job.id);
  if (row >= 0) refreshed[row] = {...refreshed[row], state: result?.ok ? 'sent' : 'failed', finishedAt: new Date().toISOString(), error: result?.error || ''};
  await chrome.storage.local.set({throneQueue: refreshed});
  await renderQueue(refreshed);
}

async function dispatch(text, fresh, clear = true) {
  const value = String(text || '').trim();
  if (!value) { show('Commission is empty.'); return {ok: false, error: 'Commission is empty'}; }
  const result = await message({type: 'throne.run', commission: value, newWorker: fresh});
  if (result?.ok && clear) {
    commission.value = '';
    await chrome.storage.local.set({throneDraft: ''});
  }
  return result;
}

async function capture() {
  return message({type: 'throne.capture'});
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
    title.textContent = `${index + 1}. ${job.state}`;
    const body = document.createElement('div');
    body.textContent = job.commission.length > 220 ? `${job.commission.slice(0, 220)}…` : job.commission;
    row.append(title, body);
    queueNode.append(row);
  }
  if (!queue.length) queueNode.textContent = 'No queued commissions.';
}
