import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/media/ids.dart';
import 'package:plezy/services/deep_links/deep_link.dart';

void main() {
  test('legacy HA shuffle deep link uses native shuffle mode', () {
    final link = DeepLink.tryParse('powerplay://shuffle?server=abc123&show=456');
    expect(link, isA<PlayLink>());
    final play = link! as PlayLink;
    expect(play.mode, PlayMode.shuffle);
    expect(play.target, isA<ItemPlayTarget>());
    final item = play.target as ItemPlayTarget;
    expect(item.serverId, ServerId('abc123'));
    expect(item.itemId, '456');
  });

  test('upstream native shuffle link still works', () {
    final link = DeepLink.tryParse('powerplay://play?server=abc123&id=456&mode=shuffle');
    expect(link, isA<PlayLink>());
    expect((link! as PlayLink).mode, PlayMode.shuffle);
  });

  test('legacy shuffle requires a server and show', () {
    expect(DeepLink.tryParse('powerplay://shuffle?server=abc123'), isNull);
    expect(DeepLink.tryParse('powerplay://shuffle?show=456'), isNull);
    expect(DeepLink.tryParse('powerplay://shuffle?server=abc123&show='), isNull);
  });
}
