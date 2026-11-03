package com.homecenter.ritsucontrol;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.json.JSONArray;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/** Ritsu's UI tab state is deliberately independent of local conversation lifetime,
 * Playwright Chrome tabs, queued turns and ChatGPT's remote archive operation. */
final class RitsuConversationDeck {
    private final Activity a;
    private final RitsuWorkspace work;
    private final SharedPreferences store;
    private final Runnable changed;
    private final Runnable controls;
    private final HorizontalScrollView strip;
    private final LinearLayout row;
    private final LinkedHashSet<String> open=new LinkedHashSet<>();
    private final LinkedHashSet<String> archived=new LinkedHashSet<>();
    private String selectedBefore="";
    RitsuConversationDeck(Activity activity,RitsuWorkspace workspace,Runnable onChanged,Runnable onControls) {
        a=activity;work=workspace;changed=onChanged;controls=onControls;
        store=a.getSharedPreferences("ritsu_conversation_deck_v1",Activity.MODE_PRIVATE);
        strip=new HorizontalScrollView(a);
        strip.setHorizontalScrollBarEnabled(false);
        strip.setFillViewport(false);
        row=new LinearLayout(a);row.setOrientation(LinearLayout.HORIZONTAL);
        strip.addView(row);
        loadSet("open",open);loadSet("archived",archived);
        if(!store.contains("open"))open.add(work.active().id);
        open.removeAll(archived);
        // An intentionally closed LAST tab stays closed across app restarts.
        persist();
        refresh();
    }
    View view(){return strip;}
    private int dp(int d){return (int)(a.getResources().getDisplayMetrics().density*d+.5f);}
    private void loadSet(String key,LinkedHashSet<String> dest){
        try{JSONArray arr=new JSONArray(store.getString(key,"[]"));for(int i=0;i<arr.length();i++){
            String v=arr.optString(i,"");if(v.matches("[A-Za-z0-9_-]{4,80}"))dest.add(v);
        }}catch(Exception error){throw new IllegalStateException("Saved tab state unreadable; no reset",error);}
    }
    private void persist(){
        JSONArray o=new JSONArray(),ar=new JSONArray();for(String v:open)o.put(v);for(String v:archived)ar.put(v);
        if(!store.edit().putString("open",o.toString()).putString("archived",ar.toString()).commit())
            throw new IllegalStateException("Tab state not saved");
    }
    private String title(RitsuWorkspace.Tab t){
        String custom=store.getString("title_"+t.id,"").trim();return custom.isEmpty()?t.title:custom;
    }
    private Button small(String label,View.OnClickListener click){
        Button b=new Button(a);b.setAllCaps(false);b.setText(label);b.setTextSize(12);
        b.setMinHeight(dp(42));b.setMinimumWidth(dp(44));b.setOnClickListener(click);return b;
    }
    private RitsuWorkspace.Tab byId(String id){for(RitsuWorkspace.Tab t:work.tabs())if(t.id.equals(id))return t;return null;}
    void refresh(){
        row.removeAllViews();
        String active=work.active().id;int activeChild=-1;
        ArrayList<String> missing=new ArrayList<>();
        for(String id:open){
            RitsuWorkspace.Tab t=byId(id);if(t==null||archived.contains(id)){missing.add(id);continue;}
            LinearLayout cell=new LinearLayout(a);cell.setOrientation(LinearLayout.HORIZONTAL);
            cell.setGravity(Gravity.CENTER_VERTICAL);
            if(id.equals(active))cell.setBackgroundColor(Color.rgb(65,48,96));
            else cell.setBackgroundColor(Color.rgb(38,38,53));
            Button name=small(title(t),v->select(id));
            name.setContentDescription("Open conversation "+title(t));
            cell.addView(name);
            Button close=small("×",v->close(id));close.setContentDescription("Close tab "+title(t)+" without deleting conversation");
            cell.addView(close,new LinearLayout.LayoutParams(dp(44),dp(44)));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-2,dp(44));lp.setMargins(0,0,dp(4),0);
            row.addView(cell,lp);
            if(id.equals(active))activeChild=row.getChildCount()-1;
        }
        if(!missing.isEmpty()){open.removeAll(missing);persist();}
        final int chosen=activeChild;
        if(chosen>=0)strip.post(()->{
            if(chosen<row.getChildCount()){
                View child=row.getChildAt(chosen);
                strip.smoothScrollTo(Math.max(0,child.getLeft()-dp(32)),0);
            }
        });
    }
    void select(String id){
        if(byId(id)==null)throw new IllegalArgumentException("Unknown conversation");
        if(archived.contains(id))throw new IllegalStateException("Restore this conversation before opening");
        work.select(id);open.add(id);persist();refresh();changed.run();
    }
    void ensureSelectedOpen(){open.add(work.active().id);archived.remove(work.active().id);persist();refresh();}
    void openWithoutSelection(String id){
        if(byId(id)==null || archived.contains(id))throw new IllegalArgumentException("Conversation not available");
        open.add(id);persist();refresh();
    }
    void close(String id){
        if(!open.remove(id))return;
        List<String> current=new ArrayList<>(open);
        if(work.active().id.equals(id)&&!current.isEmpty())work.select(current.get(current.size()-1));
        persist();refresh();changed.run();
    }
    void archive(String id){
        if(byId(id)==null)return;
        archived.add(id);open.remove(id);
        if(work.active().id.equals(id)){
            for(String next:open){work.select(next);break;}
        }
        persist();refresh();changed.run();
    }
    void restore(String id){archived.remove(id);persist();refresh();}
    boolean isOpen(String id){return open.contains(id);}
    String draft(String id){return store.getString("draft_"+id,"");}
    void setDraft(String id,String value){
        if(value==null)value="";
        if(value.length()>12000)value=value.substring(0,12000);
        if(!store.edit().putString("draft_"+id,value).commit())throw new IllegalStateException("Draft not saved");
    }
    void showDrawer(){
        String[] choices={"Open/active conversations","Archived conversations","Discover recent ChatGPT chats","Add ChatGPT URL","New conversation","Voice for this chat","Campaigns","Settings and controls"};
        new AlertDialog.Builder(a).setTitle("Conversations")
            .setItems(choices,(dialog,index)->{
                switch(index){
                    case 0: showActive();break;
                    case 1: showArchived();break;
                    case 2: RitsuConversationLinks.discover(a,this,work,changed);break;
                    case 3: RitsuConversationLinks.addUrl(a,this,work,changed);break;
                    case 4: newConversation();break;
                    case 5: RitsuConversationLinks.voicePreference(a,work.active().id,this);break;
                    case 6: a.startActivity(new android.content.Intent(a,CampaignActivity.class));break;
                    case 7: controls.run();break;
                    default:break;
                }
            }).setNegativeButton("Close",null).show();
    }
    private void showActive(){
        List<RitsuWorkspace.Tab> tabs=new ArrayList<>();
        for(RitsuWorkspace.Tab t:work.tabs())if(!archived.contains(t.id))tabs.add(t);
        String[] labels=new String[tabs.size()];
        for(int i=0;i<tabs.size();i++)labels[i]=(open.contains(tabs.get(i).id)?"● ":"◯ ")+title(tabs.get(i));
        new AlertDialog.Builder(a).setTitle("Your conversations")
            .setItems(labels,(d,which)->select(tabs.get(which).id))
            .setNeutralButton("Manage",(d,which)->showManage(tabs))
            .setPositiveButton("Add URL",(d,which)->RitsuConversationLinks.addUrl(a,this,work,changed))
            .setNegativeButton("Close",null).show();
    }
    private void showManage(List<RitsuWorkspace.Tab> tabs){
        String[] labels=new String[tabs.size()];for(int i=0;i<tabs.size();i++)labels[i]=title(tabs.get(i));
        new AlertDialog.Builder(a).setTitle("Manage active chats")
          .setItems(labels,(d,index)->{
            RitsuWorkspace.Tab t=tabs.get(index);
            new AlertDialog.Builder(a).setTitle(title(t)).setItems(new String[]{"Open tab","Close tab","Rename here","Archive here"},(menu,which)->{
                if(which==0)select(t.id);
                if(which==1)close(t.id);
                if(which==2)rename(t);
                if(which==3)archive(t.id);
            }).show();
          }).setNegativeButton("Close",null).show();
    }
    private void rename(RitsuWorkspace.Tab t){
        EditText input=new EditText(a);input.setSingleLine(true);input.setText(title(t));
        new AlertDialog.Builder(a).setTitle("Rename Ritsu label").setView(input)
          .setPositiveButton("Save",(d,w)->{
            String value=input.getText().toString().trim();
            if(value.length()<1||value.length()>48){error("Title must be 1–48 characters");return;}
            if(!store.edit().putString("title_"+t.id,value).commit()){error("Rename not saved");return;}
            refresh();
          }).setNegativeButton("Cancel",null).show();
    }
    private void showArchived(){
        ArrayList<String> ids=new ArrayList<>();ArrayList<String> labels=new ArrayList<>();
        for(String id:archived){RitsuWorkspace.Tab t=byId(id);if(t!=null){ids.add(id);labels.add(title(t));}}
        new AlertDialog.Builder(a).setTitle("Archived in Ritsu only")
          .setItems(labels.toArray(new String[0]),(d,index)->{
            final String id=ids.get(index);
            new AlertDialog.Builder(a).setTitle("Restore this conversation?")
              .setMessage("The original ChatGPT conversation is unchanged.")
              .setPositiveButton("Restore",(dd,w)->{restore(id);select(id);})
              .setNegativeButton("Cancel",null).show();
          }).setNegativeButton("Close",null).show();
    }
    private void newConversation(){
        EditText input=new EditText(a);input.setSingleLine(true);input.setHint("Conversation name");
        new AlertDialog.Builder(a).setTitle("New conversation").setView(input)
          .setPositiveButton("Create",(d,w)->{
            try{work.create(input.getText().toString());ensureSelectedOpen();changed.run();}
            catch(RuntimeException error){error(error.getMessage());}
          }).setNegativeButton("Cancel",null).show();
    }
    void error(String text){new AlertDialog.Builder(a).setTitle("Conversations").setMessage(text).setPositiveButton("OK",null).show();}
}
