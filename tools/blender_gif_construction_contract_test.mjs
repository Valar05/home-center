#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {buildGifPlaybackContract, makeLoopingGif, selectGifEvidenceFiles} from '../cloud-render/src/render_bundle.mjs';

function hasTool(name) {
  return spawnSync(name, ['-version'], {encoding: 'utf8', timeout: 5000}).status === 0;
}
function run(command, args, label) {
  const result = spawnSync(command, args, {encoding: 'utf8', timeout: 30000});
  assert.equal(result.status, 0, label + ': ' + String(result.stderr || result.stdout || ''));
  return result.stdout || '';
}
function makeSprite(file, x) {
  run('convert', ['-size', '64x32', 'xc:none', '-fill', '#ff0000ff', '-draw', 'rectangle ' + x + ',8 ' + (x + 7) + ',15', 'PNG32:' + file], 'make transparent sprite');
}
function compareEqual(actual, expected, label) {
  const result = spawnSync('compare', ['-metric', 'AE', actual, expected, 'null:'], {encoding: 'utf8', timeout: 30000});
  assert.equal(result.status, 0, label + ': ' + String(result.stderr || result.stdout || ''));
  assert.equal(String(result.stderr || result.stdout || '').trim() || '0', '0', label + ' pixel mismatch');
}
function compareDifferent(actual, unexpected, label) {
  const result = spawnSync('compare', ['-metric', 'AE', actual, unexpected, 'null:'], {encoding: 'utf8', timeout: 30000});
  assert.notEqual(String(result.stderr || result.stdout || '').trim() || '0', '0', label + ' unexpectedly matched');
}

const fakeFrames = ['frame0.png', 'frame1.png', 'frame2.png', 'frame3.png'];
const contract = buildGifPlaybackContract(fakeFrames, {
  authoredKeys: [0, 1, 2, 3, 4, 5],
  evidenceFrames: [0, 1, 2, 3],
  gifFrames: [0, 2, 1],
  gifTimingMs: [110, 90, 130],
  renderedFrames: fakeFrames,
}, {});
assert.deepEqual(contract.authoredKeys, [0, 1, 2, 3, 4, 5]);
assert.deepEqual(contract.evidenceFrames, [0, 1, 2, 3]);
assert.deepEqual(contract.gifFrames, [0, 2, 1]);
assert.deepEqual(contract.gifTimingMs, [110, 90, 130]);
assert.deepEqual(contract.selectedFrames.map((frame) => frame.sourceIndex), [0, 2, 1]);
const nonContiguousEvidence = [
  {index: 12, file: 'locked-a.png'},
  {index: 27, file: 'locked-b.png'},
  {index: 43, file: 'orthogonal-a.png'},
];
const nonContiguousPlayback = {gifFrames: [12, 43, 27]};
assert.deepEqual(
  selectGifEvidenceFiles(nonContiguousEvidence, nonContiguousPlayback),
  ['locked-a.png', 'orthogonal-a.png', 'locked-b.png'],
  'runtime GIF selection must resolve declared frame identities rather than array offsets',
);
assert(!contract.gifFrames.includes(3), 'excluded evidence frame must not enter GIF playback contract');
assert.throws(() => buildGifPlaybackContract(fakeFrames, {evidenceFrames: [0, 1, 2, 3], gifFrames: [], gifTimingMs: []}, {}), /gifFrames must not be empty/);
assert.throws(() => buildGifPlaybackContract(fakeFrames, {evidenceFrames: [0, 1, 2, 3], gifFrames: [4], gifTimingMs: [100]}, {}), /index 4 is out of range for 4 evidence frames/);
assert.throws(() => buildGifPlaybackContract(fakeFrames, {evidenceFrames: [0, 1, 2, 3], gifFrames: [1, 1], gifTimingMs: [100, 100]}, {}), /duplicate index 1/);
assert.throws(() => buildGifPlaybackContract(fakeFrames, {evidenceFrames: [0, 1, 2, 3], gifFrames: [0, 2], gifTimingMs: [100]}, {}), /gifTimingMs.length/);

const vanguardScript = fs.readFileSync(new URL('vanguard_walk_render_blender.py', import.meta.url), 'utf8');
for (const required of [
  "'authoredKeys': authored_keys",
  "'evidenceFrames': evidence_frames",
  "'gifFrames': gif_frames",
  "'gifTimingMs': gif_timing_ms",
  "playback_contract(settings, rendered)",
]) assert(vanguardScript.includes(required), 'Vanguard script missing ' + required);

if (!hasTool('convert') || !hasTool('identify') || !hasTool('compare')) {
  console.log('Blender GIF construction contract: OK (ImageMagick encode/decode fixture skipped; convert/identify/compare unavailable)');
  process.exit(0);
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hc-gif-contract-'));
const frames = [0, 16, 32, 48].map((x, index) => {
  const file = path.join(dir, 'sprite-' + index + '.png');
  makeSprite(file, x);
  return file;
});
const outGif = path.join(dir, 'walk-loop.gif');
const playback = makeLoopingGif(frames, outGif, {scriptManifest: {
  authoredKeys: [0, 1, 2, 3, 4, 5],
  evidenceFrames: [0, 1, 2, 3],
  gifFrames: [0, 2, 1],
  gifTimingMs: [110, 90, 130],
  renderedFrames: frames.map((file) => path.basename(file)),
}});
assert.deepEqual(playback.gifFrames, [0, 2, 1]);
assert(fs.existsSync(outGif), 'GIF output must exist');
const identify = run('identify', ['-format', '%T %[dispose]\\n', outGif], 'identify gif disposal');
const rows = identify.trim().split(/\n+/).filter(Boolean).map((line) => line.trim().split(/\s+/));
assert.equal(rows.length, 3, 'decoded frame count must equal gifFrames.length');
assert.deepEqual(rows.map((row) => Number(row[0]) * 10), [110, 90, 130], 'decoded timing must match gifTimingMs');
assert(rows.every((row) => row[1] && row[1] !== 'Undefined' && row[1] !== 'None'), 'each frame must have explicit non-Undefined disposal');
assert(rows.every((row) => row[1] === 'Background'), 'each frame should use Background disposal');
const decodedPattern = path.join(dir, 'decoded-%03d.png');
run('convert', [outGif, '-coalesce', 'PNG32:' + decodedPattern], 'coalesce gif');
const decoded = [0, 1, 2].map((index) => path.join(dir, 'decoded-' + String(index).padStart(3, '0') + '.png'));
assert(decoded.every((file) => fs.existsSync(file)), 'coalesced frames must exist');
compareEqual(decoded[0], frames[0], 'playback frame 0 should match source frame 0');
compareEqual(decoded[1], frames[2], 'playback frame 1 should match source frame 2');
compareEqual(decoded[2], frames[1], 'playback frame 2 should match source frame 1');
compareDifferent(decoded[0], frames[1], 'frame 0 must not retain future/previous sprite');
compareDifferent(decoded[1], frames[0], 'frame 1 must not retain historical sprite');
compareDifferent(decoded[2], frames[2], 'frame 2 must not retain historical sprite');
const bounds = decoded.map((file) => run('convert', [file, '-alpha', 'extract', '-trim', '-format', '%@', 'info:'], 'alpha bounds').trim());
assert.deepEqual(bounds, ['8x8+0+8', '8x8+32+8', '8x8+16+8'], 'decoded alpha bounds must match selected source frames');
console.log('Blender GIF construction contract: OK');
