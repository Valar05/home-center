#!/usr/bin/env node
// Explicit trusted Home Center host entrypoint, never invoked from the APK.
// One coordinator per configured campaign, no process-global singleton.
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {createRitsuVoiceReturn} from './ritsu-voice-return.mjs';
import {createCanonicalVoiceSender} from './ritsu-canonical-voice-sender.mjs';
import {createRitsuAndroidGateway} from './ritsu-android-gateway.mjs';
import {createRitsuHomeCenterCoordinator} from './ritsu-home-center-coordinator.mjs';
import {createLocalThroneTransport} from './ritsu-home-center-throne-transport.mjs';
import {createRitsuPlaywrightTransport} from '../tools/campaigns/ritsu-playwright/android-transport.mjs';
import {createFileCoordinatorStore} from './ritsu-coordinator-file-store.mjs';
function required(name) {
  const v=process.env[name];
  if(!v)throw new Error(name+'_required');
  return v;
}
async function main() {
  const token=(await readFile(required('HOME_CENTER_RITSU_PHONE_CAPABILITY_FILE'),'utf8')).trim();
  const coordinator=createRitsuHomeCenterCoordinator({
    namespace:required('HOME_CENTER_RITSU_NAMESPACE'),
    controlSessionId:required('HOME_CENTER_RITSU_CONTROL_SESSION'),
    dialogueSessionId:required('HOME_CENTER_RITSU_DIALOGUE_SESSION'),
    store:createFileCoordinatorStore({directory:required('HOME_CENTER_RITSU_STATE_DIR')}),
    transport:process.env.HOME_CENTER_RITSU_TRANSPORT==='playwright'
      ? createRitsuPlaywrightTransport({
          directory:path.join(required('HOME_CENTER_RITSU_STATE_DIR'),'playwright-jobs'),
          tabId:required('HOME_CENTER_RITSU_BOUND_TAB_ID'),
          boundUrl:required('HOME_CENTER_RITSU_BOUND_CONVERSATION_URL'),
        })
      : createLocalThroneTransport({
          capability:required('HOME_CENTER_CHROMIUM_THRONE_CAPABILITY'),
          baseUrl:process.env.HOME_CENTER_RITSU_RELAY_URL||
            'http://127.0.0.1:9235/v1/throne',
        }),
  });
  const voiceReturn=createRitsuVoiceReturn({
    directory:path.join(required('HOME_CENTER_RITSU_STATE_DIR'),'voice-return'),
    sender:createCanonicalVoiceSender({
      relayRoot:required('HOME_CENTER_RITSU_CANONICAL_RELAY_ROOT'),
    }),
  });
  const gateway=createRitsuAndroidGateway({
    host:required('HOME_CENTER_RITSU_TAILNET_IPV4'),
    port:Number(process.env.HOME_CENTER_RITSU_PHONE_PORT||19646),
    clientBearer:token,
    coordinator,
    voiceReturn,
  });
  const address=await gateway.start();
  // Receipt contains only listener address and process ID, never secret.
  process.stdout.write(JSON.stringify({ok:true,service:'ritsu-android-gateway',
    bind:address.address,port:address.port,pid:process.pid})+'\n');
  for(const event of ['SIGINT','SIGTERM'])process.on(event,async()=>{
    try{await gateway.close();}finally{process.exit(0);}
  });
}
main().catch(error=>{
  process.stderr.write(JSON.stringify({ok:false,
    error:String(error.message||'startup_failed').slice(0,120)})+'\n');
  process.exitCode=1;
});
