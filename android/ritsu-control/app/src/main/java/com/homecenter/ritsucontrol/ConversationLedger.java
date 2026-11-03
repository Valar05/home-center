package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Bounded durable private chat/outbox. The only authority for result text is
 * a verified Home Center CONTROL result. Worker drafts never reach this feed.
 * Phone and service instantiate different objects: one process-wide IO lock
 * protects SharedPreferences read/modify/write, NOT an orchestration singleton.
 */
final class ConversationLedger {
    static final int KEEP = 200;
    private static final String PREF = "ritsu_chat_local_v1";
    private static final Object IO_LOCK = new Object();
    static final String OUTBOX = "WAITING_FOR_HOME_CENTER";
    static final String VERIFIED = "VERIFIED_CHATGPT_REPLY";
    static final class Entry {
        final String id, channel, who, text, state, tabId, machineId;
        Entry(String id,String channel,String who,String text,String state,
              String tabId,String machineId) {
            this.id=id;this.channel=channel;this.who=who;this.text=text;this.state=state;
            this.tabId=tabId;this.machineId=machineId;
        }
    }
    private final SharedPreferences store;
    ConversationLedger(Context ctx) {
        store=ctx.getApplicationContext().getSharedPreferences(PREF,Context.MODE_PRIVATE);
    }

    Entry add(String channel,String who,String message,String state) {
        return addInTab("main","termux-android",channel,who,message,state);
    }
    Entry addInTab(String tabId,String machineId,String channel,String who,
                   String message,String state) {
        validateTarget(tabId,machineId);
        return insert(UUID.randomUUID().toString(),channel,who,message,state,
                false,tabId,machineId);
    }
    private static void validateTarget(String tabId,String machineId) {
        if(tabId==null||!tabId.matches("[A-Za-z0-9_-]{4,80}"))
            throw new IllegalArgumentException("Invalid conversation tab");
        RitsuWorkspace.machine(machineId);
    }
    private String[] originForTurn(String userTurnId){
        synchronized(IO_LOCK){
            JSONArray all=rows();
            for(int i=0;i<all.length();i++){
                JSONObject row=all.optJSONObject(i);
                if(row!=null && userTurnId.equals(row.optString("id")) &&
                   "You".equals(row.optString("who")))
                    return new String[]{row.optString("tabId","main"),
                        row.optString("machineId","termux-android")};
            }
        }
        return new String[]{"main","termux-android"};
    }
    /** Check turn ownership before consuming shared laptop-journal events.
     * Termux canaries may share the pairing but must never appear in this UI.
     */
    boolean containsUserTurn(String id){
        if(id==null||id.isEmpty())return false;
        synchronized(IO_LOCK){
            JSONArray all=rows();
            for(int i=0;i<all.length();i++){
                JSONObject row=all.optJSONObject(i);
                if(row!=null&&id.equals(row.optString("id"))&&
                   "You".equals(row.optString("who")))return true;
            }
            return false;
        }
    }

