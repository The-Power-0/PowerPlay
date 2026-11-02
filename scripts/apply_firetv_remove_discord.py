#!/usr/bin/env python3
"""Phase 02: remove Discord Rich Presence from custom Plex Fire TV checkout.

Run after phase 01 and the no-MPV movies-and-TV overlays on pinned Plezy 2.25.0.
Deletes desktop RPC implementation, Dart dependency, hot-path callbacks and
target-specific tests. Regular Plezy/Windows sources are not modified.
All source replacements fail closed on changed upstream anchors.
"""
from pathlib import Path


def change(path: str, before: str, after: str = "") -> None:
    file = Path(path)
    original = file.read_text(encoding="utf-8")
    occurrences = original.count(before)
    if occurrences != 1:
        raise SystemExit(f"{path}: expected one matching anchor, found {occurrences}: {before[:90]!r}")
    file.write_text(original.replace(before, after), encoding="utf-8")
    print(f"Discord removal: updated {path}")


def remove_line(path: str, line: str) -> None:
    change(path, line + "\n")


def delete_file(path: str) -> None:
    f = Path(path)
    if not f.is_file():
        raise SystemExit(f"Discord removal: file absent, review upstream: {path}")
    f.unlink()
    print(f"Discord removal: deleted {path}")


if "kFireTvNoExternalServices" not in Path("lib/services/firetv_build_flags.dart").read_text():
    raise SystemExit("Phase 01 external-service overlay must run before Discord removal")

# Stop bundling the desktop IPC package into the target pubspec/lockfile.
change(
    "pubspec.yaml",
    "  # 1.2.1: Windows IPC no longer blocks the UI isolate while Discord stalls (#2518).\n"
    "  dart_discord_presence: ^1.2.1\n",
)

main = "lib/main.dart"
remove_line(main, "import 'services/discord_rpc_service.dart';")
remove_line(main, "    bestEffort('Discord RPC', DiscordRPCService.instance.initialize);")
change(
    main,
    "      // Discord RPC errors when Discord is not running\n"
    "      if (e.type == 'DiscordStateException') return true;\n",
)

video = "lib/screens/video_player_screen.dart"
remove_line(video, "import '../services/discord_rpc_service.dart';")
remove_line(video, "    DiscordRPCService.instance.stopPlayback();")

services = "lib/screens/video_player/parts/playback_services.dart"
change(
    services,
    "        await Future.wait<void>([\n"
    "          DiscordRPCService.instance.stopPlayback(),\n"
    "          TrackerCoordinator.instance.stopPlayback(),\n"
    "        ]);",
    "        await TrackerCoordinator.instance.stopPlayback();",
)
change(
    services,
    "    // Scrobblers — Discord RPC plus the tracker coordinator, which fans out to\n"
    "    // every connected service. Both accept the neutral [MediaServerClient]; null\n"
    "    // short-circuits cleanly.\n"
    "    if (mediaClient != null) {\n"
    "      // Discord renders a timeline the live placeholder does not have; the\n"
    "      // tracker coordinator takes the live decision itself.\n"
    "      if (!widget.isLive) {\n"
    "        unawaited(DiscordRPCService.instance.startPlayback(metadata, mediaClient));\n"
    "      }\n"
    "      unawaited(TrackerCoordinator.instance.startPlayback(metadata, mediaClient, isLive: widget.isLive));\n"
    "    }",
    "    // Plex progress is tracked locally; the third-party tracker coordinator\n"
    "    // is disabled by phase 01 in this appliance build.\n"
    "    if (mediaClient != null) {\n"
    "      unawaited(TrackerCoordinator.instance.startPlayback(metadata, mediaClient, isLive: widget.isLive));\n"
    "    }",
)
remove_line(services, "        DiscordRPCService.instance.updatePosition(position);")
change(
    services,
    "    if (!widget.isLive) {\n"
    "      // Listen to playback rate changes for Discord Rich Presence\n"
    "      _mediaControlSubscriptions.add(\n"
    "        currentPlayer.streams.rate.listen((rate) {\n"
    "          DiscordRPCService.instance.updatePlaybackSpeed(rate);\n"
    "        }),\n"
    "      );\n"
    "    }\n\n",
)
remove_line(services, "      DiscordRPCService.instance.resumePlayback();")
remove_line(services, "      DiscordRPCService.instance.pausePlayback();")

prompts = "lib/screens/video_player/parts/playback_prompts.dart"
remove_line(prompts, "    unawaited(DiscordRPCService.instance.pausePlayback());")
reload = "lib/screens/video_player/parts/playback_reload.dart"
remove_line(reload, "            unawaited(DiscordRPCService.instance.stopPlayback());")

