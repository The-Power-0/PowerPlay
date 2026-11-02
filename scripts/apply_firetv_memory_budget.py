#!/usr/bin/env python3
"""Stage 13: leave more RAM headroom for Media3 on 32-bit Fire TV devices.

Keep upstream device-tier detection, pixel decode scaling and GPU policy.
Only cap Flutter's resident image-cache budget for movies/TV build.
"""
from pathlib import Path
p=Path("lib/services/device_performance.dart");s=p.read_text(encoding="utf-8")
a="import '../utils/platform_detector.dart';"
b=a+"\nimport 'firetv_build_flags.dart';"
if s.count(a)!=1:raise SystemExit("Missing import")
s=s.replace(a,b)
a="      cache.maximumSize = 400;\n      cache.maximumSizeBytes = 64 << 20; // 64MB"
b="      cache.maximumSize = kFireTvMoviesTvOnly ? 300 : 400;\n      cache.maximumSizeBytes = kFireTvMoviesTvOnly ? 48 << 20 : 64 << 20; // Fire TV video headroom"
if s.count(a)!=1:raise SystemExit("Reduced-tier budget changed")
s=s.replace(a,b)
a="      cache.maximumSize = 500;\n      cache.maximumSizeBytes = ((64 << 20) * displayBudgetFactor()).round();"
b="      cache.maximumSize = kFireTvMoviesTvOnly ? 400 : 500;\n      final existingBudget = ((64 << 20) * displayBudgetFactor()).round();\n      cache.maximumSizeBytes = kFireTvMoviesTvOnly ? math.min(existingBudget, 96 << 20) : existingBudget;"
if s.count(a)!=1:raise SystemExit("Full-tier budget changed")
s=s.replace(a,b)
p.write_text(s,encoding="utf-8")
print("Fire TV image-cache budget capped; native decoder and display pixel quality unchanged.")
