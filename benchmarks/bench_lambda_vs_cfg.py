"""Benchmark: the class-body `@lambda f: f()` trick vs `@cfg`.

Two ways to select a method implementation at class-build time based on an
enclosing environment variable (ENV == "PROD"/"DEV"):

1) The decorator-call trick (the pattern under comparison):

       class Worker:
           @lambda f: f()          # decorator immediately calls the factory
           def work():             #   -> returns the selected inner method
               if ENV == "PROD":
                   def work(self, item): ...
                   return work
               if ENV == "DEV":
                   def work(self, item): ...
                   return work

2) `@cfg` conditional-method selection:

       class Worker:
           @cfg(condition=ENV == "PROD")
           def work(self, item): ...
           @cfg(condition=ENV == "DEV")
           def work(self, item): ...

Measured axes (the factory bodies use `return` instead of `print` so the
timing measures selection/closure machinery, not I/O):

  Definition time (the class is rebuilt every iteration):
    lambda_trick_def        @lambda f: f() factory with ENV if/else
    cfg_two_method_def      two same-named @cfg methods (PROD/DEV)
    plain_method_def        plain single method baseline

  Call time (class built once; method called per iteration):
    call_lambda_trick       Worker().work(5) - closure selected by the trick
    call_cfg_two_method     Worker().work(5) - method kept by @cfg
    call_plain              Worker().work(5) - plain method baseline

Results are written to benchmarks/results/results_lambda_vs_cfg.json plus a
table on stdout.

Run:  python benchmarks/bench_lambda_vs_cfg.py
"""

from __future__ import annotations

import json
import platform
import timeit
from pathlib import Path

from conditional_method import __version__, cfg

RESULTS_PATH = Path(__file__).parent / "results" / "results_lambda_vs_cfg.json"

N = 100_000
REPEAT = 5

ENV = "PROD"
ITEM = 5


def _prod(self, item: int) -> str:
    return f"PROD item={item}"


def _dev(self, item: int) -> str:
    return f"DEV item={item}"


# --- definition-time scenarios: rebuild the class every iteration ---
def lambda_trick_def():
    def build():
        class Worker:
            @lambda f: f()
            def work():
                if ENV == "PROD":
                    return _prod
                if ENV == "DEV":
                    return _dev
                raise AssertionError

        return Worker

    return lambda: build()


def cfg_two_method_def():
    def build():
        class Worker:
            @cfg(condition=ENV == "PROD")
            def work(self, item: int):
                return _prod(self, item)

            @cfg(condition=ENV == "DEV")
            def work(self, item: int):
                return _dev(self, item)

        return Worker

    return lambda: build()


def plain_method_def():
    def build():
        class Worker:
            def work(self, item: int):
                return _prod(self, item)

        return Worker

    return lambda: build()


# --- call-time scenarios: class built once, method called per iteration.
# Trivial body (`return item`) so timing measures pure method dispatch, not
# the (identical) f-string formatting used in the definition-time scenarios. ---
def call_lambda_trick():
    class Worker:
        @lambda f: f()
        def work():
            if ENV == "PROD":
                def work(self, item: int):
                    return item

                return work
            if ENV == "DEV":
                def work(self, item: int):
                    return item

                return work
            raise AssertionError

    w = Worker()
    return lambda: w.work(ITEM)


def call_cfg_two_method():
    class Worker:
        @cfg(condition=ENV == "PROD")
        def work(self, item: int):
            return item

        @cfg(condition=ENV == "DEV")
        def work(self, item: int):
            return item

    w = Worker()
    return lambda: w.work(ITEM)


def call_plain():
    class Worker:
        def work(self, item: int):
            return item

    w = Worker()
    return lambda: w.work(ITEM)


SCENARIOS = {
    "lambda_trick_def": lambda_trick_def,
    "cfg_two_method_def": cfg_two_method_def,
    "plain_method_def": plain_method_def,
    "call_lambda_trick": call_lambda_trick,
    "call_cfg_two_method": call_cfg_two_method,
    "call_plain": call_plain,
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

    print(f"conditional-method {__version__} — @lambda f: f() trick vs @cfg "
          f"({N} loops, {REPEAT} repeats)")
    print(f"env: {env['python']} on {env['machine']} ({env['platform'][:40]})")
    print("-" * 72)
    print(f"{'scenario':26} {'best us/op':>12} {'mean us/op':>12}")
    print("-" * 72)
    for r in results:
        print(f"{r['name']:26} {r['best_us_per_op']:12.3f} {r['mean_us_per_op']:12.3f}")
    print("-" * 72)

    # sanity: all three produce the same selected method behaviour
    def _make_lambda():
        class Worker:
            @lambda f: f()
            def work():
                if ENV == "PROD":
                    return _prod
                if ENV == "DEV":
                    return _dev
                raise AssertionError

        return Worker().work

    def _make_cfg():
        class Worker:
            @cfg(condition=ENV == "PROD")
            def work(self, item: int):
                return _prod(self, item)

            @cfg(condition=ENV == "DEV")
            def work(self, item: int):
                return _dev(self, item)

        return Worker().work

    assert _make_lambda()(ITEM) == "PROD item=5"
    assert _make_cfg()(ITEM) == "PROD item=5"
    print("sanity: lambda-trick and @cfg both select the PROD method")
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
