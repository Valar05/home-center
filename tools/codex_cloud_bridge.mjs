#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const DEFAULT_PROFILE_DIR = '/var/lib/home-center/codex-cloud-profile';
const DEFAULT_OUTPUT_DIR = path.join(os.tmpdir(), 'home-center-codex-cloud-bridge');
const CODEX_CLOUD_URL = 'https://chatgpt.com/codex/';

function parseArgs(argv) {
  const args = {mode: '', resumePacket: '', outputDir: DEFAULT_OUTPUT_DIR, profileDir: DEFAULT_PROFILE_DIR, headed: true};
  const rest = [...argv];
  if (rest[0] && !rest[0].startsWith('--')) args.mode = rest.shift();
  for (let i = 0; i < rest.length; i += 1) {
    const arg = rest[i];
    if (arg === '--resume-packet') args.resumePacket = rest[++i];
    else if (arg === '--output-dir') args.outputDir = rest[++i];
    else if (arg === '--profile-dir') args.profileDir = rest[++i];
    else if (arg === '--headless') args.headed = false;
    else if (arg === '--help') {
      printHelp();
      process.exit(0);
    }
  }
  if (!args.mode) args.mode = 'self-test';
  return args;
}

function printHelp() {
  console.log([
    'Usage:',
    '  node tools/codex_cloud_bridge.mjs build-resume-prompt --resume-packet FILE [--output-dir DIR]',
    '  node tools/codex_cloud_bridge.mjs launch --resume-packet FILE [--profile-dir DIR] [--output-dir DIR]',
    '  node tools/codex_cloud_bridge.mjs self-test',
    '',
    'The bridge drives the real OpenAI Codex cloud surface. It must never copy',
    'ChatGPT/OpenAI cookies, passwords, OAuth tokens, or browser session files',
    'into Command Center. The persistent profile stays on the bridge host.',
  ].join('\n'));
}

function readJson(file) {
  if (!file) throw new Error('--resume-packet is required.');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeFile(file, text) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, String(text).endsWith('\n') ? String(text) : String(text) + '\n');
}

