#!/usr/bin/env python3
"""End-to-end smoke test against the wheel-installed command entry points."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )


def main() -> int:
    card = Path(__file__).resolve().parent / "data" / "counting.txt"
    for command in ("combine", "text2workspace.py", "higgs-combine-tool-doctor"):
        if shutil.which(command) is None:
            raise RuntimeError(f"Missing installed command: {command}")

    doctor = run(["higgs-combine-tool-doctor", "--json"])
    report = json.loads(doctor.stdout)
    if not report["ok"] or report["higgs_combine_tool_version"] != "11.0.0.post1":
        raise RuntimeError(f"Unexpected doctor report: {report}")

    with tempfile.TemporaryDirectory(prefix="higgs-combine-tool-smoke-") as tmp:
        workdir = Path(tmp)
        workspace = workdir / "workspace.root"
        t2w = run(["text2workspace.py", str(card), "-o", str(workspace)], cwd=workdir)
        print(t2w.stdout)
        if not workspace.is_file() or workspace.stat().st_size == 0:
            raise RuntimeError("text2workspace.py did not create a workspace")

        fit = run(
            [
                "combine",
                "-M",
                "AsymptoticLimits",
                str(workspace),
                "-t",
                "-1",
                "--expectSignal",
                "1",
                "--run",
                "blind",
            ],
            cwd=workdir,
        )
        print(fit.stdout)
        if "<<< v11.0.0 >>>" not in fit.stdout or "Expected 50.0%" not in fit.stdout:
            raise RuntimeError("Combine did not complete the expected blind limit")

        # Upstream regression test of PR #1345: on variable-width bins the pre-fit Asimov at
        # shape = 0, +1 and -1 must reproduce the RooHistPdf templates.
        data = card.parent
        shutil.copy(data / "datacard_RooHistPdf_variable_binning.txt", workdir)
        test = str(data / "histpdf_variable_binning.py")
        run([sys.executable, test, "make"], cwd=workdir)
        run(["text2workspace.py", "datacard_RooHistPdf_variable_binning.txt", "-o", "ws_variable_binning.root",
             "--X-allow-no-background"], cwd=workdir)
        check = run([sys.executable, test, "check", "ws_variable_binning.root"], cwd=workdir)
        print(check.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
