#!/usr/bin/env python3
"""Keep in-app Home navigation when the Companion Remote is disabled.

Run after the other Fire TV overlays on the pinned 2.25.0 source. Each
replacement fails closed if upstream or another stage changes its context.
"""
from pathlib import Path


def replace_one(name: str, before: str, after: str) -> None:
    path = Path(name)
    source = path.read_text(encoding="utf-8")
    count = source.count(before)
    if count != 1:
        raise SystemExit(f"{name}: expected one anchor, found {count}: {before[:100]!r}")
    path.write_text(source.replace(before, after), encoding="utf-8")


registry = "lib/navigation/profile_navigation_scope.dart"
replace_one(
    registry,
    "  GlobalKey<ScaffoldMessengerState>? _mainScaffoldMessengerKey;\n",
    "  GlobalKey<ScaffoldMessengerState>? _mainScaffoldMessengerKey;\n"
    "  Object? _homeHandlerOwner;\n"
    "  VoidCallback? _homeHandler;\n",
)
replace_one(
    registry,
    "  ScaffoldMessengerState? get mainScaffoldMessenger => _mainScaffoldMessengerKey?.currentState;\n",
    "  ScaffoldMessengerState? get mainScaffoldMessenger => _mainScaffoldMessengerKey?.currentState;\n"
    "  VoidCallback? get homeHandler => _homeHandler;\n\n"
    "  void attachHomeHandler(Object owner, VoidCallback handler) {\n"
    "    _homeHandlerOwner = owner;\n"
    "    _homeHandler = handler;\n"
    "  }\n\n"
    "  void detachHomeHandler(Object owner) {\n"
    "    if (identical(_homeHandlerOwner, owner)) {\n"
    "      _homeHandlerOwner = null;\n"
    "      _homeHandler = null;\n"
    "    }\n"
    "  }\n",
)

main = "lib/screens/main_screen.dart"
replace_one(
    main,
    "  void initState() {\n    super.initState();\n",
    "  void initState() {\n    super.initState();\n"
    "    if (kFireTvNoCompanionRemote) {\n"
    "      profileNavigationRegistry.attachHomeHandler(this, _navigateToHomeTab);\n"
    "    }\n",
)
replace_one(
    main,
    "    receiver.onHome = () {\n"
    "      final tabs = _getVisibleTabs(_isOffline);\n"
    "      if (tabs.isEmpty) return;\n"
    "      _selectTab(tabs.first.id);\n"
    "      WidgetsBinding.instance.addPostFrameCallback((_) {\n"
    "        if (mounted) _sideNavKey.currentState?.focusHomeItem();\n"
    "      });\n"
    "    };\n",
    "    receiver.onHome = _navigateToHomeTab;\n",
)
replace_one(
    main,
    "  Future<void> _autoStartCompanionRemoteServer() async {\n",
    "  void _navigateToHomeTab() {\n"
    "    if (!mounted) return;\n"
    "    final tabs = _getVisibleTabs(_isOffline);\n"
    "    if (tabs.isEmpty) return;\n"
    "    _selectTab(tabs.first.id);\n"
    "    WidgetsBinding.instance.addPostFrameCallback((_) {\n"
    "      if (mounted) _sideNavKey.currentState?.focusHomeItem();\n"
    "    });\n"
    "  }\n\n"
    "  Future<void> _autoStartCompanionRemoteServer() async {\n",
)
replace_one(
    main,
    "  void dispose() {\n",
    "  void dispose() {\n"
    "    if (kFireTvNoCompanionRemote) profileNavigationRegistry.detachHomeHandler(this);\n",
)

player = "lib/screens/video_player_screen.dart"
replace_one(
    player,
    "import '../providers/companion_remote_provider.dart';\n",
    "import '../providers/companion_remote_provider.dart';\n"
    "import '../navigation/profile_navigation_scope.dart';\n",
)
replace_one(
    player,
    "    final onHome = _companionRemote.savedOnHome;\n",
    "    final onHome = kFireTvNoCompanionRemote\n"
    "        ? profileNavigationRegistry.homeHandler\n"
    "        : _companionRemote.savedOnHome;\n",
)
print("Fire TV Home navigation no longer depends on the Companion Remote provider.")
