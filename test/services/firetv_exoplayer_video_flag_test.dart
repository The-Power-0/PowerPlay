import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('Fire TV candidate always chooses ExoPlayer for video', () {
    expect(kFireTvPlexOnly, isTrue);
    expect(kFireTvForceExoVideo, isTrue);
    expect(useExoPlayerForAndroidVideo(false), isTrue);
    expect(useExoPlayerForAndroidVideo(true), isTrue);
  });
}
