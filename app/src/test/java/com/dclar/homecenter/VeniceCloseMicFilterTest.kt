package com.dclar.homecenter

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin
import kotlin.math.sqrt

class VeniceCloseMicFilterTest {
    @Test fun filterChangesSignalWithoutSilenceOrClipping() {
        val sr=24000
        val input=FloatArray(sr) { i ->
            (0.20*sin(2.0*PI*60.0*i/sr)+0.18*sin(2.0*PI*260.0*i/sr)+0.12*sin(2.0*PI*3200.0*i/sr)).toFloat()
        }
        val output=VeniceCloseMicFilter.process(input,sr)
        assertEquals(input.size,output.size)
        assertTrue(output.all { it.isFinite() })
        assertTrue(output.maxOf { abs(it) } <= 0.981f)
        val delta=sqrt(output.indices.sumOf { i -> val d=(output[i]-input[i]).toDouble();d*d }/output.size)
        val rms=sqrt(output.sumOf { x -> x.toDouble()*x }/output.size)
        assertTrue("DSP must materially change the signal",delta>0.01)
        assertTrue("DSP must not collapse to silence",rms>0.02)
    }
}