    Entry insertReplyOnce(String userTurnId,String message) {
        // Immutable derived ID prevents duplicate messages after reconnect.
        String[] route=originForTurn(userTurnId);
        return insert("reply:"+userTurnId,"control","Ritsu",message,VERIFIED,
                true,route[0],route[1]);
    }
    /** One mutable in-flight assistant bubble per user turn. Revision and exact
     * originating tab are checked before a snapshot can appear on screen. */
    Entry upsertStreamingReply(String userTurnId,String message,int version,boolean complete) {
        if(version<1||version>1000000||message==null||message.trim().isEmpty()||
           message.length()>5000)throw new IllegalArgumentException("invalid streaming reply");
        synchronized(IO_LOCK){
            JSONArray previous=rows();
            JSONObject source=null,existing=null;
            String replyId="reply:"+userTurnId;
            for(int i=0;i<previous.length();i++){
                JSONObject row=previous.optJSONObject(i);
                if(row==null)continue;
                if(userTurnId.equals(row.optString("id")) && "You".equals(row.optString("who")))source=row;
                if(replyId.equals(row.optString("id")))existing=row;
            }
            if(source==null)throw new IllegalStateException("stream without local user turn");
            String tab=source.optString("tabId","main");
            String machine=source.optString("machineId","termux-android");
            validateTarget(tab,machine);
            String text=message.trim();
            if(existing!=null){
                if(!tab.equals(existing.optString("tabId"))||
                   !machine.equals(existing.optString("machineId")))
                    throw new IllegalStateException("stream reply wrong tab");
                int oldVersion=existing.optInt("streamVersion",0);
                String prior=existing.optString("text");
                if(version<oldVersion)return new Entry(replyId,"control","Ritsu",prior,
                    existing.optString("state"),tab,machine);
                if(version==oldVersion && !prior.equals(text))
                    throw new IllegalStateException("stream revision collision");
                if(VERIFIED.equals(existing.optString("state"))) {
                    if(!prior.equals(text))throw new IllegalStateException("completed reply immutable");
                    return new Entry(replyId,"control","Ritsu",prior,VERIFIED,tab,machine);
                }
                try{
                    existing.put("text",text).put("streamVersion",version)
                        .put("state",complete?VERIFIED:"STREAMING");
                }catch(Exception e){throw new IllegalStateException("stream update invalid");}
            } else {
                JSONObject row=new JSONObject();
                try {
                    row.put("id",replyId).put("channel","control").put("who","Ritsu");
                    row.put("text",text).put("state",complete?VERIFIED:"STREAMING");
                    row.put("tabId",tab).put("machineId",machine);
                    row.put("streamVersion",version).put("time",System.currentTimeMillis());
                }catch(Exception e){throw new IllegalStateException("stream insert invalid");}
                if(previous.length()>=KEEP) {
                    JSONObject first=previous.optJSONObject(0);
                    if(first!=null&&"You".equals(first.optString("who"))&&
                       !"COMPLETED".equals(first.optString("state")))
                        throw new IllegalStateException("outbox protected from eviction");
                    JSONArray bounded=new JSONArray();
                    for(int i=1;i<previous.length();i++)bounded.put(previous.optJSONObject(i));
                    previous=bounded;
                }
                previous.put(row);
            }
            if(!store.edit().putString("entries",previous.toString()).commit())
                throw new IllegalStateException("stream snapshot persistence failed");
            return new Entry(replyId,"control","Ritsu",text,complete?VERIFIED:"STREAMING",tab,machine);
        }
    }

    Entry insertPublishedOnce(String resultId, String channel, String who, String message) {
        if(resultId==null || !resultId.matches("[A-Za-z0-9_.:-]{8,100}") ||
                !("control".equals(channel)||"dialogue".equals(channel)||
                  "worker".equals(channel)) ||
                !("Ritsu".equals(who)||"Worker".equals(who)))
            throw new IllegalArgumentException("invalid signed Home Center feed identity");
        return insert("published:"+resultId,channel,who,message,VERIFIED,
                true,"main","termux-android");
    }

    private Entry insert(String id,String channel,String who,String message,
                         String state,boolean idempotent,String tabId,String machineId) {
        validateTarget(tabId,machineId);
        if(!("control".equals(channel)||"dialogue".equals(channel)||"worker".equals(channel)))
            throw new IllegalArgumentException("unknown channel");
        String text=message==null?"":message.trim();
        if(text.isEmpty()||text.length()>5000)
            throw new IllegalArgumentException("invalid text");
        synchronized(IO_LOCK) {
            JSONArray previous=rows();
            for(int i=0;i<previous.length();i++){
                JSONObject row=previous.optJSONObject(i);
                if(row!=null&&id.equals(row.optString("id"))){
                    if(!idempotent || !text.equals(row.optString("text")))
                        throw new IllegalStateException("local chat ID collision");
                    if(!tabId.equals(row.optString("tabId","main")) ||
                       !machineId.equals(row.optString("machineId","termux-android")))
                        throw new IllegalStateException("Reply routed to wrong conversation");
                    return new Entry(id,channel,who,text,row.optString("state"),
                            tabId,machineId);
                }
            }
            Entry e=new Entry(id,channel,who,text,state,tabId,machineId);
            JSONArray next=new JSONArray();
            int from=Math.max(0,previous.length()-KEEP+1);
            // Never silently discard a pending owner message just because
            // the UI has had many messages. The caller must surface capacity.
            for(int i=0;i<from;i++) {
                JSONObject old=previous.optJSONObject(i);
                if(old!=null && "You".equals(old.optString("who")) &&
                        !"COMPLETED".equals(old.optString("state")))
                    throw new IllegalStateException("outbox full, unsent messages protected");
            }
            for(int i=from;i<previous.length();i++)next.put(previous.optJSONObject(i));
            JSONObject row=new JSONObject();
            try {
                row.put("id",e.id);row.put("channel",e.channel);row.put("who",e.who);
                row.put("text",e.text);row.put("state",e.state);
                row.put("tabId",tabId);row.put("machineId",machineId);
                row.put("time",System.currentTimeMillis());
            }catch(Exception exception){throw new IllegalStateException("ledger failed");}
            next.put(row);
            if(!store.edit().putString("entries",next.toString()).commit())
                throw new IllegalStateException("ledger not persisted");
            return e;
        }
    }

