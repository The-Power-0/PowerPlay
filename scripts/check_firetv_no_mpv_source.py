#!/usr/bin/env python3
"""Fail-closed PRE-BUILD source audit of an exact, patched Fire TV checkout.

Checks the Android player-only runtime, Dart appliance flags and shared code.
Not a compiler and not an APK test: a successful run is only source evidence.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

CHECKS = 0

def require(condition: bool, detail: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        raise SystemExit("NO-MPV SOURCE AUDIT FAILED: " + detail)


def source(path: str) -> str:
    p = Path(path)
    require(p.is_file(), "Required source missing: " + path)
    return p.read_text(encoding="utf-8")


def must_not_exist(path: str) -> None:
    require(not Path(path).exists(), "MPV-only source unexpectedly present: " + path)


for item in (
    "android/app/src/main/kotlin/com/edde746/plezy/mpv",
    "android/app/src/main/kotlin/com/edde746/plezy/shared/MpvContentUriResolver.kt",
    "android/app/src/main/kotlin/com/edde746/plezy/shared/GlCapabilities.kt",
    "android/app/src/debug/kotlin/com/edde746/plezy/mpv",
    "android/app/src/androidTest/kotlin/com/edde746/plezy/mpv",
    "android/app/src/androidTestDebug/kotlin/com/edde746/plezy/mpv",
    "android/app/src/test/kotlin/com/edde746/plezy/shared/MpvContentUriResolverTest.kt",
):
    must_not_exist(item)

native = Path("android/app/src/main/kotlin")
imports = []
for f in native.rglob("*.kt"):
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if re.search(r"^\s*import\s+(?:com\.edde746\.plezy\.mpv|com\.edde746\.mpv)\b", line):
            imports.append(f"{f}:{n}:{line.strip()}")
require(not imports, "Deleted Kotlin player imported from: " + "; ".join(imports))

activity = source("android/app/src/main/kotlin/com/edde746/plezy/PlezyActivity.kt")
require("flutterEngine.plugins.add(ExoPlayerPlugin())" in activity, "Media3 plugin not registered")
require(not re.search(r"\bMpv(?:Audio)?PlayerPlugin\b", activity), "MPV plugin still registered")

bridge = source("android/app/src/main/kotlin/com/edde746/plezy/exoplayer/ExoPlayerPlugin.kt")
require("class ExoPlayerPlugin" in bridge, "Missing dedicated ExoPlayer bridge")
require('result.success("exoplayer")' in bridge, "ExoPlayer backend identity not locked")
require("override fun onFormatUnsupported(" in bridge, "Unsupported codec error callback missing")
require(re.search(r"override fun onFormatUnsupported\([\s\S]*?\)\s*:\s*Boolean\s*\{[\s\S]*?return false", bridge) is not None, "Unsupported format not terminal")
for name in ("MpvPlayerCore", "usingMpvFallback", "MpvPlayerPlugin", "MpvAudioPlayerPlugin"):
    require(name not in bridge, f"Bridge still references MPV: {name}")

core = source("android/app/src/main/kotlin/com/edde746/plezy/exoplayer/ExoPlayerCore.kt")
require("fun triggerFallback()" not in core, "MPV trigger remains in Media3 core")
require("private fun requestFormatFallback(" in core, "Core codec errors no longer forwarded")
require("emitPlaybackErrorOnce(mediaGeneration, errorMessage)" in core, "Single terminal error path removed")

surface = source("android/app/src/main/kotlin/com/edde746/plezy/shared/PlayerSurfaceHost.kt")
require("createVideoSurface(" in surface and "attachToContent(" in surface, "Media3 video surface broken")
require("createOsdSurface(" not in surface, "MPV-only OSD surface still present")

gradle = source("android/app/build.gradle.kts")
require("implementation(mpvAarDependency)" not in gradle, "Full MPV AAR still links into APK")
require("mpvAarNatives(mpvAarDependency)" in gradle, "Media3 FFmpeg build-only input unexpectedly missing")
require("libavcodec.so" in gradle and "libswresample.so" in gradle, "Media3 FFmpeg libraries not extracted")
require("libc++_shared.so" in gradle, "Required shared C++ runtime missing")

flag = source("lib/services/firetv_build_flags.dart")
for name in ("kFireTvPlexOnly", "kFireTvForceExoVideo", "kFireTvMoviesTvOnly"):
    require(name in flag, "Required Fire TV flag missing: " + name)
dart_player = source("lib/mpv/player/player.dart")
require("useExoPlayerForAndroidVideo(useExoPlayer ?? false)" in dart_player, "Android video factory not forced to Media3")
require("if (Platform.isAndroid && kFireTvMoviesTvOnly)" in dart_player, "Audio-only MPV creation not blocked")
player_android = source("lib/mpv/player/platform/player_android.dart")
require("_usingMpvFallback" not in player_android, "Dart Media3 bridge still contains MPV fallback state")

library_provider = source("lib/providers/libraries_provider.dart")
require("!library.kind.isMusic" in library_provider and "kFireTvMoviesTvOnly" in library_provider, "Music libraries not filtered")

print(f"No-MPV source audit passed: {CHECKS} checks.")
print("This does not verify compilation, ABI, native binary contents, audio codecs or on-device behavior.")
