# Benchmarks

## Harnesses

- **Standalone** — `python benchmarks/bench.py` runs a reproducible timeit
  harness (100 000 loops, 5 repeats) and writes
  `benchmarks/results/results.json` (committed) plus a table to stdout.
- **pytest-benchmark** — `nox -s benchmark` runs `tests/benchmark.py` with
  `pytest-benchmark`, giving statistical comparison across runs.

## Measured results

Environment: CPython 3.13, linux x86_64, `conditional-method` 0.2.0.dev41.
(Full JSON in `benchmarks/results/results.json`.)

| scenario | best µs/op | mean µs/op |
|---|---|---|
| plain_call | 0.071 | 0.095 |
| plain_class | 8.522 | 9.979 |
| cfg_true_decorate | 2.319 | 2.492 |
| cfg_false_decorate | 2.864 | 2.948 |
| cfg_callable_decorate | 2.543 | 2.895 |
| cfg_class_select | 14.602 | 15.881 |
| cfg_attr_true_single | 7.050 | 7.352 |
| cfg_attr_true_multi | 10.074 | 10.921 |
| cfg_attr_false | 5.190 | 5.750 |
| call_plain | 0.073 | 0.075 |
| call_through_cfg | 0.075 | 0.076 |

## Interpretation

- **Decoration cost is bounded and small**: applying `@cfg` costs roughly
  2–3 µs (condition evaluation + cache bookkeeping); `@cfg_attr` with
  decorators costs 5–10 µs (the decorators themselves dominate).
- **Call overhead is negligible**: calling a function selected by `@cfg` is
  indistinguishable from a plain call (0.075 vs 0.073 µs/op) — the selection
  happens at decoration/class-build time, not per call.
- **Class selection** (a class with multiple `@cfg`-gated same-name methods)
  costs ~15 µs to build, which is dominated by class creation itself
  (plain class baseline: ~8.5–10 µs).
- The C extension keeps decoration and selection fast while a plain Python
  decorator with equivalent logic would be several times slower per call.

Reproduce locally: `python benchmarks/bench.py`.
