package com.homecenter.ritsucontrol;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import org.json.JSONObject;
import org.json.JSONArray;
import android.content.SharedPreferences;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/** One bounded, serialized sync engine PER foreground service instance.
 * Home Center owns the CONTROL chat. Android never sends worker jobs,
 * publishes staged material, handles Chrome capabilities or fabricates replies.
 */
final class HomeCenterSync implements AutoCloseable {
    static volatile String status = "Home Center not paired";
    private final Context app;
    private final ConversationLedger ledger;
    private final Runnable onChange;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ScheduledExecutorService queue =
            Executors.newSingleThreadScheduledExecutor(r -> {
                Thread thread=new Thread(r,"RitsuHomeCenterSync");
                thread.setDaemon(true);
                return thread;
            });
    private volatile boolean stopped;
    HomeCenterSync(Context context, ConversationLedger ledger, Runnable onChange) {
        this.app=context.getApplicationContext();
        this.ledger=ledger;
        this.onChange=onChange;
    }
    void start() {
        queue.scheduleWithFixedDelay(this::safeSync,0,1200,TimeUnit.MILLISECONDS);
    }
    void requestNow() {
        if(!stopped)queue.execute(this::safeSync);
    }
    private void safeSync() {
        if(stopped)return;
        try{syncOnce();}
        catch(Exception error){
            // Never report a queued network request as accepted by ChatGPT.
            // Show actionable failure details. Never include tokens, URLs
            // with credentials, or complete response bodies in status text.
            String detail=error.getMessage();
            if(detail==null)detail=error.getClass().getSimpleName();
            detail=detail.replaceAll("[^a-zA-Z0-9 _.:()/-]"," ");
            if(detail.length()>125)detail=detail.substring(0,125);
            status="Home Center send failed: "+detail;
            main.post(onChange);
        }
    }
    private void syncOnce() throws Exception {
        // Cloud-only release. The previous desktop relay code remains below
        // for migration archaeology, but is deliberately NOT called.
        // The existing Home Center cloud identity does not yet have a deployed
        // turn/feed API for Ritsu Control. Do not misroute queued messages.
        HomeCenterCloudPairing.Paired paired=HomeCenterCloudPairing.load(app);
        if(paired==null) {
            status="Home Center cloud not paired";
            return;
        }
        HomeCenterCloudPairing.Paired current=
            HomeCenterCloudPairing.refreshIfNeeded(app,paired);
        status=HomeCenterPlaywrightBridge.sync(app,ledger,current);
        main.post(onChange);
    }

    /** Home Center alone controls deterministic result publication.
     * Unreviewed secondary results and unpublished worker material cannot
     * appear in the endpoint, and the phone cannot request publication. */
    private int consumePublishedFeed(RitsuPairing.Pair paired) throws Exception {
        SharedPreferences state=app.getSharedPreferences("ritsu_sync_feed_v1",
                Context.MODE_PRIVATE);
        long cursor=state.getLong("cursor",0);
        JSONObject answer=exchange(paired,"GET",
                "/v1/ritsu/feed?after="+cursor,null);
        if(!answer.optBoolean("ok"))throw new IllegalStateException("Feed not verified");
        JSONArray events=answer.optJSONArray("events");
        if(events==null)throw new IllegalStateException("Published feed missing");
        int processed=0;
        for(int i=0;i<events.length();i++) {
            JSONObject row=events.optJSONObject(i);
            if(row==null)throw new IllegalStateException("Invalid published result");
            long sequence=row.optLong("sequence",-1);
            if(sequence<=cursor)throw new IllegalStateException("Feed out of order");
            String type=row.optString("type");
            String channel=row.optString("channel");
            String text=row.optString("text");
            if(text.trim().isEmpty()||text.length()>5000)
                throw new IllegalStateException("Published content invalid");
            if("chat_result".equals(type) && "control".equals(channel)) {
                String turnId=row.optString("turnId");
                if(!turnId.matches("[A-Za-z0-9_.:-]{8,100}"))
                    throw new IllegalStateException("Published control turn invalid");
                ledger.insertReplyOnce(turnId,text);
            } else if("chat_result".equals(type) && "dialogue".equals(channel)) {
                String turnId=row.optString("turnId");
                ledger.insertPublishedOnce("dialogue:"+turnId,"dialogue","Ritsu",text);
            } else if("worker_result".equals(type) && "worker".equals(channel)) {
                String resultId=row.optString("resultId");
                ledger.insertPublishedOnce("worker:"+resultId,"worker","Worker",text);
            } else {
                throw new IllegalStateException("Unapproved Home Center feed envelope");
            }
            // Commit monotonically AFTER the durable local message insertion.
            // A network failure can replay the same result without duplicates.
            if(!state.edit().putLong("cursor",sequence).commit())
                throw new IllegalStateException("Feed cursor not persisted");
            cursor=sequence;
            processed++;
            main.post(onChange);
        }
        return processed;
    }

