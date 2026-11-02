package com.edde746.plezy.exoplayer

import android.app.Activity
import android.util.Log
import com.edde746.plezy.libass.media.AssHandler
import com.edde746.plezy.shared.PlayerChannelBinding
import com.edde746.plezy.shared.PlayerDebugLog
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.embedding.engine.plugins.activity.ActivityAware
import io.flutter.embedding.engine.plugins.activity.ActivityPluginBinding
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Fire TV Plex-only Media3 bridge. Never loads, imports or transitions into MPV.
 *
 * Preserves the existing Dart method/event channels and core observer protocol
 * so video screens, Plex play queues, subtitles and first-frame events use the
 * same existing ExoPlayerCore. Unsupported media errors are terminal at this
 * backend and flow to Dart; the application may offer a Plex transcode option.
 *
 * This is an appliance-only source overlay, not an upstream-wide replacement.
 */
class ExoPlayerPlugin :
  FlutterPlugin,
  MethodChannel.MethodCallHandler,
  EventChannel.StreamHandler,
  ActivityAware,
  ExoPlayerDelegate {

  companion object {
    private const val TAG = "ExoPlayerOnlyPlugin"
    private const val METHOD_CHANNEL = "com.plezy/exo_player"
  }

  private val channels = PlayerChannelBinding(METHOD_CHANNEL, this, this, TAG)
  private val observedProperties = LinkedHashMap<String, Int>()
  private var playerCore: ExoPlayerCore? = null
  private var coreInstanceId: Long? = null
  private var activity: Activity? = null
  private var sessionGeneration = 0
  private var mediaGeneration = 0
  private var debugLoggingEnabled = false

  override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
    channels.attach(binding)
  }

  override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
    teardownSession(clearActivity = true)
    channels.detach()
  }

  private fun teardownSession(clearActivity: Boolean) {
    ++sessionGeneration
    ++mediaGeneration
    val core = playerCore
    playerCore = null
    coreInstanceId = null
    observedProperties.clear()
    if (clearActivity) activity = null
    core?.dispose()
  }

  override fun onAttachedToActivity(binding: ActivityPluginBinding) {
    activity = binding.activity
  }

  override fun onDetachedFromActivity() {
    teardownSession(clearActivity = true)
  }

  override fun onReattachedToActivityForConfigChanges(binding: ActivityPluginBinding) {
    activity = binding.activity
  }

  override fun onDetachedFromActivityForConfigChanges() {
    teardownSession(clearActivity = true)
  }

  override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
    channels.listen(events)
  }

  override fun onCancel(arguments: Any?) {
    channels.cancel()
  }

  override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
    when (call.method) {
      "initialize" -> initialize(call, result)
      "dispose" -> dispose(call, result)
      "open" -> open(call, result)
      "play" -> withCore(result) { it.play(); result.success(null) }
      "pause" -> withCore(result) { it.pause(); result.success(null) }
      "stop" -> withCore(result) { it.stop(); result.success(null) }
      "seek" -> {
        val ms = call.argument<Number>("positionMs")?.toLong()
        if (ms == null) result.error("INVALID_ARGS", "Missing positionMs", null)
        else withCore(result) { it.seekTo(ms); result.success(null) }
      }
      "setVolume" -> {
        val volume = call.argument<Number>("volume")?.toFloat()
        if (volume == null) result.error("INVALID_ARGS", "Missing volume", null)
        else withCore(result) { it.setVolume(volume / 100f); result.success(null) }
      }
      "setRate" -> {
        val rate = call.argument<Number>("rate")?.toFloat()
        if (rate == null) result.error("INVALID_ARGS", "Missing rate", null)
        else withCore(result) { it.setPlaybackSpeed(rate); result.success(null) }
      }
      "selectAudioTrack" -> {
        val id = call.argument<String>("trackId")
        if (id == null) result.error("INVALID_ARGS", "Missing trackId", null)
        else withCore(result) { it.selectAudioTrack(id); result.success(null) }
      }
      "selectSubtitleTrack" -> withCore(result) {
        it.selectSubtitleTrack(call.argument<String>("trackId"))
        result.success(null)
      }
      "addSubtitleTrack" -> {
        val uri = call.argument<String>("uri")
        if (uri.isNullOrBlank()) result.error("INVALID_ARGS", "Missing subtitle URI", null)
        else withCore(result) {
          it.addSubtitleTrack(
            uri,
            call.argument("title"),
            call.argument("language"),
            call.argument("mimeType"),
            call.argument<Boolean>("select") ?: false
          )
          result.success(null)
        }
      }
      "setVisible" -> {
        val visible = call.argument<Boolean>("visible")
        if (visible == null) result.error("INVALID_ARGS", "Missing visible", null)
        else withCore(result) { it.setVisible(visible); result.success(null) }
      }
      "updateFrame" -> withCore(result) { it.updateFrame(); result.success(null) }
      "setVideoFrameRate" -> withCore(result) { core ->
        core.setVideoFrameRate(
          call.argument<Double>("fps")?.toFloat() ?: 0f,
          call.argument<Number>("duration")?.toLong() ?: 0L,
          call.argument<Number>("extraDelayMs")?.toLong() ?: 0L,
          call.argument<Number>("videoWidth")?.toInt() ?: 0,
          call.argument<Number>("videoHeight")?.toInt() ?: 0,
          call.argument<Boolean>("matchResolution") ?: false
        ) { switched -> result.success(switched) }
      }
      "clearVideoFrameRate" -> withCore(result) { it.clearVideoFrameRate(); result.success(null) }
      "requestAudioFocus" -> withCore(result) { result.success(it.requestAudioFocus()) }
      "abandonAudioFocus" -> withCore(result) { it.abandonAudioFocus(); result.success(null) }
      "isInitialized" -> result.success(playerCore?.isInitialized == true)
      "getPlayerType" -> result.success("exoplayer")
      "getStats" -> {
        // Diagnostics can poll during teardown: return a harmless snapshot.
        // Do not surface a spurious NOT_INITIALIZED error when no player exists.
        activity?.runOnUiThread {
          val core = playerCore
          val stats = if (core?.isInitialized == true) core.getStats() else emptyMap()
          result.success(stats + mapOf("playerType" to if (core?.isInitialized == true) "exoplayer" else "unknown"))
        } ?: result.success(mapOf("playerType" to "unknown"))
      }
      "observeProperty" -> {
        val name = call.argument<String>("name")
        val id = call.argument<Int>("id")
        if (name == null || id == null) result.error("INVALID_ARGS", "Missing observation", null)
        else {
          observedProperties[name] = id
          result.success(null)
        }
      }
      "setMpvProperty" -> {
        // Wire compatibility only. Native MPV is NOT linked or used.
        val name = call.argument<String>("name")
        val value = call.argument<String>("value")
        if (name == null || value == null) {
          result.error("INVALID_ARGS", "Missing property", null)
        } else {
          activity?.runOnUiThread {
            when (name) {
              "audio-delay" -> playerCore?.setAudioDelay(value.toDoubleOrNull() ?: 0.0)
              "sub-delay" -> playerCore?.setSubtitleDelay(value.toDoubleOrNull() ?: 0.0)
              "sub-ass-force-margins" -> playerCore?.setAssForceMargins(value == "yes")
              "force-seekable" -> playerCore?.setForceSeekable(value == "yes")
            }
            result.success(null)
          } ?: result.success(null)
        }
      }
      "setSubtitleStyle" -> withCore(result) {
        it.setSubtitleStyle(
          call.argument<Number>("fontSize")?.toFloat() ?: 55f,
          call.argument<String>("textColor") ?: "#FFFFFF",
          call.argument<Number>("borderSize")?.toFloat() ?: 3f,
          call.argument<String>("borderColor") ?: "#000000",
          call.argument<String>("bgColor") ?: "#000000",
          call.argument<Number>("bgOpacity")?.toInt() ?: 0,
          call.argument<Number>("subtitlePosition")?.toInt() ?: 100,
          call.argument<Boolean>("bold") ?: false,
          call.argument<Boolean>("italic") ?: false,
          call.argument<Boolean>("anchorToScreen") ?: false
        )
        result.success(null)
      }
      "setBoxFitMode" -> withCore(result) {
        val mode = call.argument<Number>("mode")?.toInt()
        if (mode == null) result.error("INVALID_ARGS", "Missing mode", null)
        else { it.setBoxFitMode(mode); result.success(null) }
      }
      "setVideoZoom" -> withCore(result) {
        val scale = call.argument<Number>("scale")?.toDouble()
        if (scale == null) result.error("INVALID_ARGS", "Missing scale", null)
        else { it.setVideoZoom(scale); result.success(null) }
      }
      "setDvConversionMode" -> withCore(result) {
        val mode = call.argument<String>("mode")
        if (mode == null) result.error("INVALID_ARGS", "Missing mode", null)
        else if (it.setDebugDvConversionMode(mode)) result.success(true)
        else result.error("INVALID_ARGS", "Invalid Dolby Vision mode", null)
      }
      "setAudioNormalization" -> withCore(result) {
        it.setAudioNormalization(call.argument<Boolean>("enabled") ?: false)
        result.success(true)
      }
      "setAudioPassthrough" -> withCore(result) {
        it.setAudioPassthrough(call.argument<Boolean>("enabled") ?: false)
        result.success(true)
      }
      "setAudioDownmix" -> withCore(result) {
        it.setAudioDownmix(
          call.argument<Boolean>("enabled") ?: false,
          call.argument<Int>("centerBoostDb") ?: 0,
          call.argument<Boolean>("normalize") ?: true
        )
        result.success(true)
      }
      "setLogLevel" -> {
        val level = call.argument<String>("level") ?: "warn"
        debugLoggingEnabled = PlayerDebugLog.isVerbose(level)
        PlayerDebugLog.enabled = debugLoggingEnabled
        playerCore?.debugLoggingEnabled = debugLoggingEnabled
        result.success(null)
      }
      // Debug forcing a backend fallback is deliberately unsupported.
      "triggerFallback" -> result.error("UNSUPPORTED", "This Fire TV edition has no MPV fallback", null)
      else -> result.notImplemented()
    }
  }

  private inline fun withCore(result: MethodChannel.Result, crossinline action: (ExoPlayerCore) -> Unit) {
    val currentActivity = activity
    if (currentActivity == null) {
      result.error("NO_ACTIVITY", "Activity is unavailable", null)
      return
    }
    currentActivity.runOnUiThread {
      val core = playerCore
      if (core?.isInitialized != true) {
        result.error("NOT_INITIALIZED", "ExoPlayer has not initialized", null)
      } else {
        try {
          action(core)
        } catch (e: Exception) {
          Log.e(TAG, "Player command failed", e)
          result.error("PLAYER_COMMAND_FAILED", e.message, null)
        }
      }
    }
  }

  private fun initialize(call: MethodCall, result: MethodChannel.Result) {
    val a = activity
    if (a == null) {
      result.error("NO_ACTIVITY", "Activity is unavailable", null)
      return
    }
    if (playerCore?.isInitialized == true) {
      result.success(true)
      return
    }
    val generation = sessionGeneration
    val scale = call.argument<Double>("subtitleRenderScale")?.toFloat() ?: 1f
    AssHandler.setRenderScale(scale)
    a.runOnUiThread {
      if (generation != sessionGeneration || activity !== a) {
        result.success(false)
        return@runOnUiThread
      }
      ++sessionGeneration
      playerCore?.dispose()
      playerCore = null
      try {
        val core = ExoPlayerCore(a).apply {
          delegate = this@ExoPlayerPlugin
          debugLoggingEnabled = this@ExoPlayerPlugin.debugLoggingEnabled
        }
        playerCore = core
        coreInstanceId = call.argument<Number>("instanceId")?.toLong()
        val ok = core.initialize(
          tunnelingEnabled = call.argument<Boolean>("tunnelingEnabled") ?: false,
          audioPassthroughEnabled = call.argument<Boolean>("audioPassthroughEnabled") ?: false,
          bufferTier = call.argument<String>("bufferTier") ?: "auto"
        )
        if (!ok) {
          core.dispose()
          playerCore = null
          result.success(false)
          return@runOnUiThread
        }
        val dvMode = call.argument<String>("dvConversionMode") ?: "auto"
        if (!core.setDebugDvConversionMode(dvMode)) Log.w(TAG, "Unknown DV mode: $dvMode")
        core.seedAssVideoLatencyFrames(call.argument<Int>("assVideoLatencyFrames") ?: 0)
        core.setVisible(false)
        result.success(true)
      } catch (e: Exception) {
        Log.e(TAG, "ExoPlayer initialization failed", e)
        playerCore?.dispose()
        playerCore = null
        result.error("INIT_FAILED", e.message, null)
      }
    }
  }

  private fun dispose(call: MethodCall, result: MethodChannel.Result) {
    val token = call.argument<Number>("instanceId")?.toLong()
    activity?.runOnUiThread {
      val owner = coreInstanceId
      if (token != null && owner != null && token != owner) {
        result.success(null)
        return@runOnUiThread
      }
      teardownSession(clearActivity = false)
      result.success(null)
    } ?: run {
      teardownSession(clearActivity = false)
      result.success(null)
    }
  }

  private fun open(call: MethodCall, result: MethodChannel.Result) {
    val uri = call.argument<String>("uri")
    if (uri.isNullOrBlank()) {
      result.error("INVALID_ARGS", "Missing media URI", null)
      return
    }
    val a = activity
    if (a == null) {
      result.error("NO_ACTIVITY", "Activity unavailable", null)
      return
    }
    val generation = ++mediaGeneration
    a.runOnUiThread {
      if (activity !== a || generation != mediaGeneration) {
        result.error("SUPERSEDED", "A newer media item replaced this open", null)
        return@runOnUiThread
      }
      val core = playerCore
      if (core?.isInitialized != true) {
        result.error("NOT_INITIALIZED", "ExoPlayer unavailable", null)
        return@runOnUiThread
      }
      try {
        @Suppress("UNCHECKED_CAST")
        val headers = call.argument<Map<String, String>>("headers")
        val subtitles = call.argument<List<Map<String, Any?>>>("externalSubtitles")
        core.open(
          uri = uri,
          headers = headers,
          startPositionMs = call.argument<Number>("startPositionMs")?.toLong() ?: 0L,
          autoPlay = call.argument<Boolean>("autoPlay") ?: true,
          mediaGeneration = generation,
          isLive = call.argument<Boolean>("isLive") ?: false,
          externalSubtitleList = subtitles,
          contentFrameRate = call.argument<Number>("contentFrameRate")?.toFloat() ?: -1f
        )
        result.success(null)
      } catch (e: Exception) {
        Log.e(TAG, "Failed opening ExoPlayer media", e)
        result.error("OPEN_FAILED", e.message, null)
      }
    }
  }

  fun onPipModeChanged(isInPipMode: Boolean) {
    activity?.runOnUiThread { playerCore?.onPipModeChanged(isInPipMode) }
  }

  override fun onPropertyChange(name: String, value: Any?) {
    observedProperties[name]?.let { channels.emitProperty(it, value) }
  }

  override fun onEvent(name: String, data: Map<String, Any>?) {
    channels.emitEvent(name, data)
  }

  override fun onFormatUnsupported(
    mediaGeneration: Int,
    uri: String,
    headers: Map<String, String>?,
    positionMs: Long,
    playWhenReady: Boolean,
    errorMessage: String
  ): Boolean {
    // ExoPlayerCore emits a single terminal playback error when we return false.
    // No MPV handover or concealed retry occurs in this APK.
    Log.e(TAG, "ExoPlayer unsupported media: $errorMessage")
    return false
  }
}
