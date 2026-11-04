import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/media/media_kind.dart';
import 'package:plezy/media/media_item.dart';
import 'package:plezy/media/media_item_labels.dart';
import 'package:plezy/services/deep_links/deep_link.dart';
import 'package:plezy/services/powerlink/powerlink_transfer.dart';

Map<String, dynamic> slot(int index, {
  String status = 'resolved',
  String ratingKey = '15',
  int height = 1080,
  int? mediaIndex = 0,
  String? mediaId,
}) => {
  'index': index,
  'status': status,
  'title': 'Episode $index',
  'kind': 'episode',
  'show_title': 'Example Show',
  'season': 2,
  'episode': index + 1,
  'thumb_path': '/library/metadata/15/thumb/100',
  if (status == 'resolved')
    'media': {
      'server_id': 'plex-main',
      'rating_key': ratingKey,
      'height': height,
      'media_index': mediaIndex,
      'media_id': mediaId,
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
      expect((queue.items![0] as PlexMediaItem).playQueueItemId, 1);
      expect((queue.items![1] as PlexMediaItem).playQueueItemId, 2);
    });

    test('PowerLink queue renders full series labels and episode thumbnails', () {
      final result = PowerLinkQueueWindow.parse(window([
        slot(0, ratingKey: '11'),
        slot(1, ratingKey: '12', height: 2160, mediaIndex: 1),
        slot(2, ratingKey: '13'),
      ]));
      final first = result.items[0].toQueueItem() as PlexMediaItem;
      final selected = result.items[1].toQueueItem() as PlexMediaItem;
      expect(first.title, 'Episode 0');
      expect(first.grandparentTitle, 'Example Show');
      expect(first.parentIndex, 2);
      expect(first.index, 1);
      expect(first.thumbPath, '/library/metadata/15/thumb/100');
      expect(formatQueueItemSubtitle(first), 'Example Show · S2E1');
      expect(formatQueueItemSubtitle(selected), 'Example Show · S2E2');
      expect(selected.playQueueItemId, 2);
      expect(result.shuffled, true);
      expect(result.positionMs, 253400);
    });

    test('old integration metadata remains optional and does not change playback', () {
      final older = slot(0);
      for (final name in ['show_title', 'season', 'episode', 'thumb_path']) {
        older.remove(name);
      }
      final row = PowerLinkQueueWindow.parse(window([older], currentIndex: 0, total: 1));
      final item = row.items.single.toQueueItem() as PlexMediaItem;
      expect(item.grandparentTitle, isNull);
      expect(item.thumbPath, isNull);
      expect(item.playQueueItemId, 1);
      expect(item.id, '15');
    });

    test('external thumbnail URLs are not forwarded to the image loader', () {
      final row = slot(0)..['thumb_path'] = 'https://external.example/image.jpg';
      final result = PowerLinkQueueWindow.parse(window([row], currentIndex: 0, total: 1));
      expect(result.items.single.toQueueItem().thumbPath, isNull);
      expect(result.items.single.isAvailable, true);
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
      expect((result.items[1].toQueueItem() as PlexMediaItem).playQueueItemId, 2);
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
