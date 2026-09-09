#!/usr/bin/env node

import {createRequire} from 'node:module';
import {mkdirSync, writeFileSync, appendFileSync} from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
const admin = require('../functions/node_modules/firebase-admin');

const PROJECT_ID = process.env.HOME_CENTER_GCP_PROJECT || 'home-center-dclar';
const SOURCE_REF = String(process.env.HOME_CENTER_SOURCE_REF || '').trim();
const DEVICE_ID = 'primary-phone';
const RUN_ID = String(process.env.GITHUB_RUN_ID || Date.now());
const RUN_ATTEMPT = String(process.env.GITHUB_RUN_ATTEMPT || '1');
const EVIDENCE_DIR = process.env.IMPROPER_IMAGE_EVIDENCE_DIR || 'runtime-evidence';
const SUMMARY = process.env.GITHUB_STEP_SUMMARY || '';

if (!/^[0-9a-f]{40}$/.test(SOURCE_REF)) {
  throw new Error('HOME_CENTER_SOURCE_REF must be the exact 40-character source commit');
}

if (!admin.apps.length) admin.initializeApp({projectId: PROJECT_ID});
const db = admin.firestore();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const now = () => Date.now();
const compactId = (value) => String(value).replace(/[^A-Za-z0-9_.-]+/g, '-').slice(0, 150);

function summary(text) {
  process.stdout.write(text + '\n');
  if (SUMMARY) appendFileSync(SUMMARY, text + '\n', 'utf8');
}

async function readDevice() {
  const snap = await db.collection('phoneHandsDevices').doc(DEVICE_ID).get();
  if (!snap.exists) throw new Error(`Home Center device ${DEVICE_ID} is not registered`);
  return snap.data() || {};
}

async function waitForDevice(predicate, timeoutMs, label) {
  const deadline = now() + timeoutMs;
  let last = null;
  while (now() < deadline) {
    last = await readDevice();
    if (predicate(last)) return last;
    await sleep(2000);
  }
  const visible = last ? {
    status:last.status,
    lastSeenAtMs:last.lastSeenAtMs,
    capabilities:last.capabilities,
  } : null;
  throw new Error(`${label} timed out; last device state=${JSON.stringify(visible)}`);
}

async function enqueueFixedCommand(ownerKey, suffix, command, timeoutSeconds, ttlMs = 45 * 60 * 1000) {
  const commandId = compactId(`phc_gha_improper_${RUN_ID}_${RUN_ATTEMPT}_${suffix}`);
  const ref = db.collection('phoneHandsCommands').doc(commandId);
  const existing = await ref.get();
  if (existing.exists) {
    const prior = existing.data() || {};
    if (prior.ownerKey !== ownerKey || prior.deviceId !== DEVICE_ID) {
      throw new Error(`existing command ${commandId} is not owned by expected Home Center device`);
    }
    return {commandId, ref, reused:true};
  }
  const createdAtMs = now();
  const record = {
    commandId,
    deviceId:DEVICE_ID,
    ownerKey,
    action:{action:'phone_shell', command, timeoutSeconds},
    status:'queued',
    createdAtMs,
    updatedAtMs:createdAtMs,
    expiresAtMs:createdAtMs + ttlMs,
    requestedBy:`github-actions:phone-improper-image-delivery:${RUN_ID}:${RUN_ATTEMPT}`,
    result:null,
    error:'',
    leaseOwner:'',
    leaseExpiresAtMs:0,
  };
  await ref.create(record);
  return {commandId, ref, reused:false};
}

async function waitForCommand(handle, timeoutMs) {
  const deadline = now() + timeoutMs;
  let last = null;
  while (now() < deadline) {
    const snap = await handle.ref.get();
    if (!snap.exists) throw new Error(`Home Center command vanished: ${handle.commandId}`);
    last = snap.data() || {};
    if (last.status === 'completed') {
      const result = last.result || {};
      if (result.ok !== true || Number(result.exitCode) !== 0) {
        throw new Error(`Home Center command ${handle.commandId} completed unsuccessfully: ${JSON.stringify({result,error:last.error})}`);
      }
      return last;
    }
    if (last.status === 'failed' || last.status === 'cancelled' || last.status === 'expired') {
      throw new Error(`Home Center command ${handle.commandId} ${last.status}: ${last.error || JSON.stringify(last.result || {})}`);
    }
    await sleep(2000);
  }
  throw new Error(`Home Center command ${handle.commandId} timed out in state ${last?.status || 'unknown'}`);
}

