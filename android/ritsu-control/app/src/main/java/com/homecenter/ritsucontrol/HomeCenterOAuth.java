package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import android.net.Uri;
import android.util.Base64;
import org.json.JSONObject;
import org.json.JSONArray;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;

/**
 * Ritsu Control's native, user-initiated Home Center OAuth sign-in.
 *
 * Public authorization server URL/client ID may ship in the APK; neither a
 * Home Center bearer, refresh token, account password nor a signing secret
 * belongs in an APK. Browser PKCE S256 + state binds each one-time callback,
 * and the resulting credentials are sealed by HomeCenterCloudPairing using
 * AndroidKeyStore after verified /oauth/userinfo readback.
 */
final class HomeCenterOAuth {
    static final String ISSUER="https://homecentermcp-vxybsaualq-uc.a.run.app";
    static final String RESOURCE=ISSUER+"/mcp";
    /** The Campaign APK must never share the Connected APK callback handler. */
    static String scheme(Context app) {
        if("com.homecenter.ritsucontrol.stable".equals(app.getPackageName())) return "ritsucontrolstable";
        if("com.homecenter.ritsucontrol.outbox".equals(app.getPackageName()))
            return "ritsucontroloutbox";
        if("com.homecenter.ritsucontrol.bridge".equals(app.getPackageName()))
            return "ritsucontrolbridge";
        return "com.homecenter.ritsucontrol.campaign".equals(app.getPackageName())
            ? "ritsucontrolcampaign"
            : "com.homecenter.ritsucontrol.outbox".equals(app.getPackageName())
                ? "ritsucontroloutbox" : "ritsucontrol";
    }
    static String redirect(Context app){return scheme(app)+"://oauth/callback";}
    private static final String STORAGE="ritsu_home_center_native_oauth_v1";
    private static final String STATE="pending_state";
    private static final String VERIFIER="pending_verifier";
    private static final String CLIENT="pending_client";
    private static final String STARTED="pending_started";
    private static final long MAX_AGE=10*60*1000L;

    private HomeCenterOAuth(){}

    static String begin(Context app) throws Exception {
        // Dynamic registration avoids embedding another application's OAuth
        // client identity or an app-wide secret in the distributable APK.
        String redirect=redirect(app);
        JSONObject registration=new JSONObject()
            .put("client_name","Ritsu Control for Android")
            .put("redirect_uris",new JSONArray().put(redirect))
            .put("grant_types",new JSONArray().put("authorization_code").put("refresh_token"))
            .put("response_types",new JSONArray().put("code"))
            .put("token_endpoint_auth_method","none");
        JSONObject registered=request("POST","/oauth/register",registration,null);
        String client=registered.optString("client_id","");
        if(!client.matches("home_center_mcp_[A-Za-z0-9_-]{20,100}"))
            throw new SecurityException("Home Center registration invalid");
        String verifier=random(48);
        String state=random(32);
        byte[] digest=MessageDigest.getInstance("SHA-256")
            .digest(verifier.getBytes(StandardCharsets.US_ASCII));
        String challenge=Base64.encodeToString(digest,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);
        boolean stored=app.getSharedPreferences(STORAGE,Context.MODE_PRIVATE).edit()
            .putString(STATE,state).putString(VERIFIER,verifier)
            .putString(CLIENT,client).putLong(STARTED,System.currentTimeMillis()).commit();
        if(!stored)throw new IllegalStateException("Cannot save pending sign-in");
        return ISSUER+"/oauth/authorize?response_type=code"+
            "&client_id="+enc(client)+
            "&redirect_uri="+enc(redirect)+
            "&resource="+enc(RESOURCE)+
            "&scope="+enc("offline_access")+
            "&code_challenge_method=S256"+
            "&code_challenge="+enc(challenge)+
            "&state="+enc(state);
    }

