'use strict';

const {createHash} = require('node:crypto');

const DUNGEON_RUN_SCHEMA = 'home-center.dungeon-run.v2';
const DUNGEON_STATUS_SCHEMA = 'home-center.dungeon-status.v2';
const DUNGEON_CAPABILITY = 'coding_dungeon_v2';
const DUNGEON_INFERENCE_POLICY = 'codex-local-low-deterministic-v1';
const DUNGEON_PUBLICATION_POLICY = 'checkpoint-only';

const RUN_KEYS = new Set([
  'action', 'schema', 'requestId', 'deviceId', 'campaignId', 'workspaceId',
  'objective', 'acceptance', 'constraints', 'taskKind', 'lane', 'criticalReason',
  'budgetProfile', 'verificationProfile', 'inferencePolicy', 'publicationPolicy',
]);
const STATUS_KEYS = new Set(['action', 'schema', 'requestId', 'deviceId', 'jobId']);
const LANES = new Set(['critical', 'standard', 'background']);
const BUDGETS = new Set(['probe', 'standard', 'long']);
const VERIFICATION_PROFILES = new Set(['fast', 'default', 'full']);
const TASK_KINDS = new Set(['implement', 'repair', 'verify', 'review', 'research']);

function fail(message, status = 400, code = 'DUNGEON_CONTRACT_INVALID') {
  throw Object.assign(new Error(message), {status, code});
}

function object(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('dungeon action must be an object');
  return value;
}

function text(value, key, {min = 1, max = 1200, pattern = null} = {}) {
  if (typeof value !== 'string') fail(`${key} must be a string`);
  const out = value.trim();
  if (out.length < min || out.length > max) fail(`${key} must contain ${min}-${max} characters`);
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(out)) fail(`${key} contains unsupported control characters`);
  if (pattern && !pattern.test(out)) fail(`${key} contains unsupported characters`);
  return out;
}

function id(value, key, max = 120) {
  const out = text(value, key, {min: 3, max, pattern: /^[A-Za-z0-9][A-Za-z0-9._:-]*$/});
  if (out.includes('..')) fail(`${key} may not contain '..'`);
  return out;
}

function stringList(value, key, {required = false, maxItems = 24, maxText = 600} = {}) {
  if (value == null && !required) return [];
  if (!Array.isArray(value)) fail(`${key} must be an array of strings`);
  if (required && value.length === 0) fail(`${key} must not be empty`);
  if (value.length > maxItems) fail(`${key} may contain at most ${maxItems} entries`);
  const seen = new Set();
  return value.map((item, index) => {
    const cleaned = text(item, `${key}[${index}]`, {min: 1, max: maxText});
    if (seen.has(cleaned)) fail(`${key} contains a duplicate entry`);
    seen.add(cleaned);
    return cleaned;
  });
}

function rejectUnknown(body, allowed, action) {
  const unknown = Object.keys(body).filter((key) => !allowed.has(key));
  if (unknown.length) fail(`${action} rejects unknown field: ${unknown[0]}`);
}

function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  fail('dungeon action contains a non-canonical JSON value');
}

function dungeonRequestHash(action) {
  return createHash('sha256').update(canonicalJson(action)).digest('hex');
}

function cleanDungeonRun(value) {
  const body = object(value);
  rejectUnknown(body, RUN_KEYS, 'dungeon_run');
  if ((body.action || 'dungeon_run') !== 'dungeon_run') fail('dungeon_run action identity is invalid');
  if ((body.schema || DUNGEON_RUN_SCHEMA) !== DUNGEON_RUN_SCHEMA) {
    fail(`dungeon_run schema must be ${DUNGEON_RUN_SCHEMA}`);
  }
  const lane = body.lane == null ? 'standard' : text(body.lane, 'lane', {max: 20});
  if (!LANES.has(lane)) fail('lane must be critical, standard, or background');
  const criticalReason = body.criticalReason == null ? '' : text(body.criticalReason, 'criticalReason', {min: 12, max: 800});
  if (lane === 'critical' && !criticalReason) fail('critical lane requires criticalReason');
  if (lane !== 'critical' && criticalReason) fail('criticalReason is only allowed for the critical lane');
  const budgetProfile = body.budgetProfile == null ? 'standard' : text(body.budgetProfile, 'budgetProfile', {max: 20});
  if (!BUDGETS.has(budgetProfile)) fail('budgetProfile must be probe, standard, or long');
  const verificationProfile = body.verificationProfile == null ? 'default' : text(body.verificationProfile, 'verificationProfile', {max: 20});
  if (!VERIFICATION_PROFILES.has(verificationProfile)) fail('verificationProfile must be fast, default, or full');
  const taskKind = body.taskKind == null ? 'implement' : text(body.taskKind, 'taskKind', {max: 20});
  if (!TASK_KINDS.has(taskKind)) fail('taskKind must be implement, repair, verify, review, or research');
  const inferencePolicy = body.inferencePolicy == null ? DUNGEON_INFERENCE_POLICY : text(body.inferencePolicy, 'inferencePolicy', {max: 80});
  if (inferencePolicy !== DUNGEON_INFERENCE_POLICY) fail(`inferencePolicy must be ${DUNGEON_INFERENCE_POLICY}`);
  const publicationPolicy = body.publicationPolicy == null ? DUNGEON_PUBLICATION_POLICY : text(body.publicationPolicy, 'publicationPolicy', {max: 40});
  if (publicationPolicy !== DUNGEON_PUBLICATION_POLICY) fail(`publicationPolicy must be ${DUNGEON_PUBLICATION_POLICY}`);
  return {
    action: 'dungeon_run',
    schema: DUNGEON_RUN_SCHEMA,
    requestId: id(body.requestId, 'requestId', 180),
    deviceId: id(body.deviceId || 'primary-phone', 'deviceId', 120).toLowerCase(),
    campaignId: id(body.campaignId, 'campaignId', 100).toLowerCase(),
    workspaceId: id(body.workspaceId, 'workspaceId', 100).toLowerCase(),
    objective: text(body.objective, 'objective', {min: 8, max: 8000}),
    acceptance: stringList(body.acceptance, 'acceptance', {required: true, maxItems: 24, maxText: 600}),
    constraints: stringList(body.constraints, 'constraints', {maxItems: 24, maxText: 600}),
    taskKind,
    lane,
    ...(criticalReason ? {criticalReason} : {}),
    budgetProfile,
    verificationProfile,
    inferencePolicy,
    publicationPolicy,
  };
}

