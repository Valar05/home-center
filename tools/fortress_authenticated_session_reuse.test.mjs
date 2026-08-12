import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const cfg=JSON.parse(fs.readFileSync(new URL('../config/fortress-online.v2.json', import.meta.url),'utf8'));

test('authenticated_session_ignored is a first-class learned failure',()=>{
  const classifier=cfg.learning.classifiers.find(x=>x.kind==='authenticated_session_ignored');
  assert.ok(classifier,'missing authenticated_session_ignored classifier');
  assert.match('open ChatGPT already open authenticated session logged out profile',new RegExp(classifier.pattern,'i'));
  const recipe=cfg.learning.recipes.authenticated_session_ignored;
  assert.ok(recipe,'missing authenticated_session_ignored recipe');
  assert.match(recipe.rule,/enumerate.*session|authenticated.*session/i);
  assert.match(recipe.regression,/logged-out.*profile.*authenticated.*ChatGPT|authenticated.*ChatGPT.*logged-out/i);
});

test('Computer Hands doctrine requires machine-wide reusable auth discovery before login handoff',()=>{
  const hands=cfg.skills.find(x=>x.id==='computer-hands');
  assert.ok(hands);
  assert.ok(hands.invariants.some(x=>/authenticated.*session|session.*authenticated/i.test(x)));
  assert.ok(hands.invariants.some(x=>/login|authentication/i.test(x) && /Drew|operator|handoff/i.test(x)));
});
