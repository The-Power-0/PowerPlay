import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('the Fire TV Plex-only build flags are enabled for candidate', () {
    expect(kFireTvPlexOnly, isTrue);
    expect(kHomeAssistantManagedUpdates, isTrue);
  });
}
