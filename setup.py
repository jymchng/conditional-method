from setuptools import setup, Extension

conditional_method_module = Extension(
    "_lib",
    sources=["src/conditional_method/_lib.c"],
    extra_compile_args=["-Wall", "-Wextra", "-std=c99"],
)

setup(
    name="conditional_method",
    version="1.0",
    description="A Python C extension module for conditional method decorators",
    ext_modules=[conditional_method_module],
    py_modules=[],
)
