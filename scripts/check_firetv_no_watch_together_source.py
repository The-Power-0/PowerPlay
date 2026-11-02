#!/usr/bin/env python3
"""Source-only contract validation for Watch Together runtime removal.

Run on exact fully patched checkout after apply_firetv_remove_watch_together.
Passing does not mean the OpenWatchParty dependency has been pruned, nor
does it mean this source compiles or has been tested on Fire TV hardware.
"""
from pathlib import Path

def check(p: str, *tokens: str) -> None:
    file = Path(p)
    if not file.is_file():
        raise SystemExit("Missing source: " + p)
    txt = file.read_text(encoding="utf-8")
    for token in tokens:
        if token not in txt:
            raise SystemExit(f"Watch Together source guard missing in {p}: {token}")

check("lib/services/firetv_build_flags.dart",
      "const bool kFireTvNoWatchTogether",
      "PLEZY_FIRETV_NO_WATCH_TOGETHER")
check("lib/navigation/profile_session_screen.dart",
      "if (!kFireTvNoWatchTogether) ChangeNotifierProvider(")
check("lib/watch_together/widgets/watch_notice_listener.dart",
      "if (kFireTvNoWatchTogether) return;")
check("lib/screens/main_screen.dart",
      "if (!_isOffline && !kFireTvNoWatchTogether)")
check("lib/screens/video_player_screen.dart",
      "if (!widget.isLive && !kFireTvNoWatchTogether)")
check("lib/screens/video_player/parts/watch_together.dart",
      "if (kFireTvNoWatchTogether) return null;")
check("lib/screens/video_player/parts/build.dart",
      "if (!kFireTvNoWatchTogether) {",
      "if (!kFireTvNoWatchTogether) const VideoPlayerWatchTogetherOverlays()")
check("lib/widgets/video_controls/widgets/video_controls_header.dart",
      "if (!kFireTvNoWatchTogether) Selector<WatchTogetherProvider")
check("lib/widgets/video_controls/sheets/video_settings_sheet.dart",
      "if (!kFireTvNoWatchTogether)",
      "if (context.watch<WatchTogetherProvider?>() case",
      "if (kFireTvNoWatchTogether) return playerRate;")
check("lib/widgets/video_controls/parts/playback_input.dart",
      "if (kFireTvNoWatchTogether) return false;")
check("lib/screens/settings/settings_screen.dart",
      "if (!kFireTvNoWatchTogether) SettingNavigationTile(")
check("lib/watch_together/providers/watch_together_provider.dart",
      "if (kFireTvNoWatchTogether) {",
      "throw StateError('Watch Together is unavailable")
check("lib/services/agent_playback_commands.dart",
      "final watchTogether = kFireTvNoWatchTogether",
      "context.context.read<WatchTogetherProvider?>()")
check("lib/utils/video_player_navigation.dart",
      "if (kFireTvNoWatchTogether) return false;")
home = Path("lib/screens/discover_screen.dart").read_text(encoding="utf-8")
for absent in (
    "Consumer2<WatchTogetherProvider, CompanionRemoteProvider>",
    "openWatchTogether()",
    "const WatchTogetherScreen()",
    "t.watchTogether.title",
):
    if absent in home:
        raise SystemExit("Watch Together Home entry remains: " + absent)
for required in ("DiscoverProvider", "manualRefresh", "Consumer<CompanionRemoteProvider>"):
    if required not in home:
        raise SystemExit("Local Plex Home or shared toolbar was removed: " + required)
nav = Path("lib/utils/video_player_navigation.dart").read_text(encoding="utf-8")
if "Future<" not in nav or "navigateToVideoPlayer(" not in nav:
    raise SystemExit("Standard Plex/HA playback navigation unexpectedly removed")
for p in (
    "test/services/firetv_no_watch_together_appliance_test.dart",
    "test/services/firetv_no_watch_together_default_test.dart",
):
    if not Path(p).is_file():
        raise SystemExit("Watch Together build-flag test missing: " + p)
print("Watch Together runtime exclusion guards present. Local Plex Home and playback preserved.")
print("NOT a build; OpenWatchParty SDK/source still require a dependency-pruning pass.")
