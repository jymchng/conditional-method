"""Targeted C-extension error-path coverage (requires -DPY_CFG_TESTING).

Exercises the parse-error, broken-protocol, surrogate-encoding, GC/clear and
module-init error branches of ``cfg._c`` that the main suite cannot reach,
carrying the gcov line-coverage gate past 90%.

(The guard-based allocation-failure sweeps for the *guarded* sites live in
``test_failinject.py``; the branches *after* a guard — e.g. an actual
``PyDict_SetItem`` failure — are unreachable from Python on a stock CPython
build because object allocations go through pymalloc, which cannot be
redirected without corrupting the interpreter.)
"""

import gc
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(
    not hasattr(__import__("cfg")._c, "set_alloc_fail_count"),
    reason="extension not built with PY_CFG_TESTING",
)

import cfg._c as c


def _reset():
    c.set_alloc_fail_count(-1)


def _run_sweep(ops, max_idx=60):
    """Sweep the allocation-failure index across ops; require >=1 MemoryError.

    ops is a list of zero-arg callables.  Each iteration arms the guard-based
    counter so the nth guarded allocation (whichever op consumes it) raises
    MemoryError; sweeping the range covers every guarded branch.  Index-based
    iteration is deliberate — ``for op in ops`` would allocate an iterator
    after the counter is armed.
    """
    raised = False
    n_ops = len(ops)
    for n in range(0, max_idx + 1):
        c.set_alloc_fail_count(n)
        i = 0
        while i < n_ops:
            op = ops[i]
            try:
                op()
            except MemoryError:
                raised = True
            except Exception:
                pass
            i += 1
        _reset()
    assert raised, "no allocation ever failed"


def test_sweep_raiser_with_qualnames():
    """_raise_typeerror with a populated f_qualnames set (non-empty message).

    A raiser produced by ``cm(f, condition=False)`` carries the function's
    qualname in f_qualnames, so the PyIter_Next/PyList_Append branches of
    _raise_typeerror run (and their allocation-failure branches fire).
    """

    def scenario():
        raiser = c.cm(lambda: 1, condition=False)
        try:
            raiser()
        except TypeError:
            pass

    ops = [scenario]
    _run_sweep(ops, max_idx=60)


def test_cfg_callable_uninitialized_call():
    """CfgCallable_call with callable==NULL raises RuntimeError.

    The heap type has no tp_new, so a bare instance can only be produced via
    PyType_GenericAlloc (allocation) + ctypes.  ``_self`` back-reference then
    forms a GC cycle whose collection exercises CfgCallable_clear.
    """
    import ctypes

    api = ctypes.pythonapi
    api.PyType_GenericAlloc.restype = ctypes.c_void_p
    api.PyType_GenericAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    ptr = api.PyType_GenericAlloc(ctypes.c_void_p(id(c._CfgCallable)), 0)
    assert ptr
    inst = ctypes.cast(ptr, ctypes.py_object).value
    with pytest.raises(RuntimeError, match="uninitialized"):
        inst()
    inst._self = inst
    del inst
    gc.collect()


