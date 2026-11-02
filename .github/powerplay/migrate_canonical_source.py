#!/usr/bin/env python3
"""Replace legacy repository-root app files with the exact v1.2.4 released source.

Only application and toolchain paths are imported. GitHub release machinery,
PowerPlay documentation and repo policy files remain untouched. The migration
is repeatable and rejects unexpected provenance or a mismatched source tree.
"""
import argparse
import filecmp
import json
import subprocess
from pathlib import Path

DIRS = (
    "lib", "android", "assets", "test", "packages", "scripts",
    "windows", "ios", "tvos", "macos", "linux", "website",
    "server", "shared", "Casks", ".maestro", ".githooks",
)
FILES = (
    "pubspec.yaml", "pubspec.lock", "analysis_options.yaml",
    "build.yaml", "slang.yaml", "relay_protocol.json",
    "devtools_options.yaml", ".metadata", ".gitignore",
    ".editorconfig", ".gitattributes", ".clang-format", ".swift-format",
    ".dockerignore", "mpv-build.lock.json",
    "POWERPLAY-RELEASE-NOTICE.md",
)
OLD_PATCH_MACHINERY = (
    "apply_121_upstream_fixes.py", "apply_124_theme_ui.py",
    "apply_curated_theme_to_release.py", "apply_next_version.py",
    "apply_rebrand.py", "apply_transparent_splash.py",
    "fix_splash_background.py", "test_fix_splash_background.py",
    "check_next_version.py", "approved-artwork.tar.gz.b64",
    "library-defaults.patch", "next-version.patch",
)

def require(root, name, pieces):
    value = (root / name).read_text()
    for piece in pieces:
        if piece not in value:
            raise SystemExit(f"Invalid published source: {name} missing {piece!r}")

def run(*cmd):
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    dest = args.repo.resolve()
    if source == dest or not (dest / ".git").is_dir():
        raise SystemExit("Expected separate extracted source and destination Git checkout")
    manifest = json.loads((dest / ".github/powerplay/release.json").read_text())
    if manifest["version"] != "1.2.4" or manifest["build_number"] != 10204:
        raise SystemExit("Migration must start with verified v1.2.4+10204 source")
    require(source, "pubspec.yaml", ["version: 1.2.4+10204"])
    require(source, "android/app/build.gradle.kts", ['applicationId = "com.power.powerplay"'])
    require(source, "lib/theme/powerplay_palette.dart", ["aurora(", "synthwave(", "midnightGold(", "oceanDepths("])
    require(source, "lib/focus/focusable_wrapper.dart", ["if ((targetOffset - currentOffset).abs() < 0.5) return;"])
    require(source, "lib/main.dart", ["assets/powerplay_splash.png"])
    require(source, "pubspec.yaml", ["assets/powerplay_splash.png"])
    for file in ("assets/powerplay_splash.png", "android/app/src/main/res/drawable-nodpi/powerplay_splash_foreground.png"):
        data = (source / file).read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n" or data[25] != 6:
            raise SystemExit(f"Not an RGBA transparent PNG: {file}")
    if not (source / "LICENSE").is_file():
        raise SystemExit("Original GPLv3 license missing")
    for folder in DIRS:
        src, dst = source / folder, dest / folder
        if not src.is_dir():
            raise SystemExit(f"Expected application source folder missing: {folder}")
        dst.mkdir(parents=True, exist_ok=True)
        # Clean generated development caches from the historic tarball.
        # Preserve real native libraries, resource assets and vendored packages.
        run("rsync", "-a", "--delete",
            "--exclude=build/", "--exclude=.dart_tool/",
            "--exclude=.gradle/", "--exclude=__pycache__/",
            "--exclude=.DS_Store", "--exclude=local.properties",
            "--exclude=key.properties", "--exclude=*.keystore",
            str(src) + "/", str(dst) + "/")
    for file in FILES:
        src = source / file
        if not src.is_file():
            raise SystemExit(f"Expected source configuration missing: {file}")
        (dest / file).write_bytes(src.read_bytes())
    # The actual released source is now the repository root. Remove patch
    # machinery that previously modified an archived 1.0.0 source at build time.
    for name in OLD_PATCH_MACHINERY:
        path = dest / ".github/powerplay" / name
        if path.exists():
            path.unlink()
    for name in (
        "lib/main.dart", "lib/theme/powerplay_palette.dart",
        "android/app/build.gradle.kts", "pubspec.yaml",
        "assets/powerplay_splash.png",
        "android/app/src/main/res/drawable-nodpi/powerplay_splash_foreground.png",
    ):
        if not filecmp.cmp(source / name, dest / name, shallow=False):
            raise SystemExit(f"Canonical source mismatch after copy: {name}")
    # No outside-the-repo files have been copied by this script.
    print("PASS: Git repository now contains verified PowerPlay 1.2.4 application source")
    print("PASS: old build-time patch scripts removed; README, releases and GitHub workflows retained")

if __name__ == "__main__":
    main()
