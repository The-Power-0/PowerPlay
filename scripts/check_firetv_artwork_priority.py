#!/usr/bin/env python3
from pathlib import Path
s=Path("lib/screens/libraries/tabs/library_browse_tab.dart").read_text(encoding="utf-8")
for x in ("final appliance = kFireTvMoviesTvOnly;", "final reduced = DevicePerformance.isReduced;", "final speculativeLimit = appliance ? (reduced ? 3 : 6) : items.length;", "if (appliance && (index < visibleEnd || speculativeQueued >= speculativeLimit)) continue;", "speculativeQueued++;"):
    if s.count(x) != 1: raise SystemExit("Artwork priority source guard failed: "+x)
print("Artwork prefetch source guard passed; real device/network tests pending.")
