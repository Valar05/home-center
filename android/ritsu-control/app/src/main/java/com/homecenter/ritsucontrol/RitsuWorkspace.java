package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Multiple independent local conversations and explicit per-conversation
 * machine targets. A preset is a routing/context INTENT, not proof of an
 * authenticated or online shell on that machine.
 */
final class RitsuWorkspace {
    static final class Machine {
        final String id,label,description;
        Machine(String id,String label,String description){
            this.id=id;this.label=label;this.description=description;
        }
    }
    static final Machine[] MACHINES={
        new Machine("termux-android","Phone · Termux",
            "Android, Termux bash. Do not assume Shizuku or packages are online."),
        new Machine("windows-cauldron","THECAULDRON · Windows",
            "Windows PowerShell. Check machine identity and availability first."),
        new Machine("home-center-cloud","Home Center · cloud",
            "Cloud operation; never treat a web request as a local shell."),
        new Machine("windows-generic","Other Windows PC",
            "Windows PowerShell. Require a proven host binding before execution.")
    };
    static final class Tab {
        final String id,title,machineId,modelPreference;
        final boolean scriptCampaign;
        Tab(String id,String title,String machineId,boolean scriptCampaign){
            this.id=id;this.title=title;this.machineId=machineId;
            this.scriptCampaign=scriptCampaign;
            // This is a preference carried with the turn, not a promise that
            // ChatGPT has selected an externally controlled model.
            this.modelPreference="instant";
        }
    }
    private static final String PREF="ritsu_tabs_v1";
    private static final Object LOCK=new Object();
    private final SharedPreferences store;
    RitsuWorkspace(Context context){
        store=context.getApplicationContext().getSharedPreferences(PREF,Context.MODE_PRIVATE);
    }
    static Machine machine(String id){
        for(Machine m:MACHINES)if(m.id.equals(id))return m;
        throw new IllegalArgumentException("Unknown machine preset");
    }
    private JSONArray rows(){
        String json=store.getString("tabs",null);
        if(json==null){
            JSONArray initial=new JSONArray();
            JSONObject first=new JSONObject();
            try{
                first.put("id","main");first.put("title","Main");
                first.put("machineId","termux-android");
                first.put("scriptCampaign",false);initial.put(first);
            }catch(Exception error){throw new IllegalStateException(error);}
            return initial;
        }
        try{return new JSONArray(json);}
        catch(Exception error){throw new IllegalStateException("Conversation tabs corrupt; no reset");}
    }
    List<Tab> tabs(){
        synchronized(LOCK){
            JSONArray raw=rows();
            List<Tab> out=new ArrayList<>();
            for(int i=0;i<raw.length();i++){
                JSONObject row=raw.optJSONObject(i);
                if(row==null)throw new IllegalStateException("Tab data invalid");
                String id=row.optString("id"),name=row.optString("title"),machineId=row.optString("machineId");
                machine(machineId);
                if(!id.matches("[A-Za-z0-9_-]{4,80}")||name.trim().isEmpty())
                    throw new IllegalStateException("Stored tab invalid");
                out.add(new Tab(id,name,machineId,row.optBoolean("scriptCampaign",false)));
            }
            return out;
        }
    }
    Tab active(){
        String id=store.getString("selected","main");
        for(Tab t:tabs())if(t.id.equals(id))return t;
        throw new IllegalStateException("Selected conversation missing");
    }
    void select(String id){
        synchronized(LOCK){
            boolean exists=false;
            for(Tab t:tabs())if(t.id.equals(id))exists=true;
            if(!exists)throw new IllegalArgumentException("Unknown conversation tab");
            if(!store.edit().putString("selected",id).commit())
                throw new IllegalStateException("Tab selection not saved");
        }
    }
    Tab create(String proposedName){
        String name=proposedName==null?"":proposedName.trim();
        if(name.isEmpty()||name.length()>48)throw new IllegalArgumentException("Tab name 1-48 characters");
        synchronized(LOCK){
            JSONArray raw=rows();
            if(raw.length()>=12)throw new IllegalStateException("12 conversation tabs maximum");
            String id="tab_"+UUID.randomUUID().toString().replace("-","").substring(0,16);
            JSONObject created=new JSONObject();
            try{
                created.put("id",id);created.put("title",name);
                created.put("machineId",active().machineId);
                created.put("scriptCampaign",false);
                raw.put(created);
            }catch(Exception e){throw new IllegalStateException(e);}
            if(!store.edit().putString("tabs",raw.toString()).putString("selected",id).commit())
                throw new IllegalStateException("New tab not persisted");
            return new Tab(id,name,created.optString("machineId"),false);
        }
    }
    void toggleScriptCampaign(String tabId){
        synchronized(LOCK){
            JSONArray raw=rows();boolean found=false;
            for(int i=0;i<raw.length();i++){
                JSONObject row=raw.optJSONObject(i);
                if(row!=null&&tabId.equals(row.optString("id"))){
                    try{row.put("scriptCampaign",!row.optBoolean("scriptCampaign",false));}
                    catch(Exception e){throw new IllegalStateException(e);}
                    found=true;break;
                }
            }
            if(!found)throw new IllegalArgumentException("Unknown tab");
            if(!store.edit().putString("tabs",raw.toString()).commit())
                throw new IllegalStateException("Runner preference not saved");
        }
    }

    void setMachine(String tabId,String machineId){
        machine(machineId);
        synchronized(LOCK){
            JSONArray raw=rows();boolean found=false;
            for(int i=0;i<raw.length();i++){
                JSONObject row=raw.optJSONObject(i);
                if(row!=null && tabId.equals(row.optString("id"))){
                    try{row.put("machineId",machineId);}
                    catch(Exception e){throw new IllegalStateException(e);}
                    found=true;break;
                }
            }
            if(!found)throw new IllegalArgumentException("Unknown conversation");
            if(!store.edit().putString("tabs",raw.toString()).commit())
                throw new IllegalStateException("Machine preset not saved");
        }
    }
}
