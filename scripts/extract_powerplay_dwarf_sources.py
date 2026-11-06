#!/usr/bin/env python3
"""Inventory source and header paths recorded in an unstripped ELF's DWARF."""

import argparse
import json
import posixpath
from pathlib import Path

from elftools.elf.elffile import ELFFile


def decode(value):
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    files = set()
    units = []
    with args.elf.open("rb") as source:
        dwarf = ELFFile(source).get_dwarf_info()
        for unit in dwarf.iter_CUs():
            attributes = unit.get_top_DIE().attributes
            units.append({
                key: decode(attributes[key].value)
                for key in ("DW_AT_name", "DW_AT_comp_dir", "DW_AT_producer")
                if key in attributes
            })
            lines = dwarf.line_program_for_CU(unit)
            if lines is None:
                continue
            header = lines.header
            for entry in header.file_entry:
                index = entry.dir_index
                if header.version >= 5:
                    directory = decode(header.include_directory[index])
                elif index:
                    directory = decode(header.include_directory[index - 1])
                else:
                    directory = ""
                files.add(posixpath.normpath(posixpath.join(directory, decode(entry.name))))

    report = {
        "compilation_units": units,
        "line_table_files": sorted(files),
        "limitation": "DWARF includes input provenance, including inline/header code; "
                      "it is not a complete GN/build-tool dependency graph.",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{args.elf.name}: {len(units)} compilation units, {len(files)} line-table paths")


if __name__ == "__main__":
    main()
