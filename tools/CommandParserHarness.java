package com.dclar.homecenter;

final class CommandParserHarness {
    private CommandParserHarness() {
    }

    public static void main(String[] args) {
        assertCommand("add eggs to the shopping list", Command.ADD_LIST_ITEM, "eggs", "shopping", null, null);
        assertCommand("add milk to grocery list", Command.ADD_LIST_ITEM, "milk", "shopping", null, null);
        assertCommand("read the shopping list", Command.READ_LIST, null, "shopping", null, null);
        assertCommand("what is on groceries", Command.READ_LIST, null, "shopping", null, null);
        assertCommand("remove the eggs from the shopping list", Command.REMOVE_LIST_ITEM, "eggs", "shopping", null, null);
        assertCommand("cross bread off grocery list", Command.REMOVE_LIST_ITEM, "bread", "shopping", null, null);
        assertCommand("create personal list meds", Command.CREATE_LIST, null, "meds", "personal", "");
        assertCommand("create household list chores", Command.CREATE_LIST, null, "chores", "household", "");
        assertCommand("create group list soccer for kids", Command.CREATE_LIST, null, "soccer", "group", "kids");
        assertCommand("read shopping preferences", Command.READ_PREFERENCES, null, "shopping", null, null);
        assertCommand("build walmart cart for shopping", Command.BUILD_CART, null, "shopping", null, null);
        assertCommand("map ranch to walmart target sku=12345|productUrl=https://www.walmart.com/ip/12345|quantity=2", Command.SET_STORE_TARGET, "ranch", "shopping", "sku=12345|producturl=https://www.walmart.com/ip/12345|quantity=2", null);
        assertCommand("next", Command.NEXT_ITEM, null, null, null, null);
        assertCommand("previous item", Command.PREVIOUS_ITEM, null, null, null, null);
        assertCommand("done", Command.MARK_DONE, null, null, null, null);
        System.out.println("CommandParserHarness: OK");
    }

    private static void assertCommand(String phrase, String action, String item, String list, String state, String group) {
        Command command = CommandParser.parse(phrase);
        assertEquals(phrase + " action", action, command.action);
        assertEquals(phrase + " item", item, command.item);
        assertEquals(phrase + " list", list, command.listName);
        assertEquals(phrase + " state", state, command.state);
        assertEquals(phrase + " group", group, command.groupName);
    }

    private static void assertEquals(String label, String expected, String actual) {
        if (expected == null) {
            if (actual != null) {
                fail(label, expected, actual);
            }
            return;
        }
        if (!expected.equals(actual)) {
            fail(label, expected, actual);
        }
    }

    private static void fail(String label, String expected, String actual) {
        throw new AssertionError(label + " expected=" + expected + " actual=" + actual);
    }
}
