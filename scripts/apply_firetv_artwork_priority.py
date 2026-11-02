#!/usr/bin/env python3
"""Stage 10: favor on-screen art over speculative Plex library precaching.
Pinned upstream 2.25.0. Only Fire TV movie/TV appliance changes behavior.
"""
from pathlib import Path
p=Path("lib/screens/libraries/tabs/library_browse_tab.dart")
s=p.read_text(encoding="utf-8")
def once(a,b):
    global s
    if s.count(a)!=1:
        raise SystemExit(f"Artwork source changed, {s.count(a)} anchors: {a[:100]!r}")
    s=s.replace(a,b)
once("import '../../../services/storage_service.dart';",
     "import '../../../services/storage_service.dart';\n"
     "import '../../../services/device_performance.dart';")
# Earlier movies/TV overlay already imports Fire TV flags via main screen,
# not directly into library browsing.
once("import '../../../services/device_performance.dart';",
     "import '../../../services/device_performance.dart';\n"
     "import '../../../services/firetv_build_flags.dart';")
once("    // Prefetch 2 rows beyond visible area\n"
     "    final prefetchEnd = visibleEnd + 2 * _scrollMetrics.columnCount;",
     "    // On the appliance the visible cards already request their own images.\n"
     "    // Give those requests priority by queuing speculative art ONLY offscreen.\n"
     "    // Limit Lite devices to one future row and a few in-flight requests.\n"
     "    final appliance = kFireTvMoviesTvOnly;\n"
     "    final reduced = DevicePerformance.isReduced;\n"
     "    final speculativeRows = appliance && reduced ? 1 : 2;\n"
     "    final speculativeLimit = appliance ? (reduced ? 3 : 6) : items.length;\n"
     "    final prefetchEnd = visibleEnd + speculativeRows * _scrollMetrics.columnCount;\n"
     "    var speculativeQueued = 0;")
once("      if (index < firstVisible || index > prefetchEnd) continue;",
     "      if (index < firstVisible || index > prefetchEnd) continue;\n"
     "      if (appliance && (index < visibleEnd || speculativeQueued >= speculativeLimit)) continue;")
once("      precacheImage(\n"
     "        MediaImageHelper.serverArtworkProvider(imageUrl: imageUrl, memWidth: memWidth, memHeight: memHeight),\n"
     "        context,\n"
     "      ).ignore();",
     "      precacheImage(\n"
     "        MediaImageHelper.serverArtworkProvider(imageUrl: imageUrl, memWidth: memWidth, memHeight: memHeight),\n"
     "        context,\n"
     "      ).ignore();\n"
     "      speculativeQueued++;")
p.write_text(s, encoding="utf-8")
print("Artwork: visible cards now outrank bounded offscreen speculative preload in Fire TV edition.")
print("No claims about byte savings or HTTP queue priorities until benchmarked.")
