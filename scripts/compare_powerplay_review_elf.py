#!/usr/bin/env python3
"""Compare native review builds without masking executable differences.

Requires pyelftools. The default compares every byte, except the GNU build-ID
descriptor. --allocated compares section addresses, types, flags, alignment,
size and contents for an upstream symbol/stripping provenance check; it is not
a substitute for a complete source rebuild comparison.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(data):
    elf = ELFFile(io.BytesIO(data))
    identity = {k: elf.header[k] for k in ("e_machine", "e_type", "e_entry", "e_flags")}
    identity.update(elfclass=elf.elfclass, little_endian=elf.little_endian)
    normalized = bytearray(data)
    build_ids = []
    allocated = {}
    for section in elf.iter_sections():
        if section.name == ".note.gnu.build-id":
            notes = list(section.iter_notes())
            if len(notes) != 1 or notes[0]["n_type"] != "NT_GNU_BUILD_ID" or notes[0]["n_name"] != "GNU":
                raise ValueError("Unexpected GNU build-ID note layout")
            note = notes[0]
            # ELF note header (12 bytes), then the four-byte-aligned owner.
            start = section["sh_offset"] + 12 + ((note["n_namesz"] + 3) & ~3)
            end = start + note["n_descsz"]
            if end > section["sh_offset"] + section["sh_size"]:
                raise ValueError("Build-ID descriptor exceeds its section")
            normalized[start:end] = bytes(end - start)
            build_ids.append(note["n_desc"])
        if section["sh_flags"] & 2:
            allocated[section.name] = {
                **{k: section[k] for k in ("sh_addr", "sh_type", "sh_flags", "sh_size", "sh_addralign")},
                "sha256": digest(section.data()),
            }
    if len(build_ids) > 1:
        raise ValueError("Expected at most one GNU build ID")
    return identity, bytes(normalized), build_ids[0] if build_ids else None, allocated


def compare(original, rebuilt, allocated=False):
    a, b = original.read_bytes(), rebuilt.read_bytes()
    ia, na, ba, sa = inspect(a)
    ib, nb, bb, sb = inspect(b)
    differing = sorted(k for k in sa.keys() | sb.keys() if sa.get(k) != sb.get(k))
    equal = ia == ib and ((sa == sb and ba == bb) if allocated else na == nb)
    return {
        "original_sha256": digest(a), "candidate_sha256": digest(b),
        "original_bytes": len(a), "candidate_bytes": len(b),
        "original_build_id": ba, "candidate_build_id": bb,
        "elf_identity_matches": ia == ib,
        "mode": "allocated-section-identity" if allocated else "all-bytes-except-build-id-descriptor",
        "differing_allocated_sections": differing,
        "matches": equal,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--allocated", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare(args.original, args.candidate, args.allocated)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")
    raise SystemExit(0 if result["matches"] else 1)


if __name__ == "__main__":
    main()
