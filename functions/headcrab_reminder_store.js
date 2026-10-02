const crypto = require('node:crypto');

function cleanText(value, max = 4000) {
  const text = typeof value === 'string' ? value.trim().replace(/\s+/g, ' ') : '';
  return text.length > max ? text.slice(0, max) : text;
}

function ownerKey(user = {}) {
  const raw = cleanText(user.uid || user.email || '', 320).toLowerCase();
  if (!raw) throw Object.assign(new Error('Headcrab reminder storage requires an authenticated user identity.'), {status: 401});
  return crypto.createHash('sha256').update(raw).digest('hex').slice(0, 32);
}

function parseDueAt(value) {
  const raw = cleanText(value, 160);
  if (!raw) return null;
  const ms = Date.parse(raw);
  if (!Number.isFinite(ms)) throw Object.assign(new Error('dueAt must be a valid ISO-8601 timestamp with timezone when supplied.'), {status: 400});
  if (!/[zZ]|[+-]\d\d:\d\d$/.test(raw)) throw Object.assign(new Error('dueAt must include an explicit timezone offset or Z.'), {status: 400});
  return new Date(ms).toISOString();
}

function baseCollection(admin, user) {
  return admin.firestore()
    .collection('headcrabReminderUsers')
    .doc(ownerKey(user))
    .collection('reminders');
}

async function listOpenReminders({admin, user, limit = 100}) {
  const snap = await baseCollection(admin, user).limit(Math.max(1, Math.min(200, Number(limit) || 100))).get();
  const items = [];
  snap.forEach((doc) => {
    const data = doc.data() || {};
    if (data.status === 'open') items.push({...data, reminderId: doc.id});
  });
  items.sort((a, b) => {
    const ad = a.dueAt || '9999-12-31T23:59:59.999Z';
    const bd = b.dueAt || '9999-12-31T23:59:59.999Z';
    if (ad !== bd) return ad.localeCompare(bd);
    return String(a.createdAt || '').localeCompare(String(b.createdAt || ''));
  });
  return items;
}

async function captureReminder({admin, user, label, dueAt = null, notes = '', source = 'conversation', sourceRef = ''}) {
  const cleanLabel = cleanText(label, 500);
  if (!cleanLabel) throw Object.assign(new Error('Reminder label is required.'), {status: 400});
  const normalizedDueAt = parseDueAt(dueAt);
  const normalizedSourceRef = cleanText(sourceRef, 500);
  const open = await listOpenReminders({admin, user, limit: 200});
  const duplicate = open.find((item) =>
    (normalizedSourceRef && cleanText(item.sourceRef, 500) === normalizedSourceRef)
    || (
      cleanText(item.label, 500).toLowerCase() === cleanLabel.toLowerCase()
      && (item.dueAt || null) === normalizedDueAt
    )
  );
  if (duplicate) return {created: false, reminder: duplicate};

  const ref = baseCollection(admin, user).doc();
  const now = new Date().toISOString();
  const reminder = {
    label: cleanLabel,
    dueAt: normalizedDueAt,
    notes: cleanText(notes, 2000),
    source: cleanText(source, 120) || 'conversation',
    sourceRef: normalizedSourceRef || null,
    status: 'open',
    createdAt: now,
    updatedAt: now,
    closedAt: null,
    closeReason: null,
  };
  await ref.set(reminder);
  return {created: true, reminder: {...reminder, reminderId: ref.id}};
}

async function closeReminder({admin, user, reminderId, status = 'done', reason = ''}) {
  const cleanId = cleanText(reminderId, 200);
  if (!cleanId) throw Object.assign(new Error('reminderId is required.'), {status: 400});
  if (!['done', 'cancelled'].includes(status)) throw Object.assign(new Error('status must be done or cancelled.'), {status: 400});
  const ref = baseCollection(admin, user).doc(cleanId);
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Headcrab reminder not found.'), {status: 404});
  const now = new Date().toISOString();
  await ref.set({
    status,
    updatedAt: now,
    closedAt: now,
    closeReason: cleanText(reason, 1000) || null,
  }, {merge: true});
  return {reminderId: cleanId, status, closedAt: now};
}

