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
#define CFG_ALLOC_FAIL_GUARD()          \
  do {                                  \
    if (_cfg_alloc_should_fail()) {     \
      PyErr_NoMemory();                 \
      return NULL;                      \
    }                                   \
  } while (0)
#define CFG_ALLOC_FAIL_GUARD_VOID()     \
  do {                                  \
    if (_cfg_alloc_should_fail()) {     \
      PyErr_NoMemory();                 \
      return;                           \
    }                                   \
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
#define CFG_ALLOC_TEST_FAIL() \
  (_cfg_alloc_should_fail() ? (PyErr_NoMemory(), 1) : 0)
#define CFG_ALLOC_TEST_FAIL_VOID() \
  (_cfg_alloc_should_fail() ? (PyErr_NoMemory(), 1) : 0)
#else
#define CFG_ALLOC_TEST_FAIL() (0)
#define CFG_ALLOC_TEST_FAIL_VOID() (0)
#endif


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

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
static PyObject *_raise_exec(PyObject *self, PyObject *args);
static PyObject *_get_func_name(PyObject *self, PyObject *func);
static PyObject *cm(PyObject *self, PyObject *args, PyObject *kwargs);
static PyObject *cfg_attr(PyObject *self, PyObject *args, PyObject *kwargs);

/* Method definitions for wrappers */
static PyMethodDef cm_wrapper_def = {"_cm_wrapper", (PyCFunction)_cm_wrapper,
                                     METH_VARARGS, NULL};

static PyMethodDef cfg_attr_wrapper_def = {
    "cfg_attr_wrapper", (PyCFunction)cfg_attr_wrapper, METH_VARARGS,
    "Wrapper function for cfg_attr when used as a decorator"};

/* Module level caches: one for cm/cfg/if_, one for cfg_attr */
static PyObject *_cm_cache = NULL;
static PyObject *_cfg_attr_cache = NULL;

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
  /* Clear the caches */
  if (_cm_cache != NULL) {
    PyDict_Clear(_cm_cache);
  }
  if (_cfg_attr_cache != NULL) {
    PyDict_Clear(_cfg_attr_cache);
  }
}

