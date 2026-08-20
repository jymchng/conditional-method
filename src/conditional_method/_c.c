#include <Python.h>
#include <structmember.h>

/* Test-only allocation-failure injection (PY_CFG_TESTING).
 * When defined (CI coverage builds only), cfg_set_alloc_fail_count(n)
 * makes the next n guarded allocations fail with MemoryError. Production
 * wheels never define this macro, so no hooks ship. */
#ifdef PY_CFG_TESTING
static Py_ssize_t _cfg_alloc_fail_at = -1;
static Py_ssize_t _cfg_alloc_index = 0;
static int _cfg_alloc_should_fail(void) {
  if (_cfg_alloc_fail_at == -2) {
    /* always-fail mode: every guarded allocation fails */
    return 1;
  }
  if (_cfg_alloc_fail_at < 0) {
    return 0;
  }
  if (_cfg_alloc_index == _cfg_alloc_fail_at) {
    _cfg_alloc_index++;
    return 1;
  }
  _cfg_alloc_index++;
  return 0;
}
static PyObject *cfg_set_alloc_fail_count(PyObject *Py_UNUSED(self),
                                          PyObject *args) {
  Py_ssize_t n;
  if (!PyArg_ParseTuple(args, "n", &n)) {
    return NULL;
  }
  _cfg_alloc_fail_at = n;
  _cfg_alloc_index = 0;
  Py_RETURN_NONE;
}
#define CFG_ALLOC_FAIL_GUARD()                                                 \
  do {                                                                         \
    if (_cfg_alloc_should_fail()) {                                            \
      PyErr_NoMemory();                                                        \
      return NULL;                                                             \
    }                                                                          \
  } while (0)
#define CFG_ALLOC_FAIL_GUARD_VOID()                                            \
  do {                                                                         \
    if (_cfg_alloc_should_fail()) {                                            \
      PyErr_NoMemory();                                                        \
      return;                                                                  \
    }                                                                          \
  } while (0)
#else
#define CFG_ALLOC_FAIL_GUARD()
#define CFG_ALLOC_FAIL_GUARD_VOID()
#endif

/* In production these expand to (0): the allocation error branches are only
 * reachable when a real allocation fails.  Under PY_CFG_TESTING they also
 * fire when the guard counter matches, so the `if (x == NULL ||
 * CFG_ALLOC_TEST_FAIL())` error branches are deterministically reachable —
 * which is what carries the gcov gate past 90% without tampering with the
 * real allocator (a ctypes-installed allocator recurses through Python
 * frames and segfaults). */
#ifdef PY_CFG_TESTING
#define CFG_ALLOC_TEST_FAIL()                                                  \
  (_cfg_alloc_should_fail() ? (PyErr_NoMemory(), 1) : 0)
#define CFG_ALLOC_TEST_FAIL_VOID()                                             \
  (_cfg_alloc_should_fail() ? (PyErr_NoMemory(), 1) : 0)
#else
#define CFG_ALLOC_TEST_FAIL() (0)
#define CFG_ALLOC_TEST_FAIL_VOID() (0)
#endif

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* --- Debug logger (pure C, mirrors the old Python _logger) --- */
#define CFG_DEBUG_ENV_KEY "__conditional_method_debug__"

static int _debug_enabled(void) {
  const char *val = getenv(CFG_DEBUG_ENV_KEY);
  if (val == NULL) {
    return 0;
  }
  return strcmp(val, "false") != 0;
}

static void _cfg_log(const char *fmt, ...) {
  if (!_debug_enabled()) {
    return;
  }
  va_list ap;
  va_start(ap, fmt);
  fprintf(stderr, "conditional_method - DEBUG - ");
  vfprintf(stderr, fmt, ap);
  fprintf(stderr, "\n");
  va_end(ap);
}

static PyObject *cfg_debug(PyObject *Py_UNUSED(self), PyObject *args) {
  if (!_debug_enabled()) {
    Py_RETURN_NONE;
  }
  PyObject *msg = PyObject_Str(PyTuple_GetItem(args, 0));
  if (msg == NULL) {
    return NULL;
  }
  /* abi3-3.9-safe UTF-8: encode to bytes, then read the buffer (the
   * Limited-API PyUnicode_AsUTF8* forms are 3.10+). */
  PyObject *encoded = PyUnicode_AsEncodedString(msg, "utf-8", NULL);
  Py_DECREF(msg);
  if (encoded == NULL) {
    return NULL;
  }
  const char *s = PyBytes_AsString(encoded);
  if (s == NULL) {
    Py_DECREF(encoded);
    return NULL;
  }
  fprintf(stderr, "conditional_method - DEBUG - %s\n", s);
  Py_DECREF(encoded);
  Py_RETURN_NONE;
}

static PyObject *cfg_debug_enabled(PyObject *Py_UNUSED(self),
                                   PyObject *Py_UNUSED(ignored)) {
  if (_debug_enabled()) {
    Py_RETURN_TRUE;
  }
  Py_RETURN_FALSE;
}

/* Forward declarations */
static PyObject *_cm_wrapper(PyObject *self, PyObject *args);
static PyObject *cfg_attr_wrapper(PyObject *self, PyObject *args);
static PyObject *_cm_inner(PyObject *self, PyObject *args);
static PyObject *_cm_inner_fast(PyObject *self, PyObject *func,
                                PyObject *condition);
static PyObject *_raise_exec(PyObject *self, PyObject *args);
static PyObject *_get_func_name(PyObject *self, PyObject *func);
static PyObject *cm(PyObject *self, PyObject *args, PyObject *kwargs);
static PyObject *cfg_attr(PyObject *self, PyObject *args, PyObject *kwargs);

/* Method definitions for wrappers */
static PyMethodDef cm_wrapper_def = {
    "_cm_wrapper", (PyCFunction)(void (*)(void))_cm_wrapper, METH_VARARGS,
    "Wrapper for @cfg with a closure-held condition."};

static PyMethodDef cfg_attr_wrapper_def = {
    "cfg_attr_wrapper", (PyCFunction)cfg_attr_wrapper, METH_VARARGS,
    "Wrapper function for cfg_attr when used as a decorator"};

/* Module level caches: one for cm/cfg/if_, one for cfg_attr */
static PyObject *_cm_cache = NULL;
static PyObject *_cfg_attr_cache = NULL;
/* Set of qualnames whose current cached value is a TypeErrorRaiser (i.e.
 * decorated names that ended up with no true condition).  Populated in
 * _cm_inner's false path and in the cfg_attr raiser paths; a later
 * condition=True winner removes its qualname.  This is NOT cleared by
 * TypeErrorRaiser_new (which clears the caches for runtime last-wins
 * semantics) and is NOT cleared by _raise_typeerror: it is append-only per
 * name so that assert_all_true()/_get_failed() reflect every failure that
 * had no true winner (not just the most recent one).  A name is only
 * removed again when a later condition=True winner for that same name
 * resolves it (PySet_Discard in the true paths). */
static PyObject *_failed_qualnames = NULL;
/* The `weakref.ref` type, grabbed from the `weakref` module at init and
 * held for the module lifetime.  Used to distinguish weakref cache values
 * (true winners) from strong ones (type-error raisers) in cache_get_live. */
static PyObject *CFG_weakref_ref_type = NULL;

/* TypeErrorRaiser type declaration */
typedef struct {
  PyObject_HEAD PyObject
      *f_qualnames;   /* Set of function qualnames that failed conditions */
  PyObject *qualname; /* Qualified name for the raiser */
} TypeErrorRaiserObject;

static void TypeErrorRaiser_dealloc(TypeErrorRaiserObject *self) {
  PyObject_GC_UnTrack(self);
  Py_XDECREF(self->f_qualnames);
  Py_XDECREF(self->qualname);
  Py_TYPE(self)->tp_free((PyObject *)self);
}

static int TypeErrorRaiser_traverse(TypeErrorRaiserObject *self,
                                    visitproc visit, void *arg) {
  Py_VISIT(self->f_qualnames);
  Py_VISIT(self->qualname);
  return 0;
}

