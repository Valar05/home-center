#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {SHE_RAW_COLLECTIONS, SHE_RAW_BRAIN_IDS, listBrainJars, handleBrainJar, runSheRawOperation, health} = require('../functions/she_raw_mcp');
const {SHE_RAW_SEED_CASES} = require('../corpus/she-raw/seed_cases.js');
class FakeDoc { constructor(store,id){this.store=store;this.id=id;} async get(){return {exists:Object.prototype.hasOwnProperty.call(this.store,this.id),id:this.id,data:()=>this.store[this.id]};} async set(data,opts={}){this.store[this.id]=opts.merge?{...(this.store[this.id]||{}),...data}:data;} }
class FakeQuery { constructor(store){this.store=store;} limit(){return this;} where(){return this;} async get(){return {forEach:(cb)=>Object.entries(this.store).forEach(([id,data])=>cb({id,data:()=>data})),docs:Object.entries(this.store).map(([id,data])=>({id,data:()=>data}))};} }
class FakeCollection extends FakeQuery { doc(id){return new FakeDoc(this.store,id);} }
class FakeFirestore { constructor(){this.data=new Map();} collection(name){if(!this.data.has(name))this.data.set(name,{});return new FakeCollection(this.data.get(name));} }
class FakeAdmin { constructor(){this.fs=new FakeFirestore();} firestore(){return this.fs;} }
delete process.env.OPENAI_API_KEY;
const admin=new FakeAdmin();
const token='test-token-for-tango';
const tokenHash=require('node:crypto').createHash('sha256').update(token).digest('hex');
await admin.firestore().collection('mcpOAuthAccessTokens').doc(tokenHash).set({email:'tester@example.com',expiresAtMs:Date.now()+60000});
const extra={requestInfo:{headers:{authorization:`Bearer ${token}`}}};
for(const seedCase of SHE_RAW_SEED_CASES)await admin.firestore().collection(SHE_RAW_COLLECTIONS.corpusCases).doc(seedCase.id).set(seedCase);
assert(SHE_RAW_BRAIN_IDS.includes('tango'));
assert(listBrainJars().some((brain)=>brain.brainId==='tango'&&brain.source==='she-raw-corpus'));
const tango=await handleBrainJar(admin,{brainId:'tango',conversationKey:'conv-tango-contract',projectKey:'home-center',commandState:'idle',boundedContext:'Mission Control watch: Tim is asleep, Drew has the phone, children need their experience curated, and the next operator needs a clean handoff. Do not invent additional duties.',question:'What must be carried now, and how does relief happen?'},extra);
assert.match(tango.invocation_id,/^srbrain_/);
assert.equal(tango.brain_id,'tango');
assert(tango.retrieved_cases.some((r)=>r.id==='sr_case_tango_humane_mission_control_001'));
assert.match(tango.preservation_action,/named duty|current owner|live state|retrieval path/i);
assert.match(tango.relief_handoff,/relief condition|transfer the watch/i);
assert.match(tango.non_sacrificial_boundary,/No person or agent is expendable|rotation|relief/i);
assert.doesNotMatch(tango.current_duty+JSON.stringify(tango.residue),/deploy|create a worker|new service/i);
const pumped=await runSheRawOperation(admin,extra,'brain.invoke',{brainId:'tango',conversationKey:'conv-tango-pump',projectKey:'home-center',commandState:'idle',boundedContext:'Preserve the current phone watch and define relief without inventing more work.',question:'Return the watch card.'});
assert.equal(pumped.result.brain_id,'tango');
assert.match(pumped.result.non_sacrificial_boundary,/not expendable|rotation|relief/i);
assert((await health(admin)).available_brain_ids.includes('tango'));
console.log('Tango brain contract test: OK');
