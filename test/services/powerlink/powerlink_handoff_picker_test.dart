import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/focus/focusable_button.dart';
import 'package:plezy/focus/focusable_wrapper.dart';
import 'package:plezy/focus/input_mode_tracker.dart';
import 'package:plezy/services/powerlink/powerlink_app_client.dart';
import 'package:plezy/services/powerlink/powerlink_handoff_picker.dart';
import 'package:plezy/theme/mono_theme.dart';

const _source = 'media_player.bedroom_fire_tv_stick_lite';
const _living = 'media_player.living_room_fire_tv_stick_4k_plus';
const _game = 'media_player.game_room_fire_tv_stick_lite';
const _offline = 'media_player.offline_fire_tv';

class _Credentials extends PowerLinkAppCredentials {
  @override
  Future<PowerLinkAppIdentity?> load() async => PowerLinkAppIdentity(
    base: Uri.parse('http://192.168.1.40:8123'),
    sourceDevice: _source,
    sourceName: 'Bedroom',
    token: 'abcdefghijklmnopqrstuvwxyz0123456789abcdefghijkl',
  );
}

class _Api extends PowerLinkAppClient {
  final responses = <Completer<PowerLinkDeviceList>>[];
  int requests = 0;

  @override
  Future<PowerLinkDeviceList> discover(PowerLinkAppIdentity identity) {
    requests++;
    final completer = Completer<PowerLinkDeviceList>();
    responses.add(completer);
    return completer.future;
  }
}

PowerLinkDeviceList _destinations({
  bool livingAvailable = true,
  bool gameAvailable = true,
}) => PowerLinkDeviceList(
  sourceDevice: _source,
  destinations: [
    PowerLinkDestination(
      entityId: _living, name: 'Living Room',
      maxHeight: 2160, available: livingAvailable,
    ),
    const PowerLinkDestination(
      entityId: _offline, name: 'Offline',
      maxHeight: 1080, available: false,
    ),
    PowerLinkDestination(
      entityId: _game, name: 'Game Room',
      maxHeight: 1080, available: gameAvailable,
    ),
  ],
);

Finder _destination(String id) => find.byKey(Key('powerlink_destination_$id'));

FocusNode _destinationNode(WidgetTester tester, String id) =>
    tester.widget<FocusableWrapper>(_destination(id)).focusNode!;

Future<void> _openPicker(WidgetTester tester, _Api api) async {
  tester.view.physicalSize = const Size(1280, 720);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    InputModeTracker(
      child: MaterialApp(
        theme: monoTheme(MonoPalette.dark),
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => showDialog<void>(
                context: context,
                builder: (_) => PowerLinkHandoffPicker(
                  credentials: _Credentials(),
                  client: api,
                ),
              ),
              child: const Text('Open PowerLink'),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('Open PowerLink'));
  await tester.pump();
  await tester.pump();
}

Future<void> _finishDiscovery(WidgetTester tester, _Api api, PowerLinkDeviceList devices) async {
  // The picker must explicitly focus rows added AFTER asynchronous discovery:
  // the dialog initially contains only a loading spinner.
  for (var i = 0; i < 8 && api.responses.isEmpty; i++) {
    await tester.pump();
  }
  expect(api.responses, isNotEmpty);
  api.responses.last.complete(devices);
  await tester.pump();
  await tester.pump();
}

void main() {
  testWidgets('asynchronous TV discovery focuses first room, skips unavailable, and Select activates', (tester) async {
    final api = _Api();
    await _openPicker(tester, api);
    expect(find.text('Living Room'), findsNothing);

    await _finishDiscovery(tester, api, _destinations());
    expect(find.text('Living Room'), findsOneWidget);
    expect(find.text('Game Room'), findsOneWidget);
    expect(_destinationNode(tester, _living).hasPrimaryFocus, isTrue);

    // The unavailable row does not consume D-pad navigation.
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    expect(_destinationNode(tester, _game).hasPrimaryFocus, isTrue);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
    await tester.pump();
    expect(_destinationNode(tester, _living).hasPrimaryFocus, isTrue);

    // With no active Plex playback in this harness, Select must invoke
    // the handoff action and display the existing friendly guard instead
    // of remaining stuck on an inert ListTile.
    await tester.sendKeyEvent(LogicalKeyboardKey.select);
    await tester.pump();
    expect(find.text('Start a movie or TV queue before transferring playback.'), findsOneWidget);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));

  testWidgets('D-pad reaches Refresh and Cancel and dismisses modal, not player', (tester) async {
    final api = _Api();
    await _openPicker(tester, api);
    await _finishDiscovery(tester, api, _destinations());

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    expect(_destinationNode(tester, _game).hasPrimaryFocus, isTrue);

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    final refresh = tester.widget<FocusableButton>(
      find.ancestor(of: find.text('Refresh'), matching: find.byType(FocusableButton)),
    );
    final cancel = tester.widget<FocusableButton>(
      find.ancestor(of: find.text('Cancel'), matching: find.byType(FocusableButton)),
    );
    expect(refresh.focusNode!.hasPrimaryFocus, isTrue);

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
    await tester.pump();
    expect(cancel.focusNode!.hasPrimaryFocus, isTrue);

    await tester.sendKeyEvent(LogicalKeyboardKey.select);
    await tester.pump();
    expect(find.byType(PowerLinkHandoffPicker), findsNothing);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));

  testWidgets('offline-only destinations leave Refresh reachable, not a dead focus trap', (tester) async {
    final api = _Api();
    await _openPicker(tester, api);
    await _finishDiscovery(tester, api,
      _destinations(livingAvailable: false, gameAvailable: false));

    final refresh = tester.widget<FocusableButton>(
      find.ancestor(of: find.text('Refresh'), matching: find.byType(FocusableButton)),
    );
    expect(refresh.focusNode!.hasPrimaryFocus, isTrue);
    expect(tester.widget<FocusableWrapper>(_destination(_living)).canRequestFocus, isFalse);
    expect(tester.widget<FocusableWrapper>(_destination(_game)).canRequestFocus, isFalse);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));
}