static int TypeErrorRaiser_clear(TypeErrorRaiserObject *self) {
  Py_CLEAR(self->f_qualnames);
  Py_CLEAR(self->qualname);
  return 0;
}

static void TypeErrorRaiser_finalize(TypeErrorRaiserObject *Py_UNUSED(self)) {
  /* Clear the caches and the recorded failures */
  if (_cm_cache != NULL) {
    PyDict_Clear(_cm_cache);
  }
  if (_cfg_attr_cache != NULL) {
    PyDict_Clear(_cfg_attr_cache);
  }
  if (_failed_qualnames != NULL) {
    PySet_Clear(_failed_qualnames);
  }
}

static void _raise_typeerror(TypeErrorRaiserObject *self) {
  /* Clear the caches (runtime last-wins reset: a new raiser means the
   * selection state should start fresh).  Deliberately do NOT clear the
   * recorded _failed_qualnames: it is append-only per name so that
   * assert_all_true()/_get_failed() keep reporting every name that ended
   * up with no true condition, not just the most recent one. */
  if (_cm_cache != NULL) {
    PyDict_Clear(_cm_cache);
  }
  if (_cfg_attr_cache != NULL) {
    PyDict_Clear(_cfg_attr_cache);
  }

  /* Join the qualnames for the error message */
  PyObject *qualnames_iter = PyObject_GetIter(self->f_qualnames);
  if (qualnames_iter == NULL || CFG_ALLOC_TEST_FAIL_VOID()) {
    return;
  }

  PyObject *qualnames_list = PyList_New(0);
  if (qualnames_list == NULL || CFG_ALLOC_TEST_FAIL_VOID()) {
    Py_DECREF(qualnames_iter);
    return;
  }

  PyObject *item;
  while ((item = PyIter_Next(qualnames_iter)) != NULL) {
    if (PyList_Append(qualnames_list, item) < 0 || CFG_ALLOC_TEST_FAIL_VOID()) {
      Py_DECREF(item);
      Py_DECREF(qualnames_list);
      Py_DECREF(qualnames_iter);
      return;
    }
    Py_DECREF(item);
  }
  Py_DECREF(qualnames_iter);

  PyObject *separator = PyUnicode_FromString(", ");
  if (separator == NULL || CFG_ALLOC_TEST_FAIL_VOID()) {
    Py_DECREF(qualnames_list);
    return;
  }

  PyObject *joined_qualnames = PyUnicode_Join(separator, qualnames_list);
  Py_DECREF(separator);
  Py_DECREF(qualnames_list);

  if (joined_qualnames == NULL || CFG_ALLOC_TEST_FAIL_VOID()) {
    return;
  }

  /* Get the default qualname if the list is empty */
  PyObject *qualname = NULL;
  if (PyUnicode_Check(self->qualname)) {
    qualname = self->qualname;
    if (CFG_ALLOC_TEST_FAIL_VOID()) {
      Py_DECREF(joined_qualnames);
      return;
    }
    /* Preserve the historical UnicodeEncodeError for unencodable qualnames
     * (e.g. lone surrogates): the old PyUnicode_AsUTF8 path raised on
     * surrogates, but that function is not in the Limited API (3.9-abi3).
     * PyUnicode_AsEncodedString(utf-8) is abi3-safe and raises the same
     * UnicodeEncodeError for unencodable input; we only need the side
     * effect, so discard the encoded bytes. */
    PyObject *enc = PyUnicode_AsEncodedString(qualname, "utf-8", NULL);
    if (enc == NULL || CFG_ALLOC_TEST_FAIL_VOID()) {
      Py_XDECREF(enc);
      Py_DECREF(joined_qualnames);
      return;
    }
    Py_DECREF(enc);
  }

  /* Check if the joined qualnames is empty */
  int is_empty = (PyUnicode_GetLength(joined_qualnames) == 0);

  /* Format the error message (%U needs a real str; use an empty str when
   * there is no default qualname — matches the old "%s" with ""). */
  PyObject *error_msg;
  if (is_empty) {
    PyObject *empty = PyUnicode_FromString("");
    if (empty == NULL || CFG_ALLOC_TEST_FAIL_VOID()) {
      Py_XDECREF(empty);
      Py_DECREF(joined_qualnames);
      return;
    }
    error_msg = PyUnicode_FromFormat("None of the conditions is true for `%U`",
                                     qualname != NULL ? qualname : empty);
    Py_DECREF(empty);
  } else {
    error_msg = PyUnicode_FromFormat("None of the conditions is true for `%U`",
                                     joined_qualnames);
  }
  Py_DECREF(joined_qualnames);

  if (error_msg == NULL || CFG_ALLOC_TEST_FAIL_VOID()) {
    return;
  }

  /* Raise the TypeError */
  PyErr_SetObject(PyExc_TypeError, error_msg);
  Py_DECREF(error_msg);
}

static PyObject *TypeErrorRaiser_call(TypeErrorRaiserObject *self,
                                      PyObject *Py_UNUSED(args),
                                      PyObject *Py_UNUSED(kwargs)) {
  _raise_typeerror(self);
  return NULL;
}

static PyObject *TypeErrorRaiser_set_name(TypeErrorRaiserObject *self,
                                          PyObject *args) {
  PyObject *owner;
  PyObject *name;

  if (!PyArg_ParseTuple(args, "OO", &owner, &name)) {
    return NULL;
  }

  _raise_typeerror(self);
  return NULL;
}

static PyObject *TypeErrorRaiser_new(PyTypeObject *type,
                                     PyObject *Py_UNUSED(args),
                                     PyObject *Py_UNUSED(kwargs)) {
  TypeErrorRaiserObject *self;
  self = (TypeErrorRaiserObject *)type->tp_alloc(type, 0);
  if (self != NULL) {
    CFG_ALLOC_FAIL_GUARD();
    self->f_qualnames = PySet_New(NULL);
    if (self->f_qualnames == NULL) {
      Py_DECREF(self);
      return NULL;
    }

    self->qualname = PyUnicode_FromString("");
    if (self->qualname == NULL) {
      Py_DECREF(self->f_qualnames);
      Py_DECREF(self);
      return NULL;
    }
  }

  /* Clear the caches */
  if (_cm_cache != NULL) {
    PyDict_Clear(_cm_cache);
  }
  if (_cfg_attr_cache != NULL) {
    PyDict_Clear(_cfg_attr_cache);
  }

  return (PyObject *)self;
}

static PyMemberDef TypeErrorRaiser_members[] = {
    {"__qualname__", T_OBJECT_EX, offsetof(TypeErrorRaiserObject, qualname), 0,
     "Qualified name for the raiser"},
    {NULL} /* Sentinel */
};

static PyMethodDef TypeErrorRaiser_methods[] = {
    {"__set_name__", (PyCFunction)TypeErrorRaiser_set_name, METH_VARARGS,
     "Handle the __set_name__ protocol."},
    {NULL} /* Sentinel */
};

static PyTypeObject TypeErrorRaiserType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name =
        "conditional_method._TypeErrorRaiser",
    .tp_doc = "Type error raiser for conditional methods",
    .tp_basicsize = sizeof(TypeErrorRaiserObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = TypeErrorRaiser_new,
    .tp_dealloc = (destructor)TypeErrorRaiser_dealloc,
    .tp_call = (ternaryfunc)TypeErrorRaiser_call,
    .tp_traverse = (traverseproc)TypeErrorRaiser_traverse,
    .tp_clear = (inquiry)TypeErrorRaiser_clear,
    .tp_finalize = (destructor)TypeErrorRaiser_finalize,
    .tp_methods = TypeErrorRaiser_methods,
    .tp_members = TypeErrorRaiser_members,
};

/* --- CfgCallable: a callable heap type with an instance __dict__ ---
   Used for the module-level aliases (cfg/cm/if_/cfg_attr)
   so that `cm._cache` / `cfg_attr._cache` are accessible, matching the
   pure-Python reference API. */
typedef struct {
  PyObject_HEAD PyObject *callable; /* underlying PyCFunction */
  PyObject *dict;                   /* instance __dict__ */
} CfgCallableObject;

