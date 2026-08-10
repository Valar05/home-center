'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const {CONTRACT_VERSION, SUPPORTED_ACTIONS, ownerKey, actionName} = require('./browser_nerve_api');

test('Browser Nerve contract is selector worker v1', () => {
  assert.equal(CONTRACT_VERSION, 'home-center.browser-nerve-contract.v1');
  assert.ok(SUPPORTED_ACTIONS.includes('navigate'));
  assert.ok(SUPPORTED_ACTIONS.includes('click'));
  assert.ok(SUPPORTED_ACTIONS.includes('type'));
  assert.ok(!SUPPORTED_ACTIONS.includes('mouse.click'));
  assert.ok(!SUPPORTED_ACTIONS.includes('screen.capture'));
});

test('owner key matches Command Center owner partition algorithm', () => {
  const email = 'dclarke1005@gmail.com';
  const expected = `owner_${createHash('sha256').update(email).digest('hex').slice(0, 32)}`;
  assert.equal(ownerKey(email), expected);
});

test('Browser Nerve accepts only its explicit semantic action vocabulary', () => {
  assert.equal(actionName('CLICK'), 'click');
  assert.equal(actionName('wait_for'), 'wait_for');
  assert.throws(() => actionName('input.mouse'), /Unsupported Browser Nerve action/);
  assert.throws(() => actionName('purchase'), /Unsupported Browser Nerve action/);
});
