from pathlib import Path

api_path = Path('functions/computer_hands_api.js')
worker_path = Path('computer-hands/windows/home-center-hands.ps1')
repair_path = Path('computer-hands/windows/repair.ps1')

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)

api = api_path.read_text(encoding='utf-8')
api = replace_once(api,
"const MAX_RESULT_BYTES = 850 * 1024;\nconst READ_ACTIONS = new Set(['system.status', 'screen.capture', 'window.list', 'process.list', 'clipboard.get']);\nconst WRITE_ACTIONS = new Set(['window.focus', 'input.type', 'input.key', 'input.mouse', 'process.start', 'process.stop', 'shell.exec', 'clipboard.set']);\nconst HIGH_RISK_ACTIONS = new Set(['process.stop', 'shell.exec']);\nconst SUPPORTED_ACTIONS = Object.freeze([...READ_ACTIONS, ...WRITE_ACTIONS]);",
"const MAX_RESULT_BYTES = 850 * 1024;\nconst MAX_PACKET_STEPS = 32;\nconst MAX_PACKET_ARGUMENT_BYTES = 96 * 1024;\nconst PACKET_ACTION = 'packet.execute';\nconst READ_ACTIONS = new Set(['system.status', 'screen.capture', 'window.list', 'process.list', 'clipboard.get']);\nconst WRITE_ACTIONS = new Set(['window.focus', 'input.type', 'input.key', 'input.mouse', 'process.start', 'process.stop', 'shell.exec', 'clipboard.set']);\nconst HIGH_RISK_ACTIONS = new Set(['process.stop', 'shell.exec']);\nconst SUPPORTED_ACTIONS = Object.freeze([...READ_ACTIONS, ...WRITE_ACTIONS, PACKET_ACTION]);",
'constants')

api = replace_once(api,
"function permissionClass(action) { return READ_ACTIONS.has(action) ? 'read' : (HIGH_RISK_ACTIONS.has(action) ? 'high_risk_write' : 'write'); }\nfunction requireApproval(action, args) { if (!WRITE_ACTIONS.has(action)) return; if (args.approved !== true) throw Object.assign(new Error(`${action} requires approved=true.`), {status: 409, failureKind: 'computer_hands_confirmation_required'}); if (HIGH_RISK_ACTIONS.has(action) && args.highRiskApproved !== true) throw Object.assign(new Error(`${action} requires highRiskApproved=true.`), {status: 409, failureKind: 'computer_hands_high_risk_confirmation_required'}); }",
"function safeLaneId(value) { const text = safeText(value || 'lane-default', 160); return /^[A-Za-z0-9_.:-]{1,160}$/.test(text) ? text : `lane-${hash(text).slice(0, 24)}`; }\nfunction permissionClass(action, actionArgs = {}) {\n  if (action === PACKET_ACTION) {\n    let level = 'read';\n    for (const step of Array.isArray(actionArgs.steps) ? actionArgs.steps : []) {\n      const stepClass = permissionClass(step.action, step.arguments || {});\n      if (stepClass === 'high_risk_write') return 'high_risk_write';\n      if (stepClass === 'write') level = 'write';\n    }\n    return level;\n  }\n  return READ_ACTIONS.has(action) ? 'read' : (HIGH_RISK_ACTIONS.has(action) ? 'high_risk_write' : 'write');\n}\nfunction requireApproval(action, args, actionArgs = {}) {\n  const cls = permissionClass(action, actionArgs);\n  if (cls === 'read') return;\n  if (args.approved !== true) throw Object.assign(new Error(`${action} requires approved=true.`), {status: 409, failureKind: 'computer_hands_confirmation_required'});\n  if (cls === 'high_risk_write' && args.highRiskApproved !== true) throw Object.assign(new Error(`${action} requires highRiskApproved=true.`), {status: 409, failureKind: 'computer_hands_high_risk_confirmation_required'});\n}\nfunction sanitizeProgress(value) {\n  const input = value && typeof value === 'object' && !Array.isArray(value) ? value : {};\n  const completedSteps = Math.max(0, Math.min(MAX_PACKET_STEPS, Math.floor(Number(input.completedSteps || 0))));\n  const totalSteps = Math.max(0, Math.min(MAX_PACKET_STEPS, Math.floor(Number(input.totalSteps || 0))));\n  return {phase: safeText(input.phase, 80) || 'running', completedSteps, totalSteps, currentStepId: safeText(input.currentStepId, 160), currentAction: safeText(input.currentAction, 80), message: safeText(input.message, 400), updatedAtMs: Date.now()};\n}",
'permission and lane helpers')

