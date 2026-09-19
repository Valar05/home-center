import {
  BELLY_PHASES,
  asciiOf,
  canonicalPointMap,
  contactOf,
  fitPointMap,
  humanize,
  interpolatePointMaps,
  lintScore,
  lintSpecimen,
  motionNoteOf,
  normalizeSpecimen,
  phaseForKey,
  roleOf,
  rootOf,
  supportOf,
  textOf,
  timingWeight
} from "./cathedral-core.js";
import { LANES, SPECIMENS } from "./specimens.js";

const $ = function (selector) { return document.querySelector(selector); };
const $$ = function (selector) { return Array.from(document.querySelectorAll(selector)); };

const els = {
  rose: $("#rose-window"),
  canvas: $("#motion-canvas"),
  runtime: $("#runtime-status"),
  ascii: $("#ascii-truth"),
  truthPanel: $(".truth-panel"),
  altar: $(".altar"),
  keyId: $("#key-id"),
  keyName: $("#key-name"),
  support: $("#support-readout"),
  contact: $("#contact-readout"),
  timing: $("#timing-readout"),
  root: $("#root-readout"),
  lane: $("#lane-badge"),
  title: $("#specimen-title"),
  phase: $("#phase-sigil"),
  causal: $("#causal-role"),
  note: $("#motion-note"),
  lintScore: $("#lint-score"),
  lintList: $("#lint-list"),
  timeline: $("#timeline"),
  keyCount: $("#key-count"),
  play: $("#play"),
  prev: $("#prev-key"),
  next: $("#next-key"),
  truth: $("#toggle-truth"),
  force: $("#toggle-force"),
  trails: $("#toggle-trails"),
  asciiToggle: $("#toggle-ascii"),
  corpusSearch: $("#corpus-search"),
  laneFilters: $("#lane-filters"),
  specimenGrid: $("#specimen-grid"),
  fileInput: $("#file-input"),
  screenreader: $("#screenreader-status")
};

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const fallback = {
  schema:"ascii-kinesis.motion.v2",
  specimen_id:"cathedral-fallback-contact-vow",
  lane:"cathedral",
  principle:"A beautiful body may deform around the contact sentence but may not contradict support, contact, root, or recovery debt.",
  keys:[
    {key_id:"VOW-K0",name:"READ",timing_class:"FOURS",support_contact:"REAR_DOMINANT",contact:"NONE",causal_role:"READ / stored force",motion_arc_root_note:"The body is quiet enough that the audience can read what owns the ground.",pose_rig:{head:[25,5],root:[25,12],rear_hand:[18,10],front_hand:[31,9],rear_knee:[21,16],front_knee:[29,16],rear_foot:[18,21],front_foot:[32,21],rear_end:[10,12],front_end:[43,8]}},
    {key_id:"VOW-K1",name:"LOAD",timing_class:"FOURS",support_contact:"REAR_HARD_FRONT_LIGHT",contact:"NONE",causal_role:"LOAD / compression",motion_arc_root_note:"The silhouette folds around the rear support and visibly stores a future.",pose_rig:{head:[22,7],root:[23,14],rear_hand:[16,12],front_hand:[28,11],rear_knee:[19,18],front_knee:[28,17],rear_foot:[17,21],front_foot:[32,21],rear_end:[7,14],front_end:[40,10]}},
    {key_id:"VOW-K2",name:"COMMIT",timing_class:"TWOS",support_contact:"REAR_DRIVE_FRONT_CATCH",contact:"NONE",causal_role:"COMMIT / safety surrendered",motion_arc_root_note:"Root and tool accelerate into the sentence; the body cannot pretend it did not choose.",pose_rig:{head:[28,5],root:[29,12],rear_hand:[23,10],front_hand:[35,9],rear_knee:[25,16],front_knee:[34,16],rear_foot:[20,21],front_foot:[38,21],rear_end:[14,12],front_end:[51,8]}},
    {key_id:"VOW-K3",name:"CONTACT",timing_class:"ONES",support_contact:"FRONT_BRACE_REAR_DRIVE",contact:"TARGET",causal_role:"CONTACT INSTANT / semantic truth",motion_arc_root_note:"The distal point becomes true while the pelvis is still arriving.",pose_rig:{head:[35,5],root:[35,12],rear_hand:[30,9],front_hand:[42,8],rear_knee:[31,16],front_knee:[40,16],rear_foot:[24,21],front_foot:[44,21],rear_end:[20,11],front_end:[59,7]}},
    {key_id:"VOW-K4",name:"CONSEQUENCE",timing_class:"TWOS",support_contact:"FRONT_OWNS_CHECK",contact:"TARGET_HOLD",causal_role:"IMPACT CONSEQUENCE / overtravel",motion_arc_root_note:"The contact point holds while the body pays the force into compression and lag.",pose_rig:{head:[37,7],root:[38,14],rear_hand:[33,11],front_hand:[44,10],rear_knee:[34,18],front_knee:[42,17],rear_foot:[26,21],front_foot:[45,21],rear_end:[22,13],front_end:[59,7]}},
    {key_id:"VOW-K5",name:"RECOVERY_DEBT",timing_class:"TWOS",support_contact:"REAR_CATCH_FRONT_LIGHT",contact:"NONE",causal_role:"RECOVERY / debt visible",motion_arc_root_note:"The root catches first. Tool and hands are late. Recovery is a new event, not undo.",pose_rig:{head:[31,8],root:[32,14],rear_hand:[27,12],front_hand:[38,11],rear_knee:[29,18],front_knee:[38,17],rear_foot:[24,21],front_foot:[42,21],rear_end:[11,14],front_end:[50,10]}},
    {key_id:"VOW-K6",name:"DISPLACED_READY",timing_class:"FOURS",support_contact:"DUAL_NEW_ADDRESS",contact:"NONE",causal_role:"RECOVERY COMPLETE / displaced ready",motion_arc_root_note:"The action ends somewhere new. The world remembers that the strike happened.",pose_rig:{head:[34,6],root:[34,13],rear_hand:[29,11],front_hand:[40,10],rear_knee:[31,17],front_knee:[40,17],rear_foot:[26,21],front_foot:[44,21],rear_end:[14,13],front_end:[52,9]}}
  ]
};

