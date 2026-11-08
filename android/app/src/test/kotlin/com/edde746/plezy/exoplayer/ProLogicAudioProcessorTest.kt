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
    for (count in 1..8) {
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
    for (encoding in intArrayOf(AudioFormat.ENCODING_PCM_16BIT, AudioFormat.ENCODING_PCM_FLOAT)) {
      for (count in intArrayOf(1, 3, 4, 5, 6, 7, 8)) {
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

}