    /** Pending user turns are phone-local until a verified cloud receipt.
     * Count them across every tab to prevent the selected tab hiding work. */
    int pendingCount() {
        synchronized(IO_LOCK) {
            JSONArray all=rows();
            int count=0;
            for(int i=0;i<all.length();i++) {
                JSONObject row=all.optJSONObject(i);
                if(row!=null && "You".equals(row.optString("who")) &&
                    !"COMPLETED".equals(row.optString("state")))count++;
            }
            return count;
        }
    }

    /** Read-only recovery of locally saved user turns. Does not invent a
     * remote ChatGPT receipt or silently replay an uncertain message. */
    List<Entry> unsent() {
        synchronized(IO_LOCK) {
            List<Entry> pending=new ArrayList<>();
            JSONArray all=rows();
            for(int i=0;i<all.length();i++) {
                JSONObject row=all.optJSONObject(i);
                if(row==null||!"You".equals(row.optString("who"))||
                    "COMPLETED".equals(row.optString("state")))continue;
                pending.add(new Entry(row.optString("id"),
                    row.optString("channel"),"You",row.optString("text"),
                    row.optString("state"),row.optString("tabId","main"),
                    row.optString("machineId","termux-android")));
            }
            return pending;
        }
    }

    boolean updateState(String id,String state) {
        if(id==null||id.isEmpty()||state==null||
                !state.matches("[A-Z_]{3,45}"))throw new IllegalArgumentException("invalid receipt state");
        synchronized(IO_LOCK) {
            JSONArray all=rows();
            boolean changed=false;
            for(int i=0;i<all.length();i++) {
                JSONObject row=all.optJSONObject(i);
                if(row==null||!id.equals(row.optString("id")))continue;
                if(!"You".equals(row.optString("who")))
                    throw new IllegalStateException("cannot change remote reply state");
                if("COMPLETED".equals(row.optString("state")))return false;
                try{row.put("state",state);}
                catch(Exception ex){throw new IllegalStateException("receipt update failed");}
                changed=true;
                break;
            }
            if(changed&&!store.edit().putString("entries",all.toString()).commit())
                throw new IllegalStateException("receipt state not persisted");
            return changed;
        }
    }

    List<Entry> list(String channel) {
        return list(channel,null);
    }
    List<Entry> list(String channel,String selectedTabId) {
        synchronized(IO_LOCK) {
            JSONArray all=rows();
            List<Entry> result=new ArrayList<>();
            for(int i=0;i<all.length();i++) {
                JSONObject row=all.optJSONObject(i);
                if(row==null)continue;
                String ch=row.optString("channel");
                String sourceTab=row.optString("tabId","main");
                if(selectedTabId!=null&&!selectedTabId.equals(sourceTab))continue;
                if(!("all".equals(channel)||channel.equals(ch)||
                        ("ritsu".equals(channel)&&("control".equals(ch)||"dialogue".equals(ch)))))
                    continue;
                result.add(new Entry(row.optString("id"),ch,row.optString("who"),
                        row.optString("text"),row.optString("state"),
                        sourceTab,row.optString("machineId","termux-android")));
            }
            return result;
        }
    }

    private JSONArray rows() {
        try{return new JSONArray(store.getString("entries","[]"));}
        catch(Exception ignored){throw new IllegalStateException("Chat ledger corrupt; no silent reset");}
    }
}
