"""Console entry points for the wheel-private Combine installation."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import NoReturn


_DISTRIBUTION_NAME = "higgs-combine-tool"
_SOURCE_PACKAGE_DIR = Path(__file__).resolve().parent


def _package_dir() -> Path:
    """Locate wheel data even when Python modules are redirected in editable mode."""

    try:
        distribution = importlib.metadata.distribution(_DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError:
        return _SOURCE_PACKAGE_DIR
    installed = Path(distribution.locate_file("cms_combine")).resolve()
    if (installed / "bin" / "combine").is_file():
        return installed
    return _SOURCE_PACKAGE_DIR


_PACKAGE_DIR = _package_dir()
_BIN_DIR = _PACKAGE_DIR / "bin"
_LIB_DIR = _PACKAGE_DIR / "lib"
_CMSSW_DIR = _PACKAGE_DIR / "cmssw"
_COMBINE_SRC = _CMSSW_DIR / "src" / "HiggsAnalysis" / "CombinedLimit"


def _root_dir() -> Path:
    spec = importlib.util.find_spec("ROOT")
    if spec is None:
        raise RuntimeError("The required `root` distribution is not installed")
    if spec.submodule_search_locations:
        return Path(next(iter(spec.submodule_search_locations))).resolve()
    if spec.origin:
        return Path(spec.origin).resolve().parent
    raise RuntimeError("Could not locate the installed ROOT package")


def _prepend_path(env: dict[str, str], key: str, paths: list[Path]) -> None:
    current = [entry for entry in env.get(key, "").split(os.pathsep) if entry]
    values: list[str] = []
    for path in paths:
        value = str(path)
        if path.exists() and value not in values and value not in current:
            values.append(value)
    env[key] = os.pathsep.join([*values, *current])


def runtime_environment() -> dict[str, str]:
    """Return a subprocess environment that can locate Combine and ROOT."""

    root_dir = _root_dir()
    env = dict(os.environ)
    env["ROOTSYS"] = str(root_dir)
    env.setdefault("COMBINE_SRC", str(_COMBINE_SRC))
    env.setdefault("CMSSW_BASE", str(_CMSSW_DIR))
    _prepend_path(env, "PATH", [_BIN_DIR])
    _prepend_path(env, "LD_LIBRARY_PATH", [_LIB_DIR, root_dir / "lib", root_dir.parent / "root.libs"])
    _prepend_path(env, "ROOT_INCLUDE_PATH", [_CMSSW_DIR / "src", root_dir / "include"])
    return env


def _exec(path: Path, argv: list[str]) -> NoReturn:
    if not path.is_file():
        raise RuntimeError(f"Packaged executable is missing: {path}")
    os.execve(str(path), argv, runtime_environment())


def _exec_native(name: str) -> NoReturn:
    path = _BIN_DIR / name
    _exec(path, [str(path), *sys.argv[1:]])


def _exec_python(name: str) -> NoReturn:
    path = _BIN_DIR / name
    _exec(Path(sys.executable), [sys.executable, str(path), *sys.argv[1:]])


def combine() -> NoReturn:
    _exec_native("combine")


def text2workspace() -> NoReturn:
    _exec_python("text2workspace.py")


def combine_cards() -> NoReturn:
    _exec_python("combineCards.py")


def combine_tool() -> NoReturn:
    _exec_python("combineTool.py")


def comment_uncerts() -> NoReturn:
    _exec_python("commentUncerts.py")


def debug_chains() -> NoReturn:
    _exec_python("debugChains.py")


def fit_roofit_ad() -> NoReturn:
    _exec_python("fitRooFitAD.py")


def plot_1d_scan() -> NoReturn:
    _exec_python("plot1DScan.py")


def plot_bsm_xsbr_limit() -> NoReturn:
    _exec_python("plotBSMxsBRLimit.py")


def plot_gof() -> NoReturn:
    _exec_python("plotGof.py")


def plot_impacts() -> NoReturn:
    _exec_python("plotImpacts.py")


def plot_limit_grid() -> NoReturn:
    _exec_python("plotLimitGrid.py")


def plot_limits() -> NoReturn:
    _exec_python("plotLimits.py")


def prune_uncerts() -> NoReturn:
    _exec_python("pruneUncerts.py")


def doctor() -> None:
    parser = argparse.ArgumentParser(
        description="Check the higgs-combine-tool wheel installation"
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    root_dir = _root_dir()
    checks: dict[str, object] = {
        "higgs_combine_tool_version": importlib.metadata.version(_DISTRIBUTION_NAME),
        "root_distribution_version": importlib.metadata.version("root"),
        "root_package": str(root_dir),
        "combine_binary": str(_BIN_DIR / "combine"),
        "combine_library": str(_LIB_DIR / "libHiggsAnalysisCombinedLimit.so"),
        "combine_source": str(_COMBINE_SRC),
    }
    missing = [
        key
        for key in ("combine_binary", "combine_library", "combine_source")
        if not Path(str(checks[key])).exists()
    ]
    probe = subprocess.run(
        [str(_BIN_DIR / "combine"), "--help"],
        env=runtime_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    checks["combine_help_returncode"] = probe.returncode
    checks["ok"] = not missing and probe.returncode == 0
    if missing:
        checks["missing"] = missing

    if args.json:
        print(json.dumps(checks, indent=2, sort_keys=True))
    else:
        for key, value in checks.items():
            print(f"{key}: {value}")
    if not checks["ok"]:
        raise SystemExit(1)
