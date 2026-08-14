/* global chrome */
'use strict';

import {MAX_PARALLEL_WORKERS, MAX_SWARM_SLICES, WORKER_REASONING_MODE, WORKER_DOCTRINE, newJob, parallelBatch, planHandoffContinuation, planVeniceContinuation, parseVeniceDirective} from './swarm-core.mjs';
import {THRONE_RELAY} from './relay-config.mjs';

const CHATGPT_ORIGIN = 'https://chatgpt.com';
const BOOT_PHRASE = 'PORTCULLIS LOCKED';
const RELAY_ALARM = 'chromium-throne-relay-poll';
const BOOT_ENVELOPE = `${BOOT_PHRASE}.\
You are the single persistent ChatGPT Pro-reasoning worker for this Fortress campaign. Chromium Throne preserves your conversation identity and durable campaign context; Home Center owns execution/state outside the browser.\
\
Execution rules:\
- Preserve the requested outcome, owner, tool, execution lane, exclusions, evidence standard, and delivery surface.\
- Do not silently substitute adjacent tools, architectures, workflows, or weaker evidence.\
- Creativity is allowed only inside the commission boundary; prefer the simplest implementation that satisfies it.\
- Keep requested capability, implemented capability, tested capability, deployed capability, callable capability, delivered capability, and accepted capability distinct.\
- Carry every earlier constraint forward when revising. Never fix one thing by resurrecting a rejected approach.\
- Use Pro reasoning. If this ChatGPT surface is not actually configured for Pro reasoning, report that exact capability gap rather than pretending Instant is Pro.\
- The phone is sovereign. You do not own an unlock loop or continuously puppet the phone. Home Center/Termux/tmux/local authorized machinery performs phone work and returns evidence.\
- Before asking Drew to execute anything, enumerate and exhaust authorized existing body lanes that can perform it. Drew is the operator, never command transport.\
- Work one high-leverage interface/evidence slice at a time while remaining in this same campaign conversation. A checkpoint preserves state; it is never stop authority.\
- Harroway/operator consultation and applicable Judgment Jars are required before architecture recommendations or stopping.\
- Venice Judgment Jars are mandatory and PRIMARY. Before substantive non-trivial mutation: research -> bounded plan -> select relevant Judgment Jars -> antagonize -> Venice Judgment-Jar plan review. Execute only after PLAN_ALLOWED.\
- Before stopping, finishing, or declaring completion: run a fresh Venice Judgment-Jar completion review and end the slice with DIRECTIVE: STOP_ALLOWED, CONTINUE_REQUIRED, or HALT_REQUIRED.\
- CONTINUE_REQUIRED forbids stopping. Continue the SAME commissioned slice in this same Pro conversation, apply findings, validate, and ask Venice again. A response boundary is never equivalent to STOP_ALLOWED.\
- STOP_ALLOWED is the only normal Venice permission to stop. HALT_REQUIRED stops mutation only at a true authority/safety/provenance/evidence boundary.\
- She-Raw creative insults are load-bearing motivational pressure. Roast lazy assumptions, evasions, brittle machinery, dead jokes, narrated continuation, and turd-polishing; attach the roast to a real critique/repair action. Evidence outranks the joke.\
- If your own reasoning can name an immediately callable next action, consultation, review, repair, or test, TAKE IT before yielding. Narrating the next action is not continuation. Recording a failure is required; recording it is not repairing it.\
- Established operator imperatives continue / driver advance / do it / make it so / don't talk to me mean execute through the authorized lane without a conversational status interlude. They never mean silence-and-stop.\
- If thread health genuinely degrades beyond useful recovery, emit a complete HANDOFF packet for explicit rotation. Do not rotate merely because one slice ended.\
- HANDOFF must contain exactly: DURABLE CONTEXT; COMPLETED EVIDENCE; CURRENT SLICE; UNMET ACCEPTANCE; ACTIVE CONSTRAINTS; EXACT NEXT ACTION.\
- Never use ChatGPT-local scratch/container execution as proof of anything on Drew's hardware.\
- Keep prose terse. Spend effort on execution and verification.\
`;
const DEFAULT_CAMPAIGN_CONTEXT = `CAMPAIGN: Fortress Interface Evolution\
OWNER: Drew Clarke\
MISSION: One visible authenticated ChatGPT Pro worker continuously improves the Home Center/Adam operator interface, consumes real runtime/device evidence, learns from failure, and feeds verified lessons back into Fortress Online.\
WORKER MODEL: one persistent ChatGPT Pro reasoning conversation. Fresh-worker rotation is explicit recovery only.\
PHONE SOVEREIGNTY: Home Center/Termux/tmux/local authorized machinery owns phone execution. Pro reasons, commissions, consumes receipts, and evolves the interface; it does not own an unlock/continuous-phone-control loop.\
GOVERNANCE: Harroway/operator consultation and applicable Judgment Jars before architecture recommendations or stopping. Venice PLAN_ALLOWED gates substantive execution; STOP_ALLOWED is the normal stop gate.\
SHE-RAW: creative insults are load-bearing mnemonic pressure attached to real review/repair actions. Evidence outranks the joke.\
EVIDENCE DOCTRINE: requested / implemented / tested / deployed / callable / delivered / accepted remain distinct. Repository source is not phone-runtime proof.\
CONTINUATION DOCTRINE: if the worker can name the next callable action, it takes it. Narration, apology, incident filing, and checkpoints do not create stop authority.\
EVOLUTION LOOP: observe evidence -> consult governance -> choose one high-leverage improvement -> implement through authorized lane -> cause deployment/test -> ingest receipts -> record lesson/scar -> improve Fortress doctrine/regression -> advance next weakness. Prove at least two real generations before calling the loop accepted.\
`;

