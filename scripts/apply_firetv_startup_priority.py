#!/usr/bin/env python3
"""Stage 06: prioritize immediate Plex/HA playback over unused warmup work.

Source only, pinned upstream 2.25.0 after feature-removal stages.
No changes to required Plex auth, startup gates, image cache budget, font
localization, hardware codec initialization or deep-link handling.
"""
from pathlib import Path

def once(path: str, old: str, new: str) -> None:
    p=Path(path); s=p.read_text(encoding="utf-8")
    if s.count(old)!=1:
        raise SystemExit(f"{path}: expected 1 anchor got {s.count(old)}: {old[:85]!r}")
    p.write_text(s.replace(old,new),encoding="utf-8")

flag=Path("lib/services/firetv_build_flags.dart")
if "kFireTvNoCompanionRemote" not in flag.read_text(encoding="utf-8"):
    raise SystemExit("Previous stages missing")
# Tracker startup is already useless: Stage 01 has zero outbound trackers and
# blocks persisted queue replay. Do not even hydrate the coordinator at first
# frame in this appliance, to free CPU and I/O for the HA deep-link start.
once("lib/main.dart",
     "  bestEffort('Trackers', TrackerCoordinator.instance.initialize);",
     "  if (!kFireTvNoExternalServices) {\n"
     "    bestEffort('Trackers', TrackerCoordinator.instance.initialize);\n"
     "  }")

# TV virtual keyboard font/layout warmup runs 3 seconds after the app begins
# and can fight first video decoder setup during HA shuffle cold-launch.
# Trade-off: first manual search can incur the original cold keyboard cost.
# Keep it on normal Plezy, omit only on the dedicated appliance.
once("lib/screens/main_screen.dart",
     "    if (PlatformDetector.isTV()) {\n"
     "      WidgetsBinding.instance.addPostFrameCallback((_) {\n"
     "        Future.delayed(const Duration(seconds: 3), () {\n"
     "          if (mounted) warmUpTvVirtualKeyboardText(context);\n"
     "        });\n"
     "      });\n"
     "    }",
     "    if (PlatformDetector.isTV() && !kFireTvMoviesTvOnly) {\n"
     "      WidgetsBinding.instance.addPostFrameCallback((_) {\n"
     "        Future.delayed(const Duration(seconds: 3), () {\n"
     "          if (mounted) warmUpTvVirtualKeyboardText(context);\n"
     "        });\n"
     "      });\n"
     "    }")

# Do not remove DownloadManager recovery, PlexHome binder, auth gate or
# image cache setup; those have correctness dependencies before playback.
print("Stage 06: skipped disabled third-party tracker bootstrap and deferred TV keyboard warmup.")
print("No time savings claimed without cold-start/first-frame benchmark on Fire Sticks.")
