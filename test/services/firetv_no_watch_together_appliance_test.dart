import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('appliance disables Watch Together', () {
    expect(kFireTvPlexOnly, isTrue);
    expect(kFireTvMoviesTvOnly, isTrue);
    expect(kFireTvNoWatchTogether, isTrue);
  });
}
