import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/navigation/profile_navigation_scope.dart';

void main() {
  test('Home handler follows the newest profile screen and ignores stale detach', () {
    final registry = ProfileNavigationRegistry();
    final firstOwner = Object();
    final secondOwner = Object();
    var selected = '';

    registry.attachHomeHandler(firstOwner, () => selected = 'first');
    registry.homeHandler?.call();
    expect(selected, 'first');

    registry.attachHomeHandler(secondOwner, () => selected = 'second');
    registry.detachHomeHandler(firstOwner);
    registry.homeHandler?.call();
    expect(selected, 'second');

    registry.detachHomeHandler(secondOwner);
    expect(registry.homeHandler, isNull);
  });
}
