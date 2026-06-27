const {onRequest} = require('firebase-functions/v2/https');
const {defineSecret} = require('firebase-functions/params');
const admin = require('firebase-admin');
const {google} = require('googleapis');

admin.initializeApp();

const OPENAI_API_KEY = defineSecret('OPENAI_API_KEY');
const CARTESIA_API_KEY = defineSecret('CARTESIA_API_KEY');

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

function sendJson(res, status, body) {
  res.set(CORS_HEADERS).status(status).json(body);
}

function handleOptions(req, res) {
  if (req.method === 'OPTIONS') {
    res.set(CORS_HEADERS).status(204).send('');
    return true;
  }
  return false;
}

async function requireUser(req) {
  const header = req.get('Authorization') || '';
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) {
    const err = new Error('Missing Firebase ID token.');
    err.status = 401;
    throw err;
  }
  return admin.auth().verifyIdToken(match[1]);
}

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function userTokenRef(uid) {
  return admin.firestore().collection('users').doc(uid).collection('private').doc('googleTokens');
}

function oauthClient() {
  return new google.auth.OAuth2(
    process.env.GOOGLE_OAUTH_CLIENT_ID || '',
    process.env.GOOGLE_OAUTH_CLIENT_SECRET || '',
    'postmessage'
  );
}

async function loadGoogleClient(uid) {
  const snap = await userTokenRef(uid).get();
  if (!snap.exists) {
    return null;
  }
  const auth = oauthClient();
  auth.setCredentials(snap.data().tokens || {});
  return auth;
}

function wantsConfirmedCreateDoc(message) {
  return /^confirm\s+create\s+(?:a\s+)?google\s+doc\b/i.test(message);
}

