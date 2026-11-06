#!/usr/bin/env python3
"""Preserve lockfile-derived Rust crate source files and license notices.

The upstream libdovi binary was built without --locked. This captures an exact
present-day lockfile closure for source review, NOT the historical binary lock.
"""
import argparse
import hashlib
import json
import re
import shutil
import tarfile
import tomllib
from pathlib import Path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--components", type=Path, required=True)
    parser.add_argument("--lockfile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.components.read_text())
    locked = {(p["name"], p["version"]): p for p in tomllib.loads(args.lockfile.read_text())["package"]}
    archive_dir = args.output / "crate-archives"
    notices_dir = args.output / "crate-license-texts"
    archive_dir.mkdir(parents=True, exist_ok=True)
    notices_dir.mkdir(parents=True, exist_ok=True)
    sources = []
    errors = []
    for row in rows:
        name, version = row["name"], row["version"]
        lock = locked.get((name, version))
        if lock is None:
            errors.append(f"{name}-{version}: absent from pinned dolby_vision Cargo.lock")
            continue
        source = lock.get("source", "(local source)")
        record = {
            "name": name,
            "version": version,
            "license_expression_from_metadata": row["license"],
            "source": source,
            "historical_binary_resolution_verified": False,
        }
        if not source.startswith("registry+"):
            record["status"] = "pinned-dovi-tool-local-package"
            sources.append(record)
            continue
        filename = f"{name}-{version}.crate"
        expected = lock.get("checksum")
        if not expected:
            errors.append(f"{filename}: no registry checksum in Cargo.lock")
            continue
        cached = sorted((Path.home() / ".cargo" / "registry" / "cache").glob("*/" + filename))
        matches = [path for path in cached if sha256(path.read_bytes()) == expected]
        if len(matches) != 1:
            errors.append(f"{filename}: {len(matches)} matching registry tarballs (expected SHA256 {expected})")
            continue
        archive = matches[0]
        shutil.copy2(archive, archive_dir / filename)
        record.update({
            "crate_archive": filename,
            "crate_sha256_verified": expected,
            "license_texts": [],
            "status": "lockfile-selected-source-not-historical-binary-attestation",
        })
        with tarfile.open(archive, "r:gz") as package:
            for member in package.getmembers():
                if not member.isfile() or member.size > 524288:
                    continue
                basename = Path(member.name).name
                if basename == "Cargo.toml" and member.name.count("/") == 1:
                    try:
                        manifest = tomllib.loads(package.extractfile(member).read().decode("utf-8"))
                        record["license_expression_from_crate_manifest"] = manifest.get("package", {}).get("license", "")
                    except (UnicodeDecodeError, ValueError):
                        record["license_expression_from_crate_manifest"] = "(cannot parse crate manifest)"
                if not re.match(r"^(LICENSE|LICENCE|COPYING|NOTICE|COPYRIGHT)([._-].*)?$",
                                basename, re.IGNORECASE):
                    continue
                data = package.extractfile(member).read()
                if b"\x00" in data:
                    continue
                target = notices_dir / f"{name}-{version}" / basename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                record["license_texts"].append({
                    "name": basename, "sha256": sha256(data)
                })
        sources.append(record)
    (args.output / "manifest.json").write_text(json.dumps(sources, indent=2) + "\n")
    (args.output / "PROVENANCE-LIMITATION.txt").write_text(
        "Cargo.lock-selected source and crate licenses are not proof of the exact\n"
        "dependency resolution or toolchain used for the historical unlocked prebuilt.\n"
    )
    if errors:
        raise SystemExit("Missing checksum-verified crates: " + "; ".join(errors))
    print(f"Preserved {len(sources)} local/registry Rust components")


if __name__ == "__main__":
    main()
