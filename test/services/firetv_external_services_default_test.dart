import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() {
  test('default build retains external integrations', () {
    expect(kFireTvNoExternalServices, isFalse);
  });
}
