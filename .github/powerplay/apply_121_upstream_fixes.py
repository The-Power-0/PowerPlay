#!/usr/bin/env python3
"""Audit shipped optimizations and backport only the missing D-pad fix for 1.2.1."""
import argparse
from pathlib import Path

# Verify against the actual pinned, transformed APK source, not repo-root files.
EXISTING_FIXES = {
    "lib/utils/platform_http_client_io.dart": ["..idleTimeout = const Duration(seconds: 15)", "..maxConnectionsPerHost = 12"],
    "lib/services/playback_progress_tracker.dart": ["_pausedKeepaliveInFlight"],
    "lib/screens/video_player/live_timeline_report.dart": ["Future<void>? _pending"],
    "lib/utils/media_server_http_client.dart": ["static Future<Uint8List> _readBody(", "int? maxBytes"],
    "lib/services/bif_thumbnail_service.dart": ["static int get _maxFileBytes"],
    "lib/screens/video_player/parts/playback_services.dart": ["_untilFirstFrameUi()"],
    "lib/widgets/card_inflation_budget.dart": ["bool Function()? isOnScreen"],
    "lib/widgets/tv_browse_rail.dart": ["Per-hub media-card widget cache"],
    "lib/screens/media_detail_screen.dart": ["bool _tvDetailRouteSettled = false"],
    "lib/profiles/active_profile_binder.dart": ["typedef _PlexBindToken"],
    "lib/services/multi_server_manager.dart": ["forceRediscovery = false"],
    "lib/widgets/media_grid_delegate.dart": ["static double cellHeightFor("],
}

BEFORE = """      final targetOffset = (currentOffset + scrollDelta).clamp(position.minScrollExtent, position.maxScrollExtent);

      position.animateTo(targetOffset, duration: const Duration(milliseconds: 200), curve: Curves.easeInOut);"""
AFTER = """      final targetOffset = (currentOffset + scrollDelta).clamp(position.minScrollExtent, position.maxScrollExtent);
      // A no-op inner scroll may collapse the NestedScrollView's floating
      // library header; animate only if the offset actually changes.
      // Adapted from Plezy 63f8cd84 (#2916).
      if ((targetOffset - currentOffset).abs() < 0.5) return;

      position.animateTo(targetOffset, duration: const Duration(milliseconds: 200), curve: Curves.easeInOut);"""
TEST_ANCHOR = """  testWidgets('dialog close restoring pointer-parked focus keeps the scroll position', (tester) async {"""
TEST = """  testWidgets('top-row D-pad focus does not collapse the floating library header (#2916)', (tester) async {
    tester.view.physicalSize = const Size(800, 600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final nodes = List.generate(4, (i) => FocusNode(debugLabel: 'card$i'));
    final outerController = ScrollController();
    for (final node in nodes) {
      addTearDown(node.dispose);
    }
    addTearDown(outerController.dispose);

    await tester.pumpWidget(
      InputModeTracker(
        child: MaterialApp(
          home: Scaffold(
            body: NestedScrollView(
              controller: outerController,
              floatHeaderSlivers: true,
              headerSliverBuilder: (context, _) => [
                SliverOverlapAbsorber(
                  handle: NestedScrollView.sliverOverlapAbsorberHandleFor(context),
                  sliver: const SliverAppBar(floating: true, snap: true, title: Text('header')),
                ),
              ],
              body: CustomScrollView(
                primary: true,
                slivers: [
                  SliverToBoxAdapter(
                    child: Row(
                      children: [
                        for (var i = 0; i < nodes.length; i++)
                          FocusableWrapper(
                            focusNode: nodes[i],
                            useComfortableZone: false,
                            scrollAlignment: 0.5,
                            onSelect: () {},
                            onNavigateRight: i + 1 < nodes.length ? nodes[i + 1].requestFocus : null,
                            child: const SizedBox(width: 100, height: 150),
                          ),
                      ],
                    ),
                  ),
                  const SliverToBoxAdapter(child: SizedBox(height: 420)),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pump();
    nodes.first.requestFocus();
    await tester.pumpAndSettle();

    final headerOffsets = [outerController.offset];
    for (var i = 1; i < nodes.length; i++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await tester.pumpAndSettle();
      expect(nodes[i].hasFocus, isTrue);
      headerOffsets.add(outerController.offset);
    }
    expect(headerOffsets, everyElement(0.0));
  });

"""

def apply(source: Path):
    for relative, needles in EXISTING_FIXES.items():
        text = (source / relative).read_text()
        for needle in needles:
            if needle not in text:
                raise SystemExit(f"Unexpected missing shipped feature: {relative}: {needle}")
    focus = source / "lib/focus/focusable_wrapper.dart"
    original = focus.read_text()
    if original.count(BEFORE) != 1:
        raise SystemExit("Focus-scroll source differs; manually review backport")
    test_file = source / "test/focus/focusable_wrapper_test.dart"
    tests = test_file.read_text()
    if tests.count(TEST_ANCHOR) != 1 or "top-row D-pad focus does not collapse" in tests:
        raise SystemExit("Focus test anchor changed; manually review backport")
    focus.write_text(original.replace(BEFORE, AFTER, 1))
    test_file.write_text(tests.replace(TEST_ANCHOR, TEST + TEST_ANCHOR, 1))
    print("PowerPlay 1.2.1: verified six preexisting improvements; patched missing focus behavior and regression test")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    apply(parser.parse_args().source.resolve())
