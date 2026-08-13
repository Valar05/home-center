import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  REGISTRY_VERSION,
  auditDocumentId,
  hashObject,
  messageId,
  normalizedProposal,
  providerEventId,
  publicRecord,
  recordOwnedBy,
  registry,
  runOperation,
} = require('../functions/sms_calendar_intake.js');

const USER = {email: 'reviewer@example.com', authKind: 'home_center_mcp_oauth'};
const MESSAGE_ID = `sms_${'a'.repeat(40)}`;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function merge(base, patch) {
  const out = {...(base || {})};
  for (const [key, value] of Object.entries(patch || {})) {
    if (value && typeof value === 'object' && !Array.isArray(value) && out[key] && typeof out[key] === 'object' && !Array.isArray(out[key])) {
      out[key] = merge(out[key], value);
    } else {
      out[key] = clone(value);
    }
  }
  return out;
}

class MemoryStore {
  constructor(records, {authorized = true} = {}) {
    this.records = new Map(records.map((record) => [record.id, clone(record)]));
    this.audits = new Map();
    this.authorized = authorized;
  }

  checkAuthorized() {
    if (!this.authorized) {
      const error = new Error('The connected Google identity is not a Home Center household member.');
      error.status = 403;
      throw error;
    }
  }

  async resolveRecord(id) {
    this.checkAuthorized();
    const record = this.records.get(id);
    if (!record) {
      const error = new Error('not found');
      error.status = 404;
      throw error;
    }
    return {bucketId: 'test-household', id, record: clone(record)};
  }

  async listRecords({status, limit}) {
    this.checkAuthorized();
    return [...this.records.values()]
      .filter((record) => !status || record.status === status)
      .slice(0, limit)
      .map((record) => ({bucketId: 'test-household', id: record.id, record: clone(record)}));
  }

  async updateRecord(resolved, patch) {
    const next = merge(this.records.get(resolved.id), patch);
    this.records.set(resolved.id, next);
    resolved.record = clone(next);
    return resolved.record;
  }

  async getAudit(id) {
    return this.audits.has(id) ? clone(this.audits.get(id)) : null;
  }

  async setAudit(id, value) {
    this.audits.set(id, merge(this.audits.get(id), value));
  }

  async claimCalendarWrite(resolved, claim) {
    const current = this.records.get(resolved.id);
    const existing = current.calendarWrite || {};
    if (existing.state === 'written') return {claimed: false, state: 'written', record: clone(current)};
    if (['calendar_write_ambiguous', 'ambiguous'].includes(existing.state)) {
      return {claimed: false, state: 'calendar_write_ambiguous', record: clone(current)};
    }
    if (existing.state === 'writing') return {claimed: false, state: 'writing', record: clone(current)};
    const next = merge(current, {status: 'approved', calendarWrite: claim, updatedAtMs: claim.startedAtMs});
    this.records.set(resolved.id, next);
    resolved.record = clone(next);
    return {claimed: true, state: 'writing', record: clone(next)};
  }
}

class FakeCalendarProvider {
  constructor({timeoutAfterInsert = false} = {}) {
    this.events = new Map();
    this.insertCount = 0;
    this.timeoutAfterInsert = timeoutAfterInsert;
  }

  async get(_calendarId, eventId) {
    return this.events.has(eventId) ? clone(this.events.get(eventId)) : null;
  }

  async search() {
    return [];
  }

  async insert(_calendarId, requestBody) {
    this.insertCount += 1;
    const event = {
      id: requestBody.id,
      summary: requestBody.summary,
      status: 'confirmed',
      htmlLink: `https://calendar.example/events/${requestBody.id}`,
      start: requestBody.start,
      end: requestBody.end,
    };
    this.events.set(event.id, event);
    if (this.timeoutAfterInsert) {
      this.timeoutAfterInsert = false;
      const error = new Error('provider response timed out after accepting request');
      error.code = 'ETIMEDOUT';
      throw error;
    }
    return clone(event);
  }
}

