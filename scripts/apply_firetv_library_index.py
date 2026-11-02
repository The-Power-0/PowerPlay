#!/usr/bin/env python3
"""Optimize Flutter sparse Plex browse-grid key lookup; preserves fallback.

This is a source patch only, run on exact 2.25.0 after stages 01-04.
The immutable index snapshot is built once per sliver update instead of
linearly scanning every loaded MediaItem for each key reordering lookup.
Asynchronous mid-frame mutations use a checked linear fallback.
"""
from pathlib import Path

p = Path("lib/screens/libraries/tabs/library_browse_tab.dart")
s = p.read_text(encoding="utf-8")

def replace(a,b):
    global s
    if s.count(a) != 1:
        raise SystemExit(f"library browse refactored; expected 1 anchor got {s.count(a)}: {a[:100]!r}")
    s = s.replace(a,b)

replace(
    "    final hasAlphaBarReservation = rightPadding > 8.0;\n"
    "    return MediaCardSliverLayout(",
    "    final hasAlphaBarReservation = rightPadding > 8.0;\n"
    "    // One map per sliver rebuild, not an O(loadedItems.length) search for\n"
    "    // every Flutter key-reconciliation call during D-pad scrolling.\n"
    "    final loadedIndexSnapshot = <String, int>{\n"
    "      for (final entry in loadedItems.entries) entry.value.id: entry.key,\n"
    "    };\n"
    "    return MediaCardSliverLayout(",
)
replace(
    "      findChildIndexCallback: (key) => _loadedIndexOfId((key as ValueKey<String>).value),",
    "      findChildIndexCallback: (key) {\n"
    "        final id = (key as ValueKey<String>).value;\n"
    "        final index = loadedIndexSnapshot[id];\n"
    "        if (index != null && loadedItems[index]?.id == id) return index;\n"
    "        // A live library refresh can mutate the sparse map between frames;\n"
    "        // never return a stale index merely because the map's size matches.\n"
    "        return _loadedIndexOfId(id);\n"
    "      },",
)
p.write_text(s, encoding="utf-8")
if s.count("loadedIndexSnapshot") != 2 or "return _loadedIndexOfId(id);" not in s:
    raise SystemExit("Index snapshot invariant failed")
print("Library key lookup uses O(1) snapshot with stale-item correctness fallback.")
print("No APK built, no performance gain claimed until device benchmarks.")
