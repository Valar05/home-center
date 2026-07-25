'use strict';

const {createHash} = require('node:crypto');

const REGISTRY_VERSION = '2026-07-25.notification-sms-calendar-v1';
const CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events';
const GMAIL_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly';
const WRITE_OPERATIONS = new Set([
  'sms_calendar.propose',
  'sms_calendar.dismiss',
  'sms_calendar.create_event',
]);

function text(value, max = 12000) {
  const clean = typeof value === 'string' ? value.trim() : '';
  return clean.length > max ? clean.slice(0, max) : clean;
}

function normalizeEmail(value) {
  return text(value, 320).toLowerCase();
}

function requestId(value) {
  const clean = text(value, 200);
  if (!clean) throw statusError(400, 'requestId is required.');
  return clean;
}

function statusError(status, message) {
  return Object.assign(new Error(message), {status});
}

function messageId(value) {
  const clean = text(value, 160);
  if (!/^sms_[a-f0-9]{32,64}$/.test(clean)) {
    throw statusError(400, 'messageId must be a Home Center SMS intake id.');
  }
  return clean;
}

function registry() {
  return {
    version: REGISTRY_VERSION,
    invocationTool: 'drive_operation',
    authorityBoundary: 'SMS intake is source evidence. A proposal is not a calendar event, and only sms_calendar.create_event may write Google Calendar after explicit confirmation.',
    operations: {
      'sms_calendar.inbox': {
        summary: 'List pending SMS reminder candidates captured locally from Google Messages notifications.',
        write: false,
        requiredScopes: [],
        input: {status: 'optional pending|proposed|dismissed|created|duplicate', limit: 'optional integer 1..50'},
      },
      'sms_calendar.get': {
        summary: 'Read one exact SMS reminder candidate and its provenance.',
        write: false,
        requiredScopes: [],
        input: {messageId: 'string'},
      },
      'sms_calendar.reconcile': {
        summary: 'Search Gmail and Google Calendar for likely matches before proposing or creating an event.',
        write: false,
        requiredScopes: [GMAIL_SCOPE, CALENDAR_SCOPE],
        input: {messageId: 'string', timeMin: 'optional RFC3339', timeMax: 'optional RFC3339'},
      },
      'sms_calendar.propose': {
        summary: 'Save a structured calendar proposal without creating an event.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {
          messageId: 'string',
          title: 'string',
          startTime: 'RFC3339',
          endTime: 'RFC3339',
          provider: 'optional string',
          location: 'optional string',
          preparation: 'optional string',
          cancellation: 'optional string',
          owner: 'optional string',
          confidence: 'number 0..1',
          uncertainties: 'optional string[]',
          requestId: 'string',
        },
      },
      'sms_calendar.dismiss': {
        summary: 'Dismiss an SMS reminder candidate without deleting its source record.',
        write: true,
        requiresRequestId: true,
        requiredScopes: [],
        input: {messageId: 'string', reason: 'string', requestId: 'string'},
      },
      'sms_calendar.create_event': {
        summary: 'Create the saved proposal in Google Calendar after duplicate checks and explicit human confirmation.',
        write: true,
        requiresRequestId: true,
        requiresExplicitConfirmation: true,
        requiredScopes: [CALENDAR_SCOPE],
        input: {messageId: 'string', approved: 'literal true', confirmationText: 'literal CREATE EVENT', requestId: 'string'},
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
  ];
  for (const [alias, pattern] of known) {
    if (pattern.test(body)) aliases.add(alias);
  }
  return [...aliases].slice(0, 8);
}

function searchQuery(record) {
  const parts = extractAliases(record);
  const sender = text(record && record.sender, 160);
  if (sender && !/^\+?[\d\s().-]+$/.test(sender)) parts.push(sender);
  return [...new Set(parts)].slice(0, 6).join(' ');
}

function validateProposal(args) {
  const title = text(args.title, 240);
  const startTime = text(args.startTime, 80);
  const endTime = text(args.endTime, 80);
  if (!title || !startTime || !endTime) {
    throw statusError(400, 'title, startTime, and endTime are required.');
  }
  const startMs = Date.parse(startTime);
  const endMs = Date.parse(endTime);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) {
    throw statusError(400, 'startTime and endTime must be valid RFC3339 timestamps with end after start.');
  }
  const confidence = Number(args.confidence);
  if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
    throw statusError(400, 'confidence must be a number from 0 through 1.');
  }
  const uncertainties = Array.isArray(args.uncertainties) ?
    args.uncertainties.map((value) => text(value, 500)).filter(Boolean).slice(0, 12) : [];
  return {
    title,
    startTime: new Date(startMs).toISOString(),
    endTime: new Date(endMs).toISOString(),
    provider: text(args.provider, 240),
    location: text(args.location, 500),
    preparation: text(args.preparation, 2000),
    cancellation: text(args.cancellation, 2000),
    owner: text(args.owner, 160),
    confidence,
    uncertainties,
  };
}

