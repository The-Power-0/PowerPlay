#!/usr/bin/env python3
"""Phase 01: disable external catalog/request/tracker services in Fire TV edition.

Applies only to the EXACT already-patched 2.25.0 source checkout, after
apply_firetv_mpv_retirement.py. Does not change local Plex Home / Continue
Watching / normal server watched progress / Home Assistant shuffle links.

The compile-time flag defaults false. No destructive account/credential
migration: old saved connections remain available to standard Plezy builds.
Source remains in the tree for now; unreachable code pruning and size
measurement are separate phases.
"""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    src = file.read_text(encoding="utf-8")
    count = src.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected 1 matching upstream anchor, found {count}: {old[:110]!r}")
    file.write_text(src.replace(old, new), encoding="utf-8")
    print("External-services appliance: patched", path)

flag_file = Path("lib/services/firetv_build_flags.dart")
if not flag_file.is_file() or "kFireTvMoviesTvOnly" not in flag_file.read_text():
    raise SystemExit("Run the existing movies/TV and MPV-retirement overlays first")
with flag_file.open("a", encoding="utf-8") as flags:
    flags.write(
        "\n/// Disable all external catalog integrations, requests and tracker syncing.\n"
        "/// Does not affect local Plex library, on-deck, watched-state or HA links.\n"
        "const bool kFireTvNoExternalServices =\n"
        "    bool.fromEnvironment('PLEZY_FIRETV_NO_EXTERNAL_SERVICES', defaultValue: false);\n"
    )

profile = "lib/navigation/profile_session_screen.dart"
# The earlier movies/TV overlay already imports firetv_build_flags.dart here.
replace_once(
    profile,
    "    plexSessionSupplier: () => resolvePlexDiscoverSession(",
    "    plexSessionSupplier: () => kFireTvNoExternalServices\n"
    "        ? Future.value(null)\n"
    "        : resolvePlexDiscoverSession(",
)
replace_once(
    profile,
    "                  unawaited(\n"
    "                    provider.onActiveProfileChanged(activeId).catchError((Object e, StackTrace s) {\n"
    "                      appLogger.w('Trackers profile hydrate failed', error: e, stackTrace: s);\n"
    "                    }),\n"
    "                  );",
    "                  if (!kFireTvNoExternalServices) {\n"
    "                    unawaited(\n"
    "                      provider.onActiveProfileChanged(activeId).catchError((Object e, StackTrace s) {\n"
    "                        appLogger.w('Trackers profile hydrate failed', error: e, stackTrace: s);\n"
    "                      }),\n"
    "                    );\n"
    "                  }",
)
replace_once(
    profile,
    "                  unawaited(\n"
    "                    provider.onActiveProfileChanged(activeId).catchError((Object e, StackTrace s) {\n"
    "                      appLogger.w('Seerr profile hydrate failed', error: e, stackTrace: s);\n"
    "                    }),\n"
    "                  );",
    "                  if (!kFireTvNoExternalServices) {\n"
    "                    unawaited(\n"
    "                      provider.onActiveProfileChanged(activeId).catchError((Object e, StackTrace s) {\n"
    "                        appLogger.w('Seerr profile hydrate failed', error: e, stackTrace: s);\n"
    "                      }),\n"
    "                    );\n"
    "                  }",
)
replace_once(
    profile,
    "                  unawaited(\n"
    "                    provider.onActiveProfileChanged(activeId).catchError((Object e, StackTrace s) {\n"
    "                      appLogger.w('Catalog sources profile hydrate failed', error: e, stackTrace: s);\n"
    "                    }),\n"
    "                  );",
    "                  if (!kFireTvNoExternalServices) {\n"
    "                    unawaited(\n"
    "                      provider.onActiveProfileChanged(activeId).catchError((Object e, StackTrace s) {\n"
    "                        appLogger.w('Catalog sources profile hydrate failed', error: e, stackTrace: s);\n"
    "                      }),\n"
    "                    );\n"
    "                  }",
)
replace_once(
    profile,
    "                  provider.update(trackers, seerr);\n"
    "                  unawaited(provider.onProfileBindingStateChanged(activeProfile.isBinding));",
    "                  if (!kFireTvNoExternalServices) {\n"
    "                    provider.update(trackers, seerr);\n"
    "                    unawaited(provider.onProfileBindingStateChanged(activeProfile.isBinding));\n"
    "                  }",
)

