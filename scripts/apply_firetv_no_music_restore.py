#!/usr/bin/env python3
"""Stage 08: no background music-session restore in the movie/TV appliance.

Video shares the MusicPlaybackService type for audio-focus arbitration; its
provider must remain, but no saved music session should reopen MPV audio.
Source-only change for pinned 2.25.0.
"""
from pathlib import Path
p=Path("lib/navigation/profile_session_screen.dart")
s=p.read_text(encoding="utf-8")
old = ("                  sessionStore: activeId == null\n"
       "                      ? null\n"
       "                      : MusicSessionStore(database: context.read<AppDatabase>(), profileId: activeId),")
new = ("                  // This movies/TV edition does not restore stale Plex music.\n"
       "                  // Keep the service interface for video audio-focus ownership.\n"
       "                  sessionStore: kFireTvMoviesTvOnly || activeId == null\n"
       "                      ? null\n"
       "                      : MusicSessionStore(database: context.read<AppDatabase>(), profileId: activeId),")
if s.count(old)!=1:
    raise SystemExit(f"Profile music session store layout unexpected: {s.count(old)}")
if "kFireTvMoviesTvOnly" not in s:
    raise SystemExit("Earlier movies/TV overlay missing")
p.write_text(s.replace(old,new),encoding="utf-8")
print("Music restore disabled for appliance; video media-focus arbitration preserved.")
print("No APK built; runtime behavior still requires a later candidate test.")
