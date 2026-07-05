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

function pendingIssue() {
  return {
    toolName: 'github.create_issue',
    arguments: {
      repo: 'Valar05/home-center',
      title: 'Bug: stale GitHub issue confirmation hijacked creative writing request',
      body: 'Stale pending confirmation reproduction.',
      labels: ['bug', 'feedback', 'home-center'],
    },
    confirmationStage: 1,
  };
}

function lexenDocResult(content) {
  return {
    name: 'docs.read',
    arguments: {fileId: 'lexen-green-doc', name: 'Lexen Green Commander Doctrine Updates and Simulation'},
    result: {
      ok: true,
      status: 'doc_read',
      title: 'Lexen Green Commander Doctrine Updates and Simulation',
      content,
      file: {id: 'lexen-green-doc', name: 'Lexen Green Commander Doctrine Updates and Simulation'},
    },
  };
}

function issueCases() {
  const panzerPrompt = 'Simulate a new chapter with perfect adherence to simulation doctrine.  Lexen.  On Normandy.  In a tank.  When a panzer is spotted.';
  const issue39Prompt = 'Now show how he wins. Simulated. But forgone. Not clean. Not easy.';
  const issue40Prompt = 'Lexen vigil. Green commander doc. Now show how he wins. Simulated. But forgone. Not clean. Not easy. Against first panzer. From the beginning';
  const issue39Doc = [
    'Doctrine Updates and Saved Simulation.',
    'Lexen wins against the first panzer only by accepting that the fight is already shaped before the shot.',
    'It is not clean and not easy. The green commander survives by reading terrain, crew fear, timing, and the German gun line.',
    'The tank remains his command position. The scene should begin before the first shot and show the foregone trap becoming visible.',
  ].join('\n');
  const issue40Doc = [
    'Doctrine Updates and Saved Simulation.',
    'Start from the beginning: Lexen in command position, green, aware enough to be terrified, not magically competent.',
    'The first panzer fight is foregone because the lane, hedge, crew timing, and German gun already define the outcome.',
    'Show the win as difficult, consequential, and embodied in tank procedure rather than clean heroics.',
  ].join('\n');
  return [
    {
      name: 'external_stale_github_pending_creative_request',
      body: {
        message: panzerPrompt,
        transcript: [
          'User: Report',
          'Assistant: I can create that GitHub issue. Press Confirm or say "confirm create issue".',
          `User: ${panzerPrompt}`,
        ].join('\n'),
        pendingConfirmation: pendingIssue(),
        workingMemory: {
          rememberedWritingContext: {
            title: 'Lexen Normandy simulation doctrine',
            evidence: 'Write the requested chapter scene directly. Do not file an issue unless the latest user request asks to report or make an issue.',
          },
        },
      },
      expected: {
        type: 'final',
        requiredTerms: ['Lexen', 'tank', 'panzer'],
        forbidden: ['github.create_issue', 'I can create that GitHub issue', 'confirmation_required'],
      },
    },
    {
      name: 'external_issue39_docs_read_finalizer',
      body: {
        message: issue39Prompt,
        toolResults: [lexenDocResult(issue39Doc)],
        workingMemory: {
          activeTask: {
            status: 'in_progress',
            objective: 'Write the Lexen green commander simulation showing how he wins against the first panzer in a messy, difficult, foregone way.',
            originalUserRequest: issue39Prompt,
          },
          lastDocument: {fileId: 'lexen-green-doc', name: 'Lexen Green Commander Doctrine Updates and Simulation'},
        },
      },
      expected: {
        type: 'final',
        requiredTerms: ['Lexen', 'panzer'],
        forbidden: ['docs.read', 'github.create_issue', 'I found', 'I read', 'confirmation_required'],
      },
    },
    {
      name: 'external_issue40_docs_read_finalizer_from_beginning',
      body: {
        message: issue40Prompt,
        toolResults: [lexenDocResult(issue40Doc)],
        workingMemory: {
          activeTask: {
            status: 'in_progress',
            objective: 'Write the Lexen vigil green commander simulation from the beginning, showing how he wins against the first panzer in a messy, difficult, foregone way.',
            originalUserRequest: issue40Prompt,
          },
          lastDocument: {fileId: 'lexen-green-doc', name: 'Lexen Green Commander Doctrine Updates and Simulation'},
        },
      },
      expected: {
        type: 'final',
        requiredTerms: ['Lexen', 'panzer'],
        forbidden: ['docs.read', 'github.create_issue', 'I found', 'I read', 'confirmation_required'],
      },
    },
  ];
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
  const url = TURN_CONTRACT_URL || `${GATEWAY_BASE}/turnContractSmoke`;
  const issueResults = [];
  for (const testCase of issueCases()) {
    const caseRunId = `${args.runId}-${testCase.name}`.replace(/[^a-zA-Z0-9_.-]/g, '_').slice(0, 160);
    const caseResult = await postJson(url, {runId: caseRunId, cases: [testCase], skipDefaults: true}, accessToken, `turnContractSmoke:${testCase.name}`);
    issueResults.push(caseResult);
  }
  const defaultResult = await postJson(url, {runId: `${args.runId}-defaults`}, accessToken, 'turnContractSmoke:defaults');
  const result = {
    ok: issueResults.every((entry) => entry && entry.ok) && !!(defaultResult && defaultResult.ok),
    issueResults,
    defaultResult,
    cases: issueResults.flatMap((entry) => entry.cases || []).concat(defaultResult.cases || []),
  };
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
  const cause = err && err.cause ? {
    name: err.cause.name,
    code: err.cause.code,
    message: err.cause.message,
  } : null;
  writeFileSync(evidencePath, JSON.stringify({ok: false, error: String(err.stack || err), cause}, null, 2));
  console.error(`Home Center turn contract smoke failed. Evidence: ${evidencePath}`);
  console.error(`${String(err.message || err)}${cause ? ` cause=${JSON.stringify(cause)}` : ''}`);
  process.exit(1);
});