function quotedGhScript(repoPath, envPrefix = '') {
  const api = `repos/Valar05/home-center/contents/${repoPath}?ref=${SOURCE_REF}`;
  return `set -o pipefail; gh api -H 'Accept: application/vnd.github.raw+json' '${api}' | ${envPrefix}bash`;
}

function parseJsonLines(stdout) {
  const lines = String(stdout || '').split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
  const parsed = [];
  for (const line of lines) {
    if (!line.startsWith('{') || !line.endsWith('}')) continue;
    try { parsed.push(JSON.parse(line)); } catch {}
  }
  return parsed;
}

function requireRelayReceipt(stdout) {
  const receipts = parseJsonLines(stdout);
  const receipt = receipts.find((x) => x?.schema === 'home-center-phone-relay-hotswap-scheduled.v1');
  if (!receipt || receipt.ok !== true || receipt.shizukuRequired !== false || receipt.sourceCommit !== SOURCE_REF) {
    throw new Error(`relay hot-swap command did not return the expected pinned receipt: ${String(stdout || '').slice(-6000)}`);
  }
  return receipt;
}

function requireFinalReceipt(stdout) {
  const receipts = parseJsonLines(stdout);
  const final = [...receipts].reverse().find((x) => x?.schema === 'improper-image-runtime-final.v1');
  if (!final || final.ok !== true) {
    throw new Error(`image campaign did not return an accepted final receipt: ${String(stdout || '').slice(-12000)}`);
  }
  if (final.sourceCommit !== SOURCE_REF || final.owner !== 'Home Center' || final.executionLane !== 'primary-phone background Termux relay') {
    throw new Error('final receipt does not prove the commissioned owner/execution lane/source commit');
  }
  if (final.renderer !== 'THECAULDRON localhost ComfyUI' || final.shizukuRequired !== false || final.atomRequired !== false) {
    throw new Error('final receipt does not prove the commissioned renderer and independence boundaries');
  }
  const acceptance = final.acceptance || {};
  const capabilities = acceptance.capabilityState || {};
  if (!acceptance.promptId) throw new Error('final receipt is missing a real ComfyUI promptId');
  if (!String(acceptance.publicPhonePath || '').startsWith('/storage/emulated/0/Pictures/Fortress/')) {
    throw new Error('final receipt is missing public Pictures/Fortress delivery');
  }
  if (!acceptance.pngSha256 || acceptance.pngSha256 !== acceptance.publicPhoneSha256) {
    throw new Error('final receipt does not prove identical accepted/public PNG hashes');
  }
  if (capabilities.publicPicturesArtifactDelivered !== true || capabilities.shizukuRequired !== false) {
    throw new Error('final receipt capability state does not prove public delivery and Shizuku independence');
  }
  return final;
}

