'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const {LOCKED_PORTRAIT_SHA256, VeniceBodyState} = require('./core');

test('portrait identity is pinned to the recovered non-canon source hash', () => {
  assert.equal(LOCKED_PORTRAIT_SHA256, 'e068976188595971194b1d7945750086c65b701eafa04c40db53d95d84884cd8');
});

test('restart state fails closed and begin requires the verified portrait', () => {
  const unavailable = new VeniceBodyState();
  assert.equal(unavailable.snapshot().state, 'DORMANT');
  assert.throws(() => unavailable.apply({type: 'begin'}), /portrait is unavailable/);
  const ready = new VeniceBodyState({portraitReady: true});
  assert.equal(ready.apply({type: 'begin'}).state, 'PRESENT');
  assert.equal(ready.snapshot().epoch, 1);
});

test('motion and speech reject stale epochs', () => {
  const body = new VeniceBodyState({portraitReady: true, voiceReady: true});
  const begun = body.apply({type: 'begin'});
  assert.throws(() => body.apply({type: 'gesture', gesture: 'nod', epoch: begun.epoch - 1}), /stale/);
  assert.equal(body.apply({type: 'gesture', gesture: 'nod', epoch: begun.epoch}).gesture, 'nod');
  assert.equal(body.apply({type: 'speak', caption: 'Venice is present.', epoch: begun.epoch}).speaking, true);
});

test('CUT THE CAM always wins and clears visible and spoken output', () => {
  const body = new VeniceBodyState({portraitReady: true, voiceReady: true});
  const begun = body.apply({type: 'begin'});
  body.apply({type: 'expression', expression: 'soft', epoch: begun.epoch});
  body.apply({type: 'speak', caption: 'A line that must disappear.', epoch: begun.epoch});
  const cut = body.apply({type: 'cut'});
  assert.deepEqual({state: cut.state, caption: cut.caption, speaking: cut.speaking, gesture: cut.gesture}, {
    state: 'CUT', caption: '', speaking: false, gesture: 'still',
  });
  assert.equal(cut.cutEpoch, 1);
  assert.throws(() => body.apply({type: 'speak', caption: 'stale', epoch: begun.epoch}), /not PRESENT/);
});

test('browser surface keeps captions, keyboard cut, and nonvisual status', () => {
  const html = fs.readFileSync(path.join(__dirname, 'public', 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(__dirname, 'public', 'app.js'), 'utf8');
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /id="cut"/);
  assert.match(app, /event\.key === 'Escape'/);
  assert.match(app, /fetch\('\/cut'/);
  assert.doesNotMatch(app, /https?:\/\//);
});
