import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  extractAliases,
  messageId,
  registry,
  searchQuery,
  validateProposal,
} = require('../functions/sms_calendar_intake.js');

const operations = registry().operations;
for (const name of [
  'sms_calendar.inbox',
  'sms_calendar.get',
  'sms_calendar.reconcile',
  'sms_calendar.propose',
  'sms_calendar.dismiss',
  'sms_calendar.create_event',
]) {
  assert.ok(operations[name], `${name} must be discoverable`);
}
assert.equal(operations['sms_calendar.create_event'].requiresExplicitConfirmation, true);
assert.deepEqual(operations['sms_calendar.reconcile'].requiredScopes, [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/calendar.events',
]);

const source = {
  sender: '+15015550100',
  body: "Reminder: June's IVX infusion appointment is Tuesday at 9:30 AM.",
  classification: {normalizedAliases: ['ivx', 'infusion']},
};
assert.deepEqual(extractAliases(source), ['ivx', 'infusion', 'appointment']);
assert.equal(searchQuery(source), 'ivx infusion appointment');

const proposal = validateProposal({
  title: "June's infusion",
  startTime: '2026-07-28T09:30:00-05:00',
  endTime: '2026-07-28T11:30:00-05:00',
  confidence: 0.92,
  uncertainties: ['Suite number not present'],
});
assert.equal(proposal.title, "June's infusion");
assert.equal(proposal.startTime, '2026-07-28T14:30:00.000Z');
assert.equal(proposal.endTime, '2026-07-28T16:30:00.000Z');
assert.throws(() => validateProposal({
  title: 'Bad',
  startTime: 'not-a-date',
  endTime: 'also-bad',
  confidence: 1,
}), /valid RFC3339/);
assert.throws(() => messageId('eve'), /Home Center SMS intake id/);
assert.equal(messageId(`sms_${'a'.repeat(40)}`), `sms_${'a'.repeat(40)}`);

console.log('SMS Calendar intake contract: OK');