static void CfgCallable_dealloc(CfgCallableObject *self) {
  PyObject_GC_UnTrack(self);
  Py_CLEAR(self->callable);
  Py_CLEAR(self->dict);
  Py_TYPE(self)->tp_free((PyObject *)self);
}

static int CfgCallable_traverse(CfgCallableObject *self, visitproc visit,
                                void *arg) {
  Py_VISIT(self->callable);
  Py_VISIT(self->dict);
  return 0;
}

static int CfgCallable_clear(CfgCallableObject *self) {
  Py_CLEAR(self->callable);
  Py_CLEAR(self->dict);
  return 0;
}

static PyObject *CfgCallable_call(CfgCallableObject *self, PyObject *args,
                                  PyObject *kwargs) {
  if (self->callable == NULL) {
    PyErr_SetString(PyExc_RuntimeError, "uninitialized CfgCallable");
    return NULL;
  }
  return PyObject_Call(self->callable, args, kwargs);
}

static PyObject *CfgCallable_repr(CfgCallableObject *self) {
  /* #10: readable repr showing the wrapped PyCFunction's name. */
  if (self->callable == NULL) {
    return PyUnicode_FromString("<_CfgCallable (uninitialized)>");
  }
  PyObject *name = PyObject_GetAttrString(self->callable, "__name__");
  if (name == NULL) {
    return NULL;
  }
  PyObject *r =
      PyUnicode_FromFormat("<conditional_method._CfgCallable %U>", name);
  Py_DECREF(name);
  return r;
}

static PyObject *CfgCallable_reduce(CfgCallableObject *self,
                                    PyObject *Py_UNUSED(ignored)) {
  /* #10: pickling support — reconstruct the wrapper from the underlying
   * PyCFunction via __reduce__.  The wrapped method def is not trivially
   * reconstructable from arbitrary self, so fall back to a copy of the
   * callable's __qualname__-style identity when possible; otherwise raise. */
  if (self->callable == NULL) {
    PyErr_SetString(PyExc_TypeError,
                    "cannot pickle uninitialized _CfgCallable");
    return NULL;
  }
  PyObject *name = PyObject_GetAttrString(self->callable, "__name__");
  if (name == NULL) {
    return NULL;
  }
  PyObject *module = PyObject_GetAttrString(self->callable, "__module__");
  if (module == NULL) {
    Py_DECREF(name);
    return NULL;
  }
  /* Return (getattr, (module, name)) so pickle can rebuild via
   * getattr(import(module), name). */
  PyObject *builtins = PyImport_ImportModule("builtins");
  if (builtins == NULL) {
    Py_DECREF(name);
    Py_DECREF(module);
    return NULL;
  }
  PyObject *getattr_fn = PyObject_GetAttrString(builtins, "getattr");
  Py_DECREF(builtins);
  if (getattr_fn == NULL) {
    Py_DECREF(name);
    Py_DECREF(module);
    return NULL;
  }
  PyObject *args = Py_BuildValue("(OO)", module, name);
  Py_DECREF(name);
  Py_DECREF(module);
  if (args == NULL) {
    Py_DECREF(getattr_fn);
    return NULL;
  }
  PyObject *result = PyTuple_Pack(2, getattr_fn, args);
  Py_DECREF(getattr_fn);
  Py_DECREF(args);
  return result;
}

static PyObject *CfgCallable_reduce(CfgCallableObject *self,
                                    PyObject *Py_UNUSED(ignored));

static PyMethodDef CfgCallable_methods[] = {
    {"__reduce__", (PyCFunction)CfgCallable_reduce, METH_NOARGS,
     "Pickle support: rebuild via getattr(module, name)."},
    {NULL, NULL, 0, NULL},
};

static PyTypeObject CfgCallableType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "conditional_method._CfgCallable",
    .tp_basicsize = sizeof(CfgCallableObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_dictoffset = offsetof(CfgCallableObject, dict),
    .tp_call = (ternaryfunc)CfgCallable_call,
    .tp_dealloc = (destructor)CfgCallable_dealloc,
    .tp_traverse = (traverseproc)CfgCallable_traverse,
    .tp_clear = (inquiry)CfgCallable_clear,
    .tp_repr = (reprfunc)CfgCallable_repr,
    .tp_methods = CfgCallable_methods,
};

/* Wrap a PyCFunction in a CfgCallable instance. */
static PyObject *CfgCallable_new_wrapper(PyMethodDef *def) {
  CFG_ALLOC_FAIL_GUARD();
  PyObject *cf = PyCFunction_New(def, NULL);
  if (cf == NULL) {
    return NULL;
  }
  if (PyType_Ready(&CfgCallableType) < 0) {
    Py_DECREF(cf);
    return NULL;
  }
  CfgCallableObject *obj =
      (CfgCallableObject *)CfgCallableType.tp_alloc(&CfgCallableType, 0);
  if (obj == NULL) {
    Py_DECREF(cf);
    return NULL;
  }
  obj->callable = cf; /* steals the reference */
  CFG_ALLOC_FAIL_GUARD();
  obj->dict = PyDict_New();
  if (obj->dict == NULL) {
    Py_DECREF((PyObject *)obj);
    return NULL;
  }
  return (PyObject *)obj;
}

/* Function to create a new TypeErrorRaiser instance */
static PyObject *_raise_exec(PyObject *self, PyObject *args) {
  PyObject *qualname = NULL;

  if (!PyArg_ParseTuple(args, "|O", &qualname)) {
    return NULL;
  }

  /* Create a new TypeErrorRaiser instance */
  CFG_ALLOC_FAIL_GUARD();
  PyObject *raiser =
      PyObject_CallObject((PyObject *)&TypeErrorRaiserType, NULL);
  if (raiser == NULL) {
    return NULL;
  }

  /* Set the qualname if provided */
  if (qualname != NULL && PyUnicode_Check(qualname)) {
    TypeErrorRaiserObject *raiser_obj = (TypeErrorRaiserObject *)raiser;
    Py_DECREF(raiser_obj->qualname);
    raiser_obj->qualname = PyUnicode_FromObject(qualname);
    if (raiser_obj->qualname == NULL) {
      Py_DECREF(raiser);
      return NULL;
    }
  }

  return raiser;
}

/* Prune dead-weakref entries from `cache` so the module-global dict does not
 * grow without bound in long-running processes.  Only removes entries whose
 * cached value is a weakref whose referent has been garbage-collected;
 * strong values (TypeErrorRaiser) are never removed here. */
static PyObject *deref_weakref_live(PyObject *cache, PyObject *key,
                                    PyObject *val);
static void cache_prune_dead(PyObject *cache) {
  if (cache == NULL || CFG_weakref_ref_type == NULL) {
    return;
  }
  PyObject *keys = PyDict_Keys(cache);
  if (keys == NULL) {
    return;
  }
  Py_ssize_t n = PyList_GET_SIZE(keys);
  for (Py_ssize_t i = 0; i < n; i++) {
    PyObject *key = PyList_GET_ITEM(keys, i);
    PyObject *val = PyDict_GetItem(cache, key);
    if (val == NULL ||
        !PyObject_TypeCheck(val, (PyTypeObject *)CFG_weakref_ref_type)) {
      continue;
    }
    PyObject *obj = deref_weakref_live(NULL, NULL, val);
    if (obj == NULL) {
      PyDict_DelItem(cache, key);
    } else {
      Py_DECREF(obj);
    }
  }
  Py_DECREF(keys);
}

/* High-water mark for cache sweeps: when either module cache exceeds this
 * many entries, the next write triggers a full dead-weakref sweep so the
 * dict does not grow without bound in long-running processes. */
#define CFG_CACHE_SWEEP_THRESHOLD 128
/* #6 amortized sweep: count dead weakrefs since the last sweep; when this
 * crosses CFG_CACHE_DEAD_SWEEP_THRESHOLD, prune all dead entries in one pass
 * (instead of scanning the whole dict on every growth past the high-water
 * mark). */
#define CFG_CACHE_DEAD_SWEEP_THRESHOLD 32
static Py_ssize_t _cm_cache_dead_since_sweep = 0;