api = replace_once(api,
"  if (action === 'screen.capture') { integer('maxWidth', 320, 2560); integer('quality', 20, 90); }",
"  if (action === PACKET_ACTION) {\n    const rawSteps = Array.isArray(input.steps) ? input.steps : [];\n    if (!rawSteps.length || rawSteps.length > MAX_PACKET_STEPS) throw Object.assign(new Error(`packet.execute requires 1-${MAX_PACKET_STEPS} steps.`), {status: 400, failureKind: 'computer_hands_invalid_packet'});\n    out.stopOnError = input.stopOnError !== false;\n    const label = safeText(input.label, 120); if (label) out.label = label;\n    out.steps = rawSteps.map((step, index) => {\n      if (!step || typeof step !== 'object' || Array.isArray(step)) throw Object.assign(new Error(`packet step ${index + 1} must be an object.`), {status: 400, failureKind: 'computer_hands_invalid_packet'});\n      const stepAction = actionName(step.action);\n      if (stepAction === PACKET_ACTION) throw Object.assign(new Error('Nested packet.execute is not supported.'), {status: 400, failureKind: 'computer_hands_invalid_packet'});\n      const stepId = safeText(step.id || `step-${String(index + 1).padStart(2, '0')}`, 160);\n      if (!/^[A-Za-z0-9_.:-]{1,160}$/.test(stepId)) throw Object.assign(new Error(`packet step ${index + 1} id is invalid.`), {status: 400, failureKind: 'computer_hands_invalid_packet'});\n      return {id: stepId, action: stepAction, arguments: sanitizeActionArgs(stepAction, step.arguments || {})};\n    });\n    if (Buffer.byteLength(JSON.stringify(out), 'utf8') > MAX_PACKET_ARGUMENT_BYTES) throw Object.assign(new Error('packet.execute arguments are too large.'), {status: 413, failureKind: 'computer_hands_packet_too_large'});\n    return out;\n  }\n  if (action === 'screen.capture') { integer('maxWidth', 320, 2560); integer('quality', 20, 90); }",
'packet sanitizer')
api = api.replace("if (action === 'input.type') { text('text', 12000);", "if (action === 'input.type') { text('text', 48000);")
api = api.replace("if (action === 'process.start') { text('command', 2000); text('arguments', 8000);", "if (action === 'process.start') { text('command', 4000); text('arguments', 32000);")
api = api.replace("if (action === 'shell.exec') { text('command', 16000);", "if (action === 'shell.exec') { text('command', 64000);")

start = api.index('async function workerStatusOperation')
end = api.index('\nasync function createRequestOperation', start)
api = api[:start] + '''async function workerStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const workerId = safeId(args.workerId || 'windows-hands-01', 'workerId');
  const snap = await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId)).get();
  if (!snap.exists) return {workerId, status: 'not_registered', online: false, fileLayer: 'drive_sync', capabilities: SUPPORTED_ACTIONS, queueDepth: 0, activeLanes: []};
  const row = snap.data() || {};
  const lastSeenAtMs = Number(row.lastSeenAtMs || 0);
  const pending = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', owner).limit(100).get();
  const rows = pending.docs.map((doc) => doc.data() || {}).filter((item) => item.workerId === workerId && ['queued', 'leased', 'running'].includes(item.status));
  const activeLanes = [...new Set(rows.map((item) => safeLaneId(item.laneId || 'lane-default')))];
  return {workerId, status: safeText(row.state, 80) || 'unknown', online: lastSeenAtMs > 0 && Date.now() - lastSeenAtMs < 30000, lastSeenAtMs, workerVersion: safeText(row.workerVersion, 120), machine: row.machine || null, capabilities: row.capabilities || SUPPORTED_ACTIONS, fileLayer: 'drive_sync', queueDepth: rows.length, activeLanes, lastServedLaneId: safeText(row.lastServedLaneId, 160)};
}
''' + api[end:]

