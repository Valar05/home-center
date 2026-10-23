package com.homecenter.ritsucontrol;

import android.Manifest;
import android.app.Activity;
import android.app.StatusBarManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.List;

/** Voice-first conversation cockpit. Visible chat results from many channels
 * while the default operation is continuous mic+silence segmentation.
 * IMPORTANT: local outbox is not remote Home Center / ChatGPT delivery. */
public final class MainActivity extends Activity {
    private static final int REQUEST_MIC = 19645;
    private static final int REQUEST_NOTIFICATIONS = 19644;
    private TextView headerStatus, details;
    private EditText composer;
    private LinearLayout transcriptRows, advanced;
    private ScrollView feedScroll;
    private ConversationLedger ledger;
    private String channel = "all";
    private boolean pendingBubbleEnable, advancedVisible;
    private long lastFeedRevision = -1;
    private long lastTranscriptRevision = -1;
    private final Handler updates = new Handler(Looper.getMainLooper());
    private final Runnable redraw = new Runnable() {
        @Override public void run() {
            if (headerStatus == null) return;
            refreshStatus();
            if (lastFeedRevision != RitsuControlService.feedRevision) {
                lastFeedRevision = RitsuControlService.feedRevision;
                renderFeed();
            }
            updates.postDelayed(this, 350);
        }
    };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ledger = new ConversationLedger(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(19, 18, 28));
        root.setPadding(dp(12), dp(12), dp(12), dp(8));

        TextView title = label("Ritsu  ·  Conversation Hub", 21, true);
        root.addView(title);
        headerStatus = label("Mic off · Home Center not connected", 12, false);
        headerStatus.setPadding(0, dp(5), 0, dp(12));
        root.addView(headerStatus);

        LinearLayout tabs = new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        addTab(tabs,"All","all");
        addTab(tabs,"Ritsu","dialogue");
        addTab(tabs,"Control","control");
        addTab(tabs,"Workers","worker");
        root.addView(tabs);

        feedScroll = new ScrollView(this);
        transcriptRows = new LinearLayout(this);
        transcriptRows.setPadding(0, dp(12), 0, dp(6));
        transcriptRows.setOrientation(LinearLayout.VERTICAL);
        feedScroll.addView(transcriptRows);
        root.addView(feedScroll,new LinearLayout.LayoutParams(-1,0,1));

        LinearLayout compose = new LinearLayout(this);
        compose.setOrientation(LinearLayout.HORIZONTAL);
        composer = new EditText(this);
        composer.setSingleLine(false);
        composer.setMaxLines(4);
        composer.setTextColor(Color.WHITE);
        composer.setHintTextColor(Color.LTGRAY);
        composer.setHint("Say something, or type with Gboard…");
        composer.setTextSize(15);
        composer.setInputType(InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_FLAG_MULTI_LINE |
                InputType.TYPE_TEXT_FLAG_AUTO_CORRECT |
                InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        composer.setContentDescription("Optional message with Gboard typing and autocorrect");
        compose.addView(composer,new LinearLayout.LayoutParams(0,dp(56),1));
        Button send=button("Queue text",v->queueTyped());
        compose.addView(send);
        root.addView(compose);

        LinearLayout controls=new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.addView(button("Listen",v->requestListening()),
                new LinearLayout.LayoutParams(0,dp(56),1));
        controls.addView(button("Mute / Resume",v->toggleMute()),
                new LinearLayout.LayoutParams(0,dp(56),1));
        controls.addView(button("More",v->toggleAdvanced()),
                new LinearLayout.LayoutParams(0,dp(56),1));
        root.addView(controls);

        advanced=new LinearLayout(this);
        advanced.setOrientation(LinearLayout.VERTICAL);
        advanced.setVisibility(View.GONE);
        details=label("",12,false);
        advanced.addView(details);
        rowButton(advanced,"Stop conversation",v->send(RitsuControlService.ACTION_STOP));
        rowButton(advanced,"Floating mute bubble",v->enableBubble());
        rowButton(advanced,"Hide floating bubble",v->send(RitsuControlService.ACTION_HIDE_BUBBLE));
        rowButton(advanced,"Pin Quick Settings tile",v->addQuickTile());
        rowButton(advanced,"Reload feed and status",v->{refreshStatus();renderFeed();});
        root.addView(advanced);
        setContentView(root);
        renderFeed();
        refreshStatus();
    }

    private void addTab(LinearLayout tabs,String label,String id) {
        Button b=button(label,v->{channel=id;renderFeed();});
        b.setTextSize(12);
        tabs.addView(b,new LinearLayout.LayoutParams(0,dp(44),1));
    }

    private TextView label(String text,int size,boolean bold) {
        TextView t=new TextView(this);
        t.setText(text);
        t.setTextColor(Color.WHITE);
        t.setTextSize(size);
        if(bold)t.setTypeface(null,Typeface.BOLD);
        t.setGravity(Gravity.CENTER_VERTICAL);
        return t;
    }

    private Button button(String text, View.OnClickListener action) {
        Button b=new Button(this);
        b.setAllCaps(false);
        b.setText(text);
        b.setTextSize(13);
        b.setOnClickListener(action);
        b.setMinHeight(dp(44));
        return b;
    }

    private void rowButton(LinearLayout box,String text,View.OnClickListener action) {
        box.addView(button(text,action));
    }

