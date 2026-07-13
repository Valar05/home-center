#!/usr/bin/env node
import {mkdirSync, writeFileSync, chmodSync, existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {join} from 'node:path';
import {homedir} from 'node:os';

const GATEWAY_BASE = process.env.HOME_CENTER_GATEWAY_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net';
const CONFIG_DIR = process.env.HOME_CENTER_CODEX_CONFIG_DIR || join(homedir(), '.config', 'home-center');
const CONFIG_PATH = process.env.HOME_CENTER_CODEX_CONFIG || join(CONFIG_DIR, 'codex-hub.json');
const DEVICE_NAME = process.env.HOME_CENTER_DEVICE_NAME || 'Termux Codex';
const POLL_MS = Number(process.env.HOME_CENTER_PAIR_POLL_MS || 3000);
const TIMEOUT_MS = Number(process.env.HOME_CENTER_PAIR_TIMEOUT_MS || 10 * 60 * 1000);
const LAUNCH_HOME_CENTER = process.argv.includes('--launch-home-center') || process.argv.includes('--auto-approve');
const HOME_CENTER_COMPONENT = process.env.HOME_CENTER_COMPONENT || 'com.dclar.homecenter/.MainActivity';
const FAKE_PAIRING = process.env.HOME_CENTER_PAIRING_FAKE === '1';

async function postJson(path, body, token = '') {
  if (FAKE_PAIRING) {
    if (path === 'termuxPairingStart') {
      return {pairingId: 'fakePairingIdForHarness', code: '123456'};
    }
    if (path === 'termuxPairingPoll') {
      return {
        status: 'paired',
        access_token: 'fake-access-token',
        refresh_token: 'fake-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        email: 'fake@example.invalid',
        allowedGroups: ['drive', 'docs', 'github'],
        tools: [],
        mcpUrl: 'https://example.invalid/homeCenterMcp/mcp',
      };
    }
  }
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


function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

function findRish() {
  const candidates = [
    process.env.RISH,
    join(homedir(), 'bin', 'rish'),
    join(homedir(), 'rish'),
    join(homedir(), '.local', 'bin', 'rish'),
    '/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish',
    '/storage/emulated/0/Documents/rish',
    '/storage/emulated/0/Download/rish',
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  const resolved = spawnSync('sh', ['-c', 'command -v rish'], {encoding: 'utf8'});
  if (resolved.status === 0 && resolved.stdout.trim()) return resolved.stdout.trim();
  return '';
}

function launchHomeCenterApproval(pairingId, code) {
  const rish = findRish();
  if (!rish) {
    console.log('rish not found; open Home Center and use manual Pair Termux Codex fallback.');
    return false;
  }
  const command = [
    'am start -S',
    '-n', shellQuote(HOME_CENTER_COMPONENT),
    '--ez home_center_termux_pairing_auto true',
    '--es home_center_termux_pairing_id', shellQuote(pairingId),
    '--es home_center_termux_pairing_code', shellQuote(code),
  ].join(' ');
  const launched = process.env.HC_FAKE_AM_FAIL === '1'
    ? {status: 1, stderr: 'fake am start failure', stdout: ''}
    : spawnSync(rish, ['-c', command], {encoding: 'utf8'});
  if (launched.status !== 0) {
    console.log(`Shizuku launch failed: ${(launched.stderr || launched.stdout || '').trim()}`);
    return false;
  }
  console.log('Launched Home Center pairing through Shizuku. Waiting for approval result.');
  return true;
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
  if (LAUNCH_HOME_CENTER) {
    const launched = launchHomeCenterApproval(started.pairingId, started.code);
    if (!launched && FAKE_PAIRING) {
      throw new Error('Fake pairing launch failed before Home Center approval.');
    }
  } else {
    console.log('Open Home Center on Android, tap Pair Termux Codex, and enter both values.');
  }
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
