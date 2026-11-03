package com.homecenter.ritsucontrol;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Handler;
import android.os.Looper;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** One deliberate owner-requested remote browser Stop. Never relabels a turn
 * stopped unless the existing paired service verifies the exact turn ID. */
final class RitsuRemoteStop {
    private static final Handler MAIN=new Handler(Looper.getMainLooper());
    static void request(Activity activity,ConversationLedger ledger,
                        ConversationLedger.Entry turn,Runnable redraw){
        final String id=turn.id,tab=turn.tabId;
        new Thread(()->{
            String message=null;boolean stopped=false;
            HttpURLConnection connection=null;
            try{
                RitsuPairing.Pair pair=RitsuPairing.load(activity);
                if(pair==null)throw new IllegalStateException("PAIRING_REQUIRED");
                String origin=RitsuPairing.validateOrigin(pair.origin);
                byte[] request=new JSONObject().put("turnId",id).put("tabId",tab)
                    .toString().getBytes(StandardCharsets.UTF_8);
                connection=(HttpURLConnection)new URL(origin+"/v1/ritsu/turn/stop").openConnection();
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(7000);connection.setReadTimeout(30000);
                connection.setUseCaches(false);connection.setRequestMethod("POST");
                connection.setRequestProperty("Authorization","Bearer "+pair.token);
                connection.setRequestProperty("Content-Type","application/json");
                connection.setDoOutput(true);
                connection.setFixedLengthStreamingMode(request.length);
                try(OutputStream out=connection.getOutputStream()){out.write(request);}
                int code=connection.getResponseCode();
                if(code!=200)throw new IllegalStateException("REMOTE_STOP_HTTP_"+code);
                ByteArrayOutputStream out=new ByteArrayOutputStream();
                try(InputStream in=connection.getInputStream()){
                    byte[] buf=new byte[1024];int n;
                    while((n=in.read(buf))!=-1){
                        if(out.size()+n>2048)throw new SecurityException("STOP_RECEIPT_OVERSIZED");
                        out.write(buf,0,n);
                    }
                }
                JSONObject result=new JSONObject(out.toString(StandardCharsets.UTF_8.name()));
                if(!result.optBoolean("stopped",false)||!id.equals(result.optString("turnId")))
                    throw new SecurityException("STOP_RECEIPT_NOT_VERIFIED");
                stopped=true;
            }catch(Exception e){
                message=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();
            }finally{if(connection!=null)connection.disconnect();}
            final boolean verified=stopped;
            final String error=message;
            MAIN.post(()->{
                if(verified){
                    ledger.updateState(id,"STOPPED");
                    RitsuControlService.feedRevision++;
                    redraw.run();
                }else{
                    new AlertDialog.Builder(activity).setTitle("Remote Stop unconfirmed")
                        .setMessage("No browser cancellation was confirmed. The original turn was preserved. " +
                            String.valueOf(error).replaceAll("[^a-zA-Z0-9 _.:/-]"," ").substring(0,
                            Math.min(110,String.valueOf(error).length())))
                        .setPositiveButton("OK",null).show();
                }
            });
        },"RitsuRemoteStopRequest").start();
    }
}
