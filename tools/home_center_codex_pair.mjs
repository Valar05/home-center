#!/usr/bin/env node
import {mkdirSync, writeFileSync, chmodSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';

const GATEWAY_BASE = process.env.HOME_CENTER_GATEWAY_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net';
const CONFIG_DIR = process.env.HOME_CENTER_CODEX_CONFIG_DIR || join(homedir(), '.config', 'home-center');
const CONFIG_PATH = process.env.HOME_CENTER_CODEX_CONFIG || join(CONFIG_DIR, 'codex-hub.json');
const DEVICE_NAME = process.env.HOME_CENTER_DEVICE_NAME || 'Termux Codex';
const POLL_MS = Number(process.env.HOME_CENTER_PAIR_POLL_MS || 3000);
const TIMEOUT_MS = Number(process.env.HOME_CENTER_PAIR_TIMEOUT_MS || 10 * 60 * 1000);

async function postJson(path, body, token = '') {
  const response = await fetch(`${GATEWAY_BASE}/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
    },
    body: JSON.stringify(body || {}),
  });
  const text = await response.text();
  const json = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`${path} HTTP ${response.status}: ${text.slice(0, 2000)}`);
  }
  return json;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function saveConfig(payload) {
  mkdirSync(CONFIG_DIR, {recursive: true, mode: 0o700});
  writeFileSync(CONFIG_PATH, JSON.stringify(payload, null, 2) + '\n', {mode: 0o600});
  try { chmodSync(CONFIG_PATH, 0o600); } catch (_) {}
}

async function pair() {
  const started = await postJson('termuxPairingStart', {
    deviceName: DEVICE_NAME,
    clientKind: 'codex-termux',
    requestedGroups: ['drive', 'docs', 'github'],
  });
  console.log('Home Center Termux/Codex pairing');
  console.log(`Pairing ID: ${started.pairingId}`);
  console.log(`Code: ${started.code}`);
  console.log('Open Home Center on Android, tap Pair Termux Codex, and enter both values.');
  const deadline = Date.now() + TIMEOUT_MS;
  while (Date.now() < deadline) {
    const polled = await postJson('termuxPairingPoll', {pairingId: started.pairingId, code: started.code});
    if (polled.status === 'paired' && polled.access_token) {
      const config = {
        gatewayBase: GATEWAY_BASE,
        mcpUrl: polled.mcpUrl,
        accessToken: polled.access_token,
        refreshToken: polled.refresh_token,
        tokenType: polled.token_type || 'Bearer',
        expiresAtMs: Date.now() + Number(polled.expires_in || 0) * 1000,
        email: polled.email || '',
        allowedGroups: polled.allowedGroups || [],
        tools: polled.tools || [],
        pairedAt: new Date().toISOString(),
      };
      saveConfig(config);
      console.log(`Paired Home Center for ${config.email || 'signed-in user'}.`);
      console.log(`Saved token config: ${CONFIG_PATH}`);
      console.log(`MCP URL: ${config.mcpUrl}`);
      return;
    }
    process.stdout.write('.');
    await sleep(POLL_MS);
  }
  throw new Error('Timed out waiting for Home Center app approval.');
}

pair().catch((err) => {
  console.error(`
${err.message || err}`);
  process.exit(1);
});
