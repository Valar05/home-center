#!/usr/bin/env node
// Home Center-only request/reply driver. JSON on stdin keeps chat private.
// One command to initiate and retrieve, or to resume read-only retrieval.
import {createRitsuHomeCenterCoordinator} from './ritsu-home-center-coordinator.mjs';
import {createLocalThroneTransport} from './ritsu-home-center-throne-transport.mjs';
import {createFileCoordinatorStore} from './ritsu-coordinator-file-store.mjs';
import {createInitiatedChat} from './ritsu-initiated-chat.mjs';

function required(name) {
  const value=process.env[name];
  if(!value)throw new Error(name+'_required');
  return value;
}
async function main() {
  let raw='';
  for await(const part of process.stdin) {
    raw+=part;
    if(raw.length>8192)throw new Error('chat_request_too_large');
  }
  const request=JSON.parse(raw);
  if(!request || typeof request!=='object' || Array.isArray(request))
    throw new Error('chat_request_object_required');
  const coordinator=createRitsuHomeCenterCoordinator({
    namespace:required('HOME_CENTER_RITSU_NAMESPACE'),
    controlSessionId:required('HOME_CENTER_RITSU_CONTROL_SESSION'),
    dialogueSessionId:required('HOME_CENTER_RITSU_DIALOGUE_SESSION'),
    store:createFileCoordinatorStore({directory:required('HOME_CENTER_RITSU_STATE_DIR')}),
    transport:createLocalThroneTransport({
      capability:required('HOME_CENTER_CHROMIUM_THRONE_CAPABILITY'),
      baseUrl:process.env.HOME_CENTER_RITSU_RELAY_URL||
        'http://127.0.0.1:9235/v1/throne',
    }),
  });
  const bridge=createInitiatedChat({coordinator});
  const {turnId}=request;
  let result;
  switch(request.operation) {
    case 'initiate_and_retrieve':
      result=await bridge.initiateAndRetrieve({
        turnId,prompt:request.prompt,channel:'control',
        timeoutMs:request.timeoutMs||135000,
      });break;
    case 'retrieve':
      result=await bridge.retrieve({turnId,timeoutMs:request.timeoutMs||135000});break;
    default:throw new Error('unsupported_chat_request');
  }
  // Only completed results contain assistant text.
  process.stdout.write(JSON.stringify({ok:true,...result})+'\n');
  if(result.state!=='retrieved')process.exitCode=2;
}
main().catch(e=>{
  // No secret/prompt/remote header reflection. Stable error contract.
  const allowed=/^(?:[a-z0-9_]+)$/.test(String(e.message||''))
    ? e.message : 'chat_bridge_error';
  process.stderr.write(JSON.stringify({ok:false,error:allowed.slice(0,120)})+'\n');
  process.exitCode=1;
});