function clearRecord(id = MESSAGE_ID) {
  return {
    id,
    schemaVersion: 'home-center.sms-calendar-intake.v2',
    messageId: id,
    status: 'proposal_ready',
    sender: 'River Dental',
    senderAddress: '+15015550100',
    body: 'Dentist appointment Tuesday at 2:30 PM, 45 minutes, at River Dental.',
    receivedAtMs: Date.parse('2026-07-26T15:00:00Z'),
    preservedAtMs: Date.parse('2026-07-26T15:00:01Z'),
    classifiedAtMs: Date.parse('2026-07-26T15:00:02Z'),
    updatedAtMs: Date.parse('2026-07-26T15:00:02Z'),
    sourceTransport: 'android_google_messages_notification',
    sourceHash: 'source-hash-v1',
    immutableHash: 'source-hash-v1',
    classification: {
      classification: 'calendar_event',
      confidence: 0.95,
      proposedTitle: 'Dentist appointment',
      proposedStartTime: '2026-07-28T19:30:00.000Z',
      proposedEndTime: '2026-07-28T20:15:00.000Z',
      durationMinutes: 45,
      timezone: 'America/Chicago',
      location: 'River Dental',
      sourceExcerpt: 'Dentist appointment Tuesday at 2:30 PM, 45 minutes, at River Dental.',
      missingFields: [],
      ambiguityFlags: [],
      inferredFields: ['startDate'],
      classifierVersion: '2026-07-26.deterministic-v2',
      classificationHash: 'classification-hash-v1',
      approvalEligible: true,
    },
    proposal: {
      revision: 1,
      sourceMessageId: id,
      sourceHash: 'source-hash-v1',
      classificationHash: 'classification-hash-v1',
      classifierVersion: '2026-07-26.deterministic-v2',
      title: 'Dentist appointment',
      startTime: '2026-07-28T19:30:00.000Z',
      endTime: '2026-07-28T20:15:00.000Z',
      durationMinutes: 45,
      timezone: 'America/Chicago',
      location: 'River Dental',
      notes: 'Diagnostic test proposal',
      sourceExcerpt: 'Dentist appointment Tuesday at 2:30 PM, 45 minutes, at River Dental.',
      missingFields: [],
      ambiguityFlags: [],
      inferredFields: ['startDate'],
      fieldProvenance: {startDate: 'normalized_weekday_relative_to_received_timestamp', endTime: 'explicit_duration'},
      approvalEligible: true,
    },
  };
}

function ambiguousRecord(id = `sms_${'b'.repeat(40)}`) {
  const record = clearRecord(id);
  record.classification.classification = 'calendar_event_ambiguous';
  record.classification.proposedStartTime = null;
  record.classification.proposedEndTime = null;
  record.classification.missingFields = ['time'];
  record.classification.ambiguityFlags = ['ambiguous_time'];
  record.classification.approvalEligible = false;
  record.proposal.startTime = null;
  record.proposal.endTime = null;
  record.proposal.missingFields = ['time'];
  record.proposal.ambiguityFlags = ['ambiguous_time'];
  record.proposal.approvalEligible = false;
  return record;
}

function nonCalendarRecord(id = `sms_${'c'.repeat(40)}`) {
  const record = clearRecord(id);
  record.status = 'classified';
  record.body = 'Want to get lunch tomorrow?';
  record.classification = {
    classification: 'not_calendar',
    confidence: 0,
    sourceExcerpt: 'Want to get lunch tomorrow?',
    missingFields: [],
    ambiguityFlags: [],
    inferredFields: [],
    classifierVersion: '2026-07-26.deterministic-v2',
    classificationHash: 'classification-non-calendar',
    approvalEligible: false,
  };
  delete record.proposal;
  return record;
}

async function operation(store, name, args, provider = null, user = USER) {
  return runOperation({
    user,
    store,
    provider,
    clock: () => Date.parse('2026-07-26T16:00:00Z'),
    args: {operation: name, args},
  });
}

async function rejectsStatus(promise, status, pattern) {
  await assert.rejects(promise, (error) => {
    assert.equal(error.status, status);
    if (pattern) assert.match(error.message, pattern);
    return true;
  });
}

const operations = registry().operations;
assert.equal(REGISTRY_VERSION, '2026-07-26.sms-calendar-proposal-v2');
for (const name of [
  'sms_calendar.inbox',
  'sms_calendar.get',
  'sms_calendar.reconcile',
  'sms_calendar.approve',
  'sms_calendar.reject',
  'sms_calendar.update_proposal',
  'sms_calendar.create_event',
  'sms_calendar.reconcile_write',
]) assert.ok(operations[name], `${name} must be discoverable`);
assert.equal(operations['sms_calendar.approve'].requiresExplicitConfirmation, true);
assert.deepEqual(operations['sms_calendar.reconcile'].requiredScopes, [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/calendar.events',
]);
assert.throws(() => messageId('eve'), /Home Center SMS intake id/);
assert.equal(recordOwnedBy({createdByEmail: 'Reviewer@Example.com'}, USER), true);
assert.equal(recordOwnedBy({createdByEmail: 'other@example.com'}, USER), false);
assert.equal(recordOwnedBy({}, USER), false);
assert.equal(messageId(MESSAGE_ID), MESSAGE_ID);
assert.notEqual(
  auditDocumentId('sms_calendar.approve', 'house', MESSAGE_ID, 'same-request'),
  auditDocumentId('sms_calendar.reject', 'house', MESSAGE_ID, 'same-request'),
  'request IDs must be namespaced by operation and intake record',
);

