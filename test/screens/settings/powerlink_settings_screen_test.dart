import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/focus/focusable_text_field.dart';
import 'package:plezy/screens/settings/powerlink_settings_screen.dart';
import 'package:plezy/theme/mono_theme.dart';
import 'package:plezy/utils/platform_detector.dart';
import 'package:plezy/widgets/focusable_list_tile.dart';

void main() {
  tearDown(() {
    TvDetectionService.debugSetAppleTVOverride(null);
    TvDetectionService.setForceTVSync(false);
  });

  Future<void> pumpPowerLink(WidgetTester tester) async {
    await TvDetectionService.getInstance(forceTv: true);
    TvDetectionService.setForceTVSync(true);
    tester.view.physicalSize = const Size(1280, 720);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(theme: monoTheme(MonoPalette.dark), home: const PowerLinkSettingsScreen()),
    );
    await tester.pump();
  }

  Finder nativeInput(String key) => find.descendant(
    of: find.byKey(Key(key)),
    matching: find.byType(TextField),
  );

  testWidgets('URL IME → code IME → Pair works with a D-pad', (tester) async {
    await pumpPowerLink(tester);

    final url = tester.widget<FocusableTextField>(
      find.byKey(const Key('powerlink_url_field')),
    );
    final code = tester.widget<FocusableTextField>(
      find.byKey(const Key('powerlink_code_field')),
    );
    final pair = tester.widget<FocusableListTile>(
      find.byKey(const Key('powerlink_pair_button')),
    );

    expect(url.tvTextInputAutoOpenBehavior, TvTextInputAutoOpenBehavior.never);
    expect(code.tvTextInputAutoOpenBehavior, TvTextInputAutoOpenBehavior.never);
    expect(pair.onTap, isNotNull);

    // Simply crossing the URL input must not launch the IME.
    url.focusNode!.requestFocus();
    await tester.pump();
    expect(tester.widget<TextField>(nativeInput('powerlink_url_field')).readOnly, isTrue);

    // Select opens the first native keyboard.
    await tester.sendKeyEvent(LogicalKeyboardKey.select);
    await tester.pump();
    expect(tester.widget<TextField>(nativeInput('powerlink_url_field')).readOnly, isFalse);
    await tester.enterText(nativeInput('powerlink_url_field'), 'http://10.0.0.10:8123');
    await tester.testTextInput.receiveAction(TextInputAction.next);
    await tester.pump();
    expect(code.focusNode!.hasPrimaryFocus, isTrue);
    expect(tester.widget<TextField>(nativeInput('powerlink_code_field')).readOnly, isTrue);

    // Select must open the SECOND native keyboard, not a stale URL session.
    await tester.sendKeyEvent(LogicalKeyboardKey.select);
    await tester.pump();
    expect(tester.widget<TextField>(nativeInput('powerlink_code_field')).readOnly, isFalse);
    await tester.enterText(nativeInput('powerlink_code_field'), '123');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    expect(pair.focusNode!.hasPrimaryFocus, isTrue);

    // A remote Select actually activates Pair, even when the code is
    // incomplete. Validation is local; no Home Assistant call is sent.
    await tester.sendKeyEvent(LogicalKeyboardKey.select);
    await tester.pump();
    expect(find.text('Enter the nine-digit PowerLink pairing code'), findsOneWidget);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));

  testWidgets('D-pad can traverse both fields and Pair without opening the keyboard', (tester) async {
    await pumpPowerLink(tester);

    final url = tester.widget<FocusableTextField>(
      find.byKey(const Key('powerlink_url_field')),
    );
    final code = tester.widget<FocusableTextField>(
      find.byKey(const Key('powerlink_code_field')),
    );
    final pair = tester.widget<FocusableListTile>(
      find.byKey(const Key('powerlink_pair_button')),
    );

    url.focusNode!.requestFocus();
    await tester.pump();
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    expect(code.focusNode!.hasPrimaryFocus, isTrue);
    expect(tester.widget<TextField>(nativeInput('powerlink_code_field')).readOnly, isTrue);

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
    await tester.pump();
    expect(url.focusNode!.hasPrimaryFocus, isTrue);

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    expect(pair.focusNode!.hasPrimaryFocus, isTrue);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));
}