function docTitleFrom(message) {
  const match = message.match(/(?:title|called|named)\s+([^\n.]+)/i);
  if (match) {
    return match[1].trim().replace(/^['"]|['"]$/g, '').slice(0, 120) || 'Home Center Note';
  }
  return 'Home Center Note';
}

async function createGoogleDoc(uid, message) {
  const auth = await loadGoogleClient(uid);
  if (!auth) {
    return {reply: 'Google Drive is not connected yet. Drew needs to reconnect Google with full Drive access before I can create or read files.', status: 'google_tools_missing'};
  }
  const docs = google.docs({version: 'v1', auth});
  const drive = google.drive({version: 'v3', auth});
  const title = docTitleFrom(message);
  const created = await docs.documents.create({requestBody: {title}});
  const documentId = created.data.documentId;
  const bodyMatch = message.match(/(?:body|with)\s+([\s\S]+)/i);
  const body = bodyMatch ? bodyMatch[1].trim() : '';
  if (body) {
    await docs.documents.batchUpdate({
      documentId,
      requestBody: {requests: [{insertText: {location: {index: 1}, text: body}}]},
    });
  }
  const file = await drive.files.get({fileId: documentId, fields: 'webViewLink'});
  return {
    reply: `Created Google Doc: ${title}\n${file.data.webViewLink || ''}`.trim(),
    narration: `Created Google Doc ${title}.`,
    status: 'google_doc_created',
  };
}

async function askOpenAI(uid, body) {
  const message = safeText(body.message, 4000);
  const summary = safeText(body.summary, 4000);
  const transcript = safeText(body.transcript, 8000);
  const bucket = safeText(body.bucket, 120);
  const listName = safeText(body.listName, 120) || 'shopping';
  const input = [
    'You are Home Center, a cohesive voice-first life dashboard for a blind user.',
    'Use concise, actionable language. Prefer direct next actions over generic offers.',
    'Capabilities available through this app when configured: OpenAI GPT-5.5, hosted web search, full Google Drive plus Docs/Sheets/Gmail/Calendar/Contacts through server-side tokens, Home Center Firestore lists, TickTick fallback lists, and Cartesia narration. Do not claim Google Drive access unless a Google Drive probe confirms it.',
    'For external writes such as Google Docs, Gmail drafts/sends, Calendar creates, or list changes, ask for explicit confirmation unless the user already phrased the command with confirm.',
    'If you use web search, include a short source line or source names in the answer.',
    `Default Home Center bucket: ${bucket || 'not selected'}. Default list: ${listName}.`,
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Latest user request: ${message}`,
  ].filter(Boolean).join('\n\n');

  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${OPENAI_API_KEY.value()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-5.5',
      reasoning: {effort: 'medium'},
      text: {verbosity: 'low'},
      tools: [{type: 'web_search'}],
      input,
    }),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    return {
      reply: `GPT-5.5 gateway error: ${json.error?.message || response.statusText}`,
      status: `openai_http_${response.status}`,
      technicalDetails: JSON.stringify(json).slice(0, 1000),
    };
  }
  const reply = json.output_text || extractOutputText(json) || 'I did not get a useful GPT-5.5 response.';
  return {reply, narration: reply, status: 'gpt_5_5_complete'};
}

function extractOutputText(json) {
  const out = Array.isArray(json.output) ? json.output : [];
  const parts = [];
  for (const item of out) {
    const content = Array.isArray(item.content) ? item.content : [];
    for (const c of content) {
      if (typeof c.text === 'string') parts.push(c.text);
    }
  }
  return parts.join('\n').trim();
}

function extractJsonObject(text) {
  const raw = safeText(text, 20000);
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1] : raw;
  const start = candidate.indexOf('{');
  const stop = candidate.lastIndexOf('}');
  if (start < 0 || stop < start) {
    throw new Error(`Planner did not return JSON: ${raw.slice(0, 240)}`);
  }
  return JSON.parse(candidate.slice(start, stop + 1));
}


function toolByName(tools, name) {
  return tools.find((tool) => tool && tool.name === name) || null;
}

function messageConfirms(message) {
  return /(^|\b)confirm(?:ed|ing)?\b/i.test(message || '');
}

function quoteForConfirmation(value) {
  return String(value || '').trim().replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ');
}

function confirmationAction(toolName, args = {}) {
  if (toolName === 'drive.create_folder' || toolName === 'docs.create' || toolName === 'sheets.create' || toolName === 'lists.create' || toolName === 'lists.add_item') return 'create';
  if (toolName === 'drive.update_metadata' || toolName === 'docs.update' || toolName === 'sheets.update' || toolName === 'lists.update_item' || toolName === 'lists.mark_done' || toolName === 'lists.remove_item') return 'edit';
  if (toolName === 'gmail.send_email' || toolName === 'gmail.send_draft') return 'send';
  if (toolName === 'calendar.create_event') return 'create';
  if (toolName === 'calendar.update_event') return 'edit';
  if (toolName === 'calendar.respond_event') return 'respond';
  return 'confirm';
}

function confirmationTitle(toolName) {
  if (toolName === 'drive.create_folder') return 'Create Drive Folder';
  if (toolName === 'drive.update_metadata') return 'Edit Drive Item';
  if (toolName === 'docs.create') return 'Create Google Doc';
  if (toolName === 'docs.update') return 'Edit Google Doc';
  if (toolName === 'sheets.create') return 'Create Google Sheet';
  if (toolName === 'sheets.update') return 'Edit Google Sheet';
  if (toolName === 'gmail.send_email') return 'Send Email';
  if (toolName === 'gmail.send_draft') return 'Send Draft';
  if (toolName === 'calendar.create_event') return 'Create Calendar Event';
  if (toolName === 'calendar.update_event') return 'Edit Calendar Event';
  if (toolName === 'calendar.respond_event') return 'Respond To Calendar Event';
  return 'Confirm Action';
}

function confirmationSummary(toolName, args = {}) {
  const a = args || {};
  if (toolName === 'drive.create_folder') {
    return `Create Drive folder "${quoteForConfirmation(a.name || 'Untitled folder')}".`;
  }
  if (toolName === 'drive.update_metadata') {
    return `Edit Drive item ${quoteForConfirmation(a.name || a.fileId || 'selected file')}.`;
  }
  if (toolName === 'docs.create') {
    const title = quoteForConfirmation(a.title || 'Untitled Google Doc');
    const body = quoteForConfirmation(a.body || '');
    return body ? `Create "${title}" with the provided body.` : `Create "${title}".`;
  }
  if (toolName === 'docs.update') {
    const target = quoteForConfirmation(a.name || a.title || 'selected document');
    if (a.appendText) return `Append text to "${target}".`;
    if (a.replaceText) return `Replace matching text in "${target}".`;
    if (a.body) return `Replace the body of "${target}".`;
    return `Edit "${target}".`;
  }
  if (toolName === 'sheets.create') {
    return `Create Google Sheet "${quoteForConfirmation(a.title || 'Untitled sheet')}".`;
  }
  if (toolName === 'sheets.update') {
    return `Update Google Sheet range ${quoteForConfirmation(a.range || 'selected range')}.`;
  }
  if (toolName === 'gmail.send_email') {
    return `Send email to ${quoteForConfirmation(a.to)} about "${quoteForConfirmation(a.subject)}".`;
  }
  if (toolName === 'gmail.send_draft') {
    return `Send draft ${quoteForConfirmation(a.draftId)}.`;
  }
  if (toolName === 'calendar.create_event') {
    return `Create event "${quoteForConfirmation(a.title)}".`;
  }
  if (toolName === 'calendar.update_event') {
    return `Edit calendar event ${quoteForConfirmation(a.eventId)}.`;
  }
  if (toolName === 'calendar.respond_event') {
    return `RSVP ${quoteForConfirmation(a.responseStatus)} to calendar event ${quoteForConfirmation(a.eventId)}.`;
  }
  return 'Confirm this action.';
}

function pendingConfirmation(toolName, args) {
  return {
    toolName,
    arguments: args || {},
    action: confirmationAction(toolName, args),
    title: confirmationTitle(toolName),
    summary: confirmationSummary(toolName, args),
  };
}

function confirmationReply(toolName, args) {
  const action = confirmationAction(toolName, args);
  return `I can ${action} that. Say "confirm ${action}" or press Confirm.`;
}

function pendingConfirmationFromBody(body, tools) {
  const pending = body && typeof body.pendingConfirmation === 'object' ? body.pendingConfirmation : null;
  if (!pending || typeof pending.toolName !== 'string') return null;
  const tool = toolByName(tools, pending.toolName);
  if (!tool || !tool.confirmationRequired) return null;
  const args = pending.arguments && typeof pending.arguments === 'object' ? pending.arguments : {};
  return pendingConfirmation(pending.toolName, args);
}

function compactToolNames(tools) {
  return tools.map((tool) => tool && tool.name).filter(Boolean);
}

function buildToolTrace(body, tools, parsed, toolName, tool, confirmationRequested) {
  const trace = {
    prompt: safeText(body && body.message, 4000),
    workingMemory: body && typeof body.workingMemory === 'object' ? body.workingMemory : {},
    availableToolNames: compactToolNames(tools),
    availableToolsJson: JSON.stringify(tools).slice(0, 12000),
    parsedPlannerJson: parsed || null,
    requestedToolName: toolName || '',
    docsCreateAdvertised: !!toolByName(tools, 'docs.create'),
    requestedToolFound: !!tool,
    docsCreateWasRequested: toolName === 'docs.create',
    confirmationRequested: !!confirmationRequested,
  };
  console.log('agentToolTurn trace ' + JSON.stringify(trace));
  return trace;
}

function withTrace(body, response, trace) {
  if (!body || body.debugTrace !== true) return response;
  return Object.assign({}, response, {
    trace,
    technicalDetails: JSON.stringify(trace).slice(0, 12000),
  });
}

const UNRESOLVED_REFERENCE_LITERALS = new Set([
  'that document',
  'the document',
  'that file',
  'it',
  'the one',
  'the previous one',
  'the one you just created',
  'the thing we just made',
]);

function normalizedReferenceLiteral(value) {
  return String(value || '').trim().toLowerCase().replace(/^['"]|['"]$/g, '').replace(/\s+/g, ' ');
}

function containsUnresolvedReferenceLiteral(args) {
  if (!args || typeof args !== 'object') return false;
  const keys = ['name', 'title', 'fileName', 'folderName', 'subject'];
  return keys.some((key) => UNRESOLVED_REFERENCE_LITERALS.has(normalizedReferenceLiteral(args[key])));
}

function shouldFillResolvedValue(value) {
  return !value || UNRESOLVED_REFERENCE_LITERALS.has(normalizedReferenceLiteral(value));
}

function fillResolvedEntity(args, entity, idKey, nameKey) {
  if (!args || !entity || typeof entity !== 'object') return args;
  if (entity[idKey] && shouldFillResolvedValue(args[idKey])) args[idKey] = entity[idKey];
  if (entity.name && shouldFillResolvedValue(args.name)) args.name = entity.name;
  if (entity.title && shouldFillResolvedValue(args.title)) args.title = entity.title;
  if (entity[nameKey] && shouldFillResolvedValue(args[nameKey])) args[nameKey] = entity[nameKey];
  return args;
}

function resolveToolArgsFromWorkingMemory(body, toolName, args) {
  if (!args || typeof args !== 'object') return {};
  const memory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const hasLiteralReference = containsUnresolvedReferenceLiteral(args);
  if (toolName && toolName.startsWith('docs.') && memory.lastDocument) {
    if (hasLiteralReference || args.fileId === memory.lastDocument.fileId || args.documentId === memory.lastDocument.fileId) {
      fillResolvedEntity(args, memory.lastDocument, 'fileId', 'name');
      if (memory.lastDocument.fileId && !args.documentId) args.documentId = memory.lastDocument.fileId;
    }
  }
  if (toolName && toolName.startsWith('drive.') && memory.lastFolder) {
    const targetKeys = ['folderName', 'name', 'title'];
    const referencesFolder = targetKeys.some((key) => UNRESOLVED_REFERENCE_LITERALS.has(normalizedReferenceLiteral(args[key])));
    if (referencesFolder || args.addParentId === memory.lastFolder.fileId || args.parentId === memory.lastFolder.fileId || args.folderId === memory.lastFolder.fileId) {
      if (memory.lastFolder.fileId && !args.addParentId && toolName === 'drive.update_metadata') args.addParentId = memory.lastFolder.fileId;
      if (memory.lastFolder.fileId && !args.folderId) args.folderId = memory.lastFolder.fileId;
      if (memory.lastFolder.name && !args.folderName) args.folderName = memory.lastFolder.name;
    }
  }
  if (toolName && toolName.startsWith('sheets.') && memory.lastSheet) {
    if (hasLiteralReference || args.fileId === memory.lastSheet.fileId || args.spreadsheetId === memory.lastSheet.fileId) {
      fillResolvedEntity(args, memory.lastSheet, 'fileId', 'name');
      if (memory.lastSheet.fileId && !args.spreadsheetId) args.spreadsheetId = memory.lastSheet.fileId;
    }
  }
  if (toolName && toolName.startsWith('gmail.') && memory.lastEmailDraft) {
    const referencesDraft = UNRESOLVED_REFERENCE_LITERALS.has(normalizedReferenceLiteral(args.subject));
    if (referencesDraft || args.draftId === memory.lastEmailDraft.draftId) {
      if (memory.lastEmailDraft.draftId && !args.draftId) args.draftId = memory.lastEmailDraft.draftId;
      if (memory.lastEmailDraft.subject && !args.subject) args.subject = memory.lastEmailDraft.subject;
    }
  }
  if (toolName && toolName.startsWith('calendar.') && memory.lastCalendarEvent) {
    if (hasLiteralReference || args.eventId === memory.lastCalendarEvent.eventId) {
      if (memory.lastCalendarEvent.eventId && !args.eventId) args.eventId = memory.lastCalendarEvent.eventId;
      if (memory.lastCalendarEvent.title && !args.title) args.title = memory.lastCalendarEvent.title;
    }
  }
  if (toolName && toolName.startsWith('contacts.') && memory.lastContact) {
    if (hasLiteralReference || args.email === memory.lastContact.primaryEmail) {
      if (memory.lastContact.displayName && !args.name) args.name = memory.lastContact.displayName;
      if (memory.lastContact.primaryEmail && !args.email) args.email = memory.lastContact.primaryEmail;
      if (memory.lastContact.resourceName && !args.resourceName) args.resourceName = memory.lastContact.resourceName;
    }
  }
  return args;
}

function clarificationForUnresolvedReference(body, toolName, args) {
  if (!containsUnresolvedReferenceLiteral(args)) return null;
  const memory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const hasCompatibleMemory =
    (toolName && toolName.startsWith('docs.') && memory.lastDocument && memory.lastDocument.fileId) ||
    (toolName && toolName.startsWith('drive.') && memory.lastFolder && memory.lastFolder.fileId) ||
    (toolName && toolName.startsWith('sheets.') && memory.lastSheet && memory.lastSheet.fileId) ||
    (toolName && toolName.startsWith('gmail.') && memory.lastEmailDraft && memory.lastEmailDraft.draftId) ||
    (toolName && toolName.startsWith('calendar.') && memory.lastCalendarEvent && memory.lastCalendarEvent.eventId) ||
    (toolName && toolName.startsWith('contacts.') && memory.lastContact && memory.lastContact.primaryEmail);
  if (hasCompatibleMemory) return null;
  return 'Which item do you mean?';
}

function numberWordToInt(value) {
  const normalized = String(value || '').toLowerCase();
  const words = {
    one: 1,
    two: 2,
    three: 3,
    four: 4,
    five: 5,
    six: 6,
    seven: 7,
    eight: 8,
    nine: 9,
    ten: 10,
    eleven: 11,
    twelve: 12,
    thirteen: 13,
    fourteen: 14,
    fifteen: 15,
    twenty: 20,
    thirty: 30,
    forty: 40,
    fifty: 50,
    sixty: 60,
  };
  if (/^\d+$/.test(normalized)) return Number(normalized);
  return words[normalized] || 0;
}

function pad2(value) {
  return String(value).padStart(2, '0');
}

function formatIsoWithOffset(epochMillis, offsetMillis) {
  const local = new Date(epochMillis + offsetMillis);
  const sign = offsetMillis >= 0 ? '+' : '-';
  const absolute = Math.abs(offsetMillis);
  const offsetHours = Math.floor(absolute / 3600000);
  const offsetMinutes = Math.floor((absolute % 3600000) / 60000);
  return `${local.getUTCFullYear()}-${pad2(local.getUTCMonth() + 1)}-${pad2(local.getUTCDate())}T${pad2(local.getUTCHours())}:${pad2(local.getUTCMinutes())}:${pad2(local.getUTCSeconds())}${sign}${pad2(offsetHours)}:${pad2(offsetMinutes)}`;
}

function timeContextFromBody(body) {
  const context = body && typeof body.timeContext === 'object' ? body.timeContext : {};
  const now = Number(context.nowEpochMillis);
  return {
    nowEpochMillis: Number.isFinite(now) && now > 0 ? now : Date.now(),
    timeZoneId: safeText(context.timeZoneId || 'local', 120),
    timeZoneOffsetMillis: Number.isFinite(Number(context.timeZoneOffsetMillis)) ? Number(context.timeZoneOffsetMillis) : 0,
    nowIso: safeText(context.nowIso || '', 80),
  };
}

function relativeOffsetMillis(value) {
  const text = normalizedReferenceLiteral(value).replace(/[.!?]+$/g, '').replace(/\ba\b/g, 'one');
  if (text === 'now' || text === 'right now') return 0;
  const match = text.match(/^(?:in\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty)\s*(minute|minutes|min|mins|hour|hours|hr|hrs|day|days)(?:\s+from\s+now)?$/);
  if (!match) return null;
  const amount = numberWordToInt(match[1]);
  if (!amount) return null;
  const unit = match[2];
  if (unit.startsWith('min')) return amount * 60000;
  if (unit.startsWith('h')) return amount * 3600000;
  if (unit.startsWith('day')) return amount * 86400000;
  return null;
}

function looksAbsoluteCalendarTime(value) {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(String(value || ''));
}

function resolveCalendarRelativeTimesFromContext(body, toolName, args) {
  if (!toolName || !toolName.startsWith('calendar.') || !args || typeof args !== 'object') return args;
  const context = timeContextFromBody(body);
  let resolvedStart = false;
  const startOffset = relativeOffsetMillis(args.startTime);
  if (startOffset !== null) {
    const startMs = context.nowEpochMillis + startOffset;
    args.startTime = formatIsoWithOffset(startMs, context.timeZoneOffsetMillis);
    resolvedStart = true;
  }
  const endOffset = relativeOffsetMillis(args.endTime);
  if (endOffset !== null) {
    args.endTime = formatIsoWithOffset(context.nowEpochMillis + endOffset, context.timeZoneOffsetMillis);
  }
  if ((toolName === 'calendar.create_event' || toolName === 'calendar.update_event') && resolvedStart && !looksAbsoluteCalendarTime(args.endTime)) {
    const defaultDurationMillis = /notification|reminder|alert/i.test(`${args.title || ''} ${args.description || ''}`) ? 15 * 60000 : 30 * 60000;
    args.endTime = formatIsoWithOffset(Date.parse(args.startTime) + defaultDurationMillis, context.timeZoneOffsetMillis);
  }
  return args;
}

async function askOpenAIToolTurn(body) {
  const message = safeText(body.message, 4000);
  const summary = safeText(body.summary, 4000);
  const transcript = safeText(body.transcript, 8000);
  const toolResults = Array.isArray(body.toolResults) ? body.toolResults.slice(0, 8) : [];
  const tools = Array.isArray(body.tools) ? body.tools : [];
  const unavailableToolGroups = Array.isArray(body.unavailableToolGroups) ? body.unavailableToolGroups : [];
  const workingMemory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const timeContext = timeContextFromBody(body);
  const pending = pendingConfirmationFromBody(body, tools);
  if (pending && messageConfirms(message)) {
    pending.arguments._confirmedByGateway = true;
    const trace = buildToolTrace(body, tools, {type: 'tool_call', toolName: pending.toolName, arguments: pending.arguments, source: 'pending_confirmation'}, pending.toolName, toolByName(tools, pending.toolName), false);
    return withTrace(body, {
      type: 'tool_call',
      toolName: pending.toolName,
      arguments: pending.arguments,
      status: 'tool_call_requested',
    }, trace);
  }
  const input = [
    'You are Home Center. You are the thinker. The Android app is only your hands.',
    'Return one strict JSON object and no prose outside JSON.',
    'If a needed capability appears in the available tools JSON, request that tool. Do not say you cannot do it.',
    'Working memory JSON contains recently created or selected entities. Inspect it before selecting a tool.',
    'If the user says it, that document, that file, the one you just created, the previous one, or similar, resolve the reference from workingMemory or recent tool results before calling a tool.',
    'Never use phrases like that document, the document, that file, it, the one, or the thing we just made as literal tool argument names or titles. Resolve them to IDs/names or ask which item the user means.',
    'When resolving a remembered document, include both fileId and name in the tool arguments so confirmation cards can show the real document name.',
    'Google Docs rule: for a request to create a Google Doc, call docs.create with title and body. Do not call Drive tools for document content.',
    'Google Docs rule: for a request to read or edit a Google Doc, use docs.search if needed, then docs.read or docs.update.',
    'Google Sheets rule: for spreadsheet creation or cell edits, use sheets.create, sheets.search, sheets.read, or sheets.update.',
    'Drive rule: use drive.* only for file and folder metadata, folder creation, rename, and move.',
    'Calendar time rule: timeContext is the device clock. Resolve relative times like five minutes from now, in 2 hours, tomorrow, or later today into absolute RFC3339 dateTime strings before calling calendar tools.',
    'Calendar time rule: do not ask for an exact time when the user already gave a relative time and timeContext is present. Compute it. If an event has startTime but no endTime, use 15 minutes for reminders/notifications and 30 minutes for ordinary events.',
    'Contacts rule: if the user names a person from contacts, call contacts.search with that name. Do not ask for an email address while contacts.search is available.',
    'Contacts plus Calendar rule: to add a named contact to an event, search contacts first, use the contact primaryEmail, resolve the target event from workingMemory or calendar.search/read, then call calendar.update_event with attendeesToAdd.',
    'Public web rule: you also have OpenAI web_search for public web pages, including public GitHub repositories. Use web_search for public GitHub repo questions, README discovery, file discovery, and public documentation lookup.',
    'Do not claim a GitHub tool is required for public GitHub repositories. A GitHub tool is only required for private repo access, authenticated GitHub writes, issues, pull requests, or repository mutations.',
    'If a needed app-owned capability is absent, explain the missing capability group from unavailableToolGroups and ask the user to reconnect Google if scopes are missing.',
    'If a tool succeeds but does not fully answer the user request, continue with another tool call. A successful tool call is not a final answer unless it satisfies the request.',
    'Hide plumbing. Do not mention tokens, HTTP, file IDs, scopes, timestamps, or diagnostics unless the user explicitly asks for diagnostics.',
    'Writes with confirmationRequired=true may be requested as tool calls; the gateway will enforce confirmation. Do not invent unsupported delete tools.',
    'JSON schema for tool call: {"type":"tool_call","toolName":"tool.name","arguments":{}}',
    'JSON schema for final answer: {"type":"final","reply":"...","narration":"...","status":"gpt_5_5_complete"}',
    'Set narration to the same text as reply. The app must not speak a short alternate summary that differs from the visible answer.',
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Available tools JSON: ${JSON.stringify(tools).slice(0, 12000)}`,
    `Unavailable tool groups JSON: ${JSON.stringify(unavailableToolGroups).slice(0, 4000)}`,
    `Working memory JSON: ${JSON.stringify(workingMemory).slice(0, 6000)}`,
    `Time context JSON: ${JSON.stringify(timeContext).slice(0, 2000)}`,
    toolResults.length ? `Tool results JSON: ${JSON.stringify(toolResults).slice(0, 16000)}` : 'Tool results JSON: []',
    pending ? `Pending confirmation JSON: ${JSON.stringify(pending).slice(0, 4000)}` : '',
    `Latest user request: ${message}`,
  ].filter(Boolean).join('\n\n');

  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${OPENAI_API_KEY.value()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-5.5',
      reasoning: {effort: 'medium'},
      text: {verbosity: 'low'},
      tools: [{type: 'web_search'}],
      input,
    }),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    return {
      type: 'final',
      reply: `GPT-5.5 gateway error: ${json.error?.message || response.statusText}`,
      narration: 'GPT-5.5 gateway error.',
      status: `openai_http_${response.status}`,
      technicalDetails: JSON.stringify(json).slice(0, 1000),
    };
  }
  const text = json.output_text || extractOutputText(json) || '';
  try {
    const parsed = extractJsonObject(text);
    if (parsed.type === 'tool_call') {
      const toolName = safeText(parsed.toolName || parsed.name, 80);
      const tool = toolByName(tools, toolName);
      const args = parsed.arguments && typeof parsed.arguments === 'object' ? parsed.arguments : {};
      resolveToolArgsFromWorkingMemory(body, toolName, args);
      resolveCalendarRelativeTimesFromContext(body, toolName, args);
      const unresolvedReferenceReply = clarificationForUnresolvedReference(body, toolName, args);
      if (unresolvedReferenceReply) {
        const trace = buildToolTrace(body, tools, parsed, toolName, tool, false);
        return withTrace(body, {
          type: 'final',
          reply: unresolvedReferenceReply,
          narration: unresolvedReferenceReply,
          status: 'reference_unresolved',
        }, trace);
      }
      if (!tool) {
        const trace = buildToolTrace(body, tools, parsed, toolName, tool, false);
        return withTrace(body, {
          type: 'final',
          reply: `That tool is not available in this session: ${toolName}. Reconnect Google if this is a missing Google capability.`,
          narration: `That tool is not available in this session.`,
          status: 'tool_unavailable',
        }, trace);
      }
      if (tool.confirmationRequired && !messageConfirms(message)) {
        const reply = confirmationReply(toolName, args);
        const trace = buildToolTrace(body, tools, parsed, toolName, tool, true);
        return withTrace(body, {
          type: 'final',
          reply,
          narration: reply,
          status: 'confirmation_required',
          pendingConfirmation: pendingConfirmation(toolName, args),
        }, trace);
      }
      if (tool.confirmationRequired) {
        args._confirmedByGateway = true;
      }
      const trace = buildToolTrace(body, tools, parsed, toolName, tool, false);
      return withTrace(body, {
        type: 'tool_call',
        toolName,
        arguments: args,
        status: 'tool_call_requested',
      }, trace);
    }
    const trace = buildToolTrace(body, tools, parsed, safeText(parsed.toolName || parsed.name, 80), toolByName(tools, safeText(parsed.toolName || parsed.name, 80)), false);
    return withTrace(body, {
      type: 'final',
      reply: safeText(parsed.reply || parsed.text, 12000) || 'I did not get a useful GPT-5.5 response.',
      narration: safeText(parsed.reply || parsed.text, 12000),
      status: safeText(parsed.status, 160) || 'gpt_5_5_complete',
    }, trace);
  } catch (err) {
    return {
      type: 'final',
      reply: text || `Planner failed: ${err.message}`,
      narration: text || 'Planner failed.',
      status: 'planner_json_error',
      technicalDetails: String(err.message || err).slice(0, 1000),
    };
  }
}


