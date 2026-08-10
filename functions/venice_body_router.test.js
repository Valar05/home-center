'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  classifyLane,
  browserActionName,
  mapComputerAction,
  browserEpisodeVerifiesAction,
  browserFallbackAction,
} = require('./venice_body_router');

test('browser verbs prefer Browser Nerve while machine verbs use Computer Hands', () => {
  assert.equal(classifyLane({verb: 'browser.click'}), 'browser');
  assert.equal(classifyLane({verb: 'browser.navigate'}), 'browser');
  assert.equal(classifyLane({verb: 'window.focus'}), 'computer');
  assert.equal(classifyLane({verb: 'media.play'}), 'computer');
  assert.equal(classifyLane({channel: 'computer', verb: 'browser.click'}), 'computer');
});

test('browser action names remain semantic and selector-friendly', () => {
  assert.equal(browserActionName('browser.open'), 'navigate');
  assert.equal(browserActionName('browser.set_value'), 'type');
  assert.equal(browserActionName('browser.click'), 'click');
});

test('computer mapping never converts browser click into pixel input', () => {
  assert.throws(() => mapComputerAction({verb: 'browser.click'}), /Unsupported Venice computer-body verb/);
  assert.deepEqual(mapComputerAction({verb: 'window.focus', arguments: {title: 'Chrome'}}), {action: 'window.focus', arguments: {title: 'Chrome'}});
  assert.equal(mapComputerAction({verb: 'media.play', target: {path: 'G:\\My Drive\\clip.mp4'}}).action, 'process.start');
});

test('requested browser action is not verified without an observed successful episode', () => {
  const actionId = 'browser_action_123';
  assert.equal(browserEpisodeVerifiesAction({episodes: []}, actionId), false);
  assert.equal(browserEpisodeVerifiesAction({episodes: [{outcome: 'observed', actions: [{actionId}]}]}, actionId), false);
  assert.equal(browserEpisodeVerifiesAction({episodes: [{outcome: 'completed', actions: [{actionId}]}]}, actionId), true);
});

test('browser fallbacks preserve page/machine boundary', () => {
  const nav = browserFallbackAction({verb: 'browser.navigate', target: {url: 'https://example.com'}});
  assert.equal(nav.kind, 'equivalent_action');
  assert.equal(nav.action, 'process.start');
  const click = browserFallbackAction({verb: 'browser.click', target: {role: 'button', name: 'Send'}});
  assert.equal(click.kind, 'observation_only');
  assert.equal(click.action, 'screen.capture');
});