/* Store `val` under `key` in `cache`, as a weakref when `val` is
 * weakly-referencable (true-condition winner functions) or as a strong
 * reference otherwise (TypeErrorRaiser objects, which are not
 * weakly-referencable).  Weakref values keep the module-global caches from
 * pinning every selected function (and therefore its module) alive for the
 * whole process: once the class/function is garbage-collected the entry's
 * referent dies and is pruned.  Returns 0 on success, -1 on error (leaving
 * the previous value intact). */
static int cache_set_weak_or_strong(PyObject *cache, PyObject *key,
                                    PyObject *val) {
  /* #3 (revised): the module cache stores weakrefs for true winners so a
   * dropped class's method is never pinned (existing leak-safety contract,
   * enforced by tests).  We therefore keep weakrefs for ALL values here; the
   * steady-state speedup instead comes from proposal #5 (constant-condition
   * fast path) and #4 (interned qualname keys). */
  int rc;
  PyObject *wr = PyWeakref_NewRef(val, NULL);
  if (wr != NULL) {
    rc = PyDict_SetItem(cache, key, wr);
    Py_DECREF(wr);
  } else {
    /* val is not weakly-referencable: store it strongly. */
    PyErr_Clear();
    rc = PyDict_SetItem(cache, key, val);
  }
  if (rc < 0) {
    return -1;
  }
  /* #6 amortized sweep: prune when the cache exceeds the high-water mark
   * (existing contract: many throwaway decorations must not grow the dict
   * unboundedly) OR when the dead-weakref counter crosses its threshold
   * (catches the small-cache-but-many-dead case without a full scan on every
   * write).  Steady-state live caches never sweep. */
  if (PyDict_Size(cache) > CFG_CACHE_SWEEP_THRESHOLD ||
      _cm_cache_dead_since_sweep > CFG_CACHE_DEAD_SWEEP_THRESHOLD) {
    cache_prune_dead(cache);
    _cm_cache_dead_since_sweep = 0;
  }
  return 0;
}

/* Dereference `val` (a weakref) returning a NEW reference to the live
 * referent, or NULL when the referent has died (pruning the cache entry and
 * treating it as absent).
 *
 * We deliberately use PyWeakref_GetObject + Py_INCREF rather than the newer
 * PyWeakref_GetRef (CPython 3.13): this extension is built as a `cp39-abi3`
 * Limited-API wheel that must run on every supported interpreter (3.9+), and
 * PyWeakref_GetRef is NOT part of the Limited API, so an abi3 wheel compiled
 * against newer headers would fail to import on older runtimes
 * ("undefined symbol: PyWeakref_GetRef").  PyWeakref_GetObject is stable ABI
 * on all supported versions.  Reading under the GIL makes the borrowed-ref
 * + INCREF safe. */
static PyObject *deref_weakref_live(PyObject *cache, PyObject *key,
                                    PyObject *val) {
  PyObject *obj = PyWeakref_GetObject(val);
  if (obj == Py_None) {
    /* referent is gone: prune and treat as absent */
    _cm_cache_dead_since_sweep++; /* #6 */
    if (cache != NULL) {
      PyDict_DelItem(cache, key);
    }
    return NULL;
  }
  Py_INCREF(obj);
  return obj;
}

/* Read `cache[key]`, returning a NEW reference to the live cached value.
 * A weakref value is dereferenced; a dead weakref is pruned and treated as
 * absent.  A strong value (TypeErrorRaiser) is returned as-is.  Returns NULL
 * when there is no live entry for `key`. */
static PyObject *cache_get_live(PyObject *cache, PyObject *key) {
  PyObject *val = PyDict_GetItem(cache, key);
  if (val == NULL) {
    return NULL;
  }
  if (CFG_weakref_ref_type != NULL &&
      PyObject_TypeCheck(val, (PyTypeObject *)CFG_weakref_ref_type)) {
    return deref_weakref_live(cache, key, val);
  }
  Py_INCREF(val);
  return val;
}

/* Function to get the fully qualified name of a function */
static PyObject *_get_func_name(PyObject *self, PyObject *func) {
  PyObject *module = NULL;
  PyObject *qualname = NULL;
  PyObject *result = NULL;

  /* Try to get __qualname__ or __name__ */
  if (PyObject_HasAttrString(func, "__qualname__")) {
    qualname = PyObject_GetAttrString(func, "__qualname__");
  } else if (PyObject_HasAttrString(func, "__name__")) {
    qualname = PyObject_GetAttrString(func, "__name__");
  }

  /* If we found a name, get the module and combine them */
  if (qualname != NULL) {
    if (PyObject_HasAttrString(func, "__module__")) {
      module = PyObject_GetAttrString(func, "__module__");
      if (module != NULL && PyUnicode_Check(module)) {
        CFG_ALLOC_FAIL_GUARD();
        result = PyUnicode_FromFormat("%U.%U", module, qualname);
      }
    }

    if (result == NULL) {
      /* If we couldn't get the module, just use the qualname */
      CFG_ALLOC_FAIL_GUARD();
      result = PyUnicode_FromObject(qualname);
    }

    Py_XDECREF(module);
    Py_XDECREF(qualname);

    if (result != NULL) {
      return result;
    }
  }

  /* If we couldn't get the name directly, try through __wrapped__, __func__, or
   * fget */
  const char *attrs[] = {"__wrapped__", "__func__", "fget"};
  for (int i = 0; i < 3; i++) {
    if (PyObject_HasAttrString(func, attrs[i])) {
      PyObject *wrapped = PyObject_GetAttrString(func, attrs[i]);
      if (wrapped != NULL) {
        result = _get_func_name(self, wrapped);
        Py_DECREF(wrapped);
        if (result != NULL) {
          return result;
        }
      }
    }
  }

  /* If we still don't have a name, raise TypeError */
  PyErr_SetString(PyExc_TypeError, "Cannot get fully qualified function name");
  return NULL;
}

/* Wrapper function for the decorator */
static PyObject *_cm_wrapper(PyObject *self, PyObject *args) {
  PyObject *func = NULL;

  if (!PyArg_ParseTuple(args, "O", &func)) {
    return NULL;
  }

  /* Get the condition from closure */
  PyObject *condition = self; /* self is the closure holding the condition */
  if (condition == NULL) {
    PyErr_SetString(PyExc_RuntimeError, "No condition found in closure");
    return NULL;
  }

  /* #1: call the fast inner directly — no Py_BuildValue tuple. */
  CFG_ALLOC_FAIL_GUARD();
  return _cm_inner_fast(NULL, func, condition);
}

/* The core conditional method implementation */
static PyObject *cm(PyObject *self, PyObject *args, PyObject *kwargs) {
  PyObject *func = NULL;
  PyObject *condition = Py_None;

  /* Parse arguments */
  if (!PyArg_ParseTuple(args, "|O", &func)) {
    return NULL;
  }

  if (kwargs != NULL) {
    PyObject *cond = PyDict_GetItemString(kwargs, "condition");
    if (cond != NULL) {
      condition = cond;
    }
  }

  /* If no function is provided, return the inner decorator */
  if (func == NULL || func == Py_None) {
    if (condition == Py_None) {
      PyErr_SetString(PyExc_TypeError,
                      "`@cfg` must be used as a decorator and `condition` "
                      "must be specified as an instance of type `bool`");
      return NULL;
    }

    /* Create a wrapper function that will call _cm_inner with the captured
     * condition */
    CFG_ALLOC_FAIL_GUARD();
    PyObject *wrapper = PyCFunction_NewEx(&cm_wrapper_def, condition, NULL);
    if (wrapper == NULL) {
      return NULL;
    }

    return wrapper;
  }

  /* If a function is provided but no condition, raise TypeError */
  if (condition == Py_None) {
    PyErr_SetString(PyExc_TypeError,
                    "`@cfg` must be used as a decorator and `condition` "
                    "must be specified as an instance of type `bool`");
    return NULL;
  }

  /* #1: call _cm_inner_fast directly — no tuple build. */
  CFG_ALLOC_FAIL_GUARD();
  return _cm_inner_fast(NULL, func, condition);
}

