import fs from 'node:fs';

function read(path) { return fs.readFileSync(path, 'utf8'); }
function write(path, text) { fs.writeFileSync(path, text, 'utf8'); }
function replaceOnce(text, before, after, label) {
  const count = text.split(before).length - 1;
  if (count !== 1) throw new Error(`${label}: expected exactly one anchor, found ${count}`);
  return text.replace(before, after);
}
function replaceAllChecked(text, before, after, minCount, label) {
  const count = text.split(before).length - 1;
  if (count < minCount) throw new Error(`${label}: expected at least ${minCount} anchors, found ${count}`);
  return text.split(before).join(after);
}
function replaceBetween(text, start, end, replacement, label) {
  const startIndex = text.indexOf(start);
  const endIndex = text.indexOf(end, startIndex + start.length);
  if (startIndex < 0 || endIndex < 0 || text.indexOf(start, startIndex + 1) >= 0) throw new Error(`${label}: unique range anchors not found`);
  return text.slice(0, startIndex) + replacement + text.slice(endIndex);
}

const corePath = 'browser-porch/extension/swarm-core.mjs';
let core = read(corePath);
core = replaceOnce(core, "export const MAX_PARALLEL_WORKERS = 1;", "export const MAX_PARALLEL_WORKERS = 4;", 'parallel worker cap');
core = replaceOnce(core, "export const WORKER_REASONING_MODE = 'Pro reasoning';", "export const WORKER_REASONING_MODE = 'high-inference non-Pro';", 'reasoning mode');
core = replaceOnce(core,
  "  singlePersistentProWorker: true,\n",
  "  singlePersistentProWorker: false,\n  highInferenceRequested: true,\n  creditBearingComputeAllowed: false,\n  boundedParallelWorkers: MAX_PARALLEL_WORKERS,\n  independentRelayJobs: true,\n",
  'worker doctrine');
core = replaceOnce(core,
  "  const explicitRecovery = source === 'explicit-recovery';\n  return {\n",
  "  const explicitRecovery = source === 'explicit-recovery';\n  const independentRelay = source === 'atom-relay';\n  const workerMode = independentRelay ? 'independent' : (explicitRecovery && fresh === true ? 'recovery' : 'persistent');\n  return {\n",
  'job worker mode');
core = replaceOnce(core,
  "    newWorker: explicitRecovery && fresh === true,\n    source,\n",
  "    newWorker: workerMode !== 'persistent',\n    workerMode,\n    source,\n",
  'job worker mode fields');
core = replaceAllChecked(core, 'same Pro worker conversation', 'same worker conversation', 2, 'continuation wording');
write(corePath, core);

const workerPath = 'browser-porch/extension/service-worker.js';
let worker = read(workerPath);
worker = replaceOnce(worker,
  'You are the single persistent ChatGPT Pro-reasoning worker for this Fortress campaign. Chromium Throne preserves your conversation identity and durable campaign context; Home Center owns execution/state outside the browser.\\\n',
  'You are one bounded visible ChatGPT worker in a Chromium Throne swarm. Chromium Throne preserves your job identity and durable campaign context; Home Center owns execution/state outside the browser.\\\n',
  'boot identity');
worker = replaceOnce(worker,
  '- Use Pro reasoning. If this ChatGPT surface is not actually configured for Pro reasoning, report that exact capability gap rather than pretending Instant is Pro.\\\n',
  '- Use the highest inference available on the current non-Pro ChatGPT surface. Do not switch to a Pro or credit-bearing lane, and do not claim a model mode you cannot observe.\\\n',
  'non-pro inference law');
