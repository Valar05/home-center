#!/usr/bin/env node
'use strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url);
const {loadConfig}=require('../functions/fortress_v2_config');
const SCRIPT_DIR=path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT=path.resolve(SCRIPT_DIR,'..');
const HARD_REQUIRED_SKILL_DOCUMENTS=['venice-stop-gate'];
function sha256(text){return crypto.createHash('sha256').update(text).digest('hex');}
function uniq(xs){return [...new Set(xs)];}
function splitRoots(raw){return uniq(String(raw||'').split(path.delimiter).map(x=>x.trim()).filter(Boolean));}
function defaultSkillRoots(extra=[]){return uniq([REPO_ROOT,...extra].map(x=>path.resolve(x)));}
function walkSkillFiles(root,excluded=[]){const out=[];if(!fs.existsSync(root))return out;const deny=new Set(excluded);const stack=[path.resolve(root)];while(stack.length){const cur=stack.pop();let entries=[];try{entries=fs.readdirSync(cur,{withFileTypes:true});}catch{continue;}for(const e of entries){const p=path.join(cur,e.name);if(e.isDirectory()&&!deny.has(e.name))stack.push(p);else if(e.isFile()&&e.name.toLowerCase()==='skill.md')out.push(p);}}return out.sort();}
function loadDiscoveredSkills(roots,excluded=[]){const files=uniq(roots.flatMap(r=>walkSkillFiles(r,excluded)));return files.map(file=>{const content=fs.readFileSync(file,'utf8');return{id:path.basename(path.dirname(file)),file,sha256:sha256(content),content};});}
function renderCoreSkill(skill){const ops=skill.operations?.length?`\noperations: ${skill.operations.join(', ')}`:'';const inv=skill.invariants?.length?`\ninvariants:\n- ${skill.invariants.join('\n- ')}`:'';return `# CORE SKILL: ${skill.id}\nrequired: ${skill.required===true}\npurpose: ${skill.purpose}${ops}${inv}`;}
function buildBootCapsule({skillRoots,extraSkills=[],configOptions={}}={}){const loadedConfig=loadConfig(configOptions),config=loadedConfig.config,roots=skillRoots===undefined?defaultSkillRoots():defaultSkillRoots(skillRoots),discovered=config.boot.scanRepoSkills===false?[]:loadDiscoveredSkills(roots,config.boot.excludedDirectories||[]),ids=new Set(discovered.map(x=>x.id)),requiredSkillDocuments=uniq([...(config.boot.requiredSkillDocuments||[]),...HARD_REQUIRED_SKILL_DOCUMENTS]),requiredMissing=requiredSkillDocuments.filter(id=>!ids.has(id)),phone=config.skills.find(x=>x.id==='phone-hands');for(const op of ['phone_hands.devices','phone_hands.enqueue','phone_hands.get'])if(!phone?.operations?.includes(op))requiredMissing.push(`phone-hands:${op}`);if(requiredMissing.length)throw new Error(`FORTRESS_BOOT_MISSING_REQUIRED_SKILLS:${uniq(requiredMissing).join(',')}`);const loadedSkills=[...config.skills.map(skill=>({id:skill.id,source:'core-contract',required:skill.required===true,sha256:sha256(renderCoreSkill(skill)),content:renderCoreSkill(skill)})),...discovered.map(skill=>({...skill,source:'SKILL.md',required:requiredSkillDocuments.includes(skill.id)})),...extraSkills.map(skill=>({id:skill.id||'extra',source:'extra',required:skill.required===true,sha256:sha256(String(skill.content||'')),content:String(skill.content||'')}))],bootPrompt=loadedSkills.map(skill=>`\n--- FORTRESS SKILL ${skill.id} | ${skill.source} | sha256:${skill.sha256} ---\n${skill.content}`).join('\n');return{kind:config.boot.capsuleKind,configKind:config.kind,configVersion:config.version,configSha256:loadedConfig.sha256,configLayers:loadedConfig.layers,isolation:config.learning.isolation,policy:config.boot.policy,skillRoots:roots,requiredSkillDocuments,coreSkillCount:config.skills.length,discoveredSkillCount:discovered.length,loadedSkillCount:loadedSkills.length,loadedSkills,bootPrompt,bootPromptSha256:sha256(bootPrompt),phoneHands:{required:phone.required===true,operations:phone.operations,invariants:phone.invariants}};}
const invokedAsScript=process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href;if(invokedAsScript){const configured=splitRoots(process.env.FORTRESS_SKILL_ROOTS);process.stdout.write(JSON.stringify(buildBootCapsule({skillRoots:configured}),null,2)+'\n');}
export{REPO_ROOT,HARD_REQUIRED_SKILL_DOCUMENTS,splitRoots,defaultSkillRoots,walkSkillFiles,loadDiscoveredSkills,buildBootCapsule};
