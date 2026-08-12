'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {appendEvent,readEvents,reduce,nextAction,snapshotFromLog}=require('./fortress_v3_event_kernel');

function tmp(){const d=fs.mkdtempSync(path.join(os.tmpdir(),'fortress-v3-'));return path.join(d,'events.ndjson');}

test('append-only log is idempotent by event id',()=>{const f=tmp();const e={id:'evt-fixed',type:'campaign.activate',campaignId:'alpha',timestamp:'2026-08-12T00:00:00Z',source:'test'};assert.equal(appendEvent(f,e).appended,true);assert.equal(appendEvent(f,e).appended,false);assert.equal(readEvents(f).length,1);});

test('campaign activation is explicit, never inferred from last mentioned noun',()=>{const s=reduce([{type:'campaign.activate',campaignId:'vlad'},{type:'user.input',campaignId:'chromium',text:'Chromium Throne also matters'}]);assert.equal(s.activeCampaignId,'vlad');assert.ok(s.unresolvedInputs.some(x=>x.campaignHint==='chromium'));});

test('correction updates both campaign and global precedent',()=>{const s=reduce([{type:'campaign.activate',campaignId:'vlad'},{type:'campaign.correction',campaignId:'vlad',text:'Do not narrate an available body; dispatch into it.'}]);assert.ok(s.campaigns.vlad.corrections.includes('Do not narrate an available body; dispatch into it.'));assert.ok(s.global.corrections.includes('Do not narrate an available body; dispatch into it.'));});

test('receipt advances only its named boundary',()=>{const s=reduce([{type:'campaign.activate',campaignId:'vlad'},{type:'campaign.boundary.set',campaignId:'vlad',data:{id:'deploy',requiresOperator:true,handoff:{command:'run me'}}},{type:'campaign.boundary.set',campaignId:'vlad',data:{id:'self-build',requiresOperator:false}},{type:'campaign.receipt',campaignId:'vlad',receipt:{ok:true,boundaryId:'deploy',summary:'vlad ready'}}]);assert.equal(s.campaigns.vlad.boundaries[0].satisfied,true);assert.equal(s.campaigns.vlad.boundaries[1].satisfied,false);assert.equal(nextAction(s).boundaryId,'self-build');assert.equal(nextAction(s).type,'execute');});

test('failed receipt never advances',()=>{const s=reduce([{type:'campaign.activate',campaignId:'vlad'},{type:'campaign.boundary.set',campaignId:'vlad',data:{id:'deploy',requiresOperator:true,handoff:{command:'run me'}}},{type:'campaign.receipt',campaignId:'vlad',receipt:{ok:false,boundaryId:'deploy',summary:'failed'}}]);assert.equal(s.campaigns.vlad.boundaries[0].satisfied,false);assert.equal(nextAction(s).type,'operator_handoff');});

test('model can misclassify input without corrupting truth',()=>{const s=reduce([{type:'campaign.activate',campaignId:'vlad'},{type:'user.input',text:'No update no learning',data:{modelGuess:'not-a-correction'}},{type:'campaign.correction',campaignId:'vlad',text:'No update no learning'},{type:'input.resolve',data:{eventId:'evt-does-not-exist'}}]);assert.ok(s.global.corrections.includes('No update no learning'));assert.equal(s.activeCampaignId,'vlad');});

test('full log reconstructs deterministic next handoff',()=>{const f=tmp();for(const e of [{type:'campaign.activate',campaignId:'vlad',source:'seed'},{type:'campaign.define',campaignId:'vlad',source:'seed',data:{objective:'Deploy Vlad then self-build'}},{type:'campaign.boundary.set',campaignId:'vlad',source:'seed',data:{id:'deploy-vlad-phone',description:'Deploy on Termux',requiresOperator:true,handoff:{shell:'sh',command:'bootstrap_minimum_vlad.sh',receipt:'readiness'}}},{type:'campaign.boundary.set',campaignId:'vlad',source:'seed',data:{id:'self-build',description:'Use Vlad to build itself',requiresOperator:false}}]) appendEvent(f,e);const a=snapshotFromLog(f);assert.equal(a.next.type,'operator_handoff');assert.equal(a.next.boundaryId,'deploy-vlad-phone');assert.equal(a.next.handoff.command,'bootstrap_minimum_vlad.sh');});
