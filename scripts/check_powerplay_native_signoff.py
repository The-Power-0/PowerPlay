#!/usr/bin/env python3
"""Produce a fail-closed PowerPlay v1.3.9 native source-license sign-off report.

Green evidence inventory means the checks were reproducible. It does not mean
redistribution/source compliance is complete. --strict blocks promotion until
the reviewed compliance ledger and all attestations are cleared.
"""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_MAVEN_NATIVE_ORIGINS = {
    "libcronet.143.0.7445.0.so": "org.chromium.net:cronet-embedded:143.7445.0",
    "libdatastore_shared_counter.so": "androidx.datastore:datastore-core-android:1.1.7",
    "libsentry-android.so": "io.sentry:sentry-native-ndk:0.16.6",
    "libsentry.so": "io.sentry:sentry-native-ndk:0.16.6",
}
WRAPS = ("freetype2", "fribidi", "harfbuzz", "libunibreak", "fontconfig", "expat")


def read(path):
    if not path.is_file():
        raise ValueError(f"Required audit evidence missing: {path}")
    return json.loads(path.read_text())


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def check_checksums(basedir, records, key="sha256"):
    checked = 0
    for row in records:
        relative = row.get("copied_path") or row.get("path") or row.get("file")
        if not relative:
            raise ValueError(f"Source record has no file path: {row}")
        relative = Path(relative)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe source record path: {relative}")
        path = basedir / relative
        if digest(path) != row[key]:
            raise ValueError(f"Source evidence checksum mismatch: {path}")
        checked += 1
    return checked