music = "lib/services/music/music_playback_service_impl.dart"
remove_line(music, "import '../discord_rpc_service.dart';")
remove_line(music, "    DiscordRPCService.instance.updatePosition(position);")
change(
    music,
    "      // Gated like the tracker: while an open is loading, the player's\n"
    "      // playing flips belong to a track whose presence is not bound yet.\n"
    "      final rpc = DiscordRPCService.instance;\n"
    "      unawaited(shouldBePlaying ? rpc.resumePlayback() : rpc.pausePlayback());\n",
)
remove_line(music, "    unawaited(DiscordRPCService.instance.pausePlayback());")
change(
    music,
    "    if (metadataClient != null) {\n"
    "      final rpc = DiscordRPCService.instance;\n"
    "      unawaited(rpc.startPlayback(track, metadataClient));\n"
    "      // Callers set [_status] before binding; a restored session or a\n"
    "      // car-restricted open binds paused, and presence must not run a\n"
    "      // timer for a track that is not audible.\n"
    "      if (_status != MusicPlaybackStatus.playing) unawaited(rpc.pausePlayback());\n"
    "    }\n",
)
remove_line(music, "    unawaited(DiscordRPCService.instance.stopPlayback());")
change(
    music,
    "  /// Discord presence — the music mirror of the video screen's",
    "  /// media control metadata — the music mirror of the video screen's",
)

mutations = "lib/services/settings_mutation_service.dart"
remove_line(mutations, "import 'discord_rpc_service.dart';")
change(
    mutations,
    "    _SettingsEffect(\n"
    "      SettingsService.enableDiscordRPC,\n"
    "      (_, settings, _) => DiscordRPCService.instance.setEnabled(settings.read(SettingsService.enableDiscordRPC)),\n"
    "    ),\n",
)

services_ui = "lib/screens/settings/services_settings_screen.dart"
remove_line(services_ui, "import '../../services/discord_rpc_service.dart';")
remove_line(services_ui, "import '../../services/settings_service.dart';")
remove_line(services_ui, "import '../../widgets/setting_tile.dart';")
change(
    services_ui,
    "            if (DiscordRPCService.isAvailable)\n"
    "              SettingsGroup(\n"
    "                title: t.services.integrations,\n"
    "                children: [\n"
    "                  SettingSwitchTile(\n"
    "                    pref: SettingsService.enableDiscordRPC,\n"
    "                    icon: Symbols.chat_rounded,\n"
    "                    title: t.settings.discordRichPresence,\n"
    "                    subtitle: t.settings.discordRichPresenceDescription,\n"
    "                  ),\n"
    "                ],\n"
    "              ),\n",
)
# This settings file is retained for standard application routes; the
# complete Services hub was hidden in the phase 01 appliance overlay.

agent = "lib/services/agent_settings_commands.dart"
remove_line(agent, "import 'discord_rpc_service.dart';")
change(
    agent,
    "      case 'enable_discord_rpc':\n"
    "        if (!DiscordRPCService.isAvailable) return 'Discord rich presence is unavailable on this platform.';",
    "      case 'enable_discord_rpc':\n"
    "        return 'Discord Rich Presence is removed from the Plex Fire TV edition.';",
)
change(
    agent,
    "    if (key == 'enable_discord_rpc') {\n"
    "      final owner = DiscordRPCService.instance;\n"
    "      runtime.addAll({\n"
    "        'enabled': owner.isEnabled,\n"
    "        'connected': owner.isConnected,\n"
    "        'state': owner.isEnabled && !owner.isConnected ? 'waitingForDiscord' : 'applied',\n"
    "      });\n"
    "    }\n",
)

# Keep the obsolete BoolPref key to avoid changing the settings schema or
# losing compatibility if this profile is later opened in standard Plezy.
# That key has no initialization, network, settings UI, or native side effect.

# Tests of a deleted feature cannot remain; preserve all non-Discord music
# service test cases. Remove ONLY the two Discord-presence tests in that file.
music_test = "test/services/music/music_playback_service_test.dart"
remove_line(music_test, "import 'package:dart_discord_presence/dart_discord_presence.dart';")
remove_line(music_test, "import 'package:plezy/services/discord_rpc_service.dart';")
remove_line(music_test, "import '../../test_helpers/discord_rpc_fakes.dart';")
music_test_source = Path(music_test).read_text(encoding="utf-8")
start_marker = "  group('Discord presence', () {\n"
end_marker = "  group('session restore (#2148)', () {\n"
if music_test_source.count(start_marker) != 1 or music_test_source.count(end_marker) != 1:
    raise SystemExit("Music integration test group structure changed")
start = music_test_source.index(start_marker)
end = music_test_source.index(end_marker, start)
excluded = music_test_source[start:end]
if excluded.count("test(") != 2 or "    });\n  });\n" not in excluded:
    raise SystemExit("Refusing to remove unexpected non-Discord music tests")
Path(music_test).write_text(music_test_source[:start] + music_test_source[end:], encoding="utf-8")

# The fixed-endpoint scan lists all active source files explicitly.
change(
    "test/android/network_security_config_test.dart",
    "  'lib/services/discord_rpc_service.dart',\n",
)

delete_file("lib/services/discord_rpc_service.dart")
delete_file("test/services/discord_rpc_service_test.dart")
delete_file("test/test_helpers/discord_rpc_fakes.dart")

# Do not silently leave Discord RPC in any runtime source after pruning.
remaining = []
for file in Path("lib").rglob("*.dart"):
    src = file.read_text(encoding="utf-8")
    if "DiscordRPCService" in src or "dart_discord_presence" in src:
        remaining.append(str(file))
if remaining:
    raise SystemExit("Discord runtime still referenced in: " + ", ".join(remaining))

print("Stage 02: Discord desktop IPC, callbacks, dependency and tests removed.")
print("Not yet compiled; no APK built, no Fire TV installed.")
