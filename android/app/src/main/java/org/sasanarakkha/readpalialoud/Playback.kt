package org.sasanarakkha.readpalialoud

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.util.Log
import java.io.File

/** The one audio player of the app. It lives as long as the app (not the window), so reading
 *  goes on with the screen off or in another app; PlaybackService shows its notification and
 *  lock-screen controls. Use from the main thread only. */
object Playback {
    fun interface Listener { fun onPlaybackChanged() }

    var listener: Listener? = null
    private var mp: MediaPlayer? = null
    private lateinit var app: Context
    private val main = Handler(Looper.getMainLooper())

    var paused = false
        private set
    var title = ""
        private set
    /** "Finished", "Stopped" … for the status line after the player is gone. */
    var lastEvent = ""
        private set

    val active get() = mp != null
    val position get() = try { mp?.currentPosition ?: 0 } catch (e: IllegalStateException) { 0 }
    val duration get() = try { mp?.duration ?: 0 } catch (e: IllegalStateException) { 0 }

    fun play(context: Context, file: File, title: String): Boolean {
        app = context.applicationContext
        release()
        val p = MediaPlayer()
        try {
            p.setAudioAttributes(attributes)
            p.setWakeMode(app, PowerManager.PARTIAL_WAKE_LOCK)  // keeps playing with the screen off
            p.setDataSource(file.path)
            p.prepare()
        } catch (e: Exception) {
            Log.e("PaliTTS", "play failed", e)
            p.release()
            return false
        }
        p.setOnCompletionListener { finish("Finished") }
        mp = p
        this.title = title
        paused = false
        requestFocus()
        p.start()
        changed()
        return true
    }

    fun pause() {
        val p = mp ?: return
        if (paused) return
        p.pause()
        paused = true
        changed()
    }

    fun resume() {
        val p = mp ?: return
        if (!paused) return
        requestFocus()
        p.start()
        paused = false
        changed()
    }

    fun stop() = finish("Stopped")

    private fun finish(event: String) {
        if (mp == null) return
        release()
        lastEvent = event
        changed()
    }

    private fun release() {
        mp?.let {
            try { it.stop() } catch (e: Exception) {}
            it.release()
        }
        mp = null
        paused = false
        abandonFocus()
    }

    private fun changed() {
        listener?.onPlaybackChanged()
        PlaybackService.refresh(app)
    }

    // ── Pause for calls, other apps' sound, and unplugged headphones ──────────────────
    private val attributes = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA)
        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
    private var focusRequest: AudioFocusRequest? = null
    private val focusListener = AudioManager.OnAudioFocusChangeListener { change ->
        if (change < 0) main.post { pause() }
    }
    private val noisy = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) = pause()
    }
    private var noisyRegistered = false

    @Suppress("DEPRECATION")
    private fun requestFocus() {
        val am = app.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        if (Build.VERSION.SDK_INT >= 26) {
            val req = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                .setAudioAttributes(attributes)
                .setOnAudioFocusChangeListener(focusListener).build()
            focusRequest = req
            am.requestAudioFocus(req)
        } else {
            am.requestAudioFocus(focusListener, AudioManager.STREAM_MUSIC, AudioManager.AUDIOFOCUS_GAIN)
        }
        if (!noisyRegistered) {
            app.registerReceiver(noisy, IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY))
            noisyRegistered = true
        }
    }

    @Suppress("DEPRECATION")
    private fun abandonFocus() {
        if (!::app.isInitialized) return
        val am = app.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        if (Build.VERSION.SDK_INT >= 26) focusRequest?.let { am.abandonAudioFocusRequest(it) }
        else am.abandonAudioFocus(focusListener)
        focusRequest = null
        if (noisyRegistered) {
            try { app.unregisterReceiver(noisy) } catch (e: Exception) {}
            noisyRegistered = false
        }
    }
}
