import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {chunkSpokenText,createRitsuVoiceReturn} from './ritsu-voice-return.mjs';

test('bounded voice chunks preserve every word and punctuation',()=>{
  const text='Darling, '+('you matter deeply to this story. '.repeat(75))+'Goodnight. 💜';
  const chunks=chunkSpokenText(text);
  assert.ok(chunks.length>1);
  assert.ok(chunks.every(s=>s.length<=320));
  assert.equal(chunks.join(''),text);
  assert.throws(()=>chunkSpokenText('x'.repeat(5001)),/bounded/);
});

test('host canonical outbox is idempotent across instances and serialized',async t=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-voice-test-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  const sent=[];
  const sender=async ({index,text})=>{
    sent.push({index,text});
    return {ok:true,relayId:'verified-clip-'+index};
  };
  const first=createRitsuVoiceReturn({directory:dir,sender});
  const text='The first sentence. '+('Then some longer sentences. '.repeat(40));
  const record=await first.dispatchOnce({turnId:'ritsu-voice-control-001',text});
  assert.equal(record.state,'enqueued');
  assert.equal(record.heard,false);
  assert.equal(sent.map(s=>s.text).join(''),text);
  const second=createRitsuVoiceReturn({directory:dir,sender});
  assert.equal((await second.dispatchOnce({
    turnId:'ritsu-voice-control-001',text
  })).state,'enqueued');
  assert.equal(sent.length,chunkSpokenText(text).length);
  await assert.rejects(second.dispatchOnce({
    turnId:'ritsu-voice-control-001',text:'Different answer!'
  }),/voice_turn_id_collision/);
});

test('unknown audio acknowledgement is never blindly resent',async t=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-voice-unknown-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  let attempts=0;
  const sender=async()=>{attempts++;throw new Error('ACK may have been lost');};
  const turn={turnId:'ritsu-voice-uncertain-001',text:'Something to hear.'};
  const one=createRitsuVoiceReturn({directory:dir,sender});
  assert.equal((await one.dispatchOnce(turn)).state,'uncertain');
  const newInstance=createRitsuVoiceReturn({directory:dir,sender});
  assert.equal((await newInstance.dispatchOnce(turn)).state,'uncertain');
  assert.equal(attempts,1);
});
