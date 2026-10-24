package com.homecenter.ritsucontrol;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONObject;
import org.json.JSONArray;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Home Center CLOUD account approval, distinct from the retired desktop
 * private gateway pairing. Exactly one pinned HTTPS origin. No desktop.
 *
 * Requires the owner to approve pairingId + code in the existing Home Center
 * Android app. The separate Ritsu Control app does not read Termux's private
 * token file or reuse credentials without the owner's consent.
 */
final class HomeCenterCloudPairing {
    static final String BASE = "https://us-central1-home-center-dclar.cloudfunctions.net";
    private static final String PREF = "ritsu_home_center_cloud_pair_v1";
    private static final String ALIAS = "ritsu_home_center_cloud_aes_v1";
    private static final String KEY = "sealed";
    private HomeCenterCloudPairing() {}

    static final class Pending {
        final String id, code;
        final long expiresAtMs;
        Pending(String id, String code, long expiresAtMs) {
            this.id=id; this.code=code; this.expiresAtMs=expiresAtMs;
        }
    }
    static final class Paired {
        final String accessToken, refreshToken, email, mcpUrl;
        final long accessExpiresAtMs;
        Paired(String accessToken, String refreshToken, String email,
               String mcpUrl, long accessExpiresAtMs) {
            this.accessToken=accessToken;this.refreshToken=refreshToken;
            this.email=email;this.mcpUrl=mcpUrl;
            this.accessExpiresAtMs=accessExpiresAtMs;
        }
    }

    static Pending start() throws Exception {
        JSONObject body=new JSONObject();
        body.put("deviceName","Ritsu Control Android");
        body.put("clientKind","ritsu-control-android");
        // Uses the currently deployed Home Center approval contract.
        // The existing Home Center app explicitly presents/approves the access.
        body.put("requestedGroups",new JSONArray()
                .put("drive").put("docs").put("github"));
        JSONObject result=call("termuxPairingStart",body,null);
        String id=result.optString("pairingId","");
        String code=result.optString("code","");
        if(!id.matches("[A-Za-z0-9_-]{12,180}") ||
           !code.matches("[0-9]{6}") ||
           result.optLong("expiresIn",0)<1)
            throw new IllegalStateException("Home Center pairing protocol invalid");
        return new Pending(id,code,System.currentTimeMillis()+
                Math.min(result.optLong("expiresIn",600),600)*1000);
    }

    /** Returns false only while Home Center is waiting for owner approval. */
    static boolean poll(Context context, Pending pending) throws Exception {
        if(System.currentTimeMillis()>=pending.expiresAtMs)
            throw new IllegalStateException("Home Center pairing expired");
        JSONObject req=new JSONObject();
        req.put("pairingId",pending.id);
        req.put("code",pending.code);
        JSONObject result=call("termuxPairingPoll",req,null);
        if("pending".equals(result.optString("status")))
            return false;
        if(!"paired".equals(result.optString("status")))
            throw new IllegalStateException("Home Center pairing not approved");
        String access=result.optString("access_token","");
        String refresh=result.optString("refresh_token","");
        String mcp=result.optString("mcpUrl","");
        String email=result.optString("email","");
        int lifetime=result.optInt("expires_in",0);
        if(access.length()<32 || refresh.length()<32 || lifetime<=0 ||
           !"https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp".equals(mcp))
            throw new IllegalStateException("Home Center returned invalid credentials");
        JSONObject check=call("termuxHubTools",null,access);
        if(!check.optBoolean("ok") || !mcp.equals(check.optString("mcpUrl")))
            throw new IllegalStateException("Home Center cloud credential verification failed");
        save(context,new Paired(access,refresh,email,mcp,
                System.currentTimeMillis()+lifetime*1000L));
        return true;
    }

