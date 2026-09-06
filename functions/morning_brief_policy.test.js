'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  MORNING_POLICY_VERSION,
  morningBriefDecision,
  classifyMorningConfirmation,
  morningFollowUpDecision,
  followUpDueUtc,
} = require('./morning_brief_policy');

function atLocal(hour, minute = 0) {
  // September 6, 2026 is CDT (UTC-05:00).
  return `2026-09-06T${String(hour + 5).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00.000Z`;
}

test('first ordinary morning turn is relevant exactly once per local date', () => {
  const first = morningBriefDecision({utcIso: atLocal(7), messageText: 'What is Organ doing?'});
  assert.equal(first.version, MORNING_POLICY_VERSION);
  assert.equal(first.localDate, '2026-09-06');
  assert.equal(first.relevant, true);
  assert.equal(first.reason, 'first_relevant_morning_turn');
  assert.deepEqual(first.requiredSections, [
    'prescribed_inhaler_and_morning_pills_reminder',
    'live_weather_today',
    'deterministic_need_to_know',
    'requested_work',
  ]);

  const repeat = morningBriefDecision({
    utcIso: atLocal(8),
    messageText: 'another request',
    briefedLocalDate: '2026-09-06',
  });
  assert.equal(repeat.relevant, false);
  assert.equal(repeat.reason, 'already_briefed_today');
});

test('good morning extends deterministic relevance through 14:59 but not 15:00', () => {
  const lateMorning = morningBriefDecision({utcIso: atLocal(14, 59), messageText: 'Good morning. Driver advance.'});
  assert.equal(lateMorning.relevant, true);
  assert.equal(lateMorning.goodMorningOverride, true);
  assert.equal(lateMorning.reason, 'explicit_good_morning');

  const tooLate = morningBriefDecision({utcIso: atLocal(15), messageText: 'good morning'});
  assert.equal(tooLate.relevant, false);
  assert.equal(tooLate.reason, 'outside_morning_window');
});

test('outside the window is a no-op even when not previously briefed', () => {
  const evening = morningBriefDecision({utcIso: atLocal(18), messageText: 'hello'});
  assert.equal(evening.relevant, false);
  assert.deepEqual(evening.requiredSections, []);
});

test('confirmation classifier accepts terse pending acknowledgements but not unrelated prose', () => {
  assert.deepEqual(classifyMorningConfirmation({messageText: 'done', pending: true}), {status: 'confirmed', confirmed: true});
  assert.deepEqual(classifyMorningConfirmation({messageText: 'I took my pills and used the inhaler', pending: true}), {status: 'confirmed', confirmed: true});
  assert.deepEqual(classifyMorningConfirmation({messageText: 'not yet', pending: true}), {status: 'explicit_not_confirmed', confirmed: false});
  assert.deepEqual(classifyMorningConfirmation({messageText: 'the code is done compiling', pending: true}), {status: 'no_confirmation', confirmed: false});
  assert.deepEqual(classifyMorningConfirmation({messageText: 'done', pending: false}), {status: 'not_applicable', confirmed: false});
});

test('follow-up fires once only after due time while confirmation remains absent', () => {
  const briefedAt = atLocal(7);
  const due = followUpDueUtc(briefedAt, 30);
  assert.equal(due, atLocal(7, 30));

  const early = morningFollowUpDecision({
    utcIso: atLocal(7, 29),
    briefedLocalDate: '2026-09-06',
    followUpDueUtc: due,
  });
  assert.equal(early.shouldFollowUp, false);
  assert.equal(early.reason, 'not_due');

  const dueNow = morningFollowUpDecision({
    utcIso: atLocal(7, 30),
    briefedLocalDate: '2026-09-06',
    followUpDueUtc: due,
  });
  assert.equal(dueNow.shouldFollowUp, true);
  assert.equal(dueNow.reason, 'pending_confirmation_due');

  const confirmed = morningFollowUpDecision({
    utcIso: atLocal(8),
    briefedLocalDate: '2026-09-06',
    confirmedLocalDate: '2026-09-06',
    followUpDueUtc: due,
  });
  assert.equal(confirmed.shouldFollowUp, false);
  assert.equal(confirmed.reason, 'already_confirmed');

  const alreadySent = morningFollowUpDecision({
    utcIso: atLocal(8),
    briefedLocalDate: '2026-09-06',
    followUpSentLocalDate: '2026-09-06',
    followUpDueUtc: due,
  });
  assert.equal(alreadySent.shouldFollowUp, false);
  assert.equal(alreadySent.reason, 'followup_already_sent');
});

test('local-date calculation survives DST offset changes', () => {
  // January is CST (UTC-06:00), not the September CDT offset used above.
  const winter = morningBriefDecision({utcIso: '2026-01-10T12:00:00.000Z', messageText: 'hello'});
  assert.equal(winter.localDate, '2026-01-10');
  assert.equal(winter.localHour, 6);
  assert.equal(winter.relevant, true);
});