catalog = "lib/providers/catalog_sources_provider.dart"
replace_once(
    catalog,
    "import 'trackers_provider.dart';",
    "import 'trackers_provider.dart';\n"
    "import '../services/firetv_build_flags.dart';",
)
replace_once(
    catalog,
    "  List<CatalogSource> get connectedSources => [",
    "  List<CatalogSource> get connectedSources => kFireTvNoExternalServices ? const <CatalogSource>[] : [",
)
replace_once(
    catalog,
    "  SeerrCatalogSource? get seerrSource => _seerr.source;",
    "  SeerrCatalogSource? get seerrSource => kFireTvNoExternalServices ? null : _seerr.source;",
)

# Prohibit outbound realtime scrobbling and queued tracker writes even if a
# future application refactor accidentally starts the coordinator.
coordinator = "lib/services/trackers/tracker_coordinator.dart"
replace_once(
    coordinator,
    "import 'trakt/trakt_tracker.dart';",
    "import 'trakt/trakt_tracker.dart';\n"
    "import '../firetv_build_flags.dart';",
)
replace_once(
    coordinator,
    "  late final List<Tracker> _trackers = [",
    "  late final List<Tracker> _trackers = kFireTvNoExternalServices ? <Tracker>[] : [",
)

replace_once(
    coordinator,
    "  Future<void> flushWriteQueue() async {\n",
    "  Future<void> flushWriteQueue() async {\n"
    "    // Do not read/replay old external tracker writes in the appliance build.\n"
    "    if (kFireTvNoExternalServices) return;\n",
)

# Remove Services hub; it consists solely of services intentionally disabled
# in this Fire TV build, but preserve it for normal builds.
settings = "lib/screens/settings/settings_screen.dart"
replace_once(
    settings,
    "import '../../services/settings_service.dart' as settings;",
    "import '../../services/settings_service.dart' as settings;\n"
    "import '../../services/firetv_build_flags.dart';",
)
replace_once(
    settings,
    "                      _buildServicesTile(),",
    "                      if (!kFireTvNoExternalServices) _buildServicesTile(),",
)

# Disable the Seerr permission probe on every background-to-foreground resume.
main = "lib/screens/main_screen.dart"
# The Plex-only source overlay already imports firetv_build_flags.dart here.
replace_once(
    main,
    "    if (resumedFromBackground && mounted) {\n"
    "      unawaited(context.read<SeerrAccountProvider?>()?.refreshUser());\n"
    "    }",
    "    if (!kFireTvNoExternalServices && resumedFromBackground && mounted) {\n"
    "      unawaited(context.read<SeerrAccountProvider?>()?.refreshUser());\n"
    "    }",
)

test_files = {
    "test/services/firetv_external_services_appliance_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() {\n"
        "  test('movies and TV edition excludes cloud catalogs and trackers', () {\n"
        "    expect(kFireTvPlexOnly, isTrue);\n"
        "    expect(kFireTvMoviesTvOnly, isTrue);\n"
        "    expect(kFireTvNoExternalServices, isTrue);\n"
        "    expect(kFireTvForceExoVideo, isTrue);\n"
        "  });\n"
        "}\n"
    ),
    "test/services/firetv_external_services_default_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() {\n"
        "  test('default build retains external integrations', () {\n"
        "    expect(kFireTvNoExternalServices, isFalse);\n"
        "  });\n"
        "}\n"
    )
}
for name, body in test_files.items():
    path = Path(name)
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing test: {name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")

# Fail closed on the critical behavior contracts.
flag = flag_file.read_text(encoding="utf-8")
for name in ("kFireTvPlexOnly", "kFireTvMoviesTvOnly", "kFireTvNoExternalServices"):
    if flag.count(f"const bool {name}") != 1:
        raise SystemExit(f"Flag definition absent/duplicated: {name}")
if "DiscoverProvider(" not in Path(profile).read_text(encoding="utf-8"):
    raise SystemExit("Plex's local Home/Continue Watching provider was unexpectedly removed")
print("Phase 01 configured. Plex local Home remains; cloud Discover, tracker and Seerr hydration bypassed.")
print("NOT an APK, and NOT a proof that unreachable source was tree-shaken.")
