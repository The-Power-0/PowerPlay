#!/usr/bin/env python3
"""Replace libasskt in the audited ARMv7 release for a local relink test."""

import argparse
import hashlib
from pathlib import Path
import zipfile

from elftools.elf.elffile import ELFFile

APK_SHA256 = "f832a2c507f997fcb047c0ab899254d1fd111520942e88da50e61ebc82e3c764"
TARGET = "lib/armeabi-v7a/libasskt.so"


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def is_signature(path):
    name = path.upper()
    return name.startswith("META-INF/") and (
        name.endswith((".SF", ".RSA", ".DSA", ".EC")) or name == "META-INF/MANIFEST.MF"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_apk", type=Path)
    parser.add_argument("modified_elf", type=Path)
    parser.add_argument("unsigned_output", type=Path)
    args = parser.parse_args()
    if sha256(args.original_apk) != APK_SHA256:
        parser.error("The original signed APK does not match the v1.3.9 release digest.")
    with args.modified_elf.open("rb") as library:
        elf = ELFFile(library)
        if elf.elfclass != 32 or elf.header["e_machine"] != "EM_ARM" or elf.header["e_type"] != "ET_DYN":
            parser.error("The replacement must be an ARMv7-compatible ELF shared library.")
    with zipfile.ZipFile(args.original_apk) as original:
        names = original.namelist()
        if len(names) != len(set(names)) or TARGET not in names:
            parser.error("Unexpected APK entries.")
        replacement = args.modified_elf.read_bytes()
        if replacement == original.read(TARGET):
            parser.error("The replacement library is identical to the shipped library.")
        with zipfile.ZipFile(args.unsigned_output, "x") as output:
            for entry in original.infolist():
                if not is_signature(entry.filename):
                    data = replacement if entry.filename == TARGET else original.read(entry)
                    output.writestr(entry.filename, data, compress_type=entry.compress_type)
    print(f"{args.unsigned_output} is unsigned. Align and sign it with a local test key.")


if __name__ == "__main__":
    main()
