#!/usr/bin/env python3
"""Archive native source inputs named by Plezy's pinned Android AAR lock."""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def archive_git(name, url, revision, target):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(f"{name}: expected a full immutable Git commit")
    with tempfile.TemporaryDirectory(prefix=f"firetv-{name}-") as directory:
        run("git", "init", "--quiet", directory)
        run("git", "-C", directory, "remote", "add", "origin", url)
        run("git", "-C", directory, "fetch", "--quiet", "--depth=1", "origin", revision)
        actual = subprocess.check_output(
            ["git", "-C", directory, "rev-parse", "FETCH_HEAD"], text=True
        ).strip()
        if actual != revision:
            raise ValueError(f"{name}: expected {revision}, fetched {actual}")
        with target.open("wb") as destination:
            run("git", "-C", directory, "archive", "--format=tar.gz",
                f"--prefix={name}/", revision, stdout=destination)
        if name == "mpv-build":
            versions = json.loads(subprocess.check_output(
                ["git", "-C", directory, "show", f"{revision}:versions.json"], text=True
            ))
            artifacts = json.loads(subprocess.check_output(
                ["git", "-C", directory, "show", f"{revision}:artifacts.json"], text=True
            ))
            return versions, artifacts
    return None


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    lock = json.loads(Path("mpv-build.lock.json").read_text(encoding="utf-8"))
    if lock["repo"] != "edde746/mpv-build":
        raise ValueError("Review changed mpv-build source repository")
    aar = lock["artifacts"]["android"]["aar"]
    with tempfile.TemporaryDirectory(prefix="firetv-native-sources-") as directory:
        root = Path(directory)
        build_revision = lock["commit"]
        build_tar = root / f"mpv-build-{build_revision}.tar.gz"
        versions, artifacts = archive_git(
            "mpv-build", "https://github.com/edde746/mpv-build.git", build_revision, build_tar
        )
        recorded = artifacts["platforms"]["android"]["libraries"]["mpv-android"]
        for key in ("asset", "key", "checksum"):
            if recorded[key] != aar[key]:
                raise ValueError(f"Pinned AAR {key} disagrees with mpv-build artifacts.json")

        # The extracted FFmpeg shared libraries are built with these inputs.
        # Use the upstream mirror for dav1d; its commit is checked identically.
        urls = {
            "ffmpeg": "https://github.com/FFmpeg/FFmpeg.git",
            "dav1d": "https://github.com/videolan/dav1d.git",
            "openssl": "https://github.com/openssl/openssl.git",
            "libdovi": "https://github.com/quietvoid/dovi_tool.git",
        }
        files = [build_tar]
        revisions = {"mpv-build": build_revision}
        for name, url in urls.items():
            component = versions["components"][name]
            pin = dict(component)
            pin.update(component.get("overrides", {}).get("android", {}))
            revision = pin["commit"]
            output = root / f"{name}-{revision}.tar.gz"
            archive_git(name, url, revision, output)
            revisions[name] = revision
            files.append(output)

        manifest = {
            "aar_asset": aar["asset"],
            "aar_sha256": aar["checksum"],
            "source_commits": revisions,
            "archive_sha256": {path.name: sha256(path) for path in files},
        }
        readme = (
            "These are the pinned Android FFmpeg build inputs referenced by Plezy's "
            "AAR lock. The mpv-build archive includes its Android driver, toolchain "
            "pins, and FFmpeg/libdovi patch series. The component archives are "
            "unpatched upstream source at the recorded commits. See versions.json "
            "and the Android download/build scripts in mpv-build for applying patches "
            "and retrieving further dependencies. This bundle has not been audited "
            "for completeness of all transitive third-party sources.\n"
        )
        output = Path("Plezy-FireTV-NoMPV-NativeSourceInputs.zip")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("README.txt", readme)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
            for path in files:
                archive.write(path, path.name)
        Path(str(output) + ".sha256").write_text(
            f"{sha256(output)}  {output.name}\n", encoding="utf-8"
        )
        print(f"Archived pinned native source inputs: {output}")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Native source archive failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
