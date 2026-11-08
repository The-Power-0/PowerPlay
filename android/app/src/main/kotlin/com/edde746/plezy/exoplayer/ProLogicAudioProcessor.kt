package com.edde746.plezy.exoplayer

import android.media.AudioFormat
import androidx.media3.common.audio.AudioProcessor
import androidx.media3.common.audio.BaseAudioProcessor
import androidx.media3.common.util.UnstableApi
import androidx.annotation.OptIn
import java.nio.ByteBuffer

/**
 * Optional PCM-only Lt/Rt matrix encoder inserted BEFORE ChannelMixingAudioProcessor.
 * Mono becomes dual mono; existing stereo (including prematrixed Lt/Rt) is untouched.
 * Multichannel 3..12 becomes stereo; extra 7.1.4-style channels are folded down.\n * Unsupported layouts are left to stock Media3 and reported as inactive by telemetry.
 */
@OptIn(UnstableApi::class)
internal class ProLogicAudioProcessor : BaseAudioProcessor() {
  @Volatile var enabled: Boolean = false

  private val matrix = ProLogicMatrixEncoder()
  private val frame = FloatArray(DownmixMatrices.MAX_MIXING_CHANNELS)
  private var pendingChannels = 0
  private var pendingEncoding = 0
  private var channels = 0
  private var encoding = 0

  // A single playback-thread writer, read from the existing 500 ms overlay stats
  // call. No logging, allocations or additional polling on the PCM hot path.
  @Volatile var configuredInputChannels: Int = 0
    private set
  @Volatile var configuredSampleRate: Int = 0
    private set
  @Volatile var configuredPcmEncoding: Int = 0
    private set
  @Volatile var processedFrames: Long = 0
    private set
  @Volatile var processedBuffers: Long = 0
    private set
  @Volatile var processingTimeNs: Long = 0
    private set
  @Volatile var peakBufferTimeNs: Long = 0
    private set
  @Volatile var lastBufferTimeNs: Long = 0
    private set

  /** Percent of one real-time audio stream budget, not total device CPU usage. */
  fun audioTimeBudgetPercent(): Double? {
    val frames = processedFrames
    val rate = configuredSampleRate
    if (frames <= 0 || rate <= 0) return null
    return processingTimeNs.toDouble() * rate * 100.0 / (frames * 1_000_000_000.0)
  }

  override fun onConfigure(format: AudioProcessor.AudioFormat): AudioProcessor.AudioFormat {
    pendingChannels = format.channelCount
    pendingEncoding = format.encoding
    return if (enabled &&
      (format.channelCount == 1 || format.channelCount in 3..DownmixMatrices.MAX_MIXING_CHANNELS) &&
      isSupportedPcmEncoding(format.encoding)
    ) {
      AudioProcessor.AudioFormat(format.sampleRate, 2, format.encoding)
    } else {
      AudioProcessor.AudioFormat.NOT_SET
    }
  }

  override fun onFlush(streamMetadata: AudioProcessor.StreamMetadata) {
    channels = pendingChannels
    encoding = pendingEncoding
    configuredInputChannels = channels
    configuredSampleRate = inputAudioFormat.sampleRate
    configuredPcmEncoding = encoding
    processedFrames = 0
    processedBuffers = 0
    processingTimeNs = 0
    peakBufferTimeNs = 0
    lastBufferTimeNs = 0
    matrix.reset(inputAudioFormat.sampleRate)
  }

  override fun onReset() {
    pendingChannels = 0
    pendingEncoding = 0
    channels = 0
    encoding = 0
    configuredInputChannels = 0
    configuredSampleRate = 0
    configuredPcmEncoding = 0
    processedFrames = 0
    processedBuffers = 0
    processingTimeNs = 0
    peakBufferTimeNs = 0
    lastBufferTimeNs = 0
    matrix.reset(48000)
  }

  override fun queueInput(inputBuffer: ByteBuffer) {
    if (channels !in 1..DownmixMatrices.MAX_MIXING_CHANNELS || channels == 2) return
    val bytes = pcmBytes(encoding)
    if (bytes == 0) return
    val inputFrameBytes = channels * bytes
    val frames = inputBuffer.remaining() / inputFrameBytes
    if (frames == 0) return
    val startNs = System.nanoTime()
    val output = replaceOutputBuffer(frames * 2 * bytes)
    repeat(frames) {
      for (i in 0 until channels) frame[i] = readPcm(inputBuffer, encoding)
      matrix.encodeFrame(frame, channels)
      writePcm(output, encoding, matrix.left)
      writePcm(output, encoding, matrix.right)
    }
    output.flip()
    val elapsedNs = (System.nanoTime() - startNs).coerceAtLeast(0)
    processedFrames += frames
    processedBuffers++
    processingTimeNs += elapsedNs
    lastBufferTimeNs = elapsedNs
    if (elapsedNs > peakBufferTimeNs) peakBufferTimeNs = elapsedNs
  }

  private fun isSupportedPcmEncoding(pcm: Int): Boolean = pcmBytes(pcm) != 0

  private fun pcmBytes(pcm: Int): Int = when (pcm) {
    AudioFormat.ENCODING_PCM_8BIT -> 1
    AudioFormat.ENCODING_PCM_16BIT -> 2
    AudioFormat.ENCODING_PCM_24BIT_PACKED -> 3
    AudioFormat.ENCODING_PCM_32BIT, AudioFormat.ENCODING_PCM_FLOAT -> 4
    else -> 0
  }

  /** PCM is little-endian on supported Fire OS/Android devices; no per-frame allocations. */
  private fun readPcm(buffer: ByteBuffer, pcm: Int): Float = when (pcm) {
    AudioFormat.ENCODING_PCM_8BIT -> ((buffer.get().toInt() and 0xff) - 128) / 128f
    AudioFormat.ENCODING_PCM_16BIT -> buffer.getShort() / 32768f
    AudioFormat.ENCODING_PCM_24BIT_PACKED -> {
      val sample = (buffer.get().toInt() and 0xff) or
        ((buffer.get().toInt() and 0xff) shl 8) or (buffer.get().toInt() shl 16)
      (sample shl 8 shr 8) / 8388608f
    }
    AudioFormat.ENCODING_PCM_32BIT -> (buffer.getInt() / 2147483648.0).toFloat()
    else -> buffer.getFloat()
  }

  private fun writePcm(buffer: ByteBuffer, pcm: Int, value: Float) {
    val sample = value.coerceIn(-1f, 1f)
    when (pcm) {
      AudioFormat.ENCODING_PCM_8BIT -> buffer.put((sample * 127f + 128f).toInt().coerceIn(0, 255).toByte())
      AudioFormat.ENCODING_PCM_16BIT -> buffer.putShort((sample * 32767f).toInt().toShort())
      AudioFormat.ENCODING_PCM_24BIT_PACKED -> {
        val v = (sample * 8388607f).toInt()
        buffer.put(v.toByte()); buffer.put((v ushr 8).toByte()); buffer.put((v ushr 16).toByte())
      }
      AudioFormat.ENCODING_PCM_32BIT -> buffer.putInt((sample.toDouble() * 2147483647.0).toInt())
      else -> buffer.putFloat(sample)
    }
  }
}