start = api.index('async function createRequestOperation')
end = api.index('\nasync function requestStatusOperation', start)
api = api[:start] + '''async function createRequestOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const owner = ownerKey(safeEmail(user && user.email));
  const action = actionName(args.action);
  const actionArgs = sanitizeActionArgs(action, args.arguments || args.actionArgs || {});
  requireApproval(action, args, actionArgs);
  const workerId = safeId(args.workerId || 'windows-hands-01', 'workerId');
  const laneId = safeLaneId(args.laneId || args.threadId || 'lane-default');
  const ticketId = safeId(args.ticketId || `hands-${requestId}`, 'ticketId');
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId));
  const totalSteps = action === PACKET_ACTION ? actionArgs.steps.length : 1;
  let idempotent = false;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (snap.exists) {
      const old = snap.data() || {};
      if (old.requestId !== requestId || old.action !== action || old.laneId !== laneId || hash(JSON.stringify(old.arguments || {})) !== hash(JSON.stringify(actionArgs))) throw Object.assign(new Error('Computer Hands idempotency conflict.'), {status: 409});
      idempotent = true;
      return;
    }
    tx.create(ref, {apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, ticketId, requestId, ownerKey: owner, workerId, laneId, action, permissionClass: permissionClass(action, actionArgs), arguments: actionArgs, fileLayer: 'drive_sync', status: 'queued', progress: {phase: 'queued', completedSteps: 0, totalSteps, currentStepId: '', currentAction: '', message: safeText(actionArgs.label, 120), updatedAtMs: nowMs}, cancelRequested: false, createdAtMs: nowMs, updatedAtMs: nowMs, lease: null, result: null});
  });
  const row = (await ref.get()).data() || {};
  return {ticketId, requestId, laneId, action, permissionClass: row.permissionClass, status: row.status, workerId, idempotent, totalSteps, fileLayer: 'drive_sync'};
}
''' + api[end:]

start = api.index('async function requestStatusOperation')
end = api.index('\nasync function leaseRequest', start)
api = api[:start] + '''async function requestStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const ticketId = safeId(args.ticketId || `hands-${safeId(args.requestId, 'requestId')}`, 'ticketId');
  const snap = await admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId)).get();
  if (!snap.exists) throw Object.assign(new Error('Computer Hands request was not found.'), {status: 404});
  const row = snap.data() || {};
  return {ticketId, requestId: row.requestId, laneId: safeLaneId(row.laneId || 'lane-default'), action: row.action, permissionClass: row.permissionClass, status: row.status, progress: row.progress || null, result: row.result || null, workerId: row.workerId, cancelRequested: row.cancelRequested === true, updatedAtMs: row.updatedAtMs, fileLayer: 'drive_sync'};
}

async function cancelRequestOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const ticketId = safeId(args.ticketId || `hands-${safeId(args.targetRequestId || args.requestId, 'requestId')}`, 'ticketId');
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId));
  let result;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (!snap.exists) throw Object.assign(new Error('Computer Hands request was not found.'), {status: 404});
    const row = snap.data() || {};
    if (['completed', 'failed', 'cancelled'].includes(row.status)) { result = {ticketId, status: row.status, idempotent: true}; return; }
    tx.set(ref, {status: 'cancelled', cancelRequested: true, progress: {...(row.progress || {}), phase: 'cancelled', message: safeText(args.reason, 300) || 'Cancelled by owner.', updatedAtMs: nowMs}, updatedAtMs: nowMs}, {merge: true});
    result = {ticketId, status: 'cancelled', idempotent: false};
  });
  return result;
}
''' + api[end:]