const state = {
  specimen:normalizeSpecimen(fallback,{authority:"DEMO"}),
  index:0,
  playing:!reduceMotion,
  showTruth:true,
  showForce:true,
  showTrails:false,
  showAscii:true,
  startedAt:performance.now(),
  lane:"all",
  query:"",
  sourcePath:null,
  lastAnnounced:-1,
  cache:new Map()
};

function setPressed(button, active) {
  button.classList.toggle("active", active);
  button.setAttribute("aria-pressed", String(active));
}

function smoothstep(t) {
  t = Math.max(0, Math.min(1, t));
  return t*t*(3-2*t);
}

function keyDuration(key) {
  return 185 * timingWeight(key);
}

function sequenceAt(now) {
  const keys = state.specimen.keys;
  if (!keys.length) return {index:0,next:0,t:0,key:null};
  if (!state.playing || keys.length === 1) {
    return {index:state.index,next:Math.min(keys.length-1,state.index+1),t:0,key:keys[state.index]};
  }
  const connector = 150;
  let total = 0;
  const spans = keys.map(function (key, i) {
    const span = keyDuration(key) + (i < keys.length-1 ? connector : 340);
    total += span;
    return span;
  });
  const loop = Math.max(1,total);
  let cursor = (now - state.startedAt) % loop;
  let index = 0;
  for (let i=0;i<spans.length;i++) {
    if (cursor <= spans[i]) { index = i; break; }
    cursor -= spans[i];
  }
  const hold = keyDuration(keys[index]);
  const next = Math.min(keys.length-1,index+1);
  const t = index < keys.length-1 && cursor > hold ? smoothstep((cursor-hold)/connector) : 0;
  return {index:index,next:next,t:t,key:keys[t > .5 ? next : index]};
}

function resizeCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const width = Math.max(1, Math.floor(rect.width*dpr));
  const height = Math.max(1, Math.floor(rect.height*dpr));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr,0,0,dpr,0,0);
  return {ctx:ctx,width:rect.width,height:rect.height,dpr:dpr};
}

