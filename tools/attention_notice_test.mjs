import assert from 'node:assert/strict';
import {compileAttentionNotice} from './attention_notice.mjs';

const gmailWaiting = {
  id: 'gmail:return-to-work',
  state: 'waiting',
  action: 'Open Gmail and check',
  fact: 'No notification does not mean no reply',
  severity: 'critical',
  pulse: 0,
};

const first = compileAttentionNotice(gmailWaiting);
assert.equal(first, compileAttentionNotice({...gmailWaiting}));
assert.ok(first.startsWith('🚨 DREW. OPEN GMAIL AND CHECK.'));
assert.ok(first.includes('NO NOTIFICATION DOES NOT MEAN NO REPLY.'));
assert.ok(first.length <= 160);

const secondPulse = compileAttentionNotice({...gmailWaiting, pulse: 1});
assert.notEqual(first, secondPulse, 'successive explicit pulses must rotate the sting');
assert.ok(secondPulse.startsWith('🚨 DREW. OPEN GMAIL AND CHECK.'));

const replyFound = compileAttentionNotice({
  id: 'gmail:return-to-work',
  state: 'action_required',
  action: 'Open Gmail',
  fact: 'Benefits replied; return-to-work access needs action',
  pulse: 0,
});
assert.ok(replyFound.indexOf('OPEN GMAIL') < replyFound.indexOf('BENEFITS REPLIED'));

const ciFailure = compileAttentionNotice({
  id: 'github:home-center:main',
  state: 'failed',
  action: 'Open Actions',
  fact: 'Home Center main is red; Android and CI failed',
  pulse: 0,
});
assert.ok(ciFailure.startsWith('🚨 DREW. OPEN ACTIONS. HOME CENTER MAIN IS RED'));

const phoneFailure = compileAttentionNotice({
  id: 'home-center:primary-phone',
  state: 'disconnected',
  action: 'Recover Phone Hands',
  fact: 'Primary phone disconnected',
  severity: 'attention',
  pulse: 2,
});
assert.ok(phoneFailure.startsWith('⚠️ DREW. RECOVER PHONE HANDS. PRIMARY PHONE DISCONNECTED.'));

assert.equal(
  compileAttentionNotice({
    id: 'gmail:return-to-work',
    state: 'resolved',
    action: 'Open Gmail',
    fact: 'Reply handled',
  }),
  null,
  'resolved conditions must not emit another alarm',
);

assert.throws(
  () => compileAttentionNotice({
    id: 'bad:action',
    state: 'due',
    action: 'X'.repeat(45),
    fact: 'Fact',
  }),
  /action exceeds 44 characters/,
);

assert.throws(
  () => compileAttentionNotice({
    id: 'bad:state',
    state: 'mystery',
    action: 'Open thing',
    fact: 'Something happened',
  }),
  /state must be one of/,
);

console.log('attention notice contract: OK');
