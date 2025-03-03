import os
import sys
import pytest
from functools import wraps, lru_cache

# Import the cfg function
from conditional_method.lib import cfg, conditional_method, if_


def add_prefix_to_yielded(prefix):
    """Add prefix to each yielded value, not to the generator object itself"""

    def decorator(f):
        def wrapper(*args, **kwargs):
            gen = f(*args, **kwargs)
            for value in gen:
                yield f"{prefix}_{value}"

        return wrapper

    return decorator


def add_prefix_async(prefix):
    """Add prefix while preserving async function behavior"""

    def decorator(f):
        async def wrapper(*args, **kwargs):
            result = await f(*args, **kwargs)
            return f"{prefix}_{result}"

        return wrapper

    return decorator


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


# Environment variable for testing
ENV_KEY = "CONDITIONAL_METHOD_TEST"


@pytest.fixture
def debug_env_var_value():
    """Set environment variable for testing and restore after test"""
    original_value = os.environ.get(ENV_KEY)
    os.environ[ENV_KEY] = "True"
    yield
    if original_value is None:
        del os.environ[ENV_KEY]
    else:
        os.environ[ENV_KEY] = original_value


def test_cfg_with_true_condition():
    @cfg(condition=True)
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_false_condition():
    @cfg(condition=False)
    def test_func():
        return "result"

    with pytest.raises(TypeError):
        test_func()


def test_cfg_with_callable_condition_true():
    @cfg(condition=lambda f: True)
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_callable_condition_false():
    @cfg(condition=lambda f: False)
    def test_func():
        return "result"

    with pytest.raises(TypeError):
        test_func()


def test_cfg_with_dynamic_condition():
    condition_value = True

    @cfg(condition=lambda f: condition_value)
    def test_func():
        return "result"

    assert test_func() == "result"

    condition_value = False

    @cfg(condition=lambda f: condition_value)
    def test_func2():
        return "result"

    with pytest.raises(TypeError):
        test_func2()


def test_cfg_with_function_arguments():
    @cfg(condition=True)
    def test_func(a, b):
        return a + b

    assert test_func(1, 2) == 3


def test_cfg_with_default_arguments():
    @cfg(condition=True)
    def test_func(a, b=2):
        return a + b

    assert test_func(1) == 3
    assert test_func(1, 3) == 4


def test_cfg_with_kwargs():
    @cfg(condition=True)
    def test_func(a, b, **kwargs):
        return a + b + kwargs.get("c", 0)

    assert test_func(1, 2, c=3) == 6


def test_cfg_with_args():
    @cfg(condition=True)
    def test_func(*args):
        return sum(args)

    assert test_func(1, 2, 3) == 6


def test_cfg_with_args_and_kwargs():
    @cfg(condition=True)
    def test_func(*args, **kwargs):
        return sum(args) + kwargs.get("c", 0)

    assert test_func(1, 2, c=3) == 6


def test_cfg_with_none_condition():
    with pytest.raises(TypeError):

        @cfg(condition=None)
        def test_func():
            return "result"


def test_cfg_with_env_var_condition(debug_env_var_value):
    @cfg(condition=lambda f: os.environ.get(ENV_KEY) == "True")
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_multiple_decorations_same_name():
    @cfg(condition=False)
    def test_func():
        return "first"

    @cfg(condition=True)
    def test_func():
        return "second"

    assert test_func() == "second"


def test_cfg_with_multiple_decorations_different_conditions():
    condition1 = False
    condition2 = True

    @cfg(condition=condition1)
    def test_func():
        return "first"

    @cfg(condition=condition2)
    def test_func():
        return "second"

    assert test_func() == "second"


def test_cfg_with_class_method():
    class TestClass:
        @cfg(condition=True)
        def test_method(self):
            return "result"

    assert TestClass().test_method() == "result"


def test_cfg_with_class_method_false_condition():
    with pytest.raises(RuntimeError):

        class TestClass:
            @cfg(condition=False)
            def test_method(self):
                return "result"

        TestClass().test_method()


def test_cfg_with_static_method():
    class TestClass:
        @staticmethod
        @cfg(condition=True)
        def test_method():
            return "result"

    assert TestClass.test_method() == "result"


def test_cfg_with_class_method_decorator():
    class TestClass:
        @classmethod
        @cfg(condition=True)
        def test_method(cls):
            return "result"

    assert TestClass.test_method() == "result"


