import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {CampaignJournal} from './journal.mjs';
import {SCRIPT_PROTOCOL} from './contract.mjs';

test('campaign journal survives process recreation, replays no script twice',async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'ritsu-journal-test-'));
 try{
  const j=await CampaignJournal.open(root);
  assert.equal(j.state.phase,'uninitialized');
  const receipt={protocol:SCRIPT_PROTOCOL,kind:'script_receipt',
    campaignId:'campaign-test-00001',tabId:'main',
    scriptId:'script-0000001',sha256:'a'.repeat(64),
    status:'succeeded',verified:true,output:'ok'};
  await j.append({event:'script_commissioned',scriptId:'script-0000001',
    sha256:receipt.sha256});
  await j.append({event:'script_receipt',scriptId:'script-0000001',receipt});
  await j.checkpoint({phase:'continue_required',lastScriptId:'script-0000001'});
  await j.ownerStop();
  const resumed=await CampaignJournal.open(root);
  assert.equal(resumed.state.phase,'continue_required');
  assert.equal(resumed.receipts.get('script-0000001').output,'ok');
  assert.equal(await resumed.isOwnerStopped(),true);
  assert.equal(resumed.receiptSummary().done,false);
  await resumed.clearOwnerStop();
  assert.equal(await resumed.isOwnerStopped(),false);
  await resumed.checkpoint({phase:'completed',
      by:'agent_explicit_complete',finalText:'Finished'});
  const last=await CampaignJournal.open(root);
  assert.equal(last.receiptSummary().done,true);
  assert.equal(last.state.finalText,'Finished');
  const lines=(await fs.readFile(path.join(root,'history.jsonl'),'utf8')).trim().split('\n');
  assert.equal(lines.length,2);
 }finally{await fs.rm(root,{recursive:true,force:true});}
});
test('journal refuses corruption instead of erasing work',async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'ritsu-corrupt-test-'));
 try{
  await fs.writeFile(path.join(root,'history.jsonl'),'not-json\n');
  await assert.rejects(CampaignJournal.open(root),SyntaxError);
  assert.equal(await fs.readFile(path.join(root,'history.jsonl'),'utf8'),'not-json\n');
 }finally{await fs.rm(root,{recursive:true,force:true});}
});
