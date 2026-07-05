#!/usr/bin/env node
import {execFileSync} from 'node:child_process';
import {mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {join, resolve} from 'node:path';

const ROOT = resolve(new URL('..', import.meta.url).pathname);
const EVIDENCE_DIR = join(ROOT, 'tools', 'metal_prompt_evidence');
const GATEWAY_BASE = process.env.HOME_CENTER_GATEWAY_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net';

function parseArgs(argv) {
  const args = {scenario: 'docs-create-update-read', runId: new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)};
  for (let i = 2; i < argv.length; i++) {
    const value = argv[i];
    if (value === '--scenario') args.scenario = argv[++i] || args.scenario;
    else if (value === '--run-id') args.runId = argv[++i] || args.runId;
    else if (value === '--help') {
      console.log('Usage: node tools/home_center_metal_prompt_smoke.mjs [--scenario docs-create-update-read] [--run-id ID]');
      process.exit(0);
    }
  }
  return args;
}

function firebaseApiKey() {
  const config = JSON.parse(readFileSync(join(ROOT, 'app', 'google-services.json'), 'utf8'));
  const key = config?.client?.[0]?.api_key?.[0]?.current_key || '';
  if (!key) throw new Error('Firebase web API key missing from app/google-services.json.');
  return key;
}

function googleAccessToken() {
  if (process.env.GOOGLE_ACCESS_TOKEN) return process.env.GOOGLE_ACCESS_TOKEN.trim();
  try {
    return execFileSync('gcloud', ['auth', 'print-access-token'], {encoding: 'utf8'}).trim();
  } catch (err) {
    throw new Error([
      'Could not get a Google access token for Firebase sign-in.',
      'Run: gcloud auth login',
      'Or set GOOGLE_ACCESS_TOKEN to a Google token that can sign in to Firebase.',
      String(err.message || err),
    ].join('\n'));
  }
}

async function postJson(url, body, bearer, label) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 310000);
  try {
    const headers = {'Content-Type': 'application/json'};
    if (bearer) headers.Authorization = `Bearer ${bearer}`;
    const response = await fetch(url, {method: 'POST', headers, body: JSON.stringify(body || {}), signal: controller.signal});
    const text = await response.text();
    const json = text ? JSON.parse(text) : {};
    if (!response.ok) throw new Error(`${label || 'POST'} HTTP ${response.status}: ${text.slice(0, 2000)}`);
    return json;
  } finally {
    clearTimeout(timeout);
  }
}

function redact(value) {
  const json = JSON.parse(JSON.stringify(value || {}));
  const scrub = (node) => {
    if (!node || typeof node !== 'object') return;
    for (const key of Object.keys(node)) {
      if (/token|authorization|secret|key/i.test(key)) node[key] = '[redacted]';
      else scrub(node[key]);
    }
  };
  scrub(json);
  return json;
}

async function main() {
  const args = parseArgs(process.argv);
  mkdirSync(EVIDENCE_DIR, {recursive: true});
  const evidencePath = join(EVIDENCE_DIR, `metal_prompt_smoke_${args.runId}.json`);
  const accessToken = googleAccessToken();
  firebaseApiKey();
  const result = await postJson(`${GATEWAY_BASE}/metalPromptSmoke`, {
    scenario: args.scenario,
    runId: args.runId,
  }, accessToken, 'metalPromptSmoke');
  writeFileSync(evidencePath, JSON.stringify(redact({
    runner: {gatewayBase: GATEWAY_BASE, auth: 'google_access_token_mapped_to_firebase_user'},
    result,
  }), null, 2));
  if (!result.ok) {
    console.error(`Home Center metal prompt smoke failed. Evidence: ${evidencePath}`);
    console.error(result.detail || result.error || 'unknown failure');
    process.exit(1);
  }
  console.log(`Home Center metal prompt smoke: OK evidence=${evidencePath} folderId=${result?.sandbox?.folderId || ''}`);
}

main().catch((err) => {
  mkdirSync(EVIDENCE_DIR, {recursive: true});
  const evidencePath = join(EVIDENCE_DIR, `metal_prompt_smoke_failed_${Date.now()}.json`);
  writeFileSync(evidencePath, JSON.stringify({ok: false, error: String(err.stack || err)}, null, 2));
  console.error(`Home Center metal prompt smoke failed. Evidence: ${evidencePath}`);
  console.error(String(err.message || err));
  process.exit(1);
});