def test_cfg_with_property():
    class TestClass:
        @property
        @cfg(condition=True)
        def test_prop(self):
            return "result"

    assert TestClass().test_prop == "result"


def test_cfg_with_recursive_function():
    @cfg(condition=True)
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    assert factorial(5) == 120


def test_cfg_aliases():
    # Test that all aliases work the same
    @cfg(condition=True)
    def func1():
        return "cfg"

    @conditional_method(condition=True)
    def func2():
        return "conditional_method"

    @if_(condition=True)
    def func3():
        return "if_"

    assert func1() == "cfg"
    assert func2() == "conditional_method"
    assert func3() == "if_"


def test_cfg_with_lambda():
    @cfg(condition=True)
    def test_func():
        return lambda x: x * 2

    assert test_func()(3) == 6


def test_cfg_with_nested_functions():
    @cfg(condition=True)
    def outer():
        def inner():
            return "inner"

        return inner

    assert outer()() == "inner"


def test_cfg_with_closure():
    def create_func():
        x = 10

        @cfg(condition=True)
        def inner():
            return x

        return inner

    assert create_func()() == 10


def test_cfg_with_multiple_functions_same_name_different_modules():
    # This test simulates functions with the same name in different modules
    module1 = type("module1", (), {})()
    module2 = type("module2", (), {})()

    @cfg(condition=True)
    def module1_func():
        return "module1"

    module1.func = module1_func
    module1.func.__module__ = "module1"

    @cfg(condition=True)
    def module2_func():
        return "module2"

    module2.func = module2_func
    module2.func.__module__ = "module2"

    assert module1.func() == "module1"
    assert module2.func() == "module2"


def test_cfg_with_exception_in_function():
    @cfg(condition=True)
    def raises_error():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        raises_error()


def test_cfg_with_exception_in_condition():
    def condition_with_error(f):
        raise ValueError("Error in condition")

    with pytest.raises(ValueError):

        @cfg(condition=condition_with_error)
        def test_func():
            return "result"


def test_cfg_with_generator_function():
    @cfg(condition=True)
    def generate_numbers(n):
        for i in range(n):
            yield i

    assert list(generate_numbers(3)) == [0, 1, 2]


def test_cfg_with_async_function():
    import asyncio

    @cfg(condition=True)
    async def async_func():
        await asyncio.sleep(0.01)
        return "result"

    result = asyncio.run(async_func())
    assert result == "result"


def test_cfg_with_inheritance():
    class BaseClass:
        @cfg(condition=True)
        def method(self):
            return "base"

    class DerivedClass(BaseClass):
        pass

    assert DerivedClass().method() == "base"


def test_cfg_with_method_override():
    class BaseClass:
        @cfg(condition=True)
        def method(self):
            return "base"

    class DerivedClass(BaseClass):
        @cfg(condition=True)
        def method(self):
            return "derived"

    assert DerivedClass().method() == "derived"


def test_cfg_with_conditional_inheritance():
    class BaseClass:
        @cfg(condition=False)
        def method(self):
            return "base_false"

        @cfg(condition=True)
        def method(self):
            return "base_true"

    with pytest.raises(RuntimeError):

        class DerivedClass(BaseClass):
            @cfg(condition=False)
            def method(self):
                return "derived_false"


def test_cfg_with_multiple_conditions_and():
    condition1 = True
    condition2 = True

    @cfg(condition=lambda f: condition1 and condition2)
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_multiple_conditions_or():
    condition1 = False
    condition2 = True

    @cfg(condition=lambda f: condition1 or condition2)
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_complex_condition():
    a, b, c = 1, 2, 3

    @cfg(condition=lambda f: (a < b < c) and (a + b == c))
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_conditional_import():
    # Only apply decorator if pytest is available
    has_pytest = True
    try:
        import importlib

        importlib.util.find_spec("pytest")
    except ImportError:
        has_pytest = False

    @cfg(condition=has_pytest)
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_cache_behavior():
    # Test that the cache is working correctly
    calls = 0

    def condition_func(f):
        nonlocal calls
        calls += 1
        return True

    @cfg(condition=condition_func)
    def func1():
        return "func1"

    @cfg(condition=condition_func)
    def func2():
        return "func2"

    assert func1() == "func1"
    assert func2() == "func2"
    assert calls == 2  # Each function should evaluate its condition once


def test_cfg_with_docstring():
    @cfg(condition=True)
    def test_func():
        """This is a test function"""
        return "result"

    assert test_func.__doc__ == "This is a test function"