function phaseColor(phase, alpha) {
  const a = alpha == null ? 1 : alpha;
  const colors = {
    LOAD:"240,191,103",
    COMMIT:"171,126,255",
    HIT:"255,101,126",
    CONSEQUENCE:"140,231,224",
    RECOVERY:"155,227,167"
  };
  return "rgba(" + (colors[phase] || colors.LOAD) + "," + a + ")";
}

function drawArchitecture(ctx,w,h,phase) {
  ctx.clearRect(0,0,w,h);
  const bg = ctx.createRadialGradient(w*.5,h*.38,10,w*.5,h*.45,Math.max(w,h)*.7);
  bg.addColorStop(0,phaseColor(phase,.16));
  bg.addColorStop(.35,"rgba(39,20,45,.16)");
  bg.addColorStop(1,"rgba(4,4,7,.98)");
  ctx.fillStyle=bg;
  ctx.fillRect(0,0,w,h);

  ctx.save();
  ctx.strokeStyle="rgba(240,191,103,.09)";
  ctx.lineWidth=1;
  const center=w*.5;
  const base=h*.9;
  for(let i=-4;i<=4;i++){
    const x=center+i*w*.12;
    const archW=w*.17;
    const archH=h*.62 + (4-Math.abs(i))*h*.025;
    ctx.beginPath();
    ctx.moveTo(x-archW/2,base);
    ctx.lineTo(x-archW/2,base-archH*.58);
    ctx.quadraticCurveTo(x,base-archH,x+archW/2,base-archH*.58);
    ctx.lineTo(x+archW/2,base);
    ctx.stroke();
  }
  for(let y=.2;y<.9;y+=.12){
    ctx.beginPath();
    ctx.moveTo(w*.06,h*y);
    ctx.lineTo(w*.94,h*y);
    ctx.stroke();
  }
  ctx.restore();
}

function line(ctx,a,b,width,stroke) {
  if(!a || !b) return;
  ctx.beginPath();
  ctx.moveTo(a.x,a.y);
  ctx.lineTo(b.x,b.y);
  ctx.lineWidth=width;
  ctx.strokeStyle=stroke;
  ctx.lineCap="round";
  ctx.lineJoin="round";
  ctx.stroke();
}

function polygon(ctx, points, fill, stroke) {
  const valid=points.filter(Boolean);
  if(valid.length<3) return;
  ctx.beginPath();
  ctx.moveTo(valid[0].x,valid[0].y);
  for(let i=1;i<valid.length;i++) ctx.lineTo(valid[i].x,valid[i].y);
  ctx.closePath();
  ctx.fillStyle=fill;
  ctx.fill();
  if(stroke){
    ctx.strokeStyle=stroke;
    ctx.lineWidth=1;
    ctx.stroke();
  }
}

function drawStainedBody(ctx, fitted, phase, w, h) {
  const p=fitted;
  const pc=phaseColor(phase,1);
  const root=p.root;
  const head=p.head;
  const sl=p.shoulder_l || p.hand_l;
  const sr=p.shoulder_r || p.hand_r;
  const hl=p.hand_l;
  const hr=p.hand_r;
  const kl=p.knee_l;
  const kr=p.knee_r;
  const fl=p.foot_l;
  const fr=p.foot_r;

  ctx.save();
  ctx.globalCompositeOperation="source-over";
  ctx.shadowColor=phaseColor(phase,.28);
  ctx.shadowBlur=30;

  polygon(ctx,[sl,sr,root],"rgba(123,55,112,.22)",phaseColor(phase,.2));
  polygon(ctx,[root,kl,fl],"rgba(185,47,72,.16)",null);
  polygon(ctx,[root,kr,fr],"rgba(111,74,168,.17)",null);
  polygon(ctx,[sl,hl,root],"rgba(240,191,103,.10)",null);
  polygon(ctx,[sr,hr,root],"rgba(140,231,224,.08)",null);

  const outer="rgba(8,6,12,.92)";
  const bone="rgba(245,226,215,.88)";
  const accent=phaseColor(phase,.95);

  line(ctx,sl,sr,18,outer);
  line(ctx,sl,hl,18,outer);
  line(ctx,sr,hr,18,outer);
  line(ctx,root,sl,22,outer);
  line(ctx,root,sr,22,outer);
  line(ctx,root,kl,25,outer);
  line(ctx,kl,fl,22,outer);
  line(ctx,root,kr,25,outer);
  line(ctx,kr,fr,22,outer);

  line(ctx,sl,sr,7,bone);
  line(ctx,sl,hl,7,bone);
  line(ctx,sr,hr,7,bone);
  line(ctx,root,sl,8,bone);
  line(ctx,root,sr,8,bone);
  line(ctx,root,kl,9,bone);
  line(ctx,kl,fl,8,bone);
  line(ctx,root,kr,9,bone);
  line(ctx,kr,fr,8,bone);

  line(ctx,p.tool_rear,p.tool_front,14,outer);
  line(ctx,p.tool_rear,p.tool_front,5,accent);

  [hl,hr,fl,fr,root].filter(Boolean).forEach(function(pt){
    ctx.beginPath();
    ctx.arc(pt.x,pt.y,5.5,0,Math.PI*2);
    ctx.fillStyle=accent;
    ctx.fill();
  });

  if(head){
    const r=Math.max(12,Math.min(w,h)*.024);
    const g=ctx.createRadialGradient(head.x-r*.25,head.y-r*.3,2,head.x,head.y,r);
    g.addColorStop(0,"rgba(255,244,224,.96)");
    g.addColorStop(.48,phaseColor(phase,.72));
    g.addColorStop(1,"rgba(22,10,26,.96)");
    ctx.fillStyle=g;
    ctx.beginPath();
    ctx.arc(head.x,head.y,r,0,Math.PI*2);
    ctx.fill();
    ctx.strokeStyle=phaseColor(phase,.65);
    ctx.lineWidth=1.5;
    ctx.stroke();
  }

  ctx.restore();
}