async function rescheduleReminder({admin, user, reminderId, dueAt}) {
  const cleanId = cleanText(reminderId, 200);
  if (!cleanId) throw Object.assign(new Error('reminderId is required.'), {status: 400});
  const normalizedDueAt = parseDueAt(dueAt);
  if (!normalizedDueAt) throw Object.assign(new Error('dueAt is required when rescheduling.'), {status: 400});
  const ref = baseCollection(admin, user).doc(cleanId);
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Headcrab reminder not found.'), {status: 404});
  const now = new Date().toISOString();
  await ref.set({dueAt: normalizedDueAt, status: 'open', updatedAt: now, closedAt: null, closeReason: null}, {merge: true});
  return {reminderId: cleanId, dueAt: normalizedDueAt, status: 'open'};
}


function checkpointCollection(admin, user) {
  return admin.firestore()
    .collection('headcrabReminderUsers')
    .doc(ownerKey(user))
    .collection('attentionCheckpoints');
}

async function recordCheckpoint({admin, user, kind, checkedAt = null}) {
  const cleanKind = cleanText(kind, 80).toLowerCase();
  if (!['email', 'work_email', 'calendar', 'records', 'bills'].includes(cleanKind)) {
    throw Object.assign(new Error('Unsupported Headcrab checkpoint kind.'), {status: 400});
  }
  const at = checkedAt ? parseDueAt(checkedAt) : new Date().toISOString();
  await checkpointCollection(admin, user).doc(cleanKind).set({
    kind: cleanKind,
    checkedAt: at,
    updatedAt: new Date().toISOString(),
  }, {merge: true});
  return {kind: cleanKind, checkedAt: at};
}

async function readCheckpoints({admin, user}) {
  const snap = await checkpointCollection(admin, user).limit(20).get();
  const values = {};
  snap.forEach((doc) => {
    const data = doc.data() || {};
    if (data.kind) values[data.kind] = data.checkedAt || null;
  });
  return values;
}

function maintenancePrompt(now = new Date()) {
  const choices = [
    {kind: 'move', text: 'Headcrab maintenance: two-minute movement snack?'},
    {kind: 'outside', text: 'Headcrab maintenance: five minutes outside if practical?'},
    {kind: 'water', text: 'Headcrab maintenance: water check.'},
    {kind: 'stretch', text: 'Headcrab maintenance: unclench, stand, stretch something stubborn.'},
  ];
  const day = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()) / 86400000;
  const slot = Math.floor(now.getUTCHours() / 3);
  return choices[Math.abs(Math.floor(day + slot)) % choices.length];
}

function attentionFallback(checkpoints = {}, now = new Date()) {
  const emailAt = checkpoints.email ? Date.parse(checkpoints.email) : NaN;
  const workEmailAt = checkpoints.work_email ? Date.parse(checkpoints.work_email) : NaN;
  const calendarAt = checkpoints.calendar ? Date.parse(checkpoints.calendar) : NaN;
  const hours = (ms) => Number.isFinite(ms) ? (now.getTime() - ms) / 3600000 : Infinity;

  if (hours(emailAt) >= 6) return {kind: 'email', class: 'attention', text: 'Headcrab: when did you last check personal email?'};
  if (hours(workEmailAt) >= 4) return {kind: 'work_email', class: 'attention', text: 'Headcrab: when did you last check work email?'};
  if (hours(calendarAt) >= 12) return {kind: 'calendar', class: 'attention', text: 'Headcrab: have you checked today\'s calendar lately?'};
  return {...maintenancePrompt(now), class: 'maintenance'};
}

async function attentionPulse({admin, user, limit = 100, now = new Date()}) {
  const reminders = await listOpenReminders({admin, user, limit});
  const checkpoints = await readCheckpoints({admin, user});
  if (reminders.length) {
    return {mode: 'obligation', reminders, checkpoints};
  }
  return {mode: 'fallback', prompt: attentionFallback(checkpoints, now), checkpoints};
}
\n
const MONTHS = Object.freeze({
  jan: 0, january: 0, feb: 1, february: 1, mar: 2, march: 2, apr: 3, april: 3,
  may: 4, jun: 5, june: 5, jul: 6, july: 6, aug: 7, august: 7,
  sep: 8, sept: 8, september: 8, oct: 9, october: 9, nov: 10, november: 10, dec: 11, december: 11,
});

function dueFromText(textValue, defaultOffset = '-05:00') {
  const value = cleanText(textValue, 4000);
  const m = value.match(/\\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\\s+(\\d{1,2})(?:,)?\\s+(20\\d{2})\\b/i);
  if (!m) return null;
  const month = MONTHS[m[1].toLowerCase()];
  const day = Number(m[2]);
  const year = Number(m[3]);
  if (!Number.isInteger(month) || day < 1 || day > 31) return null;
  const mm = String(month + 1).padStart(2, '0');
  const dd = String(day).padStart(2, '0');
  return parseDueAt(`${year}-${mm}-${dd}T17:00:00${defaultOffset}`);
}

