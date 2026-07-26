const ENVELOPE_VERSION = 'household-evidence-envelope/v1';
const BRIEFING_VERSION = 'household-calendar-briefing/v1';

const FEATURE_FLAGS = Object.freeze({
  liveSmsIngestion: false,
  liveDeviceIngestion: false,
  liveGmailIngestion: false,
  liveCalendarRead: false,
  liveCalendarMutation: false,
  homeAssistantIngestion: false,
  automaticPlayback: false,
});

const SOURCE_TYPES = new Set(['sms', 'gmail', 'calendar', 'spoken_observation', 'home_assistant', 'manual_note', 'mcp_drive', 'fixture']);
const VERIFICATION_STATES = new Set(['unverified', 'needs_review', 'conflicting', 'verified', 'rejected']);
const DISPOSITIONS = new Set(['intake_only', 'needs_decision', 'promoted', 'rejected', 'ignored']);
const CALENDAR_FACT_TYPES = new Set(['calendar_event_candidate', 'appointment', 'deadline', 'pickup', 'visit', 'reminder']);

function isPlainObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function requireString(value, path, {allowEmpty = false} = {}) {
  if (typeof value !== 'string' || (!allowEmpty && value.length === 0)) {
    throw new Error(path + ' must be a non-empty string.');
  }
  return value;
}

function requireBoolean(value, path) {
  if (typeof value !== 'boolean') throw new Error(path + ' must be boolean.');
  return value;
}

function requireConfidence(value, path) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error(path + ' must be a number from 0 to 1.');
  }
  return value;
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function assertNoLiveFlags(flags, path = 'featureFlags') {
  const clean = flags || FEATURE_FLAGS;
  for (const [key, value] of Object.entries(FEATURE_FLAGS)) {
    if (clean[key] !== false) throw new Error(path + '.' + key + ' must default to false for the inert evidence spine.');
    void value;
  }
}

function normalizeEnvelope(input) {
  if (!isPlainObject(input)) throw new Error('envelope must be an object.');
  const envelope = cloneJson(input);
  if (!envelope.version) envelope.version = ENVELOPE_VERSION;
  validateEnvelope(envelope);
  return envelope;
}

function validateEnvelope(envelope) {
  if (!isPlainObject(envelope)) throw new Error('envelope must be an object.');
  if (envelope.version !== ENVELOPE_VERSION) throw new Error('version must be ' + ENVELOPE_VERSION + '.');
  requireString(envelope.envelopeId, 'envelopeId');
  requireString(envelope.capturedAt, 'capturedAt');
  if (Number.isNaN(Date.parse(envelope.capturedAt))) throw new Error('capturedAt must be an ISO timestamp.');

  if (!isPlainObject(envelope.source)) throw new Error('source must be an object.');
  requireString(envelope.source.type, 'source.type');
  if (!SOURCE_TYPES.has(envelope.source.type)) throw new Error('source.type is not supported: ' + envelope.source.type);
  requireString(envelope.source.stableRef, 'source.stableRef');
  requireString(envelope.source.exactText, 'source.exactText', {allowEmpty: true});
  if (typeof envelope.source.observation !== 'undefined') requireString(envelope.source.observation, 'source.observation', {allowEmpty: true});

  if (!isPlainObject(envelope.inferredOwner)) throw new Error('inferredOwner must be an object.');
  requireString(envelope.inferredOwner.ownerRef, 'inferredOwner.ownerRef');
  requireConfidence(envelope.inferredOwner.confidence, 'inferredOwner.confidence');
  if (typeof envelope.inferredOwner.displayName !== 'undefined') requireString(envelope.inferredOwner.displayName, 'inferredOwner.displayName');

  if (!Array.isArray(envelope.extractedFacts)) throw new Error('extractedFacts must be an array.');
  envelope.extractedFacts.forEach((fact, index) => validateFact(fact, 'extractedFacts[' + index + ']'));

  if (!Array.isArray(envelope.possibleDuplicateRefs)) throw new Error('possibleDuplicateRefs must be an array.');
  envelope.possibleDuplicateRefs.forEach((ref, index) => requireString(ref, 'possibleDuplicateRefs[' + index + ']'));

  requireString(envelope.verificationState, 'verificationState');
  if (!VERIFICATION_STATES.has(envelope.verificationState)) throw new Error('verificationState is not supported: ' + envelope.verificationState);
  requireString(envelope.finalDisposition, 'finalDisposition');
  if (!DISPOSITIONS.has(envelope.finalDisposition)) throw new Error('finalDisposition is not supported: ' + envelope.finalDisposition);

  validateConsentScope(envelope.consentScope);
  assertNoLiveFlags(envelope.featureFlags || FEATURE_FLAGS, 'featureFlags');
  return true;
}

