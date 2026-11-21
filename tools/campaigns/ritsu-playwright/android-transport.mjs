// Serialized Home Center -> Playwright transport for Ritsu Control.
// Phone never owns a browser capability. Failed/uncertain sends are NEVER replayed.
import {createHash,randomBytes,randomUUID} from 'node:crypto';
import {open,readFile,mkdir,rename} from 'node:fs/promises';
import path from 'node:path';
import {validateRitsuTurn} from '../../../browser-porch/ritsu-turn-protocol.mjs';
const ID=/^[A-Za-z0-9_.:-]{8,120}$/;
const TAB=/^[a-fA-F0-9]{32}$/;
const CHAT=/^https:\/\/chatgpt\.com\/c\/[a-f0-9-]{36}$/;
const sleep=ms=>new Promise(ok=>setTimeout(ok,ms));
const sha=s=>createHash('sha256').update(s).digest('hex');

async function writeAtomic(file,value){
  const temp=file+'.'+randomUUID()+'.tmp';
  const f=await open(temp,'wx',0o600);
  try{await f.writeFile(JSON.stringify(value));await f.sync()}finally{await f.close()}
  await rename(temp,file);
}
async function load(file){
  try{return JSON.parse(await readFile(file,'utf8'))}
  catch(e){if(e.code==='ENOENT')return null;throw e}
}

export async function playwrightReply({tabId,boundUrl,prompt,marker,timeoutMs=90000}){
  const {chromium}=await import('playwright-core');
  const check=await fetch('http://127.0.0.1:9236/json/list',
    {signal:AbortSignal.timeout(6000)});
  if(!check.ok)throw Error('bound_cdp_browser_unavailable');
  const tabs=await check.json();
  if(tabs.filter(t=>t.type==='page'&&t.id===tabId&&t.url===boundUrl).length!==1)
    throw Error('exact_bound_tab_unavailable');
  const browser=await chromium.connectOverCDP('http://127.0.0.1:9236',
    {timeout:10000,noDefaults:true});
  let dispatched=false,composerRef=null;
  try{
    let page=null;
    for(const candidate of browser.contexts().flatMap(c=>c.pages())){
      if(candidate.url()!==boundUrl)continue;
      const cdp=await candidate.context().newCDPSession(candidate);
      let id=null;
      try{id=(await cdp.send('Target.getTargetInfo')).targetInfo?.targetId}
      finally{await cdp.detach().catch(()=>{})}
      if(id===tabId){page=candidate;break}
    }
    if(!page)throw Error('playwright_target_mismatch');
    const composer=page.locator('[contenteditable="true"][data-composer-markdown][role="textbox"]');
    composerRef=composer;
    if(await composer.count()!==1||!(await composer.isVisible())||
       (await composer.innerText()).trim())throw Error('composer_busy');
    const user=page.locator('main [class*="bg-user-message"]');
    const assistants=page.locator('main [class*="MarkdownRoot-"]');
    const stop=page.locator('button[data-testid="stop-button"],button[aria-label="Stop generating"],button[aria-label="Stop"],button[aria-label="Stop response"]');
    async function stillGenerating(){
      for(let i=0;i<await stop.count();i++)if(await stop.nth(i).isVisible())return true;
      return false;
    }
    if(await stillGenerating())throw Error('prior_response_still_running');
    const wirePrompt=prompt+
      '\n\nFor this phone-to-ChatGPT delivery, end your final reply with this exact tracking code on its own last line: '+marker+
      '. Do not put the tracking code inside a code block.';
    await composer.fill(wirePrompt);
    const typed=(await composer.innerText()).trim();
    // ProseMirror may normalize double newlines in a contenteditable composer.
    // Accept only whitespace normalization, never altered words or marker.
    const normalize=v=>v.replace(/\s+/g,' ').trim();
    if(normalize(typed)!==normalize(wirePrompt))
      throw Error('composer_roundtrip_failed');
    const send=page.locator('button[data-testid="send-button"],button[aria-label="Send"],button[aria-label="Send message"]');
    if(await send.count()!==1||!(await send.isVisible())||!(await send.isEnabled()))
      throw Error('send_control_unavailable');
    // From this point the browser MAY have sent. Never retry on failure.
    dispatched=true;
    await send.click({timeout:7500});
    const deadline=Date.now()+timeoutMs;
    let last=null,samples=0,seenPrompt=false;
    while(Date.now()<deadline){
      if(page.isClosed()||page.url()!==boundUrl)throw Error('bound_page_changed');
      const inputMatch=user.filter({hasText:marker});
      if(await inputMatch.count()===1)seenPrompt=true;
      const answerMatch=assistants.filter({hasText:marker});
      if(seenPrompt&&await answerMatch.count()===1&&!await stillGenerating()){
        const raw=await answerMatch.first().innerText();
        const text=raw.replace(/\s+$/,'');
        const index=text.lastIndexOf(marker);
        const preceding=text.slice(0,index);
        const following=text.slice(index+marker.length);
        if(index>0&&!following.trim()&&
          /(?:^|\n)\s*$/.test(preceding.slice(preceding.lastIndexOf('\n')+1))===false){
          // Last line must contain only the marker; no prose contamination.
          // In particular, fail closed for marker in a prompt echo.
          samples=0;last=null;
        }else if(index>0&&!following.trim()&&
                 text.split('\n').at(-1).trim()===marker){
          if(text===last)samples++;else{last=text;samples=1}
          if(samples>=3){
            const cleaned=text.slice(0,index).replace(/\s+$/,'');
            if(!cleaned||cleaned.length>5000)throw Error('verified_reply_length_invalid');
            return {text:cleaned,tabId,wireSha256:sha(raw),source:'playwright_exact_bound_visible_reply'};
          }
        }else{last=null;samples=0}
      }else{last=null;samples=0}
      await sleep(450);
    }
    throw Error('visible_marked_reply_unverified');
  }catch(e){
    if(!dispatched&&composerRef){
      // A failed pre-send check must not strand our own typed draft.
      // Never erase another pending human message.
      try{
        const contents=await composerRef.innerText();
        if(contents.includes(marker)&&contents.includes(prompt))
          await composerRef.fill('');
      }catch{}
    }
    e.dispatched=dispatched;throw e
  }
  finally{await browser.close().catch(()=>{})}
}