function containsSecret(value) {
  const text = String(value || '');
  return /Bearer\s+[A-Za-z0-9._~+/=-]{12,}/i.test(text)
    || /\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/.test(text)
    || /\bya29\.[A-Za-z0-9._-]{20,}\b/.test(text)
    || /\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/.test(text)
    || /(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|COOKIE)\s*[=:]\s*["']?[^"'\s]{12,}/i.test(text);
}

function normalizeResumePacket(packet) {
  const resumePacket = packet.resumePacket || packet;
  if (resumePacket.packetVersion !== 'command-center-codex-cloud-resume-v1') {
    throw new Error('Expected command-center-codex-cloud-resume-v1 packet.');
  }
  const prompt = resumePacket.activation && resumePacket.activation.task && resumePacket.activation.task.prompt || '';
  if (!prompt.trim()) throw new Error('Resume packet has no activation prompt.');
  const serialized = JSON.stringify(resumePacket);
  if (containsSecret(serialized)) throw new Error('Resume packet contains token-shaped secret material.');
  return resumePacket;
}

function buildResumePrompt(packet) {
  const agent = packet.agent || {};
  const session = packet.session || {};
  const activation = packet.activation || {};
  const task = activation.task || {};
  return [
    '# Command Center Codex Cloud Activation',
    '',
    `Agent: ${agent.name || agent.agentId || 'unknown'}`,
    `Repository: ${agent.repository || 'none'}`,
    `Session: ${session.sessionId || 'unknown'}`,
    `Activation: ${activation.activationId || 'unknown'}`,
    '',
    '## Task',
    task.prompt || '',
    '',
    '## Acceptance Criteria',
    ...(Array.isArray(task.acceptanceCriteria) && task.acceptanceCriteria.length ? task.acceptanceCriteria.map((item) => `- ${item}`) : ['- Produce a durable final report artifact.']),
    '',
    '## Constraints',
    ...(Array.isArray(task.constraints) && task.constraints.length ? task.constraints.map((item) => `- ${item}`) : ['- Do not store credentials, cookies, tokens, or session material in artifacts.']),
    '',
    '## Durable Context',
    session.currentSummary || 'No prior durable summary recorded.',
    '',
    '## Required Return',
    '- Final report suitable for Command Center artifact storage.',
    '- Exact evidence refs, files, or URLs inspected.',
    '- Explicit blocker classification if the real Codex cloud surface cannot complete the task.',
  ].join('\n');
}

function buildResumePromptMode(args) {
  const packet = normalizeResumePacket(readJson(args.resumePacket));
  const prompt = buildResumePrompt(packet);
  const promptPath = path.join(args.outputDir, 'codex-cloud-resume-prompt.md');
  const manifestPath = path.join(args.outputDir, 'codex-cloud-bridge-manifest.json');
  writeFile(promptPath, prompt);
  writeFile(manifestPath, JSON.stringify({
    ok: true,
    mode: 'build-resume-prompt',
    launchUrl: CODEX_CLOUD_URL,
    activationId: packet.activation.activationId,
    agentId: packet.agent.agentId,
    promptPath,
    credentialBoundary: packet.executionSurface && packet.executionSurface.credentialPolicy || '',
  }, null, 2));
  return {ok: true, promptPath, manifestPath};
}

async function launchMode(args) {
  const result = buildResumePromptMode(args);
  const {chromium} = await import('playwright');
  fs.mkdirSync(args.profileDir, {recursive: true});
  const context = await chromium.launchPersistentContext(args.profileDir, {headless: !args.headed});
  const page = await context.newPage();
  await page.goto(CODEX_CLOUD_URL, {waitUntil: 'domcontentloaded', timeout: 45000});
  const title = await page.title().catch(() => '');
  const evidencePath = path.join(args.outputDir, 'codex-cloud-launch-evidence.json');
  writeFile(evidencePath, JSON.stringify({
    ok: true,
    launchUrl: CODEX_CLOUD_URL,
    title,
    profileDir: args.profileDir,
    promptPath: result.promptPath,
    blockerPolicy: 'If login, CAPTCHA, or unknown Codex selectors block automation, stop and record needs_human without extracting session secrets.',
  }, null, 2));
  await context.close();
  return {...result, evidencePath};
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.mode === 'self-test') {
    const packet = {
      packetVersion: 'command-center-codex-cloud-resume-v1',
      executionSurface: {surfaceId: 'openai-codex-cloud', credentialPolicy: 'Do not copy cookies.'},
      agent: {agentId: 'home-center', name: 'Home Center', repository: 'Valar05/home-center'},
      session: {sessionId: 'session_home_center', currentSummary: 'Durable context exists.'},
      activation: {activationId: 'activation_12345678', task: {prompt: 'Inspect Command Center durable Codex cloud wiring.', acceptanceCriteria: ['Return exact files.'], constraints: ['No secrets.']}},
    };
    const out = path.join(os.tmpdir(), 'codex-cloud-bridge-self-test.json');
    writeFile(out, JSON.stringify(packet, null, 2));
    const result = buildResumePromptMode({...args, resumePacket: out, outputDir: path.join(os.tmpdir(), 'codex-cloud-bridge-self-test')});
    console.log(JSON.stringify({ok: true, ...result}, null, 2));
    return;
  }
  if (args.mode === 'build-resume-prompt') {
    console.log(JSON.stringify(buildResumePromptMode(args), null, 2));
    return;
  }
  if (args.mode === 'launch') {
    console.log(JSON.stringify(await launchMode(args), null, 2));
    return;
  }
  throw new Error('Unknown mode: ' + args.mode);
}

main().catch((err) => {
  console.error(JSON.stringify({ok: false, error: err.message}, null, 2));
  process.exit(1);
});