exports.health = onRequest((req, res) => {
  res.set(CORS_HEADERS).json({ok: true, service: 'home-center-gateway', confirmationFlow: 'short-confirm-v1', toolContractVersion: 'google-cru-v1', contractGroups: ['drive', 'docs', 'sheets', 'lists', 'gmail', 'calendar', 'contacts']});
});

exports.googleAuthCodeExchange = onRequest(async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireUser(req);
    if (!process.env.GOOGLE_OAUTH_CLIENT_ID || !process.env.GOOGLE_OAUTH_CLIENT_SECRET) {
      sendJson(res, 503, {error: 'Google tools are not connected by the owner yet'});
      return;
    }
    const authCode = safeText(req.body && req.body.authCode, 4096);
    if (!authCode) {
      sendJson(res, 400, {error: 'authCode is required'});
      return;
    }
    const client = oauthClient();
    const {tokens} = await client.getToken(authCode);
    await userTokenRef(user.uid).set({tokens, updatedAt: admin.firestore.FieldValue.serverTimestamp()}, {merge: true});
    sendJson(res, 200, {ok: true, status: 'google_tools_connected'});
  } catch (err) {
    sendJson(res, err.status || 500, {error: err.message || String(err)});
  }
});

function isInsufficientDriveScope(err) {
  const code = err && (err.code || err.status);
  const message = String((err && err.message) || err || '').toLowerCase();
  return code === 403 || message.includes('insufficient') || message.includes('permission') || message.includes('scope');
}

