/* global chrome */
'use strict';

import {
  MAX_PARALLEL_WORKERS,
  MAX_SWARM_SLICES,
  newJob,
  parallelBatch,
  parseHandoff,
  planHandoffContinuation,
} from './swarm-core.mjs';

const $ = (id) => document.getElementById(id);
const context = $('context');
const commission = $('commission');
const newWorker = $('newWorker');
const status = $('status');
const queueNode = $('queue');
const output = $('output');
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
    status.textContent = `${result.bootPhrase} · ${result.workers?.length || 0} worker tabs`;
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

async function runNext(fromSwarm = false) {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const original = throneQueue.find((job) => job.state === 'queued');
  if (!original) {
    if (!fromSwarm) show('Queue is empty.');
    return null;
  }
  return dispatchQueuedJob(original);
}

async function dispatchQueuedJob(original) {
  await markJob(original.id, 'dispatching', {startedAt: new Date().toISOString()});
  const result = await dispatch(original.commission, original.newWorker, original.context || context.value, false, original.id);
  if (!result?.ok) {
    await markJob(original.id, 'failed', {error: result?.error || 'dispatch_failed', finishedAt: new Date().toISOString()});
    return null;
  }
  const workerTabId = Number(result.receipt?.tabId || result.worker?.tabId || 0);
  await markJob(original.id, 'running', {
    dispatchReceipt: result.receipt || null,
    workerTabId,
    dispatchedAt: new Date().toISOString(),
  });
  return {job: {...original, workerTabId}, receipt: result.receipt, workerTabId};
}

async function dispatch(text, fresh, campaignContext, clear = true, jobId = '') {
  const value = String(text || '').trim();
  if (!value) return showAndReturn('Commission is empty.');
  const result = await message({
    type: 'throne.run',
    commission: value,
    context: String(campaignContext || '').trim(),
    newWorker: fresh,
    jobId,
  });
  if (result?.ok && clear) {
    commission.value = '';
    await chrome.storage.local.set({throneDraft: '', throneContext: context.value});
  }
  return result;
}

