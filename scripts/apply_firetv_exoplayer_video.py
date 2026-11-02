#!/usr/bin/env python3
"""Stage B: force Android VIDEO onto ExoPlayer in an opt-in Fire TV build.

Run AFTER apply_firetv_plex_only.py against an exact, patched upstream Plezy
source checkout (initially 2.25.0). This is NOT an MPV-free build: the native
ExoPlayer plugin may still fallback to MPV and music still uses MPV. Removing
those dependencies is a separate, tested migration stage.

All exact source anchors must match once. Normal upstream/Windows builds have
the compile-time flag OFF and retain their existing backend selection.
"""
from pathlib import Path


def replace_one(path: str, before: str, after: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    n = text.count(before)
    if n != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {n}: {before[:110]!r}")
    if before == after:
        raise SystemExit(f"{path}: refusing unchanged replacement")
    target.write_text(text.replace(before, after), encoding="utf-8")
    print(f"Stage B: updated {path}")


flags = Path("lib/services/firetv_build_flags.dart")
if not flags.is_file():
    raise SystemExit("Run Stage A Plex-only overlay first; flag module is absent")
if "kFireTvForceExoVideo" in flags.read_text(encoding="utf-8"):
    raise SystemExit("ExoPlayer video flag already exists; review upstream before proceeding")
with flags.open("a", encoding="utf-8") as out:
    out.write(
        "\n/// Stage B: Fire TV video uses ExoPlayer regardless of saved backend preference.\n"
        "/// MPV is STILL packaged for native fallback and music until later stages.\n"
        "const bool kFireTvForceExoVideo =\n"
        "    bool.fromEnvironment('PLEZY_FIRETV_FORCE_EXO_VIDEO', defaultValue: false);\n"
        "\n/// Single shared choice for the Android video factory, setup and settings.\n"
        "bool useExoPlayerForAndroidVideo(bool savedPreference) =>\n"
        "    kFireTvForceExoVideo || savedPreference;\n"
    )

replace_one(
    "lib/mpv/player/player.dart",
    "import '../../models/audio_channel_limit.dart';",
    "import '../../models/audio_channel_limit.dart';\n"
    "import '../../services/firetv_build_flags.dart';",
)
replace_one(
    "lib/mpv/player/player.dart",
    "      final useExo = useExoPlayer ?? false;",
    "      final useExo = useExoPlayerForAndroidVideo(useExoPlayer ?? false);",
)

replace_one(
    "lib/screens/video_player_screen.dart",
    "import '../services/settings_service.dart';",
    "import '../services/settings_service.dart';\n"
    "import '../services/firetv_build_flags.dart';",
)
replace_one(
    "lib/screens/video_player_screen.dart",
    "      final useExoPlayer = settingsService.read(SettingsService.useExoPlayer);",
    "      final useExoPlayer = useExoPlayerForAndroidVideo(\n"
    "        settingsService.read(SettingsService.useExoPlayer),\n"
    "      );",
)

replace_one(
    "lib/screens/settings/playback_settings_screen.dart",
    "import '../../services/settings_service.dart';",
    "import '../../services/settings_service.dart';\n"
    "import '../../services/firetv_build_flags.dart';",
)
replace_one(
    "lib/screens/settings/playback_settings_screen.dart",
    "        final exoActive = Platform.isAndroid && svc.read(SettingsService.useExoPlayer);",
    "        final exoActive = Platform.isAndroid &&\n"
    "            useExoPlayerForAndroidVideo(svc.read(SettingsService.useExoPlayer));",
)
replace_one(
    "lib/screens/settings/playback_settings_screen.dart",
    "                if (Platform.isAndroid) _playerBackendSelector(),",
    "                // The appliance always uses ExoPlayer video: don't offer MPV.\n"
    "                if (Platform.isAndroid && !kFireTvForceExoVideo) _playerBackendSelector(),",
)

tests = {
    "test/services/firetv_exoplayer_video_flag_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() {\n"
        "  test('Fire TV candidate always chooses ExoPlayer for video', () {\n"
        "    expect(kFireTvPlexOnly, isTrue);\n"
        "    expect(kFireTvForceExoVideo, isTrue);\n"
        "    expect(useExoPlayerForAndroidVideo(false), isTrue);\n"
        "    expect(useExoPlayerForAndroidVideo(true), isTrue);\n"
        "  });\n"
        "}\n"
    ),
    "test/services/firetv_exoplayer_video_default_test.dart": (
        "import 'package:flutter_test/flutter_test.dart';\n"
        "import 'package:plezy/services/firetv_build_flags.dart';\n\n"
        "void main() {\n"
        "  test('normal builds preserve saved Android video backend preference', () {\n"
        "    expect(kFireTvForceExoVideo, isFalse);\n"
        "    expect(useExoPlayerForAndroidVideo(false), isFalse);\n"
        "    expect(useExoPlayerForAndroidVideo(true), isTrue);\n"
        "  });\n"
        "}\n"
    ),
}
for path, data in tests.items():
    dest = Path(path)
    if dest.exists():
        raise SystemExit(f"{path}: already exists; do not overwrite")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(data, encoding="utf-8")

# Fail closed on an upstream refactor that introduces a second Android Player
# factory or unguarded preference read in the video-startup implementation.
factory = Path("lib/mpv/player/player.dart").read_text(encoding="utf-8")
startup = Path("lib/screens/video_player_screen.dart").read_text(encoding="utf-8")
settings = Path("lib/screens/settings/playback_settings_screen.dart").read_text(encoding="utf-8")
for file, data, marker in (
    ("lib/mpv/player/player.dart", factory, "useExoPlayerForAndroidVideo(useExoPlayer ?? false)"),
    ("lib/screens/video_player_screen.dart", startup, "final useExoPlayer = useExoPlayerForAndroidVideo("),
    ("lib/screens/settings/playback_settings_screen.dart", settings, "final exoActive = Platform.isAndroid &&"),
):
    if data.count(marker) != 1:
        raise SystemExit(f"{file}: expected one guarded ExoPlayer branch")
print("Stage B overlay ready. Native MPV fallback and MPV music are STILL present.")
