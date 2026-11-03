// Ritsu v1.3.5: signed-in existing Chromium DOM ONLY. Never send a prompt,
// never search ChatGPT's hidden endpoints, never modify ChatGPT-side state.
import {createHash} from 'node:crypto';
import {promises as fs} from 'node:fs';
import {homedir} from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
const digest=s=>createHash('sha256').update(s,'utf8').digest('hex');
const root=path.join(homedir(),'.ritsu-control','playwright-bridge');
const stateFile=path.join(root,'state.json');
const lockFile=path.join(root,'lock');
const link=/^https:\/\/chatgpt\.com\/c\/(?:[A-Za-z0-9-]{8,120}|local-chatgpt%3[Aa][a-fA-F0-9-]{36})$/;
const tabRe=/^[A-Za-z0-9_-]{4,80}$/;
const result=x=>console.log('RITSU_BROWSER_CATALOG='+JSON.stringify(x));
function getPlaywright(){
  for(const p of [path.join(process.env.LOCALAPPDATA||'','RitsuControlBridge','package.json'),path.join(root,'package.json'),path.join(homedir(),'workspace','home-center','browser-worker','package.json')]){
    try{return createRequire(p)('playwright')}catch{}
  }
  throw Error('PLAYWRIGHT_NOT_PRESENT_IN_EXISTING_WORKER');
}
async function attach(){
  const pw=getPlaywright();
  for(const port of [9236,9222,9223,9333])try{
    const base='http://127.0.0.1:'+port;
    const meta=await (await fetch(base+'/json/version',{signal:AbortSignal.timeout(1200)})).json();
    if(!/chrome|chromium/i.test(meta.Browser||''))continue;
    return await pw.chromium.connectOverCDP(base,{timeout:5500});
  }catch{}
  throw Error('SIGNED_IN_LOCAL_CHROME_CDP_UNAVAILABLE');
}
async function main(){
  const [cmd,tab,url]=process.argv.slice(2);
  if(!['--discover','--bind'].includes(cmd))throw Error('UNKNOWN_COMMAND');
  if(cmd==='--bind'&&(!tabRe.test(tab||'')||!link.test(url||'')))throw Error('UNSUPPORTED_EXACT_URL_FORMAT');
  const browser=await attach();
  try{
    const contexts=browser.contexts();
    const pages=contexts.flatMap(c=>c.pages()).filter(p=>/^https:\/\/chatgpt\.com\//.test(p.url()));
    if(pages.length===0)throw Error('NO_SIGNED_IN_CHATGPT_BROWSER_PAGE');
    if(cmd==='--discover'){
      // Never interpret a generic list of <a> as recent chats. Positive evidence
      // for top-level history and positive exclusion of Projects are mandatory.
      const rows=[];let supported=0;
      for(const p of pages.slice(0,3)){
        const r=await p.evaluate(()=>{
          let support=false;const matches=[];
          for(const a of Array.from(document.querySelectorAll('nav a[href],aside a[href]')).slice(0,250)){
            let parent=a,history=false,project=false;
            for(let i=0;parent&&i<8;i++,parent=parent.parentElement){
              const meta=((parent.getAttribute('data-testid')||'')+' '+(parent.getAttribute('aria-label')||'')+' '+(parent.getAttribute('id')||'')).toLowerCase();
              if(/(^|[\s_-])(recent|history|conversation-list|chat-list)([\s_-]|$)/.test(meta))history=true;
              if(/(^|[\s_-])(project|projects|workspace|folder)([\s_-]|$)/.test(meta))project=true;
            }
            if(history&&!project)support=true;
            if(!history||project)continue;
            const raw=a.getAttribute('href')||'';const u=new URL(raw,location.origin);
            if(u.origin!==location.origin||!/^\/c\/(?:[A-Za-z0-9-]{8,120}|local-chatgpt%3[Aa][a-fA-F0-9-]{36})$/.test(u.pathname))continue;
            const title=(a.getAttribute('title')||a.innerText||'').trim();
            if(title)matches.push({url:u.href,title:title.slice(0,90),nonProjectVerified:true});
          }
          return {supported,matches};
        });
        if(r.supported)supported++;
        rows.push(...r.matches);
      }
      if(!supported)throw Error('SIDEBAR_RECENTS_DOM_NOT_VERIFIABLE');
      const unique=[...new Map(rows.map(r=>[r.url,r])).values()].slice(0,40);
      result({kind:'ritsu_catalog',verified:true,complete:false,chats:unique,discoveryMode:'VERIFIED_TOP_LEVEL_RECENTS_ONLY'});
      return;
    }
    // For an explicitly copied local-chatgpt%3A URL, this deliberately tests
    // the same URL without normalizing it to a guessed server chat ID.
    if(await fs.stat(lockFile).then(()=>true).catch(e=>{if(e.code==='ENOENT')return false;throw e;}))
      throw Error('BROWSER_TURN_ACTIVE_REFUSE_BIND');
    let current;try{current=JSON.parse(await fs.readFile(stateFile,'utf8'))}catch(e){if(e.code==='ENOENT')current={schema:1,turns:{},tabs:{}};else throw e;}
    if(current.schema!==1||!current.turns||!current.tabs)throw Error('BRIDGE_STATE_UNSUPPORTED');
    if(Object.values(current.turns).some(t=>t?.tabId===tab&&t?.state!=='complete'))
      throw Error('PENDING_ORIGINAL_TURN_REFUSE_REBIND');
    if(current.tabs[tab]?.url&&current.tabs[tab].url!==url)throw Error('TAB_ALREADY_BOUND_TO_DIFFERENT_URL');
    const context=contexts.find(c=>c.pages().some(p=>/^https:\/\/chatgpt\.com\//.test(p.url())));
    if(!context)throw Error('SIGNED_IN_CONTEXT_NOT_FOUND');
    const page=await context.newPage();
    try{
      await page.goto(url,{waitUntil:'domcontentloaded',timeout:25000});
      if(page.url()!==url)throw Error('EXACT_URL_REDIRECTED_OR_NOT_PERSISTENT');
      if(await page.locator('a[href*="/auth/login"],#challenge-form').count())throw Error('LOGIN_OR_CHALLENGE');
      const selectors=['#prompt-textarea','[data-testid="prompt-textarea"]','div[contenteditable="true"][role="textbox"]'];
      let canEdit=false;
      for(const q of selectors)if(await page.locator(q).first().isVisible().catch(()=>false)){canEdit=true;break;}
      if(!canEdit)throw Error('EXACT_CHAT_NOT_WRITABLE_IN_CURRENT_BROWSER');
      // Avoid racing browser worker between preflight and commit.
      if(await fs.stat(lockFile).then(()=>true).catch(e=>e.code==='ENOENT'?false:Promise.reject(e)))
        throw Error('BROWSER_TURN_STARTED_DURING_BIND');
      current.tabs[tab]={url};
      const temp=stateFile+'.ritsu-v135-'+process.pid+'.tmp';
      await fs.mkdir(root,{recursive:true});
      await fs.writeFile(temp,JSON.stringify(current),'utf8');await fs.rename(temp,stateFile);
      result({kind:'ritsu_catalog_bound',verified:true,tabId:tab,url});
    }finally{await page.close();}
  }finally{await browser.close();}
}
main().catch(e=>{result({kind:'ritsu_catalog_error',verified:false,code:String(e.message||e).replace(/[^A-Za-z0-9_:.-]/g,'_').slice(0,100)});process.exitCode=1;});
