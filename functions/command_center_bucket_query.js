'use strict';
function scopeBucketQuery(collectionRef,{ownerKey='',projectId=''}={}){
  let query=collectionRef;
  if(ownerKey) query=query.where('ownerKey','==',ownerKey);
  if(projectId) query=query.where('projectId','==',projectId);
  return query;
}
function compareBucketObjects(a,b){
  return Number(b?.updatedAtMs||0)-Number(a?.updatedAtMs||0) || String(a?.objectId||'').localeCompare(String(b?.objectId||''));
}
module.exports={scopeBucketQuery,compareBucketObjects};
