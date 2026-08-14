'use strict';

const {createHash} = require('node:crypto');
const {enqueuePhoneCommand, getPhoneCommand} = require('./phone_hands_relay');
const {callerFromHomeCenterUser} = require('./home_center_fortress');
const {
  DUNGEON_RUN_SCHEMA,
  DUNGEON_STATUS_SCHEMA,
  cleanDungeonRun,
  cleanDungeonStatus,
  dungeonAdmissionTtlMs,
} = require('./dungeon_run_contract');

function boundedCommand(record) {
  const expiresAtMs = Number(record.expiresAtMs || 0);
  const admissionExpired = record.status === 'queued' && expiresAtMs > 0 && expiresAtMs <= Date.now();
  return {
    commandId: record.commandId,
    deviceId: record.deviceId,
    state: admissionExpired ? 'expired' : record.status,
    requestHash: record.requestHash || '',
    createdAtMs: Number(record.createdAtMs || 0),
    updatedAtMs: Number(record.updatedAtMs || 0),
    expiresAtMs,
    result: record.result == null ? null : record.result,
    error: String(admissionExpired ? 'admission expired before a device lease; replay the same exact requestId to renew this command' : (record.error || '')).slice(0, 4000),
  };
}

async function dungeonRunOperation({admin, user, caller: suppliedCaller, args = {}} = {}) {
  const caller = suppliedCaller || callerFromHomeCenterUser(user, 'Adam');
  const action = cleanDungeonRun({...args, action: 'dungeon_run', schema: args.schema || DUNGEON_RUN_SCHEMA});
  const record = await enqueuePhoneCommand(admin, caller, {
    idempotencyKey: action.requestId,
    deviceId: action.deviceId,
    action,
    ttlMs: dungeonAdmissionTtlMs(action),
  });
  return {
    schema: 'home-center.dungeon-admission.v2',
    ...boundedCommand(record),
    attached: Boolean(record.attached),
    next: {operation: 'dungeon_command_status', args: {commandId: record.commandId}},
  };
}

async function dungeonStatusOperation({admin, user, args = {}} = {}) {
  const caller = callerFromHomeCenterUser(user, 'Adam');
  const action = cleanDungeonStatus({...args, action: 'dungeon_status', schema: args.schema || DUNGEON_STATUS_SCHEMA});
  const record = await enqueuePhoneCommand(admin, caller, {
    idempotencyKey: action.requestId,
    deviceId: action.deviceId,
    action,
    ttlMs: dungeonAdmissionTtlMs(action),
  });
  return {
    schema: 'home-center.dungeon-status-admission.v2',
    ...boundedCommand(record),
    attached: Boolean(record.attached),
    next: {operation: 'dungeon_command_status', args: {commandId: record.commandId}},
  };
}

async function dungeonCommandStatusOperation({admin, user, args = {}} = {}) {
  const caller = callerFromHomeCenterUser(user, 'Adam');
  const record = await getPhoneCommand(admin, caller, args);
  return {schema: 'home-center.dungeon-command-status.v2', ...boundedCommand(record)};
}

function dungeonOperationEntries() {
  return {
    dungeon_run: {
      summary: 'Admit one typed phone-local Codex campaign into an isolated tmux worktree with deterministic-first fallback, durable local receipts, and no Command Center or caller-supplied shell surface.',
      write: true,
      requiresRequestId: true,
      requiredScopes: [],
      input: {
        schema: DUNGEON_RUN_SCHEMA,
        requestId: 'stable exact-intent id',
        deviceId: 'optional registered phone id; default primary-phone',
        campaignId: 'bounded campaign slug',
        workspaceId: 'phone-local registered workspace id; never a path',
        objective: 'bounded exact objective',
        acceptance: '1-24 exact acceptance strings',
        constraints: 'optional 0-24 binding constraints',
        taskKind: 'implement|repair|verify|review|research',
        lane: 'critical|standard|background; critical requires criticalReason',
        budgetProfile: 'probe|standard|long',
        verificationProfile: 'fast|default|full',
        inferencePolicy: 'fixed codex-local-low-deterministic-v1',
        publicationPolicy: 'fixed checkpoint-only',
      },
    },
    dungeon_status: {
      summary: 'Enqueue a typed read of one phone-local dungeon job receipt by opaque job id.',
      write: true,
      requiresRequestId: true,
      requiredScopes: [],
      input: {schema: DUNGEON_STATUS_SCHEMA, requestId: 'fresh unique snapshot id for each poll', deviceId: 'optional registered phone id', jobId: 'opaque dng_ id'},
    },
    dungeon_command_status: {
      summary: 'Read one owner-scoped dungeon relay command admission or completion receipt without contacting tmux.',
      write: false,
      requiresRequestId: false,
      requiredScopes: [],
      input: {commandId: 'owner-scoped relay command id'},
    },
  };
}


const DUNGEON_WORK_ROUTE = 'fortress_dungeon_v2';

function campaignIdFromProject(value) {
  const cleaned = String(value || '').toLowerCase().replace(/[^a-z0-9._:-]+/g, '-').replace(/^-+|-+$/g, '');
  return (cleaned.length >= 3 ? cleaned : 'fortress-online').slice(0, 100);
}

