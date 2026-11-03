package com.homecenter.ritsucontrol;

import static org.junit.Assert.*;
import org.junit.Test;

public final class RitsuPairingTest {
    @Test public void onlyTailscaleLiteralAddressPermitted() {
        assertEquals("http://100.68.37.106:19646",
                RitsuPairing.validateOrigin("http://100.68.37.106:19646"));
        assertEquals("http://100.68.37.106:19646",
                RitsuPairing.validateOrigin("http://100.68.37.106:19646/"));
    }

    @Test public void blocksPublicLanLoopbackAndUnencryptedWeb() {
        for(String value:new String[] {
                "http://0.0.0.0:19646",
                "http://127.0.0.1:19646",
                "http://192.168.1.22:19646",
                "http://100.63.1.1:19646",
                "http://100.64.0.1:19646",
                "http://100.127.255.254:19646",
                "http://100.68.37.107:19646",
                "http://100.128.0.1:19646",
                "http://8.8.8.8:19646",
                "http://example.com:19646",
                "https://100.100.10.10:19646",
                "http://user@100.100.10.10:19646",
                "http://100.100.10.10:19646/evil",
                "http://100.100.10.10:19646?query=1",
                "http://100.100.10.10:19647"
        }) {
            try {
                RitsuPairing.validateOrigin(value);
                fail("Unsafe endpoint accepted: "+value);
            }catch(IllegalArgumentException expected) { }
        }
    }
}