    private void renderFeed() {
        if(transcriptRows==null)return;
        transcriptRows.removeAllViews();
        List<ConversationLedger.Entry> messages=ledger.list(channel);
        if(messages.isEmpty()) {
            TextView empty=label("No verified results in this view yet.\n" +
                ("worker".equals(channel) ? "Worker results need the authenticated Home Center bridge." :
                "Your recognized words will appear here once Android returns them."),14,false);
            empty.setPadding(dp(12),dp(18),dp(12),dp(12));
            transcriptRows.addView(empty);
        }
        for(ConversationLedger.Entry entry:messages) {
            LinearLayout bubble=new LinearLayout(this);
            bubble.setOrientation(LinearLayout.VERTICAL);
            bubble.setPadding(dp(12),dp(8),dp(12),dp(12));
            bubble.setBackgroundColor(entry.who.equals("You")?
                    Color.rgb(54,42,82):Color.rgb(35,39,53));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);
            lp.setMargins(dp(4),dp(4),dp(4),dp(9));
            transcriptRows.addView(bubble,lp);
            TextView origin=label(entry.channel.toUpperCase()+" · "+entry.who,12,true);
            bubble.addView(origin);
            TextView content=label(entry.text,16,false);
            content.setPadding(0,dp(4),0,dp(4));
            bubble.addView(content);
            TextView state=label(entry.state,11,false);
            state.setTextColor(Color.LTGRAY);
            bubble.addView(state);
        }
        feedScroll.post(()->feedScroll.fullScroll(View.FOCUS_DOWN));
    }

    private void queueTyped() {
        String text=composer.getText().toString().trim();
        if(text.isEmpty())return;
        // This is an honest local outbox until authenticated ingress exists.
        String destination = "control".equals(channel) ? "control":"dialogue";
        ledger.add(destination,"You",text,ConversationLedger.OUTBOX);
        RitsuControlService.feedRevision++;
        composer.setText("");
        renderFeed();
    }

    private void toggleMute() {
        ListeningPolicy.Mode mode=RitsuControlService.liveMode;
        if(mode==ListeningPolicy.Mode.LISTENING||mode==ListeningPolicy.Mode.RECOGNIZING)
            send(RitsuControlService.ACTION_MUTE);
        else if(mode==ListeningPolicy.Mode.MUTED)send(RitsuControlService.ACTION_RESUME);
        else requestListening();
    }

    private void requestListening() {
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},REQUEST_MIC);
            return;
        }
        send(RitsuControlService.ACTION_LISTEN);
    }

    private void send(String action) {
        try {
            Intent i=new Intent(this,RitsuControlService.class).setAction(action);
            if(Build.VERSION.SDK_INT>=26)startForegroundService(i);
            else startService(i);
        }catch(RuntimeException e){
            headerStatus.setText("Control error: "+e.getClass().getSimpleName());
        }
    }

    private void toggleAdvanced() {
        advancedVisible=!advancedVisible;
        advanced.setVisibility(advancedVisible?View.VISIBLE:View.GONE);
        refreshStatus();
    }

    private void enableBubble() {
        if(!Settings.canDrawOverlays(this)){
            pendingBubbleEnable=true;
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:"+getPackageName())));
            }catch(RuntimeException error){
                pendingBubbleEnable=false;
                headerStatus.setText("Android blocked overlay settings.");
            }
            return;
        }
        send(RitsuControlService.ACTION_SHOW_BUBBLE);
    }

    private void addQuickTile() {
        if(Build.VERSION.SDK_INT<33){
            headerStatus.setText("Add Ritsu via Quick Settings > Edit");
            return;
        }
        StatusBarManager mgr=getSystemService(StatusBarManager.class);
        if(mgr==null){headerStatus.setText("Quick Settings unavailable");return;}
        mgr.requestAddTileService(new ComponentName(this,RitsuQuickTileService.class),
                "Ritsu controls",Icon.createWithResource(this,android.R.drawable.ic_btn_speak_now),
                getMainExecutor(), code->headerStatus.setText("Quick Settings result "+code));
    }

    private void refreshStatus() {
        ListeningPolicy.Mode mode=RitsuControlService.liveMode;
        String state=mode==ListeningPolicy.Mode.LISTENING?"Listening for speech and silence"
                :mode==ListeningPolicy.Mode.RECOGNIZING?"Transcribing finalized utterance"
                :mode==ListeningPolicy.Mode.MUTED?"Microphone muted"
                :mode==ListeningPolicy.Mode.ERROR?"Microphone error":"Microphone off";
        headerStatus.setText(state+" · ChatGPT not connected");
        if(details!=null)details.setText(
                "System recognizer: "+RitsuControlService.recognitionStatus+
                "\nLast recognized: "+RitsuControlService.lastTranscript+
                "\nMedia/AEC: "+RitsuControlService.mediaGuardStatus+
                "\nError: "+(RitsuControlService.lastProblem.isEmpty()?"None":RitsuControlService.lastProblem)+
                "\nLocal outbox only. Worker feed requires Home Center."+
                "\nNo real Ritsu playback or automatic barge-in yet.");
    }

    @Override protected void onResume(){
        super.onResume();
        if(pendingBubbleEnable&&Settings.canDrawOverlays(this)){
            pendingBubbleEnable=false;
            send(RitsuControlService.ACTION_SHOW_BUBBLE);
        }
        updates.removeCallbacks(redraw);
        updates.postDelayed(redraw,350);
        renderFeed();
    }

    @Override protected void onPause(){
        updates.removeCallbacks(redraw);
        super.onPause();
    }

    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] results){
        super.onRequestPermissionsResult(code,permissions,results);
        if(code==REQUEST_MIC&&results.length>0&&results[0]==PackageManager.PERMISSION_GRANTED)
            send(RitsuControlService.ACTION_LISTEN);
        else if(code==REQUEST_MIC)headerStatus.setText("Microphone permission not granted.");
        else if(code==REQUEST_NOTIFICATIONS)refreshStatus();
    }

    private int dp(int value){
        return Math.round(value*getResources().getDisplayMetrics().density);
    }
}
