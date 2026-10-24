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
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.AdapterView;
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
    private RitsuWorkspace workspace;
    private Spinner tabChooser, machineChooser;
    private boolean syncingSelectors;
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
        workspace = new RitsuWorkspace(this);
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

        // These select independently persisted conversations, NOT just the
        // old channel filters. Each conversation carries a machine preset.
        LinearLayout sessions=new LinearLayout(this);
        sessions.setOrientation(LinearLayout.HORIZONTAL);
        tabChooser=new Spinner(this);
        sessions.addView(tabChooser,new LinearLayout.LayoutParams(0,dp(48),1));
        sessions.addView(button("+ Tab",v->createConversationTab()));
        root.addView(sessions);

        LinearLayout machineRow=new LinearLayout(this);
        machineRow.setOrientation(LinearLayout.HORIZONTAL);
        machineRow.setGravity(Gravity.CENTER_VERTICAL);
        TextView machineTitle=label("Machine",12,true);
        machineTitle.setPadding(0,0,dp(10),0);
        machineRow.addView(machineTitle);
        machineChooser=new Spinner(this);
        machineRow.addView(machineChooser,new LinearLayout.LayoutParams(0,dp(48),1));
        root.addView(machineRow);
        initConversationSelectors();

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
        acceptHomeCenterOAuth(getIntent());
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
                "dialogue".equals(channel) ? "ritsu" : channel,
                workspace.active().id);
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
            TextView origin=label(entry.channel.toUpperCase()+" · "+entry.who+
                    " · "+RitsuWorkspace.machine(entry.machineId).label,12,true);
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
        RitsuWorkspace.Tab active=workspace.active();
        // Machine + conversation + Instant preference + loop mode are durable
        // metadata; do not falsify acceptance by an agent when cloud turn/feed
        // integration is not yet deployed.
        ledger.addInTab(active.id,active.machineId,"control","You",text,
                ConversationLedger.OUTBOX);
        RitsuControlService.feedRevision++;
        send(RitsuControlService.ACTION_SYNC_NOW);
        composer.setText("");
        renderFeed();
    }

    /** Cockpit has a dark surface; Android platform dropdown is light. */
    private ArrayAdapter<String> newReadableSpinner(){
        return new ArrayAdapter<String>(this,
                android.R.layout.simple_spinner_item){
            @Override public View getView(int position,View convertView,
                                          android.view.ViewGroup parent){
                View v=super.getView(position,convertView,parent);
                if(v instanceof TextView)((TextView)v).setTextColor(Color.WHITE);
                return v;
            }
            @Override public View getDropDownView(int position,View convertView,
                                                   android.view.ViewGroup parent){
                View v=super.getDropDownView(position,convertView,parent);
                if(v instanceof TextView)((TextView)v).setTextColor(Color.DKGRAY);
                v.setBackgroundColor(Color.WHITE);
                return v;
            }
        };
    }

    private void initConversationSelectors() {
        ArrayAdapter<String> machines=newReadableSpinner();
        for(RitsuWorkspace.Machine m:RitsuWorkspace.MACHINES)
            machines.add(m.label);
        machineChooser.setAdapter(machines);
        machineChooser.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            @Override public void onNothingSelected(AdapterView<?> parent){}
            @Override public void onItemSelected(AdapterView<?> parent,View view,
                                                  int position,long id){
                if(syncingSelectors)return;
                try{
                    RitsuWorkspace.Tab t=workspace.active();
                    workspace.setMachine(t.id,RitsuWorkspace.MACHINES[position].id);
                    renderFeed();refreshStatus();
                }catch(RuntimeException error){
                    headerStatus.setText("Machine selection failed");
                }
            }
        });
        tabChooser.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            @Override public void onNothingSelected(AdapterView<?> parent){}
            @Override public void onItemSelected(AdapterView<?> parent,View view,
                                                  int position,long id){
                if(syncingSelectors)return;
                try{
                    java.util.List<RitsuWorkspace.Tab> items=workspace.tabs();
                    if(position>=items.size())return;
                    workspace.select(items.get(position).id);
                    refreshConversationSelectors();
                    renderFeed();refreshStatus();
                }catch(RuntimeException error){
                    headerStatus.setText("Tab selection failed");
                }
            }
        });
        refreshConversationSelectors();
    }

    private void refreshConversationSelectors(){
        syncingSelectors=true;
        try{
            java.util.List<RitsuWorkspace.Tab> items=workspace.tabs();
            ArrayAdapter<String> list=newReadableSpinner();
            int selected=0;
            String current=workspace.active().id;
            for(int i=0;i<items.size();i++){
                RitsuWorkspace.Tab t=items.get(i);
                list.add(t.title+(t.scriptCampaign?"  ⚙":""));
                if(t.id.equals(current))selected=i;
            }
            tabChooser.setAdapter(list);
            tabChooser.setSelection(selected);
            String machine=workspace.active().machineId;
            for(int i=0;i<RitsuWorkspace.MACHINES.length;i++)
                if(RitsuWorkspace.MACHINES[i].id.equals(machine))
                    machineChooser.setSelection(i);
        }finally{syncingSelectors=false;}
    }

    private void createConversationTab(){
        EditText name=new EditText(this);
        name.setSingleLine(true);name.setTextColor(Color.DKGRAY);
        name.setHint("Conversation title");
        LinearLayout panel=new LinearLayout(this);
        panel.setPadding(dp(16),0,dp(16),0);panel.addView(name);
        new AlertDialog.Builder(this).setTitle("New conversation tab")
            .setView(panel).setNegativeButton("Cancel",null)
            .setPositiveButton("Create",(dialog,which)->{
                try{
                    workspace.create(name.getText().toString());
                    refreshConversationSelectors();
                    renderFeed();refreshStatus();
                }catch(RuntimeException error){
                    headerStatus.setText("Tab not created: "+error.getMessage());
                }
            }).show();
    }

    private void requestAssetExplicitly(){
        new AlertDialog.Builder(this).setTitle("Request retrieval for this turn")
            .setItems(new String[]{"Ask for an image","Ask for a file"},(dialog,which)->{
                // Compose only an explicit owner request. DO NOT silently
                // retrieve or transfer files in a background poll.
                String prefix=which==0?
                    "Please retrieve an image for this request only: ":
                    "Please retrieve a file for this request only: ";
                composer.setText(prefix+composer.getText().toString());
                composer.setSelection(composer.length());
                composer.requestFocus();
            }).setNegativeButton("Cancel",null).show();
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
                "Connect Home Center account",
                "Disconnect Home Center",
                "Ask Android to pause media",
                "Stop conversation",
                "Enable floating mute bubble",
                "Hide floating bubble",
                "Pin Quick Settings tile",
                "Reload conversation feed",
                "Script campaign: toggle this tab",
                "Request image / file retrieval"
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
                                        HomeCenterOAuth.clearPending(this);
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
                        case 10:
                            workspace.toggleScriptCampaign(workspace.active().id);
                            refreshConversationSelectors();refreshStatus();
                            break;
                        case 11:requestAssetExplicitly();break;
                        default: break;
                    }
                }).setNegativeButton("Close", null).show();
    }

    private void pairHomeCenter() {
        try {
            HomeCenterCloudPairing.Paired existing=HomeCenterCloudPairing.load(this);
            if(existing!=null && existing.oauthClientId.length()>0) {
                new AlertDialog.Builder(this)
                    .setTitle("Home Center account connected")
                    .setMessage("Your Home Center sign-in is encrypted on this phone. " +
                        "The cloud conversation reply transport is not yet deployed.")
                    .setPositiveButton("Close",null).show();
                return;
            }
        }catch(RuntimeException ignored){
            headerStatus.setText("Home Center session needs sign-in");
        }
        if(!cloudPairActive.compareAndSet(false,true)) {
            headerStatus.setText("Home Center sign-in already running");
            return;
        }
        headerStatus.setText("Preparing Home Center sign-in");
        cloudPairWorker.execute(()->{
            try{
                final String authorize=HomeCenterOAuth.begin(getApplicationContext());
                updates.post(()->{
                    try {
                        // External browser is mandatory. Never collect Google
                        // passwords in WebView or use a shared APK credential.
                        Intent view=new Intent(Intent.ACTION_VIEW, Uri.parse(authorize));
                        view.addCategory(Intent.CATEGORY_BROWSABLE);
                        startActivity(view);
                        // Browser sign-in is independently bound by persisted
                        // PKCE state. The Activity can be retried if the user
                        // closes Chrome without completing authorization.
                        cloudPairActive.set(false);
                        headerStatus.setText("Complete Home Center sign-in in your browser");
                    }catch(RuntimeException browserError){
                        cloudPairActive.set(false);
                        HomeCenterOAuth.clearPending(getApplicationContext());
                        headerStatus.setText("Could not open a secure browser");
                    }
                });
            }catch(Exception error){
                cloudPairActive.set(false);
                updates.post(()->headerStatus.setText(
                    "Home Center sign-in unavailable: "+error.getClass().getSimpleName()));
            }
        });
    }

    /**
     * Android delivers this intent only after a user-completed Home Center
     * browser redirect. The short-lived state and PKCE proof prevent another
     * Android app from completing an unsolicited or replayed login.
     */
    private void acceptHomeCenterOAuth(Intent intent) {
        if(intent==null||intent.getData()==null||
           !"ritsucontrol".equals(intent.getData().getScheme()))return;
        Uri callback=intent.getData();
        intent.setData(null);
        // The saved OAuth state, rather than an in-memory Activity flag,
        // establishes whether this callback belongs to this app.
        cloudPairActive.set(true);
        headerStatus.setText("Verifying Home Center sign-in");
        cloudPairWorker.execute(()->{
            try{
                HomeCenterCloudPairing.Paired paired=
                    HomeCenterOAuth.complete(getApplicationContext(),callback);
                HomeCenterCloudPairing.save(getApplicationContext(),paired);
                HomeCenterSync.status="Home Center cloud paired; conversation bridge not deployed";
                updates.post(()->{
                    cloudPairActive.set(false);
                    refreshStatus();
                    new AlertDialog.Builder(this)
                        .setTitle("Home Center connected")
                        .setMessage("Ritsu Control signed in directly and stored its " +
                            "own Home Center credentials securely. No pairing codes " +
                            "or Termux scripts required. Conversation reply routing " +
                            "has not yet been deployed.")
                        .setPositiveButton("Done",null).show();
                });
            }catch(Exception error){
                HomeCenterOAuth.clearPending(getApplicationContext());
                updates.post(()->{
                    cloudPairActive.set(false);
                    headerStatus.setText(
                        "Home Center sign-in failed: "+error.getClass().getSimpleName());
                });
            }
        });
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        acceptHomeCenterOAuth(intent);
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
        RitsuWorkspace.Tab selected=workspace.active();
        headerStatus.setText(state + " · " + detail + "\n" + HomeCenterSync.status+
            "\nTab: "+selected.title+" · Machine: "+
            RitsuWorkspace.machine(selected.machineId).label+
            " · Instant preferred · Script loop "+(selected.scriptCampaign?"ON":"OFF"));
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
