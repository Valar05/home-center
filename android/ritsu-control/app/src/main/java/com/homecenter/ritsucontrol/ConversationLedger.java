package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Private, bounded text feed of real events only; no invented ChatGPT replies.
 * Device-local outbox is NOT Home Center acceptance or remote delivery. */
final class ConversationLedger {
    static final int KEEP = 80;
    private static final String PREF = "ritsu_chat_local_v1";
    static final String OUTBOX = "WAITING_FOR_HOME_CENTER";
    static final class Entry {
        final String id, channel, who, text, state;
        Entry(String id, String channel, String who, String text, String state) {
            this.id=id; this.channel=channel; this.who=who; this.text=text; this.state=state;
        }
    }
    private final SharedPreferences store;
    ConversationLedger(Context ctx) {
        store=ctx.getApplicationContext().getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }
    synchronized Entry add(String channel, String who, String message, String state) {
        if (!("control".equals(channel) || "dialogue".equals(channel) || "worker".equals(channel)))
            throw new IllegalArgumentException("unknown channel");
        String text = message == null ? "" : message.trim();
        if (text.isEmpty() || text.length() > 5000) throw new IllegalArgumentException("invalid text");
        Entry e = new Entry(UUID.randomUUID().toString(), channel, who, text, state);
        JSONArray old = rows();
        JSONArray next = new JSONArray();
        for (int i=Math.max(0,old.length()-KEEP+1); i<old.length(); i++) next.put(old.optJSONObject(i));
        JSONObject row = new JSONObject();
        try {
            row.put("id",e.id);row.put("channel",e.channel);row.put("who",e.who);
            row.put("text",e.text);row.put("state",e.state);
            row.put("time",System.currentTimeMillis());
        } catch (Exception ignored) { throw new IllegalStateException("ledger failed"); }
        next.put(row);
        store.edit().putString("entries",next.toString()).apply();
        return e;
    }
    synchronized List<Entry> list(String channel) {
        JSONArray all=rows();
        List<Entry> result=new ArrayList<>();
        for(int i=0;i<all.length();i++){
            JSONObject row=all.optJSONObject(i);
            if(row==null)continue;
            String ch=row.optString("channel");
            if(!("all".equals(channel)||channel.equals(ch)))continue;
            result.add(new Entry(row.optString("id"),ch,row.optString("who"),
                    row.optString("text"),row.optString("state")));
        }
        return result;
    }
    private JSONArray rows() {
        try{return new JSONArray(store.getString("entries","[]"));}
        catch(Exception ignored){return new JSONArray();}
    }
}
