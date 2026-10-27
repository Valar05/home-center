package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Direct phone-to-laptop streaming on the private Tailscale VPN.
 * Neither Home Center's cloud identity nor Computer Hands is called.
 * Each POST uses the immutable phone turn ID. The server durably deduplicates.
 */
final class RitsuLocalSync implements AutoCloseable {
    static volatile String status = "Pair THECAULDRON over Tailscale";
    private final Context app;
    private final ConversationLedger ledger;
    private final Runnable onChange;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService input = Executors.newSingleThreadExecutor(r -> {
        Thread t=new Thread(r,"RitsuDirectSse");t.setDaemon(true);return t;
    });
    private final ExecutorService output = Executors.newSingleThreadExecutor(r -> {
        Thread t=new Thread(r,"RitsuDirectOutbox");t.setDaemon(true);return t;
    });
    private volatile boolean stopped;
    private volatile HttpURLConnection activeStream;

    RitsuLocalSync(Context ctx, ConversationLedger ledger,Runnable callback) {
        this.app=ctx.getApplicationContext();
        this.ledger=ledger;
        this.onChange=callback;
    }
    void start(){input.execute(this::receiveLoop);requestNow();}
    void requestNow(){if(!stopped)output.execute(this::sendPending);}
    private void updated(){main.post(onChange);}
    private void fail(Exception e){
        String detail=e.getMessage();
        if(detail==null)detail=e.getClass().getSimpleName();
        detail=detail.replaceAll("[^a-zA-Z0-9 _.:()/-]"," ");
        status="Direct link error: "+detail.substring(0,Math.min(105,detail.length()));
        updated();
    }
    private static HttpURLConnection connect(RitsuPairing.Pair pair,String suffix) throws Exception {
        String base=RitsuPairing.validateOrigin(pair.origin);
        if(!suffix.startsWith("/v1/ritsu/"))throw new SecurityException("Unexpected local route");
        HttpURLConnection c=(HttpURLConnection)new URL(base+suffix).openConnection();
        c.setInstanceFollowRedirects(false);
        c.setConnectTimeout(7000);
        c.setReadTimeout(12000);
        c.setUseCaches(false);
        c.setRequestProperty("Authorization","Bearer "+pair.token);
        c.setRequestProperty("Cache-Control","no-store");
        return c;
    }
    private static String json(InputStream stream) throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        byte[] buf=new byte[1024];int n;
        while((n=stream.read(buf))!=-1){
            if(out.size()+n>18000)throw new IllegalStateException("Response exceeds limit");
            out.write(buf,0,n);
        }
        return out.toString(StandardCharsets.UTF_8.name());
    }
    private void sendPending() {
        if(stopped)return;
        RitsuPairing.Pair p;
        try{p=RitsuPairing.load(app);}
        catch(RuntimeException error){fail(error);return;}
        if(p==null){status="Pair THECAULDRON to send";updated();return;}
        // Only local-campaign turns are eligible. Never replay legacy Home Center
        // outbox entries, and never resubmit an ambiguous previous submission.
        for(ConversationLedger.Entry e:ledger.unsent()){
            if(stopped)return;
            if(!"LOCAL_QUEUED".equals(e.state))continue;
            try{
                JSONObject payload=new JSONObject()
                    .put("turnId",e.id).put("tabId",e.tabId).put("text",e.text);
                byte[] raw=payload.toString().getBytes(StandardCharsets.UTF_8);
                if(raw.length>12000)throw new IllegalArgumentException("Message too long");
                // Persist ambiguity BEFORE network I/O. Retry only by explicit
                // reconciliation of the same immutable ID.
                ledger.updateState(e.id,"LOCAL_UNCERTAIN");
                HttpURLConnection c=connect(p,"/v1/ritsu/turn");
                try{
                    c.setRequestMethod("POST");
                    c.setRequestProperty("Content-Type","application/json");
                    c.setDoOutput(true);
                    c.setFixedLengthStreamingMode(raw.length);
                    try(OutputStream out=c.getOutputStream()){out.write(raw);}
                    int code=c.getResponseCode();
                    if(code!=200&&code!=202)throw new IllegalStateException("Laptop HTTP "+code);
                    JSONObject ack=new JSONObject(json(c.getInputStream()));
                    if(!ack.optBoolean("accepted")||!e.id.equals(ack.optString("turnId")))
                        throw new SecurityException("Turn receipt mismatch");
                    ledger.updateState(e.id,"LOCAL_SUBMITTED");
                    status="Sent to THECAULDRON · waiting for ChatGPT";
                    updated();
                }finally{c.disconnect();}
            }catch(Exception error){fail(error);return;}
        }
    }
    private static String digest(String value) throws Exception {
        byte[] bytes=MessageDigest.getInstance("SHA-256")
            .digest(value.getBytes(StandardCharsets.UTF_8));
        StringBuilder b=new StringBuilder();
        for(byte v:bytes)b.append(String.format(Locale.ROOT,"%02x",v&255));
        return b.toString();
    }
    private void accept(JSONObject event,SharedPreferences cursor) throws Exception {
        long seq=event.optLong("seq",-1);
        long previous=cursor.getLong("seq",0);
        if(seq<=previous)return;
        if(seq!=previous+1)throw new SecurityException("Lost SSE sequence");
        String type=event.optString("type"),turnId=event.optString("turnId");
        // The journal also contains canary/Termux turns from the same paired
        // device. Those are never displayed as fabricated app conversations.
        if(ledger.containsUserTurn(turnId)){
            if("accepted".equals(type)){
                ledger.updateState(turnId,"LOCAL_SUBMITTED");
                status="ChatGPT browser processing turn";
            }else if("partial".equals(type)||"complete".equals(type)){
                String text=event.optString("text","");
                int revision=event.optInt("revision",-1);
                if(text.isEmpty()||text.length()>5000||revision<1||
                   !digest(text).equals(event.optString("sha256")))
                    throw new SecurityException("Stream checksum or revision invalid");
                boolean complete="complete".equals(type);
                if(complete&&!event.optBoolean("verified"))
                    throw new SecurityException("Final reply not verified");
                ledger.upsertStreamingReply(turnId,text,revision,complete);
                if(complete){
                    ledger.updateState(turnId,"COMPLETED");
                    status="ChatGPT reply complete";
                }else status="ChatGPT responding · streaming";
            }else if("uncertain".equals(type)){
                ledger.updateState(turnId,"LOCAL_UNCERTAIN");
                status="ChatGPT result uncertain · not resending";
            }else throw new SecurityException("Unknown stream event");
        }
        // Persist sequence only AFTER the corresponding local reply is saved.
        if(!cursor.edit().putLong("seq",seq).commit())
            throw new IllegalStateException("Stream cursor could not persist");
        updated();
    }
    private void receiveLoop(){
        while(!stopped){
            try{
                RitsuPairing.Pair pair=RitsuPairing.load(app);
                if(pair==null){
                    status="Pair THECAULDRON over Tailscale";
                    updated();sleep(1500);continue;
                }
                SharedPreferences cursor=app.getSharedPreferences(
                    "ritsu_local_sse_cursor_v1",Context.MODE_PRIVATE);
                long seq=cursor.getLong("seq",0);
                HttpURLConnection c=connect(pair,"/v1/ritsu/events?after="+seq);
                activeStream=c;
                c.setReadTimeout(0);
                c.setRequestProperty("Accept","text/event-stream");
                int code=c.getResponseCode();
                if(code!=200)throw new IllegalStateException("Local SSE HTTP "+code);
                status="THECAULDRON connected · direct Tailscale";
                updated();requestNow();
                try(BufferedReader reader=new BufferedReader(
                        new InputStreamReader(c.getInputStream(),StandardCharsets.UTF_8))){
                    String line;
                    while(!stopped&&(line=reader.readLine())!=null){
                        if(line.startsWith("data: "))
                            accept(new JSONObject(line.substring(6)),cursor);
                    }
                }finally{c.disconnect();activeStream=null;}
            }catch(Exception error){if(!stopped)fail(error);}
            sleep(1500);
        }
    }
    private void sleep(long millis){
        try{Thread.sleep(millis);}catch(InterruptedException error){
            Thread.currentThread().interrupt();
        }
    }
    @Override public void close(){
        stopped=true;
        HttpURLConnection c=activeStream;
        if(c!=null)c.disconnect();
        input.shutdownNow();output.shutdownNow();
    }
}