def test_cfg_callable_clear_via_self_cycle():
    """CfgCallable_clear via a self-referential CfgCallable cycle.

    Runs in a subprocess: the module-level CfgCallables are rooted by the
    module dict, so this drops every external reference before collecting.
    """
    code = (
        "import gc\n"
        "import cfg._c as cmod\n"
        "import cfg as pkg\n"
        "cm_obj = cmod.cm\n"
        "cm_obj._self = cm_obj  # self-cycle via the instance dict\n"
        "for mod in (cmod, pkg):\n"
        "    for name in ('cm', 'cfg', 'if_', 'conditional_method', 'cfg_attr'):\n"
        "        delattr(mod, name)\n"
        "del cm_obj, cmod, pkg\n"
        "gc.collect()\n"
        "gc.collect()\n"
        "print('clear-cycle ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "clear-cycle ok" in proc.stdout


def test_cm_wrapper_null_self():
    """_cm_wrapper with self==NULL raises RuntimeError (closure-less path).

    Build a fresh PyCFunction from the same PyMethodDef with a NULL self by
    reading m_ml out of the existing module method.
    """
    import ctypes

    api = ctypes.pythonapi
    base = id(c._cm_wrapper)
    m_ml = ctypes.c_void_p.from_address(base + 2 * ctypes.sizeof(ctypes.c_void_p)).value

    # PyCFunction_New is not exported on CPython 3.9 (macro only); fall back
    # to the exported PyCFunction_NewEx (ml, self, module).
    if hasattr(api, "PyCFunction_NewEx"):
        new_fn = api.PyCFunction_NewEx
        new_fn.restype = ctypes.c_void_p
        new_fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        ptr = new_fn(ctypes.c_void_p(m_ml), None, None)
    else:
        new_fn = api.PyCFunction_New
        new_fn.restype = ctypes.c_void_p
        new_fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        ptr = new_fn(ctypes.c_void_p(m_ml), None)
    assert ptr
    fn = ctypes.cast(ptr, ctypes.py_object).value
    with pytest.raises(RuntimeError, match="No condition found"):
        fn(lambda: 1)


def test_raiser_surrogate_qualname():
    """_raise_typeerror with a surrogate qualname hits the AsUTF8 NULL branch."""
    raiser = c._raise_exec("\ud800")
    with pytest.raises(UnicodeEncodeError):
        raiser()


def test_debug_str_raises():
    """cfg.debug: PyObject_Str failing (obj __str__ raises) -> return NULL."""

    class S:
        def __str__(self):
            raise RuntimeError("boom-str")

    orig = os.environ.get("__conditional_method_debug__")
    os.environ["__conditional_method_debug__"] = "true"
    try:
        with pytest.raises(RuntimeError, match="boom-str"):
            c.debug(S())
    finally:
        if orig is None:
            os.environ.pop("__conditional_method_debug__", None)
        else:
            os.environ["__conditional_method_debug__"] = orig


def test_debug_surrogate():
    """cfg.debug with an unencodable object hits the AsUTF8 NULL branch."""

    class S:
        def __str__(self):
            return "\ud800"

    orig = os.environ.get("__conditional_method_debug__")
    os.environ["__conditional_method_debug__"] = "true"
    try:
        with pytest.raises(UnicodeEncodeError):
            c.debug(S())
    finally:
        if orig is None:
            os.environ.pop("__conditional_method_debug__", None)
        else:
            os.environ["__conditional_method_debug__"] = orig


def test_set_alloc_fail_count_bad_arg():
    """set_alloc_fail_count parse error."""
    with pytest.raises(TypeError):
        c.set_alloc_fail_count("x")


def test_debug_no_args():
    """cfg.debug() with no args -> SystemError from PyTuple_GetItem."""
    orig = os.environ.get("__conditional_method_debug__")
    os.environ["__conditional_method_debug__"] = "true"
    try:
        with pytest.raises(SystemError):
            c.debug()
    finally:
        if orig is None:
            os.environ.pop("__conditional_method_debug__", None)
        else:
            os.environ["__conditional_method_debug__"] = orig


def test_raise_exec_bad_args():
    """_raise_exec with too many positional args."""
    with pytest.raises(TypeError):
        c._raise_exec(1, 2)


def test_cm_wrapper_no_args():
    """_cm_wrapper() with no args."""
    with pytest.raises(TypeError):
        c._cm_wrapper()


def test_cm_two_positional():
    """cm(f, g) with two positional args."""
    with pytest.raises(TypeError):
        c.cm(lambda: 1, lambda: 1)


def test_cm_func_no_condition():
    """cm(f) without condition raises TypeError."""
    with pytest.raises(TypeError):
        c.cm(lambda: 1)


def test_cm_inner_one_arg():
    """_cm_inner with a single arg."""
    with pytest.raises(TypeError):
        c._cm_inner(1)


def test_cm_callable_cond_broken_bool():
    """cm callable condition returning an object with a raising __bool__."""

    class BrokenBool:
        def __bool__(self):
            raise RuntimeError("bb")

    with pytest.raises(RuntimeError, match="bb"):
        c.cm(lambda: 1, condition=lambda fn: BrokenBool())


def test_cfg_attr_wrapper_no_args():
    """cfg_attr_wrapper() with no args."""
    with pytest.raises(TypeError):
        c.cfg_attr_wrapper()


def test_cfg_attr_decorators_broken_len():
    """decorators whose __len__ raises -> PySequence_Length error."""

    class BrokenLen:
        def __len__(self):
            raise RuntimeError("len boom")

        def __getitem__(self, i):
            raise IndexError

    with pytest.raises(RuntimeError, match="len boom"):
        c.cfg_attr(lambda: 1, condition=True, decorators=BrokenLen())


def test_cfg_attr_decorators_broken_getitem():
    """decorators whose __getitem__ raises -> PySequence_GetItem error."""

    class BrokenGet:
        def __len__(self):
            return 1

        def __getitem__(self, i):
            raise RuntimeError("getitem boom")

    with pytest.raises(RuntimeError, match="getitem boom"):
        c.cfg_attr(lambda: 1, condition=True, decorators=BrokenGet())


def test_cfg_attr_unexpected_kwarg():
    """cfg_attr with an unexpected keyword."""
    with pytest.raises(TypeError):
        c.cfg_attr(foo=1)


def test_cfg_attr_callable_cond_broken_bool():
    """cfg_attr callable condition returning a broken-bool object."""

    class BrokenBool:
        def __bool__(self):
            raise RuntimeError("bb2")

    with pytest.raises(RuntimeError, match="bb2"):
        c.cfg_attr(lambda: 1, condition=lambda fn: BrokenBool(), decorators=[])


def test_cfg_attr_noncall_cond_broken_bool():
    """cfg_attr non-callable condition with broken __bool__."""

    class BrokenBool:
        def __bool__(self):
            raise RuntimeError("bb3")

    with pytest.raises(RuntimeError, match="bb3"):
        c.cfg_attr(lambda: 1, condition=BrokenBool(), decorators=[])


def test_cfg_attr_nonfunc_false():
    """cfg_attr false with an object that has no qualname."""
    with pytest.raises(TypeError):
        c.cfg_attr(42, condition=False)


def test_set_name_wrong_args():
    """TypeErrorRaiser.__set_name__ with one arg."""
    raiser = c._raise_exec("q")
    with pytest.raises(TypeError):
        raiser.__set_name__("x")
