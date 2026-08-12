'use strict';
const test=require('node:test');const assert=require('node:assert/strict');
const {scopeBucketQuery,compareBucketObjects}=require('./command_center_bucket_query');
test('query scopes owner then project before get',()=>{const calls=[];const q={where(f,o,v){calls.push([f,o,v]);return this;}};assert.equal(scopeBucketQuery(q,{ownerKey:'owner-a',projectId:'fortress-online-v3'}),q);assert.deepEqual(calls,[['ownerKey','==','owner-a'],['projectId','==','fortress-online-v3']]);});
test('query can scope owner without project',()=>{const calls=[];const q={where(f,o,v){calls.push([f,o,v]);return this;}};scopeBucketQuery(q,{ownerKey:'owner-a'});assert.deepEqual(calls,[['ownerKey','==','owner-a']]);});
test('sort is newest first with deterministic object id tie break',()=>{const x=[{objectId:'b',updatedAtMs:9},{objectId:'a',updatedAtMs:9},{objectId:'z',updatedAtMs:10}];x.sort(compareBucketObjects);assert.deepEqual(x.map(v=>v.objectId),['z','a','b']);});
