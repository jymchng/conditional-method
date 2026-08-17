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
- **`@lambda f: f()` trick vs `@cfg`** — `python benchmarks/bench_lambda_vs_cfg.py`
  compares the decorator-call trick (a factory run at class creation that
  returns the selected method closure) against `@cfg` conditional method
  selection, plus a plain baseline; writes
  `benchmarks/results/results_lambda_vs_cfg.json` (committed).
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

## `@lambda f: f()` trick vs `@cfg`

Environment: CPython 3.13.13, linux x86_64, `conditional-method` 0.2.6.dev1.
(Full JSON in `benchmarks/results/results_lambda_vs_cfg.json`.)

Two ways to pick a method implementation at class-build time from an
enclosing `ENV`:

```python
# 1) decorator-call trick: the factory runs at class creation
class Worker:
    @lambda f: f()
    def work():
        if ENV == "PROD":
            def work(self, item: int): ...   # closure returned as the method
            return work
        if ENV == "DEV":
            def work(self, item: int): ...
            return work

# 2) @cfg conditional selection (same-named methods, conditions over ENV)
class Worker:
    @cfg(condition=ENV == "PROD")
    def work(self, item: int): ...
    @cfg(condition=ENV == "DEV")
    def work(self, item: int): ...
```

Definition time (class rebuilt per iteration; bodies use `return` so timing
measures selection/closure machinery, not I/O):

| scenario | best µs/op | mean µs/op |
|---|---|---|
| lambda_trick_def | 8.310 | 9.190 |
| cfg_two_method_def | 12.196 | 12.863 |
| plain_method_def | 8.238 | 8.798 |

Call time (class built once, trivial body `return item` = pure dispatch):

| scenario | best µs/op | mean µs/op |
|---|---|---|
| call_lambda_trick | 0.081 | 0.081 |
| call_cfg_two_method | 0.080 | 0.109 |
| call_plain | 0.080 | 0.091 |

### Interpretation

- **Both patterns select the intended method** (sanity-checked: `ENV="PROD"`
  → the PROD method runs). `@cfg` also caches the selection and replaces a
  False method with a `TypeErrorRaiser` build-time guard.
- **Definition**: `@cfg` costs ~12.2 µs vs ~8.3 µs for the `@lambda f: f()`
  trick (+~48%) and ~8.2 µs for a plain method — the extra is `@cfg`'s
  condition evaluation + cache bookkeeping, a one-time class-build cost.
- **Call time is identical** (~0.08 µs best for all three): selection happens
  at class-build time, so the per-call dispatch is the same whether you use
  the trick, `@cfg`, or a plain method.
- The `@lambda f: f()` trick is plain Python (no caching, no guard); `@cfg`
  buys the build-time guard, caching, and identical call-time at a modest
  one-time definition cost.

Reproduce locally: `python benchmarks/bench_lambda_vs_cfg.py`.
