#!/usr/bin/env python3
"""Inventory exact Gradle release AAR/JAR binaries and their embedded notices.

The Gradle init script emits source releaseRuntimeClasspath paths; this script
hashes each resolved artifact, scans its distribution notices and maps native
payloads byte-for-byte to the exact signed APK. This is *evidence*, not clearance.
"""
import argparse
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

NOTICE_NAME = re.compile(r"(^|/)(?:LICENSE|LICENCE|COPYING|NOTICE|COPYRIGHT)(?:$|[._-])", re.I)
APK_SHA = "f832a2c507f997fcb047c0ab899254d1fd111520942e88da50e61ebc82e3c764"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scan_archive(path, notices_dir, artifact_index, depth=0):
    notices = []
    natives = []
    poms = []
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            name = entry.filename
            if entry.is_dir():
                continue
            if (name.startswith("jni/") or name.startswith("lib/")) and name.endswith(".so"):
                data = archive.read(entry)
                if data[:4] == b"\x7fELF":
                    natives.append({"archive_path": name, "sha256": digest(data), "size": len(data)})
            if NOTICE_NAME.search(name) and entry.file_size <= 524288:
                data = archive.read(entry)
                # Do not misclassify binary or nontext entries as legal text.
                if b"\0" not in data:
                    target = notices_dir / f"artifact-{artifact_index:03d}" / name
                    if ".." not in Path(name).parts and not name.startswith("/"):
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                        notices.append({"archive_path": name, "copied_to": str(target), "sha256": digest(data)})
            if name.lower().endswith("/pom.xml") and name.startswith("META-INF/maven/"):
                poms.append(name)
            if name == "classes.jar" and depth == 0:
                # Some AAR notice files are embedded in classes.jar, not AAR root.
                import io
                try:
                    nested = scan_archive(io.BytesIO(archive.read(entry)), notices_dir,
                                          artifact_index, depth=1)
                    notices.extend([dict(n, archive_path="classes.jar!" + n["archive_path"])
                                    for n in nested["notices"]])
                except zipfile.BadZipFile:
                    pass
    return {"notices": notices, "natives": natives, "maven_poms": poms}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gradle-json", type=Path, required=True)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if digest(args.apk.read_bytes()) != APK_SHA:
        parser.error("Published PowerPlay 1.3.9 APK SHA256 mismatch")
    rows = json.loads(args.gradle_json.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    notices_dir = args.output / "gradle-embedded-notices"
    apk_libs = {}
    with zipfile.ZipFile(args.apk) as apk:
        for name in apk.namelist():
            if name.startswith("lib/") and name.endswith(".so"):
                data = apk.read(name)
                apk_libs[name] = digest(data)
    matches = defaultdict(list)
    artifacts = []
    for index, row in enumerate(rows):
        file = Path(row["path"])
        if not file.is_file():
            raise FileNotFoundError(f"Gradle resolved artifact no longer accessible: {file}")
        data_hash = digest(file.read_bytes())
        item = {key: row.get(key, "") for key in ("coordinate", "name", "component_type", "variant")}
        item.update({"sha256": data_hash, "size": file.stat().st_size, "notices": [],
                     "natives": [], "maven_poms": []})
        if zipfile.is_zipfile(file):
            scanned = scan_archive(file, notices_dir, index)
            item.update(scanned)
            for native in scanned["natives"]:
                for apk_path, apk_hash in apk_libs.items():
                    if native["sha256"] == apk_hash:
                        matches[apk_path].append({"coordinate": row["coordinate"],
                                                  "artifact": row["name"],
                                                  "archive_path": native["archive_path"]})
        artifacts.append(item)
    coverage = [{"apk_path": path, "sha256": sha,
                 "byte_identical_gradle_sources": matches.get(path, [])}
                for path, sha in sorted(apk_libs.items())]
    report = {
        "target_release": "powerplay-v1.3.9",
        "published_apk_sha256": APK_SHA,
        "resolved_artifact_count": len(artifacts),
        "embedded_notice_artifact_count": sum(bool(a["notices"]) for a in artifacts),
        "artifacts_without_embedded_notice_count": sum(not a["notices"] for a in artifacts),
        "native_apk_match_count": sum(bool(x["byte_identical_gradle_sources"]) for x in coverage),
        "total_apk_native_count": len(coverage),
        "gradle_artifacts": artifacts,
        "apk_native_byte_matches": coverage,
        "limitations": [
            "Absence of a license file inside an AAR/JAR does not establish its license or noncompliance.",
            "Gradle resolution alone does not prove which classes or resources survived R8 shrinking.",
            "Flutter engine, Dart AOT, native_assets and app-built JNI libraries may not originate in AARs.",
            "Embedded Maven POM names are recorded, but legal terms must be checked against exact source.",
            "Statically linked native dependencies, Rust crates and Chromium bundled code are not resolved here.",
            "No source coverage or redistribution compliance is certified by this report."
        ]
    }
    (args.output / "gradle-runtime-artifacts.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# PowerPlay v1.3.9 Gradle runtime binary/notice inventory", "",
        f"Resolved runtime artifacts: {len(artifacts)}",
        f"Artifacts with one or more embedded notice files: {report['embedded_notice_artifact_count']}",
        f"Artifacts without embedded notices: {report['artifacts_without_embedded_notice_count']}",
        f"APK ELF libraries byte-matched to Gradle AARs: {report['native_apk_match_count']}/{len(coverage)}",
        "", "## Published APK native libraries mapped by SHA256", "",
        "| APK library | Byte-identical Gradle artifact |",
        "| --- | --- |",
    ]
    for lib in coverage:
        matches_text = ", ".join(v["coordinate"] + " (" + v["artifact"] + ")"
                                 for v in lib["byte_identical_gradle_sources"]) or "No Gradle AAR/JAR byte match"
        lines.append(f"| {lib['apk_path']} | {matches_text} |")
    lines += ["", "## Gradle artifacts and embedded notice counts", "",
              "| Coordinate | Binary SHA256 | Embedded notices | AAR native ELFs |",
              "| --- | --- | ---: | ---: |"]
    for a in artifacts:
        lines.append(f"| {a['coordinate']} / {a['name']} | {a['sha256']} | {len(a['notices'])} | {len(a['natives'])} |")
    lines += ["", "**This is binary provenance evidence, not a full license/source sign-off.**"]
    (args.output / "gradle-runtime-artifacts.md").write_text("\n".join(lines) + "\n")
    print(f"Captured {len(artifacts)} runtime artifacts; {report['native_apk_match_count']}/{len(coverage)} APK native libraries byte-matched to Gradle artifacts")


if __name__ == "__main__":
    main()
