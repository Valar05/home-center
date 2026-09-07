const API = Object.freeze({
  status: '/v1/atom/status',
  commands: '/v1/atom/commands',
  receipts: '/v1/atom/receipts',
  diagnose: '/v1/atom/diagnose',
  tabs: '/v1/atom/throne/tabs',
  vlad: '/v1/atom/vlad',
});
const QUEUE_KEY='atom.chromium-throne.offline-queue.v1';
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const els={atom:$('#atomState'),vlad:$('#vladState'),queue:$('#queueState'),net:$('#netState'),missions:$('#missionList'),tabs:$('#tabList'),receipts:$('#receiptList'),diag:$('#diagOut'),live:$('#live'),navLive:$('#navLive'),text:$('#commandText')};
const viewTabs=$$('[role="tab"][data-view]');
const viewPanels=$$('[role="tabpanel"].view');
const queue=()=>{try{return JSON.parse(localStorage.getItem(QUEUE_KEY)||'[]')}catch{return []}};
const save=q=>{localStorage.setItem(QUEUE_KEY,JSON.stringify(q)); els.queue.textContent=`Queue: ${q.length}`};
const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
const card=(title,body,meta='')=>`<article class="item"><strong>${esc(title)}</strong><div>${esc(body)}</div><div class="meta">${esc(meta)}</div></article>`;
const selectedTab=()=>viewTabs.find(tab=>tab.getAttribute('aria-selected')==='true')||viewTabs[0];
function activateView(button,{focusTab=false,announce=true}={}){if(!button)return;const targetId=button.dataset.view;viewTabs.forEach(tab=>{const selected=tab===button;tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1});viewPanels.forEach(panel=>{const selected=panel.id===targetId;panel.hidden=!selected;panel.classList.toggle('hidden',!selected)});if(focusTab)button.focus();if(announce&&els.navLive)els.navLive.textContent=`${button.textContent.trim()} view selected.`}
function returnToSelectedTab(){const tab=selectedTab();if(!tab)return;tab.focus();if(els.navLive)els.navLive.textContent=`Returned to ${tab.textContent.trim()} tab.`}
async function req(path, options={}){const r=await fetch(path,{...options,headers:{'content-type':'application/json',...(options.headers||{})}});if(!r.ok)throw new Error(`${r.status} ${await r.text()}`);return r.status===204?null:r.json()}
function localCommand(text){return {clientCommandId:crypto.randomUUID(),text,createdAt:new Date().toISOString(),source:'atom.chromium-throne',humanInitiated:true}}
async function submit(command){try{const out=await req(API.commands,{method:'POST',body:JSON.stringify(command)});els.live.textContent='Command accepted by Atom and Vlad.';return out}catch(error){const q=queue();q.push(command);save(q);els.live.textContent='Atom is unreachable. Command preserved offline.';throw error}}
async function flush(){if(!navigator.onLine)return;const q=queue();if(!q.length)return;const keep=[];for(const command of q){try{await req(API.commands,{method:'POST',body:JSON.stringify(command)})}catch{keep.push(command)}}save(keep)}
async function refresh(){els.net.textContent=`Network: ${navigator.onLine?'online':'offline'}`;els.net.classList.toggle('offline',!navigator.onLine);save(queue());try{const s=await req(API.status);els.atom.textContent=`Atom: ${s.state||'online'}`;const v=s.vlad||{};els.vlad.textContent=v.loaded?`Vlad: ${v.state||'loaded'} · ${v.maxParallelWorkers||'?'} workers`:'Vlad: contract missing';els.vlad.classList.toggle('offline',!v.loaded);const missions=s.missions||[];els.missions.innerHTML=missions.length?missions.map(m=>card(m.title||m.missionId,m.summary||m.state,`${m.state||''} · ${m.receiptState||'no receipt yet'}`)).join(''):'<p class="meta">No active missions.</p>'}catch{els.atom.textContent='Atom: unreachable';els.vlad.textContent='Vlad: unavailable';els.vlad.classList.add('offline')}try{const t=await req(API.tabs);els.tabs.innerHTML=(t.tabs||[]).map(x=>card(x.title||x.tabId,x.summary||x.url,`${x.state||'unknown'} · ${x.worker||'Atom-routed'}`)).join('')||'<p class="meta">No browser organs active.</p>'}catch{els.tabs.innerHTML='<p class="meta">Throne data unavailable while Atom is offline.</p>'}try{const r=await req(API.receipts);els.receipts.innerHTML=(r.receipts||[]).slice(0,30).map(x=>card(x.title||x.kind||'Receipt',x.summary||x.result||'',`${x.state||''} ${x.at||''}`)).join('')||'<p class="meta">No receipts yet.</p>'}catch{}}
$('#commandForm').addEventListener('submit',async e=>{e.preventDefault();const text=els.text.value.trim();if(!text)return;els.text.value='';try{await submit(localCommand(text))}catch{}await refresh()});
$('#diagnose').addEventListener('click',async()=>{els.diag.textContent='Diagnosing…';try{const r=await req(API.diagnose,{method:'POST',body:JSON.stringify({repair:true,humanInitiated:true})});els.diag.textContent=JSON.stringify(r,null,2);els.live.textContent='Diagnostic repair finished.'}catch(e){els.diag.textContent=`Atom unavailable: ${e.message}`}});
viewTabs.forEach((button,index)=>{button.addEventListener('click',()=>activateView(button));button.addEventListener('keydown',event=>{let nextIndex=null;if(event.key==='ArrowRight'||event.key==='ArrowDown')nextIndex=(index+1)%viewTabs.length;else if(event.key==='ArrowLeft'||event.key==='ArrowUp')nextIndex=(index-1+viewTabs.length)%viewTabs.length;else if(event.key==='Home')nextIndex=0;else if(event.key==='End')nextIndex=viewTabs.length-1;if(nextIndex===null)return;event.preventDefault();activateView(viewTabs[nextIndex],{focusTab:true})})});
viewPanels.forEach(panel=>panel.addEventListener('keydown',event=>{if(event.key!=='Escape'||event.target===els.text)return;event.preventDefault();returnToSelectedTab()}));
activateView(selectedTab(),{announce:false});
window.addEventListener('online',async()=>{await flush();await refresh()});window.addEventListener('offline',refresh);setInterval(refresh,5000);await flush();await refresh();
