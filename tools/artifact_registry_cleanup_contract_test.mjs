#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
const policies=JSON.parse(fs.readFileSync(new URL('../ops/artifact_registry_cleanup.v1.json',import.meta.url),'utf8'));
assert.equal(Array.isArray(policies),true);
const deletion=policies.find((policy)=>policy.action?.type==='Delete');
const retention=policies.find((policy)=>policy.action?.type==='Keep');
assert.deepEqual(deletion?.condition,{tagState:'any',olderThan:'14d'});
assert.equal(retention?.mostRecentVersions?.keepCount,5);
assert.equal('packageNamePrefixes' in retention.mostRecentVersions,false);
assert.equal(policies.filter((policy)=>policy.action?.type==='Delete').length,1);
assert.equal(policies.filter((policy)=>policy.action?.type==='Keep').length,1);
console.log(JSON.stringify({ok:true,deleteAfter:'14d',keepMostRecentPerPackage:5}));
