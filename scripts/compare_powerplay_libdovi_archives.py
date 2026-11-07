#!/usr/bin/env python3
"""Compare historical libdovi Android ARMv7 archive with a pinned source rebuild.

The upstream build on March 4, 2026 used cargo build without --locked.
Rust 1.93.1 was the stable toolchain available at that date.
"""
import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def original_library(path):
    with tarfile.open(path, "r:gz") as archive:
        libs = [m for m in archive.getmembers() if m.isfile()
                and Path(m.name).name == "libdovi.a"]
        if len(libs) != 1:
            raise ValueError(f"Expected one libdovi.a, found {len(libs)}")
        return archive.extractfile(libs[0]).read()


def ar_members(path, tool):
    result = subprocess.run([tool, "t", str(path)], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Archive inspection failed: {result.stderr[:300]}")
    return result.stdout.splitlines()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published-tar", type=Path, required=True)
    parser.add_argument("--rebuilt-lib", type=Path, required=True)
    parser.add_argument("--lock-before", type=Path, required=True)
    parser.add_argument("--lock-after", type=Path, required=True)
    parser.add_argument("--ar-tool", default="ar")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = original_library(args.published_tar)
    rebuilt = args.rebuilt_lib.read_bytes()
    with tempfile.TemporaryDirectory(prefix="libdovi-repro-") as tmp:
        original_file = Path(tmp) / "published.a"
        original_file.write_bytes(original)
        old_members = ar_members(original_file, args.ar_tool)
        new_members = ar_members(args.rebuilt_lib, args.ar_tool)
    same_lockfile = args.lock_before.read_bytes() == args.lock_after.read_bytes()
    same_bytes = rebuilt == original
    result = {
        "release": "PowerPlay v1.3.9 uses libdovi prebuilt v2.3.1",
        "target": "armv7-linux-androideabi",
        "upstream_build_date": "2026-03-04",
        "historical_expected_stable_rust": "1.93.1",
        "published_libdovi_sha256": sha256(original),
        "reproduced_libdovi_sha256": sha256(rebuilt),
        "original_bytes": len(original),
        "rebuilt_bytes": len(rebuilt),
        "byte_identical": same_bytes,
        "cargo_lock_unchanged_by_historical_unlocked_command": same_lockfile,
        "cargo_lock_before_sha256": sha256(args.lock_before.read_bytes()),
        "cargo_lock_after_sha256": sha256(args.lock_after.read_bytes()),
        "published_archive_members": len(old_members),
        "rebuilt_archive_members": len(new_members),
        "member_sequence_equal": old_members == new_members,
        "published_only_member_names": sorted(set(old_members) - set(new_members)),
        "rebuilt_only_member_names": sorted(set(new_members) - set(old_members)),
        "limitations": [
            "A non-identical rebuild does not establish which build inputs were different.",
            "The original prebuilt did not preserve a resolved Cargo artifact manifest or exact compiler options.",
            "Cargo.lock unchanged in a modern reproduction supports, but does not prove, historical resolution.",
            "An archive match alone does not satisfy all Rust transitive license/notice obligations.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "libdovi-armv7-rebuild-comparison.json").write_text(
        json.dumps(result, indent=2) + "\n")
    (args.output / "published-archive-members.txt").write_text("\n".join(old_members) + "\n")
    (args.output / "rebuilt-archive-members.txt").write_text("\n".join(new_members) + "\n")
    (args.output / "README.md").write_text(
        "# PowerPlay v1.3.9 libdovi ARMv7 reproducibility\n\n"
        f"Original SHA256: {result['published_libdovi_sha256']}\n"
        f"Rebuilt SHA256: {result['reproduced_libdovi_sha256']}\n"
        f"Byte identical: {same_bytes}\n"
        f"Cargo.lock unchanged during the historical unlocked command: {same_lockfile}\n\n"
        "This comparison is evidence rather than complete distribution signoff.\n")
    print(f"libdovi v2.3.1 ARMv7: identical={same_bytes}; "
          f"Cargo.lock unchanged={same_lockfile}; "
          f"members {len(old_members)} vs {len(new_members)}")


if __name__ == "__main__":
    main()
