#!/usr/bin/env python3
"""Audit-only reproduction of sqlite3 3.5.0's SQLite 3.53.3 ARMv7 asset."""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sqlite_dart_source", type=Path)
    p.add_argument("amalgamation", type=Path)
    p.add_argument("ndk_r29", type=Path)
    p.add_argument("new_output", type=Path)
    args = p.parse_args()
    if args.new_output.exists():
        p.error("Output directory already exists")
    if "Pkg.Revision = 29.0.14206865" not in (args.ndk_r29 / "source.properties").read_text():
        p.error("Expected Android NDK 29.0.14206865")
    definitions = (args.sqlite_dart_source / "sqlite3/lib/src/hook/compile/description.dart").read_text()
    defines = definitions.split("const _defaultDefines = '''", 1)[1].split("'''", 1)[0].split()
    if not defines or any(not x.startswith("SQLITE_") for x in defines):
        p.error("Unexpected pinned SQLite default defines")
    toolchain = args.ndk_r29.resolve() / "toolchains/llvm/prebuilt/linux-x86_64/bin"
    args.new_output.mkdir(parents=True)
    output = args.new_output.resolve()
    command = [str(toolchain / "armv7a-linux-androideabi24-clang"),
               "-shared", "-fPIC", "-O3", "-DNDEBUG",
               "-Wl,-z,max-page-size=16384", "-Wl,-rpath,$ORIGIN",
               *["-D" + x for x in defines], str(args.amalgamation.resolve()),
               "-lm", "-o", str(output / "libsqlite3.unstripped.so")]
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    subprocess.run(command, check=True)
    subprocess.run([str(toolchain / "llvm-strip"), "--strip-unneeded",
                    "-o", str(output / "libsqlite3.so"),
                    str(output / "libsqlite3.unstripped.so")], check=True)


if __name__ == "__main__":
    main()
