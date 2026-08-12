import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const worker = fs.readFileSync(path.join(HERE, 'service-worker.js'), 'utf8');
const panel = fs.readFileSync(path.join(HERE, 'sidepanel.js'), 'utf8');
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

test('choked threads must emit compact handoff and rotate', () => {
  assert.match(worker, /thread is CHOKED/);
  assert.match(worker, /do not keep wrestling the same thread/);
  for (const field of ['DURABLE CONTEXT', 'COMPLETED EVIDENCE', 'CURRENT SLICE', 'UNMET ACCEPTANCE', 'ACTIVE CONSTRAINTS', 'EXACT NEXT ACTION']) {
    assert.match(worker, new RegExp(field));
    assert.match(panel, new RegExp(field));
  }
  assert.match(worker, /continue the work in a fresh thread/);
});

test('every worker packet includes durable campaign context before bounded commission', () => {
  assert.match(worker, /DURABLE CAMPAIGN CONTEXT:/);
  assert.match(worker, /COMMISSION — ONE BOUNDED SLICE:/);
  assert.match(worker, /DEFAULT_CAMPAIGN_CONTEXT/);
});

test('queued work snapshots context instead of reading mutable context later', () => {
  assert.match(panel, /context: String\(campaignContext/);
  assert.match(panel, /job\.context \|\| context\.value/);
  assert.match(panel, /context locked/);
});

test('bounded swarm consumes handoff into a fresh worker instead of wrestling a choked thread', () => {
  assert.match(html, /id="runSwarm"/);
  assert.match(panel, /MAX_SWARM_SLICES = 12/);
  assert.match(panel, /function parseHandoff/);
  assert.match(panel, /mergeHandoffContext/);
  assert.match(panel, /newJob\(handoff\['EXACT NEXT ACTION'\], nextContext, true, 'handoff'\)/);
  assert.match(panel, /state: 'handed_off'/);
  assert.match(panel, /assistant_completion_timeout/);
});

test('malformed handoffs cannot auto-dispatch', () => {
  assert.match(panel, /if \(!start\) return null/);
  assert.match(panel, /if \(!found\) return null/);
  assert.match(panel, /if \(!value\) return null/);
  assert.match(panel, /Object\.keys\(values\)\.length === HANDOFF_FIELDS\.length/);
});

test('manifest identifies automatic swarm babysitting release', () => {
  assert.equal(manifest.version, '0.5.0');
  assert.match(manifest.description, /bounded swarm babysitting/i);
  assert.match(manifest.description, /automatic choke handoff rotation/i);
});
