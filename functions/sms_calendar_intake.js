'use strict';

const {createHash} = require('node:crypto');

const REGISTRY_VERSION = '2026-07-26.sms-calendar-proposal-v2';
const CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events';
const GMAIL_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly';
const WRITE_OPERATIONS = new Set([
  'sms_calendar.approve',
  'sms_calendar.reject',
  'sms_calendar.update_proposal',
  'sms_calendar.propose',
  'sms_calendar.dismiss',
  'sms_calendar.create_event',
  'sms_calendar.reconcile_write',
]);
const TERMINAL_AUDIT_STATES = new Set(['success', 'failed', 'quarantined']);

function text(value, max = 12000) {
  const clean = typeof value === 'string' ? value.trim() : '';
  return clean.length > max ? clean.slice(0, max) : clean;
}

function stringArray(value, maxItems = 12, maxLength = 240) {
  return Array.isArray(value) ? value.map((item) => text(item, maxLength)).filter(Boolean).slice(0, maxItems) : [];
}

function normalizeEmail(value) {
  return text(value, 320).toLowerCase();
}

function requestId(value) {
  const clean = text(value, 200);
  if (!clean) throw statusError(400, 'requestId is required.');
  return clean;
}

function statusError(status, message, code = '') {
  return Object.assign(new Error(message), {status, code});
}

function messageId(value) {
  const clean = text(value, 160);
  if (!/^sms_[a-f0-9]{32,64}$/.test(clean)) {
    throw statusError(400, 'messageId must be a Home Center SMS intake id.');
  }
  return clean;
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
  }
  if (value === undefined) return null;
  return value;
}

function hashObject(value) {
  return createHash('sha256').update(JSON.stringify(canonicalize(value))).digest('hex');
}

function auditDocumentId(operation, bucketId, id, rid) {
  return createHash('sha256').update([
    text(operation, 120),
    text(bucketId, 200),
    messageId(id),
    requestId(rid),
  ].join('\n')).digest('hex');
}

function registry() {
  return {
    version: REGISTRY_VERSION,
    invocationTool: 'drive_operation',
    authorityBoundary: 'SMS source evidence and proposals are separate. Calendar mutation requires a durable approval bound to the exact source, classification, and proposal revision.',
    operations: {
      'sms_calendar.inbox': {
        summary: 'List bounded redacted SMS Calendar statuses for connected households.',
        write: false,
        requiredScopes: [],
        input: {status: 'optional state', limit: 'optional integer 1..50'},
      },
      'sms_calendar.get': {
        summary: 'Read one bounded redacted SMS Calendar status and evidence chain.',
        write: false,
        requiredScopes: [],
        input: {messageId: 'string'},
      },
      'sms_calendar.reconcile': {
        summary: 'Search Gmail and Google Calendar for likely matches without mutation.',
        write: false,
        requiredScopes: [GMAIL_SCOPE, CALENDAR_SCOPE],
        input: {messageId: 'string', timeMin: 'optional RFC3339', timeMax: 'optional RFC3339'},
      },
      'sms_calendar.approve': {
        summary: 'Approve the exact current proposal revision for Calendar mutation.',
        write: true,
        requiresRequestId: true,
        requiresExplicitConfirmation: true,
        requiredScopes: [],
        input: {messageId: 'string', proposalRevision: 'integer', requestId: 'string'},
      },
      'sms_calendar.reject': {
        summary: 'Reject the exact current proposal revision without deleting source evidence.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {messageId: 'string', proposalRevision: 'integer', reason: 'string', requestId: 'string'},
      },
      'sms_calendar.update_proposal': {
        summary: 'Create a new proposal revision; any prior approval is invalidated.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {messageId: 'string', proposalRevision: 'integer', title: 'optional string', startTime: 'optional RFC3339', endTime: 'optional RFC3339', timezone: 'optional IANA timezone', location: 'optional string', notes: 'optional string', requestId: 'string'},
      },
      'sms_calendar.propose': {
        summary: 'Compatibility alias for update_proposal. Creates a new review revision and invalidates approval.',
        write: true,
        requiresRequestId: true,
        deprecated: true,
        requiredScopes: [],
        input: {messageId: 'string', proposalRevision: 'integer', title: 'optional string', startTime: 'optional RFC3339', endTime: 'optional RFC3339', timezone: 'optional IANA timezone', location: 'optional string', notes: 'optional string', requestId: 'string'},
      },
      'sms_calendar.dismiss': {
        summary: 'Compatibility alias for reject. Preserves source evidence.',
        write: true,
        requiresRequestId: true,
        deprecated: true,
        requiredScopes: [],
        input: {messageId: 'string', proposalRevision: 'integer', reason: 'string', requestId: 'string'},
      },
      'sms_calendar.create_event': {
        summary: 'Create or return exactly one Calendar event for the durably approved proposal.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [CALENDAR_SCOPE],
        input: {messageId: 'string', requestId: 'string'},
      },
      'sms_calendar.reconcile_write': {
        summary: 'Resolve an uncertain Calendar write by deterministic provider event ID without repeating insert.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [CALENDAR_SCOPE],
        input: {messageId: 'string', requestId: 'string'},
      },
    },
  };
}

