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

async function captureReminder({admin, user, label, dueAt = null, notes = '', source = 'conversation'}) {
  const cleanLabel = cleanText(label, 500);
  if (!cleanLabel) throw Object.assign(new Error('Reminder label is required.'), {status: 400});
  const normalizedDueAt = parseDueAt(dueAt);
  const open = await listOpenReminders({admin, user, limit: 200});
  const duplicate = open.find((item) =>
    cleanText(item.label, 500).toLowerCase() === cleanLabel.toLowerCase()
    && (item.dueAt || null) === normalizedDueAt
  );
  if (duplicate) return {created: false, reminder: duplicate};

  const ref = baseCollection(admin, user).doc();
  const now = new Date().toISOString();
  const reminder = {
    label: cleanLabel,
    dueAt: normalizedDueAt,
    notes: cleanText(notes, 2000),
    source: cleanText(source, 120) || 'conversation',
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

function registerHeadcrabReminderTools(server, {admin, z, textResult, requestUserContext, securitySchemes}) {
  const commonMeta = {
    securitySchemes,
    _meta: {securitySchemes},
  };

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
