// Android -> Home Center boundary. Independent, per-campaign instances.
// No direct Android -> browser bearer, no worker fanout, no singleton.
// Production MUST bind to a specific Tailscale-owned 100.64/10 address.
import http from 'node:http';
import {createHash,timingSafeEqual} from 'node:crypto';

const ID=/^[A-Za-z0-9_.:-]{8,100}$/;
const MAX_BYTES=6500;
function tailnetIPv4(host) {
  const n=String(host||'').split('.');
  if(n.length!==4 || n.some(s=>!/^\d{1,3}$/.test(s)||Number(s)>255))return false;
  const x=n.map(Number);
  return x[0]===100 && x[1]>=64 && x[1]<=127;
}
function constantTimeEqual(a,b) {
  const left=createHash('sha256').update(String(a)).digest();
  const right=createHash('sha256').update(String(b)).digest();
  return timingSafeEqual(left,right);
}
function response(res,status,value) {
  res.writeHead(status,{
    'content-type':'application/json; charset=utf-8',
    'cache-control':'no-store',
    'x-content-type-options':'nosniff',
    'referrer-policy':'no-referrer',
  });
  res.end(JSON.stringify(value));
}
async function readRequestBody(req) {
  let bytes=0;
  const parts=[];
  for await(const part of req) {
    bytes+=part.length;
    if(bytes>MAX_BYTES)throw new Error('body_too_large');
    parts.push(part);
  }
  try{return JSON.parse(Buffer.concat(parts).toString('utf8'));}
  catch{throw new Error('invalid_json');}
}
function safeRow(row) {
  if(!row)return {state:'missing'};
  return {
    turnId:row.turn?.turnId,
    channel:row.turn?.channel,
    state:row.state,
    // The exact browser reply is exposed ONLY after the coordinator verifies
    // the completion envelope. No raw worker/private draft is exported.
    result:row.state==='completed'&&row.turn?.channel==='control'
      ? {text:row.result?.text,tabId:row.result?.tabId} : null,
  };
}

/** A trusted Home Center operator must configure client token out-of-band.
 *  Android stores this separate device token in Android Keystore.
 *  HTTP rides the WireGuard-encrypted tailnet, and never binds to LAN/public.
 */
export function createRitsuAndroidGateway({
  host,port=19646,clientBearer,coordinator,voiceReturn=null,
  allowLoopbackForTests=false,
}={}) {
  if(!tailnetIPv4(host) && !(allowLoopbackForTests && host==='127.0.0.1'))
    throw new Error('gateway_must_bind_specific_tailnet_ipv4');
  if(!Number.isInteger(port)||(!allowLoopbackForTests && port<1024)||port<0||port>65535)
    throw new Error('gateway_port_invalid');
  if(typeof clientBearer!=='string'||clientBearer.length<40)
    throw new Error('separate_device_capability_required');
  if(!coordinator||['submitUserTurn','readOneTurn','projectedFeed']
      .some(k=>typeof coordinator[k]!=='function'))
    throw new Error('home_center_coordinator_required');

  // The initial release only speaks verified main/control answers.
  // Replies staged in dialogue/worker lanes remain silent until Home Center
  // publishes them, and voice is never confused with phone playback proof.
  let voiceSequence=Promise.resolve();
  const voiceScheduled=new Set();
  function scheduleCanonicalVoice(turnId,text) {
    if(!voiceReturn||!ID.test(String(turnId||''))||
        typeof text!=='string'||!text.trim()||voiceScheduled.has(turnId))return;
    voiceScheduled.add(turnId);
    voiceSequence=voiceSequence.then(()=>
      voiceReturn.dispatchOnce({turnId,text})).catch(()=>{});
  }
  const server=http.createServer(async(req,res)=>{
    const token=/^Bearer (\S+)$/.exec(String(req.headers.authorization||''))?.[1]||'';
    if(!constantTimeEqual(token,clientBearer))
      return response(res,401,{ok:false,error:'unauthorized'});
    let url;
    try{url=new URL(req.url,'http://ritsu.local');}
    catch{return response(res,400,{ok:false,error:'invalid_path'});}
    if(url.pathname==='/v1/ritsu/health' && req.method==='GET')
      return response(res,200,{ok:true,service:'home-center-ritsu-gateway'});
    if(url.pathname==='/v1/ritsu/turn' && req.method==='POST') {
      try{
        if(!/^application\/json(?:;|$)/i.test(String(req.headers['content-type']||'')))
          return response(res,415,{ok:false,error:'json_required'});
        const body=await readRequestBody(req);
        if(!body||typeof body!=='object'||!ID.test(body.turnId)||
            typeof body.prompt!=='string'||!body.prompt.trim()||
            body.prompt.length>5000 || body.channel && body.channel!=='control')
          return response(res,400,{ok:false,error:'invalid_control_turn'});
        const row=await coordinator.submitUserTurn({
          turnId:body.turnId,channel:'control',prompt:body.prompt
        });
        // 202 confirms durable HOME CENTER intake, NOT ChatGPT acceptance.
        return response(res,202,{ok:true,receipt:safeRow(row),
          boundary:'home_center_only_not_browser_delivery'});
      } catch(e) {
        return response(res,/collision/.test(e.message)?409:503,
          {ok:false,error:/collision/.test(e.message)
            ? 'turn_id_collision':'home_center_intake_failed'});
      }
    }
    if(url.pathname==='/v1/ritsu/turn' && req.method==='GET') {
      const turnId=url.searchParams.get('turnId');
      if(!ID.test(turnId||''))return response(res,400,{ok:false,error:'invalid_turn_id'});
      try {
        const row=await coordinator.readOneTurn(turnId);
        if(row.state==='completed'&&row.turn?.channel==='control')
          scheduleCanonicalVoice(turnId,row.result?.text);
        return response(res,200,{ok:true,receipt:safeRow(row)});
      }catch(e) {
        return response(res,/turn_not_found/.test(e.message)?404:503,
          {ok:false,error:/turn_not_found/.test(e.message)
            ? 'turn_not_found':'home_center_readback_failed'});
      }
    }
    if(url.pathname==='/v1/ritsu/feed' && req.method==='GET') {
      const after=Number(url.searchParams.get('after')||0);
      if(!Number.isSafeInteger(after)||after<0)
        return response(res,400,{ok:false,error:'cursor_invalid'});
      try{
        const all=await coordinator.projectedFeed();
        // Only main-owned published feed, never staged dialogue or workers.
        const events=all.filter(e=>Number(e.sequence)>after).slice(0,60);
        for(const event of events) {
          if(event.channel==='control'&&event.type==='chat_result')
            scheduleCanonicalVoice(event.turnId,event.text);
        }
        return response(res,200,{ok:true,events,
          nextCursor:events.length?events.at(-1).sequence:after});
      }catch{return response(res,503,{ok:false,error:'home_center_feed_unavailable'});}
    }
    return response(res,404,{ok:false,error:'route_not_found'});
  });
  return Object.freeze({
    start:()=>new Promise((resolve,reject)=>{
      server.once('error',reject);
      server.listen(port,host,()=>{server.removeListener('error',reject);resolve(server.address());});
    }),
    close:()=>new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve())),
    address:()=>server.address(),
  });
}
