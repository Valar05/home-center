import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const worker = fs.readFileSync(path.join(HERE, 'service-worker.js'), 'utf8');
const panel = fs.readFileSync(path.join(HERE, 'throne-panel.mjs'), 'utf8');
const core = fs.readFileSync(path.join(HERE, 'swarm-core.mjs'), 'utf8');
const html = fs.readFileSync(path.join(HERE, 'sidepanel.html'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(HERE, 'manifest.json'), 'utf8'));

test('worker boot locks operator-handoff and evidence doctrine', () => {
  assert.match(worker, /PORTCULLIS LOCKED/);
  assert.match(worker, /Computer Hands is the desktop body/);
  assert.match(worker, /Phone Hands is the phone body/);
  assert.match(worker, /Drew's hands are the final fallback/);
  assert.match(worker, /requested capability, implemented capability, tested capability, deployed capability, callable capability, delivered capability, and accepted capability/);
  assert.match(worker, /Never use ChatGPT-local scratch\/container execution as proof/);
  assert.match(worker, /available_body_lane_ignored/);
});

test('Instant workers are bounded needy slices, not campaign brains', () => {
  assert.match(worker, /chat-mode Instant execution worker/);
  assert.match(worker, /one bounded bite/i);
  assert.match(worker, /Work ONE small feature, repair, proof, or acceptance slice at a time/);
  assert.match(worker, /No Great War/);
  assert.match(worker, /Be usefully needy/);
});

test('choked threads emit compact handoff and rotate through testable swarm core', () => {
  for (const field of ['DURABLE CONTEXT', 'COMPLETED EVIDENCE', 'CURRENT SLICE', 'UNMET ACCEPTANCE', 'ACTIVE CONSTRAINTS', 'EXACT NEXT ACTION']) {
    assert.match(worker, new RegExp(field));
    assert.match(core, new RegExp(field));
  }
  assert.match(core, /planHandoffContinuation/);
  assert.match(core, /source = 'handoff'/);
  assert.match(panel, /planHandoffContinuation/);
  assert.match(panel, /state: 'handed_off'/);
  assert.match(panel, /assistant_completion_timeout/);
});

test('every worker packet includes durable campaign context before bounded commission', () => {
  assert.match(worker, /DURABLE CAMPAIGN CONTEXT:/);
  assert.match(worker, /COMMISSION — ONE BOUNDED SLICE:/);
  assert.match(worker, /DEFAULT_CAMPAIGN_CONTEXT/);
});

test('queued work snapshots context instead of reading mutable context later', () => {
  assert.match(core, /context: String\(campaignContext \|\| ''\)\.trim\(\)/);
  assert.match(panel, /original\.context \|\| context\.value/);
  assert.match(panel, /context locked/);
});

test('bounded swarm uses modular handoff core', () => {
  assert.match(html, /id="runSwarm"/);
  assert.match(panel, /MAX_SWARM_SLICES/);
  assert.match(panel, /planHandoffContinuation/);
  assert.match(core, /export const MAX_SWARM_SLICES = 12/);
  assert.match(core, /parseHandoff/);
  assert.match(core, /mergeHandoffContext/);
});

test('ChatGPT cannot be the terminal review gate', () => {
  assert.doesNotMatch(panel, /state: 'completed'/);
  assert.match(panel, /awaiting_venice_review/);
  assert.match(panel, /reviewer: 'venice-local'/);
  assert.match(panel, /independentOfChatGPT: true/);
  assert.match(panel, /externalReviewGateSatisfied/);
  assert.match(panel, /terminalGate: 'Venice external code review'/);
  assert.match(panel, /accepted: false/);
});

test('manifest identifies bounded swarm release', () => {
  assert.equal(manifest.version, '0.5.0');
  assert.match(manifest.description, /bounded swarm babysitting/i);
});
