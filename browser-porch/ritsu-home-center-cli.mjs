#!/usr/bin/env node
// Trusted Home Center / THECAULDRON local executor entrypoint.
// JSON request on stdin, one operation per process. No HTTP server,
// no APK secret, no direct phone->Throne link, no singleton process state.
// Input is intentionally NOT command-line arguments (avoid prompt history).
import {createRitsuHomeCenterCoordinator} from './ritsu-home-center-coordinator.mjs';
import {createLocalThroneTransport} from './ritsu-home-center-throne-transport.mjs';
import {createFileCoordinatorStore} from './ritsu-coordinator-file-store.mjs';

function required(name) {
  const value=process.env[name];
  if(!value)throw new Error(name+'_required');
  return value;
}
async function readRequest() {
  let input='';
  for await (const chunk of process.stdin) {
    input+=chunk;
    if(input.length>16_384)throw new Error('request_too_large');
  }
  const parsed=JSON.parse(input);
  if(!parsed || typeof parsed!=='object' || Array.isArray(parsed))
    throw new Error('request_object_required');
  return parsed;
}

async function main() {
  const request=await readRequest();
  const coordinator=createRitsuHomeCenterCoordinator({
    namespace:required('HOME_CENTER_RITSU_NAMESPACE'),
    controlSessionId:required('HOME_CENTER_RITSU_CONTROL_SESSION'),
    dialogueSessionId:required('HOME_CENTER_RITSU_DIALOGUE_SESSION'),
    store:createFileCoordinatorStore({
      directory:required('HOME_CENTER_RITSU_STATE_DIR'),
    }),
    transport:createLocalThroneTransport({
      capability:required('HOME_CENTER_CHROMIUM_THRONE_CAPABILITY'),
      baseUrl:process.env.HOME_CENTER_RITSU_RELAY_URL ||
        'http://127.0.0.1:9234/v1/throne',
    }),
  });
  let result;
  switch(request.operation) {
    case 'submit':
      result=await coordinator.submitUserTurn({
        turnId:request.turnId,
        channel:request.channel || 'dialogue',
        prompt:request.prompt,
      });
      break;
    case 'poll':
      result=await coordinator.readOneTurn(request.turnId);
      break;
    case 'state':
      result=await coordinator.status();
      break;
    case 'feed':
      result=await coordinator.projectedFeed();
      break;
    case 'publish':
      // This operation is reserved for the authenticated Home Center
      // CONTROL-thread executor, not Android input or worker output.
      result=await coordinator.mainThreadPublish({
        controlTurnId:request.controlTurnId,
        turnIds:request.turnIds || [],
        resultIds:request.resultIds || [],
      });
      break;
    default:throw new Error('unknown_home_center_operation');
  }
  process.stdout.write(JSON.stringify({ok:true,result})+'\n');
}
main().catch(error=>{
  // Never echo credentials, remote headers, or untrusted supplied prompt.
  process.stderr.write(JSON.stringify({
    ok:false,error:String(error.message || 'operation_failed').slice(0,140),
  })+'\n');
  process.exitCode=1;
});
