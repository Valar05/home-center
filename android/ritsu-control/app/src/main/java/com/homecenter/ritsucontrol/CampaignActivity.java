package com.homecenter.ritsucontrol;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.graphics.Color;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONObject;
import java.util.regex.Pattern;
import java.util.concurrent.atomic.AtomicInteger;

/** An Android UI wired to the actual deterministic Termux v0.13 supervisor.
 * This does not execute model-proposed shell commands or bypass OS permissions.
 */
public final class CampaignActivity extends Activity {
    private static final AtomicInteger REQUEST = new AtomicInteger(10000);
    private static final String HOME="/data/data/com.termux/files/home";
    private static final String PY="/data/data/com.termux/files/usr/bin/python3";
    // Filled by signed build from known bundled SHA-256. Never a user-controlled path.
    private static final String BRIDGE="/data/data/com.termux/files/home/.local/share/ritsu-integrated-engine/v13-campaign1/bridge.py";
    private EditText id, title, mission, approvedFile;
    private TextView result;
    private static final Pattern SAFE_ID=Pattern.compile("[A-Za-z0-9][A-Za-z0-9_-]{2,63}");

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView sc=new ScrollView(this);
        LinearLayout ll=new LinearLayout(this);
        ll.setOrientation(LinearLayout.VERTICAL);ll.setPadding(28,32,28,36);ll.setBackgroundColor(Color.rgb(23,24,30));
        sc.addView(ll);
        TextView heading=text("RITSU  •  CAMPAIGN CONTROL",22); ll.addView(heading);
        ll.addView(text("Native Android control + bundled, real Termux v0.13 supervisor. Start is gated by owner-confirmed Instant mode and a read-only authenticated probe. Browser-origin code execution remains disabled.",13));
        id=edit("Campaign ID (e.g. my_project_001)",false);ll.addView(id);
        title=edit("Campaign title",false);ll.addView(title);
        mission=edit("Mission and constraints",true);ll.addView(mission);
        approvedFile=edit("Approved script filename (e.g. build.sh)",false);ll.addView(approvedFile);
        button(ll,"Create scoped campaign",()->create());
        button(ll,"Engine doctor (no model calls)",()->send("doctor",null,null));
        button(ll,"Campaign status",()->sendForId("status"));
        button(ll,"Confirm browser Instant mode",()->sendForId("confirm-instant"));
        button(ll,"Probe private browser bridge (read only)",()->sendForId("probe"));
        button(ll,"Start campaign in background",()->sendForId("start"));
        button(ll,"Stop campaign",()->sendForId("stop"));
        button(ll,"Recover stopped campaign",()->sendForId("recover"));
        button(ll,"Accept completed campaign",()->sendForId("accept"));
        button(ll,"Approve and execute selected local script",()->approvedExecute());
        button(ll,"Revoke campaign",()->sendForId("revoke"));
        button(ll,"Open Ritsu voice controls",()->startActivity(new Intent(this, MainActivity.class)));
        button(ll,"Refresh latest result",()->refresh());
        result=text("",13);result.setTextIsSelectable(true);ll.addView(result);
        setContentView(sc);
        refresh();
    }
    private TextView text(String s,int sp) {
        TextView t=new TextView(this); t.setText(s);t.setTextSize(sp);t.setTextColor(Color.WHITE);
        t.setPadding(0,10,0,12);return t;
    }
    private EditText edit(String hint,boolean multi){
        EditText e=new EditText(this);e.setHint(hint);e.setHintTextColor(Color.LTGRAY);e.setTextColor(Color.WHITE);
        e.setInputType(multi ? InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE|InputType.TYPE_TEXT_FLAG_CAP_SENTENCES : InputType.TYPE_CLASS_TEXT);
        e.setMinLines(multi?3:1);e.setMaxLines(multi?6:1);return e;
    }
    private void button(LinearLayout ll,String label,Runnable action){
        Button b=new Button(this);b.setText(label);ll.addView(b);b.setOnClickListener(v->action.run());
    }
    private void create(){
        String campaign=id.getText().toString().trim();
        if(!SAFE_ID.matcher(campaign).matches()){show("Invalid campaign ID. Use 3-64 letters, numbers, - or _.");return;}
        try {
            JSONObject obj=new JSONObject();obj.put("title",title.getText().toString());obj.put("mission",mission.getText().toString());
            send("create",campaign,obj.toString());
        } catch(Exception e){show("Input error: "+e.getClass().getSimpleName());}
    }
    private void sendForId(String op){
        String campaign=id.getText().toString().trim();
        if(!SAFE_ID.matcher(campaign).matches()){show("Enter a valid campaign ID first.");return;}
        if(op.equals("confirm-instant")){
            new android.app.AlertDialog.Builder(this)
                .setTitle("Confirm Instant browser mode")
                .setMessage("Confirm that you personally selected Instant in your signed-in browser. This is owner-asserted, not machine-verifiable. No model request is sent by confirmation.")
                .setPositiveButton("I confirm Instant",(d,w)->send(op,campaign,null))
                .setNegativeButton("Cancel",null).show();return;
        }
        if(op.equals("revoke")){
            new android.app.AlertDialog.Builder(this).setTitle("Revoke campaign?")
                .setMessage("Revocation is terminal. No automatic recovery will be attempted.")
                .setPositiveButton("Revoke",(d,w)->send(op,campaign,null))
                .setNegativeButton("Cancel",null).show();return;
        }
        send(op,campaign,null);
    }
    private void approvedExecute(){
        String campaign=id.getText().toString().trim();
        String file=approvedFile.getText().toString().trim();
        if(!SAFE_ID.matcher(campaign).matches() || !file.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\\.(sh|py)")){
            show("Enter a campaign ID and a simple .sh or .py script filename.");return;
        }
        new android.app.AlertDialog.Builder(this)
            .setTitle("Execute this local script?")
            .setMessage("Approve this exact file once: "+file+". Termux scripts are NOT an OS sandbox and may access your phone files and network. Stop campaign first. Never approve an unreviewed script.")
            .setPositiveButton("Execute once",(d,w)->send("execute-file",campaign,file,null))
            .setNegativeButton("Cancel",null).show();
    }
    private void send(String op,String campaign,String payload){ send(op,campaign,null,payload); }
    private void send(String op,String campaign,String file,String payload){
        if(checkSelfPermission("com.termux.permission.RUN_COMMAND")!=PackageManager.PERMISSION_GRANTED){
            show("PERMISSION_REQUIRED: Grant 'Run commands in Termux environment' to Ritsu Fresh in Android Settings > Apps > Permissions > Additional permissions. Also enable allow-external-apps=true in Termux properties.");return;
        }
        Intent cmd=new Intent("com.termux.RUN_COMMAND");
        cmd.setClassName("com.termux","com.termux.app.RunCommandService");
        cmd.putExtra("com.termux.RUN_COMMAND_PATH",PY);
        cmd.putExtra("com.termux.RUN_COMMAND_ARGUMENTS",campaign==null ? new String[]{BRIDGE,op} : (file==null ? new String[]{BRIDGE,op,campaign} : new String[]{BRIDGE,op,campaign,file}));
        cmd.putExtra("com.termux.RUN_COMMAND_WORKDIR",HOME);
        cmd.putExtra("com.termux.RUN_COMMAND_BACKGROUND",true);
        if(payload!=null){cmd.putExtra("com.termux.RUN_COMMAND_STDIN",payload);}
        int request=REQUEST.incrementAndGet();
        Intent callback=new Intent(this,CampaignResultReceiver.class);callback.putExtra("operation",op);
        PendingIntent resultIntent=PendingIntent.getBroadcast(this,request,callback,PendingIntent.FLAG_ONE_SHOT|PendingIntent.FLAG_MUTABLE);
        cmd.putExtra("com.termux.RUN_COMMAND_PENDING_INTENT",resultIntent);
        try{startService(cmd);show("Submitted "+op+" to Termux. Results are returned here. If nothing arrives, check Termux external-app settings.");}
        catch (SecurityException e){show("Termux denied permission: grant Run Command in Additional permissions.");}
        catch (Exception e){show("Termux unavailable: "+e.getClass().getSimpleName()+". Open Termux and check external-app settings.");}
    }
    private void show(String msg){
        getPreferences(MODE_PRIVATE).edit().putString("last_result",msg).apply();if(result!=null)result.setText(msg);
    }
    private void refresh(){String value=getPreferences(MODE_PRIVATE).getString("last_result","No commands submitted."); if(result!=null)result.setText(value);}
    @Override protected void onResume(){super.onResume();refresh();}
}
