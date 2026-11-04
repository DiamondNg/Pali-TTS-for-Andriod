package io.github.diamondng.readpalialoud

import java.io.File
import java.io.IOException

/** Audio file → MP3 (64 kbps mono, as on the desktop), with LAME built into the app
 *  (Android itself can decode MP3 but not write it). */
object Mp3 {
    init { System.loadLibrary("mp3") }

    @JvmStatic private external fun open(rate: Int, kbps: Int): Long
    @JvmStatic private external fun encode(handle: Long, pcm: ShortArray, n: Int, out: ByteArray): Int
    @JvmStatic private external fun flush(handle: Long, out: ByteArray): Int
    @JvmStatic private external fun close(handle: Long)

    fun encodeFile(src: File, out: File, kbps: Int = 64) {
        val samples = AudioTools.decodeMono(src).samples
        val h = open(AudioTools.RATE, kbps)
        if (h == 0L) throw IOException("MP3 encoder failed to start")
        val chunk = 8192
        val buf = ByteArray(chunk * 5 / 4 + 7200)  // LAME's worst case for this many samples
        val part = ShortArray(chunk)
        try {
            out.outputStream().buffered().use { os ->
                var pos = 0
                while (pos < samples.size) {
                    val n = minOf(chunk, samples.size - pos)
                    samples.copyInto(part, 0, pos, pos + n)
                    val m = encode(h, part, n, buf)
                    if (m < 0) throw IOException("MP3 encoding failed ($m)")
                    os.write(buf, 0, m)
                    pos += n
                }
                val m = flush(h, buf)
                if (m > 0) os.write(buf, 0, m)
            }
        } finally {
            close(h)
        }
    }
}
