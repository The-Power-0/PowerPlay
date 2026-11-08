package com.edde746.plezy.exoplayer

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ProLogicMatrixEncoderTest {
  @Test fun monoBecomesIdenticalStereo() {
    val encoder = ProLogicMatrixEncoder().apply { reset(48000) }
    encoder.encodeFrame(floatArrayOf(0.35f), 1)
    assertEquals(0.35f, encoder.left, 0f)
    assertEquals(0.35f, encoder.right, 0f)
  }

  @Test fun frontLeftAndRightAreIsolated() {
    val encoder = ProLogicMatrixEncoder().apply { reset(48000) }
    val ch = FloatArray(6)
    ch[0] = 0.5f
    repeat(200) { encoder.encodeFrame(ch, 6) }
    assertTrue(encoder.left > 0.19f)
    assertEquals(0f, encoder.right, 1e-5f)
    encoder.reset(48000)
    ch.fill(0f); ch[1] = 0.5f
    repeat(200) { encoder.encodeFrame(ch, 6) }
    assertEquals(0f, encoder.left, 1e-5f)
    assertTrue(encoder.right > 0.19f)
  }

  @Test fun centerIsEqualAndInPhase() {
    val encoder = ProLogicMatrixEncoder().apply { reset(48000) }
    val ch = FloatArray(6)
    ch[2] = 0.5f
    repeat(200) { encoder.encodeFrame(ch, 6) }
    assertTrue(encoder.left > 0f)
    assertEquals(encoder.left, encoder.right, 1e-5f)
  }

  @Test fun rearIsOppositePolarityAndNotSilent() {
    val encoder = ProLogicMatrixEncoder().apply { reset(48000) }
    val ch = FloatArray(6)
    var energy = 0f
    repeat(1600) { t ->
      val v = sin(2.0 * PI * 1000.0 * t / 48000.0).toFloat()
      ch[4] = v; ch[5] = v
      encoder.encodeFrame(ch, 6)
      if (t > 500) {
        energy += abs(encoder.left)
        assertEquals("t=$t", -encoder.left, encoder.right, 1e-5f)
      }
    }
    assertTrue("Rear signal should not vanish", energy > 15f)
  }

  @Test fun lfeIsNotIncorrectlySentToCenterOrSurround() {
    val encoder = ProLogicMatrixEncoder().apply { reset(48000) }
    val ch = FloatArray(6); ch[3] = 1f
    repeat(200) { encoder.encodeFrame(ch, 6) }
    assertEquals(0f, encoder.left, 0f)
    assertEquals(0f, encoder.right, 0f)
  }

  @Test fun sevenPointOneSideChannelsContributeToMonoRear() {
    val encoder = ProLogicMatrixEncoder().apply { reset(48000) }
    val ch = FloatArray(8)
    var energy = 0f
    repeat(1600) { t ->
      ch[6] = sin(2.0 * PI * 600.0 * t / 48000.0).toFloat()
      encoder.encodeFrame(ch, 8)
      if (t > 500) energy += abs(encoder.left)
    }
    assertTrue(energy > 3f)
  }

  @Test fun resetRemovesPreviouslyBufferedSignal() {
    val encoder = ProLogicMatrixEncoder().apply { reset(48000) }
    val ch = FloatArray(6); ch[4] = 1f; ch[5] = 1f
    repeat(400) { encoder.encodeFrame(ch, 6) }
    encoder.reset(48000)
    ch.fill(0f)
    encoder.encodeFrame(ch, 6)
    assertEquals(0f, encoder.left, 0f)
    assertEquals(0f, encoder.right, 0f)
  }
}
