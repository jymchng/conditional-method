"""pytest-benchmark benchmarks for the pure-C implementation.

The library is a C extension (``cfg._c``); there is no pure-Python
implementation to compare against. These benchmarks therefore measure the C
implementation's cost relative to plain Python baselines (no decoration,
manual if/else, plain decorators).

Run::

    nox -s benchmark          # pytest-benchmark (tests/benchmark.py)
    python benchmarks/bench.py  # standalone timeit harness (results JSON)
"""

import os
from functools import wraps

import pytest

from cfg import cfg, cfg_attr


# --- helper decorators ---
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


# --- baselines ---
@pytest.mark.benchmark(group="plain")
def test_benchmark_plain_call(benchmark):
    def f():
        return 1

    def run():
        f()

    benchmark(run)


@pytest.mark.benchmark(group="plain")
def test_benchmark_plain_class(benchmark):
    def run():
        class Worker:
            def work(self):
                return 1

        Worker().work()

    benchmark(run)


# --- cfg / cm / conditional_method (C) ---
@pytest.mark.benchmark(group="cfg_true")
def test_benchmark_cfg_true_condition(benchmark):
    def make():
        @cfg(condition=True)
        def f():
            return 1

        return f

    benchmark(make)


@pytest.mark.benchmark(group="cfg_false")
def test_benchmark_cfg_false_condition(benchmark):
    def make():
        @cfg(condition=False)
        def f():
            return 1

        return f

    # Creating a false-conditioned function succeeds; calling it raises.
    benchmark(make)


@pytest.mark.benchmark(group="cfg_callable")
def test_benchmark_cfg_callable_condition(benchmark):
    def make():
        @cfg(condition=lambda f: f.__name__.startswith("f"))
        def f():
            return 1

        return f

    benchmark(make)


@pytest.mark.benchmark(group="cfg_class")
def test_benchmark_cfg_class_selection(benchmark):
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

    benchmark(make)


# --- cfg_attr (C) ---
@pytest.mark.benchmark(group="cfg_attr_true")
def test_benchmark_cfg_attr_true_single(benchmark):
    def make():
        @cfg_attr(condition=True, decorators=[add_prefix("p")])
        def f():
            return "x"

        return f

    benchmark(make)


@pytest.mark.benchmark(group="cfg_attr_true_multi")
def test_benchmark_cfg_attr_true_multiple(benchmark):
    def make():
        @cfg_attr(condition=True, decorators=[add_prefix("p"), add_suffix("s")])
        def f():
            return "x"

        return f

    benchmark(make)


@pytest.mark.benchmark(group="cfg_attr_false")
def test_benchmark_cfg_attr_false(benchmark):
    def make():
        @cfg_attr(condition=False, decorators=[add_prefix("p")])
        def f():
            return "x"

        return f

    benchmark(make)


# --- overhead of a call through a selected method vs plain dict access ---
@pytest.mark.benchmark(group="call")
def test_benchmark_call_through_cfg(benchmark):
    @cfg(condition=True)
    def f():
        return 1

    def run():
        f()

    benchmark(run)


@pytest.mark.benchmark(group="call")
def test_benchmark_plain_call_baseline(benchmark):
    def f():
        return 1

    def run():
        f()

    benchmark(run)
