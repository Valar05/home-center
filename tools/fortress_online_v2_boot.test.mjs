import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { CORE_SKILLS, walkSkillFiles, loadDiscoveredSkills, buildBootCapsule } from './fortress_online_v2_boot.mjs';

test('Phone Hands is mandatory core boot skill with full operation triplet',()=>{
  const p=CORE_SKILLS.find(x=>x.id==='phone-hands');
  assert.ok(p); assert.equal(p.required,true);
  assert.deepEqual(p.operations,['phone_hands.devices','phone_hands.enqueue','phone_hands.get']);
  assert.match(p.purpose,/Shizuku\/rish/);
});

test('boot discovers every nested SKILL.md rather than first match',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'fortress-skills-'));
  for(const rel of ['alpha/SKILL.md','nested/beta/SKILL.md','nested/deeper/gamma/SKILL.md']){
    const p=path.join(root,rel); fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,`# ${rel}\n`);
  }
  fs.writeFileSync(path.join(root,'nested','IGNORE.md'),'nope');
  const found=walkSkillFiles(root);
  assert.equal(found.length,3);
  const loaded=loadDiscoveredSkills([root]);
  assert.deepEqual(loaded.map(x=>x.id).sort(),['alpha','beta','gamma']);
  assert.ok(loaded.every(x=>x.sha256.length===64));
});

test('boot capsule carries all discovered skills plus core skills',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'fortress-capsule-'));
  for(const name of ['one','two']){const p=path.join(root,name,'SKILL.md');fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,`# ${name}\n`);}
  const c=buildBootCapsule({skillRoots:[root]});
  assert.equal(c.discoveredSkills.length,2);
  assert.equal(c.loadedSkillCount,CORE_SKILLS.length+2);
  assert.equal(c.phoneHands.required,true);
  assert.equal(c.policy,'load every discovered SKILL.md; never first-match and stop');
});

test('missing skill roots are tolerated without dropping mandatory core contracts',()=>{
  const c=buildBootCapsule({skillRoots:['/definitely/not/a/real/skill/root']});
  assert.equal(c.discoveredSkills.length,0);
  assert.ok(c.coreSkills.some(x=>x.id==='phone-hands'));
  assert.ok(c.coreSkills.some(x=>x.id==='request-budget'));
});
