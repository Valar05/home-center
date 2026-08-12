'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {eventObject,snapshotObject,eventsFromListResult,snapshotFromGetResult,recoveryPlan,PROJECT_ID,EVENT_KIND,SNAPSHOT_KIND}=require('./fortress_v3_bucket_adapter');

test('event object is immutable/idempotent bucket write',()=>{const op=eventObject({id:'evt-1',type:'campaign.activate',campaignId:'vlad',timestamp:'2026-08-12T00:00:00Z',source:'chat'});assert.equal(op.operation,'bucket.put_object');assert.equal(op.args.objectId,'fortress_v3_evt-1');assert.equal(op.args.projectId,PROJECT_ID);assert.equal(op.args.kind,EVENT_KIND);assert.match(op.args.path,/memory\/past-logs\/fortress-v3\/evt-1\.json$/);assert.equal(JSON.parse(op.args.body).campaignId,'vlad');});

test('snapshot uses stable object id and condensed lane',()=>{const op=snapshotObject([{id:'evt-a',type:'campaign.activate',campaignId:'vlad',timestamp:'2026-08-12T00:00:00Z'}]);assert.equal(op.args.objectId,'fortress_v3_current_snapshot');assert.equal(op.args.kind,SNAPSHOT_KIND);const body=JSON.parse(op.args.body);assert.equal(body.state.activeCampaignId,'vlad');assert.equal(body.lastEventId,'evt-a');});

test('list response normalizes event order independent of bucket order',()=>{const mk=(id,t)=>({projectId:PROJECT_ID,kind:EVENT_KIND,tags:['fortress-v3'],body:JSON.stringify({id,type:'user.input',text:id,timestamp:t,source:'test'})});const events=eventsFromListResult({objects:[mk('evt-b','2026-08-12T00:00:02Z'),mk('evt-a','2026-08-12T00:00:01Z')]});assert.deepEqual(events.map(x=>x.id),['evt-a','evt-b']);});

test('snapshot parser rejects wrong object kind',()=>{assert.throws(()=>snapshotFromGetResult({object:{body:JSON.stringify({kind:'wrong'})}}),/BAD_SNAPSHOT/);});

test('recovery replays only tail after snapshot event',()=>{const baseEvents=[{id:'evt-1',type:'campaign.activate',campaignId:'vlad',timestamp:'2026-08-12T00:00:01Z'},{id:'evt-2',type:'campaign.boundary.set',campaignId:'vlad',timestamp:'2026-08-12T00:00:02Z',data:{id:'deploy',requiresOperator:true,handoff:{command:'bootstrap'}}}];const snap=JSON.parse(snapshotObject(baseEvents).args.body);const tailObj=eventObject({id:'evt-3',type:'campaign.receipt',campaignId:'vlad',timestamp:'2026-08-12T00:00:03Z',receipt:{ok:true,boundaryId:'deploy'}}).args;const result=recoveryPlan(snap,{objects:[tailObj]});assert.equal(result.replayed,1);assert.equal(result.state.campaigns.vlad.boundaries[0].satisfied,true);assert.equal(result.next.type,'verify_completion');});

test('missing snapshot replays available events from scratch',()=>{const objs=[eventObject({id:'evt-1',type:'campaign.activate',campaignId:'vlad',timestamp:'2026-08-12T00:00:01Z'}).args,eventObject({id:'evt-2',type:'campaign.boundary.set',campaignId:'vlad',timestamp:'2026-08-12T00:00:02Z',data:{id:'deploy',requiresOperator:false}}).args];const r=recoveryPlan(null,{objects:objs});assert.equal(r.replayed,2);assert.equal(r.next.type,'execute');});
