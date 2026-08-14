'use strict';

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
  return {
    commandId: record.commandId,
    deviceId: record.deviceId,
    state: record.status,
    requestHash: record.requestHash || '',
    createdAtMs: Number(record.createdAtMs || 0),
    updatedAtMs: Number(record.updatedAtMs || 0),
    expiresAtMs: Number(record.expiresAtMs || 0),
    result: record.result == null ? null : record.result,
    error: String(record.error || '').slice(0, 4000),
  };
}

async function dungeonRunOperation({admin, user, args = {}} = {}) {
  const caller = callerFromHomeCenterUser(user, 'Adam');
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
      input: {schema: DUNGEON_STATUS_SCHEMA, requestId: 'stable status request id', deviceId: 'optional registered phone id', jobId: 'opaque dng_ id'},
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

module.exports = {
  dungeonOperationEntries,
  dungeonRunOperation,
  dungeonStatusOperation,
  dungeonCommandStatusOperation,
  boundedCommand,
};
