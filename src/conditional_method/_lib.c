#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>

/* Forward declarations */
static PyObject *_cm_wrapper(PyObject *self, PyObject *args);
static PyObject *cfg_attr_wrapper(PyObject *self, PyObject *args);
static PyObject *_cm_inner(PyObject *self, PyObject *args);
static PyObject *_raise_exec(PyObject *self, PyObject *args, PyObject *kwargs);
static PyObject *_get_func_name(PyObject *self, PyObject *func);
static PyObject *cm(PyObject *self, PyObject *args, PyObject *kwargs);
static PyObject *cfg_attr(PyObject *self, PyObject *args, PyObject *kwargs);

/* Method definitions for wrappers */
static PyMethodDef cm_wrapper_def = {
    "_cm_wrapper",
    (PyCFunction)_cm_wrapper,
    METH_VARARGS,
    NULL};

static PyMethodDef cfg_attr_wrapper_def = {
    "cfg_attr_wrapper",
    (PyCFunction)cfg_attr_wrapper,
    METH_VARARGS,
    "Wrapper function for cfg_attr when used as a decorator"};

/* Module level cache for decorated functions */
static PyObject *_cache = NULL;

/* TypeErrorRaiser type declaration */
typedef struct
{
  PyObject_HEAD PyObject
      *f_qualnames;   /* Set of function qualnames that failed conditions */
  PyObject *qualname; /* Qualified name for the raiser */
} TypeErrorRaiserObject;

static void TypeErrorRaiser_dealloc(TypeErrorRaiserObject *self)
{
  PyObject_GC_UnTrack(self);
  Py_XDECREF(self->f_qualnames);
  Py_XDECREF(self->qualname);
  Py_TYPE(self)->tp_free((PyObject *)self);
}

static int TypeErrorRaiser_traverse(TypeErrorRaiserObject *self,
                                    visitproc visit, void *arg)
{
  Py_VISIT(self->f_qualnames);
  Py_VISIT(self->qualname);
  return 0;
}

static int TypeErrorRaiser_clear(TypeErrorRaiserObject *self)
{
  Py_CLEAR(self->f_qualnames);
  Py_CLEAR(self->qualname);
  return 0;
}

static void TypeErrorRaiser_finalize(TypeErrorRaiserObject *self)
{
  /* Clear the cache */
  if (_cache != NULL)
  {
    PyDict_Clear(_cache);
  }
}

static void _raise_typeerror(TypeErrorRaiserObject *self)
{
  /* Clear the cache */
  if (_cache != NULL)
  {
    PyDict_Clear(_cache);
  }

  /* Join the qualnames for the error message */
  PyObject *qualnames_iter = PyObject_GetIter(self->f_qualnames);
  if (qualnames_iter == NULL)
  {
    return;
  }

  PyObject *qualnames_list = PyList_New(0);
  if (qualnames_list == NULL)
  {
    Py_DECREF(qualnames_iter);
    return;
  }

  PyObject *item;
  while ((item = PyIter_Next(qualnames_iter)) != NULL)
  {
    if (PyList_Append(qualnames_list, item) < 0)
    {
      Py_DECREF(item);
      Py_DECREF(qualnames_list);
      Py_DECREF(qualnames_iter);
      return;
    }
    Py_DECREF(item);
  }
  Py_DECREF(qualnames_iter);

  PyObject *separator = PyUnicode_FromString(", ");
  if (separator == NULL)
  {
    Py_DECREF(qualnames_list);
    return;
  }

  PyObject *joined_qualnames = PyUnicode_Join(separator, qualnames_list);
  Py_DECREF(separator);
  Py_DECREF(qualnames_list);

  if (joined_qualnames == NULL)
  {
    return;
  }

  /* Get the default qualname if the list is empty */
  const char *qualname_str = "";
  if (PyUnicode_Check(self->qualname))
  {
    qualname_str = PyUnicode_AsUTF8(self->qualname);
    if (qualname_str == NULL)
    {
      Py_DECREF(joined_qualnames);
      return;
    }
  }

  /* Check if the joined qualnames is empty */
  int is_empty = (PyUnicode_GetLength(joined_qualnames) == 0);

  /* Format the error message */
  PyObject *error_msg;
  if (is_empty)
  {
    error_msg = PyUnicode_FromFormat("None of the conditions is true for `%s`",
                                     qualname_str);
  }
  else
  {
    error_msg = PyUnicode_FromFormat("None of the conditions is true for `%U`",
                                     joined_qualnames);
  }
  Py_DECREF(joined_qualnames);

  if (error_msg == NULL)
  {
    return;
  }

  /* Raise the TypeError */
  PyErr_SetObject(PyExc_TypeError, error_msg);
  Py_DECREF(error_msg);
}

