# Reproduce the v1.3.9 ARMv7 FFmpeg comparison

Use the release's `PowerPlay-v1.3.9-NativeSourceInputs.zip` with SHA-256 `9b58bab24a54219af312e397566281bcdd84a84cae6f5f49d4e6eefd6e4af756`. It includes the mpv-build driver, FFmpeg, dav1d, dovi_tool and OpenSSL sources and their individual digests. The supplemental review archive includes the checked Cargo sources, original notices and captured configuration.

1. Extract the mpv-build source at `/home/runner/work/mpv-build/mpv-build`. Extract the four dependency archives with their top-level directory removed under `platforms/android/deps/{ffmpeg,dav1d,libdovi,openssl}`.
2. Restore the upstream Git metadata for FFmpeg tag `n8.0.1` and dav1d tag `1.5.4` using shallow fetches of those tags and mixed resets to their manifest commits. This retains the original files and gives the historical version strings `n8.0.1` and `1.5.4-0-g54706fc`. Use the mpv-build `scripts/patches.py apply ffmpeg android platforms/android/deps/ffmpeg` from the driver root. Keep the original patch series and confirm the commits against the manifest.
3. Make Android NDK 29.0.14206865 available in the SDK's `ndk` directory. Put CMake, Ninja, Meson, pkgconf, rustup and Cargo on PATH. Use Rust 1.88.0 with the `armv7-linux-androideabi` target and set `CARGO_HOME=/home/runner/.cargo`. Keep `rust-src` outside this build toolchain. Its presence changes embedded panic paths. The driver uses the locked manifest and generates the static Dolby Vision library with `panic=abort` and PIC.
4. Export `MPV_ANDROID_SDK` to the SDK root, then run `bash platforms/android/build.sh --arch armv7l ffmpeg` from the driver root.
5. Strip the rebuilt `libavcodec.so`, `libavutil.so` and `libswresample.so` under `platforms/android/deps/ffmpeg/_build` with NDK `llvm-strip --strip-unneeded`. Compare each to the matching ELF extracted from the original signed APK using `scripts/compare_powerplay_review_elf.py ORIGINAL REBUILT` with pyelftools installed.

The verified run matched every byte after masking only the GNU build-ID descriptor. Run from the same checkout and Cargo paths because they appear in the shipped binary. See the [comparison report](evidence-v1.3.9/ffmpeg-binary-comparison.json).

The [file-level notice index](evidence-v1.3.9/ffmpeg-extra-notices.json) identifies 31 files with additional or distinct terms from 1,675 source paths observed in the matching rebuilds. Preserve the original header texts from the supplement and the original full source files.
