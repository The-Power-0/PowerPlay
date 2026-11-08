import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/widgets/video_controls/widgets/performance_overlay/performance_stats.dart';

void main() {
  group('Pro Logic overlay diagnostics', () {
    test('does not appear for unsupported playback backends', () {
      const stats = PerformanceStats(playerType: 'mpv');
      expect(stats.hasProLogicDiagnostics, isFalse);
    });

    test('reports default-off without claiming an active encoder', () {
      const stats = PerformanceStats(playerType: 'exoplayer', proLogicEnabled: false);
      expect(stats.hasProLogicDiagnostics, isTrue);
      expect(stats.proLogicStateFormatted, 'Off');
    });

    test('reports actual PCM processing and budget distinctly from input codec', () {
      const stats = PerformanceStats(
        playerType: 'exoplayer',
        audioCodec: 'AC-3',
        audioChannels: '5.1',
        proLogicEnabled: true,
        proLogicProcessorConfigured: true,
        proLogicEncoding: true,
        proLogicOutputStereoPcm: true,
        proLogicInputChannels: 6,
        proLogicOutputChannels: 2,
        proLogicOutputSampleRate: 48000,
        proLogicOutputEncoding: 'pcm16',
        proLogicProcessedFrames: 48000,
        proLogicProcessedBuffers: 50,
        proLogicAverageBufferUs: 120.0,
        proLogicAudioTimePercent: 0.6,
        audioUnderruns: 0,
      );
      expect(stats.proLogicStateFormatted, 'Active - Lt/Rt');
      expect(stats.proLogicPathFormatted, contains('5.1'));
      expect(stats.proLogicPathFormatted, contains('2ch pcm16'));
      expect(stats.proLogicLoadFormatted, contains('0.60% audio time'));
      expect(stats.proLogicBuffersFormatted, '50 encoded / 0 underruns');
    });

    test('stereo is bypassed rather than claiming matrix encoding', () {
      const stats = PerformanceStats(
        playerType: 'exoplayer',
        proLogicEnabled: true,
        proLogicProcessorConfigured: false,
        proLogicInputChannels: 2,
        proLogicEncoding: false,
        proLogicProcessedFrames: 0,
      );
      expect(stats.proLogicStateFormatted, 'Stereo unchanged');
    });

    test('distinguishes pending PCM from an invalid output route', () {
      const pending = PerformanceStats(
        playerType: 'exoplayer',
        proLogicEnabled: true,
        proLogicProcessorConfigured: true,
        proLogicProcessedFrames: 0,
      );
      const mismatch = PerformanceStats(
        playerType: 'exoplayer',
        proLogicEnabled: true,
        proLogicProcessorConfigured: true,
        proLogicProcessedFrames: 480,
        proLogicOutputStereoPcm: false,
      );
      expect(pending.proLogicStateFormatted, 'Armed - awaiting PCM');
      expect(mismatch.proLogicStateFormatted, 'PCM output mismatch');
    });
  });
}
