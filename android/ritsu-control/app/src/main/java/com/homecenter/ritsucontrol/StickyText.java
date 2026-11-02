package com.homecenter.ritsucontrol;

/** Immutable, deterministic sticky-context composition at turn intake.
 * This is user-supplied prompt context, not a system/developer instruction.
 * Snapshot once when the turn is queued; never regenerate on network retry.
 */
final class StickyText {
    static final int MAX_SNIPPET_CHARS=6000;
    static final int MAX_TOTAL_TURN_CHARS=9000;
    private StickyText(){}

    static String normalize(String text) {
        if(text==null)return "";
        String value=text.trim();
        if(value.length()>MAX_SNIPPET_CHARS)
            throw new IllegalArgumentException("Sticky snippet exceeds 6000 characters");
        return value;
    }

    static String append(String existing,String insertion){
        String before=existing==null?"":existing;
        String extra=normalize(insertion);
        if(extra.isEmpty())return before;
        String joined=before.trim().isEmpty()?extra:before+"\n\n"+extra;
        if(joined.length()>MAX_SNIPPET_CHARS)
            throw new IllegalArgumentException("Sticky text exceeds 6000 characters");
        return joined;
    }

    static String compose(String message,String sticky){
        String body=message==null?"":message.trim();
        String context=normalize(sticky);
        if(body.isEmpty())return "";
        if(context.isEmpty())return body;
        // Text repeated on EVERY queued turn so context is not truncated to
        // an earlier conversational turn, but models may still disregard it.
        String result="[Persistent user-supplied context for this conversation tab]\n"
                +context
                +"\n[End persistent context]\n\n"
                +body;
        if(result.length()>MAX_TOTAL_TURN_CHARS)
            throw new IllegalArgumentException("Message plus sticky text is too long");
        return result;
    }
}
