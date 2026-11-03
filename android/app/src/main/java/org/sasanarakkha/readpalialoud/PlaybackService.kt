package org.sasanarakkha.readpalialoud

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.media.app.NotificationCompat.MediaStyle

/** Keeps the app alive while reading and shows the player in the notification shade and on
 *  the lock screen (Pause / Play / Stop; also headphone buttons). */
class PlaybackService : Service() {
    private lateinit var session: MediaSessionCompat

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        if (Build.VERSION.SDK_INT >= 26) {
            val ch = NotificationChannel(CHANNEL, "Playing", NotificationManager.IMPORTANCE_LOW)
            ch.setShowBadge(false)
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
        session = MediaSessionCompat(this, "ReadPaliAloud").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay() = Playback.resume()
                override fun onPause() = Playback.pause()
                override fun onStop() = Playback.stop()
            })
            isActive = true
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PLAY -> Playback.resume()
            ACTION_PAUSE -> Playback.pause()
            ACTION_STOP -> Playback.stop()
        }
        update()
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        instance = null
        session.release()
        super.onDestroy()
    }

    private fun action(name: String): PendingIntent = PendingIntent.getService(this, name.hashCode(),
        Intent(this, PlaybackService::class.java).setAction(name), PendingIntent.FLAG_IMMUTABLE)

    fun update() {
        if (!Playback.active) {
            ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
            stopSelf()
            return
        }
        val paused = Playback.paused
        session.setMetadata(MediaMetadataCompat.Builder()
            .putString(MediaMetadataCompat.METADATA_KEY_TITLE, Playback.title)
            .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, getString(R.string.app_name))
            .putLong(MediaMetadataCompat.METADATA_KEY_DURATION, Playback.duration.toLong())
            .build())
        session.setPlaybackState(PlaybackStateCompat.Builder()
            .setActions(PlaybackStateCompat.ACTION_PLAY or PlaybackStateCompat.ACTION_PAUSE or
                PlaybackStateCompat.ACTION_PLAY_PAUSE or PlaybackStateCompat.ACTION_STOP)
            .setState(if (paused) PlaybackStateCompat.STATE_PAUSED else PlaybackStateCompat.STATE_PLAYING,
                Playback.position.toLong(), if (paused) 0f else 1f)
            .build())
        val open = PendingIntent.getActivity(this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE)
        val n = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_wheel)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(Playback.title)
            .setContentIntent(open)
            .setDeleteIntent(action(ACTION_STOP))
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .addAction(if (paused) android.R.drawable.ic_media_play else android.R.drawable.ic_media_pause,
                if (paused) "Play" else "Pause", action(if (paused) ACTION_PLAY else ACTION_PAUSE))
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", action(ACTION_STOP))
            .setStyle(MediaStyle().setMediaSession(session.sessionToken).setShowActionsInCompactView(0, 1))
            .build()
        try {
            ServiceCompat.startForeground(this, NOTIFICATION_ID, n,
                if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK else 0)
        } catch (e: Exception) {  // e.g. not allowed from the background: still show the controls
            Log.w("PaliTTS", "startForeground", e)
            getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, n)
        }
    }

    companion object {
        private const val CHANNEL = "playback"
        private const val NOTIFICATION_ID = 1
        const val ACTION_PLAY = "org.sasanarakkha.readpalialoud.PLAY"
        const val ACTION_PAUSE = "org.sasanarakkha.readpalialoud.PAUSE"
        const val ACTION_STOP = "org.sasanarakkha.readpalialoud.STOP"
        private var instance: PlaybackService? = null

        /** Called by Playback after every change. */
        fun refresh(context: Context) {
            val s = instance
            if (s != null) {
                s.update()
            } else if (Playback.active) {
                try {
                    ContextCompat.startForegroundService(context, Intent(context, PlaybackService::class.java))
                } catch (e: Exception) {
                    Log.w("PaliTTS", "could not start the player notification", e)
                }
            }
        }
    }
}
