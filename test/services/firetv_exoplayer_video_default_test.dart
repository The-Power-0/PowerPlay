import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('normal builds preserve saved Android video backend preference', () {
    expect(kFireTvForceExoVideo, isFalse);
    expect(useExoPlayerForAndroidVideo(false), isFalse);
    expect(useExoPlayerForAndroidVideo(true), isTrue);
  });
}
