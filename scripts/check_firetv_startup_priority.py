#!/usr/bin/env python3
from pathlib import Path
main=Path("lib/main.dart").read_text(encoding="utf-8")
screen=Path("lib/screens/main_screen.dart").read_text(encoding="utf-8")
required=[
    ("main.dart", main, "if (!kFireTvNoExternalServices) {"),
    ("main.dart", main, "bestEffort('Trackers', TrackerCoordinator.instance.initialize);"),
    ("MainScreen", screen, "if (PlatformDetector.isTV() && !kFireTvMoviesTvOnly) {"),
    ("MainScreen", screen, "if (mounted) warmUpTvVirtualKeyboardText(context);"),
    ("MainScreen", screen, "_attachDeepLinks();"),
    ("MainScreen", screen, "ensureActiveLoaded()"),
]
for label, body, snippet in required:
    if snippet not in body:
        raise SystemExit(f"Startup source guard missing in {label}: {snippet}")
print("Startup-priority source audit passed; no benchmarks or APK build were run.")
