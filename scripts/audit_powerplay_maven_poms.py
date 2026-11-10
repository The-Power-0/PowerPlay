#!/usr/bin/env python3
"""Collect Maven POM license *declarations* for resolved Android runtime modules.

No POM declaration is a legal conclusion. Preserve original POM bytes, parent
inheritance, source links, hashes and unresolved modules for human review.
"""
import argparse
import concurrent.futures
import hashlib
import json
import re
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPOS = (
    ("google-maven", "https://dl.google.com/dl/android/maven2"),
    ("maven-central", "https://repo.maven.apache.org/maven2"),
    ("flutter", "https://storage.googleapis.com/download.flutter.io"),
)
SOURCE_PRIORITY = {
    "org.chromium.net:cronet-embedded:143.7445.0",
    "org.chromium.net:cronet-api:143.7445.0",
    "io.sentry:sentry-native-ndk:0.16.6",
    "androidx.datastore:datastore-core-android:1.1.7",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def coord_tuple(coordinate):
    parts = coordinate.split(":")
    if len(parts) != 3 or not all(parts):
        raise ValueError("Unexpected Maven coordinate: " + coordinate)
    return parts


def repos_for(group):
    if group.startswith("io.flutter"):
        order = (2, 1, 0)
    elif group.startswith(("androidx.", "com.android.", "com.google.android.",
                           "org.chromium.net")):
        order = (0, 1, 2)
    else:
        order = (1, 0, 2)
    return [REPOS[i] for i in order]


def http_get(url, limit=1024 * 1024):
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": "PowerPlay-audit/1.3.9 (source-license-evidence)",
            "Accept": "application/xml,application/java-archive,*/*",
        })
        with urllib.request.urlopen(request, timeout=35) as result:
            content = result.read(limit + 1)
            if len(content) > limit:
                return None, "response exceeds size limit"
            return content, None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        return None, str(error)


def artifact_url(base, coordinate, filename):
    group, artifact, version = coord_tuple(coordinate)
    return (base + "/" + group.replace(".", "/") + "/" + artifact + "/" +
            version + "/" + filename)


def get_pom(coordinate):
    group, artifact, version = coord_tuple(coordinate)
    errors = []
    for repo_name, base in repos_for(group):
        name = f"{artifact}-{version}.pom"
        url = artifact_url(base, coordinate, name)
        data, error = http_get(url)
        if data is not None:
            try:
                root = ET.fromstring(data)
                if root.tag.split("}")[-1] != "project":
                    raise ValueError("not a Maven project XML")
            except ET.ParseError as parse_error:
                errors.append(f"{repo_name}: invalid XML: {parse_error}")
                continue
            except ValueError as parse_error:
                errors.append(f"{repo_name}: {parse_error}")
                continue
            return {"raw": data, "url": url, "repository": repo_name,
                    "root": root, "sha256": sha256(data), "errors": errors}
        errors.append(f"{repo_name}: {error}")
    return {"errors": errors}


def child(element, name):
    return element.find("{*}" + name) if element is not None else None


def value(element, name):
    child_node = child(element, name)
    return (child_node.text or "").strip() if child_node is not None else ""


def parse_pom(root):
    licenses = []
    collection = child(root, "licenses")
    if collection is not None:
        for lic in collection.findall("{*}license"):
            licenses.append({
                "name": value(lic, "name"),
                "url": value(lic, "url"),
                "distribution": value(lic, "distribution"),
                "comments": value(lic, "comments"),
            })
    parent = child(root, "parent")
    parent_coord = None
    if parent is not None:
        g, a, v = (value(parent, key) for key in ("groupId", "artifactId", "version"))
        if all((g, a, v)) and "$" not in (g + a + v):
            parent_coord = f"{g}:{a}:{v}"
    scm = child(root, "scm")
    return {
        "licenses": licenses, "parent": parent_coord,
        "scm": {"url": value(scm, "url"), "connection": value(scm, "connection")},
        "homepage": value(root, "url"),
        "description": value(root, "description")[:300],
    }