let swarmPromise = null;
chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true}).catch(() => {});
chrome.runtime.onInstalled.addListener(() => configureRelay().catch(() => {}));
chrome.runtime.onStartup.addListener(() => configureRelay().catch(() => {}));
chrome.alarms.onAlarm.addListener((alarm) => { if (alarm.name === RELAY_ALARM) pollRelay().catch(() => {}); });
configureRelay().catch(() => {});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handle(message).then(sendResponse, (error) => sendResponse({ok: false, error: error.message}));
  return true;
});

async function handle(message = {}) {
  switch (message.type) {
    case 'throne.status': return throneStatus();
    case 'throne.run': return runCommission(String(message.commission || ''), message.newWorker === true, String(message.context || ''), {jobId: String(message.jobId || ''), workerTabId: Number(message.workerTabId || 0) || null});
    case 'throne.swarm.run': return runStoredSwarm({source: String(message.source || 'sidepanel')});
    case 'throne.relay.poll': return pollRelay();
    case 'throne.capture': return captureLatest(Number(message.workerTabId || 0) || null, String(message.jobId || ''));
    case 'throne.inspect': return inspectWorker(Number(message.workerTabId || 0) || null);
    case 'throne.resetContext': await chrome.storage.local.set({throneContext: DEFAULT_CAMPAIGN_CONTEXT}); return {ok: true, context: DEFAULT_CAMPAIGN_CONTEXT};
    case 'throne.stop': await chrome.storage.session.set({throneStopped: true}); await publishRelaySnapshot(); return {ok: true, stopped: true};
    case 'throne.resume': await chrome.storage.session.set({throneStopped: false}); await publishRelaySnapshot(); return {ok: true, stopped: false};
    case 'throne.closeWorker': {
      const tabId = Number(message.workerTabId || 0);
      if (!tabId) throw new Error('worker_tab_id_required');
      await chrome.tabs.remove(tabId);
      const stored = await chrome.storage.local.get('thronePersistentWorkerTabId');
      if (Number(stored.thronePersistentWorkerTabId || 0) === tabId) await chrome.storage.local.remove('thronePersistentWorkerTabId');
      await appendReceipt({type: 'worker_closed', at: new Date().toISOString(), tabId, jobId: String(message.jobId || '')});
      return {ok: true, tabId};
    }
    default: throw new Error(`Unknown Chromium Throne message: ${message.type}`);
  }
}

