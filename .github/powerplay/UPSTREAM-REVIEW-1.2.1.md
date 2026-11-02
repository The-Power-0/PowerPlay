# PowerPlay 1.2.1 upstream adoption audit

The actual **PowerPlay 1.2.0 APK** is compiled from a SHA256-pinned v1.0.0 application source archive, with newer PowerPlay transformations applied. It is **not built from the repository-root Dart files**.

Reviewing PRs #29–35 against that successful release candidate's matching archived source showed that six fixes were already included:
- **#29:** 15-second pooled HTTP socket timeout prevents stale Plex artwork connections.
- **#31:** in-flight playback progress/keepalive protection.
- **#32:** memory-bounded BIF preview loading and deferred player preview work.
- **#33:** cached and budgeted Fire TV cards and smoother detail transitions.
- **#34:** Plex server-endpoint rediscovery after failed reconnect.
- **#35:** grid poster aspect-ratio preservation.

**Missing:** only **#30**, Plezy `63f8cd84`, which avoids issuing a no-op `NestedScrollView.animateTo` from a focused library card. On some layouts such calls collapse the floating header and make it jump during D-pad movement.

The `1.2.1+10201` release workflow audits the preexisting fixes against the source used for the APK, applies #30 there with strict source anchors, executes the upstream-derived focus regression test, and creates a signed **candidate**. Public publication continues to require a successful candidate and the separate existing promotion workflow. Root-only PRs must not be blindly merged or counted as APK changes.