start = api.index('async function leaseRequest')
end = api.index('\nasync function ticketForWorker', start)
api = api[:start] + '''async function leaseRequest({admin, worker, nowMs = Date.now()}) {
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId));
  const workerSnap = await workerRef.get();
  const lastServedLaneId = safeLaneId((workerSnap.exists && workerSnap.data()?.lastServedLaneId) || 'lane-default');
  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', worker.ownerKey).limit(100).get();
  const eligible = query.docs.map((doc) => ({ref: doc.ref, row: doc.data() || {}})).filter((item) => {
    if (item.row.workerId !== worker.workerId || item.row.cancelRequested === true || item.row.status === 'cancelled') return false;
    if (item.row.status === 'queued') return true;
    if (!['leased', 'running'].includes(item.row.status)) return false;
    return !item.row.lease || Number(item.row.lease.expiresAtMs || 0) <= nowMs;
  }).sort((a, b) => Number(a.row.createdAtMs || 0) - Number(b.row.createdAtMs || 0));

  const laneHeads = [];
  const seenLanes = new Set();
  for (const item of eligible) {
    const laneId = safeLaneId(item.row.laneId || 'lane-default');
    if (seenLanes.has(laneId)) continue;
    seenLanes.add(laneId);
    laneHeads.push({...item, laneId});
  }
  const ordered = laneHeads.length > 1
    ? [...laneHeads.filter((item) => item.laneId !== lastServedLaneId), ...laneHeads.filter((item) => item.laneId === lastServedLaneId)]
    : laneHeads;

  for (const item of ordered) {
    let leased = null;
    await admin.firestore().runTransaction(async (tx) => {
      const snap = await tx.get(item.ref);
      if (!snap.exists) return;
      const row = snap.data() || {};
      const active = row.lease && Number(row.lease.expiresAtMs || 0) > nowMs;
      if (row.cancelRequested === true || row.status === 'cancelled' || active) return;
      if (row.status === 'queued' || ['leased', 'running'].includes(row.status)) {
        leased = {...row, laneId: safeLaneId(row.laneId || 'lane-default'), status: 'leased', lease: {workerId: worker.workerId, leasedAtMs: nowMs, expiresAtMs: nowMs + LEASE_TTL_MS}, progress: {...(row.progress || {}), phase: 'leased', updatedAtMs: nowMs}, updatedAtMs: nowMs};
        tx.set(item.ref, leased, {merge: false});
      }
    });
    if (leased) {
      await workerRef.set({state: 'leased', lastSeenAtMs: nowMs, updatedAtMs: nowMs, lastServedLaneId: leased.laneId}, {merge: true});
      return {ticket: leased, pollAfterSeconds: 1};
    }
  }
  await workerRef.set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticket: null, pollAfterSeconds: 2};
}
''' + api[end:]

start = api.index('async function heartbeat(')
end = api.index('\nasync function completeRequest', start)
api = api[:start] + '''async function heartbeat({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  if (found.row.cancelRequested === true || found.row.status === 'cancelled') return {ticketId, status: 'cancelled', cancelRequested: true};
  const lease = found.row.lease || {};
  if (lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  const progress = args.progress ? sanitizeProgress(args.progress) : {...(found.row.progress || {}), phase: safeText(args.phase, 80) || 'running', updatedAtMs: nowMs};
  await found.ref.set({status: 'running', phase: safeText(args.phase, 80) || 'running', progress, lease: {...lease, expiresAtMs: nowMs + LEASE_TTL_MS}, updatedAtMs: nowMs}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'running', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticketId, status: 'running', cancelRequested: false};
}
''' + api[end:]

start = api.index('async function completeRequest(')
end = api.index('\n\nfunction computerHandsOperationEntries', start)
api = api[:start] + '''async function completeRequest({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  if (found.row.cancelRequested === true || found.row.status === 'cancelled') return {ticketId, status: 'cancelled', resultBytes: 0, discarded: true};
  if (!found.row.lease || found.row.lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  const result = args.result && typeof args.result === 'object' && !Array.isArray(args.result) ? args.result : {ok: false, error: 'worker_result_missing'};
  const bytes = Buffer.byteLength(JSON.stringify(result), 'utf8');
  if (bytes > MAX_RESULT_BYTES) throw Object.assign(new Error('Computer Hands evidence envelope is too large.'), {status: 413});
  const status = result.ok === false ? 'failed' : 'completed';
  const totalSteps = Number(found.row.progress?.totalSteps || (found.row.action === PACKET_ACTION ? found.row.arguments?.steps?.length : 1) || 1);
  await found.ref.set({status, lease: null, result, progress: {...(found.row.progress || {}), phase: status, completedSteps: status === 'completed' ? totalSteps : Number(found.row.progress?.completedSteps || 0), totalSteps, updatedAtMs: nowMs}, completedAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticketId, status, resultBytes: bytes};
}
''' + api[end:]

