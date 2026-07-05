#!/usr/bin/env node
import {execFileSync, spawnSync} from 'node:child_process';
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {resolve, join} from 'node:path';
import {randomBytes} from 'node:crypto';

const ROOT = resolve(new URL('..', import.meta.url).pathname);
const GATEWAY_BASE = process.env.HOME_CENTER_GATEWAY_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net';
const PORT = Number(process.env.HOME_CENTER_GOOGLE_SETUP_PORT || 8789);
const REDIRECT_URI = process.env.HOME_CENTER_GOOGLE_SETUP_REDIRECT_URI || `http://127.0.0.1:${PORT}/oauth2callback`;
const SCOPES = [
  'openid',
  'email',
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/spreadsheets',
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/gmail.compose',
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/calendar.events',
  'https://www.googleapis.com/auth/contacts.readonly',
];

function webClientId() {
  if (process.env.GOOGLE_OAUTH_CLIENT_ID) return process.env.GOOGLE_OAUTH_CLIENT_ID.trim();
  const config = JSON.parse(readFileSync(join(ROOT, 'app', 'google-services.json'), 'utf8'));
  for (const client of config.client || []) {
    for (const oauth of client.oauth_client || []) {
      if (oauth.client_type === 3 && oauth.client_id) return oauth.client_id;
    }
  }
  throw new Error('No web OAuth client id found. Set GOOGLE_OAUTH_CLIENT_ID or refresh app/google-services.json.');
}

function openUrl(url) {
  const result = spawnSync('termux-open-url', [url], {stdio: 'ignore'});
  if (result.status === 0) return;
  console.log(`Open this URL:\n${url}\n`);
}

function consoleUrl(clientId) {
  return `https://console.cloud.google.com/apis/credentials/oauthclient/${encodeURIComponent(clientId)}?project=home-center-dclar`;
}

function printRedirectInstructions(clientId) {
  console.log([
    'Google OAuth setup requirement:',
    `OAuth web client: ${clientId}`,
    `Authorized redirect URI: ${REDIRECT_URI}`,
    `Console URL: ${consoleUrl(clientId)}`,
    '',
    'If Google shows redirect_uri_mismatch, add the Authorized redirect URI above to that OAuth web client, save, then rerun this command.',
    '',
  ].join('\n'));
}

function postJson(url, body) {
  return fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).then(async (response) => {
    const text = await response.text();
    const json = text ? JSON.parse(text) : {};
    if (!response.ok) {
      const detail = json.detail || json.error || text;
      if (String(detail).includes('redirect_uri_mismatch')) {
        throw new Error(`redirect_uri_mismatch: add this exact redirect URI to the Google OAuth web client:\n${REDIRECT_URI}`);
      }
      throw new Error(`googleCliAuthExchange HTTP ${response.status}: ${text.slice(0, 2000)}`);
    }
    return json;
  });
}

function waitForCode(state) {
  return new Promise((resolveCode, reject) => {
    const server = createServer((req, res) => {
      try {
        const url = new URL(req.url || '/', REDIRECT_URI);
        if (url.pathname !== '/oauth2callback') {
          res.writeHead(404).end('Not found');
          return;
        }
        if (url.searchParams.get('state') !== state) {
          res.writeHead(400).end('State mismatch.');
          reject(new Error('OAuth state mismatch.'));
          server.close();
          return;
        }
        const error = url.searchParams.get('error');
        if (error) {
          res.writeHead(400).end(`Google returned error: ${error}`);
          reject(new Error(`Google OAuth error: ${error}`));
          server.close();
          return;
        }
        const code = url.searchParams.get('code');
        if (!code) {
          res.writeHead(400).end('Missing code.');
          reject(new Error('OAuth callback did not include a code.'));
          server.close();
          return;
        }
        res.writeHead(200, {'Content-Type': 'text/plain'}).end('Home Center Google tools connected. You can return to Termux.');
        resolveCode(code);
        server.close();
      } catch (err) {
        reject(err);
        server.close();
      }
    });
    server.on('error', reject);
    server.listen(PORT, '127.0.0.1');
  });
}

async function main() {
  const clientId = webClientId();
  if (process.argv.includes('--print-setup')) {
    printRedirectInstructions(clientId);
    return;
  }
  const state = randomBytes(18).toString('hex');
  const codePromise = waitForCode(state);
  const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
  authUrl.searchParams.set('client_id', clientId);
  authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('scope', SCOPES.join(' '));
  authUrl.searchParams.set('access_type', 'offline');
  authUrl.searchParams.set('prompt', 'consent');
  authUrl.searchParams.set('state', state);
  printRedirectInstructions(clientId);
  console.log(`Opening Google consent. Redirect URI: ${REDIRECT_URI}`);
  openUrl(authUrl.toString());
  const authCode = await codePromise;
  const result = await postJson(`${GATEWAY_BASE}/googleCliAuthExchange`, {authCode, redirectUri: REDIRECT_URI});
  console.log(`Home Center Google tools connected for ${result.email || 'Google account'} linkedToFirebase=${Boolean(result.firebaseUserLinked)}`);
}

main().catch((err) => {
  console.error(String(err.message || err));
  process.exit(1);
});
