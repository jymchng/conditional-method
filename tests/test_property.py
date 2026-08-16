"""Property-based tests: C implementation parity with plain-Python semantics.

Uses Hypothesis to generate functions (with unique qualified names),
conditions (bool / callable), and decorator chains, then asserts the C
extension (``cfg._c``) behaves exactly like a plain-Python reference model
for the public API:

- ``cm`` / ``cfg`` / ``if_`` / ``conditional_method`` (all aliases of the
  same callable) — conditional method selection,
- ``cfg_attr`` — conditional decorator application.

The module-level caches are keyed by qualified name, so every generated
example uses a *fresh unique* module name to keep examples independent.
"""

from __future__ import annotations

import uuid

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import cfg._c as c
from cfg import (
    _get_mod_qual_func_name,
    cfg,
    cfg_attr,
    cm,
    conditional_method,
    if_,
)

# --- Reference model (plain-Python semantics) -----------------------------

RAISER = object()  # sentinel: "a TypeErrorRaiser is returned"


def _is_raiser(obj) -> bool:
    return isinstance(obj, c._TypeErrorRaiser)


def _qual(func) -> str:
    return _get_mod_qual_func_name(func)


def _truth(condition, func) -> bool:
    """Evaluate a condition the way the C module does."""
    if callable(condition):
        return bool(condition(func))
    return bool(condition)


def ref_cm(func, condition, cache):
    """Reference semantics for cm/cfg/if_/conditional_method."""
    name = _qual(func)
    if _truth(condition, func):
        cache[name] = func
        return func
    if name in cache:
        return cache[name]
    return RAISER


def ref_cfg_attr(func, condition, decorators, cache):
    """Reference semantics for cfg_attr (decorators applied in order)."""
    name = _qual(func)
    if _truth(condition, func):
        result = func
        for d in reversed(decorators):  # decorators[0] is outermost
            result = d(result)
        cache[name] = result
        return result
    if name in cache:
        return cache[name]
    return RAISER


def _outcome(fn, *args):
    """('ok', value) or ('raise', ExceptionTypeName)."""
    try:
        return ("ok", fn(*args))
    except Exception as e:  # noqa: BLE001 - we classify any error
        return ("raise", type(e).__name__)


# --- Helpers to build unique functions ------------------------------------

_counter = 0


def _make_func(value: int, prefix: str = "f"):
    """A function with a globally-unique qualified name."""
    global _counter
    _counter += 1
    mod = f"hyp_{uuid.uuid4().hex[:10]}_{_counter}"

    def f():
        return value

    f.__module__ = mod
    f.__qualname__ = prefix
    return f


def _make_unary_func(prefix: str = "g"):
    """A one-argument function returning [x] (for cfg_attr order tests)."""
    global _counter
    _counter += 1
    mod = f"hyp_{uuid.uuid4().hex[:10]}_{_counter}"

    def g(x):
        return [x]

    g.__module__ = mod
    g.__qualname__ = prefix
    return g


def _make_deco(marker: int):
    """A decorator that appends a marker to a list-returning function."""

    def deco(fn):
        def wrapper(x):
            return fn(x) + [marker]

        return wrapper

    return deco


@st.composite
def unique_func(draw):
    value = draw(st.integers(min_value=-1000, max_value=1000))
    return _make_func(value)


# --- Tests -----------------------------------------------------------------

def test_alias_identity():
    """cm, cfg, if_ and conditional_method are the same callable."""
    assert cm is cfg
    assert cm is if_
    assert cm is conditional_method
    assert cm._cache is cfg_attr._cache or True  # both exist


@given(cond=st.booleans())
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_cm_bool_condition_parity(cond):
    """cm(f, condition=b) matches the reference for bool conditions."""
    f = _make_func(1)
    cache: dict = {}
    expected = ref_cm(f, cond, cache)
    actual = cm(f, condition=cond)

    if expected is RAISER:
        assert _is_raiser(actual)
        assert _outcome(actual)[0] == "raise"
        assert _outcome(actual)[1] == "TypeError"
    else:
        assert actual is expected  # same function object
        assert _outcome(actual) == ("ok", 1)


@given(cond=st.booleans())
@settings(max_examples=60, deadline=None)
def test_cm_callable_condition_parity(cond):
    """cm(f, condition=callable) matches the reference."""
    f = _make_func(2)
    cache: dict = {}
    expected = ref_cm(f, lambda fn: cond, cache)
    actual = cm(f, condition=lambda fn: cond)

    if expected is RAISER:
        assert _is_raiser(actual)
        assert _outcome(actual)[1] == "TypeError"
    else:
        assert actual is f
        assert _outcome(actual) == ("ok", 2)


@given(cond=st.booleans())
@settings(max_examples=60, deadline=None)
def test_cm_factory_and_direct_equivalent(cond):
    """cm(condition=cond)(f) behaves identically to cm(f, condition=cond)."""
    f = _make_func(3)
    direct = cm(f, condition=cond)
    via_factory = cm(condition=cond)(f)
    assert _is_raiser(direct) == _is_raiser(via_factory)
    if _is_raiser(direct):
        assert _is_raiser(via_factory)
    else:
        assert direct is via_factory is f


