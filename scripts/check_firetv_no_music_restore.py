#!/usr/bin/env python3
from pathlib import Path
s=Path("lib/navigation/profile_session_screen.dart").read_text(encoding="utf-8")
for x in ("sessionStore: kFireTvMoviesTvOnly || activeId == null",
          "MusicPlaybackServiceImpl(", "ChangeNotifierProvider<MusicPlaybackService>("):
    if s.count(x)!=1:
        raise SystemExit("Unexpected music service structure: "+x)
if "MusicSessionStore(database: context.read<AppDatabase>(), profileId: activeId)" not in s:
    raise SystemExit("Normal Plezy music restore unexpectedly removed")
print("Movie/TV build has no saved music restore; shared service interface intact.")
