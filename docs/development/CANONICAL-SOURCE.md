# Canonical PowerPlay application source

## Policy

The source PowerPlay actually compiles is the tracked `lib/`, `android/`, `assets/`, `test/`, `packages/`, and project configuration **at repository root**. After this migration, there is no second application source or build-time patch replay. The Git commit a reviewer inspects builds the release APK.

The migration uses the matching SHA256-verified source tarball attached to [PowerPlay v1.2.4](https://github.com/The-Power-0/PowerPlay/releases/tag/powerplay-v1.2.4). Other platform scaffolding, including Windows, is preserved for possible later work; only Fire OS 7/8 is a supported APK target.

## Developing and releasing

1. Branch from `main`. Edit and review `lib/`, `android/`, `assets/`, `test/`, and other tracked project files **directly**. Do not modify the historic archived source tarball or legacy version patch scripts.
2. Run `flutter pub get` and `flutter test` against repository root. Preserve the `com.power.powerplay` identity, `powerplay://` deep links, hardware-specific library defaults and GPL notices.
3. For a release, create `release/powerplay-vX.Y.Z-rc1`, update **both** `pubspec.yaml` (`version: X.Y.Z+BUILD_NUMBER`) and `.github/powerplay/release.json` (`version`, `build_number`). ARMv7 APK versionCode adds 1000.
4. Pushing the release branch triggers the existing candidate workflow. It checks out that exact commit, tests, builds and signs a Fire TV APK, verifies ABI/package/version/splash, then archives the **same Git commit** as its source. No pinned v1.0.0 source is restored or patched.
5. After candidate success and device validation, merge its PR; update `.github/powerplay/publication-request.json` on `main` with the successful candidate run ID and version. The existing publication workflow promotes the **identical APK without recompilation**.

## Historical provenance and native sources

PowerPlay v1.0.0 through v1.2.4 were created with prior version-specific build transformations. Their corresponding source tarballs remain available on their GitHub release pages; do not substitute GitHub-generated source archives for those versions.

The native-source input ZIP is checksum-pinned to v1.2.4 and remains an attachment for source/license obligations only. It is **not extracted to change the application** during builds. The existing GPL-3.0 notices and unresolved full native/transitive dependency audit remain documented.

## Migration and validation

The one-time `powerplay-canonical-migration.yml` workflow retrieves and verifies the published v1.2.4 source, copies its application tree to root while excluding generated caches and signing secrets, removes superseded build-time patch scripts, checks the bytes of critical app files and tests theme, focus, Plex defaults and HA links before pushing the migration branch. Nothing automatically publishes or installs an APK; `main` changes only when its PR is merged.
