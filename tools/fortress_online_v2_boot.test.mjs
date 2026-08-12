import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { REPO_ROOT, CORE_SKILLS, defaultSkillRoots, walkSkillFiles, loadDiscoveredSkills, buildBootCapsule } from './fortress_online_v2_boot.mjs';

test('Phone Hands is mandatory core boot skill with full operation triplet',()=>{
  const p=CORE_SKILLS.find(x=>x.id==='phone-hands');
  assert.ok(p); assert.equal(p.required,true);
  assert.deepEqual(p.operations,['phone_hands.devices','phone_hands.enqueue','phone_hands.get']);
  assert.match(p.purpose,/Shizuku\/rish/);
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
  const marker='PHONE-HANDS-STYLE-SKILL-BODY-UNIQUE-MARKER';
  const p=path.join(root,'proof-skill','SKILL.md'); fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,`# Proof\n${marker}\n`);
  const c=buildBootCapsule({skillRoots:[root]});
  const proof=c.loadedSkills.find(x=>x.id==='proof-skill');
  assert.ok(proof); assert.match(proof.content,new RegExp(marker));
  assert.match(c.bootPrompt,new RegExp(marker));
  assert.equal(c.bootPromptSha256.length,64);
  assert.equal(c.phoneHands.required,true);
  assert.ok(c.loadedSkills.some(x=>x.id==='phone-hands' && x.source==='core'));
});

test('default capsule includes every repository SKILL.md body',()=>{
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
