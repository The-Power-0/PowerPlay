# PowerPlay release note policy

Each published PowerPlay version has exactly one Markdown note template named `vX.Y.Z.md` here. The release candidate and stable publisher read the **matching version's file from the exact compiled source commit**, rather than concatenating notes from previous releases.

Keep these headings consistent:

1. `# PowerPlay vX.Y.Z — Fire TV`
2. `## Changes in this release` — only features and fixes **introduced in that version**; no running changelog or repeated legacy notes
3. Optional `## Compatibility` — only version-specific installation dependencies or breaking changes
4. `## Download and source` — links to the APK, corresponding source, native inputs, and hashes
5. `## Build and attribution` — app identity, verified candidate, and licensing notice

Leave exactly one `{{CANDIDATE_RUN_ID}}` placeholder in the candidate URL and one `{{SOURCE_SHA}}` placeholder. The publisher substitutes the verified build's run ID and commit SHA at publication time. Do not replace those placeholders by hand, even for older releases.

**To make a new release:** add `vX.Y.Z.md` and update `release.json` / `pubspec.yaml` in the `release/powerplay-vX.Y.Z-rc1` branch *before* building. The signed candidate verifies the release notes file, and the publisher extracts it from the candidate's corresponding source archive. Editing release notes does not rebuild or change the signed APK.

The `powerplay-release-notes-sync.yml` workflow updates descriptions on already-published PowerPlay releases when templates on `main` change. It never creates a release, touches binaries/assets, changes release tags, or edits archived Plezy releases. If a version has not been published yet, it is skipped.
