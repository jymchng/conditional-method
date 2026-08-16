# Changelog

All notable changes to `python-cfg` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI coverage gate (`scripts/coverage-gate.sh`): builds `cfg._c` with gcov
  coverage + `PY_CFG_TESTING`, runs the suite, and fails if `src/cfg/_c.c`
  line coverage drops below 90%.
- CI sanitizer gate (`scripts/sanitize-gate.sh`): runs the full suite under
  ASan/UBSan with `abort_on_error`/`halt_on_error` so any report fails CI.
- Many-arch abi3 wheel workflow (`wheels.yml`): cibuildwheel matrix
  (linux x86_64/aarch64/i686/ppc64le/s390x/armv7l, macos arm64/x86_64,
  windows AMD64/ARM64/x86), each producing a single `cp39-abi3` wheel;
  artifacts are tag-checked and smoke-tested (`scripts/smoke_wheel.py`).
- GitHub Pages workflow (`pages.yml`): builds the MkDocs+Material site and
  deploys it to GitHub Pages when enabled.
- `tests/test_alloc_fail.py`: deterministic allocation-failure / error-path
  coverage for the C module (raises C line coverage past 90%).

### Changed
- CPython 3.9–3.14 cross-version support: `tests/_compat.py` handles the
  `<3.13` `__set_name__` `RuntimeError` wrapping vs `3.13+` `TypeError`,
  and the `AttributeError` vs `TypeError` context-manager-protocol
  difference.
- README rewritten in a FastAPI-style layout with logo, badges, and
  quick examples.

## [0.2.0.dev] - unreleased

### Added
- Pure-C implementation: `cfg._c` (a CPython C extension) replaces the
  pure-Python implementation entirely.
  - `@cfg` (aliases `@if_`, `@cm`, `@conditional_method`): conditional
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

### Changed
- Project renamed from `conditional-method` to **`python-cfg`**;
  import module is `cfg`.
- Raised the C line coverage from ~84% to >91% via targeted error-path
  tests and `CFG_ALLOC_TEST_FAIL()` test-only reachability hooks.
- Modernized tests for current CPython (`RuntimeError` → `TypeError`
  where the interpreter changed).

### Removed
- Pure-Python implementation files (`_py_lib.py`, `_logger.py`).
