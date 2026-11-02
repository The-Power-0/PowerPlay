#!/usr/bin/env python3
from pathlib import Path
s=Path("pubspec.yaml").read_text(encoding="utf-8")
for name in ("jellyfin_icon.svg","trakt_circlemark.svg","mal_mark.svg","anilist_mark.svg","simkl_mark.svg"):
    if "    - assets/"+name in s: raise SystemExit("Inactive feature asset bundled: "+name)
for name in ("openwatchparty: ^1.1.0","assets/","flutter:"):
    if name not in s: raise SystemExit("Essential source/package anchor missing: "+name)
if "dart_discord_presence:" in s: raise SystemExit("Discord dependency retained")
print("Explicit unused asset declarations excluded; complete dependency graph awaits compilation.")
