#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import fs from 'node:fs';

const require = createRequire(import.meta.url);
const {
  ENVELOPE_VERSION,
  FEATURE_FLAGS,
  validateEnvelope,
  serializeEnvelope,
  deserializeEnvelope,
  compileCalendarBriefing,
  decisionLedger,
} = require('../functions/household_evidence.js');

const fixtures = JSON.parse(fs.readFileSync('tools/fixtures/household_evidence_envelopes.json', 'utf8'));
assert.equal(fixtures.length, 2);
assert.deepEqual(FEATURE_FLAGS, {
  liveSmsIngestion: false,
  liveDeviceIngestion: false,
  liveGmailIngestion: false,
  liveCalendarRead: false,
  liveCalendarMutation: false,
  homeAssistantIngestion: false,
  automaticPlayback: false,
});

for (const envelope of fixtures) {
  assert.equal(envelope.version, ENVELOPE_VERSION);
  assert.equal(validateEnvelope(envelope), true);
  const serialized = serializeEnvelope(envelope);
  const roundTrip = deserializeEnvelope(serialized);
  assert.equal(roundTrip.source.exactText, envelope.source.exactText, 'exact source evidence must survive serialization exactly');
  assert.deepEqual(roundTrip, envelope, 'envelope must survive JSON serialize/deserialize without semantic drift');
}

const ambiguousOnly = compileCalendarBriefing([fixtures[0]], {now: '2026-07-25T12:00:00.000Z'});
assert.equal(ambiguousOnly.json.calendarMutationAttempted, false);
assert.equal(ambiguousOnly.json.liveIngestionAttempted, false);
assert.equal(ambiguousOnly.json.automaticPlaybackAttempted, false);
assert.equal(ambiguousOnly.json.assertedCalendarFacts.length, 0, 'ambiguous fixture must not become an asserted calendar fact');
assert.equal(ambiguousOnly.json.unresolvedFacts.length, 1);
assert.match(ambiguousOnly.plainText, /No live ingestion ran. No calendar event was created or modified. No automatic playback ran./);
assert.match(ambiguousOnly.plainText, /Unresolved or uncertain items:/);
assert.match(ambiguousOnly.plainText, /June veto remains active/);
assert(!/[│┌┐└┘]/.test(ambiguousOnly.plainText), 'briefing must remain plain text, not visual table formatting');

const confirmed = compileCalendarBriefing([fixtures[1]], {now: '2026-07-25T12:05:00.000Z'});
assert.equal(confirmed.json.assertedCalendarFacts.length, 1, 'verified promoted fixture may become a human-review briefing fact');
assert.equal(confirmed.json.calendarMutationAttempted, false, 'compiler must never create or modify a calendar event');
assert.match(confirmed.plainText, /Confirmed calendar facts for human review:/);

const together = compileCalendarBriefing(fixtures, {now: '2026-07-25T12:10:00.000Z'});
assert.equal(together.json.calendarMutationAttempted, false);
assert.equal(together.json.unresolvedFacts.some((fact) => fact.envelopeId === 'fixture-oakheart-001'), true);
assert.equal(together.json.assertedCalendarFacts.some((fact) => fact.envelopeId === 'fixture-oakheart-002'), true);


const conflictA = JSON.parse(JSON.stringify(fixtures[1]));
conflictA.envelopeId = 'fixture-oakheart-conflict-a';
conflictA.source.stableRef = 'fixture://oakheart/calendar-note/conflict-a';
conflictA.source.exactText = 'June says dentist is Thursday at 3:30 PM.';
conflictA.extractedFacts[0].factId = 'fact-conflict-a';
conflictA.extractedFacts[0].calendar.title = 'Dentist appointment';
conflictA.extractedFacts[0].calendar.startText = 'Thursday 3:30 PM';
conflictA.extractedFacts[0].value = {label: 'dentist', time: 'Thursday 3:30 PM'};
conflictA.extractedFacts[0].rawText = conflictA.source.exactText;
const conflictB = JSON.parse(JSON.stringify(fixtures[1]));
conflictB.envelopeId = 'fixture-oakheart-conflict-b';
conflictB.source.stableRef = 'fixture://oakheart/calendar-note/conflict-b';
conflictB.source.exactText = 'Eve says dentist is Thursday at 4 PM.';
conflictB.extractedFacts[0].factId = 'fact-conflict-b';
conflictB.extractedFacts[0].calendar.title = 'Dentist appointment';
conflictB.extractedFacts[0].calendar.startText = 'Thursday 4 PM';
conflictB.extractedFacts[0].value = {label: 'dentist', time: 'Thursday 4 PM'};
conflictB.extractedFacts[0].rawText = conflictB.source.exactText;
const conflicting = compileCalendarBriefing([conflictA, conflictB], {now: '2026-07-25T12:15:00.000Z'});
assert.equal(conflicting.json.assertedCalendarFacts.length, 0, 'conflicting verified facts must not become asserted calendar facts');
assert.equal(conflicting.json.conflicts.length, 1, 'conflicting verified facts must be surfaced explicitly');
assert.match(conflicting.plainText, /Conflicts:/);

const bad = JSON.parse(JSON.stringify(fixtures[0]));
bad.featureFlags.liveSmsIngestion = true;
assert.throws(() => validateEnvelope(bad), /liveSmsIngestion must default to false/);

const badConsent = JSON.parse(JSON.stringify(fixtures[0]));
badConsent.consentScope.calendarMutationAllowed = true;
assert.throws(() => validateEnvelope(badConsent), /calendar mutation/);

assert(decisionLedger().some((item) => /June/.test(item)), 'decision ledger must preserve June veto decisions');
console.log('Household evidence envelope and briefing contract: OK');
