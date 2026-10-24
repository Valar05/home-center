// The smallest useful ChatGPT bridge: launch ONE Home Center-owned turn,
// then retrieve the verified assistant text under the SAME turn/session.
// Never confuse a queued command or browser tab with an answered chat.
// Does not create tabs, start workers, provision phone, or play audio.
const ID = /^[A-Za-z0-9_.:-]{8,100}$/;
const sleep = ms => new Promise(resolve => setTimeout(resolve,ms));
export function createInitiatedChat({
  coordinator, pause=sleep, now=()=>Date.now(),
}={}) {
  if(!coordinator || typeof coordinator.submitUserTurn!=='function' ||
      typeof coordinator.readOneTurn!=='function')
    throw new Error('authoritative_home_center_coordinator_required');
  if(typeof pause!=='function' || typeof now!=='function')
    throw new Error('clock_and_pause_required');
  async function retrieve({turnId,timeoutMs=135000,pollMs=2500}={}) {
    if(!ID.test(String(turnId||'')))throw new Error('stable_turn_id_required');
    if(!Number.isInteger(timeoutMs)||timeoutMs<1000||timeoutMs>180000 ||
       !Number.isInteger(pollMs)||pollMs<100||pollMs>10000)
      throw new Error('bounded_retrieval_timing_required');
    const started=now(), deadline=started+timeoutMs;
    let attempts=0,last;
    while(true) {
      // Only GET/read state. Never re-POST an unknown sent prompt.
      const row=await coordinator.readOneTurn(turnId);
      attempts++;
      if(!row || row.turn?.turnId!==turnId)
        throw new Error('home_center_result_identity_mismatch');
      if(row.state==='completed') {
        if(!['control','dialogue'].includes(row.turn.channel) ||
           row.result?.turnId!==turnId ||
           row.result?.sessionId!==row.turn.sessionId ||
           row.result?.channel!==row.turn.channel ||
           typeof row.result?.text!=='string' ||
           !row.result.text.trim() ||
           !Number.isInteger(row.result.tabId)||row.result.tabId<=0)
          throw new Error('completed_reply_lacks_chatgpt_identity');
        return Object.freeze({
          state:'retrieved',turnId,channel:row.turn.channel,
          sessionId:row.turn.sessionId,tabId:row.result.tabId,
          text:row.result.text,verified:true,pollCount:attempts,
          source:'home_center_verified_chromium_throne_chatgpt',
        });
      }
      if(['failed','unknown'].includes(row.state))
        return Object.freeze({state:row.state,turnId,verified:false,
          pollCount:attempts,text:null,reason:'no_verified_chatgpt_reply'});
      if(now()>=deadline)
        return Object.freeze({state:'pending',turnId,verified:false,
          pollCount:attempts,text:null,reason:'retrieval_deadline_no_repost'});
      if(row.state!==last)last=row.state;
      await pause(Math.min(pollMs,Math.max(1,deadline-now())));
    }
  }
  return Object.freeze({
    async initiateAndRetrieve({turnId,prompt,channel='control',...timing}={}) {
      if(!ID.test(String(turnId||'')) ||
         typeof prompt!=='string'||!prompt.trim()||prompt.length>5000||
         !['control','dialogue'].includes(channel))
        throw new Error('valid_single_chat_turn_required');
      const accepted=await coordinator.submitUserTurn({turnId,prompt,channel});
      if(accepted.turn?.turnId!==turnId ||
         accepted.turn.channel!==channel ||
         accepted.turn.prompt!==prompt)
        throw new Error('home_center_submission_identity_mismatch');
      // The returned value from submit is an intake receipt, not a reply.
      // A real result is returned only after verified relay readback.
      return retrieve({turnId,...timing});
    },
    retrieve,
  });
}
