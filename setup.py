from setuptools import setup, Extension
import importlib

conditional_method_module = Extension(
    "_lib",
    sources=["src/conditional_method/_lib.c"],
    extra_compile_args=["-Wall", "-Wextra", "-std=c99", "-O3", "-march=native", "-ffast-math"] if not (
        "win32" in importlib.import_module("sys").platform
    ) else ["/W3", "/std:c11", "/O2", "/arch:AVX2", "/fp:fast"],
    define_macros=[("PY_SSIZE_T_CLEAN", None), ("NDEBUG", None)],
    py_limited_api=False,
)

setup(
    name="conditional_method",
    version="1.0",
    description="A Python C extension module for conditional method decorators",
    ext_modules=[conditional_method_module],
    py_modules=[],
)