    static HomeCenterCloudPairing.Paired complete(Context app, Uri callback)
        throws Exception {
        if(callback==null||!scheme(app).equals(callback.getScheme())||
           !"oauth".equals(callback.getHost())||
           !"/callback".equals(callback.getPath()))
            throw new SecurityException("Unexpected OAuth redirect");
        SharedPreferences prefs=app.getSharedPreferences(STORAGE,Context.MODE_PRIVATE);
        String expected=prefs.getString(STATE,"");
        String verifier=prefs.getString(VERIFIER,"");
        String client=prefs.getString(CLIENT,"");
        long started=prefs.getLong(STARTED,0);
        if(expected.length()<30||verifier.length()<40||client.isEmpty()||
           started<=0||System.currentTimeMillis()-started>MAX_AGE)
            throw new SecurityException("Sign-in expired or not started");
        String got=callback.getQueryParameter("state");
        if(got==null||!MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8),
           got.getBytes(StandardCharsets.UTF_8)))
            throw new SecurityException("OAuth state mismatch");
        // One use even on a failed token exchange. Never retain the PKCE
        // verifier or authorize a second callback with the same login state.
        clearPending(app);
        if(callback.getQueryParameter("error")!=null)
            throw new SecurityException("Home Center sign-in declined");
        String code=callback.getQueryParameter("code");
        if(code==null||code.length()<16||code.length()>4096)
            throw new SecurityException("Missing Home Center authorization code");
        JSONObject token=request("POST","/oauth/token",new JSONObject()
            .put("grant_type","authorization_code").put("client_id",client)
            .put("code",code).put("redirect_uri",redirect(app))
            .put("code_verifier",verifier).put("resource",RESOURCE),null);
        return validatedPair(token,client);
    }

    static HomeCenterCloudPairing.Paired refresh(HomeCenterCloudPairing.Paired p)
        throws Exception {
        if(p.oauthClientId.isEmpty())throw new IllegalArgumentException("Not OAuth credential");
        JSONObject token=request("POST","/oauth/token",new JSONObject()
            .put("grant_type","refresh_token").put("client_id",p.oauthClientId)
            .put("refresh_token",p.refreshToken).put("resource",RESOURCE),null);
        if(!token.has("refresh_token"))token.put("refresh_token",p.refreshToken);
        return validatedPair(token,p.oauthClientId);
    }

    static void clearPending(Context context){
        context.getSharedPreferences(STORAGE,Context.MODE_PRIVATE).edit().clear().apply();
    }

    private static HomeCenterCloudPairing.Paired validatedPair(JSONObject token,String client)
        throws Exception {
        String access=token.optString("access_token","");
        String refresh=token.optString("refresh_token","");
        int expires=token.optInt("expires_in",0);
        if(access.length()<32||refresh.length()<32||expires<60)
            throw new SecurityException("Home Center token response invalid");
        JSONObject identity=request("GET","/oauth/userinfo",null,access);
        String email=identity.optString("email","");
        if(!identity.optBoolean("email_verified")||
           !email.matches("[^@\\s]+@[^@\\s]+\\.[^@\\s]+")||
           !client.equals(identity.optString("client_id"))||
           !RESOURCE.equals(identity.optString("resource")))
            throw new SecurityException("Home Center identity verification failed");
        return new HomeCenterCloudPairing.Paired(access,refresh,email,
            "https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp",
            System.currentTimeMillis()+expires*1000L,client);
    }

    private static String random(int bytes) {
        byte[] data=new byte[bytes];new SecureRandom().nextBytes(data);
        return Base64.encodeToString(data,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);
    }
    private static String enc(String s) throws Exception {
        return URLEncoder.encode(s,StandardCharsets.UTF_8.name());
    }
    private static JSONObject request(String method,String route,JSONObject body,String bearer)
        throws Exception {
        if(!route.matches("/oauth/register|/oauth/token|/oauth/userinfo"))
            throw new SecurityException("Route not approved");
        URL url=new URL(ISSUER+route);
        HttpURLConnection connection=(HttpURLConnection)url.openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(12000);
        connection.setUseCaches(false);
        connection.setRequestMethod(method);
        connection.setRequestProperty("Accept","application/json");
        connection.setRequestProperty("Cache-Control","no-store");
        if(bearer!=null)connection.setRequestProperty("Authorization","Bearer "+bearer);
        try{
            if(body!=null){
                byte[] data=body.toString().getBytes(StandardCharsets.UTF_8);
                if(data.length>4096)throw new SecurityException("Request too large");
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type","application/json");
                connection.setFixedLengthStreamingMode(data.length);
                try(OutputStream out=connection.getOutputStream()){out.write(data);}
            }
            int status=connection.getResponseCode();
            if(status<200||status>=300)
                throw new IllegalStateException("Home Center OAuth HTTP "+status);
            try(InputStream in=connection.getInputStream()){
                ByteArrayOutputStream out=new ByteArrayOutputStream();
                byte[] buf=new byte[1024];int n;
                while((n=in.read(buf))!=-1){
                    if(out.size()+n>16384)throw new SecurityException("OAuth response too large");
                    out.write(buf,0,n);
                }
                return new JSONObject(out.toString(StandardCharsets.UTF_8.name()));
            }
        }finally{connection.disconnect();}
    }
}
