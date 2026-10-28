// Fail-closed repair for a Playwright-authored UNSENT draft only.
// It must match the original exact private job nonce plus original request;
// never delete arbitrary phone or human composer content.
import {readFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright-core';
const jobId=process.argv[2];
if(!/^ritsu-android-test-[a-f0-9]{16}$/.test(jobId||''))throw Error('exact_smoke_job_id_required');
const root=path.join(process.env.LOCALAPPDATA,
  'HomeCenter','RitsuPlaywrightAndroidSmoke',jobId,'transport');
const files=(await readdir(root)).filter(x=>/^[a-f0-9]{64}\.json$/.test(x));
if(files.length!==1)throw Error('exact_one_owner_job_required');
const job=JSON.parse(await readFile(path.join(root,files[0]),'utf8'));
if(job.state!=='failed'||job.reason!=='composer_roundtrip_failed'||!job.marker||
  !job.command?.turn?.prompt)throw Error('unverified_or_sent_attempt_must_not_be_cleared');
const browser=await chromium.connectOverCDP('http://127.0.0.1:9236',
  {timeout:10000,noDefaults:true});
try{
  const tabId=process.argv[3],boundUrl=process.argv[4];
  if(!/^[A-Fa-f0-9]{32}$/.test(tabId||'')||
    !/^https:\/\/chatgpt\.com\/c\/[a-f0-9-]{36}$/.test(boundUrl||''))
    throw Error('explicit_bound_tab_required');
  let page=null;
  for(const p of browser.contexts().flatMap(c=>c.pages())){
    if(p.url()!==boundUrl)continue;
    const c=await p.context().newCDPSession(p);
    let id;
    try{id=(await c.send('Target.getTargetInfo')).targetInfo?.targetId}
    finally{await c.detach()}
    if(id===tabId){page=p;break}
  }
  if(!page)throw Error('bound_tab_not_found');
  const composer=page.locator('[contenteditable="true"][data-composer-markdown][role="textbox"]');
  if(await composer.count()!==1)throw Error('ambiguous_composer');
  const text=await composer.innerText();
  if(!text.includes(job.marker)||!text.includes(job.command.turn.prompt))
    throw Error('draft_not_owned_by_exact_failed_job');
  if(await page.locator('main [class*="bg-user-message"]').filter({hasText:job.marker}).count())
    throw Error('prompt_may_already_be_sent');
  await composer.fill('');
  if((await composer.innerText()).trim())throw Error('draft_clear_failed');
  process.stdout.write(JSON.stringify({state:'own_unsent_draft_cleared',jobId})+'\n');
}finally{await browser.close()}
