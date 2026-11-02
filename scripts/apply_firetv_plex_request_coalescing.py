#!/usr/bin/env python3
"""Stage 11: combine concurrent read-only Plex server preference fetches.

No caching across completed requests: every subsequent refresh still reaches
Plex and retains existing watched-threshold semantics.
"""
from pathlib import Path
p=Path("lib/services/plex_client.dart")
s=p.read_text(encoding="utf-8")
a="  Future<void> fetchServerPrefs() async {\n"
b=("  // Multiple connect/resume observers can request the same read concurrently.\n"
   "  // Coalesce only in flight, not across refresh cycles or Plex profiles.\n"
   "  Future<void>? _pendingServerPrefs;\n\n"
   "  Future<void> fetchServerPrefs() {\n"
   "    return _pendingServerPrefs ??= _fetchServerPrefsOnce().whenComplete(() {\n"
   "      _pendingServerPrefs = null;\n"
   "    });\n"
   "  }\n\n"
   "  Future<void> _fetchServerPrefsOnce() async {\n")
if s.count(a)!=1: raise SystemExit("Unexpected server preferences method")
s=s.replace(a,b)
p.write_text(s, encoding="utf-8")
print("Concurrent server-pref reads share one in-flight future; subsequent calls still refresh.")
