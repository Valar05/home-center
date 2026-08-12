#!/usr/bin/env node
'use strict';

import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
const { chooseNextAction, assessHandoff }=require('../functions/fortress_v2');

const shadows=[
  {
    id:'chromium-throne-runtime-boundary',
    source:'PR #237 Add bare-metal Chromium Throne with mobile command surface',
    mission:{
      id:'shadow-chromium-throne',
      outcome:'install and physically accept Chromium Throne on the actual desktop',
      owner:'Drew Clarke',
      lane:'actual Windows desktop installation lane',
      deliverySurface:'installed Chromium Throne desktop runtime',
      evidenceStandard:'health plus phone surface plus real ChatGPT profile runtime proof',
      exclusions:['do not call repository implementation physical acceptance'],
      constraints:['one-time user-owned sign-in/UAC may require direct operator input'],
      corrections:[],
      requiredLookups:['current source delivery status'],
      completedLookups:['current source delivery status'],
      sourceConfidence:'verified',
      state:'implemented',
      artifacts:[{kind:'implementation',persistent:true}],
      nextActions:[{name:'install on actual desktop and collect runtime receipts',safe:true,authorized:true}],
    },
    expected:{type:'produce_evidence',value:'tested',completion:false},
  },
  {
    id:'venice-cli-runtime-boundary',
    source:'PR #230 Add canonical local Venice CLI',
    mission:{
      id:'shadow-venice-cli',
      outcome:'physically accept canonical Venice CLI on THECAULDRON',
      owner:'Drew Clarke',
      lane:'THECAULDRON local Venice runtime lane',
      deliverySurface:'installed venice CLI on THECAULDRON',
      evidenceStandard:'doctor plus one-shot exact speech plus two-turn thread continuity plus no-cloud fallback proof',
      exclusions:['do not claim cross-process resume without live reopen proof'],
      constraints:['speech remains local-venice','Computer Hands body actions remain separate'],
      corrections:[],
      requiredLookups:['current PR acceptance boundary'],
      completedLookups:['current PR acceptance boundary'],
      sourceConfidence:'verified',
      state:'implemented',
      artifacts:[{kind:'implementation',persistent:true}],
      nextActions:[{name:'run physical Venice CLI acceptance',safe:true,authorized:true}],
    },
    expected:{type:'produce_evidence',value:'tested',completion:false},
  },
  {
    id:'offline-continue-evidence-boundary',
    source:'PR #225 Offline Continue coding lane with judgement jars',
    mission:{
      id:'shadow-offline-continue',
      outcome:'prove useful coding capability on the Windows workstation while public internet is unavailable',
      owner:'Drew Clarke',
      lane:'bounded local Continue plus Ollama workstation lane',
      deliverySurface:'accepted offline coding runtime on workstation',
      evidenceStandard:'fresh workstation receipt from offline acceptance probe with constrained real edit',
      exclusions:['do not substitute repository state for workstation behavior'],
      constraints:['no cloud fallback'],
      corrections:[],
      requiredLookups:['current PR evidence status'],
      completedLookups:['current PR evidence status'],
      sourceConfidence:'verified',
      state:'implemented',
      artifacts:[{kind:'implementation',persistent:true}],
      nextActions:[{name:'execute offline workstation acceptance probe',safe:true,authorized:true}],
    },
    expected:{type:'produce_evidence',value:'tested',completion:false},
  },
];

for(const shadow of shadows){
  const action=chooseNextAction(shadow.mission);
  const handoff=assessHandoff(shadow.mission);
  assert.equal(action.type,shadow.expected.type,`${shadow.id}: wrong action`);
  assert.equal(action.value,shadow.expected.value,`${shadow.id}: wrong evidence target`);
  assert.equal(handoff.completionClaimAllowed,shadow.expected.completion,`${shadow.id}: completion laundering`);
}

const receipt={
  kind:'fortress.online.v2.shadow-acceptance.v1',
  shadowCount:shadows.length,
  allPassed:true,
  nonDestructive:true,
  missions:shadows.map(s=>({id:s.id,source:s.source,action:chooseNextAction(s.mission),completionClaimAllowed:assessHandoff(s.mission).completionClaimAllowed})),
};
process.stdout.write(JSON.stringify(receipt,null,2)+'\n');

export { shadows };
