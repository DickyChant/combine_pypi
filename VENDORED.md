# Vendored Combine source

`vendor/CombinedLimit` is derived from
`cms-analysis/HiggsAnalysis-CombinedLimit` tag `v11.0.0`, commit
`66f59f9a899b143dc95a1d6d866fab5df8850189`.

Included paths:

- `CMakeLists.txt`, `LICENSE`
- `bin/`, `interface/`, `src/`, `python/`, `scripts/`
- runtime `data/` except the large `data/ci/` and `data/tutorials/` trees and
  binary `.root` benchmark fixtures

Local modification:

- `CMakeLists.txt` wraps `add_subdirectory(test)` in the existing
  `BUILD_TESTS` option. The changed lines carry an inline modification notice.
- Its Python/script source inputs use `CMAKE_CURRENT_SOURCE_DIR` so the source
  can be included by the wheel wrapper with `add_subdirectory()`.
- Native artifacts use the existing configurable `CMAKE_INSTALL_*DIR`
  variables instead of hard-coded `bin`, `lib`, and `include` destinations, so
  they remain private to the `cms_combine` wheel package.
- Boost discovery permits CMake's standard `FindBoost` module instead of
  requiring `BoostConfig.cmake`, which AlmaLinux 8's `boost-devel` package does
  not provide; the component targets are linked directly so their include paths
  and transitive dependencies remain attached.

The ROOT-wheel relocation is not a vendored-source change. It is applied only
to the ephemeral build environment by `scripts/prepare_root.py` after an exact
distribution-version check.
