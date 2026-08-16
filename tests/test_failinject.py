"""Test-only allocation-failure injection (requires -DPY_CFG_TESTING).

Sweeps conditional_method._c.set_alloc_fail_count(n) so each guarded allocation site fails
with MemoryError once, covering the C module's OOM error paths (which is how
the C line coverage reaches >90% in the gcov CI gate).
"""

import pytest

pytestmark = pytest.mark.skipif(
    not hasattr(__import__("conditional_method")._c, "set_alloc_fail_count"),
    reason="extension not built with PY_CFG_TESTING",
)

import conditional_method._c as c


def _reset():
    c.set_alloc_fail_count(-1)


@pytest.fixture(autouse=True)
def reset_count():
    yield
    _reset()


def _expect_memoryerror(fn, *args, **kwargs):
    c.set_alloc_fail_count(0)
    with pytest.raises(MemoryError):
        fn(*args, **kwargs)
    _reset()


def test_fail_type_error_raiser_new():
    def f():
        return 1

    _expect_memoryerror(c._raise_exec, "x")


def test_fail_cm_decorator_alloc():
    # _cm_wrapper triggers Py_BuildValue("(OO)", func, condition) guarded alloc
    def f():
        return 1

    _expect_memoryerror(c._cm_wrapper, f)


def test_fail_cm_inner_tuple_alloc():
    def f():
        return 1

    _expect_memoryerror(c.cm, f, condition=lambda fn: True)


def test_fail_cfg_attr_default_decorators():
    def f():
        return 1

    _expect_memoryerror(c.cfg_attr, f, condition=True)


def test_fail_cfg_attr_apply_decorators():
    def f():
        return 1

    _expect_memoryerror(c.cfg_attr, f, condition=True, decorators=[lambda fn: fn])


def test_fail_cfg_make_raiser():
    def f():
        return 1

    _expect_memoryerror(c.cm, f, condition=False)


def test_fail_cm_wrapper_buildvalue():
    def f():
        return 1

    _expect_memoryerror(c._cm_wrapper, f)


def _run_scenario(fn):
    """Fail at each guarded-allocation index 0..N so EVERY guard site and its
    cleanup lines execute (the precise per-site coverage sweep)."""
    raised = False
    for n in range(0, 30):
        c.set_alloc_fail_count(n)
        try:
            fn()
        except MemoryError:
            raised = True
        except Exception:
            pass
        finally:
            c.set_alloc_fail_count(-1)
    assert raised, f"scenario {fn} never raised MemoryError"


def _run_scenario_fail_last(fn):
    """Best-effort: fail at a high index so the LAST guard fires (if the
    scenario has enough guards); not asserted for short scenarios."""
    for n in (3, 4, 5, 6, 8, 10):
        c.set_alloc_fail_count(n)
        try:
            fn()
        except MemoryError:
            return
        except Exception:
            pass
        finally:
            c.set_alloc_fail_count(-1)


def test_exhaustive_fail_sweep_cm():
    def f():
        return 1

    def scenario():
        cm_d = c.cm(condition=True)
        cm_d(f)

    _run_scenario(scenario)
    _run_scenario_fail_last(scenario)


def test_exhaustive_fail_sweep_cm_false():
    def f():
        return 1

    def scenario():
        cm_d = c.cm(condition=False)
        cm_d(f)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cm_callable():
    def f():
        return 1

    def scenario():
        cm_d = c.cm(condition=lambda fn: True)
        cm_d(f)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_true():
    def f():
        return 1

    def scenario():
        d = c.cfg_attr(condition=True, decorators=[lambda fn: fn])
        d(f)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_false():
    def f():
        return 1

    def scenario():
        d = c.cfg_attr(condition=False, decorators=[lambda fn: fn])
        d(f)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_callable():
    def f():
        return 1

    def scenario():
        d = c.cfg_attr(condition=lambda fn: True, decorators=[lambda fn: fn])
        d(f)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_raiser_call():
    """Fail sweeps over TypeErrorRaiser.__call__ -> _raise_typeerror allocs."""
    from conditional_method._c import _TypeErrorRaiser

    def scenario():
        r = _TypeErrorRaiser()
        try:
            r()
        except TypeError:
            pass

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cm_callable_false():
    """cm callable condition -> False -> raiser creation allocs."""

    def f():
        return 1

    def scenario():
        cm_d = c.cm(condition=lambda fn: False)
        cm_d(f)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_callable_false():
    """cfg_attr callable condition -> False -> raiser creation allocs."""

    def f():
        return 1

    def scenario():
        d = c.cfg_attr(condition=lambda fn: False, decorators=[lambda fn: fn])
        d(f)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_factory_true():
    """cfg_attr factory (True, non-callable) -> closure allocs."""

    def scenario():
        d = c.cfg_attr(condition=True, decorators=[])
        d(lambda: 1)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_factory_false():
    """cfg_attr factory (False, non-callable) -> closure allocs."""

    def scenario():
        d = c.cfg_attr(condition=False, decorators=[])
        d(lambda: 1)

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_direct_empty_decorators():
    """cfg_attr direct True with empty decorators -> PyTuple_New(0)."""

    def f():
        return 1

    def scenario():
        c.cfg_attr(f, condition=True, decorators=[])

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_direct_true_multi_deco():
    """cfg_attr direct True with multiple decorators -> apply loop allocs."""

    def f():
        return 1

    def scenario():
        c.cfg_attr(f, condition=True, decorators=[lambda fn: fn, lambda fn: fn])

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_direct_false():
    """cfg_attr direct False -> raiser allocs."""

    def f():
        return 1

    def scenario():
        c.cfg_attr(f, condition=False, decorators=[])

    _run_scenario(scenario)


