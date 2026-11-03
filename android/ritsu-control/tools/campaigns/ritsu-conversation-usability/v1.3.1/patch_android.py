#!/usr/bin/env python3
"""Source-aware, fail-closed Ritsu usability patch, no install/no signing.
Never modifies the original; stages an isolated project copy first.
"""
from pathlib import Path
import re,sys,hashlib

def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected one source anchor, saw {n}')
    return s.replace(old,new,1)

def patch(src:Path,assets:Path):
    java=src/'app/src/main/java/com/homecenter/ritsucontrol'
    main=java/'MainActivity.java'
    wk=java/'RitsuWorkspace.java'
    required=(main,wk,java/'RitsuLocalSync.java',java/'RitsuPairing.java',java/'ConversationLedger.java')
    for path in required:
        if not path.is_file():raise RuntimeError(f'MISSING_REQUIRED_SOURCE={path.name}')
    s=main.read_text(encoding='utf8')
    if 'RITSU_CONVERSATION_USABILITY_V1_3_1' in s:
        raise RuntimeError('Patch already installed; refuse to double-apply')
    if 'private ScrollView feedScroll;' not in s or 'renderFeed()' not in s:
        raise RuntimeError('Source identity not supported; no file changed')
    s=one(s,'    private ScrollView feedScroll;','''    private ScrollView feedScroll;
    // RITSU_CONVERSATION_USABILITY_V1_3_1: OPEN tabs are NOT chat deletion.
    private RitsuConversationDeck conversationDeck;
    private String drawnConversation=null;
    private final android.content.SharedPreferences.OnSharedPreferenceChangeListener unusedDeckWatcher=null;
''','fields')
    s=one(s,'TextView title = label("Ritsu  ·  Conversation Hub", 21, true);','TextView title = label("Ritsu", 19, true);','title')
    s=one(s,'        root.addView(title);','''        LinearLayout titleBar=new LinearLayout(this);
        titleBar.setOrientation(LinearLayout.HORIZONTAL);
        Button conversations=button("☰",v->{if(conversationDeck!=null)conversationDeck.showDrawer();});
        conversations.setContentDescription("Conversations menu");
        titleBar.addView(conversations,new LinearLayout.LayoutParams(dp(48),dp(44)));
        titleBar.addView(title,new LinearLayout.LayoutParams(0,dp(44),1));
        Button connection=button("●",v->showDirectLinkStatus());
        connection.setContentDescription("Direct link status");
        titleBar.addView(connection,new LinearLayout.LayoutParams(dp(48),dp(44)));
        root.addView(titleBar);''','header')
    s=one(s,'        root.addView(headerStatus);','        headerStatus.setVisibility(View.GONE);','header visibility')
    campaign_button='        root.addView(button("Campaigns", v->startActivity(new Intent(this, CampaignActivity.class))));'
    if s.count(campaign_button)!=1:raise RuntimeError('Accepted campaign button not found; source may not be the installed Fresh integrated app')
    s=s.replace(campaign_button,'        // Campaigns remains accessible through the conversation drawer.',1)

    s=one(s,'        root.addView(outboxWarning);','        // Pending detail stays available in the existing More/Status menu.\n        outboxWarning.setVisibility(View.GONE);','outbox visibility')
    s=one(s,'        root.addView(sessions);','        // Old selectors remain initialized and usable in code, not on the default screen.','sessions hide')
    s=one(s,'        root.addView(machineRow);','        // Machine presets remain available through the existing advanced controls.','machine hide')
    s=one(s,'        root.addView(tabs);','''        // Channel filters remain a private advanced compatibility view.
        conversationDeck=new RitsuConversationDeck(this,workspace,
            ()->deckSelectionChanged(),()->toggleAdvanced());
        root.addView(conversationDeck.view(),new LinearLayout.LayoutParams(-1,dp(46)));''','tab strip')
    s=one(s,'        root.addView(controls);','        // Existing Listen/Mute/More actions move to the conversations/controls drawer.','controls hide')
    s=one(s,'        renderFeed();\n        refreshStatus();\n        send(RitsuControlService.ACTION_SYNC_NOW);','''        composer.setText(conversationDeck.draft(workspace.active().id));
        renderFeed();
        refreshStatus();
        send(RitsuControlService.ACTION_SYNC_NOW);''','init draft')
    old=s[s.index('    private void renderFeed() {'):s.index('    private void showDirectLinkStatus() {')]
    new='''    private void rememberReadingPosition(){
        if(drawnConversation==null||feedScroll==null||transcriptRows==null)return;
        String anchor="";int offset=0;int scroll=feedScroll.getScrollY();
        for(int i=0;i<transcriptRows.getChildCount();i++){
            View v=transcriptRows.getChildAt(i);
            if(v.getBottom()>scroll){
                Object id=v.getTag();
                if(id instanceof String){anchor=(String)id;offset=v.getTop()-scroll;}
                break;
            }
        }
        if(!anchor.isEmpty()){
            android.content.SharedPreferences st=getSharedPreferences("ritsu_scroll_anchor_v1",MODE_PRIVATE);
            st.edit().putString("anchor_"+drawnConversation,anchor)
                .putInt("offset_"+drawnConversation,offset).commit();
        }
        if(composer!=null&&conversationDeck!=null)conversationDeck.setDraft(
            drawnConversation,composer.getText().toString());
    }
    private void deckSelectionChanged(){
        rememberReadingPosition();
        String id=workspace.active().id;
        if(composer!=null)composer.setText(conversationDeck.draft(id));
        refreshConversationSelectors();renderFeed();refreshStatus();
    }
    private void renderFeed() {
        if(transcriptRows==null)return;
        final String newTab=workspace.active().id;
        final boolean same=newTab.equals(drawnConversation);
        final boolean previousAtBottom=feedScroll.getChildCount()==0 ||
            feedScroll.getScrollY()+feedScroll.getHeight() >=
              transcriptRows.getHeight()-dp(28);
        if(same && !previousAtBottom)rememberReadingPosition();
        if(!same)rememberReadingPosition();
        drawnConversation=newTab;
        transcriptRows.removeAllViews();
        if(conversationDeck!=null&&!conversationDeck.isOpen(newTab)){
            TextView empty=label("No tab open. Choose a conversation from ☰.",15,false);
            transcriptRows.addView(empty);return;
        }
        List<ConversationLedger.Entry> messages=ledger.list(
                "dialogue".equals(channel)?"ritsu":channel,newTab);
        if(messages.isEmpty()){
            TextView empty=label("No messages in this conversation yet.",15,false);
            empty.setPadding(dp(12),dp(18),dp(12),dp(12));
            transcriptRows.addView(empty);
        }
        for(ConversationLedger.Entry entry:messages){
            LinearLayout bubble=new LinearLayout(this);
            bubble.setTag(entry.id);bubble.setOrientation(LinearLayout.VERTICAL);
            bubble.setPadding(dp(12),dp(8),dp(12),dp(12));
            bubble.setBackgroundColor(entry.who.equals("You")?
                    Color.rgb(54,42,82):Color.rgb(35,39,53));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);
            lp.setMargins(dp(4),dp(4),dp(4),dp(9));transcriptRows.addView(bubble,lp);
            TextView origin=label(entry.who,12,true);bubble.addView(origin);
            TextView content=label(entry.text,16,false);
            content.setPadding(0,dp(4),0,dp(4));
            content.setTextIsSelectable(true);bubble.addView(content);
            if("You".equals(entry.who)&&!"COMPLETED".equals(entry.state)){
                TextView state=label(entry.state,11,false);
                state.setTextColor(Color.rgb(255,193,113));bubble.addView(state);
            }
        }
        android.content.SharedPreferences st=getSharedPreferences("ritsu_scroll_anchor_v1",MODE_PRIVATE);
        final String anchor=st.getString("anchor_"+newTab,"");
        final int offset=st.getInt("offset_"+newTab,0);
        // Changing tabs restores their individual reading anchor; new replies
        // do NOT forcibly yank a reader back to the bottom.
        final boolean follow=same && previousAtBottom;
        feedScroll.post(()->{
            if(!newTab.equals(workspace.active().id))return;
            if(follow || (anchor.isEmpty() && !same)){
                feedScroll.fullScroll(View.FOCUS_DOWN);return;
            }
            for(int i=0;i<transcriptRows.getChildCount();i++){
                View v=transcriptRows.getChildAt(i);
                if(anchor.equals(v.getTag())){
                    feedScroll.scrollTo(0,Math.max(0,v.getTop()-offset));return;
                }
            }
            if(!same)feedScroll.scrollTo(0,0);
        });
    }

'''
    s=one(s,old,new,'renderFeed bounded replacement')
    s=one(s,'        // The operator already pressed Send. No second confirmation:', '''        if(conversationDeck!=null&&!conversationDeck.isOpen(workspace.active().id)){
            new AlertDialog.Builder(this).setMessage("Open a conversation tab before sending.")
                .setPositiveButton("OK",null).show();return;
        }
        if(RitsuConversationLinks.blocked(this,workspace.active().id)){
            new AlertDialog.Builder(this).setMessage("ChatGPT link not verified. No message was sent.")
                .setPositiveButton("OK",null).show();return;
        }
        // The operator already pressed Send. No second confirmation:''','send guard')
    s=one(s,'            composer.setText("");\n            renderFeed();','''            composer.setText("");
            if(conversationDeck!=null)conversationDeck.setDraft(active.id,"");
            renderFeed();''','draft reset')
    s=one(s,'                     workspace.create(name.getText().toString());\n                     refreshConversationSelectors();', '''                     workspace.create(name.getText().toString());
                     conversationDeck.ensureSelectedOpen();
                     refreshConversationSelectors();'''.replace('                     ','                    '),'tab creation') if False else s
    # Exact whitespace above is version-dependent, protect with a direct known sequence.
    s=one(s,'                    workspace.create(name.getText().toString());\n                    refreshConversationSelectors();','''                    workspace.create(name.getText().toString());
                    conversationDeck.ensureSelectedOpen();
                    refreshConversationSelectors();''','new tab opening')
    s=one(s,'        updates.removeCallbacks(redraw);\n        super.onPause();','''        rememberReadingPosition();
        updates.removeCallbacks(redraw);
        super.onPause();''','pause preserve')
    # On-resume must never reselect the oldest stale tab or clear a draft.
    s=one(s,'        renderFeed();\n    }\n\n    @Override protected void onPause()', '''        if(conversationDeck!=null)conversationDeck.refresh();
        renderFeed();
    }

    @Override protected void onPause()''','resume refresh')
    workspace=wk.read_text(encoding='utf8')
    workspace=one(workspace,'if(raw.length()>=12)throw new IllegalStateException("12 conversation tabs maximum");',
                  'if(raw.length()>=200)throw new IllegalStateException("200 stored conversations maximum");','workspace cap')
    # Guard all source targets before first write; these are staged isolated sources.
    targets={main:s,wk:workspace}
    for name in ('RitsuConversationDeck.java','RitsuConversationLinks.java'):
        dest=java/name
        if dest.exists():raise RuntimeError(f'Existing {name} needs source reconciliation')
        targets[dest]=(assets/name).read_text(encoding='utf8')
    for dest,text in targets.items():
        dest.write_text(text,encoding='utf8')
    print('ANDROID_PATCH=UI_TABS_SCROLL_DRAWER_AND_CATALOG_CLIENT_STAGED')
    print('ANDROID_PATCH_CLASSES='+','.join(t.name for t in targets))
    for dest in targets:print('PATCH_SHA256_'+dest.name+'='+hashlib.sha256(dest.read_bytes()).hexdigest())

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: patch_android.py isolated_android_project packet_dir')
    try:patch(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
    except Exception as e:
        print('ANDROID_PATCH=BLOCKED')
        print('ANDROID_PATCH_REASON='+str(e).replace('\n',' ')[:300]);raise SystemExit(1)