    private static JSONObject call(String action, JSONObject body, String bearer)
            throws Exception {
        if(!action.matches("termuxPairingStart|termuxPairingPoll|termuxHubTools"))
            throw new IllegalArgumentException("Unrecognized Home Center route");
        URL url=new URL(BASE+"/"+action);
        HttpURLConnection conn=(HttpURLConnection)url.openConnection();
        conn.setInstanceFollowRedirects(false);
        conn.setConnectTimeout(5500); conn.setReadTimeout(6500);
        conn.setUseCaches(false);
        conn.setRequestProperty("Accept","application/json");
        conn.setRequestProperty("Cache-Control","no-store");
        conn.setRequestMethod(body==null?"GET":"POST");
        if(bearer!=null)conn.setRequestProperty("Authorization","Bearer "+bearer);
        try {
            if(body!=null) {
                byte[] bytes=body.toString().getBytes(StandardCharsets.UTF_8);
                if(bytes.length>2048)throw new IllegalArgumentException("Cloud request oversized");
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type","application/json");
                conn.setFixedLengthStreamingMode(bytes.length);
                try(OutputStream out=conn.getOutputStream()){out.write(bytes);}
            }
            int status=conn.getResponseCode();
            if(status<200||status>=300)
                throw new IllegalStateException("Home Center cloud HTTP "+status);
            try(InputStream stream=conn.getInputStream()) {
                ByteArrayOutputStream output=new ByteArrayOutputStream();
                byte[] buf=new byte[2048];int read;
                while((read=stream.read(buf))!=-1){
                    if(output.size()+read>16384)
                        throw new IllegalStateException("Cloud response oversized");
                    output.write(buf,0,read);
                }
                JSONObject json=new JSONObject(output.toString(StandardCharsets.UTF_8.name()));
                if(!json.optBoolean("ok"))
                    throw new IllegalStateException("Home Center cloud request rejected");
                return json;
            }
        }finally{conn.disconnect();}
    }

    static void save(Context context,Paired pair) throws Exception {
        JSONObject obj=new JSONObject();
        obj.put("access",pair.accessToken);
        obj.put("refresh",pair.refreshToken);
        obj.put("email",pair.email);
        obj.put("mcp",pair.mcpUrl);
        obj.put("expiresAtMs",pair.accessExpiresAtMs);
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE,key());
        byte[] iv=cipher.getIV();
        byte[] encrypted=cipher.doFinal(obj.toString().getBytes(StandardCharsets.UTF_8));
        byte[] bytes=Arrays.copyOf(iv,iv.length+encrypted.length);
        System.arraycopy(encrypted,0,bytes,iv.length,encrypted.length);
        boolean ok=context.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit()
                .putString(KEY,Base64.encodeToString(bytes,Base64.NO_WRAP)).commit();
        if(!ok)throw new IllegalStateException("Cloud pairing not persisted");
    }
    static Paired load(Context context) {
        String sealed=context.getSharedPreferences(PREF,Context.MODE_PRIVATE)
                .getString(KEY,"");
        if(sealed.isEmpty())return null;
        try {
            byte[] bytes=Base64.decode(sealed,Base64.DEFAULT);
            if(bytes.length<29)throw new IllegalStateException("Encrypted cloud credential malformed");
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,key(),
                    new GCMParameterSpec(128,Arrays.copyOf(bytes,12)));
            JSONObject x=new JSONObject(new String(cipher.doFinal(bytes,12,bytes.length-12),
                    StandardCharsets.UTF_8));
            return new Paired(x.getString("access"),x.getString("refresh"),
                    x.optString("email"),x.getString("mcp"),
                    x.getLong("expiresAtMs"));
        }catch(Exception e){throw new IllegalStateException("Cloud pairing cannot be opened");}
    }
    static void disconnect(Context context) {
        context.getSharedPreferences(PREF,Context.MODE_PRIVATE)
                .edit().remove(KEY).commit();
    }
    private static SecretKey key() throws Exception {
        KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
        java.security.Key k=ks.getKey(ALIAS,null);
        if(k instanceof SecretKey)return (SecretKey)k;
        KeyGenerator gen=KeyGenerator.getInstance("AES","AndroidKeyStore");
        gen.init(new KeyGenParameterSpec.Builder(ALIAS,
                 KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build());
        return gen.generateKey();
    }
}
