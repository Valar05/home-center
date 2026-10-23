package com.homecenter.ritsucontrol;

import static org.junit.Assert.*;
import org.junit.Test;

public final class RitsuPairingTest {
    @Test public void onlyTailscaleLiteralAddressPermitted() {
        assertEquals("http://100.64.0.1:19645",
                RitsuPairing.validateOrigin("http://100.64.0.1:19645"));
        assertEquals("http://100.127.255.254:19645",
                RitsuPairing.validateOrigin("http://100.127.255.254:19645/"));
    }

    @Test public void blocksPublicLanLoopbackAndUnencryptedWeb() {
        for(String value:new String[] {
                "http://0.0.0.0:19645",
                "http://127.0.0.1:19645",
                "http://192.168.1.22:19645",
                "http://100.63.1.1:19645",
                "http://100.128.0.1:19645",
                "http://8.8.8.8:19645",
                "http://example.com:19645",
                "https://100.100.10.10:19645",
                "http://user@100.100.10.10:19645",
                "http://100.100.10.10:19645/evil",
                "http://100.100.10.10:19645?query=1",
                "http://100.100.10.10:19646"
        }) {
            try {
                RitsuPairing.validateOrigin(value);
                fail("Unsafe endpoint accepted: "+value);
            }catch(IllegalArgumentException expected) { }
        }
    }
}
