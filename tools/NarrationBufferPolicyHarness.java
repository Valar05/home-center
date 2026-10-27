package com.dclar.homecenter;
import java.util.Arrays;
import java.util.Collections;
public final class NarrationBufferPolicyHarness {
 public static void main(String[] args) {
  if (NarrationBufferPolicy.requiredAheadSeconds(Collections.emptyList(), 100) != 15.0) throw new AssertionError("fallback");
  double fast=NarrationBufferPolicy.requiredAheadSeconds(Arrays.asList(2.0,1.5),120);
  if (Math.abs(fast-5.0)>0.0001) throw new AssertionError("fast rate");
  double slow=NarrationBufferPolicy.requiredAheadSeconds(Arrays.asList(0.5,0.75),60);
  if (Math.abs(slow-95.0)>0.0001) throw new AssertionError("slow rate "+slow);
  double lastEight=NarrationBufferPolicy.requiredAheadSeconds(Arrays.asList(0.1,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0),60);
  if (Math.abs(lastEight-5.0)>0.0001) throw new AssertionError("last eight");
  System.out.println("NarrationBufferPolicyHarness: OK");
 }
}
