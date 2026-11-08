package com.edde746.plezy.exoplayer

import androidx.media3.common.MimeTypes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ProLogicDecoderChannelPolicyTest {
  @Test fun originalAudioDecoderPolicyUnchangedWhenFeatureIsOff() {
    assertNull(ProLogicDecoderChannelPolicy.requestedOutputChannels(false, MimeTypes.AUDIO_AC3, 6))
    assertNull(ProLogicDecoderChannelPolicy.requestedOutputChannels(false, MimeTypes.AUDIO_E_AC3, 8))
  }

  @Test fun onlyEnabledMultichannelDolbyIsRequestedFromHardwareDecoder() {
    assertEquals(6, ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_AC3, 6))
    assertEquals(6, ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_E_AC3, 6))
    assertEquals(8, ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_E_AC3_JOC, 8))
    assertNull(ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_AC3, 2))
    assertNull(ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_AC3, 1))
    assertNull(ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_AC3, 9))
    assertNull(ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_RAW, 6))
    assertNull(ProLogicDecoderChannelPolicy.requestedOutputChannels(true, MimeTypes.AUDIO_IAMF, 6))
  }

  @Test fun fallbackIsOnlyForActualStereoPcmFromMultichannelSource() {
    val policy = ProLogicDecoderChannelPolicy
    assertTrue(policy.needsSoftwareFallback(true, MimeTypes.AUDIO_AC3, 6, 2, true, false))
    assertTrue(policy.needsSoftwareFallback(true, MimeTypes.AUDIO_E_AC3, 6, 2, true, false))
    assertFalse(policy.needsSoftwareFallback(false, MimeTypes.AUDIO_AC3, 6, 2, true, false))
    assertFalse(policy.needsSoftwareFallback(true, MimeTypes.AUDIO_AC3, 2, 2, true, false))
    assertFalse(policy.needsSoftwareFallback(true, MimeTypes.AUDIO_AC3, 6, 6, true, false))
    assertFalse(policy.needsSoftwareFallback(true, MimeTypes.AUDIO_AC3, 6, 2, false, false))
    assertFalse(policy.needsSoftwareFallback(true, MimeTypes.AUDIO_AC3, 6, 2, true, true))
    assertFalse(policy.needsSoftwareFallback(true, MimeTypes.AUDIO_DTS, 6, 2, true, false))
  }
}
