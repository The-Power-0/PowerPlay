# PowerPlay v1.3.9 source review disposition

This records the verification and release decisions for the published ARMv7 APK with SHA-256 `f832a2c507f997fcb047c0ab899254d1fd111520942e88da50e61ebc82e3c764`. The decision is **NOT CLEARED**.

| Area | Evidence and disposition |
| --- | --- |
| App native JNI | Rebuilt `libdovi_bridge.so` and `libffmpegJNI.so` from the checksum-verified public source archive using its CMake files. Both match the APK except for the GNU build ID. The inputs were NDK 29.0.14206865, CMake 4.1.2 with Ninja, ARMv7, the API 25 configuration, RelWithDebInfo, the checksum-pinned libdovi archive and the rebuilt FFmpeg headers and matching shared libraries. |
| FFmpeg | The GPLv3 configuration, patched sources, dav1d, both Rust build contexts, compiler options and original notices are preserved. The IJG-derived files require retaining their original attribution and noting modifications. The three shipped rebuilds contain no defined OpenSSL, SSL, EVP or CRYPTO symbol families. They have no OpenSSL shared-library requirement, and their recorded source paths contain no OpenSSL paths. Those symbols appear in the rebuilt but unshipped `libavformat.so`. Retain OpenSSL as a build input and distinguish it from code proven present in the APK. |
| Flutter and Cronet | All 98 Flutter and 194 Cronet toolchain paths in the observed debug line tables resolve. The review uses Flutter's exact Clang package, NDK r28c, and Chromium's pinned Android toolchain, Clang headers, compiler-rt and Rust source. The files and hashes are in the supplement. All 150 Flutter and 128 Cronet generated paths have identified source or generator candidates. The maps include Impeller shader and FlatBuffers generation, Dart version generation, Cronet JNI and Rust bridges, and protocol buffers. This closes the missing toolchain path checks. Full historical GN build and generated output verification are still open. |
| FriBidi | Reran the original Linux relink and produced an aligned APK signed with a disposable local key. Android Build Tools verified its signature and alignment. Only the intended ELF changed among the non-signature ZIP entries. A Linux libass render of the supplied ASS fixture changed all eight frames containing U+E000 and preserved the four control frames. Install and exercise subtitles on an ARMv7 Fire TV before closing device validation. |
| GMS | 16 recognizable definitions, including 10 classes containing 61 method bodies. Fifteen class names map to the pinned base, basement and cronet AARs. Google Maven returns HTTP 404 at all three standard exact-version source JAR URLs. This documents what is missing from the public source path. It does not establish that no separate grant or source delivery exists. |
| Public distribution | The current GitHub release links the verified app source and an incomplete native input archive. The reviewed public delivery is a standalone APK download. The available facts show no associated transfer of a Fire TV to the recipient, so the extra GPLv3 section 6 installation-information condition is not established for this delivery. Reassess for any hardware transfer. Equivalent access to complete Corresponding Source remains a separate requirement. |

The Media3-derived JNI source has AOSP Apache-2.0 headers. Preserve those headers and the Apache-2.0 text with the modified adapter, credit the upstream Media3 decoder, and identify the PowerPlay version's buffer handling and ARMv7 integration changes in its notices. The project application license and FFmpeg library terms are separate from this attribution.

The three GMS client artifacts are application build inputs with implementation code retained in the APK. The external Google Play Services process is separate. The observed implementation placement does not establish the GPLv3 System Library exception for the APK's client code. An artifact-specific grant and source access, or a supported basis for treating that code outside Corresponding Source, is required to clear it under the fixed dependency constraint. A GMS grant alone would not waive terms imposed by other copyright holders. See [Google's client architecture](https://developers.google.com/android/guides/overview), [Android SDK terms](https://developer.android.com/studio/terms) and [GPLv3 sections 1, 5, 6, 7 and 12](https://opensource.org/license/gpl-3.0).

The evidence supports a **hold** for the current public binary. It does not certify infringement or full compliance. The [ledger](native-v1.3.9-signoff.json) retains the required evidence for release clearance. The privately saved review files are evidence for assembling a corrected public source and notice package.

The [APK payload review](APK-PAYLOAD-REVIEW-v1.3.9.md) records the subsequent Play Billing finding, Dart source checks, and asset provenance.

## Run the isolated Fire TV check

Use the ARMv7 FriBidi relink kit to build `modified.so`. Install Python with pyelftools and Android Build Tools. The unsigned APK builder verifies the original release digest before replacing the ELF.

```sh
python scripts/prepare_powerplay_fribidi_test_apk.py PowerPlay-v1.3.9.apk modified.so relink-unsigned.apk
zipalign -P 16 -f 4 relink-unsigned.apk relink-aligned.apk
keytool -genkeypair -keystore relink-test.p12 -alias relink -keyalg RSA -keysize 2048 -validity 30
apksigner sign --ks relink-test.p12 --ks-key-alias relink --out relink-test.apk relink-aligned.apk
apksigner verify --verbose relink-test.apk
zipalign -c -P 16 4 relink-test.apk
```

Use a spare ARMv7 Fire TV without PowerPlay installed. The test key cannot update an installation signed with the release key. Confirm the connected test device explicitly before running `adb -s SERIAL install relink-test.apk`. Mux the included `evidence/fribidi-playback.ass` into a short MKV and play it as an ASS track. The first two cues move the U+E000 glyph or its fallback box from one side of the Hebrew run to the other. The final cue serves as a control. Confirm the subtitle renderer starts, the test build displays ASS subtitles and the expected bidi change appears against the baseline. Record device model, Fire OS version, APK/ELF SHA-256, subtitle output, and any renderer errors. Do not use the test-signed APK as a public release.


## Continuation review update

The candidate CI APK built from the pinned application source commit is byte-identical to the published signed APK; all 15 native libraries match. Go Noto v7.0 font source and OFL 1.1 terms are now verified, and the shipped Hangul subset regenerates byte-for-byte. The chapter model itself matches both source and APK, but its original training inputs are not archived. The upstream Plezy trademark policy still requires replacement of bundled original app icons in public forks absent written permission.

The release remains **NOT CLEARED**. Remaining items are: Google Play Services/Billing artifact rights and source access; historical Flutter engine and Cronet build verification; Fire TV validation of the FriBidi relink; public corresponding source and notice delivery; chapter-model training-input provenance; and resolution of the upstream Plezy alternate-icon/adaptive-icon policy. No app or dependency changes were made as part of this continuation.


## Owner disposition

The project owner has chosen to defer further investigation of the remaining source, rights, build, device-validation and distribution items. The collected notices, source inputs and evidence are retained. Deferral does not change the evidence or establish compliance; the signoff remains **NOT CLEARED**. See [source and third-party notices](THIRD-PARTY-NOTICES-v1.3.9.md).