function emailReminderCandidate(message = {}, defaultOffset = '-05:00') {
  const subject = cleanText(message.subject, 500);
  const snippet = cleanText(message.snippet, 1200);
  const haystack = `${subject} ${snippet}`.toLowerCase();
  const labels = new Set(Array.isArray(message.labels) ? message.labels : []);
  if (labels.has('CATEGORY_PROMOTIONS') || labels.has('SPAM') || labels.has('TRASH')) return null;

  const rules = [
    {kind: 'vehicle_renewal', re: /\\b(?:tag|tags|vehicle|registration)\\b.*\\brenew(?:al|ed)?\\b|\\brenew(?:al|ed)?\\b.*\\b(?:tag|tags|vehicle|registration)\\b/i, label: 'Handle vehicle tags / registration renewal'},
    {kind: 'insurance_claim', re: /\\b(?:claim|disability|insurance)\\b.*\\b(?:action required|due|deadline|records?|documents?)\\b|\\b(?:action required|due|deadline)\\b.*\\b(?:claim|disability|insurance)\\b/i, label: 'Handle insurance claim requirement'},
    {kind: 'medical_records', re: /\\bmedical records?\\b.*\\b(?:ready|requested|request|pick up|available|send|release)\\b|\\b(?:records?|documents?)\\b.*\\bprovider\\b/i, label: 'Handle medical records request'},
    {kind: 'account_action', re: /\\b(?:action required|final reminder|past due|payment due|finish registration|renewal due)\\b/i, label: subject || 'Handle account action'},
  ];
  const rule = rules.find((entry) => entry.re.test(haystack));
  if (!rule) return null;
  const dueAt = dueFromText(subject + ' ' + snippet, defaultOffset);
  const label = rule.kind === 'account_action' ? cleanText(subject, 300) : rule.label;
  return {
    kind: rule.kind,
    label,
    dueAt,
    notes: subject && snippet ? `${subject} — ${snippet}` : (subject || snippet),
  };
}

