package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Android-keystore sealed, owner-operated direct Tailscale pairing.
 * No Chromium Throne capability, browser cookie or default credential in APK.
 * HTTP is allowed ONLY to a literal Tailscale 100.64/10 address: WireGuard
 * provides the transport encryption, and bearer auth is separate from Throne.
 */
final class RitsuPairing {
    private static final String ALIAS = "ritsu_direct_tailnet_phone_v1";
    private static final String PREF = "ritsu_phone_direct_tailnet_v1";
    static final class Pair {
        final String origin, token;
        Pair(String origin, String token) { this.origin=origin; this.token=token; }
    }
    private RitsuPairing() {}

    static String validateOrigin(String text) {
        try {
            URI uri=new URI(text == null ? "" : text.trim());
            if (!"http".equals(uri.getScheme()) ||
                    uri.getRawUserInfo()!=null || uri.getQuery()!=null ||
                    uri.getFragment()!=null || uri.getPort()!=19646 ||
                    !("".equals(uri.getPath()) || "/".equals(uri.getPath())))
                throw new IllegalArgumentException("Tailscale address required");
            String host=uri.getHost();
            if(host==null)throw new IllegalArgumentException("Numeric tailnet address required");
            String[] parts=host.split("\\.",-1);
            if(parts.length!=4)throw new IllegalArgumentException("Numeric tailnet address required");
            int[] ip=new int[4];
            for(int i=0;i<4;i++){
                if(!parts[i].matches("[0-9]{1,3}"))
                    throw new IllegalArgumentException("Numeric tailnet address required");
                ip[i]=Integer.parseInt(parts[i]);
                if(ip[i]>255)throw new IllegalArgumentException("Invalid IP");
            }
            if(ip[0]!=100 || ip[1]!=68 || ip[2]!=37 || ip[3]!=106)
                throw new IllegalArgumentException("Only the pinned THECAULDRON tailnet address is accepted");
            return "http://"+String.format(java.util.Locale.ROOT,"%d.%d.%d.%d",
                    ip[0],ip[1],ip[2],ip[3])+":19646";
        }catch(java.net.URISyntaxException e){
            throw new IllegalArgumentException("Invalid Tailscale address");
        }
    }

    static void save(Context context, String origin, String token) {
        String safe=validateOrigin(origin);
        if(token==null || !token.trim().matches("[a-f0-9]{64}"))
            throw new IllegalArgumentException("Invalid device pairing token");
        try {
            byte[] clear=(safe+"\n"+token.trim()).getBytes(StandardCharsets.UTF_8);
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE,key());
            byte[] iv=cipher.getIV(), encrypted=cipher.doFinal(clear);
            byte[] data=Arrays.copyOf(iv,iv.length+encrypted.length);
            System.arraycopy(encrypted,0,data,iv.length,encrypted.length);
            boolean committed=context.getSharedPreferences(PREF,Context.MODE_PRIVATE)
                    .edit().putString("sealed",Base64.encodeToString(data,Base64.NO_WRAP))
                    .commit();
            if(!committed)throw new IllegalStateException("Pairing not saved");
            // Always reset the direct journal cursor on device re-pairing.
            if(!context.getSharedPreferences("ritsu_local_sse_cursor_v1",Context.MODE_PRIVATE)
                    .edit().putLong("seq",0).commit())
                throw new IllegalStateException("Feed cursor not reset");
        }catch(IllegalArgumentException e){throw e;}
        catch(Exception e){throw new IllegalStateException("Secure pairing failed");}
    }

    static Pair load(Context context) {
        SharedPreferences prefs=context.getSharedPreferences(PREF,Context.MODE_PRIVATE);
        String sealed=prefs.getString("sealed","");
        if(sealed.isEmpty())return null;
        try {
            byte[] data=Base64.decode(sealed,Base64.DEFAULT);
            if(data.length<29)throw new IllegalStateException("Invalid protected data");
            byte[] iv=Arrays.copyOfRange(data,0,12);
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,iv));
            String clear=new String(cipher.doFinal(data,12,data.length-12),
                    StandardCharsets.UTF_8);
            int split=clear.indexOf('\n');
            if(split<=0)throw new IllegalStateException("Invalid protected pairing");
            String origin=validateOrigin(clear.substring(0,split));
            String token=clear.substring(split+1);
            if(token.length()<40)throw new IllegalStateException("Invalid protected token");
            return new Pair(origin,token);
        }catch(Exception e){throw new IllegalStateException("Pairing cannot be decrypted; re-pair");}
    }

    static void disconnect(Context context) {
        context.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit().remove("sealed").commit();
        context.getSharedPreferences("ritsu_sync_feed_v1",Context.MODE_PRIVATE)
                .edit().putLong("seq",0).commit();
    }

    private static SecretKey key() throws Exception {
        KeyStore keystore=KeyStore.getInstance("AndroidKeyStore");
        keystore.load(null);
        java.security.Key loaded=keystore.getKey(ALIAS,null);
        if(loaded instanceof SecretKey)return (SecretKey)loaded;
        KeyGenerator generator=KeyGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(ALIAS,
                KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build());
        return generator.generateKey();
    }
}