def snapshot_module(coordinate, target):
    group, artifact, version = coord_tuple(coordinate)
    poms_dir = target / "poms"
    poms_dir.mkdir(parents=True, exist_ok=True)
    record = {"coordinate": coordinate, "pom_found": False,
              "licenses": [], "pom_ancestry": [], "unresolved": []}
    current = coordinate
    visited = set()
    for depth in range(4):
        if current in visited:
            record["unresolved"].append("POM parent cycle at " + current)
            break
        visited.add(current)
        result = get_pom(current)
        if "raw" not in result:
            record["unresolved"].append(
                f"No public POM for {current}: " + "; ".join(result.get("errors", [])))
            break
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", current) + ".pom"
        dest = poms_dir / name
        dest.write_bytes(result["raw"])
        parsed = parse_pom(result["root"])
        record["pom_ancestry"].append({
            "coordinate": current, "repository": result["repository"],
            "pom_sha256": result["sha256"],
            "url": result["url"],
            "saved_as": str(dest.relative_to(target)),
            "license_count": len(parsed["licenses"]),
        })
        if depth == 0:
            record["pom_found"] = True
            record["published_source_homepage"] = parsed["homepage"]
            record["published_scm"] = parsed["scm"]
        if parsed["licenses"]:
            record["licenses"] = parsed["licenses"]
            record["license_declaration_source"] = current
            record["licenses_inherited_from_parent"] = depth != 0
            break
        if not parsed["parent"]:
            break
        current = parsed["parent"]
    if not record["licenses"]:
        record["unresolved"].append("No usable POM license declaration found through parent chain")
    if coordinate in SOURCE_PRIORITY:
        record["critical_source_jar"] = {"available": False, "checked": []}
        for repo_name, base in repos_for(group):
            filename = f"{artifact}-{version}-sources.jar"
            url = artifact_url(base, coordinate, filename)
            data, error = http_get(url, limit=50000000)
            if data is not None and data[:4] == b"PK\x03\x04":
                out = target / "priority-source-jars" / filename
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                record["critical_source_jar"] = {
                    "available": True, "file": str(out.relative_to(target)),
                    "sha256": sha256(data), "url": url, "repository": repo_name,
                    "does_not_prove_native_source": True,
                }
                break
            record["critical_source_jar"]["checked"].append({
                "repo": repo_name, "url": url,
                "error": error or "not a ZIP source jar"
            })
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gradle-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.gradle_report.read_text())
    if report["target_release"] != "powerplay-v1.3.9":
        parser.error("This audit is scoped to signed PowerPlay v1.3.9 only")
    coordinates = sorted({
        x["coordinate"] for x in report["gradle_artifacts"]
        if x["coordinate"].count(":") == 2
    })
    if not coordinates:
        parser.error("Gradle artifact graph has no external coordinates")
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=True)
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(snapshot_module, coordinate, target): coordinate
                   for coordinate in coordinates}
        for future in concurrent.futures.as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda x: x["coordinate"])
    counts = {
        "unique_gradle_runtime_modules": len(coordinates),
        "retrieved_poms": sum(x["pom_found"] for x in records),
        "modules_with_pom_license_declaration": sum(bool(x["licenses"]) for x in records),
        "modules_without_pom_license_declaration": sum(not x["licenses"] for x in records),
        "critical_source_jars_found": sum(
            x.get("critical_source_jar", {}).get("available", False) for x in records),
    }
    findings = {
        "release": "powerplay-v1.3.9",
        "scope": "Gradle external-module POMs from immutable app source; not proof of packaging after R8",
        "counts": counts,
        "certifies_license_compliance": False,
        "limitations": [
            "Maven POM license fields are publisher declarations, not file-level legal analyses.",
            "No POM license declaration is not evidence that a component is unlicensed.",
            "POM parent inheritance is recorded and needs manual verification when ambiguous.",
            "Source JAR presence does not establish corresponding source for embedded native ELF.",
            "Google SDK, Chromium, Flutter and Sentry native code require separate licenses/notices.",
            "Direct/indirect Gradle resolution may include components not packaged after R8.",
        ],
        "modules": records,
    }
    (target / "maven-pom-license-evidence.json").write_text(
        json.dumps(findings, indent=2) + "\n")
    lines = [
        "# PowerPlay v1.3.9 — Maven runtime POM license declaration audit",
        "",
        "No sign-off; publisher POM declarations are not complete license or source review.",
        "",
        *(f"- {key.replace('_', ' ')}: **{val}**" for key, val in counts.items()),
        "", "| Module | POM license declaration | Status |", "| --- | --- | --- |",
    ]
    for record in records:
        license_text = ", ".join(x["name"] or "(unnamed)" for x in record["licenses"])
        lines.append("| " + record["coordinate"] + " | " + (license_text or "(none found)") +
                     " | " + ("POM retrieved" if record["pom_found"] else "POM missing") + " |")
    lines += [
        "", "## Modules without published license declarations",
        "",
        *(f"- {r['coordinate']}" for r in records if not r["licenses"]),
        "",
        "**Passing this scan is not a full native source/license compliance certification.**"
    ]
    (target / "maven-pom-license-evidence.md").write_text("\n".join(lines) + "\n")
    print("POM module inventory: " + json.dumps(counts))
    if counts["retrieved_poms"] == 0:
        raise SystemExit("No POMs retrieved; likely network or source repository failure")


if __name__ == "__main__":
    main()