function drawTruthSkeleton(ctx,p,phase) {
  ctx.save();
  ctx.setLineDash([3,5]);
  ctx.strokeStyle="rgba(140,231,224,.68)";
  ctx.lineWidth=1.2;
  line(ctx,p.shoulder_l,p.shoulder_r,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.shoulder_l,p.hand_l,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.shoulder_r,p.hand_r,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.root,p.shoulder_l,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.root,p.shoulder_r,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.root,p.knee_l,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.knee_l,p.foot_l,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.root,p.knee_r,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.knee_r,p.foot_r,1.2,"rgba(140,231,224,.68)");
  line(ctx,p.tool_rear,p.tool_front,1.2,"rgba(140,231,224,.68)");
  ctx.setLineDash([]);
  const glyphs=[
    ["head","O"],["root","+"],["hand_l","o"],["hand_r","o"],
    ["foot_l","="],["foot_r","="],["tool_rear","<"],["tool_front",">"]
  ];
  ctx.font="700 13px monospace";
  ctx.textAlign="center";
  ctx.textBaseline="middle";
  glyphs.forEach(function(entry){
    const pt=p[entry[0]];
    if(!pt) return;
    ctx.fillStyle=entry[0].indexOf("tool")===0 ? phaseColor(phase,1) : "rgba(140,231,224,.96)";
    ctx.fillText(entry[1],pt.x,pt.y);
  });
  ctx.restore();
}

