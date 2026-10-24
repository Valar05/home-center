// Ritsu Control's deterministic, owner-local Playwright ChatGPT turn executor.
// Only called through Home Center Computer Hands with a fixed, reviewed entrypoint.
// The prompt is inert base64 input. It is NEVER evaluated as shell or JavaScript.
import {createHash} from 'node:crypto';
import {promises as fs} from 'node:fs';
import {homedir} from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
const args=new Map();
for(let i=2;i<process.argv.length;i+=2)args.set(process.argv[i],process.argv[i+1]??'');
const sha=s=>createHash('sha256').update(s,'utf8').digest('hex');
const ID=/^[A-Za-z0-9_.:-]{8,100}$/;
const TAB=/^[A-Za-z0-9_-]{4,80}$/;
const root=path.join(homedir(),'.ritsu-control','playwright-bridge');
const stateFile=path.join(root,'state.json');
const lockFile=path.join(root,'lock');
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
  // THECAULDRON's approved Chromium Throne Chrome CDP port was verified
  // against a live Chrome PID + listening 127.0.0.1 socket on 2026-10-24.
  const endpoints=[9236,9222,9223,9333].map(port=>'http://127.0.0.1:'+port);
  for(const url of endpoints){
    try{
      const res=await fetch(url+'/json/version',{signal:AbortSignal.timeout(1500)});
      if(!res.ok)continue;
      const version=await res.json();
      if(!String(version.Browser||'').toLowerCase().includes('chrome') &&
         !String(version.Browser||'').toLowerCase().includes('chromium'))continue;
      return await pw.chromium.connectOverCDP(url,{timeout:7000});
    }catch{}
  }
  throw Error('approved_chromium_cdp_session_unavailable');
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
    surfaces.push({path:new URL(page.url()).pathname.slice(0,90),...state});
  }
  output({kind:'doctor',playwright:true,cdp:true,contextCount:contexts.length,
    authorizedChatgptTabs:chat.length,surfaces,signedIn:'unverified',executed:false});
  await browser.close();
}
async function main(){
  await fs.mkdir(root,{recursive:true});
  if(args.has('--doctor'))return doctor();
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
  let lock;
  try{lock=await fs.open(lockFile,'wx');await lock.writeFile(String(process.pid));}
  catch(e){if(e.code==='EEXIST')throw Error('another_turn_running_no_duplicate_send');throw e;}
  try{
    const state=await load(),prior=state.turns[turnId],promptSha256=sha(prompt);
    if(prior){
      if(prior.promptSha256!==promptSha256||prior.tabId!==tabId)
        throw Error('turn_id_collision');
      if(prior.state==='complete'){output(prior.receipt);return;}
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
        await page.goto('https://chatgpt.com/',{waitUntil:'domcontentloaded',timeout:35000});
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
      const before=await page.locator('[data-message-author-role="assistant"]').count();
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
      const answers=page.locator('[data-message-author-role="assistant"]');
      await page.waitForFunction(
        n=>document.querySelectorAll('[data-message-author-role="assistant"]').length>n,
        before,{timeout:45000});
      const latest=answers.last();
      let last='',stable=0,finished=false;
      const deadline=Date.now()+150000;
      while(Date.now()<deadline){
        await page.waitForTimeout(900);
        const text=(await latest.innerText()).trim();
        const busy=await page.getByRole('button',{name:/stop generating|stop streaming|stop response/i}).count();
        if(text&&text===last&&!busy)stable++;else stable=0;
        last=text;
        if(stable>=3){finished=true;break;}
      }
      if(!finished||!last)throw Error('chatgpt_reply_not_stably_observed');
      const receipt={kind:'chatgpt_reply',turnId,tabId,verified:true,
        source:'playwright-rendered-chatgpt-reply',text:last,sha256:sha(last),
        url:page.url(),completedAt:new Date().toISOString()};
      state.turns[turnId]={state:'complete',tabId,promptSha256,receipt};
      state.tabs[tabId]={url:page.url()};
      await save(state);
      output(receipt);
    }finally{await browser.close();}
  }finally{await lock.close();await fs.unlink(lockFile).catch(()=>{});}
}
main().catch(error=>{
  output({kind:'error',verified:false,code:safe(error),executed:false});
  process.exitCode=1;
});
