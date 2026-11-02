#!/usr/bin/env python3
"""Phase 04: disable Plezy Companion Remote on the Plex movie/TV Fire TV build.

Pinned upstream 2.25.0, run after stages 01-03. This is a strict runtime
exclusion; shared declarations will be pruned after compile-time reachability
checks. Never touches the actual Android TV remote, D-pad or HA URI receiver.
"""
from pathlib import Path

def change(path: str, before: str, after: str = "") -> None:
    f = Path(path)
    content = f.read_text(encoding="utf-8")
    count = content.count(before)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {before[:90]!r}")
    f.write_text(content.replace(before, after), encoding="utf-8")
    print("No Companion Remote:", path)

flags = Path("lib/services/firetv_build_flags.dart")
if "kFireTvNoWatchTogether" not in flags.read_text(encoding="utf-8"):
    raise SystemExit("Requires all earlier Fire TV overlays")
if "kFireTvNoCompanionRemote" in flags.read_text(encoding="utf-8"):
    raise SystemExit("Remote exclusion already applied")
with flags.open("a", encoding="utf-8") as stream:
    stream.write(
        "\n/// Exclude Plezy Remote host/client/pairing from Fire TV appliance.\n"
        "/// Physical D-pad, media keys and Home Assistant URIs are unaffected.\n"
        "const bool kFireTvNoCompanionRemote =\n"
        "    bool.fromEnvironment('PLEZY_FIRETV_NO_COMPANION_REMOTE', defaultValue: false);\n"
    )

# Skip constructing the provider. This avoids crypto identity hydration and
# long-lived LAN/peer services even if a stale preference says 'enabled'.
profile = "lib/navigation/profile_session_screen.dart"
change(profile,
       "              ChangeNotifierProvider(\n"
       "                create: (context) {\n"
       "                  final provider = CompanionRemoteProvider();",
       "              if (!kFireTvNoCompanionRemote) ChangeNotifierProvider(\n"
       "                create: (context) {\n"
       "                  final provider = CompanionRemoteProvider();")

main = "lib/screens/main_screen.dart"
change(main, "    if (!_companionRemoteSetup && PlatformDetector.shouldActAsRemoteHost(context)) {",
       "    if (!kFireTvNoCompanionRemote && !_companionRemoteSetup && PlatformDetector.shouldActAsRemoteHost(context)) {")
change(main, "        if (_companionRemoteSetup) {\n          unawaited(_autoStartCompanionRemoteServer());",
       "        if (!kFireTvNoCompanionRemote && _companionRemoteSetup) {\n          unawaited(_autoStartCompanionRemoteServer());")
change(main, "  Future<void> _autoStartCompanionRemoteServer() async {\n",
       "  Future<void> _autoStartCompanionRemoteServer() async {\n"
       "    if (kFireTvNoCompanionRemote) return;\n")
change(main, "hasActiveCompanionRemoteSession: resumedFromBackground && context.read<CompanionRemoteProvider>().isInSession,",
       "hasActiveCompanionRemoteSession: !kFireTvNoCompanionRemote && resumedFromBackground && context.read<CompanionRemoteProvider>().isInSession,")

# Stage 03 converted the Home toolbar to Consumer<CompanionRemoteProvider>.
# Drop the entire remote button + status badge but keep the same action-bar
# layout, manual Refresh, server activities, Plex hubs and Continue Watching.
home = "lib/screens/discover_screen.dart"
change(home, "import '../providers/companion_remote_provider.dart';\n", "")
change(home, "import '../widgets/companion_remote/remote_session_dialog.dart';\n", "")
change(home, "import 'companion_remote/mobile_remote_screen.dart';\n", "")
change(home,
       "          Consumer<CompanionRemoteProvider>(\n"
       "            builder: (context, companionRemote, _) {",
       "          Builder(\n"
       "            builder: (context) {")
change(home, "              final isDesktop = PlatformDetector.shouldActAsRemoteHost(context);\n", "")
hf = Path(home)
text = hf.read_text(encoding="utf-8")
start = "              void openCompanionRemote() {\n"
end = "              return FocusableActionBar(\n"
if text.count(start) != 1 or text.count(end) != 1:
    raise SystemExit("Unexpected Home remote action helper structure")
a, b = text.index(start), text.index(end, text.index(start))
text = text[:a] + text[b:]
start = "                  // Companion Remote\n"
end = "                  // Server Tasks"
if text.count(start) != 1 or text.count(end) != 1:
    raise SystemExit("Unexpected Home remote button structure")
a, b = text.index(start), text.index(end, text.index(start))
text = text[:a] + text[b:]
for forbidden in ("CompanionRemoteProvider", "RemoteSessionDialog", "MobileRemoteScreen", "openCompanionRemote"):
    if forbidden in text:
        raise SystemExit("Remote control still wired to local Home: " + forbidden)
