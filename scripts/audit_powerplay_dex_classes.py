#!/usr/bin/env python3
"""Inventory defined Java/Kotlin classes in the exact signed PowerPlay APK DEX.

The external Gradle graph alone does not establish which Google Play Services
(or other) classes survive shrinking. This directly parses DEX class_defs.
Obfuscation means absence of a recognizable package is NOT proof the vendor's
code is absent. This is binary evidence, not a license conclusion.
"""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

APK_SHA = "f832a2c507f997fcb047c0ab899254d1fd111520942e88da50e61ebc82e3c764"
PREFIXES = {
    "google_play_services": "Lcom/google/android/gms/",
    "google_datatransport": "Lcom/google/android/datatransport/",
    "firebase": "Lcom/google/firebase/",
    "google_tink": "Lcom/google/crypto/tink/",
    "chromium_cronet": "Lorg/chromium/net/",
    "sentry": "Lio/sentry/",
    "androidx_media3": "Landroidx/media3/",
    "androidx_datastore": "Landroidx/datastore/",
    "androidx_work": "Landroidx/work/",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def uint32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Malformed DEX access at offset {offset}")
    return struct.unpack_from("<I", data, offset)[0]


def uleb_skip(data, offset):
    for _ in range(5):
        if offset >= len(data):
            raise ValueError("Malformed DEX string UTF-16 length")
        byte = data[offset]
        offset += 1
        if byte & 0x80 == 0:
            return offset
    raise ValueError("DEX ULEB128 length exceeds five bytes")


def dex_defined_classes(data):
    if len(data) < 112 or data[:4] != b"dex\n" or data[7] != 0:
        raise ValueError("Not a standard Android DEX file")
    size = uint32(data, 32)
    if size != len(data):
        raise ValueError(f"DEX header size mismatch {size} != {len(data)}")
    string_size, string_off = uint32(data, 56), uint32(data, 60)
    type_size, type_off = uint32(data, 64), uint32(data, 68)
    class_size, class_off = uint32(data, 96), uint32(data, 100)
    if any((
        string_off + 4 * string_size > len(data),
        type_off + 4 * type_size > len(data),
        class_off + 32 * class_size > len(data),
    )):
        raise ValueError("DEX index array goes beyond end of file")
    descriptors = []
    for i in range(class_size):
        type_index = uint32(data, class_off + 32 * i)
        if type_index >= type_size:
            raise ValueError("DEX class_def references invalid type index")
        string_index = uint32(data, type_off + 4 * type_index)
        if string_index >= string_size:
            raise ValueError("DEX type references invalid string index")
        string_data_off = uint32(data, string_off + 4 * string_index)
        start = uleb_skip(data, string_data_off)
        end = data.find(b"\0", start, min(len(data), start + 8192))
        if end < 0:
            raise ValueError("Missing DEX class descriptor string terminator")
        descriptor = data[start:end].decode("ascii", "replace")
        if not descriptor.startswith("L") or not descriptor.endswith(";"):
            raise ValueError("Unexpected DEX class descriptor " + descriptor[:100])
        descriptors.append(descriptor)
    return descriptors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    actual = sha256(args.apk.read_bytes())
    if actual != APK_SHA:
        parser.error(f"Published signed APK SHA256 mismatch: {actual}")
    dex_files = []
    named = {key: [] for key in PREFIXES}
    all_classes = set()
    with zipfile.ZipFile(args.apk) as apk:
        dex_entries = sorted(path for path in apk.namelist()
                             if path.startswith("classes") and path.endswith(".dex")
                             and "/" not in path)
        if not dex_entries:
            parser.error("Signed APK contains no top-level DEX files")
        for entry in dex_entries:
            data = apk.read(entry)
            classes = dex_defined_classes(data)
            duplicates = all_classes.intersection(classes)
            if duplicates:
                parser.error(f"Duplicate DEX class definitions: {sorted(duplicates)[:5]}")
            all_classes.update(classes)
            for desc in classes:
                for kind, prefix in PREFIXES.items():
                    if desc.startswith(prefix):
                        named[kind].append(desc)
            dex_files.append({
                "apk_path": entry, "sha256": sha256(data),
                "byte_length": len(data),
                "dex_version": data[4:7].decode("ascii"),
                "defined_classes": len(classes),
            })
    result = {
        "release": "powerplay-v1.3.9",
        "published_apk_sha256": APK_SHA,
        "top_level_dex_entries": dex_files,
        "total_defined_classes": len(all_classes),
        "recognized_package_counts": {key: len(value) for key, value in named.items()},
        "recognized_package_examples": {
            key: sorted(value)[:25] for key, value in named.items()
        },
        "limitations": [
            "DEX class_defs is exact for classes in the published artifact, but R8 can rename classes.",
            "A zero recognizable package count is NOT proof no vendor code remains.",
            "DEX does not report native ELF code, resources, statically linked binaries or dynamically loaded classes.",
            "Gradle resolution includes components that might be removed by shrinking.",
            "No GPL compatibility, license coverage or corresponding source sign-off is implied.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "dex-defined-class-inventory.json").write_text(
        json.dumps(result, indent=2) + "\n")
    lines = [
        "# Signed PowerPlay v1.3.9 DEX defined-class evidence", "",
        f"SHA256: {actual}",
        f"DEX entries: {len(dex_files)}",
        f"Total non-duplicated defined classes: {len(all_classes)}",
        "", "| Recognizable source namespace | Defined classes |",
        "| --- | ---: |",
    ]
    for name, descriptors in named.items():
        lines.append(f"| {name} | {len(descriptors)} |")
    lines += [
        "", "These are exact **defined classes**, not generic DEX string matches.",
        "Obfuscation and class rewriting limit package-name attribution.",
        "**No license or source-closure clearance is implied.**",
    ]
    (args.output / "dex-defined-class-inventory.md").write_text("\n".join(lines) + "\n")
    print(f"DEX files={len(dex_files)}; defined classes={len(all_classes)}; "
          f"recognizable Play Services classes={len(named['google_play_services'])}")


if __name__ == "__main__":
    main()