worker = replaceAllChecked(worker, 'same Pro conversation', 'same worker conversation', 1, 'same worker continuation');
worker = replaceOnce(worker,
  'MISSION: One visible authenticated ChatGPT Pro worker continuously improves the Home Center/Adam operator interface, consumes real runtime/device evidence, learns from failure, and feeds verified lessons back into Fortress Online.\\\nWORKER MODEL: one persistent ChatGPT Pro reasoning conversation. Fresh-worker rotation is explicit recovery only.\\\nPHONE SOVEREIGNTY: Home Center/Termux/tmux/local authorized machinery owns phone execution. Pro reasons, commissions, consumes receipts, and evolves the interface; it does not own an unlock/continuous-phone-control loop.\\\n',
  'MISSION: A bounded visible swarm of authenticated ChatGPT workers improves the Home Center/Adam operator interface, consumes real runtime/device evidence, learns from failure, and feeds verified lessons back into Fortress Online.\\\nWORKER MODEL: independent relay jobs receive dedicated visible non-Pro worker tabs, bounded to four concurrent workers; continuations stay in their owning conversation and explicit recovery can rotate a worker.\\\nPHONE SOVEREIGNTY: Home Center/Termux/tmux/local authorized machinery owns phone execution. ChatGPT workers reason, commission, consume receipts, and evolve the interface; they do not own an unlock/continuous-phone-control loop.\\\n',
  'campaign seed');
worker = replaceOnce(worker,
  "    const result = await runCommission(original.commission, original.newWorker === true, original.context || '', {jobId: original.id, workerTabId: Number(original.workerTabId || 0) || null});",
  "    const result = await runCommission(original.commission, original.newWorker === true, original.context || '', {jobId: original.id, workerTabId: Number(original.workerTabId || 0) || null, workerMode: String(original.workerMode || (original.newWorker ? 'recovery' : 'persistent'))});",
  'dispatch worker mode');
worker = replaceOnce(worker,
  "    continuation.job.workerTabId = job.workerTabId;\n",
  "    continuation.job.workerTabId = job.workerTabId;\n    continuation.job.workerMode = current.workerMode || 'persistent';\n",
  'handoff worker ownership');
worker = replaceOnce(worker,
  "  venice.job.workerTabId = job.workerTabId;\n",
  "  venice.job.workerTabId = job.workerTabId;\n  venice.job.workerMode = current.workerMode || 'persistent';\n",
  'venice worker ownership');
worker = replaceBetween(worker,
  'async function resolvePersistentWorker(identityWorkerTabId = null, forceFresh = false) {',
  'async function runCommission(commission, newWorker, suppliedContext, identity = {}) {',
  `async function resolveWorker(identityWorkerTabId = null, workerMode = 'persistent') {\n  const stored = await chrome.storage.local.get('thronePersistentWorkerTabId');\n  const canUsePersistent = workerMode === 'persistent' || workerMode === 'recovery';\n  const preferred = Number(identityWorkerTabId || (canUsePersistent ? stored.thronePersistentWorkerTabId : 0) || 0) || null;\n  if (preferred) {\n    try { return await requireChatTab(preferred); }\n    catch { if (canUsePersistent) await chrome.storage.local.remove('thronePersistentWorkerTabId'); }\n  }\n  if (workerMode === 'independent') return createWorkerTab();\n  if (workerMode === 'recovery') {\n    const tab = await createWorkerTab();\n    await chrome.storage.local.set({thronePersistentWorkerTabId: tab.id});\n    return tab;\n  }\n  const tab = await requireChatTab();\n  await chrome.storage.local.set({thronePersistentWorkerTabId: tab.id});\n  return tab;\n}\n\n`,
  'worker resolver');
worker = replaceOnce(worker,
  "  const tab = await resolvePersistentWorker(identity.workerTabId, newWorker === true);\n",
  "  const workerMode = String(identity.workerMode || (newWorker ? 'recovery' : 'persistent'));\n  const tab = await resolveWorker(identity.workerTabId, workerMode);\n",
  'run commission resolver');
