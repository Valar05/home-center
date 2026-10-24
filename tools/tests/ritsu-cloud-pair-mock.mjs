// Deterministic offline fake HOME CENTER CLOUD for Termux pairing client tests.
import assert from 'node:assert/strict';
let seenStatus=0;
const ok=(value)=>new Response(JSON.stringify({ok:true,...value}),{status:200,headers:{'content-type':'application/json'}});
globalThis.fetch=async(url,opts={})=>{
  assert.equal(String(url).startsWith('https://us-central1-home-center-dclar.cloudfunctions.net/'),true);
  const path=new URL(String(url)).pathname;
  const auth=opts.headers?.Authorization||'';
  if(path==='/termuxHubTools'){
    assert.match(auth,/^Bearer test_[A-Za-z0-9]+$/);
    return ok({mcpUrl:'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp'});
  }
  if(path==='/termuxPairingApproveHub'){
    assert.match(auth,/^Bearer test_[A-Za-z0-9]+$/);
    const b=JSON.parse(opts.body);
    assert.equal(b.pairingId,'TEST_REAL_RITSU_ID_123456');
    assert.equal(b.code,'023456');
    return ok({status:'approved',clientKind:'ritsu-control-android'});
  }
  if(path==='/termuxPairingStatusHub'){
    assert.match(auth,/^Bearer test_[A-Za-z0-9]+$/);
    const b=JSON.parse(opts.body);
    assert.equal(b.pairingId,'TEST_REAL_RITSU_ID_123456');
    seenStatus++;
    return ok({status:seenStatus>=2?'claimed':'approved',claimed:seenStatus>=2});
  }
  if(path==='/termuxTokenRefresh')
    throw Error('unexpected_test_refresh');
  throw Error('unexpected_cloud_route_'+path);
};
