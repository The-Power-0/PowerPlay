import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/mpv/player/platform/player_android.dart';
import 'package:plezy/services/settings_service.dart';

import '../test_helpers/mock_player_channels.dart';
import '../test_helpers/prefs.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    resetSharedPreferencesForTest();
    SettingsService.resetForTesting();
    await SettingsService.getInstance();
  });

  test('volume set before initialization is sent once the player is ready', () async {
    final calls = <MethodCall>[];
    await withMockPlayerChannels(
      methodChannelName: 'com.plezy/exo_player',
      eventChannelName: 'com.plezy/exo_player/events',
      methodHandler: (call) async {
        calls.add(call);
        if (call.method == 'initialize' || call.method == 'requestAudioFocus') return true;
        return null;
      },
      testBody: () async {
        final player = PlayerAndroid();
        try {
          await player.setVolume(35);
          await player.setVolume(70);
          expect(player.state.volume, 70);
          expect(calls.where((call) => call.method == 'setVolume'), isEmpty);

          await player.requestAudioFocus();
          final writes = calls.where((call) => call.method == 'setVolume').toList();
          expect(writes, hasLength(1));
          expect((writes.single.arguments as Map)['volume'], 70);
          expect(calls.indexWhere((call) => call.method == 'initialize'), lessThan(calls.indexOf(writes.single)));
        } finally {
          await player.dispose();
        }
      },
    );
  });

  test('the newest volume requested during initialization wins', () async {
    final calls = <MethodCall>[];
    final started = Completer<void>();
    final initialization = Completer<bool>();
    await withMockPlayerChannels(
      methodChannelName: 'com.plezy/exo_player',
      eventChannelName: 'com.plezy/exo_player/events',
      methodHandler: (call) async {
        calls.add(call);
        if (call.method == 'initialize') {
          started.complete();
          return initialization.future;
        }
        return call.method == 'requestAudioFocus' ? true : null;
      },
      testBody: () async {
        final player = PlayerAndroid();
        try {
          final focus = player.requestAudioFocus();
          await started.future;
          final first = player.setVolume(40);
          final latest = player.setVolume(60);
          initialization.complete(true);
          await focus;
          await first;
          await latest;
          final writes = calls.where((call) => call.method == 'setVolume').toList();
          expect(writes, isNotEmpty);
          expect(writes.map((call) => (call.arguments as Map)['volume']), everyElement(60));
          expect(player.state.volume, 60);
        } finally {
          await player.dispose();
        }
      },
    );
  });

  test('volume changes after initialization are sent immediately', () async {
    final calls = <MethodCall>[];
    await withMockPlayerChannels(
      methodChannelName: 'com.plezy/exo_player',
      eventChannelName: 'com.plezy/exo_player/events',
      methodHandler: (call) async {
        calls.add(call);
        if (call.method == 'initialize' || call.method == 'requestAudioFocus') return true;
        return null;
      },
      testBody: () async {
        final player = PlayerAndroid();
        try {
          await player.requestAudioFocus();
          await player.setVolume(42);
          final writes = calls.where((call) => call.method == 'setVolume').toList();
          expect(writes, hasLength(1));
          expect((writes.single.arguments as Map)['volume'], 42);
          expect(player.state.volume, 42);
        } finally {
          await player.dispose();
        }
      },
    );
  });
}