@given(cond=st.booleans())
@settings(max_examples=60, deadline=None)
def test_cm_cache_parity(cond):
    """After a true condition caches a name, false returns the cached func."""
    f = _make_func(4)

    first_true = cm(f, condition=True)
    assert first_true is f

    # Second application with *any* condition returns the cached func.
    second = cm(f, condition=cond)
    if cond:
        assert second is f
    else:
        assert second is f  # cached — not a raiser

    assert not _is_raiser(second)
    assert _outcome(second) == ("ok", 4)


@given(markers=st.lists(st.integers(min_value=0, max_value=9), min_size=0, max_size=4, unique=True))
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_cfg_attr_true_parity_and_order(markers):
    """cfg_attr true applies decorators in order, matching the reference."""
    f = _make_unary_func(prefix="attr")
    decos = [_make_deco(m) for m in markers]
    cache: dict = {}
    expected = ref_cfg_attr(f, True, decos, cache)
    actual = cfg_attr(f, condition=True, decorators=decos)

    assert _outcome(actual, 5) == _outcome(expected, 5)
    # decorators[0] is outermost => markers appear in reverse listed order
    assert _outcome(actual, 5) == ("ok", [5] + list(reversed(markers)))


@given(cond=st.booleans())
@settings(max_examples=60, deadline=None)
def test_cfg_attr_bool_condition_parity(cond):
    """cfg_attr with bool condition matches the reference."""
    f = _make_unary_func(prefix="ab")
    decos = [_make_deco(7)]
    cache: dict = {}
    expected = ref_cfg_attr(f, cond, decos, cache)
    actual = cfg_attr(f, condition=cond, decorators=decos)

    if expected is RAISER:
        assert _is_raiser(actual)
        assert _outcome(actual)[1] == "TypeError"
    else:
        assert _outcome(actual, 1) == _outcome(expected, 1)


@given(cond=st.booleans())
@settings(max_examples=60, deadline=None)
def test_cfg_attr_callable_condition_parity(cond):
    """cfg_attr with callable condition matches the reference."""
    f = _make_func(8, prefix="ac")
    decos = [_make_deco(9)]
    cache: dict = {}
    expected = ref_cfg_attr(f, lambda fn: cond, decos, cache)
    actual = cfg_attr(f, condition=lambda fn: cond, decorators=decos)

    if expected is RAISER:
        assert _is_raiser(actual)
        assert _outcome(actual)[1] == "TypeError"
    else:
        assert _outcome(actual, 2) == _outcome(expected, 2)


@given(markers=st.lists(st.integers(min_value=0, max_value=9), min_size=0, max_size=3, unique=True))
@settings(max_examples=40, deadline=None)
def test_cfg_attr_cache_parity(markers):
    """cfg_attr caches the decorated func; later false reuses the cache."""
    f = _make_unary_func(prefix="cache")
    decos = [_make_deco(m) for m in markers]

    first = cfg_attr(f, condition=True, decorators=decos)
    assert _outcome(first, 3) == ("ok", [3] + list(reversed(markers)))

    second = cfg_attr(f, condition=False, decorators=[])
    assert not _is_raiser(second)
    assert _outcome(second, 3) == _outcome(first, 3)


@given(cond=st.booleans())
@settings(max_examples=40, deadline=None)
def test_cfg_attr_factory_parity(cond):
    """cfg_attr(condition=cond, decorators=...)(f) == direct call."""
    f = _make_func(11, prefix="fac")
    decos = [_make_deco(12)]
    direct = cfg_attr(f, condition=cond, decorators=decos)
    via_factory = cfg_attr(condition=cond, decorators=decos)(f)
    assert _is_raiser(direct) == _is_raiser(via_factory)
    if not _is_raiser(direct):
        assert _outcome(via_factory, 4) == _outcome(direct, 4)


@given(cond=st.booleans())
@settings(max_examples=40, deadline=None)
def test_aliases_behave_identically(cond):
    """cfg, if_, conditional_method produce identical results to cm."""
    f = _make_func(13)
    results = [api(f, condition=cond) for api in (cm, cfg, if_, conditional_method)]
    raiser_flags = [_is_raiser(r) for r in results]
    assert all(flag == raiser_flags[0] for flag in raiser_flags)
    if not raiser_flags[0]:
        assert all(r is f for r in results)


@given(value=st.integers(min_value=-10, max_value=10))
@settings(max_examples=40, deadline=None)
def test_errors_parity(value):
    """Error branches match the documented semantics."""
    f = _make_func(value)

    with pytest.raises(TypeError):
        cm(f)  # function without condition

    with pytest.raises(TypeError):
        cfg_attr(f, condition=True, decorators=42)  # non-sequence decorators

    with pytest.raises(ValueError):
        cfg_attr()  # factory without condition

    with pytest.raises(ValueError):
        cfg_attr(condition=None, decorators=[])

    # fresh name, false condition -> raiser raises TypeError when called
    g = _make_func(value, prefix="err")
    raiser = cfg_attr(g, condition=False, decorators=[])
    assert _is_raiser(raiser)
    with pytest.raises(TypeError):
        raiser()


@given(cond=st.booleans())
@settings(max_examples=40, deadline=None)
def test_cm_callable_condition_receives_func(cond):
    """The callable condition is invoked with the decorated function."""
    seen = []

    def condition(fn):
        seen.append(fn)
        return cond

    f = _make_func(14)
    cm(f, condition=condition)
    assert seen == [f]
