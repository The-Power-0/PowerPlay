# PowerPlay v1.3.9: source and third-party notices

This notice describes the published Fire TV ARMv7 release at [powerplay-v1.3.9](https://github.com/The-Power-0/PowerPlay/releases/tag/powerplay-v1.3.9). PowerPlay is based on Plezy and is distributed under the [GNU GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html). The release contains third-party components under their own applicable licenses; retain the original copyright notices and license texts with their respective materials.

## Published source

- [PowerPlay v1.3.9 application source](https://github.com/The-Power-0/PowerPlay/releases/download/powerplay-v1.3.9/PowerPlay-v1.3.9-Source.tar.gz), SHA-256 `7bfd23b0010dbc999758cea3d0d65f6fad31784527f4b0cd6a01cc484f17853c`.
- [Native source inputs](https://github.com/The-Power-0/PowerPlay/releases/download/powerplay-v1.3.9/PowerPlay-v1.3.9-NativeSourceInputs.zip), SHA-256 `9b58bab24a54219af312e397566281bcdd84a84cae6f5f49d4e6eefd6e4af756`. This attachment does not cover every transitive native build input.
- The signed APK SHA-256 is `f832a2c507f997fcb047c0ab899254d1fd111520942e88da50e61ebc82e3c764`. The candidate CI APK matches it byte-for-byte.

## Preserved notices

The audit collected license texts and attribution for native and application components. See the [notice files](notices/), including [FFmpeg](notices/ffmpeg-LICENSE.md), [dav1d](notices/dav1d-COPYING), [libunibreak](notices/libunibreak-6.1-LICENCE), [Sentry native](notices/sentry-native-0.16.6-LICENSE), Chromium's [NSPR](notices/Cronet-NSPR-LICENSE) and [Mozilla URL parser](notices/Cronet-Mozilla-LICENSE.txt), [Material Icons](notices/Flutter-MaterialIcons-LICENSE.txt), and [NoSleep](notices/NoSleep-v0.12.0-LICENSE). The FFmpeg build is configured with GPL version 3 or later and has additional file-specific terms retained in the notice directory and audit evidence.

The bundled Go Noto font files are licensed under SIL OFL 1.1; their upstream generation scripts use the Unlicense. The [Go Noto v7.0 license bundle](notices/GoNoto-v7.0-UNLICENSE-and-OFL.txt) and [Noto OFL notice](notices/Noto-Latin-Greek-Cyrillic-OFL.txt) preserve the original terms. The Hangul companion font is a modified subset. Other dependencies, including Rust crates and Android toolchain runtimes, have original notices collected in the separately retained audit supplement.

## Review scope and limitations

The review traced the signed APK, rebuilt several native components, compared the candidate build to the published APK, and collected available source, notices, patches and build instructions. The application source archive is published. The current public native-input attachment is incomplete, and the expanded audit supplements have not been published as release assets.

Some missing information is not simply absent from the Plezy repository. The exact Google Maven source JARs checked for retained Google Play Services and Play Billing client implementations were unavailable at the standard URLs, and the applicable artifact-specific rights and source treatment are unresolved. The chapter model matches the upstream source and APK, but its original training inputs are not archived. Flutter engine and Chromium Cronet historical build outputs have not been fully reproduced. FriBidi relink materials were exercised on Linux; the Fire TV subtitle check remains unperformed. The APK contains upstream Plezy alternate-icon assets, and written permission under the upstream [trademark policy](https://github.com/edde746/plezy/blob/9b514179d34970496eb557f3fb425a034a9e6e17/TRADEMARKS.md) has not been found.

The project owner has chosen to defer further investigation of these remaining items. This records the decision and the substantial review completed; it does not establish that the release meets every applicable license or source-distribution condition. See the [review disposition](SOURCE-REVIEW-DISPOSITION-v1.3.9.md), [APK payload review](APK-PAYLOAD-REVIEW-v1.3.9.md), and [signoff ledger](native-v1.3.9-signoff.json).
