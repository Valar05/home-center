#!/usr/bin/env node
'use strict';

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const REQUIRED_SKILL_DOCUMENTS = Object.freeze(['fortress-core','phone-runtime']);

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
function defaultSkillRoots(extra=[]){ return uniq([REPO_ROOT,...extra].map(x=>path.resolve(x))); }
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
      if(e.isDirectory() && !['.git','node_modules'].includes(e.name)) stack.push(p);
      else if(e.isFile() && e.name.toLowerCase()==='skill.md') out.push(p);
    }
  }
  return out.sort();
}
function loadDiscoveredSkills(roots){
  const files=uniq(roots.flatMap(walkSkillFiles));
  return files.map(file=>{ const content=fs.readFileSync(file,'utf8'); return {id:path.basename(path.dirname(file)),file,sha256:sha256(content),content}; });
}
function renderCoreSkill(skill){
  const ops=skill.operations?.length?`\noperations: ${skill.operations.join(', ')}`:'';
  const inv=skill.invariants?.length?`\ninvariants:\n- ${skill.invariants.join('\n- ')}`:'';
  return `# CORE SKILL: ${skill.id}\nrequired: ${skill.required===true}\npurpose: ${skill.purpose}${ops}${inv}`;
}
function buildBootCapsule({skillRoots, extraSkills=[]}={}){
  const roots=skillRoots===undefined?defaultSkillRoots():defaultSkillRoots(skillRoots);
  const discovered=loadDiscoveredSkills(roots);
  const discoveredIds=new Set(discovered.map(x=>x.id));
  const requiredMissing=REQUIRED_SKILL_DOCUMENTS.filter(id=>!discoveredIds.has(id));
  const phone=CORE_SKILLS.find(x=>x.id==='phone-hands');
  if(!phone || !phone.operations?.includes('phone_hands.devices') || !phone.operations?.includes('phone_hands.enqueue') || !phone.operations?.includes('phone_hands.get')) requiredMissing.push('phone-hands-contract');
  if(requiredMissing.length) throw new Error(`FORTRESS_BOOT_MISSING_REQUIRED_SKILLS:${uniq(requiredMissing).join(',')}`);

  const loadedSkills=[
    ...CORE_SKILLS.map(skill=>({id:skill.id,source:'core-contract',required:true,sha256:sha256(renderCoreSkill(skill)),content:renderCoreSkill(skill)})),
    ...discovered.map(skill=>({...skill,source:'SKILL.md',required:REQUIRED_SKILL_DOCUMENTS.includes(skill.id)})),
    ...extraSkills.map(skill=>({id:skill.id||'extra',source:'extra',required:skill.required===true,sha256:sha256(String(skill.content||'')),content:String(skill.content||'')})),
  ];
  const bootPrompt=loadedSkills.map(skill=>`\n--- FORTRESS SKILL ${skill.id} | ${skill.source} | sha256:${skill.sha256} ---\n${skill.content}`).join('\n');
  return {
    kind:'fortress.online.v2.boot-capsule.v3',
    isolation:'fortress-online-v2',
    policy:'load every discovered SKILL.md content; canonical skill books are boot-required; never first-match and stop',
    skillRoots:roots,
    requiredSkillDocuments:REQUIRED_SKILL_DOCUMENTS,
    coreSkillCount:CORE_SKILLS.length,
    discoveredSkillCount:discovered.length,
    loadedSkillCount:loadedSkills.length,
    loadedSkills,
    bootPrompt,
    bootPromptSha256:sha256(bootPrompt),
    phoneHands:{required:true,operations:phone.operations,invariants:phone.invariants},
  };
}

const invokedAsScript=process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href;
if(invokedAsScript){
  const configured=splitRoots(process.env.FORTRESS_SKILL_ROOTS);
  const capsule=buildBootCapsule({skillRoots:configured});
  process.stdout.write(JSON.stringify(capsule,null,2)+'\n');
}

export { REPO_ROOT, REQUIRED_SKILL_DOCUMENTS, CORE_SKILLS, splitRoots, defaultSkillRoots, walkSkillFiles, loadDiscoveredSkills, buildBootCapsule };