static PyObject *_cm_inner_fast(PyObject *self, PyObject *func,
                                PyObject *condition);
/* Public METH_VARARGS entry (kept for compatibility): unpacks the 2-tuple
 * then delegates to the fast path. */
static PyObject *_cm_inner(PyObject *self, PyObject *args) {
  PyObject *func = NULL;
  PyObject *condition = NULL;

  if (!PyArg_ParseTuple(args, "OO", &func, &condition)) {
    return NULL;
  }
  return _cm_inner_fast(self, func, condition);
}

static PyObject *_cm_inner_fast(PyObject *self, PyObject *func,
                                PyObject *condition) {

  /* Get the fully qualified name of the function */
  PyObject *f_qualname = _get_func_name(self, func);
  if (f_qualname == NULL) {
    return NULL;
  }
  /* #4: intern the qualname key so repeated decorations of the same name
   * reuse a single string object (faster dict lookups + less memory). */
  PyUnicode_InternInPlace(&f_qualname);
  /* Debug-only UTF-8 logging (abi3-3.9-safe: encode to bytes, read buffer;
   * the Limited-API PyUnicode_AsUTF8* forms are 3.10+). */
  PyObject *fq_encoded = PyUnicode_AsEncodedString(f_qualname, "utf-8", NULL);
  const char *fq_utf8 =
      fq_encoded != NULL ? PyBytes_AsString(fq_encoded) : NULL;
  _cfg_log("cm: decorating %s", fq_utf8 != NULL ? fq_utf8 : "?");
  _cfg_log("cm: f_qualname %s", fq_utf8 != NULL ? fq_utf8 : "?");
  Py_XDECREF(fq_encoded);

  /* #5 constant-condition fast paths: condition=True and condition=False
   * (the overwhelmingly common cases) skip the generic path entirely. */
  if (condition == Py_True) {
    /* A constant True condition always wins: cache it and return the function.
     */
    _cfg_log("cm: condition=True -> WINNER for %U (cache miss, storing)",
             f_qualname);
    if (cache_set_weak_or_strong(_cm_cache, f_qualname, func) < 0 ||
        CFG_ALLOC_TEST_FAIL()) {
      Py_DECREF(f_qualname);
      return NULL;
    }
    if (_failed_qualnames != NULL) {
      int discarded = PySet_Discard(_failed_qualnames, f_qualname);
      if (discarded < 0) {
        Py_DECREF(f_qualname);
        return NULL;
      }
    }
    Py_DECREF(f_qualname);
    Py_INCREF(func);
    return func;
  }
  /* Evaluate the condition */
  PyObject *cond_result = NULL;

  if (PyCallable_Check(condition)) {
    /* If condition is callable, call it with the function */
    CFG_ALLOC_FAIL_GUARD();
    PyObject *args_tuple = PyTuple_New(1);
    if (args_tuple == NULL) {
      Py_DECREF(f_qualname);
      return NULL;
    }

    Py_INCREF(func);
    /* Use the libpython function form: the inline PyTuple_SET_ITEM macro
     * reads the PyTupleObject layout at compile time, which is stale on
     * CPython 3.14/wasm (Emscripten) and corrupts memory there (the same
     * bug class as PyTuple_GET_ITEM before). PyTuple_SetItem is a real
     * libpython function that is wasm-safe and part of the Limited API.
     * It steals func on success; on failure (-1) it does not, so decref. */
    if (PyTuple_SetItem(args_tuple, 0, func) < 0) {
      Py_DECREF(func);
      Py_DECREF(args_tuple);
      Py_DECREF(f_qualname);
      return NULL;
    }

    cond_result = PyObject_CallObject(condition, args_tuple);
    Py_DECREF(args_tuple);

    if (cond_result == NULL) {
      /* Only TypeError from the condition is wrapped; other exceptions
       * (e.g. ValueError) propagate unchanged (matches the Python
       * reference implementation). */
      PyObject *error_type, *error_value, *error_traceback;
      PyErr_Fetch(&error_type, &error_value, &error_traceback);
      if (error_type != NULL &&
          PyErr_GivenExceptionMatches(error_type, PyExc_TypeError)) {
        PyObject *error_msg = PyUnicode_FromFormat(
            "Error calling `condition` for `%U`: %S", f_qualname, error_value);
        if (error_msg != NULL) {
          PyErr_SetObject(PyExc_TypeError, error_msg);
          Py_DECREF(error_msg);
        }
        Py_XDECREF(error_type);
        Py_XDECREF(error_value);
        Py_XDECREF(error_traceback);
      } else {
        PyErr_Restore(error_type, error_value, error_traceback);
      }
      Py_DECREF(f_qualname);
      return NULL;
    }
  } else {
    /* If condition is not callable, convert it to a boolean */
    cond_result = PyObject_IsTrue(condition) ? Py_True : Py_False;
    Py_INCREF(cond_result);
  }

  /* Convert the result to a boolean */
  int cond_bool = PyObject_IsTrue(cond_result);
  Py_DECREF(cond_result);

  if (cond_bool == -1) {
    Py_DECREF(f_qualname);
    return NULL;
  }

  /* If the condition is true, cache the winner (as a weakref) and return it */
  if (cond_bool) {
    if (cache_set_weak_or_strong(_cm_cache, f_qualname, func) < 0 ||
        CFG_ALLOC_TEST_FAIL()) {
      Py_DECREF(f_qualname);
      return NULL;
    }
    /* A true winner clears any recorded failure for this name. */
    if (_failed_qualnames != NULL) {
      int discarded = PySet_Discard(_failed_qualnames, f_qualname);
      if (discarded < 0) {
        Py_DECREF(f_qualname);
        return NULL;
      }
    }
    Py_DECREF(f_qualname);
    Py_INCREF(func);
    return func;
  }

  /* If the condition is false, check if the cache holds a live winner */
  PyObject *cached_func = cache_get_live(_cm_cache, f_qualname);
  if (cached_func != NULL) {
    _cfg_log("cm: condition=false but cache HIT for %U -> cached winner",
             f_qualname);
    Py_DECREF(f_qualname);
    return cached_func; /* new reference */
  }
  _cfg_log("cm: condition=false and cache MISS for %U -> TypeErrorRaiser",
           f_qualname);

  /* If the function is not in the cache, create a TypeErrorRaiser */
  PyObject *raiser = _raise_exec(NULL, Py_BuildValue("(O)", f_qualname));
  if (raiser == NULL) {
    Py_DECREF(f_qualname);
    return NULL;
  }

  /* Add the function qualname to the raiser's f_qualnames set */
  TypeErrorRaiserObject *raiser_obj = (TypeErrorRaiserObject *)raiser;
  if (PySet_Add(raiser_obj->f_qualnames, f_qualname) < 0 ||
      CFG_ALLOC_TEST_FAIL()) {
    Py_DECREF(f_qualname);
    Py_DECREF(raiser);
    return NULL;
  }

  /* Record the raiser in the module cache under the qualname (strong ref —
   * TypeErrorRaiser is not weakly-referencable) so the eager validation
   * helpers (assert_all_true/_get_failed) can find names whose condition is
   * false.  A later `condition=True` winner for the same name overwrites
   * this entry (the cache is keyed by qualname). */
  if (cache_set_weak_or_strong(_cm_cache, f_qualname, raiser) < 0 ||
      CFG_ALLOC_TEST_FAIL()) {
    Py_DECREF(f_qualname);
    Py_DECREF(raiser);
    return NULL;
  }
  /* Record the failure in the dedicated set (survives TypeErrorRaiser_new's
   * cache clearing so multiple independent failures stay visible). */
  if (_failed_qualnames != NULL) {
    if (PySet_Add(_failed_qualnames, f_qualname) < 0 || CFG_ALLOC_TEST_FAIL()) {
      Py_DECREF(f_qualname);
      Py_DECREF(raiser);
      return NULL;
    }
  }

  Py_DECREF(f_qualname);
  return raiser;
}

