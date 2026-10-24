package com.homecenter.ritsucontrol;
import android.content.Context;
import android.util.Base64;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import org.json.JSONObject;
import org.json.JSONArray;

/** Fixed Playwright transport over owner-authenticated Home Center MCP.
 * Dispatch uncertain is persisted before network write; never blind-replay.
 */
final class HomeCenterPlaywrightBridge {
    static final String PREF="ritsu_playwright_dispatch_v1";
    private static final String WORKER="windows-hands-01";
    private static final String LANE="lane-ritsu-playwright-phone";
    private static final String SCRIPT=
        "C:\\Users\\dclar\\AppData\\Local\\RitsuControlBridge\\ritsu_control_playwright_bridge.mjs";
    private static final String ROOT="C:\\Users\\dclar\\workspace\\home-center";
    private static final String PREFIX="RITSU_BROWSER_RECEIPT=";
    private HomeCenterPlaywrightBridge(){}
    static boolean enabled(Context app) {
        return app.getSharedPreferences(PREF,Context.MODE_PRIVATE).getBoolean("enabled",false);
    }
    static void enable(Context app,boolean value){
        if(!app.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit()
              .putBoolean("enabled",value).commit())
            throw new IllegalStateException("Playwright approval not persisted");
    }
    static String sync(Context app,ConversationLedger ledger,
                       HomeCenterCloudPairing.Paired paired) throws Exception {
        if(!enabled(app))return "Playwright delivery OFF; unsent messages stay local";
        List<ConversationLedger.Entry> entries=ledger.unsent();
        int active=0,uncertain=0,failed=0;
        for(ConversationLedger.Entry e:entries) {
            if("HOME_CENTER_FAILED".equals(e.state)){failed++;continue;}
            if(ConversationLedger.OUTBOX.equals(e.state)) {
                ledger.updateState(e.id,"HOME_CENTER_UNCERTAIN");
                JSONObject args=new JSONObject()
                    .put("requestId",requestId(e.id)).put("workerId",WORKER)
                    .put("laneId",LANE).put("action","shell.exec")
                    .put("arguments",new JSONObject()
                        .put("command",command(e)).put("workingDirectory",ROOT))
                    .put("approved",true).put("highRiskApproved",true);
                JSONObject record=operation(paired,"computer_hands.request.create",args)
                    .getJSONObject("result");
                if(!requestId(e.id).equals(record.optString("requestId"))||
                    !WORKER.equals(record.optString("workerId"))||
                    !"queued".equals(record.optString("status")))
                    throw new IllegalStateException("Computer Hands intake not verified");
                ledger.updateState(e.id,"HOME_CENTER_QUEUED");
                active++;
                // Preserve ordered turns: one fresh remote dispatch per pass.
                break;
            }
            if(e.state.startsWith("HOME_CENTER_")) {
                JSONObject record=operation(paired,"computer_hands.request.status",
                    new JSONObject().put("requestId",requestId(e.id)))
                    .getJSONObject("result");
                if(!requestId(e.id).equals(record.optString("requestId")))
                    throw new IllegalStateException("Computer Hands receipt wrong turn");
                switch(record.optString("status")) {
                    case "queued":
                        ledger.updateState(e.id,"HOME_CENTER_QUEUED");active++;break;
                    case "leased":case "running":
                        ledger.updateState(e.id,"HOME_CENTER_LEASED");active++;break;
                    case "completed":
                        applyCompleted(ledger,e,record);break;
                    case "failed":case "cancelled":case "expired":
                        ledger.updateState(e.id,"HOME_CENTER_FAILED");failed++;break;
                    default:
                        ledger.updateState(e.id,"HOME_CENTER_UNCERTAIN");uncertain++;break;
                }
            }
        }
        return "Playwright transport · "+active+" active · "+uncertain+
            " uncertain · "+failed+" failed";
    }
    private static String requestId(String turnId){
        if(turnId==null||!turnId.matches("[a-fA-F0-9-]{36}"))
            throw new IllegalArgumentException("Invalid UUID turn");
        return "ritsu.phone."+turnId;
    }
    private static String command(ConversationLedger.Entry e){
        if(!e.tabId.matches("[A-Za-z0-9_-]{4,80}"))
            throw new IllegalArgumentException("Unsafe tab ID");
        String encoded=Base64.encodeToString(
            e.text.getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP);
        if(encoded.length()>30000)throw new IllegalArgumentException("Message too long");
        return "node \""+SCRIPT+"\" --turn "+e.id+" --tab "+e.tabId+
            " --prompt-b64 "+encoded;
    }
    private static JSONObject operation(HomeCenterCloudPairing.Paired p,
                                        String operation,JSONObject args) throws Exception {
        if(!("computer_hands.request.create".equals(operation)||
             "computer_hands.request.status".equals(operation)))
            throw new SecurityException("Operation not allowed");
        JSONObject rpc=new JSONObject().put("jsonrpc","2.0").put("id",1)
            .put("method","tools/call").put("params",new JSONObject()
                .put("name","drive_operation").put("arguments",new JSONObject()
                    .put("operation",operation).put("args",args)));
        URL url=new URL(p.mcpUrl);
        if(!"https".equals(url.getProtocol())||
           !"us-central1-home-center-dclar.cloudfunctions.net".equals(url.getHost())||
           !"/homeCenterMcp/mcp".equals(url.getPath()))
            throw new SecurityException("Incorrect authenticated Home Center origin");
        HttpURLConnection c=(HttpURLConnection)url.openConnection();
        c.setInstanceFollowRedirects(false);
        c.setConnectTimeout(8000);c.setReadTimeout(18000);
        c.setUseCaches(false);c.setDoOutput(true);c.setRequestMethod("POST");
        c.setRequestProperty("Authorization","Bearer "+p.accessToken);
        c.setRequestProperty("Content-Type","application/json");
        c.setRequestProperty("Accept","application/json, text/event-stream");
        c.setRequestProperty("MCP-Protocol-Version","2025-06-18");
        c.setRequestProperty("Cache-Control","no-store");
        byte[] data=rpc.toString().getBytes(StandardCharsets.UTF_8);
        if(data.length>12000)throw new SecurityException("Request too large");
        try {
            c.setFixedLengthStreamingMode(data.length);
            try(OutputStream out=c.getOutputStream()){out.write(data);}
            int status=c.getResponseCode();
            if(status<200||status>=300)
                throw new IllegalStateException("Home Center MCP HTTP "+status);
            ByteArrayOutputStream sink=new ByteArrayOutputStream();
            try(InputStream in=c.getInputStream()){
                byte[] buffer=new byte[4096];int n;
                while((n=in.read(buffer))!=-1){
                    if(sink.size()+n>900000)
                        throw new IllegalStateException("MCP response oversized");
                    sink.write(buffer,0,n);
                }
            }
            String wire=sink.toString(StandardCharsets.UTF_8.name());
            JSONObject envelope;
            if(wire.trim().startsWith("{"))envelope=new JSONObject(wire);
            else {
                JSONObject observed=null;
                for(String line:wire.split("\\r?\\n"))
                    if(line.startsWith("data: ")){
                        JSONObject item=new JSONObject(line.substring(6));
                        if(item.has("id"))observed=item;
                    }
                if(observed==null)throw new IllegalStateException("MCP result missing");
                envelope=observed;
            }
            if(envelope.has("error"))
                throw new IllegalStateException("MCP operation rejected");
            JSONObject result=envelope.getJSONObject("result");
            if(result.optBoolean("isError"))
                throw new IllegalStateException("MCP operation error");
            JSONArray content=result.optJSONArray("content");
            if(content==null||content.length()==0)
                throw new IllegalStateException("MCP content missing");
            JSONObject payload=new JSONObject(content.getJSONObject(0).getString("text"));
            if(!operation.equals(payload.optString("operation"))||
               !payload.optBoolean("completed"))
                throw new IllegalStateException("MCP evidence invalid");
            return payload;
        }finally{c.disconnect();}
    }
    private static void applyCompleted(ConversationLedger ledger,
                                       ConversationLedger.Entry e,
                                       JSONObject record) throws Exception {
        JSONObject outcome=record.optJSONObject("result");
        if(outcome==null||!outcome.optBoolean("ok")||
           outcome.optInt("exitCode",-1)!=0)
            throw new IllegalStateException("Playwright exit not verified");
        String stdout=outcome.optString("stdout","");
        int at=stdout.lastIndexOf(PREFIX);
        if(at<0)throw new IllegalStateException("Playwright receipt missing");
        int start=at+PREFIX.length(),end=stdout.indexOf('\n',start);
        JSONObject reply=new JSONObject((end<0?stdout.substring(start):
            stdout.substring(start,end)).trim());
        String text=reply.optString("text","");
        if(!"chatgpt_reply".equals(reply.optString("kind"))||
           !reply.optBoolean("verified")||
           !"playwright-rendered-chatgpt-reply".equals(reply.optString("source"))||
           !e.id.equals(reply.optString("turnId"))||
           !e.tabId.equals(reply.optString("tabId"))||
           !reply.optString("url").startsWith("https://chatgpt.com/")||
           text.trim().isEmpty()||text.length()>5000||
           !sha256(text).equals(reply.optString("sha256")))
            throw new SecurityException("Unverified ChatGPT reply identity/hash");
        ledger.insertReplyOnce(e.id,text);
        ledger.updateState(e.id,"COMPLETED");
    }
    private static String sha256(String s) throws Exception {
        byte[] digest=MessageDigest.getInstance("SHA-256")
            .digest(s.getBytes(StandardCharsets.UTF_8));
        StringBuilder out=new StringBuilder();
        for(byte b:digest)out.append(String.format(java.util.Locale.ROOT,"%02x",b&255));
        return out.toString();
    }
}
