#!/usr/bin/env python3
"""Source-level regression guard for phase 01 Fire TV external-service pruning.

This validates exact patched source guards; it is NOT a compilation, runtime,
network-capture or binary-size test. Never prints Plex tokens or stored sessions.
"""
from pathlib import Path

checks = {
    "lib/services/firetv_build_flags.dart": (
        "const bool kFireTvNoExternalServices",
        "'PLEZY_FIRETV_NO_EXTERNAL_SERVICES'",
    ),
    "lib/navigation/profile_session_screen.dart": (
        "plexSessionSupplier: () => kFireTvNoExternalServices",
        "if (!kFireTvNoExternalServices)",
        "DiscoverProvider(",
    ),
    "lib/providers/catalog_sources_provider.dart": (
        "get connectedSources => kFireTvNoExternalServices ? const <CatalogSource>[]",
        "get seerrSource => kFireTvNoExternalServices ? null",
    ),
    "lib/services/trackers/tracker_coordinator.dart": (
        "_trackers = kFireTvNoExternalServices ? <Tracker>[]",
        "Future<void> flushWriteQueue() async {",
        "if (kFireTvNoExternalServices) return;",
    ),
    "lib/screens/settings/settings_screen.dart": (
        "if (!kFireTvNoExternalServices) _buildServicesTile()",
    ),
    "lib/screens/main_screen.dart": (
        "if (!kFireTvNoExternalServices && resumedFromBackground && mounted)",
    ),
    "test/services/firetv_external_services_appliance_test.dart": (
        "expect(kFireTvNoExternalServices, isTrue)",
    ),
    "test/services/firetv_external_services_default_test.dart": (
        "expect(kFireTvNoExternalServices, isFalse)",
    ),
}
for name, required in checks.items():
    file = Path(name)
    if not file.is_file():
        raise SystemExit(f"Missing required source/test: {name}")
    contents = file.read_text(encoding="utf-8")
    for text in required:
        if text not in contents:
            raise SystemExit(f"Missing external-service gate in {name}: {text}")
profile = Path("lib/navigation/profile_session_screen.dart").read_text(encoding="utf-8")
if profile.count("import '../services/firetv_build_flags.dart';") != 1:
    raise SystemExit("Appliance flags imported zero or multiple times in profile session")
main = Path("lib/screens/main_screen.dart").read_text(encoding="utf-8")
if main.count("import '../services/firetv_build_flags.dart';") != 1:
    raise SystemExit("Appliance flags imported zero or multiple times in MainScreen")
print(f"External-service source audit passed ({len(checks)} files).")
print("Local Plex Home/Continue Watching retained. No APK build or live HTTP test performed.")