// 3. A non-calendar SMS has no approvable proposal.
{
  const store = new MemoryStore([nonCalendarRecord()]);
  await rejectsStatus(operation(store, 'sms_calendar.approve', {
    messageId: `sms_${'c'.repeat(40)}`,
    proposalRevision: 1,
    requestId: 'approve-non-calendar',
  }), 409, /structured proposal/);
}

// 4. The structured clear proposal is bounded and carries the expected fields.
{
  const record = clearRecord();
  const proposal = normalizedProposal(record);
  assert.equal(proposal.title, 'Dentist appointment');
  assert.equal(proposal.startTime, '2026-07-28T19:30:00.000Z');
  assert.equal(proposal.endTime, '2026-07-28T20:15:00.000Z');
  assert.equal(proposal.timezone, 'America/Chicago');
  assert.equal(proposal.durationMinutes, 45);
  assert.ok(proposal.proposalHash);
}

// 6. An ambiguous date/time remains blocked for approval.
{
  const record = ambiguousRecord();
  const store = new MemoryStore([record]);
  await rejectsStatus(operation(store, 'sms_calendar.approve', {
    messageId: record.id,
    proposalRevision: 1,
    requestId: 'approve-ambiguous',
  }), 409, /blocked/);
}

// 8. An unapproved proposal cannot write to Calendar.
{
  const store = new MemoryStore([clearRecord()]);
  await rejectsStatus(operation(store, 'sms_calendar.create_event', {
    messageId: MESSAGE_ID,
    requestId: 'calendar-before-approval',
  }, new FakeCalendarProvider()), 409, /durable approved proposal/);
}

// 9. Approval binds to the exact proposal revision.
{
  const store = new MemoryStore([clearRecord()]);
  await rejectsStatus(operation(store, 'sms_calendar.approve', {
    messageId: MESSAGE_ID,
    proposalRevision: 2,
    requestId: 'approve-wrong-revision',
  }), 409, /revision conflict/);
  const approved = await operation(store, 'sms_calendar.approve', {
    messageId: MESSAGE_ID,
    proposalRevision: 1,
    requestId: 'approve-v1',
  });
  assert.equal(approved.result.state, 'approved');
  const stored = store.records.get(MESSAGE_ID);
  assert.equal(stored.approval.proposalRevision, 1);
  assert.equal(stored.approval.proposalHash, normalizedProposal(stored).proposalHash);
  assert.equal(stored.approval.sourceHash, stored.sourceHash);
  assert.equal(stored.approval.classificationHash, stored.classification.classificationHash);
}

// 10. Editing an approved proposal creates a new revision and invalidates approval.
{
  const store = new MemoryStore([clearRecord()]);
  await operation(store, 'sms_calendar.approve', {
    messageId: MESSAGE_ID,
    proposalRevision: 1,
    requestId: 'approve-before-edit',
  });
  const edited = await operation(store, 'sms_calendar.update_proposal', {
    messageId: MESSAGE_ID,
    proposalRevision: 1,
    title: 'Dentist appointment - updated',
    requestId: 'edit-approved-v1',
  });
  assert.equal(edited.result.proposal.revision, 2);
  assert.equal(edited.result.approval.state, 'invalidated');
  await rejectsStatus(operation(store, 'sms_calendar.create_event', {
    messageId: MESSAGE_ID,
    requestId: 'calendar-after-invalidated-approval',
  }, new FakeCalendarProvider()), 409, /durable approved proposal/);
}

// 11 and 12. Approved execution creates exactly one event and replay returns it.
{
  const store = new MemoryStore([clearRecord()]);
  const provider = new FakeCalendarProvider();
  await operation(store, 'sms_calendar.approve', {
    messageId: MESSAGE_ID,
    proposalRevision: 1,
    requestId: 'approve-for-write',
  });
  const first = await operation(store, 'sms_calendar.create_event', {
    messageId: MESSAGE_ID,
    requestId: 'calendar-write-1',
  }, provider);
  assert.equal(first.result.state, 'calendar_written');
  assert.equal(first.result.existing, false);
  assert.equal(provider.insertCount, 1);
  const eventId = first.result.calendarWrite.providerEventId;
  assert.equal(eventId, providerEventId(normalizedProposal(store.records.get(MESSAGE_ID)).proposalHash));
  const replay = await operation(store, 'sms_calendar.create_event', {
    messageId: MESSAGE_ID,
    requestId: 'calendar-write-2',
  }, provider);
  assert.equal(replay.result.state, 'calendar_written');
  assert.equal(replay.result.existing, true);
  assert.equal(replay.result.calendarWrite.providerEventId, eventId);
  assert.equal(provider.insertCount, 1);
}

