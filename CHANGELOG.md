# Changelog

All notable changes to `conditional-method` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-08-20

### Removed

- **Pure-Python fallback (`conditional_method._py`)**: the fallback module
  and its automatic use when the C extension cannot be imported were removed.
  `import conditional_method` now requires the C extension
  (`conditional_method._c`), reverting to the pre-0.3.0 behavior; the package
  is C-only again.

## [0.3.0] - 2026-08-20

### Added

- **Performance optimizations** (C extension, `_c.c`):
  - **#1** internal `_cm_inner_fast(func, condition)` fast path: `cm()`
    and `_cm_wrapper` call the cache/selection logic directly, eliminating
    the `Py_BuildValue` tuple packing on every decoration. The public
    `_cm_inner` stays as a `METH_VARARGS` shim for the closure protocol.
  - **#4** cache keys (qualified names) are interned
    (`PyUnicode_InternInPlace`), so repeated decorations of the same name
    share one key object.
  - **#5** constant-condition fast path: `condition is True` short-circuits
    condition evaluation, caches and returns the function identity, and
    clears any recorded failure for that name.
  - **#6** amortized dead-weakref sweep: a dead-counter threshold (plus the
    existing high-water mark) triggers the cache sweep, keeping the
    bounded-cache contract while avoiding a full scan on every write.
  - Benchmark wins (median of 3, best us/op): `cfg_true_decorate` −4.2%,
    `cfg_false_decorate` −4.2%, `cfg_callable_decorate` −2.3%,
    `cfg_class_select` −1.8%, `cfg_attr_true_single` −9.2%,
    `cfg_attr_true_multi` −11.9%; `call_through_cfg` unchanged (−0.2%).
  - **Not applicable** (documented in code): `PyDict_Freeze` (#2) is not
    part of the Limited API; the strong-ref cache (#3) was reverted to
    preserve the leak-safety contract (weakrefs retained for winners).
- **Friendly failure API** (#7): public `pending_failures()` alias of the
  private `_get_failed()`, and `ConditionFailureError(TypeError)` carrying
  the failing qualnames on a `.failed` attribute; `assert_all_true()`
  keeps raising, now with the richer exception.
- **Pure-Python fallback** (#10): new `src/conditional_method/_py.py`
  mirrors the C extension's public API and is used automatically when the
  C extension cannot be imported (e.g. exotic platforms without a
  wheel), so `import conditional_method` never fails outright.

### Changed

- The package docstring and build/benchmark docstrings no longer claim
  there is "no pure-Python implementation".
- Type stubs (`__init__.pyi`) now declare `pending_failures()` and
  `ConditionFailureError`; mypy is clean across the configured scope.

## [0.2.10] - 2026-08-18

### Added

- **Bounded, leak-free module caches** (`_cm_cache` / `_cfg_attr_cache`):
  true-condition winners are cached as **weak references** instead of strong
  references, so a `@cfg`-selected function no longer keeps its class and
  module alive for the whole process after the class is garbage-collected.
  When either cache grows past an internal high-water mark (128 entries),
  the next write triggers a sweep that prunes dead weakref entries, keeping
  long-running processes bounded. `_TypeErrorRaiser` placeholders are stored
  strongly (they are not weakly referencable) and are never pruned.
- **Append-only failure tracking**: `_failed_qualnames` (backing
  `assert_all_true()` / `_get_failed()`) is no longer cleared when a
  `_TypeErrorRaiser` is created or called. Every name whose condition ended
  up with no true winner is reported, across all classes in the
  module/process \u2014 not just the most recent one. A name is removed again
  only when a later `condition=True` winner for that exact name resolves it
  (or the set is cleared explicitly).

### Fixed

- **abi3 wheel portability**: the weakref-based cache dereference previously
  used `PyWeakref_GetRef` (CPython 3.13+), which is **not** part of the
  Limited API. The `cp39-abi3` wheel compiled against newer headers failed to
  import on older runtimes (`ImportError: undefined symbol: PyWeakref_GetRef`
  on Python 3.9/3.12). Dereferencing now uses the portable, stable-ABI
  `PyWeakref_GetObject` + `Py_INCREF`, verified to import and pass the test
  suite on Python 3.9, 3.12, 3.13 and 3.14.

## [0.2.9] - 2026-08-17

### Added

- **Eager module-level validation**: `assert_all_true()` raises `TypeError`
  at import time (call it as the last module statement) naming every
  `@cfg`-decorated function whose condition is false — i.e. that ended up as
  a `_TypeErrorRaiser` with no `condition=True` winner. `_get_failed()`
  returns the failing qualname list for introspection. This makes
  config/feature-flag modules fail fast instead of at first call.
- New fail-injection sweep tests (`test_alloc_fail.py`) exercising every
  public code path under allocation failure; the C coverage gate now
  reports **testable** coverage (import-time-only `PyInit__c` /
  `CfgCallable_new_wrapper` guard branches, unreachable by any test, are
  excluded) — gate passes at 92.76%.

## [0.2.8] - 2026-08-17

### Fixed

- **Wasm crash with callable conditions** (`@cfg(condition=lambda f: ...)`,
  `@cfg_attr` with callable conditions, and the factory closure paths):
  the C extension used the inline `PyTuple_SET_ITEM` / `PyTuple_GET_ITEM` /
  `PyTuple_GET_SIZE` macros, which read a stale `PyTupleObject` layout on
  CPython 3.14/wasm (pyodide/Emscripten) and corrupted memory — the runtime
  died with `RuntimeError: null function or function signature mismatch` as
  soon as a callable condition was evaluated. All remaining tuple macros were
  replaced with the real libpython functions (`PyTuple_SetItem`,
  `PyTuple_GetItem`, `PyTuple_Size`), which are wasm-safe and Limited-API
  (abi3) clean. The native test suite could not catch this (native CPython's
  layout differs); the crash was reproduced on pyodide 314.0.3 (the AsyncMove
  playground runtime).

## [0.2.7] - 2026-08-17

### Added

- **PEP 561 type stubs**: `conditional_method/__init__.pyi` ships in the
  wheel (and sdist), giving editors/type checkers precise signatures for the
  C-extension API via `@overload` — `@cfg(condition=...)` / `@cm` / `@if_`
  (factory, direct, and positional-condition forms), `@cfg_attr`
  (with `decorators=[...]`), plus `debug`, `debug_enabled`,
  `_get_mod_qual_func_name`, `__version__`. The stubs cover only the real
  runtime exports; the nonexistent `conditional_method` import alias is not
  stubbed.

### Changed

- **Docs match reality**: `docs/api.md` and the package docstring no longer
  claim a `conditional_method` import alias (it was never exported by the C
  module); `docs/errors.md` error heading corrected to the actual message
  (`@cfg`). The legacy `cfg` shim's `py.typed` marker is restored so it
  ships typed-consistent with its package-data declaration.
- **Release pipeline**: the pyodide wheel is now built against the pinned
  `314.0.3` xbuildenv (`[tool.cibuildwheel] pyodide-version`) and re-tagged
  into two variants — `pyemscripten_2026_0_wasm32` (published to PyPI so
  `micropip.install("conditional-method")` works from the playground's
  Packages tab) and `emscripten_5_0_3_wasm32` (GitHub Release asset for
  direct-URL installs). PyPI upload excludes only the non-py `emscripten`
  variant.

## [0.2.6] - 2026-08-17

### Changed

- **Leaner source distribution**: added a `MANIFEST.in` that prunes
  nonessential files from the sdist (`.github/`, `.vscode/`, `assets/`,
  `benchmarks/`, `docs/`, `examples/`, `scripts/`, `test-assets/`, `tests/`,
  plus CI/dev config). The sdist now ships only the buildable sources
  (`src/` including the C source needed for source installs) and essential
  metadata (README, LICENSE, CHANGELOG, SECURITY, pyproject.toml, setup.py)
  — from ~110 entries down to ~24. Wheels were already package + dist-info
  only and are unchanged.

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
