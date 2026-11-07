import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:plezy/services/powerlink/powerlink_app_client.dart';
import 'package:plezy/services/powershuffle/powershuffle_event_journal.dart';

class _Server extends PowerLinkAppClient {
  _Server();

  bool offline = false;
  final List<String> seen = [];

  @override
  Future<Map<String, dynamic>> powerShuffleEvent(
    PowerLinkAppIdentity identity, Map<String, dynamic> event,
  ) async {
    if (offline) throw StateError('Home Assistant temporarily offline');
    seen.add(event['event_id'] as String);
    return {'accepted': true, 'event_id': event['event_id'], 'queue': <String>[]};
  }
}

void main() {
  const identity = PowerLinkAppIdentity(
    base: _unusedBase, sourceDevice: 'media_player.bedroom',
    sourceName: 'Bedroom', token: 'not-a-real-test-credential',
  );

  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('durably retries unacknowledged playback events after restart', () async {
    final server = _Server()..offline = true;
    final journal = PowerShuffleEventJournal(client: server);
    final event = <String, dynamic>{
      'session_id': 'session-1', 'episode_key': '1:1',
      'event_id': 'stable-event-1', 'action': 'started',
    };
    await expectLater(journal.send(identity, event), throwsStateError);
    final preferences = await SharedPreferences.getInstance();
    final raw = preferences.getString('powershuffle.pending.v1.media_player.bedroom');
    expect(raw, isNotNull);
    expect(jsonDecode(raw!) as List, hasLength(1));

    server.offline = false;
    await PowerShuffleEventJournal(client: server).flush(identity);
    expect(server.seen, ['stable-event-1']);
    expect(jsonDecode(
      preferences.getString('powershuffle.pending.v1.media_player.bedroom')!,
    ) as List, isEmpty);
  });

  test('latest offline progress supersedes redundant unsent heartbeat', () async {
    final server = _Server()..offline = true;
    final journal = PowerShuffleEventJournal(client: server);
    final first = <String, dynamic>{
      'session_id': 'session-1', 'episode_key': '1:1',
      'event_id': 'started', 'action': 'started',
    };
    await expectLater(journal.send(identity, first), throwsStateError);
    for (var i = 1; i < 50; i++) {
      await expectLater(journal.send(identity, {
        'session_id': 'session-1', 'episode_key': '1:1',
        'event_id': 'progress-$i', 'action': 'progress',
        'ranges': <List<int>>[[0, i * 1000]],
      }), throwsStateError);
    }
    final prefs = await SharedPreferences.getInstance();
    final events = (jsonDecode(
      prefs.getString('powershuffle.pending.v1.media_player.bedroom')!,
    ) as List).cast<Map<String, dynamic>>();
    expect(events, hasLength(2));
    expect(events.last['event_id'], 'progress-49');
    server.offline = false;
    await journal.flush(identity);
    expect(server.seen, ['started', 'progress-49']);
  });
}

const _unusedBase = Uri(scheme: 'http', host: '10.0.0.10', port: 8123);
