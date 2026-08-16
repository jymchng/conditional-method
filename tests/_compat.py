"""Version-agnostic exception assertions for CPython behavior differences.

CPython changed two observable behaviors across the supported range
(3.9 – 3.14):

1. ``__set_name__`` failures:
   - CPython < 3.12 wraps the error raised by ``__set_name__`` in
     ``RuntimeError: Error calling __set_name__ on ...``; the original
     ``TypeError`` is attached as ``__cause__``.
   - CPython 3.12+ propagates the original ``TypeError`` unchanged (with
     the wrapper text attached as a *note* via ``__notes__``).

2. Using an object that lacks ``__enter__`` / ``__exit__`` as a context
   manager:
   - CPython < 3.11 raises ``AttributeError`` (``__enter__`` not found).
   - CPython 3.11+ raises ``TypeError`` (``does not support the context
     manager protocol``).

These helpers return the appropriate ``pytest.raises`` context manager so a
single test body is correct on every supported interpreter.
"""

import sys

import pytest

_IS_312_PLUS = sys.version_info >= (3, 12)
_IS_311_PLUS = sys.version_info >= (3, 11)


def raises_set_name_error():
    """The exception a raiser's ``__set_name__`` produces at class build."""
    if _IS_312_PLUS:
        return pytest.raises(TypeError)
    return pytest.raises(RuntimeError, match="Error calling __set_name__")


def raises_missing_context_manager():
    """Using an object without ``__enter__``/``__exit__`` as a context manager."""
    if _IS_311_PLUS:
        return pytest.raises(TypeError, match="context manager protocol")
    return pytest.raises(AttributeError)