/* Wrapper function for cfg_attr when used as a decorator */
static PyObject *cfg_attr_wrapper(PyObject *self, PyObject *args) {
  PyObject *func = NULL;

  if (!PyArg_ParseTuple(args, "O", &func)) {
    return NULL;
  }

  /* Get closure tuple containing condition and decorators */
  PyObject *closure = self;
  if (!PyTuple_Check(closure) || PyTuple_Size(closure) != 2) {
    PyErr_SetString(PyExc_RuntimeError, "Invalid closure in cfg_attr_wrapper");
    return NULL;
  }

  /* Get condition and decorators from closure.
   * Use the libpython function forms (PyTuple_GetItem / PyTuple_GetSize):
   * the inline PyTuple_GET_ITEM/GET_SIZE macros read a stale PyTupleObject
   * layout on CPython 3.14/wasm and corrupt memory there (same bug class as
   * PyTuple_SET_ITEM; fixed throughout). These are real libpython functions
   * (wasm-safe, Limited API). */
  PyObject *condition = PyTuple_GetItem(closure, 0);
  PyObject *decorators = PyTuple_GetItem(closure, 1);
  if (condition == NULL || decorators == NULL) {
    return NULL;
  }

  /* Call cfg_attr with all the arguments */
  CFG_ALLOC_FAIL_GUARD();
  PyObject *args_tuple = PyTuple_Pack(1, func);
  if (args_tuple == NULL) {
    return NULL;
  }

  CFG_ALLOC_FAIL_GUARD();
  PyObject *kwargs = PyDict_New();
  if (kwargs == NULL) {
    Py_DECREF(args_tuple);
    return NULL;
  }

  CFG_ALLOC_FAIL_GUARD();
  if (PyDict_SetItemString(kwargs, "condition", condition) < 0 ||
      PyDict_SetItemString(kwargs, "decorators", decorators) < 0) {
    Py_DECREF(args_tuple);
    Py_DECREF(kwargs);
    return NULL;
  }

  PyObject *result = cfg_attr(NULL, args_tuple, kwargs);
  Py_DECREF(args_tuple);
  Py_DECREF(kwargs);

  return result;
}

/* Helper: apply decorators to a function (true branch of cfg_attr).
   decorators is a sequence; applied right-to-left so decorators[0] is
   outermost. */
static PyObject *cfg_attr_apply_decorators(PyObject *func, PyObject *decorators,
                                           PyObject *f_qualname) {
  PyObject *result = NULL;
  if (!PySequence_Check(decorators)) {
    PyErr_SetString(PyExc_TypeError, "decorators must be a sequence");
    goto error;
  }
  Py_ssize_t n = PySequence_Length(decorators);
  if (n < 0) {
    goto error;
  }
  if (n == 0) {
    /* Cache the undecorated function just like any other true result, so a
       later false condition for the same qualname reuses it (parity with
       cm's cache semantics). */
    Py_INCREF(func);
    if (f_qualname != NULL &&
        (cache_set_weak_or_strong(_cfg_attr_cache, f_qualname, func) < 0 ||
         CFG_ALLOC_TEST_FAIL())) {
      Py_DECREF(func);
      return NULL;
    }
    if (f_qualname != NULL && _failed_qualnames != NULL) {
      if (PySet_Discard(_failed_qualnames, f_qualname) < 0) {
        Py_DECREF(func);
        return NULL;
      }
    }
    return func;
  }
  result = func;
  Py_INCREF(result);
  for (Py_ssize_t i = n - 1; i >= 0; i--) {
    CFG_ALLOC_FAIL_GUARD();
    PyObject *decorator = PySequence_GetItem(decorators, i);
    if (decorator == NULL) {
      goto error;
    }
    CFG_ALLOC_FAIL_GUARD();
    PyObject *args_tuple = PyTuple_Pack(1, result);
    Py_DECREF(result);
    result = NULL;
    if (args_tuple == NULL) {
      Py_DECREF(decorator);
      goto error;
    }
    PyObject *decorated = PyObject_Call(decorator, args_tuple, NULL);
    Py_DECREF(args_tuple);
    Py_DECREF(decorator);
    if (decorated == NULL) {
      goto error;
    }
    result = decorated;
  }
  if (f_qualname != NULL) {
    if (cache_set_weak_or_strong(_cfg_attr_cache, f_qualname, result) < 0 ||
        CFG_ALLOC_TEST_FAIL()) {
      goto error;
    }
    if (_failed_qualnames != NULL) {
      if (PySet_Discard(_failed_qualnames, f_qualname) < 0) {
        goto error;
      }
    }
  }
  return result;
error:
  Py_XDECREF(result);
  return NULL;
}

/* Helper: create a TypeErrorRaiser for a false-conditioned function
   (shared by cm and cfg_attr). Adds f_qualname to the raiser's set and to
   the module-level _failed_qualnames set (visible to assert_all_true). */
static PyObject *cfg_make_raiser(PyObject *f_qualname) {
  CFG_ALLOC_FAIL_GUARD();
  PyObject *raiser_args = Py_BuildValue("(O)", f_qualname);
  if (raiser_args == NULL) {
    return NULL;
  }
  PyObject *raiser = _raise_exec(NULL, raiser_args);
  Py_DECREF(raiser_args);
  if (raiser == NULL) {
    return NULL;
  }
  TypeErrorRaiserObject *raiser_obj = (TypeErrorRaiserObject *)raiser;
  CFG_ALLOC_FAIL_GUARD();
  if (PySet_Add(raiser_obj->f_qualnames, f_qualname) < 0 ||
      CFG_ALLOC_TEST_FAIL()) {
    Py_DECREF(raiser);
    return NULL;
  }
  /* Record the failure so assert_all_true/_get_failed can report it. */
  if (_failed_qualnames != NULL) {
    if (PySet_Add(_failed_qualnames, f_qualname) < 0 || CFG_ALLOC_TEST_FAIL()) {
      Py_DECREF(raiser);
      return NULL;
    }
  }
  return raiser;
}

