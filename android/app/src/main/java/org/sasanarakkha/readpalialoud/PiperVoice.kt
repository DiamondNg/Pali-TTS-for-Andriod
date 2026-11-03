package org.sasanarakkha.readpalialoud

import android.content.Context
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import android.util.Log
import java.io.File
import kotlin.math.roundToInt

/** The Piper Kannada voice (same voice as the desktop apps), built into the app: works
 *  offline on every phone. Engine: sherpa-onnx. Voice: micahchoo/piper-kn, CC BY 4.0. */
object PiperVoice {
    private const val DIR = "piper"
    private var tts: OfflineTts? = null

    fun available(context: Context) = try {
        context.assets.open("$DIR/tokens.txt").close()
        true
    } catch (e: Exception) {
        false
    }

    /** Kannada text → WAV file; speed 1.0 = normal (as rate_factor() on the desktop). */
    @Synchronized
    fun synthesize(context: Context, kannada: String, speed: Float, out: File) {
        if (!available(context)) throw VoiceError("The offline Piper voice is not in this build of the app.")
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
        // eSpeak NG (pronunciation rules) must be real files: copied once per app version
        val data = File(context.filesDir, "espeak-ng-data")
        val stamp = File(data, ".version")
        val version = BuildConfig.VERSION_CODE.toString()
        if (!stamp.exists() || stamp.readText() != version) {
            data.deleteRecursively()
            copyAssets(context, "$DIR/espeak-ng-data", data)
            stamp.writeText(version)
            Log.i("PaliTTS", "Piper: eSpeak NG data copied")
        }
        val config = OfflineTtsConfig(
            model = OfflineTtsModelConfig(
                vits = OfflineTtsVitsModelConfig(
                    model = "$DIR/model.onnx",
                    tokens = "$DIR/tokens.txt",
                    dataDir = data.path,
                ),
                numThreads = 2,
                debug = false,
                provider = "cpu",
            ),
        )
        Log.i("PaliTTS", "Piper: loading the model")
        return OfflineTts(context.assets, config).also { Log.i("PaliTTS", "Piper: model loaded") }
    }

    private fun copyAssets(context: Context, path: String, dest: File) {
        val children = context.assets.list(path).orEmpty()
        if (children.isEmpty()) {  // a file
            dest.parentFile?.mkdirs()
            context.assets.open(path).use { input -> dest.outputStream().use { input.copyTo(it) } }
            return
        }
        dest.mkdirs()
        for (c in children) copyAssets(context, "$path/$c", File(dest, c))
    }
}
