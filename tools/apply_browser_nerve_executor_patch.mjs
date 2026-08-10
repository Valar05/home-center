import fs from 'node:fs';

function read(file) { return fs.readFileSync(file, 'utf8'); }
function write(file, text) { fs.writeFileSync(file, text, 'utf8'); }
function replaceOnce(text, from, to, label) {
  if (text.includes(to)) return text;
  const first = text.indexOf(from);
  if (first < 0) throw new Error(`Missing ${label} anchor.`);
  if (text.indexOf(from, first + from.length) >= 0) throw new Error(`Ambiguous ${label} anchor.`);
  return text.slice(0, first) + to + text.slice(first + from.length);
}
function insertAfterOnce(text, anchor, insertion, label) {
  if (text.includes(insertion.trim())) return text;
  const first = text.indexOf(anchor);
  if (first < 0) throw new Error(`Missing ${label} anchor.`);
  if (text.indexOf(anchor, first + anchor.length) >= 0) throw new Error(`Ambiguous ${label} anchor.`);
  return text.slice(0, first + anchor.length) + insertion + text.slice(first + anchor.length);
}

// ---- Browser Nerve cloud API: never persist an explicit undefined field. ----
const apiPath = 'functions/browser_nerve_api.js';
let api = read(apiPath);
api = replaceOnce(
  api,
  "  await found.ref.set({status, lease: null, result: {...result, value: undefined}, completedAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});",
  "  const storedResult = {...result};\n  delete storedResult.value;\n  await found.ref.set({status, lease: null, result: storedResult, completedAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});",
  'Browser Nerve stored-result redaction',
);
write(apiPath, api);

// ---- Windows installer: valid PowerShell here-string. ----
const installerPath = 'browser-nerve/windows/install.ps1';
let installer = read(installerPath);
installer = replaceOnce(installer, "@'{\n  \"name\":", "@'\n{\n  \"name\":", 'PowerShell package here-string');
write(installerPath, installer);

// ---- Windows worker: report executor failures durably before returning to poll loop. ----
const workerPath = 'browser-nerve/windows/home-center-browser-nerve.ps1';
let worker = read(workerPath);
const workerOld = `    $hb = Invoke-Api 'POST' "tickets/$($ticket.ticketId)/heartbeat" @{phase='running';message="Executing $($ticket.action)";machine=$env:COMPUTERNAME;browser='chrome-cdp';workerVersion=$WorkerVersion}\n    if ($hb.cancelRequested -eq $true) { Write-Progress @{phase='cancelled';ticketId=$ticket.ticketId}; continue }\n    $result = Invoke-Executor $ticket\n    $completion = Invoke-Api 'POST' "tickets/$($ticket.ticketId)/complete" @{result=$result}\n    Write-Progress @{phase=$completion.status;ticketId=$ticket.ticketId;sessionId=$ticket.sessionId;action=$ticket.action;episodeId=$completion.episodeId;ok=($result.ok -ne $false)}\n    Log "ticket_complete id=$($ticket.ticketId) status=$($completion.status) episode=$($completion.episodeId)"`;
const workerNew = `    try {\n      $hb = Invoke-Api 'POST' "tickets/$($ticket.ticketId)/heartbeat" @{phase='running';message="Executing $($ticket.action)";machine=$env:COMPUTERNAME;browser='chrome-cdp';workerVersion=$WorkerVersion}\n      if ($hb.cancelRequested -eq $true) { Write-Progress @{phase='cancelled';ticketId=$ticket.ticketId}; continue }\n      $result = Invoke-Executor $ticket\n      $completion = Invoke-Api 'POST' "tickets/$($ticket.ticketId)/complete" @{result=$result}\n      Write-Progress @{phase=$completion.status;ticketId=$ticket.ticketId;sessionId=$ticket.sessionId;action=$ticket.action;episodeId=$completion.episodeId;ok=($result.ok -ne $false)}\n      Log "ticket_complete id=$($ticket.ticketId) status=$($completion.status) episode=$($completion.episodeId)"\n    } catch {\n      $detail = $_.Exception.Message\n      Log "ticket_action_failed id=$($ticket.ticketId) detail=$detail"\n      try {\n        $failed = Invoke-Api 'POST' "tickets/$($ticket.ticketId)/complete" @{result=@{ok=$false;error=$detail;workerVersion=$WorkerVersion;browser='chrome-cdp'}}\n        Write-Progress @{phase=$failed.status;ticketId=$ticket.ticketId;sessionId=$ticket.sessionId;action=$ticket.action;episodeId=$failed.episodeId;ok=$false;error=$detail}\n      } catch {\n        Log "ticket_failure_report_failed id=$($ticket.ticketId) detail=$($_.Exception.Message)"\n        Write-Progress @{phase='failure_report_failed';ticketId=$ticket.ticketId;error=$detail}\n      }\n    }`;
worker = replaceOnce(worker, workerOld, workerNew, 'Browser Nerve worker ticket body');
write(workerPath, worker);

