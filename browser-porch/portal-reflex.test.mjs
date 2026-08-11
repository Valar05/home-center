import test from 'node:test';
import assert from 'node:assert/strict';

import {createReflexState, normalizeObservation, parsePrompt, planPrompt} from './portal-reflex.mjs';

const DOM = {
  url: 'https://portal.example/claim/19284100',
  title: 'Claim overview',
  documentId: 'document-001',
  bodyTextLength: 800,
  semanticElements: [
    {ref: 'r1', role: 'button', name: 'View documents'},
    {ref: 'r2', role: 'textbox', name: 'Search claims'},
    {ref: 'r3', role: 'combobox', name: 'Document type'},
  ],
};

test('plain status prompt becomes DOM observation', () => assert.equal(parsePrompt('where am I').intent, 'observe'));
test('quoted click prompt is parsed without a model', () => assert.deepEqual(parsePrompt('click "View documents"'), {intent: 'click', target: 'View documents'}));
test('field entry has a fixed grammar', () => assert.deepEqual(parsePrompt('type "19284100" into "Search claims"'), {intent: 'set_value', value: '19284100', target: 'Search claims'}));
test('unknown prose asks instead of hallucinating', () => assert.equal(parsePrompt('handle the annoying insurance maze').intent, 'ask'));
test('submission requires separate approval', () => {
  const plan = planPrompt('submit', DOM);
  assert.equal(plan.action, 'ask');
  assert.equal(plan.requiresApproval, true);
});
test('uploads route to Computer Hands', () => {
  const plan = planPrompt('upload appeal packet', DOM);
  assert.equal(plan.action, 'route_native');
  assert.equal(plan.route, 'computer_hands');
});
test('exact accessible name resolves before substring', () => {
  const plan = planPrompt('click "View documents"', DOM);
  assert.equal(plan.action, 'click');
  assert.equal(plan.target.ref, 'r1');
  assert.equal(plan.locatorStrategy, 'accessible_name_exact');
});
test('ambiguous accessible names stop without mutation', () => {
  const plan = planPrompt('click "Document"', {...DOM, semanticElements: [{ref: 'a', name: 'Document one'}, {ref: 'b', name: 'Document two'}]});
  assert.equal(plan.action, 'ask');
});
test('first missing target refreshes DOM', () => {
  const plan = planPrompt('click "Appeal receipt"', DOM, createReflexState(), 20_000);
  assert.equal(plan.action, 'observe');
});
test('third attempt uses one bounded screenshot after two misses', () => {
  const state = createReflexState();
  assert.equal(planPrompt('click "Appeal receipt"', DOM, state, 20_000).action, 'observe');
  assert.equal(planPrompt('click "Appeal receipt"', DOM, state, 21_000).action, 'observe');
  const third = planPrompt('click "Appeal receipt"', DOM, state, 22_000);
  assert.equal(third.action, 'screenshot');
  assert.equal(third.screenshotReason, 'target_failed_twice');
});
test('sparse DOM asks for screenshot immediately', () => {
  const plan = planPrompt('look', {...DOM, bodyTextLength: 20, semanticElements: []}, createReflexState(), 20_000);
  assert.equal(plan.action, 'screenshot');
  assert.equal(plan.screenshotReason, 'dom_sparse');
});
test('visual surface asks for screenshot', () => assert.equal(planPrompt('look', {...DOM, visualSurface: true}, createReflexState(), 20_000).screenshotReason, 'visual_surface'));
test('unexpected document change asks for screenshot', () => assert.equal(planPrompt('look', {...DOM, unexpectedDocumentChange: true}, createReflexState(), 20_000).screenshotReason, 'unexpected_document_change'));
test('postcondition mismatch asks for screenshot', () => assert.equal(planPrompt('look', {...DOM, postconditionMismatch: true}, createReflexState(), 20_000).screenshotReason, 'postcondition_mismatch'));
test('automatic screenshot is rate limited per document', () => {
  const state = createReflexState();
  assert.equal(planPrompt('look', {...DOM, visualSurface: true}, state, 20_000).action, 'screenshot');
  assert.equal(planPrompt('look', {...DOM, visualSurface: true}, state, 21_000).action, 'observe');
  assert.equal(planPrompt('look', {...DOM, visualSurface: true}, state, 31_000).action, 'screenshot');
});
test('explicit screenshot bypasses automatic cooldown', () => {
  const state = createReflexState();
  assert.equal(planPrompt('screenshot', DOM, state, 20_000).action, 'screenshot');
  assert.equal(planPrompt('screenshot', DOM, state, 20_001).action, 'screenshot');
});
test('sensitive typed value is hashed and absent from receipt', () => {
  const plan = planPrompt('type "private-value" into "Search claims"', DOM);
  assert.equal(plan.action, 'set_value');
  assert.equal(JSON.stringify(plan.receipt).includes('private-value'), false);
  assert.match(plan.receipt.valueHash, /^[a-f0-9]{64}$/);
});
test('identical first inputs produce identical receipt hashes', () => {
  const a = planPrompt('click "View documents"', DOM, createReflexState(), 20_000);
  const b = planPrompt('click "View documents"', DOM, createReflexState(), 20_000);
  assert.equal(a.receipt.receiptSha256, b.receipt.receiptSha256);
});
test('receipt records no model or inference network', () => {
  const receipt = planPrompt('where am I', DOM).receipt;
  assert.equal(receipt.modelUsed, false);
  assert.equal(receipt.networkInferenceUsed, false);
});
test('normalization produces stable document fingerprint', () => {
  assert.equal(normalizeObservation(DOM).documentFingerprint, normalizeObservation({...DOM}).documentFingerprint);
});