worker = replaceOnce(worker,
  "  const receipt = {type: newWorker ? 'campaign_worker_rotated' : 'campaign_advanced', at: new Date().toISOString(), jobId: identity.jobId || '', tabId: tab.id, persistentWorkerTabId: tab.id, url: tab.url || `${CHATGPT_ORIGIN}/`, bootPhrase: BOOT_PHRASE, workerModel: `ChatGPT ${WORKER_REASONING_MODE}`, workerDoctrine: WORKER_DOCTRINE, slicePolicy: 'persistent-pro-evolution-slice', commission, contextChars: context.length, promptChars: prompt.length, baselineAssistantCount, newWorker: Boolean(newWorker)};\n  await tagWorker(tab.id, {jobId: identity.jobId || '', commission, state: 'commissioned', persistent: true, baselineAssistantCount, commissionedAt: receipt.at});\n",
  "  const receiptType = workerMode === 'independent' ? 'swarm_worker_spawned' : (workerMode === 'recovery' ? 'campaign_worker_rotated' : 'campaign_advanced');\n  const receipt = {type: receiptType, at: new Date().toISOString(), jobId: identity.jobId || '', tabId: tab.id, persistentWorkerTabId: workerMode === 'independent' ? 0 : tab.id, url: tab.url || `${CHATGPT_ORIGIN}/`, bootPhrase: BOOT_PHRASE, workerModel: `ChatGPT ${WORKER_REASONING_MODE}`, workerDoctrine: WORKER_DOCTRINE, workerMode, slicePolicy: workerMode === 'independent' ? 'bounded-independent-high-inference' : 'persistent-high-inference-evolution-slice', commission, contextChars: context.length, promptChars: prompt.length, baselineAssistantCount, newWorker: Boolean(newWorker)};\n  await tagWorker(tab.id, {jobId: identity.jobId || '', commission, state: 'commissioned', persistent: workerMode !== 'independent', workerMode, baselineAssistantCount, commissionedAt: receipt.at});\n",
  'commission receipt');
worker = replaceOnce(worker,
  "  const tab = await resolvePersistentWorker(workerTabId, false);\n",
  "  const tab = await resolveWorker(workerTabId, 'persistent');\n",
  'capture resolver');
worker = replaceOnce(worker,
  "  return {ok: true, bootPhrase: BOOT_PHRASE, workerDoctrine: WORKER_DOCTRINE, defaultContext: DEFAULT_CAMPAIGN_CONTEXT, context: throneContext, persistentWorkerTabId: Number(thronePersistentWorkerTabId || 0), tab: await chatTabSummary(), workers: await workerTabSummaries(), queue: compactQueue(throneQueue), stopped: await isStopped(), relayEnabled: relayEnabled()};",
  "  return {ok: true, bootPhrase: BOOT_PHRASE, workerDoctrine: WORKER_DOCTRINE, maxParallelWorkers: MAX_PARALLEL_WORKERS, defaultContext: DEFAULT_CAMPAIGN_CONTEXT, context: throneContext, persistentWorkerTabId: Number(thronePersistentWorkerTabId || 0), tab: await chatTabSummary(), workers: await workerTabSummaries(), queue: compactQueue(throneQueue), stopped: await isStopped(), relayEnabled: relayEnabled()};",
  'status parallel visibility');
write(workerPath, worker);

const panelPath = 'browser-porch/extension/throne-panel.mjs';
let panel = read(panelPath);
panel = replaceAllChecked(panel, 'SINGLE_PRO_CONTEXT', 'SWARM_CONTEXT', 6, 'panel context symbol');
panel = replaceOnce(panel,
  'MISSION: Prove that one visible authenticated ChatGPT Pro worker can continuously improve the Home Center/Adam operator interface, consume real device/runtime evidence, learn from failures, and feed verified lessons back into Fortress Online.\\nWORKER: one persistent ChatGPT Pro reasoning conversation by default. Rotation is recovery, not normal operation.\\nPHONE SOVEREIGNTY: the Pro worker never owns an unlock/continuous-phone-control loop.',
  'MISSION: Prove that bounded visible authenticated ChatGPT workers can improve the Home Center/Adam operator interface concurrently without paid or Pro-only compute, consume real device/runtime evidence, learn from failures, and feed verified lessons back into Fortress Online.\\nWORKER: up to four independent high-inference non-Pro worker conversations may run concurrently; continuation stays with its owning worker and explicit recovery may rotate it.\\nPHONE SOVEREIGNTY: ChatGPT workers never own an unlock/continuous-phone-control loop.',
  'panel campaign context');
