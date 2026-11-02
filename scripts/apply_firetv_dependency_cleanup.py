#!/usr/bin/env python3
"""Stage 14: prune disabled third-party branding assets from Flutter bundle.

Remove ONLY explicitly listed unused feature artwork declarations; keep
original source artwork and all codec, subtitles, native, or Flutter plugins.
OpenWatchParty is not safely removable until shared types are eliminated.
"""
from pathlib import Path
p=Path("pubspec.yaml");s=p.read_text(encoding="utf-8")
for asset in ("jellyfin_icon.svg","trakt_circlemark.svg","mal_mark.svg","anilist_mark.svg","simkl_mark.svg"):
    marker=f"    - assets/{asset}\n"
    if s.count(marker)!=1: raise SystemExit(f"Missing/excess asset declaration {asset}")
    s=s.replace(marker,"")
if "  openwatchparty: ^1.1.0" not in s:
    raise SystemExit("Watch Together shared package changed; review before dependency pruning")
if "dart_discord_presence" in s:
    raise SystemExit("Stage 02 Discord IPC dependency still present")
p.write_text(s,encoding="utf-8")
print("Five inactive backend/service SVGs removed from Flutter asset bundle declaration.")
print("Retain codecs, movie/TV audio and OpenWatchParty until type-reference audit.")