// ---- Command Center: enqueue every allowed browser action onto Browser Nerve. ----
const commandPath = 'functions/command_center_mcp.js';
let command = read(commandPath);
command = insertAfterOnce(
  command,
  "const {APP_CONTROL_COLLECTIONS, APP_CONTROL_DEFAULT_SEEDS, appControlProfileObjectId, appControlProfilePath} = require('./app_control_cloud');",
  "\nconst {enqueueBrowserNerveTicket} = require('./browser_nerve_api');",
  'Browser Nerve Command Center import',
);
command = replaceOnce(command,
  "    runtime: safeText(surface.runtime, 80) || 'playwright',\n    browser: safeText(surface.browser, 80) || 'chromium',",
  "    runtime: safeText(surface.runtime, 80) || 'browser_nerve',\n    browser: safeText(surface.browser, 80) || 'chrome',",
  'browser surface runtime defaults',
);
command = replaceOnce(command,
  "    workerId: safeText(surface.workerId, 120),",
  "    workerId: safeText(surface.workerId, 120) || 'windows-browser-nerve-01',",
  'browser surface worker default',
);
const actionTailOld = `    await appendEvent(admin, {type: 'browser_action_' + status, projectId: 'home-center', actor: caller.actor, summary: \`${'${action}'}: \${status}\`, data: payload});\n    return {action: payload};`;
const actionTailNew = `    let execution = null;\n    if (status === 'requested') {\n      execution = await enqueueBrowserNerveTicket({\n        admin,\n        caller,\n        args: {sessionId, actionId, action, target: payload.target, value: args.value, reason: payload.reason, workerId: safeText(args.workerId, 120) || 'windows-browser-nerve-01'},\n      });\n    }\n    const eventPayload = {...payload, execution: execution ? {ticketId: execution.ticketId, workerId: execution.workerId, status: execution.status} : null};\n    await appendEvent(admin, {type: 'browser_action_' + status, projectId: 'home-center', actor: caller.actor, summary: \`${'${action}'}: \${status}\`, data: eventPayload});\n    return {action: {...payload, execution}};`;
command = replaceOnce(command, actionTailOld, actionTailNew, 'browser action enqueue tail');
command = replaceOnce(command,
  "inputSchema: {idempotencyKey: z.string(), sessionId: z.string(), actionId: z.string().optional(), action: z.string(), target: z.record(z.string(), z.any()).optional(), value: z.string().optional(), reason: z.string().optional()},",
  "inputSchema: {idempotencyKey: z.string(), sessionId: z.string(), actionId: z.string().optional(), action: z.string(), target: z.record(z.string(), z.any()).optional(), value: z.string().optional(), reason: z.string().optional(), workerId: z.string().optional()},",
  'browser action schema workerId',
);
write(commandPath, command);

// ---- Venice body router: fresh worker observation is an action; poll episodes for bounded proof. ----
const routerPath = 'functions/venice_body_router.js';
let router = read(routerPath);
router = replaceOnce(router,
  "      surface: {runtime: 'playwright', browser: 'chromium', mode: 'desktop'},",
  "      surface: {runtime: 'browser_nerve', browser: 'chrome', mode: 'desktop', workerId: safeText(args.browserWorkerId, 160) || 'windows-browser-nerve-01'},",
  'Venice router browser surface',
);
const observeOld = `  if (verb === 'browser.observe' || verb === 'browser.status') {\n    const observation = await runCommandCenterOperation(admin, extra, 'browser_sessions.observe', {sessionId, limit: 10});\n    return {sessionId, session, observation, verified: observation && observation.found === true, state: observation && observation.found ? 'observed' : 'not_found'};\n  }`;
const observeNew = `  if (verb === 'browser.status') {\n    const observation = await runCommandCenterOperation(admin, extra, 'browser_sessions.observe', {sessionId, limit: 10});\n    return {sessionId, session, observation, verified: observation && observation.found === true, state: observation && observation.found ? 'observed' : 'not_found'};\n  }`;
router = replaceOnce(router, observeOld, observeNew, 'browser status-only observation');
router = replaceOnce(router,
  "    reason: intent,\n  });\n  let observation = null;",
  "    reason: intent,\n    workerId: safeText(args.browserWorkerId, 160) || 'windows-browser-nerve-01',\n  });\n  let observation = null;",
  'browser worker routing argument',
);
const pollOld = `  try {\n    observation = await runCommandCenterOperation(admin, extra, 'browser_sessions.observe', {sessionId, limit: 20});\n  } catch (error) {\n    observeError = safeText(error && error.message, 1000);\n  }\n  const actionRecord = action && action.action || null;\n  const actionId = safeText(actionRecord && actionRecord.actionId, 180);\n  const verified = browserEpisodeVerifiesAction(observation, actionId);`;
const pollNew = `  const actionRecord = action && action.action || null;\n  const actionId = safeText(actionRecord && actionRecord.actionId, 180);\n  const actionStatus = safeText(actionRecord && actionRecord.status, 80);\n  const waitMs = Math.max(0, Math.min(Number(args.browserWaitMs) || 12000, 30000));\n  const deadline = Date.now() + (actionStatus === 'requested' ? waitMs : 0);\n  do {\n    try {\n      observation = await runCommandCenterOperation(admin, extra, 'browser_sessions.observe', {sessionId, limit: 20});\n      observeError = '';\n    } catch (error) {\n      observeError = safeText(error && error.message, 1000);\n    }\n    if (browserEpisodeVerifiesAction(observation, actionId) || Date.now() >= deadline) break;\n    await new Promise((resolve) => setTimeout(resolve, 250));\n  } while (true);\n  const verified = browserEpisodeVerifiesAction(observation, actionId);`;
router = replaceOnce(router, pollOld, pollNew, 'browser episode polling');
router = replaceOnce(router,
  "        browserSessionId: 'optional existing Browser Nerve session id',",
  "        browserSessionId: 'optional existing Browser Nerve session id',\n        browserWorkerId: 'optional Browser Nerve worker id',\n        browserWaitMs: 'optional 0-30000 bounded wait for durable episode evidence',",
  'Venice body Browser Nerve inputs',
);
write(routerPath, router);

