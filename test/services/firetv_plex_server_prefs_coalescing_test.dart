import 'dart:async';
import 'dart:convert';

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:plezy/database/app_database.dart';
import 'package:plezy/media/ids.dart';
import 'package:plezy/services/plex_api_cache.dart';

import '../test_helpers/backend_client_fixtures.dart';

http.Response prefsResponse(int threshold) => http.Response(
  jsonEncode({
    'MediaContainer': {
      'Setting': [
        {'id': 'LibraryVideoPlayedThreshold', 'value': '$threshold'},
      ],
    },
  }),
  200,
  headers: const {'content-type': 'application/json'},
);

void main() {
  late AppDatabase database;
  setUp(() {
    database = AppDatabase.forTesting(NativeDatabase.memory());
    PlexApiCache.initialize(database);
  });
  tearDown(() => database.close());

  test('overlapping preference reads share one request, then refresh again', () async {
    final started = Completer<void>();
    final response = Completer<http.Response>();
    var requests = 0;
    final client = testPlexClient(
      handler: (request) {
        expect(request.url.path, '/:/prefs');
        requests++;
        if (requests == 1) {
          started.complete();
          return response.future;
        }
        return Future.value(prefsResponse(93));
      },
    );
    addTearDown(client.close);

    final first = client.fetchServerPrefs();
    final second = client.fetchServerPrefs();
    await started.future;
    expect(requests, 1);
    response.complete(prefsResponse(90));
    await Future.wait([first, second]);
    expect(client.watchedThresholdPercent, 90);

    await client.fetchServerPrefs();
    expect(requests, 2);
    expect(client.watchedThresholdPercent, 93);
  });

  test('a failed read does not block a later refresh', () async {
    var requests = 0;
    final client = testPlexClient(
      handler: (_) async {
        requests++;
        return requests == 1 ? http.Response('unavailable', 503) : prefsResponse(91);
      },
    );
    addTearDown(client.close);

    await client.fetchServerPrefs();
    await client.fetchServerPrefs();
    expect(requests, 2);
    expect(client.watchedThresholdPercent, 91);
  });

  test('two Plex clients do not share an in-flight preference request', () async {
    final pending = Completer<http.Response>();
    final started = Completer<void>();
    var firstCount = 0;
    var secondCount = 0;
    final first = testPlexClient(
      serverId: ServerId('first-server'),
      handler: (_) {
        firstCount++;
        started.complete();
        return pending.future;
      },
    );
    final second = testPlexClient(
      serverId: ServerId('second-server'),
      handler: (_) async {
        secondCount++;
        return prefsResponse(94);
      },
    );
    addTearDown(first.close);
    addTearDown(second.close);

    final firstFetch = first.fetchServerPrefs();
    await started.future;
    await second.fetchServerPrefs();
    expect((firstCount, secondCount), (1, 1));
    expect(second.watchedThresholdPercent, 94);
    pending.complete(prefsResponse(90));
    await firstFetch;
    expect(first.watchedThresholdPercent, 90);
  });
}
