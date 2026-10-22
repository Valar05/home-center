'use strict';
const {createHash,randomBytes}=require('node:crypto');
const VERSION='ritsu-warm-typed-v1',VOICE='warm-v1',WORKER='cauldron-ritsu-warm-01',LEASE_MS=20*60*1000;
const COL={tickets:'ritsuWarmVoiceTickets',workers:'ritsuWarmVoiceWorkers',bootstrap:'ritsuWarmVoiceBootstrap',tokens:'ritsuWarmVoiceTokens'};
const ORIGIN=process.env.HOME_CENTER_RITSU_VOICE_ORIGIN||'https://us-central1-home-center-dclar.cloudfunctions.net/ritsuVoice';
function fail(message,status=400){throw Object.assign(new Error(message),{status});}
function hash(value){return createHash('sha256').update(String(value)).digest('hex');}
function id(s){if(typeof s!=='string'||!/^[A-Za-z0-9_.:-]{6,160}$/.test(s))fail('Invalid identifier');return s;}
function own(user){const email=String(user?.email||'').trim().toLowerCase();if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))fail('Authenticated owner required',401);return hash(email).slice(0,32);}
function key(owner,requestId){return hash(owner+'\n'+requestId);}
function validate(args){
 for(const k of Object.keys(args))if(!['requestId','text','voice','delivery','chunks'].includes(k))fail('Unexpected speech field');
 id(args.requestId);
 if(typeof args.text!=='string'||!args.text.trim()||args.text.length>5000||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(args.text))fail('Invalid dialogue');
 if(args.voice!==undefined&&args.voice!==VOICE)fail('Only approved Warm v1 is permitted');
 if(args.delivery!==undefined&&args.delivery!=='phone')fail('Only existing phone relay is permitted');
 const count=args.chunks===undefined?null:args.chunks;
 if(count!==null&&(!Number.isInteger(count)||count<1||count>50))fail('Invalid chunk count');
 return {requestId:args.requestId,text:args.text,textSha256:hash(args.text),voice:VOICE,delivery:'phone',expectedChunks:count};
}
function entries(){return {
 'ritsu.voice.speak':{summary:'Queue exact dialogue only for approved Warm v1 on existing Android Tailscale relay; no arbitrary shell, alternate voice or transport.',write:true,requiresRequestId:true,requiredScopes:[],input:{requestId:'stable unique id',text:'exact dialogue',voice:'warm-v1',delivery:'phone',chunks:'optional expected chunk count'}},
 'ritsu.voice.status':{summary:'Read Ritsu ticket state, enqueue receipts; hearing never implied.',write:false,requiresRequestId:false,requiredScopes:[],input:{requestId:'ticket ID'}},
 'ritsu.voice.worker.register':{summary:'One-time private bootstrap for THECAULDRON fixed Warm worker.',write:true,requiresRequestId:true,requiredScopes:[],input:{requestId:'stable unique id'}}
};}
async function speak({admin,user,args,now=Date.now()}){
 const owner=own(user),request=validate(args),ref=admin.firestore().collection(COL.tickets).doc(key(owner,request.requestId));let idempotent=false;
 await admin.firestore().runTransaction(async tx=>{
 const old=await tx.get(ref);
 if(old.exists){const row=old.data();if(row.request.textSha256!==request.textSha256||row.request.expectedChunks!==request.expectedChunks)fail('Idempotency conflict',409);idempotent=true;return;}
 tx.create(ref,{version:VERSION,ownerKey:owner,workerId:WORKER,request,status:'queued',createdAtMs:now,updatedAtMs:now,lease:null,result:null});
 });
 const row=(await ref.get()).data();return {ticketId:request.requestId,status:row.status,voice:VOICE,textSha256:request.textSha256,idempotent,heard:'not_verified'};
}
async function status({admin,user,args}){
 const owner=own(user),ticketId=id(args.requestId||args.ticketId);
 const snap=await admin.firestore().collection(COL.tickets).doc(key(owner,ticketId)).get();if(!snap.exists)fail('Ticket not found',404);
 const r=snap.data();return {ticketId,status:r.status,voice:VOICE,textSha256:r.request.textSha256,expectedChunks:r.request.expectedChunks,result:r.result||null,updatedAtMs:r.updatedAtMs,heard:'not_verified'};
}
async function register({admin,user,args,now=Date.now()}){
 const owner=own(user),requestId=id(args.requestId),code=randomBytes(24).toString('base64url'),ref=admin.firestore().collection(COL.bootstrap).doc(hash(code));
 await admin.firestore().runTransaction(async tx=>{tx.create(ref,{ownerKey:owner,workerId:WORKER,requestId,expiresAtMs:now+600000,used:false});tx.set(admin.firestore().collection(COL.workers).doc(key(owner,WORKER)),{ownerKey:owner,workerId:WORKER,state:'bootstrap_pending',updatedAtMs:now},{merge:true});});
 return {status:'bootstrap_ready',workerId:WORKER,origin:ORIGIN,bootstrapCode:code,expiresAtMs:now+600000,warning:'Private one-time code; never print or commit worker credentials'};
}
async function run({admin,user,operation,args={}}){
 if(operation==='ritsu.voice.speak')return speak({admin,user,args});
 if(operation==='ritsu.voice.status')return status({admin,user,args});
 if(operation==='ritsu.voice.worker.register')return register({admin,user,args});
 fail('Unsupported voice operation');
}
function body(req){return req.body&&typeof req.body==='object'&&!Buffer.isBuffer(req.body)?req.body:{};}
async function authenticate(admin,req,now=Date.now()){
 const m=String(req.get('Authorization')||'').match(/^Bearer ([A-Za-z0-9_-]+)$/);if(!m)fail('Bearer required',401);
 const snap=await admin.firestore().collection(COL.tokens).doc(hash(m[1])).get();if(!snap.exists)fail('Unknown worker',401);
 const w=snap.data();if(w.revoked||w.expiresAtMs<=now)fail('Token inactive',401);
 if(req.get('X-Home-Center-Worker')!==WORKER||w.workerId!==WORKER)fail('Worker mismatch',403);
 return w;
}
async function bootstrap({admin,args,now=Date.now()}){
 const code=String(args.bootstrapCode||'');if(!code||code.length>180)fail('Bootstrap required');
 const ref=admin.firestore().collection(COL.bootstrap).doc(hash(code)),token=randomBytes(32).toString('base64url');let data;
 await admin.firestore().runTransaction(async tx=>{
 const old=await tx.get(ref);if(!old.exists)fail('Bootstrap not found',404);data=old.data();
 if(data.used||data.expiresAtMs<=now)fail('Bootstrap used or expired',410);
 tx.update(ref,{used:true,usedAtMs:now});
 tx.create(admin.firestore().collection(COL.tokens).doc(hash(token)),{ownerKey:data.ownerKey,workerId:WORKER,expiresAtMs:now+90*86400000,createdAtMs:now,revoked:false});
 });
 return {status:'registered',workerId:WORKER,token,expiresAtMs:now+90*86400000};
}
async function lease({admin,worker,now=Date.now()}){
 const q=await admin.firestore().collection(COL.tickets).where('status','in',['queued','leased']).limit(200).get();
 const candidates=q.docs.filter(d=>{const r=d.data();return r.ownerKey===worker.ownerKey&&r.workerId===WORKER&&(r.status==='queued'||r.status==='leased'&&r.lease?.expiresAtMs<=now);}).sort((a,b)=>a.data().createdAtMs-b.data().createdAtMs);
 for(const candidate of candidates){let result=null;
 await admin.firestore().runTransaction(async tx=>{
 const old=await tx.get(candidate.ref);if(!old.exists)return;const row=old.data();
 if(row.ownerKey!==worker.ownerKey||!(row.status==='queued'||row.status==='leased'&&row.lease?.expiresAtMs<=now))return;
 tx.update(candidate.ref,{status:'leased',lease:{workerId:WORKER,expiresAtMs:now+LEASE_MS},updatedAtMs:now});
 result={ticketId:row.request.requestId,text:row.request.text,voice:VOICE,delivery:'phone',textSha256:row.request.textSha256,expectedChunks:row.request.expectedChunks};
 });if(result)return {ticket:result,pollAfterSeconds:1};
 }return {ticket:null,pollAfterSeconds:3};
}
async function complete({admin,worker,ticketId,args,now=Date.now()}){
 const name=id(ticketId),state=String(args.status||''),ids=Array.isArray(args.relayIds)?args.relayIds:[];
 if(!['enqueued','maintenance','failed'].includes(state))fail('Invalid completion state');
 if(ids.length>50||ids.some(x=>typeof x!=='string'||!/^[a-f0-9]{16,80}$/.test(x)))fail('Invalid relay IDs');
 const ref=admin.firestore().collection(COL.tickets).doc(key(worker.ownerKey,name));let response;
 await admin.firestore().runTransaction(async tx=>{
 const snap=await tx.get(ref);if(!snap.exists)fail('Ticket missing',404);const row=snap.data();
 if(row.ownerKey!==worker.ownerKey)fail('Worker mismatch',403);
 if(['enqueued','maintenance','failed'].includes(row.status)){response={ticketId:name,status:row.status,alreadyFinal:true};return;}
 if(row.status!=='leased'||row.lease?.expiresAtMs<=now)fail('Lease inactive',409);
 if(state==='enqueued'&&(!ids.length||(row.request.expectedChunks!==null&&ids.length!==row.request.expectedChunks)))fail('Incomplete ordered chunk receipts',422);
 const result={state,relayIds:ids,errorCode:state==='failed'?String(args.errorCode||'unknown').slice(0,90):null,heard:false};
 tx.update(ref,{status:state,result,lease:null,updatedAtMs:now});response={ticketId:name,status:state,relayIds:ids,heard:'not_verified'};
 });return response;
}
function handler({admin}){return async(req,res)=>{try{
 const path=String(req.path||req.url||'').replace(/^\/+/, '');
 if(req.method==='GET'&&path==='health')return res.status(200).json({ok:true,service:'ritsu-voice',voice:VOICE});
 if(req.method==='POST'&&path==='bootstrap')return res.status(200).json(await bootstrap({admin,args:body(req)}));
 const worker=await authenticate(admin,req);
 if(req.method==='POST'&&path==='lease')return res.status(200).json(await lease({admin,worker}));
 const match=path.match(/^tickets\/([A-Za-z0-9_.:-]{6,160})\/complete$/);
 if(req.method==='POST'&&match)return res.status(200).json(await complete({admin,worker,ticketId:match[1],args:body(req)}));
 return res.status(404).json({error:'Unknown route'});
 }catch(e){return res.status(e.status||500).json({error:e.status?e.message:'internal error'});}};}
module.exports={entryList:entries,runOperation:run,handler,validateSpeak:validate};