api = api.replace("'computer_hands.request.create': {summary: 'Queue a computer action. Reads need no approval. UI/process/clipboard writes require approved=true; shell.exec and process.stop also require highRiskApproved=true. No file-transfer API: Drive sync owns files.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional', action: SUPPORTED_ACTIONS.join('|'), arguments: 'action-specific object', approved: 'boolean for writes', highRiskApproved: 'boolean for high-risk writes'}},",
"'computer_hands.request.create': {summary: 'Queue one computer action or a bounded packet.execute sequence. Multiple ChatGPT threads should provide distinct laneId values; one physical desktop remains serialized with fair lane scheduling. Reads need no approval. Writes require approved=true; high-risk writes also require highRiskApproved=true. Drive sync owns files.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional', laneId: 'stable thread/lane id', action: SUPPORTED_ACTIONS.join('|'), arguments: 'action-specific object; packet.execute accepts up to 32 steps', approved: 'boolean for writes', highRiskApproved: 'boolean for high-risk writes'}},\n  'computer_hands.request.cancel': {summary: 'Cancel a queued/running Computer Hands request. Packet workers observe cancellation between steps.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'audit id', ticketId: 'target ticket id', targetRequestId: 'target request id alias', reason: 'optional'}},")
api = api.replace("if (operation === 'computer_hands.request.create') return createRequestOperation({admin, user, args}); if (operation === 'computer_hands.request.status') return requestStatusOperation({admin, user, args});",
"if (operation === 'computer_hands.request.create') return createRequestOperation({admin, user, args}); if (operation === 'computer_hands.request.cancel') return cancelRequestOperation({admin, user, args}); if (operation === 'computer_hands.request.status') return requestStatusOperation({admin, user, args});")
api = api.replace("sanitizeActionArgs, permissionClass, computerHandsOperationEntries", "sanitizeActionArgs, permissionClass, safeLaneId, computerHandsOperationEntries")
api_path.write_text(api, encoding='utf-8')

worker = worker_path.read_text(encoding='utf-8')
worker = replace_once(worker,
"$LogPath = if ($Cfg.logPath) { [string]$Cfg.logPath } else { Join-Path (Split-Path $ConfigPath) 'worker.log' }",
"$LogPath = if ($Cfg.logPath) { [string]$Cfg.logPath } else { Join-Path (Split-Path $ConfigPath) 'worker.log' }\n$progressProperty = $Cfg.PSObject.Properties['progressPath']\n$ProgressPath = if ($progressProperty -and $progressProperty.Value) { [string]$progressProperty.Value } else { Join-Path (Split-Path $ConfigPath) 'progress.json' }",
'worker progress path')
worker = replace_once(worker,
"function Invoke-HandsApi([string]$Method, [string]$Path, [object]$Body = $null) {",
"function Write-ProgressState([object]$State) {\n  try {\n    $payload = [ordered]@{\n      updatedAt = (Get-Date).ToUniversalTime().ToString('o')\n      workerId = $WorkerId\n      machine = $env:COMPUTERNAME\n      pid = $PID\n      state = $State\n    } | ConvertTo-Json -Depth 12\n    $directory = Split-Path -Parent $ProgressPath\n    if ($directory) { [IO.Directory]::CreateDirectory($directory) | Out-Null }\n    $temp = \"$ProgressPath.tmp\"\n    [IO.File]::WriteAllText($temp, $payload, [Text.UTF8Encoding]::new($false))\n    Move-Item -Force $temp $ProgressPath\n  } catch { Log \"progress_write_failed $($_.Exception.Message)\" }\n}\n\nfunction Invoke-HandsApi([string]$Method, [string]$Path, [object]$Body = $null) {",
'worker progress writer')

