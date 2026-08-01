#!/usr/bin/env python3
"""Validate and relocate the CMake metadata in ROOT's alpha PyPI wheel."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys


SUPPORTED_ROOT_DISTRIBUTION = "0.1a12"
BROKEN_CMAKE_FRAGMENT = "/mock_site_packages/"
RELOCATED_CMAKE_FRAGMENT = "/site-packages/"


def locate_root() -> Path:
    version = importlib.metadata.version("root")
    if version != SUPPORTED_ROOT_DISTRIBUTION:
        raise RuntimeError(
            f"higgs-combine-tool expects root=={SUPPORTED_ROOT_DISTRIBUTION}; "
            f"found {version}. "
            "The relocation workaround is deliberately version-specific."
        )
    spec = importlib.util.find_spec("ROOT")
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError("Could not locate the ROOT package directory")
    return Path(next(iter(spec.submodule_search_locations))).resolve()


def patch_cmake_metadata(root_dir: Path) -> int:
    files = [
        root_dir / "cmake" / "ROOTConfig-targets.cmake",
        root_dir / "cmake" / "ROOTConfig-targets-release.cmake",
    ]
    replacements = 0
    for path in files:
        if not path.is_file():
            raise RuntimeError(f"ROOT wheel CMake metadata is missing: {path}")
        original = path.read_text(encoding="utf-8")
        count = original.count(BROKEN_CMAKE_FRAGMENT)
        if count:
            path.write_text(
                original.replace(BROKEN_CMAKE_FRAGMENT, RELOCATED_CMAKE_FRAGMENT),
                encoding="utf-8",
            )
            replacements += count
        elif RELOCATED_CMAKE_FRAGMENT not in original:
            raise RuntimeError(
                f"Unexpected ROOT CMake layout in {path}; refusing an unverified rewrite"
            )
    return replacements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root_dir = locate_root()
    replacements = patch_cmake_metadata(root_dir)
    external_lib_dir = root_dir.parent / "root.libs"
    for required in (root_dir / "cmake" / "ROOTConfig.cmake", root_dir / "include", root_dir / "lib", external_lib_dir):
        if not required.exists():
            raise RuntimeError(f"ROOT wheel component is missing: {required}")

    result = {
        "root_distribution_version": SUPPORTED_ROOT_DISTRIBUTION,
        "root_package_dir": str(root_dir),
        "root_external_lib_dir": str(external_lib_dir),
        "cmake_replacements": replacements,
    }
    print(
        f"ROOT {SUPPORTED_ROOT_DISTRIBUTION} CMake metadata ready "
        f"({replacements} staging-path replacements)",
        file=sys.stderr,
    )
    if args.json:
        print(json.dumps(result))
    else:
        for key, value in result.items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"prepare_root.py: {error}", file=sys.stderr)
        raise SystemExit(1) from error
