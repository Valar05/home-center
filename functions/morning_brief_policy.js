'use strict';

const MORNING_POLICY_VERSION = 'dru.morning-clock.v1';
const DEFAULT_TIME_ZONE = 'America/Chicago';
const NORMAL_MORNING_START_HOUR = 4;
const NORMAL_MORNING_END_HOUR = 12;
const GOOD_MORNING_OVERRIDE_START_HOUR = 3;
const GOOD_MORNING_OVERRIDE_END_HOUR = 15;
const FOLLOW_UP_DELAY_MINUTES = 30;

function safeText(value, max = 2000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function parseUtc(value) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new Error('utcIso must be a valid timestamp.');
  return date;
}

function localClockParts(utcIso, timeZone = DEFAULT_TIME_ZONE) {
  const date = parseUtc(utcIso);
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  });
  const values = {};
  for (const part of formatter.formatToParts(date)) {
    if (part.type !== 'literal') values[part.type] = part.value;
  }
  const hour = Number(values.hour);
  const minute = Number(values.minute);
  const second = Number(values.second);
  return {
    timeZone,
    localDate: `${values.year}-${values.month}-${values.day}`,
    localHour: hour,
    localMinute: minute,
    localSecond: second,
    localMinuteOfDay: hour * 60 + minute,
  };
}

function hasGoodMorning(messageText) {
  return /\bgood\s+morning\b/i.test(safeText(messageText, 4000));
}

function morningBriefDecision({
  utcIso,
  timeZone = DEFAULT_TIME_ZONE,
  messageText = '',
  briefedLocalDate = '',
} = {}) {
  const clock = localClockParts(utcIso, timeZone);
  const explicitGoodMorning = hasGoodMorning(messageText);
  const normalMorningWindow = clock.localHour >= NORMAL_MORNING_START_HOUR
    && clock.localHour < NORMAL_MORNING_END_HOUR;
  const goodMorningOverride = explicitGoodMorning
    && clock.localHour >= GOOD_MORNING_OVERRIDE_START_HOUR
    && clock.localHour < GOOD_MORNING_OVERRIDE_END_HOUR;
  const alreadyBriefedToday = safeText(briefedLocalDate, 40) === clock.localDate;
  const relevant = !alreadyBriefedToday && (normalMorningWindow || goodMorningOverride);
  let reason = 'outside_morning_window';
  if (alreadyBriefedToday) reason = 'already_briefed_today';
  else if (goodMorningOverride) reason = 'explicit_good_morning';
  else if (normalMorningWindow) reason = 'first_relevant_morning_turn';
  return {
    version: MORNING_POLICY_VERSION,
    ...clock,
    explicitGoodMorning,
    normalMorningWindow,
    goodMorningOverride,
    alreadyBriefedToday,
    relevant,
    reason,
    requiredSections: relevant ? [
      'prescribed_inhaler_and_morning_pills_reminder',
      'live_weather_today',
      'deterministic_need_to_know',
      'requested_work',
    ] : [],
    needToKnowPolicy: relevant ? [
      'today_calendar_time_bound_items',
      'material_or_severe_weather',
      'explicit_due_today_home_center_obligations',
    ] : [],
    confirmationRequired: relevant,
    followUpDelayMinutes: FOLLOW_UP_DELAY_MINUTES,
  };
}

function classifyMorningConfirmation({messageText = '', pending = false} = {}) {
  if (!pending) return {status: 'not_applicable', confirmed: false};
  const raw = safeText(messageText, 2000);
  const text = raw.toLowerCase().replace(/[.!?]+$/g, '').trim();
  if (!text) return {status: 'no_confirmation', confirmed: false};

  const negative = /\b(not yet|later|haven't|have not|didn't|did not|nope|not taken|not done|skip|skipping)\b/i.test(text)
    || /^(no|nah)$/i.test(text);
  if (negative) return {status: 'explicit_not_confirmed', confirmed: false};

  const exactPositive = new Set([
    'done',
    'taken',
    'yes',
    'yep',
    'yeah',
    'got them',
    'did it',
    'both done',
    'both taken',
  ]);
  if (exactPositive.has(text)) return {status: 'confirmed', confirmed: true};

  const mentionsMedication = /\b(inhaler|pill|pills|med|meds|medicine|medication|medications)\b/i.test(text);
  const saysCompleted = /\b(took|taken|used|done|did it|got them|already took|already used)\b/i.test(text);
  if (mentionsMedication && saysCompleted) return {status: 'confirmed', confirmed: true};

  return {status: 'no_confirmation', confirmed: false};
}

function morningFollowUpDecision({
  utcIso,
  timeZone = DEFAULT_TIME_ZONE,
  briefedLocalDate = '',
  confirmedLocalDate = '',
  followUpSentLocalDate = '',
  followUpDueUtc = '',
} = {}) {
  const clock = localClockParts(utcIso, timeZone);
  const briefedToday = safeText(briefedLocalDate, 40) === clock.localDate;
  const confirmedToday = safeText(confirmedLocalDate, 40) === clock.localDate;
  const followUpSentToday = safeText(followUpSentLocalDate, 40) === clock.localDate;
  const dueMs = followUpDueUtc ? parseUtc(followUpDueUtc).getTime() : Number.POSITIVE_INFINITY;
  const nowMs = parseUtc(utcIso).getTime();
  const due = nowMs >= dueMs;
  const shouldFollowUp = briefedToday && !confirmedToday && !followUpSentToday && due;
  let reason = 'not_due';
  if (!briefedToday) reason = 'no_brief_today';
  else if (confirmedToday) reason = 'already_confirmed';
  else if (followUpSentToday) reason = 'followup_already_sent';
  else if (due) reason = 'pending_confirmation_due';
  return {
    version: MORNING_POLICY_VERSION,
    ...clock,
    briefedToday,
    confirmedToday,
    followUpSentToday,
    due,
    shouldFollowUp,
    reason,
  };
}

function followUpDueUtc(briefedAtUtc, delayMinutes = FOLLOW_UP_DELAY_MINUTES) {
  const briefed = parseUtc(briefedAtUtc);
  const delay = Number(delayMinutes);
  if (!Number.isFinite(delay) || delay < 1 || delay > 1440) throw new Error('delayMinutes must be from 1 to 1440.');
  return new Date(briefed.getTime() + Math.floor(delay * 60000)).toISOString();
}

module.exports = {
  MORNING_POLICY_VERSION,
  DEFAULT_TIME_ZONE,
  FOLLOW_UP_DELAY_MINUTES,
  localClockParts,
  morningBriefDecision,
  classifyMorningConfirmation,
  morningFollowUpDecision,
  followUpDueUtc,
};
