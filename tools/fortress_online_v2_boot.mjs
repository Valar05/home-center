#!/usr/bin/env node
'use strict';

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const CORE_SKILLS = Object.freeze([
  { id:'mission-kernel', required:true, purpose:'preserve outcome/owner/lane/exclusions/evidence/delivery' },
  { id:'tetsuya-judgement', required:true, purpose:'deterministic precedent and correction judgement' },
  { id:'motivated-continuation', required:true, purpose:'continue until direct operator input or verified completion' },
  { id:'authoritative-retrieval', required:true, purpose:'look up materially uncertain state before acting' },
  { id:'cumulative-context', required:true, purpose:'preserve all earlier non-conflicting locks and corrections' },
  { id:'evidence-truth', required:true, purpose:'separate requested/implemented/tested/deployed/callable/delivered/accepted' },
  { id:'request-budget', required:true, purpose:'plan first, cache reads, forbid blind retries and polling storms' },
  { id:'home-center-persistence', required:true, purpose:'persistent authoritative execution/evidence lane' },
  { id:'phone-hands', required:true, purpose:'ChatGPT -> Home Center -> phone relay -> primary-phone agent -> Shizuku/rish -> Android -> receipt', operations:['phone_hands.devices','phone_hands.enqueue','phone_hands.get'], invariants:['primary-phone receipt required','no desktop/GitHub/local-scratch substitution for phone proof'] },
  { id:'computer-hands', required:true, purpose:'bounded workstation body lane when the commissioned lane is desktop' },
  { id:'browser-nerve', required:true, purpose:'semantic browser/page body lane; separate from machine body' },
  { id:'venice-nerve', required:true, purpose:'local Venice speech/collaboration lane; speech remains separate from body actions' },
  { id:'local-code-continue', required:true, purpose:'local coding continuation when cloud inference is unavailable' },
]);

function sha256(text){ return crypto.createHash('sha256').update(text).digest('hex'); }
function uniq(xs){ return [...new Set(xs)]; }
function splitRoots(raw){ return uniq(String(raw||'').split(path.delimiter).map(x=>x.trim()).filter(Boolean)); }
function walkSkillFiles(root){
  const out=[];
  if(!fs.existsSync(root)) return out;
  const stack=[path.resolve(root)];
  while(stack.length){
    const cur=stack.pop();
    let entries=[];
    try { entries=fs.readdirSync(cur,{withFileTypes:true}); } catch { continue; }
    for(const e of entries){
      const p=path.join(cur,e.name);
      if(e.isDirectory()) stack.push(p);
      else if(e.isFile() && e.name.toLowerCase()==='skill.md') out.push(p);
    }
  }
  return out.sort();
}
function loadDiscoveredSkills(roots){
  const files=uniq(roots.flatMap(walkSkillFiles));
  return files.map(file=>{ const content=fs.readFileSync(file,'utf8'); return {id:path.basename(path.dirname(file)),file,sha256:sha256(content),content}; });
}
function buildBootCapsule({skillRoots=[], extraSkills=[]}={}){
  const discovered=loadDiscoveredSkills(skillRoots);
  const ids=new Set([...CORE_SKILLS.map(x=>x.id),...discovered.map(x=>x.id),...extraSkills.map(x=>x.id)]);
  const requiredMissing=CORE_SKILLS.filter(x=>x.required&&!ids.has(x.id)).map(x=>x.id);
  const phone=CORE_SKILLS.find(x=>x.id==='phone-hands');
  if(!phone || !phone.operations?.includes('phone_hands.devices') || !phone.operations?.includes('phone_hands.enqueue') || !phone.operations?.includes('phone_hands.get')) requiredMissing.push('phone-hands-contract');
  if(requiredMissing.length) throw new Error(`FORTRESS_BOOT_MISSING_REQUIRED_SKILLS:${uniq(requiredMissing).join(',')}`);
  return {
    kind:'fortress.online.v2.boot-capsule.v1',
    isolation:'fortress-online-v2',
    policy:'load every discovered SKILL.md; never first-match and stop',
    coreSkills:CORE_SKILLS,
    discoveredSkills:discovered.map(({content,...meta})=>meta),
    loadedSkillCount:CORE_SKILLS.length+discovered.length+extraSkills.length,
    phoneHands:{required:true,operations:phone.operations,invariants:phone.invariants},
    skillRoots:skillRoots.map(path.resolve),
  };
}

if(import.meta.url===`file://${process.argv[1]}`){
  const roots=splitRoots(process.env.FORTRESS_SKILL_ROOTS);
  const capsule=buildBootCapsule({skillRoots:roots});
  process.stdout.write(JSON.stringify(capsule,null,2)+'\n');
}

export { CORE_SKILLS, splitRoots, walkSkillFiles, loadDiscoveredSkills, buildBootCapsule };
