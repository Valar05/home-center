// Read-only, exact SHA-256 user-turn recovery from an already signed-in browser.
// No Send, no new conversation, no hidden ChatGPT API, no account search.
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
const hash=s=>createHash('sha256').update(s,'utf8').digest('hex');
const digest=process.argv[2]||'';
const savedTab=process.argv[3]||'';
const knownUrl=process.argv[4]||'';
if(!/^[0-9a-f]{64}$/.test(digest)||!(/^[A-Za-z0-9_-]{4,80}$/.test(savedTab)))throw Error('RECOVERY_ARGUMENT_INVALID');
if(knownUrl&&!/^https:\/\/chatgpt\.com\/c\/[a-zA-Z0-9-]+$/.test(knownUrl))throw Error('RECOVERY_CONVERSATION_URL_INVALID');
function loadPlaywright(){
  for(const f of [path.join(process.env.LOCALAPPDATA||'', 'RitsuControlBridge','package.json'),
    path.join(homedir(),'.ritsu-control','playwright-bridge','package.json'),
    path.join(homedir(),'workspace','home-center','browser-worker','package.json')]){
    try{return createRequire(f)('playwright');}catch{}
  }
  throw Error('EXISTING_PLAYWRIGHT_UNAVAILABLE');
}
function occurrences(source,needle){let at=0,n=0;while((at=source.indexOf(needle,at))>=0){n++;at+=needle.length;}return n;}
function extract(main){
  const matched=[];const start='You said:\n';const marker='\nChatGPT said:\n';
  let p=0;
  while((p=main.indexOf(start,p))>=0){
    const end=main.indexOf(marker,p+start.length);
    if(end<0)break;
    const next=main.indexOf(start,end+marker.length);
    const prompt=main.slice(p+start.length,end).trim();
    if(hash(prompt)===digest){
      const textArea=main.slice(end+marker.length,next<0?undefined:next);
      const footer='ChatGPT can make mistakes. Check important info.';
      const last=textArea.indexOf(footer);
      const answer=(last>=0?textArea.slice(0,last):textArea).trim();
      const complete=next>=0||last>=0;
      matched.push({answer,complete,prompt});
    }
    p=end+marker.length;
  }
  return matched;
}
async function main(){
  const playwright=loadPlaywright();let browser=null;
  for(const port of [9236,9222,9223,9333]){
    try{
      const url=`http://127.0.0.1:${port}`;
      const info=await (await fetch(url+'/json/version',{signal:AbortSignal.timeout(1000)})).json();
      if(!/chrome|chromium/i.test(info.Browser||''))continue;
      browser=await playwright.chromium.connectOverCDP(url,{timeout:3000});break;
    }catch{}
  }
  if(!browser)throw Error('APPROVED_CHROMIUM_SESSION_UNAVAILABLE');
  try{
    const contexts=browser.contexts();if(!contexts.length)throw Error('CHROME_CONTEXT_UNAVAILABLE');
    const tabs=contexts.flatMap(c=>c.pages()).filter(p=>/^https:\/\/chatgpt\.com\/(c\/|$)/.test(p.url()));
    if(knownUrl&&!tabs.some(p=>p.url()===knownUrl)){
      const page=await contexts[0].newPage();
      await page.goto(knownUrl,{waitUntil:'domcontentloaded',timeout:12000});
      tabs.push(page);
    }
    if(tabs.length>20)throw Error('TOO_MANY_OPEN_BROWSER_TABS');
    // Deduplicate different browser windows showing the same exact canonical conversation.
    const unique=new Map();
    for(const page of tabs){
      if(!/^https:\/\/chatgpt\.com\/c\/[a-zA-Z0-9-]+$/.test(page.url()))continue;
      // Saved tab URL is a preferred restoration hint, NOT a unique authority.
      // A later turn can move the tab binding to a newer conversation.
      // Search other already-open signed-in chat pages too, requiring one exact SHA match.
      if(!unique.has(page.url()))unique.set(page.url(),page);
    }
    const matches=[];
    for(const [url,page] of unique){
      let prior='',stable=0;
      for(let j=0;j<5;j++){
        const screen=await page.locator('main').innerText({timeout:4500}).catch(()=>null);
        if(!screen)break;
        const found=extract(screen);
        if(found.length>1)throw Error('DUPLICATE_MATCHED_PROMPT_IN_SAME_CONVERSATION');
        if(found.length===0)break;
        const {answer,complete}=found[0];
        if(!complete||!answer||answer.length>5000||/^(Latest response|Thinking effort|ChatGPT can make mistakes)/i.test(answer))break;
        const busy=await page.getByRole('button',{name:/stop generating|stop streaming|stop response/i}).count().catch(()=>1);
        if(busy!==0)break;
        if(answer===prior)stable++;else stable=0;
        prior=answer;
        if(stable>=2){matches.push({url,text:answer,sha256:hash(answer)});break;}
        await page.waitForTimeout(300);
      }
    }
    if(matches.length!==1)throw Error(matches.length?'RESPONSE_AMBIGUOUS_NO_JOURNAL_WRITE':'NO_UNIQUE_VERIFIED_BROWSER_REPLY');
    console.log('RITSU_RECOVERY_RESULT='+JSON.stringify({ok:true,verified:true,source:'playwright-rendered-chatgpt-reply',...matches[0]}));
  }finally{await browser.close();}
}
main().catch(e=>{console.log('RITSU_RECOVERY_ERROR='+String(e.message||e).replace(/[^A-Za-z0-9_:-]/g,'_').slice(0,110));process.exitCode=1;});
