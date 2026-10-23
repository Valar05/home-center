import {test} from 'node:test';
import assert from 'node:assert/strict';
import {RitsuNetworkSse} from './ritsu-network-sse.mjs';
const marker = 'RITSU_CANARY_XYZ';
const m = (text, opts={}) => ({message:{id:opts.id??'msg-1',author:{role:opts.role??'assistant'},recipient:opts.recipient??'all',content:{content_type:'text',parts:[text]},status:'finished_successfully',metadata:{channel:opts.channel??'final'}}});
const frame=o=>`data: ${JSON.stringify(o)}\n\n`;
const done='data: [DONE]\n\n';
test('recovers exact text from UTF8/sse byte fragmentation, snapshots and terminal event',()=>{
  const x=new RitsuNetworkSse();
  const data=Buffer.from(frame(m(`🦀 Partial`))+frame(m(`🦀 Fully answered ${marker}.`))+done,'utf8');
  for (let i=0;i<data.length;i++) x.push(data.subarray(i,i+1));
  const r=x.result({marker,requestFinished:true});
  assert.equal(r.text,`🦀 Fully answered ${marker}.`);
  assert.equal(r.eventCount,3);
});
test('filters reasoning, tool, hidden and unrelated traffic',()=>{
  const x=new RitsuNetworkSse();
  x.push(Buffer.from(frame(m(`leaked ${marker}`,{channel:'analysis'}))+frame(m(`leaked ${marker}`,{recipient:'python'}))+frame(m(`answer ${marker}`))+done));
  assert.equal(x.result({marker,requestFinished:true}).text,`answer ${marker}`);
});
test('never promotes a prompt or expected text without actual network bytes',()=>{
  const x=new RitsuNetworkSse();x.push(Buffer.from(done));
  assert.throws(()=>x.result({marker,requestFinished:true}),/no_matching_final/);
});
test('requires terminal marker and request end',()=>{
  const x=new RitsuNetworkSse();x.push(Buffer.from(frame(m(`answer ${marker}`))));
  assert.throws(()=>x.result({marker,requestFinished:true}),/not_terminal/);
});
test('rejects two final answer identities and incomplete nonassistant data',()=>{
  const x=new RitsuNetworkSse();x.push(Buffer.from(frame(m(marker))+frame(m(marker,{id:'other'}))+done));
  assert.throws(()=>x.result({marker,requestFinished:true}),/multiple_final/);
});
test('unknown wire formats remain unknown; never fabricate text',()=>{
  const x=new RitsuNetworkSse();x.push(Buffer.from('data: {"delta":"test"}\n\n'+done));
  assert.throws(()=>x.result({marker,requestFinished:true}),/no_matching_final/);
});

test('redacted shape diagnostic cannot contain message text or canary nonce',()=>{
  const x=new RitsuNetworkSse();
  const secret='USER_VISIBLE_PRIVATE_SENTENCE_'+marker;
  x.push(Buffer.from(frame(m(secret))+done));
  const diagnostic=JSON.stringify(x.diagnostic());
  assert.equal(diagnostic.includes(secret),false);
  assert.equal(diagnostic.includes(marker),false);
  assert.equal(x.diagnostic().eventCount,2);
  assert.equal(x.diagnostic().terminalDone,true);
  assert.equal(x.diagnostic().textCandidate,true);
});
