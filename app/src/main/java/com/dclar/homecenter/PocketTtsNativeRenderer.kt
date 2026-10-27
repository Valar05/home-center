package com.dclar.homecenter

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import kotlin.math.roundToInt

internal object PocketTtsNativeRenderer {
    const val CONTRACT_VERSION = "pocket-tts-render-v4-native"
    const val LEGACY_CONTRACT_VERSION = "pocket-tts-render-v3"
    const val VOICE_PROFILE_ID = "vera-venice-close-mic-v1"
    const val MODEL_REVISION = "66c9d2fb05fc44cc69cb14c15cff9574c4381788"
    private val lock = Any()
    private var synthesizer: PocketTtsSynthesizer? = null

    fun interface CancelCheck { fun cancelled(): Boolean }
    class Result(
        @JvmField val wav: File,
        @JvmField val sampleRate: Int,
        @JvmField val pcmBytes: Long,
        @JvmField val artifactSha256: String,
        @JvmField val realTimeFactor: Double,
    )

    @JvmStatic fun acceptsContract(value: String?): Boolean = value == CONTRACT_VERSION || value == LEGACY_CONTRACT_VERSION

    @JvmStatic fun hasCompletedOutput(context: Context, requestId: String): Boolean = try {
        inspect(outputFile(context, requestId)) != null
    } catch (_: Exception) { false }

    @JvmStatic
    @Throws(java.io.IOException::class)
    fun render(context: Context, requestId: String, text: String, cancel: CancelCheck?): Result {
        val safeId = safe(requestId)
        inspect(outputFile(context, safeId))?.let { return it }
        synchronized(lock) {
            inspect(outputFile(context, safeId))?.let { return it }
            if (cancel?.cancelled() == true) throw java.io.IOException("Pocket TTS render cancelled")
            val clean = text.trim()
            if (clean.isEmpty()) throw java.io.IOException("Pocket TTS text is empty")
            val started = System.nanoTime()
            val generated = try {
                val engine = synthesizer ?: PocketTtsSynthesizer(context.applicationContext).also { synthesizer = it }
                engine.synthesize(clean, "vera")
            } catch (ex: LinkageError) {
                throw java.io.IOException("Pocket TTS native runtime unavailable: ${ex.message ?: ex.javaClass.simpleName}", ex)
            }
            if (cancel?.cancelled() == true) throw java.io.IOException("Pocket TTS render cancelled")
            val filtered = VeniceCloseMicFilter.process(generated.audio, PocketTtsSynthesizer.SAMPLE_RATE)
            if (filtered.size < PocketTtsSynthesizer.SAMPLE_RATE / 5) throw java.io.IOException("Pocket TTS native output is too short")
            val wav = outputFile(context, safeId)
            val part = File(wav.parentFile, wav.name + ".part")
            writeWav(part, filtered, PocketTtsSynthesizer.SAMPLE_RATE)
            val artifact = sha256(part)
            if (wav.exists() && !wav.delete()) throw java.io.IOException("Could not replace native Pocket TTS output")
            if (!part.renameTo(wav)) throw java.io.IOException("Could not publish native Pocket TTS output")
            val elapsed = (System.nanoTime() - started) / 1_000_000_000.0
            val duration = filtered.size.toDouble() / PocketTtsSynthesizer.SAMPLE_RATE
            val receipt = JSONObject()
                .put("status", "complete").put("accepted", true)
                .put("contractVersion", CONTRACT_VERSION).put("voiceProfileId", VOICE_PROFILE_ID)
                .put("voice", "vera").put("backend", "android-native-litert")
                .put("modelRevision", MODEL_REVISION).put("audioFilter", VeniceCloseMicFilter.ID)
                .put("requestId", safeId).put("textSha256", sha256(clean.toByteArray(Charsets.UTF_8)))
                .put("artifactSha256", artifact).put("sampleRate", PocketTtsSynthesizer.SAMPLE_RATE)
                .put("pcmBytes", filtered.size * 2L).put("durationSeconds", duration)
                .put("renderSeconds", elapsed).put("realTimeFactor", elapsed / duration)
            writeAtomic(receiptFile(context, safeId), receipt.toString() + "\n")
            return inspect(wav) ?: throw java.io.IOException("Native Pocket TTS receipt validation failed")
        }
    }

    private fun outputDir(context: Context): File = File(context.cacheDir, "pocket-tts-native-results").also {
        if (!it.exists() && !it.mkdirs()) throw java.io.IOException("Could not create native Pocket TTS result directory")
    }
    private fun outputFile(context: Context, id: String)=File(outputDir(context),safe(id)+".wav")
    private fun receiptFile(context: Context,id:String)=File(outputDir(context),safe(id)+".json")
    private fun inspect(wav: File): Result? {
        if (!wav.isFile || wav.length() <= 44) return null
        val receipt=File(wav.parentFile,wav.name.removeSuffix(".wav")+".json")
        if (!receipt.isFile) return null
        val j=JSONObject(receipt.readText())
        if (j.optString("status")!="complete" || !j.optBoolean("accepted") || j.optString("contractVersion")!=CONTRACT_VERSION || j.optString("voiceProfileId")!=VOICE_PROFILE_ID || j.optString("backend")!="android-native-litert") return null
        val hash=sha256(wav); if (hash!=j.optString("artifactSha256")) return null
        return Result(wav,j.optInt("sampleRate",24000),wav.length()-44,hash,j.optDouble("realTimeFactor",0.0))
    }
    private fun writeWav(file:File,audio:FloatArray,sampleRate:Int){
        FileOutputStream(file,false).use { out ->
            val pcm=audio.size*2; val h=ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
            h.put("RIFF".toByteArray()).putInt(36+pcm).put("WAVEfmt ".toByteArray()).putInt(16).putShort(1).putShort(1).putInt(sampleRate).putInt(sampleRate*2).putShort(2).putShort(16).put("data".toByteArray()).putInt(pcm)
            out.write(h.array()); val b=ByteArray(65536); var at=0
            for (x in audio) { val v=(x.coerceIn(-1f,1f)*32767f).roundToInt(); b[at++]=(v and 255).toByte(); b[at++]=((v ushr 8) and 255).toByte(); if(at==b.size){out.write(b);at=0} }
            if(at>0) out.write(b,0,at); out.fd.sync()
        }
    }
    private fun writeAtomic(file:File,text:String){ val part=File(file.parentFile,file.name+".part"); FileOutputStream(part,false).use{it.write(text.toByteArray());it.fd.sync()}; if(file.exists())file.delete(); check(part.renameTo(file)) }
    private fun sha256(file:File):String=file.inputStream().use{input->val d=MessageDigest.getInstance("SHA-256");val b=ByteArray(65536);while(true){val n=input.read(b);if(n<0)break;if(n>0)d.update(b,0,n)};d.digest().joinToString(""){"%02x".format(it)}}
    private fun sha256(bytes:ByteArray):String=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString(""){"%02x".format(it)}
    private fun safe(value:String):String=value.replace(Regex("[^A-Za-z0-9_.-]+"),"-").trim('-').ifEmpty{"section"}.take(160)
}
