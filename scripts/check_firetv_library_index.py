#!/usr/bin/env python3
from pathlib import Path
s=Path("lib/screens/libraries/tabs/library_browse_tab.dart").read_text(encoding="utf-8")
checks=(
    "final loadedIndexSnapshot = <String, int>{",
    "for (final entry in loadedItems.entries) entry.value.id: entry.key,",
    "final index = loadedIndexSnapshot[id];",
    "if (index != null && loadedItems[index]?.id == id) return index;",
    "return _loadedIndexOfId(id);",
)
for needle in checks:
    if s.count(needle) != 1:
        raise SystemExit(f"Browse index snapshot missing or duplicated: {needle!r}")
print("Browse index source guard passed. No Flutter build or frame benchmark executed.")