start = worker.index('function Execute-Ticket')
end = worker.index('\n\nLog "worker_start', start)
replacement = r'''function Execute-Action([string]$Action, [object]$ActionArgs) {
  $a=$ActionArgs
  switch($Action){
    'system.status'{return Get-SystemStatus}
    'screen.capture'{return Capture-Screen $a}
    'window.list'{return Get-WindowList}
    'window.focus'{return Focus-Window $a}
    'process.list'{return Get-ProcessList}
    'process.start'{$command=[string](Get-ActionArg $a 'command' '');if(-not $command){throw 'process.start command was missing from the leased ticket.'};$sp=@{FilePath=$command;PassThru=$true};$processArguments=[string](Get-ActionArg $a 'arguments' '');$workingDirectory=[string](Get-ActionArg $a 'workingDirectory' '');if($processArguments){$sp.ArgumentList=$processArguments};if($workingDirectory){$sp.WorkingDirectory=$workingDirectory};$p=Start-Process @sp;return @{ok=$true;pid=$p.Id;name=$p.ProcessName}}
    'process.stop'{Stop-Process -Id ([int]$a.pid) -ErrorAction Stop;return @{ok=$true;pid=[int]$a.pid}}
    'input.type'{[HomeCenterHandsNative]::TypeUnicode([string]$a.text);return @{ok=$true;characters=([string]$a.text).Length}}
    'input.key'{Invoke-Key ([string]$a.key);return @{ok=$true;key=[string]$a.key}}
    'input.mouse'{return Invoke-Mouse $a}
    'clipboard.get'{return @{ok=$true;text=[string](Get-Clipboard -Raw -ErrorAction Stop)}}
    'clipboard.set'{Set-Clipboard -Value ([string]$a.text);return @{ok=$true;characters=([string]$a.text).Length}}
    'shell.exec'{return Run-Shell $a}
    default{throw "Unsupported action: $Action"}
  }
}

function Execute-Ticket([object]$Ticket) {
  $action=[string]$Ticket.action
  $a=$Ticket.arguments
  if($action -ne 'packet.execute'){ return Execute-Action $action $a }

  $steps=@(Get-ActionArg $a 'steps' @())
  $stopOnError=[bool](Get-ActionArg $a 'stopOnError' $true)
  $results=New-Object System.Collections.Generic.List[object]
  $completed=0
  $allOk=$true
  for($index=0;$index -lt $steps.Count;$index+=1){
    $step=$steps[$index]
    $stepId=[string](Get-ActionArg $step 'id' ("step-{0:d2}" -f ($index+1)))
    $stepAction=[string](Get-ActionArg $step 'action' '')
    $stepArgs=Get-ActionArg $step 'arguments' ([pscustomobject]@{})
    $progress=@{phase='packet_step';completedSteps=$completed;totalSteps=$steps.Count;currentStepId=$stepId;currentAction=$stepAction;message=("Running {0}/{1}: {2}" -f ($index+1),$steps.Count,$stepAction)}
    Write-ProgressState @{ticketId=$Ticket.ticketId;requestId=$Ticket.requestId;laneId=$Ticket.laneId;action=$action;progress=$progress}
    $heartbeat=Invoke-HandsApi 'POST' "tickets/$($Ticket.ticketId)/heartbeat" @{phase='packet_step';progress=$progress}
    if($heartbeat.cancelRequested -eq $true){
      return @{ok=$false;cancelled=$true;packet=$true;completedSteps=$completed;totalSteps=$steps.Count;steps=@($results)}
    }
    try{
      $stepResult=Execute-Action $stepAction $stepArgs
      $completed+=1
      $results.Add([pscustomobject]@{id=$stepId;action=$stepAction;ok=($stepResult.ok -ne $false);result=$stepResult})
      if($stepResult.ok -eq $false){$allOk=$false;if($stopOnError){break}}
    }catch{
      $allOk=$false
      $results.Add([pscustomobject]@{id=$stepId;action=$stepAction;ok=$false;error=$_.Exception.Message})
      if($stopOnError){break}
    }
  }
  return @{ok=$allOk;packet=$true;completedSteps=$completed;totalSteps=$steps.Count;steps=@($results)}
}'''
worker = worker[:start] + replacement + worker[end:]

