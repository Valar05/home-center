// Ritsu v1.3.3 server insertion; loaded into existing authenticated server.mjs.
// Uses only existing Node/Playwright and its signed-in Chromium profile.
const browserRecoveryJobs=new Map();
async function recoverOriginalTurn(turnId, tabId, promptSha256){
  const row=turns.get(turnId);
  if(!row)return {ok:true,state:'no_server_receipt'};
  if(row.tabId!==tabId||row.hash!==promptSha256)throw Error('recovery_identity_collision');
  if(row.state==='complete')return {ok:true,state:'already_complete'};
  if(row.state!=='uncertain')return {ok:true,state:'still_processing',reason:'existing_browser_work_not_interrupted'};
  if(busy)return {ok:true,state:'still_processing',reason:'browser_worker_active'};
  if(browserRecoveryJobs.has(turnId))return browserRecoveryJobs.get(turnId);
  const task=(async()=>{
    const helper=path.join(path.dirname(BRIDGE),'ritsu_browser_recover_v133.mjs');
    let storedUrl='';
    try{
      const data=JSON.parse(await fs.readFile(path.join(os.homedir(),'.ritsu-control','playwright-bridge','state.json'),'utf8'));
      const previous=data.turns?.[turnId];
      if(previous&&(previous.tabId!==tabId||previous.promptSha256!==promptSha256))
        throw Error('bridge_stored_turn_collision');
      const url=data.tabs?.[tabId]?.url;
      if(typeof url==='string'&&/^https:\/\/chatgpt\.com\/c\/[a-zA-Z0-9-]+$/.test(url))storedUrl=url;
    }catch(e){if(e.code!=='ENOENT')return {ok:true,state:'uncertain',reason:'browser_state_unavailable_or_conflicted'};}
    const proc=spawn(process.execPath,[helper,promptSha256,tabId,storedUrl],{
      cwd:path.dirname(BRIDGE),windowsHide:true,stdio:['ignore','pipe','pipe'],env:{...process.env,RITSU_RECOVERY_READONLY:'1'}});
    let out='',err='';proc.stdout.on('data',b=>{out=(out+b.toString()).slice(-12000);});
    proc.stderr.on('data',b=>{err=(err+b.toString()).slice(-300);});
    const timeout=setTimeout(()=>proc.kill('SIGTERM'),40000);timeout.unref?.();
    const code=await new Promise(resolve=>{proc.on('error',()=>resolve(-1));proc.on('close',resolve);});clearTimeout(timeout);
    const line=out.split('\n').find(v=>v.startsWith('RITSU_RECOVERY_RESULT='));
    if(code!==0||!line)return {ok:true,state:'uncertain',reason:'read_only_browser_reply_not_verified'};
    let result;try{result=JSON.parse(line.slice('RITSU_RECOVERY_RESULT='.length));}
    catch{return {ok:true,state:'uncertain',reason:'invalid_recovery_receipt'};}
    if(!result.ok||!result.verified||result.source!=='playwright-rendered-chatgpt-reply'||
      typeof result.text!=='string'||!result.text.trim()||result.text.length>5000||
      hash(result.text)!==result.sha256||
      !/^https:\/\/chatgpt\.com\/c\/[A-Za-z0-9-]+$/.test(result.url||''))
      return {ok:true,state:'uncertain',reason:'recovery_source_not_cryptographically_verified'};
    // Check again immediately before the append. Never replace a real reply.
    if(turns.get(turnId)?.state==='complete')return {ok:true,state:'already_complete'};
    const prior=history.filter(e=>e.turnId===turnId).reduce((m,e)=>Math.max(m,e.revision||0),0);
    await append({type:'complete',turnId,tabId,revision:prior+1,text:result.text,
      sha256:hash(result.text),verified:true,url:result.url,source:'read-only-browser-recovery'});
    return {ok:true,state:'recovered',verified:true};
  })();
  browserRecoveryJobs.set(turnId,task);
  try{return await task;}finally{browserRecoveryJobs.delete(turnId);}
}
