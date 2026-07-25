import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {frameRecords, makeLoopingGif, resolveGifPlaybackContract} from '../cloud-render/src/render_bundle.mjs';

function need(cmd) {
  const res = spawnSync('sh', ['-c', `command -v ${cmd}`], {encoding: 'utf8'});
  assert.equal(res.status, 0, `${cmd} is required for decoder-backed GIF tests`);
}
function run(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, {encoding: 'utf8', timeout: 60000, ...opts});
  assert.equal(res.status, 0, `${cmd} ${args.join(' ')} failed: ${res.stderr || res.stdout}`);
  return res.stdout || '';
}
function throwsMessage(fn, text) {
  assert.throws(fn, (err) => String(err && err.message || err).includes(text));
}
function pixelText(file) {
  return run('convert', [file, 'txt:-']);
}
function nonTransparentPixels(file) {
  const pixels = [];
  for (const line of pixelText(file).split('\n')) {
    const match = line.match(/^(\d+),(\d+):.*(?:srgba|rgba)\(([^)]*)\)/i);
    if (!match) continue;
    const x = Number(match[1]);
    const y = Number(match[2]);
    const parts = match[3].split(',').map((part) => part.trim());
    const alphaRaw = parts[3] || '1';
    const alpha = alphaRaw.endsWith('%') ? Number(alphaRaw.slice(0, -1)) / 100 : Number(alphaRaw);
    if (alpha > 0) pixels.push({x, y, text: line});
  }
  return pixels;
}
function bounds(pixels) {
  return {
    x: Math.min(...pixels.map((p) => p.x)),
    y: Math.min(...pixels.map((p) => p.y)),
    w: Math.max(...pixels.map((p) => p.x)) - Math.min(...pixels.map((p) => p.x)) + 1,
    h: Math.max(...pixels.map((p) => p.y)) - Math.min(...pixels.map((p) => p.y)) + 1,
  };
}
function assertOneSprite(file, expected) {
  const pixels = nonTransparentPixels(file);
  assert.equal(pixels.length, 64, `${path.basename(file)} should contain exactly one 8x8 sprite`);
  assert.deepEqual(bounds(pixels), {x: expected.x, y: expected.y, w: 8, h: 8});
  for (const prior of positions) {
    const center = run('convert', [file, '-format', `%[pixel:p{${prior.x + 3},${prior.y + 3}}]`, 'info:']).trim();
    if (prior.index === expected.index) {
      assert.match(center, /srgb|srgba|rgba/i, 'selected sprite center should be nontransparent');
      assert.doesNotMatch(center, /\b0\)$/i, 'selected sprite center should not be alpha zero');
    } else {
      assert.match(center, /none|transparent|rgba\(0,0,0,0\)|srgba\([^)]*,0\)/i, `excluded/prior sprite position ${prior.index} leaked into ${expected.index}: ${center}`);
    }
  }
}
function disposalList(file) {
  const formatted = spawnSync('identify', ['-format', '%[dispose]\n', file], {encoding: 'utf8'});
  if (formatted.status === 0 && formatted.stdout.trim()) return formatted.stdout.trim().split(/\n+/);
  const verbose = run('identify', ['-verbose', file]);
  return [...verbose.matchAll(/Dispose:\s*(\S+)/g)].map((m) => m[1]);
}
function delayList(file) {
  return run('identify', ['-format', '%T\n', file]).trim().split(/\n+/).map(Number);
}

need('convert');
need('identify');