static PyObject *TypeErrorRaiser_call(TypeErrorRaiserObject *self,
                                      PyObject *args, PyObject *kwargs)
{
  _raise_typeerror(self);
  return NULL;
}

static PyObject *TypeErrorRaiser_set_name(TypeErrorRaiserObject *self,
                                          PyObject *args)
{
  PyObject *owner;
  PyObject *name;

  if (!PyArg_ParseTuple(args, "OO", &owner, &name))
  {
    return NULL;
  }

  _raise_typeerror(self);
  return NULL;
}

static PyObject *TypeErrorRaiser_new(PyTypeObject *type, PyObject *args,
                                     PyObject *kwargs)
{
  TypeErrorRaiserObject *self;
  self = (TypeErrorRaiserObject *)type->tp_alloc(type, 0);
  if (self != NULL)
  {
    self->f_qualnames = PySet_New(NULL);
    if (self->f_qualnames == NULL)
    {
      Py_DECREF(self);
      return NULL;
    }

    self->qualname = PyUnicode_FromString("");
    if (self->qualname == NULL)
    {
      Py_DECREF(self->f_qualnames);
      Py_DECREF(self);
      return NULL;
    }
  }

  /* Clear the cache */
  if (_cache != NULL)
  {
    PyDict_Clear(_cache);
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

/* Function to create a new TypeErrorRaiser instance */
static PyObject *_raise_exec(PyObject *self, PyObject *args, PyObject *kwargs)
{
  static char *kwlist[] = {"qualname", NULL};
  PyObject *qualname = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|O", kwlist, &qualname))
  {
    return NULL;
  }

  /* Create a new TypeErrorRaiser instance */
  PyObject *raiser =
      PyObject_CallObject((PyObject *)&TypeErrorRaiserType, NULL);
  if (raiser == NULL)
  {
    return NULL;
  }

  /* Set the qualname if provided */
  if (qualname != NULL && PyUnicode_Check(qualname))
  {
    TypeErrorRaiserObject *raiser_obj = (TypeErrorRaiserObject *)raiser;
    Py_DECREF(raiser_obj->qualname);
    raiser_obj->qualname = PyUnicode_FromObject(qualname);
    if (raiser_obj->qualname == NULL)
    {
      Py_DECREF(raiser);
      return NULL;
    }
  }

  return raiser;
}

/* Function to get the fully qualified name of a function */
static PyObject *_get_func_name(PyObject *self, PyObject *func)
{
  PyObject *module = NULL;
  PyObject *qualname = NULL;
  PyObject *result = NULL;

  /* Try to get __qualname__ or __name__ */
  if (PyObject_HasAttrString(func, "__qualname__"))
  {
    qualname = PyObject_GetAttrString(func, "__qualname__");
  }
  else if (PyObject_HasAttrString(func, "__name__"))
  {
    qualname = PyObject_GetAttrString(func, "__name__");
  }

  /* If we found a name, get the module and combine them */
  if (qualname != NULL)
  {
    if (PyObject_HasAttrString(func, "__module__"))
    {
      module = PyObject_GetAttrString(func, "__module__");
      if (module != NULL && PyUnicode_Check(module))
      {
        result = PyUnicode_FromFormat("%U.%U", module, qualname);
      }
    }

    if (result == NULL)
    {
      /* If we couldn't get the module, just use the qualname */
      result = PyUnicode_FromObject(qualname);
    }

    Py_XDECREF(module);
    Py_XDECREF(qualname);

    if (result != NULL)
    {
      return result;
    }
  }

  /* If we couldn't get the name directly, try through __wrapped__, __func__, or
   * fget */
  const char *attrs[] = {"__wrapped__", "__func__", "fget"};
  for (int i = 0; i < 3; i++)
  {
    if (PyObject_HasAttrString(func, attrs[i]))
    {
      PyObject *wrapped = PyObject_GetAttrString(func, attrs[i]);
      if (wrapped != NULL)
      {
        result = _get_func_name(self, wrapped);
        Py_DECREF(wrapped);
        if (result != NULL)
        {
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
static PyObject *_cm_wrapper(PyObject *self, PyObject *args)
{
  PyObject *func = NULL;

  if (!PyArg_ParseTuple(args, "O", &func))
  {
    return NULL;
  }

  /* Get the condition from closure */
  PyObject *condition = self; /* self is actually our closure with the condition */
  if (condition == NULL)
  {
    PyErr_SetString(PyExc_RuntimeError, "No condition found in closure");
    return NULL;
  }

  /* Call _cm_inner with func and condition */
  PyObject *inner_args = Py_BuildValue("(OO)", func, condition);
  if (inner_args == NULL)
  {
    return NULL;
  }

  PyObject *result = _cm_inner(NULL, inner_args);
  Py_DECREF(inner_args);

  return result;
}

/* The core conditional method implementation */
static PyObject *cm(PyObject *self, PyObject *args, PyObject *kwargs)
{
  PyObject *func = NULL;
  PyObject *condition = Py_None;

  /* Parse arguments */
  if (!PyArg_ParseTuple(args, "|O", &func))
  {
    return NULL;
  }

  if (kwargs != NULL)
  {
    PyObject *cond = PyDict_GetItemString(kwargs, "condition");
    if (cond != NULL)
    {
      condition = cond;
    }
  }

  /* If no function is provided, return the inner decorator */
  if (func == NULL || func == Py_None)
  {
    if (condition == Py_None)
    {
      PyErr_SetString(
          PyExc_TypeError,
          "`@conditional_method` must be used as a decorator and `condition` "
          "must be specified as an instance of type `bool`");
      return NULL;
    }

    /* Create a wrapper function that will call _cm_inner with the captured
     * condition */
    PyObject *wrapper = PyCFunction_NewEx(&cm_wrapper_def, condition, NULL);
    if (wrapper == NULL)
    {
      return NULL;
    }

    return wrapper;
  }

  /* If a function is provided but no condition, raise TypeError */
  if (condition == Py_None)
  {
    PyErr_SetString(
        PyExc_TypeError,
        "`@conditional_method` must be used as a decorator and `condition` "
        "must be specified as an instance of type `bool`");
    return NULL;
  }

  /* Call _cm_inner directly with the function and condition */
  PyObject *args_tuple = Py_BuildValue("(OO)", func, condition);
  if (args_tuple == NULL)
  {
    return NULL;
  }

  PyObject *result = _cm_inner(NULL, args_tuple);
  Py_DECREF(args_tuple);

  return result;
}

static PyObject *_cm_inner(PyObject *self, PyObject *args)
{
  PyObject *func = NULL;
  PyObject *condition = NULL;

  if (!PyArg_ParseTuple(args, "OO", &func, &condition))
  {
    return NULL;
  }

  /* Get the fully qualified name of the function */
  PyObject *f_qualname = _get_func_name(self, func);
  if (f_qualname == NULL)
  {
    return NULL;
  }

  /* Evaluate the condition */
  PyObject *cond_result = NULL;

  if (PyCallable_Check(condition))
  {
    /* If condition is callable, call it with the function */
    PyObject *args_tuple = PyTuple_New(1);
    if (args_tuple == NULL)
    {
      Py_DECREF(f_qualname);
      return NULL;
    }

    Py_INCREF(func);
    PyTuple_SET_ITEM(args_tuple, 0, func);

    cond_result = PyObject_CallObject(condition, args_tuple);
    Py_DECREF(args_tuple);

    if (cond_result == NULL)
    {
      /* Get the error message and format it */
      PyObject *error_type, *error_value, *error_traceback;
      PyErr_Fetch(&error_type, &error_value, &error_traceback);

      PyObject *error_msg = PyUnicode_FromFormat(
          "Error calling `condition` for `%U`: %S", f_qualname, error_value);

      if (error_msg != NULL)
      {
        PyErr_SetObject(PyExc_TypeError, error_msg);
        Py_DECREF(error_msg);
      }

      Py_XDECREF(error_type);
      Py_XDECREF(error_value);
      Py_XDECREF(error_traceback);
      Py_DECREF(f_qualname);
      return NULL;
    }
  }
  else
  {
    /* If condition is not callable, convert it to a boolean */
    cond_result = PyObject_IsTrue(condition) ? Py_True : Py_False;
    Py_INCREF(cond_result);
  }

  /* Convert the result to a boolean */
  int cond_bool = PyObject_IsTrue(cond_result);
  Py_DECREF(cond_result);

  if (cond_bool == -1)
  {
    Py_DECREF(f_qualname);
    return NULL;
  }

  /* If the condition is true, add the function to the cache and return it */
  if (cond_bool)
  {
    if (PyDict_SetItem(_cache, f_qualname, func) < 0)
    {
      Py_DECREF(f_qualname);
      return NULL;
    }
    Py_DECREF(f_qualname);
    Py_INCREF(func);
    return func;
  }

  /* If the condition is false, check if the function is in the cache */
  PyObject *cached_func = PyDict_GetItem(_cache, f_qualname);
  if (cached_func != NULL)
  {
    Py_DECREF(f_qualname);
    Py_INCREF(cached_func);
    return cached_func;
  }

  /* If the function is not in the cache, create a TypeErrorRaiser */
  PyObject *raiser = _raise_exec(self, Py_BuildValue("(O)", f_qualname), NULL);
  if (raiser == NULL)
  {
    Py_DECREF(f_qualname);
    return NULL;
  }

  /* Add the function qualname to the raiser's f_qualnames set */
  TypeErrorRaiserObject *raiser_obj = (TypeErrorRaiserObject *)raiser;
  if (PySet_Add(raiser_obj->f_qualnames, f_qualname) < 0)
  {
    Py_DECREF(f_qualname);
    Py_DECREF(raiser);
    return NULL;
  }

  Py_DECREF(f_qualname);
  return raiser;
}

/* Wrapper function for cfg_attr when used as a decorator */
static PyObject *cfg_attr_wrapper(PyObject *self, PyObject *args)
{
  PyObject *func = NULL;

  if (!PyArg_ParseTuple(args, "O", &func))
  {
    return NULL;
  }

  /* Get closure tuple containing condition and decorators */
  PyObject *closure = self;
  if (!PyTuple_Check(closure) || PyTuple_GET_SIZE(closure) != 2)
  {
    PyErr_SetString(PyExc_RuntimeError, "Invalid closure in cfg_attr_wrapper");
    return NULL;
  }

  /* Get condition and decorators from closure */
  PyObject *condition = PyTuple_GET_ITEM(closure, 0);
  PyObject *decorators = PyTuple_GET_ITEM(closure, 1);

  /* Call cfg_attr with all the arguments */
  PyObject *args_tuple = PyTuple_Pack(1, func);
  if (args_tuple == NULL)
  {
    return NULL;
  }

  PyObject *kwargs = PyDict_New();
  if (kwargs == NULL)
  {
    Py_DECREF(args_tuple);
    return NULL;
  }

  if (PyDict_SetItemString(kwargs, "condition", condition) < 0 ||
      PyDict_SetItemString(kwargs, "decorators", decorators) < 0)
  {
    Py_DECREF(args_tuple);
    Py_DECREF(kwargs);
    return NULL;
  }

  PyObject *result = cfg_attr(NULL, args_tuple, kwargs);
  Py_DECREF(args_tuple);
  Py_DECREF(kwargs);

  return result;
}

/* Implementation of cfg_attr function */
static PyObject *cfg_attr(PyObject *self, PyObject *args, PyObject *kwargs)
{
  PyObject *func = NULL;
  PyObject *condition = Py_None;
  PyObject *decorators = NULL;

  static char *kwlist[] = {"", "condition", "decorators", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|OOO", kwlist, &func,
                                   &condition, &decorators))
  {
    return NULL;
  }

  /* If decorators is not provided, use an empty tuple */
  if (decorators == NULL)
  {
    decorators = PyTuple_New(0);
    if (decorators == NULL)
    {
      return NULL;
    }
  }
  else
  {
    Py_INCREF(decorators);
  }

  /* If func is None, return a decorator */
  if (func == NULL || func == Py_None)
  {
    /* If condition is not provided, raise an error */
    if (condition == Py_None)
    {
      PyErr_SetString(PyExc_ValueError,
                      "condition is required and must be a bool or a callable "
                      "that takes the decorated function and returns a bool");
      Py_DECREF(decorators);
      return NULL;
    }

    /* Create a closure with condition and decorators */
    PyObject *closure = PyTuple_New(2);
    if (closure == NULL)
    {
      Py_DECREF(decorators);
      return NULL;
    }

    Py_INCREF(condition);
    PyTuple_SET_ITEM(closure, 0, condition);
    PyTuple_SET_ITEM(closure, 1,
                     decorators); // Transfers ownership of decorators

    /* Create and return the wrapper function */
    PyObject *wrapper = PyCFunction_New(&cfg_attr_wrapper_def, closure);
    if (wrapper == NULL)
    {
      Py_DECREF(closure);
      return NULL;
    }

    return wrapper;
  }

  /* If func is not None and condition is true, apply the decorators */
  if (condition != Py_None && PyObject_IsTrue(condition))
  {
    /* Check if decorators is a sequence */
    if (!PySequence_Check(decorators))
    {
      PyErr_SetString(PyExc_TypeError, "decorators must be a sequence");
      Py_DECREF(decorators);
      return NULL;
    }

    /* Get the length of decorators */
    Py_ssize_t n_decorators = PySequence_Length(decorators);
    if (n_decorators < 0)
    {
      Py_DECREF(decorators);
      return NULL;
    }

    /* If no decorators, just return the function */
    if (n_decorators == 0)
    {
      Py_DECREF(decorators);
      Py_INCREF(func);
      return func;
    }

    /* Apply each decorator in reverse order for proper nesting */
    PyObject *result = func;
    Py_INCREF(result);

    for (Py_ssize_t i = n_decorators - 1; i >= 0; i--)
    {
      PyObject *decorator = PySequence_GetItem(decorators, i);
      if (decorator == NULL)
      {
        Py_DECREF(result);
        Py_DECREF(decorators);
        return NULL;
      }

      /* Apply the decorator to the function */
      PyObject *args_tuple = PyTuple_Pack(1, result);
      if (args_tuple == NULL)
      {
        Py_DECREF(decorator);
        Py_DECREF(result);
        Py_DECREF(decorators);
        return NULL;
      }

      PyObject *decorated = PyObject_Call(decorator, args_tuple, NULL);
      Py_DECREF(args_tuple);
      Py_DECREF(result);
      Py_DECREF(decorator);

      if (decorated == NULL)
      {
        Py_DECREF(decorators);
        return NULL;
      }

      result = decorated;
    }

    Py_DECREF(decorators);
    return result;
  }

  /* If condition is false, return the function unchanged */
  Py_DECREF(decorators);
  Py_INCREF(func);
  return func;
}

/* Define the methods of the module */
static PyMethodDef ConditionalMethodMethods[] = {
    {"_raise_exec", _raise_exec, METH_VARARGS | METH_KEYWORDS,
     "Create a TypeErrorRaiser instance."},
    {"_get_func_name", _get_func_name, METH_O,
     "Get the fully qualified name of a function."},
    {"cm", cm, METH_VARARGS | METH_KEYWORDS,
     "Conditionally select function implementations based on a runtime "
     "condition."},
    {"_cm_inner", _cm_inner, METH_VARARGS,
     "Inner implementation of the conditional method decorator."},
    {"cfg_attr", cfg_attr, METH_VARARGS | METH_KEYWORDS,
     "Conditionally apply a chain of decorators to a function."},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/* Module definition */
static struct PyModuleDef conditionalmodule = {
    PyModuleDef_HEAD_INIT,
    "_lib",                                /* m_name */
    "Conditional method decorator module", /* m_doc */
    -1,                                    /* m_size */
    ConditionalMethodMethods,              /* m_methods */
    NULL,                                  /* m_slots */
    NULL,                                  /* m_traverse */
    NULL,                                  /* m_clear */
    NULL                                   /* m_free */
};

/* Module initialization function */
PyMODINIT_FUNC PyInit__lib(void)
{
  /* Initialize the module */
  PyObject *m = PyModule_Create(&conditionalmodule);
  if (m == NULL)
  {
    return NULL;
  }

  /* Add the TypeErrorRaiser type to the module */
  if (PyType_Ready(&TypeErrorRaiserType) < 0)
  {
    Py_DECREF(m);
    return NULL;
  }

  Py_INCREF(&TypeErrorRaiserType);
  if (PyModule_AddObject(m, "_TypeErrorRaiser",
                         (PyObject *)&TypeErrorRaiserType) < 0)
  {
    Py_DECREF(&TypeErrorRaiserType);
    Py_DECREF(m);
    return NULL;
  }

  /* Create the cache dictionary */
  _cache = PyDict_New();
  if (_cache == NULL)
  {
    Py_DECREF(m);
    return NULL;
  }

  /* Add the cache to the module */
  if (PyModule_AddObject(m, "_cache", _cache) < 0)
  {
    Py_DECREF(_cache);
    Py_DECREF(m);
    return NULL;
  }

  /* Create global aliases for the cm function */
  PyObject *cm_func =
      PyCFunction_New(&ConditionalMethodMethods[2], NULL); // Index 2 is "cm"
  if (cm_func == NULL)
  {
    Py_DECREF(m);
    return NULL;
  }

  if (PyModule_AddObject(m, "cfg", cm_func) < 0)
  {
    Py_DECREF(cm_func);
    Py_DECREF(m);
    return NULL;
  }

  Py_INCREF(cm_func);
  if (PyModule_AddObject(m, "conditional_method", cm_func) < 0)
  {
    Py_DECREF(cm_func);
    Py_DECREF(m);
    return NULL;
  }

  Py_INCREF(cm_func);
  if (PyModule_AddObject(m, "if_", cm_func) < 0)
  {
    Py_DECREF(cm_func);
    Py_DECREF(m);
    return NULL;
  }

  /* Create and add cfg_attr function */
  PyObject *cfg_attr_func = PyCFunction_New(&ConditionalMethodMethods[4],
                                            NULL); // Index 4 is "cfg_attr"
  if (cfg_attr_func == NULL)
  {
    Py_DECREF(m);
    return NULL;
  }

  if (PyModule_AddObject(m, "cfg_attr", cfg_attr_func) < 0)
  {
    Py_DECREF(cfg_attr_func);
    Py_DECREF(m);
    return NULL;
  }

  return m;
}