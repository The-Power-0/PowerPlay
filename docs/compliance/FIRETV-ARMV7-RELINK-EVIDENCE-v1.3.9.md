# PowerPlay 1.3.9 ARMv7 relink verification

The input was the signed Fire TV APK from tag `powerplay-v1.3.9`, source commit `dfab0f7ae979c0edee617f9f50a6c72efac51aa4`. Its verified SHA-256 was `f832a2c507f997fcb047c0ab899254d1fd111520942e88da50e61ebc82e3c764`.

The tagged subtitle JNI source was built with CMake 4.1.2, NDK 29.0.14206865, API 21, ARMv7, RelWithDebInfo and the original checksum-pinned libass 0.18.3 archive. The stripped result matched the APK ELF byte for byte after removing only the GNU build-ID note from both files.

FriBidi 1.0.16 was then built from historical WrapDB source with a test-only change for U+E000. All 18 original FriBidi archive members were replaced before relinking. The modified branch was visible in the disassembly of the resulting `fribidi_get_bidi_types`. Dynamic exports, SONAME and DT_NEEDED entries matched the baseline. The historical six WrapDB source archives, original notices, relink script and input checksums were captured together, including the libunibreak `LICENCE`.

| ELF | SHA-256 from the verification run |
| --- | --- |
| Shipped | `680b7cb6a28b716aebb2dd51e968812c80eae8db9c2788f16406462ce9b09931` |
| Baseline relink | `46378bdd7b63ce5081a3854a85c7197f69ea56d129bb79032803cc2096c3f492` |
| Modified relink | `96ab077505e1050259b0c8a2dfd97b8a8546ec41d0da9f80e997dcf3d3cdcf4c` |

The Linux test establishes the technical relink path. Fire TV installation and subtitle playback have yet to be verified. LGPL-003 remains open for device validation and distribution of the release-specific materials. No GPL conversion was performed.

## Dart JNI and AndroidX DataStore source rebuilds

Both comparisons used the same SHA-256-verified APK. After stripping each rebuilt ARMv7 ELF with its own NDK's `llvm-strip --strip-unneeded`, only the GNU build-ID note differed. Removing that note from both sides produced full-file equality.

| Component | Exact source | Tested build options | SHA-256 after normalization |
| --- | --- | --- | --- |
| `libdartjni.so` | [Dart jni 0.14.2 package](https://pub.dev/api/archives/jni-0.14.2.tar.gz), lockfile SHA-256 `d2c361082d554d4593c3012e26f6b188f902acd291330f13d6427641a92b3da1` | Package `src/CMakeLists.txt`, NDK 28.2.13676358, API 21, RelWithDebInfo | `6e5d7a804fd2b7b40114a690264cfd8d1c7f459121c3912e0be42583929b04e4` |
| `libdatastore_shared_counter.so` | [AndroidX DataStore 1.1.7 release source](https://android.googlesource.com/platform/frameworks/support/+/420da5f291449f11801e378c6789a328a06ec6cb/datastore/datastore-core/src/androidMain/cpp/) | Upstream `CMakeLists.txt`, NDK 25.2.9519653, API 19, `c++_static`, Release | `85a6875f6eab3f0126cafe1e210d3fa00013d74f9ba61617575909690985d9c6` |

Both used CMake 4.1.2 and Ninja with `-DANDROID_ABI=armeabi-v7a` and the versioned NDK CMake toolchain. Dart JNI's package license is BSD-3-Clause and the compiled `src/third_party/global_jni_env.c` carries an Apache-2.0 notice. The AndroidX counter's source and JNI wrapper carry Apache-2.0 notices. These notices still need to be reconciled with the public distribution.

The corrected NDK libc++ provenance check passed in the [signed APK inspection job](https://github.com/The-Power-0/PowerPlay/actions/runs/42214816298).
