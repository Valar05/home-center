package com.homecenter.ritsucontrol;
import org.junit.Test;
import static org.junit.Assert.*;
public final class StickyTextTest {
 @Test public void appendKeepsOldText(){assertEquals("Before\n\nAfter",StickyText.append("Before","After"));}
 @Test public void eachTurnCarriesContext(){assertTrue(StickyText.compose("One","Pinned context").contains("Pinned context"));assertTrue(StickyText.compose("Two","Pinned context").contains("Pinned context"));}
 @Test public void independentTabHasNoContext(){assertEquals("Message",StickyText.compose("Message",""));}
}
