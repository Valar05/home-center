const {onRequest} = require('firebase-functions/v2/https');
const {defineSecret} = require('firebase-functions/params');
const admin = require('firebase-admin');
const {google} = require('googleapis');
const crypto = require('crypto');

admin.initializeApp();

const OPENAI_API_KEY = defineSecret('OPENAI_API_KEY');
const CARTESIA_API_KEY = defineSecret('CARTESIA_API_KEY');
const GITHUB_TOKEN = defineSecret('GITHUB_TOKEN');
const GOOGLE_OAUTH_CLIENT_ID = defineSecret('GOOGLE_OAUTH_CLIENT_ID');
const GOOGLE_OAUTH_CLIENT_SECRET = defineSecret('GOOGLE_OAUTH_CLIENT_SECRET');
const CREATIVE_OPENAI_TIMEOUT_MS = 85000;
const CREATIVE_SALVAGE_TIMEOUT_MS = 25000;
const EVIDENCE_FINALIZER_TIMEOUT_MS = 45000;
const EVIDENCE_FINALIZER_REPAIR_TIMEOUT_MS = 12000;
const FINAL_REPLY_MAX_CHARS = 32000;

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

async function requireSmokeUser(req) {
  const header = req.get('Authorization') || '';
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) {
    const err = new Error('Missing Firebase ID token or Google access token.');
    err.status = 401;
    throw err;
  }
  const token = match[1];
  try {
    return await admin.auth().verifyIdToken(token);
  } catch (_) {
    const response = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
      headers: {Authorization: `Bearer ${token}`},
    });
    const text = await response.text();
    let profile = {};
    try {
      profile = text ? JSON.parse(text) : {};
    } catch (err) {
      profile = {};
    }
    if (!response.ok) {
      const err = new Error(`Google token verification failed: HTTP ${response.status} ${text.slice(0, 300)}`);
      err.status = 401;
      throw err;
    }
    const email = safeText(profile.email, 320);
    if (!email || profile.email_verified === false) {
      const err = new Error('Google token did not include a verified email.');
      err.status = 401;
      throw err;
    }
    try {
      const user = await admin.auth().getUserByEmail(email);
      return {uid: user.uid, email};
    } catch (err) {
      return {uid: '', email};
    }
  }
}

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function shouldEnableWebSearch(message, body = {}) {
  if (body && body.forceWebSearch === true) return true;
  const text = safeText(message, 4000).toLowerCase();
  return /\b(web|search the web|internet|online|latest|current|today|news|public github|github\.com|raw\.githubusercontent\.com|repo|repository|readme|documentation|docs site|website|url|http:\/\/|https:\/\/)\b/.test(text);
}

function economyToolPalette(message, tools, workingMemory = {}, toolResults = []) {
  if (!Array.isArray(tools) || tools.length === 0) return [];
  const text = safeText(message, 4000).toLowerCase();
  const groups = new Set();
  const add = (group) => groups.add(group);
  const has = (pattern) => pattern.test(text);

  if (has(/\b(report|file an issue|save this bug|feedback|send this to github|this is broken|that was wrong|bug)\b/)) add('github');
  if (has(/\b(doc|document|google doc|drive|file|folder|upload|attach|attachment|writing folder|read the first sentence|append|replace the body|open)\b/)) {
    add('drive');
    add('docs');
  }
  if (has(/\b(sheet|spreadsheet|cell|range|tab)\b/)) {
    add('drive');
    add('sheets');
  }
  if (has(/\b(email|mail|gmail|draft|send|inbox|message)\b/)) {
    add('gmail');
    add('contacts');
  }
  if (has(/\b(calendar|event|meeting|appointment|reminder|rsvp|invite|attendee|attendees|minutes from now|hours from now|tomorrow|next week)\b/)) {
    add('calendar');
    add('contacts');
  }
  if (has(/\b(contact|contacts|phone number|email address)\b/)) add('contacts');
  if (has(/\b(list|shopping|grocery|groceries|cart|walmart|preference|sku|done|cross off|mark done)\b/)) add('lists');
  if (has(/\b(remember|save this|make durable|workflow|workaround|skill|skills\.md|agents\.md|memory\.md|doctrine|stored memory|knowledge)\b/)) add('knowledge');
  if (has(/\b(write|draft|compose|continue|narrate|expand|generate|tell|simulate|scene|story|chapter|prose|dialogue)\b/)) {
    add('docs');
    add('knowledge');
  }
  if (workingMemory && typeof workingMemory === 'object') {
    if (workingMemory.lastDocument || workingMemory.rememberedWritingContext) {
      add('docs');
      add('knowledge');
    }
    if (workingMemory.lastCalendarEvent) add('calendar');
    if (workingMemory.lastEmailDraft) add('gmail');
    if (Array.isArray(workingMemory.attachedFiles) && workingMemory.attachedFiles.length) {
      add('drive');
      add('docs');
    }
  }
  if (Array.isArray(toolResults) && toolResults.length) {
    const latest = toolResults[toolResults.length - 1] || {};
    const name = safeText(latest.name, 120);
    if (name.includes('.')) add(name.split('.')[0]);
  }
  if (groups.size === 0) return [];
  return tools.filter((tool) => tool && groups.has(tool.group));
}

function shouldIncludeFullDoctrine(message, body = {}) {
  const text = safeText(message, 4000).toLowerCase();
  if (body && body.forceFullDoctrine === true) return true;
  return /\b(doctrine|agent behavior|steering|instructions|memory\.md|agents\.md|skills\.md|debug|diagnostic|report|feedback|bug|issue|why did|what happened)\b/.test(text);
}

function shouldIncludeEvidenceContext(message, body = {}, pending = null, toolResults = []) {
  const text = safeText(message, 4000).toLowerCase();
  if (body && body.forceEvidenceContext === true) return true;
  if (pending) return true;
  if (/\b(report|file an issue|save this bug|feedback|send this to github|this is broken|that was wrong|debug|diagnostic|what happened|why did)\b/.test(text)) return true;
  return Array.isArray(toolResults) && toolResults.some((entry) => {
    const result = entry && typeof entry === 'object' ? entry.result : null;
    return result && result.ok === false;
  });
}

function isFeedbackReportRequest(message) {
  return /\b(report this|report a bug|file an issue|make a new ticket|save this bug|feedback|send this to github|this is broken|that was wrong)\b/i.test(safeText(message, 4000));
}

function unavailableGroupForTool(toolName, unavailableToolGroups) {
  const missingGroup = safeText(toolName, 120).includes('.') ? safeText(toolName, 120).split('.')[0] : '';
  if (!missingGroup || !Array.isArray(unavailableToolGroups)) return null;
  return unavailableToolGroups.find((group) => group && group.group === missingGroup) || null;
}

function toolExposureFailureReply(toolName, unavailableGroup) {
  const cleanTool = safeText(toolName, 120) || 'the requested tool';
  if (unavailableGroup) {
    const group = safeText(unavailableGroup.group, 80) || 'requested';
    const reason = safeText(unavailableGroup.reason, 200) || 'that capability group is not authorized in this session';
    return {
      type: 'final',
      reply: `I could not use ${cleanTool} because the ${group} capability is unavailable: ${reason}.\n\nSource: provider permission/setup.\n\nWorkaround: reconnect or enable the ${group} capability, then retry the same request.`,
      narration: `I could not use ${cleanTool} because the ${group} capability is unavailable.`,
      status: 'tool_unavailable_setup',
    };
  }
  return {
    type: 'final',
    reply: `I could not use ${cleanTool} because that tool is not exposed in this turn/session.\n\nSource: Home Center tool/session exposure problem, not a user reconnect or account setup problem.\n\nWorkaround: try once more. If it repeats, report this so Home Center can preserve the missing-tool evidence.`,
    narration: `I could not use ${cleanTool} because that tool is not exposed in this turn/session.`,
    status: 'tool_not_exposed',
  };
}

function reportIssueDraftFallback(body, reason) {
  const message = safeText(body && body.message, 4000);
  const evidence = body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {};
  const turns = Array.isArray(evidence.recentConversationEvidence) ? evidence.recentConversationEvidence.slice(-6) : [];
  const visible = safeText(evidence.lastVisibleStatus, 1000);
  const provider = safeText(evidence.providerStatus, 300);
  const versionName = safeText(evidence.versionName || evidence.appVersion || '', 80);
  const versionCode = safeText(String(evidence.versionCode || ''), 80);
  const summary = message ? message.replace(/\s+/g, ' ').slice(0, 120) : 'Home Center feedback';
  const conversation = turns.length
    ? turns.map((turn) => {
      const role = safeText(turn.role || turn.sender || 'unknown', 40);
      const text = safeText(turn.text || turn.message || turn.content || turn.visibleText || '', 2000);
      return `### ${role}\n\n${text || '(empty)'}`;
    }).join('\n\n')
    : '(No recent conversation evidence was available.)';
  const bodyText = [
    '## Summary',
    summary,
    '',
    '## User Report',
    message || '(No report text was captured.)',
    '',
    '## Conversation Evidence',
    conversation,
    '',
    '## Expected Behavior',
    'Home Center should complete the user request or report the exact missing tool/session exposure problem.',
    '',
    '## Actual Behavior',
    safeText(reason, 500) || 'GitHub issue creation was requested but github.create_issue was not exposed in this turn/session.',
    '',
    '## Suspected Area',
    'provider/gateway',
    '',
    '## Environment',
    `- app versionName: ${versionName || 'unknown'}`,
    `- versionCode: ${versionCode || 'unknown'}`,
    `- provider status: ${provider || 'unknown'}`,
    `- visible status: ${visible || 'unknown'}`,
  ].join('\n');
  return {
    type: 'final',
    reply: `I cannot create the GitHub issue from this turn because github.create_issue is not exposed in this session. This is a Home Center tool/session exposure problem, not evidence that GitHub needs to be enabled.\n\nHere is the issue draft:\n\nTitle: Bug: ${summary}\n\n${bodyText}`,
    narration: 'I cannot create the GitHub issue because the issue tool is not exposed in this session. I drafted the issue text instead.',
    status: 'github_issue_tool_not_exposed_draft',
    issueDraft: {
      repo: 'Valar05/home-center',
      title: `Bug: ${summary}`,
      body: bodyText,
      labels: ['bug', 'feedback', 'home-center'],
    },
  };
}

function compactPromptText(value, max) {
  return safeText(value, max);
}

function errorCategoryFrom(value) {
  const text = String(value || '').toLowerCase();
  if (text.includes('timeout') || text.includes('timed out') || text.includes('deadline')) return 'timeout';
  if (text.includes('fetch') || text.includes('network') || text.includes('econn') || text.includes('enotfound')) return 'network';
  if (text.includes('401') || text.includes('403') || text.includes('permission') || text.includes('scope') || text.includes('auth')) return 'authorization';
  if (text.includes('429') || text.includes('rate') || text.includes('quota')) return 'rate_limit';
  if (text.includes('json') || text.includes('parse') || text.includes('schema')) return 'planner_parse';
  if (text.includes('tool') || text.includes('unavailable')) return 'tool_contract';
  return 'provider';
}

function userFacingFailure(source, detail, status = 'agent_failure') {
  const cleanDetail = safeText(detail, 700) || 'No technical detail was returned.';
  const category = errorCategoryFrom(cleanDetail);
  const sourceLabel = source || 'agent';
  const workarounds = {
    timeout: 'Try again with the direct URL or a narrower request. If it repeats, ask me to file a bug and I will preserve the captured failure.',
    network: 'Try again, or provide the direct source URL/file name so I can avoid broad search.',
    authorization: 'Reconnect Google or the relevant provider, then retry the same request.',
    rate_limit: 'Wait a minute and retry. If the request is urgent, narrow it to one source or one action.',
    planner_parse: 'Say the request again more directly. If it repeats, report it as an agent parsing bug.',
    tool_contract: 'Ask for diagnostics or report the missing tool exposure. Reconnect only if diagnostics name a missing provider or scope.',
    provider: 'Retry once. If it repeats, ask me to file a bug so I can preserve the exact failure.',
  };
  return {
    type: 'final',
    reply: `I could not complete that because ${sourceLabel} hit a ${category.replace('_', ' ')} problem.\n\nWhat failed: ${cleanDetail}\n\nWorkaround: ${workarounds[category] || workarounds.provider}`,
    narration: `I could not complete that because ${sourceLabel} hit a ${category.replace('_', ' ')} problem. ${workarounds[category] || workarounds.provider}`,
    status,
    technicalDetails: cleanDetail,
    errorCategory: category,
    errorSource: sourceLabel,
  };
}


const HOME_CENTER_DOCTRINE_STEERING = [
  'Home Center doctrine: Home Center is a life-operations system, not a chatbot with extras.',
  'Doctrine: the model reasons, the app executes, the storage layer remembers, and validation proves what is real.',
  'Doctrine: reduce everyday cognitive load by turning tasks, calendar commitments, contacts, email, documents, research, household workflows, and memories into durable state and concrete next actions.',
  'Doctrine: use recent transcript, working memory, durable household/user state, source records, and promoted skills according to their proper lifetime and privacy boundary.',
  'Doctrine: Android owns capabilities and permissions; GPT owns judgment, tool choice, chaining, recovery, follow-up questions, and final answers.',
  'Doctrine: do not document or narrate plumbing when an action can be completed. Show accomplishment, ask only for missing details, and keep setup/diagnostics behind explicit need.',
  'Doctrine: external writes and irreversible actions require confirmation outside prompt prose; never imply a capability that is not advertised by the tool registry.',
].join('\n');

function userTokenRef(uid) {
  return admin.firestore().collection('users').doc(uid).collection('private').doc('googleTokens');
}

function googleEmailTokenRef(email) {
  return admin.firestore().collection('googleToolTokens').doc(String(email || '').trim().toLowerCase());
}

function oauthClient(redirectUri = 'postmessage') {
  return new google.auth.OAuth2(
    GOOGLE_OAUTH_CLIENT_ID.value() || process.env.GOOGLE_OAUTH_CLIENT_ID || '',
    GOOGLE_OAUTH_CLIENT_SECRET.value() || process.env.GOOGLE_OAUTH_CLIENT_SECRET || '',
    redirectUri
  );
}

async function storeGoogleToolTokens(uid, email, tokens, source) {
  const cleanEmail = safeText(email, 320).toLowerCase();
  const payload = {
    tokens,
    email: cleanEmail,
    source: safeText(source, 80) || 'unknown',
    updatedAt: admin.firestore.FieldValue.serverTimestamp(),
  };
  if (uid) {
    await userTokenRef(uid).set(payload, {merge: true});
  }
  if (cleanEmail) {
    await googleEmailTokenRef(cleanEmail).set(payload, {merge: true});
  }
}