function extractAliases(record) {
  const aliases = new Set();
  const classification = record && record.classification || {};
  for (const value of classification.normalizedAliases || []) {
    const clean = text(value, 80);
    if (clean) aliases.add(clean);
  }
  const body = text(record && record.body, 12000).toLowerCase();
  const known = [
    ['vts', /\bvts\b/i],
    ['ivx', /\bivx\b/i],
    ['infusion', /\binfusion\b/i],
    ['appointment', /\b(?:appointment|appt)\b/i],
    ['dentist', /\b(?:dentist|dental)\b/i],
  ];
  for (const [alias, pattern] of known) if (pattern.test(body)) aliases.add(alias);
  return [...aliases].slice(0, 8);
}

function searchQuery(record) {
  const parts = extractAliases(record);
  const sender = text(record && record.sender, 160);
  if (sender && !/^\+?[\d\s().-]+$/.test(sender)) parts.push(sender);
  return [...new Set(parts)].slice(0, 6).join(' ');
}

function proposalRevision(value) {
  const revision = Number(value);
  if (!Number.isInteger(revision) || revision < 1) {
    throw statusError(400, 'proposalRevision must be a positive integer.');
  }
  return revision;
}

function parseRfc3339(value, field, required = false) {
  const clean = text(value, 80);
  if (!clean && !required) return '';
  const parsed = Date.parse(clean);
  if (!clean || !Number.isFinite(parsed)) throw statusError(400, `${field} must be a valid RFC3339 timestamp.`);
  return new Date(parsed).toISOString();
}

function normalizedProposal(record) {
  const proposal = record && record.proposal;
  if (!proposal || typeof proposal !== 'object') return null;
  const revision = Number(proposal.revision || 1);
  const normalized = {
    revision: Number.isInteger(revision) && revision > 0 ? revision : 1,
    sourceMessageId: text(proposal.sourceMessageId || record.id, 160),
    sourceHash: text(proposal.sourceHash || record.sourceHash, 128),
    classificationHash: text(proposal.classificationHash || record.classification && record.classification.classificationHash, 128),
    classifierVersion: text(proposal.classifierVersion || record.classification && record.classification.classifierVersion, 120),
    title: text(proposal.title, 240),
    startTime: parseRfc3339(proposal.startTime, 'proposal.startTime'),
    endTime: parseRfc3339(proposal.endTime, 'proposal.endTime'),
    durationMinutes: Math.max(0, Math.min(10080, Number(proposal.durationMinutes || 0))),
    timezone: text(proposal.timezone || record.classification && record.classification.timezone, 120),
    location: text(proposal.location, 500),
    notes: text(proposal.notes || proposal.preparation, 2000),
    sourceExcerpt: text(proposal.sourceExcerpt || record.classification && record.classification.sourceExcerpt || record.body, 240),
    missingFields: stringArray(proposal.missingFields),
    ambiguityFlags: stringArray(proposal.ambiguityFlags || proposal.uncertainties),
    inferredFields: stringArray(proposal.inferredFields),
    fieldProvenance: proposal.fieldProvenance && typeof proposal.fieldProvenance === 'object' ? canonicalize(proposal.fieldProvenance) : {},
    approvalEligible: proposal.approvalEligible !== false,
  };
  normalized.proposalHash = text(proposal.proposalHash, 128) || proposalHash(normalized);
  return normalized;
}

function proposalHash(proposal) {
  return hashObject({
    revision: Number(proposal.revision || 0),
    sourceMessageId: text(proposal.sourceMessageId, 160),
    sourceHash: text(proposal.sourceHash, 128),
    classificationHash: text(proposal.classificationHash, 128),
    classifierVersion: text(proposal.classifierVersion, 120),
    title: text(proposal.title, 240),
    startTime: text(proposal.startTime, 80),
    endTime: text(proposal.endTime, 80),
    durationMinutes: Number(proposal.durationMinutes || 0),
    timezone: text(proposal.timezone, 120),
    location: text(proposal.location, 500),
    notes: text(proposal.notes, 2000),
    missingFields: stringArray(proposal.missingFields),
    ambiguityFlags: stringArray(proposal.ambiguityFlags),
    inferredFields: stringArray(proposal.inferredFields),
    fieldProvenance: proposal.fieldProvenance || {},
  });
}

function proposalBlockers(proposal) {
  if (!proposal) return ['proposal_missing'];
  const blockers = new Set([...stringArray(proposal.missingFields), ...stringArray(proposal.ambiguityFlags)]);
  if (!text(proposal.title, 240)) blockers.add('title_missing');
  if (!text(proposal.startTime, 80)) blockers.add('start_time_missing');
  if (!text(proposal.endTime, 80)) blockers.add('end_time_missing');
  if (!text(proposal.timezone, 120)) blockers.add('timezone_missing');
  if (proposal.startTime && proposal.endTime && Date.parse(proposal.endTime) <= Date.parse(proposal.startTime)) {
    blockers.add('end_not_after_start');
  }
  return [...blockers].slice(0, 20);
}

function assertCurrentRevision(record, expectedRevision) {
  const proposal = normalizedProposal(record);
  if (!proposal) throw statusError(409, 'A structured proposal is required.');
  const expected = proposalRevision(expectedRevision);
  if (proposal.revision !== expected) {
    throw statusError(409, `Proposal revision conflict: current=${proposal.revision} requested=${expected}.`, 'PROPOSAL_REVISION_CONFLICT');
  }
  return proposal;
}

