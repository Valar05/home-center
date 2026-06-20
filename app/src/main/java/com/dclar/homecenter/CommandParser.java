package com.dclar.homecenter;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class CommandParser {
    private static final Pattern CREATE_GROUP_LIST = Pattern.compile(
            "^(?:please\\s+)?create\\s+(?:a\\s+)?(?:group|family)\\s+list\\s+(.+?)\\s+(?:for|with)\\s+(?:the\\s+)?(.+?)(?:\\s+(?:group|family))?$"
    );
    private static final Pattern CREATE_SCOPED_LIST = Pattern.compile(
            "^(?:please\\s+)?create\\s+(?:a\\s+)?(personal|private|shared|household|family)\\s+list\\s+(.+?)$"
    );
    private static final Pattern CREATE_LIST = Pattern.compile(
            "^(?:please\\s+)?create\\s+(?:a\\s+)?list\\s+(.+?)$"
    );
    private static final Pattern SET_PREFERENCE = Pattern.compile(
            "^(?:please\\s+)?(?:prefer|set\\s+preference\\s+for|save\\s+preference\\s+for)\\s+(.+?)\\s+(?:as|to)\\s+(.+?)$"
    );
    private static final Pattern SET_STORE_TARGET_SPEC = Pattern.compile(
            "^(?:please\\s+)?(?:map|save)\\s+(.+?)\\s+(?:to|as)\\s+walmart\\s+(?:target|product|item)\\s+(.+?)$"
    );
    private static final Pattern SET_STORE_TARGET = Pattern.compile(
            "^(?:please\\s+)?(?:map|set\\s+sku\\s+for|save\\s+sku\\s+for)\\s+(.+?)\\s+(?:to|as)\\s+(?:walmart\\s+)?sku\\s+(.+?)$"
    );
    private static final Pattern READ_PREFERENCES = Pattern.compile(
            "^(?:please\\s+)?(?:read|show)\\s+(?:the\\s+)?(.+?)\\s+preferences$"
    );
    private static final Pattern BUILD_CART = Pattern.compile(
            "^(?:please\\s+)?(?:build|export|prepare)\\s+(?:the\\s+)?(?:walmart\\s+)?cart\\s+(?:for|from)\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern ADD_TO_LIST = Pattern.compile(
            "^(?:please\\s+)?add\\s+(.+?)\\s+to\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern READ_LIST = Pattern.compile(
            "^(?:please\\s+)?(?:read|show|list)\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern WHAT_IS_ON_LIST = Pattern.compile(
            "^(?:what(?:'s| is) on)\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern REMOVE_FROM_LIST = Pattern.compile(
            "^(?:please\\s+)?(?:remove|delete)\\s+(.+?)\\s+(?:from|off)\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern TAKE_OFF_LIST = Pattern.compile(
            "^(?:please\\s+)?take\\s+(.+?)\\s+off\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern CROSS_OFF_LIST = Pattern.compile(
            "^(?:please\\s+)?cross\\s+(.+?)\\s+off\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern MARK_ITEM_DONE = Pattern.compile(
            "^(?:please\\s+)?(?:mark|complete)\\s+(.+?)\\s+(?:done|complete|completed)\\s+(?:on|from|off)\\s+(?:the\\s+)?(.+?)$"
    );
    private static final Pattern HOTSPOT = Pattern.compile(
            "^(?:turn|switch)\\s+(on|off)\\s+(?:my\\s+)?hotspot$"
    );

    private CommandParser() {
    }

    static Command parse(String raw) {
        String cleaned = normalize(raw);
        if (cleaned.equals("next") || cleaned.equals("next item") || cleaned.equals("advance")
                || cleaned.equals("advance list")) {
            return Command.nextItem(raw);
        }
        if (cleaned.equals("previous") || cleaned.equals("previous item") || cleaned.equals("back")
                || cleaned.equals("go back")) {
            return Command.previousItem(raw);
        }
        if (cleaned.equals("done") || cleaned.equals("mark done") || cleaned.equals("mark it done")
                || cleaned.equals("complete") || cleaned.equals("complete item")
                || cleaned.equals("remove this") || cleaned.equals("delete this")
                || cleaned.equals("cross this off") || cleaned.equals("remove current item")) {
            return Command.markDone(raw);
        }

        Matcher createGroup = CREATE_GROUP_LIST.matcher(cleaned);
        if (createGroup.matches()) {
            return Command.createList(normalizeListName(createGroup.group(1)), "group", cleanGroupName(createGroup.group(2)), raw);
        }

        Matcher createScoped = CREATE_SCOPED_LIST.matcher(cleaned);
        if (createScoped.matches()) {
            String visibility = normalizeVisibility(createScoped.group(1));
            return Command.createList(normalizeListName(createScoped.group(2)), visibility, "", raw);
        }

        Matcher create = CREATE_LIST.matcher(cleaned);
        if (create.matches()) {
            return Command.createList(normalizeListName(create.group(1)), "household", "", raw);
        }

        Matcher add = ADD_TO_LIST.matcher(cleaned);
        if (add.matches()) {
            return Command.addListItem(cleanItem(add.group(1)), normalizeListName(add.group(2)), raw);
        }

        Matcher remove = REMOVE_FROM_LIST.matcher(cleaned);
        if (remove.matches()) {
            return Command.removeListItem(cleanItem(remove.group(1)), normalizeListName(remove.group(2)), raw);
        }

        Matcher takeOff = TAKE_OFF_LIST.matcher(cleaned);
        if (takeOff.matches()) {
            return Command.removeListItem(cleanItem(takeOff.group(1)), normalizeListName(takeOff.group(2)), raw);
        }

        Matcher crossOff = CROSS_OFF_LIST.matcher(cleaned);
        if (crossOff.matches()) {
            return Command.removeListItem(cleanItem(crossOff.group(1)), normalizeListName(crossOff.group(2)), raw);
        }

        Matcher markItemDone = MARK_ITEM_DONE.matcher(cleaned);
        if (markItemDone.matches()) {
            return Command.removeListItem(cleanItem(markItemDone.group(1)), normalizeListName(markItemDone.group(2)), raw);
        }

        Matcher setPreference = SET_PREFERENCE.matcher(cleaned);
        if (setPreference.matches()) {
            return Command.setPreference(cleanItem(setPreference.group(1)), cleanItem(setPreference.group(2)), normalizeListName("shopping"), raw);
        }

        Matcher setStoreTargetSpec = SET_STORE_TARGET_SPEC.matcher(cleaned);
        if (setStoreTargetSpec.matches()) {
            return Command.setStoreTarget(cleanItem(setStoreTargetSpec.group(1)), setStoreTargetSpec.group(2).trim(), normalizeListName("shopping"), raw);
        }

        Matcher setStoreTarget = SET_STORE_TARGET.matcher(cleaned);
        if (setStoreTarget.matches()) {
            return Command.setStoreTarget(cleanItem(setStoreTarget.group(1)), cleanItem(setStoreTarget.group(2)), normalizeListName("shopping"), raw);
        }

        Matcher readPreferences = READ_PREFERENCES.matcher(cleaned);
        if (readPreferences.matches()) {
            return Command.readPreferences(normalizeListName(readPreferences.group(1)), raw);
        }

        Matcher buildCart = BUILD_CART.matcher(cleaned);
        if (buildCart.matches()) {
            return Command.buildCart(normalizeListName(buildCart.group(1)), raw);
        }

        Matcher read = READ_LIST.matcher(cleaned);
        if (read.matches()) {
            return Command.readList(normalizeListName(read.group(1)), raw);
        }

        Matcher whatIsOn = WHAT_IS_ON_LIST.matcher(cleaned);
        if (whatIsOn.matches()) {
            return Command.readList(normalizeListName(whatIsOn.group(1)), raw);
        }

        Matcher hotspot = HOTSPOT.matcher(cleaned);
        if (hotspot.matches()) {
            return Command.setHotspot(hotspot.group(1), raw);
        }

        return Command.unknown(raw);
    }

    static String normalizeListName(String value) {
        String lower = normalize(value);
        lower = lower.replaceFirst("^(the|a|an|my|our)\\s+", "");
        lower = lower.replaceFirst("\\s+(list|lists)$", "");
        lower = lower.trim();
        if (lower.equals("shopping") || lower.equals("shop")
                || lower.equals("groceries") || lower.equals("grocery")) {
            return "shopping";
        }
        return lower;
    }

    private static String normalizeVisibility(String value) {
        String cleaned = normalize(value);
        if (cleaned.equals("private")) {
            return "personal";
        }
        if (cleaned.equals("shared") || cleaned.equals("family")) {
            return "household";
        }
        return cleaned;
    }

    private static String cleanGroupName(String value) {
        String group = normalize(value);
        group = group.replaceFirst("^(the|a|an|my|our)\\s+", "");
        group = group.replaceFirst("\\s+(group|family)$", "");
        return group.trim();
    }

    private static String cleanItem(String value) {
        String item = normalize(value);
        item = item.replaceFirst("^(the|a|an|some)\\s+", "");
        return item;
    }

    private static String normalize(String value) {
        return value == null ? "" : value.trim().replaceAll("\\s+", " ").toLowerCase(Locale.US);
    }
}