worker = replace_once(worker,
"Log \"worker_start workerId=$WorkerId pid=$PID\"\nwhile($true){\n  try{\n    $lease=Invoke-HandsApi 'POST' 'lease' @{};if(-not $lease.ticket){Start-Sleep -Seconds ([Math]::Max(1,[int]$lease.pollAfterSeconds));continue};$ticket=$lease.ticket;Log \"ticket_leased id=$($ticket.ticketId) action=$($ticket.action)\"\n    try{[void](Invoke-HandsApi 'POST' \"tickets/$($ticket.ticketId)/heartbeat\" @{phase='executing'});$result=Execute-Ticket $ticket;[void](Invoke-HandsApi 'POST' \"tickets/$($ticket.ticketId)/complete\" @{result=$result});Log \"ticket_complete id=$($ticket.ticketId) ok=$($result.ok)\"}\n    catch{$failure=@{ok=$false;error='worker_action_failed';detail=$_.Exception.Message;action=[string]$ticket.action};try{[void](Invoke-HandsApi 'POST' \"tickets/$($ticket.ticketId)/complete\" @{result=$failure})}catch{Log \"ticket_failure_report_failed id=$($ticket.ticketId) detail=$($_.Exception.Message)\"};Log \"ticket_failed id=$($ticket.ticketId) detail=$($failure.detail)\"}\n  }catch{Log \"poll_error $($_.Exception.Message)\";Start-Sleep -Seconds 5}\n}",
"Log \"worker_start workerId=$WorkerId pid=$PID\"\nWrite-ProgressState @{phase='worker_start';message='Computer Hands worker started.'}\nwhile($true){\n  try{\n    $lease=Invoke-HandsApi 'POST' 'lease' @{}\n    if(-not $lease.ticket){Write-ProgressState @{phase='idle';message='Waiting for work.'};Start-Sleep -Seconds ([Math]::Max(1,[int]$lease.pollAfterSeconds));continue}\n    $ticket=$lease.ticket\n    Log \"ticket_leased id=$($ticket.ticketId) lane=$($ticket.laneId) action=$($ticket.action)\"\n    Write-ProgressState @{phase='leased';ticketId=$ticket.ticketId;requestId=$ticket.requestId;laneId=$ticket.laneId;action=$ticket.action;progress=$ticket.progress}\n    try{\n      $heartbeat=Invoke-HandsApi 'POST' \"tickets/$($ticket.ticketId)/heartbeat\" @{phase='executing';progress=@{phase='executing';completedSteps=0;totalSteps=if($ticket.action -eq 'packet.execute'){@($ticket.arguments.steps).Count}else{1};currentStepId='';currentAction=[string]$ticket.action;message='Executing ticket.'}}\n      if($heartbeat.cancelRequested -eq $true){Write-ProgressState @{phase='cancelled';ticketId=$ticket.ticketId;laneId=$ticket.laneId;message='Ticket cancelled before execution.'};continue}\n      $result=Execute-Ticket $ticket\n      [void](Invoke-HandsApi 'POST' \"tickets/$($ticket.ticketId)/complete\" @{result=$result})\n      Write-ProgressState @{phase=if($result.cancelled){'cancelled'}elseif($result.ok -eq $false){'failed'}else{'completed'};ticketId=$ticket.ticketId;requestId=$ticket.requestId;laneId=$ticket.laneId;action=$ticket.action;result=$result}\n      Log \"ticket_complete id=$($ticket.ticketId) ok=$($result.ok)\"\n    }catch{\n      $failure=@{ok=$false;error='worker_action_failed';detail=$_.Exception.Message;action=[string]$ticket.action}\n      try{[void](Invoke-HandsApi 'POST' \"tickets/$($ticket.ticketId)/complete\" @{result=$failure})}catch{Log \"ticket_failure_report_failed id=$($ticket.ticketId) detail=$($_.Exception.Message)\"}\n      Write-ProgressState @{phase='failed';ticketId=$ticket.ticketId;requestId=$ticket.requestId;laneId=$ticket.laneId;action=$ticket.action;error=$failure.detail}\n      Log \"ticket_failed id=$($ticket.ticketId) detail=$($failure.detail)\"\n    }\n  }catch{Log \"poll_error $($_.Exception.Message)\";Write-ProgressState @{phase='poll_error';message=$_.Exception.Message};Start-Sleep -Seconds 3}\n}",
'worker main loop')
worker_path.write_text(worker, encoding='utf-8')

