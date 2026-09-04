'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  SOCIAL_MAX_STEPS,
  cleanSocialUrl,
  cleanSocialWorkflow,
  splitReplyFragments,
  browserSocialOperationEntries,
} = require('./browser_social_operator');

const startUrl = new URL('https://example.social/compose');
const allowedOrigins = ['https://example.social'];
const publishSteps = () => [
  {stepId: 'account-read', action: 'read', target: {selector: '[data-account]'}, captureAs: 'account'},
  {stepId: 'content-type', action: 'type', target: {role: 'textbox', name: 'Post text'}, valueSource: 'content'},
  {stepId: 'publish-click', action: 'click', target: {role: 'button', name: 'Publish'}, mutation: 'publish'},
  {stepId: 'post-read', action: 'read', target: {selector: '[data-post]'}, captureAs: 'post'},
  {stepId: 'permalink-read', action: 'read', target: {selector: '[data-permalink]'}, captureAs: 'permalink'},
];

test('public social URL rejects local/private surfaces', () => {
  assert.equal(cleanSocialUrl('https://bsky.app/').origin, 'https://bsky.app');
  assert.throws(() => cleanSocialUrl('http://127.0.0.1:9000'), /public https/);
  assert.throws(() => cleanSocialUrl('https://localhost/messages'), /public https/);
});

test('publish workflow preserves public-authority invariants', () => {
  const cleaned = cleanSocialWorkflow('publish', publishSteps(), {startUrl, allowedOrigins});
  assert.equal(cleaned.length, 5);
  assert.equal(cleaned[1].valueSource, 'content');
  assert.equal(cleaned[2].mutation, true);
  assert.equal(cleaned[3].captureAs, 'post');
});

test('publish workflow requires account before mutation and proof after mutation', () => {
  const lateAccount = publishSteps();
  lateAccount.splice(0, 1);
  lateAccount.push({stepId: 'late-account', action: 'read', target: {selector: '[data-account]'}, captureAs: 'account'});
  assert.throws(() => cleanSocialWorkflow('publish', lateAccount, {startUrl, allowedOrigins}), /before publication/);
  const missingPermalink = publishSteps().filter((step) => step.captureAs !== 'permalink');
  assert.throws(() => cleanSocialWorkflow('publish', missingPermalink, {startUrl, allowedOrigins}), /permalink capture/);
});

test('replies workflow is read-only and excludes private paths and coordinates', () => {
  assert.throws(() => cleanSocialWorkflow('replies', [{stepId: 'reply-type', action: 'type', target: {selector: '#x'}, valueSource: 'content'}, {stepId: 'reply-read', action: 'read', target: {selector: '#r'}, captureAs: 'replies'}], {startUrl, allowedOrigins}), /cannot type/);
  assert.throws(() => cleanSocialWorkflow('replies', [{stepId: 'private-nav', action: 'navigate', target: {url: 'https://example.social/messages'}}, {stepId: 'reply-read', action: 'read', target: {selector: '#r'}, captureAs: 'replies'}], {startUrl, allowedOrigins}), /private inbox\/account/);
  assert.throws(() => cleanSocialWorkflow('replies', [{stepId: 'pixel-click', action: 'click', target: {coordinates: [1, 2]}}, {stepId: 'reply-read', action: 'read', target: {selector: '#r'}, captureAs: 'replies'}], {startUrl, allowedOrigins}), /pixel-coordinate/);
});

test('recon defaults to a finite navigate and observe workflow', () => {
  const steps = cleanSocialWorkflow('recon', [], {startUrl, allowedOrigins});
  assert.equal(steps.length, 2);
  assert.equal(steps[0].action, 'navigate');
  assert.equal(steps[1].captureAs, 'recon');
  assert.ok(steps.length <= SOCIAL_MAX_STEPS);
});

test('reply fragments are stable and bounded', () => {
  const fragments = splitReplyFragments('Alice: Neat idea.\n\nBob: How did you handle state?\n\nAlice: Neat idea.');
  assert.equal(fragments.length, 3);
  assert.equal(fragments[0].hash, fragments[2].hash);
  assert.notEqual(fragments[0].hash, fragments[1].hash);
});

test('Home Center registry exposes the bounded social loop', () => {
  const operations = browserSocialOperationEntries();
  assert.ok(operations['browser_nerve.social.recon']);
  assert.ok(operations['browser_nerve.social.publish']);
  assert.ok(operations['browser_nerve.social.replies']);
  assert.ok(operations['browser_nerve.social.advance']);
  assert.ok(operations['browser_nerve.social.get']);
  assert.equal(operations['browser_nerve.social.get'].write, false);
});
