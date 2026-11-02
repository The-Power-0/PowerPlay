package com.edde746.plezy.exoplayer

import android.os.Looper
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Shadows
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** Tests for the Fire TV-specific Media3-only channel; no native MPV is linked. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class ExoPlayerOnlyPluginTest {

  @Test
  fun unsupportedMediaCannotSwitchToAnyOtherPlaybackEngine() {
    val plugin = ExoPlayerPlugin()
    val didHandover = plugin.onFormatUnsupported(
      mediaGeneration = 3,
      uri = "https://example.invalid/media",
      headers = null,
      positionMs = 1000L,
      playWhenReady = true,
      errorMessage = "Unsupported video format"
    )
    assertFalse(didHandover)
  }

  @Test
  fun backendIsAlwaysExoPlayer() {
    val plugin = ExoPlayerPlugin()
    val result = RecordingResult()
    plugin.onMethodCall(MethodCall("getPlayerType", null), result)
    assertEquals("exoplayer", result.value)
    assertNull(result.errorCode)
  }

  @Test
  fun debugFallbackRequestIsRejectedExplicitly() {
    val plugin = ExoPlayerPlugin()
    val result = RecordingResult()
    plugin.onMethodCall(MethodCall("triggerFallback", null), result)
    assertEquals("UNSUPPORTED", result.errorCode)
  }

  @Test
  fun uninitializedCommandsAndInvalidOpensReturnErrors() {
    val plugin = ExoPlayerPlugin()
    val play = RecordingResult()
    plugin.onMethodCall(MethodCall("play", null), play)
    assertEquals("NO_ACTIVITY", play.errorCode)

    val open = RecordingResult()
    plugin.onMethodCall(MethodCall("open", emptyMap<String, Any>()), open)
    assertEquals("INVALID_ARGS", open.errorCode)

    val unknown = RecordingResult()
    plugin.onMethodCall(MethodCall("unknownMethod", null), unknown)
    assertEquals("NOT_IMPLEMENTED", unknown.errorCode)
  }

  @Test
  fun registeredPropertiesAndPlayerEventsReachTheFlutterStream() {
    val plugin = ExoPlayerPlugin()
    val sink = RecordingSink()
    plugin.onListen(null, sink)
    val registration = RecordingResult()
    plugin.onMethodCall(MethodCall("observeProperty", mapOf("name" to "pause", "id" to 7)), registration)
    assertTrue(registration.succeeded)

    plugin.onPropertyChange("pause", true)
    plugin.onPropertyChange("not-observed", "ignored")
    plugin.onEvent("end-file", mapOf("reason" to "eof"))
    Shadows.shadowOf(Looper.getMainLooper()).idle()
    assertEquals(
      listOf(listOf(7, true), mapOf("type" to "event", "name" to "end-file", "data" to mapOf("reason" to "eof"))),
      sink.events
    )

    plugin.onCancel(null)
    plugin.onPropertyChange("pause", false)
    Shadows.shadowOf(Looper.getMainLooper()).idle()
    assertEquals(2, sink.events.size)
  }

  private class RecordingSink : EventChannel.EventSink {
    val events = mutableListOf<Any?>()

    override fun success(event: Any?) { events.add(event) }
    override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {
      throw AssertionError("Unexpected event error: $errorCode")
    }
    override fun endOfStream() {}
  }

  private class RecordingResult : MethodChannel.Result {
    var value: Any? = null
    var errorCode: String? = null
    var succeeded = false

    override fun success(result: Any?) { value = result; succeeded = true }

    override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {
      this.errorCode = errorCode
    }

    override fun notImplemented() { errorCode = "NOT_IMPLEMENTED" }
  }
}
