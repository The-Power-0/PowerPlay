#!/usr/bin/env python3
"""Stage 03: remove Watch Together execution paths from Fire TV Plex edition.

Run on EXACT upstream 2.25.0 checkout after stages 01 and 02. No build.
Normal upstream / Windows builds are unmodified by this source overlay.
openwatchparty SDK and shared interface types are kept until type-reachability
analysis can remove all dependencies safely; no room can actually be created.
"""
from pathlib import Path


def change(path: str, before: str, after: str = "") -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    count = s.count(before)
    if count != 1:
        raise SystemExit(f"{path}: expected exact anchor once, got {count}: {before[:110]!r}")
    p.write_text(s.replace(before, after), encoding="utf-8")
    print("No Watch Together:", path)


flags = Path("lib/services/firetv_build_flags.dart")
if not flags.is_file() or "kFireTvNoExternalServices" not in flags.read_text(encoding="utf-8"):
    raise SystemExit("Stage 03 requires Plex-only + movies/TV-only + external-service overlays")
if "kFireTvNoWatchTogether" in flags.read_text(encoding="utf-8"):
    raise SystemExit("Watch Together flag already exists")
with flags.open("a", encoding="utf-8") as out:
    out.write(
        "\n/// This appliance excludes room sessions, relays and shared playback.\n"
        "const bool kFireTvNoWatchTogether =\n"
        "    bool.fromEnvironment('PLEZY_FIRETV_NO_WATCH_TOGETHER', defaultValue: false);\n"
    )

profile = "lib/navigation/profile_session_screen.dart"
change(
    profile,
    "              // Per profile: a profile switch disposes of it, which leaves the\n"
    "              // room and closes the party.\n"
    "              ChangeNotifierProvider(",
    "              // A room provider is not constructed in this appliance.\n"
    "              if (!kFireTvNoWatchTogether) ChangeNotifierProvider(",
)

# The profile wrapper may remain, but without a room provider it must not
# call Provider.of or install any notification stream subscription.
notice = "lib/watch_together/widgets/watch_notice_listener.dart"
change(notice, "import '../../navigation/profile_navigation_scope.dart';",
       "import '../../navigation/profile_navigation_scope.dart';\n"
       "import '../../services/firetv_build_flags.dart';")
change(notice, "    super.didChangeDependencies();\n"
               "    final provider = Provider.of<WatchTogetherProvider>(context, listen: false);",
       "    super.didChangeDependencies();\n"
       "    if (kFireTvNoWatchTogether) return;\n"
       "    final provider = Provider.of<WatchTogetherProvider>(context, listen: false);")

main = "lib/screens/main_screen.dart"
change(main,
       "    if (!_isOffline) {\n"
       "      _setupWatchTogetherCallback();\n"
       "    }",
       "    if (!_isOffline && !kFireTvNoWatchTogether) {\n"
       "      _setupWatchTogetherCallback();\n"
       "    }")

# Remove the Home toolbar entry (but retain Refresh and Companion Remote for
# the next independent feature-removal PR). This also removes an entire
# WatchTogetherProvider dependency from Home's reactive rebuild triggers.
home = "lib/screens/discover_screen.dart"
change(home, "import '../watch_together/watch_together.dart';\n", "")
change(home,
       "              void openWatchTogether() =>\n"
       "                  Navigator.push(context, MaterialPageRoute(builder: (_) => const WatchTogetherScreen()));\n",
       "")
change(home,
       "          Consumer2<WatchTogetherProvider, CompanionRemoteProvider>(\n"
       "            builder: (context, watchTogether, companionRemote, _) {",
       "          Consumer<CompanionRemoteProvider>(\n"
       "            builder: (context, companionRemote, _) {")
home_file = Path(home)
h = home_file.read_text(encoding="utf-8")
start_key = "                  // Watch Together\n"
end_key = "                  // Companion Remote\n"
if h.count(start_key) != 1 or h.count(end_key) != 1:
    raise SystemExit("Home toolbar action block changed upstream")
start = h.index(start_key)
end = h.index(end_key, start)
assert "FocusableAction(" in h[start:end] and "WatchTogetherScreen" not in h[start:end]
h = h[:start] + h[end:]
# The local Home screen still displays Plex hubs/Continue Watching.
if "manualRefresh" not in h or "DiscoverProvider" not in h:
    raise SystemExit("Home source unexpectedly damaged")
home_file.write_text(h, encoding="utf-8")

# No room may take control of ExoPlayer's start, seek, next episode or speed.
# Other Plex player and HA deep-link paths stay exactly as upstream.
video = "lib/screens/video_player_screen.dart"
change(video,
       "    if (!widget.isLive) {\n"
       "      try {\n"
       "        _watchTogetherProvider = context.read<WatchTogetherProvider?>();",
       "    if (!widget.isLive && !kFireTvNoWatchTogether) {\n"
       "      try {\n"
       "        _watchTogetherProvider = context.read<WatchTogetherProvider?>();")
part = "lib/screens/video_player/parts/watch_together.dart"
change(part, "  WatchTogetherProvider? _watchTogetherRoom() {\n",
       "  WatchTogetherProvider? _watchTogetherRoom() {\n"
       "    if (kFireTvNoWatchTogether) return null;\n")
change(part, "  WatchTogetherProvider? _followedRoom() {\n",
       "  WatchTogetherProvider? _followedRoom() {\n"
       "    if (kFireTvNoWatchTogether) return null;\n")

build = "lib/screens/video_player/parts/build.dart"
change(build,
       "                    try {\n"
       "                      authority = context",
       "                    if (!kFireTvNoWatchTogether) {\n"
       "                      try {\n"
       "                        authority = context")
