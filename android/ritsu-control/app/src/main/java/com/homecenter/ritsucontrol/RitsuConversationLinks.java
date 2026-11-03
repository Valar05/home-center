package com.homecenter.ritsucontrol;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.widget.EditText;
import android.os.Handler;
import android.os.Looper;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;

/** Browser-based READ-ONLY discovery; explicit owner-selected exact URL binding.
 * All server operations use existing direct-pairing bearer authorization. */
final class RitsuConversationLinks {
    private static final ExecutorService NETWORK=Executors.newSingleThreadExecutor(r->{
        Thread t=new Thread(r,"RitsuCatalog");t.setDaemon(true);return t;});
    private static final Handler MAIN=new Handler(Looper.getMainLooper());
    private static final String PREF="ritsu_linked_chats_v1";
    private RitsuConversationLinks(){}
    static boolean blocked(Activity a,String id){
        String state=a.getSharedPreferences(PREF,Activity.MODE_PRIVATE).getString("state_"+id,"");
        return "PENDING".equals(state)||"FAILED".equals(state);
    }
    static void discover(Activity a,RitsuConversationDeck deck,RitsuWorkspace workspace,Runnable onChange){
        NETWORK.execute(()->{
            try{
                JSONObject response=request(a,"GET","/v1/ritsu/catalog",null);
                JSONArray chats=response.optJSONArray("chats");
                if(!response.optBoolean("verified",false)||chats==null)
                    throw new IllegalStateException("Unverified catalog; no changes made");
                ArrayList<String> titles=new ArrayList<>(),urls=new ArrayList<>();
                for(int i=0;i<chats.length();i++){
                    JSONObject c=chats.optJSONObject(i);if(c==null)continue;
                    String url=canonical(c.optString("url"));if(url==null)continue;
                    if(!c.optBoolean("nonProjectVerified",false))continue;
                    String title=c.optString("title","ChatGPT conversation").trim();
                    if(title.isEmpty())title="ChatGPT conversation";
                    titles.add(title.length()>70?title.substring(0,70):title);urls.add(url);
                }
                MAIN.post(()->new AlertDialog.Builder(a).setTitle("Recent non-project chats")
                    .setItems(titles.toArray(new String[0]),(d,n)->bindUrl(a,deck,workspace,onChange,urls.get(n),titles.get(n)))
                    .setPositiveButton("Add URL",(d,w)->addUrl(a,deck,workspace,onChange))
                    .setNegativeButton("Close",null).show());
            }catch(Exception error){MAIN.post(()->deck.error("Discovery unavailable: "+coarse(error)+". Use Add URL; existing conversations are preserved."));}
        });
    }
    static void addUrl(Activity a,RitsuConversationDeck deck,RitsuWorkspace workspace,Runnable onChange){
        EditText field=new EditText(a);field.setSingleLine(true);field.setHint("https://chatgpt.com/c/...");
        new AlertDialog.Builder(a).setTitle("Link existing ChatGPT chat").setView(field)
            .setPositiveButton("Verify and add",(d,w)->bindUrl(a,deck,workspace,onChange,field.getText().toString(),"Linked chat"))
            .setNegativeButton("Cancel",null).show();
    }
    private static String canonical(String value){
        // RITSU_V135_CANONICAL_LOCAL_URL: accept the *exact* browser URL as a candidate.
        // The authenticated laptop must still prove it is a writable, same-account chat.
        if(value==null||!value.matches("https://chatgpt\\.com/c/(?:[A-Za-z0-9-]{8,120}|local-chatgpt%3[Aa][0-9A-Fa-f-]{36})/?"))return null;

        if(value.endsWith("/"))return value.substring(0,value.length()-1);
        return value;
    }
    private static String coarse(Exception e){
        if(e instanceof java.net.SocketTimeoutException)return "TIMEOUT";
        if(e instanceof java.net.ConnectException)return "LAPTOP_UNREACHABLE";
        String message=e.getMessage();
        if(message!=null){
            if(message.startsWith("CATALOG_HTTP_"))return message;
            if(message.contains("PAIRING_REQUIRED"))return "PAIRING_REQUIRED";
            if(message.contains("Unverified catalog"))return "CATALOG_NOT_VERIFIED";
        }
        return e.getClass().getSimpleName();
    }
    static void bindUrl(Activity a,RitsuConversationDeck deck,RitsuWorkspace work,Runnable onChange,String proposed,String label){
        String url=canonical(proposed==null?null:proposed.trim());
        if(url==null){deck.error("Only an existing personal https://chatgpt.com/c/... conversation URL is supported.");return;}
        SharedPreferences prefs=a.getSharedPreferences(PREF,Activity.MODE_PRIVATE);
        String prior=prefs.getString("url_"+url,"");
        if(!prior.isEmpty()){
            try {deck.select(prior);return;}catch(Exception ignored){}
        }
        final RitsuWorkspace.Tab t;
        try {t=work.create(label.trim().isEmpty()?"Linked ChatGPT":label.substring(0,Math.min(label.length(),45)));}
        catch(Exception ex){deck.error("Cannot create local conversation: "+coarse(ex));return;}
        if(!prefs.edit().putString("state_"+t.id,"PENDING").commit()){
            deck.error("Link guard was not persisted. Sending remains disabled.");return;
        }
        onChange.run();
        NETWORK.execute(()->{
            try{
                JSONObject req=new JSONObject().put("tabId",t.id).put("url",url);
                JSONObject ack=request(a,"POST","/v1/ritsu/bind",req);
                if(!ack.optBoolean("verified",false)||!t.id.equals(ack.optString("tabId"))||!url.equals(ack.optString("url")))
                    throw new SecurityException("Binding response mismatch");
                if(!prefs.edit().putString("state_"+t.id,"VERIFIED")
                    .putString("url_"+url,t.id).putString("linked_"+t.id,url).commit())
                    throw new IllegalStateException("Binding receipt not persisted");
                MAIN.post(()->{deck.openWithoutSelection(t.id);onChange.run();});
            }catch(Exception error){
                prefs.edit().putString("state_"+t.id,"FAILED").commit();
                MAIN.post(()->deck.error("Link not verified ("+coarse(error)+"). The new tab is blocked from sending, and no message was submitted."));
            }
        });
    }
    static void voicePreference(Activity a,String tabId,RitsuConversationDeck deck){
        SharedPreferences prefs=a.getSharedPreferences(PREF,Activity.MODE_PRIVATE);
        boolean enabled=!prefs.getBoolean("voice_"+tabId,false);
        NETWORK.execute(()->{
            try{
                JSONObject req=new JSONObject().put("tabId",tabId).put("enabled",enabled);
                JSONObject answer=request(a,"POST","/v1/ritsu/voice-preference",req);
                if(!answer.optBoolean("verified",false)||answer.optBoolean("enabled")!=enabled)
                    throw new SecurityException("Voice preference response mismatch");
                if(!prefs.edit().putBoolean("voice_"+tabId,enabled).commit())
                    throw new IllegalStateException("Voice selection not persisted");
                MAIN.post(()->deck.error(enabled?"Pocket voice enabled for new complete replies up to 450 characters; longer text remains visible but is not silently cut for speech.":
                    "Pocket voice disabled for this chat."));
            }catch(Exception error){MAIN.post(()->deck.error("Voice preference unchanged: "+coarse(error)));}
        });
    }
    private static JSONObject request(Activity a,String method,String suffix,JSONObject json)throws Exception{
        RitsuPairing.Pair pair=RitsuPairing.load(a);
        if(pair==null)throw new IllegalStateException("PAIRING_REQUIRED");
        String origin=RitsuPairing.validateOrigin(pair.origin);
        if(!suffix.equals("/v1/ritsu/catalog")&&!suffix.equals("/v1/ritsu/bind")&&!suffix.equals("/v1/ritsu/voice-preference"))throw new SecurityException("Route refused");
        HttpURLConnection c=(HttpURLConnection)new URL(origin+suffix).openConnection();
        try{
            c.setInstanceFollowRedirects(false);c.setConnectTimeout(7000);c.setReadTimeout(17000);
            c.setUseCaches(false);c.setRequestMethod(method);
            c.setRequestProperty("Authorization","Bearer "+pair.token);
            c.setRequestProperty("Accept","application/json");
            if(json!=null){
                byte[] bytes=json.toString().getBytes(StandardCharsets.UTF_8);
                if(bytes.length>2048)throw new IllegalArgumentException("Request too large");
                c.setRequestProperty("Content-Type","application/json");c.setDoOutput(true);c.setFixedLengthStreamingMode(bytes.length);
                try(OutputStream out=c.getOutputStream()){out.write(bytes);}
            }
            int code=c.getResponseCode();
            if(code!=200){
                String detail="";
                java.io.InputStream trouble=c.getErrorStream();
                if(trouble!=null)try(java.io.InputStream in=trouble){
                    byte[] bytes=new byte[1000];int n=in.read(bytes);
                    if(n>0){
                        String body=new String(bytes,0,n,java.nio.charset.StandardCharsets.UTF_8);
                        detail=new JSONObject(body).optString("error","");
                    }
                }
                detail=detail.replaceAll("[^A-Za-z0-9_.:-]","_");
                if(detail.length()>72)detail=detail.substring(0,72);
                throw new IllegalStateException("CATALOG_HTTP_"+code+(detail.isEmpty()?"":"_"+detail));
            }
            ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buf=new byte[1024];int n;
            try(InputStream stream=c.getInputStream()){
                while((n=stream.read(buf))!=-1){if(out.size()+n>48000)throw new IllegalStateException("Catalog too large");out.write(buf,0,n);}
            }
            return new JSONObject(out.toString("UTF-8"));
        }finally{c.disconnect();}
    }
}