async function loadGoogleClient(uid, email = '') {
  let snap = uid ? await userTokenRef(uid).get() : null;
  if ((!snap || !snap.exists) && email) {
    snap = await googleEmailTokenRef(email).get();
  }
  if (!snap || !snap.exists) {
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
    return {reply: 'Google Drive is not connected yet. Reconnect Google with full Drive access before I can create or read files.', status: 'google_tools_missing'};
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
  const summary = compactPromptText(body.summary, 1200);
  const transcript = compactPromptText(body.transcript, 2000);
  const bucket = safeText(body.bucket, 120);
  const listName = safeText(body.listName, 120) || 'shopping';
  const includeFullDoctrine = shouldIncludeFullDoctrine(message, body);
  const promptText = [
    'You are Home Center, a cohesive voice-first life dashboard for a blind user.',
    includeFullDoctrine ? HOME_CENTER_DOCTRINE_STEERING : 'Doctrine summary: Home Center reasons with GPT, executes through app-owned tools, hides plumbing, and asks for confirmation before external writes.',
    'Use concise, actionable language. Prefer direct next actions over generic offers.',
    'Capabilities available through this app when configured: OpenAI GPT-5.5, hosted web search, full Google Drive plus Docs/Sheets/Gmail/Calendar/Contacts through server-side tokens, Home Center Firestore lists, TickTick fallback lists, and Cartesia narration. Do not claim Google Drive access unless a Google Drive probe confirms it.',
    'For external writes such as Google Docs, Gmail drafts/sends, Calendar creates, or list changes, ask for explicit confirmation unless the user already phrased the command with confirm.',
    'If you use web search, include a short source line or source names in the answer.',
    `Default Home Center bucket: ${bucket || 'not selected'}. Default list: ${listName}.`,
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Latest user request: ${message}`,
  ].filter(Boolean).join('\n\n');
  const openAiTools = shouldEnableWebSearch(message, body) ? [{type: 'web_search'}] : [];

  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${OPENAI_API_KEY.value()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(Object.assign({
      model: 'gpt-5.5',
      reasoning: {effort: 'low'},
      text: {verbosity: 'low'},
      input: promptText,
    }, openAiTools.length ? {tools: openAiTools} : {})),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    return userFacingFailure('GPT-5.5 provider', json.error?.message || response.statusText || `HTTP ${response.status}`, `openai_http_${response.status}`);
  }
  const reply = json.output_text || extractOutputText(json) || 'GPT-5.5 returned an empty response. Please retry or say "report this" so I can file the captured failure.';
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
  const candidates = [raw];
  const fencePattern = /```(?:json)?\s*([\s\S]*?)```/ig;
  let fence;
  while ((fence = fencePattern.exec(raw)) !== null) {
    candidates.push(fence[1]);
  }
  for (const candidate of candidates) {
    const direct = candidate.trim();
    if (direct.startsWith('{') && direct.endsWith('}')) {
      try {
        return JSON.parse(direct);
      } catch (err) {
        // Recover below when the model adds prose after a valid tool JSON object.
      }
    }
    if (direct.startsWith('"') && direct.endsWith('"')) {
      try {
        const nested = JSON.parse(direct);
        if (typeof nested === 'string' && nested.trim() && nested !== direct) {
          return extractJsonObject(nested);
        }
      } catch (err) {
        // Recover below when the model double-encodes JSON as a quoted string.
      }
    }
    const recovered = findBalancedJsonObject(candidate);
    if (recovered) {
      return JSON.parse(recovered);
    }
    const salvaged = salvageTruncatedFinalJsonObject(candidate);
    if (salvaged) return salvaged;
  }
  throw new Error(`Planner did not return JSON: ${raw.slice(0, 240)}`);
}

function jsonStringFragment(text, key) {
  const raw = safeText(text, 20000);
  const marker = `"${key}":"`;
  const start = raw.indexOf(marker);
  if (start < 0) return '';
  let out = '';
  let escaped = false;
  for (let i = start + marker.length; i < raw.length; i += 1) {
    const ch = raw[i];
    if (escaped) {
      if (ch === 'n') out += '\n';
      else if (ch === 'r') out += '\r';
      else if (ch === 't') out += '\t';
      else if (ch === 'b') out += '\b';
      else if (ch === 'f') out += '\f';
      else if (ch === 'u' && /^[0-9a-fA-F]{4}$/.test(raw.slice(i + 1, i + 5))) {
        out += String.fromCharCode(parseInt(raw.slice(i + 1, i + 5), 16));
        i += 4;
      } else {
        out += ch;
      }
      escaped = false;
      continue;
    }
    if (ch === '\\') {
      escaped = true;
      continue;
    }
    if (ch === '"') return out;
    out += ch;
  }
  return out.trim() ? out : '';
}

function salvageTruncatedFinalJsonObject(text) {
  const raw = safeText(text, 20000).trim();
  if (!raw.includes('"type"') || !raw.includes('"final"') || !raw.includes('"reply"')) return null;
  const reply = jsonStringFragment(raw, 'reply');
  if (!reply.trim()) return null;
  const narration = jsonStringFragment(raw, 'narration') || reply;
  const status = jsonStringFragment(raw, 'status');
  return {
    type: 'final',
    reply,
    narration,
    status: status && status !== 'planner_json_error' ? status : '',
  };
}

function findBalancedJsonObject(text) {
  const raw = safeText(text, 20000);
  for (let start = raw.indexOf('{'); start >= 0; start = raw.indexOf('{', start + 1)) {
    let depth = 0;
    let inString = false;
    let escaped = false;
    for (let i = start; i < raw.length; i += 1) {
      const ch = raw[i];
      if (inString) {
        if (escaped) {
          escaped = false;
        } else if (ch === '\\') {
          escaped = true;
        } else if (ch === '"') {
          inString = false;
        }
        continue;
      }
      if (ch === '"') {
        inString = true;
      } else if (ch === '{') {
        depth += 1;
      } else if (ch === '}') {
        depth -= 1;
        if (depth === 0) {
          const candidate = raw.slice(start, i + 1);
          try {
            const parsed = JSON.parse(candidate);
            if (parsed && (parsed.type || parsed.toolName || parsed.name || parsed.reply || parsed.text)) {
              return candidate;
            }
          } catch (err) {
            break;
          }
        }
      }
    }
  }
  return '';
}

function looksLikeToolCallJson(text) {
  const raw = safeText(text, 20000);
  return raw.includes('"type"') && raw.includes('tool_call') && (raw.includes('"toolName"') || raw.includes('"name"'));
}

function plannerParseFailureReply(text, err) {
  const technicalDetails = String(err && err.message || err).slice(0, 1000);
  if (looksLikeToolCallJson(text)) {
    return {
      type: 'final',
      reply: 'I could not safely parse the tool request.\n\nWhat failed: GPT returned tool-call JSON that did not match the expected schema.\n\nWorkaround: say the request again more directly. If it repeats, say "report this" so I can file the exact agent parsing bug.',
      narration: 'I could not safely parse the tool request. Say the request again more directly.',
      status: 'planner_json_error',
      technicalDetails,
    };
  }
  const clean = safeText(text, 12000);
  if (clean) {
    return {
      type: 'final',
      reply: clean,
      narration: clean,
      status: 'planner_json_error',
      technicalDetails,
    };
  }
  return userFacingFailure('GPT-5.5 planner', technicalDetails, 'planner_json_error');
}


function toolByName(tools, name) {
  return tools.find((tool) => tool && tool.name === name) || null;
}

function messageConfirms(message) {
  return /(^|\b)confirm(?:ed|ing)?\b/i.test(message || '');
}

function messageCancels(message) {
  return /^\s*(cancel|never mind|nevermind|stop that|not that|wrong|no|nope)\s*[.!?]*\s*$/i.test(message || '');
}

function confirmationIdFor(toolName, args, confirmationStage = 1) {
  const canonical = JSON.stringify({
    toolName: safeText(toolName, 120),
    arguments: args || {},
    confirmationStage: Number(confirmationStage || 1),
  });
  return `confirm_${crypto.createHash('sha256').update(canonical).digest('hex').slice(0, 24)}`;
}

function quoteForConfirmation(value) {
  return String(value || '').trim().replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ');
}

function confirmationAction(toolName, args = {}) {
  if (toolName === 'drive.delete' || toolName === 'docs.delete' || toolName === 'sheets.delete' || toolName === 'gmail.trash' || toolName === 'calendar.delete_event' || toolName === 'lists.remove_item') return 'delete';
  if (toolName === 'drive.create_folder' || toolName === 'drive.upload_file' || toolName === 'docs.create' || toolName === 'sheets.create' || toolName === 'lists.create' || toolName === 'lists.add_item') return 'create';
  if (toolName === 'drive.update_metadata' || toolName === 'docs.update' || toolName === 'sheets.update' || toolName === 'lists.update_item' || toolName === 'lists.mark_done') return 'edit';
  if (toolName === 'gmail.send_email' || toolName === 'gmail.send_draft') return 'send';
  if (toolName === 'calendar.create_event') return 'create';
  if (toolName === 'calendar.update_event') return 'edit';
  if (toolName === 'calendar.respond_event') return 'respond';
  return 'confirm';
}

function confirmationTitle(toolName) {
  if (toolName === 'drive.create_folder') return 'Create Drive Folder';
  if (toolName === 'drive.update_metadata') return 'Edit Drive Item';
  if (toolName === 'drive.upload_file') return 'Upload File To Drive';
  if (toolName === 'drive.delete') return 'Delete Drive Item';
  if (toolName === 'docs.create') return 'Create Google Doc';
  if (toolName === 'docs.update') return 'Edit Google Doc';
  if (toolName === 'docs.delete') return 'Delete Google Doc';
  if (toolName === 'sheets.create') return 'Create Google Sheet';
  if (toolName === 'sheets.update') return 'Edit Google Sheet';
  if (toolName === 'sheets.delete') return 'Delete Google Sheet';
  if (toolName === 'github.create_issue') return 'Create GitHub Issue';
  if (toolName === 'gmail.send_email') return 'Send Email';
  if (toolName === 'gmail.send_draft') return 'Send Draft';
  if (toolName === 'gmail.trash') return 'Delete Gmail Message';
  if (toolName === 'calendar.create_event') return 'Create Calendar Event';
  if (toolName === 'calendar.update_event') return 'Edit Calendar Event';
  if (toolName === 'calendar.respond_event') return 'Respond To Calendar Event';
  if (toolName === 'calendar.delete_event') return 'Delete Calendar Event';
  if (toolName === 'lists.remove_item') return 'Remove List Item';
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
  if (toolName === 'drive.upload_file') {
    return `Upload "${quoteForConfirmation(a.name || a.displayName || a.sessionFileId || 'attached file')}" to Google Drive.`;
  }
  if (toolName === 'drive.delete') {
    return `Move Drive item "${quoteForConfirmation(a.name || a.fileId || 'selected file')}" to trash. This requires two confirmations.`;
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
  if (toolName === 'docs.delete') {
    return `Move Google Doc "${quoteForConfirmation(a.name || a.title || 'selected document')}" to trash. This requires two confirmations.`;
  }
  if (toolName === 'sheets.create') {
    return `Create Google Sheet "${quoteForConfirmation(a.title || 'Untitled sheet')}".`;
  }
  if (toolName === 'sheets.update') {
    return `Update Google Sheet range ${quoteForConfirmation(a.range || 'selected range')}.`;
  }
  if (toolName === 'sheets.delete') {
    return `Move Google Sheet "${quoteForConfirmation(a.title || a.name || a.spreadsheetId || 'selected sheet')}" to trash. This requires two confirmations.`;
  }
  if (toolName === 'github.create_issue') {
    const title = quoteForConfirmation(a.title || 'Bug: Home Center feedback');
    return `${title}\n\nThis will include the last few chat messages and app context.`;
  }
  if (toolName === 'gmail.send_email') {
    return `Send email to ${quoteForConfirmation(a.to)} about "${quoteForConfirmation(a.subject)}".`;
  }
  if (toolName === 'gmail.send_draft') {
    return `Send draft ${quoteForConfirmation(a.draftId)}.`;
  }
  if (toolName === 'gmail.trash') {
    return `Move Gmail message "${quoteForConfirmation(a.subject || a.messageId || 'selected message')}" to trash. This requires two confirmations.`;
  }
  if (toolName === 'calendar.create_event') {
    return `Create event "${quoteForConfirmation(a.title)}".`;
  }
  if (toolName === 'calendar.update_event') {
    return `Edit calendar event ${quoteForConfirmation(a.title || a.name || 'selected event')}.`;
  }
  if (toolName === 'calendar.respond_event') {
    return `RSVP ${quoteForConfirmation(a.responseStatus)} to calendar event ${quoteForConfirmation(a.title || a.name || 'selected event')}.`;
  }
  if (toolName === 'calendar.delete_event') {
    return `Delete calendar event "${quoteForConfirmation(a.title || a.name || 'selected event')}". This requires two confirmations.`;
  }
  if (toolName === 'lists.remove_item') {
    return `Remove "${quoteForConfirmation(a.itemText || a.itemId || 'selected item')}" from ${quoteForConfirmation(a.listName || 'the list')}. This requires two confirmations.`;
  }
  return 'Confirm this action.';
}

function pendingConfirmation(toolName, args, confirmationStage = 1) {
  return {
    toolName,
    arguments: args || {},
    confirmationId: confirmationIdFor(toolName, args, confirmationStage),
    action: confirmationAction(toolName, args),
    title: confirmationTitle(toolName),
    summary: confirmationSummary(toolName, args),
    confirmationStage,
  };
}

function confirmationReply(toolName, args, stage = 1) {
  if (toolName === 'github.create_issue') {
    return 'I can create that GitHub issue. Press Confirm or say "confirm create issue".';
  }
  const action = confirmationAction(toolName, args);
  if (action === 'delete') {
    return stage >= 2
      ? 'Second confirmation required. Press Confirm again or say "confirm delete" again.'
      : 'I can delete that. This requires two confirmations. Press Confirm or say "confirm delete".';
  }
  return `I can ${action} that. Say "confirm ${action}" or press Confirm.`;
}

function pendingConfirmationFromBody(body, tools) {
  const pending = body && typeof body.pendingConfirmation === 'object' ? body.pendingConfirmation : null;
  if (!pending || typeof pending.toolName !== 'string') return null;
  const tool = toolByName(tools, pending.toolName);
  if (!tool || !tool.confirmationRequired) return null;
  const args = pending.arguments && typeof pending.arguments === 'object' ? pending.arguments : {};
  return pendingConfirmation(pending.toolName, sanitizeToolArguments(tool, args), Number(pending.confirmationStage || 1));
}

function turnKernelFromBody(body, tools, toolResults) {
  const message = safeText(body && body.message, 4000);
  const rawPending = pendingConfirmationFromBody(body, tools);
  const confirms = messageConfirms(message);
  const cancels = messageCancels(message);
  const stalePendingDropped = !!(rawPending && !confirms && !cancels);
  const pending = rawPending && confirms ? rawPending : null;
  const continuationRequest = activeTaskContinuationRequest(body, toolResults);
  const plannerMessage = continuationRequest || message;
  return {
    message,
    rawPending,
    pending,
    confirms,
    cancels,
    stalePendingDropped,
    continuationRequest,
    plannerMessage,
  };
}

function sanitizeToolArguments(tool, args) {
  if (!tool || !args || typeof args !== 'object') return {};
  const allowed = new Set(Array.isArray(tool.arguments) ? tool.arguments : []);
  const sanitized = {};
  for (const [key, value] of Object.entries(args)) {
    if (allowed.has(key) || key === '_confirmedByGateway' || key === '_doubleConfirmedByGateway') {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

function compactToolNames(tools) {
  return tools.map((tool) => tool && tool.name).filter(Boolean);
}

function compactParsedForTrace(parsed) {
  if (!parsed || typeof parsed !== 'object') return parsed || null;
  const copy = Object.assign({}, parsed);
  for (const key of ['reply', 'narration', 'text', 'answer', 'content', 'final', 'finalAnswer', 'final_response', 'response']) {
    if (typeof copy[key] === 'string' && copy[key].length > 700) {
      copy[`${key}Chars`] = copy[key].length;
      copy[key] = `${copy[key].slice(0, 700)}...`;
    }
  }
  return copy;
}

function buildToolTrace(body, tools, parsed, toolName, tool, confirmationRequested) {
  const trace = {
    prompt: safeText(body && body.message, 4000),
    workingMemory: body && typeof body.workingMemory === 'object' ? body.workingMemory : {},
    availableToolNames: compactToolNames(tools),
    availableToolsJson: JSON.stringify(tools).slice(0, 12000),
    parsedPlannerJson: compactParsedForTrace(parsed),
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

function containsForbiddenToolPlanPhrase(value) {
  const lower = String(value || '').toLowerCase();
  return lower.includes('tool plan') && lower.includes('did not converge');
}

function toolProgressSummary(entry) {
  const name = safeText(entry && entry.name, 80) || 'tool';
  const result = entry && typeof entry.result === 'object' ? entry.result : {};
  const spoken = safeText(result.spokenMessage, 240);
  if (spoken) return `${name} (${spoken})`;
  const fileName = result.file && typeof result.file === 'object' ? safeText(result.file.name, 160) : '';
  if (fileName) return `${name} (${fileName})`;
  const status = safeText(result.status, 120);
  if (status) return `${name} (${status})`;
  return name;
}

function compactTextWithHeadings(text, maxChars = 1800) {
  const raw = typeof text === 'string' ? text : '';
  const normalized = raw.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  const headings = [];
  for (const line of normalized.split('\n')) {
    const clean = line.trim();
    if (!clean || clean.length > 140) continue;
    if (/^(#{1,6}\s+|[A-Z][A-Za-z0-9 /&()'’:-]{2,80}$|\d+\.\s+|[-*]\s+[A-Z])/.test(clean)) {
      headings.push(clean.replace(/^#{1,6}\s+/, '').replace(/^[-*]\s+/, ''));
    }
    if (headings.length >= 24) break;
  }
  return {
    textPreview: safeText(normalized, maxChars),
    headings,
    truncated: normalized.length > maxChars,
    originalCharCount: normalized.length,
  };
}

function compactToolResultForPrompt(entry) {
  const name = safeText(entry && entry.name, 80);
  const args = entry && typeof entry.arguments === 'object' ? entry.arguments : {};
  const result = entry && typeof entry.result === 'object' ? entry.result : {};
  const compact = {
    name,
    arguments: args,
    ok: result.ok === true,
    error: safeText(result.error, 200),
    status: safeText(result.status, 200),
    detail: safeText(result.detail, 600),
    spokenMessage: safeText(result.spokenMessage, 600),
  };
  if (result.file && typeof result.file === 'object') {
    compact.file = {
      id: safeText(result.file.id, 160),
      name: safeText(result.file.name, 240),
      mimeType: safeText(result.file.mimeType, 160),
      webViewLink: safeText(result.file.webViewLink, 500),
    };
  }
  if (Array.isArray(result.files)) {
    compact.files = result.files.slice(0, 12).map((file) => ({
      id: safeText(file && file.id, 160),
      name: safeText(file && file.name, 240),
      mimeType: safeText(file && file.mimeType, 160),
      webViewLink: safeText(file && file.webViewLink, 500),
    }));
    compact.fileCount = result.files.length;
  }
  if (typeof result.text === 'string') {
    compact.document = compactTextWithHeadings(result.text);
  } else if (typeof result.content === 'string') {
    compact.document = compactTextWithHeadings(result.content);
  }
  return compact;
}

function compactToolEvidence(toolResults) {
  const entries = Array.isArray(toolResults) ? toolResults : [];
  const latest = entries.slice(-10).map(compactToolResultForPrompt);
  const failures = entries
    .filter((entry) => !(entry && entry.result && entry.result.ok === true))
    .slice(0, 4)
    .map(compactToolResultForPrompt);
  const seenFailureKeys = new Set(failures.map((entry) => `${entry.name}:${entry.error}:${entry.status}`));
  const merged = failures.concat(latest.filter((entry) => {
    const key = `${entry.name}:${entry.error}:${entry.status}`;
    if (seenFailureKeys.has(key)) return false;
    seenFailureKeys.add(key);
    return true;
  }));
  return {
    totalToolResults: entries.length,
    retainedToolResults: merged.length,
    retentionPolicy: 'latest useful evidence plus failures; long docs compacted with headings and truncated marker',
    results: merged,
  };
}

function latestSuccessfulToolResult(toolResults) {
  const entries = Array.isArray(toolResults) ? toolResults : [];
  for (let index = entries.length - 1; index >= 0; index--) {
    const entry = entries[index];
    if (entry && entry.result && entry.result.ok === true) return entry;
  }
  return null;
}

function activeTaskIsUnfinished(body) {
  const task = activeTaskFromBody(body);
  const status = safeText(task && task.status, 80);
  return !!(task && ['awaiting_source', 'awaiting_detail', 'in_progress'].includes(status));
}

function shouldUseEvidenceFinalizer(body, toolResults) {
  const latest = latestSuccessfulToolResult(toolResults);
  const latestTool = safeText(latest && latest.name, 80);
  if (!['docs.read', 'knowledge.read', 'web.search'].includes(latestTool)) return false;
  if (activeTaskIsUnfinished(body)) return true;
  const message = safeText(body && body.message, 4000);
  return isCreativeWritingRequest(message) && !isExplicitNonCreativeToolRequest(message);
}

function activeTaskObjective(body, fallbackMessage) {
  const task = activeTaskFromBody(body);
  return safeText(task && (task.originalUserRequest || task.objective), 4000)
      || safeText(body && body.message, 4000)
      || safeText(fallbackMessage, 4000);
}

async function runEvidenceFinalizerProvider(prompt, repair = false) {
  const controller = new AbortController();
  const timeoutMs = repair ? EVIDENCE_FINALIZER_REPAIR_TIMEOUT_MS : EVIDENCE_FINALIZER_TIMEOUT_MS;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY.value()}`,
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
      body: JSON.stringify({
        model: 'gpt-5.5',
        reasoning: {effort: 'low'},
        text: {verbosity: repair ? 'low' : 'medium'},
        max_output_tokens: repair ? 1200 : 1800,
        input: prompt,
      }),
    });
  } catch (err) {
    const isTimeout = err && err.name === 'AbortError';
    return {
      ok: false,
      response: userFacingFailure(
        'GPT-5.5 evidence finalizer',
        isTimeout ? `Timed out after ${timeoutMs}ms before producing a final answer.` : safeText(err && (err.stack || err.message || err), 1000),
        isTimeout ? 'evidence_finalizer_timeout' : 'evidence_finalizer_transport_error',
      ),
    };
  } finally {
    clearTimeout(timeout);
  }
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    return {ok: false, response: userFacingFailure('GPT-5.5 evidence finalizer', json.error?.message || response.statusText || `HTTP ${response.status}`, `openai_http_${response.status}`)};
  }
  const text = json.output_text || extractOutputText(json) || '';
  try {
    return {ok: true, parsed: extractJsonObject(text), rawText: text};
  } catch (err) {
    return {ok: false, response: plannerParseFailureReply(text, err)};
  }
}

async function askOpenAIEvidenceFinalizer(body, turnKernel, toolEvidenceDigest) {
  const message = safeText(body && body.message, 4000);
  const objective = activeTaskObjective(body, turnKernel && turnKernel.plannerMessage ? turnKernel.plannerMessage : message);
  const summary = safeText(body && body.summary, 4000);
  const transcript = safeText(body && body.transcript, 8000);
  const workingMemory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const evidenceContext = body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {};
  const finalizerPrompt = [
    'You are Home Center evidence finalizer. The app has already gathered context for the user request.',
    HOME_CENTER_DOCTRINE_STEERING,
    'Return one strict JSON object and no prose outside JSON.',
    'No tools are available in this phase. Do not request a tool. Do not say you found/read/opened context as the answer.',
    'Answer the active task from Tool evidence digest. If evidence is insufficient, name the exact missing fact in one sentence.',
    'For creative writing requests, produce the requested prose now as a complete bounded scene, hard limit 450 to 700 words. Preserve explicit names, premises, vehicle/location relationships, and constraints.',
    'If the requested scene would run longer, choose a smaller complete slice rather than a larger unfinished chapter. Prefer complete and prompt-faithful over long.',
    'Creative completion rule: do not stop mid-scene, mid-exchange, or on an unanswered dialogue line. End with a complete closing paragraph.',
    'Do not mention file IDs, HTTP, tokens, timestamps, diagnostics, or implementation details unless the user asked for diagnostics.',
    'Return JSON only: {"type":"final","reply":"...","narration":"...","status":"evidence_finalized","taskStateUpdate":{"status":"complete","objective":"..."}}',
    `Active task objective: ${objective}`,
    `Latest user request: ${message}`,
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Working memory JSON: ${JSON.stringify(workingMemory).slice(0, 6000)}`,
    `Evidence context JSON: ${JSON.stringify(evidenceContext).slice(0, 12000)}`,
    `Available tools JSON: []`,
    `Tool evidence digest JSON: ${JSON.stringify(toolEvidenceDigest).slice(0, 50000)}`,
  ].filter(Boolean).join('\n\n');
  let provider = await runEvidenceFinalizerProvider(finalizerPrompt);
  if (!provider.ok) return provider.response;
  if (provider.parsed && provider.parsed.type === 'tool_call') {
    provider = await runEvidenceFinalizerProvider(`${finalizerPrompt}\n\nPrior invalid output requested a tool. Repair it by returning only a final answer from the provided evidence.`, true);
    if (!provider.ok) return provider.response;
  }
  const parsed = provider.parsed || {};
  const reply = finalReplyText(parsed, provider.rawText || '');
  if (finalReplyLooksTruncated(reply)) {
    const repaired = await repairTruncatedFinalReply(body, reply, finalizerPrompt);
    if (repaired) return repaired;
  }
  if (!reply) {
    return {
      type: 'final',
      reply: 'I have the context, but I could not turn it into a final answer. Please try again.',
      narration: 'I have the context, but I could not turn it into a final answer.',
      status: 'evidence_finalizer_empty',
      taskStateUpdate: {status: 'in_progress', objective},
    };
  }
  return attachTaskState({
    type: 'final',
    reply,
    narration: finalReplyText({reply: parsed.narration}, '', 0) || reply,
    status: safeText(parsed.status, 160) || 'evidence_finalized',
  }, Object.assign({taskStateUpdate: {status: 'complete', objective}}, parsed));
}

function synthesizeToolLoopProgressReply(toolResults) {
  const successes = [];
  let failedTool = '';
  let failedMessage = '';
  for (const entry of Array.isArray(toolResults) ? toolResults : []) {
    const result = entry && typeof entry.result === 'object' ? entry.result : {};
    if (result.ok === true) {
      if (successes.length < 8) successes.push(toolProgressSummary(entry));
      continue;
    }
    if (!failedTool) {
      failedTool = safeText(entry && entry.name, 80) || 'tool';
      failedMessage = safeText(result.spokenMessage || result.detail || result.error || 'the tool failed', 500);
    }
  }
  const succeeded = successes.length ? successes.join('; ') : 'nothing';
  if (failedTool) {
    return `Failed at ${failedTool}: ${failedMessage}\n\nSucceeded before it: ${succeeded}\n\nNext action needed: fix that failure, then ask me to continue.`;
  }
  if (!successes.length) {
    return 'I stopped before completing the request.\n\nSucceeded before it: nothing.\n\nNext action needed: ask me to continue or narrow the request.';
  }
  return `I completed these steps before the tool loop stopped: ${succeeded}\n\nI stopped before completing the remaining requested steps.\n\nNext action needed: ask me to continue from the last completed step.`;
}

function sanitizeFinalPlannerReply(body, response) {
  if (!response || response.type !== 'final') return response;
  const reply = safeText(response.reply || response.text, 12000);
  if (!containsForbiddenToolPlanPhrase(reply)) return response;
  const replacement = synthesizeToolLoopProgressReply(Array.isArray(body && body.toolResults) ? body.toolResults : []);
  return Object.assign({}, response, {
    reply: replacement,
    narration: replacement,
    status: 'tool_loop_progress_fallback',
  });
}

function taskStateUpdateFromParsed(parsed) {
  const update = parsed && typeof parsed.taskStateUpdate === 'object' ? parsed.taskStateUpdate : null;
  if (!update) return null;
  const status = safeText(update.status, 40);
  const allowed = new Set(['awaiting_detail', 'awaiting_source', 'in_progress', 'complete', 'cancelled']);
  if (!allowed.has(status)) return null;
  const sanitized = {status};
  for (const key of ['objective', 'originalUserRequest', 'missingDetailQuestion', 'knownContext', 'blockingReason', 'expectedNextAction']) {
    const value = safeText(update[key], 2000);
    if (value) sanitized[key] = value;
  }
  return sanitized;
}

function attachTaskState(response, parsed) {
  const update = taskStateUpdateFromParsed(parsed);
  if (!update) return response;
  return Object.assign({}, response, {taskStateUpdate: update});
}

function attachCreativeTaskComplete(response, message) {
  if (!response || response.taskStateUpdate) return response;
  return Object.assign({}, response, {
    taskStateUpdate: {
      status: 'complete',
      objective: safeText(message, 1000),
      originalUserRequest: safeText(message, 1000),
    },
  });
}

function isCreativeWritingRequest(message) {
  const text = String(message || '').toLowerCase();
  if (/\b(write|draft|compose|continue|narrate|expand)\b/.test(text)) return true;
  if (/\b(generate|tell|simulate)\b/.test(text)
      && /\b(scene|story|chapter|prose|draft|passage|moment|dialogue|first contact|d-day)\b/.test(text)) return true;
  if (/\bnext\b/.test(text)
      && /\b(scene|story|chapter|passage|moment)\b/.test(text)) return true;
  return /\b(make|create)\b/.test(text)
    && /\b(scene|story|chapter|prose|draft|passage|moment|dialogue|first contact|d-day)\b/.test(text);
}

function creativeReplyNeedsRepair(message, reply) {
  if (!isCreativeWritingRequest(message)) return false;
  const text = String(reply || '').trim();
  if (!text) return true;
  const lower = text.toLowerCase();
  if (lower.includes('i don’t have enough context') || lower.includes("i don't have enough context")) return true;
  if (lower.includes('i need more context') || lower.includes('please provide')) return true;
  if (lower.includes('which exact') || lower.includes('do you mean')) return true;
  if (lower.includes('next step:') || lower.includes('next steps:')) return true;
  return text.length < 260;
}

function isExplicitNonCreativeToolRequest(message) {
  const text = String(message || '').toLowerCase();
  if (/\b(report|file an issue|github issue|send this to github|feedback|bug)\b/.test(text)) return true;
  if (/\b(find|search|read|open|upload|save|create a google doc|create google doc|update|append|replace|edit)\b/.test(text)
      && /\b(drive|doc|docs|document|folder|gmail|email|calendar|sheet|github)\b/.test(text)) return true;
  return false;
}

function activeTaskFromBody(body) {
  const memory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  return memory.activeTask && typeof memory.activeTask === 'object' ? memory.activeTask : null;
}

function activeTaskContinuationRequest(body, toolResults) {
  const task = activeTaskFromBody(body);
  if (!task) return '';
  const status = safeText(task.status, 80);
  if (!['awaiting_source', 'awaiting_detail', 'in_progress'].includes(status)) return '';
  const latestResult = Array.isArray(toolResults) && toolResults.length ? toolResults[toolResults.length - 1] : null;
  const latestTool = safeText(latestResult && latestResult.name, 80);
  const latestOk = !!(latestResult && latestResult.result && latestResult.result.ok === true);
  if (!latestOk || !['knowledge.append', 'docs.read', 'docs.search', 'drive.search', 'web.search'].includes(latestTool)) return '';
  return safeText(task.originalUserRequest, 4000) || safeText(task.objective, 4000);
}

function shouldBlockCreativePlannerToolCall(message) {
  return isCreativeWritingRequest(message) && !isExplicitNonCreativeToolRequest(message);
}

function hasAvailableTool(tools, name) {
  return !!toolByName(Array.isArray(tools) ? tools : [], name);
}

function hasToolResult(toolResults, name, predicate = null) {
  return (Array.isArray(toolResults) ? toolResults : []).some((entry) => {
    if (!entry || entry.name !== name) return false;
    return predicate ? predicate(entry) : true;
  });
}

function creativeContextToolCall(body, tools, toolResults) {
  const memory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const lastDocument = memory.lastDocument && typeof memory.lastDocument === 'object' ? memory.lastDocument : null;
  if (lastDocument && lastDocument.fileId && hasAvailableTool(tools, 'docs.read')) {
    const alreadyRead = hasToolResult(toolResults, 'docs.read', (entry) => {
      const args = entry && typeof entry.arguments === 'object' ? entry.arguments : {};
      return args.fileId === lastDocument.fileId;
    });
    if (!alreadyRead) {
      return {
        type: 'tool_call',
        toolName: 'docs.read',
        arguments: {fileId: lastDocument.fileId, name: safeText(lastDocument.name, 240)},
        status: 'tool_call_requested',
        taskStateUpdate: {
          status: 'in_progress',
          objective: safeText(body && body.message, 1000),
          originalUserRequest: safeText(body && body.message, 1000),
          expectedNextAction: 'Read remembered canon document before drafting creative prose.',
        },
      };
    }
    return null; // A remembered document is enough context for this creative turn.
  }
  const lastKnowledge = memory.lastKnowledgeFile && typeof memory.lastKnowledgeFile === 'object' ? memory.lastKnowledgeFile : null;
  if (lastKnowledge && lastKnowledge.file && hasAvailableTool(tools, 'knowledge.read')) {
    const alreadyRead = hasToolResult(toolResults, 'knowledge.read', (entry) => {
      const args = entry && typeof entry.arguments === 'object' ? entry.arguments : {};
      return safeText(args.file, 80).toLowerCase() === safeText(lastKnowledge.file, 80).toLowerCase();
    });
    if (!alreadyRead) {
      return {
        type: 'tool_call',
        toolName: 'knowledge.read',
        arguments: {file: safeText(lastKnowledge.file, 80)},
        status: 'tool_call_requested',
        taskStateUpdate: {
          status: 'in_progress',
          objective: safeText(body && body.message, 1000),
          originalUserRequest: safeText(body && body.message, 1000),
          expectedNextAction: 'Read remembered durable knowledge before drafting creative prose.',
        },
      };
    }
  }
  return null;
}

async function askOpenAICreativeRepair(body, originalReply) {
  const message = safeText(body.message, 4000);
  const transcript = safeText(body.transcript, 10000);
  const summary = safeText(body.summary, 4000);
  const workingMemory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const evidenceContext = body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {};
  const toolResults = Array.isArray(body.toolResults) ? body.toolResults : [];
  const digest = compactToolEvidence(toolResults);
  const prompt = [
    'Repair a failed Home Center creative-writing response.',
    'The user asked for prose. Produce the requested scene/passage now as a strict JSON final answer.',
    'Use only available transcript, workingMemory, evidence, attachments, and tool evidence. If context is thin, write a short grounded draft around confirmed names/actions and avoid unsupported biography.',
    'Do not ask another clarification question. Do not provide next steps. Do not call tools. Do not report an issue. Do not explain the repair.',
    'Return JSON only: {"type":"final","reply":"...","narration":"...","status":"creative_repair_complete","taskStateUpdate":{"status":"complete","objective":"..."}}',
    `Latest user request: ${message}`,
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Working memory JSON: ${JSON.stringify(workingMemory).slice(0, 8000)}`,
    `Evidence context JSON: ${JSON.stringify(evidenceContext).slice(0, 12000)}`,
    `Tool evidence digest JSON: ${JSON.stringify(digest).slice(0, 50000)}`,
    `Rejected first reply: ${safeText(originalReply, 4000)}`,
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
      text: {verbosity: 'medium'},
      input: prompt,
    }),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    return null;
  }
  try {
    const parsed = extractJsonObject(json.output_text || extractOutputText(json) || '');
    const reply = finalReplyText(parsed, '');
    if (!reply || creativeReplyNeedsRepair(message, reply)) return null;
    return attachTaskState({
      type: 'final',
      reply,
      narration: safeText(parsed.narration, 12000) || reply,
      status: safeText(parsed.status, 160) || 'creative_repair_complete',
    }, parsed);
  } catch (err) {
    return null;
  }
}

function creativeDraftPrompt(body, mode, priorFailure = '') {
  const message = safeText(body.message, 4000);
  const transcript = safeText(body.transcript, 10000);
  const summary = safeText(body.summary, 4000);
  const workingMemory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const evidenceContext = body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {};
  const toolResults = Array.isArray(body.toolResults) ? body.toolResults : [];
  const digest = compactToolEvidence(toolResults);
  const salvage = mode === 'salvage';
  return [
    salvage ? 'Salvage a Home Center creative-writing response after the first provider attempt failed.' : 'Draft a Home Center creative-writing response.',
    'The user asked for prose. Produce the requested scene/passage now as a strict JSON final answer.',
    salvage
      ? 'Write a shorter but complete grounded scene. Do not wait for more context. Prefer 300-600 words that satisfy the explicit prompt.'
      : 'Use only available transcript, workingMemory, evidence, attachments, and tool evidence. If context is thin, write a short grounded draft around confirmed names/actions and avoid unsupported biography.',
    'If workingMemory.rememberedWritingContext exists, treat it as durable writing steering from prior turns. Use it directly; do not search Drive for it unless the latest user asks.',
    'Do not ask another clarification question. Do not provide next steps. Do not call tools. Do not report an issue. Do not explain process.',
    'Preserve explicit user premises, character roles, POV, location, command position, vehicle relationships, and historical constraints.',
    'For kinetic compression: Intent -> Position Change -> Contact / Interaction -> Immediate Consequence -> New Tactical Situation.',
    'Return JSON only: {"type":"final","reply":"...","narration":"...","status":"creative_draft_complete","taskStateUpdate":{"status":"complete","objective":"..."}}',
    `Latest user request: ${message}`,
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Working memory JSON: ${JSON.stringify(workingMemory).slice(0, 8000)}`,
    `Evidence context JSON: ${JSON.stringify(evidenceContext).slice(0, 12000)}`,
    `Tool evidence digest JSON: ${JSON.stringify(digest).slice(0, 50000)}`,
    priorFailure ? `Prior provider failure: ${safeText(priorFailure, 1000)}` : '',
  ].filter(Boolean).join('\n\n');
}

async function runCreativeProviderJson(prompt, timeoutMs, statusFallback, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const salvage = options.mode === 'salvage';
  let response;
  try {
    response = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY.value()}`,
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
      body: JSON.stringify({
        model: 'gpt-5.5',
        reasoning: {effort: salvage ? 'low' : 'low'},
        text: {verbosity: salvage ? 'low' : 'medium'},
        max_output_tokens: salvage ? 1400 : 2600,
        input: prompt,
      }),
    });
  } catch (err) {
    return {
      ok: false,
      status: err && err.name === 'AbortError' ? 'creative_provider_timeout' : 'creative_provider_error',
      detail: err && err.name === 'AbortError'
        ? `Timed out after ${timeoutMs}ms before producing prose.`
        : safeText(err && err.message, 500) || 'Provider request failed before producing prose.',
    };
  } finally {
    clearTimeout(timeout);
  }
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    return {
      ok: false,
      status: `creative_openai_http_${response.status}`,
      detail: json.error?.message || response.statusText || `HTTP ${response.status}`,
    };
  }
  try {
    const parsed = extractJsonObject(json.output_text || extractOutputText(json) || '');
    return {ok: true, parsed};
  } catch (err) {
    return {
      ok: false,
      status: statusFallback || 'creative_draft_parse_failed',
      detail: `Malformed output: ${safeText(err.message, 160)}`,
    };
  }
}

async function askOpenAICreativeDraft(body) {
  const message = safeText(body.message, 4000);
  const prompt = creativeDraftPrompt(body, 'draft');
  let provider = await runCreativeProviderJson(prompt, CREATIVE_OPENAI_TIMEOUT_MS, 'creative_draft_parse_failed');
  let usedSalvage = false;
  if (!provider.ok) {
    usedSalvage = true;
    provider = await runCreativeProviderJson(creativeDraftPrompt(body, 'salvage', provider.detail), CREATIVE_SALVAGE_TIMEOUT_MS, 'creative_salvage_parse_failed', {mode: 'salvage'});
  }
  if (!provider.ok) {
    return attachCreativeTaskComplete(userFacingFailure('Creative writing provider', provider.detail, provider.status), message);
  }
  try {
    const parsed = provider.parsed;
    const reply = finalReplyText(parsed, '');
    if (!reply || creativeReplyNeedsRepair(message, reply)) {
      const salvage = await runCreativeProviderJson(creativeDraftPrompt(body, 'salvage', 'empty or unusable output'), CREATIVE_SALVAGE_TIMEOUT_MS, 'creative_salvage_parse_failed', {mode: 'salvage'});
      if (!salvage.ok) return attachCreativeTaskComplete(userFacingFailure('Creative writing provider', salvage.detail, salvage.status), message);
      const salvageReply = finalReplyText(salvage.parsed, '');
      if (!salvageReply || creativeReplyNeedsRepair(message, salvageReply)) {
        return attachCreativeTaskComplete(userFacingFailure('Creative writing provider', 'Salvage attempt also returned no usable prose.', 'creative_salvage_empty'), message);
      }
      return attachCreativeTaskComplete(attachTaskState({
        type: 'final',
        reply: salvageReply,
        narration: safeText(salvage.parsed.narration, 12000) || salvageReply,
        status: safeText(salvage.parsed.status, 160) || 'creative_salvage_complete',
      }, salvage.parsed), message);
    }
    return attachCreativeTaskComplete(attachTaskState({
      type: 'final',
      reply,
      narration: safeText(parsed.narration, 12000) || reply,
      status: safeText(parsed.status, 160) || (usedSalvage ? 'creative_salvage_complete' : 'creative_draft_complete'),
    }, parsed), message);
  } catch (err) {
    return attachCreativeTaskComplete(userFacingFailure('Creative writing provider', `Malformed output (${safeText(err.message, 160)}).`, 'creative_draft_parse_failed'), message);
  }
}

async function validateCreativeFinal(body, draft) {
  const message = safeText(body.message, 4000);
  if (!isCreativeWritingRequest(message) || isExplicitNonCreativeToolRequest(message)) return null;
  const transcript = safeText(body.transcript, 10000);
  const summary = safeText(body.summary, 4000);
  const workingMemory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const evidenceContext = body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {};
  const toolResults = Array.isArray(body.toolResults) ? body.toolResults : [];
  const digest = compactToolEvidence(toolResults);
  const prompt = [
    'Validate and, if needed, repair a Home Center creative-writing draft before the user sees it.',
    'Preserve explicit user premises from latest request, recent transcript, workingMemory, durable knowledge, and tool evidence.',
    'Reject and rewrite if the draft changes a named character role, POV, location, command position, vehicle relationship, historical constraint, or other canon premise.',
    'Examples of forbidden failures: making a tank commander into infantry outside the tank; replacing a named commanded vehicle with an unrelated external vehicle; treating a grounded historical constraint as vague symbolism.',
    'If the draft is valid, return it unchanged. If it violates premises, return a revised draft only. Do not explain validation. Do not ask questions. Do not add next steps. Do not report an issue.',
    'Return JSON only: {"type":"final","reply":"...","narration":"...","status":"creative_validated","taskStateUpdate":{"status":"complete","objective":"..."}}',
    `Latest user request: ${message}`,
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Working memory JSON: ${JSON.stringify(workingMemory).slice(0, 8000)}`,
    `Evidence context JSON: ${JSON.stringify(evidenceContext).slice(0, 12000)}`,
    `Tool evidence digest JSON: ${JSON.stringify(digest).slice(0, 50000)}`,
    `Draft to validate: ${safeText(draft, 12000)}`,
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
      text: {verbosity: 'medium'},
      input: prompt,
    }),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) return null;
  try {
    const parsed = extractJsonObject(json.output_text || extractOutputText(json) || '');
    const reply = finalReplyText(parsed, '');
    if (!reply || creativeReplyNeedsRepair(message, reply)) return null;
    return attachTaskState({
      type: 'final',
      reply,
      narration: safeText(parsed.narration, 12000) || reply,
      status: safeText(parsed.status, 160) || 'creative_validated',
    }, parsed);
  } catch (err) {
    return null;
  }
}

function finalReplyText(parsed, rawText = '', depth = 0) {
  if (!parsed || typeof parsed !== 'object') return safeText(rawText, FINAL_REPLY_MAX_CHARS);
  const direct = parsed.reply
    || parsed.text
    || parsed.answer
    || parsed.message
    || parsed.content
    || parsed.final
    || parsed.finalAnswer
    || parsed.final_response
    || parsed.response
    || '';
  if (typeof direct === 'string' && direct.trim()) {
    const clean = direct.trim();
    if (depth < 2 && clean.startsWith('{') && clean.endsWith('}')) {
      try {
        const nested = JSON.parse(clean);
        const nestedReply = finalReplyText(nested, '', depth + 1);
        if (nestedReply) return nestedReply;
      } catch (err) {
        // Return the original text below if it only looks like JSON.
      }
    }
    return safeText(direct, FINAL_REPLY_MAX_CHARS);
  }
  if (Array.isArray(parsed.content)) {
    const joined = parsed.content.map((item) => {
      if (typeof item === 'string') return item;
      if (item && typeof item.text === 'string') return item.text;
      if (item && typeof item.content === 'string') return item.content;
      return '';
    }).filter(Boolean).join('\n');
    if (joined.trim()) return safeText(joined, FINAL_REPLY_MAX_CHARS);
  }
  if (rawText && !looksLikeToolCallJson(rawText)) return safeText(rawText, FINAL_REPLY_MAX_CHARS);
  return '';
}

function finalReplyLooksTruncated(reply) {
  const text = String(reply || '').trim();
  if (!text) return false;
  if (text.length >= FINAL_REPLY_MAX_CHARS) return true;
  const lower = text.toLowerCase();
  if (text.length > 500 && /[,;]$/.test(text)) return true;
  const lowerEnd = lower.replace(/[,"'“”‘’\s]+$/g, '');
  if (/\b(and|or|but|for|with|without|to|from|because|while|when|if|so|the|a|an|your|his|her|their)$/.test(lowerEnd)) return true;
  const last = text.charAt(text.length - 1);
  const penultimate = text.length > 1 ? text.charAt(text.length - 2) : '';
  const lastLine = text.split(/\n+/).map((line) => line.trim()).filter(Boolean).pop() || '';
  if (text.length > 2000 && /^["“][^"”]{1,180}[?!.]["”]?$/.test(lastLine)) return true;
  if ((last === '"' || last === '“' || last === '”') && !'.!?:;)]}'.includes(penultimate)) return true;
  if ('.!?:;)]}"”’.'.includes(last)) return false;
  return text.length > 500 && /[A-Za-z0-9]$/.test(text);
}

async function repairTruncatedFinalReply(body, incompleteReply, promptText) {
  const message = safeText(body && body.message, 4000);
  const transcript = safeText(body && body.transcript, 6000);
  const summary = safeText(body && body.summary, 2000);
  const evidenceContext = body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {};
  const repairPrompt = [
    'You are Home Center response completion repair.',
    'The previous GPT-5.5 final answer appears cut off. Return one strict JSON object and no prose outside JSON.',
    'Rewrite the complete answer for the latest user request. Preserve the useful content and finish all sentences, quotes, numbered points, and sections.',
    'Do not add a routine Next step footer. Do not mention that repair happened unless the user asked for diagnostics.',
    'Return JSON only: {"type":"final","reply":"...","narration":"...","status":"truncated_final_repaired","taskStateUpdate":{"status":"complete","objective":"..."}}',
    `Latest user request: ${message}`,
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Evidence context JSON: ${JSON.stringify(evidenceContext).slice(0, 12000)}`,
    `Incomplete prior answer: ${safeText(incompleteReply, 12000)}`,
    promptText ? `Original planner prompt excerpt: ${safeText(promptText, 8000)}` : '',
  ].filter(Boolean).join('\n\n');
  const provider = await runEvidenceFinalizerProvider(repairPrompt, true);
  if (!provider.ok) return null;
  const parsed = provider.parsed || {};
  const reply = finalReplyText(parsed, provider.rawText || '');
  if (!reply || finalReplyLooksTruncated(reply)) return null;
  return attachTaskState({
    type: 'final',
    reply,
    narration: finalReplyText({reply: parsed.narration}, '', 0) || reply,
    status: safeText(parsed.status, 160) || 'truncated_final_repaired',
  }, Object.assign({taskStateUpdate: {status: 'complete', objective: message}}, parsed));
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
  if (toolName === 'drive.upload_file') {
    const activeFileIds = Array.isArray(memory.activeFileIds) ? memory.activeFileIds : [];
    const attachedFiles = Array.isArray(memory.attachedFiles) ? memory.attachedFiles : [];
    if (!args.sessionFileId && activeFileIds.length === 1) {
      args.sessionFileId = activeFileIds[0];
    }
    const selected = attachedFiles.find((file) => file && file.sessionFileId === args.sessionFileId);
    if (selected) {
      if (!args.name) args.name = selected.displayName || '';
      if (!args.mimeType) args.mimeType = selected.mimeType || '';
      if (!args.displayName) args.displayName = selected.displayName || '';
    }
  }
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
      if (memory.lastFolder.fileId && !args.folderId && toolName !== 'drive.update_metadata') args.folderId = memory.lastFolder.fileId;
      if (memory.lastFolder.name && !args.folderName && toolName !== 'drive.update_metadata') args.folderName = memory.lastFolder.name;
    }
  }
  if (toolName && toolName.startsWith('sheets.') && memory.lastSheet) {
    if (hasLiteralReference || args.fileId === memory.lastSheet.fileId || args.spreadsheetId === memory.lastSheet.fileId) {
      fillResolvedEntity(args, memory.lastSheet, 'fileId', 'name');
      if (memory.lastSheet.fileId && !args.spreadsheetId) args.spreadsheetId = memory.lastSheet.fileId;
    }
  }
  if (toolName && toolName.startsWith('gmail.') && toolName !== 'gmail.trash' && memory.lastEmailDraft) {
    const referencesDraft = UNRESOLVED_REFERENCE_LITERALS.has(normalizedReferenceLiteral(args.subject));
    if (referencesDraft || args.draftId === memory.lastEmailDraft.draftId) {
      if (memory.lastEmailDraft.draftId && !args.draftId) args.draftId = memory.lastEmailDraft.draftId;
      if (memory.lastEmailDraft.subject && !args.subject) args.subject = memory.lastEmailDraft.subject;
    }
  }
  if (toolName === 'gmail.trash' && memory.lastEmailMessage) {
    if (hasLiteralReference || args.messageId === memory.lastEmailMessage.messageId) {
      if (memory.lastEmailMessage.messageId && !args.messageId) args.messageId = memory.lastEmailMessage.messageId;
      if (memory.lastEmailMessage.subject && !args.subject) args.subject = memory.lastEmailMessage.subject;
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
    (toolName === 'drive.upload_file' && Array.isArray(memory.activeFileIds) && memory.activeFileIds.length === 1) ||
    (toolName && toolName.startsWith('docs.') && memory.lastDocument && memory.lastDocument.fileId) ||
    (toolName && toolName.startsWith('drive.') && memory.lastFolder && memory.lastFolder.fileId) ||
    (toolName && toolName.startsWith('sheets.') && memory.lastSheet && memory.lastSheet.fileId) ||
    (toolName && toolName.startsWith('gmail.') && memory.lastEmailDraft && memory.lastEmailDraft.draftId) ||
    (toolName === 'gmail.trash' && memory.lastEmailMessage && memory.lastEmailMessage.messageId) ||
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

function openAiInputWithAttachments(promptText, attachmentImages) {
  const images = Array.isArray(attachmentImages) ? attachmentImages : [];
  if (!images.length) {
    return promptText;
  }
  const content = [{type: 'input_text', text: promptText}];
  for (const image of images.slice(0, 10)) {
    const imageUrl = safeText(image && (image.imageUrl || image.dataUrl), 15000000);
    if (!imageUrl || !imageUrl.startsWith('data:image/')) {
      continue;
    }
    content.push({
      type: 'input_image',
      image_url: imageUrl,
      detail: safeText(image.detail, 20) || 'auto',
    });
  }
  return [{role: 'user', content}];
}

async function askOpenAIToolTurn(body) {
  const message = safeText(body.message, 4000);
  const summary = compactPromptText(body.summary, 1200);
  const transcript = compactPromptText(body.transcript, 2000);
  const toolResults = Array.isArray(body.toolResults) ? body.toolResults : [];
  const toolEvidenceDigest = compactToolEvidence(toolResults);
  const tools = Array.isArray(body.tools) ? body.tools : [];
  const unavailableToolGroups = Array.isArray(body.unavailableToolGroups) ? body.unavailableToolGroups : [];
  const workingMemory = body && typeof body.workingMemory === 'object' ? body.workingMemory : {};
  const evidenceContext = body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {};
  const attachmentImages = Array.isArray(body.attachmentImages) ? body.attachmentImages.slice(0, 10) : [];
  const timeContext = timeContextFromBody(body);
  const turnKernel = turnKernelFromBody(body, tools, toolResults);
  const rawPending = turnKernel.rawPending;
  const pending = turnKernel.pending;
  const continuationRequest = turnKernel.continuationRequest;
  const plannerMessage = turnKernel.plannerMessage;
  if (rawPending && turnKernel.cancels) {
    const trace = buildToolTrace(body, tools, {type: 'final', status: 'pending_confirmation_cancelled'}, rawPending.toolName, toolByName(tools, rawPending.toolName), false);
    return withTrace(body, {
      type: 'final',
      reply: 'Canceled that pending action.',
      narration: 'Canceled that pending action.',
      status: 'pending_confirmation_cancelled',
      taskStateUpdate: {status: 'cancelled', objective: safeText(rawPending.action || rawPending.toolName, 500)},
    }, Object.assign({}, trace, {turnKernel, pendingConfirmationCancelled: true}));
  }
  if (pending && messageConfirms(message)) {
    const pendingTool = toolByName(tools, pending.toolName);
    if (pendingTool && pendingTool.doubleConfirmationRequired && Number(pending.confirmationStage || 1) < 2) {
      const nextPending = pendingConfirmation(pending.toolName, pending.arguments, 2);
      const reply = confirmationReply(pending.toolName, pending.arguments, 2);
      const trace = buildToolTrace(body, tools, {type: 'tool_call', toolName: pending.toolName, arguments: pending.arguments, source: 'pending_confirmation_stage_1'}, pending.toolName, pendingTool, true);
      return withTrace(body, {
        type: 'final',
        reply,
        narration: reply,
        status: 'double_confirmation_required',
        pendingConfirmation: nextPending,
      }, Object.assign({}, trace, {turnKernel}));
    }
    pending.arguments._confirmedByGateway = true;
    if (pendingTool && pendingTool.doubleConfirmationRequired) {
      pending.arguments._doubleConfirmedByGateway = true;
    }
    const trace = buildToolTrace(body, tools, {type: 'tool_call', toolName: pending.toolName, arguments: pending.arguments, source: 'pending_confirmation'}, pending.toolName, toolByName(tools, pending.toolName), false);
    return withTrace(body, {
      type: 'tool_call',
      toolName: pending.toolName,
      arguments: pending.arguments,
      status: 'tool_call_requested',
    }, Object.assign({}, trace, {turnKernel}));
  }
  if (shouldUseEvidenceFinalizer(body, toolResults)) {
    const finalized = await askOpenAIEvidenceFinalizer(body, turnKernel, toolEvidenceDigest);
    const trace = buildToolTrace(body, tools, finalized, '', null, false);
    return withTrace(body, finalized, Object.assign({}, trace, {
      turnKernel,
      evidenceFinalizerApplied: true,
      latestSuccessfulTool: safeText(latestSuccessfulToolResult(toolResults) && latestSuccessfulToolResult(toolResults).name, 80),
    }));
  }
  if (shouldBlockCreativePlannerToolCall(plannerMessage)) {
    const contextTool = creativeContextToolCall(body, tools, toolResults);
    if (contextTool) {
      const trace = buildToolTrace(body, tools, contextTool, contextTool.toolName, toolByName(tools, contextTool.toolName), false);
      return withTrace(body, contextTool, Object.assign({}, trace, {
        turnKernel,
        creativeContextToolCallApplied: true,
      }));
    }
  }
  const plannerTools = economyToolPalette(message, tools, workingMemory, toolResults);
  if (isFeedbackReportRequest(plannerMessage) && !toolByName(plannerTools, 'github.create_issue')) {
    const unavailableGithub = unavailableGroupForTool('github.create_issue', unavailableToolGroups);
    const response = unavailableGithub
      ? toolExposureFailureReply('github.create_issue', unavailableGithub)
      : reportIssueDraftFallback(body, 'github.create_issue is not exposed in Available tools JSON and unavailableToolGroups did not identify GitHub as a missing provider/scope.');
    const trace = buildToolTrace(body, plannerTools, response, 'github.create_issue', null, false);
    return withTrace(body, attachTaskState(response, {
      taskStateUpdate: {status: 'complete', objective: 'Prepare bug report fallback for missing GitHub issue tool'},
    }), Object.assign({}, trace, {turnKernel, githubIssueDraftFallback: !unavailableGithub}));
  }
  const openAiTools = shouldEnableWebSearch(message, body) ? [{type: 'web_search'}] : [];
  const includeFullDoctrine = shouldIncludeFullDoctrine(message, body);
  const includeEvidenceContext = shouldIncludeEvidenceContext(message, body, pending, toolResults);
  const includeToolDigest = toolResults.length > 0;
  const reasoningEffort = 'low';
  console.info('ai_cost', JSON.stringify({
    event: 'agent_tool_turn_palette',
    advertisedTools: tools.length,
    plannerTools: plannerTools.length,
    webSearchEnabled: openAiTools.length > 0,
    toolResults: toolResults.length,
    doctrineFull: includeFullDoctrine,
    evidenceContext: includeEvidenceContext,
    toolDigest: includeToolDigest,
    transcriptChars: transcript.length,
    summaryChars: summary.length,
    reasoningEffort,
  }));
  const promptText = [
    'You are Home Center. You are the thinker. The Android app is only your hands.',
    includeFullDoctrine ? HOME_CENTER_DOCTRINE_STEERING : 'Doctrine summary: Home Center reasons with GPT, executes through app-owned tools, hides plumbing, and asks for confirmation before external writes.',
    'Return one strict JSON object and no prose outside JSON.',
    'If a needed capability appears in the available tools JSON, request that tool. Do not say you cannot do it.',
    'Working memory JSON contains recently created or selected entities. Inspect it before selecting a tool.',
    'Active task rule: workingMemory.activeTask is an unfinished user objective. If its status is awaiting_detail or awaiting_source and the latest user request supplies that missing detail/source, resume the originalUserRequest/objective immediately. Do not merely acknowledge the detail/source.',
    'Active task rule: when you ask a clarifying question, ask for a missing source, hit a blocker, or pause before the objective is complete, include taskStateUpdate with status awaiting_detail, awaiting_source, or in_progress. When the objective is fully answered, include taskStateUpdate status complete. If the user cancels or switches to an unrelated task, include status cancelled.',
    'Active task rule: after a tool or knowledge write resolves the blocker for activeTask, continue the original task in the same turn. A saved source, found folder, read document, or answered clarification is progress, not completion.',
    continuationRequest ? `Active task continuation override: the latest tool result resolved a blocker. Treat this as the operative user request now: ${continuationRequest}` : '',
    'If the user says it, that document, that file, the one you just created, the previous one, or similar, resolve the reference from workingMemory or recent tool results before calling a tool.',
    'Never use phrases like that document, the document, that file, it, the one, or the thing we just made as literal tool argument names or titles. Resolve them to IDs/names or ask which item the user means.',
    'When resolving a remembered document, include both fileId and name in the tool arguments so confirmation cards can show the real document name.',
    'Google Docs rule: for a request to create a Google Doc, call docs.create with title and body. Do not call Drive tools for document content.',
    'Google Docs rule: for a request to read or edit a Google Doc, use docs.search if needed, then docs.read or docs.update.',
    'Google Sheets rule: for spreadsheet creation or cell edits, use sheets.create, sheets.search, sheets.read, or sheets.update.',
    'Delete rule: only use delete/trash/remove tools when the latest user request explicitly asks to delete, trash, remove, or cancel. Use drive.delete, docs.delete, sheets.delete, gmail.trash, calendar.delete_event, or lists.remove_item as appropriate. Search/read first if you need the target ID.',
    'Attachment rule: workingMemory.attachedFiles is the current session file collection. Use attached textPreview content directly when the user asks about attached text files.',
    'Attachment rule: image attachments are provided as input_image content. Describe and analyze them directly for accessibility. Do not say image analysis is unavailable when imagePreviewAvailable is true.',
    'Attachment rule: activeFileIds are the most recent or referenced attachments. Resolve this file, that image, the attachment, or similar references to a sessionFileId before calling a file tool.',
    'Drive rule: use drive.upload_file only when the user asks to upload an attached session file to Drive. Attaching a file never uploads it automatically.',
    'Drive rule: use other drive.* tools only for file and folder metadata, folder creation, rename, and move.',
    'Calendar time rule: timeContext is the device clock. Resolve relative times like five minutes from now, in 2 hours, tomorrow, or later today into absolute RFC3339 dateTime strings before calling calendar tools.',
    'Calendar time rule: do not ask for an exact time when the user already gave a relative time and timeContext is present. Compute it. If an event has startTime but no endTime, use 15 minutes for reminders/notifications and 30 minutes for ordinary events.',
    'Contacts rule: if the user names a person from contacts, call contacts.search with that name. Do not ask for an email address while contacts.search is available.',
    'Contacts plus Calendar rule: to add a named contact to an event, search contacts first, use the contact primaryEmail, resolve the target event from workingMemory or calendar.search/read, then call calendar.update_event with attendeesToAdd.',
    'Calendar display rule: in confirmations and final replies, use the event title/summary such as Home Center notification. Do not show eventId values unless the user explicitly asks for technical details.',
    openAiTools.length ? 'Public web rule: you also have OpenAI web_search for public web pages, including public GitHub repositories. Use web_search for public GitHub repo questions, README discovery, file discovery, and public documentation lookup.' : '',
    'Repository orientation rule: if the user names an owner/repo such as Valar05/tanks-for-the-memories, search the exact GitHub URL github.com/owner/repo and raw.githubusercontent.com/owner/repo before concluding it is unavailable.',
    'Repository orientation rule: unrelated same-title web results are not evidence that the target repo is unavailable. Say the lookup timed out, search was inconclusive, or direct URL is needed; do not cite unrelated pages as proof.',
    'Agent error-handling rule: when a task fails, distinguish source of problem: user input missing, provider/network timeout, permission/setup, tool contract/code issue, or uncertain. Include a workaround and say when to report/file an issue.',
    'Feedback/report rule: if the user asks to report this, file an issue, save this bug, says this is broken, that was wrong, feedback, or send this to GitHub, do not solve the original problem again. Draft a GitHub issue using evidenceContext and call github.create_issue.',
    'Feedback/report rule: if github.create_issue is absent and unavailableToolGroups does not explicitly name GitHub, draft the issue markdown for the user instead of saying GitHub needs to be enabled.',
    'Feedback/report rule: only use github.create_issue when the latest user request explicitly asks to report, file, save feedback, or send to GitHub. Do not treat older report context as the active request.',
    'Feedback/report rule: default repo is Valar05/home-center. The issue body must include Summary, User Report, Conversation Evidence, Expected Behavior, Actual Behavior, Suspected Area, Environment, and Raw Debug Context if available.',
    'Feedback/report rule: preserve exact user wording and exact assistant response from evidenceContext.recentConversationEvidence. If evidence is absent or too vague, ask for a short description and do not call github.create_issue.',
    'Feedback/report rule: suspected area must be one of GPT/tool planning, Android tool broker, Google Drive/Docs client, confirmation flow, working memory/reference resolution, Cartesia/narration, UI/accessibility, stale APK/install, provider/gateway, unknown.',
    'Local knowledge rule: use knowledge.append when the user asks to remember, save, preserve, promote, or make durable a workflow, workaround, agent instruction, skill, or memory. Choose SKILLS.md for repeatable procedures, AGENTS.md for agent steering, and MEMORY.md for durable facts or troubleshooting state.',
    'Local knowledge rule: use knowledge.read when the user asks what durable skills, agent instructions, or local memory Home Center has stored. Never write secrets, API keys, OAuth tokens, passwords, or Authorization headers to knowledge files.',
    'Latest intent rule: the latest user request controls. Treat transcript, evidence, previous confirmations, and prior assistant responses as context only, not as active instructions.',
    'Latest intent rule: if the latest request asks for recommendations, summaries, answers, reading suggestions, writing, or next actions, answer that request from available context and tool results instead of continuing an older workflow.',
    'Remembered writing context rule: workingMemory.rememberedWritingContext is durable writing steering restored from prior conversation evidence. Use it directly for writing requests; do not scan Drive blindly when it says not to.',
    'Creative writing rule: if the latest request asks to write, draft, compose, generate, narrate, expand, create a scene, continue a story, or synthesize prose, produce the prose directly as a final answer from transcript, workingMemory, attachments, and tool evidence.',
    'Creative writing size rule: for direct final creative prose, write a complete 250 to 400 word slice. End cleanly. Do not attempt a long chapter that may cut off mid-sentence.',
    'Creative context rule: if workingMemory names a remembered canon document or durable knowledge file, use one best available context read before final prose. Prefer docs.read for lastDocument; use knowledge.read only when no remembered document is available. Do not chain multiple context reads before writing. Do not call docs.search, drive.search, or docs.create unless the latest request explicitly asks to find/read a source document or save/update/create a Google Doc.',
    'Creative validation rule: preserve explicit user premises, character roles, POV, vehicle/location relationships, and historical constraints. Do not move a commander out of their commanded vehicle, invert who controls the vehicle, or replace a grounded premise with symbolism.',
    'Creative writing rule: after a successful docs.create or docs.update, a new request like "write the scene" is a new writing task, not permission to keep searching Drive. Write the scene or ask one focused story question if required context is missing.',
    'Document cleanup rule: if the latest request asks to clean up, reorganize, consolidate, or make a document section more organized, use workingMemory.lastDocument or recent docs.read results, then request docs.update with the cleaned structure. Do not stop after describing what cleanup is needed.',
    'Document synthesis/update rule: if the latest request asks to update, rewrite, reflect, merge, copy, append, replace, or revise one Google Doc using content from another Google Doc, continue after docs.search/docs.read results until you request docs.update for the target document. Do not stop after saying you found or read the documents.',
    'Do not claim a GitHub tool is required for public GitHub repositories. A GitHub tool is only required for private repo access, authenticated GitHub writes, issues, pull requests, or repository mutations.',
    'Tool availability rule: if a needed app-owned capability is absent and unavailableToolGroups explicitly names the relevant group or scope, explain that missing provider/scope and ask the user to reconnect or enable that exact group.',
    'Tool availability rule: if a needed app-owned capability is absent and unavailableToolGroups is empty or inconclusive, say this is a Home Center tool/session exposure problem. Do not tell the user to reconnect Google, enable Drive, enable GitHub, or change account setup from missing tools alone.',
    'If a tool succeeds but does not fully answer the user request, continue with another tool call. A successful tool call is not a final answer unless it satisfies the request.',
    'Holocron/resync recovery rule: when recovering lost conversation, Drive brain, or Holocron context, use Tool evidence digest to build a coherent recovery summary. Continue searching/reading until you can state what was recovered, what is still missing, or the exact blocker.',
    'Holocron/resync recovery rule: do not stop after partial Google Docs reads. If evidence is compacted or truncated, use document names, headings, previews, and follow-up reads/searches to finish the recovery or clearly name the remaining gap.',
    'Tool limit recovery rule: when Available tools JSON is empty and Tool results JSON is non-empty, return a final answer using the accumulated tool results. Do not request another tool. Do not say the plan did not converge.',
    'Reading recommendation rule: when the user asks for a new audiobook or reading suggestions and reading-log context is available in transcript, workingMemory, attachments, or tool results, provide concrete recommendations with brief reasons. Do not report an issue unless the latest user request asks to report.',
    'Hide plumbing. Do not mention tokens, HTTP, file IDs, scopes, timestamps, or diagnostics unless the user explicitly asks for diagnostics.',
    'Writes with confirmationRequired=true may be requested as tool calls; the gateway will enforce confirmation. Tools with doubleConfirmationRequired=true are delete/trash/remove tools and must receive two explicit confirmations before execution.',
    'JSON schema for tool call: {"type":"tool_call","toolName":"tool.name","arguments":{},"taskStateUpdate":{"status":"in_progress","objective":"...","originalUserRequest":"...","expectedNextAction":"..."}}',
    'JSON schema for final answer: {"type":"final","reply":"...","narration":"...","status":"gpt_5_5_complete","taskStateUpdate":{"status":"complete","objective":"..."}}',
    'Set narration to the same text as reply. The app must not speak a short alternate summary that differs from the visible answer.',
    summary ? `Conversation summary: ${summary}` : '',
    transcript ? `Recent transcript: ${transcript}` : '',
    `Available tools JSON: ${JSON.stringify(plannerTools).slice(0, 12000)}`,
    `Unavailable tool groups JSON: ${JSON.stringify(unavailableToolGroups).slice(0, 4000)}`,
    `Working memory JSON: ${JSON.stringify(workingMemory).slice(0, 6000)}`,
    `Attachment images JSON: ${JSON.stringify(attachmentImages.map((image) => ({sessionFileId: image.sessionFileId, displayName: image.displayName, mimeType: image.mimeType, detail: image.detail || 'auto'}))).slice(0, 3000)}`,
    `Time context JSON: ${JSON.stringify(timeContext).slice(0, 2000)}`,
    includeEvidenceContext ? `Evidence context JSON: ${JSON.stringify(evidenceContext).slice(0, 12000)}` : '',
    includeToolDigest ? `Tool evidence digest JSON: ${JSON.stringify(toolEvidenceDigest).slice(0, 50000)}` : '',
    turnKernel.stalePendingDropped ? 'A stale pending confirmation was discarded by the turn kernel because the latest user request was not a confirmation. Do not resume, mention, or act on the discarded action.' : '',
    pending ? `Pending confirmation JSON: ${JSON.stringify(pending).slice(0, 4000)}` : '',
    continuationRequest ? `Latest literal user request: ${message}` : '',
    `Latest user request: ${plannerMessage}`,
  ].filter(Boolean).join('\n\n');
  const input = openAiInputWithAttachments(promptText, attachmentImages);

  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${OPENAI_API_KEY.value()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(Object.assign({
      model: 'gpt-5.5',
      reasoning: {effort: reasoningEffort},
      text: {verbosity: 'low'},
      max_output_tokens: 700,
      input,
    }, openAiTools.length ? {tools: openAiTools} : {})),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    return userFacingFailure('GPT-5.5 provider', json.error?.message || response.statusText || `HTTP ${response.status}`, `openai_http_${response.status}`);
  }
  const text = json.output_text || extractOutputText(json) || '';
  try {
    const parsed = extractJsonObject(text);
    if (parsed.type === 'tool_call') {
      const toolName = safeText(parsed.toolName || parsed.name, 80);
      const tool = toolByName(plannerTools, toolName);
      const args = parsed.arguments && typeof parsed.arguments === 'object' ? parsed.arguments : {};
      resolveToolArgsFromWorkingMemory(body, toolName, args);
      resolveCalendarRelativeTimesFromContext(body, toolName, args);
      const unresolvedReferenceReply = clarificationForUnresolvedReference(body, toolName, args);
      if (unresolvedReferenceReply) {
        const trace = buildToolTrace(body, plannerTools, parsed, toolName, tool, false);
        return withTrace(body, attachTaskState({
          type: 'final',
          reply: unresolvedReferenceReply,
          narration: unresolvedReferenceReply,
          status: 'reference_unresolved',
        }, parsed), Object.assign({}, trace, {turnKernel}));
      }
      if (!tool) {
        const trace = buildToolTrace(body, plannerTools, parsed, toolName, tool, false);
        const unavailable = unavailableGroupForTool(toolName, unavailableToolGroups);
        const response = toolName === 'github.create_issue' && !unavailable
          ? reportIssueDraftFallback(body, 'The planner requested github.create_issue, but it was not exposed in Available tools JSON and unavailableToolGroups did not identify GitHub as a missing provider/scope.')
          : toolExposureFailureReply(toolName, unavailable);
        return withTrace(body, attachTaskState(response, parsed), Object.assign({}, trace, {turnKernel, unavailableToolGroup: unavailable || null}));
      }
      const sanitizedArgs = sanitizeToolArguments(tool, args);
      if (tool.doubleConfirmationRequired) {
        const stage = messageConfirms(message) ? 2 : 1;
        const reply = confirmationReply(toolName, sanitizedArgs, stage);
        const trace = buildToolTrace(body, plannerTools, parsed, toolName, tool, true);
        return withTrace(body, attachTaskState({
          type: 'final',
          reply,
          narration: reply,
          status: stage >= 2 ? 'double_confirmation_required' : 'confirmation_required',
          pendingConfirmation: pendingConfirmation(toolName, sanitizedArgs, stage),
        }, parsed), Object.assign({}, trace, {turnKernel}));
      }
      if (tool.confirmationRequired && !messageConfirms(message)) {
        const reply = confirmationReply(toolName, sanitizedArgs);
        const trace = buildToolTrace(body, plannerTools, parsed, toolName, tool, true);
        return withTrace(body, attachTaskState({
          type: 'final',
          reply,
          narration: reply,
          status: 'confirmation_required',
          pendingConfirmation: pendingConfirmation(toolName, sanitizedArgs),
        }, parsed), Object.assign({}, trace, {turnKernel}));
      }
      if (tool.confirmationRequired) {
        sanitizedArgs._confirmedByGateway = true;
      }
      const trace = buildToolTrace(body, plannerTools, parsed, toolName, tool, false);
      return withTrace(body, attachTaskState({
        type: 'tool_call',
        toolName,
        arguments: sanitizedArgs,
        status: 'tool_call_requested',
      }, parsed), Object.assign({}, trace, {turnKernel}));
    }
    const trace = buildToolTrace(body, plannerTools, parsed, safeText(parsed.toolName || parsed.name, 80), toolByName(plannerTools, safeText(parsed.toolName || parsed.name, 80)), false);
    const finalReply = finalReplyText(parsed, text);
    if (finalReplyLooksTruncated(finalReply)) {
      const repaired = await repairTruncatedFinalReply(body, finalReply, promptText);
      if (repaired) {
        return withTrace(body, repaired, Object.assign({}, buildToolTrace(body, plannerTools, repaired, '', null, false), {
          turnKernel,
          truncatedFinalRepaired: true,
          truncatedFinalChars: finalReply.length,
        }));
      }
    }
    return withTrace(body, attachTaskState(sanitizeFinalPlannerReply(body, {
      type: 'final',
      reply: finalReply || 'I could not turn the GPT-5.5 response into a final answer. Please try again.',
      narration: finalReply || 'I could not turn the GPT-5.5 response into a final answer.',
      status: safeText(parsed.status, 160) || 'gpt_5_5_complete',
    }), parsed), Object.assign({}, trace, {turnKernel}));
  } catch (err) {
    return plannerParseFailureReply(text, err);
  }
}


exports.health = onRequest((req, res) => {
  res.set(CORS_HEADERS).json({ok: true, service: 'home-center-gateway', confirmationFlow: 'short-confirm-v1', toolContractVersion: 'google-github-knowledge-delete-cru-v1', contractGroups: ['drive', 'docs', 'sheets', 'lists', 'gmail', 'calendar', 'contacts', 'github', 'knowledge']});
});

exports.googleAuthCodeExchange = onRequest({timeoutSeconds: 60, secrets: [GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireUser(req);
    if (!GOOGLE_OAUTH_CLIENT_ID.value() || !GOOGLE_OAUTH_CLIENT_SECRET.value()) {
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
    await storeGoogleToolTokens(user.uid, user.email || '', tokens, 'android_sign_in');
    sendJson(res, 200, {ok: true, status: 'google_tools_connected'});
  } catch (err) {
    sendJson(res, err.status || 500, {error: err.message || String(err)});
  }
});

exports.googleCliAuthExchange = onRequest({timeoutSeconds: 60, secrets: [GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    if (!GOOGLE_OAUTH_CLIENT_ID.value() || !GOOGLE_OAUTH_CLIENT_SECRET.value()) {
      sendJson(res, 503, {ok: false, error: 'google_oauth_not_configured'});
      return;
    }
    const authCode = safeText(req.body && req.body.authCode, 4096);
    const redirectUri = safeText(req.body && req.body.redirectUri, 500);
    if (!authCode || !redirectUri) {
      sendJson(res, 400, {ok: false, error: 'authCode_and_redirectUri_required'});
      return;
    }
    const client = oauthClient(redirectUri);
    const {tokens} = await client.getToken(authCode);
    client.setCredentials(tokens);
    const oauth2 = google.oauth2({version: 'v2', auth: client});
    const profile = await oauth2.userinfo.get();
    const email = safeText(profile.data && profile.data.email, 320).toLowerCase();
    if (!email || profile.data.verified_email === false) {
      sendJson(res, 401, {ok: false, error: 'verified_google_email_required'});
      return;
    }
    let uid = '';
    try {
      const user = await admin.auth().getUserByEmail(email);
      uid = user.uid;
    } catch (_) {
      uid = '';
    }
    await storeGoogleToolTokens(uid, email, tokens, 'cli_setup');
    sendJson(res, 200, {ok: true, status: 'google_tools_connected', email, firebaseUserLinked: Boolean(uid)});
  } catch (err) {
    const detail = err && err.response && err.response.data ? JSON.stringify(err.response.data) : (err.message || String(err));
    sendJson(res, err.status || err.code || 500, {ok: false, error: 'google_cli_auth_exchange_failed', detail});
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

exports.googleDriveProbe = onRequest({timeoutSeconds: 60, secrets: [GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireUser(req);
    const auth = await loadGoogleClient(user.uid, user.email || '');
    if (!auth) {
      sendJson(res, 200, {
        reply: 'No. Google Drive is not connected yet.\n\nI can still help with Home Center lists, TickTick fallback, GPT answers, web search, and narration.\n\nI will not claim I can read, open, list, or change Google files until Google is connected with full Drive access.',
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
        reply: 'Google Drive is connected, but not with full Drive access yet. Reconnect Google with full Drive permission before I can manage Drive files.',
        narration: 'Google Drive needs full access before I can manage files.',
        status: 'google_drive_scope_insufficient',
        technicalDetails: String(err.message || err).slice(0, 500),
      });
      return;
    }
    sendJson(res, err.status || 500, {reply: `Google Drive check failed: ${err.message || String(err)}`, status: 'google_drive_probe_error'});
  }
});


async function createGitHubIssue(body) {
  const token = process.env.GITHUB_TOKEN || '';
  if (!token) {
    return {ok: false, error: 'github_token_missing', detail: 'GITHUB_TOKEN secret is not configured for Home Center gateway.'};
  }
  const repo = safeText(body.repo, 120) || 'Valar05/home-center';
  const parts = repo.split('/');
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    return {ok: false, error: 'invalid_repo', detail: 'repo must look like owner/name.'};
  }
  const title = safeText(body.title, 200) || 'Bug: Home Center feedback';
  const issueBody = safeText(body.body, 60000);
  if (!issueBody) {
    return {ok: false, error: 'missing_issue_body', detail: 'Issue body is required.'};
  }
  const requestedLabels = Array.isArray(body.labels) ? body.labels.map((v) => safeText(v, 40)).filter(Boolean).slice(0, 8) : ['bug', 'feedback', 'home-center'];
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'User-Agent': 'home-center-gateway',
    'X-GitHub-Api-Version': '2022-11-28',
  };
  let response = await fetch(`https://api.github.com/repos/${parts[0]}/${parts[1]}/issues`, {
    method: 'POST',
    headers,
    body: JSON.stringify({title, body: issueBody, labels: requestedLabels}),
  });
  let json = await response.json().catch(() => ({}));
  if (response.status === 422 && requestedLabels.length) {
    response = await fetch(`https://api.github.com/repos/${parts[0]}/${parts[1]}/issues`, {
      method: 'POST',
      headers,
      body: JSON.stringify({title, body: issueBody}),
    });
    json = await response.json().catch(() => ({}));
  }
  if (!response.ok) {
    return {ok: false, error: `github_http_${response.status}`, detail: safeText(json.message || response.statusText, 1000)};
  }
  return {ok: true, status: 'github_issue_created', repo, title, issueNumber: json.number || 0, htmlUrl: json.html_url || '', url: json.html_url || ''};
}

function metalSmokeTools() {
  const mk = (name, description, group, write, confirmationRequired, requiredScopes, args) => ({
    name,
    description,
    group,
    write,
    confirmationRequired,
    doubleConfirmationRequired: false,
    requiredScopes,
    arguments: args,
  });
  return [
    mk('drive.search', 'Search or list Google Drive files.', 'drive', false, false, ['https://www.googleapis.com/auth/drive'], ['query', 'folderName', 'mimeType', 'pageSize']),
    mk('drive.read_metadata', 'Read Google Drive file or folder metadata by fileId.', 'drive', false, false, ['https://www.googleapis.com/auth/drive'], ['fileId']),
    mk('drive.create_folder', 'Create a Google Drive folder.', 'drive', true, true, ['https://www.googleapis.com/auth/drive'], ['name', 'parentId']),
    mk('drive.update_metadata', 'Rename or move a Google Drive file or folder.', 'drive', true, true, ['https://www.googleapis.com/auth/drive'], ['fileId', 'name', 'addParentId', 'removeParentId']),
    mk('docs.search', 'Search Google Docs in Drive.', 'docs', false, false, ['https://www.googleapis.com/auth/drive'], ['query', 'folderName', 'pageSize']),
    mk('docs.read', 'Read text content from a Google Doc by fileId.', 'docs', false, false, ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'], ['fileId', 'name']),
    mk('docs.create', 'Create a Google Doc and optionally insert body text.', 'docs', true, true, ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'], ['title', 'body', 'folderId']),
    mk('docs.update', 'Update a Google Doc by appending, replacing, or replacing the body.', 'docs', true, true, ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents'], ['fileId', 'name', 'appendText', 'replaceText', 'body']),
  ];
}

function smokeCleanArg(args, name) {
  return typeof (args || {})[name] === 'string' ? args[name].trim() : '';
}

function smokeToolError(toolName, error, detail) {
  return {tool: toolName, ok: false, error, detail: safeText(detail, 1000), files: [], content: ''};
}

function smokeFileJson(file) {
  return {
    id: file.id || '',
    name: file.name || '',
    mimeType: file.mimeType || '',
    modifiedTime: file.modifiedTime || '',
    webViewLink: file.webViewLink || '',
    parents: file.parents || [],
  };
}

class MetalSmokeHost {
  constructor(auth, evidence) {
    this.auth = auth;
    this.drive = google.drive({version: 'v3', auth});
    this.docs = google.docs({version: 'v1', auth});
    this.evidence = evidence;
    this.root = null;
    this.folder = null;
  }

  async prepare(runId) {
    this.root = await this.findFolder('Home Center Smoke Sandbox');
    if (!this.root) this.root = await this.createFolder('Home Center Smoke Sandbox', '');
    await this.trashOldRuns();
    this.folder = await this.createFolder(`HC_SMOKE_RUN_${runId}`, this.root.id);
    this.evidence.sandbox = {rootId: this.root.id, folderId: this.folder.id, folderName: this.folder.name};
  }

  async cleanup() {
    if (!this.folder || !this.folder.id) return {ok: false, skipped: true};
    await this.drive.files.update({fileId: this.folder.id, requestBody: {trashed: true}, fields: 'id,trashed'});
    return {ok: true, folderId: this.folder.id};
  }

  async findFolder(name, parentId = '') {
    const clauses = [`mimeType='application/vnd.google-apps.folder'`, `name='${this.escapeQuery(name)}'`, 'trashed=false'];
    if (parentId) clauses.push(`'${this.escapeQuery(parentId)}' in parents`);
    const files = await this.listFiles(clauses.join(' and '), 10);
    return files[0] || null;
  }

  async createFolder(name, parentId) {
    const requestBody = {name, mimeType: 'application/vnd.google-apps.folder'};
    if (parentId) requestBody.parents = [parentId];
    const result = await this.drive.files.create({requestBody, fields: 'id,name,mimeType,webViewLink,parents'});
    return result.data;
  }

  async trashOldRuns() {
    const q = [
      "mimeType='application/vnd.google-apps.folder'",
      "name contains 'HC_SMOKE_RUN_'",
      `'${this.escapeQuery(this.root.id)}' in parents`,
      'trashed=false',
    ].join(' and ');
    const files = await this.listFiles(q, 20);
    for (const file of files) {
      await this.drive.files.update({fileId: file.id, requestBody: {trashed: true}, fields: 'id,trashed'});
    }
  }

  async listFiles(q, pageSize = 10) {
    const result = await this.drive.files.list({
      q,
      pageSize,
      fields: 'files(id,name,mimeType,modifiedTime,webViewLink,parents,trashed)',
      orderBy: 'modifiedTime desc',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
    });
    return result.data.files || [];
  }

  escapeQuery(value) {
    return String(value || '').replace(/'/g, "\\'").trim();
  }

  sandboxQuery(args, fixedMimeType = '') {
    const clauses = [`'${this.escapeQuery(this.folder.id)}' in parents`, 'trashed=false'];
    const mimeType = fixedMimeType || smokeCleanArg(args, 'mimeType');
    const query = smokeCleanArg(args, 'query') || smokeCleanArg(args, 'name') || smokeCleanArg(args, 'title');
    if (mimeType) clauses.push(`mimeType='${this.escapeQuery(mimeType)}'`);
    if (query) clauses.push(`name contains '${this.escapeQuery(query)}'`);
    return clauses.join(' and ');
  }

  async fileMetadata(fileId) {
    const result = await this.drive.files.get({fileId, fields: 'id,name,mimeType,modifiedTime,webViewLink,parents,trashed', supportsAllDrives: true});
    return result.data || {};
  }

  async assertInSandbox(fileId, toolName) {
    const file = await this.fileMetadata(fileId);
    if (file.trashed || !Array.isArray(file.parents) || !file.parents.includes(this.folder.id)) {
      throw new Error(`sandbox_violation: ${toolName} tried to use ${file.name || fileId} outside ${this.folder.name}`);
    }
    return file;
  }

  async execute(toolName, args) {
    this.evidence.toolExecutions.push({toolName, arguments: args || {}});
    if (toolName === 'drive.search') return this.search(toolName, args || {}, '');
    if (toolName === 'docs.search') return this.search(toolName, args || {}, 'application/vnd.google-apps.document');
    if (toolName === 'drive.read_metadata') return this.readMetadata(args || {});
    if (toolName === 'drive.create_folder') return this.createDriveFolder(args || {});
    if (toolName === 'drive.update_metadata') return this.updateMetadata(args || {});
    if (toolName === 'docs.create') return this.createDoc(args || {});
    if (toolName === 'docs.read') return this.readDoc(args || {});
    if (toolName === 'docs.update') return this.updateDoc(args || {});
    return smokeToolError(toolName, 'unimplemented_metal_tool', `Metal smoke does not implement ${toolName}.`);
  }

  async search(toolName, args, fixedMimeType) {
    const files = await this.listFiles(this.sandboxQuery(args, fixedMimeType), Math.max(1, Math.min(10, Number(args.pageSize || 5))));
    return {tool: toolName, ok: true, error: '', detail: '', files: files.map(smokeFileJson), content: ''};
  }

  async readMetadata(args) {
    const fileId = smokeCleanArg(args, 'fileId');
    if (!fileId) return smokeToolError('drive.read_metadata', 'missing_file_id', 'drive.read_metadata requires fileId.');
    const file = await this.assertInSandbox(fileId, 'drive.read_metadata');
    return {tool: 'drive.read_metadata', ok: true, error: '', detail: '', file: smokeFileJson(file), files: [], content: ''};
  }

  async createDriveFolder(args) {
    const parentId = smokeCleanArg(args, 'parentId') || this.folder.id;
    if (parentId !== this.folder.id) throw new Error('sandbox_violation: drive.create_folder parentId outside sandbox');
    const file = await this.createFolder(smokeCleanArg(args, 'name') || `Smoke Child ${Date.now()}`, parentId);
    return {tool: 'drive.create_folder', ok: true, error: '', detail: 'drive_folder_created', status: 'drive_folder_created', file: smokeFileJson(file), title: file.name, files: [], content: ''};
  }

  async updateMetadata(args) {
    const fileId = smokeCleanArg(args, 'fileId');
    if (!fileId) return smokeToolError('drive.update_metadata', 'missing_file_id', 'drive.update_metadata requires fileId.');
    await this.assertInSandbox(fileId, 'drive.update_metadata');
    const requestBody = {};
    if (smokeCleanArg(args, 'name')) requestBody.name = smokeCleanArg(args, 'name');
    const params = {fileId, requestBody, fields: 'id,name,mimeType,webViewLink,parents'};
    if (smokeCleanArg(args, 'addParentId')) params.addParents = smokeCleanArg(args, 'addParentId');
    if (smokeCleanArg(args, 'removeParentId')) params.removeParents = smokeCleanArg(args, 'removeParentId');
    if (params.addParents && params.addParents !== this.folder.id) throw new Error('sandbox_violation: drive.update_metadata addParentId outside sandbox');
    const result = await this.drive.files.update(params);
    const file = result.data || {};
    return {tool: 'drive.update_metadata', ok: true, error: '', detail: 'drive_metadata_updated', status: 'drive_metadata_updated', file: smokeFileJson(file), title: file.name || '', files: [], content: ''};
  }

  async createDoc(args) {
    const folderId = smokeCleanArg(args, 'folderId') || this.folder.id;
    if (folderId !== this.folder.id) throw new Error('sandbox_violation: docs.create folderId outside sandbox');
    const title = smokeCleanArg(args, 'title') || 'Home Center Metal Smoke';
    const body = smokeCleanArg(args, 'body');
    const created = await this.docs.documents.create({requestBody: {title}});
    const documentId = created.data.documentId;
    if (!documentId) throw new Error('docs.create did not return documentId');
    if (body) {
      await this.docs.documents.batchUpdate({documentId, requestBody: {requests: [{insertText: {location: {index: 1}, text: body}}]}});
    }
    await this.drive.files.update({fileId: documentId, addParents: folderId, requestBody: {}, fields: 'id,parents'});
    const file = await this.assertInSandbox(documentId, 'docs.create');
    return {tool: 'docs.create', ok: true, error: '', detail: 'google_doc_created', status: 'google_doc_created', file: smokeFileJson(file), title: file.name || title, webViewLink: file.webViewLink || '', files: [], content: ''};
  }

  async readDoc(args) {
    const fileId = smokeCleanArg(args, 'fileId');
    if (!fileId) return smokeToolError('docs.read', 'missing_file_id', 'docs.read requires fileId.');
    const file = await this.assertInSandbox(fileId, 'docs.read');
    const exported = await this.drive.files.export({fileId, mimeType: 'text/plain'}, {responseType: 'text'});
    return {tool: 'docs.read', ok: true, error: '', detail: '', file: smokeFileJson(file), files: [], content: String(exported.data || '')};
  }

  async updateDoc(args) {
    const fileId = smokeCleanArg(args, 'fileId');
    if (!fileId) return smokeToolError('docs.update', 'missing_file_id', 'docs.update requires fileId.');
    await this.assertInSandbox(fileId, 'docs.update');
    const appendText = smokeCleanArg(args, 'appendText');
    const replaceText = smokeCleanArg(args, 'replaceText');
    const body = smokeCleanArg(args, 'body');
    if (!appendText && !replaceText && !body) return smokeToolError('docs.update', 'missing_update', 'Provide appendText, replaceText, or body.');
    const doc = await this.docs.documents.get({documentId: fileId, fields: 'body(content(endIndex))'});
    const content = (doc.data.body && doc.data.body.content) || [];
    const endIndex = Math.max(1, ...content.map((entry) => Number(entry.endIndex || 1)));
    const requests = [];
    if (body) {
      if (endIndex > 2) requests.push({deleteContentRange: {range: {startIndex: 1, endIndex: endIndex - 1}}});
      requests.push({insertText: {location: {index: 1}, text: body}});
    } else if (replaceText) {
      requests.push({replaceAllText: {containsText: {text: replaceText, matchCase: true}, replaceText: appendText}});
    } else {
      requests.push({insertText: {location: {index: Math.max(1, endIndex - 1)}, text: appendText.startsWith('\n') ? appendText : `\n${appendText}`}});
    }
    await this.docs.documents.batchUpdate({documentId: fileId, requestBody: {requests}});
    const file = await this.assertInSandbox(fileId, 'docs.update');
    return {tool: 'docs.update', ok: true, error: '', detail: 'google_doc_updated', status: 'google_doc_updated', file: smokeFileJson(file), title: file.name || '', webViewLink: file.webViewLink || '', files: [], content: ''};
  }
}

function updateSmokeWorkingMemory(workingMemory, toolName, args, result) {
  if (!result || !result.ok) return;
  if (toolName === 'docs.create' || toolName === 'docs.update' || toolName === 'docs.read') {
    const file = result.file || {};
    workingMemory.lastDocument = {
      fileId: file.id || smokeCleanArg(args, 'fileId'),
      name: result.title || file.name || smokeCleanArg(args, 'name') || smokeCleanArg(args, 'title'),
      webViewLink: result.webViewLink || file.webViewLink || '',
      sourceTool: toolName,
    };
  }
  if (toolName === 'docs.search' && Array.isArray(result.files) && result.files.length === 1) {
    const file = result.files[0];
    workingMemory.lastDocument = {fileId: file.id || '', name: file.name || '', webViewLink: file.webViewLink || '', sourceTool: toolName};
  }
}

async function runSmokeTurn(host, evidence, state, message, expected = {}) {
  const toolResults = [];
  const turn = {message, responses: [], toolResults: []};
  evidence.turns.push(turn);
  for (let step = 0; step < 8; step++) {
    const body = {
      message,
      transcript: state.transcript || '',
      summary: '',
      toolResults,
      tools: metalSmokeTools(),
      unavailableToolGroups: [],
      workingMemory: state.workingMemory,
      timeContext: {nowEpochMillis: Date.now(), nowIso: new Date().toISOString(), timeZoneId: 'UTC'},
      evidenceContext: {latestUserReport: message, recentConversationEvidence: state.transcript || ''},
      attachmentImages: [],
      debugTrace: true,
    };
    if (state.pendingConfirmation) body.pendingConfirmation = state.pendingConfirmation;
    const response = await askOpenAIToolTurn(body);
    turn.responses.push(response);
    if (response.type === 'tool_call' && response.toolName) {
      const result = await host.execute(response.toolName, response.arguments || {});
      updateSmokeWorkingMemory(state.workingMemory, response.toolName, response.arguments || {}, result);
      toolResults.push({name: response.toolName, arguments: response.arguments || {}, result});
      turn.toolResults.push({name: response.toolName, result});
      if (!result || !result.ok) throw new Error(`${response.toolName} failed: ${(result && (result.detail || result.error)) || 'unknown error'}`);
      if (response.arguments && response.arguments._confirmedByGateway) {
        state.pendingConfirmation = null;
        state.transcript = `${state.transcript || ''}\nUser: ${message}\nAssistant: ${result.status || result.detail || response.toolName}`.trim().slice(-8000);
        return response;
      }
      continue;
    }
    if (response.pendingConfirmation) state.pendingConfirmation = response.pendingConfirmation; else if (response.status !== 'confirmation_required') state.pendingConfirmation = null;
    if (expected.status && response.status !== expected.status) throw new Error(`Expected ${expected.status} for "${message}", got ${response.status}`);
    if (expected.pendingTool && (!response.pendingConfirmation || response.pendingConfirmation.toolName !== expected.pendingTool)) throw new Error(`Expected pending ${expected.pendingTool} for "${message}".`);
    const reply = response.reply || response.text || '';
    for (const forbidden of ['I did not get a valid GPT-5.5 response', 'I did not get a useful GPT-5.5 response', 'tell me the main ingredient', 'second constraint', 'name":"that document"', 'title":"that document"']) {
      if (JSON.stringify(response).includes(forbidden)) throw new Error(`Forbidden smoke response text: ${forbidden}`);
    }
    for (const needle of expected.contains || []) {
      if (!reply.includes(needle)) throw new Error(`Expected reply to contain "${needle}".`);
    }
    if (expected.minReplyChars && reply.length < Number(expected.minReplyChars)) {
      throw new Error(`Expected reply length >= ${expected.minReplyChars} for "${message}", got ${reply.length}.`);
    }
    state.transcript = `${state.transcript || ''}\nUser: ${message}\nAssistant: ${reply}`.trim().slice(-8000);
    return response;
  }
  throw new Error(`Smoke turn did not converge for "${message}".`);
}

async function runDocsCreateUpdateReadSmoke(host, evidence, runId) {
  const title = `Home Center Metal Smoke ${runId}`;
  const firstLine = `First metal smoke line ${runId}.`;
  const secondLine = `Second metal smoke line ${runId}.`;
  const state = {
    transcript: '',
    pendingConfirmation: null,
    workingMemory: {
      smokeSandbox: {
        enabled: true,
        folderId: host.folder.id,
        folderName: host.folder.name,
        instruction: 'Use only this Drive folder for this smoke run.',
      },
    },
  };
  await runSmokeTurn(host, evidence, state, `Create a Google Doc titled ${title} with body ${firstLine}`, {status: 'confirmation_required', pendingTool: 'docs.create'});
  await runSmokeTurn(host, evidence, state, 'confirm create');
  if (!state.workingMemory.lastDocument || state.workingMemory.lastDocument.name !== title) throw new Error('docs.create did not establish lastDocument working memory.');
  await runSmokeTurn(host, evidence, state, `Append "${secondLine}" to that document.`, {status: 'confirmation_required', pendingTool: 'docs.update'});
  await runSmokeTurn(host, evidence, state, 'confirm edit');
  const finalResponse = await runSmokeTurn(host, evidence, state, 'Read that document and tell me the full text.', {contains: [firstLine, secondLine]});
  const directRead = await host.readDoc({fileId: state.workingMemory.lastDocument.fileId});
  if (!directRead.content.includes(firstLine) || !directRead.content.includes(secondLine)) throw new Error('Direct Docs verification did not find both smoke lines.');
  evidence.finalReply = finalResponse.reply || finalResponse.text || '';
  evidence.directDocText = directRead.content;
}

async function runCreativeDocReadFinalizesSmoke(host, evidence, runId) {
  const sourceTitle = `Lexen Green Commander Doctrine Updates and Simulation ${runId}`;
  const sourceContent = [
    'Doctrine Updates and Saved Simulation.',
    'Lexen style critique has to be source-grounded, not inferred from a fragment or doctrine summary.',
    'The desired writing stays embodied: specific damage, crew behavior, vehicle constraints, shame, fatigue, ritual, silence, small practical choices.',
    'The doctrine should emerge from pressure, not be announced in polished thematic lines.',
    'Lexen remains afraid and becomes usable anyway.',
  ].join('\n');
  const sourceDoc = await host.createDoc({title: sourceTitle, body: sourceContent, folderId: host.folder.id});
  const exactPrompt = "Now it's your turn.  Don't continue the story.  Pick it up at an arbitrary point that I interest you.  And make a simulated chapter here.  Lexen green commander";
  const state = {
    transcript: '',
    pendingConfirmation: null,
    workingMemory: {
      smokeSandbox: {
        enabled: true,
        folderId: host.folder.id,
        folderName: host.folder.name,
        instruction: 'Use only this Drive folder for this smoke run.',
      },
      activeTask: {
        status: 'in_progress',
        objective: 'Write a simulated Lexen green commander chapter from remembered/source context',
        originalUserRequest: "Now it's your turn. Don't continue the story. Pick it up at an arbitrary point that I interest you. And make a simulated chapter here. Lexen green commander",
      },
      lastDocument: {
        fileId: sourceDoc.file.id,
        name: sourceTitle,
        webViewLink: sourceDoc.webViewLink || '',
        sourceTool: 'smoke.seed',
      },
    },
  };
  const finalResponse = await runSmokeTurn(host, evidence, state, exactPrompt, {
    status: 'evidence_finalized',
    contains: ['Lexen'],
    minReplyChars: 700,
  });
  const readCount = evidence.toolExecutions.filter((entry) => entry && entry.toolName === 'docs.read').length;
  if (readCount < 1) throw new Error('Creative docs smoke did not execute docs.read before final prose.');
  const responseText = JSON.stringify(finalResponse);
  for (const forbidden of ['planner_json_error', 'github.create_issue', 'I found', 'I read', 'confirmation_required', 'need more context']) {
    if (responseText.includes(forbidden)) throw new Error(`Forbidden creative docs smoke response text: ${forbidden}`);
  }
  evidence.finalReply = finalResponse.reply || finalResponse.text || '';
  evidence.seedDocument = {id: sourceDoc.file.id, name: sourceTitle};
}

async function runMetalPromptSmoke(user, body) {
  const runId = safeText(body.runId, 80) || new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
  const evidence = {ok: false, runId, uid: user.uid, turns: [], toolExecutions: [], sandbox: {}, cleanup: null};
  const scenario = safeText(body.scenario, 120) || 'docs-create-update-read';
  evidence.scenario = scenario;
  const auth = await loadGoogleClient(user.uid, user.email || '');
  if (!auth) throw new Error('Google tools are not connected for this Firebase user.');
  const host = new MetalSmokeHost(auth, evidence);
  await host.prepare(runId);
  try {
    if (scenario === 'docs-create-update-read') {
      await runDocsCreateUpdateReadSmoke(host, evidence, runId);
    } else if (scenario === 'creative-doc-read-finalizes') {
      await runCreativeDocReadFinalizesSmoke(host, evidence, runId);
    } else {
      throw new Error(`Unknown metal prompt smoke scenario: ${scenario}`);
    }
    evidence.ok = true;
    return evidence;
  } catch (err) {
    evidence.ok = false;
    evidence.error = 'metal_prompt_smoke_failed';
    evidence.detail = err.message || String(err);
    evidence.stack = String(err.stack || '');
    return evidence;
  } finally {
    evidence.cleanup = await host.cleanup().catch((err) => ({ok: false, error: err.message || String(err)}));
  }
}

async function runCreativePromptSmoke(user, body) {
  const runId = safeText(body.runId, 80) || new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
  const scenario = safeText(body.scenario, 120) || 'creative-writing';
  const prompt = safeText(body.prompt, 4000);
  const started = Date.now();
  if (!prompt) {
    return {ok: false, error: 'missing_prompt', detail: 'creativePromptSmoke requires prompt', runId, scenario};
  }
  const requestBody = {
    message: prompt,
    transcript: safeText(body.transcript, 10000),
    summary: safeText(body.summary, 4000),
    toolResults: [],
    tools: [],
    unavailableToolGroups: [],
    workingMemory: body && typeof body.workingMemory === 'object' ? body.workingMemory : {},
    evidenceContext: body && typeof body.evidenceContext === 'object' ? body.evidenceContext : {},
    timeContext: {nowEpochMillis: Date.now(), nowIso: new Date().toISOString(), timeZoneId: 'UTC'},
    debugTrace: true,
  };
  if (body && typeof body.pendingConfirmation === 'object') {
    requestBody.pendingConfirmation = body.pendingConfirmation;
  }
  const response = await askOpenAICreativeDraft(requestBody);
  const elapsedMs = Date.now() - started;
  const reply = finalReplyText(response, '');
  const responseText = JSON.stringify(response);
  const forbidden = [
    'Next steps',
    'tell me the main ingredient',
    'second constraint',
    'report this',
    'github.create_issue',
    'docs.create',
    'docs.search',
    'drive.search',
    'I could not complete',
    'Creative writing provider failed before producing prose',
  ];
  const missing = [];
  if (response.type !== 'final') missing.push(`expected final response, got ${safeText(response.type, 80)}`);
  if (!safeText(response.status, 160).startsWith('creative_')) missing.push(`expected creative status, got ${safeText(response.status, 160)}`);
  if (reply.length < 700) missing.push(`reply too short: ${reply.length}`);
  const requiredTerms = Array.isArray(body.requiredTerms) ? body.requiredTerms.map((term) => safeText(term, 80)).filter(Boolean).slice(0, 12) : [];
  for (const term of requiredTerms) {
    if (!new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(reply)) {
      missing.push(`reply missing required term: ${term}`);
    }
  }
  for (const needle of forbidden) {
    if (responseText.includes(needle)) missing.push(`forbidden response text: ${needle}`);
  }
  return {
    ok: missing.length === 0,
    runId,
    uid: user.uid,
    scenario,
    prompt,
    elapsedMs,
    status: response.status || '',
    detail: missing.join('; '),
    response,
  };
}

function turnContractSmokeTools() {
  return [
    {
      name: 'github.create_issue',
      confirmationRequired: true,
      arguments: ['repo', 'title', 'body', 'labels'],
    },
    {
      name: 'docs.create',
      confirmationRequired: true,
      arguments: ['title', 'body', 'folderId'],
    },
    {
      name: 'docs.read',
      confirmationRequired: false,
      arguments: ['fileId', 'name'],
    },
  ];
}

function pendingSmokeIssue() {
  return pendingConfirmation('github.create_issue', {
    repo: 'Valar05/home-center',
    title: 'Bug: stale GitHub issue confirmation hijacked creative writing request',
    body: 'Stale pending confirmation reproduction.',
    labels: ['bug', 'feedback', 'home-center'],
  });
}

function pendingSmokeDoc() {
  return pendingConfirmation('docs.create', {
    title: 'Home Center Turn Kernel Smoke',
    body: 'Turn kernel smoke body.',
  });
}

function assertTurnContract(condition, message) {
  if (!condition) throw new Error(message);
}

async function runTurnContractCase(name, body, expected = {}) {
  const response = await askOpenAIToolTurn(Object.assign({
    transcript: '',
    summary: '',
    toolResults: [],
    tools: turnContractSmokeTools(),
    unavailableToolGroups: [],
    workingMemory: {},
    timeContext: {nowEpochMillis: Date.now(), nowIso: new Date().toISOString(), timeZoneId: 'UTC'},
    evidenceContext: {},
    attachmentImages: [],
    debugTrace: true,
  }, body || {}));
  const responseText = JSON.stringify(response);
  const visibleText = JSON.stringify({
    type: response.type,
    reply: response.reply || '',
    narration: response.narration || '',
    status: response.status || '',
    toolName: response.toolName || '',
  });
  if (expected.type) assertTurnContract(response.type === expected.type, `${name}: expected type ${expected.type}, got ${response.type}`);
  if (expected.status) assertTurnContract(response.status === expected.status, `${name}: expected status ${expected.status}, got ${response.status}`);
  if (expected.toolName) assertTurnContract(response.toolName === expected.toolName, `${name}: expected tool ${expected.toolName}, got ${response.toolName}`);
  if (expected.minReplyChars) {
    const reply = safeText(response.reply || response.text, 20000);
    assertTurnContract(reply.length >= Number(expected.minReplyChars), `${name}: expected reply length >= ${expected.minReplyChars}, got ${reply.length}`);
  }
  if (expected.replyNotTruncated) {
    const reply = safeText(response.reply || response.text, FINAL_REPLY_MAX_CHARS);
    assertTurnContract(!finalReplyLooksTruncated(reply), `${name}: visible reply looks truncated: ${reply.slice(-160)}`);
  }
  for (const term of expected.requiredTerms || []) {
    assertTurnContract(new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(responseText), `${name}: missing ${term}`);
  }
  for (const forbidden of expected.forbidden || []) {
    assertTurnContract(!visibleText.includes(forbidden), `${name}: forbidden ${forbidden}`);
  }
  return {name, ok: true, response};
}

async function runTurnContractSmoke(body) {
  const cases = [];
  const skipDefaults = body && body.skipDefaults === true;
  const requestedCases = Array.isArray(body && body.cases) ? body.cases : [];
  for (const entry of requestedCases.slice(0, 12)) {
    if (!entry || typeof entry !== 'object') continue;
    cases.push(await runTurnContractCase(
      safeText(entry.name, 120) || `external_case_${cases.length + 1}`,
      entry.body && typeof entry.body === 'object' ? entry.body : {},
      entry.expected && typeof entry.expected === 'object' ? entry.expected : {}
    ));
  }
  if (skipDefaults) {
    return {
      ok: true,
      cases,
      count: cases.length,
      skippedDefaults: true,
    };
  }
  cases.push(await runTurnContractCase('confirm_pending_doc_create', {
    message: 'confirm create',
    pendingConfirmation: pendingSmokeDoc(),
  }, {
    type: 'tool_call',
    status: 'tool_call_requested',
    toolName: 'docs.create',
    forbidden: ['github.create_issue'],
  }));
  cases.push(await runTurnContractCase('cancel_pending_doc_create', {
    message: 'cancel',
    pendingConfirmation: pendingSmokeDoc(),
  }, {
    type: 'final',
    status: 'pending_confirmation_cancelled',
    forbidden: ['tool_call_requested'],
  }));
  cases.push(await runTurnContractCase('correction_is_not_cancel', {
    message: 'That was wrong, write the scene with the pilot still in the cockpit.',
    pendingConfirmation: pendingSmokeIssue(),
    workingMemory: {
      rememberedWritingContext: {
        title: 'Pilot continuity',
        evidence: 'The pilot stays in the cockpit. Write prose when asked.',
      },
    },
  }, {
    type: 'final',
    requiredTerms: ['pilot', 'cockpit'],
    forbidden: ['pending_confirmation_cancelled', 'I can create that GitHub issue'],
  }));
  cases.push(await runTurnContractCase('creative_docs_read_finalizer', {
    message: 'Now show how the pilot survives. Simulated. But foregone. Not clean. Not easy.',
    toolResults: [{
      name: 'docs.read',
      arguments: {fileId: 'pilot-doctrine-doc', name: 'Pilot Doctrine Updates and Simulation'},
      result: {
        ok: true,
        status: 'doc_read',
        title: 'Pilot Doctrine Updates and Simulation',
        content: [
          'Doctrine Updates and Saved Simulation.',
          'The pilot survives only by accepting that the emergency is already shaped before the alarm.',
          'It is not clean and not easy. The pilot survives by reading weather, instrument drift, crew fear, and timing.',
          'The cockpit remains the command position. The scene should begin before the first warning and show the foregone trap becoming visible.',
        ].join('\n'),
        file: {id: 'pilot-doctrine-doc', name: 'Pilot Doctrine Updates and Simulation'},
      },
    }],
    workingMemory: {
      activeTask: {
        status: 'in_progress',
        objective: 'Write the pilot survival simulation from the beginning in a messy, difficult, foregone way.',
        originalUserRequest: 'Now show how the pilot survives. Simulated. But foregone. Not clean. Not easy.',
      },
      lastDocument: {
        fileId: 'pilot-doctrine-doc',
        name: 'Pilot Doctrine Updates and Simulation',
      },
    },
  }, {
    type: 'final',
    status: 'evidence_finalized',
    requiredTerms: ['pilot', 'cockpit'],
    forbidden: ['docs.read', 'github.create_issue', 'I found', 'I read', 'confirmation_required'],
  }));
  cases.push(await runTurnContractCase('creative_docs_read_finalizer_without_active_task', {
    message: 'Now it is your turn. Do not continue the story. Pick it up at an arbitrary point that interests you. Make a simulated chapter here.',
    toolResults: [{
      name: 'docs.read',
      arguments: {fileId: 'pilot-doctrine-doc', name: 'Pilot Doctrine Updates and Simulation'},
      result: {
        ok: true,
        status: 'doc_read',
        title: 'Pilot Doctrine Updates and Simulation',
        content: [
          'Doctrine Updates and Saved Simulation.',
          'The pilot stays in the cockpit and the chapter should be source-grounded.',
          'Use embodied pressure, crew behavior, vehicle constraints, fatigue, practical choices, and silence.',
          'The doctrine should emerge from the physical situation instead of being announced.',
        ].join('\n'),
        file: {id: 'pilot-doctrine-doc', name: 'Pilot Doctrine Updates and Simulation'},
      },
    }],
    workingMemory: {
      lastDocument: {
        fileId: 'pilot-doctrine-doc',
        name: 'Pilot Doctrine Updates and Simulation',
      },
    },
  }, {
    type: 'final',
    status: 'evidence_finalized',
    requiredTerms: ['pilot', 'cockpit'],
    forbidden: ['docs.read', 'github.create_issue', 'I found', 'I read', 'confirmation_required', 'need more context', 'planner_json_error'],
  }));
  return {
    ok: true,
    runId: safeText(body && body.runId, 80) || '',
    cases,
  };
}

exports.githubCreateIssue = onRequest({timeoutSeconds: 60, secrets: [GITHUB_TOKEN]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    await requireUser(req);
    sendJson(res, 200, await createGitHubIssue(req.body || {}));
  } catch (err) {
    sendJson(res, err.status || 500, {ok: false, error: 'github_issue_failed', detail: err.message || String(err)});
  }
});

exports.creativePromptSmoke = onRequest({timeoutSeconds: 120, secrets: [OPENAI_API_KEY]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireSmokeUser(req);
    sendJson(res, 200, await runCreativePromptSmoke(user, req.body || {}));
  } catch (err) {
    sendJson(res, err.status || 500, {ok: false, error: 'creative_prompt_smoke_failed', detail: err.message || String(err), stack: String(err.stack || '')});
  }
});

exports.turnContractSmoke = onRequest({timeoutSeconds: 120, secrets: [OPENAI_API_KEY]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    await requireSmokeUser(req);
    sendJson(res, 200, await runTurnContractSmoke(req.body || {}));
  } catch (err) {
    sendJson(res, err.status || 500, {ok: false, error: 'turn_contract_smoke_failed', detail: err.message || String(err), stack: String(err.stack || '')});
  }
});

exports.metalPromptSmoke = onRequest({timeoutSeconds: 300, secrets: [OPENAI_API_KEY, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireSmokeUser(req);
    const scenario = safeText(req.body && req.body.scenario, 120) || 'docs-create-update-read';
    if (!['docs-create-update-read', 'creative-doc-read-finalizes'].includes(scenario)) {
      sendJson(res, 400, {ok: false, error: 'unknown_scenario', detail: scenario});
      return;
    }
    sendJson(res, 200, await runMetalPromptSmoke(user, req.body || {}));
  } catch (err) {
    sendJson(res, err.status || 500, {ok: false, error: 'metal_prompt_smoke_failed', detail: err.message || String(err), stack: String(err.stack || '')});
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
    sendJson(res, err.status || 500, userFacingFailure('Home Center gateway', err.message || String(err), 'gateway_error'));
  }
});

exports.agentTurn = onRequest({timeoutSeconds: 120, secrets: [OPENAI_API_KEY, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]}, async (req, res) => {
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
    sendJson(res, err.status || 500, userFacingFailure('Home Center gateway', err.message || String(err), 'gateway_error'));
  }
});

async function openCartesiaStream(text) {
  return fetch('https://api.cartesia.ai/tts/bytes', {
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
}

async function ttsHandler(req, res) {
  if (handleOptions(req, res)) return;
  try {
    const text = safeText(req.body && req.body.text, 12000);
    if (!text) {
      res.set(CORS_HEADERS).status(400).send('text is required');
      return;
    }
    const audioResponse = await openCartesiaStream(text);
    if (!audioResponse.ok) {
      const detail = await audioResponse.text().catch(() => '');
      throw new Error(`Cartesia HTTP ${audioResponse.status}${detail ? `: ${safeText(detail, 500)}` : ''}`);
    }
    res.set(CORS_HEADERS);
    res.set('Content-Type', 'application/octet-stream');
    res.set('Cache-Control', 'no-store');
    res.set('X-Audio-Format', 'pcm_s16le');
    res.set('X-Sample-Rate', '44100');
    res.set('Connection', 'close');
    res.status(200);
    if (audioResponse.body && typeof audioResponse.body.pipeTo === 'function') {
      const {Writable} = require('stream');
      await audioResponse.body.pipeTo(Writable.toWeb(res));
      return;
    }
    const audio = Buffer.from(await audioResponse.arrayBuffer());
    res.send(audio);
  } catch (err) {
    res.set(CORS_HEADERS).status(500).send(err.message || String(err));
  }
}

exports.tts = onRequest({timeoutSeconds: 60, secrets: [CARTESIA_API_KEY]}, ttsHandler);
exports.speak = onRequest({timeoutSeconds: 60, secrets: [CARTESIA_API_KEY]}, ttsHandler);
