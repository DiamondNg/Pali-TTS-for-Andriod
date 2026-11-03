package io.github.diamondng.readpalialoud

import android.content.BroadcastReceiver
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.speech.tts.TextToSpeech
import android.util.Log
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.slider.Slider
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale
import java.util.concurrent.Executors

/** What was asked for: the same key → the audio already made is reused. */
data class Key(val mode: String, val segs: List<Pair<String, String>>, val speed: Int,
               val voice: String, val enVoice: String?, val enSpeed: Double?)

/** Kept while the app lives, also when the window is closed and opened again. */
object Session {
    var playKey: Key? = null
    var playText: String? = null
    var audio: File? = null
    var audioKey: Key? = null
    var counter = 0
    // Python and the voices serve the whole app: they keep working when the window is
    // closed or rebuilt (e.g. turning the phone), and start only once.
    val worker: java.util.concurrent.ExecutorService = Executors.newSingleThreadExecutor()
    var bridge: PyObject? = null
    var phone: PhoneVoices? = null
    var kannada: PhoneVoices? = null
}

class MainActivity : AppCompatActivity() {

    // Pāli voices: (label, id). Same Microsoft voices as on the desktop.
    private val paliVoices = listOf(
        "Male · Microsoft (online)" to "kn-IN-GaganNeural",
        "Female · Microsoft (online)" to "kn-IN-SapnaNeural",
        "Male · Piper (offline, download once)" to PIPER,
        "Kannada · Google voice on this phone (offline)" to ANDROID_KANNADA,
    )
    private var paliSpeeds = listOf("0.33x", "0.67x", "1x", "1.33x", "1.67x")  // from pali_tts.py
    private var translationSpeeds = listOf(0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
    private var enVoices = listOf(AUTO_LABEL to AUTO_VOICE, SYSTEM_LABEL to "")

    private lateinit var text: TextView
    private lateinit var mode: MaterialButtonToggleGroup
    private lateinit var paliVoice: Spinner
    private lateinit var paliSpeed: Slider
    private lateinit var paliSpeedLabel: TextView
    private lateinit var enVoice: Spinner
    private lateinit var enVoiceLabel: TextView
    private lateinit var enSpeed: Slider
    private lateinit var enSpeedLabel: TextView
    private lateinit var status: TextView
    private lateinit var time: TextView
    private lateinit var playBtn: Button
    private lateinit var stopBtn: Button
    private lateinit var saveBtn: Button

    private val prefs by lazy { getSharedPreferences("settings", MODE_PRIVATE) }
    private val ui = Handler(Looper.getMainLooper())
    private val worker get() = Session.worker  // Python + voices, in order
    private val bridge: PyObject get() = Session.bridge ?: throw IllegalStateException("Python not started")
    private val phone: PhoneVoices get() = Session.phone!!

    private val kannada: PhoneVoices get() = Session.kannada!!  // Google's engine if installed

    private var busy = false
    // The audio made last and what it was made from: kept while the app lives (Session)
    private var playKey by Session::playKey
    private var playText by Session::playText
    private var audio by Session::audio
    private var audioKey by Session::audioKey

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        findViews()
        // Android 15 draws behind the status/navigation bars and the keyboard: keep clear of them
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.root)) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            WindowInsetsCompat.CONSUMED
        }
        val toolbar = findViewById<MaterialToolbar>(R.id.toolbar)
        toolbar.inflateMenu(R.menu.main)
        toolbar.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                R.id.action_paste -> paste()
                R.id.action_clear -> { stop(); text.text = "" }
                R.id.action_help -> showHelp()
                R.id.action_remove_piper -> removePiper()
            }
            true
        }

        setUpControls()
        restoreSettings()
        if (Session.phone == null) {
            Session.phone = PhoneVoices(applicationContext)
            Session.kannada = if (googleTtsInstalled()) PhoneVoices(applicationContext, GOOGLE_TTS) else Session.phone
        }
        Playback.listener = Playback.Listener { showPlayback() }
        showPlayback()
        status.text = "Starting…"
        worker.execute {
            try {
                if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                if (Session.bridge == null) Session.bridge = Python.getInstance().getModule("bridge")
                val sp = JSONObject(bridge.callAttr("speeds").toString())
                val labels = sp.getJSONArray("labels").let { a -> (0 until a.length()).map { a.getString(it) } }
                val tr = sp.getJSONArray("translation").let { a -> (0 until a.length()).map { a.getDouble(it) } }
                ui.post {
                    paliSpeeds = labels
                    translationSpeeds = tr
                    updateSpeedLabels()
                    if (status.text == "Starting…") status.text = ""
                }
            } catch (e: Throwable) {
                Log.e(TAG, "Python did not start", e)
                ui.post { status.text = "Could not start: ${e.message}" }
            }
        }
        worker.execute { loadPhoneVoices() }
        handleIntent(intent, savedInstanceState == null)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent, true)
    }

    override fun onPause() {
        super.onPause()
        saveSettings()
    }

    override fun onDestroy() {
        // Reading, Python and the voices go on (Session, Playback); only the window ends
        Log.i(TAG, "window closed (rebuilt: $isChangingConfigurations)")
        Playback.listener = null
        ui.removeCallbacks(ticker)
        super.onDestroy()
    }

    private fun findViews() {
        text = findViewById(R.id.text)
        mode = findViewById(R.id.mode)
        paliVoice = findViewById(R.id.pali_voice)
        paliSpeed = findViewById(R.id.pali_speed)
        paliSpeedLabel = findViewById(R.id.pali_speed_label)
        enVoice = findViewById(R.id.en_voice)
        enVoiceLabel = findViewById(R.id.en_voice_label)
        enSpeed = findViewById(R.id.en_speed)
        enSpeedLabel = findViewById(R.id.en_speed_label)
        status = findViewById(R.id.status)
        time = findViewById(R.id.time)
        playBtn = findViewById(R.id.play)
        stopBtn = findViewById(R.id.stop)
        saveBtn = findViewById(R.id.save)
    }

    // ── Text from other apps ─────────────────────────────────────────────────
    /** Select text → "Read Pāli Aloud", or Share → Read Pāli Aloud: show it and start reading. */
    private fun handleIntent(intent: Intent?, fresh: Boolean) {
        if (intent == null) return
        if (intent.getBooleanExtra("selftest", false)) {
            selftest()
            return
        }
        if (!fresh) return
        val incoming = when (intent.action) {
            Intent.ACTION_PROCESS_TEXT -> intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)
            Intent.ACTION_SEND -> intent.getCharSequenceExtra(Intent.EXTRA_TEXT)
            else -> null
        }?.toString()
        if (incoming.isNullOrBlank()) return
        stop()
        text.text = incoming.trim()
        worker.execute {  // after Python has started
            val prepared = try { bridge.callAttr("prepare_text", incoming).toString() } catch (e: Throwable) { incoming.trim() }
            ui.post {
                text.text = prepared
                start()
            }
        }
    }

    private fun paste() {
        val clip = (getSystemService(CLIPBOARD_SERVICE) as ClipboardManager).primaryClip
        val pasted = clip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(this)?.toString()
        if (!pasted.isNullOrBlank()) {
            stop()
            text.text = pasted.trim()
        }
    }

    // ── Controls and settings ─────────────────────────────────────────────────
    private fun setUpControls() {
        paliVoice.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item,
            paliVoices.map { it.first })
        setEnVoiceList()
        paliVoice.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                if (paliVoices[pos].second == PIPER && !PiperVoice.installed(this@MainActivity)) offerPiper(null)
                else lastPaliVoice = pos
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        paliSpeed.setLabelFormatter { paliSpeeds.getOrElse(it.toInt()) { "" } }
        enSpeed.setLabelFormatter { speedLabel(translationSpeeds.getOrElse(it.toInt()) { 1.0 }) }
        paliSpeed.addOnChangeListener { _, _, _ -> updateSpeedLabels() }
        enSpeed.addOnChangeListener { _, _, _ -> updateSpeedLabels() }
        mode.addOnButtonCheckedListener { _, _, _ -> onModeChanged() }
        playBtn.setOnClickListener { toggle() }
        stopBtn.setOnClickListener { stop() }
        saveBtn.setOnClickListener { save() }
        findViewById<Button>(R.id.kannada_setup).setOnClickListener { kannadaSetup() }
        saveBtn.isEnabled = false
        updateSpeedLabels()
    }

    private fun setEnVoiceList() {
        val keep = selectedEnVoiceId() ?: prefs.getString("en_voice", AUTO_VOICE)
        enVoice.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item,
            enVoices.map { it.first })
        enVoice.setSelection(enVoices.indexOfFirst { it.second == keep }.coerceAtLeast(0))
    }

    private fun selectedEnVoiceId(): String? =
        if (!::enVoice.isInitialized || enVoice.adapter == null) null
        else enVoices.getOrNull(enVoice.selectedItemPosition)?.second

    private fun loadPhoneVoices() {
        if (!phone.awaitReady()) return
        val list = phone.voices().map { phone.label(it) to it.name }.sortedBy { it.first }
        ui.post {
            enVoices = listOf(AUTO_LABEL to AUTO_VOICE, SYSTEM_LABEL to "") + list
            setEnVoiceList()
        }
    }

    /** 1.0 → "1x", 0.75 → "0.75x" (as speed_label() in pali_tts.py) */
    private fun speedLabel(x: Double) =
        (if (x == Math.floor(x)) x.toLong().toString() else x.toString()) + "x"

    private fun updateSpeedLabels() {
        paliSpeedLabel.text = "Pāli speed:  " + paliSpeeds.getOrElse(paliSpeed.value.toInt()) { "" }
        enSpeedLabel.text = "Translation speed:  " + speedLabel(currentEnSpeed())
    }

    private fun currentEnSpeed() = translationSpeeds.getOrElse(enSpeed.value.toInt()) { 1.0 }

    private fun currentMode() = when (mode.checkedButtonId) {
        R.id.mode_en -> "en"
        R.id.mode_both -> "both"
        else -> "pi"
    }

    private fun onModeChanged() {
        val translation = currentMode() != "pi"
        for (v in listOf<View>(enVoice, enSpeed, enVoiceLabel, enSpeedLabel)) v.alpha = if (translation) 1f else 0.4f
        enVoice.isEnabled = translation
        enSpeed.isEnabled = translation
    }

    private fun restoreSettings() {
        mode.check(when (prefs.getString("mode", "pi")) {
            "en" -> R.id.mode_en
            "both" -> R.id.mode_both
            else -> R.id.mode_pi
        })
        paliVoice.setSelection(paliVoices.indexOfFirst { it.second == prefs.getString("voice", "") }.coerceAtLeast(0))
        paliSpeed.value = prefs.getInt("rate", 2).coerceIn(0, 4).toFloat()
        val en = prefs.getFloat("en_speed", 1f).toDouble()
        enSpeed.value = translationSpeeds.indexOfFirst { it == en }.coerceAtLeast(0).toFloat()
        text.text = prefs.getString("text", "")
        onModeChanged()
        updateSpeedLabels()
    }

    private fun saveSettings() {
        prefs.edit()
            .putString("mode", currentMode())
            .putString("voice", paliVoices[paliVoice.selectedItemPosition].second)
            .putInt("rate", paliSpeed.value.toInt())
            .putString("en_voice", selectedEnVoiceId() ?: AUTO_VOICE)
            .putFloat("en_speed", currentEnSpeed().toFloat())
            .putString("text", text.text.toString())
            .apply()
    }

    // ── Play / Pause / Stop ───────────────────────────────────────────────────
    private fun isPlaying() = Playback.active

    private fun toggle() {
        if (busy) return
        if (isPlaying()) {
            if (!Playback.paused) {
                Playback.pause()
                return
            }
            // Paused: resume, unless the text, speed or voice changed meanwhile
            if (unchangedSincePlay()) {
                Playback.resume()
                return
            }
            stop()
        }
        start()
    }

    /** True if the text and choices are still those of the audio being played. */
    private fun unchangedSincePlay(): Boolean {
        val k = playKey ?: return false
        return k.mode == currentMode() && k.speed == paliSpeed.value.toInt() &&
            k.voice == paliVoices[paliVoice.selectedItemPosition].second &&
            (k.mode == "pi" || (k.enVoice == selectedEnVoiceId() && k.enSpeed == currentEnSpeed())) &&
            playText == text.text.toString()
    }

    private fun start() {
        val content = text.text.toString().trim()
        if (content.isEmpty()) {
            status.text = "Please paste some text first."
            return
        }
        val m = currentMode()
        val speed = paliSpeed.value.toInt()
        val voice = paliVoices[paliVoice.selectedItemPosition].second
        if (voice == PIPER && !PiperVoice.installed(this)) {
            offerPiper { start() }
            return
        }
        val enV = if (m != "pi") selectedEnVoiceId() ?: AUTO_VOICE else null
        val enS = if (m != "pi") currentEnSpeed() else null
        busy = true
        playBtn.isEnabled = false
        time.text = ""
        status.text = if (voice in OFFLINE_VOICES) "Generating…" else "Connecting…"
        val shownText = text.text.toString()
        worker.execute {
            try {
                val segs = JSONArray(bridge.callAttr("segments", content, m).toString()).let { a ->
                    (0 until a.length()).map { a.getJSONArray(it).let { p -> p.getString(0) to p.getString(1) } }
                }
                if (segs.isEmpty()) {
                    fail(if (m == "en") "No translation (non-Pāli) text detected." else "No Pāli text detected.")
                    return@execute
                }
                val key = Key(m, segs, speed, voice, enV, enS)
                val ready = audio
                if (key == audioKey && ready != null && ready.exists()) {
                    ui.post { done(key, ready, shownText) }
                    return@execute
                }
                val out = generate(key)
                ui.post { done(key, out, shownText) }
            } catch (e: VoiceError) {
                fail(e.message ?: "Voice error")
            } catch (e: Throwable) {
                Log.e(TAG, "generation failed", e)
                fail(if (voice in OFFLINE_VOICES && enV == null) "Audio generation failed."
                     else "Audio generation failed — check internet.")
            }
        }
    }

    private fun setStatus(msg: String) = ui.post { status.text = msg }

    private fun fail(msg: String) = ui.post {
        busy = false
        playBtn.isEnabled = true
        status.text = msg
    }

    /** Runs on the worker thread: text → one audio file (MP3 or WAV). */
    private fun generate(key: Key): File {
        val work = File(cacheDir, "audio").apply { mkdirs() }
        work.listFiles()?.forEach { if (it != audio) it.delete() }  // old audio
        val tag = "%d_%d".format(System.currentTimeMillis(), ++Session.counter)
        setStatus("Transliterating…")
        val parts = key.segs.map { (lang, t) ->
            if (lang == "pi") "kn" to bridge.callAttr("kannada", t).toString() else lang to t
        }
        val files = arrayOfNulls<List<File>>(parts.size)
        val kn = parts.indices.filter { parts[it].first == "kn" }
        if (kn.isNotEmpty()) {
            setStatus("Generating Pāli audio…")
            if (key.voice == PIPER) {
                val factor = bridge.callAttr("rate_factor", key.speed).toFloat()
                for (i in kn) {
                    val f = File(work, "${tag}_$i.wav")
                    PiperVoice.synthesize(this, parts[i].second, factor, f)
                    files[i] = listOf(f)
                }
            } else if (key.voice == ANDROID_KANNADA) {
                val v = kannada.kannadaVoice()
                val factor = bridge.callAttr("rate_factor", key.speed).toFloat()
                for (i in kn) files[i] = kannada.synthesize(parts[i].second, v, factor,
                    File(work, "${tag}_$i"), PhoneVoices.KANNADA)
            } else {
                val jobs = JSONArray()
                for (i in kn) jobs.put(JSONArray().put(parts[i].second).put(File(work, "${tag}_$i.mp3").path))
                bridge.callAttr("microsoft", jobs.toString(), key.speed, key.voice)
                for (i in kn) files[i] = listOf(File(work, "${tag}_$i.mp3"))
            }
        }
        val other = parts.indices.filter { parts[it].first != "kn" }
        if (other.isNotEmpty()) {
            setStatus("Generating translation audio…")
            if (!phone.awaitReady()) throw VoiceError("The phone's text-to-speech is not working. " + PhoneVoices.TTS_SETTINGS)
            val chosen = key.enVoice ?: AUTO_VOICE
            val fixed = if (chosen == AUTO_VOICE || chosen == "") null else phone.voices().firstOrNull { it.name == chosen }
            for (i in other) {
                val v = if (chosen == AUTO_VOICE) phone.voiceFor(parts[i].first) else fixed
                files[i] = phone.synthesize(parts[i].second, v, (key.enSpeed ?: 1.0).toFloat(), File(work, "${tag}_$i"))
            }
        }
        val all = files.flatMap { it.orEmpty() }
        if (all.size == 1) return all[0]
        setStatus("Joining…")
        val out = File(work, "$tag.wav")
        AudioTools.join(all, out)
        all.forEach { it.delete() }
        return out
    }

    private fun done(key: Key, file: File, shownText: String) {
        busy = false
        playBtn.isEnabled = true
        if (audio != null && audio != file) audio?.delete()
        audio = file
        audioKey = key
        saveBtn.isEnabled = true
        playKey = key
        playText = shownText
        play(file)
    }

    private fun play(file: File) {
        val first = audioKey?.segs?.firstOrNull()?.second.orEmpty()
        val title = first.split(Regex("\\s+")).take(6).joinToString(" ")
        if (!Playback.play(this, file, title)) status.text = "Could not play the audio."
    }

    private fun stop() = Playback.stop()

    /** Shows the player's state (also after the window was closed and opened again). */
    private fun showPlayback() {
        ui.removeCallbacks(ticker)
        when {
            !Playback.active -> {
                playBtn.text = getString(R.string.play)
                if (Playback.lastEvent.isNotEmpty() && !busy) status.text = Playback.lastEvent
            }
            Playback.paused -> {
                playBtn.text = getString(R.string.resume)
                status.text = "Paused"
                tick()
            }
            else -> {
                playBtn.text = getString(R.string.pause)
                status.text = "Playing…"
                tick()
            }
        }
        saveBtn.isEnabled = audio?.exists() == true
    }

    private val ticker = Runnable { tick() }

    private fun tick() {
        if (!Playback.active) return
        time.text = fmt(Playback.position) + " / " + fmt(Playback.duration)
        ui.removeCallbacks(ticker)
        if (!Playback.paused) ui.postDelayed(ticker, 250)
    }

    private fun fmt(ms: Int): String {
        val s = (ms / 1000).coerceAtLeast(0)
        return if (s >= 3600) "%d:%02d:%02d".format(s / 3600, s / 60 % 60, s % 60)
        else "%d:%02d".format(s / 60, s % 60)
    }

    // ── Save ──────────────────────────────────────────────────────────────────
    private val saveMp3 = registerForActivityResult(ActivityResultContracts.CreateDocument("audio/mpeg")) { uri ->
        uri?.let { writeSaved(it) }
    }
    private val saveM4a = registerForActivityResult(ActivityResultContracts.CreateDocument("audio/mp4")) { uri ->
        uri?.let { writeSaved(it) }
    }

    /** Microsoft's Pāli audio is saved as MP3 (as on the desktop); anything joined with the
     *  phone's voices as M4A (Android cannot write MP3). */
    private fun save() {
        val f = audio ?: return
        val key = audioKey ?: return
        worker.execute {
            val name = try {
                bridge.callAttr("save_name", key.mode, key.segs[0].second, key.speed,
                    key.enSpeed ?: 1.0).toString()
            } catch (e: Throwable) { "pali_audio" }
            ui.post {
                if (f.name.endsWith(".mp3")) saveMp3.launch("$name.mp3") else saveM4a.launch("$name.m4a")
            }
        }
    }

    private fun writeSaved(uri: Uri) {
        val f = audio ?: return
        status.text = "Saving…"
        worker.execute {
            try {
                val src = if (f.name.endsWith(".mp3")) f else
                    File(cacheDir, "export.m4a").also { AudioTools.toM4a(f, it) }
                contentResolver.openOutputStream(uri)?.use { out -> src.inputStream().use { it.copyTo(out) } }
                if (src != f) src.delete()
                setStatus("Saved.")
            } catch (e: Throwable) {
                Log.e(TAG, "save failed", e)
                setStatus("Could not save the audio.")
            }
        }
    }

    // ── Piper voice: downloaded once when chosen ──────────────────────────────────────
    private var lastPaliVoice = 0
    private var downloading = false

    /** Asks before downloading the Piper voice; then (optionally) continues with `after`. */
    private fun offerPiper(after: (() -> Unit)?) {
        if (downloading) return
        MaterialAlertDialogBuilder(this)
            .setTitle("Download the Piper voice?")
            .setMessage("The offline Piper voice (male, the same as on the computer) is downloaded " +
                "once: about ${PiperVoice.downloadMb(this)} MB — Wi-Fi recommended. After that it " +
                "works without internet.")
            .setPositiveButton("Download") { _, _ -> downloadPiper(after) }
            .setNegativeButton("Not now") { _, _ -> paliVoice.setSelection(lastPaliVoice) }
            .setOnCancelListener { paliVoice.setSelection(lastPaliVoice) }
            .show()
    }

    private fun downloadPiper(after: (() -> Unit)?) {
        downloading = true
        playBtn.isEnabled = false
        status.text = "Downloading the Piper voice…"
        Thread {
            try {
                PiperVoice.download(this) { pct -> setStatus("Downloading the Piper voice… $pct%") }
                ui.post {
                    downloading = false
                    playBtn.isEnabled = true
                    status.text = "Piper voice ready (offline)."
                    lastPaliVoice = paliVoices.indexOfFirst { it.second == PIPER }
                    after?.invoke()
                }
            } catch (e: Exception) {
                ui.post {
                    downloading = false
                    playBtn.isEnabled = true
                    status.text = e.message ?: "Could not download the Piper voice."
                    paliVoice.setSelection(lastPaliVoice)
                }
            }
        }.start()
    }

    private fun removePiper() {
        if (!PiperVoice.installed(this)) {
            status.text = "The Piper voice is not downloaded."
            return
        }
        MaterialAlertDialogBuilder(this)
            .setTitle("Remove the Piper voice?")
            .setMessage("Frees about ${PiperVoice.downloadMb(this)} MB. You can download it again later.")
            .setPositiveButton("Remove") { _, _ ->
                worker.execute { PiperVoice.remove(this) }
                if (paliVoices[paliVoice.selectedItemPosition].second == PIPER) {
                    lastPaliVoice = 0
                    paliVoice.setSelection(0)
                }
                status.text = "Piper voice removed."
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    // ── The phone's own (Google) Kannada voice ───────────────────────────────────────
    private fun googleTtsInstalled() = try {
        packageManager.getPackageInfo(GOOGLE_TTS, 0)
        true
    } catch (e: Exception) {
        false
    }

    private fun tryStart(vararg intents: Intent): Boolean {
        for (i in intents) {
            try {
                startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return true
            } catch (e: Exception) {}
        }
        status.text = "Could not open the settings on this phone: see Help."
        return false
    }

    /** Steps to get Google's offline Kannada voice, with buttons that open the right screens. */
    private fun kannadaSetup() {
        val installed = googleTtsInstalled()
        MaterialAlertDialogBuilder(this)
            .setTitle("Offline Kannada voice (Google)")
            .setMessage(KANNADA_STEPS + if (installed) "" else
                "\n\nThis phone does not have \"Speech Services by Google\" yet: tap \"Get Google's voices\" first.")
            .setPositiveButton(if (installed) "Install Kannada" else "Get Google's voices") { _, _ ->
                if (installed) {
                    tryStart(Intent(TextToSpeech.Engine.ACTION_INSTALL_TTS_DATA).setPackage(GOOGLE_TTS),
                        Intent(TTS_SETTINGS_ACTION))
                } else {
                    tryStart(Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$GOOGLE_TTS")),
                        Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=$GOOGLE_TTS")))
                }
            }
            .setNeutralButton("Speech settings") { _, _ -> tryStart(Intent(TTS_SETTINGS_ACTION)) }
            .setNegativeButton("Use it") { _, _ ->
                paliVoice.setSelection(paliVoices.indexOfFirst { it.second == ANDROID_KANNADA })
            }
            .show()
    }

    // ── Help ──────────────────────────────────────────────────────────────────
    private fun showHelp() {
        val version = try { packageManager.getPackageInfo(packageName, 0).versionName } catch (e: Exception) { "" }
        MaterialAlertDialogBuilder(this)
            .setTitle("Read Pāli Aloud $version")
            .setMessage(HELP)
            .setPositiveButton("OK", null)
            .show()
    }

    // ── Automated test (CI): no sound, only the Python part and the phone's voices ─
    private fun selftest() {
        worker.execute {
            try {
                val result = bridge.callAttr("selftest").toString()
                Log.i(TAG, "SELFTEST python $result")
                val voices = if (phone.awaitReady()) phone.voices().size else -1
                Log.i(TAG, "SELFTEST phone voices: $voices")
                // Joining: two short silent WAVs → one, and M4A export
                val a = File(cacheDir, "t1.wav").also { AudioTools.writeWav(it, ShortArray(2400)) }
                val b = File(cacheDir, "t2.wav").also { AudioTools.writeWav(it, ShortArray(12000), 16000) }
                val j = File(cacheDir, "tj.wav")
                AudioTools.join(listOf(a, b), j)
                val m = File(cacheDir, "tj.m4a")
                AudioTools.toM4a(j, m)
                Log.i(TAG, "SELFTEST join ${j.length()} m4a ${m.length()}")
                // Offline Piper voice (the whole chain: Kannada → eSpeak NG → model → WAV)
                Log.i(TAG, "SELFTEST piper download starting")
                PiperVoice.download(this) { pct -> if (pct % 25 == 0) Log.i(TAG, "SELFTEST piper download $pct%") }
                Log.i(TAG, "SELFTEST piper installed: ${PiperVoice.installed(this)}")
                val pv = File(cacheDir, "piper.wav")
                val kn = bridge.callAttr("kannada", "Evaṃ me sutaṃ. Ekaṃ samayaṃ bhagavā.").toString()
                PiperVoice.synthesize(this, kn, 1f, pv)
                val secs = AudioTools.decodeMono(pv).samples.size / AudioTools.RATE.toDouble()
                Log.i(TAG, "SELFTEST piper %.2f s".format(secs))
                if (secs < 1.0) throw IllegalStateException("Piper audio too short")
                // Background player: plays the joined (silent) file → notification appears
                val tone = File(cacheDir, "tone.wav").also {
                    AudioTools.writeWav(it, ShortArray(24000 * 20) { i -> (Math.sin(i * 0.06) * 3000).toInt().toShort() })
                }
                ui.post {
                    Log.i(TAG, "SELFTEST label: ${paliSpeedLabel.text}")
                    val ok = Playback.play(this, tone, "Selftest tone")
                    Log.i(TAG, "SELFTEST playback started: $ok")
                }
                Log.i(TAG, "SELFTEST OK")
            } catch (e: Throwable) {
                Log.e(TAG, "SELFTEST FAILED", e)
            }
        }
    }

    companion object {
        const val TAG = "PaliTTS"
        const val ANDROID_KANNADA = "android-kn"
        const val PIPER = "piper"
        val OFFLINE_VOICES = setOf(PIPER, ANDROID_KANNADA)
        const val GOOGLE_TTS = "com.google.android.tts"
        const val TTS_SETTINGS_ACTION = "com.android.settings.TTS_SETTINGS"
        val KANNADA_STEPS = """
            Google's Kannada voice works without internet. To install it once:
            1. Tap "Install Kannada" (or Phone Settings → search "Text-to-speech" → ⚙ next to "Speech Services by Google" → Install voice data).
            2. Find Kannada (ಕನ್ನಡ) in the list and tap the download arrow ⤓. Wait until it is downloaded.
            3. Come back here and choose the Pāli voice "Kannada · Google voice on this phone (offline)".
            Your phone does not need Google as its main voice: this app asks Google directly.
        """.trimIndent()
        const val AUTO_VOICE = "auto"
        const val AUTO_LABEL = "Auto (by language)"
        const val SYSTEM_LABEL = "Phone's default voice"

        val HELP = """
            HOW TO USE
            • Paste or type text, then tap Play. Or, in any app, select text → in the menu that appears (tap ⋮ if needed) → Read Pāli Aloud. Or Share → Read Pāli Aloud.

            READ
            • Pāli: only the Pāli lines are read; translations are skipped.
            • Translation: only the other lines (any language), read by the phone's own voices.
            • Both: everything, in order.

            PĀLI VOICE
            • Microsoft Male/Female: the best quality; needs internet.
            • Male · Piper: works offline on every phone (the same voice as on the computer). Downloaded once (about 60 MB) the first time you choose it; ⋮ → "Remove Piper voice" frees the space. Voice: micahchoo/piper-kn (CC BY 4.0), engine sherpa-onnx.
            • Kannada · Google voice on this phone: works offline once installed. Tap "Offline Kannada voice…" under the Pāli voice for the steps:
              Phone Settings → search "Text-to-speech" → ⚙ next to "Speech Services by Google" → Install voice data → Kannada (ಕನ್ನಡ) → download.

            LISTENING IN THE BACKGROUND
            • Reading goes on with the screen off or in other apps. Pause / Play / Stop are in the notification and on the lock screen (and on headphone buttons).

            TRANSLATION VOICE
            • Auto: a voice for each line's language (English, Chinese, Malay, …). Add languages in the phone's text-to-speech settings.

            SAVE AUDIO
            • After playing, "Save audio…" lets you choose where to keep it. Pāli with a Microsoft voice is saved as MP3, everything else as M4A.

            Pāli is written in Kannada letters (Aksharamukha) so the Kannada voice pronounces it well.
            Free software (AGPL-3.0). Āyasmā Paññādhammika.
        """.trimIndent()
    }
}
