#!/usr/bin/env python3
from pathlib import Path
s=Path("lib/services/device_performance.dart").read_text(encoding="utf-8")
for t in ("cache.maximumSize = kFireTvMoviesTvOnly ? 300 : 400;", "kFireTvMoviesTvOnly ? 48 << 20 : 64 << 20", "cache.maximumSize = kFireTvMoviesTvOnly ? 400 : 500;", "math.min(existingBudget, 96 << 20)", "Skia.setResourceCacheMaxBytes"):
    if t not in s: raise SystemExit("Missing memory guard: "+t)
print("Memory cache source policy checked, runtime pressure not measured.")
