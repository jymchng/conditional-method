"""Benchmark: ``@cfg`` with the class-body closure pattern (conditional-method).

The pattern under test is the nested-factory closure inside a class body:

    class Worker:
        def make():
            def work(self): ...      # inner function closes over make's scope
            return work
        work = make()                # class body assigns the closure

``make()`` builds a method as a closure; ``@cfg`` applied to the inner
``work`` decides at decoration time whether it is kept (and cached) or
replaced by a ``TypeErrorRaiser``.

Measured axes:

  Definition time (the class is rebuilt every iteration):
    plain_closure_def            work = make() with a plain inner function
    cfg_closure_true_def         @cfg(condition=True) on the inner work
    cfg_closure_cond_def         @cfg(condition=<cell>) - condition closes
                                 over an enclosing variable
    cfg_closure_select_def       two make() factories (prod/dev); the class
                                 body assigns the selected one

  Call time (class built once; method called per iteration):
    call_plain_closure           Worker().work() - plain closure method
    call_cfg_closure             Worker().work() - @cfg-kept closure method
    call_runtime_if              baseline: the method does the check at call
                                 time (the pattern @cfg replaces at build time)

Results are written to benchmarks/results/results_cfg_closure.json and a
human-readable table is printed.

Run:  python benchmarks/bench_cfg_closure.py
"""

from __future__ import annotations

import json
import platform
import timeit
from pathlib import Path

from conditional_method import __version__, cfg

RESULTS_PATH = Path(__file__).parent / "results" / "results_cfg_closure.json"

N = 100_000
REPEAT = 5

PROD = "production"
DEV = "development"


# --- definition-time scenarios: each rebuilds the class per iteration ---
def plain_closure_def():
    def build():
        def make():
            def work(self):
                return 1

            return work

        class Worker:
            work = make()

        return Worker

    return lambda: build()


def cfg_closure_true_def():
    def build():
        def make():
            @cfg(condition=True)
            def work(self):
                return 1

            return work

        class Worker:
            work = make()

        return Worker

    return lambda: build()


def cfg_closure_cond_def():
    def build():
        enabled = True  # a cell the condition closes over

        def make():
            @cfg(condition=enabled)
            def work(self):
                return 1

            return work

        class Worker:
            work = make()

        return Worker

    return lambda: build()


def cfg_closure_select_def():
    def build():
        env = PROD

        def make_prod():
            @cfg(condition=env == PROD)
            def work(self):
                return "prod"

            return work

        def make_dev():
            @cfg(condition=env == DEV)
            def work(self):
                return "dev"

            return work

        class Worker:
            work = make_prod()  # selected at class-build time

        return Worker

    return lambda: build()


# --- call-time scenarios: class built once, method called per iteration ---
def call_plain_closure():
    def make():
        def work(self):
            return 1

        return work

    class Worker:
        work = make()

    w = Worker()
    return lambda: w.work()


def call_cfg_closure():
    def make():
        @cfg(condition=True)
        def work(self):
            return 1

        return work

    class Worker:
        work = make()

    w = Worker()
    return lambda: w.work()


def call_runtime_if():
    def make():
        def work(self):
            if True:
                return 1
            return 2

        return work

    class Worker:
        work = make()

    w = Worker()
    return lambda: w.work()


SCENARIOS = {
    # definition-time
    "plain_closure_def": plain_closure_def,
    "cfg_closure_true_def": cfg_closure_true_def,
    "cfg_closure_cond_def": cfg_closure_cond_def,
    "cfg_closure_select_def": cfg_closure_select_def,
    # call-time
    "call_plain_closure": call_plain_closure,
    "call_cfg_closure": call_cfg_closure,
    "call_runtime_if": call_runtime_if,
}


def bench(name: str, fn) -> dict:
    timer = timeit.Timer(fn)
    times = timer.repeat(repeat=REPEAT, number=N)
    best = min(times)
    mean = sum(times) / len(times)
    return {
        "name": name,
        "loops": N,
        "repeat": REPEAT,
        "best_s": best,
        "mean_s": mean,
        "best_us_per_op": best / N * 1e6,
        "mean_us_per_op": mean / N * 1e6,
    }


def main() -> None:
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "version": __version__,
        "machine": platform.machine(),
    }

    results = []
    for name, make in SCENARIOS.items():
        fn = make()
        results.append(bench(name, fn))

    doc = {"environment": env, "results": results}
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"conditional-method {__version__} — @cfg class-body closure pattern "
          f"({N} loops, {REPEAT} repeats)")
    print(f"env: {env['python']} on {env['machine']} ({env['platform'][:40]})")
    print("-" * 72)
    print(f"{'scenario':26} {'best us/op':>12} {'mean us/op':>12}")
    print("-" * 72)
    for r in results:
        print(f"{r['name']:26} {r['best_us_per_op']:12.3f} {r['mean_us_per_op']:12.3f}")
    print("-" * 72)

    # sanity: the pattern behaves correctly
    def make():
        @cfg(condition=True)
        def work(self):
            return "kept"

        return work

    class Worker:
        work = make()

    assert Worker().work() == "kept", Worker().work()

    # a condition=False method inside a class body makes class creation fail
    # (TypeErrorRaiser.__set_name__) - a build-time guard, not a call-time drop
    def make_false():
        @cfg(condition=False)
        def work(self):
            return "dropped"

        return work

    try:

        class Worker2:
            work = make_false()

        raise AssertionError("expected TypeError at class creation for condition=False")
    except TypeError:
        pass

    print("sanity: kept closure method returns 'kept'; condition=False guards class creation")
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
