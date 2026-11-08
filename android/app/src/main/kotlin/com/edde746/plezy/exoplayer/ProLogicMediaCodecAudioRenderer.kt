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
 * Keep the decoded PCM layout for every FFmpeg-recoverable multichannel codec.
 * This mirrors FfmpegLibrary.getCodecName, without claiming that an installed
 * FFmpeg binary necessarily supports every individual stream/profile.
 * Raw PCM and IAMF keep Media3's own channel-mask negotiation untouched.
 */
@OptIn(UnstableApi::class)
internal object ProLogicDecoderChannelPolicy {
  private val ffmpegRecoverableMimes = setOf(
    MimeTypes.AUDIO_AAC,
    MimeTypes.AUDIO_MPEG, MimeTypes.AUDIO_MPEG_L1, MimeTypes.AUDIO_MPEG_L2,
    MimeTypes.AUDIO_AC3, MimeTypes.AUDIO_E_AC3, MimeTypes.AUDIO_E_AC3_JOC,
    MimeTypes.AUDIO_TRUEHD, MimeTypes.AUDIO_DTS, MimeTypes.AUDIO_DTS_HD,
    MimeTypes.AUDIO_VORBIS, MimeTypes.AUDIO_OPUS,
    MimeTypes.AUDIO_FLAC, MimeTypes.AUDIO_ALAC,
    MimeTypes.AUDIO_AMR_NB, MimeTypes.AUDIO_AMR_WB,
    MimeTypes.AUDIO_MLAW, MimeTypes.AUDIO_ALAW
  )

  fun requestedOutputChannels(enabled: Boolean, mimeType: String?, channels: Int): Int? =
    if (enabled && supportsSoftwareFallback(mimeType) && channels in 3..12) channels else null

  fun supportsSoftwareFallback(mimeType: String?): Boolean = mimeType in ffmpegRecoverableMimes

  fun needsSoftwareFallback(
    enabled: Boolean,
    mimeType: String?,
    sourceChannels: Int,
    decodedChannels: Int,
    stereoPcmOutput: Boolean,
    alreadyRetried: Boolean
  ): Boolean =
    requestedOutputChannels(enabled, mimeType, sourceChannels) != null &&
      decodedChannels in 1 until sourceChannels &&
      stereoPcmOutput && !alreadyRetried
}

/**
 * Media3 1.11 only sets KEY_MAX_OUTPUT_CHANNEL_COUNT on API 32+.
 * Fire OS 7/8 devices may negotiate stereo PCM for multichannel
 * AC3, E-AC3, AAC or other supported codecs before the Lt/Rt matrix sees it.
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
