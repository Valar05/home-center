package com.homecenter.ritsucontrol;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;

/** Explicit, nonexported callback for user-triggered Termux command receipts. */
public final class CampaignResultReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context,Intent intent){
        if(intent==null)return;
        Bundle r=intent.getBundleExtra("result");
        String op=intent.getStringExtra("operation");
        String message;
        if(r==null){ message="No Termux result bundle. Confirm allow-external-apps and permission."; }
        else {
            int code=r.getInt("exitCode",-999);
            int err=r.getInt("err",-1);
            String out=r.getString("stdout","");String stderr=r.getString("stderr","");
            String error=r.getString("errmsg","");
            // Results contain no app secrets from our bridge. Bound UI output.
            message="Command="+op+"  EXIT="+code+"  TERMUX_ERROR="+err+"\n"+
                  (out==null?"":out)+(stderr==null?"":"\n"+stderr)+
                  (error==null?"":"\n"+error);
        }
        if(message.length()>16000)message=message.substring(0,16000)+"\n[TRUNCATED]";
        context.getSharedPreferences("CampaignActivity",Context.MODE_PRIVATE)
             .edit().putString("last_result",message).apply();
    }
}
