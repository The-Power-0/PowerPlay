package com.edde746.plezy.exoplayer

import android.content.Context
import android.media.MediaFormat
import android.os.Handler
import androidx.annotation.OptIn
import androidx.media3.common.Format
import androidx.media3.common.MimeTypes
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.audio.AudioRendererEventListener
import androidx.media3.exoplayer.audio.AudioSink
import androidx.media3.exoplayer.audio.MediaCodecAudioRenderer
import androidx.media3.exoplayer.mediacodec.MediaCodecAdapter
import androidx.media3.exoplayer.mediacodec.MediaCodecSelector

/**
 * Only encoded AC3/EAC3 is eligible for this explicit decoder channel request.
 * Do not request it for stereo or while Pro Logic is disabled, and do not
 * override the special output-layout negotiation used for other audio codecs.
 */
@OptIn(UnstableApi::class)
internal object ProLogicDecoderChannelPolicy {
  fun requestedOutputChannels(enabled: Boolean, mimeType: String?, channels: Int): Int? =
    if (enabled && supportsSoftwareFallback(mimeType) && channels in 3..8) channels else null

  fun supportsSoftwareFallback(mimeType: String?): Boolean =
    mimeType == MimeTypes.AUDIO_AC3 ||
      mimeType == MimeTypes.AUDIO_E_AC3 ||
      mimeType == MimeTypes.AUDIO_E_AC3_JOC

  fun needsSoftwareFallback(
    enabled: Boolean,
    mimeType: String?,
    sourceChannels: Int,
    decodedChannels: Int,
    stereoPcmOutput: Boolean,
    alreadyRetried: Boolean
  ): Boolean =
    requestedOutputChannels(enabled, mimeType, sourceChannels) != null &&
      decodedChannels == 2 && stereoPcmOutput && !alreadyRetried
}

/**
 * Media3 1.11 only sets KEY_MAX_OUTPUT_CHANNEL_COUNT on API 32+.
 * Fire OS 7/8 devices may therefore negotiate stereo PCM for 5.1 AC3
 * even when our custom AudioProcessor can convert 6ch PCM to Lt/Rt.
 *
 * Retain the stock hardware decoder, audio sink and renderer parameters.
 * This only changes a codec configuration hint when Pro Logic is opted in.
 */
@OptIn(UnstableApi::class)
internal class ProLogicMediaCodecAudioRenderer(
  context: Context,
  codecAdapterFactory: MediaCodecAdapter.Factory,
  mediaCodecSelector: MediaCodecSelector,
  enableDecoderFallback: Boolean,
  eventHandler: Handler,
  eventListener: AudioRendererEventListener,
  audioSink: AudioSink,
  private val proLogicEnabled: () -> Boolean
) : MediaCodecAudioRenderer(
  context, codecAdapterFactory, mediaCodecSelector, enableDecoderFallback,
  eventHandler, eventListener, audioSink
) {
  override fun getMediaFormat(
    format: Format,
    codecMimeType: String,
    codecMaxInputSize: Int,
    codecOperatingRate: Float
  ): MediaFormat {
    val mediaFormat = super.getMediaFormat(format, codecMimeType, codecMaxInputSize, codecOperatingRate)
    val channels = ProLogicDecoderChannelPolicy.requestedOutputChannels(
      proLogicEnabled(), format.sampleMimeType, format.channelCount
    )
    if (channels != null) {
      mediaFormat.setInteger(MediaFormat.KEY_MAX_OUTPUT_CHANNEL_COUNT, channels)
    }
    return mediaFormat
  }
}
