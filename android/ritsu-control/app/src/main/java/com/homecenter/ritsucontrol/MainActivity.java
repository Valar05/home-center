package com.homecenter.ritsucontrol;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.StatusBarManager;
import android.content.ComponentName;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
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
    private static final int REQUEST_SNIPPET_IMPORT = 19652;
    private static final int REQUEST_SNIPPET_EXPORT = 19653;
    private TextView headerStatus, details, outboxWarning;
    private EditText composer;
    private Button listenButton, muteButton, sendButton, stickyButton;
    private StickySnippets stickySnippets;
    private String pendingSnippetTab;
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
        stickySnippets = new StickySnippets(this);
        if(savedInstanceState!=null)
            pendingSnippetTab=savedInstanceState.getString("pendingSnippetTab");
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
        headerStatus = label("Mic off · Laptop link not paired", 12, false);
        headerStatus.setPadding(0, dp(5), 0, dp(12));
        root.addView(headerStatus);

        outboxWarning=label("",13,true);
        outboxWarning.setTextColor(Color.rgb(255,193,113));
        outboxWarning.setPadding(dp(10),dp(8),dp(10),dp(8));
        outboxWarning.setOnClickListener(view->showPendingMessages());
        root.addView(outboxWarning);

        // These select independently persisted conversations, NOT just the
        // old channel filters. Each conversation carries a machine preset.
        LinearLayout sessions=new LinearLayout(this);
        sessions.setOrientation(LinearLayout.HORIZONTAL);
        tabChooser=new Spinner(this);
        sessions.addView(tabChooser,new LinearLayout.LayoutParams(0,dp(48),1));
        sessions.addView(button("+ Tab",v->createConversationTab()));
        stickyButton=button("Sticky",v->showStickySnippets());
        sessions.addView(stickyButton);
        updateStickyButton();
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
        composer.setHint("Message Ritsu through ChatGPT…");
        composer.setTextSize(15);
        composer.setInputType(InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_FLAG_MULTI_LINE |
                InputType.TYPE_TEXT_FLAG_AUTO_CORRECT |
                InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        composer.setContentDescription("Optional message with Gboard typing and autocorrect");
        compose.addView(composer,new LinearLayout.LayoutParams(0,dp(56),1));
        sendButton=button("Send",v->queueTyped());
        compose.addView(sendButton);
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
        send(RitsuControlService.ACTION_SYNC_NOW);
        updates.post(()->{
            if(RitsuPairing.load(this)==null)pairTheCauldron();
        });
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
                ("worker".equals(channel) ? "Worker results are not enabled in local conversation mode." :
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
            TextView state=label("You".equals(entry.who) &&
                !"COMPLETED".equals(entry.state)
                ? ("WAITING_FOR_HOME_CENTER".equals(entry.state)
                    ? "LOCAL ONLY · not sent"
                    : entry.state)
                : entry.state,11,false);
            state.setTextColor("You".equals(entry.who) &&
                !"COMPLETED".equals(entry.state)
                ? Color.rgb(255,193,113) : Color.LTGRAY);
            bubble.addView(state);
        }
        feedScroll.post(()->feedScroll.fullScroll(View.FOCUS_DOWN));
    }

    private void showDirectLinkStatus() {
        new AlertDialog.Builder(this).setTitle("Direct Tailscale link")
            .setMessage(RitsuLocalSync.status.replace("Home Center","Local transport"))
            .setPositiveButton("Close",null).show();
    }

    private void queueTyped() {
        String text=composer.getText().toString().trim();
        if(text.isEmpty())return;
        if(RitsuPairing.load(this)==null){
            headerStatus.setText("Pair THECAULDRON to send ChatGPT messages");
            pairTheCauldron();
            return;
        }
        // The operator already pressed Send. No second confirmation:
        // retain the exact originating tab and durably queue before clearing.
        RitsuWorkspace.Tab active=workspace.active();
        try {
            ledger.addInTab(active.id,active.machineId,
                "control","You",StickyText.compose(text,stickySnippets.forTab(active.id)),
                "LOCAL_QUEUED");
            RitsuControlService.feedRevision++;
            composer.setText("");
            renderFeed();
            send(RitsuControlService.ACTION_SYNC_NOW);
            refreshStatus();
        } catch(RuntimeException error) {
            // Never discard an unpersisted draft.
            headerStatus.setText("Message not saved: "+error.getClass().getSimpleName());
        }
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
        updateStickyButton();
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


    /** Sticky context belongs to the conversation tab, not channel filters.
     * It is snapshotted into every outbound turn, typed or spoken.
     */
    private void updateStickyButton(){
        if(stickyButton==null||stickySnippets==null)return;
        String text=stickySnippets.forTab(workspace.active().id);
        stickyButton.setText(text.isEmpty()?"Sticky":"Sticky ●");
        stickyButton.setContentDescription(text.isEmpty()
            ?"Edit persistent context for this tab"
            :"Sticky context active in this tab; edit or insert saved snippet");
    }

    private void stickyFailure(Exception error){
        headerStatus.setText("Sticky text: "+error.getMessage());
    }

    private void showStickySnippets(){
        final String tabId=workspace.active().id;
        final EditText editor=new EditText(this);
        editor.setText(stickySnippets.forTab(tabId));
        editor.setTextColor(Color.DKGRAY);
        editor.setHint("Read campaign etiquette before every reply...");
        editor.setSingleLine(false);
        editor.setMinLines(4);
        editor.setMaxLines(9);
        editor.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        final LinearLayout panel=new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(16),dp(8),dp(16),dp(8));
        TextView help=label("Included with EVERY sent message in this tab, including voice. "
            +"This is user context, not a guaranteed system lock.",12,false);
        help.setTextColor(Color.DKGRAY);
        panel.addView(help);
        panel.addView(editor);
        final LinearLayout actions=new LinearLayout(this);
        actions.setOrientation(LinearLayout.VERTICAL);
        final LinearLayout first=new LinearLayout(this);
        first.setOrientation(LinearLayout.HORIZONTAL);
        first.addView(button("Insert saved",v->chooseQuickSnippet(editor)),
                new LinearLayout.LayoutParams(0,dp(48),1));
        first.addView(button("Save quick",v->saveQuickSnippet(editor)),
                new LinearLayout.LayoutParams(0,dp(48),1));
        actions.addView(first);
        final LinearLayout second=new LinearLayout(this);
        second.setOrientation(LinearLayout.HORIZONTAL);
        second.addView(button("Import .txt",v->{
            try{
                stickySnippets.setForTab(tabId,editor.getText().toString());
                updateStickyButton();
                pendingSnippetTab=tabId;
                Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT)
                    .addCategory(Intent.CATEGORY_OPENABLE).setType("text/plain");
                startActivityForResult(pick,REQUEST_SNIPPET_IMPORT);
            }catch(Exception e){stickyFailure(e);}
        }),new LinearLayout.LayoutParams(0,dp(48),1));
        second.addView(button("Export .txt",v->{
            try{
                stickySnippets.setForTab(tabId,editor.getText().toString());
                updateStickyButton();
                pendingSnippetTab=tabId;
                Intent create=new Intent(Intent.ACTION_CREATE_DOCUMENT)
                    .addCategory(Intent.CATEGORY_OPENABLE).setType("text/plain");
                create.putExtra(Intent.EXTRA_TITLE,"ritsu-sticky-"+tabId+".txt");
                startActivityForResult(create,REQUEST_SNIPPET_EXPORT);
            }catch(Exception e){stickyFailure(e);}
        }),new LinearLayout.LayoutParams(0,dp(48),1));
        actions.addView(second);
        panel.addView(actions);
        new AlertDialog.Builder(this).setTitle("Sticky snippets · "+workspace.active().title)
            .setView(panel).setNegativeButton("Cancel",null)
            .setPositiveButton("Save for this tab",(d,w)->{
                try{stickySnippets.setForTab(tabId,editor.getText().toString());
                    updateStickyButton();
                }catch(Exception e){stickyFailure(e);}
            }).show();
    }

    private void chooseQuickSnippet(EditText editor){
        final java.util.List<StickySnippets.Item> items;
        try{items=stickySnippets.library();}
        catch(Exception e){stickyFailure(e);return;}
        if(items.isEmpty()){
            new AlertDialog.Builder(this).setTitle("No quick snippets yet")
                .setMessage("Save a named snippet, or import a .txt file from Documents.")
                .setPositiveButton("OK",null).show();
            return;
        }
        String[] names=new String[items.size()];
        for(int i=0;i<items.size();i++)names[i]=items.get(i).title;
        new AlertDialog.Builder(this).setTitle("Insert into existing sticky text")
            .setItems(names,(d,index)->{
                try{
                    editor.setText(StickyText.append(editor.getText().toString(),
                            items.get(index).text));
                    editor.setSelection(editor.length());
                }catch(Exception e){stickyFailure(e);}
            }).setNegativeButton("Cancel",null).show();
    }

    private void saveQuickSnippet(EditText editor){
        final EditText name=new EditText(this);
        name.setSingleLine(true);
        name.setTextColor(Color.DKGRAY);
        name.setHint("Snippet title");
        new AlertDialog.Builder(this).setTitle("Save quick snippet")
            .setView(name).setNegativeButton("Cancel",null)
            .setPositiveButton("Save",(d,w)->{
                try{stickySnippets.addToLibrary(
                    name.getText().toString(),editor.getText().toString());
                }catch(Exception e){stickyFailure(e);}
            }).show();
    }

    @Override protected void onSaveInstanceState(Bundle out){
        super.onSaveInstanceState(out);
        out.putString("pendingSnippetTab",pendingSnippetTab);
    }

    @Override protected void onActivityResult(int code,int result,Intent data){
        super.onActivityResult(code,result,data);
        if(code!=REQUEST_SNIPPET_IMPORT&&code!=REQUEST_SNIPPET_EXPORT)return;
        final String tabId=pendingSnippetTab;
        pendingSnippetTab=null;
        if(result!=RESULT_OK||data==null||data.getData()==null)return;
        if(tabId==null){headerStatus.setText("Snippet file tab lost; no changes made");return;}
        try{
            Uri uri=data.getData();
            if(code==REQUEST_SNIPPET_EXPORT){
                byte[] bytes=stickySnippets.forTab(tabId).getBytes(StandardCharsets.UTF_8);
                if(bytes.length==0)throw new IllegalArgumentException("No text to export");
                try(OutputStream output=getContentResolver().openOutputStream(uri,"wt")){
                    if(output==null)throw new IllegalStateException("Cannot open output document");
                    output.write(bytes);
                }
                headerStatus.setText("Sticky text saved as independent .txt file");
            }else{
                ByteArrayOutputStream bytes=new ByteArrayOutputStream();
                try(InputStream input=getContentResolver().openInputStream(uri)){
                    if(input==null)throw new IllegalStateException("Cannot open document");
                    byte[] buffer=new byte[1024];int n;
                    while((n=input.read(buffer))!=-1){
                        if(bytes.size()+n>16000)
                            throw new IllegalArgumentException("Snippet file is too large");
                        bytes.write(buffer,0,n);
                    }
                }
                String imported=bytes.toString(StandardCharsets.UTF_8.name());
                stickySnippets.setForTab(tabId,
                    StickyText.append(stickySnippets.forTab(tabId),imported));
                headerStatus.setText("Snippet inserted into tab without replacing text");
            }
            updateStickyButton();
        }catch(Exception e){stickyFailure(e);}
    }

    private void showPendingMessages(){
        java.util.List<ConversationLedger.Entry> pending=ledger.unsent();
        if(pending.isEmpty()){
            new AlertDialog.Builder(this).setTitle("Phone outbox")
                .setMessage("No unsent messages. New messages use direct Tailscale streaming.")
                .setPositiveButton("Close",null).show();
            return;
        }
        String[] descriptions=new String[pending.size()];
        for(int i=0;i<pending.size();i++){
            ConversationLedger.Entry e=pending.get(i);
            String preview=e.text.replace('\n',' ');
            if(preview.length()>70)preview=preview.substring(0,70)+"…";
            descriptions[i]=e.tabId+" · "+e.state+" · "+preview;
        }
        new AlertDialog.Builder(this)
            .setTitle("Pending conversation turns ("+pending.size()+")")
            .setMessage("Local-only and remote-pending turns are distinct. A verified browser reply changes its state to COMPLETED. Select to view / copy.")
            .setItems(descriptions,(dialog,index)->{
                ConversationLedger.Entry entry=pending.get(index);
                new AlertDialog.Builder(this)
                    .setTitle(entry.state+" · "+entry.tabId)
                    .setMessage(entry.text)
                    .setNegativeButton("Close",null)
                    .setPositiveButton("Copy text",(d,w)->{
                        ClipboardManager clipboard=(ClipboardManager)
                            getSystemService(Context.CLIPBOARD_SERVICE);
                        if(clipboard!=null)clipboard.setPrimaryClip(
                            ClipData.newPlainText("Ritsu unsent message",
                                entry.text));
                    }).show();
            })
            .setNegativeButton("Close",null).show();
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
                "Pair THECAULDRON",
                "Unpair THECAULDRON",
                "Ask Android to pause media",
                "Stop conversation",
                "Enable floating mute bubble",
                "Hide floating bubble",
                "Pin Quick Settings tile",
                "Reload conversation feed",
                "Script campaign: toggle this tab",
                "Request image / file retrieval",
                "Pending and streaming messages",
                "Direct link status"
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
                        case 2: pairTheCauldron(); break;
                        case 3:
                            new AlertDialog.Builder(this)
                                .setTitle("Unpair THECAULDRON?")
                                .setMessage("This removes the encrypted local device token. Saved messages remain.")
                                .setPositiveButton("Unpair",(d,w)->{
                                    RitsuPairing.disconnect(this);
                                    getSharedPreferences("ritsu_local_sse_cursor_v1",MODE_PRIVATE)
                                        .edit().putLong("seq",0).commit();
                                    RitsuLocalSync.status="THECAULDRON unpaired";
                                    refreshStatus();
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
                        case 12:showPendingMessages();break;
                        case 13:showDirectLinkStatus();break;
                        default: break;
                    }
                }).setNegativeButton("Close", null).show();
    }

    /** One-time device pairing. The token is entered on the device and
     * sealed with Android Keystore. Nothing is sent to Home Center cloud.
     */
    private void pairTheCauldron() {
        final EditText server=new EditText(this);
        server.setSingleLine(true);
        server.setText("http://100.68.37.106:19646");
        server.setHint("Tailscale IP and port");
        final EditText token=new EditText(this);
        token.setSingleLine(true);
        token.setHint("Device token from THECAULDRON");
        token.setInputType(InputType.TYPE_CLASS_TEXT |
            InputType.TYPE_TEXT_VARIATION_PASSWORD);
        LinearLayout inputs=new LinearLayout(this);
        inputs.setOrientation(LinearLayout.VERTICAL);
        inputs.setPadding(dp(14),dp(6),dp(14),0);
        inputs.addView(server);
        inputs.addView(token);
        new AlertDialog.Builder(this)
            .setTitle("Pair THECAULDRON")
            .setMessage("One-time direct Tailscale pairing. No Home Center cloud traffic. The laptop must be online.")
            .setView(inputs)
            .setNegativeButton("Cancel",null)
            .setPositiveButton("Pair",(dialog,which)->{
                try{
                    RitsuPairing.save(this,server.getText().toString(),
                        token.getText().toString());
                    getSharedPreferences("ritsu_local_sse_cursor_v1",MODE_PRIVATE)
                        .edit().putLong("seq",0).commit();
                    RitsuLocalSync.status="Paired · connecting to THECAULDRON";
                    send(RitsuControlService.ACTION_SYNC_NOW);
                    refreshStatus();
                }catch(RuntimeException error){
                    headerStatus.setText("Pairing failed: "+error.getMessage());
                }
            }).show();
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        // Cloud OAuth retired from the active conversation path.
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
                + "\nChatGPT text streams through THECAULDRON over Tailscale."
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
        headerStatus.setText(state + " · " + detail + "\n" + RitsuLocalSync.status+
            "\nTab: "+selected.title+" · Machine: "+
            RitsuWorkspace.machine(selected.machineId).label+
            " · Instant preferred · Script loop "+(selected.scriptCampaign?"ON":"OFF"));
        int unsent=ledger.pendingCount();
        outboxWarning.setText("Direct Tailscale · "+unsent+" pending"+
            (unsent==0?"":" · Tap to inspect"));
        outboxWarning.setContentDescription("Direct laptop streaming. "+
            unsent+" pending turns. Tap to inspect.");
        if(sendButton!=null){
            sendButton.setText("Send");
            sendButton.setContentDescription("Send to ChatGPT over the Tailscale laptop connection");
        }
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
