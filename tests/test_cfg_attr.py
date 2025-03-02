import os
import pytest
from functools import wraps, lru_cache
from conditional_method.lib import cfg_attr


# Fix for generator function test
def add_prefix_to_yielded(prefix):
    """Add prefix to each yielded value, not to the generator object itself"""

    def decorator(f):
        def wrapper(*args, **kwargs):
            gen = f(*args, **kwargs)
            for value in gen:
                yield f"{prefix}_{value}"

        return wrapper

    return decorator


# Fix for async function test
def add_prefix_async(prefix):
    """Add prefix while preserving async function behavior"""

    def decorator(f):
        async def wrapper(*args, **kwargs):
            result = await f(*args, **kwargs)
            return f"{prefix}_{result}"

        return wrapper

    return decorator


def add_prefix_to_final_result(prefix):
    """
    A decorator that adds a prefix only to the final result of a recursive function,
    using a function attribute to track recursion state.
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we're already inside a recursive call of this function
            is_recursive = getattr(wrapper, "_in_recursion", False)

            try:
                # Set recursion flag before calling
                wrapper._in_recursion = True

                # Call the original function
                result = func(*args, **kwargs)

                # Only add prefix if this is the outermost call
                if not is_recursive:
                    return f"{prefix}_{result}"
                return result
            finally:
                # Reset the flag when we're at the original call level
                if not is_recursive:
                    wrapper._in_recursion = False

        # Initialize the recursion tracking attribute
        wrapper._in_recursion = False
        return wrapper

    return decorator


# Helper decorators for testing
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


def uppercase_result(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return str(result).upper()

    return wrapper


class TestCfgAttr:
    def test_basic_true_condition(self):
        @cfg_attr(condition=True)
        def test_func():
            return "result"

        assert test_func() == "result"

    def test_basic_false_condition(self):
        @cfg_attr(condition=False)
        def test_func():
            return "result"

        assert test_func() == "result"  # Function should be unchanged

    def test_single_decorator_true_condition(self):
        @cfg_attr(condition=True, decorators=[add_prefix("test")])
        def test_func():
            return "result"

        assert test_func() == "test_result"

    def test_single_decorator_false_condition(self):
        @cfg_attr(condition=False, decorators=[add_prefix("test")])
        def test_func():
            return "result"

        assert test_func() == "result"  # Decorator should not be applied

    def test_multiple_decorators_true_condition(self):
        @cfg_attr(condition=True, decorators=[add_prefix("pre"), add_suffix("post")])
        def test_func():
            return "result"

        assert test_func() == "pre_result_post"

    def test_multiple_decorators_order(self):
        @cfg_attr(condition=True, decorators=[add_suffix("post"), add_prefix("pre")])
        def test_func():
            return "result"

        # Decorators should be applied in the order they are listed
        assert test_func() == "pre_result_post"

    def test_decorator_factory_true_condition(self):
        decorator = cfg_attr(condition=True, decorators=[add_prefix("test")])

        @decorator
        def test_func():
            return "result"

        assert test_func() == "test_result"

    def test_decorator_factory_false_condition(self):
        decorator = cfg_attr(condition=False, decorators=[add_prefix("test")])

        @decorator
        def test_func():
            return "result"

        assert test_func() == "result"

    def test_with_environment_variable(self, monkeypatch):
        monkeypatch.setenv("TEST_FLAG", "enabled")

        @cfg_attr(
            condition=os.environ.get("TEST_FLAG") == "enabled",
            decorators=[add_prefix("env")],
        )
        def test_func():
            return "result"

        assert test_func() == "env_result"

    def test_with_environment_variable_false(self, monkeypatch):
        monkeypatch.setenv("TEST_FLAG", "disabled")

        @cfg_attr(
            condition=os.environ.get("TEST_FLAG") == "enabled",
            decorators=[add_prefix("env")],
        )
        def test_func():
            return "result"

        assert test_func() == "result"

    def test_with_function_arguments(self):
        @cfg_attr(condition=True, decorators=[add_prefix("args")])
        def test_func(a, b):
            return f"{a}_{b}"

        assert test_func(1, 2) == "args_1_2"

    def test_with_kwargs(self):
        @cfg_attr(condition=True, decorators=[add_prefix("kwargs")])
        def test_func(a, b=2):
            return f"{a}_{b}"

        assert test_func(1, b=3) == "kwargs_1_3"

    def test_raises_value_error_when_condition_is_none(self):
        with pytest.raises(ValueError):

            @cfg_attr(decorators=[add_prefix("test")])
            def test_func():
                return "result"

    def test_preserves_function_metadata(self):
        def original_func():
            """Test docstring"""
            return "result"

        decorated = cfg_attr(
            original_func, condition=True, decorators=[add_prefix("meta")]
        )

        assert decorated.__name__ == "original_func"
        assert decorated.__doc__ == "Test docstring"
        assert decorated() == "meta_result"

    def test_with_class_method(self):
        class TestClass:
            @cfg_attr(condition=True, decorators=[add_prefix("method")])
            def test_method(self):
                return "result"

        instance = TestClass()
        assert instance.test_method() == "method_result"

    def test_with_static_method(self):
        class TestClass:
            @staticmethod
            @cfg_attr(condition=True, decorators=[add_prefix("static")])
            def test_method():
                return "result"

        assert TestClass.test_method() == "static_result"

    def test_with_class_method_false_condition(self):
        class TestClass:
            @cfg_attr(condition=False, decorators=[add_prefix("method")])
            def test_method(self):
                return "result"

        instance = TestClass()
        assert instance.test_method() == "result"

    def test_with_lambda_function(self):
        func = lambda x: x * 2
        decorated = cfg_attr(func, condition=True, decorators=[add_prefix("lambda")])

        assert decorated(5) == "lambda_10"

    def test_with_numeric_result(self):
        @cfg_attr(condition=True, decorators=[double_result])
        def test_func():
            return 5

        assert test_func() == 10

    def test_with_list_result(self):
        @cfg_attr(condition=True, decorators=[double_result])
        def test_func():
            return [1, 2, 3]

        assert test_func() == [1, 2, 3, 1, 2, 3]

    def test_with_string_transformation(self):
        @cfg_attr(condition=True, decorators=[uppercase_result])
        def test_func():
            return "hello"

        assert test_func() == "HELLO"

    def test_with_multiple_transformations(self):
        @cfg_attr(condition=True, decorators=[double_result, uppercase_result])
        def test_func():
            return "hello"

        assert test_func() == "HELLOHELLO"

    def test_with_reverse_transformations(self):
        @cfg_attr(condition=True, decorators=[uppercase_result, double_result])
        def test_func():
            return "hello"

        assert test_func() == "HELLOHELLO"

    def test_with_conditional_expression(self):
        x = 10

        @cfg_attr(condition=x > 5, decorators=[add_prefix("greater")])
        def test_func():
            return "result"

        assert test_func() == "greater_result"

    def test_with_false_conditional_expression(self):
        x = 3

        @cfg_attr(condition=x > 5, decorators=[add_prefix("greater")])
        def test_func():
            return "result"

        assert test_func() == "result"

    def test_with_dynamic_condition(self):
        def dynamic_condition():
            return True

        @cfg_attr(condition=dynamic_condition(), decorators=[add_prefix("dynamic")])
        def test_func():
            return "result"

        assert test_func() == "dynamic_result"

    def test_with_standard_library_decorator(self):
        @cfg_attr(condition=True, decorators=[lru_cache(maxsize=None)])
        def fibonacci(n):
            if n < 2:
                return n
            return fibonacci(n - 1) + fibonacci(n - 2)

        # First call calculates everything
        result1 = fibonacci(10)
        # Second call should use cached values
        result2 = fibonacci(10)

        assert result1 == 55
        assert result2 == 55
        assert fibonacci.cache_info().hits > 0

    def test_with_nested_cfg_attr(self):
        @cfg_attr(
            condition=True,
            decorators=[cfg_attr(condition=True, decorators=[add_prefix("inner")])],
        )
        def test_func():
            return "result"

        assert test_func() == "inner_result"

    def test_with_nested_cfg_attr_mixed_conditions(self):
        @cfg_attr(
            condition=True,
            decorators=[cfg_attr(condition=False, decorators=[add_prefix("inner")])],
        )
        def test_func():
            return "result"

        assert test_func() == "result"

    def test_with_empty_decorators_list(self):
        @cfg_attr(condition=True, decorators=[])
        def test_func():
            return "result"

        assert test_func() == "result"

    def test_with_multiple_arguments(self):
        @cfg_attr(condition=True, decorators=[add_prefix("multi")])
        def test_func(a, b, c):
            return f"{a}_{b}_{c}"

        assert test_func(1, 2, 3) == "multi_1_2_3"

    def test_with_args_and_kwargs(self):
        @cfg_attr(condition=True, decorators=[add_prefix("mixed")])
        def test_func(*args, **kwargs):
            args_str = "_".join(str(arg) for arg in args)
            kwargs_str = "_".join(f"{k}:{v}" for k, v in kwargs.items())
            return f"{args_str}_{kwargs_str}"

        assert test_func(1, 2, a=3, b=4) == "mixed_1_2_a:3_b:4"

    def test_with_default_arguments(self):
        @cfg_attr(condition=True, decorators=[add_prefix("default")])
        def test_func(a, b=2, c="c"):
            return f"{a}_{b}_{c}"

        assert test_func(1) == "default_1_2_c"
        assert test_func(1, 5) == "default_1_5_c"
        assert test_func(1, c="d") == "default_1_2_d"

    def test_with_recursive_function(self):
        @cfg_attr(condition=True, decorators=[add_prefix_to_final_result("recursive")])
        def factorial(n):
            if n <= 1:
                return 1
            return n * factorial(n - 1)

        # This will only prefix the final result
        assert factorial(5) == "recursive_120"

    def test_with_generator_function(self):
        @cfg_attr(condition=True, decorators=[add_prefix_to_yielded("gen")])
        def generate_numbers(n):
            for i in range(n):
                yield i

        # The decorator should apply to each yielded value
        result = list(generate_numbers(3))
        assert result == ["gen_0", "gen_1", "gen_2"]

    def test_with_async_function(self):
        import asyncio

        @cfg_attr(condition=True, decorators=[add_prefix_async("async")])
        async def async_func():
            await asyncio.sleep(0.01)
            return "result"

        result = asyncio.run(async_func())
        assert result == "async_result"

    def test_with_exception_raising_function(self):
        @cfg_attr(condition=True, decorators=[add_prefix("exception")])
        def raises_error():
            raise ValueError("Test error")
            return "result"

        with pytest.raises(ValueError):
            raises_error()

    def test_with_conditional_import(self):
        # Only apply decorator if pytest is available
        has_pytest = True
        try:
            import pytest
        except ImportError:
            has_pytest = False

        @cfg_attr(condition=has_pytest, decorators=[add_prefix("pytest")])
        def test_func():
            return "result"

        assert test_func() == "pytest_result"

    def test_with_multiple_conditions_and(self):
        condition1 = True
        condition2 = True

        @cfg_attr(condition=condition1 and condition2, decorators=[add_prefix("and")])
        def test_func():
            return "result"

        assert test_func() == "and_result"

    def test_with_multiple_conditions_or(self):
        condition1 = False
        condition2 = True

        @cfg_attr(condition=condition1 or condition2, decorators=[add_prefix("or")])
        def test_func():
            return "result"

        assert test_func() == "or_result"

    def test_with_complex_condition(self):
        a, b, c = 1, 2, 3

        @cfg_attr(
            condition=(a < b < c) and (a + b == c), decorators=[add_prefix("complex")]
        )
        def test_func():
            return "result"

        assert test_func() == "complex_result"
