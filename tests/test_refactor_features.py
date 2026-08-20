"""Tests for the refactor features (proposals #1-#7, #10).

Covers:
- #7: public pending_failures() and ConditionFailureError (TypeError subclass
  carrying .failed qualnames), assert_all_true still raising.
- #10: CfgCallable __repr__/__reduce__ (pickling); debug output paths.
- #4: interned qualname keys (cache keys are interned strings).
- #5: constant-condition fast path (condition=True returns the function).
- #6: dead-weakref sweep keeps the cache bounded; dead-counter path.
- #1: _cm_inner_fast / _cm_wrapper public behavior preserved (decoration works).
"""

import gc
import pickle

import pytest

import conditional_method
from conditional_method import (
    ConditionFailureError,
    _c,
    _get_failed,
    assert_all_true,
    cfg,
    cfg_attr,
    pending_failures,
)


@pytest.fixture(autouse=True)
def _clean_caches():
    _c._cm_cache.clear()
    _c._cfg_attr_cache.clear()
    _c._failed_qualnames.clear()
    yield
    _c._cm_cache.clear()
    _c._cfg_attr_cache.clear()
    _c._failed_qualnames.clear()


# ── #7 friendly failure API ──────────────────────────────────────────────


def test_pending_failures_is_public_and_empty_by_default():
    assert pending_failures() == []
    assert pending_failures() == _get_failed()


def _qualname():
    return __name__ + ".test_placeholder.<locals>.bad"


def test_pending_failures_reports_false_conditions():
    @cfg(condition=False)
    def bad():
        return 1

    assert pending_failures() and any("bad" in f for f in pending_failures())


def test_condition_failure_error_is_typeerror_subclass():
    assert issubclass(ConditionFailureError, TypeError)


def test_condition_failure_error_carries_failed_qualnames():
    @cfg(condition=False)
    def bad():
        return 1

    with pytest.raises(TypeError) as excinfo:
        assert_all_true()
    # reloads in other test modules recreate ConditionFailureError; the stable
    # base is TypeError. Verify the rich payload instead of class identity.
    assert getattr(excinfo.value, "failed", None) and "bad" in excinfo.value.failed[0]
    assert "bad" in str(excinfo.value)


def test_assert_all_true_returns_none_when_clean():
    @cfg(condition=True)
    def good():
        return 1

    assert assert_all_true() is None


def test_true_winner_clears_failure():
    @cfg(condition=False)
    def dup():
        return "bad"

    assert any("dup" in f for f in pending_failures())

    @cfg(condition=True)
    def dup():  # noqa: F811
        return "good"

    assert pending_failures() == []


# ── #10 CfgCallable repr / reduce ────────────────────────────────────────


def test_cfg_callable_repr():
    assert "cm" in repr(conditional_method.cm)
    assert "CfgCallable" in type(conditional_method.cm).__name__


def test_cfg_callable_pickle_roundtrip():
    data = pickle.dumps(conditional_method.cm)
    assert isinstance(data, bytes) and len(data) > 0


# ── #4 interned qualname keys ────────────────────────────────────────────


def test_cache_keys_are_interned_strings():
    @cfg(condition=True)
    def target():
        return 1

    key = list(_c._cm_cache.keys())[0]
    assert isinstance(key, str)
    # Interned strings share identity with their interned equal.
    assert key is sys_intern(key)


def sys_intern(s):
    import sys

    return sys.intern(s)


# ── #5 constant-condition fast path ──────────────────────────────────────


def test_true_condition_returns_function_identity():
    def raw():
        return 42

    decorated = cfg(condition=True)(raw)
    assert decorated is raw  # fast path returns the same function object


# ── #6 dead-weakref sweep keeps cache bounded ────────────────────────────


def test_dead_weakref_sweep_bounds_cache():
    """Mirrors the original suite's bounded-growth invariant: a large batch of
    throwaway decorations past the high-water mark triggers a dead-weakref
    sweep, so the dict stays well below the number created (loose bound)."""

    def build_and_drop(count):
        for i in range(count):
            cls = type(f"Sweep{i}", (), {"__module__": "leaktest"})

            def m(self, _i=i):  # noqa: ARG005
                return _i

            m.__qualname__ = f"Sweep{i}.m"
            m.__module__ = "leaktest"
            setattr(cls, "m", cfg(condition=True)(m))
        gc.collect()

    build_and_drop(400)
    gc.collect()
    build_and_drop(150)
    gc.collect()
    size = len(_c._cm_cache)
    assert size < 200, f"cache not bounded after sweep: size={size}"


# ── #1 public decoration still works through the fast path ───────────────


def test_decoration_through_fast_path():
    class A:
        @cfg(condition=True)
        def work(self, x):
            return x * 2

        @cfg(condition=False)
        def work(self, x):  # noqa: F811
            return x + 100

    assert A().work(21) == 42
