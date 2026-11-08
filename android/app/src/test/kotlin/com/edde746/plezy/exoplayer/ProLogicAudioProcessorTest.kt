package com.edde746.plezy.exoplayer

import android.media.AudioFormat
import androidx.media3.common.audio.AudioProcessor
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
}