panel = replaceOnce(panel,
  "  status.textContent = `${result.bootPhrase} · single Pro campaign · ${workerCount} visible ChatGPT tab${workerCount === 1 ? '' : 's'}${result.relayEnabled ? ' · Atom relay' : ''}${result.stopped ? ' · STOPPED' : ''}`;",
  "  status.textContent = `${result.bootPhrase} · high-inference non-Pro · ${workerCount} visible ChatGPT tab${workerCount === 1 ? '' : 's'} · max ${result.maxParallelWorkers || 1} concurrent${result.relayEnabled ? ' · Atom relay' : ''}${result.stopped ? ' · STOPPED' : ''}`;",
  'panel status');
panel = replaceOnce(panel, "source: 'single-pro-fortress-evolution-seed'", "source: 'bounded-nonpro-swarm-seed'", 'panel seed receipt');
panel = replaceOnce(panel, "  status.textContent = 'evolution loop running · one persistent Pro worker';\n  const result = await message({type: 'throne.swarm.run', source: 'single-pro-evolution-loop'});", "  status.textContent = 'swarm running · bounded high-inference non-Pro workers';\n  const result = await message({type: 'throne.swarm.run', source: 'bounded-nonpro-swarm'});", 'panel run status');
write(panelPath, panel);

const htmlPath = 'browser-porch/extension/sidepanel.html';
let html = read(htmlPath);
html = replaceOnce(html, 'One visible ChatGPT Pro worker owns the evolving campaign conversation.', 'Visible bounded ChatGPT workers own independent swarm threads; continuations stay with their owning conversation.', 'panel hint identity');
html = replaceOnce(html, 'Give the persistent Pro worker the next commission, correction, evidence packet, failure scar, or acceptance target', 'Give a high-inference non-Pro worker the next commission, correction, evidence packet, failure scar, or acceptance target', 'panel placeholder');
html = replaceOnce(html, 'Default behavior reuses one Pro worker. Rotation is an explicit recovery action, not the normal loop.', 'Manual campaign work reuses its worker by default; relay swarm jobs receive dedicated visible workers, bounded to four concurrent tabs. Rotation remains an explicit recovery action for a continuing thread.', 'panel hint swarm');
write(htmlPath, html);

const manifestPath = 'browser-porch/extension/manifest.json';
let manifest = read(manifestPath);
manifest = replaceOnce(manifest, '"version": "0.7.0"', '"version": "0.8.0"', 'manifest version');
manifest = replaceOnce(manifest, '"description": "One visible persistent ChatGPT Pro campaign worker for Fortress interface evolution, with durable context, Venice/Judgment Jar continuation, She-Raw motivational review pressure, and the existing Atom/Vlad relay seam."', '"description": "Visible bounded high-inference non-Pro ChatGPT workers for Fortress interface evolution, with independent relay jobs, durable continuation, Venice/Judgment Jar review pressure, and the existing Atom/Vlad relay seam."', 'manifest description');
write(manifestPath, manifest);

