'use strict';

const assert = require('node:assert/strict');
const {
  DUNGEON_INFERENCE_POLICY,
  cleanDungeonRun,
  cleanDungeonStatus,
  dungeonRequestHash,
  dungeonPriority,
  validateDungeonDeviceReceipt,
} = require('./dungeon_run_contract');

const request = {
  requestId: 'fortress-android67-0001',
  campaignId: 'fortress-online',
  workspaceId: 'home-center',
  objective: 'Implement and verify the typed Coding Dungeon ingress.',
  acceptance: ['Unknown fields fail closed.', 'The job owns an isolated tmux session.'],
  constraints: ['No raw shell or caller-supplied path.'],
  lane: 'critical',
  criticalReason: 'Restore the missing first-class Fortress execution aperture.',
};
const action = cleanDungeonRun(request);
assert.equal(action.schema, 'home-center.dungeon-run.v2');
assert.equal(action.inferencePolicy, DUNGEON_INFERENCE_POLICY);
assert.equal(action.publicationPolicy, 'checkpoint-only');
assert.equal(action.deviceId, 'primary-phone');
assert.equal(dungeonPriority(action), 0);
assert.equal(dungeonRequestHash(action), dungeonRequestHash({...action}));

for (const [field, value] of [
  ['manifest', '/tmp/attack.json'],
  ['path', '/data/data/com.termux/files/home'],
  ['command', 'rm -rf anything'],
  ['argv', ['bash', '-lc', 'evil']],
  ['url', 'https://example.invalid'],
  ['env', {TOKEN: 'secret'}],
  ['model', 'caller-selected'],
]) {
  assert.throws(() => cleanDungeonRun({...request, [field]: value}), /rejects unknown field/);
}
assert.throws(() => cleanDungeonRun({...request, lane: 'standard'}), /criticalReason is only allowed/);
assert.throws(() => cleanDungeonRun({...request, criticalReason: undefined}), /critical lane requires/);
assert.throws(() => cleanDungeonRun({...request, inferencePolicy: 'maximum-cloud'}), /inferencePolicy must/);
assert.throws(() => cleanDungeonRun({...request, publicationPolicy: 'push-main'}), /publicationPolicy must/);
assert.throws(() => cleanDungeonRun({...request, acceptance: []}), /must not be empty/);
assert.throws(() => cleanDungeonRun({...request, objective: 'Valid prefix\u0000invalid control'}), /control characters/);

const unicodeFixture = cleanDungeonRun({
  requestId:'fortress-unicode-fixture-0001', campaignId:'fortress-online', workspaceId:'home-center',
  objective:'Map Ω "star" \\ path\nwithout shell.', acceptance:['Preserve 🌟 exactly.'],
  constraints:['Keep tabs\tinside evidence.'], taskKind:'verify', lane:'standard',
  budgetProfile:'probe', verificationProfile:'fast',
});
assert.equal(dungeonRequestHash(unicodeFixture), '5a380184616f6e0abc66e8b6d358d5b4d0f3b5fab9231ba04bb97830c2e3651d');

const hash = dungeonRequestHash(action);
assert.doesNotThrow(() => validateDungeonDeviceReceipt(action, {
  schema: 'home-center.dungeon-submit-receipt.v2',
  requestId: action.requestId,
  inputHash: hash,
  jobId: 'dng_0123456789abcdef01234567',
  tmuxSession: 'hc-dng-0123456789abcdef01234567',
  state: 'ACCEPTED',
  attached: false,
  statusRef: 'phone-state://coding-dungeon-v2/jobs/dng_0123456789abcdef01234567',
}));
assert.throws(() => validateDungeonDeviceReceipt(action, {
  schema: 'home-center.dungeon-submit-receipt.v2', requestId: action.requestId,
  inputHash: '0'.repeat(64), jobId: 'dng_0123456789abcdef01234567',
  tmuxSession: 'hc-dng-0123456789abcdef01234567', state: 'ACCEPTED', attached: false,
  statusRef: 'phone-state://coding-dungeon-v2/jobs/dng_0123456789abcdef01234567',
}), /identity is invalid/);
assert.throws(() => validateDungeonDeviceReceipt(action, {
  schema: 'home-center.dungeon-submit-receipt.v2', requestId: action.requestId,
  inputHash: hash, jobId: 'dng_0123456789abcdef01234567',
  tmuxSession: 'hc-dng-0123456789abcdef01234567', state: 'ACCEPTED', attached: false,
  statusRef: 'phone-state://coding-dungeon-v2/jobs/dng_0123456789abcdef01234567',
  phonePath: '/data/data/com.termux/files/home/private',
}), /rejects unknown field/);

const status = cleanDungeonStatus({requestId: 'fortress-status-0001', jobId: 'dng_0123456789abcdef01234567'});
assert.equal(status.action, 'dungeon_status');
assert.equal(dungeonPriority(status), -1);
assert.throws(() => cleanDungeonStatus({...status, path: '/tmp/no'}), /rejects unknown field/);
const statusReceipt = validateDungeonDeviceReceipt(status, {
  schema:'home-center.dungeon-status-receipt.v2', requestId:status.requestId,
  jobId:status.jobId, inputHash:'a'.repeat(64), state:'SUCCEEDED',
  statusRef:`phone-state://coding-dungeon-v2/jobs/${status.jobId}`,
  job:{
    jobId:status.jobId, campaignId:'fortress-online', workspaceId:'home-center',
    taskKind:'verify', lane:'standard', state:'SUCCEEDED', stage:'checkpoint_only',
    acceptedAtMs:100, updatedAtMs:200, branch:`fortress/fortress-online-${status.jobId.slice(4)}`,
    executor:'codex_exec', executorSummary:'Verified.', executorOutputBytes:1200,
    executorOutputTruncated:false,
    executorLogRef:`phone-state://coding-dungeon-v2/runs/${status.jobId}/codex.jsonl`,
    reason:'verified checkpoint ready', verificationOk:true,
  },
});
assert.equal(statusReceipt.job.executorSummary, 'Verified.');
assert.throws(() => validateDungeonDeviceReceipt(status, {
  ...statusReceipt, job:{...statusReceipt.job, arbitraryPhoneData:'must not cross'},
}), /rejects unknown field/);

console.log('Dungeon ingress contract: PASS');
