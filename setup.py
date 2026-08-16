"""setuptools build configuration for the C extension.

The core implementation of ``conditional-method`` is a C extension (``cfg._c``)
built with the Limited API / Stable ABI (abi3) so a single ``cp39-abi3``
wheel covers CPython 3.9+.

There is no pure-Python implementation: ``cfg`` is an import shim over the
C extension only.
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
            "cfg._c",
            sources=["src/cfg/_c.c"],
            **ext_kwargs,
        ),
    ],
    options=options,
)
