#!/usr/bin/env node
import {execFileSync} from 'node:child_process';
import {mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {join, resolve} from 'node:path';

const ROOT = resolve(new URL('..', import.meta.url).pathname);
const EVIDENCE_DIR = join(ROOT, 'tools', 'live_prompt_evidence');
const GATEWAY_BASE = process.env.HOME_CENTER_GATEWAY_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net';
const TURN_CONTRACT_URL = process.env.HOME_CENTER_TURN_CONTRACT_URL || 'https://turncontractsmoke-vxybsaualq-uc.a.run.app';

function parseArgs(argv) {
  const args = {runId: new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)};
  for (let i = 2; i < argv.length; i++) {
    const value = argv[i];
    if (value === '--run-id') args.runId = argv[++i] || args.runId;
    else if (value === '--help') {
      console.log('Usage: node tools/home_center_turn_contract_smoke.mjs [--run-id ID]');
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
      'Could not get a Google access token for Firebase smoke auth.',
      'Run: gcloud auth login',
      'Or set GOOGLE_ACCESS_TOKEN to a Google token that can sign in to Firebase.',
      String(err.message || err),
    ].join('\n'));
  }
}

async function postJson(url, body, bearer, label) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 125000);
  try {
    const headers = {'Content-Type': 'application/json'};
    if (bearer) headers.Authorization = `Bearer ${bearer}`;
    const response = await fetch(url, {method: 'POST', headers, body: JSON.stringify(body || {}), signal: controller.signal});
    const text = await response.text();
    let json = {};
    try {
      json = text ? JSON.parse(text) : {};
    } catch (err) {
      throw new Error(`${label || 'POST'} returned non-JSON HTTP ${response.status}: ${text.slice(0, 1000)}`);
    }
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
  const evidencePath = join(EVIDENCE_DIR, `turn_contract_smoke_${args.runId}.json`);
  const accessToken = googleAccessToken();
  firebaseApiKey();
  const result = await postJson(TURN_CONTRACT_URL || `${GATEWAY_BASE}/turnContractSmoke`, {runId: args.runId}, accessToken, 'turnContractSmoke');
  writeFileSync(evidencePath, JSON.stringify(redact({
    runner: {gatewayBase: GATEWAY_BASE, turnContractUrl: TURN_CONTRACT_URL, auth: 'google_access_token_or_firebase_id_token'},
    result,
  }), null, 2));
  if (!result.ok) {
    console.error(`Home Center turn contract smoke failed. Evidence: ${evidencePath}`);
    console.error(result.detail || result.error || 'unknown failure');
    process.exit(1);
  }
  const caseNames = (result.cases || []).map((entry) => entry.name).join(',');
  console.log(`Home Center turn contract smoke: OK evidence=${evidencePath} cases=${caseNames}`);
}

main().catch((err) => {
  mkdirSync(EVIDENCE_DIR, {recursive: true});
  const evidencePath = join(EVIDENCE_DIR, `turn_contract_smoke_failed_${Date.now()}.json`);
  writeFileSync(evidencePath, JSON.stringify({ok: false, error: String(err.stack || err)}, null, 2));
  console.error(`Home Center turn contract smoke failed. Evidence: ${evidencePath}`);
  console.error(String(err.message || err));
  process.exit(1);
});
