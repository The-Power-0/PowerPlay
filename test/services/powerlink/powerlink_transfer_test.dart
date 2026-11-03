import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/media/media_kind.dart';
import 'package:plezy/services/deep_links/deep_link.dart';
import 'package:plezy/services/powerlink/powerlink_transfer.dart';

Map<String, dynamic> slot(int index, {
  String status = 'resolved',
  String ratingKey = '15',
  int height = 1080,
  int? mediaIndex,
  String? mediaId,
}) => {
  'index': index,
  'status': status,
  'title': 'Episode $index',
  'kind': 'episode',
  if (status == 'resolved')
    'media': {
      'server_id': 'plex-main',
      'rating_key': ratingKey,
      'height': height,
      if (mediaIndex != null) 'media_index': mediaIndex,
      if (mediaId != null) 'media_id': mediaId,
      'guid': 'plex://episode/example',
    }
  else
    'media': null,
};

Map<String, dynamic> window(List<Map<String, dynamic>> rows, {
  int currentIndex = 1,
  int position = 253400,
  bool shuffled = true,
  int start = 0,
  int total = 3,
}) => {
  'schema': 1,
  'total': total,
  'current_index': currentIndex,
  'position_ms': position,
  'shuffled': shuffled,
  'start': start,
  'items': rows,
  'profile_id': null,
};

void main() {
  group('PowerLink transfer URI', () {
    final token = List.filled(32, 'x').join();

    test('accepts explicitly local HA endpoints and HTTPS remote links', () {
      for (final base in [
        'http://10.0.0.3:8123',
        'http://172.19.2.4:8123',
        'http://192.168.50.4:8123',
        'http://homeassistant.local:8123',
        'https://ha.example.com',
      ]) {
        final request = PowerLinkRequest.parse(base, token);
        expect(request, isNotNull, reason: base);
        expect(request!.windowUri(0, 16).queryParameters['count'], '16');
      }
    });

    test('rejects insecure remote URLs and embedded credentials', () {
      for (final base in [
        'http://8.8.8.8:8123',
        'http://example.com',
        'ftp://192.168.1.4',
        'https://user:pass@ha.example.com',
        'https://ha.example.com/?token=abc',
        'http://172.32.0.1:8123',
      ]) {
        expect(PowerLinkRequest.parse(base, token), isNull, reason: base);
      }
      expect(PowerLinkRequest.parse('https://ha.example.com', 'short'), isNull);
    });

    test('roundtrips through PowerPlay deep-link grammar', () {
      final link = PowerLinkResumeLink(
        PowerLinkRequest.parse('http://192.168.1.20:8123', token)!,
      );
      final reparsed = DeepLink.tryParse(link.toUri().toString());
      expect(reparsed, isA<PowerLinkResumeLink>());
      expect(reparsed!.toUri(), link.toUri());
      expect(DeepLink.tryParse('powerplay://powerlink?v=2&token=$token&base=https://ha.example.com'), isNull);
      expect(DeepLink.tryParse('powerplay://powerlink/other?v=1&token=$token&base=https://ha.example.com'), isNull);
    });
  });

  group('PowerLink queue window', () {
    test('preserves current index, resume position and shuffle state', () {
      final result = PowerLinkQueueWindow.parse(window([
        slot(0, ratingKey: '11'),
        slot(1, ratingKey: '11', height: 2160, mediaIndex: 1, mediaId: 'media-200'),
        slot(2, ratingKey: '42'),
      ]));
      expect(result.shuffled, isTrue);
      expect(result.currentIndex, 1);
      expect(result.positionMs, 253400);
      expect(result.selected!.ratingKey, '11');
      expect(result.selected!.height, 2160);
      expect(result.selected!.mediaIndex, 1);
      expect(result.selected!.mediaId, 'media-200');
      final queue = result.toPlaybackWindow();
      expect(queue.playQueueID, -2);
      expect(queue.playQueueSelectedItemID, 2);
      expect(queue.playQueueShuffled, true);
      expect(queue.items!.length, 3);
      expect(queue.items![0].id, queue.items![1].id);
      expect(queue.items![0].playQueueItemId, 1);
      expect(queue.items![1].playQueueItemId, 2);
    });

    test('normal playback queue is not converted into shuffle', () {
      final result = PowerLinkQueueWindow.parse(window([
        slot(0),
        slot(1),
        slot(2),
      ], shuffled: false));
      expect(result.toPlaybackWindow().playQueueShuffled, false);
      expect(result.selected!.kind, MediaKind.episode);
    });

    test('unavailable items keep their absolute position', () {
      final result = PowerLinkQueueWindow.parse(window([
        slot(0),
        slot(1, status: 'unavailable'),
        slot(2),
      ]));
      expect(result.items[1].isAvailable, false);
      expect(result.items[1].toQueueItem().raw?['powerlink_unavailable'], true);
      expect(result.items[1].toQueueItem().playQueueItemId, 2);
    });

    test('truncated/reordered windows and invalid offsets fail closed', () {
      expect(
        () => PowerLinkQueueWindow.parse(window([slot(0), slot(2)])),
        throwsFormatException,
      );
      expect(
        () => PowerLinkQueueWindow.parse(window([slot(0)], currentIndex: 10)),
        throwsFormatException,
      );
      expect(
        () => PowerLinkQueueWindow.parse(window([slot(0)], position: -2)),
        throwsFormatException,
      );
      expect(
        () => PowerLinkQueueWindow.parse(window([slot(0, status: 'resolved')..remove('media')])),
        throwsFormatException,
      );
    });
  });
}
