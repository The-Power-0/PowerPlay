#!/usr/bin/env python3
"""Inventory the exact PowerPlay Fire TV APK's ELF libraries and their DT_NEEDED edges.

This is a binary inventory, NOT a license-compliance certification. In
particular, static dependencies inside ELF files are not visible to readelf.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

KNOWN = {
    "libapp.so": ("PowerPlay Flutter AOT", "GPL-3.0-only", "Tracked application source"),
    "libflutter.so": ("Flutter Android engine", "BSD-3-Clause and third-party notices", "Flutter engine revision/source still needs binary mapping"),
    "libavcodec.so": ("FFmpeg 8.0.1 plus static dependencies", "GPL-3.0-or-later (build flags)", "mpv-build FFmpeg patches, dav1d/OpenSSL/libdovi and further source verification"),
    "libavutil.so": ("FFmpeg 8.0.1", "GPL-3.0-or-later (build flags)", "mpv-build FFmpeg source/patches; check compiled third-party code"),
    "libswresample.so": ("FFmpeg 8.0.1", "GPL-3.0-or-later (build flags)", "mpv-build FFmpeg source/patches"),
    "libffmpegJNI.so": ("PowerPlay Media3 FFmpeg adapter", "GPL-3.0-only application; verify upstream file notices", "Tracked JNI source; verify Media3 source attribution"),
    "libdovi_bridge.so": ("PowerPlay bridge with static libdovi and Rust crates", "GPL-3.0-only wrapper; libdovi MIT plus crate licenses", "Rust resolved crate closure/build recipe not archived"),
    "libasskt.so": ("PowerPlay subtitle JNI with static libass", "GPL-3.0-only wrapper; ISC and several third-party licenses", "Six wrapped static dependency revisions/sources not archived"),
    "libc++_shared.so": ("Android NDK libc++ runtime (mpv AAR copy)", "Apache-2.0 WITH LLVM-exception (verify binary revision)", "Source/toolchain revision and copy verification pending"),
}
REQUIRED = frozenset(("libapp.so", "libflutter.so", "libavcodec.so",
                      "libavutil.so", "libswresample.so", "libffmpegJNI.so",
                      "libdovi_bridge.so", "libasskt.so", "libc++_shared.so"))
ANDROID_SYSTEM_LIBRARIES = frozenset((
    "libandroid.so", "liblog.so", "libc.so", "libm.so", "libdl.so",
    "libz.so", "libEGL.so", "libGLESv1_CM.so", "libGLESv2.so",
    "libGLESv3.so", "libOpenSLES.so", "libmediandk.so",
    "libjnigraphics.so", "libvulkan.so", "libaaudio.so",
    "libnativewindow.so", "libsync.so", "libcamera2ndk.so",
    "libbinder_ndk.so", "libatomic.so", "libstdc++.so",
))


def identity(name):
    if name in KNOWN:
        component, license_id, gap = KNOWN[name]
        return dict(component=component, license=license_id, source_gap=gap,
                    classification="mapped-needs-source-verification")
    if name.startswith("libcronet") or "cronet" in name.lower():
        return dict(component="Chromium Cronet embedded", license="BSD-style + Chromium third-party notices; verify exact distribution",
                    source_gap="Exact Chromium revision, bundled third-party notices and source mapping pending",
                    classification="mapped-needs-source-verification")
    return dict(component="Unclassified bundled ELF", license="UNKNOWN",
                source_gap="Determine origin, licenses, dependency closure, and corresponding source",
                classification="unclassified")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def needed_from_elf(filename, data, root):
    if not shutil.which("readelf"):
        return {"error": "readelf unavailable; DT_NEEDED not inspected"}
    path = root / filename
    path.write_bytes(data)
    process = subprocess.run(["readelf", "-d", str(path)], capture_output=True, text=True)
    if process.returncode:
        return {"error": process.stderr.strip()[:400]}
    return {"dt_needed": re.findall(r"\(NEEDED\).*Shared library: \[([^\]]+)\]", process.stdout)}


def audit(apk, expected_sha, output):
    actual = sha256(apk.read_bytes())
    if expected_sha and actual != expected_sha.lower():
        raise ValueError(f"APK SHA256 mismatch: expected {expected_sha}, got {actual}")
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory() as tmp:
        library_paths = sorted(name for name in archive.namelist()
                               if name.startswith("lib/") and name.endswith(".so"))
        for i, path in enumerate(library_paths):
            parts = path.split("/")
            if len(parts) != 3:
                raise ValueError(f"Unexpected packaged native library path: {path}")
            data = archive.read(path)
            if data[:4] != b"\x7fELF":
                raise ValueError(f"Not ELF: {path}")
            name = parts[2]
            item = dict(path=path, name=name, abi=parts[1],
                        size=len(data), sha256=sha256(data), **identity(name))
            item.update(needed_from_elf(f"lib-{i}.so", data, Path(tmp)))
            entries.append(item)
    abis = sorted({entry["abi"] for entry in entries})
    names = {entry["name"] for entry in entries}
    missing = sorted(REQUIRED - names)
    unclassified = sorted(e["path"] for e in entries if e["classification"] == "unclassified")
    unresolved_sonames = sorted({
        dep for entry in entries for dep in entry.get("dt_needed", [])
        if dep not in names and dep not in ANDROID_SYSTEM_LIBRARIES
    })
    report = {
        "target_release": "powerplay-v1.3.9",
        "apk_sha256": actual,
        "abi_list": abis,
        "library_count": len(entries),
        "missing_expected_libraries": missing,
        "unclassified_packaged_libraries": unclassified,
        "unresolved_external_sonames": unresolved_sonames,
        "source_coverage_complete": False,
        "limitations": [
            "ELF enumeration does not reveal statically linked crates, C/C++ archives, or embedded binary assets.",
            "DT_NEEDED reports dynamic links only; system libraries do not ship in this APK.",
            "License classification is provisional until corresponding sources, file notices, and build flags are verified.",
            "Full Gradle/Flutter transitive resolved graph is a separate evidence artifact.",
            "This does not certify that the release is compliant or that its source bundle is complete."
        ],
        "libraries": entries,
    }
    (output / "native-elf-inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# PowerPlay 1.3.9 — APK native ELF inventory",
        "",
        f"APK SHA256: {actual}",
        f"ABIs: {', '.join(abis) or '(none)'}",
        f"ELF count: {len(entries)}",
        "",
        "| APK ELF path | Component | License hypothesis | Provenance/source work |",
        "| --- | --- | --- | --- |",
    ]
    for entry in entries:
        cells = [entry["path"], entry["component"], entry["license"], entry["source_gap"]]
        lines.append("| " + " | ".join(s.replace("|", "/").replace("\n", " ") for s in cells) + " |")
    lines.extend([
        "",
        "## Unclassified packaged libraries",
        ", ".join(unclassified) if unclassified else "None by filename (this does not prove source completeness).",
        "",
        "## Expected libraries missing",
        ", ".join(missing) if missing else "None.",
        "",
        "## Non-system DT_NEEDED names not found inside APK",
        ", ".join(unresolved_sonames) if unresolved_sonames else "None identified.",
        "",
        "**This inventory is not a full license/source compliance sign-off.**",
    ])
    (output / "native-elf-inventory.md").write_text("\n".join(lines) + "\n")
    print(f"APK SHA256 {actual}; {len(entries)} ELF libraries; {len(unclassified)} unclassified.")
    print(f"Unresolved external DT_NEEDED: {unresolved_sonames}")
    if abis != ["armeabi-v7a"]:
        raise ValueError(f"Fire TV release expected armeabi-v7a only, got {abis}")
    if any("mpv" in n.lower() for n in names):
        raise ValueError("MPV player runtime unexpectedly packaged")
    if missing:
        raise ValueError(f"Expected native libraries absent: {missing}")
    return len(unclassified)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--expected-sha256", default="")
    parser.add_argument("--output", type=Path, default=Path("native-license-audit"))
    parser.add_argument("--fail-unclassified", action="store_true")
    args = parser.parse_args()
    unclassified = audit(args.apk, args.expected_sha256, args.output)
    if args.fail_unclassified and unclassified:
        parser.error("Unclassified APK libraries remain; inspect the JSON inventory")


if __name__ == "__main__":
    main()
