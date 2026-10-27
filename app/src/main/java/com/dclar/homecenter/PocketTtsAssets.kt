package com.dclar.homecenter

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

internal object PocketTtsAssets {
    private const val ASSET_ROOT = "pockettts"
    private const val MANIFEST = "manifest.json"
    private val lock = Any()

    @JvmStatic
    fun ensureInstalled(context: Context): File = synchronized(lock) {
        val dir = File(context.filesDir, "pockettts-native-v1")
        if (!dir.exists() && !dir.mkdirs()) error("Could not create Pocket TTS model directory")
        val manifestBytes = context.assets.open("$ASSET_ROOT/$MANIFEST").use { it.readBytes() }
        val manifestHash = sha256(manifestBytes)
        val json = JSONObject(String(manifestBytes, Charsets.UTF_8))
        val files = json.getJSONArray("files")
        val marker = File(dir, ".installed-$manifestHash")
        var quick = marker.isFile()
        if (quick) for (i in 0 until files.length()) {
            val row = files.getJSONObject(i)
            val target = File(dir, row.getString("name"))
            if (!target.isFile || target.length() != row.getLong("bytes")) { quick = false; break }
        }
        if (quick) return@synchronized dir
        for (i in 0 until files.length()) {
            val row = files.getJSONObject(i)
            val name = row.getString("name")
            val expectedBytes = row.getLong("bytes")
            val expectedSha = row.getString("sha256")
            val target = File(dir, name)
            if (target.isFile && target.length() == expectedBytes && sha256(target) == expectedSha) continue
            val part = File(dir, "$name.part")
            context.assets.open("$ASSET_ROOT/$name").use { input ->
                FileOutputStream(part, false).use { output -> input.copyTo(output, 1024 * 1024); output.fd.sync() }
            }
            check(part.length() == expectedBytes) { "Pocket TTS asset size mismatch: $name" }
            check(sha256(part) == expectedSha) { "Pocket TTS asset hash mismatch: $name" }
            if (target.exists() && !target.delete()) error("Could not replace Pocket TTS asset: $name")
            check(part.renameTo(target)) { "Could not publish Pocket TTS asset: $name" }
        }
        File(dir, MANIFEST).writeBytes(manifestBytes)
        dir.listFiles { f -> f.name.startsWith(".installed-") }?.forEach { it.delete() }
        marker.writeText(manifestHash + "\n")
        dir
    }

    private fun sha256(file: File): String = file.inputStream().use { input ->
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(1024 * 1024)
        while (true) { val n = input.read(buffer); if (n < 0) break; if (n > 0) digest.update(buffer, 0, n) }
        digest.digest().joinToString("") { "%02x".format(it) }
    }
    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
}
