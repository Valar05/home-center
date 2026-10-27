package com.dclar.homecenter

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

internal object VeniceCloseMicFilter {
    const val ID = "highpass=f=90,lowpass=f=7800,equalizer=f=260:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1:g=3,acompressor=threshold=-28dB:ratio=3:attack=10:release=120,volume=1.18"

    @JvmStatic fun process(input: FloatArray, sampleRate: Int): FloatArray {
        val hp = Biquad.highPass(90.0, 0.70710678, sampleRate)
        val lp = Biquad.lowPass(7800.0, 0.70710678, sampleRate)
        val eqLow = Biquad.peak(260.0, 1.0, 2.0, sampleRate)
        val eqPresence = Biquad.peak(3200.0, 1.0, 3.0, sampleRate)
        val out = FloatArray(input.size)
        val threshold = 10.0.pow(-28.0 / 20.0)
        val attack = exp(-1.0 / (0.010 * sampleRate))
        val release = exp(-1.0 / (0.120 * sampleRate))
        var envelope = 0.0
        for (i in input.indices) {
            var x = eqPresence.run(eqLow.run(lp.run(hp.run(input[i].toDouble()))))
            val level = kotlin.math.abs(x)
            val c = if (level > envelope) attack else release
            envelope = c * envelope + (1.0 - c) * level
            if (envelope > threshold) {
                val target = threshold * (envelope / threshold).pow(1.0 / 3.0)
                x *= target / envelope
            }
            x *= 1.18
            check(x.isFinite()) { "Venice DSP produced non-finite PCM" }
            out[i] = x.coerceIn(-0.98, 0.98).toFloat()
        }
        return out
    }

    private class Biquad(private val b0: Double, private val b1: Double, private val b2: Double, private val a1: Double, private val a2: Double) {
        private var z1=0.0; private var z2=0.0
        fun run(x: Double): Double { val y=b0*x+z1; z1=b1*x-a1*y+z2; z2=b2*x-a2*y; return y }
        companion object {
            private fun make(freq: Double, q: Double, gainDb: Double, sr: Int, kind: Int): Biquad {
                val w=2.0*PI*freq/sr; val c=cos(w); val s=sin(w); val a=s/(2.0*q); val A=10.0.pow(gainDb/40.0)
                val raw=when(kind){
                    0 -> doubleArrayOf((1+c)/2,-(1+c),(1+c)/2,1+a,-2*c,1-a)
                    1 -> doubleArrayOf((1-c)/2,1-c,(1-c)/2,1+a,-2*c,1-a)
                    else -> doubleArrayOf(1+a*A,-2*c,1-a*A,1+a/A,-2*c,1-a/A)
                }
                val a0=raw[3]; return Biquad(raw[0]/a0,raw[1]/a0,raw[2]/a0,raw[4]/a0,raw[5]/a0)
            }
            fun highPass(f:Double,q:Double,sr:Int)=make(f,q,0.0,sr,0)
            fun lowPass(f:Double,q:Double,sr:Int)=make(f,q,0.0,sr,1)
            fun peak(f:Double,q:Double,g:Double,sr:Int)=make(f,q,g,sr,2)
        }
    }
}
