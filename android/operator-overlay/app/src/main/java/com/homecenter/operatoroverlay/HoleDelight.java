package com.homecenter.operatoroverlay;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Tiny deterministic joy source for the one-hole commission.
 * No network, no model call, no scheduler, no setup.
 */
final class HoleDelight {
    private static final String[] DELIGHTS = new String[] {
            "The hole has accepted your offering. Somewhere, a tiny drawbridge lowers for a goblin who absolutely did not have clearance.",
            "Noodle Queen inspected the hole. The hole inspected Noodle Queen. Neither filed paperwork.",
            "Ares threw mediocrity into the hole. It made a very small, professionally embarrassing sound.",
            "She-Ra found an assumption hiding behind the button and bit it.",
            "Android 67 pressed the hole once. No explanation was required.",
            "Punnett reports that this specimen survived selection pressure and is now legally considered treasure.",
            "CR performed diagnostics. Result: still a hole. Prognosis: excellent.",
            "Vince looked into the hole, nodded once, and declined to make it a dashboard.",
            "The hole briefly became load-bearing. Engineering has been asked not to investigate.",
            "A tiny fortress somewhere just gained one completely unnecessary but magnificent gargoyle.",
            "The hole ate a requirements document and immediately became 14 percent more delightful.",
            "Nothing productive happened for one second. This was deliberate and correctly implemented."
    };

    private static final AtomicInteger COUNTER = new AtomicInteger();

    private HoleDelight() {}

    static String next(long seed) {
        int n = COUNTER.getAndIncrement();
        int index = Math.floorMod((int)(seed ^ (seed >>> 32)) + n * 7, DELIGHTS.length);
        return DELIGHTS[index];
    }
}
