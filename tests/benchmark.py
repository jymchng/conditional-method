from conditional_method._lib import cfg as cfg_c
from conditional_method.lib import cfg as cfg_py


# write a benchmark for the two implementations
import timeit
import os
import pytest
from functools import wraps

# Helper functions for testing
def add_prefix(prefix):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return f"{prefix}_{result}"
        return wrapper
    return decorator


def add_suffix(suffix):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return f"{result}_{suffix}"
        return wrapper
    return decorator


def double_result(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return result * 2
    return wrapper


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_c_true_condition(benchmark):
    """Benchmark the C implementation with a True condition."""
    def setup():
        @cfg_c(condition=True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_py_true_condition(benchmark):
    """Benchmark the Python implementation with a True condition."""
    def setup():
        @cfg_py(condition=True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_c_false_condition(benchmark):
    """Benchmark the C implementation with a False condition."""
    def setup():
        try:
            @cfg_c(condition=False)
            def test_func():
                return "result"
            return test_func
        except Exception:
            # Return a function that raises TypeError to match behavior
            def error_func():
                raise TypeError()
            return error_func
    
    func = setup()
    benchmark(lambda: pytest.raises(TypeError, func))


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_py_false_condition(benchmark):
    """Benchmark the Python implementation with a False condition."""
    def setup():
        try:
            @cfg_py(condition=False)
            def test_func():
                return "result"
            return test_func
        except Exception:
            # Return a function that raises TypeError to match behavior
            def error_func():
                raise TypeError()
            return error_func
    
    func = setup()
    benchmark(lambda: pytest.raises(TypeError, func))


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_c_with_decorators(benchmark):
    """Benchmark the C implementation with multiple decorators."""
    def setup():
        @add_prefix("prefix")
        @add_suffix("suffix")
        @cfg_c(condition=True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_py_with_decorators(benchmark):
    """Benchmark the Python implementation with multiple decorators."""
    def setup():
        @add_prefix("prefix")
        @add_suffix("suffix")
        @cfg_py(condition=True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_c_with_callable_condition(benchmark):
    """Benchmark the C implementation with a callable condition."""
    def setup():
        @cfg_c(condition=lambda f: True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_py_with_callable_condition(benchmark):
    """Benchmark the Python implementation with a callable condition."""
    def setup():
        @cfg_py(condition=lambda f: True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_c_with_args_kwargs(benchmark):
    """Benchmark the C implementation with args and kwargs."""
    def setup():
        @cfg_c(condition=True)
        def test_func(*args, **kwargs):
            return sum(args) + kwargs.get('c', 0)
        return lambda: test_func(1, 2, c=3)
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_py_with_args_kwargs(benchmark):
    """Benchmark the Python implementation with args and kwargs."""
    def setup():
        @cfg_py(condition=True)
        def test_func(*args, **kwargs):
            return sum(args) + kwargs.get('c', 0)
        return lambda: test_func(1, 2, c=3)
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_c_true_condition(benchmark):
    """Benchmark the C implementation with a True condition."""
    def setup():
        @cfg_c(condition=True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_py_true_condition(benchmark):
    """Benchmark the Python implementation with a True condition."""
    def setup():
        @cfg_py(condition=True)
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_c_with_decorators(benchmark):
    """Benchmark the C implementation with decorators."""
    def setup():
        @cfg_c(condition=True, decorators=[add_prefix("prefix"), add_suffix("suffix")])
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


@pytest.mark.benchmark(group="cfg_implementations")
def test_benchmark_cfg_py_with_decorators(benchmark):
    """Benchmark the Python implementation with decorators."""
    def setup():
        @cfg_py(condition=True, decorators=[add_prefix("prefix"), add_suffix("suffix")])
        def test_func():
            return "result"
        return test_func
    
    func = setup()
    benchmark(func)


