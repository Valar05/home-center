#!/usr/bin/env python3
"""Fail-closed source-aware Playwright/browser and Ritsu local-server extensions.
For isolated Windows source staging ONLY. Never mutates journal, Chrome profile,
or a live server in place. Includes no message sending or speaker substitution.
"""
from pathlib import Path
import hashlib,sys

def one(s,a,b,label):
    n=s.count(a)
    if n!=1:raise RuntimeError(f'{label}: {n} anchor matches')
    return s.replace(a,b,1)

CATALOG_JS=r'''
async function ritsuCatalog(){
  const pw=playwright(),browser=await attach(pw);
  try{
    const candidates=[];const seen=new Set();
    const pages=browser.contexts().flatMap(c=>c.pages()).filter(p=>
      /^https:\/\/chatgpt\.com\/(?:c\/|$)/.test(p.url()));
    for(const page of pages.slice(0,4)){
      const items=await page.evaluate(()=>{
        const out=[];
        const nodes=Array.from(document.querySelectorAll('nav a[href],aside a[href]')).slice(0,250);
        for(const n of nodes){
          const href=n.getAttribute('href')||'';
          const u=new URL(href,location.origin);
          if(u.origin!=='https://chatgpt.com'||!/^\/c\/[a-zA-Z0-9-]+$/.test(u.pathname))continue;
          // Project membership must be POSITIVELY distinguished; otherwise omit.
          // Only links in a dedicated recent-history nav group are eligible.
          let parent=n,verified=false,project=false;
          for(let depth=0;parent&&depth<6;depth++,parent=parent.parentElement){
            const tid=(parent.getAttribute('data-testid')||'').toLowerCase();
            const aria=(parent.getAttribute('aria-label')||'').toLowerCase();
            const role=(parent.getAttribute('role')||'').toLowerCase();
            if(/project|workspace|folder/.test(tid+' '+aria))project=true;
            if(/history|recent|conversation-list|chat-list/.test(tid+' '+aria))verified=true;
          }
          if(!verified||project)continue;
          const title=(n.getAttribute('title')||n.innerText||'').trim().slice(0,100);
          if(!title)continue;
          out.push({url:u.origin+u.pathname,title,nonProjectVerified:true});
          if(out.length>=30)break;
        }
        return out;
      });
      for(const item of items){if(!seen.has(item.url)){
        seen.add(item.url);candidates.push(item);
      }}
    }
    // DOM drift may yield an empty list. This is not proof there are no chats.
    output({kind:'ritsu_catalog',verified:true,chats:candidates.slice(0,40),
      discoveryMode:'VERIFIED_MAIN_RECENTS_ONLY',complete:false});
  }finally{await browser.close();}
}
async function ritsuBind(){
  const tabId=args.get('--tab'),url=args.get('--url');
  if(!TAB.test(tabId||'')||!/^https:\/\/chatgpt\.com\/c\/[a-zA-Z0-9-]{8,120}$/.test(url||''))
    throw Error('invalid_exact_conversation_binding');
  // Never change a mapping while a browser turn may be dispatched.
  try{await fs.access(lockFile);throw Error('turn_running_refuse_conversation_rebind');}
  catch(e){if(e.code!=='ENOENT')throw e;}
  const state=await load();
  for(const t of Object.values(state.turns)){
    if(t?.tabId===tabId && t?.state!=='complete')
      throw Error('unresolved_turn_refuse_conversation_rebind');
  }
  if(state.tabs[tabId]?.url && state.tabs[tabId].url!==url)
    throw Error('existing_tab_binding_refuse_implicit_retarget');
  const pw=playwright(),browser=await attach(pw);
  try{
    const contexts=browser.contexts();
    const context=contexts.find(c=>c.pages().some(p=>/^https:\/\/chatgpt\.com\//.test(p.url())));
    if(!context)throw Error('signed_in_chatgpt_context_unavailable');
    const page=await context.newPage();
    try{
      await page.goto(url,{waitUntil:'domcontentloaded',timeout:25000});
      if(page.url()!==url)throw Error('conversation_redirect_or_wrong_account');
      const selectors=['#prompt-textarea','[data-testid="prompt-textarea"]',
        'div[contenteditable="true"][role="textbox"]'];
      let editor=false;
      for(const selector of selectors){if(await page.locator(selector).first().isVisible().catch(()=>false)){
        editor=true;break;
      }}
      if(!editor)throw Error('existing_chat_not_writable_or_login_challenge');
      state.tabs[tabId]={url};await save(state);
      output({kind:'ritsu_catalog_bound',verified:true,tabId,url});
    }finally{await page.close();}
  }finally{await browser.close();}
}
'''

