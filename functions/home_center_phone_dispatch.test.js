'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {createHash} = require('node:crypto');

const source = fs.readFileSync(require.resolve('./home_center_mcp.js'), 'utf8');
const start = source.indexOf('async function commandCenterOperationRunOperation(');
const end = source.indexOf('\nfunction mcpToolJsonSchema(', start);
assert(start >= 0 && end > start, 'dispatch function must exist');

function harness() {
  const calls = [];
  const email = 'operator@example.com';
  const ctx = {
    createHash, calls,
    safeText: (x) => typeof x === 'string' ? x.trim() : '',
    commandCenterToolName: (x) => x.startsWith('command_center.') ? x : 'command_center.' + x,
    requireCreditGatedContext: async () => ({user:{email}}),
    assertHomeCenterIdentityAllowed: (x) => { assert.equal(x,email); calls.push(['auth',x]); },
    listPhoneDevices: async (_admin,caller) => {calls.push(['devices',caller]); return {devices:[]};},
    enqueuePhoneCommand: async (_admin,caller,args) => {calls.push(['enqueue',caller,args]); return {commandId:'phc_1',status:'queued'};},
    getPhoneCommand: async (_admin,caller,args) => {calls.push(['get',caller,args]); return {commandId:'phc_1',status:'succeeded'};},
    bearerTokenFromExtra: () => {calls.push(['bearer']); return 'token';},
    postCommandCenterMcp: async () => {calls.push(['remote']); throw Error('remote call forbidden');},
  };
  vm.createContext(ctx);
  vm.runInContext(source.slice(start,end) + '\nthis.dispatch = commandCenterOperationRunOperation;',ctx);
  return ctx;
}

for (const [operation,expected,args] of [
  ['command_center.phone_hands.devices','devices',{}],
  ['command_center.phone_hands.enqueue','enqueue',{idempotencyKey:'test-key',action:{action:'phone_shell',command:'true'}}],
  ['command_center.phone_hands.get','get',{commandId:'phc_1'}],
]) {
  test(operation + ' dispatches locally without remote MCP',async () => {
    const h = harness();
    const result = await h.dispatch({admin:{},args:{operation,args}});
    assert.equal(result.commandCenterMcpUrl,null);
    assert.equal(h.calls.filter(x=>x[0]===expected).length,1);
    assert.equal(h.calls.filter(x=>x[0]==='remote'||x[0]==='bearer').length,0);
    const caller=h.calls.find(x=>x[0]===expected)[1];
    assert.equal(caller.actor,'operator@example.com');
    assert.equal(caller.ownerKey,'owner_'+createHash('sha256').update(caller.actor).digest('hex').slice(0,32));
  });
}

test('non-phone operations preserve legacy remote routing',async () => {
  const h=harness();
  await assert.rejects(h.dispatch({admin:{},args:{operation:'command_center.health',args:{}}}),/remote call forbidden/);
  assert.equal(h.calls.filter(x=>x[0]==='remote').length,1);
});

test('phone relay is imported and native Computer Hands registration is retained',()=>{
  assert.match(source,/require\('\.\/phone_hands_relay'\)/);
  assert.match(source,/\.\.\.computerHandsOperationEntries\(\)/);
  assert.match(source,/computerHandsOperationRunOperation\(/);
});
