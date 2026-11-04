package io.github.diamondng.readpalialoud

import android.content.Context
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import java.io.File
import java.io.IOException
import java.util.Locale
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** A voice cannot be used; the message is shown to the user. */
class VoiceError(message: String) : Exception(message)

/** The phone's own text-to-speech voices (Google, Samsung, ...): translations in any
 *  language, and the offline Kannada voice for Pāli. */
class PhoneVoices(context: Context, engine: String? = null) {
    private val ready = CountDownLatch(1)
    @Volatile private var ok = false
    private val waits = ConcurrentHashMap<String, CountDownLatch>()
    private val errors = ConcurrentHashMap<String, Int>()
    private val tts = TextToSpeech(context.applicationContext, { status ->
        ok = status == TextToSpeech.SUCCESS
        ready.countDown()
    }, engine)

    init {
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String) {}
            override fun onDone(utteranceId: String) {
                waits[utteranceId]?.countDown()
            }
            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String) {
                errors[utteranceId] = -1
                waits[utteranceId]?.countDown()
            }
            override fun onError(utteranceId: String, errorCode: Int) {
                errors[utteranceId] = errorCode
                waits[utteranceId]?.countDown()
            }
        })
    }

    /** Waits (on a background thread) until the voices can be used. */
    fun awaitReady(seconds: Long = 20): Boolean {
        return try {
            ready.await(seconds, TimeUnit.SECONDS)
            ok
        } catch (e: InterruptedException) {
            false
        }
    }

    fun shutdown() = try { tts.shutdown() } catch (e: Exception) {}

    /** Installed voices (not the ones still to be downloaded). */
    fun voices(): List<Voice> = try {
        tts.voices.orEmpty().filter {
            TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED !in it.features.orEmpty()
        }
    } catch (e: Exception) {
        emptyList()
    }

    private fun defaultVoice(): Voice? = try { tts.defaultVoice } catch (e: Exception) { null }

    fun label(v: Voice): String =
        v.locale.getDisplayName(Locale.ENGLISH) + " · " + v.name +
            (if (v.isNetworkConnectionRequired) " (online)" else "")

    /** Best installed voice for a language code from pali_core.guess_language ("en", "zh", ...);
     *  null = the phone's default voice. Same preferences as the desktop's pick_voice(). */
    fun voiceFor(lang: String): Voice? {
        val default = defaultVoice()
        for (code in listOf(lang) + SIMILAR_LANGUAGE[lang].orEmpty()) {
            if (default != null && languageOf(default) == code) return default
            val match = voices().filter { languageOf(it) == code }
            if (match.isNotEmpty()) {
                val region = PREFERRED_REGION[code]
                return match.sortedWith(compareBy<Voice>(
                    { it.isNetworkConnectionRequired },
                    { region != null && it.locale.country != region },
                    { -it.quality },
                )).first()
            }
        }
        return null
    }

    /** The phone's Kannada voice for Pāli (offline if possible), or a VoiceError. */
    fun kannadaVoice(): Voice? {
        val kn = voices().filter { languageOf(it) == "kn" }
        if (kn.isNotEmpty()) return kn.sortedWith(compareBy<Voice>({ it.isNetworkConnectionRequired }, { -it.quality })).first()
        val available = try { tts.isLanguageAvailable(KANNADA) } catch (e: Exception) { -2 }
        if (available >= TextToSpeech.LANG_AVAILABLE) return null  // use the language instead
        throw VoiceError(KANNADA_HOWTO)
    }

    /** Text → WAV file(s) in the given voice (null = default) at the given speed (1.0 = normal).
     *  Long text is cut into pieces (the voices take about 4000 letters at most). */
    @Synchronized
    fun synthesize(text: String, voice: Voice?, rate: Float, base: File, locale: Locale? = null): List<File> {
        if (!awaitReady()) throw VoiceError("The phone's text-to-speech is not working. " + TTS_SETTINGS)
        val max = minOf(TextToSpeech.getMaxSpeechInputLength() - 100, 3000)
        val files = mutableListOf<File>()
        for ((i, piece) in pieces(text, max).withIndex()) {
            when {
                voice != null -> tts.voice = voice
                locale != null -> tts.language = locale
                else -> defaultVoice()?.let { tts.voice = it } ?: run { tts.language = Locale.getDefault() }
            }
            tts.setSpeechRate(rate)
            val out = File(base.path + "_$i.wav")
            val id = UUID.randomUUID().toString()
            val latch = CountDownLatch(1)
            waits[id] = latch
            try {
                if (tts.synthesizeToFile(piece, Bundle(), out, id) != TextToSpeech.SUCCESS)
                    throw IOException("synthesizeToFile refused")
                if (!latch.await(10, TimeUnit.MINUTES)) throw IOException("voice timed out")
                errors.remove(id)?.let { throw IOException("voice error $it") }
            } finally {
                waits.remove(id)
            }
            if (!out.exists() || out.length() <= 44) throw IOException("voice made no audio")
            files.add(out)
        }
        return files
    }

    companion object {
        val KANNADA = Locale("kn", "IN")
        const val TTS_SETTINGS = "Phone Settings → search \"Text-to-speech\"."
        const val KANNADA_HOWTO = "Google's Kannada voice is not installed yet: tap " +
            "\"Offline Kannada voice…\" for the steps, or choose a Microsoft voice (needs internet)."

        // Same as PREFERRED_REGION / SIMILAR_LANGUAGE in pali_tts.py (desktop)
        val PREFERRED_REGION = mapOf("en" to "US", "zh" to "CN", "pt" to "BR", "es" to "ES",
            "fr" to "FR", "de" to "DE")
        val SIMILAR_LANGUAGE = mapOf("ms" to listOf("id"), "id" to listOf("ms"),
            "uk" to listOf("ru"), "tl" to listOf("fil"))

        /** Java's old codes ("in" = Indonesian, "iw" = Hebrew) → today's. */
        fun languageOf(v: Voice): String = when (val l = v.locale.language) {
            "in" -> "id"
            "iw" -> "he"
            "ji" -> "yi"
            else -> l
        }

        /** Cuts text into pieces of at most `max` letters, at sentence ends if possible. */
        fun pieces(text: String, max: Int): List<String> {
            val out = mutableListOf<String>()
            var current = StringBuilder()
            for (sentence in text.split(Regex("(?<=[.!?;।。！？])\\s+"))) {
                var s = sentence
                while (s.length > max) {  // one very long sentence: cut at a space
                    val cut = s.lastIndexOf(' ', max).takeIf { it > 0 } ?: max
                    if (current.isNotEmpty()) { out.add(current.toString()); current = StringBuilder() }
                    out.add(s.substring(0, cut))
                    s = s.substring(cut).trim()
                }
                if (current.length + s.length + 1 > max && current.isNotEmpty()) {
                    out.add(current.toString())
                    current = StringBuilder()
                }
                if (current.isNotEmpty()) current.append(' ')
                current.append(s)
            }
            if (current.isNotBlank()) out.add(current.toString())
            return out
        }
    }
}
