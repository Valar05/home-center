const {onRequest} = require('firebase-functions/v2/https');
const {defineSecret} = require('firebase-functions/params');
const admin = require('firebase-admin');
const {google} = require('googleapis');

admin.initializeApp();

const OPENAI_API_KEY = defineSecret('OPENAI_API_KEY');
const CARTESIA_API_KEY = defineSecret('CARTESIA_API_KEY');
const GOOGLE_OAUTH_CLIENT_ID = defineSecret('GOOGLE_OAUTH_CLIENT_ID');
const GOOGLE_OAUTH_CLIENT_SECRET = defineSecret('GOOGLE_OAUTH_CLIENT_SECRET');

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
    GOOGLE_OAUTH_CLIENT_ID.value(),
    GOOGLE_OAUTH_CLIENT_SECRET.value(),
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
    return {reply: 'Google tools are not connected yet. Sign in with Google again from Home Center so I can connect Drive and Docs.', status: 'google_tools_missing'};
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
    'Capabilities available through this app: OpenAI GPT-5.5, hosted web search, Google Drive/Docs/Gmail/Calendar through server-side tokens, Home Center Firestore lists, TickTick fallback lists, and Cartesia narration.',
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

exports.health = onRequest((req, res) => {
  res.set(CORS_HEADERS).json({ok: true, service: 'home-center-gateway'});
});

exports.googleAuthCodeExchange = onRequest({secrets: [GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireUser(req);
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

exports.agentTurn = onRequest({timeoutSeconds: 120, secrets: [OPENAI_API_KEY, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET]}, async (req, res) => {
  if (handleOptions(req, res)) return;
  try {
    const user = await requireUser(req);
    const message = safeText(req.body && req.body.message, 4000);
    if (!message) {
      sendJson(res, 400, {reply: 'Tell me what you want Home Center to do.', status: 'missing_message'});
      return;
    }
    if (/create\s+(?:a\s+)?google\s+doc/i.test(message) && !wantsConfirmedCreateDoc(message)) {
      sendJson(res, 200, {
        reply: 'Create Google Doc\nI can do that. Say: confirm create Google Doc titled <title> with body <text>.',
        narration: 'I can create that Google Doc after you confirm the title and body.',
        status: 'confirmation_required',
      });
      return;
    }
    if (wantsConfirmedCreateDoc(message)) {
      sendJson(res, 200, await createGoogleDoc(user.uid, message));
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
      model_id: 'sonic-english',
      transcript: text,
      voice: {mode: 'id', id: process.env.CARTESIA_VOICE_ID || 'a0e99841-438c-4a64-b679-ae501e7d6091'},
      output_format: {container: 'raw', encoding: 'pcm_s16le', sample_rate: 22050},
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