function validateFact(fact, path) {
  if (!isPlainObject(fact)) throw new Error(path + ' must be an object.');
  requireString(fact.factId, path + '.factId');
  requireString(fact.type, path + '.type');
  requireString(fact.subject, path + '.subject');
  requireString(fact.predicate, path + '.predicate');
  if (typeof fact.value === 'undefined') throw new Error(path + '.value is required.');
  requireString(fact.rawText, path + '.rawText', {allowEmpty: true});
  requireConfidence(fact.confidence, path + '.confidence');
  requireString(fact.verificationState, path + '.verificationState');
  if (!VERIFICATION_STATES.has(fact.verificationState)) throw new Error(path + '.verificationState is not supported: ' + fact.verificationState);
  if (typeof fact.calendar !== 'undefined' && !isPlainObject(fact.calendar)) throw new Error(path + '.calendar must be an object when present.');
  if (fact.calendar) {
    if (typeof fact.calendar.startText !== 'undefined') requireString(fact.calendar.startText, path + '.calendar.startText');
    if (typeof fact.calendar.endText !== 'undefined') requireString(fact.calendar.endText, path + '.calendar.endText');
    if (typeof fact.calendar.title !== 'undefined') requireString(fact.calendar.title, path + '.calendar.title');
  }
  if (typeof fact.scope !== 'undefined') requireString(fact.scope, path + '.scope');
  return true;
}

function validateConsentScope(scope) {
  if (!isPlainObject(scope)) throw new Error('consentScope must be an object.');
  requireString(scope.scopeId, 'consentScope.scopeId');
  requireString(scope.householdRef, 'consentScope.householdRef');
  requireString(scope.capturedBy, 'consentScope.capturedBy');
  requireString(scope.vetoOwner, 'consentScope.vetoOwner');
  if (!Array.isArray(scope.allowedUses)) throw new Error('consentScope.allowedUses must be an array.');
  scope.allowedUses.forEach((use, index) => requireString(use, 'consentScope.allowedUses[' + index + ']'));
  requireBoolean(scope.liveIngestionAllowed, 'consentScope.liveIngestionAllowed');
  requireBoolean(scope.calendarMutationAllowed, 'consentScope.calendarMutationAllowed');
  requireBoolean(scope.automaticPlaybackAllowed, 'consentScope.automaticPlaybackAllowed');
  if (scope.liveIngestionAllowed || scope.calendarMutationAllowed || scope.automaticPlaybackAllowed) {
    throw new Error('consentScope must keep live ingestion, calendar mutation, and automatic playback disabled.');
  }
  return true;
}

function serializeEnvelope(envelope) {
  const normalized = normalizeEnvelope(envelope);
  return JSON.stringify(normalized, null, 2) + '\n';
}

function deserializeEnvelope(text) {
  return normalizeEnvelope(JSON.parse(text));
}

function factCalendarIdentityKey(fact) {
  const cal = fact.calendar || {};
  const value = isPlainObject(fact.value) ? fact.value.label : fact.value;
  return [fact.subject, fact.type, String(cal.title || value || '')].join('|').toLowerCase();
}

function factCalendarAssertionKey(fact) {
  const cal = fact.calendar || {};
  return [factCalendarIdentityKey(fact), String(cal.startText || ''), JSON.stringify(fact.value)].join('|').toLowerCase();
}

function buildConflictMap(envelopes) {
  const factsByKey = new Map();
  for (const envelope of envelopes) {
    for (const fact of envelope.extractedFacts) {
      if (!CALENDAR_FACT_TYPES.has(fact.type)) continue;
      const key = factCalendarIdentityKey(fact);
      if (!factsByKey.has(key)) factsByKey.set(key, []);
      factsByKey.get(key).push({envelope, fact});
    }
  }
  const conflicts = new Map();
  for (const [key, items] of factsByKey.entries()) {
    const assertions = new Set(items.map(({fact}) => factCalendarAssertionKey(fact)));
    if (assertions.size > 1) {
      conflicts.set(key, items);
    }
  }
  return conflicts;
}

function canAssertCalendarFact(envelope, fact, conflictMap, options) {
  if (!CALENDAR_FACT_TYPES.has(fact.type)) return false;
  if (envelope.verificationState !== 'verified') return false;
  if (envelope.finalDisposition !== 'promoted') return false;
  if (fact.verificationState !== 'verified') return false;
  if (fact.confidence < options.minAssertedConfidence) return false;
  if (envelope.inferredOwner.confidence < options.minAssertedConfidence) return false;
  if (conflictMap.has(factCalendarIdentityKey(fact))) return false;
  return true;
}

