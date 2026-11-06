# PowerPlay v1.3.9: Android native dependency/source licensing review

**Scope:** the signed, public Fire TV ARMv7 APK at tag [powerplay-v1.3.9](https://github.com/The-Power-0/PowerPlay/releases/tag/powerplay-v1.3.9), source commit `dfab0f7ae979c0edee617f9f50a6c72efac51aa4`. The PowerLink HACS component and non-Android binaries are outside this review. This document describes evidence and open obligations, not legal advice.

**Audit state: NOT CLEARED FOR FULL NATIVE-SOURCE COMPLIANCE SIGN-OFF.** The release has a verified corresponding application-source archive but has not demonstrated complete corresponding native/transitive source or distribution notices. Do not replace this sentence with a compliance claim solely because a CI inventory passes.

## Evidence anchored to the published release

| Item | Evidence |
| --- | --- |
| Signed release APK | `PowerPlay-v1.3.9.apk`; SHA256 `f832a2c507f997fcb047c0ab899254d1fd111520942e88da50e61ebc82e3c764` |
| Matching application source | `PowerPlay-v1.3.9-Source.tar.gz`; SHA256 `7bfd23b0010dbc999758cea3d0d65f6fad31784527f4b0cd6a01cc484f17853c` |
| NativeSourceInputs attachment | `PowerPlay-v1.3.9-NativeSourceInputs.zip`; SHA256 `9b58bab24a54219af312e397566281bcdd84a84cae6f5f49d4e6eefd6e4af756` |
| Source archive generation | Release candidate workflow exports the reviewed Git commit, without the historic application patch replay |
| Native source attachment generation | Candidate workflow downloads the unchanged v1.2.4 native source ZIP, checks a fixed digest and renames it; this is not a fresh dependency closure |
| App licensing | `LICENSE` GPL-3.0; `POWERPLAY-RELEASE-NOTICE.md` credits Plezy 2.25.0 |
| Android target | ARMv7 `armeabi-v7a`; Media3/ExoPlayer replaces libmpv runtime, but native FFmpeg remains |
| Binary inventory | CI runs [42155338174](https://github.com/The-Power-0/PowerPlay/actions/runs/42155338174) and [42155843835](https://github.com/The-Power-0/PowerPlay/actions/runs/42155843835) verified APK checksum, found **15 ARMv7 ELF libraries**, zero unresolved DT_NEEDED names and no mpv runtime; all are provisionally identified. **FFmpeg's 3 libraries and libc++ match the pinned AAR byte-for-byte.** |

The original native ZIP generator, `scripts/archive_firetv_native_sources.py`, packages `mpv-build` source and pinned FFmpeg, dav1d, OpenSSL and libdovi upstream archives. Its own README disclaims transitive-source completeness. It does **not** follow the separately downloaded static `libass`, `libdovi-builds`, Chromium Cronet, resolved Gradle graph, Rust crate closure or Flutter engine source.

## Scoped native build dependency graph

```text
PowerPlay signed APK (Fire TV / armeabi-v7a)
  Flutter AOT application + Flutter engine
  Android Gradle releaseRuntimeClasspath (Media3, Cronet, Flutter plugins, ...)
    Chromium Cronet native runtime + its embedded third-party code
  Media3 FFmpeg JNI adapter (PowerPlay native source)
    FFmpeg 8.0.1 shared libraries extracted from pinned mpv-android AAR
      FFmpeg's static Android dependencies: dav1d 1.5.4,
        OpenSSL 4.0.3, libdovi 2.3.1
  dovi_bridge (PowerPlay native source)
    statically linked libdovi 2.3.1 from edde746/libdovi-builds
      Rust runtime and target/features-selected Cargo dependencies
  asskt (PowerPlay native source)
    statically linked edde746/libass 0.18.3
      FreeType, FriBidi, HarfBuzz, libunibreak, Fontconfig, Expat
      (the fork's build script combines these into libass.a)
  libc++_shared.so from the pinned mpv-android AAR
  Any additional packaged native libraries: must be classified from the APK
```

A source input that contributed only to the **unused** libmpv player inside the upstream AAR is not automatically a distributed PowerPlay component. In particular, mpv, Lua, libplacebo and the mpv-build-specific libass/Freetype/HarfBuzz copies must not be marked as shipped merely because they are in its `versions.json`. Conversely, the independent static libass archive **is** a shipped transitive dependency of `asskt`.

## Component review and source obligations

| Component or dependency closure | Verified build identity | License review | Source and attribution review |
| --- | --- | --- | --- |
| PowerPlay + upstream Plezy application | GPL-3.0 application, source commit above | GPL-3.0; original notices retained | Application source archived and SHA256-published; **established** |
| FFmpeg shared libraries | FFmpeg n8.0.1 at `894da5ca7d742e4429ffb2af534fcda0103ef593`, patched by mpv-build `3b9f38affe3c4171f8e6bc47331feffd3d13be1d`; AAR checksum `8ad8dbf2ebae864a14d768d7787895a74d044f18b270df886e76c9a23ee80158` | Build script explicitly passes `--enable-gpl --enable-version3`, so treat its shipped FFmpeg as **GPL-3.0-or-later**, not LGPL-only. Review file-level exceptions including IJG notices | **Pass:** libavcodec.so, libavutil.so, libswresample.so are byte-identical to checksum-pinned AAR; FFmpeg source and patch series archived. **Gap:** build config output, complete compiled native source/notice set and direct artifact-to-build provenance |
| dav1d inside FFmpeg | 1.5.4, `54706fc6bc0cdecab7e9593974a4039cc038fca7` | BSD-style upstream; confirm exact source notices | Upstream snapshot included in native ZIP; audit assembly/flags and attribution |
| OpenSSL inside FFmpeg | 4.0.3, `af1775b60dfa141a4ad762585052cabeb9f37e9e` | Apache-2.0; FFmpeg n8.0.1 configure explicitly permits OpenSSL >=3 under GPLv3 when `--enable-version3` is on | Source snapshot included; archive exact NOTICE and build commands/config |
| libdovi inside FFmpeg | dovi_tool tag 2.3.1 commit `b25558062e4a56973482ec70133bd7b891320e48` | Rust library MIT; individual crate licenses still apply | Upstream dovi_tool snapshot included; static Rust crate closure and exact builds not established |
| libdovi statically linked into dovi_bridge | v2.3.1; ARMv7 archive SHA256 `ed6fec8bf744e41c661b97f5fc4bf1197ebe9b09a140cbde369728e790ee3a68` | MIT upstream plus transitively linked crates and Rust runtime | Source/tag-locked ARMv7 `cargo tree --features capi` resolves **15 packages total**: dolby_vision, anyhow, bitvec, funty, radium, tap, wyz, bitvec_helpers, bitstream-io, core2, memchr, crc, crc-catalog, libc, tinyvec. **Gap:** released prebuilt compiled without `--locked`, so tree is not proof of historic binary resolution; preserve exact crate sources/checksums/licenses and build inputs |
| libass statically linked into asskt | edde746/libass 0.18.3 Git tag commit `76cdb2bc174828aac74a458d38a0786cb7af922d`; archive SHA256 `fc98637752695d7cf9e26b02befaa634dd4cad25a2f38fba80de814bfd310a17` | libass ISC; separate notices for all six static dependencies | Pinned release ZIP verified and **15 files described as notices/attributions** enumerated. **Confirmed notice defect:** libunibreak's folder has only `AUTHORS` and Meson's `LICENSE.build` (not the actual upstream zlib-style `LICENCE`); the upstream package's UK-spelled `LICENCE` is omitted by the builder's `LICENSE*` pattern. FreeType offers FTL or GPLv2; explicitly elect the **FreeType License** for GPLv3 compatibility and reproduce its attribution. FriBidi includes LGPL-2.1 text; HarfBuzz says Old MIT; Fontconfig and Expat carry permissive notices. **Gaps:** exact WrapDB revisions, full file-level notices, and LGPL static-relink/source obligations. |
| Android C++ shared runtime | `libc++_shared.so` selected from mpv AAR | LLVM libc++ Apache-2.0 WITH LLVM-exception, subject to exact binary provenance | **Pass:** byte-identical to pinned AAR. **Gap:** exact NDK/LLVM source version and license source mapping |
| Flutter engine and AOT | Flutter 3.47.9, framework `c197ca5199e9ee5661e865596c9c07294dfab51c`, engine `89c39edfdfae2949f6806e4a315c0c08522238b7`, engine content hash `9e025265bef30b838c0c1b68cad19decf97048f2` | Flutter BSD-3-Clause plus engine/Skia/ICU/other embedded third-party notices | Engine revision resolved from workflow. **Gap:** archive engine licenses and embedded third-party source and prove engine native binary correspondence |
| AndroidX Media3, JNI and Android plugin dependencies | Media3 1.11.0; exact release Gradle graph now captured (157 distinct external module coordinates including platform variants/constraints, not 157 necessarily packaged binaries) | Generally Apache-2.0 for AndroidX, but per-artifact verification needed | Full resolved graph exported. **Gap:** verify every packaged artifact and file-level license/notice; compare dependency graph with DEX/resource shrinking results |
| Chromium Cronet embedded | `org.chromium.net:cronet-embedded:143.7445.0`; resolved graph also includes `com.google.android.gms:play-services-cronet:18.0.1` | Chromium BSD-style license **plus** bundled third-party licenses; assess additional Play Services licensing separately | **Gap:** exact Chromium source revision, artifact-specific license bundle and GPLv3 compatibility of any packaged Google SDK components |
| Dart JNI native bridge | `libdartjni.so`; Dart `jni` package 0.14.2 in `pubspec.lock` | BSD-3-Clause per Dart project's package license | Verify exact native build, licenses and binary-to-source correspondence |
| AndroidX DataStore native counter | `libdatastore_shared_counter.so`; **DataStore 1.1.7** from exact release Gradle graph | Apache-2.0 | Version known; verify exact AAR/SHA and shipped source/notice |
| Sentry Android + native crash reporting | `libsentry-android.so`, `libsentry.so`; Flutter `sentry_flutter` 9.30.0; **Sentry Android/NDK 8.56.0; native-ndk 0.16.6** | MIT for SDK/native base; investigate bundled third-party notices | Maven versions resolved; obtain exact native binary source/submodule closure, original notices and AAR hash mappings |
| SQLite via Dart FFI | `libsqlite3.so`; `sqlite3` Dart package 3.5.0 | SQLite core is public domain; Dart package MIT. Verify exact compiled SQLite third-party extensions | Identify SQLite core version/configuration and binary source/rebuild materials |
| Other binary assets and static closures | Published APK inventory finds 15 ELF libraries, all provisionally named | File-level licenses not yet complete | **Gap:** enumerate non-ELF embedded code/resources, static archives and compiled license exceptions |

Official FFmpeg licensing reference: https://ffmpeg.org/legal.html and upstream FFmpeg n8.0.1 `LICENSE.md`. The FFmpeg library remains GPLv3 because of the **actual build configuration**, independent of which codec happens to be played at runtime. The app's GPLv3 attribution does not replace all third-party notices.

### Concrete libass notice correction

The upstream edde746/libass Android 0.18.3 packaging script searches for files named `LICENSE*` and similar, but the actual libunibreak source license is named `LICENCE`. The packaged `libass-android-0.18.3.zip` therefore has `libunibreak/LICENSE.build` (a Meson build-system notice) **without** libunibreak's own zlib-style `LICENCE`. That is a verifiable incomplete redistribution notice set, not merely a theoretical provenance gap.

A corrective PowerPlay notice/source bundle must include the exact libunibreak `LICENCE` from the source revision actually built. For FreeType, elect the FTL branch of the dual licensing option and retain `FTL.TXT`, `LICENSE.TXT` and any file-specific notices. For FriBidi (LGPL-2.1), explicitly address the static linking/relinking requirements and track version-specific exceptions.

The packaged `assets/licenses/SpatialAudioBridge.txt` describes an Apple-side spatial audio framework. Its presence as a Flutter asset is **not evidence** that its Rust framework is linked into the Fire TV ELF set; treat the text as a separate asset notice unless the APK audit demonstrates otherwise.

## Release gate: conditions for real sign-off

1. Download the **published** APK and verify its SHA256. Enumerate each packaged ELF, exact per-file hash and `DT_NEEDED`; reconcile each object to a named license, corresponding source and original notices. Keep all unknown/extra entries as blockers. Include static component closures and generated native binary assets.
2. Resolve the exact release Gradle/Flutter runtime trees (not dev-only dependencies) and produce a versioned SBOM. Identify all AAR/JAR/embedded native payloads and origin/notice text.
3. For FFmpeg, preserve actual patch series, configure output, FFmpeg license exceptions, OpenSSL notice and relevant build recipes; tie each AAR-derived shared object to the release AAR. Recheck all upstream tags and file-level license restrictions.
4. For the libass combined archive, obtain the exact per-ABI prebuilt release ZIP, its bundled license directory and the **actual** WrapDB fallbacks/versions; archive source and options for FreeType, FriBidi, HarfBuzz, libunibreak, Fontconfig, Expat.
5. For both libdovi builds, record the exact target/features-selected Rust dependency closure, license files and checked crate checksums. Rebuild from recorded toolchain inputs, or document an alternative GPL-compliant corresponding-source path including required scripts.
6. Provide a newly generated, version-specific native corresponding-source/notice bundle covering every shipped component and its complete legal terms, plus checksum manifest. If modifications to LGPL-covered static or dynamically linked parts require relinking ability, include suitable object/relink materials or document the verified GPLv3-compatible alternative.
7. Verify the source and notice bundle **as part of candidate validation**, then retain that exact bundle when promoting the identical signed APK. Do not merely rename the 1.2.4 archive. Make missing components fail the compliance gate.
8. Review the GPLv3 distribution requirements for installation information, patent grants and any additional applicable conditions. Do not assume every Android device is a User Product or that all signed builds require public signing keys; decide based on actual distribution facts.

## Reproduce available inventory

The repository workflow `.github/workflows/native-license-inventory.yml` downloads the immutable release APK, verifies the exact expected digest and publishes:

- `native-elf-inventory.json` with every `lib/armeabi-v7a/*.so`, SHA256, provisional component mapping and dynamic-link edges.
- `native-elf-inventory.md` showing unknown libraries and unresolved external SONAMEs.
- `gradle-releaseRuntimeClasspath.txt` generated from source at the **v1.3.9 commit**, documenting resolved Android runtime dependencies (if its Gradle job succeeds).

The inventory code intentionally sets `source_coverage_complete: false`. The initial scan reported 15 native ELF libraries, including five not found through the original hand-read native build inputs: `libdartjni.so`, `libdatastore_shared_counter.so`, `libsentry-android.so`, `libsentry.so`, and `libsqlite3.so`. Those are now provisionally mapped above, but their source/notice obligations remain open. A green inventory job is **not** a license certification; these artifacts are evidence inputs for the outstanding transitive-source closure.

### Additional audit evidence introduced by this PR

The inventory now includes **two separate dependency-resolution layers** anchored to the signed v1.3.9 release, each deliberately limited to what it can prove:

- `scripts/export_gradle_runtime_artifacts.init.gradle` runs against the **immutable shipped Flutter/Gradle source**. `scripts/audit_powerplay_gradle_runtime.py` records exact resolved AAR/JAR paths, artifact SHA256 values and notice-file contents, and matches embedded ARMv7 native libraries to the release APK by full binary hash. A missing embedded license is **not automatically a license violation**; upstream Maven POM/source terms still require separate review. Resolving an artifact does not prove its bytecode survived shrinking.
- `scripts/audit_powerplay_rust_crates.py` copies `Cargo.lock`-selected Rust registry source archives, validates each against its registry checksum, and extracts each crate's available legal texts. It separately labels local dovi_tool crates and retains a **historical provenance limitation**: the published libdovi prebuilt was compiled without `--locked`, so a current lockfile source snapshot does **not** establish the exact dependency set used in the original binary.
- `scripts/audit_powerplay_native_release.py` also archives APK-embedded license assets and tries to decode Flutter's `NOTICES.Z` license corpus when present. This helps distinguish Flutter/engine-provided notices from separately packaged native libraries and non-Android-only notice assets.

The independent libass upstream [Android 0.18.3 release workflow](https://github.com/edde746/libass/actions/runs/29063098223) was built on July 10, 2026. Its build recipe calls the **live** Meson WrapDB during compilation and does not package exact resolved `.wrap` files. Historical workflow logs could not be retrieved through the GitHub API. Consequently, the six WrapDB source revisions cannot be certified solely from the published `libass.a` ZIP; for a future fully reproducible release, the builder needs to pin and archive those wraps and actual source archives before compiling.

These additions produce reviewable evidence but **do not change the sign-off status**. The original release's incomplete-source warning remains appropriate.

### Verified APK-embedded notice evidence (signed v1.3.9)

The updated ELF inventory job [42161034057](https://github.com/The-Power-0/PowerPlay/actions/runs/42161034057) extracts the actual published APK's legal assets:

- `assets/flutter_assets/NOTICES.Z` — 153,893 compressed bytes, SHA256 `e18eddabcdfd3c6b62197b1b20e7f444477de4ea313c69582cc7b8ddd1484db8`; successfully decoded into 1,560,143 bytes of readable notices. This corpus is genuine distributed attribution evidence, **not** by itself proof that every Flutter engine/Skia/ICU source requirement has been fulfilled.
- `META-INF/SENTRY_THIRD_PARTY_NOTICES.md` — 24,486 bytes, SHA256 `a2ea6ba8658edd12f4601e7351c2e6fc9eb85f7c1a234b04945ca4fa194a395e`. Sentry Java's documented vendored/third-party notice text is present in the APK; separately inspect native sentry source, its build and license closure.
- Four AndroidX `META-INF/.../LICENSE.txt` assets are present, each copied from the signed APK and checksum-inventoried. License assets for other Maven components must not be assumed to exist merely because these four are present.
- All 15 `armeabi-v7a` APK ELF libraries remain identified by name and SHA256, with no as-yet-unclassified library; this is not a static-dependency closure.

The **lockfile-derived** libdovi evidence artifact captures all 15 identified Rust source components. It includes checksum-verified source archives for registry packages and original legal text for each component, including `crc-catalog`'s `LICENSES/` files and the local Dolby Vision MIT license from the pinned dovi_tool tag. Those packages are not a substitute for reconstructing the exact historical `cargo build` resolution.

### Resolved Maven binary-to-APK closure: verified

[GitHub Actions run 42161034057](https://github.com/The-Power-0/PowerPlay/actions/runs/42161034057) completed **all three audit jobs successfully**, including the new external Maven AAR/JAR artifact exporter. The `PowerPlay-v1.3.9-Android-runtime-graph` artifact contains 230 binary artifact records from raw AAR and derived JAR views; these are **not 230 unique dependencies** (one module often appears as both an AAR and a `classes.jar`). The original dependency-tree evidence records 157 external coordinates including platforms/constraints. Only 20 artifact records had an embedded text notice matching the scanner's strict filename rules. Absence of such a file in the other 210 is **not** a conclusion about licensing or final notice obligations.

Full SHA256 binary comparisons establish these byte-identical origins inside the **signed APK**:

| APK ELF | Maven component and exact binary | Maven AAR SHA256 |
| --- | --- | --- |
| `libcronet.143.0.7445.0.so` | `org.chromium.net:cronet-embedded:143.7445.0` | `afdd7af7568e9758e3690c3a4a228f30993ac3e4ef0f94c72bb68503c0167697` |
| `libdatastore_shared_counter.so` | `androidx.datastore:datastore-core-android:1.1.7` | `adca1d7cde73406fcca2a0eeabac63459adc9d1fe201b79ba08711fa2e331984` |
| `libsentry-android.so`, `libsentry.so` | `io.sentry:sentry-native-ndk:0.16.6` | `07fea3e481b27a08ff235cf06ea70bc845ae973521d689442774577f20584ba9` |

The other 11 libraries derive from other paths (app-built JNI, pinned FFmpeg AAR, Flutter engine/AOT, Dart JNI and SQLite native assets) and must be tied to corresponding source by their own build/distribution evidence. Source/notice closure for the **embedded code within** Cronet and sentry-native is not proven just by a byte-for-byte upstream AAR match.

### Historical WrapDB source reconstruction (July 10, 2026)

The original libass v0.18.3 upstream Android job began on **2026-07-10 01:46 UTC**. The last public `mesonbuild/wrapdb` commit before that instant was [`99634f253c3f2e83295b210018d071f6570284e6`](https://github.com/mesonbuild/wrapdb/commit/99634f253c3f2e83295b210018d071f6570284e6) (2026-07-09 22:41 UTC). It is an immutable time-qualified **reconstruction**, not an archived record of what the ephemeral build runner actually fetched.

| Independent static libass fallback | Historical WrapDB package | Verified upstream source SHA256 |
| --- | --- | --- |
| FreeType | `freetype-2.14.3` | `36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f` |
| FriBidi | `fribidi-1.0.16` | `1b1cde5b235d40479e91be2f0e88a309e3214c8ab470ec8a2744d82a5a9ea05c` |
| HarfBuzz | `harfbuzz-13.0.1` | `3553d943401c34ab9b8c75f35cdb8452ca660233b0e9d4a22395ce5245484bd7` |
| libunibreak | `libunibreak-6.1` | `cc4de0099cf7ff05005ceabff4afed4c582a736abc38033e70fdac86335ce93f` |
| Fontconfig | `fontconfig-2.16.2` | `165b8fd2a119864c87464b233986c4a1bc09efb09c65de1ca40cc1e85ffb77e2` |
| Expat | `expat-2.8.2` | `3ad89b8588e6644bd4e49981480d48b21289eebbcd4f0a1a4afb1c29f99b6ab4` |

A later **2026-07-10 05:43 UTC** WrapDB commit updated Fontconfig to 2.18.3, *after* the historical build began; using current WrapDB instead of this pinned snapshot silently yields wrong input versions. FriBidi, FreeType and Expat also have later updates.

The `scripts/audit_libass_historical_wraps.py` workflow integration downloads all six source archives, validates the WrapDB-published SHA256 values, preserves the original `.wrap` descriptors, 6 Meson patch files in the libunibreak and Expat fallback directories, and collects original upstream legal texts. The source-only artifact also includes original libass 0.18.3 and `dovi_tool` 2.3.1 source archives anchored to their verified Git commits. In [CI run 42163576746](https://github.com/The-Power-0/PowerPlay/actions/runs/42163576746) the complete WrapDB download/source-hash stage succeeded.

**Confirmed missing redistribution notice recovered:** the verified libunibreak 6.1 source includes its actual `LICENCE`, SHA256 `0c57e2ec42ece17791a75d2f9b2f8e0663181be008667a507f765b3ef22522db`. The upstream libass prebuilt ZIP omitted that file because its collector did not match UK-spelled `LICENCE`. The corrected license is now present in the *audit evidence artifact*, but the existing v1.3.9 public release attachment has **not** been amended.

**Remaining limitation:** the historical libass job did not pin a WrapDB snapshot or preserve its resolved dependency manifests/compilation records. Therefore date-qualified source checksums do not by themselves prove that the compiled `libass.a` was built from these exact archives. The related static LGPL-2.1 compliance route (relinkable objects versus suitable GPL conversion under the actual license terms) must also be resolved before source-closure sign-off.

### Conclusion

**Corresponding application source: available. Native license and source closure: incomplete.** Until the static/embedded/Gradle/Flutter graphs and a replacement release-native-source bundle are reconciled, do not remove the incompleteness disclosure from existing releases or label v1.3.9 fully compliant.
