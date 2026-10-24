#!/usr/bin/env node
// Home Center Playwright response-readback campaign. Existing explicitly bound
// Chrome-for-Testing tab only; no new browser/tab, screenshots or response network parsing.
import {readFile,writeFile,appendFile,open,mkdir,rename} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {randomBytes,randomUUID} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateConfig,canaryPrompt,evidence,publicDiagnostic} from './capture-policy.mjs';

const current=fileURLToPath(import.meta.url);
const checkout=path.resolve(path.dirname(current),'../../..');
const stateDir=path.join(process.env.LOCALAPPDATA||path.join(checkout,'.private'),
  'HomeCenter','RitsuPlaywrightProbe');
const allowedModes=new Set(['Plan','Inspect','Apply','Status','Receipts','Stop']);
const entries=process.argv.slice(2),args={};
for(let i=0;i<entries.length;i+=2){
  if(!entries[i]?.startsWith('--')||!entries[i+1])throw Error('named_pairs_required');
  const key=entries[i].slice(2);
  if(Object.hasOwn(args,key))throw Error('duplicate_argument');
  args[key]=entries[i+1];
}
const mode=args.mode||'Plan';
const now=()=>new Date().toISOString();
const sleep=n=>new Promise(r=>setTimeout(r,n));

async function atomic(file,data){
  await mkdir(path.dirname(file),{recursive:true});
  const temp=file+'.'+randomUUID()+'.tmp';
  await writeFile(temp,JSON.stringify(data),{mode:0o600});
  await rename(temp,file);
}
async function readJSON(file){
  try{return JSON.parse(await readFile(path.join(stateDir,file),'utf8'))}
  catch(err){if(err.code==='ENOENT')return null;throw err}
}
async function receipt(data){
  const row={...data,at:now()};
  await mkdir(stateDir,{recursive:true});
  await appendFile(path.join(stateDir,'history.jsonl'),JSON.stringify(row)+'\n');
  await atomic(path.join(stateDir,'latest.json'),row);
  return row;
}
function pinned(){
  const actual=execFileSync('git',['rev-parse','HEAD'],{cwd:checkout,encoding:'utf8'}).trim();
  if(actual!==args.revision)throw Error('pinned_git_revision_mismatch');
  if(execFileSync('git',['status','--porcelain'],{cwd:checkout,encoding:'utf8'}).trim())
    throw Error('dirty_or_unreviewed_checkout');
}
async function isStopped(){return existsSync(path.join(stateDir,'stop.json'))}
async function ownedPage(){
  const {chromium}=await import('playwright-core');
  const response=await fetch('http://127.0.0.1:9236/json/list',
    {signal:AbortSignal.timeout(8000)});
  if(!response.ok)throw Error('authorized_cdp_browser_offline');
  const targets=await response.json();
  const tabs=targets.filter(t=>t.id===args.tabId&&t.type==='page'&&
    t.url===args.boundUrl);
  if(tabs.length!==1)throw Error('bound_tab_missing_or_mismatched');
  const browser=await chromium.connectOverCDP('http://127.0.0.1:9236',
    {timeout:12000,noDefaults:true});
  const candidates=browser.contexts().flatMap(c=>c.pages())
    .filter(p=>p.url()===args.boundUrl);
  for(const page of candidates){
    const cdp=await page.context().newCDPSession(page);
    let id;
    try{id=(await cdp.send('Target.getTargetInfo')).targetInfo?.targetId}
    finally{await cdp.detach().catch(()=>{})}
    if(id!==args.tabId)continue;
    return {browser,page};
  }
  await browser.close();
  throw Error('playwright_did_not_bind_exact_target');
}
async function currentMetadata(page){
  const assistant=page.locator('[data-message-author-role="assistant"]');
  const users=page.locator('[data-message-author-role="user"]');
  const composer=page.locator('[contenteditable="true"][data-composer-markdown][role="textbox"]');
  const stops=page.locator(
    'button[data-testid="stop-button"],button[aria-label="Stop generating"],'+
    'button[aria-label="Stop"],button[aria-label="Stop response"]');
  const stopVisible=async()=>{
    const count=await stops.count();
    for(let i=0;i<count;i++)if(await stops.nth(i).isVisible())return true;
    return false;
  };
  return {assistant,users,composer,stopVisible,
    assistants:await assistant.count(),usersBefore:await users.count(),
    composerCount:await composer.count(),stopRunning:await stopVisible()};
}
async function inspect(){
  const c=validateConfig(args);pinned();
  const {browser,page}=await ownedPage();
  try{
    const meta=await currentMetadata(page);
    return {schema:1,state:'inspect',revision:c.revision,jobId:c.jobId,
      tabId:c.tabId,boundUrl:c.boundUrl,
      assistantCount:meta.assistants,userCount:meta.usersBefore,
      composerPresent:meta.composerCount===1,
      composerVisible:meta.composerCount===1&&await meta.composer.isVisible(),
      composerEmpty:meta.composerCount===1&&
        (await meta.composer.innerText()).trim()==='',
      generating:meta.stopRunning,
      playwrightAttached:true,createdBrowser:false,createdTab:false,
      replyTextRead:false,
      structuralSelectors:Object.fromEntries(await Promise.all([
        '[data-message-author-role]', '[data-testid="conversation-turn"]',
        '[data-testid*="conversation"]','[data-testid*="message"]',
        '.markdown','article','main',
        'button[data-testid="send-button"]','button[aria-label="Send"]',
        'button[data-testid="stop-button"]'
      ].map(async sel=>[sel,await page.locator(sel).count()]))),
      mainTextCharacters:await page.locator('main').first().count()===1?
        (await page.locator('main').first().innerText()).length:0,
      mainHasCanaryPrefix:await page.locator('main').first().count()===1?
        (await page.locator('main').first().innerText()).includes('RITSU_PW_'):false,
      composerTextCharacters:meta.composerCount===1?
        (await meta.composer.innerText()).length:0,
      canaryNodeChains:await page.evaluate(()=>{
        const root=document.querySelector('main');
        if(!root)return [];
        const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
        const out=[];
        while(walker.nextNode()&&out.length<8){
          const n=walker.currentNode;
          if(!(n.textContent||'').includes('RITSU_PW_'))continue;
          let p=n.parentElement;const chain=[];
          for(let i=0;i<9&&p;i++,p=p.parentElement){
            chain.push({
              tag:p.tagName.toLowerCase(),
              cls:typeof p.className==='string'?p.className.slice(0,110):'',
              testid:(p.getAttribute('data-testid')||'').slice(0,100),
              role:(p.getAttribute('role')||'').slice(0,50),
              aria:(p.getAttribute('aria-label')||'').slice(0,60),
              length:(p.innerText||'').length,
              siblings:p.parentElement?.children?.length||0
            });
          }
          out.push({nodeTextLength:(n.textContent||'').length,chain});
        }
        return out;
      })
    };
  }finally{await browser.close().catch(()=>{})}
}
async function apply(){
  const c=validateConfig(args);
  pinned();
  if(await isStopped())throw Error('campaign_stop_latched');
  const old=await readJSON('latest.json');
  if(old&&!['blocked','retrieved'].includes(old.state))
    throw Error('previous_campaign_not_terminal');
  if(old?.jobId===c.jobId)throw Error('campaign_job_id_reused');
  // Reserve the ID and durable state before the one irreversible prompt.
  await mkdir(stateDir,{recursive:true});
  const fd=await open(path.join(stateDir,'job-'+c.jobId+'.json'),'wx',0o600);
  try{await fd.writeFile(JSON.stringify(c));await fd.sync()}finally{await fd.close()}
  await receipt({state:'running',...c,phase:'preflight'});
  const marker='RITSU_PW_'+randomBytes(10).toString('hex').toUpperCase();
  const prompt=canaryPrompt(marker);
  const {browser,page}=await ownedPage();
  try{
    const meta=await currentMetadata(page);
    if(meta.composerCount!==1||!(await meta.composer.isVisible())||
       (await meta.composer.innerText()).trim()!==''||meta.stopRunning)
      throw Error('composer_not_ready_for_one_canary');
    await receipt({state:'running',...c,phase:'bound_tab_verified',
      baseline:meta.assistants});
    // Playwright locators are used for input; all answer text comes exclusively
    // from a NEW assistant message in the exact previously bound conversation.
    await meta.composer.fill(prompt);
    if((await meta.composer.innerText()).trim()!==prompt)
      throw Error('composer_prompt_did_not_roundtrip');
    const send=page.locator('button[data-testid="send-button"],'+
      'button[aria-label="Send"],button[aria-label="Send message"]');
    if(await send.count()!==1||!(await send.isVisible())||
       !(await send.isEnabled()))
      throw Error('send_button_not_ready');
    // Never retry the click after an uncertain acknowledgment.
    await receipt({state:'running',...c,phase:'single_send_committed',
      baseline:meta.assistants});
    await send.click({timeout:8000});
    let stableText=null,stableSamples=0,lastPulse=0;
    const deadline=Date.now()+90000;
    while(Date.now()<deadline){
      if(await isStopped())throw Error('owner_stop_requested');
      if(page.isClosed()||page.url()!==c.boundUrl)
        throw Error('bound_page_changed_or_closed');
      const count=await meta.assistant.count();
      const userCount=await meta.users.count();
      let promptObserved=false;
      if(userCount===meta.usersBefore+1){
        promptObserved=(await meta.users.last().innerText()).includes(marker);
      }
      const stop=await meta.stopVisible();
      if(promptObserved&&count===meta.assistants+1){
        const target=meta.assistant.nth(meta.assistants);
        const markdown=target.locator('.markdown').first();
        const body=await markdown.count()===1?markdown:target;
        const text=await body.innerText();
        if(text.includes(marker)&&!stop){
          if(text===stableText)stableSamples++;
          else{stableText=text;stableSamples=1}
          if(stableSamples>=3){
            const proof=evidence({...c,marker,text,baseline:meta.assistants,
              assistantCount:count,stableSamples,stopVisible:stop,
              promptObserved,conversationUrl:page.url()});
            return await receipt({...proof,phase:'complete'});
          }
        }else{stableText=null;stableSamples=0}
      }
      if(Date.now()-lastPulse>5000){
        await receipt({state:'running',...c,phase:'waiting_for_visible_final',
          seenNewAssistant:count>meta.assistants,
          seenUniqueUserPrompt:promptObserved,stopVisible:stop});
        lastPulse=Date.now();
      }
      await sleep(450);
    }
    throw Error('visible_final_answer_not_verified_within_bound');
  }finally{await browser.close().catch(()=>{})}
}
async function main(){
  if(!allowedModes.has(mode))throw Error('unrecognized_mode');
  if(mode==='Plan'){console.log(JSON.stringify({state:'plan',
    entrypoint:'tools/campaigns/ritsu-playwright/runner.mjs',
    modes:[...allowedModes],source:'playwright_core_existing_Chrome_CDP',
    browserPort:9236,createdBrowser:false,createdTab:false,
    contract:'exact tab ID, URL, new assistant count, unique canary, stable completed text',
    launcher:'Home Center process.start on pinned isolated Windows Git checkout',
    responseLayer:'DOM only for authorized existing tab'}));return}
  if(mode==='Status'){console.log(JSON.stringify(await readJSON('latest.json')));return}
  if(mode==='Receipts'){
    try{console.log((await readFile(path.join(stateDir,'history.jsonl'),'utf8'))
      .split('\n').slice(-30).join('\n'))}
    catch(e){if(e.code==='ENOENT')console.log('NO_RECEIPTS');else throw e}return;
  }
  if(mode==='Stop'){
    await atomic(path.join(stateDir,'stop.json'),{requestedAt:now()});
    console.log(JSON.stringify(await receipt({state:'stop_requested'})));return;
  }
  try{
    if(mode==='Inspect')console.log(JSON.stringify(await inspect()));
    else console.log(JSON.stringify(await apply()));
  }catch(e){
    const err=publicDiagnostic(e);
    if(mode==='Apply')await receipt({state:'blocked',revision:args.revision,
      jobId:args.jobId,...err});
    console.log(JSON.stringify({state:'blocked',mode,...err}));
    process.exitCode=1;
  }
}
main().catch(e=>{console.error(JSON.stringify({state:'blocked',...publicDiagnostic(e)}));process.exitCode=1});