SERVER_JS=r'''
  async function browserCatalogCommand(flags){
    return new Promise((resolve,reject)=>{
      const processArgs=[BRIDGE,...flags];
      const p=spawn(process.execPath,processArgs,{windowsHide:true,stdio:['ignore','pipe','pipe']});
      let out='',err='';
      const timer=setTimeout(()=>{p.kill();reject(Error('browser_catalog_timeout'));},28000);
      p.stdout.on('data',b=>{out=(out+b.toString()).slice(-50000);});
      p.stderr.on('data',b=>{err=(err+b.toString()).slice(-500);});
      p.on('error',e=>{clearTimeout(timer);reject(Error('browser_catalog_spawn_failed'));});
      p.on('close',code=>{
        clearTimeout(timer);
        if(code!==0)return reject(Error('browser_catalog_failed_'+code));
        const rows=out.split(/\r?\n/).filter(x=>x.startsWith('RITSU_BROWSER_RECEIPT='));
        if(rows.length!==1)return reject(Error('browser_catalog_receipt_missing'));
        let value;try{value=JSON.parse(rows[0].slice('RITSU_BROWSER_RECEIPT='.length));}
        catch{return reject(Error('browser_catalog_receipt_invalid'));}
        resolve(value);
      });
    });
  }
'''

def patch(root:Path):
    server=root/'tools/ritsu-local-server/server.mjs'
    bridge=root/'tools/campaigns/ritsu_control_playwright_bridge.mjs'
    if not server.is_file() or not bridge.is_file():raise RuntimeError('Expected Windows source tree not present')
    s=server.read_text('utf8');b=bridge.read_text('utf8')
    if 'ritsuCatalog' in b or 'browserCatalogCommand' in s:raise RuntimeError('Catalog patch exists; do not duplicate')
    b=one(b,"if(['--doctor','--peek','--launch','--recover-reply','--resume-draft'].includes(flag))",
        "if(['--doctor','--peek','--launch','--recover-reply','--resume-draft','--catalog','--bind'].includes(flag))",'arg parser')
    b=one(b,' async function main(){',CATALOG_JS+'\n async function main(){','browser catalog funcs')
    b=one(b,"  if(args.has('--doctor'))return doctor();","  if(args.has('--doctor'))return doctor();\n  if(args.has('--catalog'))return ritsuCatalog();\n  if(args.has('--bind'))return ritsuBind();",'main cli')
    s=one(s,'  const server=http.createServer(async(req,res)=>{',SERVER_JS+'\n  const server=http.createServer(async(req,res)=>{','server wrapper')
    s=one(s,"import {fileURLToPath} from 'node:url';","import {fileURLToPath} from 'node:url';\nimport {voiceSet,voiceDeliver} from './ritsu_pocket_voice_hook.mjs';",'voice module import')
    s=one(s,"       if(ev.complete)complete=true;","       if(ev.complete){complete=true;void voiceDeliver(job.tabId,job.turnId,ev.text).catch(()=>{});}",'voice verified-final hook')
    marker="       if(req.method==='GET'&&url.pathname==='/v1/ritsu/status')return send(200,{ok:true,transport:'tailscale-sse',cloudOps:0,seq});"
    add=r'''       if(req.method==='GET'&&url.pathname==='/v1/ritsu/catalog'){
         const result=await browserCatalogCommand(['--catalog']);
         if(result.kind!=='ritsu_catalog'||!result.verified)throw Error('catalog_not_verified');
         return send(200,result);
       }
       if(req.method==='POST'&&url.pathname==='/v1/ritsu/bind'){
         let body='',bytes=0;
         for await(const part of req){bytes+=part.length;if(bytes>2100)return send(413,{error:'too_large'});body+=part.toString();}
         const request=JSON.parse(body);
         if(!tabPattern.test(request.tabId||'')||
           !/^https:\/\/chatgpt\.com\/c\/[a-zA-Z0-9-]{8,120}$/.test(request.url||''))
           return send(400,{error:'invalid_binding'});
         const result=await browserCatalogCommand(['--bind','--tab',request.tabId,'--url',request.url]);
         if(result.kind!=='ritsu_catalog_bound'||!result.verified||result.url!==request.url||result.tabId!==request.tabId)
           throw Error('browser_binding_not_verified');
         return send(200,result);
       }
'''
    s=one(s,marker,marker+'\n'+add,'catalog routes')
    voice_route=r'''       if(req.method==='POST'&&url.pathname==='/v1/ritsu/voice-preference'){
         let body='',bytes=0;
         for await(const part of req){bytes+=part.length;if(bytes>400)return send(413,{error:'too_large'});body+=part.toString();}
         const request=JSON.parse(body);
         return send(200,await voiceSet(request.tabId,request.enabled));
       }
'''
    s=one(s,marker,marker+'\n'+voice_route,'voice preference route')
    target=root/'tools/ritsu-local-server/ritsu_pocket_voice_hook.mjs'
    if target.exists():raise RuntimeError('Existing voice hook requires reconciliation')
    # Same code packet directory is the directory containing this patcher.
    voice_source=Path(__file__).resolve().parent/'ritsu_pocket_voice_hook.mjs'
    if not voice_source.is_file():raise RuntimeError('Voice hook source missing')
    target.write_bytes(voice_source.read_bytes())
    # Patcher produces candidate stage only; caller must check Node syntax in Windows.
    server.write_text(s,encoding='utf8');bridge.write_text(b,encoding='utf8')
    for p in [server,bridge]:print('PATCHED='+p.as_posix()+' SHA256='+hashlib.sha256(p.read_bytes()).hexdigest())

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: patch_backend.py STAGED_WINDOWS_TREE')
    try:patch(Path(sys.argv[1]).resolve())
    except Exception as e:print('BACKEND_PATCH=BLOCKED '+str(e)[:240]);raise SystemExit(1)