const coreTestPath = 'browser-porch/extension/swarm-core.test.mjs';
let coreTest = read(coreTestPath);
coreTest = replaceOnce(coreTest, "  planVeniceContinuation,\n", "  planVeniceContinuation,\n  parallelBatch,\n", 'parallelBatch import');
coreTest = replaceOnce(coreTest, "test('handoff continuation remains in the persistent Pro worker'", "test('handoff continuation remains in the owning worker'", 'handoff test title');
coreTest = replaceOnce(coreTest,
  "test('fresh worker rotation is explicit recovery only', () => {\n  assert.equal(newJob('normal', 'ctx', true, 'manual').newWorker, false);\n  assert.equal(newJob('relay', 'ctx', true, 'atom-relay').newWorker, false);\n  assert.equal(newJob('recover', 'ctx', true, 'explicit-recovery').newWorker, true);\n});",
  "test('relay jobs are independent while manual continuity and explicit recovery remain distinct', () => {\n  assert.equal(newJob('normal', 'ctx', true, 'manual').workerMode, 'persistent');\n  assert.equal(newJob('normal', 'ctx', true, 'manual').newWorker, false);\n  assert.equal(newJob('relay', 'ctx', false, 'atom-relay').workerMode, 'independent');\n  assert.equal(newJob('relay', 'ctx', false, 'atom-relay').newWorker, true);\n  assert.equal(newJob('recover', 'ctx', true, 'explicit-recovery').workerMode, 'recovery');\n  assert.equal(newJob('recover', 'ctx', true, 'explicit-recovery').newWorker, true);\n});",
  'worker mode test');
coreTest = replaceBetween(coreTest,
  "test('worker doctrine binds single Pro, phone sovereignty, Harroway, and She-Raw'",
  "test('Venice parser uses final explicit directive'",
  `test('worker doctrine binds bounded non-Pro concurrency, phone sovereignty, Harroway, and She-Raw', () => {\n  const job = newJob('prove one thing', 'ctx');\n  assert.equal(job.workerDoctrine.reasoningMode, 'high-inference non-Pro');\n  assert.equal(WORKER_REASONING_MODE, 'high-inference non-Pro');\n  assert.equal(MAX_PARALLEL_WORKERS, 4);\n  assert.equal(WORKER_DOCTRINE.singlePersistentProWorker, false);\n  assert.equal(WORKER_DOCTRINE.highInferenceRequested, true);\n  assert.equal(WORKER_DOCTRINE.creditBearingComputeAllowed, false);\n  assert.equal(WORKER_DOCTRINE.boundedParallelWorkers, 4);\n  assert.equal(WORKER_DOCTRINE.independentRelayJobs, true);\n  assert.equal(WORKER_DOCTRINE.phoneSovereign, true);\n  assert.equal(WORKER_DOCTRINE.phoneControlFromProWorker, false);\n  assert.equal(WORKER_DOCTRINE.harrowayConsultationRequired, true);\n  assert.equal(WORKER_DOCTRINE.sheRawMotivationRequired, true);\n  assert.equal(WORKER_DOCTRINE.narratedContinuationForbidden, true);\n  assert.equal(WORKER_DOCTRINE.localVeniceRequired, false);\n});\n\ntest('parallel batch is bounded to four independent queue slots', () => {\n  const queue = Array.from({length: 7}, (_, index) => newJob('job ' + index, 'ctx', false, 'atom-relay', 'job-' + index));\n  const wave = parallelBatch(queue, 99);\n  assert.equal(wave.length, 4);\n  assert.ok(wave.every((job) => job.workerMode === 'independent'));\n});\n\n`,
  'doctrine test block');
coreTest = replaceOnce(coreTest, "test('CONTINUE_REQUIRED stays in same Pro conversation and demands action'", "test('CONTINUE_REQUIRED stays in same worker conversation and demands action'", 'venice test title');
coreTest = replaceOnce(coreTest, "/same Pro worker conversation/i", "/same worker conversation/i", 'venice worker regex');
write(coreTestPath, coreTest);

const contextTestPath = 'browser-porch/extension/throne_context.test.mjs';
let contextTest = read(contextTestPath);
contextTest = replaceBetween(contextTest,
  "test('one persistent Pro worker is the campaign reasoning body'",
  "test('phone remains sovereign and Pro cannot own unlock loop'",
  `test('bounded high-inference non-Pro workers are the swarm reasoning body', () => {\n  assert.match(worker, /bounded visible ChatGPT worker/i);\n  assert.match(worker, /highest inference available on the current non-Pro ChatGPT surface/i);\n  assert.match(core, /MAX_PARALLEL_WORKERS = 4/);\n  assert.match(core, /creditBearingComputeAllowed: false/);\n  assert.match(core, /independentRelayJobs: true/);\n  assert.doesNotMatch(worker, /Use Pro reasoning/i);\n});\n\n`,
  'context worker doctrine test');