function compileCalendarBriefing(envelopesInput, optionsInput = {}) {
  const options = {
    minAssertedConfidence: typeof optionsInput.minAssertedConfidence === 'number' ? optionsInput.minAssertedConfidence : 0.85,
    now: optionsInput.now || new Date().toISOString(),
  };
  assertNoLiveFlags(optionsInput.featureFlags || FEATURE_FLAGS, 'featureFlags');
  const envelopes = envelopesInput.map(normalizeEnvelope);
  const conflictMap = buildConflictMap(envelopes);
  const assertedFacts = [];
  const unresolved = [];
  const sourceRefs = [];

  for (const envelope of envelopes) {
    sourceRefs.push({envelopeId: envelope.envelopeId, sourceType: envelope.source.type, stableRef: envelope.source.stableRef});
    for (const fact of envelope.extractedFacts) {
      const conflictItems = conflictMap.get(factCalendarIdentityKey(fact)) || [];
      const reasons = [];
      if (!CALENDAR_FACT_TYPES.has(fact.type)) reasons.push('not a calendar fact');
      if (envelope.verificationState !== 'verified') reasons.push('envelope is ' + envelope.verificationState);
      if (envelope.finalDisposition !== 'promoted') reasons.push('disposition is ' + envelope.finalDisposition);
      if (fact.verificationState !== 'verified') reasons.push('fact is ' + fact.verificationState);
      if (fact.confidence < options.minAssertedConfidence) reasons.push('fact confidence ' + fact.confidence + ' is below ' + options.minAssertedConfidence);
      if (envelope.inferredOwner.confidence < options.minAssertedConfidence) reasons.push('owner confidence ' + envelope.inferredOwner.confidence + ' is below ' + options.minAssertedConfidence);
      if (conflictItems.length) reasons.push('conflicts with ' + conflictItems.map(({envelope: other}) => other.envelopeId).join(', '));

      const item = {
        envelopeId: envelope.envelopeId,
        factId: fact.factId,
        sourceRef: envelope.source.stableRef,
        ownerRef: envelope.inferredOwner.ownerRef,
        type: fact.type,
        value: cloneJson(fact.value),
        calendar: cloneJson(fact.calendar || {}),
        confidence: fact.confidence,
        rawText: fact.rawText,
      };
      if (canAssertCalendarFact(envelope, fact, conflictMap, options)) assertedFacts.push(item);
      else unresolved.push({...item, reasons});
    }
  }

  const structured = {
    version: BRIEFING_VERSION,
    generatedAt: options.now,
    featureFlags: {...FEATURE_FLAGS},
    calendarMutationAttempted: false,
    automaticPlaybackAttempted: false,
    liveIngestionAttempted: false,
    assertedCalendarFacts: assertedFacts,
    unresolvedFacts: unresolved,
    conflicts: [...conflictMap.entries()].map(([key, items]) => ({
      key,
      envelopeIds: items.map(({envelope}) => envelope.envelopeId),
      factIds: items.map(({fact}) => fact.factId),
    })),
    sourceRefs,
  };
  return {plainText: renderPlainTextBriefing(structured), json: structured};
}

function renderPlainTextBriefing(briefing) {
  const lines = [];
  lines.push('Household calendar briefing.');
  lines.push('No live ingestion ran. No calendar event was created or modified. No automatic playback ran.');
  lines.push('');
  if (briefing.assertedCalendarFacts.length === 0) {
    lines.push('Confirmed calendar facts: none.');
  } else {
    lines.push('Confirmed calendar facts for human review:');
    briefing.assertedCalendarFacts.forEach((fact, index) => {
      const title = fact.calendar.title || String(fact.value);
      const time = fact.calendar.startText ? ' at ' + fact.calendar.startText : '';
      lines.push((index + 1) + '. ' + title + time + '. Source ' + fact.sourceRef + '.');
    });
  }
  lines.push('');
  if (briefing.unresolvedFacts.length === 0) {
    lines.push('Unresolved or uncertain items: none.');
  } else {
    lines.push('Unresolved or uncertain items:');
    briefing.unresolvedFacts.forEach((fact, index) => {
      const title = fact.calendar.title || String(fact.value);
      const reason = fact.reasons.length ? fact.reasons.join('; ') : 'requires review';
      lines.push((index + 1) + '. ' + title + '. Source ' + fact.sourceRef + '. Reason: ' + reason + '. Evidence: ' + fact.rawText);
    });
  }
  lines.push('');
  if (briefing.conflicts.length === 0) {
    lines.push('Conflicts: none detected.');
  } else {
    lines.push('Conflicts:');
    briefing.conflicts.forEach((conflict, index) => {
      lines.push((index + 1) + '. Envelopes ' + conflict.envelopeIds.join(', ') + ' disagree and need human review.');
    });
  }
  lines.push('');
  lines.push('June veto remains active. Treat this briefing as intake evidence, not calendar canon.');
  return lines.join('\n');
}

function decisionLedger() {
  return [
    'Who may create HouseholdEvidenceEnvelope records for House Oakheart.',
    'Which source types June permits: SMS, Gmail, Calendar read, Google Home or Home Assistant, manual notes, or spoken observations.',
    'Which household members or groups each source may mention.',
    'Minimum confidence and verification requirements before a fact can leave intake-only status.',
    'How duplicate and conflict review should be presented to June.',
    'Whether calendar writes are ever allowed, and what explicit confirmation gesture is required.',
    'Whether spoken output is pull-only or may ever play automatically.',
    'Where the obvious off switch lives in the Android app and MCP feature flags.',
    'Retention limits for exact source evidence and redaction rules for private messages.',
  ];
}

module.exports = {
  ENVELOPE_VERSION,
  BRIEFING_VERSION,
  FEATURE_FLAGS,
  normalizeEnvelope,
  validateEnvelope,
  serializeEnvelope,
  deserializeEnvelope,
  compileCalendarBriefing,
  decisionLedger,
};