async function runSwarm() {
  if (swarmRunning) return show('Swarm already running.');
  swarmRunning = true;
  status.textContent = `swarm running · up to ${MAX_PARALLEL_WORKERS} parallel Instant workers`;
  const receipts = [];
  let totalSlices = 0;
  try {
    while (swarmRunning && totalSlices < MAX_SWARM_SLICES) {
      const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
      const wave = parallelBatch(throneQueue, Math.min(MAX_PARALLEL_WORKERS, MAX_SWARM_SLICES - totalSlices));
      if (!wave.length) {
        receipts.push({state: 'queue_empty'});
        break;
      }

      const dispatched = (await Promise.all(wave.map((job) => dispatchQueuedJob(job)))).filter(Boolean);
      totalSlices += dispatched.length;
      if (!dispatched.length) {
        receipts.push({state: 'dispatch_wave_failed'});
        break;
      }
      receipts.push({state: 'wave_dispatched', workers: dispatched.map((x) => ({jobId: x.job.id, tabId: x.workerTabId}))});

      await Promise.all(dispatched.map(async (entry) => {
        const checkpoint = await waitForCompletedAssistant(entry.workerTabId);
        if (!checkpoint.ok) {
          await markJob(entry.job.id, 'choked_unreadable', {error: checkpoint.error});
          receipts.push({jobId: entry.job.id, tabId: entry.workerTabId, state: 'choked_unreadable', error: checkpoint.error});
          return;
        }

        const continuation = planHandoffContinuation(entry.job.context || context.value, checkpoint.text);
        await recordSwarmReceipt({
          type: 'swarm_checkpoint',
          jobId: entry.job.id,
          tabId: entry.workerTabId,
          at: new Date().toISOString(),
          text: checkpoint.text,
          handoff: continuation?.handoff || null,
        });

        if (continuation) {
          context.value = continuation.context;
          const {throneQueue: currentQueue = []} = await chrome.storage.local.get('throneQueue');
          currentQueue.push(continuation.job);
          await chrome.storage.local.set({throneQueue: currentQueue, throneContext: continuation.context});
          await markJob(entry.job.id, 'handed_off', {handoff: continuation.handoff});
          receipts.push({jobId: entry.job.id, tabId: entry.workerTabId, state: 'handed_off', next: continuation.job.commission});
          return;
        }

        const reviewRequirement = {
          reviewer: 'venice-local',
          independentOfChatGPT: true,
          requiredReceiptField: 'externalReviewGateSatisfied',
          requiredReceiptValue: true,
          vladRequired: true,
          finalRelease: 'tetsuya',
        };
        await markJob(entry.job.id, 'awaiting_venice_review', {checkpoint: checkpoint.text, reviewRequirement});
        await recordSwarmReceipt({
          type: 'swarm_external_review_required',
          jobId: entry.job.id,
          tabId: entry.workerTabId,
          at: new Date().toISOString(),
          reviewRequirement,
        });
        receipts.push({jobId: entry.job.id, tabId: entry.workerTabId, state: 'awaiting_venice_review'});
      }));

      const updated = (await chrome.storage.local.get('throneQueue')).throneQueue || [];
      await renderQueue(updated);
    }
  } finally {
    swarmRunning = false;
    const ready = await message({type: 'throne.status'}, false);
    status.textContent = ready?.ok ? `${ready.bootPhrase} · ${ready.workers?.length || 0} worker tabs` : 'Chromium Throne unavailable';
    show({ok: true, accepted: false, swarm: receipts, terminalGate: 'Vlad + Venice review; Tetsuya final release'});
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
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const selected = throneQueue.find((job) => Number(job.workerTabId) > 0 && ['running', 'awaiting_venice_review', 'handed_off'].includes(job.state));
  const result = await message({type: 'throne.capture', workerTabId: selected?.workerTabId || null, jobId: selected?.id || ''});
  if (result?.ok) {
    const handoff = parseHandoff(result.receipt?.text || '');
    show({ok: true, checkpoint: result.receipt, handoff});
  }
  return result;
}

async function waitForCompletedAssistant(workerTabId, timeoutMs = 10 * 60 * 1000) {
  const started = Date.now();
  let baselineCount = null;
  let lastText = '';
  let stablePolls = 0;
  while (Date.now() - started < timeoutMs && swarmRunning) {
    const peek = await inspectConversation(workerTabId);
    if (peek.ok) {
      if (baselineCount === null) baselineCount = Number(peek.assistantCount || 0);
      if (peek.assistantCount > baselineCount && peek.text) {
        stablePolls = !peek.generating && peek.text === lastText ? stablePolls + 1 : 0;
        lastText = peek.text;
        if (!peek.generating && stablePolls >= 1) return {ok: true, text: peek.text, assistantCount: peek.assistantCount};
      }
    }
    await sleep(1800);
  }
  return {ok: false, error: swarmRunning ? 'assistant_completion_timeout' : 'swarm_stopped'};
}

async function inspectConversation(workerTabId) {
  return message({type: 'throne.inspect', workerTabId}, false);
}

async function recordSwarmReceipt(receipt) {
  const {throneSwarmReceipts = []} = await chrome.storage.local.get('throneSwarmReceipts');
  throneSwarmReceipts.push(receipt);
  if (throneSwarmReceipts.length > 500) throneSwarmReceipts.splice(0, throneSwarmReceipts.length - 500);
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

function showAndReturn(text) {
  const result = {ok: false, error: text};
  show(result);
  return result;
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
    title.textContent = `${index + 1}. ${job.state}${job.workerTabId ? ` · tab ${job.workerTabId}` : ''}${job.context ? ' · context locked' : ''}${job.source === 'handoff' ? ' · rotated' : ''}`;
    const body = document.createElement('div');
    body.textContent = job.commission.length > 220 ? `${job.commission.slice(0, 220)}…` : job.commission;
    row.append(title, body);
    queueNode.append(row);
  }
  if (!queue.length) queueNode.textContent = 'No queued commissions.';
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