if "manualRefresh" not in text or "DiscoverProvider" not in text:
    raise SystemExit("Local Plex Home was damaged")
hf.write_text(text, encoding="utf-8")

# Fire TV playback remains fully controlled by local key events. The removed
# companion binding has no effect on Home Assistant plezy:// deep links.
player = "lib/screens/video_player_screen.dart"
change(player, "    _companionRemote.bind();", "    if (!kFireTvNoCompanionRemote) _companionRemote.bind();")

settings = "lib/screens/settings/settings_screen.dart"
change(settings,
       "      if (PlatformDetector.shouldActAsRemoteHost(context))\n"
       "        SettingSwitchTile(\n"
       "          focusNode: _focusTracker.get(_kCompanionRemoteServer),",
       "      if (!kFireTvNoCompanionRemote && PlatformDetector.shouldActAsRemoteHost(context))\n"
       "        SettingSwitchTile(\n"
       "          focusNode: _focusTracker.get(_kCompanionRemoteServer),")

mutations = "lib/services/settings_mutation_service.dart"
change(mutations,
       "import 'companion_remote/companion_remote_host_controller.dart';",
       "import 'companion_remote/companion_remote_host_controller.dart';\n"
       "import 'firetv_build_flags.dart';")
change(mutations,
       "  static Future<void> _applyCompanionRemoteServer(\n"
       "    BuildContext context,\n"
       "    SettingsService settings,\n"
       "    void Function()? checkCurrent,\n"
       "  ) async {\n",
       "  static Future<void> _applyCompanionRemoteServer(\n"
       "    BuildContext context,\n"
       "    SettingsService settings,\n"
       "    void Function()? checkCurrent,\n"
       "  ) async {\n"
       "    if (kFireTvNoCompanionRemote) return;\n")

teardown = "lib/screens/profile/profile_teardown.dart"
change(teardown,
       "import '../../providers/companion_remote_provider.dart';",
       "import '../../providers/companion_remote_provider.dart';\n"
       "import '../../services/firetv_build_flags.dart';")
change(teardown,
       "  final companionRemote = context.read<CompanionRemoteProvider>();",
       "  final companionRemote = kFireTvNoCompanionRemote ? null : context.read<CompanionRemoteProvider>();")
change(teardown, "  await companionRemote.resetForLogout();",
       "  if (companionRemote != null) await companionRemote.resetForLogout();")

# Defense in depth: bypass transport even if some future refactor tries to
# instantiate a remote provider directly instead of reading the profile scope.
provider = "lib/providers/companion_remote_provider.dart"
change(provider,
       "import '../services/companion_remote/companion_remote_peer_service.dart';",
       "import '../services/companion_remote/companion_remote_peer_service.dart';\n"
       "import '../services/firetv_build_flags.dart';")
change(provider,
       "  Future<void> _startHostServerLocked({void Function()? checkCurrent}) async {\n",
       "  Future<void> _startHostServerLocked({void Function()? checkCurrent}) async {\n"
       "    if (kFireTvNoCompanionRemote) return;\n")
change(provider,
       "  Stream<List<DiscoveredHost>>? discoverHosts() {\n",
       "  Stream<List<DiscoveredHost>>? discoverHosts() {\n"
       "    if (kFireTvNoCompanionRemote) return null;\n")

# Reject direct pairing entrypoints even if future code constructs this
# provider in an isolated test or outside the scoped profile.
change(provider,
       "  Future<void> connectToDiscoveredHost(DiscoveredHost host) async {\n",
       "  Future<void> connectToDiscoveredHost(DiscoveredHost host) async {\n"
       "    if (kFireTvNoCompanionRemote) return;\n")
change(provider,
       "  Future<void> connectToManualHost(String hostAddress) async {\n",
       "  Future<void> connectToManualHost(String hostAddress) async {\n"
       "    if (kFireTvNoCompanionRemote) return;\n")

for name, data in {
    "test/services/firetv_no_remote_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() {\n"
        "  test('Fire TV profile has no companion remote', () {\n"
        "    expect(kFireTvNoCompanionRemote, isTrue);\n"
        "    expect(kFireTvNoWatchTogether, isTrue);\n"
        "  });\n"
        "}\n"
    ),
    "test/services/firetv_no_remote_default_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() => test('regular builds retain remote', () {\n"
        "  expect(kFireTvNoCompanionRemote, isFalse);\n"
        "});\n"
    ),
}.items():
    target = Path(name)
    if target.exists():
        raise SystemExit(f"Existing test, refusing overwrite: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data, encoding="utf-8")
print("Companion Remote disabled. Plex D-pad and HA deep links retained.")
print("No APK built; source and type reachability still need compilation checks.")
