package io.github.diamondng.readpalialoud

import android.content.Context
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.zip.ZipInputStream
import kotlin.math.roundToInt

/** The Piper Kannada voice (same voice as the desktop apps): works offline once downloaded
 *  (about 60 MB, from this project's GitHub Release "android-voice"; not in the APK to keep
 *  the app small). Engine: sherpa-onnx. Voice: micahchoo/piper-kn, CC BY 4.0. */
object PiperVoice {
    private var tts: OfflineTts? = null

    private class Download(val url: String, val name: String, val size: Long)

    private fun info(context: Context): Download? = try {
        val j = JSONObject(context.assets.open("piper_download.json").bufferedReader().readText())
        Download(j.getString("url"), j.getString("name"), j.getLong("size"))
    } catch (e: Exception) {
        null
    }

    private fun dir(context: Context) = File(context.filesDir, "piper")

    /** Size of the download in MB (for the question to the user). */
    fun downloadMb(context: Context): Int = ((info(context)?.size ?: 60_000_000L) / 1_000_000).toInt()

    /** True when the voice is on the phone (the version this app expects). */
    fun installed(context: Context): Boolean {
        val d = dir(context)
        val stamp = File(d, ".installed")
        return stamp.exists() && stamp.readText() == info(context)?.name &&
            File(d, "model.onnx").exists() && File(d, "tokens.txt").exists()
    }

    /** Downloads and unpacks the voice (background thread). progress(0..100). */
    @Synchronized
    fun download(context: Context, progress: (Int) -> Unit) {
        val i = info(context) ?: throw VoiceError("This build of the app has no Piper voice download.")
        if (installed(context)) return
        val zip = File(context.cacheDir, "piper.zip")
        try {
            var url = URL(i.url)
            var conn: HttpURLConnection
            var redirects = 0
            while (true) {  // GitHub sends the file from another address
                conn = url.openConnection() as HttpURLConnection
                conn.connectTimeout = 20_000
                conn.readTimeout = 60_000
                conn.instanceFollowRedirects = true
                val code = conn.responseCode
                if (code in 300..399 && redirects++ < 5) {
                    url = URL(url, conn.getHeaderField("Location"))
                    conn.disconnect()
                    continue
                }
                if (code != 200) throw IOException("HTTP $code")
                break
            }
            conn.inputStream.use { input ->
                zip.outputStream().use { out ->
                    val buf = ByteArray(64 * 1024)
                    var done = 0L
                    var last = -1
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        done += n
                        val pct = (done * 100 / i.size).toInt().coerceIn(0, 100)
                        if (pct != last) { progress(pct); last = pct }
                    }
                }
            }
            if (zip.length() != i.size) throw IOException("incomplete download (${zip.length()} of ${i.size})")
            val tmp = File(context.filesDir, "piper.tmp")
            tmp.deleteRecursively()
            ZipInputStream(zip.inputStream().buffered()).use { z ->
                while (true) {
                    val e = z.nextEntry ?: break
                    val f = File(tmp, e.name).canonicalFile
                    if (!f.path.startsWith(tmp.canonicalPath)) continue  // ignore odd paths
                    if (e.isDirectory) f.mkdirs() else {
                        f.parentFile?.mkdirs()
                        f.outputStream().use { z.copyTo(it) }
                    }
                }
            }
            File(tmp, ".installed").writeText(i.name)
            synchronized(this) { tts?.release(); tts = null }
            dir(context).deleteRecursively()
            if (!tmp.renameTo(dir(context))) throw IOException("could not install the voice")
            Log.i("PaliTTS", "Piper: voice installed (${i.name})")
        } catch (e: VoiceError) {
            throw e
        } catch (e: Exception) {
            Log.e("PaliTTS", "Piper download failed", e)
            throw VoiceError("Could not download the Piper voice — check internet and try again.")
        } finally {
            zip.delete()
        }
    }

    /** Removes the downloaded voice (frees about 60 MB). */
    @Synchronized
    fun remove(context: Context) {
        tts?.release()
        tts = null
        dir(context).deleteRecursively()
    }

    /** Kannada text → WAV file; speed 1.0 = normal (as rate_factor() on the desktop). */
    @Synchronized
    fun synthesize(context: Context, kannada: String, speed: Float, out: File) {
        if (!installed(context)) throw VoiceError("The Piper voice is not downloaded yet: choose it as Pāli voice again to download it.")
        val engine = tts ?: load(context.applicationContext).also { tts = it }
        Log.i("PaliTTS", "Piper: generating ${kannada.length} letters")
        val audio = engine.generate(kannada, 0, speed)
        Log.i("PaliTTS", "Piper: ${audio.samples.size} samples at ${audio.sampleRate} Hz")
        val samples = ShortArray(audio.samples.size) {
            (audio.samples[it].coerceIn(-1f, 1f) * 32767f).roundToInt().toShort()
        }
        if (samples.isEmpty()) throw VoiceError("The offline Piper voice made no sound.")
        AudioTools.writeWav(out, samples, audio.sampleRate)
    }

    private fun load(context: Context): OfflineTts {
        val d = dir(context)
        val config = OfflineTtsConfig(
            model = OfflineTtsModelConfig(
                vits = OfflineTtsVitsModelConfig(
                    model = File(d, "model.onnx").path,
                    tokens = File(d, "tokens.txt").path,
                    dataDir = File(d, "espeak-ng-data").path,
                ),
                numThreads = 2,
                debug = false,
                provider = "cpu",
            ),
        )
        Log.i("PaliTTS", "Piper: loading the model")
        return OfflineTts(null, config).also { Log.i("PaliTTS", "Piper: model loaded") }
    }
}
