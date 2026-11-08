package com.edde746.plezy.exoplayer

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import java.util.concurrent.atomic.AtomicLong
import kotlin.math.PI
import kotlin.math.sin

/**
 * Device-route check. Emits stereo PCM through Android's normal media output,
 * using the same 5.1-to-Lt/Rt matrix as real playback. Does not use a movie,
 * and never requires the persistent preference to be enabled.
 *
 * Intended for the Fire TV -> HDMI -> TCL optical PCM -> stereo DAC -> receiver path.
 */
internal class ProLogicSpeakerTest {
  private val generation = AtomicLong(0)
  @Volatile private var worker: Thread? = null
  @Volatile private var track: AudioTrack? = null

  fun play(speaker: String): Boolean {
    if (speaker !in setOf("left", "center", "right", "surround")) return false
    stop()
    val token = generation.incrementAndGet()
    val isCurrent = { generation.get() == token }
    val thread = Thread({
      var audio: AudioTrack? = null
      try {
        val rate = 48000
        val minBuffer = AudioTrack.getMinBufferSize(
          rate, AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_16BIT
        )
        if (minBuffer <= 0) return@Thread
        audio = AudioTrack(
          AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_MOVIE).build(),
          AudioFormat.Builder().setSampleRate(rate)
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build(),
          maxOf(minBuffer, rate / 4), AudioTrack.MODE_STREAM, AudioManager.AUDIO_SESSION_ID_GENERATE
        )
        if (!isCurrent()) return@Thread
        track = audio
        if (audio.state != AudioTrack.STATE_INITIALIZED || !isCurrent()) return@Thread
        audio.play()
        val matrix = ProLogicMatrixEncoder().apply { reset(rate) }
        val channels = FloatArray(6)
        val framesPerChunk = 1024
        val pcm = ShortArray(framesPerChunk * 2)
        val hz = when (speaker) {
          "left" -> 440.0
          "center" -> 554.37
          "right" -> 659.25
          else -> 392.0
        }
        // 1.6 seconds with 80ms linear fades, low output to avoid surprises.
        val totalFrames = rate * 8 / 5
        var offset = 0
        while (isCurrent() && offset < totalFrames) {
          val n = minOf(framesPerChunk, totalFrames - offset)
          for (i in 0 until n) {
            val t = offset + i
            val fade = minOf(1.0, t / (rate * 0.08), (totalFrames - t) / (rate * 0.08))
            val signal = (0.55 * fade * sin(2.0 * PI * hz * t / rate)).toFloat()
            channels.fill(0f)
            when (speaker) {
              "left" -> channels[0] = signal
              "center" -> channels[2] = signal
              "right" -> channels[1] = signal
              "surround" -> { channels[4] = signal; channels[5] = signal }
            }
            matrix.encodeFrame(channels, 6)
            pcm[i * 2] = (matrix.left * 32767f).toInt().toShort()
            pcm[i * 2 + 1] = (matrix.right * 32767f).toInt().toShort()
          }
          var written = 0
          while (isCurrent() && written < n * 2) {
            val count = audio.write(pcm, written, n * 2 - written, AudioTrack.WRITE_BLOCKING)
            if (count <= 0) break
            written += count
          }
          if (written < n * 2) break
          offset += n
        }
        if (isCurrent()) audio.stop()
      } catch (_: Exception) {
        // The UI remains usable on devices with an unavailable PCM route.
      } finally {
        audio?.release()
        if (track === audio) track = null
        // A finished older test must not stop a newer test.
      }
    }, "PowerPlay-ProLogic-SpeakerTest").apply { isDaemon = true }
    worker = thread
    thread.start()
    return true
  }

  fun stop() {
    generation.incrementAndGet()
    try { track?.pause() } catch (_: Exception) {}
    try { track?.flush() } catch (_: Exception) {}
    // Worker owns AudioTrack.release(); never block the Flutter/UI thread.
  }
}