def test_cfg_with_annotations():
    @cfg(condition=True)
    def test_func(a: int, b: str) -> str:
        return b * a

    assert test_func(3, "a") == "aaa"
    assert test_func.__annotations__ == {"a": int, "b": str, "return": str}


def test_cfg_with_module_level_function():
    # Test at module level
    assert sys.modules[__name__].__name__ == "tests.test_cfg"

    @cfg(condition=True)
    def module_func():
        return __name__

    assert module_func() == "tests.test_cfg"


def test_cfg_with_nested_decorators():
    def outer_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return "outer_" + func(*args, **kwargs)

        return wrapper

    @outer_decorator
    @cfg(condition=True)
    def test_func():
        return "result"

    assert test_func() == "outer_result"


def test_cfg_with_decorator_and_false_condition():
    @add_prefix("prefix")
    @cfg(condition=False)
    def test_func():
        return "result"

    with pytest.raises(TypeError):
        test_func()


def test_cfg_with_multiple_decorators():
    @add_prefix("prefix")
    @add_suffix("suffix")
    @cfg(condition=True)
    def test_func():
        return "result"

    assert test_func() == "prefix_result_suffix"


def test_cfg_with_lru_cache():
    calls = 0

    @lru_cache(maxsize=None)
    @cfg(condition=True)
    def cached_func(n):
        nonlocal calls
        calls += 1
        return n * 2

    assert cached_func(5) == 10
    assert cached_func(5) == 10
    assert calls == 1  # Should only be called once due to caching


def test_cfg_with_generator_and_decorator():
    @add_prefix_to_yielded("prefix")
    @cfg(condition=True)
    def generate_values():
        for i in range(3):
            yield i

    results = list(generate_values())
    assert results == ["prefix_0", "prefix_1", "prefix_2"]


def test_cfg_with_async_generator():
    import asyncio

    @cfg(condition=True)
    async def async_gen():
        for i in range(3):
            await asyncio.sleep(0.01)
            yield i

    async def run_test():
        results = []
        async for val in async_gen():
            results.append(val)
        return results

    results = asyncio.run(run_test())
    assert results == [0, 1, 2]


def test_cfg_with_async_and_decorator():
    import asyncio

    @add_prefix_async("prefix")
    @cfg(condition=True)
    async def async_func():
        await asyncio.sleep(0.01)
        return "result"

    result = asyncio.run(async_func())
    assert result == "prefix_result"


def test_cfg_with_multiple_async_decorators():
    import asyncio

    @add_prefix_async("prefix")
    @cfg(condition=True)
    @add_prefix_async("suffix")
    async def async_func():
        await asyncio.sleep(0.01)
        return "result"

    result = asyncio.run(async_func())
    assert result == "prefix_suffix_result"


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


def test_cfg_with_recursive_decorator():
    @add_prefix_to_final_result("prefix")
    @cfg(condition=True)
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    assert factorial(5) == "prefix_120"


def test_cfg_with_recursive_function_and_false_condition():
    @cfg(condition=False)
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    with pytest.raises(TypeError):
        factorial(5)


def test_cfg_with_conditional_decorator():
    use_decorator = True

    if use_decorator:
        decorator = add_prefix("prefix")
    else:

        def decorator(f):
            return f

    @decorator
    @cfg(condition=True)
    def test_func():
        return "result"

    assert test_func() == "prefix_result"


def test_cfg_with_dynamic_decorator_selection():
    decorators = [add_prefix("prefix"), add_suffix("suffix"), double_result]
    selected = decorators[0]

    @selected
    @cfg(condition=True)
    def test_func():
        return "result"

    assert test_func() == "prefix_result"


def test_cfg_with_multiple_conditions_combined():
    condition1 = True
    condition2 = False
    condition3 = True

    @cfg(condition=lambda f: (condition1 or condition2) and condition3)
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_function_name_in_condition():
    @cfg(condition=lambda f: f.__name__ == "test_func")
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_function_signature_in_condition():
    import inspect

    @cfg(condition=lambda f: len(inspect.signature(f).parameters) == 2)
    def test_func(a, b):
        return a + b

    assert test_func(1, 2) == 3


def test_cfg_with_nested_cfg_decorators():
    @cfg(condition=True)
    @cfg(condition=True)
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_nested_cfg_decorators_one_false():
    @cfg(condition=True)
    @cfg(condition=False)
    def test_func():
        return "result"

    with pytest.raises(TypeError):
        test_func()


