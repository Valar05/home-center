'use strict';
// Home Center MCP-to-MCP reply channel. The commissioned ChatGPT thread
// publishes ITS OWN answer through a connected MCP tool. The initiating thread
// retrieves the same text through MCP. No DOM, screenshot, CDP, or page parsing.
const {createHash,randomBytes,timingSafeEqual}=require('node:crypto');
const COL='ritsuChatMcpCallbacks';
const VERSION='ritsu-chat-mcp-callback-v1';
const ID=/^[A-Za-z0-9_.:-]{8,100}$/;
function fail(code,status=400){throw Object.assign(new Error(code),{status});}
function id(value,label){if(typeof value!=='string'||!ID.test(value))fail(label+'_invalid');return value;}
function hash(x){return createHash('sha256').update(x).digest('hex');}
function email(user){
  const v=String(user?.email||'').trim().toLowerCase();
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v))fail('authenticated_mcp_owner_required',401);
  return v;
}
function key(user,turnId){return hash(email(user)+'\n'+id(turnId,'turn_id'));}
function safeText(value) {
  if(typeof value!=='string'||!value.trim()||value.length>5000||
     /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value))
    fail('bounded_answer_text_required');
  return value;
}
function fixedEquals(a,b){
  const aa=Buffer.from(hash(String(a)),'hex'),bb=Buffer.from(hash(String(b)),'hex');
  return timingSafeEqual(aa,bb);
}
function entries(){return {
  'ritsu.chat.prepare':{
    summary:'Create one Home Center MCP callback ticket for a named ChatGPT turn. Returns a one-time scoped publication key on first creation. Does not open a browser or start a model.',
    write:true,requiresRequestId:true,requiredScopes:[],input:{
      requestId:'stable turn ID',sessionId:'Home Center session ID',
      channel:'control|dialogue',promptSha256:'optional exact prompt SHA256'
    }
  },
  'ritsu.chat.publish':{
    summary:'Called by the responding ChatGPT thread to publish its own answer to the initiating Home Center MCP ticket. This is a model-origin MCP callback, not a browser scrape.',
    write:true,requiresRequestId:true,requiredScopes:[],input:{
      requestId:'exact turn ID',sessionId:'exact session ID',channel:'control|dialogue',
      callbackKey:'scoped one-time key from prepare',text:'exact assistant answer'
    }
  },
  'ritsu.chat.result':{
    summary:'Retrieve the model-published answer for one owner-scoped ChatGPT turn, or report pending without claiming a response. No screen scraping.',
    write:false,requiresRequestId:false,requiredScopes:[],input:{turnId:'stable turn ID'}
  }
};}
async function prepare({admin,user,args={},now=Date.now()}){
  const turnId=id(args.requestId,'turn_id'),sessionId=id(args.sessionId,'session_id');
  const channel=args.channel||'control';
  if(!['control','dialogue'].includes(channel))fail('channel_invalid');
  const promptSha256=args.promptSha256||'';
  if(promptSha256 && !/^[a-f0-9]{64}$/.test(promptSha256))fail('prompt_hash_invalid');
  const ref=admin.firestore().collection(COL).doc(key(user,turnId));
  const secret=randomBytes(32).toString('base64url');
  const record={schema:1,version:VERSION,turnId,sessionId,channel,
    promptSha256,callbackHash:hash(secret),state:'prepared',
    ownerKey:hash(email(user)),createdAtMs:now,updatedAtMs:now,
    result:null,disposition:'model_mcp_publish_only'};
  let created=false;
  await admin.firestore().runTransaction(async tx=>{
    const old=await tx.get(ref);
    if(old.exists){
      const row=old.data();
      if(row.sessionId!==sessionId||row.channel!==channel||
         row.promptSha256!==promptSha256)fail('turn_id_collision',409);
      return;
    }
    tx.create(ref,record);created=true;
  });
  // Secret is returned ONCE. Never persisted in plaintext. A repeat does
  // not regenerate a second usable key or silently issue another turn.
  return {turnId,sessionId,channel,state:created?'prepared':'already_prepared',
    callbackKey:created?secret:null,callbackOperation:'ritsu.chat.publish',
    retrievalOperation:'ritsu.chat.result',source:'home_center_mcp',
    warning:created?null:'callback_key_was_returned_on_first_prepare_only'};
}
async function publish({admin,user,args={},now=Date.now()}){
  const turnId=id(args.requestId,'turn_id'),sessionId=id(args.sessionId,'session_id');
  const channel=args.channel||'control';
  if(!['control','dialogue'].includes(channel))fail('channel_invalid');
  const callbackKey=String(args.callbackKey||'');
  if(!/^[a-zA-Z0-9_-]{30,100}$/.test(callbackKey))fail('callback_key_invalid',401);
  const text=safeText(args.text);
  const ref=admin.firestore().collection(COL).doc(key(user,turnId));
  let repeated=false,updated=false;
  await admin.firestore().runTransaction(async tx=>{
    const snap=await tx.get(ref);
    if(!snap.exists)fail('chat_callback_not_prepared',404);
    const row=snap.data();
    if(row.sessionId!==sessionId||row.channel!==channel ||
       !fixedEquals(row.callbackHash,hash(callbackKey)))
      fail('chat_callback_identity_mismatch',403);
    if(row.state==='published'){
      if(row.result?.text!==text)fail('already_published_immutable',409);
      repeated=true;return;
    }
    if(row.state!=='prepared')fail('chat_callback_incompatible_state',409);
    tx.update(ref,{
      state:'published',result:{text,source:'responding_chat_mcp_tool_call',
        sessionId,turnId,channel,modelClaimed:true},
      updatedAtMs:now,publishedAtMs:now
    });
    updated=true;
  });
  return {turnId,sessionId,channel,state:'published',idempotent:repeated,
    accepted:updated||repeated,receipt:'mcp_model_publish',
    // Deliberately do not mark 'ChatGPT native API response verified'.
    provenance:'responding_mcp_tool_call'};
}
async function result({admin,user,args={}}) {
  const turnId=id(args.turnId||args.requestId,'turn_id');
  const snap=await admin.firestore().collection(COL).doc(key(user,turnId)).get();
  if(!snap.exists)fail('chat_callback_not_prepared',404);
  const row=snap.data();
  return {turnId,sessionId:row.sessionId,channel:row.channel,
    state:row.state,publishedAtMs:row.publishedAtMs||null,
    text:row.state==='published'?row.result?.text:null,
    source:row.state==='published'?'responding_chat_mcp_tool_call':null,
    nativeApiProvenance:false};
}
async function run({admin,user,operation,args={}}){
  if(operation==='ritsu.chat.prepare')return prepare({admin,user,args});
  if(operation==='ritsu.chat.publish')return publish({admin,user,args});
  if(operation==='ritsu.chat.result')return result({admin,user,args});
  fail('unsupported_ritsu_chat_mcp_operation');
}
module.exports={entryList:entries,runOperation:run,prepare,publish,result};
