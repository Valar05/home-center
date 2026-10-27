'use strict';
const {createHash, timingSafeEqual} = require('node:crypto');

const fail=(code,status=400)=>Object.assign(new Error(code),{status,code});
const string=(x,max=160)=>typeof x==='string'?x.trim().slice(0,max):'';
const ID_RE=/^[A-Za-z0-9_-]{12,160}$/;
const CODE_RE=/^[0-9]{6}$/;
const normalizeEmail=e=>string(e,320).toLowerCase();
const sameCode=(code,stored)=>{
  if(!/^[a-f0-9]{64}$/.test(String(stored||'')))return false;
  const hash=createHash('sha256').update(code).digest();
  return timingSafeEqual(hash,Buffer.from(stored,'hex'));
};

async function ownerIdentity(admin,user){
  const email=normalizeEmail(user&&user.email);
  if(!email)throw fail('home_center_oauth_identity_missing',401);
  let firebase;
  try{firebase=await admin.auth().getUserByEmail(email)}
  catch(e){
    if(e&&e.code==='auth/user-not-found')throw fail('home_center_firebase_owner_not_registered',409);
    throw e;
  }
  if(!firebase||!firebase.uid||normalizeEmail(firebase.email)!==email)
    throw fail('home_center_identity_mapping_invalid',403);
  if(firebase.disabled)throw fail('home_center_owner_disabled',403);
  return {email,uid:firebase.uid};
}

async function runRitsuCloudPairMcp({admin,user,operation,args={}}){
  const owner=await ownerIdentity(admin,user);
  const p=string(args.pairingId);
  if(!ID_RE.test(p))throw fail('ritsu_pairing_id_invalid');
  const ref=admin.firestore().collection('termuxPairingRequests').doc(p);
  if(operation==='ritsu.cloud.pair.status'){
    const snap=await ref.get();
    if(!snap.exists)return {ok:false,state:'not_found'};
    const doc=snap.data()||{};
    if(doc.clientKind!=='ritsu-control-android')return {ok:false,state:'wrong_client'};
    if(doc.status==='pending')
      return {ok:true,state:Number(doc.expiresAtMs||0)>Date.now()?'pending':'expired'};
    if(doc.uid!==owner.uid||normalizeEmail(doc.email)!==owner.email)
      throw fail('ritsu_pairing_other_owner',403);
    return {ok:true,state:doc.status==='claimed'?'claimed':doc.status==='approved'?'approved':'closed',
      devicePaired:doc.status==='claimed',source:'home_center_cloud_firebase'};
  }
  if(operation!=='ritsu.cloud.pair.approve')throw fail('ritsu_pairing_operation_unknown');
  if(args.approved!==true)throw fail('explicit_pairing_approval_required',403);
  const code=string(args.code,20);
  if(!CODE_RE.test(code))throw fail('ritsu_six_digit_code_invalid');
  const requestId=string(args.requestId,160);
  if(!/^[A-Za-z0-9_.:-]{12,160}$/.test(requestId))throw fail('audit_request_id_required');
  const now=Date.now();
  const auditRef=admin.firestore().collection('ritsuCloudOAuthPairAudit').doc(requestId);
  const result=await admin.firestore().runTransaction(async tx=>{
    const [auditSnap,pairSnap]=await Promise.all([tx.get(auditRef),tx.get(ref)]);
    if(auditSnap.exists){
      const prev=auditSnap.data()||{};
      if(prev.uid!==owner.uid||prev.pairingId!==p)throw fail('audit_request_id_conflict',409);
      return {state:prev.state,idempotent:true};
    }
    if(!pairSnap.exists)throw fail('ritsu_pairing_not_found',404);
    const doc=pairSnap.data()||{};
    if(doc.status!=='pending'||Number(doc.expiresAtMs||0)<=now)
      throw fail('ritsu_pairing_expired_or_used',409);
    if(doc.clientKind!=='ritsu-control-android')
      throw fail('not_ritsu_control_android',403);
    if(!sameCode(code,doc.codeHash))
      throw fail('ritsu_pairing_code_rejected',403);
    const requested=Array.isArray(doc.requestedGroups)?doc.requestedGroups:[];
    // Home Center v0.10 requests these explicit groups. No scope escalation.
    if(requested.some(group=>!['drive','docs','github'].includes(group)))
      throw fail('ritsu_pairing_scope_rejected',403);
    if(!requested.length)throw fail('ritsu_pairing_scope_empty',409);
    const entry={status:'approved',approvedAtMs:now,uid:owner.uid,email:owner.email,
      allowedGroups:Array.from(new Set(requested)),clientId:'ritsu-control-'+p,
      approvalSource:'home_center_mcp_oauth_owner'};
    tx.update(ref,entry);
    tx.create(auditRef,{uid:owner.uid,email:owner.email,pairingId:p,
      atMs:now,clientKind:'ritsu-control-android',state:'approved',groups:entry.allowedGroups});
    return {state:'approved',idempotent:false};
  });
  return {ok:true,state:result.state,idempotent:result.idempotent,
    cloudApprovalRecorded:result.state==='approved',devicePaired:false,
    next:'Keep Ritsu Control open until it claims the approval; check status for claimed.'};
}
module.exports={runRitsuCloudPairMcp};