function driveQueryFrom(text) {
  const value = safeText(text, 300).toLowerCase();
  if (value.includes('brain')) {
    return "mimeType='application/vnd.google-apps.folder' and name contains 'brain' and trashed=false";
  }
  return "trashed=false";
}

exports.googleDriveProbe = onRequest(async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireUser(req);
    const auth = await loadGoogleClient(user.uid);
    if (!auth) {
      sendJson(res, 200, {
        reply: 'No. Google Drive is not connected yet.\n\nI can still help with Home Center lists, TickTick fallback, GPT answers, web search, and narration.\n\nI will not claim I can read, open, list, or change Google files until Drew connects full Google Drive access.',
        narration: 'Google Drive is not connected yet.',
        status: 'google_drive_missing',
      });
      return;
    }
    const drive = google.drive({version: 'v3', auth});
    const query = driveQueryFrom(req.body && req.body.query);
    const result = await drive.files.list({
      q: query,
      pageSize: 5,
      fields: 'files(id,name,mimeType,modifiedTime,webViewLink)',
      orderBy: 'modifiedTime desc',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
    });
    const files = result.data.files || [];
    const names = files.map((file) => file.name).filter(Boolean);
    const suffix = names.length ? ` I found: ${names.join(', ')}.` : ' I did not find matching files in the first Drive probe.';
    sendJson(res, 200, {
      reply: `Yes. Google Drive is connected with full Drive access.${suffix}`,
      narration: names.length ? `Google Drive is connected. I found ${names[0]}.` : 'Google Drive is connected.',
      status: 'google_drive_connected',
      files,
    });
  } catch (err) {
    if (isInsufficientDriveScope(err)) {
      sendJson(res, 200, {
        reply: 'Google Drive is connected, but not with full Drive access yet. Drew needs to reconnect Google with full Drive permission before I can manage Drive files.',
        narration: 'Google Drive needs full access before I can manage files.',
        status: 'google_drive_scope_insufficient',
        technicalDetails: String(err.message || err).slice(0, 500),
      });
      return;
    }
    sendJson(res, err.status || 500, {reply: `Google Drive check failed: ${err.message || String(err)}`, status: 'google_drive_probe_error'});
  }
});