// 13 and 14. Timeout after provider acceptance quarantines; reconcile reads by stable ID without insert.
{
  const record = clearRecord(`sms_${'d'.repeat(40)}`);
  const store = new MemoryStore([record]);
  const provider = new FakeCalendarProvider({timeoutAfterInsert: true});
  await operation(store, 'sms_calendar.approve', {
    messageId: record.id,
    proposalRevision: 1,
    requestId: 'approve-timeout-case',
  });
  const uncertain = await operation(store, 'sms_calendar.create_event', {
    messageId: record.id,
    requestId: 'calendar-timeout-after-accept',
  }, provider);
  assert.equal(uncertain.result.state, 'calendar_write_ambiguous');
  assert.equal(uncertain.result.blocked, true);
  assert.equal(uncertain.result.calendarWrite.retryAllowed, false);
  assert.equal(provider.insertCount, 1);
  const reconciled = await operation(store, 'sms_calendar.reconcile_write', {
    messageId: record.id,
    requestId: 'calendar-timeout-reconcile',
  }, provider);
  assert.equal(reconciled.result.state, 'calendar_written');
  assert.equal(reconciled.result.reconciled, true);
  assert.equal(provider.insertCount, 1);
}

// Exact-input idempotency rejects a reused request ID with changed immutable operation input.
{
  const record = clearRecord(`sms_${'e'.repeat(40)}`);
  const store = new MemoryStore([record]);
  await operation(store, 'sms_calendar.reject', {
    messageId: record.id,
    proposalRevision: 1,
    reason: 'Not mine',
    requestId: 'reject-idempotency-conflict',
  });
  await assert.rejects(operation(store, 'sms_calendar.reject', {
    messageId: record.id,
    proposalRevision: 1,
    reason: 'Different reason',
    requestId: 'reject-idempotency-conflict',
  }), (error) => {
    assert.equal(error.status, 409);
    assert.equal(error.code, 'REQUEST_ID_CONFLICT');
    return true;
  });
}

// 15. Unauthorized callers cannot list, approve, or create events.
{
  const store = new MemoryStore([clearRecord()], {authorized: false});
  await rejectsStatus(operation(store, 'sms_calendar.inbox', {limit: 1}), 403, /not a Home Center household member/);
  await rejectsStatus(operation(store, 'sms_calendar.approve', {
    messageId: MESSAGE_ID,
    proposalRevision: 1,
    requestId: 'unauthorized-approve',
  }), 403, /not a Home Center household member/);
  await rejectsStatus(operation(store, 'sms_calendar.create_event', {
    messageId: MESSAGE_ID,
    requestId: 'unauthorized-calendar',
  }, new FakeCalendarProvider()), 403, /not a Home Center household member/);
}

// 16. Status remains bounded and redacts raw SMS content, phone number, internals, and provider payloads.
{
  const record = clearRecord();
  record.body = `private-prefix ${'sensitive '.repeat(3000)}private-tail`;
  record.senderAddress = '+15015550100';
  record.bucketId = 'internal-firestore-bucket';
  record.providerRaw = {access_token: 'secret-provider-token'};
  const status = publicRecord(record);
  const encoded = JSON.stringify(status);
  assert.ok(encoded.length < 8000, `status payload must be bounded, got ${encoded.length}`);
  assert.ok(!Object.prototype.hasOwnProperty.call(status, 'body'));
  assert.ok(!encoded.includes('+15015550100'));
  assert.ok(!encoded.includes('private-tail'));
  assert.ok(!encoded.includes('internal-firestore-bucket'));
  assert.ok(!encoded.includes('secret-provider-token'));
  assert.equal(status.sender, 'phone_ending_0100');
}

console.log(JSON.stringify({
  ok: true,
  registryVersion: REGISTRY_VERSION,
  contractCases: 16,
  providerDouble: true,
  auditHashExample: hashObject({messageId: MESSAGE_ID, revision: 1}).slice(0, 12),
}, null, 2));