async function mineEmailReminders({google, auth, admin, user, query = 'newer_than:7d -category:promotions -in:spam -in:trash', maxResults = 50, defaultOffset = '-05:00'}) {
  if (!google || !auth) throw Object.assign(new Error('Gmail mining requires connected Google OAuth context.'), {status: 401});
  const gmail = google.gmail({version: 'v1', auth});
  const listed = await gmail.users.messages.list({
    userId: 'me',
    q: cleanText(query, 500),
    maxResults: Math.max(1, Math.min(100, Number(maxResults) || 50)),
  });
  const ids = (listed.data.messages || []).map((item) => item.id).filter(Boolean);
  const created = [];
  const skipped = [];
  for (const id of ids) {
    const fetched = await gmail.users.messages.get({userId: 'me', id, format: 'metadata', metadataHeaders: ['Subject', 'From', 'Date']});
    const headers = Object.fromEntries((fetched.data.payload && fetched.data.payload.headers || []).map((h) => [String(h.name || '').toLowerCase(), String(h.value || '')]));
    const message = {
      id,
      subject: headers.subject || '',
      from: headers.from || '',
      snippet: fetched.data.snippet || '',
      labels: fetched.data.labelIds || [],
    };
    const candidate = emailReminderCandidate(message, defaultOffset);
    if (!candidate) {
      skipped.push({messageId: id, reason: 'not_high_confidence'});
      continue;
    }
    const result = await captureReminder({
      admin,
      user,
      label: candidate.label,
      dueAt: candidate.dueAt,
      notes: candidate.notes,
      source: 'gmail_miner',
      sourceRef: `gmail:${id}`,
    });
    if (result.created) created.push({messageId: id, kind: candidate.kind, reminder: result.reminder});
    else skipped.push({messageId: id, reason: 'duplicate'});
  }
  return {query, scanned: ids.length, created, skippedCount: skipped.length};
}
\nfunction registerHeadcrabReminderTools(server, {admin, google, z, textResult, requestUserContext, securitySchemes}) {
  const commonMeta = {
    securitySchemes,
    _meta: {securitySchemes},
  };



  server.registerTool('headcrab_mine_email', {
    title: 'Headcrab mine email',
    description: 'Scan recent non-promotional Gmail for high-confidence actionable obligations and persist them into the same durable Headcrab reminder ledger. This is a worker/intake operation, not a reminder delivery channel. Ambiguous mail is skipped; it does not create Calendar events.',
    inputSchema: {
      query: z.string().max(500).optional(),
      maxResults: z.number().int().min(1).max(100).default(50),
      defaultOffset: z.string().max(16).default('-05:00'),
    },
    ...commonMeta,
    annotations: {readOnlyHint: false, openWorldHint: true},
  }, async (args, extra) => {
    const {user, auth} = await requestUserContext(extra);
    return textResult(await mineEmailReminders({google, auth, admin, user, ...(args || {})}));
  });

  server.registerTool('headcrab_attention_pulse', {
    title: 'Headcrab attention pulse',
    description: 'Return the durable unresolved reminder stack, or when no open reminder exists, a tiny fallback attention prompt such as checking email/calendar. Intended for every conversational preflight so Headcrab cannot disappear during deep work.',
    inputSchema: {limit: z.number().int().min(1).max(200).default(100)},
    ...commonMeta,
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestUserContext(extra);
    return textResult(await attentionPulse({admin, user, limit: args && args.limit}));
  });

  server.registerTool('headcrab_mark_checked', {
    title: 'Headcrab mark checked',
    description: 'Record that Drew actually checked a recurring attention surface such as personal email, work email, calendar, records, or bills. Do not mark a surface checked merely because Headcrab asked about it.',
    inputSchema: {
      kind: z.enum(['email', 'work_email', 'calendar', 'records', 'bills']),
      checkedAt: z.string().optional().describe('Optional ISO-8601 timestamp with timezone; defaults to now.'),
    },
    ...commonMeta,
    annotations: {readOnlyHint: false, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestUserContext(extra);
    return textResult(await recordCheckpoint({admin, user, ...(args || {})}));
  });

  server.registerTool('headcrab_remember', {
    title: 'Headcrab remember',
    description: 'Persist an unresolved Drew-facing obligation in Home Center. Use this when Drew says ordinary things like "remember this", "don\'t let me forget", "I need to", "I have to", or otherwise clearly asks Headcrab to keep an obligation in view. This is durable conversational reminder state, NOT a scheduled job or calendar event. dueAt is optional; never invent a due time.',
    inputSchema: {
      label: z.string().min(1).max(500),
      dueAt: z.string().optional().describe('Optional ISO-8601 timestamp with explicit timezone. Omit when Drew gave no real time.'),
      notes: z.string().max(2000).optional(),
      source: z.string().max(120).optional(),
    },
    ...commonMeta,
    annotations: {readOnlyHint: false, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestUserContext(extra);
    return textResult(await captureReminder({admin, user, ...(args || {})}));
  });

  server.registerTool('headcrab_reminders', {
    title: 'Headcrab reminders',
    description: 'Read the durable unresolved Headcrab reminder stack for the authenticated user. Use during conversational preflight so open obligations can surface in the current chat instead of relying on another reminder chat or scheduled event.',
    inputSchema: {limit: z.number().int().min(1).max(200).default(100)},
    ...commonMeta,
    annotations: {readOnlyHint: true, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestUserContext(extra);
    return textResult({reminders: await listOpenReminders({admin, user, limit: args && args.limit})});
  });

  server.registerTool('headcrab_close_reminder', {
    title: 'Headcrab close reminder',
    description: 'Close a durable Headcrab obligation only after Drew explicitly confirms completion or cancellation. Ordinary language is sufficient; never close merely because the reminder was shown.',
    inputSchema: {
      reminderId: z.string().min(1).max(200),
      status: z.enum(['done', 'cancelled']).default('done'),
      reason: z.string().max(1000).optional(),
    },
    ...commonMeta,
    annotations: {readOnlyHint: false, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestUserContext(extra);
    return textResult(await closeReminder({admin, user, ...(args || {})}));
  });

  server.registerTool('headcrab_reschedule_reminder', {
    title: 'Headcrab reschedule reminder',
    description: 'Replace the due time of an existing durable Headcrab obligation. This updates reminder state; it does not create a scheduled automation or calendar event.',
    inputSchema: {
      reminderId: z.string().min(1).max(200),
      dueAt: z.string().min(1).max(160),
    },
    ...commonMeta,
    annotations: {readOnlyHint: false, openWorldHint: false},
  }, async (args, extra) => {
    const {user} = await requestUserContext(extra);
    return textResult(await rescheduleReminder({admin, user, ...(args || {})}));
  });
}

module.exports = {
  cleanText,
  ownerKey,
  parseDueAt,
  listOpenReminders,
  captureReminder,
  closeReminder,
  rescheduleReminder,
  registerHeadcrabReminderTools,
};
