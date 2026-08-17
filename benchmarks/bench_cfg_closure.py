"""Benchmark: ``@cfg`` with closures inside a class (conditional-method).

Measures two axes for methods that close over an enclosing variable (a
class built inside a factory function, methods referencing ``env``):

  Definition time (per-iteration class build + decoration):
    plain_class_def              class with a plain method closing over env
    cfg_class_closure_def        @cfg(condition=env == "prod") selecting one of
                                 two same-named methods (closure bool condition)
    cfg_class_closure_callable_def  @cfg(condition=lambda f: env == "prod")
                                 (callable condition closed over env)
    cfg_class_two_conditions_def two @cfg methods with complementary closure
                                 conditions (prod/dev split)

  Call time (instance method calls; the class is built once):
    call_plain_method            plain method reading the closure cell
    call_cfg_method              @cfg-selected method (cached, reads closure)
    call_runtime_if              baseline: method does the env check at runtime
                                 (the pattern @cfg replaces at class-build time)

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


# --- definition-time scenarios: each returns a callable that REBUILDS the class ---
def plain_class_def():
    def make():
        env = PROD

        class Worker:
            def work(self):
                return env

        return Worker

    return lambda: make()


def cfg_class_closure_def():
    def make():
        env = PROD

        class Worker:
            @cfg(condition=env == PROD)
            def work(self):
                return "prod"

            @cfg(condition=env == DEV)
            def work(self):
                return "dev"

        return Worker

    return lambda: make()


def cfg_class_closure_callable_def():
    def make():
        env = PROD

        class Worker:
            @cfg(condition=lambda f: env == PROD)
            def work(self):
                return "prod"

            @cfg(condition=lambda f: env == DEV)
            def work(self):
                return "dev"

        return Worker

    return lambda: make()


def cfg_class_two_conditions_def():
    def make():
        env = PROD
        # two independent conditions, both closures over env
        is_prod = lambda: env == PROD  # noqa: E731

        class Worker:
            @cfg(condition=is_prod())
            def work(self):
                return "prod"

            @cfg(condition=not is_prod())
            def work(self):
                return "dev"

        return Worker

    return lambda: make()


# --- call-time scenarios: class built ONCE, then method called per iteration ---
def call_plain_method():
    env = PROD

    class Worker:
        def work(self):
            return env

    w = Worker()
    return lambda: w.work()


def call_cfg_method():
    env = PROD

    class Worker:
        @cfg(condition=env == PROD)
        def work(self):
            return "prod"

        @cfg(condition=env == DEV)
        def work(self):
            return "dev"

    w = Worker()
    return lambda: w.work()


def call_runtime_if():
    env = PROD

    class Worker:
        def work(self):
            if env == PROD:
                return "prod"
            return "dev"

    w = Worker()
    return lambda: w.work()


SCENARIOS = {
    # definition-time
    "plain_class_def": plain_class_def,
    "cfg_class_closure_def": cfg_class_closure_def,
    "cfg_class_closure_callable_def": cfg_class_closure_callable_def,
    "cfg_class_two_conditions_def": cfg_class_two_conditions_def,
    # call-time
    "call_plain_method": call_plain_method,
    "call_cfg_method": call_cfg_method,
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

    print(f"conditional-method {__version__} — @cfg with closures in a class "
          f"({N} loops, {REPEAT} repeats)")
    print(f"env: {env['python']} on {env['machine']} ({env['platform'][:40]})")
    print("-" * 72)
    print(f"{'scenario':30} {'best us/op':>12} {'mean us/op':>12}")
    print("-" * 72)
    for r in results:
        print(f"{r['name']:30} {r['best_us_per_op']:12.3f} {r['mean_us_per_op']:12.3f}")
    print("-" * 72)

    # quick sanity: selected methods behave correctly
    from conditional_method import cfg as _cfg  # noqa: F401

    def _sanity():
        env = PROD

        class Worker:
            @cfg(condition=env == PROD)
            def work(self):
                return "prod"

            @cfg(condition=env == DEV)
            def work(self):
                return "dev"

        return Worker().work()

    assert _sanity() == "prod", _sanity()
    print(f"sanity: closure-selected method returns {_sanity()!r}")
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
