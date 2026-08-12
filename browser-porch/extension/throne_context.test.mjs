import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const worker = fs.readFileSync(path.join(HERE, 'service-worker.js'), 'utf8');
const panel = fs.readFileSync(path.join(HERE, 'sidepanel.js'), 'utf8');
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

test('every worker packet includes durable campaign context before commission', () => {
  assert.match(worker, /DURABLE CAMPAIGN CONTEXT:/);
  assert.match(worker, /COMMISSION:/);
  assert.match(worker, /DEFAULT_CAMPAIGN_CONTEXT/);
});

test('queued work snapshots context instead of reading mutable context later', () => {
  assert.match(panel, /context: campaignContext/);
  assert.match(panel, /job\.context \|\| context\.value/);
  assert.match(panel, /context locked/);
});

test('manifest identifies campaign-context release', () => {
  assert.equal(manifest.version, '0.3.0');
  assert.match(manifest.description, /durable Fortress campaign context/i);
});
