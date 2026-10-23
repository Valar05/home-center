// Approved Pocket TTS / canonical 19643 relay return, no alternate audio path.
// Per-instance outbox, per-turn durable journal, no global singleton.
// Enqueue != receiver consumed != user heard.
import {mkdir,open,readFile,rename,rm} from 'node:fs/promises';
import {createHash,randomUUID} from 'node:crypto';
import path from 'node:path';
const ID=/^[A-Za-z0-9_.:-]{8,100}$/;
const hash=s=>createHash('sha256').update(s).digest('hex');
export function chunkSpokenText(text,maximum=320) {
  if(typeof text!=='string'||!text.trim()||text.length>5000 ||
      !Number.isInteger(maximum)||maximum<100||maximum>600)
    throw new Error('bounded_voice_text_required');
  const chunks=[];
  let rest=text;
  while(rest.length>maximum) {
    const boundary=rest.lastIndexOf(' ',maximum);
    const end=boundary>=Math.floor(maximum/2)?boundary+1:maximum;
    chunks.push(rest.slice(0,end));
    rest=rest.slice(end);
  }
  if(rest)chunks.push(rest);
  if(chunks.join('')!==text||chunks.length>40)throw new Error('voice_chunk_integrity_failed');
  return chunks;
}
async function writeAtomic(file,body) {
  const tmp=file+'.'+randomUUID()+'.tmp';
  try {
    const handle=await open(tmp,'wx',0o600);
    try {await handle.writeFile(JSON.stringify(body));await handle.sync();}
    finally {await handle.close();}
    await rename(tmp,file);
  }finally{await rm(tmp,{force:true}).catch(()=>{});}
}
export function createRitsuVoiceReturn({directory,sender}={}) {
  if(!path.isAbsolute(directory||''))throw new Error('private_absolute_voice_directory_required');
  if(typeof sender!=='function')throw new Error('canonical_voice_sender_required');
  const fileFor=turnId=>path.join(directory,hash(turnId)+'.json');
  return Object.freeze({
    async dispatchOnce({turnId,text}={}) {
      if(!ID.test(String(turnId||'')))throw new Error('turn_id_invalid');
      const chunks=chunkSpokenText(text);
      const textHash=hash(text);
      await mkdir(directory,{recursive:true,mode:0o700});
      const file=fileFor(turnId),lock=file+'.lock';
      let guard;
      const deadline=Date.now()+8000;
      while(!guard) {
        try{guard=await open(lock,'wx',0o600);}
        catch(e) {
          if(e.code!=='EEXIST'||Date.now()>=deadline)
            throw new Error('voice_outbox_locked_manual_recovery_required');
          await new Promise(resolve=>setTimeout(resolve,50));
        }
      }
      try {
        let state;
        try{state=JSON.parse(await readFile(file,'utf8'));}
        catch(e) {
          if(e.code!=='ENOENT')throw e; // corrupt journal is NOT an empty queue
          state={schema:1,turnId,textHash,chunks:chunks.map((t,index)=>({
            index,chunkHash:hash(t),status:'pending',relayId:null
          }))};
          await writeAtomic(file,state);
        }
        if(state.schema!==1||state.turnId!==turnId||state.textHash!==textHash||
            state.chunks.length!==chunks.length||
            state.chunks.some((r,i)=>r.chunkHash!==hash(chunks[i])))
          throw new Error('voice_turn_id_collision');
        for(let index=0;index<chunks.length;index++) {
          const row=state.chunks[index];
          if(row.status==='enqueued')continue;
          if(row.status!=='pending')
            return {state:'uncertain',turnId,queuedChunks:index,
              reason:'prior_audio_enqueue_may_have_succeeded_do_not_replay'};
          // Persist the attempt *before* the irreversible phone relay enqueue.
          row.status='attempt_unknown';
          await writeAtomic(file,state);
          try {
            const reply=await sender({turnId,index,text:chunks[index]});
            if(!reply||reply.ok!==true||typeof reply.relayId!=='string'||
                !ID.test(reply.relayId))
              throw new Error('canonical_audio_relay_receipt_missing');
            row.status='enqueued';
            row.relayId=reply.relayId;
            await writeAtomic(file,state);
          }catch {
            return {state:'uncertain',turnId,queuedChunks:index,
              reason:'audio_enqueue_unverified_no_automatic_retry'};
          }
        }
        return {state:'enqueued',turnId,queuedChunks:chunks.length,
          // This proves only host relay submission, NEVER audible playback.
          heard:false};
      } finally {
        try{await guard.close();}finally{await rm(lock,{force:true});}
      }
    },
  });
}
