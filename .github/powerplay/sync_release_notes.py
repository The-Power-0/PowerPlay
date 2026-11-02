#!/usr/bin/env python3
"""Synchronize audited PowerPlay release descriptions and publish legacy draft archives.

Never changes APKs, assets, tags, release target commits, or signing material.
Existing release metadata and assets must match the request snapshot before edits.
"""
import argparse
import json
import os
from pathlib import Path
import urllib.request

REPO = "The-Power-0/PowerPlay"
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".github/powerplay/release-notes-metadata.json"
REQUEST = ROOT / ".github/powerplay/release-notes.request.json"

def api(path, payload=None):
    url = f"https://api.github.com/repos/{REPO}/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PowerPlay-Release-Notes-Housekeeping",
    }
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("Missing GH_TOKEN")
    headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode()
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers,
                                     method="GET" if payload is None else "PATCH")
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.load(response)

def asset_signature(release):
    return sorted((a["id"], a["name"], a["size"]) for a in release["assets"])

def target_equal(release, entry):
    return all(release[k] == entry["desired"][k]
               for k in ("name", "body", "draft", "prerelease"))

def initial_equal(release, entry):
    return all(release[k] == entry["expected"][k]
               for k in ("name", "body", "draft", "prerelease"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    request = json.loads(REQUEST.read_text())
    assert os.getenv("GITHUB_REPOSITORY", REPO) == REPO
    assert request["confirm"] == "STANDARDIZE_POWERPLAY_RELEASES_AND_PUBLISH_ARCHIVES"
    assert request["metadata_revision"] == data["revision"] == 1
    assert data["repository"] == REPO
    assert request["latest_tag"] == data["latest_tag"] == "powerplay-v1.2.1"
    assert api("releases/latest")["tag_name"] == data["latest_tag"], "Latest has advanced: stop without changes"

    entries = data["releases"]
    assert len(entries) == 10 and len({e["id"] for e in entries}) == 10
    assert len({e["tag"] for e in entries}) == 11
    expected_tags = {
        "powerplay-v1.0.0", "powerplay-v1.1.0", "powerplay-v1.1.1",
        "powerplay-v1.1.2", "powerplay-v1.2.0", "powerplay-v1.2.1",
        "2.22.0-ha-shuffle.1", "2.23.0-ha-shuffle.1",
        "2.24.0-ha-shuffle.1", "2.25.0-ha-shuffle.1",
    }
    assert len(entries) == len(expected_tags) and {e["tag"] for e in entries} == expected_tags
    snapshot = []
    for entry in entries:
        current = api(f"releases/{entry['id']}")
        assert current["tag_name"] == entry["tag"], entry["tag"]
        assert not current.get("immutable", False), entry["tag"]
        assert asset_signature(current) == sorted(tuple(a) for a in entry["assets"]), entry["tag"]
        assert current["target_commitish"] == entry["target_commitish"], entry["tag"]
        assert initial_equal(current, entry) or target_equal(current, entry), (
            "Release changed since the audit: " + entry["tag"]
        )
        if entry["tag"].startswith("powerplay-"):
            assert not entry["desired"]["draft"] and not entry["desired"]["prerelease"]
            assert "Plezy 2.25.0" in entry["desired"]["body"]
            assert "Based on Plezy 2.24.0" not in entry["desired"]["body"]
        else:
            assert not entry["desired"]["draft"] and entry["desired"]["prerelease"]
            assert current["created_at"] < api("releases/tags/powerplay-v1.0.0")["created_at"]
        snapshot.append((entry, current))
    print("AUDIT PASS: all source release metadata, target commits, and asset IDs/sizes match.")
    for entry, current in snapshot:
        already = target_equal(current, entry)
        print(("UNCHANGED" if already else "UPDATE" if args.apply else "WOULD UPDATE"),
              entry["tag"], "(publish archive)" if current["draft"] else "")
        if args.apply and not already:
            changes = dict(entry["desired"])
            if not entry["tag"].startswith("powerplay-"):
                changes["make_latest"] = "false"
            result = api(f"releases/{entry['id']}", changes)
            assert result["tag_name"] == entry["tag"] and target_equal(result, entry)
            assert asset_signature(result) == asset_signature(current)
    if not args.apply:
        print("DRY RUN: no changes made.")
        return
    assert api("releases/latest")["tag_name"] == data["latest_tag"]
    listing = api("releases?per_page=50")
    by_tag = {r["tag_name"]: i for i, r in enumerate(listing)}
    for entry in entries:
        current = api(f"releases/{entry['id']}")
        assert target_equal(current, entry)
        assert asset_signature(current) == sorted(tuple(a) for a in entry["assets"])
    for archive in ("2.25.0-ha-shuffle.1", "2.24.0-ha-shuffle.1",
                    "2.23.0-ha-shuffle.1", "2.22.0-ha-shuffle.1"):
        assert by_tag[archive] > by_tag["powerplay-v1.0.0"], (archive, by_tag)
    assert by_tag["powerplay-v1.2.1"] < by_tag["2.25.0-ha-shuffle.1"]
    print("VERIFIED: Latest remains 1.2.1; all legacy archives follow all stable releases.")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(
            "# PowerPlay release notes and archive order\n\n"
            "Standardized six stable descriptions, clarified Plezy 2.25.0 "
            "as the original PowerPlay code baseline, and published three "
            "legacy drafts as historical prereleases. Latest remains 1.2.1. "
            "No tags, assets, or APKs changed.\n"
        )

if __name__ == "__main__":
    main()
