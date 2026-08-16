# Development

Everything you need to develop `conditional-method` locally.

## Setup

```bash
uv sync --group dev --group test --group build
```

## Build the C extension

```bash
uv run --group build python setup.py build_ext --inplace
```

For coverage instrumentation (used by the gcov gate):

```bash
CFLAGS="-DPY_CFG_TESTING --coverage -O0" LDFLAGS="--coverage" \
  uv run --group build python setup.py build_ext --inplace
```

## Run the tests

```bash
uv run --group test python -m pytest tests -q
```

With the fault-injection hooks active (all 264 tests run):

```bash
CFLAGS="-DPY_CFG_TESTING" uv run --group build python setup.py build_ext --inplace
uv run --group test python -m pytest tests -q
```

## Lint and format

```bash
uvx ruff check .
uvx ruff format --check .
```

## CI gates (also runnable locally)

```bash
bash scripts/coverage-gate.sh        # C line coverage must be >= 90%
bash scripts/sanitize-gate.sh        # ASan/UBSan must run clean
```

## Benchmarks

```bash
uv run --group test python -m pytest tests/benchmark.py -v   # pytest-benchmark
uv run python benchmarks/bench.py                            # standalone harness
```

Results are written to `benchmarks/results/results.json` and summarized in
[Benchmarks](benchmarks.md).

## Project layout

```
src/cfg/            package (import shim + C extension sources)
  __init__.py       thin import shim
  _c.c              the entire implementation (CPython C extension)
  py.typed          type marker
tests/              pytest suite (incl. fault-injection + error-path tests)
scripts/            CI gate scripts (coverage, sanitizers, wheel smoke)
benchmarks/         standalone benchmark harness + results
docs/               MkDocs site sources
.github/workflows/  CI/CD workflows
```
