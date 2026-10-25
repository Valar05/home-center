// Ritsu Control's deterministic, owner-local Playwright ChatGPT turn executor.
// Only called through Home Center Computer Hands with a fixed, reviewed entrypoint.
// The prompt is inert base64 input. It is NEVER evaluated as shell or JavaScript.
import {createHash} from 'node:crypto';
import {promises as fs} from 'node:fs';
import {homedir} from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
const args=new Map();
for(let i=2;i<process.argv.length;i+=2)args.set(process.argv[i],process.argv[i+1]??'');
const sha=s=>createHash('sha256').update(s,'utf8').digest('hex');
const ID=/^[A-Za-z0-9_.:-]{8,100}$/;
const TAB=/^[A-Za-z0-9_-]{4,80}$/;
const root=path.join(homedir(),'.ritsu-control','playwright-bridge');
const stateFile=path.join(root,'state.json');
const lockFile=path.join(root,'lock');
const streams=path.join(root,'streams');
function streamPath(turnId){if(!ID.test(turnId))throw Error('invalid_stream_turn');return path.join(streams,turnId+'.json');}
async function streamWrite(turnId,tabId,kind,text='',extra={}) {
  await fs.mkdir(streams,{recursive:true});
  const file=streamPath(turnId),tmp=file+'.'+process.pid+'.new';
  let previous=null;try{previous=JSON.parse(await fs.readFile(file,'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
  if(previous&&previous.tabId!==tabId)throw Error('stream_tab_collision');
  const version=(previous?.version||0)+1;
  const event={kind:'stream_snapshot',turnId,tabId,version,state:kind,text,
    sha256:sha(text),complete:kind==='complete',verified:kind==='complete',
    ...extra};
  await fs.writeFile(tmp,JSON.stringify(event),'utf8');
  await fs.rename(tmp,file);
  return event;
}
async function streamPeek(turnId,tabId){
  let value;try{value=JSON.parse(await fs.readFile(streamPath(turnId),'utf8'));}
  catch(e){if(e.code==='ENOENT')return output({kind:'stream_snapshot',turnId,tabId,version:0,state:'pending',text:'',sha256:sha(''),complete:false,verified:false});throw e;}
  if(value.tabId!==tabId||value.turnId!==turnId)throw Error('stream_identity_mismatch');
  output(value);
}
const safe=e=>String(e?.message||e||'unknown').slice(0,220);
const output=x=>console.log('RITSU_BROWSER_RECEIPT='+JSON.stringify(x));
function playwright(){
  const probe=[
    path.join(process.env.LOCALAPPDATA||homedir(),'RitsuControlBridge','package.json'),
    path.join(root,'package.json'),
    path.join(process.cwd(),'browser-worker','package.json'),
    path.join(process.cwd(),'package.json'),
    path.join(homedir(),'workspace','home-center','browser-worker','package.json'),
    path.join(homedir(),'Documents','GodotProjects','home-center','browser-worker','package.json'),
  ];
  for(const p of probe){
    try{const req=createRequire(p);return req('playwright')}catch{}
  }
  throw Error('playwright_not_installed_in_authorized_home_center_worker');
}
async function attach(pw){
  // Use only the approved, already-provisioned Chromium Throne profile.
  // Port 9234 is the protected relay, NOT a Chrome DevTools endpoint.
  const endpoints=[9236,9222,9223,9333].map(port=>'http://127.0.0.1:'+port);
  const tryAttach=async()=>{
    for(const url of endpoints){
      try{
        const res=await fetch(url+'/json/version',{signal:AbortSignal.timeout(1500)});
        if(!res.ok)continue;
        const version=await res.json();
        if(!/chrome|chromium/i.test(String(version.Browser||'')))continue;
        return await pw.chromium.connectOverCDP(url,{timeout:7000});
      }catch{}
    }
    return null;
  };
  const current=await tryAttach();
  if(current)return current;
  // Browser windows/processes are replaceable; account profile and turns are not.
  // Start only the existing Home Center launcher, without creating a new profile.
  const existing=path.join(homedir(),'AppData','Local','HomeCenter','ChromiumThrone');
  const launcher=path.join(existing,'launch-chromium-throne.cmd');
  const profile=path.join(existing,'profile');
  let launchText='';
  try{
    if(!(await fs.stat(profile)).isDirectory())throw Error('profile_missing');
    launchText=await fs.readFile(launcher,'utf8');
  }catch{throw Error('approved_chromium_throne_profile_unavailable');}
  if(!launchText.includes('--remote-debugging-port=9236') ||
     !launchText.includes('--remote-debugging-address=127.0.0.1') ||
     !launchText.includes('--user-data-dir=') ||
     !launchText.includes('ChromiumThrone'))
    throw Error('approved_browser_launcher_not_ready');
  const child=spawn('cmd.exe',['/d','/c',launcher],{
    cwd:existing,windowsHide:true,detached:true,stdio:'ignore'
  });
  child.unref();
  for(let attempt=0;attempt<24;attempt++){
    await new Promise(resolve=>setTimeout(resolve,850));
    const recovered=await tryAttach();
    if(recovered)return recovered;
  }
  throw Error('approved_chromium_cdp_session_unavailable_after_recovery');
}
async function load(){
  try {const value=JSON.parse(await fs.readFile(stateFile,'utf8'));
    if(value.schema!==1||typeof value.turns!=='object'||typeof value.tabs!=='object')throw Error('invalid_state');
    return value;
  }catch(e){if(e.code==='ENOENT')return {schema:1,turns:{},tabs:{}};throw e;}
}
async function save(state){
  const pending=stateFile+'.new-'+process.pid;
  await fs.writeFile(pending,JSON.stringify(state),'utf8');
  await fs.rename(pending,stateFile);
}
async function doctor(){
  const pw=playwright();const browser=await attach(pw);
  const contexts=browser.contexts(),pages=contexts.flatMap(c=>c.pages());
  const chat=pages.filter(p=>/^https:\/\/(chatgpt\.com|chat\.openai\.com)\//i.test(p.url()));
  const surfaces=[];
  for(const page of chat.slice(0,5)){
    const state=await page.evaluate(()=>{
      const qs=s=>document.querySelectorAll(s).length;
      return {promptId:qs('#prompt-textarea'),
        editable:qs('[contenteditable="true"]'),
        textbox:qs('[role="textbox"]'),textarea:qs('textarea'),
        login:qs('a[href*="/auth/login"],a[href*="/login"]'),
        challenge:qs('#challenge-form, iframe[src*="challenges.cloudflare.com"]'),
        userNodes:qs('[data-message-author-role="user"]'),
        assistantNodes:qs('[data-message-author-role="assistant"]'),
        conversationTurns:qs('[data-testid^="conversation-turn"]'),
        articles:qs('article'),
        stopButtons:Array.from(document.querySelectorAll('button')).filter(b=>
          /stop generating|stop response|stop streaming/i.test(b.getAttribute('aria-label')||'')).length,
        canaryUser:Array.from(document.querySelectorAll('[data-message-author-role="user"]')).some(e=>
          e.innerText.includes('RITSU_PW_BRIDGE_CANARY_20261024_OK')),
        canaryAssistant:Array.from(document.querySelectorAll('[data-message-author-role="assistant"]')).some(e=>
          e.innerText.includes('RITSU_PW_BRIDGE_CANARY_20261024_OK')),
        canaryAnywhere:document.body?.innerText?.includes('RITSU_PW_BRIDGE_CANARY_20261024_OK')||false,
        mainTextLength:document.querySelector('main')?.innerText?.length||0,
        editorMeta:Array.from(document.querySelectorAll('[contenteditable="true"]')).slice(0,3).map(e=>({
          tag:e.tagName,id:e.id,role:e.getAttribute('role'),
          dataTestId:e.getAttribute('data-testid'),
          placeholder:e.getAttribute('data-placeholder'),
          charCount:(e.innerText||'').length
        })),
        sendControls:Array.from(document.querySelectorAll('button')).map(b=>({
          aria:b.getAttribute('aria-label'),testId:b.getAttribute('data-testid'),
          disabled:b.disabled
        })).filter(b=>/send|submit|stop/i.test((b.aria||'')+' '+(b.testId||''))).slice(0,12)
      };
    }).catch(()=>({error:'page_evaluation_unavailable'}));
    const canary=state.canaryAnywhere
       ? await page.locator('main').innerText().then(t=>t.slice(0,800)).catch(()=>null)
       : null;
    surfaces.push({path:new URL(page.url()).pathname.slice(0,90),...state,
      canaryMainPreview:canary});
  }
  output({kind:'doctor',playwright:true,cdp:true,contextCount:contexts.length,
    authorizedChatgptTabs:chat.length,surfaces,signedIn:'unverified',executed:false});
  await browser.close();
}
// This installed ChatGPT website renders natural-language conversation labels
// ("You said:" and "ChatGPT said:") rather than legacy data-message-author-role.
// Read only a main-scoped response following the user's exact last prompt.
// Require the standard completed-response footer and stable visible text.
async function renderedReply(page, prompt, timeoutMs=74000, onProgress=async()=>{}){
  const deadline=Date.now()+timeoutMs;
  let previous='',stable=0;
  const anchor='You said:\n'+prompt+'\nChatGPT said:\n';
  const footer='\nChatGPT can make mistakes. Check important info.';
  while(Date.now()<deadline){
    const mainText=await page.locator('main').innerText().catch(()=>null);
    const i=mainText?.lastIndexOf('You said:\n')??-1;
    let value='';
    if(i>=0&&mainText.slice(i).startsWith(anchor)){
      const after=mainText.slice(i+anchor.length);
      const end=after.indexOf(footer);
      value=(end>=0?after.slice(0,end):after).trim();
      if(value.length>5000)throw Error('stream_reply_exceeds_limit');
    }
    // Publish a monotonic growing snapshot before final completion. Never
    // wait for the standard footer or stop button to show the first words.
    if(value && value!==previous)await onProgress(value);
    const busy=await page.getByRole('button',{name:/stop generating|stop streaming|stop response/i}).count().catch(()=>0);
    if(value && value===previous && busy===0)stable++;else stable=0;
    previous=value;
    if(stable>=3)return value;
    await page.waitForTimeout(350);
  }
  throw Error('rendered_assistant_answer_unverified_no_repost');
}
async function locateSentPage(browser,prompt,knownUrl) {
  const contexts=browser.contexts();
  const pages=contexts.flatMap(c=>c.pages());
  // Rehydrate the saved conversation URL after Chrome/window restarts.
  // Never re-submit a prompt merely because the page was closed.
  if(knownUrl && /^https:\/\/chatgpt\.com\/c\/[a-zA-Z0-9-]+$/.test(knownUrl) &&
     !pages.some(p=>p.url()===knownUrl)) {
    if(!contexts.length)throw Error('browser_context_unavailable');
    const restored=await contexts[0].newPage();
    await restored.goto(knownUrl,{waitUntil:'domcontentloaded',timeout:35000});
    pages.push(restored);
  }
  const found=[];
  for(const page of pages){
    if(!/^https:\/\/chatgpt\.com\/c\//.test(page.url()))continue;
    const main=await page.locator('main').innerText().catch(()=>null);
    if(main && main.includes('You said:\n'+prompt+'\nChatGPT said:\n'))
      found.push(page);
  }
  if(found.length!==1)throw Error('answered_turn_page_not_unique_no_repost');
  return found[0];
}
function makeReply(turnId,tabId,page,text){
  if(!text||typeof text!=='string'||text.length>5000)
    throw Error('rendered_reply_empty_or_oversized');
  return {kind:'chatgpt_reply',turnId,tabId,verified:true,
    source:'playwright-rendered-chatgpt-reply',text,sha256:sha(text),
    url:page.url(),completedAt:new Date().toISOString()};
}
async function main(){
  await fs.mkdir(root,{recursive:true});
  if(args.has('--doctor'))return doctor();
  if(args.has('--peek')) {
    const turnId=args.get('--turn'),tabId=args.get('--tab');
    if(!ID.test(turnId||'')||!TAB.test(tabId||''))throw Error('peek_identity_invalid');
    return streamPeek(turnId,tabId);
  }
  if(args.has('--launch')) {
    const turnId=args.get('--turn'),tabId=args.get('--tab'),encoded=args.get('--prompt-b64');
    if(!ID.test(turnId||'')||!TAB.test(tabId||'')||
       !encoded||encoded.length>30000||!/^[a-zA-Z0-9+/]+={0,2}$/.test(encoded))
      throw Error('launch_identity_invalid');
    const child=spawn(process.execPath,[process.argv[1],'--turn',turnId,
      '--tab',tabId,'--prompt-b64',encoded],{detached:true,windowsHide:true,
      stdio:'ignore',cwd:process.cwd()});
    child.unref();
    output({kind:'stream_launch',turnId,tabId,pid:child.pid,verified:false});
    return;
  }
  const turnId=args.get('--turn'),tabId=args.get('--tab'),encoded=args.get('--prompt-b64');
  if(!ID.test(turnId||'')||!TAB.test(tabId||'')||!encoded||
     encoded.length>30000||!/^[a-zA-Z0-9+/]+={0,2}$/.test(encoded))
    throw Error('invalid_turn_tab_or_encoded_prompt');
  const buffer=Buffer.from(encoded,'base64');
  const prompt=buffer.toString('utf8');
  if(!prompt.trim()||prompt.length>5000||
     Buffer.compare(buffer,Buffer.from(prompt,'utf8'))!==0)
    throw Error('invalid_utf8_prompt');
  // Refuse concurrent browser use. The queue remains serialized in Computer Hands.
  // A machine crash cannot leave a permanent dead-process lock.
  // Old owner PID is checked; never override a live worker.
  let lock;
  try {
    lock=await fs.open(lockFile,'wx');
  } catch(e) {
    if(e.code!=='EEXIST')throw e;
    const previous=(await fs.readFile(lockFile,'utf8')).trim().split(':')[0];
    const previousPid=Number(previous);
    if(!Number.isInteger(previousPid)||previousPid<=0)
      throw Error('ambiguous_lock_owner_no_duplicate_send');
    let alive=true;
    try{process.kill(previousPid,0)}catch(error){
      if(error.code==='ESRCH')alive=false;
      else throw Error('cannot_verify_previous_lock_owner');
    }
    if(alive)throw Error('another_turn_running_no_duplicate_send');
    const stale=lockFile+'.stale-'+Date.now();
    await fs.rename(lockFile,stale);
    lock=await fs.open(lockFile,'wx');
  }
  await lock.writeFile(process.pid+':'+new Date().toISOString());
  try{
    const state=await load(),prior=state.turns[turnId],promptSha256=sha(prompt);
    if(prior){
      if(prior.promptSha256!==promptSha256||prior.tabId!==tabId)
        throw Error('turn_id_collision');
      if(prior.state==='complete'){
        await streamWrite(turnId,tabId,'complete',prior.receipt.text,
          {url:prior.receipt.url,source:'playwright-rendered-chatgpt-reply'});
        output(prior.receipt);return;
      }
      if(args.has('--recover-reply')){
        const pw=playwright(),browser=await attach(pw);
        try{
          const page=await locateSentPage(browser,prompt,state.tabs[tabId]?.url);
          const answer=await renderedReply(page,prompt,60000,
            text=>streamWrite(turnId,tabId,'streaming',text));
          const receipt=makeReply(turnId,tabId,page,answer);
          state.turns[turnId]={state:'complete',tabId,promptSha256,receipt};
          state.tabs[tabId]={url:page.url()};
          await save(state);
          await streamWrite(turnId,tabId,'complete',answer,
            {url:page.url(),source:'playwright-rendered-chatgpt-reply'});
          output(receipt);return;
        }finally{await browser.close();}
      }
      // Only a specifically requested recovery may advance a still-visible,
      // exact local draft. Never resend a prompt that might already be posted.
      if(!args.has('--resume-draft'))throw Error('dispatch_uncertain_do_not_repost');
      const pw=playwright(),browser=await attach(pw);
      try {
        const pages=browser.contexts().flatMap(c=>c.pages());
        const matches=[];
        for(const page of pages){
          if(page.url()!=='https://chatgpt.com/')continue;
          const editor=page.locator('div[contenteditable="true"][role="textbox"]').first();
          if(await editor.count() && (await editor.innerText()).trim()===prompt)
            matches.push(page);
        }
        if(matches.length!==1)throw Error('draft_identity_not_uniquely_verified_no_repost');
        const page=matches[0],send=page.getByRole('button',{name:'Send',exact:true});
        if(!(await send.isVisible()))throw Error('verified_draft_send_button_missing');
        await send.click({timeout:10000});
        await page.waitForURL(/\/c\//,{timeout:35000});
        state.tabs[tabId]={url:page.url()};
        prior.state='browser_dispatched_reply_pending';
        await save(state);
        output({kind:'dispatch_receipt',turnId,tabId,
          state:'browser_dispatched_reply_pending',verified:false,
          source:'playwright-rendered-chatgpt-submit',url:page.url()});
        return;
      }finally{await browser.close();}
    }
    const pw=playwright();
    const browser=await attach(pw);
    try{
      const contexts=browser.contexts();
      if(!contexts.length)throw Error('chrome_context_unavailable');
      let page=null;const known=state.tabs[tabId];
      if(known?.url && known.url.startsWith('https://chatgpt.com/')){
        page=contexts.flatMap(c=>c.pages()).find(p=>p.url()===known.url)||null;
      }
      if(!page){
        const chatContext=contexts.find(c=>c.pages().some(p=>/^https:\/\/chatgpt\.com\//.test(p.url())))||contexts[0];
        page=await chatContext.newPage();
        // A missing window is not a missing conversation. Reopen its exact URL.
        const savedUrl=known?.url;
        const restore=typeof savedUrl==='string' &&
          /^https:\/\/chatgpt\.com\/c\/[a-zA-Z0-9-]+$/.test(savedUrl);
        await page.goto(restore?savedUrl:'https://chatgpt.com/',
          {waitUntil:'domcontentloaded',timeout:35000});
      }
      // ChatGPT's composer varies by currently deployed web UI revision.
      // Select only an actual visible editable composer; never a login box.
      const selectors=['#prompt-textarea','[data-testid="prompt-textarea"]',
        'div[contenteditable="true"][role="textbox"]',
        '[contenteditable="true"][data-placeholder]',
        'textarea[placeholder*="Ask"]'];
      let input=null;
      for(const selector of selectors) {
        const found=page.locator(selector).first();
        if(await found.isVisible().catch(()=>false)){input=found;break;}
      }
      if(!input) {
        await page.waitForTimeout(1500);
        for(const selector of selectors) {
          const found=page.locator(selector).first();
          if(await found.isVisible().catch(()=>false)){input=found;break;}
        }
      }
      if(!input)throw Error('chatgpt_composer_not_available_requires_owner_session');
      // Presence of a previous assistant node is not proof a new turn completed.
      // Durable marker precedes dispatch. Never silently re-send on uncertain state.
      state.turns[turnId]={state:'sending',tabId,promptSha256,startedAt:new Date().toISOString()};
      state.tabs[tabId]={url:page.url()};
      await save(state);
      await input.fill(prompt);
      const send=page.getByRole('button',{name:'Send',exact:true});
      if(!(await send.isVisible()))throw Error('send_button_not_visible_no_submission');
      await send.click({timeout:10000});
      // Navigation is real browser submission proof, not proof of an answer.
      await page.waitForURL(/\/c\//,{timeout:35000});
      state.tabs[tabId]={url:page.url()};
      await save(state);
      const answer=await renderedReply(page,prompt,70000,
        text=>streamWrite(turnId,tabId,'streaming',text));
      const receipt=makeReply(turnId,tabId,page,answer);
      state.turns[turnId]={state:'complete',tabId,promptSha256,receipt};
      state.tabs[tabId]={url:page.url()};
      await save(state);
      await streamWrite(turnId,tabId,'complete',answer,
        {url:page.url(),source:'playwright-rendered-chatgpt-reply'});
      output(receipt);
    }finally{await browser.close();}
  }finally{await lock.close();await fs.unlink(lockFile).catch(()=>{});}
}
main().catch(async error=>{
  const turnId=args.get('--turn'),tabId=args.get('--tab');
  if(!args.has('--peek')&&!args.has('--launch')&&ID.test(turnId||'')&&TAB.test(tabId||'')){
    try{await streamWrite(turnId,tabId,'error','',{code:safe(error)});}catch{}
  }
  output({kind:'error',verified:false,code:safe(error),executed:false});
  process.exitCode=1;
});
