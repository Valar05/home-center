#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const root = path.resolve(import.meta.dirname, '..');
const configPath = path.join(root, 'config', 'fortress-pocket-tts-performance.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

function fail(message) {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
}

if (config.schema !== 'fortress.pocket-tts-performance.v1') fail('schema');
if (config.engineLock !== 'pocket-tts-phone') fail('Pocket TTS engine lock');
if (config.providerLock !== 'pocket-home-center') fail('provider lock');
if (config.playbackLock !== 'com.dclar.homecenter/.PocketTtsPlaybackActivity') fail('playback component lock');
if (config.systemFallbackAllowed !== false) fail('system fallback must stay forbidden');
if (config.cloudFallbackAllowed !== false) fail('cloud fallback must stay forbidden');

const policy = config.mutationPolicy ?? {};
if (policy.maxDimensionsPerCandidate !== 1) fail('one-dimension candidate law');
if (policy.explicitDrewFeedbackWins !== true) fail('explicit feedback precedence');
if (policy.candidateRequiresEvidence !== true) fail('candidate evidence gate');
if (policy.retainLastKnownGood !== true) fail('last-known-good retention');
if (policy.urgentStatusFallsBackImmediately !== true) fail('urgent fallback law');

for (const name of ['orandroid67', 'she-ra']) {
  const p = config.personas?.[name];
  if (!p) { fail(`missing ${name}`); continue; }
  if (p.status !== 'LAST_KNOWN_GOOD_BASELINE') fail(`${name} baseline status`);
  if (!(p.tempo > 1.0 && p.tempo <= 1.5)) fail(`${name} bounded tempo`);
  if (!(p.pitchSemitones >= 0 && p.pitchSemitones <= 12)) fail(`${name} bounded pitch`);
  if (!(p.utteranceMaxChars > 0 && p.utteranceMaxChars <= 300)) fail(`${name} bounded utterance length`);
  if (p.postProcessing?.kind !== 'ffmpeg-nightcore') fail(`${name} local post-processing kind`);
  if (p.postProcessing?.reversible !== true) fail(`${name} reversible post-processing`);
}

const o = config.personas?.orandroid67;
const s = config.personas?.['she-ra'];
if (o && s) {
  if (!(s.pitchSemitones > o.pitchSemitones)) fail('She-Ra must remain squeakier than Orandroid 67');
  if (!(s.tempo >= o.tempo)) fail('She-Ra must not be slower than Orandroid 67');
  if (!(s.roastDensity > o.roastDensity)) fail('role split roast density');
}

if (!Array.isArray(config.lineage)) fail('lineage must be an array');

if (!process.exitCode) console.log('PASS: Pocket TTS performance contract');