repair = repair_path.read_text(encoding='utf-8')
repair = repair.replace("$WorkerLog = Join-Path $Root 'worker.log'", "$WorkerLog = Join-Path $Root 'worker.log'\n$ProgressPath = Join-Path $Root 'progress.json'")
repair = repair.replace("$secure = Get-Content -LiteralPath $TokenPath -Raw | ConvertTo-SecureString", "$secure = (Get-Content -LiteralPath $TokenPath -Raw).Trim() | ConvertTo-SecureString")
needle = "if (-not $cfg.origin -or -not $cfg.workerId -or -not $cfg.tokenPath) { throw 'Computer Hands config is incomplete.' }"
insert = needle + "\n$driveProgress = Get-PSDrive -PSProvider FileSystem | ForEach-Object { Join-Path $_.Root 'My Drive\\Venice Runtime\\Venice Reconstruction' } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1\nif ($driveProgress) { $ProgressPath = Join-Path $driveProgress 'LOCAL_HANDS_PROGRESS.json' }\n$cfg | Add-Member -NotePropertyName progressPath -NotePropertyValue $ProgressPath -Force\n[IO.File]::WriteAllText($ConfigPath, ($cfg | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))"
repair = replace_once(repair, needle, insert, 'repair progress config')
repair = repair.replace("  workerLog = if (Test-Path -LiteralPath $WorkerLog) { @(Get-Content -LiteralPath $WorkerLog -Tail 30) } else { @('worker.log missing') }", "  workerLog = if (Test-Path -LiteralPath $WorkerLog) { @(Get-Content -LiteralPath $WorkerLog -Tail 30) } else { @('worker.log missing') }\n  progressPath = $ProgressPath\n  progress = if (Test-Path -LiteralPath $ProgressPath) { Get-Content -LiteralPath $ProgressPath -Raw } else { 'progress missing' }")
repair_path.write_text(repair, encoding='utf-8')

# Add focused contract tests that do not require Firestore.
test = Path('functions/computer_hands_shared_lanes.test.js')
test.write_text(r'''\n'use strict';\nconst test = require('node:test');\nconst assert = require('node:assert/strict');\nconst api = require('./computer_hands_api');\n\ntest('packet.execute sanitizes bounded multi-step packets', () => {\n  const packet = api.sanitizeActionArgs('packet.execute', {label: 'archaeology', steps: [\n    {id: 'status', action: 'system.status', arguments: {}},\n    {id: 'windows', action: 'window.list', arguments: {}},\n    {id: 'shell', action: 'shell.exec', arguments: {command: 'Get-Date'}},\n  ]});\n  assert.equal(packet.steps.length, 3);\n  assert.equal(packet.steps[2].arguments.command, 'Get-Date');\n  assert.equal(api.permissionClass('packet.execute', packet), 'high_risk_write');\n});\n\ntest('packet nesting and oversize step counts fail closed', () => {\n  assert.throws(() => api.sanitizeActionArgs('packet.execute', {steps: [{action: 'packet.execute', arguments: {steps: []}}]}), /Nested packet/);\n  assert.throws(() => api.sanitizeActionArgs('packet.execute', {steps: Array.from({length: 33}, () => ({action: 'system.status'}))}), /1-32/);\n});\n\ntest('lane ids preserve safe ids and hash unsafe thread names', () => {\n  assert.equal(api.safeLaneId('chat.thread-01'), 'chat.thread-01');\n  assert.match(api.safeLaneId('thread with spaces / punctuation'), /^lane-[0-9a-f]{24}$/);\n});\n'''.lstrip(), encoding='utf-8')

print('Computer Hands shared lanes v3 patch applied')