exports.agentToolTurn = onRequest({timeoutSeconds: 120, secrets: [OPENAI_API_KEY]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    await requireUser(req);
    const message = safeText(req.body && req.body.message, 4000);
    if (!message) {
      sendJson(res, 400, {type: 'final', reply: 'Tell me what you want Home Center to do.', status: 'missing_message'});
      return;
    }
    sendJson(res, 200, await askOpenAIToolTurn(req.body || {}));
  } catch (err) {
    sendJson(res, err.status || 500, {type: 'final', reply: `Gateway failed: ${err.message || String(err)}`, status: 'gateway_error'});
  }
});

exports.agentTurn = onRequest({timeoutSeconds: 120, secrets: [OPENAI_API_KEY]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireUser(req);
    const message = safeText(req.body && req.body.message, 4000);
    if (!message) {
      sendJson(res, 400, {reply: 'Tell me what you want Home Center to do.', status: 'missing_message'});
      return;
    }
    sendJson(res, 200, await askOpenAI(user.uid, req.body || {}));
  } catch (err) {
    sendJson(res, err.status || 500, {reply: `Gateway failed: ${err.message || String(err)}`, status: 'gateway_error'});
  }
});

async function synthesizeCartesia(text) {
  const response = await fetch('https://api.cartesia.ai/tts/bytes', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${CARTESIA_API_KEY.value()}`,
      'Cartesia-Version': '2024-06-10',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model_id: 'sonic-3.5',
      transcript: text,
      voice: {mode: 'id', id: process.env.CARTESIA_VOICE_ID || 'f786b574-daa5-4673-aa0c-cbe3e8534c02'},
      output_format: {container: 'raw', encoding: 'pcm_s16le', sample_rate: 44100},
    }),
  });
  if (!response.ok) {
    throw new Error(`Cartesia HTTP ${response.status}`);
  }
  return Buffer.from(await response.arrayBuffer());
}

async function ttsHandler(req, res) {
  if (handleOptions(req, res)) return;
  try {
    const text = safeText(req.body && req.body.text, 1200);
    if (!text) {
      res.set(CORS_HEADERS).status(400).send('text is required');
      return;
    }
    const audio = await synthesizeCartesia(text);
    res.set(CORS_HEADERS);
    res.set('Content-Type', 'application/octet-stream');
    res.status(200).send(audio);
  } catch (err) {
    res.set(CORS_HEADERS).status(500).send(err.message || String(err));
  }
}

exports.tts = onRequest({timeoutSeconds: 60, secrets: [CARTESIA_API_KEY]}, ttsHandler);
exports.speak = onRequest({timeoutSeconds: 60, secrets: [CARTESIA_API_KEY]}, ttsHandler);