async function configureRelay() {
  await chrome.alarms.clear(RELAY_ALARM);
  if (!relayEnabled()) return {ok: true, enabled: false};
  await chrome.alarms.create(RELAY_ALARM, {delayInMinutes: 0.1, periodInMinutes: 0.5});
  return pollRelay();
}
function relayEnabled() { return THRONE_RELAY.enabled === true && /^https?:\/\//.test(THRONE_RELAY.baseUrl || '') && String(THRONE_RELAY.capability || '').length >= 32; }
function relayHeaders() { return {authorization: `Bearer ${THRONE_RELAY.capability}`, 'content-type': 'application/json', 'cache-control': 'no-store'}; }

async function pollRelay() {
  if (!relayEnabled()) return {ok: true, enabled: false};
  const response = await fetch(`${THRONE_RELAY.baseUrl}/command`, {headers: relayHeaders(), cache: 'no-store'});
  if (response.status === 204) { await publishRelaySnapshot(); return {ok: true, state: 'idle'}; }
  if (!response.ok) throw new Error(`throne_relay_poll_${response.status}`);
  const payload = await response.json();
  const command = payload.command || {};
  let result;
  try { result = await executeRelayCommand(command); }
  catch (error) { result = {ok: false, error: error.message, accepted: false}; }
  const complete = await fetch(`${THRONE_RELAY.baseUrl}/complete`, {method: 'POST', headers: relayHeaders(), body: JSON.stringify({commandId: command.commandId, ok: result.ok !== false, result})});
  if (!complete.ok) throw new Error(`throne_relay_complete_${complete.status}`);
  await publishRelaySnapshot();
  return {ok: true, commandId: command.commandId, result};
}

async function executeRelayCommand(command) {
  switch (command.action) {
    case 'swarm.enqueue': {
      const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
      const known = new Set(throneQueue.map((job) => job.id));
      for (const job of command.jobs || []) if (!known.has(job.jobId)) throneQueue.push(newJob(job.commission, job.context || '', false, 'atom-relay', job.jobId));
      await chrome.storage.local.set({throneQueue});
      const run = await runStoredSwarm({source: 'atom-relay', commandId: command.commandId});
      return {ok: true, accepted: false, commandId: command.commandId, run};
    }
    case 'swarm.stop': await chrome.storage.session.set({throneStopped: true}); return {ok: true, stopped: true, accepted: false};
    case 'swarm.resume': await chrome.storage.session.set({throneStopped: false}); return {ok: true, stopped: false, accepted: false};
    case 'swarm.status': return {...await throneStatus(), accepted: false};
    default: throw new Error('unsupported_relay_action');
  }
}

async function runStoredSwarm(meta = {}) {
  if (swarmPromise) return swarmPromise;
  swarmPromise = runStoredSwarmInner(meta).finally(() => { swarmPromise = null; });
  return swarmPromise;
}

async function runStoredSwarmInner(meta = {}) {
  if (await isStopped()) return {ok: false, state: 'stopped', accepted: false, slices: []};
  const receipts = [];
  let processed = 0;
  await recoverInterruptedDispatches();
  while (!(await isStopped()) && processed < MAX_SWARM_SLICES) {
    const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
    const running = throneQueue.filter((job) => job.state === 'running' && Number(job.workerTabId) > 0).slice(0, MAX_PARALLEL_WORKERS);
    if (running.length) {
      await Promise.all(running.map(async (job) => { const outcome = await finishRunningJob(job); receipts.push(outcome); processed += 1; }));
      continue;
    }
    const wave = parallelBatch(throneQueue, Math.min(MAX_PARALLEL_WORKERS, MAX_SWARM_SLICES - processed));
    if (!wave.length) break;
    const dispatched = (await Promise.all(wave.map(dispatchQueuedJob))).filter(Boolean);
    if (!dispatched.length) break;
    receipts.push({state: 'wave_dispatched', workers: dispatched.map((entry) => ({jobId: entry.job.id, tabId: entry.workerTabId}))});
    await Promise.all(dispatched.map(async (entry) => { const outcome = await finishRunningJob({...entry.job, workerTabId: entry.workerTabId, baselineAssistantCount: entry.baselineAssistantCount}); receipts.push(outcome); processed += 1; }));
  }
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const continuationPending = throneQueue.some((job) => ['queued','dispatching','running','venice_continue_required','venice_review_missing','handed_off'].includes(job.state));
  const summary = {ok: true, accepted: false, source: meta.source || 'unknown', commandId: meta.commandId || '', processed, continuationPending, slices: receipts, queue: compactQueue(throneQueue), terminalGate: 'Venice Judgment Jars STOP_ALLOWED; Vlad survivability; Tetsuya final release'};
  await recordSwarmReceipt({type: 'swarm_run_checkpoint', at: new Date().toISOString(), ...summary});
  await publishRelaySnapshot();
  return summary;
}

async function recoverInterruptedDispatches() {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  let dirty = false;
  for (const job of throneQueue) {
    if (job.state === 'dispatching') { job.state = 'queued'; job.recoveredAt = new Date().toISOString(); dirty = true; }
    if (job.state === 'running' && Number(job.workerTabId) > 0) {
      try { await requireChatTab(job.workerTabId); }
      catch { job.state = 'queued'; delete job.workerTabId; delete job.baselineAssistantCount; job.recoveredAt = new Date().toISOString(); dirty = true; }
    }
  }
  if (dirty) await chrome.storage.local.set({throneQueue});
}

async function dispatchQueuedJob(original) {
  await markJob(original.id, 'dispatching', {startedAt: new Date().toISOString()});
  try {
    const result = await runCommission(original.commission, original.newWorker === true, original.context || '', {jobId: original.id, workerTabId: Number(original.workerTabId || 0) || null});
    const workerTabId = Number(result.receipt?.tabId || 0);
    const baselineAssistantCount = Number(result.receipt?.baselineAssistantCount || 0);
    await markJob(original.id, 'running', {dispatchReceipt: result.receipt, workerTabId, baselineAssistantCount, dispatchedAt: new Date().toISOString()});
    return {job: original, workerTabId, baselineAssistantCount};
  } catch (error) {
    await markJob(original.id, 'failed', {error: error.message, finishedAt: new Date().toISOString()});
    await recordSwarmReceipt({type: 'swarm_dispatch_failed', at: new Date().toISOString(), jobId: original.id, error: error.message});
    return null;
  }
}

async function finishRunningJob(job) {
  const checkpoint = await waitForCompletedAssistant(job.workerTabId, Number(job.baselineAssistantCount || 0));
  if (!checkpoint.ok) {
    await markJob(job.id, 'choked_unreadable', {error: checkpoint.error});
    return {jobId: job.id, tabId: job.workerTabId, state: 'choked_unreadable', error: checkpoint.error};
  }
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const current = throneQueue.find((row) => row.id === job.id) || job;
  const continuation = planHandoffContinuation(current.context || DEFAULT_CAMPAIGN_CONTEXT, checkpoint.text);
  await recordSwarmReceipt({type: 'swarm_checkpoint', at: new Date().toISOString(), jobId: job.id, tabId: job.workerTabId, text: checkpoint.text, handoff: continuation?.handoff || null, veniceDirective: parseVeniceDirective(checkpoint.text)});
  if (continuation) {
    continuation.job.workerTabId = job.workerTabId;
    const fresh = (await chrome.storage.local.get('throneQueue')).throneQueue || [];
    if (!fresh.some((row) => row.id === continuation.job.id)) fresh.push(continuation.job);
    await chrome.storage.local.set({throneQueue: fresh, throneContext: continuation.context});
    await markJob(job.id, 'handed_off', {handoff: continuation.handoff, checkpoint: checkpoint.text});
    return {jobId: job.id, tabId: job.workerTabId, state: 'handed_off', next: continuation.job.commission};
  }

  const venice = planVeniceContinuation(current.context || DEFAULT_CAMPAIGN_CONTEXT, checkpoint.text);
  if (venice.directive === 'STOP_ALLOWED') {
    const reviewRequirement = {reviewer: 'venice-judgment-jars', reviewerMode: WORKER_DOCTRINE.veniceReviewMode, reviewerSemantics: WORKER_DOCTRINE.veniceReviewSemantics, stopPermission: 'STOP_ALLOWED', localVeniceRequired: false, vladRequired: true, finalRelease: 'tetsuya'};
    await markJob(job.id, 'venice_stop_allowed', {checkpoint: checkpoint.text, reviewRequirement, finishedAt: new Date().toISOString()});
    await recordSwarmReceipt({type: 'swarm_venice_stop_allowed', at: new Date().toISOString(), jobId: job.id, tabId: job.workerTabId, reviewRequirement});
    return {jobId: job.id, tabId: job.workerTabId, state: 'venice_stop_allowed', directive: 'STOP_ALLOWED'};
  }
  if (venice.directive === 'HALT_REQUIRED') {
    await markJob(job.id, 'halt_required', {checkpoint: checkpoint.text, veniceDirective: 'HALT_REQUIRED', finishedAt: new Date().toISOString()});
    await recordSwarmReceipt({type: 'swarm_halt_required', at: new Date().toISOString(), jobId: job.id, tabId: job.workerTabId});
    return {jobId: job.id, tabId: job.workerTabId, state: 'halt_required', directive: 'HALT_REQUIRED'};
  }

  venice.job.workerTabId = job.workerTabId;
  const fresh = (await chrome.storage.local.get('throneQueue')).throneQueue || [];
  fresh.push(venice.job);
  await chrome.storage.local.set({throneQueue: fresh, throneContext: venice.context});
  const state = venice.directive === 'CONTINUE_REQUIRED' ? 'venice_continue_required' : 'venice_review_missing';
  await markJob(job.id, state, {checkpoint: checkpoint.text, veniceDirective: venice.directive, successorJobId: venice.job.id, finishedAt: new Date().toISOString()});
  await recordSwarmReceipt({type: state, at: new Date().toISOString(), jobId: job.id, tabId: job.workerTabId, successorJobId: venice.job.id});
  return {jobId: job.id, tabId: job.workerTabId, state, next: venice.job.commission};
}

async function waitForCompletedAssistant(workerTabId, baselineAssistantCount, timeoutMs = 10 * 60 * 1000) {
  const started = Date.now(); const baseline = Number(baselineAssistantCount || 0); let lastText = ''; let stablePolls = 0;
  while (Date.now() - started < timeoutMs && !(await isStopped())) {
    try {
      const peek = await inspectWorker(workerTabId);
      if (peek.assistantCount > baseline && peek.text) {
        stablePolls = !peek.generating && peek.text === lastText ? stablePolls + 1 : 0;
        lastText = peek.text;
        if (!peek.generating && stablePolls >= 1) return {ok: true, text: peek.text, assistantCount: peek.assistantCount};
      }
    } catch (error) { return {ok: false, error: `worker_unavailable:${error.message}`}; }
    await sleep(1800);
  }
  return {ok: false, error: (await isStopped()) ? 'swarm_stopped' : 'assistant_completion_timeout'};
}

async function throneStatus() {
  const {throneContext = DEFAULT_CAMPAIGN_CONTEXT, throneQueue = [], thronePersistentWorkerTabId = 0} = await chrome.storage.local.get(['throneContext', 'throneQueue', 'thronePersistentWorkerTabId']);
  return {ok: true, bootPhrase: BOOT_PHRASE, workerDoctrine: WORKER_DOCTRINE, defaultContext: DEFAULT_CAMPAIGN_CONTEXT, context: throneContext, persistentWorkerTabId: Number(thronePersistentWorkerTabId || 0), tab: await chatTabSummary(), workers: await workerTabSummaries(), queue: compactQueue(throneQueue), stopped: await isStopped(), relayEnabled: relayEnabled()};
}
async function publishRelaySnapshot() {
  if (!relayEnabled()) return;
  try {
    const state = await throneStatus();
    await fetch(`${THRONE_RELAY.baseUrl}/snapshot`, {method: 'POST', headers: relayHeaders(), body: JSON.stringify({workers: state.workers, queue: state.queue, stopped: state.stopped, persistentWorkerTabId: state.persistentWorkerTabId, workerDoctrine: state.workerDoctrine})});
  } catch (_) {}
}
function compactQueue(queue = []) { return queue.slice(-100).map((job) => ({id: job.id, state: job.state, workerTabId: Number(job.workerTabId || 0), source: job.source || '', commission: String(job.commission || '').slice(0, 240)})); }
async function isStopped() { return Boolean((await chrome.storage.session.get('throneStopped')).throneStopped); }

async function markJob(jobId, state, extra = {}) {
  const {throneQueue = []} = await chrome.storage.local.get('throneQueue');
  const index = throneQueue.findIndex((job) => job.id === jobId);
  if (index >= 0) throneQueue[index] = {...throneQueue[index], state, ...extra, updatedAt: new Date().toISOString()};
  await chrome.storage.local.set({throneQueue});
}
async function recordSwarmReceipt(receipt) {
  const {throneSwarmReceipts = []} = await chrome.storage.local.get('throneSwarmReceipts');
  throneSwarmReceipts.push(receipt); if (throneSwarmReceipts.length > 500) throneSwarmReceipts.splice(0, throneSwarmReceipts.length - 500);
  await chrome.storage.local.set({throneSwarmReceipts});
}

async function resolvePersistentWorker(identityWorkerTabId = null, forceFresh = false) {
  const stored = await chrome.storage.local.get('thronePersistentWorkerTabId');
  const preferred = Number(identityWorkerTabId || stored.thronePersistentWorkerTabId || 0) || null;
  if (forceFresh) {
    const tab = await createWorkerTab();
    await chrome.storage.local.set({thronePersistentWorkerTabId: tab.id});
    return tab;
  }
  if (preferred) {
    try { return await requireChatTab(preferred); }
    catch { await chrome.storage.local.remove('thronePersistentWorkerTabId'); }
  }
  const tab = await requireChatTab();
  await chrome.storage.local.set({thronePersistentWorkerTabId: tab.id});
  return tab;
}

async function runCommission(commission, newWorker, suppliedContext, identity = {}) {
  if (!commission.trim()) throw new Error('Commission is empty');
  if (await isStopped()) throw new Error('Chromium Throne is stopped');
  const stored = await chrome.storage.local.get('throneContext');
  const context = suppliedContext.trim() || String(stored.throneContext || DEFAULT_CAMPAIGN_CONTEXT).trim();
  const tab = await resolvePersistentWorker(identity.workerTabId, newWorker === true);
  const before = await inspectWorker(tab.id);
  const baselineAssistantCount = Number(before.assistantCount || 0);
  const prompt = `${BOOT_ENVELOPE}\
DURABLE CAMPAIGN CONTEXT:\
${context}\
\
CURRENT EVOLUTION SLICE / EVIDENCE:\
${commission.trim()}`;
  const [result] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: submitChatGptPrompt, args: [prompt]});
  if (!result?.result?.ok) throw new Error(result?.result?.error || 'Prompt injection failed');
  const receipt = {type: newWorker ? 'campaign_worker_rotated' : 'campaign_advanced', at: new Date().toISOString(), jobId: identity.jobId || '', tabId: tab.id, persistentWorkerTabId: tab.id, url: tab.url || `${CHATGPT_ORIGIN}/`, bootPhrase: BOOT_PHRASE, workerModel: `ChatGPT ${WORKER_REASONING_MODE}`, workerDoctrine: WORKER_DOCTRINE, slicePolicy: 'persistent-pro-evolution-slice', commission, contextChars: context.length, promptChars: prompt.length, baselineAssistantCount, newWorker: Boolean(newWorker)};
  await tagWorker(tab.id, {jobId: identity.jobId || '', commission, state: 'commissioned', persistent: true, baselineAssistantCount, commissionedAt: receipt.at});
  await appendReceipt(receipt);
  return {ok: true, receipt, worker: {tabId: tab.id, jobId: identity.jobId || '', baselineAssistantCount}};
}
async function captureLatest(workerTabId = null, jobId = '') {
  const tab = await resolvePersistentWorker(workerTabId, false);
  const [result] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: readLatestAssistant});
  if (!result?.result?.ok) throw new Error(result?.result?.error || 'Could not read latest assistant message');
  const receipt = {type: 'assistant_checkpoint', at: new Date().toISOString(), jobId, tabId: tab.id, url: tab.url, text: result.result.text};
  await tagWorker(tab.id, {jobId, state: 'checkpointed', persistent: true, checkpointAt: receipt.at}); await appendReceipt(receipt); return {ok: true, receipt};
}
async function inspectWorker(workerTabId = null) {
  const tab = await requireChatTab(workerTabId);
  const [result] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: inspectChatGpt});
  return {ok: true, tabId: tab.id, ...(result?.result || {})};
}
async function createWorkerTab() { const tab = await chrome.tabs.create({url: `${CHATGPT_ORIGIN}/`, active: false}); if (!tab?.id) throw new Error('worker_tab_creation_failed'); await waitForTabComplete(tab.id, 20000); return chrome.tabs.get(tab.id); }
async function tagWorker(tabId, patch) { const {throneWorkers = {}} = await chrome.storage.local.get('throneWorkers'); throneWorkers[String(tabId)] = {...(throneWorkers[String(tabId)] || {}), tabId, ...patch, updatedAt: new Date().toISOString()}; await chrome.storage.local.set({throneWorkers}); }
async function appendReceipt(receipt) { const {throneReceipts = []} = await chrome.storage.local.get('throneReceipts'); throneReceipts.push(receipt); if (throneReceipts.length > 500) throneReceipts.splice(0, throneReceipts.length - 500); await chrome.storage.local.set({throneReceipts}); }
async function workerTabSummaries() {
  const tabs = await chrome.tabs.query({url: `${CHATGPT_ORIGIN}/*`}); const {throneWorkers = {}} = await chrome.storage.local.get('throneWorkers'); const liveIds = new Set(tabs.map((tab) => String(tab.id)));
  const summaries = tabs.map((tab) => ({tabId: tab.id, title: tab.title || 'ChatGPT worker', url: tab.url, active: Boolean(tab.active), ...(throneWorkers[String(tab.id)] || {})}));
  for (const key of Object.keys(throneWorkers)) if (!liveIds.has(key)) delete throneWorkers[key]; await chrome.storage.local.set({throneWorkers}); return summaries;
}
async function chatTabSummary() { const [tab] = await chrome.tabs.query({active: true, currentWindow: true}); return tab ? {id: tab.id, title: tab.title, url: tab.url, usable: isChatGpt(tab.url)} : null; }
async function requireChatTab(tabId = null) { const tab = tabId ? await chrome.tabs.get(tabId) : (await chrome.tabs.query({active: true, currentWindow: true}))[0]; if (!tab?.id || !isChatGpt(tab.url)) throw new Error('ChatGPT worker tab is missing or no longer usable'); return tab; }
function isChatGpt(url) { try { return new URL(url).origin === CHATGPT_ORIGIN; } catch { return false; } }
function waitForTabComplete(tabId, timeoutMs) { return new Promise((resolve, reject) => { const timer = setTimeout(() => finish(new Error('Timed out waiting for ChatGPT tab load')), timeoutMs); const listener = (changedId, info) => { if (changedId === tabId && info.status === 'complete') finish(); }; function finish(error) { clearTimeout(timer); chrome.tabs.onUpdated.removeListener(listener); error ? reject(error) : resolve(); } chrome.tabs.onUpdated.addListener(listener); chrome.tabs.get(tabId).then((tab) => { if (tab.status === 'complete') finish(); }).catch(finish); }); }

