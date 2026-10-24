package com.homecenter.ritsucontrol;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.StatusBarManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Insets;
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
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.atomic.AtomicBoolean;

/** Voice-first conversation cockpit. Visible chat results from many channels
 * while the default operation is continuous mic+silence segmentation.
 * IMPORTANT: local outbox is not remote Home Center / ChatGPT delivery. */
public final class MainActivity extends Activity {
    private static final int REQUEST_MIC = 19646;
    private static final int REQUEST_NOTIFICATIONS = 19644;
    private TextView headerStatus, details;
    private EditText composer;
    private Button listenButton, muteButton;
    private TextView liveWords;
    private LinearLayout transcriptRows;
    private ScrollView feedScroll;
    private ConversationLedger ledger;
    private String channel = "all";
    private boolean pendingBubbleEnable;
    private long lastFeedRevision = -1;

    private final Handler updates = new Handler(Looper.getMainLooper());
    private final ExecutorService cloudPairWorker=Executors.newSingleThreadExecutor();
    private final AtomicBoolean cloudPairActive=new AtomicBoolean(false);
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
        // Android 15+ draws behind the system gesture bar and keyboard.
        // Apply actual status-bar, navigation and IME insets to the *whole*
        // fixed-footer chat column so its composer/controls remain tappable.
        root.setPadding(dp(12), dp(12), dp(12), dp(8));
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            root.setOnApplyWindowInsetsListener((view, windowInsets) -> {
                Insets bars = windowInsets.getInsets(WindowInsets.Type.systemBars());
                Insets keyboard = windowInsets.getInsets(WindowInsets.Type.ime());
                Insets cutout = windowInsets.getInsets(WindowInsets.Type.displayCutout());
                int top = SafeInsets.top(bars.top, cutout.top);
                int bottom = SafeInsets.bottom(bars.bottom, keyboard.bottom);
                view.setPadding(dp(12) + Math.max(bars.left, cutout.left),
                        dp(12) + top,
                        dp(12) + Math.max(bars.right, cutout.right),
                        dp(8) + bottom);
                return windowInsets;
            });
            root.requestApplyInsets();
        } else {
            root.setFitsSystemWindows(true);
        }

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

        liveWords = label("", 14, false);
        liveWords.setVisibility(View.GONE);
        liveWords.setPadding(dp(8), dp(6), dp(8), dp(6));
        root.addView(liveWords);
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
        listenButton = button("Listen",v->requestListening());
        muteButton = button("Mute",v->toggleMute());
        controls.addView(listenButton, new LinearLayout.LayoutParams(0,dp(56),1));
        controls.addView(muteButton, new LinearLayout.LayoutParams(0,dp(56),1));
        controls.addView(button("More",v->toggleAdvanced()),
                new LinearLayout.LayoutParams(0,dp(56),1));
        root.addView(controls);

        // Advanced actions live in a dialog: never push the composer
        // or the always-visible Listen/Mute footer under the keyboard.
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 30) root.requestApplyInsets();
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
        List<ConversationLedger.Entry> messages=ledger.list(
                "dialogue".equals(channel) ? "ritsu" : channel);
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
        // The main CONTROL thread owns every external user turn.
        // Secondary dialogue requires an explicit Home Center decision.
        ledger.add("control","You",text,ConversationLedger.OUTBOX);
        RitsuControlService.feedRevision++;
        send(RitsuControlService.ACTION_SYNC_NOW);
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
        String[] labels = {
                "Status and recognition errors",
                "Speech pause timing (Gboard-like)",
                "Pair with Home Center (cloud)",
                "Disconnect Home Center",
                "Ask Android to pause media",
                "Stop conversation",
                "Enable floating mute bubble",
                "Hide floating bubble",
                "Pin Quick Settings tile",
                "Reload conversation feed"
        };
        new AlertDialog.Builder(this)
                .setTitle("Ritsu controls")
                .setItems(labels, (dialog, choice) -> {
                    switch (choice) {
                        case 0:
                            new AlertDialog.Builder(this).setTitle("Voice diagnostics")
                                    .setMessage(diagnosticText())
                                    .setPositiveButton("Close", null).show();
                            break;
                        case 1: selectSpeechTiming(); break;
                        case 2: pairHomeCenter(); break;
                        case 3:
                            new AlertDialog.Builder(this)
                                    .setTitle("Disconnect Ritsu from Home Center?")
                                    .setMessage("Only the local encrypted pairing is erased. Saved messages remain on this phone.")
                                    .setPositiveButton("Disconnect", (d,w) -> {
                                        cloudPairActive.set(false);
                                        HomeCenterCloudPairing.disconnect(this);
                                        RitsuPairing.disconnect(this);
                                        HomeCenterSync.status="Home Center not paired";refreshStatus();
                                    }).setNegativeButton("Cancel",null).show();
                            break;
                        case 4: send(RitsuControlService.ACTION_MEDIA_TALK); break;
                        case 5: send(RitsuControlService.ACTION_STOP); break;
                        case 6: enableBubble(); break;
                        case 7: send(RitsuControlService.ACTION_HIDE_BUBBLE); break;
                        case 8: addQuickTile(); break;
                        case 9: refreshStatus(); renderFeed(); break;
                        default: break;
                    }
                }).setNegativeButton("Close", null).show();
    }

    private void pairHomeCenter() {
        // This is the actual Home Center CLOUD, not THECAULDRON's
        // private Tailscale gateway. The old Home Center app approves it.
        try {
            HomeCenterCloudPairing.Paired existing=HomeCenterCloudPairing.load(this);
            if(existing!=null){
                new AlertDialog.Builder(this)
                    .setTitle("Home Center cloud already paired")
                    .setMessage("Your cloud identity is stored securely in Android Keystore. " +
                        "The direct cloud conversation channel is not deployed yet, " +
                        "so this confirms account pairing, not message delivery.")
                    .setPositiveButton("Close",null).show();
                return;
            }
        }catch(RuntimeException error){
            headerStatus.setText("Cloud pairing needs repair");
        }
        if(!cloudPairActive.compareAndSet(false,true)){
            headerStatus.setText("Home Center cloud pairing already in progress");
            return;
        }
        headerStatus.setText("Requesting cloud approval from Home Center");
        cloudPairWorker.execute(()->{
            try {
                HomeCenterCloudPairing.Pending pending=HomeCenterCloudPairing.start();
                updates.post(()->showHomeCenterApproval(pending));
                boolean approved=false;
                while(System.currentTimeMillis()<pending.expiresAtMs && cloudPairActive.get()){
                    Thread.sleep(2800);
                    if(!cloudPairActive.get())return;
                    if(HomeCenterCloudPairing.poll(getApplicationContext(),pending)){
                        approved=true;break;
                    }
                }
                if(!cloudPairActive.get())return;
                if(!approved)throw new IllegalStateException("Approval expired");
                updates.post(()->{
                    // Cloud credentials are independent of the legacy LAN
                    // pair. HomeCenterSync will select cloud-first and will NOT
                    // forward queued messages to the computer gateway.
                    HomeCenterSync.status="Home Center cloud paired; conversation bridge not deployed";
                    refreshStatus();
                    new AlertDialog.Builder(this)
                        .setTitle("Home Center cloud account connected")
                        .setMessage("Home Center approved Ritsu Control directly. " +
                            "ChatGPT replies have not yet been tested from this app.")
                        .setPositiveButton("Close",null).show();
                });
            }catch(InterruptedException ignored){
                Thread.currentThread().interrupt();
            }catch(Exception error){
                updates.post(()->headerStatus.setText(
                    "Cloud pairing blocked: "+error.getClass().getSimpleName()));
            }finally{cloudPairActive.set(false);}
        });
    }

    private void showHomeCenterApproval(HomeCenterCloudPairing.Pending pending) {
        LinearLayout panel=new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(18),dp(8),dp(18),0);
        TextView instructions=label(
            "Open the OLD Home Center app, select Pair Termux Codex, " +
            "and approve this Ritsu Control request. " +
            "The request expires automatically. Keep Ritsu Control running.",14,false);
        panel.addView(instructions);
        TextView id=label("Pairing ID: "+pending.id,15,true);
        id.setTextIsSelectable(true);
        panel.addView(id);
        TextView code=label("Approval code: "+pending.code,22,true);
        code.setTextIsSelectable(true);
        panel.addView(code);
        new AlertDialog.Builder(this)
            .setTitle("Approve Ritsu Control in Home Center")
            .setView(panel)
            .setPositiveButton("Continue in Home Center",(dialog,which)->{
                headerStatus.setText("Waiting for Home Center cloud approval");
            })
            .setNegativeButton("Cancel pairing",(dialog,which)->{
                cloudPairActive.set(false);
                headerStatus.setText("Cloud pairing canceled");
            }).show();
    }

    private void selectSpeechTiming() {
        final int[] values = {2000, 3200, 5000};
        final String[] names = {
                "Quick · 2 seconds",
                "Natural · 3.2 seconds",
                "Thoughtful · 5 seconds (default)"
        };
        int selected = 2;
        for (int i = 0; i < values.length; i++) {
            if (RitsuControlService.speechPauseMs == values[i]) selected = i;
        }
        new AlertDialog.Builder(this).setTitle("Wait after I finish speaking")
                .setSingleChoiceItems(names, selected, (dialog, index) -> {
                    Intent intent = new Intent(this, RitsuControlService.class)
                            .setAction(RitsuControlService.ACTION_PAUSE_WINDOW)
                            .putExtra(RitsuControlService.EXTRA_PAUSE_MS, values[index]);
                    try {
                        if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent);
                        else startService(intent);
                    } catch (RuntimeException error) {
                        headerStatus.setText("Cannot update speech timing: "
                                + error.getClass().getSimpleName());
                    }
                    dialog.dismiss();
                }).setNegativeButton("Cancel", null).show();
    }

    private String diagnosticText() {
        return "System recognizer: " + RitsuControlService.recognitionStatus
                + "\nLast recognized: " + RitsuControlService.lastTranscript
                + "\nPending speech: " + RitsuControlService.pendingSpeechText
                + "\nSpeech pause: " + RitsuControlService.speechPauseMs + " ms"
                + "\nMedia guard: " + RitsuControlService.mediaGuardStatus
                + "\nLast error: " + (RitsuControlService.lastProblem.isEmpty()
                        ? "None" : RitsuControlService.lastProblem)
                + "\nLocal outbox only. Worker replies require Home Center."
                + "\nNo Ritsu voice playback in this build.";
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
        ListeningPolicy.Mode mode = RitsuControlService.liveMode;
        String state = mode == ListeningPolicy.Mode.RECOGNIZING ? "Google mic on"
                : mode == ListeningPolicy.Mode.MUTED ? "Mic muted"
                : mode == ListeningPolicy.Mode.ERROR ? "Recognition error"
                : mode == ListeningPolicy.Mode.LISTENING ? "Local mic active"
                : "Mic off";
        String detail = RitsuControlService.recognitionStatus;
        if (detail.length() > 75) detail = detail.substring(0, 75);
        headerStatus.setText(state + " · " + detail + "\n" + HomeCenterSync.status);
        if (listenButton != null) {
            listenButton.setText(mode == ListeningPolicy.Mode.RECOGNIZING
                    ? "Listening ●" : "Listen");
        }
        if (muteButton != null) {
            muteButton.setText(mode == ListeningPolicy.Mode.MUTED ? "Resume" : "Mute");
        }
        if (liveWords != null) {
            String draft = RitsuControlService.pendingSpeechText;
            String interim = RitsuControlService.partialTranscript;
            String text = draft.isEmpty() ? interim
                    : interim.isEmpty() ? draft : draft + " " + interim;
            if (mode == ListeningPolicy.Mode.RECOGNIZING && !text.isEmpty()) {
                liveWords.setText("Composing: " + text
                        + (interim.isEmpty() ? "  ·  thinking pause…" : ""));
                liveWords.setVisibility(View.VISIBLE);
            } else {
                liveWords.setVisibility(View.GONE);
            }
        }
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
