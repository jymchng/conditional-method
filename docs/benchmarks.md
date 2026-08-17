# Benchmarks

## Harnesses

- **Standalone** — `python benchmarks/bench.py` runs a reproducible timeit
  harness (100 000 loops, 5 repeats) and writes
  `benchmarks/results/results.json` (committed) plus a table to stdout.
- **Class-body closure pattern** — `python benchmarks/bench_cfg_closure.py`
  measures `@cfg` on the nested-factory closure pattern
  (`work = make()` in a class body): definition time and call time vs
  plain/runtime-if baselines; writes
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

## @cfg with the class-body closure pattern

Environment: CPython 3.13.13, linux x86_64, `conditional-method` 0.2.6.dev1.
(Full JSON in `benchmarks/results/results_cfg_closure.json`.)

The pattern under test is a nested factory inside a class body that builds a
method as a closure:

```python
class Worker:
    def make():                      # factory defined in the class body
        @cfg(condition=True)         # selection happens at decoration time
        def work(self): ...
        return work                  # returns the (possibly cfg-kept) closure
    work = make()                    # class body assigns the closure
```

Definition time (per iteration: rebuild the class, `work = make()`):

| scenario | best µs/op | mean µs/op |
|---|---|---|
| plain_closure_def | 9.866 | 10.556 |
| cfg_closure_true_def | 11.078 | 11.350 |
| cfg_closure_cond_def | 11.006 | 11.888 |
| cfg_closure_select_def | 11.687 | 12.696 |

Call time (class built once, method called per op):

| scenario | best µs/op | mean µs/op |
|---|---|---|
| call_plain_closure | 0.076 | 0.108 |
| call_cfg_closure | 0.075 | 0.120 |
| call_runtime_if | 0.077 | 0.085 |

### Interpretation

- **`@cfg` works with the class-body closure pattern** — `work = make()`
  where `make()` returns an inner function decorated with `@cfg` selects and
  caches the method at class-build time (sanity-checked: returns `'kept'`).
  A condition closing over an enclosing cell (`condition=enabled`) and a
  prod/dev selection via two `make()` factories behave identically.
- **Definition cost is small**: adding `@cfg` to the closure method costs
  ~11 µs vs ~10 µs for a plain `work = make()` (+~12%, a one-time
  class-build-time cost).
- **Call time is unchanged**: calling the `@cfg`-kept closure method
  (0.075 µs) is the same as a plain closure method (0.076 µs) — selection
  happens once at class-build time, not per call. (Best-case values; means
  are noisy at this scale.)
- **Guard behavior**: a `condition=False` method in this pattern makes
  **class creation fail** (`TypeErrorRaiser.__set_name__` raises TypeError) —
  it is a build-time guard, not a per-call drop.

Reproduce locally: `python benchmarks/bench_cfg_closure.py`.