def test_cfg_with_class_inheritance_chain():
    class GrandParent:
        @cfg(condition=True)
        def method(self):
            return "grandparent"

    class Parent(GrandParent):
        pass

    class Child(Parent):
        pass

    assert Child().method() == "grandparent"


def test_cfg_with_method_override_in_inheritance_chain():
    class GrandParent:
        @cfg(condition=True)
        def method(self):
            return "grandparent"

    class Parent(GrandParent):
        @cfg(condition=True)
        def method(self):
            return "parent"

    class Child(Parent):
        pass

    assert Child().method() == "parent"


def test_cfg_with_super_call():
    class Parent:
        @cfg(condition=True)
        def method(self):
            return "parent"

    class Child(Parent):
        @cfg(condition=True)
        def method(self):
            return f"child_{super().method()}"

    assert Child().method() == "child_parent"


def test_cfg_with_abstract_method():
    from abc import ABC, abstractmethod

    class AbstractBase(ABC):
        @abstractmethod
        @cfg(condition=True)
        def method(self):
            pass

    class Concrete(AbstractBase):
        @cfg(condition=True)
        def method(self):
            return "implemented"

    assert Concrete().method() == "implemented"


def test_cfg_with_property_setter():
    class TestClass:
        def __init__(self):
            self._value = None

        @property
        @cfg(condition=True)
        def value(self):
            return self._value

        @value.setter
        @cfg(condition=True)
        def value(self, val):
            self._value = f"set_{val}"

    obj = TestClass()
    obj.value = "test"
    assert obj.value == "set_test"


def test_cfg_with_property_deleter():
    class TestClass:
        def __init__(self):
            self._value = "initial"

        @property
        @cfg(condition=True)
        def value(self):
            return self._value

        @value.deleter
        @cfg(condition=True)
        def value(self):
            self._value = "deleted"

    obj = TestClass()
    del obj.value
    assert obj.value == "deleted"


def test_cfg_with_descriptor():
    class Descriptor:
        def __init__(self, name):
            self.name = name

        @cfg(condition=True)
        def __get__(self, instance, owner):
            return f"get_{self.name}"

        @cfg(condition=True)
        def __set__(self, instance, value):
            self.name = f"set_{value}"

    class TestClass:
        desc = Descriptor("initial")

    obj = TestClass()
    assert obj.desc == "get_initial"
    obj.desc = "new"
    assert obj.desc == "get_set_new"


def test_cfg_with_context_manager():
    class TestContextManager:
        @cfg(condition=True)
        def __enter__(self):
            return "entered"

        @cfg(condition=True)
        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    with TestContextManager() as result:
        assert result == "entered"


def test_cfg_with_metaclass():
    class TestMeta(type):
        @cfg(condition=True)
        def __new__(mcs, name, bases, attrs):
            attrs["extra"] = "meta_added"
            return super().__new__(mcs, name, bases, attrs)

    class TestClass(metaclass=TestMeta):
        pass

    assert TestClass.extra == "meta_added"


def test_cfg_with_dataclass():
    from dataclasses import dataclass

    @dataclass
    class TestDataClass:
        value: str

        @cfg(condition=True)
        def get_value(self):
            return f"got_{self.value}"

    obj = TestDataClass("test")
    assert obj.get_value() == "got_test"


def test_cfg_with_namedtuple():
    from collections import namedtuple

    TestTuple = namedtuple("TestTuple", ["value"])

    @cfg(condition=True)
    def process_tuple(tup):
        return f"processed_{tup.value}"

    tup = TestTuple("test")
    assert process_tuple(tup) == "processed_test"


def test_cfg_with_enum():
    from enum import Enum, auto

    class TestEnum(Enum):
        A = auto()
        B = auto()

    @cfg(condition=True)
    def process_enum(enum_val):
        return f"enum_{enum_val.name}"

    assert process_enum(TestEnum.A) == "enum_A"


def test_cfg_with_partial_function():
    from functools import partial

    @cfg(condition=True)
    def base_func(a, b, c):
        return a + b + c

    partial_func = partial(base_func, 1, 2)
    assert partial_func(3) == 6


def test_cfg_with_wrapped_partial_function():
    from functools import partial

    def base_func(a, b, c):
        return a + b + c

    @cfg(condition=True)
    def wrapped_partial():
        return partial(base_func, 1, 2)

    assert wrapped_partial()(3) == 6