const work = fs.mkdtempSync(path.join(os.tmpdir(), 'cloud-render-gif-test-'));
const positions = [
  {index: 0, x: 2, y: 16, color: '#ff0000ff'},
  {index: 1, x: 18, y: 16, color: '#00ff00ff'},
  {index: 2, x: 34, y: 16, color: '#0000ffff'},
  {index: 3, x: 50, y: 16, color: '#ffff00ff'},
  {index: 4, x: 66, y: 16, color: '#ff00ffff'},
];
const frames = [];
for (const pos of positions) {
  const file = path.join(work, `frame-${pos.index}.png`);
  run('convert', ['-size', '80x40', 'xc:none', '-fill', pos.color, '-draw', `rectangle ${pos.x},${pos.y} ${pos.x + 7},${pos.y + 7}`, file]);
  frames.push(file);
}
const evidence = frameRecords(frames, frames.map((_, i) => `frames/frame-${i}.png`));
const explicit = resolveGifPlaybackContract(evidence, {gifFrames: [0, 2, 4], gifTimingMs: [110, 100, 130]}, {authoredKeys: [0, 1, 2, 3, 4, 5, 6]}, {});
assert.equal(explicit.gifFrameSelection, 'explicit');
assert.deepEqual(explicit.gifFrames, [0, 2, 4]);
assert.deepEqual(explicit.gifTimingMs, [110, 100, 130]);
assert.deepEqual(explicit.excludedFrames, [1, 3]);
assert.deepEqual(explicit.authoredKeys, [0, 1, 2, 3, 4, 5, 6]);
const gif = path.join(work, 'subset.gif');
assert.equal(makeLoopingGif(explicit.gifFrames.map((i) => evidence[i]), gif, explicit), true);
const decodedPattern = path.join(work, 'decoded-%02d.png');
run('convert', [gif, '-coalesce', decodedPattern]);
const decoded = fs.readdirSync(work).filter((name) => /^decoded-\d+\.png$/.test(name)).sort().map((name) => path.join(work, name));
assert.equal(decoded.length, 3, 'exactly three displayed frames should decode');
const selectedPositions = [positions[0], positions[2], positions[4]];
decoded.forEach((file, i) => assertOneSprite(file, selectedPositions[i]));
assert.deepEqual(delayList(gif), [11, 10, 13], 'decoded GIF timing must match requested durations in centiseconds');
const disposal = disposalList(gif);
assert.equal(disposal.length, 3, 'disposal metadata should exist for every encoded frame');
for (const [index, value] of disposal.entries()) {
  assert.notEqual(value, 'Undefined', `frame ${index} disposal must not be Undefined`);
  assert.equal(value, 'Background', `frame ${index} disposal should be Background`);
}

const fallback = resolveGifPlaybackContract(evidence, {}, {frameDurationsMs: [90, 91, 92, 93, 94]}, {});
assert.equal(fallback.gifFrameSelection, 'fallback');
assert.deepEqual(fallback.gifFrames, [0, 1, 2, 3, 4]);
assert.deepEqual(fallback.gifTimingMs, [90, 91, 92, 93, 94]);
throwsMessage(() => resolveGifPlaybackContract(evidence, {gifFrames: [], gifTimingMs: []}, {}, {}), 'gifFrames must not be empty');
throwsMessage(() => resolveGifPlaybackContract(evidence, {gifFrames: [0, 5], gifTimingMs: [100, 100]}, {}, {}), 'out of range');
throwsMessage(() => resolveGifPlaybackContract(evidence, {gifFrames: [0, 1.5], gifTimingMs: [100, 100]}, {}, {}), 'must be an integer');
throwsMessage(() => resolveGifPlaybackContract(evidence, {gifFrames: [0, 1], gifTimingMs: [100]}, {}, {}), 'gifTimingMs.length');
throwsMessage(() => resolveGifPlaybackContract(evidence, {gifFrames: [0, 1], gifTimingMs: [100, 0]}, {}, {}), 'positive finite');
throwsMessage(() => resolveGifPlaybackContract(evidence, {gifFrames: [0, 0], gifTimingMs: [100, 100]}, {}, {}), 'duplicate');
const repeated = resolveGifPlaybackContract(evidence, {gifFrames: [0, 0], gifTimingMs: [100, 100], allowRepeatedGifFrames: true}, {}, {});
assert.deepEqual(repeated.gifFrames, [0, 0]);
console.log(JSON.stringify({ok: true, gif, frameCount: decoded.length, gifFrames: explicit.gifFrames, gifTimingMs: explicit.gifTimingMs, disposal, transparentNoResidue: true}, null, 2));