function drawForce(ctx,p,key,phase,w,h) {
  if(!state.showForce) return;
  const support=(supportOf(key)||"").toUpperCase();
  const feet=[["foot_l","L"],["foot_r","R"]];
  feet.forEach(function(entry){
    const pt=p[entry[0]];
    if(!pt) return;
    const active =
      support.indexOf(entry[1]==="L" ? "LEFT" : "RIGHT")>=0 ||
      support.indexOf(entry[1]==="L" ? "REAR" : "FRONT")>=0 ||
      support.indexOf("BOTH")>=0 || support.indexOf("DUAL")>=0;
    ctx.save();
    ctx.strokeStyle=active ? phaseColor(phase,.9) : "rgba(246,234,216,.2)";
    ctx.lineWidth=active ? 3 : 1;
    ctx.beginPath();
    ctx.moveTo(pt.x-18,pt.y+13);
    ctx.lineTo(pt.x+18,pt.y+13);
    ctx.stroke();
    if(active){
      ctx.beginPath();
      ctx.moveTo(pt.x,pt.y+12);
      ctx.lineTo(pt.x,pt.y-38);
      ctx.strokeStyle=phaseColor(phase,.35);
      ctx.stroke();
    }
    ctx.restore();
  });

  const target=p.tool_front || p.hand_r || p.hand_l || p.head;
  if(p.root && target){
    ctx.save();
    ctx.strokeStyle=phaseColor(phase,.32);
    ctx.lineWidth=2;
    ctx.setLineDash([8,8]);
    ctx.beginPath();
    ctx.moveTo(p.root.x,p.root.y);
    ctx.lineTo(target.x,target.y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }

  if(phase==="HIT" && target){
    ctx.save();
    for(let r=12;r<56;r+=13){
      ctx.strokeStyle=phaseColor(phase,Math.max(.08,.55-r/120));
      ctx.lineWidth=2;
      ctx.beginPath();
      ctx.arc(target.x,target.y,r,0,Math.PI*2);
      ctx.stroke();
    }
    ctx.restore();
  }
}

function drawAsciiCloud(ctx,key,w,h,phase) {
  const raw=asciiOf(key);
  const lines=raw.split("\n");
  const longest=Math.max(1,...lines.map(function(line){return line.length;}));
  const rows=Math.max(1,lines.length);
  const cell=Math.min((w*.82)/longest,(h*.7)/rows);
  const ox=(w-longest*cell)/2;
  const oy=(h-rows*cell)/2;
  ctx.save();
  ctx.font=Math.max(7,cell*.88)+"px monospace";
  ctx.textBaseline="top";
  ctx.shadowColor=phaseColor(phase,.35);
  ctx.shadowBlur=10;
  for(let y=0;y<lines.length;y++){
    for(let x=0;x<lines[y].length;x++){
      const ch=lines[y][x];
      if(ch===" ") continue;
      ctx.fillStyle=/[O+o=<>]/.test(ch) ? phaseColor(phase,.95) : "rgba(235,225,236,.74)";
      ctx.fillText(ch,ox+x*cell,oy+y*cell);
    }
  }
  ctx.restore();
}

function drawGhosts(ctx,keyIndex,w,h,phase) {
  if(!state.showTrails) return;
  for(let back=1;back<=3;back++){
    const idx=Math.max(0,keyIndex-back);
    const pts=canonicalPointMap(state.specimen.keys[idx]);
    if(!Object.keys(pts).length) continue;
    const fit=fitPointMap(pts,w,h,Math.min(w,h)*.14);
    ctx.save();
    ctx.globalAlpha=.1*(4-back);
    drawTruthSkeleton(ctx,fit,phase);
    ctx.restore();
  }
}

function renderMotion(now) {
  const dims=resizeCanvas(els.canvas);
  const ctx=dims.ctx,w=dims.width,h=dims.height;
  const seq=sequenceAt(now);
  const keys=state.specimen.keys;
  if(!keys.length) return;

  if(state.playing && seq.index!==state.index){
    state.index=seq.index;
    updateText(seq.key,false);
  }

  const current=keys[seq.index];
  const next=keys[seq.next] || current;
  const phase=phaseForKey(seq.key || current);
  drawArchitecture(ctx,w,h,phase);

  const a=canonicalPointMap(current);
  const b=canonicalPointMap(next);

  if(Object.keys(a).length){
    const raw=seq.t>0 && Object.keys(b).length ? interpolatePointMaps(a,b,seq.t) : a;
    const fitted=fitPointMap(raw,w,h,Math.min(w,h)*.14);
    drawGhosts(ctx,seq.index,w,h,phase);
    drawStainedBody(ctx,fitted,phase,w,h);
    drawForce(ctx,fitted,seq.key || current,phase,w,h);
    if(state.showTruth) drawTruthSkeleton(ctx,fitted,phase);
  } else {
    drawAsciiCloud(ctx,seq.key || current,w,h,phase);
  }

  drawFrameInscription(ctx,w,h,seq.key || current,phase);
}

function drawFrameInscription(ctx,w,h,key,phase) {
  ctx.save();
  ctx.fillStyle="rgba(246,234,216,.36)";
  ctx.font="700 10px ui-monospace, monospace";
  ctx.textAlign="left";
  ctx.fillText("SEMANTIC CONTACT LOCK",18,24);
  ctx.textAlign="right";
  ctx.fillStyle=phaseColor(phase,.7);
  ctx.fillText(phase,w-18,24);
  ctx.restore();
}

function updateText(key,announce) {
  if(!key) return;
  const phase=phaseForKey(key);
  const index=state.specimen.keys.indexOf(key);
  els.keyId.textContent=textOf(key.key_id || key.id || "K"+Math.max(0,index));
  els.keyName.textContent=textOf(key.name || key.phase || "UNNAMED KEY");
  els.ascii.textContent=asciiOf(key);
  els.support.textContent=supportOf(key);
  els.contact.textContent=contactOf(key);
  els.timing.textContent=textOf(key.timing_class || key.timing || key.expose || "UNNAMED");
  els.root.textContent=rootOf(key);
  els.phase.textContent=phase;
  els.causal.textContent=roleOf(key) || "No causal role named.";
  els.note.textContent=motionNoteOf(key) || state.specimen.principle || "No motion note named.";
  els.timeline.value=String(Math.max(0,index));
  els.keyCount.textContent=(Math.max(0,index)+1)+" / "+state.specimen.keys.length;
  $$(".belly-cycle button").forEach(function(button){
    button.classList.toggle("active",button.dataset.phase===phase);
  });
  if(announce!==false && state.lastAnnounced!==index){
    els.screenreader.textContent=
      "Key "+(index+1)+" of "+state.specimen.keys.length+", "+
      (key.name || key.key_id || "unnamed")+", phase "+phase+
      ". Support "+supportOf(key)+". Contact "+contactOf(key)+".";
    state.lastAnnounced=index;
  }
}

function updateSpecimenUI() {
  const s=state.specimen;
  els.lane.textContent=(s.lane || "unknown").toUpperCase();
  els.title.textContent=s.title;
  els.timeline.max=String(Math.max(0,s.keys.length-1));
  els.timeline.value="0";
  state.index=0;
  state.startedAt=performance.now();
  state.lastAnnounced=-1;
  const issues=lintSpecimen(s);
  const score=lintScore(issues);
  els.lintScore.textContent=score+"/100";
  els.lintScore.style.color=score>=88?"var(--green)":score>=70?"var(--gold)":"#ef8da1";
  els.lintList.innerHTML="";
  if(!issues.length){
    const li=document.createElement("li");
    li.textContent="No structural warnings from the Cathedral adapter.";
    els.lintList.appendChild(li);
  } else {
    issues.forEach(function(issue){
      const li=document.createElement("li");
      li.className=issue.severity;
      li.textContent=issue.code+" · "+issue.message;
      els.lintList.appendChild(li);
    });
  }
  updateText(s.keys[0],true);
}

async function loadSpecimen(meta,scroll) {
  els.runtime.textContent="Opening "+meta.id+"…";
  try {
    let raw=state.cache.get(meta.path);
    if(!raw){
      const response=await fetch(meta.path,{cache:"no-store"});
      if(!response.ok) throw new Error("HTTP "+response.status);
      raw=await response.json();
      state.cache.set(meta.path,raw);
    }
    state.specimen=normalizeSpecimen(raw,meta);
    state.sourcePath=meta.path;
    updateSpecimenUI();
    els.runtime.textContent=
      "LIVE CORPUS · "+state.specimen.keys.length+" decisive keys · "+
      (meta.authority || "EVIDENCE")+" · "+meta.id;
    if(scroll!==false) $("#nave").scrollIntoView({behavior:reduceMotion?"auto":"smooth",block:"start"});
  } catch(error) {
    console.error(error);
    state.specimen=normalizeSpecimen(fallback,{authority:"DEMO"});
    state.sourcePath=null;
    updateSpecimenUI();
    els.runtime.textContent=
      "Corpus fetch failed ("+error.message+"). Showing embedded Cathedral vow. Serve this directory over HTTP to open repository specimens.";
  }
}

function gotoKey(index) {
  const count=state.specimen.keys.length;
  if(!count) return;
  state.playing=false;
  state.index=Math.max(0,Math.min(count-1,index));
  els.play.textContent="PLAY";
  state.startedAt=performance.now();
  updateText(state.specimen.keys[state.index],true);
}

function togglePlay() {
  state.playing=!state.playing;
  state.startedAt=performance.now()-state.index*250;
  els.play.textContent=state.playing?"PAUSE":"PLAY";
}

function renderLaneFilters() {
  const lanes=["all"].concat(LANES);
  lanes.forEach(function(lane){
    const b=document.createElement("button");
    b.type="button";
    b.textContent=lane;
    b.classList.toggle("active",lane==="all");
    b.addEventListener("click",function(){
      state.lane=lane;
      Array.from(els.laneFilters.children).forEach(function(child){child.classList.toggle("active",child===b);});
      renderSpecimenGrid();
    });
    els.laneFilters.appendChild(b);
  });
}

function renderSpecimenGrid() {
  const q=state.query.trim().toLowerCase();
  const filtered=SPECIMENS
    .filter(function(s){return state.lane==="all" || s.lane===state.lane;})
    .filter(function(s){
      if(!q) return true;
      return (s.id+" "+s.title+" "+s.lane+" "+s.note).toLowerCase().indexOf(q)>=0;
    })
    .sort(function(a,b){
      if(a.featured!==b.featured) return a.featured?-1:1;
      return a.id.localeCompare(b.id);
    });

  els.specimenGrid.innerHTML="";
  filtered.forEach(function(meta){
    const card=document.createElement("button");
    card.type="button";
    card.className="specimen-card"+(meta.featured?" featured":"");
    card.setAttribute("aria-label","Open "+meta.title);
    const lane=document.createElement("div");
    lane.className="card-lane";
    lane.textContent=meta.lane;
    const h=document.createElement("h3");
    h.textContent=meta.title;
    const p=document.createElement("p");
    p.textContent=meta.note;
    const foot=document.createElement("div");
    foot.className="card-foot";
    const auth=document.createElement("strong");
    auth.textContent=meta.authority;
    const arrow=document.createElement("span");
    arrow.textContent="OPEN →";
    foot.append(auth,arrow);
    card.append(lane,h,p,foot);
    card.addEventListener("click",function(){loadSpecimen(meta,true);});
    els.specimenGrid.appendChild(card);
  });

  if(!filtered.length){
    const empty=document.createElement("p");
    empty.textContent="No specimens match this vault search.";
    empty.style.color="var(--muted)";
    els.specimenGrid.appendChild(empty);
  }
}

function bindEvents() {
  els.play.addEventListener("click",togglePlay);
  els.prev.addEventListener("click",function(){gotoKey(state.index-1);});
  els.next.addEventListener("click",function(){gotoKey(state.index+1);});
  els.timeline.addEventListener("input",function(){gotoKey(Number(els.timeline.value));});

  els.truth.addEventListener("click",function(){
    state.showTruth=!state.showTruth;
    setPressed(els.truth,state.showTruth);
  });
  els.force.addEventListener("click",function(){
    state.showForce=!state.showForce;
    setPressed(els.force,state.showForce);
  });
  els.trails.addEventListener("click",function(){
    state.showTrails=!state.showTrails;
    setPressed(els.trails,state.showTrails);
  });
  els.asciiToggle.addEventListener("click",function(){
    state.showAscii=!state.showAscii;
    setPressed(els.asciiToggle,state.showAscii);
    els.truthPanel.classList.toggle("hidden",!state.showAscii);
    els.altar.classList.toggle("ascii-hidden",!state.showAscii);
  });

  els.corpusSearch.addEventListener("input",function(){
    state.query=els.corpusSearch.value;
    renderSpecimenGrid();
  });

  els.fileInput.addEventListener("change",async function(){
    const file=els.fileInput.files && els.fileInput.files[0];
    if(!file) return;
    try{
      const raw=JSON.parse(await file.text());
      state.specimen=normalizeSpecimen(raw,{id:file.name,authority:"USER FILE",lane:raw.lane || "local"});
      state.sourcePath=null;
      updateSpecimenUI();
      els.runtime.textContent="USER FILE · "+file.name+" · "+state.specimen.keys.length+" decisive keys";
      $("#nave").scrollIntoView({behavior:reduceMotion?"auto":"smooth"});
    }catch(error){
      els.runtime.textContent="Could not read "+file.name+": "+error.message;
    } finally {
      els.fileInput.value="";
    }
  });

  $$(".belly-cycle button").forEach(function(button){
    button.addEventListener("click",function(){
      const wanted=button.dataset.phase;
      const found=state.specimen.keys.findIndex(function(key){return phaseForKey(key)===wanted;});
      if(found>=0) gotoKey(found);
    });
  });

  window.addEventListener("keydown",function(event){
    const tag=(document.activeElement && document.activeElement.tagName || "").toLowerCase();
    if(tag==="input" || tag==="textarea") return;
    if(event.code==="Space"){event.preventDefault();togglePlay();}
    else if(event.key==="ArrowLeft") gotoKey(state.index-1);
    else if(event.key==="ArrowRight") gotoKey(state.index+1);
    else if(event.key==="Home") gotoKey(0);
    else if(event.key==="End") gotoKey(state.specimen.keys.length-1);
    else if(event.key.toLowerCase()==="t"){state.showTruth=!state.showTruth;setPressed(els.truth,state.showTruth);}
    else if(event.key.toLowerCase()==="f"){state.showForce=!state.showForce;setPressed(els.force,state.showForce);}
    else if(event.key.toLowerCase()==="a"){els.asciiToggle.click();}
    else if(event.key.toLowerCase()==="r"){state.startedAt=performance.now();gotoKey(0);}
  });
}

function drawRose(now) {
  const dims=resizeCanvas(els.rose);
  const ctx=dims.ctx,w=dims.width,h=dims.height;
  ctx.clearRect(0,0,w,h);
  const cx=w*.5,cy=h*.36;
  const radius=Math.min(w,h)*.27;
  const t=reduceMotion?0:now*.00004;

  const halo=ctx.createRadialGradient(cx,cy,0,cx,cy,radius*1.6);
  halo.addColorStop(0,"rgba(185,47,72,.11)");
  halo.addColorStop(.45,"rgba(111,74,168,.08)");
  halo.addColorStop(1,"rgba(0,0,0,0)");
  ctx.fillStyle=halo;
  ctx.fillRect(0,0,w,h);

  ctx.save();
  ctx.translate(cx,cy);
  ctx.rotate(t);
  for(let ring=0;ring<5;ring++){
    const r=radius*(.25+ring*.18);
    ctx.strokeStyle="rgba(240,191,103,"+(0.08+ring*.025)+")";
    ctx.lineWidth=1;
    ctx.beginPath();
    ctx.arc(0,0,r,0,Math.PI*2);
    ctx.stroke();
  }
  for(let i=0;i<24;i++){
    const a=i*Math.PI*2/24;
    const inner=radius*.18;
    const outer=radius*(i%2?1:.88);
    ctx.beginPath();
    ctx.moveTo(Math.cos(a)*inner,Math.sin(a)*inner);
    ctx.lineTo(Math.cos(a)*outer,Math.sin(a)*outer);
    ctx.strokeStyle=i%3===0?"rgba(185,47,72,.2)":"rgba(240,191,103,.12)";
    ctx.stroke();
  }
  for(let i=0;i<12;i++){
    const a=i*Math.PI*2/12;
    const r=radius*.63;
    ctx.beginPath();
    ctx.moveTo(Math.cos(a-.11)*r,Math.sin(a-.11)*r);
    ctx.lineTo(Math.cos(a)*radius*.93,Math.sin(a)*radius*.93);
    ctx.lineTo(Math.cos(a+.11)*r,Math.sin(a+.11)*r);
    ctx.closePath();
    ctx.fillStyle=i%2?"rgba(111,74,168,.07)":"rgba(185,47,72,.07)";
    ctx.fill();
  }
  ctx.restore();
}

function frame(now) {
  drawRose(now);
  renderMotion(now);
  requestAnimationFrame(frame);
}

function init() {
  setPressed(els.truth,state.showTruth);
  setPressed(els.force,state.showForce);
  setPressed(els.trails,state.showTrails);
  setPressed(els.asciiToggle,state.showAscii);
  els.play.textContent=state.playing?"PAUSE":"PLAY";
  renderLaneFilters();
  renderSpecimenGrid();
  bindEvents();
  updateSpecimenUI();
  const first=SPECIMENS.find(function(s){return s.id==="v2-strikes-025-rear-clearance-gates-commit-step-debt";}) || SPECIMENS[0];
  if(first) loadSpecimen(first,false);
  requestAnimationFrame(frame);
}

init();
