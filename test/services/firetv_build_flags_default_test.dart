import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('ordinary upstream and future Windows builds retain full support', () {
    expect(kFireTvPlexOnly, isFalse);
    expect(kHomeAssistantManagedUpdates, isFalse);
  });
}