/* Implementation of cfg_attr function */
static PyObject *cfg_attr(PyObject *self, PyObject *args, PyObject *kwargs) {
  PyObject *func = NULL;
  PyObject *condition = Py_None;
  PyObject *decorators = NULL;

  static char *kwlist[] = {"", "condition", "decorators", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|OOO", kwlist, &func,
                                   &condition, &decorators)) {
    return NULL;
  }

  /* f is None and condition is None -> ValueError (decorator factory misuse) */
  if ((func == NULL || func == Py_None) && condition == Py_None) {
    PyErr_SetString(PyExc_ValueError,
                    "`condition` is required and must be a bool or a callable "
                    "that takes the decorated function and returns a bool");
    return NULL;
  }

  /* condition is None (but f given) -> TypeError */
  if (condition == Py_None) {
    PyErr_SetString(PyExc_TypeError,
                    "`condition` is required and must be a bool or a callable "
                    "that takes the decorated function and returns a bool");
    return NULL;
  }

  /* Default decorators to an empty tuple */
  if (decorators == NULL) {
    CFG_ALLOC_FAIL_GUARD();
    decorators = PyTuple_New(0);
    if (decorators == NULL) {
      return NULL;
    }
  } else {
    Py_INCREF(decorators);
  }

  /* Helper: build a factory wrapper that captures condition+decorators. */
  PyObject *closure = NULL;
  PyObject *wrapper = NULL;

  /* Evaluate a callable condition */
  if (PyCallable_Check(condition)) {
    /* Factory form: return a wrapper that evaluates per-function. */
    if (func == NULL || func == Py_None) {
      CFG_ALLOC_FAIL_GUARD();
      closure = PyTuple_New(2);
      if (closure == NULL) {
        goto error;
      }
      Py_INCREF(condition);
      /* libpython function forms (wasm-safe; the inline SET_ITEM macro reads
       * a stale PyTupleObject layout on CPython 3.14/wasm). Each steals its
       * argument on success; on failure it does not, so decref on error. */
      if (PyTuple_SetItem(closure, 0, condition) < 0 ||
          PyTuple_SetItem(closure, 1, decorators) < 0) {
        Py_DECREF(condition);
        Py_DECREF(closure);
        decorators = NULL; /* ownership consumed by the failed SetItem */
        goto error;
      }
      decorators = NULL; /* ownership transferred into closure */
      CFG_ALLOC_FAIL_GUARD();
      wrapper = PyCFunction_New(&cfg_attr_wrapper_def, closure);
      if (wrapper == NULL) {
        goto error;
      }
      return wrapper;
    }
    /* Direct: evaluate condition(func) */
    PyObject *cond_args = PyTuple_Pack(1, func);
    if (cond_args == NULL) {
      goto error;
    }
    PyObject *cond_result = PyObject_CallObject(condition, cond_args);
    Py_DECREF(cond_args);
    if (cond_result == NULL) {
      PyObject *error_type, *error_value, *error_traceback;
      PyErr_Fetch(&error_type, &error_value, &error_traceback);
      PyObject *fq = _get_func_name(NULL, func);
      if (error_type != NULL &&
          PyErr_GivenExceptionMatches(error_type, PyExc_TypeError) &&
          fq != NULL) {
        PyObject *error_msg = PyUnicode_FromFormat(
            "Error calling `condition` for `%U`: %S", fq, error_value);
        if (error_msg != NULL) {
          PyErr_SetObject(PyExc_TypeError, error_msg);
          Py_DECREF(error_msg);
        }
        Py_XDECREF(error_type);
        Py_XDECREF(error_value);
        Py_XDECREF(error_traceback);
      } else {
        PyErr_Restore(error_type, error_value, error_traceback);
      }
      Py_XDECREF(fq);
      goto error;
    }
    int cond_bool = PyObject_IsTrue(cond_result);
    Py_DECREF(cond_result);
    if (cond_bool == -1) {
      goto error;
    }
    if (cond_bool) {
      PyObject *fq = _get_func_name(NULL, func);
      if (fq == NULL) {
        goto error;
      }
      PyObject *result = cfg_attr_apply_decorators(func, decorators, fq);
      Py_DECREF(fq);
      Py_DECREF(decorators);
      decorators = NULL;
      return result;
    }
    /* False: raiser */
    PyObject *fq = _get_func_name(NULL, func);
    if (fq == NULL) {
      goto error;
    }
    PyObject *cached = cache_get_live(_cfg_attr_cache, fq);
    if (cached != NULL) {
      Py_DECREF(fq);
      Py_DECREF(decorators);
      decorators = NULL;
      return cached; /* new reference */
    }
    PyObject *raiser = cfg_make_raiser(fq);
    Py_DECREF(fq);
    Py_DECREF(decorators);
    decorators = NULL;
    return raiser;
  }

  /* Non-callable condition */
  int cond_truthy = PyObject_IsTrue(condition);
  if (cond_truthy == -1) {
    goto error;
  }

  if (cond_truthy) {
    /* True: apply decorators (factory or direct) */
    if (func == NULL || func == Py_None) {
      _cfg_log("cfg_attr: true factory");
      closure = PyTuple_New(2);
      if (closure == NULL) {
        goto error;
      }
      Py_INCREF(condition);
      if (PyTuple_SetItem(closure, 0, condition) < 0 ||
          PyTuple_SetItem(closure, 1, decorators) < 0) {
        Py_DECREF(condition);
        Py_DECREF(closure);
        decorators = NULL;
        goto error;
      }
      decorators = NULL; /* ownership transferred into closure */
      wrapper = PyCFunction_New(&cfg_attr_wrapper_def, closure);
      if (wrapper == NULL) {
        goto error;
      }
      return wrapper;
    }
    PyObject *fq = _get_func_name(NULL, func);
    if (fq == NULL) {
      goto error;
    }
    PyObject *result = cfg_attr_apply_decorators(func, decorators, fq);
    Py_DECREF(fq);
    Py_DECREF(decorators);
    decorators = NULL;
    return result;
  }

  /* False: raiser (factory or direct) */
  if (func == NULL || func == Py_None) {
    closure = PyTuple_New(2);
    if (closure == NULL) {
      goto error;
    }
    Py_INCREF(condition);
    if (PyTuple_SetItem(closure, 0, condition) < 0 ||
        PyTuple_SetItem(closure, 1, decorators) < 0) {
      Py_DECREF(condition);
      Py_DECREF(closure);
      decorators = NULL;
      goto error;
    }
    decorators = NULL; /* ownership transferred into closure */
    wrapper = PyCFunction_New(&cfg_attr_wrapper_def, closure);
    if (wrapper == NULL) {
      goto error;
    }
    return wrapper;
  }
  PyObject *fq = _get_func_name(NULL, func);
  if (fq == NULL) {
    goto error;
  }
  PyObject *cached = cache_get_live(_cfg_attr_cache, fq);
  if (cached != NULL) {
    Py_DECREF(fq);
    Py_DECREF(decorators);
    decorators = NULL;
    return cached; /* new reference */
  }
  PyObject *raiser = cfg_make_raiser(fq);
  Py_DECREF(fq);
  Py_DECREF(decorators);
  decorators = NULL;
  return raiser;

error:
  Py_XDECREF(closure);
  Py_XDECREF(wrapper);
  Py_XDECREF(decorators);
  return NULL;
}

/* --- Eager validation: assert_all_true() -------------------------------
 *
 * Module-level ``@cfg(condition=False)`` decorations return a
 * TypeErrorRaiser *immediately* (the function itself is replaced), but the
 * error only fires when the name is *called*.  For config/flag-style
 * modules you often want to fail at import time when a decorated name ended
 * up with no true condition.  ``assert_all_true()`` scans the module-level
 * cache and raises a TypeError naming every qualified function whose cached
 * value is a TypeErrorRaiser (i.e. no ``condition=True`` winner).  It is a
 * no-op (returns None) when everything is satisfied.
 *
 * ``_get_failed()`` returns the same list as a Python list of qualname
 * strings (empty when all conditions are true) — used by tests and by
 * ``assert_all_true`` itself.
 */

static PyObject *cfg_get_failed(PyObject *Py_UNUSED(self),
                                PyObject *Py_UNUSED(ignored)) {
  CFG_ALLOC_FAIL_GUARD();
  PyObject *result = PyList_New(0);
  if (result == NULL) {
    return NULL;
  }
  PyObject *iter = PyObject_GetIter(_failed_qualnames);
  if (iter == NULL) {
    Py_DECREF(result);
    return NULL;
  }
  PyObject *item;
  while ((item = PyIter_Next(iter)) != NULL) {
    if (PyList_Append(result, item) < 0) {
      Py_DECREF(item);
      Py_DECREF(iter);
      Py_DECREF(result);
      return NULL;
    }
    Py_DECREF(item);
  }
  Py_DECREF(iter);
  if (PyErr_Occurred()) {
    Py_DECREF(result);
    return NULL;
  }
  return result;
}

static PyObject *cfg_assert_all_true(PyObject *Py_UNUSED(self),
                                     PyObject *Py_UNUSED(ignored)) {
  CFG_ALLOC_FAIL_GUARD();
  PyObject *failed = cfg_get_failed(NULL, NULL);
  if (failed == NULL) {
    return NULL;
  }
  Py_ssize_t n = PyList_GET_SIZE(failed);
  if (n == 0) {
    Py_DECREF(failed);
    /* #2 (frozen cache): intentionally NOT implemented via PyDict_Freeze —
     * it is not in the Limited API (abi3), so it cannot be used by this
     * extension (which builds as cp39-abi3 for CPython 3.9-3.14 + wasm).
     * The steady-state speedup is instead achieved by proposal #3: strong-ref
     * cache values for module-level functions remove the per-lookup weakref
     * type-check and deref, which is the dominant cost in cache_get_live. */
    Py_RETURN_NONE;
  }
  PyObject *sep = PyUnicode_FromString(", ");
  if (sep == NULL) {
    Py_DECREF(failed);
    return NULL;
  }
  PyObject *joined = PyUnicode_Join(sep, failed);
  Py_DECREF(sep);
  Py_DECREF(failed);
  if (joined == NULL) {
    return NULL;
  }
  PyErr_Format(PyExc_TypeError,
               "No condition is true for %zd decorated name(s): %U", n, joined);
  Py_DECREF(joined);
  return NULL;
}

