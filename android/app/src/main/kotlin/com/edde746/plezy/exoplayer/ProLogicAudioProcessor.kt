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
 * Multichannel 3..8 becomes stereo. Any other format is left to stock Media3.
 */
@OptIn(UnstableApi::class)
internal class ProLogicAudioProcessor : BaseAudioProcessor() {
  @Volatile var enabled: Boolean = false

  private val matrix = ProLogicMatrixEncoder()
  private val frame = FloatArray(8)
  private var pendingChannels = 0
  private var pendingEncoding = 0
  private var channels = 0
  private var encoding = 0

  override fun onConfigure(format: AudioProcessor.AudioFormat): AudioProcessor.AudioFormat {
    pendingChannels = format.channelCount
    pendingEncoding = format.encoding
    return if (enabled &&
      (format.channelCount == 1 || format.channelCount in 3..8) &&
      (format.encoding == AudioFormat.ENCODING_PCM_16BIT ||
        format.encoding == AudioFormat.ENCODING_PCM_FLOAT)
    ) {
      AudioProcessor.AudioFormat(format.sampleRate, 2, format.encoding)
    } else {
      AudioProcessor.AudioFormat.NOT_SET
    }
  }

  override fun onFlush(streamMetadata: AudioProcessor.StreamMetadata) {
    channels = pendingChannels
    encoding = pendingEncoding
    matrix.reset(inputAudioFormat.sampleRate)
  }

  override fun onReset() {
    pendingChannels = 0
    pendingEncoding = 0
    channels = 0
    encoding = 0
    matrix.reset(48000)
  }

  override fun queueInput(inputBuffer: ByteBuffer) {
    if (channels !in 1..8 || channels == 2) return
    val bytes = if (encoding == AudioFormat.ENCODING_PCM_FLOAT) 4 else 2
    val inputFrameBytes = channels * bytes
    val frames = inputBuffer.remaining() / inputFrameBytes
    val output = replaceOutputBuffer(frames * 2 * bytes)
    repeat(frames) {
      for (i in 0 until channels) {
        frame[i] = if (bytes == 4) inputBuffer.float else inputBuffer.short / 32768f
      }
      matrix.encodeFrame(frame, channels)
      if (bytes == 4) {
        output.putFloat(matrix.left)
        output.putFloat(matrix.right)
      } else {
        output.putShort((matrix.left * 32767f).toInt().toShort())
        output.putShort((matrix.right * 32767f).toInt().toShort())
      }
    }
    output.flip()
  }
}
