#!/usr/bin/env python3
"""Static checks for the repaired higgs-combine-tool wheel artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile
import zipfile


REQUIRED_MEMBERS = {
    "cms_combine/bin/combine",
    "cms_combine/lib/libHiggsAnalysisCombinedLimit.so",
    "cms_combine/lib/libHiggsAnalysisCombinedLimit_rdict.pcm",
    "HiggsAnalysis/CombinedLimit/PhysicsModel.py",
    "cms_combine/cmssw/src/HiggsAnalysis/CombinedLimit/data/lhc-hxswg/sm/br/BR4.txt",
}


def dynamic_section(path: Path) -> str:
    return subprocess.run(
        ["readelf", "-d", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument(
        "--expected-plat",
        default="manylinux_2_28_x86_64",
        help="Expected platform component of the wheel tag",
    )
    args = parser.parse_args()

    with zipfile.ZipFile(args.wheel) as archive:
        names = set(archive.namelist())
        missing = REQUIRED_MEMBERS - names
        if missing:
            raise RuntimeError(f"Wheel is missing required members: {sorted(missing)}")
        if any(name.endswith("/libCore.so") for name in names):
            raise RuntimeError("The wheel duplicated libCore.so instead of depending on root")
        if not any(
            "higgs_combine_tool.libs/libboost_program_options" in name
            for name in names
        ):
            raise RuntimeError("auditwheel did not bundle Boost.Program_options")

        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        wheel_name = next(name for name in names if name.endswith(".dist-info/WHEEL"))
        metadata = archive.read(metadata_name).decode()
        wheel_metadata = archive.read(wheel_name).decode()
        if (
            "Name: higgs-combine-tool" not in metadata
            or "Requires-Dist: root==0.1a12" not in metadata
        ):
            raise RuntimeError("Wheel metadata does not pin the expected ROOT distribution")
        expected_tag = f"Tag: py3-none-{args.expected_plat}"
        if expected_tag not in wheel_metadata:
            raise RuntimeError(f"Unexpected wheel tags:\n{wheel_metadata}")

        with tempfile.TemporaryDirectory(prefix="verify-higgs-combine-tool-") as tmp:
            tmp_path = Path(tmp)
            for member in (
                "cms_combine/bin/combine",
                "cms_combine/lib/libHiggsAnalysisCombinedLimit.so",
            ):
                archive.extract(member, tmp_path)
                section = dynamic_section(tmp_path / member)
                if "/mnt/" in section or "/project/" in section or "/tmp/" in section:
                    raise RuntimeError(f"Absolute build path remains in {member}:\n{section}")
                if "$ORIGIN" not in section or "ROOT/lib" not in section:
                    raise RuntimeError(f"Relocatable ROOT runtime path missing in {member}:\n{section}")

    print(f"Verified {args.wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
