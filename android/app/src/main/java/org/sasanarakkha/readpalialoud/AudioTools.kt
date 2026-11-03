package org.sasanarakkha.readpalialoud

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.min
import kotlin.math.roundToInt

/** Joining audio parts (Microsoft MP3s, phone-voice WAVs) into one file, and M4A export. */
object AudioTools {
    const val RATE = 24000  // = Microsoft's voice; everything is converted to this
    private const val TIMEOUT_US = 10_000L

    class Pcm(val samples: ShortArray, val rate: Int)

    private class ShortList {
        var data = ShortArray(1 shl 16)
        var size = 0
        fun add(v: Short) {
            if (size == data.size) data = data.copyOf(data.size * 2)
            data[size++] = v
        }
        fun toArray(): ShortArray = data.copyOf(size)
    }

    /** Any audio file → mono 16-bit samples at RATE. */
    fun decodeMono(file: File): Pcm {
        val pcm = readWav16(file) ?: decodeWithCodec(file)
        return Pcm(resample(pcm.samples, pcm.rate, RATE), RATE)
    }

    /** Fast path for 16-bit PCM WAV (what Android's voices write); null for anything else. */
    private fun readWav16(file: File): Pcm? {
        val b = file.readBytes()
        if (b.size < 44 || String(b, 0, 4, Charsets.US_ASCII) != "RIFF" ||
            String(b, 8, 4, Charsets.US_ASCII) != "WAVE") return null
        val bb = ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN)
        var pos = 12
        var channels = 1
        var rate = RATE
        var bits = 16
        var format = 1
        while (pos + 8 <= b.size) {
            val id = String(b, pos, 4, Charsets.US_ASCII)
            val len = bb.getInt(pos + 4)
            val body = pos + 8
            if (id == "fmt " && body + 16 <= b.size) {
                format = bb.getShort(body).toInt()
                channels = bb.getShort(body + 2).toInt().coerceAtLeast(1)
                rate = bb.getInt(body + 4)
                bits = bb.getShort(body + 14).toInt()
            } else if (id == "data") {
                if (format != 1 || bits != 16) return null
                // Some voices leave the length at 0 or too big: then read to the end
                val dataLen = if (len <= 0 || body + len > b.size) b.size - body else len
                val frames = dataLen / (2 * channels)
                val out = ShortArray(frames)
                for (i in 0 until frames) {
                    var sum = 0
                    for (c in 0 until channels) sum += bb.getShort(body + (i * channels + c) * 2)
                    out[i] = (sum / channels).toShort()
                }
                return Pcm(out, rate)
            }
            if (len < 0 || body + len > b.size) return null
            pos = body + len + (len and 1)
        }
        return null
    }

    private fun decodeWithCodec(file: File): Pcm {
        val ex = MediaExtractor()
        ex.setDataSource(file.path)
        val track = (0 until ex.trackCount).firstOrNull {
            ex.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("audio/") == true
        } ?: throw IOException("No audio in ${file.name}")
        ex.selectTrack(track)
        val fmt = ex.getTrackFormat(track)
        var rate = fmt.getInteger(MediaFormat.KEY_SAMPLE_RATE)
        var channels = fmt.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
        val codec = MediaCodec.createDecoderByType(fmt.getString(MediaFormat.KEY_MIME)!!)
        val out = ShortList()
        try {
            codec.configure(fmt, null, null, 0)
            codec.start()
            val info = MediaCodec.BufferInfo()
            var inputDone = false
            var outputDone = false
            while (!outputDone) {
                if (!inputDone) {
                    val i = codec.dequeueInputBuffer(TIMEOUT_US)
                    if (i >= 0) {
                        val buf = codec.getInputBuffer(i)!!
                        val n = ex.readSampleData(buf, 0)
                        if (n < 0) {
                            codec.queueInputBuffer(i, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputDone = true
                        } else {
                            codec.queueInputBuffer(i, 0, n, ex.sampleTime, 0)
                            ex.advance()
                        }
                    }
                }
                val o = codec.dequeueOutputBuffer(info, TIMEOUT_US)
                if (o == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    rate = codec.outputFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                    channels = codec.outputFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                } else if (o >= 0) {
                    val buf = codec.getOutputBuffer(o)!!
                    buf.position(info.offset)
                    buf.limit(info.offset + info.size)
                    val sb = buf.order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
                    val frames = sb.remaining() / channels
                    for (f in 0 until frames) {
                        var sum = 0
                        for (c in 0 until channels) sum += sb.get(f * channels + c)
                        out.add((sum / channels).toShort())
                    }
                    codec.releaseOutputBuffer(o, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) outputDone = true
                }
            }
            codec.stop()
        } finally {
            codec.release()
            ex.release()
        }
        return Pcm(out.toArray(), rate)
    }

    private fun resample(s: ShortArray, from: Int, to: Int): ShortArray {
        if (from == to || s.isEmpty() || from <= 0) return s
        val n = (s.size.toLong() * to / from).toInt()
        val out = ShortArray(n)
        val last = s.size - 1
        for (i in 0 until n) {
            val x = i.toDouble() * from / to
            val j = x.toInt()
            val a = s[min(j, last)].toInt()
            val b = s[min(j + 1, last)].toInt()
            out[i] = (a + (b - a) * (x - j)).roundToInt().toShort()
        }
        return out
    }

    fun writeWav(file: File, samples: ShortArray, rate: Int = RATE) {
        val bb = ByteBuffer.allocate(44 + samples.size * 2).order(ByteOrder.LITTLE_ENDIAN)
        bb.put("RIFF".toByteArray()).putInt(36 + samples.size * 2).put("WAVE".toByteArray())
        bb.put("fmt ".toByteArray()).putInt(16).putShort(1).putShort(1)
            .putInt(rate).putInt(rate * 2).putShort(2).putShort(16)
        bb.put("data".toByteArray()).putInt(samples.size * 2)
        for (v in samples) bb.putShort(v)
        file.writeBytes(bb.array())
    }

    /** Parts in order, with 0.4 s of silence between them (as on the desktop). */
    fun join(parts: List<File>, out: File, gapSeconds: Double = 0.4) {
        val gap = (RATE * gapSeconds).toInt()
        val pcm = parts.map { decodeMono(it).samples }
        val total = pcm.sumOf { it.size } + gap * (pcm.size - 1).coerceAtLeast(0)
        val all = ShortArray(total)
        var pos = 0
        pcm.forEachIndexed { i, s ->
            if (i > 0) pos += gap
            s.copyInto(all, pos)
            pos += s.size
        }
        writeWav(out, all)
    }

    /** Audio file → AAC in an .m4a file (Android has no MP3 encoder). */
    fun toM4a(src: File, out: File) {
        val samples = decodeMono(src).samples
        val fmt = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, RATE, 1)
        fmt.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
        fmt.setInteger(MediaFormat.KEY_BIT_RATE, 64_000)
        fmt.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16_384)
        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        val muxer = MediaMuxer(out.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var track = -1
        try {
            codec.configure(fmt, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            codec.start()
            val info = MediaCodec.BufferInfo()
            var pos = 0
            var inputDone = false
            var outputDone = false
            while (!outputDone) {
                if (!inputDone) {
                    val i = codec.dequeueInputBuffer(TIMEOUT_US)
                    if (i >= 0) {
                        val buf = codec.getInputBuffer(i)!!
                        buf.clear()
                        val n = min(buf.capacity() / 2, samples.size - pos)
                        val pts = pos * 1_000_000L / RATE
                        if (n <= 0) {
                            codec.queueInputBuffer(i, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputDone = true
                        } else {
                            buf.order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().put(samples, pos, n)
                            codec.queueInputBuffer(i, 0, n * 2, pts, 0)
                            pos += n
                        }
                    }
                }
                val o = codec.dequeueOutputBuffer(info, TIMEOUT_US)
                if (o == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    track = muxer.addTrack(codec.outputFormat)
                    muxer.start()
                } else if (o >= 0) {
                    val buf = codec.getOutputBuffer(o)!!
                    val config = info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0
                    if (!config && info.size > 0 && track >= 0) {
                        buf.position(info.offset)
                        buf.limit(info.offset + info.size)
                        muxer.writeSampleData(track, buf, info)
                    }
                    codec.releaseOutputBuffer(o, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) outputDone = true
                }
            }
            codec.stop()
            if (track >= 0) muxer.stop()
        } finally {
            codec.release()
            muxer.release()
        }
    }
}