async function authorizedBucketIds(admin, user) {
  const email = normalizeEmail(user && user.email);
  if (!email) throw statusError(401, 'Connected Google identity is required.');
  const snapshot = await admin.firestore().collectionGroup('members').where('email', '==', email).get();
  const ids = new Set();
  for (const doc of snapshot.docs || []) {
    const segments = doc.ref.path.split('/');
    if (segments.length === 4 && segments[0] === 'households' && segments[2] === 'members') {
      ids.add(segments[1]);
    }
  }
  if (!ids.size) throw statusError(403, 'The connected Google identity is not a Home Center household member.');
  return [...ids];
}

async function resolveRecord({admin, user, id, authorize = authorizedBucketIds}) {
  const buckets = await authorize(admin, user);
  for (const bucketId of buckets) {
    const ref = admin.firestore().collection('households').doc(bucketId).collection('smsCalendarIntake').doc(id);
    const snap = await ref.get();
    if (snap.exists) return {bucketId, ref, record: {id: snap.id, ...snap.data()}};
  }
  throw statusError(404, 'SMS intake message was not found for the connected household.');
}

function publicRecord(bucketId, record) {
  return {
    id: record.id,
    bucketId,
    status: record.status || 'pending',
    sender: record.sender || '',
    body: record.body || '',
    receivedAtMs: Number(record.receivedAtMs || 0),
    source: record.source || {},
    classification: record.classification || {},
    proposal: record.proposal || null,
    createdEvent: record.createdEvent || null,
    createdAtMs: Number(record.createdAtMs || 0),
    updatedAtMs: Number(record.updatedAtMs || 0),
  };
}

async function listInbox({admin, user, args, authorize = authorizedBucketIds}) {
  const buckets = await authorize(admin, user);
  const wantedStatus = text(args.status || 'pending', 40).toLowerCase();
  const limit = Math.max(1, Math.min(50, Number(args.limit || 20)));
  const messages = [];
  for (const bucketId of buckets) {
    const snapshot = await admin.firestore().collection('households').doc(bucketId)
      .collection('smsCalendarIntake').limit(100).get();
    for (const doc of snapshot.docs || []) {
      const record = {id: doc.id, ...doc.data()};
      if (wantedStatus && (record.status || 'pending') !== wantedStatus) continue;
      messages.push(publicRecord(bucketId, record));
    }
  }
  messages.sort((a, b) => b.receivedAtMs - a.receivedAtMs || a.id.localeCompare(b.id));
  return {status: wantedStatus, count: Math.min(limit, messages.length), messages: messages.slice(0, limit)};
}

async function gmailMatches(google, auth, record) {
  const query = searchQuery(record);
  if (!query) return [];
  const gmail = google.gmail({version: 'v1', auth});
  const listed = await gmail.users.messages.list({userId: 'me', q: `newer_than:365d {${query}}`, maxResults: 10});
  const summaries = [];
  for (const entry of (listed.data && listed.data.messages || []).slice(0, 10)) {
    const response = await gmail.users.messages.get({
      userId: 'me',
      id: entry.id,
      format: 'metadata',
      metadataHeaders: ['Subject', 'From', 'Date'],
    });
    const data = response.data || {};
    const headers = {};
    for (const header of data.payload && data.payload.headers || []) {
      headers[String(header.name || '').toLowerCase()] = header.value || '';
    }
    summaries.push({
      messageId: data.id || entry.id,
      threadId: data.threadId || '',
      subject: headers.subject || '',
      from: headers.from || '',
      date: headers.date || '',
      snippet: text(data.snippet, 1000),
    });
  }
  return summaries;
}

