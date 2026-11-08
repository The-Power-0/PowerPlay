package com.edde746.plezy.exoplayer

import android.media.AudioFormat
import androidx.media3.common.audio.AudioProcessor
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProLogicAudioProcessorTest {
  @Test fun disabledByDefaultForEveryChannelCount() {
    val processor = ProLogicAudioProcessor()
    for (count in 1..12) {
      val result = processor.configure(
        AudioProcessor.AudioFormat(48000, count, AudioFormat.ENCODING_PCM_16BIT)
      )
      assertEquals(AudioProcessor.AudioFormat.NOT_SET, result)
      assertFalse(processor.isActive)
    }
  }

  @Test fun stereoIsAlwaysPreservedIncludingExistingLtRt() {
    val processor = ProLogicAudioProcessor().apply { enabled = true }
    val result = processor.configure(
      AudioProcessor.AudioFormat(48000, 2, AudioFormat.ENCODING_PCM_16BIT)
    )
    assertEquals(AudioProcessor.AudioFormat.NOT_SET, result)
    assertFalse(processor.isActive)
  }

  @Test fun supportedMultichannelPcmIsConvertedToTwoChannels() {
    for (encoding in intArrayOf(
      AudioFormat.ENCODING_PCM_8BIT, AudioFormat.ENCODING_PCM_16BIT,
      AudioFormat.ENCODING_PCM_24BIT_PACKED, AudioFormat.ENCODING_PCM_32BIT,
      AudioFormat.ENCODING_PCM_FLOAT
    )) {
      for (count in intArrayOf(1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)) {
        val processor = ProLogicAudioProcessor().apply { enabled = true }
        val result = processor.configure(AudioProcessor.AudioFormat(48000, count, encoding))
        assertTrue("encoding=$encoding count=$count", processor.isActive)
        assertEquals(2, result.channelCount)
        assertEquals(encoding, result.encoding)
        assertEquals(48000, result.sampleRate)
      }
    }
  }

  @Test fun pcmTelemetryCountsRealOutputAndResetsOnReconfigure() {
    val processor = ProLogicAudioProcessor().apply { enabled = true }
    val format = AudioProcessor.AudioFormat(48000, 6, AudioFormat.ENCODING_PCM_16BIT)
    processor.configure(format)
    processor.flush()
    assertEquals(0L, processor.processedFrames)
    assertEquals(6, processor.configuredInputChannels)
    assertEquals(48000, processor.configuredSampleRate)

    val frames = 256
    val pcm = ByteBuffer.allocateDirect(frames * 6 * 2).order(ByteOrder.nativeOrder())
    repeat(frames) {
      pcm.putShort(16000)
      repeat(5) { pcm.putShort(0) }
    }
    pcm.flip()
    processor.queueInput(pcm)
    val output = processor.getOutput()
    assertEquals(frames * 2 * 2, output.remaining())
    assertEquals(frames.toLong(), processor.processedFrames)
    assertEquals(1L, processor.processedBuffers)
    assertTrue(processor.processingTimeNs > 0L)
    assertTrue(processor.peakBufferTimeNs > 0L)
    assertTrue(processor.audioTimeBudgetPercent() != null)

    processor.flush()
    assertEquals(0L, processor.processedFrames)
    assertEquals(0L, processor.processedBuffers)
    assertEquals(null, processor.audioTimeBudgetPercent())
  }


  @Test fun twelveChannelFloatSamplesAreActuallyMatrixEncoded() {
    val processor = ProLogicAudioProcessor().apply { enabled = true }
    processor.configure(AudioProcessor.AudioFormat(48000, 12, AudioFormat.ENCODING_PCM_FLOAT))
    processor.flush()
    val frames = 256
    val pcm = ByteBuffer.allocateDirect(frames * 12 * 4).order(ByteOrder.nativeOrder())
    repeat(frames) {
      repeat(12) { channel -> pcm.putFloat(if (channel == 8) 0.5f else 0f) }
    }
    pcm.flip()
    processor.queueInput(pcm)
    val out = processor.getOutput().order(ByteOrder.nativeOrder())
    assertEquals(frames * 2 * 4, out.remaining())
    assertEquals(frames.toLong(), processor.processedFrames)
    var energy = 0f
    while (out.hasRemaining()) energy += kotlin.math.abs(out.getFloat())
    assertTrue("Extended front-height audio must be audible", energy > 1f)
  }

  @Test fun packedPcm24IsConvertedToStereoWithCorrectBufferShape() {
    val processor = ProLogicAudioProcessor().apply { enabled = true }
    processor.configure(AudioProcessor.AudioFormat(48000, 6, AudioFormat.ENCODING_PCM_24BIT_PACKED))
    processor.flush()
    val frames = 192
    val pcm = ByteBuffer.allocateDirect(frames * 6 * 3).order(ByteOrder.nativeOrder())
    repeat(frames) {
      // +0.5 on front left, remaining channels silent.
      pcm.put(0); pcm.put(0); pcm.put(0x40)
      repeat(5) { pcm.put(0); pcm.put(0); pcm.put(0) }
    }
    pcm.flip()
    processor.queueInput(pcm)
    val out = processor.getOutput()
    assertEquals(frames * 2 * 3, out.remaining())
    var nonzero = false
    while (out.hasRemaining()) if (out.get().toInt() != 0) nonzero = true
    assertTrue("Front-left 24-bit PCM should produce nonzero Lt", nonzero)
  }

}
