# `higgs-combine-tool`: a pip-installable CMS Combine experiment

This repository builds an **unofficial, experimental** Linux wheel for the
[CMS Higgs Combine tool](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/v11.0.0/).
The wheel contains Combine v11.0.0's native executable, shared library, Python
modules, command-line scripts, headers, and runtime model data. ROOT itself is
provided by the official [`root` PyPI wheel](https://pypi.org/project/root/).

This project deliberately does **not** publish to PyPI. It supports CI-built
wheels, editable source checkouts, and direct installation from GitHub.
The compact project page is hosted at
[dickychant.github.io/combine_pypi](https://dickychant.github.io/combine_pypi/).

## Installation

### Install a CI wheel

Download the `higgs-combine-tool-wheel` artifact from a successful
[GitHub Actions run](https://github.com/DickyChant/combine_pypi/actions), then:

```bash
python3.13 -m pip install virtualenv
python3.13 -m virtualenv .venv
source .venv/bin/activate
python -m pip install ./higgs_combine_tool-11.0.0-*.whl

combine --help
text2workspace.py card.txt -o workspace.root
combine -M AsymptoticLimits workspace.root
```

### Editable source checkout

After installing the system C++ headers listed under
[Local development](#local-development-with-virtualenv):

```bash
git clone https://github.com/DickyChant/combine_pypi.git
cd combine_pypi
python3.13 -m pip install virtualenv
python3.13 -m virtualenv .venv
source .venv/bin/activate
python -m pip install -e .
```

### Directly from GitHub

This performs the same native build and therefore has the same system-header
requirements as an editable checkout:

```bash
python -m pip install "git+https://github.com/DickyChant/combine_pypi.git"
```

## Why the package is not named `combine`

The exact PyPI project name [`combine`](https://pypi.org/project/combine/) is
already owned by an unrelated static-site builder. The distribution metadata
therefore uses `higgs-combine-tool`; installing it still creates the expected
`combine` command. The private implementation module remains `cms_combine` so
the wheel layout can describe what it wraps without claiming an upstream CMS
distribution.

## Current support boundary

- Combine source: tag `v11.0.0`, commit
  `66f59f9a899b143dc95a1d6d866fab5df8850189`.
- ROOT distribution: exactly `root==0.1a12` (ROOT 6.40.00).
- Platform: CPython 3.10–3.14 on Linux x86-64 with glibc 2.28 or newer.
- Core CLI, datacard parsing, workspace creation, and native statistical methods
  are in scope.
- CMSSW-, CRAB-, and CombineHarvester-specific integrations remain external;
  plotting helpers may require `pip install 'higgs-combine-tool[plotting]'`.

The ROOT project labels its PyPI distribution alpha and explicitly says not to
rely on it for production. This wheel therefore is not a replacement for the
official CMSSW installation in production or publication workflows.

## What had to be adapted

Combine already supports standalone CMake builds, so no CMSSW code is needed
for the core executable. Four narrow packaging workarounds are currently
required:

1. ROOT 0.1a12's generated CMake target files contain the wheel-build staging
   path `mock_site_packages/ROOT`. `scripts/prepare_root.py` validates the exact
   ROOT distribution version and relocates only that known fragment inside the
   isolated build environment.
2. Combine v11.0.0 adds its `test` directory even with `BUILD_TESTS=OFF`, which
   triggers a GoogleTest network fetch. The vendored CMake file is marked with a
   small guard so runtime wheels do not build tests.
3. Its native install rules hard-code top-level `bin`, `lib`, and `include`
   destinations. They now honor Combine's existing `CMAKE_INSTALL_*DIR`
   variables so those files stay inside the wheel's private package directory.
4. AlmaLinux 8's `boost-devel` package has no `BoostConfig.cmake`, so the
   vendored lookup permits CMake's standard `FindBoost` module rather than
   forcing config mode and links the imported component targets directly.

The resulting wheel depends on `root==0.1a12` rather than duplicating roughly
250 MB of ROOT libraries. The repair step bundles Boost libraries but excludes
SONAMEs supplied by the declared ROOT dependency, then verifies relocatable
`$ORIGIN` runtime paths.

## Local development with `virtualenv`

Install the ordinary C++ build headers first. For Alma/RHEL-like systems:

```bash
sudo dnf install gcc-c++ boost-devel eigen3-devel
```

For Ubuntu/Debian-like systems:

```bash
sudo apt-get install g++ libboost-filesystem-dev libboost-program-options-dev libeigen3-dev
```

Then build in a project-local virtualenv:

```bash
python3.13 -m pip install virtualenv
python3.13 -m virtualenv .venv
source .venv/bin/activate
python -m pip install root==0.1a12 pandas PyYAML build scikit-build-core cmake ninja auditwheel patchelf
python -m pip install -e .
```

To produce and repair a wheel instead of using editable mode:

```bash
python -m build --wheel --no-isolation
python scripts/repair_wheel.py \
  --wheel dist/higgs_combine_tool-11.0.0-py3-none-linux_x86_64.whl \
  --dest-dir wheelhouse \
  --plat manylinux_2_34_x86_64  # use the policy supported by the local host
```

For a clean end-to-end install test:

```bash
python3.13 -m virtualenv .venv-test
source .venv-test/bin/activate
python -m pip install wheelhouse/higgs_combine_tool-11.0.0-*.whl
python tests/smoke_test.py
```

The local platform tag is host-dependent. CI artifacts are built in the
`manylinux_2_28_x86_64` container by GitHub Actions. RHEL/AlmaLinux 9 marks
executables with its `x86-64-v2` platform baseline, which a generic x86-64 wheel
must not claim. On such a host, either test the raw wheel or add
`--disable-isa-ext-check` only for a host-local diagnostic repair; never
distribute that artifact. The CI artifact path deliberately keeps the ISA check
enabled.

## CI wheel artifacts

`.github/workflows/build-wheels.yml` builds once with CPython 3.13 because the
native code does not use the Python C API; scikit-build-core therefore emits a
`py3-none` wheel with a `manylinux_2_28_x86_64` compatibility tag (auditwheel
may also add a compatible older policy tag). The workflow then installs that
same wheel with Python 3.10 and 3.14 and runs a blind AsymptoticLimits fit at
both ends of the supported range. Every successful run uploads the wheel as
the `higgs-combine-tool-wheel` artifact.

There is deliberately no PyPI publishing job or release credential in this
repository. GitHub Actions produces installable build artifacts only; editable
and direct-GitHub installs remain source builds.

## Provenance and licensing

The minimal source subset needed to compile and run Combine is vendored under
`vendor/CombinedLimit`; the large upstream tutorial/CI samples and binary ROOT
benchmark fixtures are omitted.
See `vendor/CombinedLimit/UPSTREAM_COMMIT` and `VENDORED.md` for the exact source
and modifications. Combine and this packaging layer are distributed under the
Apache License 2.0; both license copies are included in source and wheel
metadata.
