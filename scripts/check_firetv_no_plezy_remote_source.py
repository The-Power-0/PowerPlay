#!/usr/bin/env python3
"""Fail-closed source checks for Fire TV Plezy Remote runtime exclusion.

Source-only: does not imply Dart compilation, Android runtime tests or APK size.
"""
from pathlib import Path

def require(path: str, *markers: str) -> str:
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"Missing expected source {path}")
    body = p.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in body:
            raise SystemExit(f"Remote exclusion guard missing: {path}: {marker}")
    return body

require("lib/services/firetv_build_flags.dart", "kFireTvNoCompanionRemote", "PLEZY_FIRETV_NO_COMPANION_REMOTE")
require("lib/navigation/profile_session_screen.dart", "if (!kFireTvNoCompanionRemote) ChangeNotifierProvider(")
require("lib/screens/main_screen.dart",
        "if (!kFireTvNoCompanionRemote && !_companionRemoteSetup",
        "if (!kFireTvNoCompanionRemote && _companionRemoteSetup)",
        "hasActiveCompanionRemoteSession: !kFireTvNoCompanionRemote")
require("lib/screens/video_player_screen.dart", "if (!kFireTvNoCompanionRemote) _companionRemote.bind();")
require("lib/services/settings_mutation_service.dart", "if (kFireTvNoCompanionRemote) return;")
require("lib/screens/profile/profile_teardown.dart",
        "kFireTvNoCompanionRemote ? null : context.read<CompanionRemoteProvider>()",
        "if (companionRemote != null) await companionRemote.resetForLogout();")
require("lib/providers/companion_remote_provider.dart",
        "if (kFireTvNoCompanionRemote) return;",
        "Stream<List<DiscoveredHost>>? discoverHosts()",
        "Future<void> connectToDiscoveredHost(",
        "Future<void> connectToManualHost(")
home = require("lib/screens/discover_screen.dart", "DiscoverProvider", "manualRefresh")
for unexpected in ("CompanionRemoteProvider", "openCompanionRemote", "MobileRemoteScreen", "RemoteSessionDialog"):
    if unexpected in home:
        raise SystemExit("Plezy Remote action remains on Plex Home: " + unexpected)
require("lib/screens/settings/settings_screen.dart",
        "if (!kFireTvNoCompanionRemote && PlatformDetector.shouldActAsRemoteHost(context))")
require("test/services/firetv_no_remote_test.dart", "expect(kFireTvNoCompanionRemote, isTrue)")
require("test/services/firetv_no_remote_default_test.dart", "expect(kFireTvNoCompanionRemote, isFalse)")
# Make sure the physical Android TV remote and HA shuffle routes were NOT
# removed as a side effect of isolating Plezy Remote.
require("lib/screens/video_player_screen.dart", "_handleBackButton()", "_handleHomeButton()")
require("lib/screens/main_screen.dart", "_attachDeepLinks();")
print("Stage 04 Plezy Remote source exclusion checks passed.")
print("NOT an APK build; Dart type checks and hardware regression tests remain.")