function cleanDungeonStatus(value) {
  const body = object(value);
  rejectUnknown(body, STATUS_KEYS, 'dungeon_status');
  if ((body.action || 'dungeon_status') !== 'dungeon_status') fail('dungeon_status action identity is invalid');
  if ((body.schema || DUNGEON_STATUS_SCHEMA) !== DUNGEON_STATUS_SCHEMA) {
    fail(`dungeon_status schema must be ${DUNGEON_STATUS_SCHEMA}`);
  }
  return {
    action: 'dungeon_status',
    schema: DUNGEON_STATUS_SCHEMA,
    requestId: id(body.requestId, 'requestId', 180),
    deviceId: id(body.deviceId || 'primary-phone', 'deviceId', 120).toLowerCase(),
    jobId: text(body.jobId, 'jobId', {min: 20, max: 40, pattern: /^dng_[0-9a-f]{24}$/}),
  };
}

function dungeonPriority(action) {
  if (action && action.action === 'dungeon_status') return -1;
  if (!action || action.action !== 'dungeon_run') return 50;
  return action.lane === 'critical' ? 0 : action.lane === 'standard' ? 10 : 20;
}

function dungeonAdmissionTtlMs(action) {
  if (action && action.action === 'dungeon_status') return 5 * 60 * 1000;
  return action && action.budgetProfile === 'long' ? 24 * 60 * 60 * 1000 : 4 * 60 * 60 * 1000;
}

function validateDungeonDeviceReceipt(action, result) {
  const body = object(result);
  const requestHash = dungeonRequestHash(action);
  if (action.action === 'dungeon_run') {
    if (body.schema !== 'home-center.dungeon-submit-receipt.v2') fail('dungeon_run returned an invalid receipt schema');
    if (body.requestId !== action.requestId || body.inputHash !== requestHash) fail('dungeon_run receipt identity is invalid');
    if (!/^dng_[0-9a-f]{24}$/.test(String(body.jobId || ''))) fail('dungeon_run receipt jobId is invalid');
    if (!/^hc-dng-[0-9a-f]{16}$/.test(String(body.tmuxSession || ''))) fail('dungeon_run receipt tmuxSession is invalid');
    if (!['ACCEPTED', 'RUNNING', 'CHECKPOINTED', 'SUCCEEDED', 'FAILED', 'QUARANTINED'].includes(body.state)) fail('dungeon_run receipt state is invalid');
    if (typeof body.attached !== 'boolean') fail('dungeon_run receipt attached must be boolean');
    return body;
  }
  if (body.schema !== 'home-center.dungeon-status-receipt.v2') fail('dungeon_status returned an invalid receipt schema');
  if (body.requestId !== action.requestId || body.jobId !== action.jobId) fail('dungeon_status receipt identity is invalid');
  if (!/^[0-9a-f]{64}$/.test(String(body.inputHash || ''))) fail('dungeon_status receipt inputHash is invalid');
  if (!['ACCEPTED', 'RUNNING', 'CHECKPOINTED', 'SUCCEEDED', 'FAILED', 'QUARANTINED'].includes(body.state)) fail('dungeon_status receipt state is invalid');
  return body;
}

module.exports = {
  DUNGEON_RUN_SCHEMA,
  DUNGEON_STATUS_SCHEMA,
  DUNGEON_CAPABILITY,
  DUNGEON_INFERENCE_POLICY,
  DUNGEON_PUBLICATION_POLICY,
  cleanDungeonRun,
  cleanDungeonStatus,
  dungeonRequestHash,
  dungeonPriority,
  dungeonAdmissionTtlMs,
  validateDungeonDeviceReceipt,
  canonicalJson,
};
