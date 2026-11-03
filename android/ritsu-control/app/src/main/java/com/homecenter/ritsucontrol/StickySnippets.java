package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;

/** Per-tab sticky text and named reusable snippets. */
final class StickySnippets {
    private static final String PREF="ritsu_sticky_snippets_v1";
    private final SharedPreferences store;

    static final class Item {
        final String title,text;
        Item(String title,String text){this.title=title;this.text=text;}
    }
    StickySnippets(Context context){
        store=context.getApplicationContext()
                .getSharedPreferences(PREF,Context.MODE_PRIVATE);
    }
    static void checkTab(String id){
        if(id==null||!id.matches("[A-Za-z0-9_-]{4,80}"))
            throw new IllegalArgumentException("Invalid conversation tab");
    }
    String forTab(String id){
        checkTab(id);
        return store.getString("sticky_"+id,"");
    }
    void setForTab(String id,String value){
        checkTab(id);
        String safe=StickyText.normalize(value);
        if(!store.edit().putString("sticky_"+id,safe).commit())
            throw new IllegalStateException("Sticky context not persisted");
    }
    List<Item> library(){
        String stored=store.getString("library","[]");
        try{
            JSONArray arr=new JSONArray(stored);
            List<Item> out=new ArrayList<>();
            for(int i=0;i<arr.length();i++){
                JSONObject obj=arr.getJSONObject(i);
                out.add(new Item(obj.getString("title"),obj.getString("text")));
            }
            return out;
        }catch(Exception error){
            throw new IllegalStateException("Snippet library corrupt: not resetting",error);
        }
    }
    void addToLibrary(String title,String text){
        String name=title==null?"":title.trim();
        if(name.isEmpty()||name.length()>80)
            throw new IllegalArgumentException("Snippet name must be 1-80 characters");
        String value=StickyText.normalize(text);
        if(value.isEmpty())throw new IllegalArgumentException("Nothing to save");
        List<Item> prior=library();
        if(prior.size()>=30)
            throw new IllegalStateException("Quick library full (30). Export to device");
        try{
            JSONArray arr=new JSONArray();
            for(Item p:prior)arr.put(new JSONObject().put("title",p.title).put("text",p.text));
            arr.put(new JSONObject().put("title",name).put("text",value));
            if(!store.edit().putString("library",arr.toString()).commit())
                throw new IllegalStateException("Snippet library not persisted");
        }catch(org.json.JSONException error){throw new IllegalStateException(error);}
    }
}