def test_exhaustive_fail_sweep_cfg_attr_wrapper():
    """cfg_attr_wrapper with a valid closure -> kwargs/apply allocs."""

    def scenario():
        d = c.cfg_attr(condition=True, decorators=[lambda fn: fn])
        d(lambda: 1)

    _run_scenario(scenario)


def test_global_union_fail_sweep():
    """Run every public op at each fail index 0..40 so EVERY guard in EVERY
    function fires at least once across the whole suite."""
    import gc as _gc

    def f():
        return 1

    ops = [
        lambda: c.cm(condition=True)(f),
        lambda: c.cm(condition=False)(f),
        lambda: c.cm(condition=lambda fn: True)(f),
        lambda: c.cm(condition=lambda fn: False)(f),
        lambda: c.cfg_attr(f, condition=True, decorators=[]),
        lambda: c.cfg_attr(f, condition=True, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(
            f, condition=True, decorators=[lambda fn: fn, lambda fn: fn]
        ),
        lambda: c.cfg_attr(f, condition=False, decorators=[]),
        lambda: c.cfg_attr(f, condition=False, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(f, condition=lambda fn: True, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(f, condition=lambda fn: False, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(condition=True, decorators=[])(f),
        lambda: c.cfg_attr(condition=False, decorators=[])(f),
        lambda: c._cm_wrapper(f),
        lambda: c._raise_exec("q"),
        lambda: c._TypeErrorRaiser(),
    ]

    raised_any = False
    for n in range(0, 45):
        c.set_alloc_fail_count(n)
        for op in ops:
            try:
                op()
            except MemoryError:
                raised_any = True
            except Exception:
                pass
        c.set_alloc_fail_count(-1)
    _gc.collect()
    assert raised_any, "no MemoryError across the union sweep"


def test_always_fail_mode_covers_all_guards():
    """set_alloc_fail_count(-2) makes EVERY guarded allocation fail; running
    the union of ops then covers every guard's cleanup path in one pass."""
    import gc as _gc

    def f():
        return 1

    ops = [
        lambda: c.cm(condition=True)(f),
        lambda: c.cm(condition=False)(f),
        lambda: c.cm(condition=lambda fn: True)(f),
        lambda: c.cm(condition=lambda fn: False)(f),
        lambda: c.cfg_attr(f, condition=True, decorators=[]),
        lambda: c.cfg_attr(f, condition=True, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(
            f, condition=True, decorators=[lambda fn: fn, lambda fn: fn]
        ),
        lambda: c.cfg_attr(f, condition=False, decorators=[]),
        lambda: c.cfg_attr(f, condition=False, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(f, condition=lambda fn: True, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(f, condition=lambda fn: False, decorators=[lambda fn: fn]),
        lambda: c.cfg_attr(condition=True, decorators=[])(f),
        lambda: c.cfg_attr(condition=False, decorators=[])(f),
        lambda: c.cfg_attr(condition=lambda fn: True, decorators=[lambda fn: fn])(f),
        lambda: c._cm_wrapper(f),
        lambda: c.cfg_attr_wrapper("x"),
        lambda: c._raise_exec("q"),
        lambda: c._TypeErrorRaiser(),
        lambda: c._TypeErrorRaiser()(),
    ]

    c.set_alloc_fail_count(-2)
    raised = 0
    for op in ops:
        try:
            op()
        except MemoryError:
            raised += 1
        except Exception:
            pass
    c.set_alloc_fail_count(-1)
    _gc.collect()
    assert raised > 0, "always-fail mode never raised"
