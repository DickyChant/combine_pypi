#!/usr/bin/env python3
"""Repair a wheel while keeping ROOT supplied by the declared root dependency."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def locate_root() -> Path:
    spec = importlib.util.find_spec("ROOT")
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError("Install root==0.1a12 before repairing the wheel")
    return Path(next(iter(spec.submodule_search_locations))).resolve()


def sonames(directory: Path) -> set[str]:
    names: set[str] = set()
    for path in directory.glob("*.so*"):
        if not path.is_file():
            continue
        result = subprocess.run(
            ["readelf", "-d", str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        for line in result.stdout.splitlines():
            if "(SONAME)" in line and "[" in line and "]" in line:
                names.add(line.split("[", 1)[1].split("]", 1)[0])
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--dest-dir", type=Path, required=True)
    parser.add_argument("--plat", required=True)
    parser.add_argument(
        "--disable-isa-ext-check",
        action="store_true",
        help=(
            "Allow a host-only diagnostic repair even when the local OS marks "
            "an ELF as x86-64-v2; never use this for release artifacts"
        ),
    )
    args = parser.parse_args()

    root_dir = locate_root()
    root_external = root_dir.parent / "root.libs"
    supplied_by_root = sonames(root_dir / "lib") | sonames(root_external)
    if "libCore.so" not in supplied_by_root or "libRooFitCore.so" not in supplied_by_root:
        raise RuntimeError("Could not enumerate the expected ROOT shared libraries")

    args.dest_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "auditwheel",
        "repair",
        "--plat",
        args.plat,
        "--wheel-dir",
        str(args.dest_dir),
    ]
    if args.disable_isa_ext_check:
        command.append("--disable-isa-ext-check")
    for name in sorted(supplied_by_root):
        command.extend(["--exclude", name])
    command.append(str(args.wheel))

    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(
        (str(Path(sys.prefix) / "bin"), env.get("PATH", ""))
    )
    lookup = os.pathsep.join((str(root_dir / "lib"), str(root_external)))
    previous = env.get("AUDITWHEEL_LD_LIBRARY_PATH")
    env["AUDITWHEEL_LD_LIBRARY_PATH"] = os.pathsep.join(filter(None, (lookup, previous)))
    subprocess.run(command, env=env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