function actor(user) {
  const email = normalizeEmail(user && user.email);
  if (!email) throw statusError(401, 'Connected Google identity is required.');
  return {email, authKind: text(user && user.authKind, 80) || 'google_oauth'};
}

function recordOwnedBy(record, user) {
  const ownerEmail = normalizeEmail(record && record.createdByEmail);
  return Boolean(ownerEmail) && ownerEmail === actor(user).email;
}

function redactSender(record) {
  const phone = text(record && record.senderAddress, 64).replace(/\D/g, '');
  if (phone) return `phone_ending_${phone.slice(-4)}`;
  const sender = text(record && record.sender, 80);
  if (!sender) return 'unknown_sender';
  return sender.replace(/[\r\n]+/g, ' ');
}

function boundedClassification(record) {
  const value = record && record.classification || {};
  return {
    classification: text(value.classification || (value.candidate ? 'calendar_event' : 'not_calendar'), 80),
    confidence: Math.max(0, Math.min(1, Number(value.confidence || 0))),
    proposedTitle: text(value.proposedTitle, 240),
    proposedStartTime: text(value.proposedStartTime, 80) || null,
    proposedEndTime: text(value.proposedEndTime, 80) || null,
    durationMinutes: Number(value.durationMinutes || 0) || null,
    timezone: text(value.timezone, 120),
    location: text(value.location, 500),
    sourceExcerpt: text(value.sourceExcerpt || record && record.body, 240),
    missingFields: stringArray(value.missingFields),
    ambiguityFlags: stringArray(value.ambiguityFlags),
    inferredFields: stringArray(value.inferredFields),
    classifierVersion: text(value.classifierVersion, 120),
    classificationHash: text(value.classificationHash, 128),
    approvalEligible: value.approvalEligible === true,
  };
}

function boundedProposal(record) {
  const proposal = normalizedProposal(record);
  if (!proposal) return null;
  return {
    revision: proposal.revision,
    proposalHash: proposal.proposalHash,
    title: proposal.title,
    startTime: proposal.startTime || null,
    endTime: proposal.endTime || null,
    durationMinutes: proposal.durationMinutes || null,
    timezone: proposal.timezone,
    location: proposal.location,
    notes: text(proposal.notes, 500),
    sourceExcerpt: proposal.sourceExcerpt,
    missingFields: proposal.missingFields,
    ambiguityFlags: proposal.ambiguityFlags,
    inferredFields: proposal.inferredFields,
    approvalEligible: proposalBlockers(proposal).length === 0,
  };
}

function boundedApproval(record) {
  const approval = record && record.approval || {};
  return {
    state: text(approval.state, 40) || 'pending',
    proposalRevision: Number(approval.proposalRevision || 0) || null,
    proposalHash: text(approval.proposalHash, 128),
    sourceHash: text(approval.sourceHash, 128),
    classificationHash: text(approval.classificationHash, 128),
    actor: normalizeEmail(approval.actor && approval.actor.email || approval.approvedBy || approval.rejectedBy),
    decidedAtMs: Number(approval.decidedAtMs || approval.approvedAtMs || approval.rejectedAtMs || 0) || null,
    reason: text(approval.reason, 500),
  };
}

function boundedCalendarWrite(record) {
  const write = record && record.calendarWrite || {};
  const provider = write.providerResponseSummary || record && record.createdEvent || {};
  return {
    state: text(write.state, 60) || 'not_started',
    calendarId: text(write.calendarId, 120),
    providerEventId: text(write.providerEventId || provider.eventId, 240),
    providerStatus: text(provider.status, 80),
    providerLink: text(provider.htmlLink, 1000),
    requestHash: text(write.requestHash, 128),
    createdAtMs: Number(write.createdAtMs || provider.createdAtMs || 0) || null,
    executionIdentity: normalizeEmail(write.executionIdentity),
    failureCode: text(write.failure && write.failure.code, 120),
    failureMessage: text(write.failure && write.failure.message, 500),
    ambiguity: text(write.ambiguity, 500),
    retryAllowed: write.retryAllowed === true,
  };
}

function publicRecord(record) {
  const current = record || {};
  return {
    state: text(current.status, 60) || 'received',
    sourceMessageReference: text(current.id || current.messageId, 160),
    sourceHash: text(current.sourceHash, 128),
    sender: redactSender(current),
    receivedAtMs: Number(current.receivedAtMs || 0),
    sourceTransport: text(current.sourceTransport || current.source && current.source.transport, 120),
    classification: boundedClassification(current),
    proposal: boundedProposal(current),
    approval: boundedApproval(current),
    calendarWrite: boundedCalendarWrite(current),
    blockingError: text(current.blockingError, 500),
    timestamps: {
      preservedAtMs: Number(current.preservedAtMs || current.createdAtMs || 0) || null,
      classifiedAtMs: Number(current.classifiedAtMs || 0) || null,
      updatedAtMs: Number(current.updatedAtMs || 0) || null,
    },
  };
}

