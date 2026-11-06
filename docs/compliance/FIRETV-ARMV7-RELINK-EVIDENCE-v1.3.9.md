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
