#!/usr/bin/env python3
"""Reconstruct the time-qualified WrapDB libass build inputs with SHA256 proofs.

This records what public WrapDB contained immediately before the historical
libass Android workflow, NOT an attestation of that job's actual Meson cache.
"""
import argparse
import configparser
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import urlparse

HISTORICAL_WRAPDB = "99634f253c3f2e83295b210018d071f6570284e6"
LIBASS_BUILD_STARTED = "2026-07-10T01:46:26Z"
PACKAGES = ("freetype2", "fribidi", "harfbuzz", "libunibreak", "fontconfig", "expat")
LEGAL_NAME = re.compile(
    r"^(LICEN[CS]E(?:[._-].*)?|COPYING(?:[._-].*)?|NOTICE(?:[._-].*)?|"
    r"COPYRIGHT(?:[._-].*)?|FTL\.TXT|GPLv2\.TXT|AUTHORS(?:[._-].*)?)$", re.I
)


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def out(*args):
    return subprocess.check_output(args).decode("utf-8").strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_component(value):
    if not value or Path(value).name != value or value in (".", ".."):
        raise ValueError(f"Unsafe single path component: {value!r}")
    return value


def download(url, destination, expected_sha):
    if urlparse(url).scheme != "https":
        raise ValueError(f"Only HTTPS source URLs allowed: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="libass-wrap-fetch-") as tmp:
        part = Path(tmp) / "download"
        run("curl", "--fail", "--location", "--silent", "--show-error",
            "--retry", "3", "--connect-timeout", "20", "--max-time", "240",
            url, "--output", str(part))
        actual = digest(part.read_bytes())
        if actual != expected_sha:
            raise ValueError(f"Source SHA256 mismatch for {url}: {actual} != {expected_sha}")
        shutil.copyfile(part, destination)
    return actual


def from_git(repo_dir, revision, path):
    return subprocess.check_output(["git", "-C", str(repo_dir), "show",
                                    f"{revision}:{path}"])


def archive_licenses(source_archive, root, package):
    result = []
    with tarfile.open(source_archive, mode="r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.size > 1048576:
                continue
            parts = Path(member.name).parts
            if (not parts or Path(member.name).is_absolute()
                    or ".." in parts or len(parts) > 8):
                continue
            if not LEGAL_NAME.match(parts[-1]):
                continue
            data = tar.extractfile(member).read()
            if b"\0" in data:
                continue
            relative = Path(*parts[1:]) if len(parts) > 1 else Path(parts[-1])
            dest = root / "legal-texts" / package / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            result.append({
                "upstream_path": member.name, "sha256": digest(data),
                "copied_path": str(dest.relative_to(root))
            })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="libass-wrapdb-") as tmp:
        repo = Path(tmp) / "wrapdb"
        run("git", "init", "--quiet", str(repo))
        run("git", "-C", str(repo), "remote", "add", "origin",
            "https://github.com/mesonbuild/wrapdb.git")
        run("git", "-C", str(repo), "fetch", "--quiet", "--depth=1",
            "origin", HISTORICAL_WRAPDB)
        verified = out("git", "-C", str(repo), "rev-parse", "FETCH_HEAD")
        if verified != HISTORICAL_WRAPDB:
            raise ValueError(f"WrapDB revision unexpectedly changed: {verified}")

        items = []
        for package in PACKAGES:
            wrap_path = f"subprojects/{package}.wrap"
            raw = from_git(repo, HISTORICAL_WRAPDB, wrap_path)
            wrap_file = root / "wraps" / f"{package}.wrap"
            wrap_file.parent.mkdir(parents=True, exist_ok=True)
            wrap_file.write_bytes(raw)
            config = configparser.ConfigParser(interpolation=None)
            config.read_string(raw.decode("utf-8"))
            section = config["wrap-file"]
            source_filename = safe_component(section["source_filename"])
            source_hash = section["source_hash"].lower()
            if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
                raise ValueError(f"{package}: invalid source SHA256")
            source_file = root / "source-archives" / source_filename
            urls = [section["source_url"]]
            if section.get("source_fallback_url"):
                urls.append(section["source_fallback_url"])
            fetched_url = None
            failures = []
            for url in urls:
                try:
                    download(url, source_file, source_hash)
                    fetched_url = url
                    break
                except (subprocess.CalledProcessError, ValueError) as error:
                    failures.append(f"{url}: {error}")
            if fetched_url is None:
                raise RuntimeError(f"{package}: could not retrieve a verified source archive:\n" +
                                   "\n".join(failures))
            licenses = archive_licenses(source_file, root, package)
            patches = []
            patch_directory = section.get("patch_directory")
            if patch_directory:
                safe_component(patch_directory)
                prefix = f"subprojects/packagefiles/{patch_directory}"
                paths = out("git", "-C", str(repo), "ls-tree",
                            "--name-only", "-r", HISTORICAL_WRAPDB, prefix).splitlines()
                if not paths:
                    raise ValueError(f"{package}: missing historical Meson patch directory: {prefix}")
                for path in paths:
                    file_data = from_git(repo, HISTORICAL_WRAPDB, path)
                    relative = Path(path).relative_to("subprojects/packagefiles")
                    target = root / "patches" / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(file_data)
                    patches.append({"path": str(relative), "sha256": digest(file_data)})
            items.append({
                "name": package,
                "version": section["directory"],
                "wrapdb_sha256": digest(raw),
                "source_sha256": source_hash,
                "source_file": str(source_file.relative_to(root)),
                "source_url": fetched_url,
                "original_source_url": section["source_url"],
                "meson_patches": patches,
                "legal_texts": licenses,
                "historical_binary_wrap_resolution_confirmed": False
            })
            print(f"{package}: {section['directory']}; verified {source_hash}; "
                  f"{len(licenses)} notice files; {len(patches)} Meson patch files")
        unibreak = next(item for item in items if item["name"] == "libunibreak")
        if not any(Path(record["upstream_path"]).name.upper() == "LICENCE"
                   for record in unibreak["legal_texts"]):
            raise ValueError("libunibreak 6.1 source archive does not expose expected LICENCE")
        manifest = {
            "purpose": "historical-wrapdb-time-qualified-source-snapshot",
            "libass_upstream_build_start_utc": LIBASS_BUILD_STARTED,
            "wrapdb_snapshot_commit": HISTORICAL_WRAPDB,
            "wrapdb_snapshot_precedes_build": True,
            "historical_binary_provenance_confirmed": False,
            "limitation": (
                "The original release workflow ran meson wrap update-db/install/download without "
                "recording resolved wraps or subproject source hashes. These are the verified "
                "public WrapDB inputs immediately before the build, NOT proof that the "
                "historical runner used those exact source bytes."
            ),
            "components": items,
        }
        (root / "wrapdb-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (root / "README.md").write_text(
            "# PowerPlay 1.3.9 independent libass: historical WrapDB source snapshot\n\n"
            "Contains six SHA256-verified upstream release source archives, historical "
            "WrapDB .wrap descriptors and Meson patch files, and copied original license "
            "texts, including libunibreak's UK-spelled LICENCE omitted by the "
            "prebuilt libass release ZIP.\n\n"
            "**Not an exact binary-build attestation.** The original build used dynamic "
            "WrapDB lookup without a retained wrap/subproject lock or build log. "
            "Source versions are reconstructed from the public WrapDB commit immediately "
            "before the upstream Android build, not verified against the archived .a. "
            "This alone does not satisfy all LGPL/GPL corresponding-source or relinking "
            "obligations.\n"
        )


if __name__ == "__main__":
    main()
