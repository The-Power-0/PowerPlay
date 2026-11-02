#!/usr/bin/env python3
from pathlib import Path
s=Path("lib/services/plex_client.dart").read_text(encoding="utf-8")
for x in ("Future<void>? _pendingServerPrefs;", "return _pendingServerPrefs ??= _fetchServerPrefsOnce().whenComplete(() {", "_pendingServerPrefs = null;", "Future<void> _fetchServerPrefsOnce() async {", "_getWithFailover('/:/prefs')"):
    if s.count(x)!=1: raise SystemExit("Plex server-pref single-flight missing: "+x)
print("Plex preference request coalescing source audit passed.")
