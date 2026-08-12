import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { REPO_ROOT, CONFIG_PATH, REQUIRED_SKILL_DOCUMENTS, CORE_SKILLS, defaultSkillRoots, loadRuntimeConfig, walkSkillFiles, loadDiscoveredSkills, buildBootCapsule } from './fortress_online_v2_boot.mjs';

test('Phone Hands is mandatory core boot skill with full operation triplet',()=>{
  const p=CORE_SKILLS.find(x=>x.id==='phone-hands');
  assert.ok(p); assert.equal(p.required,true);
  assert.deepEqual(p.operations,['phone_hands.devices','phone_hands.enqueue','phone_hands.get']);
  assert.match(p.purpose,/Shizuku\/rish/);
});

test('canonical skill books are boot-required',()=>{
  assert.deepEqual(REQUIRED_SKILL_DOCUMENTS,['fortress-core','phone-runtime']);
  const c=buildBootCapsule();
  for(const id of REQUIRED_SKILL_DOCUMENTS){
    const skill=c.loadedSkills.find(x=>x.id===id && x.source==='SKILL.md');
    assert.ok(skill,`missing canonical skill ${id}`);
    assert.equal(skill.required,true);
    assert.ok(skill.content.length>100,`${id} is suspiciously empty`);
  }
});

test('runtime configuration telemetry is mandatory and enforces single handoff',()=>{
  const cfg=loadRuntimeConfig();
  assert.equal(cfg.path,CONFIG_PATH);
  assert.equal(cfg.value.operatorHandoff.maxExecutableHandoffsPerTurn,1);
  assert.equal(cfg.value.operatorHandoff.requireReceiptBeforeNextHandoff,true);
  assert.equal(cfg.value.operatorHandoff.forbidDownstreamCommandsBeforeReceipt,true);
  assert.ok(cfg.value.telemetry.incidents.some(x=>x.kind==='handoff_fanout'));
  const c=buildBootCapsule();
  assert.equal(c.kind,'fortress.online.v2.boot-capsule.v4');
  assert.equal(c.configurationTelemetry.sha256, cfg.sha256);
  assert.equal(c.configurationTelemetry.operatorHandoff.maxExecutableHandoffsPerTurn,1);
  assert.ok(c.loadedSkills.some(x=>x.id==='runtime-config' && x.required===true));
  assert.match(c.bootPrompt,/handoff_fanout/);
});

test('invalid handoff configuration fails boot instead of silently degrading',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'fortress-config-'));
  const p=path.join(root,'config.json');
  fs.writeFileSync(p,JSON.stringify({schema:'fortress.online.v2.config.v1',operatorHandoff:{maxExecutableHandoffsPerTurn:2,requireReceiptBeforeNextHandoff:true,forbidDownstreamCommandsBeforeReceipt:true}}));
  assert.throws(()=>loadRuntimeConfig(p),/FORTRESS_BOOT_INVALID_HANDOFF_POLICY/);
});

test('default boot roots always include repository root',()=>{
  assert.ok(defaultSkillRoots().includes(REPO_ROOT));
  assert.ok(defaultSkillRoots(['/tmp/example']).includes(REPO_ROOT));
});

test('boot discovers every nested SKILL.md rather than first match',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'fortress-skills-'));
  for(const rel of ['alpha/SKILL.md','nested/beta/SKILL.md','nested/deeper/gamma/SKILL.md']){
    const p=path.join(root,rel); fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,`# ${rel}\nBODY:${rel}\n`);
  }
  fs.writeFileSync(path.join(root,'nested','IGNORE.md'),'nope');
  const found=walkSkillFiles(root);
  assert.equal(found.length,3);
  const loaded=loadDiscoveredSkills([root]);
  assert.deepEqual(loaded.map(x=>x.id).sort(),['alpha','beta','gamma']);
  assert.ok(loaded.every(x=>x.sha256.length===64));
  assert.ok(loaded.every(x=>x.content.includes('BODY:')));
});

test('boot capsule contains actual discovered skill bodies, not metadata only',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'fortress-capsule-'));
  for(const id of REQUIRED_SKILL_DOCUMENTS){
    const p=path.join(root,id,'SKILL.md'); fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,`# ${id}\n${'BODY '.repeat(30)}\n`);
  }
  const marker='PHONE-HANDS-STYLE-SKILL-BODY-UNIQUE-MARKER';
  const p=path.join(root,'proof-skill','SKILL.md'); fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,`# Proof\n${marker}\n`);
  const c=buildBootCapsule({skillRoots:[root]});
  const proof=c.loadedSkills.find(x=>x.id==='proof-skill');
  assert.ok(proof); assert.match(proof.content,new RegExp(marker));
  assert.match(c.bootPrompt,new RegExp(marker));
  assert.equal(c.bootPromptSha256.length,64);
  assert.equal(c.phoneHands.required,true);
  assert.ok(c.loadedSkills.some(x=>x.id==='phone-hands' && x.source==='core-contract'));
});

test('default capsule includes every repository SKILL.md body exactly',()=>{
  const repoSkillFiles=walkSkillFiles(REPO_ROOT);
  const c=buildBootCapsule();
  assert.equal(c.discoveredSkillCount,repoSkillFiles.length);
  for(const file of repoSkillFiles){
    const expected=fs.readFileSync(file,'utf8');
    assert.ok(c.loadedSkills.some(x=>x.file===file && x.content===expected),`missing skill body ${file}`);
  }
});

test('missing configured roots do not drop repo scan or mandatory core contracts',()=>{
  const c=buildBootCapsule({skillRoots:['/definitely/not/a/real/skill/root']});
  assert.ok(c.skillRoots.includes(REPO_ROOT));
  assert.ok(c.loadedSkills.some(x=>x.id==='phone-hands'));
  assert.ok(c.loadedSkills.some(x=>x.id==='request-budget'));
  assert.equal(c.loadedSkillCount,c.loadedSkills.length);
});
