#!/data/data/com.termux/files/usr/bin/bash
# One-shot: Ritsu Control Android -> actual Home Center CLOUD via Termux login.
set -Eeuo pipefail
umask 077
CFG="$HOME/.config/home-center/codex-hub.json"
DEST="$HOME/.local/state/home-center/ritsu-cloud-pair"
mkdir -p "$DEST"; chmod 700 "$DEST"
RECEIPT="$DEST/latest.txt"
STATE=preflight
RID="ritsu-$(date -u +%Y%m%dT%H%M%SZ)"
emit(){
  local line="RITSU_CLOUD_PAIR run=$RID state=$STATE $*"
  printf '%s\n' "$line" | tee "$RECEIPT"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf %s "$line" | termux-clipboard-set >/dev/null 2>&1 || printf '%s\n' 'RITSU_PAIR_CLIPBOARD_UNAVAILABLE'
  else
    printf '%s\n' 'RITSU_PAIR_CLIPBOARD_UNAVAILABLE'
  fi
}
bad(){ STATE=blocked; emit "reason=$1"; exit 1; }
trap 'x=$?; if [ "$x" -ne 0 ] && [ "$STATE" != blocked ]; then STATE=blocked; emit "reason=unexpected_failure exit=$x"; fi' EXIT
if [ "$#" -gt 0 ] && { [ "$1" = --help ] || [ "$1" = -h ]; }; then
  printf '%s\n' 'Usage: bash tools/ritsu_cloud_pair_termux.sh [--auth-check | PAIRING_ID SIX_DIGIT_CODE]' \
    'Open Ritsu Control > More > Pair with Home Center (cloud).' \
    'Paste its pairing ID and six-digit code into Termux.' \
    'Uses the already authenticated HOME CENTER CLOUD Termux account, not the desktop or old Android app.'
  exit 0
fi
[ "$PREFIX" = /data/data/com.termux/files/usr ] || bad 'run_inside_Termux'
command -v node >/dev/null 2>&1 || bad 'Termux_nodejs_missing'
[ -r "$CFG" ] || bad 'existing_Home_Center_Termux_login_missing'
AUTH_CHECK=0
if [ "${1:-}" = '--auth-check' ]; then
  AUTH_CHECK=1
  ID='AUTH_CHECK_ONLY_123456'; CODE='000000'
elif [ "$#" -ge 2 ]; then
  ID="$1"; CODE="$2"
else
  [ -r /dev/tty ] || bad 'cannot_read_terminal_enter_id_and_code_as_args'
  printf '%s\n' 'Open Ritsu Control > More > Pair with Home Center (cloud).'
  printf 'Ritsu Control pairing ID: '
  IFS= read -r ID </dev/tty || bad 'id_input_cancelled'
  printf 'Six-digit approval code: '
  IFS= read -r CODE </dev/tty || bad 'code_input_cancelled'
fi
[[ "$ID" =~ ^[a-zA-Z0-9_-]{12,160}$ ]] || bad invalid_pairing_id
[[ "$CODE" =~ ^[0-9]{6}$ ]] || bad invalid_six_digit_code
STATE=authorizing
if [ "$AUTH_CHECK" = 1 ]; then
  emit 'mode=credential_preflight no_pairing_code_required=1'
else
  emit 'target=Home_Center_cloud_Ritsu_Control no_Windows=1'
fi
export RITSU_AUTH_CHECK="$AUTH_CHECK"
export HOME_CENTER_CODEX_CONFIG="$CFG"
if node --input-type=module - "$ID" "$CODE" <<'RITSU_NODE'
import fs from 'node:fs';
import path from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
const [id,code]=process.argv.slice(2);
const p=process.env.HOME_CENTER_CODEX_CONFIG;
const base='https://us-central1-home-center-dclar.cloudfunctions.net/';
const valid=new Set(['termuxHubTools','termuxTokenRefresh','termuxPairingApproveHub','termuxPairingStatusHub']);
const req=async(name,body,token)=>{
  if(!valid.has(name))throw Error('invalid_cloud_route');
  const controller=new AbortController();
  const clock=setTimeout(()=>controller.abort(),12000);
  try{
    const response=await fetch(base+name,{method:body?'POST':'GET',headers:{
      'Accept':'application/json','Cache-Control':'no-store',
      ...(body?{'Content-Type':'application/json'}:{}),
      ...(token?{'Authorization':'Bearer '+token}:{})
    },...(body?{body:JSON.stringify(body)}:{}),signal:controller.signal,redirect:'error'});
    let obj={};
    try{const raw=await response.text();if(raw.length>16000)throw Error('oversized');obj=JSON.parse(raw)}
    catch{throw Error('bad_cloud_response')}
    if(!response.ok||!obj.ok)throw Error('Home_Center_'+name+'_HTTP_'+response.status+'_'
      +String(obj.error||'rejected').replace(/[^A-Za-z0-9_]/g,'_').slice(0,45));
    return obj;
  }finally{clearTimeout(clock)}
};
let config;
try{config=JSON.parse(fs.readFileSync(p,'utf8'))}
catch{throw Error('existing_termux_login_invalid')}
if(config.gatewayBase&&config.gatewayBase!=='https://us-central1-home-center-dclar.cloudfunctions.net')
  throw Error('existing_termux_login_wrong_authority');
