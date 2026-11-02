#!/usr/bin/env python3
"""Source-only verification of Discord removal from the Fire TV appliance.

Must run after apply_firetv_remove_discord.py. Does not compile Dart or produce
APK and does not measure performance.
"""
from pathlib import Path


def must(condition: bool, description: str) -> None:
    if not condition:
        raise SystemExit("NO-DISCORD SOURCE CHECK FAILED: " + description)


for path in (
    "lib/services/discord_rpc_service.dart",
    "test/services/discord_rpc_service_test.dart",
    "test/test_helpers/discord_rpc_fakes.dart",
):
    must(not Path(path).exists(), f"Discord-only file still exists: {path}")

pubspec = Path("pubspec.yaml").read_text(encoding="utf-8")
must("dart_discord_presence:" not in pubspec, "Discord IPC dependency still declared")

for file in Path("lib").rglob("*.dart"):
    text = file.read_text(encoding="utf-8")
    for bad in ("DiscordRPCService", "dart_discord_presence", "discord_rpc_service.dart"):
        must(bad not in text, f"Discord RPC runtime reference in {file}: {bad}")

for file in Path("test").rglob("*.dart"):
    text = file.read_text(encoding="utf-8")
    must("package:dart_discord_presence/" not in text, f"Discord test dependency in {file}")

video = Path("lib/screens/video_player/parts/playback_services.dart").read_text(encoding="utf-8")
must("TrackerCoordinator.instance.startPlayback(" in video, "Trackers seam unexpectedly removed")
must("_rebindProgressTracker(" in video, "Plex's own progress tracking removed")
must("currentPlayer.streams.rate.listen" not in video, "Discord-only rate subscription retained")

main = Path("lib/main.dart").read_text(encoding="utf-8")
must("bestEffort('Discord RPC'" not in main, "Discord startup initializer retained")
settings = Path("lib/services/settings_service.dart").read_text(encoding="utf-8")
must("static const enableDiscordRPC" in settings, "Persisted preference compatibility removed")

music = Path("test/services/music/music_playback_service_test.dart").read_text(encoding="utf-8")
must("group('session restore (#2148)'" in music, "Non-Discord music test group removed")
must("group('Discord presence'" not in music, "Discord-only music tests retained")

config_test = Path("test/android/network_security_config_test.dart").read_text(encoding="utf-8")
must("  'lib/services/discord_rpc_service.dart'," not in config_test, "TLS scan references deleted source")
print("Phase 02 source audit passed: no Discord RPC runtime or IPC package references.")
print("No Android build, native tests, APK inspection or device testing performed.")