function compileDungeonWorkAction({caller, work, args = {}} = {}) {
  if (!caller || !caller.ownerKey) throw Object.assign(new Error('dungeon work requires authenticated owner authority'), {status:401});
  if (!work || work.route !== DUNGEON_WORK_ROUTE) throw Object.assign(new Error(`dungeon work route must be ${DUNGEON_WORK_ROUTE}`), {status:400});
  if (typeof args.requestId !== 'string' || args.requestId.trim().length < 3) {
    throw Object.assign(new Error('fortress_dungeon_v2 requires a stable home_center_work_request requestId'), {status:400});
  }
  const allowedKinds = new Set(['implement','repair','verify','review','research']);
  const taskKind = args.dungeonTaskKind || (allowedKinds.has(work.taskKind) ? work.taskKind : 'implement');
  const requestId = `hcw-${createHash('sha256').update(`${caller.ownerKey}:${args.requestId.trim()}:${work.taskId}:${work.requestHash}`).digest('hex').slice(0, 40)}`;
  return cleanDungeonRun({
    requestId,
    deviceId: 'primary-phone',
    campaignId: campaignIdFromProject(work.projectId),
    workspaceId: args.dungeonWorkspaceId || 'home-center',
    objective: work.requestText,
    acceptance: args.acceptance,
    constraints: args.constraints || [],
    taskKind,
    lane: args.dungeonLane || 'standard',
    ...(args.dungeonCriticalReason ? {criticalReason:args.dungeonCriticalReason} : {}),
    budgetProfile: args.dungeonBudgetProfile || 'standard',
    verificationProfile: args.dungeonVerificationProfile || 'default',
    inferencePolicy: DUNGEON_INFERENCE_POLICY,
    publicationPolicy: DUNGEON_PUBLICATION_POLICY,
  });
}

function advanceDungeonWork(work, state, note, updates = {}, now = Date.now()) {
  const history = Array.isArray(work.stateHistory) ? work.stateHistory.slice(-119) : [];
  history.push({state, atMs:now, note:String(note || '').slice(0, 1000)});
  return {...work, ...updates, state, updatedAtMs:now, stateHistory:history};
}

function boundedDungeonAdmission(admission = {}) {
  const result = admission && typeof admission.result === 'object' && admission.result ? admission.result : {};
  return {
    schema: 'home-center.fortress-dungeon-dispatch.v1',
    route: DUNGEON_WORK_ROUTE,
    commandId: String(admission.commandId || ''),
    relayState: String(admission.state || ''),
    requestHash: String(admission.requestHash || ''),
    attached: Boolean(admission.attached),
    jobId: String(result.jobId || ''),
    dungeonState: String(result.state || ''),
    tmuxSession: String(result.tmuxSession || ''),
    statusRef: String(result.statusRef || ''),
    inferencePolicy: DUNGEON_INFERENCE_POLICY,
    publicationPolicy: DUNGEON_PUBLICATION_POLICY,
    tokenDroughtControl: 'phone-local-fail-closed',
    capabilityMeaning: 'A SUCCEEDED dungeon state means a verified isolated checkpoint only; it does not mean pushed, merged, deployed, installed, delivered, or human-accepted.',
  };
}

async function executeDungeonWorkRequest({admin, caller, args = {}, work, now = Date.now(), runOperation = dungeonRunOperation} = {}) {
  const action = compileDungeonWorkAction({caller, work, args});
  let admission;
  try {
    admission = await runOperation({admin, caller, args:action});
  } catch (error) {
    const message = String(error && error.message || error || 'dungeon admission failed').slice(0, 1000);
    return advanceDungeonWork(work, 'CONTINUE_REQUIRED', `Dungeon admission remains pending: ${message}`, {
      resultSummary: `CONTINUE_REQUIRED: ${message}`,
      result: {
        schema:'home-center.fortress-dungeon-dispatch.v1', route:DUNGEON_WORK_ROUTE,
        dungeonRequestId:action.requestId, relayState:'unavailable', error:message,
        inferencePolicy:DUNGEON_INFERENCE_POLICY, publicationPolicy:DUNGEON_PUBLICATION_POLICY,
        tokenDroughtControl:'phone-local-fail-closed',
      },
    }, now);
  }
  const bounded = boundedDungeonAdmission(admission);
  let state = 'QUEUED';
  if (bounded.relayState === 'leased') state = 'RUNNING';
  if (bounded.relayState === 'completed') {
    if (bounded.dungeonState === 'SUCCEEDED') state = 'SUCCEEDED';
    else if (bounded.dungeonState === 'FAILED' || bounded.dungeonState === 'QUARANTINED') state = 'FAILED';
    else state = 'RUNNING';
  }
  if (bounded.relayState === 'failed' || bounded.relayState === 'expired') state = 'CONTINUE_REQUIRED';
  const refs = Array.from(new Set([...(work.subsystemRefs || []), ...(bounded.commandId ? [`home-center://dungeon-command/${bounded.commandId}`] : []), ...(bounded.statusRef ? [bounded.statusRef] : [])]));
  const note = state === 'SUCCEEDED'
    ? 'Phone-local deterministic verification produced an isolated checkpoint; publication and deployment remain separate.'
    : `Dungeon relay=${bounded.relayState || 'unknown'} local=${bounded.dungeonState || 'not-yet-reported'}.`;
  return advanceDungeonWork(work, state, note, {
    subsystemRefs:refs,
    resultSummary:note,
    result:{...bounded, dungeonRequestId:action.requestId},
  }, now);
}

module.exports = {
  dungeonOperationEntries,
  dungeonRunOperation,
  dungeonStatusOperation,
  dungeonCommandStatusOperation,
  boundedCommand,
  DUNGEON_WORK_ROUTE,
  compileDungeonWorkAction,
  executeDungeonWorkRequest,
  boundedDungeonAdmission,
};
