/* global chrome */
'use strict';

import {newJob, parseHandoff} from './swarm-core.mjs';

const $ = (id) => document.getElementById(id);
const context = $('context');
const commission = $('commission');
const newWorker = $('newWorker');
const status = $('status');
const queueNode = $('queue');
const output = $('output');

$('enqueue').addEventListener('click', enqueue);
$('run').addEventListener('click', runSingle);
$('runNext').addEventListener('click', runSwarm);
$('runSwarm').addEventListener('click', runSwarm);
$('capture').addEventListener('click', capture);
$('resetContext').addEventListener('click', resetContext);
$('stop').addEventListener('click', () => message({type: 'throne.stop'}));
$('resume').addEventListener('click', () => message({type: 'throne.resume'}));

init();

async function init() {
  const saved = await chrome.storage.local.get(['throneQueue', 'throneDraft', 'throneContext']);
  commission.value = saved.throneDraft || '';
  commission.addEventListener('input', () => chrome.storage.local.set({throneDraft: commission.value}));
  context.addEventListener('input', () => chrome.storage.local.set({throneContext: context.value}));
  await renderQueue(saved.throneQueue || []);
  await refreshStatus(saved.throneContext || '');
}

async function refreshStatus(fallbackContext = '') {
  const result = await message({type: 'throne.status'}, false);
  if (!result?.ok) { status.textContent = 'Chromium Throne unavailable'; return result; }
  context.value = fallbackContext || result.context || result.defaultContext || '';
  status.textContent = `${result.bootPhrase} · ${result.workers?.length || 0} worker tabs${result.relayEnabled ? ' · Atom relay' : ''}${result.stopped ? ' · STOPPED' : ''}`;
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  await renderQueue(throneQueue);
  return result;
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

async function runSingle() {
  const text = commission.value.trim();
  if (!text) return show('Commission is empty.');
  const campaignContext = context.value.trim();
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  throneQueue.push(newJob(text, campaignContext, newWorker.checked, 'manual'));
  await chrome.storage.local.set({throneQueue, throneDraft: '', throneContext: campaignContext});
  commission.value = '';
  return runSwarm();
}

async function runSwarm() {
  status.textContent = 'swarm running · service-worker owned';
  const result = await message({type: 'throne.swarm.run', source: 'sidepanel'});
  await refreshStatus(context.value.trim());
  return result;
}

async function capture() {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const selected = [...throneQueue].reverse().find((job) => Number(job.workerTabId) > 0);
  const result = await message({type: 'throne.capture', workerTabId: selected?.workerTabId || null, jobId: selected?.id || ''});
  if (result?.ok) show({ok: true, checkpoint: result.receipt, handoff: parseHandoff(result.receipt?.text || '')});
  return result;
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

function show(value) { output.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); }

async function renderQueue(queue) {
  queueNode.replaceChildren();
  for (const [index, job] of queue.entries()) {
    const row = document.createElement('div'); row.className = 'job';
    const title = document.createElement('strong');
    title.textContent = `${index + 1}. ${job.state}${job.workerTabId ? ` · tab ${job.workerTabId}` : ''}${job.context ? ' · context locked' : ''}${job.source === 'handoff' ? ' · rotated' : ''}`;
    const body = document.createElement('div'); body.textContent = job.commission.length > 220 ? `${job.commission.slice(0, 220)}…` : job.commission;
    row.append(title, body); queueNode.append(row);
  }
  if (!queue.length) queueNode.textContent = 'No queued commissions.';
}
