# Benchmarks

## Harnesses

- **Standalone** — `python benchmarks/bench.py` runs a reproducible timeit
  harness (100 000 loops, 5 repeats) and writes
  `benchmarks/results/results.json` (committed) plus a table to stdout.
- **Closures in a class** — `python benchmarks/bench_cfg_closure.py` measures
  `@cfg` with closure conditions on class methods (definition time and call
  time vs plain/runtime-if baselines); writes
  `benchmarks/results/results_cfg_closure.json` (committed).
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

## @cfg with closures in a class

Environment: CPython 3.13.13, linux x86_64, `conditional-method` 0.2.6.dev1.
(Full JSON in `benchmarks/results/results_cfg_closure.json`.)

Definition time (per iteration: build the class inside a factory; methods
close over an enclosing `env` variable):

| scenario | best µs/op | mean µs/op |
|---|---|---|
| plain_class_def | 8.930 | 10.897 |
| cfg_class_closure_def | 12.758 | 13.398 |
| cfg_class_closure_callable_def | 12.695 | 13.252 |
| cfg_class_two_conditions_def | 12.843 | 13.364 |

Call time (class built once, method called per op; methods read the closure
cell):

| scenario | best µs/op | mean µs/op |
|---|---|---|
| call_plain_method | 0.087 | 0.088 |
| call_cfg_method | 0.078 | 0.079 |
| call_runtime_if | 0.105 | 0.106 |

### Interpretation

- **Closure conditions work with `@cfg` on class methods** — a `bool`
  condition closing over an enclosing variable, a callable condition
  (`lambda f: env == ...`), and two complementary conditions all select the
  intended method (sanity-checked: returns `'prod'`).
- **Definition cost is bounded**: a class with `@cfg`-gated closure methods
  takes ~13 µs to build vs ~9 µs for a plain class (+~1.4×, a one-time
  class-build-time cost). Callable-closure conditions cost the same as
  bool-closure ones.
- **Call-time payoff**: the `@cfg`-selected method call (0.078 µs) is faster
  than both the plain method (0.087 µs) and the runtime-`if` baseline it
  replaces (0.105 µs, ~26% faster) — selection happens once at class-build
  time, not per call.

Reproduce locally: `python benchmarks/bench_cfg_closure.py`.