async function main() {
  summary('# Improper Image Runtime Campaign');
  summary(`Source commit: \`${SOURCE_REF}\``);
  summary(`Execution owner: **Home Center**; device: **${DEVICE_ID}**; renderer: **THECAULDRON localhost ComfyUI**.`);

  const initial = await waitForDevice(
    (d) => d.status === 'online' && Number(d.lastSeenAtMs || 0) >= now() - 45_000 && typeof d.ownerKey === 'string' && d.ownerKey,
    150_000,
    'existing Home Center phone relay heartbeat',
  );
  const ownerKey = initial.ownerKey;
  const initialSeen = Number(initial.lastSeenAtMs || 0);
  summary('Existing Home Center phone relay observed live.');

  const hotSwapCommand = quotedGhScript(
    'tools/hot_swap_phone_relay_no_shizuku.sh',
    `HOME_CENTER_SOURCE_REF='${SOURCE_REF}' `,
  );
  const hotSwap = await enqueueFixedCommand(ownerKey, 'relay', hotSwapCommand, 240, 15 * 60 * 1000);
  const hotSwapDone = await waitForCommand(hotSwap, 6 * 60 * 1000);
  requireRelayReceipt(hotSwapDone.result?.stdout);
  summary(`Relay hot-swap command completed through Home Center: \`${hotSwap.commandId}\`.`);

  const relayReady = await waitForDevice(
    (d) => d.status === 'online' &&
      d.ownerKey === ownerKey &&
      Number(d.lastSeenAtMs || 0) > initialSeen &&
      Number(d.lastSeenAtMs || 0) >= now() - 30_000 &&
      Array.isArray(d.capabilities) && d.capabilities.includes('background_termux_shizuku_independent'),
    150_000,
    'Shizuku-independent Home Center relay registration',
  );
  summary(`Shizuku-independent relay registered and polling; lastSeenAtMs=${relayReady.lastSeenAtMs}.`);

  const hotswapProofCommand = "python3 - <<'PY'\nimport json, pathlib\np=pathlib.Path.home()/'.local/state/home-center/relay-hotswap/latest.json'\nr=json.load(open(p,encoding='utf-8'))\nassert r.get('ok') is True\nassert r.get('sourceCommit') == '" + SOURCE_REF + "'\nassert r.get('baselineTransport') == 'termux-no-shizuku'\nassert r.get('shizukuRequired') is False\nprint(json.dumps(r,sort_keys=True))\nPY";
  const hotswapProof = await enqueueFixedCommand(ownerKey, 'relay-proof', hotswapProofCommand, 60, 10 * 60 * 1000);
  const hotswapProofDone = await waitForCommand(hotswapProof, 2 * 60 * 1000);
  const hotProof = parseJsonLines(hotswapProofDone.result?.stdout).find((x) => x?.schema === 'home-center-phone-relay-hotswap.v1');
  if (!hotProof || hotProof.ok !== true || hotProof.shizukuRequired !== false || hotProof.sourceCommit !== SOURCE_REF) {
    throw new Error('phone-local relay hot-swap receipt was not accepted');
  }
  summary('Phone-local relay receipt proves baselineTransport=termux-no-shizuku.');

  const imageCommand = quotedGhScript(
    'tools/run_improper_image_campaign_pinned.sh',
    `HOME_CENTER_SOURCE_REF='${SOURCE_REF}' `,
  );
  const image = await enqueueFixedCommand(ownerKey, 'image', imageCommand, 840, 45 * 60 * 1000);
  const imageDone = await waitForCommand(image, 18 * 60 * 1000);
  const final = requireFinalReceipt(imageDone.result?.stdout);

  mkdirSync(EVIDENCE_DIR, {recursive:true});
  const evidencePath = path.join(EVIDENCE_DIR, `improper-image-${RUN_ID}-${RUN_ATTEMPT}.json`);
  const evidence = {
    schema:'github-home-center-improper-image-runtime-evidence.v1',
    ok:true,
    githubRunId:RUN_ID,
    githubRunAttempt:RUN_ATTEMPT,
    sourceCommit:SOURCE_REF,
    phoneDevice:DEVICE_ID,
    hotSwapCommandId:hotSwap.commandId,
    hotSwapReceipt:hotProof,
    imageCommandId:image.commandId,
    final,
  };
  writeFileSync(evidencePath, JSON.stringify(evidence, null, 2) + '\n', 'utf8');

  const acceptance = final.acceptance;
  summary('');
  summary('## Runtime acceptance: PASS');
  summary(`ComfyUI promptId: \`${acceptance.promptId}\``);
  summary(`Phone PNG: \`${acceptance.publicPhonePath}\``);
  summary(`SHA-256: \`${acceptance.pngSha256}\``);
  summary('Shizuku required: **false**. Atom required: **false**. Public Pictures delivery: **true**.');
  summary(`Evidence: \`${evidencePath}\``);
}

main().catch((error) => {
  mkdirSync(EVIDENCE_DIR, {recursive:true});
  const failurePath = path.join(EVIDENCE_DIR, `improper-image-${RUN_ID}-${RUN_ATTEMPT}-failure.json`);
  writeFileSync(failurePath, JSON.stringify({
    schema:'github-home-center-improper-image-runtime-failure.v1',
    ok:false,
    sourceCommit:SOURCE_REF,
    githubRunId:RUN_ID,
    githubRunAttempt:RUN_ATTEMPT,
    error:String(error?.stack || error),
  }, null, 2) + '\n', 'utf8');
  summary('');
  summary(`## Runtime acceptance: FAIL\n\n\`${String(error?.message || error)}\``);
  process.exitCode = 1;
});
