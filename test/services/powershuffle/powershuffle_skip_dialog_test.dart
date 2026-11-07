import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/focus/focusable_button.dart';
import 'package:plezy/focus/input_mode_tracker.dart';
import 'package:plezy/services/powershuffle/powershuffle_skip_dialog.dart';
import 'package:plezy/theme/mono_theme.dart';

Finder _option(String label) => find.ancestor(
      of: find.text(label),
      matching: find.byType(FocusableButton),
    );

FocusNode _focus(WidgetTester tester, String label) =>
    tester.widget<FocusableButton>(_option(label)).focusNode!;

Future<void> _open(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    InputModeTracker(
      child: MaterialApp(
        theme: monoTheme(MonoPalette.dark),
        home: Scaffold(
          body: Builder(
            builder: (context) => Center(
              child: TextButton(
                onPressed: () async {
                  final result = await PowerShuffleSkipDialog.show(context);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(result ?? 'cancelled')),
                    );
                  }
                },
                child: const Text('Open PowerShuffle'),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('Open PowerShuffle'));
  await tester.pump();
  await tester.pump();
}

void main() {
  testWidgets('TV remote focuses first choice and D-pad moves between exactly two choices',
      (tester) async {
    await _open(tester, const Size(1280, 720));
    expect(find.byType(PowerShuffleSkipDialog), findsOneWidget);
    expect(find.byType(FocusableButton), findsNWidgets(2));
    expect(find.text('Skip for 5 days'), findsOneWidget);
    expect(find.text('Skip until next cycle'), findsOneWidget);
    expect(_focus(tester, 'Skip for 5 days').hasPrimaryFocus, isTrue);

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    expect(_focus(tester, 'Skip until next cycle').hasPrimaryFocus, isTrue);

    await tester.sendKeyEvent(LogicalKeyboardKey.select);
    await tester.pumpAndSettle();
    expect(find.byType(PowerShuffleSkipDialog), findsNothing);
    expect(find.text('next_cycle'), findsOneWidget);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));

  testWidgets('Back cancels without selecting a skip or dismissing the underlying player',
      (tester) async {
    await _open(tester, const Size(1280, 720));
    expect(_focus(tester, 'Skip for 5 days').hasPrimaryFocus, isTrue);
    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();
    expect(find.byType(PowerShuffleSkipDialog), findsNothing);
    expect(find.text('cancelled'), findsOneWidget);
    expect(find.text('Open PowerShuffle'), findsOneWidget);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));

  testWidgets('small Fire TV viewport keeps both choices visible without overflow',
      (tester) async {
    await _open(tester, const Size(960, 540));
    expect(find.byKey(const Key('powershuffle_skip_5_days')), findsOneWidget);
    expect(find.byKey(const Key('powershuffle_skip_next_cycle')), findsOneWidget);
    final first = tester.getRect(find.byKey(const Key('powershuffle_skip_5_days')));
    final second = tester.getRect(find.byKey(const Key('powershuffle_skip_next_cycle')));
    expect(first.bottom, lessThanOrEqualTo(second.top));
    expect(second.bottom, lessThanOrEqualTo(540));
    expect(tester.takeException(), isNull);
  }, variant: TargetPlatformVariant.only(TargetPlatform.android));
}
