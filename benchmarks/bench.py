"""Standalone benchmark harness for python-cfg (pure-C implementation).

Reproducible timeit-based measurements of the C extension's conditional
method/decorator machinery vs plain Python baselines. Results are written
to ``benchmarks/results/results.json`` (committed) plus a human-readable
table on stdout.

Run::

    python benchmarks/bench.py
"""

from __future__ import annotations

import json
import platform
import sys
import timeit
from functools import wraps
from pathlib import Path

from cfg import __version__, cfg, cfg_attr

RESULTS_PATH = Path(__file__).parent / "results" / "results.json"

N = 100_000
REPEAT = 5


# --- helpers ---
def add_prefix(prefix):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return f"{prefix}_{func(*args, **kwargs)}"

        return wrapper

    return decorator


def add_suffix(suffix):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return f"{func(*args, **kwargs)}_{suffix}"

        return wrapper

    return decorator


# --- scenarios: each returns a callable to benchmark ---
def plain_call():
    def f():
        return 1

    return lambda: f()


def plain_class():
    def run():
        class Worker:
            def work(self):
                return 1

        Worker().work()

    return run


def cfg_true_decorate():
    def make():
        @cfg(condition=True)
        def f():
            return 1

        return f

    return lambda: make()


def cfg_false_decorate():
    def make():
        @cfg(condition=False)
        def f():
            return 1

        return f

    return lambda: make()


def cfg_callable_decorate():
    def make():
        @cfg(condition=lambda f: f.__name__.startswith("f"))
        def f():
            return 1

        return f

    return lambda: make()


def cfg_class_select():
    def make():
        env = "production"

        class Worker:
            @cfg(condition=env == "production")
            def work(self):
                return "prod"

            @cfg(condition=env == "development")
            def work(self):
                return "dev"

        return Worker

    return lambda: make()


def cfg_attr_true_single():
    def make():
        @cfg_attr(condition=True, decorators=[add_prefix("p")])
        def f():
            return "x"

        return f

    return lambda: make()


def cfg_attr_true_multi():
    def make():
        @cfg_attr(condition=True, decorators=[add_prefix("p"), add_suffix("s")])
        def f():
            return "x"

        return f

    return lambda: make()


def cfg_attr_false():
    def make():
        @cfg_attr(condition=False, decorators=[add_prefix("p")])
        def f():
            return "x"

        return f

    return lambda: make()


def call_plain():
    def f():
        return 1

    return lambda: f()


def call_through_cfg():
    @cfg(condition=True)
    def f():
        return 1

    return lambda: f()


SCENARIOS = {
    "plain_call": plain_call,
    "plain_class": plain_class,
    "cfg_true_decorate": cfg_true_decorate,
    "cfg_false_decorate": cfg_false_decorate,
    "cfg_callable_decorate": cfg_callable_decorate,
    "cfg_class_select": cfg_class_select,
    "cfg_attr_true_single": cfg_attr_true_single,
    "cfg_attr_true_multi": cfg_attr_true_multi,
    "cfg_attr_false": cfg_attr_false,
    "call_plain": call_plain,
    "call_through_cfg": call_through_cfg,
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

    # human-readable table
    print(f"python-cfg {__version__} benchmarks ({N} loops, {REPEAT} repeats)")
    print(f"env: {env['python']} on {env['machine']} ({env['platform'][:50]})")
    print("-" * 64)
    print(f"{'scenario':26} {'best us/op':>12} {'mean us/op':>12}")
    print("-" * 64)
    for r in results:
        print(f"{r['name']:26} {r['best_us_per_op']:12.3f} {r['mean_us_per_op']:12.3f}")
    print("-" * 64)
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