export function createRitsuPlaywrightTransport({
  directory,tabId,boundUrl,reply=playwrightReply,
}={}){
  if(!path.isAbsolute(directory||''))throw Error('absolute_private_transport_dir_required');
  if(!TAB.test(tabId||'')||!CHAT.test(boundUrl||''))
    throw Error('exact_authorized_chat_tab_and_url_required');
  if(typeof reply!=='function')throw Error('playwright_reply_adapter_required');
  let previous=Promise.resolve();
  const filename=id=>path.join(directory,sha(id)+'.json');
  async function work(file,command,marker){
    let row=await load(file);
    if(!row||row.state!=='queued'||row.pid!==process.pid)return;
    // Persist uncertain disposition BEFORE any potential browser side effect.
    row={...row,state:'uncertain',phase:'may_have_dispatched',at:new Date().toISOString()};
    await writeAtomic(file,row);
    try{
      const result=await reply({tabId,boundUrl,prompt:command.turn.prompt,marker});
      if(!result||typeof result.text!=='string'||!result.text.trim()||
        result.tabId!==tabId||result.text.length>5000)
        throw Error('playwright_answer_receipt_invalid');
      row={...row,state:'completed',phase:'verified',result:{
        ok:true,sessionId:command.turn.sessionId,turnId:command.turn.turnId,
        channel:command.turn.channel,tabId,text:result.text,
      }};
    }catch(error){
      row={...row,state:error.dispatched===false?'failed':'uncertain',
        phase:'unverified',reason:String(error.message||'playwright_failed').slice(0,110)};
    }
    await writeAtomic(file,row);
  }
  return Object.freeze({
    async submit(command){
      const id=command?.commandId;
      if(!ID.test(id||'')||command.action!=='chat.turn'||
        command.source!=='home-center')throw Error('invalid_home_center_chat_command');
      const turn=validateRitsuTurn(command.turn);
      if(id!=='ritsu.'+turn.turnId)throw Error('command_id_turn_mismatch');
      await mkdir(directory,{recursive:true,mode:0o700});
      const file=filename(id);
      const old=await load(file);
      if(old){
        if(old.command?.turn?.prompt!==turn.prompt||
           old.command?.turn?.sessionId!==turn.sessionId)throw Error('turn_id_collision');
        return {ok:true,commandId:id,state:old.state==='queued'?'queued':
          old.state==='completed'?'completed':'leased'};
      }
      const marker='RITSU_PHONE_PROOF_'+randomBytes(10).toString('hex').toUpperCase();
      const row={schema:1,state:'queued',command,pid:process.pid,
        marker,at:new Date().toISOString()};
      const fd=await open(file,'wx',0o600);
      try{await fd.writeFile(JSON.stringify(row));await fd.sync()}finally{await fd.close()}
      previous=previous.then(()=>work(file,command,marker)).catch(()=>{});
      return {ok:true,commandId:id,state:'queued'};
    },
    async readResult(id){
      if(!ID.test(id||''))throw Error('invalid_command_identifier');
      const row=await load(filename(id));
      if(!row)return null;
      if(row.pid!==process.pid&&row.state!=='completed')
        return {commandId:id,state:'uncertain'};
      if(row.state==='completed')
        return {commandId:id,state:'completed',result:row.result};
      if(row.state==='failed')return {commandId:id,state:'failed'};
      if(row.state==='uncertain'&&row.phase==='unverified')
        return {commandId:id,state:'uncertain'};
      if(Date.now()-Date.parse(row.at)>125000)
        return {commandId:id,state:'uncertain'};
      return {commandId:id,state:'leased'};
    }
  });
}
