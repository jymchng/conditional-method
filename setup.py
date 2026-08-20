"""setuptools build configuration for the C extension.

The core implementation is a C extension (``conditional_method._c``)
built with the Limited API / Stable ABI (abi3) so a single ``cp39-abi3``
wheel covers CPython 3.9+.

A pure-Python fallback (``conditional_method._py``) with the same public
API is used automatically when the C extension cannot be imported.
"""

import sys

from setuptools import Extension, setup

IS_EMSCRIPTEN = sys.platform == "emscripten"

ext_kwargs = {}
options = {}
if not IS_EMSCRIPTEN:
    ext_kwargs["py_limited_api"] = True
    options["bdist_wheel"] = {"py_limited_api": "cp39"}

setup(
    ext_modules=[
        Extension(
            "conditional_method._c",
            sources=["src/conditional_method/_c.c"],
            **ext_kwargs,
        ),
    ],
    options=options,
)