    private void apply(String turnId, JSONObject receipt) {
        if(receipt==null)throw new IllegalStateException("Missing durable receipt");
        if(!turnId.equals(receipt.optString("turnId")) ||
                !"control".equals(receipt.optString("channel")))
            throw new IllegalStateException("Wrong Home Center conversation receipt");
        String state=receipt.optString("state");
        switch(state) {
            case "queued":
                ledger.updateState(turnId,"HOME_CENTER_QUEUED");break;
            case "leased":
                ledger.updateState(turnId,"HOME_CENTER_LEASED");break;
            case "dispatch_unknown":
            case "unknown":
                ledger.updateState(turnId,"HOME_CENTER_UNCERTAIN");break;
            case "failed":
                ledger.updateState(turnId,"HOME_CENTER_FAILED");break;
            case "completed":
                JSONObject result=receipt.optJSONObject("result");
                if(result==null||result.optString("text").trim().isEmpty())
                    throw new IllegalStateException("Completed without verified text");
                ledger.insertReplyOnce(turnId,result.optString("text"));
                ledger.updateState(turnId,"COMPLETED");
                break;
            default:throw new IllegalStateException("Unrecognized receipt state");
        }
        main.post(onChange);
    }

    /** No redirects, no arbitrary hosts. Pairing validates tailnet 100.64/10
     * and port 19645; all requests stay inside WireGuard Tailscale VPN.
     * A successful HTTP response only proves Home Center intake/readback.
     */
    private static JSONObject exchange(RitsuPairing.Pair paired,String method,
                                       String path,JSONObject payload) throws Exception {
        URL url=new URL(paired.origin+path);
        HttpURLConnection conn=(HttpURLConnection)url.openConnection();
        conn.setInstanceFollowRedirects(false);
        conn.setConnectTimeout(3200);
        conn.setReadTimeout(5200);
        conn.setRequestMethod(method);
        conn.setRequestProperty("Authorization","Bearer "+paired.token);
        conn.setRequestProperty("Accept","application/json");
        conn.setRequestProperty("Cache-Control","no-store");
        if(payload!=null) {
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type","application/json");
        }
        try {
            if(payload!=null) {
                byte[] bytes=payload.toString().getBytes(StandardCharsets.UTF_8);
                if(bytes.length>6500)throw new IllegalArgumentException("message oversized");
                conn.setFixedLengthStreamingMode(bytes.length);
                try(OutputStream output=conn.getOutputStream()){output.write(bytes);}
            }
            int code=conn.getResponseCode();
            if(code==401)throw new IllegalStateException("Device pairing unauthorized");
            if(code==409)throw new IllegalStateException("Turn ID collision");
            if(code<200||code>299)throw new IllegalStateException("Gateway HTTP "+code);
            try(InputStream stream=conn.getInputStream()){
                ByteArrayOutputStream buffer=new ByteArrayOutputStream();
                byte[] chunk=new byte[2048];
                int read;
                while((read=stream.read(chunk))!=-1) {
                    if(buffer.size()+read>100000)
                        throw new IllegalStateException("Gateway reply too large");
                    buffer.write(chunk,0,read);
                }
                return new JSONObject(buffer.toString(StandardCharsets.UTF_8.name()));
            }
        } finally {conn.disconnect();}
    }
    @Override public void close() {
        stopped=true;
        queue.shutdownNow();
    }
}