static void _raise_typeerror(TypeErrorRaiserObject *self) {
  /* Clear the caches */
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
    if (PyList_Append(qualnames_list, item) < 0 ||
        CFG_ALLOC_TEST_FAIL_VOID()) {
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
  PyObject_HEAD
  PyObject *callable; /* underlying PyCFunction */
  PyObject *dict;     /* instance __dict__ */
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

static PyTypeObject CfgCallableType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "conditional_method._CfgCallable",
    .tp_basicsize = sizeof(CfgCallableObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_dictoffset = offsetof(CfgCallableObject, dict),
    .tp_call = (ternaryfunc)CfgCallable_call,
    .tp_dealloc = (destructor)CfgCallable_dealloc,
    .tp_traverse = (traverseproc)CfgCallable_traverse,
    .tp_clear = (inquiry)CfgCallable_clear,
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
  PyObject *condition =
      self; /* self is actually our closure with the condition */
  if (condition == NULL) {
    PyErr_SetString(PyExc_RuntimeError, "No condition found in closure");
    return NULL;
  }

  /* Call _cm_inner with func and condition */
  CFG_ALLOC_FAIL_GUARD();
  PyObject *inner_args = Py_BuildValue("(OO)", func, condition);
  if (inner_args == NULL) {
    return NULL;
  }

  PyObject *result = _cm_inner(NULL, inner_args);
  Py_DECREF(inner_args);

  return result;
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
      PyErr_SetString(
          PyExc_TypeError,
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
    PyErr_SetString(
        PyExc_TypeError,
        "`@cfg` must be used as a decorator and `condition` "
        "must be specified as an instance of type `bool`");
    return NULL;
  }

  /* Call _cm_inner directly with the function and condition */
  CFG_ALLOC_FAIL_GUARD();
  PyObject *args_tuple = Py_BuildValue("(OO)", func, condition);
  if (args_tuple == NULL) {
    return NULL;
  }

  PyObject *result = _cm_inner(NULL, args_tuple);
  Py_DECREF(args_tuple);

  return result;
}

static PyObject *_cm_inner(PyObject *self, PyObject *args) {
  PyObject *func = NULL;
  PyObject *condition = NULL;

  if (!PyArg_ParseTuple(args, "OO", &func, &condition)) {
    return NULL;
  }

  /* Get the fully qualified name of the function */
  PyObject *f_qualname = _get_func_name(self, func);
  if (f_qualname == NULL) {
    return NULL;
  }
  /* Debug-only UTF-8 logging (abi3-3.9-safe: encode to bytes, read buffer;
   * the Limited-API PyUnicode_AsUTF8* forms are 3.10+). */
  PyObject *fq_encoded = PyUnicode_AsEncodedString(f_qualname, "utf-8", NULL);
  const char *fq_utf8 = fq_encoded != NULL ? PyBytes_AsString(fq_encoded) : NULL;
  _cfg_log("cm: decorating %s", fq_utf8 != NULL ? fq_utf8 : "?");
  _cfg_log("cm: f_qualname %s", fq_utf8 != NULL ? fq_utf8 : "?");
  Py_XDECREF(fq_encoded);


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

  /* If the condition is true, add the function to the cache and return it */
  if (cond_bool) {
    if (PyDict_SetItem(_cm_cache, f_qualname, func) < 0 ||
        CFG_ALLOC_TEST_FAIL()) {
      Py_DECREF(f_qualname);
      return NULL;
    }
    Py_DECREF(f_qualname);
    Py_INCREF(func);
    return func;
  }

  /* If the condition is false, check if the function is in the cache */
  PyObject *cached_func = PyDict_GetItem(_cm_cache, f_qualname);
  if (cached_func != NULL) {
    Py_DECREF(f_qualname);
    Py_INCREF(cached_func);
    return cached_func;
  }

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
   decorators is a sequence; applied right-to-left so decorators[0] is outermost. */
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
        (PyDict_SetItem(_cfg_attr_cache, f_qualname, func) < 0 ||
         CFG_ALLOC_TEST_FAIL())) {
      Py_DECREF(func);
      return NULL;
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
    if (PyDict_SetItem(_cfg_attr_cache, f_qualname, result) < 0 ||
        CFG_ALLOC_TEST_FAIL()) {
      goto error;
    }
  }
  return result;
error:
  Py_XDECREF(result);
  return NULL;
}

/* Helper: create a TypeErrorRaiser for a false-conditioned function
   (shared by cm and cfg_attr). Adds f_qualname to the raiser's set. */
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
    PyObject *cached = PyDict_GetItem(_cfg_attr_cache, fq);
    if (cached != NULL) {
      Py_DECREF(fq);
      Py_DECREF(decorators);
      decorators = NULL;
      Py_INCREF(cached);
      return cached;
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
  PyObject *cached = PyDict_GetItem(_cfg_attr_cache, fq);
  if (cached != NULL) {
    Py_DECREF(fq);
    Py_DECREF(decorators);
    decorators = NULL;
    Py_INCREF(cached);
    return cached;
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

/* Named method definitions (used for module aliases in PyInit__c). */
static PyMethodDef cm_method_def = {
    "cm", (PyCFunction)(void (*)(void))cm, METH_VARARGS | METH_KEYWORDS,
    "Conditionally select function implementations based on a runtime condition."};

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
    {"debug", cfg_debug, METH_VARARGS, "Log a debug message (noop unless enabled)."},
    {"debug_enabled", cfg_debug_enabled, METH_NOARGS, "Whether debug logging is enabled."},
    {"_cm_wrapper", _cm_wrapper, METH_VARARGS,
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
    "_c",                                   /* m_name */
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
  if (_cm_cache == NULL || _cfg_attr_cache == NULL) {
    Py_XDECREF(_cm_cache);
    Py_XDECREF(_cfg_attr_cache);
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