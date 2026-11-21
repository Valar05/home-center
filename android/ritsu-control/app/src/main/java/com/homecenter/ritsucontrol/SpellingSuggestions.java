package com.homecenter.ritsucontrol;

import android.content.Context;
import android.os.Bundle;
import android.view.textservice.SentenceSuggestionsInfo;
import android.view.textservice.SpellCheckerSession;
import android.view.textservice.SuggestionsInfo;
import android.view.textservice.TextInfo;
import android.view.textservice.TextServicesManager;
import java.util.ArrayList;
import java.util.LinkedHashSet;

/** Optional Android system spellchecker. Does not fetch Gboard-private data.
 * Suggestions are user-visible and NEVER silently applied to a transcript. */
final class SpellingSuggestions {
    interface Callback { void suggestions(String source, String[] items); }
    private final Context context;
    private SpellCheckerSession session;
    SpellingSuggestions(Context context) { this.context = context; }
    void check(String source, Callback callback) {
        close();
        String original = source == null ? "" : source.trim();
        if (original.isEmpty()) { callback.suggestions(original, new String[0]); return; }
        TextServicesManager mgr = (TextServicesManager) context.getSystemService(Context.TEXT_SERVICES_MANAGER_SERVICE);
        if (mgr == null || !mgr.isSpellCheckerEnabled()) {
            callback.suggestions(original, new String[0]); return;
        }
        try {
            session = mgr.newSpellCheckerSession(null, null, new SpellCheckerSession.SpellCheckerSessionListener() {
                @Override public void onGetSuggestions(SuggestionsInfo[] infos) {}
                @Override public void onGetSentenceSuggestions(SentenceSuggestionsInfo[] sentences) {
                    LinkedHashSet<String> choices = new LinkedHashSet<>();
                    if (sentences != null) for (SentenceSuggestionsInfo sentence : sentences) {
                        if (sentence == null) continue;
                        for (int i = 0; i < sentence.getSuggestionsCount(); i++) {
                            SuggestionsInfo info = sentence.getSuggestionsInfoAt(i);
                            if (info == null) continue;
                            int start = sentence.getOffsetAt(i);
                            int end = start + sentence.getLengthAt(i);
                            if (start < 0 || end > original.length() || end <= start) continue;
                            for (int j = 0; j < Math.max(0, info.getSuggestionsCount()); j++) {
                                String suggestion = info.getSuggestionAt(j);
                                if (suggestion == null || suggestion.trim().isEmpty()) continue;
                                choices.add(original.substring(0, start) + suggestion
                                        + original.substring(end));
                                if (choices.size() >= 12) break;
                            }
                        }
                    }
                    callback.suggestions(original, new ArrayList<>(choices).toArray(new String[0]));
                    close();
                }
            }, true);
            if (session == null) { callback.suggestions(original, new String[0]); return; }
            session.getSentenceSuggestions(new TextInfo[]{new TextInfo(original)}, 5);
        } catch (RuntimeException error) {
            close();
            callback.suggestions(original, new String[0]);
        }
    }
    void close() {
        if (session != null) { session.close(); session = null; }
    }
}
