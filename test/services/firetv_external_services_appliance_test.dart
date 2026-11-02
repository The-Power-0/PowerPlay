import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('movies and TV edition excludes cloud catalogs and trackers', () {
    expect(kFireTvPlexOnly, isTrue);
    expect(kFireTvMoviesTvOnly, isTrue);
    expect(kFireTvNoExternalServices, isTrue);
    expect(kFireTvForceExoVideo, isTrue);
  });
}
