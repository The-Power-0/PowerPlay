package com.edde746.plezy.exoplayer

import kotlin.math.PI
import kotlin.math.cos

/**
 * Experimental Dolby Surround / original Pro Logic I-compatible Lt/Rt matrix.
 *
 * Input follows the Android/MediaCodec PCM channel order used by DownmixMatrices.
 * LFE is intentionally omitted: a Pro Logic receiver has no discrete LFE channel.
 * A mono, bandwidth-limited surround is sent at opposite polarities into Lt/Rt.
 * Fronts are delayed to match the group delay of the surround Hilbert FIR.
 *
 * This is an independent matrix implementation, NOT a licensed Dolby encoder.
 * Real hardware steering, TV PCM output and phase preservation require listening
 * tests before releasing this feature.
 */
internal class ProLogicMatrixEncoder {
  companion object {
    private const val HALF = 64
    private const val TAPS = HALF * 2 + 1
    private const val HEADROOM = 0.40f
    private const val CENTER = 0.70710678f
    private const val SURROUND = 0.70710678f
  }

  private val leftDelay = FloatArray(TAPS)
  private val rightDelay = FloatArray(TAPS)
  private val centerDelay = FloatArray(TAPS)
  private val surroundDelay = FloatArray(TAPS)
  private val hilbertWeights = FloatArray(HALF + 1) { k ->
    if (k == 0 || k % 2 == 0) 0f
    else (2.0 / (PI * k) * (0.5 + 0.5 * cos(PI * k / HALF))).toFloat()
  }
  private var head = 0
  private var hpPrevInput = 0f
  private var hpPrevOutput = 0f
  private var lpOutput = 0f
  private var hpAlpha = 0f
  private var lpAlpha = 0f
  var left = 0f
    private set
  var right = 0f
    private set

  fun reset(rate: Int) {
    val sampleRate = rate.coerceAtLeast(8000)
    val dt = 1f / sampleRate
    hpAlpha = ((1.0 / (2.0 * PI * 100.0)).toFloat()).let { it / (it + dt) }
    lpAlpha = dt / ((1.0 / (2.0 * PI * 7000.0)).toFloat() + dt)
    leftDelay.fill(0f)
    rightDelay.fill(0f)
    centerDelay.fill(0f)
    surroundDelay.fill(0f)
    head = 0
    hpPrevInput = 0f
    hpPrevOutput = 0f
    lpOutput = 0f
    left = 0f
    right = 0f
  }

  /** Input array is reused by the caller; no per-sample allocations. */
  fun encodeFrame(ch: FloatArray, count: Int) {
    if (count == 1) {
      left = ch[0]
      right = ch[0]
      return
    }
    val l = ch[0]
    val r = ch[1]
    val c = if (count == 3 || count >= 5) ch[2] else 0f
    val surround = when (count) {
      4 -> (ch[2] + ch[3]) * 0.5f
      5 -> (ch[3] + ch[4]) * 0.5f
      6 -> (ch[4] + ch[5]) * 0.5f
      7 -> (ch[4] + ch[5] + ch[6]) / 3f
      8 -> (ch[4] + ch[5] + ch[6] + ch[7]) * 0.25f
      else -> 0f
    }

    // First-order HP at 100 Hz and LP at 7 kHz, matched to Pro Logic I rear.
    val hp = hpAlpha * (hpPrevOutput + surround - hpPrevInput)
    hpPrevInput = surround
    hpPrevOutput = hp
    lpOutput += lpAlpha * (hp - lpOutput)

    leftDelay[head] = l
    rightDelay[head] = r
    centerDelay[head] = c
    surroundDelay[head] = lpOutput
    val delayedIndex = (head - HALF + TAPS) % TAPS
    var q = 0f
    // Odd-symmetric 129-tap windowed Hilbert transform; 32 paired multiply-adds.
    for (k in 1 until HALF step 2) {
      val newer = (head - (HALF - k) + TAPS) % TAPS
      val older = (head - (HALF + k) + TAPS) % TAPS
      q += hilbertWeights[k] * (surroundDelay[newer] - surroundDelay[older])
    }
    val common = CENTER * centerDelay[delayedIndex]
    left = (HEADROOM * (leftDelay[delayedIndex] + common + SURROUND * q)).coerceIn(-1f, 1f)
    right = (HEADROOM * (rightDelay[delayedIndex] + common - SURROUND * q)).coerceIn(-1f, 1f)
    head = (head + 1) % TAPS
  }
}