def audit(args):
    policy = read(args.policy)
    native = read(args.native)
    gradle = read(args.gradle)
    rust = read(args.rust)
    wraps = read(args.wrap)
    pom = read(args.maven)
    if policy["release"] != native["target_release"] or native["target_release"] != gradle["target_release"]:
        raise ValueError("Source ledger and binary reports refer to different releases")
    if native["apk_sha256"] != policy["signed_apk_sha256"]:
        raise ValueError("Ledger checksum differs from the signed APK inventory")
    expected = set(policy["native_components"])
    observed = {x["name"] for x in native["libraries"]}
    if expected != observed:
        raise ValueError(f"Native library closure changed: missing={sorted(expected - observed)} "
                         f"unexpected={sorted(observed - expected)}")
    if native["unclassified_packaged_libraries"] or native["missing_expected_libraries"]:
        raise ValueError("One or more native packaged ELF identities remain unclassified")
    if native["unresolved_external_sonames"]:
        raise ValueError("Non-system native DT_NEEDED libraries missing from signed APK")

    matches = {Path(row["apk_path"]).name: row["byte_identical_gradle_sources"]
               for row in gradle["apk_native_byte_matches"]}
    for lib, expected_coordinate in REQUIRED_MAVEN_NATIVE_ORIGINS.items():
        if not any(m["coordinate"] == expected_coordinate for m in matches.get(lib, [])):
            raise ValueError(f"Missing exact signed-APK AAR byte-match for {lib}: {expected_coordinate}")

    if wraps["wrapdb_snapshot_commit"] != policy["historical_wrapdb_commit"]:
        raise ValueError("Wrong historical WrapDB snapshot")
    package_names = {x["name"] for x in wraps["components"]}
    if package_names != set(WRAPS):
        raise ValueError(f"Unexpected libass WrapDB closure: {package_names}")
    wrap_root = args.wrap.parent
    wrap_checksum_count = 0
    for component in wraps["components"]:
        source = wrap_root / component["source_file"]
        if digest(source) != component["source_sha256"]:
            raise ValueError(f"Wrong upstream source for {component['name']}")
        wrap = wrap_root / "wraps" / (component["name"] + ".wrap")
        if digest(wrap) != component["wrapdb_sha256"]:
            raise ValueError(f"Incorrect Meson wrap descriptor for {component['name']}")
        wrap_checksum_count += check_checksums(wrap_root, component["legal_texts"])
        for patch in component["meson_patches"]:
            file = wrap_root / "patches" / patch["path"]
            if digest(file) != patch["sha256"]:
                raise ValueError(f"Incorrect historical Meson patch for {component['name']}")
            wrap_checksum_count += 1
    unibreak = next(x for x in wraps["components"] if x["name"] == "libunibreak")
    if not any(Path(x["upstream_path"]).name == "LICENCE" for x in unibreak["legal_texts"]):
        raise ValueError("Known missing libunibreak LICENCE not recovered from upstream source")

    if len(rust) != 15 or len({(x["name"], x["version"]) for x in rust}) != 15:
        raise ValueError("Expected 15 lockfile-selected Rust package records")
    rust_root = args.rust.parent
    rust_texts = 0
    for component in rust:
        if not component.get("license_texts"):
            raise ValueError(f"No archived legal text for Rust crate {component['name']}")
        if component.get("crate_archive"):
            archive = rust_root / "crate-archives" / component["crate_archive"]
            if digest(archive) != component["crate_sha256_verified"]:
                raise ValueError(f"Rust crate checksum failed: {component['name']}")
        for notice in component["license_texts"]:
            file = rust_root / "crate-license-texts" / (
                component["name"] + "-" + component["version"]) / notice["name"]
            if digest(file) != notice["sha256"]:
                raise ValueError(f"Rust legal text checksum failed: {file}")
            rust_texts += 1

    count = pom["counts"]["unique_gradle_runtime_modules"]
    distinct = len({x["coordinate"] for x in gradle["gradle_artifacts"]})
    if count != distinct or len(pom["modules"]) != count:
        raise ValueError("Maven POM audit does not cover every resolved external module")
    remaining = [x for x in policy["open_blockers"] if x.get("status", "open") != "closed"]
    signed_off = (not remaining and policy["status"] == "CLEARED"
                  and policy["human_license_review_approved"]
                  and policy["version_specific_complete_source_bundle_verified"])
    findings = {
        "release": policy["release"],
        "signed_apk_sha256": policy["signed_apk_sha256"],
        "audit_integrity_passed": True,
        "native_elf_names_reconciled": len(observed),
        "maven_native_binary_byte_matches": len(REQUIRED_MAVEN_NATIVE_ORIGINS),
        "historical_wrapdb_verified_archives": len(wraps["components"]),
        "historical_wrapdb_notices_and_patch_files_verified": wrap_checksum_count,
        "rust_lockfile_crates_with_notice_text": len(rust),
        "rust_notice_files_verified": rust_texts,
        "maven_external_modules": count,
        "maven_poms_retrieved": pom["counts"]["retrieved_poms"],
        "maven_modules_with_published_license_declarations":
            pom["counts"]["modules_with_pom_license_declaration"],
        "historical_libass_binary_source_provenance_verified": False,
        "historical_libdovi_binary_source_provenance_verified": False,
        "complete_source_and_notice_signoff": signed_off,
        "release_approval": "CLEARED" if signed_off else "BLOCKED",
        "open_blockers": remaining,
        "human_review_required": True,
        "caution": "A passing evidence job is not a GPL/LGPL or license/source compliance certification.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "native-license-signoff.json").write_text(json.dumps(findings, indent=2) + "\n")
    lines = [
        "# PowerPlay v1.3.9 — native source/license sign-off state",
        "", f"**Release approval: {findings['release_approval']}**",
        "", "All available source evidence hashes were validated. This is a verification "
        "of the evidence, NOT approval of the legal or corresponding-source obligations.",
        "",
        f"- Signed native ELF components reconciled: {len(observed)}",
        f"- Historical libass WrapDB source archives verified: {len(wraps['components'])}",
        f"- Locked Rust crate license records verified: {len(rust)}",
        f"- Maven external modules examined: {count}",
        f"- Maven license declarations found: "
        f"{findings['maven_modules_with_published_license_declarations']}",
        "", "## Outstanding sign-off blockers", "",
    ]
    for row in remaining:
        lines += [f"### {row['id']} — {row['area']}", "",
                  row["detail"], "", "**Evidence needed:** " + row["required_evidence"], ""]
    lines += ["**Do not use this report to claim full native source or license compliance.**"]
    (args.output / "native-license-signoff.md").write_text("\n".join(lines) + "\n")
    print("Verified available source evidence; release status: " + findings["release_approval"])
    print(f"Blocking obligations: {len(remaining)}")
    return signed_off


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--gradle", type=Path, required=True)
    parser.add_argument("--rust", type=Path, required=True)
    parser.add_argument("--wrap", type=Path, required=True)
    parser.add_argument("--maven", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true",
                        help="Fail release promotion until complete source/license sign-off")
    args = parser.parse_args()
    approved = audit(args)
    if args.strict and not approved:
        parser.error("NOT CLEARED: full native corresponding source/license sign-off blockers remain")


if __name__ == "__main__":
    main()