if(typeof config.refreshToken!=='string'||config.refreshToken.length<32)
  throw Error('existing_termux_refresh_missing');
let token=config.accessToken;
const refresh=async()=>{
  const r=await req('termuxTokenRefresh',{refreshToken:config.refreshToken},null);
  if(typeof r.access_token!=='string'||r.access_token.length<32)throw Error('refresh_response_invalid');
  token=config.accessToken=r.access_token;
  config.refreshToken=r.refresh_token||config.refreshToken;
  config.expiresAtMs=Date.now()+Number(r.expires_in||0)*1000;
  const temp=path.join(path.dirname(p),'.ritsu-refresh-'+process.pid+'.tmp');
  try{
    fs.writeFileSync(temp,JSON.stringify(config,null,2)+'\n',{mode:0o600,flag:'wx'});
    fs.renameSync(temp,p);fs.chmodSync(p,0o600);
  }finally{try{fs.unlinkSync(temp)}catch{}}
};
// Always try the server-verified access token first, even if the local
// expiration timestamp is stale. A 401 refresh is NOT proof that a still-
// live access token fails. Do not generate/guess or reveal credentials.
let tools=null;
if(typeof token==='string' && token.length>=32) {
  try{tools=await req('termuxHubTools',null,token)}
  catch(e){
    if(!String(e?.message||'').includes('termuxHubTools_HTTP_401'))
      throw e;
  }
}
if(!tools) {
  try {
    await refresh();
    tools=await req('termuxHubTools',null,token);
  }catch(e){
    if(String(e?.message||'').includes('HTTP_401')) {
      console.error('TERMUX_HOME_CENTER_SESSION=REAUTH_REQUIRED');
      console.error('Existing Home Center access and refresh credentials were rejected. The Ritsu pairing code was NOT sent.');
      console.error('Keep the saved login file intact; a new authenticated Home Center sign-in is required.');
      throw Error('home_center_termux_session_requires_reauthorization');
    }
    throw e;
  }
}
if(tools.mcpUrl!=='https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp')
  throw Error('wrong_home_center_cloud_authority');
console.log('EXISTING_HOME_CENTER_CLOUD_LOGIN_VALID=1');
if(process.env.RITSU_AUTH_CHECK==='1') {
  console.log('HOME_CENTER_LOGIN_PREFLIGHT=VALID');
  process.exit(0);
}
const approved=await req('termuxPairingApproveHub',{pairingId:id,code},token);
if(approved.status!=='approved'||approved.clientKind!=='ritsu-control-android')
  throw Error('cloud_did_not_confirm_approval');
console.log('RITSU_CLOUD_PAIR_APPROVED=1');
let claimed=false;
for(let i=0;i<24;i++){
  await delay(2500);
  const r=await req('termuxPairingStatusHub',{pairingId:id},token);
  if(r.claimed===true&&r.status==='claimed'){claimed=true;break}
  if(r.status!=='approved')throw Error('cloud_pairing_status_unexpected');
}
if(!claimed)throw Error('Ritsu_app_did_not_claim_pairing');
console.log('RITSU_CLOUD_PAIR_CLAIMED_BY_APP=1');
console.log('ANDROID_KEYSTORE_SAVE=check_Ritsu_Control_status');
RITSU_NODE
then
  if [ "$AUTH_CHECK" = 1 ]; then
    STATE=auth_valid
    emit 'Home_Center_credentials=valid no_Ritsu_code_consumed=1'
  else
    STATE=claimed
    emit 'cloud_claimed=1 app_local_keystore=verify_in_Ritsu_Control'
  fi
else
  bad 'cloud_approval_failed_or_Ritsu_app_not_claimed_see_error_above'
fi
