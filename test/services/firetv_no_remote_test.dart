import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('Fire TV profile has no companion remote', () {
    expect(kFireTvNoCompanionRemote, isTrue);
    expect(kFireTvNoWatchTogether, isTrue);
  });
}
