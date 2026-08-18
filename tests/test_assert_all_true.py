"""Tests for the eager module-level validation API (assert_all_true/_get_failed).

These cover:
- clean module: assert_all_true() -> None, _get_failed() -> []
- a single false-only decoration is reported and makes assert_all_true raise
- multiple failing names are all listed
- adding a true winner clears the raiser (cache keyed by qualname)
- cfg_attr raisers are also visible to the validation
- calling a raiser does NOT clear the recorded failures (append-only
  _failed_qualnames); it only clears the selection caches
- true winners are not reported
- weakref based caches prune dead entries (no unbounded growth)
"""

import gc

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


def test_raiser_call_keeps_failures():
    """Calling a raiser raises TypeError but does NOT clear the recorded
    failures: _failed_qualnames is append-only per name, so assert_all_true
    and _get_failed keep reporting the name until a true winner resolves it
    (or the set is cleared explicitly)."""

    @cfg(condition=False)
    def h():  # noqa: F811
        return 1

    assert _get_failed() == [_loc("test_raiser_call_keeps_failures.<locals>.h")]
    with pytest.raises(TypeError):
        h()
    # New #4 behavior: the failure persists after calling the raiser.
    assert _get_failed() == [_loc("test_raiser_call_keeps_failures.<locals>.h")]
    with pytest.raises(TypeError, match="No condition is true"):
        assert_all_true()


def test_raiser_call_clears_selection_caches_but_not_failures():
    """Calling a raiser clears the selection caches (last-wins reset) but the
    recorded _failed_qualnames is preserved (append-only)."""

    @cfg(condition=True)
    def win():  # noqa: F811
        return "ok"

    assert win() == "ok"

    @cfg(condition=False)
    def loser():  # noqa: F811
        return "no"

    loc = _loc("test_raiser_call_clears_selection_caches_but_not_failures.<locals>.loser")
    assert _get_failed() == [loc]
    with pytest.raises(TypeError):
        loser()
    # The failure remains reported (append-only) even though the caches reset.
    assert _get_failed() == [loc]
    with pytest.raises(TypeError, match="No condition is true"):
        assert_all_true()


def test_failures_persist_across_multiple_independent_raisers():
    """#4: all false-only names across the module stay reported, even after
    creating and calling several raisers (they must not wipe each other)."""
    locs = []

    @cfg(condition=False)
    def a1():  # noqa: F811
        return 1
    locs.append(_loc("test_failures_persist_across_multiple_independent_raisers.<locals>.a1"))

    @cfg(condition=False)
    def b1():  # noqa: F811
        return 2
    locs.append(_loc("test_failures_persist_across_multiple_independent_raisers.<locals>.b1"))

    # Calling one raiser must not clear the other's recorded failure.
    with pytest.raises(TypeError):
        a1()
    assert sorted(_get_failed()) == sorted(locs)

    # A true winner for one name removes only that name.
    @cfg(condition=True)
    def a1():  # noqa: F811
        return "ok"
    remaining = [l for l in locs if not l.endswith(".a1")]
    assert _get_failed() == remaining


def test_weakref_cache_prunes_dead_entries():
    """#1: the module cache stores weakrefs for true winners, so a dropped
    class's method is not pinned forever, and a high-water-mark sweep keeps
    the dict itself bounded.  Order-independent: it asserts the bounded-growth
    invariant rather than exact thresholds (dead-referent collection timing
    differs across CPython versions, so an exact `size < 128` boundary is not
    stable)."""
    _c._cm_cache.clear()
    _c._cfg_attr_cache.clear()

    def build_and_drop(count):
        for i in range(count):
            cls = type(f"Prune{i}", (), {"__module__": "leaktest"})

            def m(self, _i=i):  # noqa: ARG005
                return _i

            m.__qualname__ = f"Prune{i}.m"
            m.__module__ = "leaktest"
            setattr(cls, "m", cfg(condition=True)(m))
        gc.collect()

    # Build a large number of throwaway decorated winners, then garbage
    # collect them so their weakref referents die.
    build_and_drop(400)
    gc.collect()

    def referent_alive(k):
        v = _c._cm_cache.get(k)
        return v is not None and v() is not None

    # Nothing keeps these methods alive, so after GC none of the cached
    # referents is pinned (weakrefs, not strong refs).
    assert sum(1 for k in list(_c._cm_cache) if referent_alive(k)) == 0

    # A fresh batch of writes that clearly exceeds the high-water mark forces
    # a dead-weakref sweep, so the dict stays bounded well below the 400 that
    # were created.  The bound is deliberately loose (a buffer over the sweep
    # threshold) because how many dead entries accumulate before the sweep
    # runs depends on the interpreter's GC/reference-counting timing.
    build_and_drop(150)
    gc.collect()
    size = len(_c._cm_cache)
    assert size < 200, f"cache not bounded after sweep: size={size}"
    assert sum(1 for k in list(_c._cm_cache) if referent_alive(k)) == 0



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