contextTest = replaceBetween(contextTest,
  "test('service worker persists one ChatGPT tab identity across continuation'",
  "test('fresh worker creation is explicit recovery rather than queue default'",
  `test('service worker binds independent jobs to dedicated tabs and continuation to the owning tab', () => {\n  assert.match(worker, /resolveWorker/);\n  assert.match(worker, /workerMode === 'independent'/);\n  assert.match(worker, /continuation\\.job\\.workerTabId = job\\.workerTabId/);\n  assert.match(worker, /continuation\\.job\\.workerMode = current\\.workerMode/);\n  assert.match(worker, /venice\\.job\\.workerTabId = job\\.workerTabId/);\n  assert.match(worker, /venice\\.job\\.workerMode = current\\.workerMode/);\n  assert.match(worker, /bounded-independent-high-inference/);\n});\n\n`,
  'context worker ownership test');
contextTest = replaceBetween(contextTest,
  "test('fresh worker creation is explicit recovery rather than queue default'",
  "test('service worker mechanically continues Venice in same worker'",
  `test('relay queue creates independent workers while manual fresh means explicit recovery', () => {\n  assert.match(core, /const independentRelay = source === 'atom-relay'/);\n  assert.match(core, /workerMode = independentRelay \? 'independent'/);\n  assert.match(worker, /message\\.newWorker === true/);\n  assert.match(worker, /newJob\\(job\\.commission, job\\.context \\|\\| '', false, 'atom-relay'/);\n  assert.doesNotMatch(html, /id=\"newWorker\"[^>]*checked/i);\n  assert.match(html, /Explicit recovery only/i);\n});\n\n`,
  'context relay mode test');
contextTest = replaceOnce(contextTest, "test('phone remains sovereign and Pro cannot own unlock loop'", "test('phone remains sovereign and workers cannot own unlock loop'", 'phone test title');
contextTest = replaceOnce(contextTest, "test('single worker scheduler still uses existing service-worker and relay architecture'", "test('bounded parallel scheduler still uses existing service-worker and relay architecture'", 'scheduler test title');
contextTest = replaceBetween(contextTest,
  "test('panel exposes evolution controls rather than disposable-worker swarm language'",
  "test('ChatGPT worker cannot self-accept or bypass final release'",
  `test('panel exposes bounded non-Pro swarm state and existing evolution controls', () => {\n  assert.match(html, /Advance campaign/);\n  assert.match(html, /Run evolution loop/);\n  assert.match(html, /She-Raw insults are load-bearing/i);\n  assert.match(html, /bounded to four concurrent tabs/i);\n  assert.match(panel, /high-inference non-Pro/);\n  assert.match(panel, /bounded-nonpro-swarm/);\n});\n\n`,
  'panel context test');
contextTest = replaceBetween(contextTest,
  "test('manifest identifies the single-Pro evolution organ'",
  "",
  `test('manifest identifies the bounded non-Pro swarm organ', () => {\n  assert.equal(manifest.version, '0.8.0');\n  assert.ok(manifest.permissions.includes('tabs'));\n  assert.match(manifest.description, /bounded high-inference non-Pro/i);\n  assert.match(manifest.key, /^MIIB/);\n  assert.equal(manifest.background.type, 'module');\n});\n`,
  'manifest context test');
write(contextTestPath, contextTest);

console.log(JSON.stringify({ok: true, patch: 'chromium-throne-nonpro-parallel-v1', files: [corePath, workerPath, panelPath, htmlPath, manifestPath, coreTestPath, contextTestPath]}));
