# Changelog

All notable changes to `conditional-method` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.5] - 2026-08-17

### Changed

- **Docs/README scrubbed of personal identifiers**: the GitHub username
  `jymchng` is replaced with an `OWNER` placeholder across README, docs,
  CHANGELOG, SECURITY.md and mkdocs.yml, so the PyPI description and docs no
  longer expose the maintainer's handle.

## [0.2.4] - 2026-08-16

### Fixed

- **Pyodide wheel is now actually installable in Pyodide 314.0.3** (the
  AsyncMove playground). The release pipeline re-tags the wheel from
  `pyemscripten_2025_0_wasm32` to `emscripten_5_0_3_wasm32` (filename,
  `WHEEL` metadata, and recomputed `RECORD` hashes — the binary is
  unchanged) before uploading, because micropip 0.11.1's
  `platform_to_version()` only strips the `emscripten_` prefix and rejected
  the `pyemscripten_*` tag with `ValueError: Wheel was built with Emscripten
  vpyemscripten.2025.0 but Pyodide was built with Emscripten v5.0.3`.
  Resolves the caveat noted in 0.2.3.

## [0.2.3] - 2026-08-16

### Changed

- **Pyodide wheel now targets Emscripten 5.0.3** (pyodide 314.0.3): the
  release workflow pins `pyodide-version: 314.0.3`, so the `*.whl` built
  for the browser matches the AsyncMove playground's Pyodide runtime.
  (Caveat: micropip 0.11.1 in pyodide 314.0.3 still reports the runtime as
  Emscripten "5.0.3" while the wheel tag uses the "2025.0" scheme — the
  installability mismatch is a pyodide runtime-side issue, tracked
  separately.)

## [0.2.2] - 2026-08-16

### Fixed
- README logo on PyPI: the header image used a relative path
  (`assets/conditional-method-logo.png`), which PyPI cannot render. The
  logo asset was renamed to match the distribution and the README now
  references an absolute URL
  (`https://raw.githubusercontent.com/OWNER/conditional-method/main/...`),
  so the logo displays on the PyPI project page.
- The logo image was downscaled 1024→512 px (1 MB → ~250 KB) to keep the
  sdist and page loads light.

## [0.2.1] - 2026-08-16

### Changed
- **Import module renamed to `conditional_method`** (the distribution was
  already `conditional-method`). The decorator is `@cfg` with aliases
  `@cm`/`@if_`; there is **no** `@conditional_method` decorator (the old
  callable alias was removed and the error text now says "`@cfg` must be
  used as a decorator").
- The old `cfg` module is kept as a thin **compatibility shim** re-exporting
  from `conditional_method` (incl. `_c`, `__version__`, `__all__`), so code
  written against the 0.2.0 module keeps working.
- C extension path is `conditional_method._c`; gate scripts and CI point at
  the renamed source.
- Canonical form everywhere: `from conditional_method import cfg`.

## [0.2.0] - 2026-08-16

### Added
- Pure-C implementation: `conditional_method._c` (a CPython C extension) replaces the
  pure-Python implementation entirely.
  - `@cfg` (aliases `@cm`, `@if_`): conditional
    method selection at class build time.
  - `@cfg_attr`: conditionally apply a chain of decorators.
  - `debug` / `debug_enabled`: opt-in C debug logging.
  - `_get_mod_qual_func_name`: qualified-name helper.
- abi3 (Limited API) build: a single `cp39-abi3` wheel covers CPython
  3.9–3.14.
- Test-only fault injection (`PY_CFG_TESTING`): `set_alloc_fail_count`
  makes guarded allocations fail deterministically for OOM-path coverage.
- Benchmarks: `tests/benchmark.py` (pytest-benchmark) and
  `benchmarks/bench.py` (standalone timeit harness → `results.json`).
- CI coverage gate (`scripts/coverage-gate.sh`): builds `conditional_method._c` with gcov
  coverage + `PY_CFG_TESTING`, runs the suite, and fails if `src/conditional_method/_c.c`
  line coverage drops below 90%.
- CI sanitizer gate (`scripts/sanitize-gate.sh`): runs the full suite under
  ASan/UBSan with `abort_on_error`/`halt_on_error` so any report fails CI.
- Many-arch abi3 wheel workflow (`wheels.yml`): cibuildwheel matrix
  (linux x86_64/aarch64/i686/ppc64le/s390x/armv7l, macos arm64/x86_64,
  windows AMD64/ARM64/x86), each producing a single `cp39-abi3` wheel;
  artifacts are tag-checked and smoke-tested (`scripts/smoke_wheel.py`).
- GitHub Pages workflow (`pages.yml`): builds the MkDocs+Material site and
  deploys it to GitHub Pages when enabled.
- Release workflow (`release.yml`): sdist + full wheel matrix + GitHub
  Release + PyPI trusted publishing.
- `tests/test_alloc_fail.py`: deterministic allocation-failure / error-path
  coverage for the C module (raises C line coverage past 90%).
- `tests/test_property.py`: 13 hypothesis property tests asserting parity
  with a plain-Python reference model (caught and fixed a real cfg_attr
  empty-decorator cache bug).

### Changed
- Rebuilt as a production-ready package: the C extension (`conditional_method._c`) with
  the `cfg` import module, published on PyPI as **`conditional-method`**.
- Raised the C line coverage from ~84% to >91% via targeted error-path
  tests and `CFG_ALLOC_TEST_FAIL()` test-only reachability hooks.
- Modernized tests for current CPython (`RuntimeError` → `TypeError`
  where the interpreter changed).
- CPython 3.9–3.14 cross-version support: `tests/_compat.py` handles the
  `<3.12` `__set_name__` `RuntimeError` wrapping vs `3.12+` `TypeError`,
  and the `<3.11` `AttributeError` vs `3.11+` `TypeError`
  context-manager-protocol difference.
- README rewritten in a FastAPI-style layout with logo, badges, and
  quick examples.
- Production docs: MkDocs+Material site (12 pages), CHANGELOG, SECURITY.

### Removed
- Pure-Python implementation files (`_py_lib.py`, `_logger.py`).
