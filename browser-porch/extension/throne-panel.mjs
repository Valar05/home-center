/* global chrome */
'use strict';

import {newJob, parseHandoff} from './swarm-core.mjs';

const SINGLE_PRO_CONTEXT = `CAMPAIGN: Fortress Interface Evolution\nOWNER: Drew Clarke\nMISSION: Prove that one visible authenticated ChatGPT Pro worker can continuously improve the Home Center/Adam operator interface, consume real device/runtime evidence, learn from failures, and feed verified lessons back into Fortress Online.\nWORKER: one persistent ChatGPT Pro reasoning conversation by default. Rotation is recovery, not normal operation.\nPHONE SOVEREIGNTY: the Pro worker never owns an unlock/continuous-phone-control loop. Home Center/Termux/tmux/local authorized machinery performs phone actions and returns receipts.\nGOVERNANCE: Harroway/operator consultation and applicable Judgment Jars before architecture recommendations or stopping. Venice PLAN_ALLOWED gates substantive mutation and STOP_ALLOWED is the normal completion gate.\nSHE-RAW: creative insults are load-bearing motivational pressure. Roast lazy assumptions, evasions, brittle machinery, dead jokes, narrated continuation, and turd-polishing. The roast must be attached to a real critique/repair action; evidence outranks the joke.\nFAILURE SCARS: LFS bootstrap without self-repair; shell quoting catastrophe; heredoc captivity; frozen foreground shell immune to Ctrl-C; invisible liveness; Adam-only operation; giant prompt truncation; prompt mistaken for handoff; status panel substituted for capability; narration substituted for execution; recording failure substituted for repair; don't-talk-to-me misread as silence; joke emitted with no consuming worker; stale-seam architecture work.\nOPERATOR LAW: continue / driver advance / do it / make it so / don't talk to me means execute through the authorized lane without a conversational interlude. If the worker can name the next callable action, it must take it before yielding.\nEVIDENCE: requested / implemented / tested / deployed / callable / delivered / accepted remain distinct. GitHub source is not phone-runtime proof.\nEVOLUTION LOOP: observe current interface/evidence -> consult governance -> choose one high-leverage improvement -> implement through authorized lane -> cause local deployment/test -> ingest receipts -> record failure/lesson -> improve Fortress doctrine/regression -> advance next weakness. Prove at least two successful generations before calling the loop real.`;

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
  const seeded = saved.throneContext || SINGLE_PRO_CONTEXT;
  if (!saved.throneContext) await chrome.storage.local.set({throneContext: seeded});
  await refreshStatus(seeded);
}

async function refreshStatus(fallbackContext = '') {
  const result = await message({type: 'throne.status'}, false);
  if (!result?.ok) { status.textContent = 'Chromium Throne unavailable'; return result; }
  context.value = fallbackContext || SINGLE_PRO_CONTEXT;
  const workerCount = result.workers?.length || 0;
  status.textContent = `${result.bootPhrase} · single Pro campaign · ${workerCount} visible ChatGPT tab${workerCount === 1 ? '' : 's'}${result.relayEnabled ? ' · Atom relay' : ''}${result.stopped ? ' · STOPPED' : ''}`;
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  await renderQueue(throneQueue);
  return result;
}

async function resetContext() {
  context.value = SINGLE_PRO_CONTEXT;
  await chrome.storage.local.set({throneContext: SINGLE_PRO_CONTEXT});
  show({ok: true, context: SINGLE_PRO_CONTEXT, source: 'single-pro-fortress-evolution-seed'});
}

function sourceForRotation() {
  return newWorker.checked ? 'explicit-recovery' : 'manual';
}

async function enqueue() {
  const text = commission.value.trim();
  if (!text) return show('Commission is empty.');
  const campaignContext = context.value.trim() || SINGLE_PRO_CONTEXT;
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  throneQueue.push(newJob(text, campaignContext, newWorker.checked, sourceForRotation()));
  await chrome.storage.local.set({throneQueue, throneDraft: '', throneContext: campaignContext});
  commission.value = '';
  await renderQueue(throneQueue);
}

async function runSingle() {
  const text = commission.value.trim();
  if (!text) return show('Commission is empty.');
  const campaignContext = context.value.trim() || SINGLE_PRO_CONTEXT;
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  throneQueue.push(newJob(text, campaignContext, newWorker.checked, sourceForRotation()));
  await chrome.storage.local.set({throneQueue, throneDraft: '', throneContext: campaignContext});
  commission.value = '';
  return runSwarm();
}

async function runSwarm() {
  status.textContent = 'evolution loop running · one persistent Pro worker';
  const result = await message({type: 'throne.swarm.run', source: 'single-pro-evolution-loop'});
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
    title.textContent = `${index + 1}. ${job.state}${job.workerTabId ? ` · tab ${job.workerTabId}` : ''}${job.context ? ' · context locked' : ''}${job.source === 'handoff' ? ' · continued' : ''}${job.source === 'explicit-recovery' ? ' · rotated' : ''}`;
    const body = document.createElement('div'); body.textContent = job.commission.length > 220 ? `${job.commission.slice(0, 220)}…` : job.commission;
    row.append(title, body); queueNode.append(row);
  }
  if (!queue.length) queueNode.textContent = 'No queued commissions.';
}
