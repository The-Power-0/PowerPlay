#!/usr/bin/env bash
# Audit-only build of the original Sentry 0.16.6 Android libraries.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo 'Usage: rebuild_powerplay_sentry.sh SENTRY_SOURCE NDK_R27 NEW_OUTPUT' >&2
  exit 2
fi
source_dir=$(realpath "$1")
ndk_dir=$(realpath "$2")
output_dir=$(realpath -m "$3")
test ! -e "$output_dir"
test -f "$source_dir/external/libunwindstack-ndk/cmake/CMakeLists.txt"
grep -qx 'Pkg.Revision = 27.0.12077973' "$ndk_dir/source.properties"
mkdir -p "$output_dir"
prefix_map="-ffile-prefix-map=$source_dir=/home/runner/work/sentry-native/sentry-native"
cmake -S "$source_dir/ndk/lib" -B "$output_dir/build" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$ndk_dir/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=armeabi-v7a -DANDROID_PLATFORM=android-21 \
  -DANDROID_STL=c++_static -DSENTRY_NATIVE_SRC="$source_dir" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_C_FLAGS="$prefix_map" -DCMAKE_CXX_FLAGS="$prefix_map"
cmake --build "$output_dir/build" --parallel 8
strip_tool="$ndk_dir/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"
"$strip_tool" --strip-unneeded -o "$output_dir/libsentry.so" \
  "$output_dir/build/sentry_build/libsentry.so"
"$strip_tool" --strip-unneeded -o "$output_dir/libsentry-android.so" \
  "$output_dir/build/libsentry-android.so"
ninja -C "$output_dir/build" -t deps > "$output_dir/header-inputs.txt"
echo 'Compare both outputs with the signed APK using compare_powerplay_review_elf.py.'