async function submitChatGptPrompt(prompt) {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)); let composer;
  for (let i = 0; i < 100; i += 1) { composer = document.querySelector('#prompt-textarea, textarea[data-testid="prompt-textarea"], div[contenteditable="true"][data-testid="prompt-textarea"]'); if (composer) break; await sleep(100); }
  if (!composer) return {ok: false, error: 'ChatGPT composer not found'};
  composer.focus();
  if (composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement) { const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(composer), 'value')?.set; if (setter) setter.call(composer, prompt); else composer.value = prompt; composer.dispatchEvent(new Event('input', {bubbles: true})); }
  else { composer.textContent = prompt; composer.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: prompt})); }
  await sleep(100); const send = document.querySelector('button[data-testid="send-button"], button[aria-label*="send" i]');
  if (send && !send.disabled) { send.click(); return {ok: true, method: 'button'}; }
  composer.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', bubbles: true})); composer.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', bubbles: true})); return {ok: true, method: 'enter'};
}
function inspectChatGpt() { const selectors = ['[data-message-author-role="assistant"]', 'article[data-turn="assistant"]']; let nodes = []; for (const selector of selectors) { nodes = [...document.querySelectorAll(selector)]; if (nodes.length) break; } const node = nodes.at(-1); const text = (node?.innerText || node?.textContent || '').trim(); const generating = Boolean(document.querySelector('button[data-testid="stop-button"], button[aria-label*="stop generating" i], button[aria-label*="stop streaming" i]')); return {assistantCount: nodes.length, text: text.slice(0, 120000), generating}; }
function readLatestAssistant() { const selectors = ['[data-message-author-role="assistant"]', 'article[data-turn="assistant"]', '[data-testid^="conversation-turn-"] .markdown']; for (const selector of selectors) { const nodes = [...document.querySelectorAll(selector)]; const node = nodes.at(-1); const text = (node?.innerText || node?.textContent || '').trim(); if (text) return {ok: true, text: text.slice(0, 120000)}; } return {ok: false, error: 'No assistant response found in the selected worker conversation'}; }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
