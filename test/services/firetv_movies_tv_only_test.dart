import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('movies/TV appliance has no music engine', () {
    expect(kFireTvPlexOnly, isTrue);
    expect(kFireTvForceExoVideo, isTrue);
    expect(kFireTvMoviesTvOnly, isTrue);
    expect(useExoPlayerForAndroidVideo(false), isTrue);
  });
}
