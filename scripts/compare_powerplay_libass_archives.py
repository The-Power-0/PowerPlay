#!/usr/bin/env python3
"""Compare published libass Android ARMv7 static archive to a source-rebuild.

Byte-for-byte identity would be strong evidence. If not identical, record
precise hash/member differences without claiming source provenance.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

ENTRY = "libass-android-0.18.3/lib/armeabi-v7a/libass.a"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def members(path, ar_tool):
    p = subprocess.run([ar_tool, "t", str(path)], capture_output=True, text=True)
    if p.returncode:
        raise ValueError(f"Archive member inspection failed: {p.stderr[:350]}")
    return p.stdout.splitlines()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-zip", type=Path, required=True)
    parser.add_argument("--rebuilt-zip", type=Path, required=True)
    parser.add_argument("--ar-tool", default="llvm-ar")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.original_zip) as old, zipfile.ZipFile(args.rebuilt_zip) as new:
        before, after = old.read(ENTRY), new.read(ENTRY)
    with tempfile.TemporaryDirectory(prefix="libass-rebuild-comparison-") as tmp:
        before_path, after_path = Path(tmp) / "published.a", Path(tmp) / "rebuilt.a"
        before_path.write_bytes(before)
        after_path.write_bytes(after)
        old_members = members(before_path, args.ar_tool)
        new_members = members(after_path, args.ar_tool)
    identical = before == after
    result = {
        "target": "PowerPlay v1.3.9 pinned edde746/libass 0.18.3 armv7 static archive",
        "published_archive_sha256": sha256(before),
        "rebuilt_archive_sha256": sha256(after),
        "published_archive_size": len(before),
        "rebuilt_archive_size": len(after),
        "byte_identical": identical,
        "published_archive_members": len(old_members),
        "rebuilt_archive_members": len(new_members),
        "same_archive_member_sequence": old_members == new_members,
        "published_only_archive_member_names": sorted(set(old_members) - set(new_members)),
        "rebuilt_only_archive_member_names": sorted(set(new_members) - set(old_members)),
        "build_provenance_proven_exactly": identical,
        "limitations": [
            "The historical upstream build did not record WrapDB resolved inputs or a fully pinned Meson version.",
            "A mismatch can reflect toolchain, flags, packaging or source changes; inspect before attributing causality.",
            "A matching libass.a does not independently certify all LGPL-2.1/GPLv3 distribution obligations.",
            "This compares the upstream combined static archive, not the linked libasskt.so itself.",
        ],
    }
    (args.output / "libass-armv7-rebuild-comparison.json").write_text(
        json.dumps(result, indent=2) + "\n")
    (args.output / "published-archive-members.txt").write_text(
        "\n".join(old_members) + "\n")
    (args.output / "rebuilt-archive-members.txt").write_text(
        "\n".join(new_members) + "\n")
    (args.output / "README.md").write_text(
        "# PowerPlay 1.3.9 libass ARMv7 reproducibility comparison\n\n"
        f"- Published archive SHA256: \`{sha256(before)}\`\n"
        f"- Source-rebuilt SHA256: \`{sha256(after)}\`\n"
        f"- Identical bytes: **{identical}**\n"
        f"- Identical archive member order: **{old_members == new_members}**\n\n"
        "Build uses the publicly time-qualified July 10, 2026 Meson WrapDB "
        "snapshot and an NDK version equal to the upstream build recipe. "
        "Original Meson version and all ephemeral build inputs were not "
        "preserved; differing binaries do not identify which input changed.\n"
    )
    print(f"libass 0.18.3 armeabi-v7a: byte identical={identical}; "
          f"archive members {len(old_members)} vs {len(new_members)}")


if __name__ == "__main__":
    main()
