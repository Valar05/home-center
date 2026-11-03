package com.homecenter.ritsucontrol;

import android.content.Context;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;

/** Read-only, exact-ID reconciliation against the *entire* durable SSE journal.
 * No POST, no cursor mutation, no retry, no reset of local messages or pairing.
 * A separate explicit owner action may retry only after an exhaustive unchanged
 * journal proves the turn was never accepted by this server.
 */
final class RitsuTurnRecovery {
    static final class Result {
        int recovered, notAccepted, submitted, uncertain;
        String message(){return "Turn audit: " + recovered + " recovered, " + notAccepted
            + " not received, " + submitted + " accepted, " + uncertain + " unresolved";}
    }
    private static final class Remote {
        String type="",tab="",promptHash="",text="",hash="";
        int revision=0;
        boolean verified=false,seenAccepted=false;
    }
    private static String hash(String s) throws Exception {
        byte[] b=MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8));
        StringBuilder out=new StringBuilder();
        for(byte c:b)out.append(String.format(Locale.ROOT,"%02x",c&255));
        return out.toString();
    }
    private static HttpURLConnection get(RitsuPairing.Pair pair,String path,int readMs) throws Exception {
        String base=RitsuPairing.validateOrigin(pair.origin);
        if(!path.startsWith("/v1/ritsu/"))throw new SecurityException("unexpected reconciliation path");
        HttpURLConnection c=(HttpURLConnection)new URL(base+path).openConnection();
        c.setRequestMethod("GET");c.setInstanceFollowRedirects(false);
        c.setConnectTimeout(7000);c.setReadTimeout(readMs);c.setUseCaches(false);
        c.setRequestProperty("Authorization","Bearer "+pair.token);
        c.setRequestProperty("Cache-Control","no-store");
        return c;
    }
    private static long status(RitsuPairing.Pair pair) throws Exception {
        HttpURLConnection c=get(pair,"/v1/ritsu/status",9000);
        try{
            if(c.getResponseCode()!=200)throw new IllegalStateException("turn audit status HTTP "+c.getResponseCode());
            java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream();
            try(java.io.InputStream in=c.getInputStream()){
                byte[] b=new byte[512];int n;
                while((n=in.read(b))!=-1){
                    if(out.size()+n>2048)throw new IllegalStateException("turn audit status too large");
                    out.write(b,0,n);
                }
            }
            if(out.size()<2)throw new IllegalStateException("empty turn audit status");
            JSONObject o=new JSONObject(out.toString("UTF-8"));
            long count=o.optLong("seq",-1);
            if(!o.optBoolean("ok")||count<0||count>10000)
                throw new IllegalStateException("turn audit journal window unavailable");
            return count;
        }finally{c.disconnect();}
    }
    /** No user prompt is submitted. The server may append only a uniquely
     * verified browser reply for an ORIGINAL accepted immutable turn ID.
     * A 404 signals an older server; never enable a retry based on it.
     */
    private static boolean tryBrowserRecovery(RitsuPairing.Pair pair,ConversationLedger.Entry e) throws Exception {
        String url="/v1/ritsu/recover?turnId=" + java.net.URLEncoder.encode(e.id,"UTF-8")
            + "&tabId=" + java.net.URLEncoder.encode(e.tabId,"UTF-8")
            + "&promptSha256=" + hash(e.text);
        HttpURLConnection c=get(pair,url,48000);
        try {
            int code=c.getResponseCode();
            if(code==404) return false; // do not interpret old server as no remote turn
            if(code!=200)throw new IllegalStateException("upstream recovery HTTP " + code);
            java.io.ByteArrayOutputStream buffer=new java.io.ByteArrayOutputStream();
            try(java.io.InputStream in=c.getInputStream()) {
                byte[] part=new byte[512];int n;
                while((n=in.read(part))!=-1){
                    if(buffer.size()+n>2000)throw new IllegalStateException("upstream recovery receipt too large");
                    buffer.write(part,0,n);
                }
            }
            JSONObject remote=new JSONObject(buffer.toString("UTF-8"));
            if(!remote.optBoolean("ok"))throw new IllegalStateException("remote recovery receipt invalid");
            String state=remote.optString("state","");
            if(!("no_server_receipt".equals(state)||"already_complete".equals(state)||
                 "still_processing".equals(state)||"uncertain".equals(state)||"recovered".equals(state)))
                throw new IllegalStateException("remote recovery state unsupported");
            return !"no_server_receipt".equals(state);
        }finally{c.disconnect();}
    }
    static Result reconcile(Context context,ConversationLedger ledger,RitsuPairing.Pair pair) throws Exception {
        List<ConversationLedger.Entry> pending=new ArrayList<>();
        for(ConversationLedger.Entry entry:ledger.unsent()){
            if("LOCAL_UNCERTAIN".equals(entry.state)||"LOCAL_SUBMITTED".equals(entry.state)||"LOCAL_NOT_ACCEPTED".equals(entry.state))pending.add(entry);
        }
        Result result=new Result();if(pending.isEmpty())return result;
        if(pending.size()>100)throw new IllegalStateException("too many uncertain turns for bounded audit");
        // Reconcile the oldest first. This GET never enqueues a prompt or
        // changes the Android SSE cursor; the server's journal is re-read below.
        java.util.HashSet<String> endpointChecked=new java.util.HashSet<>();
        int checked=0;
        for(ConversationLedger.Entry e:pending){
            if(checked>=2)break;
            if(tryBrowserRecovery(pair,e))endpointChecked.add(e.id);
            checked++;
        }

        LinkedHashMap<String,ConversationLedger.Entry> local=new LinkedHashMap<>();
        for(ConversationLedger.Entry entry:pending)local.put(entry.id,entry);
        long count=status(pair),seen=0;
        HashMap<String,Remote> remote=new HashMap<>();
        HttpURLConnection stream=count==0?null:get(pair,"/v1/ritsu/events?after=0",9000);
        if(stream!=null)try{
            if(stream.getResponseCode()!=200)throw new IllegalStateException("turn audit replay HTTP "+stream.getResponseCode());
            try(BufferedReader reader=new BufferedReader(new InputStreamReader(stream.getInputStream(),StandardCharsets.UTF_8))){
                int total=0;
                while(seen<count){
                    String line=reader.readLine();
                    if(line==null)throw new IllegalStateException("turn audit truncated before snapshot");
                    total+=line.length();
                    if(total>18000000||line.length()>8000)throw new IllegalStateException("turn audit exceeded bound");
                    if(!line.startsWith("data: "))continue;
                    JSONObject e=new JSONObject(line.substring(6));
                    if(e.optLong("seq",-1)!=seen+1)throw new SecurityException("turn audit lost journal event");
                    seen++;
                    String id=e.optString("turnId","");
                    ConversationLedger.Entry owner=local.get(id);
                    if(owner==null)continue;
                    String tab=e.optString("tabId","");
                    if(!owner.tabId.equals(tab))throw new SecurityException("turn audit cross-tab identity mismatch");
                    Remote current=remote.get(id);
                    if(current==null){current=new Remote();current.tab=tab;remote.put(id,current);}
                    String type=e.optString("type","");
                    if("accepted".equals(type)){
                        String digest=e.optString("promptSha256","");
                        // The accepted SSE repair may relabel the historical empty
                        // partial seq14 as an accepted/no-text event. Its original
                        // accepted row (with prompt SHA) must already be present.
                        if(digest.isEmpty() && current.seenAccepted){current.type=type;continue;}
                        if(!digest.equals(hash(owner.text)))throw new SecurityException("turn audit prompt hash collision");
                        current.seenAccepted=true;current.promptHash=digest;
                    }else if("partial".equals(type)||"complete".equals(type)){
                        if(!current.seenAccepted)throw new SecurityException("turn audit reply without acceptance");
                        String text=e.optString("text","");int revision=e.optInt("revision",-1);
                        if(text.isEmpty()||text.length()>5000||revision<1||!hash(text).equals(e.optString("sha256","")))
                            throw new SecurityException("turn audit reply integrity invalid");
                        if("complete".equals(type)&&!e.optBoolean("verified"))
                            throw new SecurityException("turn audit reply not verified");
                        if(revision>=current.revision){current.text=text;current.hash=e.optString("sha256");
                            current.revision=revision;current.verified="complete".equals(type);}
                    }else if(!"uncertain".equals(type))throw new SecurityException("unknown turn audit event");
                    current.type=type;
                }
            }
        }finally{stream.disconnect();}
        if(seen!=count || status(pair)!=count)
            throw new IllegalStateException("turn audit changed during snapshot, no local changes");
        // All remote evidence is validated BEFORE any local state transition.
        for(ConversationLedger.Entry owner:pending){
            Remote item=remote.get(owner.id);
            if(item==null){
                if(endpointChecked.contains(owner.id)){ledger.updateState(owner.id,"LOCAL_NOT_ACCEPTED");result.notAccepted++;}
                else {ledger.updateState(owner.id,"LOCAL_UNCERTAIN");result.uncertain++;}
                continue;
            }
            if(item.verified){ledger.upsertStreamingReply(owner.id,item.text,item.revision,true);
                ledger.updateState(owner.id,"COMPLETED");result.recovered++;}
            else if("uncertain".equals(item.type)){
                ledger.updateState(owner.id,"LOCAL_UNCERTAIN");result.uncertain++;
            }else if(item.revision>0){ledger.upsertStreamingReply(owner.id,item.text,item.revision,false);
                ledger.updateState(owner.id,"LOCAL_SUBMITTED");result.submitted++;}
            else if(item.seenAccepted){ledger.updateState(owner.id,"LOCAL_SUBMITTED");result.submitted++;}
            else result.uncertain++;
        }
        return result;
    }
    private RitsuTurnRecovery(){}
}