async function calendarMatches(google, auth, record, args) {
  const calendar = google.calendar({version: 'v3', auth});
  const proposal = record.proposal || {};
  const receivedAt = Number(record.receivedAtMs || Date.now());
  const defaultMin = new Date(receivedAt - 30 * 86400000).toISOString();
  const defaultMax = new Date(receivedAt + 365 * 86400000).toISOString();
  const response = await calendar.events.list({
    calendarId: 'primary',
    singleEvents: true,
    orderBy: 'startTime',
    maxResults: 20,
    q: text(args.query, 240) || proposal.title || searchQuery(record) || undefined,
    timeMin: text(args.timeMin, 80) || proposal.startTime || defaultMin,
    timeMax: text(args.timeMax, 80) || proposal.endTime || defaultMax,
  });
  return (response.data && response.data.items || []).map((event) => ({
    eventId: event.id || '',
    title: event.summary || '',
    start: event.start || {},
    end: event.end || {},
    location: event.location || '',
    status: event.status || '',
    htmlLink: event.htmlLink || '',
  }));
}

async function auditOnce(admin, id, payload, apply) {
  const db = admin.firestore();
  const ref = db.collection('smsCalendarAudit').doc(createHash('sha256').update(id).digest('hex'));
  return db.runTransaction(async (tx) => {
    const existing = await tx.get(ref);
    if (existing.exists && existing.data().status === 'success') {
      return {idempotent: true, ...(existing.data().result || {}), auditId: ref.id};
    }
    const result = await apply(tx);
    tx.set(ref, {
      ...payload,
      requestId: id,
      status: 'success',
      createdAtMs: Date.now(),
      result,
    });
    return {...result, auditId: ref.id};
  });
}

async function createCalendarEvent({google, admin, auth, user, args, resolved}) {
  if (args.approved !== true || text(args.confirmationText, 80) !== 'CREATE EVENT') {
    throw statusError(409, 'Explicit confirmation is required: approved=true and confirmationText="CREATE EVENT".');
  }
  const proposal = resolved.record.proposal;
  if (!proposal) throw statusError(409, 'Save a proposal before creating a calendar event.');
  const calendar = google.calendar({version: 'v3', auth});
  const exact = await calendar.events.list({
    calendarId: 'primary',
    privateExtendedProperty: [`homeCenterSmsIntakeId=${resolved.record.id}`],
    maxResults: 10,
    singleEvents: true,
  });
  const exactItems = exact.data && exact.data.items || [];
  if (exactItems.length) {
    return {created: false, duplicate: true, reason: 'existing_home_center_source', event: exactItems[0]};
  }
  const fuzzy = await calendar.events.list({
    calendarId: 'primary',
    q: proposal.title,
    timeMin: proposal.startTime,
    timeMax: proposal.endTime,
    maxResults: 10,
    singleEvents: true,
  });
  const fuzzyItems = fuzzy.data && fuzzy.data.items || [];
  if (fuzzyItems.length) {
    await resolved.ref.set({
      status: 'duplicate',
      duplicateCandidates: fuzzyItems.slice(0, 5).map((event) => ({
        eventId: event.id || '',
        title: event.summary || '',
        start: event.start || {},
        end: event.end || {},
      })),
      updatedAtMs: Date.now(),
    }, {merge: true});
    return {created: false, duplicate: true, reason: 'possible_existing_calendar_event', events: fuzzyItems};
  }
  const description = [
    `Home Center SMS intake: ${resolved.record.id}`,
    `Source received: ${new Date(Number(resolved.record.receivedAtMs || Date.now())).toISOString()}`,
    proposal.provider ? `Provider: ${proposal.provider}` : '',
    proposal.owner ? `For: ${proposal.owner}` : '',
    proposal.preparation ? `Preparation: ${proposal.preparation}` : '',
    proposal.cancellation ? `Cancellation: ${proposal.cancellation}` : '',
    'Exact source wording remains in the Home Center intake record.',
  ].filter(Boolean).join('\n');
  const inserted = await calendar.events.insert({
    calendarId: 'primary',
    sendUpdates: 'none',
    requestBody: {
      summary: proposal.title,
      location: proposal.location || undefined,
      description,
      start: {dateTime: proposal.startTime},
      end: {dateTime: proposal.endTime},
      extendedProperties: {private: {
        homeCenterSmsIntakeId: resolved.record.id,
        homeCenterSmsSourceHash: resolved.record.sourceHash || '',
      }},
    },
  });
  const event = inserted.data || {};
  await resolved.ref.set({
    status: 'created',
    createdEvent: {
      eventId: event.id || '',
      title: event.summary || proposal.title,
      htmlLink: event.htmlLink || '',
      createdAtMs: Date.now(),
      createdBy: normalizeEmail(user && user.email),
    },
    updatedAtMs: Date.now(),
  }, {merge: true});
  return {created: true, duplicate: false, event};
}

