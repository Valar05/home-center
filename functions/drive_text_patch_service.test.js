'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {applyTextPatches, protectedRegionDigests} = require('./drive_text_patch_service');

test('exact and between patches are deterministic', () => {
  const source = 'alpha\n<!-- ART -->old art<!-- /ART -->\n<script>keep()</script>\nomega\n';
  const before = protectedRegionDigests(source, [{label: 'runtime', startMarker: '<script>', endMarker: '</script>'}]);
  const patched = applyTextPatches(source, [
    {label: 'word', mode: 'exact', find: 'alpha', replace: 'beta', expectedCount: 1},
    {label: 'art', mode: 'between', startMarker: '<!-- ART -->', endMarker: '<!-- /ART -->', replace: 'new art'},
  ]);
  assert.equal(patched.text, 'beta\n<!-- ART -->new art<!-- /ART -->\n<script>keep()</script>\nomega\n');
  assert.deepEqual(patched.receipts.map((item) => [item.label, item.actualCount]), [['word', 1], ['art', 1]]);
  const after = protectedRegionDigests(patched.text, [{label: 'runtime', startMarker: '<script>', endMarker: '</script>'}]);
  assert.equal(after[0].sha256, before[0].sha256);
  assert.equal(after[0].byteCount, before[0].byteCount);
});

test('exact patch refuses an unexpected match count', () => {
  assert.throws(() => applyTextPatches('x x', [{mode: 'exact', find: 'x', replace: 'y', expectedCount: 1}]), /expected 1 exact matches but found 2/);
});

test('between patch refuses ambiguous markers', () => {
  assert.throws(() => applyTextPatches('A one B A two B', [{mode: 'between', startMarker: 'A', endMarker: 'B', replace: 'z'}]), /markers must each occur exactly once/);
});

test('protected region digest changes when protected bytes change', () => {
  const spec = [{label: 'runtime', startMarker: '<script>', endMarker: '</script>'}];
  const a = protectedRegionDigests('<script>one()</script>', spec);
  const b = protectedRegionDigests('<script>two()</script>', spec);
  assert.notEqual(a[0].sha256, b[0].sha256);
});
