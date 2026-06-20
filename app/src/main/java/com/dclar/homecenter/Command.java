package com.dclar.homecenter;

final class Command {
    static final String ADD_LIST_ITEM = "add_list_item";
    static final String READ_LIST = "read_list";
    static final String NEXT_ITEM = "next_item";
    static final String PREVIOUS_ITEM = "previous_item";
    static final String MARK_DONE = "mark_done";
    static final String REMOVE_LIST_ITEM = "remove_list_item";
    static final String CREATE_LIST = "create_list";
    static final String SET_PREFERENCE = "set_preference";
    static final String SET_STORE_TARGET = "set_store_target";
    static final String READ_PREFERENCES = "read_preferences";
    static final String BUILD_CART = "build_cart";
    static final String SET_HOTSPOT = "set_hotspot";
    static final String UNKNOWN = "unknown";

    final String action;
    final String item;
    final String listName;
    final String state;
    final String groupName;
    final String raw;

    private Command(String action, String item, String listName, String state, String groupName, String raw) {
        this.action = action;
        this.item = item;
        this.listName = listName;
        this.state = state;
        this.groupName = groupName;
        this.raw = raw;
    }

    static Command addListItem(String item, String listName, String raw) {
        return new Command(ADD_LIST_ITEM, item, listName, null, null, raw);
    }

    static Command readList(String listName, String raw) {
        return new Command(READ_LIST, null, listName, null, null, raw);
    }

    static Command nextItem(String raw) {
        return new Command(NEXT_ITEM, null, null, null, null, raw);
    }

    static Command previousItem(String raw) {
        return new Command(PREVIOUS_ITEM, null, null, null, null, raw);
    }

    static Command markDone(String raw) {
        return new Command(MARK_DONE, null, null, null, null, raw);
    }

    static Command removeListItem(String item, String listName, String raw) {
        return new Command(REMOVE_LIST_ITEM, item, listName, null, null, raw);
    }

    static Command createList(String listName, String visibility, String groupName, String raw) {
        return new Command(CREATE_LIST, null, listName, visibility, groupName, raw);
    }

    static Command setPreference(String item, String preferredLabel, String listName, String raw) {
        return new Command(SET_PREFERENCE, item, listName, preferredLabel, null, raw);
    }

    static Command setStoreTarget(String item, String sku, String listName, String raw) {
        return new Command(SET_STORE_TARGET, item, listName, sku, null, raw);
    }

    static Command readPreferences(String listName, String raw) {
        return new Command(READ_PREFERENCES, null, listName, null, null, raw);
    }

    static Command buildCart(String listName, String raw) {
        return new Command(BUILD_CART, null, listName, null, null, raw);
    }

    static Command setHotspot(String state, String raw) {
        return new Command(SET_HOTSPOT, null, null, state, null, raw);
    }

    static Command unknown(String raw) {
        return new Command(UNKNOWN, null, null, null, null, raw);
    }
}