async function runOperation({google, admin, auth, user, args = {}, authorize = authorizedBucketIds}) {
  const operation = text(args.operation || args.type, 120);
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : args;
  if (!registry().operations[operation]) throw statusError(400, `Unsupported SMS Calendar operation: ${operation}`);
  if (WRITE_OPERATIONS.has(operation)) requestId(operationArgs.requestId);

  if (operation === 'sms_calendar.inbox') {
    return {operation, registryVersion: REGISTRY_VERSION, result: await listInbox({admin, user, args: operationArgs, authorize})};
  }

  const id = messageId(operationArgs.messageId);
  const resolved = await resolveRecord({admin, user, id, authorize});
  if (operation === 'sms_calendar.get') {
    return {operation, registryVersion: REGISTRY_VERSION, result: publicRecord(resolved.bucketId, resolved.record)};
  }
  if (operation === 'sms_calendar.reconcile') {
    const [gmail, calendar] = await Promise.all([
      gmailMatches(google, auth, resolved.record),
      calendarMatches(google, auth, resolved.record, operationArgs),
    ]);
    return {
      operation,
      registryVersion: REGISTRY_VERSION,
      result: {
        message: publicRecord(resolved.bucketId, resolved.record),
        query: searchQuery(resolved.record),
        gmailMatches: gmail,
        calendarMatches: calendar,
        safeToPropose: calendar.length === 0,
      },
    };
  }
  if (operation === 'sms_calendar.propose') {
    const proposal = validateProposal(operationArgs);
    const rid = requestId(operationArgs.requestId);
    const result = await auditOnce(admin, rid, {
      operation,
      actor: normalizeEmail(user && user.email),
      messageId: id,
      bucketId: resolved.bucketId,
    }, async () => {
      await resolved.ref.set({
        status: 'proposed',
        proposal: {...proposal, proposedAtMs: Date.now(), proposedBy: normalizeEmail(user && user.email)},
        updatedAtMs: Date.now(),
      }, {merge: true});
      return {messageId: id, status: 'proposed', proposal};
    });
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  if (operation === 'sms_calendar.dismiss') {
    const rid = requestId(operationArgs.requestId);
    const reason = text(operationArgs.reason, 2000);
    if (!reason) throw statusError(400, 'reason is required.');
    const result = await auditOnce(admin, rid, {
      operation,
      actor: normalizeEmail(user && user.email),
      messageId: id,
      bucketId: resolved.bucketId,
    }, async () => {
      await resolved.ref.set({
        status: 'dismissed',
        dismissal: {reason, dismissedAtMs: Date.now(), dismissedBy: normalizeEmail(user && user.email)},
        updatedAtMs: Date.now(),
      }, {merge: true});
      return {messageId: id, status: 'dismissed', reason};
    });
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  if (operation === 'sms_calendar.create_event') {
    const rid = requestId(operationArgs.requestId);
    const result = await auditOnce(admin, rid, {
      operation,
      actor: normalizeEmail(user && user.email),
      messageId: id,
      bucketId: resolved.bucketId,
    }, async () => createCalendarEvent({google, admin, auth, user, args: operationArgs, resolved}));
    return {operation, registryVersion: REGISTRY_VERSION, result};
  }
  throw statusError(400, `Unsupported SMS Calendar operation: ${operation}`);
}

module.exports = {
  CALENDAR_SCOPE,
  GMAIL_SCOPE,
  REGISTRY_VERSION,
  authorizedBucketIds,
  extractAliases,
  messageId,
  registry,
  runOperation,
  searchQuery,
  validateProposal,
};