def test_cfg_with_class_decorator():
    def class_decorator(f):
        def wrapper(*args, **kwargs):
            cls = f(*args, **kwargs)
            cls.extra_attr = "added"
            return cls

        return wrapper

    @class_decorator
    @cfg(condition=True)
    def create_class():
        class DynamicClass: ...

        return DynamicClass

    cls = create_class()
    assert cls.extra_attr == "added"


def test_cfg_with_function_returning_class():
    @cfg(condition=True)
    def create_class():
        class DynamicClass:
            def method(self):
                return "dynamic"

        return DynamicClass

    cls = create_class()
    assert cls().method() == "dynamic"


def test_cfg_with_function_factory():
    @cfg(condition=True)
    def function_factory(prefix):
        def inner_func(value):
            return f"{prefix}_{value}"

        return inner_func

    func = function_factory("test")
    assert func("value") == "test_value"


def test_cfg_with_decorator_factory():
    @cfg(condition=True)
    def decorator_factory(prefix):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                return f"{prefix}_{result}"

            return wrapper

        return decorator

    decorator = decorator_factory("test")

    @decorator
    def test_func():
        return "value"

    assert test_func() == "test_value"


def test_cfg_with_recursive_generator():
    @cfg(condition=True)
    def recursive_gen(n):
        if n <= 0:
            yield "base"
        else:
            for val in recursive_gen(n - 1):
                yield f"{n}_{val}"

    assert list(recursive_gen(2)) == ["2_1_base"]


def test_cfg_with_generator_expression():
    @cfg(condition=True)
    def gen_func(n):
        return (i * i for i in range(n))

    assert list(gen_func(3)) == [0, 1, 4]


def test_cfg_with_list_comprehension():
    @cfg(condition=True)
    def list_comp(n):
        return [i * i for i in range(n)]

    assert list_comp(3) == [0, 1, 4]


def test_cfg_with_dict_comprehension():
    @cfg(condition=True)
    def dict_comp(n):
        return {i: i * i for i in range(n)}

    assert dict_comp(3) == {0: 0, 1: 1, 2: 4}


def test_cfg_with_set_comprehension():
    @cfg(condition=True)
    def set_comp(n):
        return {i * i for i in range(n)}

    assert set_comp(3) == {0, 1, 4}


def test_cfg_with_condition_based_on_globals():
    global global_var
    global_var = "test_value"

    @cfg(condition=lambda f: globals().get("global_var") == "test_value")
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_condition_based_on_locals():
    local_var = "test_value"

    @cfg(condition=lambda f: local_var == "test_value")
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_condition_based_on_function_attributes():
    def test_func():
        return "result"

    test_func.custom_attr = "test_value"

    @cfg(condition=lambda f: getattr(test_func, "custom_attr", None) == "test_value")
    def conditional_func():
        return "conditional"

    assert conditional_func() == "conditional"


def test_cfg_with_condition_based_on_module_attributes():
    sys.test_attr = "test_value"

    @cfg(condition=lambda f: getattr(sys, "test_attr", None) == "test_value")
    def test_func():
        return "result"

    assert test_func() == "result"

    # Clean up
    delattr(sys, "test_attr")


def test_cfg_with_condition_based_on_platform():
    import platform

    @cfg(condition=lambda f: platform.system() in ["Linux", "Darwin", "Windows"])
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_condition_based_on_python_version():
    @cfg(condition=lambda f: sys.version_info >= (3, 6))
    def test_func():
        return "result"

    assert test_func() == "result"


def test_cfg_with_condition_based_on_package_availability():
    has_numpy = False
    try:
        import importlib

        importlib.util.find_spec("numpy")

        has_numpy = True
    except ImportError:
        pass

    @cfg(condition=lambda f: has_numpy)
    def numpy_func():
        return "numpy_available"

    if has_numpy:
        assert numpy_func() == "numpy_available"
    else:
        with pytest.raises(TypeError):
            numpy_func()


def test_cfg_with_condition_based_on_function_name_pattern():
    import re

    @cfg(condition=lambda f: re.match(r"test_.*", f.__name__))
    def test_pattern_func():
        return "result"

    assert test_pattern_func() == "result"

    @cfg(condition=lambda f: re.match(r"test_.*", f.__name__))
    def non_matching_func():
        return "result"

    with pytest.raises(TypeError):
        non_matching_func()