async function authorizedBucketIds(admin, user) {
  const email = actor(user).email;
  const snapshot = await admin.firestore().collectionGroup('members').where('email', '==', email).get();
  const ids = new Set();
  for (const doc of snapshot.docs || []) {
    const segments = doc.ref.path.split('/');
    const member = doc.data && doc.data() || {};
    if (member.textMiningAuthorized !== true) continue;
    if (segments.length === 4 && segments[0] === 'households' && segments[2] === 'members') ids.add(segments[1]);
  }
  if (!ids.size) throw statusError(403, 'Text message mining is not authorized for the connected Home Center identity.');
  return [...ids];
}

function mergeObjects(base, patch) {
  const out = {...(base || {})};
  for (const [key, value] of Object.entries(patch || {})) {
    if (value && typeof value === 'object' && !Array.isArray(value) && out[key] && typeof out[key] === 'object' && !Array.isArray(out[key])) {
      out[key] = mergeObjects(out[key], value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

function firestoreStore(admin, user, authorize = authorizedBucketIds) {
  const db = admin.firestore();
  let bucketPromise = null;
  const buckets = () => bucketPromise || (bucketPromise = authorize(admin, user));
  return {
    async resolveRecord(id) {
      for (const bucketId of await buckets()) {
        const ref = db.collection('households').doc(bucketId).collection('smsCalendarIntake').doc(id);
        const snap = await ref.get();
        if (snap.exists) {
          const record = {id: snap.id, ...snap.data()};
          if (recordOwnedBy(record, user)) return {bucketId, id: snap.id, record, ref};
        }
      }
      throw statusError(404, 'SMS intake message was not found for the connected household.');
    },
    async listRecords({status, limit}) {
      const records = [];
      for (const bucketId of await buckets()) {
        const snapshot = await db.collection('households').doc(bucketId).collection('smsCalendarIntake').limit(100).get();
        for (const doc of snapshot.docs || []) {
          const record = {id: doc.id, ...doc.data()};
          if (!recordOwnedBy(record, user)) continue;
          if (status && text(record.status, 60) !== status) continue;
          records.push({bucketId, id: doc.id, record, ref: doc.ref});
        }
      }
      records.sort((a, b) => Number(b.record.receivedAtMs || 0) - Number(a.record.receivedAtMs || 0) || a.id.localeCompare(b.id));
      return records.slice(0, limit);
    },
    async updateRecord(resolved, patch) {
      await resolved.ref.set(patch, {merge: true});
      resolved.record = mergeObjects(resolved.record, patch);
      return resolved.record;
    },
    async getAudit(id) {
      const snap = await db.collection('smsCalendarAudit').doc(id).get();
      return snap.exists ? snap.data() : null;
    },
    async setAudit(id, value) {
      await db.collection('smsCalendarAudit').doc(id).set(value, {merge: true});
    },
    async claimCalendarWrite(resolved, claim) {
      return db.runTransaction(async (transaction) => {
        const snap = await transaction.get(resolved.ref);
        if (!snap.exists) throw statusError(404, 'SMS intake message disappeared before Calendar execution.');
        const record = {id: snap.id, ...snap.data()};
        assertApprovalBinding(record);
        const existing = record.calendarWrite || {};
        if (existing.state === 'written') return {claimed: false, state: 'written', record};
        if (existing.state === 'calendar_write_ambiguous' || existing.state === 'ambiguous') {
          return {claimed: false, state: 'calendar_write_ambiguous', record};
        }
        if (existing.state === 'writing') return {claimed: false, state: 'writing', record};
        if (existing.requestHash && existing.requestHash !== claim.requestHash && existing.state !== 'failed') {
          throw statusError(409, 'Calendar execution request conflicts with existing write state.', 'CALENDAR_REQUEST_CONFLICT');
        }
        transaction.set(resolved.ref, {status: 'approved', calendarWrite: claim, updatedAtMs: claim.startedAtMs}, {merge: true});
        const next = mergeObjects(record, {status: 'approved', calendarWrite: claim, updatedAtMs: claim.startedAtMs});
        return {claimed: true, state: 'writing', record: next};
      });
    },
  };
}

async function withAudit({store, resolved, operation, rid, input, user, now}, apply) {
  const auditId = auditDocumentId(operation, resolved.bucketId, resolved.id, rid);
  const inputHash = hashObject(input);
  const existing = await store.getAudit(auditId);
  if (existing) {
    if (text(existing.inputHash, 128) !== inputHash) {
      throw statusError(409, 'requestId was already used with different input.', 'REQUEST_ID_CONFLICT');
    }
    if (TERMINAL_AUDIT_STATES.has(existing.status)) {
      return {idempotent: true, ...(existing.result || {}), auditId, inputHash};
    }
  } else {
    await store.setAudit(auditId, {
      operation,
      actor: actor(user),
      messageId: resolved.id,
      bucketId: resolved.bucketId,
      requestId: rid,
      inputHash,
      status: 'accepted',
      acceptedAtMs: now(),
    });
  }
  try {
    const result = await apply();
    const auditStatus = result && result.auditStatus === 'quarantined' ? 'quarantined' : 'success';
    const bounded = result && result.result ? result.result : result;
    await store.setAudit(auditId, {status: auditStatus, completedAtMs: now(), result: bounded});
    return {...bounded, auditId, inputHash};
  } catch (error) {
    await store.setAudit(auditId, {
      status: 'failed',
      completedAtMs: now(),
      error: {code: text(error && error.code, 120), message: text(error && error.message, 500)},
    }).catch(() => null);
    throw error;
  }
}

function buildEditedProposal(record, args, user, now) {
  if (record.status === 'calendar_written') throw statusError(409, 'A written Calendar proposal cannot be edited.');
  const current = assertCurrentRevision(record, args.proposalRevision);
  const next = {...current};
  for (const field of ['title', 'timezone', 'location', 'notes']) {
    if (Object.prototype.hasOwnProperty.call(args, field)) next[field] = text(args[field], field === 'notes' ? 2000 : field === 'location' ? 500 : 240);
  }
  if (Object.prototype.hasOwnProperty.call(args, 'startTime')) next.startTime = parseRfc3339(args.startTime, 'startTime');
  if (Object.prototype.hasOwnProperty.call(args, 'endTime')) next.endTime = parseRfc3339(args.endTime, 'endTime');
  next.revision = current.revision + 1;
  next.updatedAtMs = now();
  next.updatedBy = actor(user);
  next.sourceMessageId = record.id;
  next.sourceHash = text(record.sourceHash, 128);
  next.classificationHash = text(record.classification && record.classification.classificationHash, 128) || current.classificationHash;
  const missing = [];
  if (!next.title) missing.push('title');
  if (!next.startTime) missing.push('startTime');
  if (!next.endTime) missing.push('endTime');
  if (!next.timezone) missing.push('timezone');
  next.missingFields = missing;
  next.ambiguityFlags = [];
  next.inferredFields = current.inferredFields.filter((field) => !Object.prototype.hasOwnProperty.call(args, field));
  next.fieldProvenance = {...current.fieldProvenance};
  for (const field of ['title', 'startTime', 'endTime', 'timezone', 'location', 'notes']) {
    if (Object.prototype.hasOwnProperty.call(args, field)) next.fieldProvenance[field] = 'explicit_reviewer_edit';
  }
  next.approvalEligible = proposalBlockers(next).length === 0;
  delete next.proposalHash;
  next.proposalHash = proposalHash(next);
  return next;
}

function approvalRecord(state, record, proposal, user, now, reason = '') {
  return {
    state,
    sourceMessageId: record.id,
    sourceHash: text(record.sourceHash, 128),
    classificationHash: text(record.classification && record.classification.classificationHash, 128),
    proposalRevision: proposal.revision,
    proposalHash: proposal.proposalHash,
    actor: actor(user),
    decidedAtMs: now(),
    reason: text(reason, 500),
  };
}

function assertApprovalBinding(record) {
  const proposal = normalizedProposal(record);
  const approval = record && record.approval || {};
  if (!proposal || approval.state !== 'approved') throw statusError(409, 'Calendar mutation requires a durable approved proposal.');
  const expected = {
    sourceHash: text(record.sourceHash, 128),
    classificationHash: text(record.classification && record.classification.classificationHash, 128),
    proposalRevision: proposal.revision,
    proposalHash: proposal.proposalHash,
  };
  for (const [field, value] of Object.entries(expected)) {
    if (String(approval[field] || '') !== String(value || '')) {
      throw statusError(409, `Approval no longer matches current ${field}.`, 'APPROVAL_BINDING_INVALID');
    }
  }
  if (proposalBlockers(proposal).length) throw statusError(409, 'Approved proposal is blocked by missing or ambiguous fields.');
  return {proposal, approval};
}

function providerEventId(proposalHashValue) {
  return `hc${createHash('sha256').update(text(proposalHashValue, 128)).digest('hex').slice(0, 50)}`;
}

function providerCode(error) {
  return Number(error && (error.code || error.response && error.response.status) || 0);
}

function isNotFound(error) {
  return providerCode(error) === 404;
}

function isConflict(error) {
  return providerCode(error) === 409;
}

function isAmbiguousProviderError(error) {
  const code = providerCode(error);
  const name = text(error && error.code, 80).toUpperCase();
  return code >= 500 || code === 408 || ['ETIMEDOUT', 'ECONNRESET', 'EPIPE', 'ENETUNREACH', 'ECONNABORTED'].includes(name);
}

function calendarProvider(google, auth) {
  const calendar = google.calendar({version: 'v3', auth});
  return {
    async get(calendarId, eventId) {
      try {
        const response = await calendar.events.get({calendarId, eventId});
        return response.data || null;
      } catch (error) {
        if (isNotFound(error)) return null;
        throw error;
      }
    },
    async search(calendarId, proposal) {
      const response = await calendar.events.list({
        calendarId,
        q: proposal.title,
        timeMin: proposal.startTime,
        timeMax: proposal.endTime,
        maxResults: 10,
        singleEvents: true,
      });
      return response.data && response.data.items || [];
    },
    async insert(calendarId, requestBody) {
      const response = await calendar.events.insert({calendarId, sendUpdates: 'none', requestBody});
      return response.data || {};
    },
  };
}

function eventSummary(event) {
  const value = event || {};
  return {
    eventId: text(value.id, 240),
    title: text(value.summary, 240),
    status: text(value.status, 80),
    htmlLink: text(value.htmlLink, 1000),
    start: text(value.start && (value.start.dateTime || value.start.date), 80),
    end: text(value.end && (value.end.dateTime || value.end.date), 80),
  };
}

function calendarRequest(record, proposal, eventId, calendarId) {
  return {
    id: eventId,
    summary: proposal.title,
    location: proposal.location || undefined,
    description: [
      `Home Center SMS proposal: ${record.id}`,
      `Proposal revision: ${proposal.revision}`,
      `Source hash: ${text(record.sourceHash, 128)}`,
      'Original private message remains in Home Center and is not copied into this event.',
      proposal.notes ? `Notes: ${text(proposal.notes, 500)}` : '',
    ].filter(Boolean).join('\n'),
    start: {dateTime: proposal.startTime, timeZone: proposal.timezone},
    end: {dateTime: proposal.endTime, timeZone: proposal.timezone},
    extendedProperties: {private: {
      homeCenterSmsIntakeId: record.id,
      homeCenterSmsSourceHash: text(record.sourceHash, 128),
      homeCenterSmsProposalHash: proposal.proposalHash,
      homeCenterSmsProposalRevision: String(proposal.revision),
    }},
  };
}

async function findProviderEvent(provider, calendarId, eventId) {
  return provider.get(calendarId, eventId);
}

async function executeCalendarWrite({store, provider, resolved, user, now}) {
  const {proposal, approval} = assertApprovalBinding(resolved.record);
  const calendarId = 'primary';
  const eventId = providerEventId(proposal.proposalHash);
  const requestBody = calendarRequest(resolved.record, proposal, eventId, calendarId);
  const requestHash = hashObject({calendarId, requestBody, approval});
  const startedAtMs = now();
  const claim = {
    state: 'writing',
    calendarId,
    providerEventId: eventId,
    requestHash,
    proposalRevision: proposal.revision,
    proposalHash: proposal.proposalHash,
    sourceHash: text(resolved.record.sourceHash, 128),
    executionIdentity: actor(user).email,
    executionAuthKind: actor(user).authKind,
    startedAtMs,
  };
  const claimed = await store.claimCalendarWrite(resolved, claim);
  resolved.record = claimed.record;
  if (!claimed.claimed) {
    if (claimed.state === 'written') return {state: 'calendar_written', existing: true, calendarWrite: boundedCalendarWrite(claimed.record)};
    if (claimed.state === 'calendar_write_ambiguous') {
      return {state: 'calendar_write_ambiguous', blocked: true, nextOperation: 'sms_calendar.reconcile_write', calendarWrite: boundedCalendarWrite(claimed.record)};
    }
    return {state: 'writing', blocked: true, nextOperation: 'sms_calendar.reconcile_write', calendarWrite: boundedCalendarWrite(claimed.record)};
  }

  try {
    const existing = await findProviderEvent(provider, calendarId, eventId);
    if (existing) {
      const patch = writtenCalendarPatch(existing, claim, now(), true);
      await store.updateRecord(resolved, patch);
      return {state: 'calendar_written', existing: true, calendarWrite: boundedCalendarWrite(resolved.record)};
    }
    const fuzzy = await provider.search(calendarId, proposal);
    if (fuzzy.length) {
      const patch = {
        status: 'failed',
        calendarWrite: {...claim, state: 'failed', retryAllowed: false, failure: {code: 'POSSIBLE_DUPLICATE', message: 'A likely existing Calendar event requires review.'}, duplicateCandidates: fuzzy.slice(0, 5).map(eventSummary)},
        blockingError: 'A likely existing Calendar event requires review.',
        updatedAtMs: now(),
      };
      await store.updateRecord(resolved, patch);
      return {state: 'failed', blocked: true, reason: 'possible_existing_calendar_event', calendarWrite: boundedCalendarWrite(resolved.record)};
    }
    const inserted = await provider.insert(calendarId, requestBody);
    const patch = writtenCalendarPatch(inserted, claim, now(), false);
    await store.updateRecord(resolved, patch);
    return {state: 'calendar_written', existing: false, calendarWrite: boundedCalendarWrite(resolved.record)};
  } catch (error) {
    if (isConflict(error)) {
      const existing = await findProviderEvent(provider, calendarId, eventId);
      if (existing) {
        const patch = writtenCalendarPatch(existing, claim, now(), true);
        await store.updateRecord(resolved, patch);
        return {state: 'calendar_written', existing: true, calendarWrite: boundedCalendarWrite(resolved.record)};
      }
    }
    if (isAmbiguousProviderError(error)) {
      const patch = {
        status: 'calendar_write_ambiguous',
        calendarWrite: {...claim, state: 'calendar_write_ambiguous', retryAllowed: false, ambiguity: 'Provider may have accepted the deterministic event ID before the response was lost.', failure: {code: text(error && error.code, 120) || `HTTP_${providerCode(error) || 'UNKNOWN'}`, message: text(error && error.message, 500)}, quarantinedAtMs: now()},
        blockingError: 'Calendar provider outcome is uncertain. Reconcile before any new write.',
        updatedAtMs: now(),
      };
      await store.updateRecord(resolved, patch);
      return {auditStatus: 'quarantined', result: {state: 'calendar_write_ambiguous', blocked: true, nextOperation: 'sms_calendar.reconcile_write', calendarWrite: boundedCalendarWrite(resolved.record)}};
    }
    const patch = {
      status: 'failed',
      calendarWrite: {...claim, state: 'failed', retryAllowed: true, failure: {code: text(error && error.code, 120) || `HTTP_${providerCode(error) || 'UNKNOWN'}`, message: text(error && error.message, 500)}, failedAtMs: now()},
      blockingError: 'Calendar provider rejected the write.',
      updatedAtMs: now(),
    };
    await store.updateRecord(resolved, patch);
    return {state: 'failed', blocked: true, calendarWrite: boundedCalendarWrite(resolved.record)};
  }
}

function writtenCalendarPatch(event, claim, createdAtMs, reconciled) {
  return {
    status: 'calendar_written',
    calendarWrite: {
      ...claim,
      state: 'written',
      providerResponseSummary: eventSummary(event),
      createdAtMs,
      reconciled: reconciled === true,
      retryAllowed: false,
      failure: null,
      ambiguity: '',
    },
    blockingError: '',
    updatedAtMs: createdAtMs,
  };
}

async function reconcileCalendarWrite({store, provider, resolved, now}) {
  const write = resolved.record.calendarWrite || {};
  if (!['calendar_write_ambiguous', 'ambiguous', 'writing'].includes(write.state)) {
    if (write.state === 'written') return {state: 'calendar_written', existing: true, calendarWrite: boundedCalendarWrite(resolved.record)};
    throw statusError(409, 'Calendar write is not in an ambiguous or unresolved state.');
  }
  const eventId = text(write.providerEventId, 240);
  const calendarId = text(write.calendarId, 120) || 'primary';
  if (!eventId) throw statusError(409, 'Ambiguous write has no deterministic provider event ID.');
  const event = await findProviderEvent(provider, calendarId, eventId);
  if (event) {
    await store.updateRecord(resolved, writtenCalendarPatch(event, write, now(), true));
    return {state: 'calendar_written', existing: true, reconciled: true, calendarWrite: boundedCalendarWrite(resolved.record)};
  }
  await store.updateRecord(resolved, {
    status: 'failed',
    calendarWrite: {...write, state: 'failed', retryAllowed: true, reconciledAtMs: now(), failure: {code: 'RECONCILED_NOT_FOUND', message: 'Deterministic provider event ID was not found; a new explicit execution may be attempted.'}, ambiguity: ''},
    blockingError: 'Provider reconciliation found no event. A new explicit Calendar execution is required.',
    updatedAtMs: now(),
  });
  return {state: 'failed', reconciled: true, eventFound: false, retryAllowed: true, calendarWrite: boundedCalendarWrite(resolved.record)};
}

async function gmailMatches(google, auth, record) {
  const query = searchQuery(record);
  if (!query) return [];
  const gmail = google.gmail({version: 'v1', auth});
  const listed = await gmail.users.messages.list({userId: 'me', q: `newer_than:365d {${query}}`, maxResults: 10});
  const summaries = [];
  for (const entry of (listed.data && listed.data.messages || []).slice(0, 10)) {
    const response = await gmail.users.messages.get({userId: 'me', id: entry.id, format: 'metadata', metadataHeaders: ['Subject', 'From', 'Date']});
    const data = response.data || {};
    const headers = {};
    for (const header of data.payload && data.payload.headers || []) headers[String(header.name || '').toLowerCase()] = header.value || '';
    summaries.push({messageId: text(data.id || entry.id, 240), threadId: text(data.threadId, 240), subject: text(headers.subject, 240), from: text(headers.from, 240), date: text(headers.date, 120), snippet: text(data.snippet, 500)});
  }
  return summaries;
}

async function calendarMatches(google, auth, record, args) {
  const calendar = google.calendar({version: 'v3', auth});
  const proposal = normalizedProposal(record) || {};
  const receivedAt = Number(record.receivedAtMs || Date.now());
  const response = await calendar.events.list({
    calendarId: 'primary',
    singleEvents: true,
    orderBy: 'startTime',
    maxResults: 20,
    q: text(args.query, 240) || proposal.title || searchQuery(record) || undefined,
    timeMin: text(args.timeMin, 80) || proposal.startTime || new Date(receivedAt - 30 * 86400000).toISOString(),
    timeMax: text(args.timeMax, 80) || proposal.endTime || new Date(receivedAt + 365 * 86400000).toISOString(),
  });
  return (response.data && response.data.items || []).slice(0, 20).map(eventSummary);
}

async function runOperation({google, admin, auth, user, args = {}, authorize = authorizedBucketIds, store = null, provider = null, clock = Date.now}) {
  const operation = text(args.operation || args.type, 120);
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : args;
  if (!registry().operations[operation]) throw statusError(400, `Unsupported SMS Calendar operation: ${operation}`);
  if (WRITE_OPERATIONS.has(operation)) requestId(operationArgs.requestId);
  const now = () => Number(clock());
  const dataStore = store || firestoreStore(admin, user, authorize);

  if (operation === 'sms_calendar.inbox') {
    const wantedStatus = text(operationArgs.status, 60);
    const limit = Math.max(1, Math.min(50, Number(operationArgs.limit || 20)));
    const records = await dataStore.listRecords({status: wantedStatus, limit});
    return {operation, registryVersion: REGISTRY_VERSION, result: {state: wantedStatus || 'all', count: records.length, messages: records.map((item) => publicRecord(item.record))}};
  }

  const id = messageId(operationArgs.messageId);
  const resolved = await dataStore.resolveRecord(id);
  if (operation === 'sms_calendar.get') {
    return {operation, registryVersion: REGISTRY_VERSION, result: publicRecord(resolved.record)};
  }
  if (operation === 'sms_calendar.reconcile') {
    const [gmail, calendar] = await Promise.all([
      gmailMatches(google, auth, resolved.record),
      calendarMatches(google, auth, resolved.record, operationArgs),
    ]);
    return {operation, registryVersion: REGISTRY_VERSION, result: {message: publicRecord(resolved.record), query: searchQuery(resolved.record), gmailMatches: gmail, calendarMatches: calendar, safeToPropose: calendar.length === 0}};
  }

  const rid = requestId(operationArgs.requestId);
  if (operation === 'sms_calendar.approve') {
    const proposal = assertCurrentRevision(resolved.record, operationArgs.proposalRevision);
    const blockers = proposalBlockers(proposal);
    if (blockers.length) throw statusError(409, `Proposal cannot be approved while blocked: ${blockers.join(', ')}`);
    const input = {messageId: id, proposalRevision: proposal.revision, proposalHash: proposal.proposalHash};
    const result = await withAudit({store: dataStore, resolved, operation, rid, input, user, now}, async () => {
      const approval = approvalRecord('approved', resolved.record, proposal, user, now);
      await dataStore.updateRecord(resolved, {status: 'approved', approval, blockingError: '', updatedAtMs: now()});
      return {state: 'approved', messageId: id, approval: boundedApproval(resolved.record)};
    });
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  if (operation === 'sms_calendar.reject' || operation === 'sms_calendar.dismiss') {
    const proposal = assertCurrentRevision(resolved.record, operationArgs.proposalRevision);
    const reason = text(operationArgs.reason, 500);
    if (!reason) throw statusError(400, 'reason is required.');
    const input = {messageId: id, proposalRevision: proposal.revision, proposalHash: proposal.proposalHash, reason};
    const result = await withAudit({store: dataStore, resolved, operation, rid, input, user, now}, async () => {
      const approval = approvalRecord('rejected', resolved.record, proposal, user, now, reason);
      await dataStore.updateRecord(resolved, {status: 'rejected', approval, blockingError: '', updatedAtMs: now()});
      return {state: 'rejected', messageId: id, approval: boundedApproval(resolved.record)};
    });
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  if (operation === 'sms_calendar.update_proposal' || operation === 'sms_calendar.propose') {
    const current = assertCurrentRevision(resolved.record, operationArgs.proposalRevision);
    const input = {...operationArgs, messageId: id, currentProposalHash: current.proposalHash};
    delete input.requestId;
    const result = await withAudit({store: dataStore, resolved, operation, rid, input, user, now}, async () => {
      const proposal = buildEditedProposal(resolved.record, operationArgs, user, now);
      const prior = resolved.record.approval || {};
      const approval = prior.state === 'approved' ? {...prior, state: 'invalidated', invalidatedAtMs: now(), invalidatedBy: actor(user)} : {state: 'pending'};
      await dataStore.updateRecord(resolved, {status: 'proposal_ready', proposal, approval, calendarWrite: {state: 'not_started'}, blockingError: '', updatedAtMs: now()});
      return {state: 'proposal_ready', messageId: id, proposal: boundedProposal(resolved.record), approval: boundedApproval(resolved.record)};
    });
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  if (operation === 'sms_calendar.create_event') {
    const binding = assertApprovalBinding(resolved.record);
    const input = {messageId: id, proposalRevision: binding.proposal.revision, proposalHash: binding.proposal.proposalHash, approval: boundedApproval(resolved.record), calendarId: 'primary'};
    const calendar = provider || calendarProvider(google, auth);
    const result = await withAudit({store: dataStore, resolved, operation, rid, input, user, now}, () => executeCalendarWrite({store: dataStore, provider: calendar, resolved, user, now}));
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  if (operation === 'sms_calendar.reconcile_write') {
    const write = resolved.record.calendarWrite || {};
    const input = {messageId: id, providerEventId: text(write.providerEventId, 240), requestHash: text(write.requestHash, 128)};
    const calendar = provider || calendarProvider(google, auth);
    const result = await withAudit({store: dataStore, resolved, operation, rid, input, user, now}, () => reconcileCalendarWrite({store: dataStore, provider: calendar, resolved, now}));
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  throw statusError(400, `Unsupported SMS Calendar operation: ${operation}`);
}

module.exports = {
  CALENDAR_SCOPE,
  GMAIL_SCOPE,
  REGISTRY_VERSION,
  auditDocumentId,
  authorizedBucketIds,
  canonicalize,
  extractAliases,
  firestoreStore,
  hashObject,
  messageId,
  normalizedProposal,
  providerEventId,
  publicRecord,
  recordOwnedBy,
  registry,
  runOperation,
  searchQuery,
};
