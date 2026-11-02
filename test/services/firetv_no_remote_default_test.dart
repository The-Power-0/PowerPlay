import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/firetv_build_flags.dart';

void main() => test('regular builds retain remote', () {
  expect(kFireTvNoCompanionRemote, isFalse);
});
