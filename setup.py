from setuptools import setup, Extension
import importlib

conditional_method_module = Extension(
    "_lib",
    sources=["src/conditional_method/_lib.c"],
    extra_compile_args=[
        # "-Werror",
        "-Wall",
        "-Wextra",
        "-std=c99",
        "-O3",  # Maximum optimization
        "-march=native",  # Optimize for the host CPU
        "-mtune=native",  # Tune for the host CPU
        "-ffast-math",  # Allow aggressive floating-point optimizations
        "-funroll-loops",  # Unroll loops for better performance
        "-fomit-frame-pointer",  # Reduce stack overhead
        "-flto",  # Link-time optimization
        "-falign-functions=32",  # Better instruction alignment
        "-falign-jumps=32",  # Improve branch prediction
        "-falign-loops=32",  # Optimize loop execution
        "-fstrict-aliasing",  # Enable strict aliasing for better optimization
        "-fprefetch-loop-arrays",  # Prefetch data for loops
        "-ftree-vectorize",  # Enable auto-vectorization
        "-fipa-pta",  # Interprocedural pointer analysis
        "-fipa-cp-clone",  # Interprocedural constant propagation
        # "-fprofile-generate",  # Profile-guided optimization (for training runs)
    ]
    if not ("win32" in importlib.import_module("sys").platform)
    else [
        # "/WX",
        "/W3",
        "/std:c11",
        "/O2",
        "/arch:AVX2",
        "/fp:fast",
        "/GL",  # Whole program optimization
        "/Gy",  # Enable function-level linking
        "/Qpar",  # Auto-parallelization
        "/Qvec",  # Auto-vectorization
        "/Qfast_transcendentals",  # Fast transcendental functions
        "/Qopt-report:5",  # Optimization report for debugging
        "/fp:except-",  # Disable floating-point exceptions
    ],
    define_macros=[("NDEBUG", None)],
    py_limited_api=False,
)


setup(
    name="conditional_method",
    version="1.0",
    description="A Python C extension module for conditional method decorators",
    ext_modules=[conditional_method_module],
    py_modules=[],
)