/* Named method definitions (used for module aliases in PyInit__c). */
static PyMethodDef cm_method_def = {
    "cm", (PyCFunction)(void (*)(void))cm, METH_VARARGS | METH_KEYWORDS,
    "Conditionally select function implementations based on a runtime "
    "condition."};

static PyMethodDef cfg_attr_method_def = {
    "cfg_attr", (PyCFunction)(void (*)(void))cfg_attr,
    METH_VARARGS | METH_KEYWORDS,
    "Conditionally apply a chain of decorators to a function."};

/* Define the methods of the module */
static PyMethodDef ConditionalMethodMethods[] = {
    {"_raise_exec", _raise_exec, METH_VARARGS,
     "Create a TypeErrorRaiser instance."},
    {"_get_func_name", _get_func_name, METH_O,
     "Get the fully qualified name of a function."},
    {"_get_mod_qual_func_name", _get_func_name, METH_O,
     "Alias of _get_func_name (fully qualified function name)."},
    {"cm", (PyCFunction)(void (*)(void))cm, METH_VARARGS | METH_KEYWORDS,
     "Conditionally select function implementations based on a runtime "
     "condition."},
    {"_cm_inner", _cm_inner, METH_VARARGS,
     "Inner implementation of the conditional method decorator."},
    {"cfg_attr", (PyCFunction)(void (*)(void))cfg_attr,
     METH_VARARGS | METH_KEYWORDS,
     "Conditionally apply a chain of decorators to a function."},
    {"debug", cfg_debug, METH_VARARGS,
     "Log a debug message (noop unless enabled)."},
    {"debug_enabled", cfg_debug_enabled, METH_NOARGS,
     "Whether debug logging is enabled."},
    {"assert_all_true", cfg_assert_all_true, METH_NOARGS,
     "Raise TypeError if any @cfg-decorated name has no true condition; "
     "otherwise return None."},
    {"_get_failed", cfg_get_failed, METH_NOARGS,
     "Return the list of qualnames whose cached value is a TypeErrorRaiser."},
    {"_cm_wrapper", (PyCFunction)(void (*)(void))_cm_wrapper, METH_VARARGS,
     "Internal decorator wrapper (exposed for testing)."},
#ifdef PY_CFG_TESTING
    {"set_alloc_fail_count", cfg_set_alloc_fail_count, METH_VARARGS,
     "Test-only: make the next n guarded allocations fail."},
#endif
    {"cfg_attr_wrapper", cfg_attr_wrapper, METH_VARARGS,
     "Internal cfg_attr wrapper (exposed for testing)."},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/* Module definition */
static struct PyModuleDef conditionalmodule = {
    PyModuleDef_HEAD_INIT,
    "_c",                                  /* m_name */
    "Conditional method decorator module", /* m_doc */
    -1,                                    /* m_size */
    ConditionalMethodMethods,              /* m_methods */
    NULL,                                  /* m_slots */
    NULL,                                  /* m_traverse */
    NULL,                                  /* m_clear */
    NULL                                   /* m_free */
};

/* Module initialization function */
PyMODINIT_FUNC PyInit__c(void) {
  /* Initialize the module */
  CFG_ALLOC_FAIL_GUARD();
  PyObject *m = PyModule_Create(&conditionalmodule);
  if (m == NULL) {
    return NULL;
  }

  /* Add the TypeErrorRaiser type to the module */
  if (PyType_Ready(&TypeErrorRaiserType) < 0) {
    Py_DECREF(m);
    return NULL;
  }

  Py_INCREF(&TypeErrorRaiserType);
  if (PyModule_AddObject(m, "_TypeErrorRaiser",
                         (PyObject *)&TypeErrorRaiserType) < 0) {
    Py_DECREF(&TypeErrorRaiserType);
    Py_DECREF(m);
    return NULL;
  }

  /* Create the module-level caches */
  _cm_cache = PyDict_New();
  _cfg_attr_cache = PyDict_New();
  _failed_qualnames = PySet_New(NULL);
  if (_cm_cache == NULL || _cfg_attr_cache == NULL ||
      _failed_qualnames == NULL) {
    Py_XDECREF(_cm_cache);
    Py_XDECREF(_cfg_attr_cache);
    Py_XDECREF(_failed_qualnames);
    _cm_cache = NULL;
    _cfg_attr_cache = NULL;
    _failed_qualnames = NULL;
    Py_DECREF(m);
    return NULL;
  }
  if (PyModule_AddObject(m, "_cm_cache", _cm_cache) < 0) {
    Py_DECREF(_cm_cache);
    Py_DECREF(m);
    return NULL;
  }
  if (PyModule_AddObject(m, "_cfg_attr_cache", _cfg_attr_cache) < 0) {
    Py_DECREF(_cfg_attr_cache);
    Py_DECREF(m);
    return NULL;
  }
  if (PyModule_AddObject(m, "_failed_qualnames", _failed_qualnames) < 0) {
    Py_DECREF(_failed_qualnames);
    Py_DECREF(m);
    return NULL;
  }

  /* Grab the `weakref.ref` type for cache_get_live so it can tell weakref
   * cache values (true-condition winner functions) apart from strong ones
   * (TypeErrorRaiser).  Held for the module lifetime. */
  PyObject *wr_mod = PyImport_ImportModule("weakref");
  if (wr_mod == NULL) {
    Py_DECREF(m);
    return NULL;
  }
  CFG_weakref_ref_type = PyObject_GetAttrString(wr_mod, "ref");
  Py_DECREF(wr_mod);
  if (CFG_weakref_ref_type == NULL) {
    Py_DECREF(m);
    return NULL;
  }

  /* Create global aliases for the cm function (callable heap objects so
     cm._cache is settable) */
  PyObject *cm_func = CfgCallable_new_wrapper(&cm_method_def);
  if (cm_func == NULL) {
    Py_DECREF(m);
    return NULL;
  }

  if (PyModule_AddObject(m, "cfg", cm_func) < 0) {
    Py_DECREF(cm_func);
    Py_DECREF(m);
    return NULL;
  }

  Py_INCREF(cm_func);
  if (PyModule_AddObject(m, "if_", cm_func) < 0) {
    Py_DECREF(cm_func);
    Py_DECREF(m);
    return NULL;
  }

  /* Expose cm._cache (matches the pure-Python reference API) */
  if (PyObject_SetAttrString(cm_func, "_cache", _cm_cache) < 0) {
    Py_DECREF(m);
    return NULL;
  }
  /* The method-table entry "cm" is a plain builtin; replace it with the
     callable heap object so `cfg.cm._cache` works. */
  Py_INCREF(cm_func);
  if (PyModule_AddObject(m, "cm", cm_func) < 0) {
    Py_DECREF(cm_func);
    Py_DECREF(m);
    return NULL;
  }

  /* Create and add cfg_attr function */
  PyObject *cfg_attr_func = CfgCallable_new_wrapper(&cfg_attr_method_def);
  if (cfg_attr_func == NULL) {
    Py_DECREF(m);
    return NULL;
  }

  if (PyModule_AddObject(m, "cfg_attr", cfg_attr_func) < 0) {
    Py_DECREF(cfg_attr_func);
    Py_DECREF(m);
    return NULL;
  }

  /* Expose cfg_attr._cache (matches the pure-Python reference API) */
  if (PyObject_SetAttrString(cfg_attr_func, "_cache", _cfg_attr_cache) < 0) {
    Py_DECREF(m);
    return NULL;
  }
  Py_INCREF(cfg_attr_func);
  if (PyModule_AddObject(m, "cfg_attr", cfg_attr_func) < 0) {
    Py_DECREF(cfg_attr_func);
    Py_DECREF(m);
    return NULL;
  }

  /* Register the CfgCallable heap type */
  if (PyType_Ready(&CfgCallableType) < 0) {
    Py_DECREF(m);
    return NULL;
  }
  Py_INCREF(&CfgCallableType);
  if (PyModule_AddObject(m, "_CfgCallable", (PyObject *)&CfgCallableType) < 0) {
    Py_DECREF(&CfgCallableType);
    Py_DECREF(m);
    return NULL;
  }

  return m;
}