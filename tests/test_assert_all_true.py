"""Tests for the eager module-level validation API (assert_all_true/_get_failed).

These cover:
- clean module: assert_all_true() -> None, _get_failed() -> []
- a single false-only decoration is reported and makes assert_all_true raise
- multiple failing names are all listed
- adding a true winner clears the raiser (cache keyed by qualname)
- cfg_attr raisers are also visible to the validation
- calling a raiser clears the caches (no stale failures)
- true winners are not reported
"""

import pytest

from conditional_method import _c, assert_all_true, cfg, cfg_attr, _get_failed


@pytest.fixture(autouse=True)
def _clean_caches():
    """Each test starts with an empty cm cache and no recorded failures."""
    _c._cm_cache.clear()
    _c._cfg_attr_cache.clear()
    _c._failed_qualnames.clear()
    yield
    _c._cm_cache.clear()
    _c._cfg_attr_cache.clear()
    _c._failed_qualnames.clear()


def _loc(qname_suffix):
    """Return the fully-qualified name pytest assigns to a local function."""
    return f"{__name__}.{qname_suffix}"


def test_assert_all_true_clean_module():
    """No failures: assert_all_true returns None and _get_failed is empty."""
    assert _get_failed() == []
    assert assert_all_true() is None


def test_assert_all_true_single_failure():
    """A false-only name is reported and assert_all_true raises TypeError."""

    @cfg(condition=False)
    def bad():  # noqa: F811
        return 1

    assert _get_failed() == [_loc("test_assert_all_true_single_failure.<locals>.bad")]
    with pytest.raises(TypeError, match="No condition is true for 1 decorated name"):
        assert_all_true()


def test_assert_all_true_multiple_failures():
    """Multiple failing names are all listed in the error."""

    @cfg(condition=False)
    def one():  # noqa: F811
        return 1

    @cfg(condition=False)
    def two():  # noqa: F811
        return 2

    failed = _get_failed()
    assert sorted(failed) == sorted(
        [
            _loc("test_assert_all_true_multiple_failures.<locals>.one"),
            _loc("test_assert_all_true_multiple_failures.<locals>.two"),
        ]
    )
    with pytest.raises(TypeError, match="2 decorated name"):
        assert_all_true()


def test_true_winner_clears_raiser():
    """A later condition=True winner for the same name removes the failure."""

    @cfg(condition=False)
    def f():  # noqa: F811
        return 1

    assert _get_failed() == [_loc("test_true_winner_clears_raiser.<locals>.f")]

    @cfg(condition=True)
    def f():  # noqa: F811
        return 2

    assert _get_failed() == []
    assert assert_all_true() is None
    assert f() == 2


def test_cfg_attr_raiser_visible():
    """cfg_attr(condition=False) also produces a visible failure."""

    @cfg_attr(condition=False, decorators=[])
    def g():  # noqa: F811
        return 1

    assert _get_failed() == [_loc("test_cfg_attr_raiser_visible.<locals>.g")]
    with pytest.raises(TypeError, match="No condition is true"):
        assert_all_true()


def test_raiser_call_clears_failures():
    """Calling a raiser clears the caches, so _get_failed becomes empty."""

    @cfg(condition=False)
    def h():  # noqa: F811
        return 1

    assert _get_failed() == [_loc("test_raiser_call_clears_failures.<locals>.h")]
    with pytest.raises(TypeError):
        h()
    assert _get_failed() == []


def test_get_failed_after_true_winners_only():
    """Only false names are reported; true winners are not."""

    @cfg(condition=True)
    def ok():  # noqa: F811
        return "ok"

    @cfg(condition=False)
    def bad():  # noqa: F811
        return "bad"

    assert _get_failed() == [_loc("test_get_failed_after_true_winners_only.<locals>.bad")]
    assert ok() == "ok"


@pytest.mark.skipif(
    not hasattr(_c, "set_alloc_fail_count"),
    reason="extension not built with PY_CFG_TESTING",
)
def test_assert_all_true_alloc_fail():
    """assert_all_true surfaces MemoryError when a guarded allocation fails."""
    _c.set_alloc_fail_count(-1)
    try:
        # A failing name must be present so the error path (join/format)
        # runs; then sweep the guard index so every guarded allocation in
        # assert_all_true/_get_failed is exercised.
        @cfg(condition=False)
        def boom():  # noqa: F811
            return 1

        raised = False
        for n in range(0, 12):
            _c.set_alloc_fail_count(n)
            try:
                assert_all_true()
            except MemoryError:
                raised = True
                break
        assert raised, "no MemoryError raised across the guard sweep"
    finally:
        _c.set_alloc_fail_count(-1)