// ---- Home Center stable operation registry: expose Browser Nerve register/status. ----
const mcpPath = 'functions/home_center_mcp.js';
let mcp = read(mcpPath);
mcp = insertAfterOnce(
  mcp,
  "const {computerHandsOperationEntries, computerHandsOperationRunOperation} = require('./computer_hands_api');",
  "\nconst {browserNerveOperationEntries, browserNerveOperationRunOperation} = require('./browser_nerve_api');",
  'Home Center Browser Nerve import',
);
if (!mcp.includes('...browserNerveOperationEntries()')) {
  mcp = replaceOnce(mcp, '...computerHandsOperationEntries(),', '...computerHandsOperationEntries(),\n    ...browserNerveOperationEntries(),', 'Home Center Browser Nerve registry spread');
}
if (!mcp.includes('browserNerveOperationRunOperation({')) {
  const blockRegex = /if\s*\(\s*computerHandsOperationEntries\(\)\[operation\]\s*\)\s*\{([\s\S]{0,1600}?)\n\s*\}/;
  const block = mcp.match(blockRegex);
  if (!block || !block[0].includes('computerHandsOperationRunOperation')) throw new Error('Could not locate Computer Hands dispatcher for Browser Nerve clone.');
  const clone = block[0]
    .replaceAll('computerHandsOperationEntries', 'browserNerveOperationEntries')
    .replaceAll('computerHandsOperationRunOperation', 'browserNerveOperationRunOperation');
  mcp = mcp.replace(block[0], `${block[0]}\n  ${clone}`);
}
write(mcpPath, mcp);

// ---- Function export: dedicated Browser Nerve HTTPS queue endpoint. ----
const indexPath = 'functions/index.js';
let index = read(indexPath);
index = insertAfterOnce(index,
  "const {createComputerHandsHandler} = require('./computer_hands_api');",
  "\nconst {createBrowserNerveHandler} = require('./browser_nerve_api');",
  'Browser Nerve function import',
);
index = insertAfterOnce(index,
  "exports.computerHands = onRequest({timeoutSeconds: 300}, createComputerHandsHandler({admin}));",
  "\n\nexports.browserNerve = onRequest({timeoutSeconds: 300}, createBrowserNerveHandler({admin}));",
  'Browser Nerve function export',
);
write(indexPath, index);

const checks = {
  apiStoredResultSafe: api.includes('delete storedResult.value'),
  validHereString: installer.includes("@'\n{\n  \"name\":"),
  workerReportsFailure: worker.includes('ticket_failure_report_failed'),
  commandEnqueues: command.includes('enqueueBrowserNerveTicket'),
  routerPolls: router.includes('browserWaitMs') && router.includes('setTimeout(resolve, 250)'),
  mcpExposes: mcp.includes('browserNerveOperationEntries') && mcp.includes('browserNerveOperationRunOperation'),
  functionExported: index.includes('exports.browserNerve'),
};
if (Object.values(checks).some((value) => !value)) throw new Error(`Browser Nerve integration incomplete: ${JSON.stringify(checks)}`);
console.log(JSON.stringify({ok: true, checks, contract: 'browser_nerve_owns_page__computer_hands_owns_machine'}));