change(build,
       "                      // Watch Together is optional outside the main app shell.\n"
       "                    }\n"
       "                    if (_lastMediaControlAuthority != authority) {",
       "                      // Watch Together is optional outside the main app shell.\n"
       "                      }\n"
       "                    }\n"
       "                    if (_lastMediaControlAuthority != authority) {")
change(build, "              const VideoPlayerWatchTogetherOverlays(),",
       "              if (!kFireTvNoWatchTogether) const VideoPlayerWatchTogetherOverlays(),")

header = "lib/widgets/video_controls/widgets/video_controls_header.dart"
change(header, "import '../../../watch_together/providers/watch_together_provider.dart';",
       "import '../../../watch_together/providers/watch_together_provider.dart';\n"
       "import '../../../services/firetv_build_flags.dart';")
change(header, "        Selector<WatchTogetherProvider, bool>(",
       "        if (!kFireTvNoWatchTogether) Selector<WatchTogetherProvider, bool>(")

sheet = "lib/widgets/video_controls/sheets/video_settings_sheet.dart"
change(sheet, "import '../../../watch_together/providers/watch_together_provider.dart';",
       "import '../../../watch_together/providers/watch_together_provider.dart';\n"
       "import '../../../services/firetv_build_flags.dart';")
change(sheet,
       "        if (context.watch<WatchTogetherProvider?>() case final watchTogether? when watchTogether.isInSession)",
       "        if (!kFireTvNoWatchTogether)\n"
       "          if (context.watch<WatchTogetherProvider?>() case final watchTogether? when watchTogether.isInSession)")

# The playback speed sheet also reads room drift ownership on every rate
# update. Avoid even a failed provider lookup when rooms are disabled.
change(sheet,
       "  double _displayedRate(double playerRate) {\n    try {",
       "  double _displayedRate(double playerRate) {\n"
       "    if (kFireTvNoWatchTogether) return playerRate;\n"
       "    try {")

controls = "lib/widgets/video_controls/parts/playback_input.dart"
change(controls, "  bool _syncOwnsRate() {\n    try {",
       "  bool _syncOwnsRate() {\n"
       "    if (kFireTvNoWatchTogether) return false;\n"
       "    try {")
change("lib/widgets/video_controls/video_controls.dart",
       "import '../../watch_together/providers/watch_together_provider.dart';",
       "import '../../watch_together/providers/watch_together_provider.dart';\n"
       "import '../../services/firetv_build_flags.dart';")

# The settings relay URL remains inert for compatibility; no relay-settings
# action or provider is constructed in this custom edition.
settings = "lib/screens/settings/settings_screen.dart"
change(settings,
       "        SettingNavigationTile(\n"
       "          focusNode: _focusTracker.get(_kWatchTogetherRelay),",
       "        if (!kFireTvNoWatchTogether) SettingNavigationTile(\n"
       "          focusNode: _focusTracker.get(_kWatchTogetherRelay),")

# Hard block outbound room transport, including direct calls to create/join.
provider = "lib/watch_together/providers/watch_together_provider.dart"
change(provider, "import '../services/watch_party_relays.dart';",
       "import '../services/watch_party_relays.dart';\n"
       "import '../../services/firetv_build_flags.dart';")
change(provider, "  Future<owp.WatchParty<WatchCopy>> _newParty() async {\n",
       "  Future<owp.WatchParty<WatchCopy>> _newParty() async {\n"
       "    if (kFireTvNoWatchTogether) {\n"
       "      throw StateError('Watch Together is unavailable in this Fire TV edition');\n"
       "    }\n")

# Avoid room-provider lookups from HA/agent playback commands when absent.
agent = "lib/services/agent_playback_commands.dart"
change(agent,
       "import '../watch_together/providers/watch_together_provider.dart';",
       "import '../watch_together/providers/watch_together_provider.dart';\n"
       "import '../services/firetv_build_flags.dart';")
change(agent,
       "    final watchTogether = context.context.read<WatchTogetherProvider?>();",
       "    final watchTogether = kFireTvNoWatchTogether\n"
       "        ? null\n"
       "        : context.context.read<WatchTogetherProvider?>();")

nav = "lib/utils/video_player_navigation.dart"
change(nav, "import '../watch_together/providers/watch_together_provider.dart';",
       "import '../watch_together/providers/watch_together_provider.dart';\n"
       "import '../services/firetv_build_flags.dart';")
change(nav, "Future<bool> navigateToWatchTogetherPlayback(BuildContext context, WatchCopy copy) async {\n",
       "Future<bool> navigateToWatchTogetherPlayback(BuildContext context, WatchCopy copy) async {\n"
       "  if (kFireTvNoWatchTogether) return false;\n")

for name, content in {
    "test/services/firetv_no_watch_together_appliance_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() {\n"
        "  test('appliance disables Watch Together', () {\n"
        "    expect(kFireTvPlexOnly, isTrue);\n"
        "    expect(kFireTvMoviesTvOnly, isTrue);\n"
        "    expect(kFireTvNoWatchTogether, isTrue);\n"
        "  });\n"
        "}\n"),
    "test/services/firetv_no_watch_together_default_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() {\n"
        "  test('ordinary builds preserve room controls', () {\n"
        "    expect(kFireTvNoWatchTogether, isFalse);\n"
        "  });\n"
        "}\n"),
}.items():
    file = Path(name)
    if file.exists():
        raise SystemExit("Refusing to overwrite existing Watch Together test: " + name)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")

print("Stage 03: no room provider, toolbar action, playback takeover, relay or UI overlay.")
print("openwatchparty types remain in source for later safe pruning. No APK built.")
