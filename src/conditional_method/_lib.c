#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>

/* Module level cache for decorated functions */
static PyObject *_cache = NULL;

/* TypeErrorRaiser type declaration */
typedef struct {
    PyObject_HEAD
    PyObject *f_qualnames;  /* Set of function qualnames that failed conditions */
    PyObject *qualname;     /* Qualified name for the raiser */
} TypeErrorRaiserObject;

static void
TypeErrorRaiser_dealloc(TypeErrorRaiserObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_XDECREF(self->f_qualnames);
    Py_XDECREF(self->qualname);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static int
TypeErrorRaiser_traverse(TypeErrorRaiserObject *self, visitproc visit, void *arg)
{
    Py_VISIT(self->f_qualnames);
    Py_VISIT(self->qualname);
    return 0;
}

static int
TypeErrorRaiser_clear(TypeErrorRaiserObject *self)
{
    Py_CLEAR(self->f_qualnames);
    Py_CLEAR(self->qualname);
    return 0;
}

static void
_raise_typeerror(TypeErrorRaiserObject *self)
{
    /* Clear the cache */
    if (_cache != NULL) {
        PyDict_Clear(_cache);
    }
    
    /* Join the qualnames for the error message */
    PyObject *qualnames_iter = PyObject_GetIter(self->f_qualnames);
    if (qualnames_iter == NULL) {
        return;
    }
    
    PyObject *qualnames_list = PyList_New(0);
    if (qualnames_list == NULL) {
        Py_DECREF(qualnames_iter);
        return;
    }
    
    PyObject *item;
    while ((item = PyIter_Next(qualnames_iter)) != NULL) {
        if (PyList_Append(qualnames_list, item) < 0) {
            Py_DECREF(item);
            Py_DECREF(qualnames_list);
            Py_DECREF(qualnames_iter);
            return;
        }
        Py_DECREF(item);
    }
    Py_DECREF(qualnames_iter);
    
    PyObject *separator = PyUnicode_FromString(", ");
    if (separator == NULL) {
        Py_DECREF(qualnames_list);
        return;
    }
    
    PyObject *joined_qualnames = PyUnicode_Join(separator, qualnames_list);
    Py_DECREF(separator);
    Py_DECREF(qualnames_list);
    
    if (joined_qualnames == NULL) {
        return;
    }
    
    /* Get the default qualname if the list is empty */
    const char *qualname_str = "";
    if (PyUnicode_Check(self->qualname)) {
        qualname_str = PyUnicode_AsUTF8(self->qualname);
        if (qualname_str == NULL) {
            Py_DECREF(joined_qualnames);
            return;
        }
    }
    
    /* Check if the joined qualnames is empty */
    int is_empty = (PyUnicode_GetLength(joined_qualnames) == 0);
    
    /* Format the error message */
    PyObject *error_msg;
    if (is_empty) {
        error_msg = PyUnicode_FromFormat(
            "None of the conditions is true for `%s`", 
            qualname_str
        );
    } else {
        error_msg = PyUnicode_FromFormat(
            "None of the conditions is true for `%U`", 
            joined_qualnames
        );
    }
    Py_DECREF(joined_qualnames);
    
    if (error_msg == NULL) {
        return;
    }
    
    /* Raise the TypeError */
    PyErr_SetObject(PyExc_TypeError, error_msg);
    Py_DECREF(error_msg);
}

static PyObject *
TypeErrorRaiser_call(TypeErrorRaiserObject *self, PyObject *args, PyObject *kwargs)
{
    _raise_typeerror(self);
    return NULL;
}

static PyObject *
TypeErrorRaiser_set_name(TypeErrorRaiserObject *self, PyObject *args)
{
    PyObject *owner;
    PyObject *name;
    
    if (!PyArg_ParseTuple(args, "OO", &owner, &name)) {
        return NULL;
    }
    
    _raise_typeerror(self);
    return NULL;
}

static PyObject *
TypeErrorRaiser_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    TypeErrorRaiserObject *self;
    self = (TypeErrorRaiserObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
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
    
    /* Clear the cache */
    if (_cache != NULL) {
        PyDict_Clear(_cache);
    }
    
    return (PyObject *)self;
}

static PyMethodDef TypeErrorRaiser_methods[] = {
    {"__set_name__", (PyCFunction)TypeErrorRaiser_set_name, METH_VARARGS,
     "Handle the __set_name__ protocol."},
    {NULL}  /* Sentinel */
};

static PyTypeObject TypeErrorRaiserType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "conditional_method._TypeErrorRaiser",
    .tp_doc = "Type error raiser for conditional methods",
    .tp_basicsize = sizeof(TypeErrorRaiserObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = TypeErrorRaiser_new,
    .tp_dealloc = (destructor)TypeErrorRaiser_dealloc,
    .tp_call = (ternaryfunc)TypeErrorRaiser_call,
    .tp_traverse = (traverseproc)TypeErrorRaiser_traverse,
    .tp_clear = (inquiry)TypeErrorRaiser_clear,
    .tp_methods = TypeErrorRaiser_methods,
};

/* Function to create a new TypeErrorRaiser instance */
static PyObject *
_raise_exec(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"qualname", NULL};
    PyObject *qualname = NULL;
    
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|O", kwlist, &qualname)) {
        return NULL;
    }
    
    /* Create a new TypeErrorRaiser instance */
    PyObject *raiser = PyObject_CallObject((PyObject *)&TypeErrorRaiserType, NULL);
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
static PyObject *
_get_func_name(PyObject *self, PyObject *func)
{
    PyObject *module = NULL;
    PyObject *qualname = NULL;
    PyObject *name = NULL;
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
                result = PyUnicode_FromFormat("%U.%U", module, qualname);
            }
        }
        
        if (result == NULL) {
            /* If we couldn't get the module, just use the qualname */
            result = PyUnicode_FromObject(qualname);
        }
        
        Py_XDECREF(module);
        Py_XDECREF(qualname);
        
        if (result != NULL) {
            return result;
        }
    }
    
    /* If we couldn't get the name directly, try through __wrapped__, __func__, or fget */
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

/* The core conditional method implementation */
static PyObject *
cm(PyObject *self, PyObject *args, PyObject *kwargs)
{
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
                "`@conditional_method` must be used as a decorator and `condition` must be specified as an instance of type `bool`");
            return NULL;
        }
        
        /* Create and return the inner decorator */
        PyObject *inner_func = PyObject_GetAttrString(self, "_cm_inner");
        if (inner_func == NULL) {
            return NULL;
        }
        
        return Py_BuildValue("(OO)", inner_func, condition);
    }
    
    /* If a function is provided but no condition, raise TypeError */
    if (condition == Py_None) {
        PyErr_SetString(PyExc_TypeError, 
            "`@conditional_method` must be used as a decorator and `condition` must be specified as an instance of type `bool`");
        return NULL;
    }
    
    /* Get the inner decorator and call it with the function and condition */
    PyObject *inner_func = PyObject_GetAttrString(self, "_cm_inner");
    if (inner_func == NULL) {
        return NULL;
    }
    
    PyObject *args_tuple = Py_BuildValue("(OO)", func, condition);
    if (args_tuple == NULL) {
        Py_DECREF(inner_func);
        return NULL;
    }
    
    PyObject *result = PyObject_Call(inner_func, args_tuple, NULL);
    Py_DECREF(inner_func);
    Py_DECREF(args_tuple);
    
    return result;
}

static PyObject *
_cm_inner(PyObject *self, PyObject *args)
{
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
    
    /* Evaluate the condition */
    PyObject *cond_result = NULL;
    
    if (PyCallable_Check(condition)) {
        /* If condition is callable, call it with the function */
        PyObject *args_tuple = PyTuple_New(1);
        if (args_tuple == NULL) {
            Py_DECREF(f_qualname);
            return NULL;
        }
        
        Py_INCREF(func);
        PyTuple_SET_ITEM(args_tuple, 0, func);
        
        cond_result = PyObject_CallObject(condition, args_tuple);
        Py_DECREF(args_tuple);
        
        if (cond_result == NULL) {
            /* Get the error message and format it */
            PyObject *error_type, *error_value, *error_traceback;
            PyErr_Fetch(&error_type, &error_value, &error_traceback);
            
            PyObject *error_msg = PyUnicode_FromFormat(
                "Error calling `condition` for `%U`: %S", 
                f_qualname, error_value
            );
            
            if (error_msg != NULL) {
                PyErr_SetObject(PyExc_TypeError, error_msg);
                Py_DECREF(error_msg);
            }
            
            Py_XDECREF(error_type);
            Py_XDECREF(error_value);
            Py_XDECREF(error_traceback);
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
        if (PyDict_SetItem(_cache, f_qualname, func) < 0) {
            Py_DECREF(f_qualname);
            return NULL;
        }
        Py_DECREF(f_qualname);
        Py_INCREF(func);
        return func;
    }
    
    /* If the condition is false, check if the function is in the cache */
    PyObject *cached_func = PyDict_GetItem(_cache, f_qualname);
    if (cached_func != NULL) {
        Py_DECREF(f_qualname);
        Py_INCREF(cached_func);
        return cached_func;
    }
    
    /* If the function is not in the cache, create a TypeErrorRaiser */
    PyObject *raiser = _raise_exec(self, Py_BuildValue("(O)", f_qualname), NULL);
    if (raiser == NULL) {
        Py_DECREF(f_qualname);
        return NULL;
    }
    
    /* Add the function qualname to the raiser's f_qualnames set */
    TypeErrorRaiserObject *raiser_obj = (TypeErrorRaiserObject *)raiser;
    if (PySet_Add(raiser_obj->f_qualnames, f_qualname) < 0) {
        Py_DECREF(f_qualname);
        Py_DECREF(raiser);
        return NULL;
    }
    
    Py_DECREF(f_qualname);
    return raiser;
}

/* Implementation of cfg_attr function */
static PyObject *
cfg_attr(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *func = NULL;
    PyObject *condition = Py_None;
    PyObject *decorators = NULL;
    
    static char *kwlist[] = {"", "condition", "decorators", NULL};
    
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|OOO", kwlist, &func, &condition, &decorators)) {
        return NULL;
    }
    
    /* If decorators is not provided, use an empty tuple */
    if (decorators == NULL) {
        decorators = PyTuple_New(0);
        if (decorators == NULL) {
            return NULL;
        }
    } else {
        Py_INCREF(decorators);
    }
    
    /* If func is None, return a decorator */
    if (func == NULL || func == Py_None) {
        /* If condition is not provided, raise an error */
        if (condition == Py_None) {
            PyErr_SetString(PyExc_ValueError, 
                "condition is required and must be a bool or a callable that takes the decorated function and returns a bool");
            Py_DECREF(decorators);
            return NULL;
        }
        
        /* Create a lambda that will apply cfg_attr to the decorated function */
        PyObject *lambda_args = PyTuple_New(0);
        if (lambda_args == NULL) {
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *lambda_def = PyUnicode_FromString(
            "lambda f: cfg_attr(f, condition=condition, decorators=decorators)");
        if (lambda_def == NULL) {
            Py_DECREF(lambda_args);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *globals = PyDict_New();
        if (globals == NULL) {
            Py_DECREF(lambda_def);
            Py_DECREF(lambda_args);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *locals = PyDict_New();
        if (locals == NULL) {
            Py_DECREF(globals);
            Py_DECREF(lambda_def);
            Py_DECREF(lambda_args);
            Py_DECREF(decorators);
            return NULL;
        }
        
        /* Set the variables in the locals dictionary */
        if (PyDict_SetItemString(locals, "cfg_attr", self) < 0 ||
            PyDict_SetItemString(locals, "condition", condition) < 0 ||
            PyDict_SetItemString(locals, "decorators", decorators) < 0) {
            Py_DECREF(locals);
            Py_DECREF(globals);
            Py_DECREF(lambda_def);
            Py_DECREF(lambda_args);
            Py_DECREF(decorators);
            return NULL;
        }
        
        /* Compile and evaluate the lambda */
        PyObject *code = Py_CompileString(PyUnicode_AsUTF8(lambda_def), "<string>", Py_eval_input);
        if (code == NULL) {
            Py_DECREF(locals);
            Py_DECREF(globals);
            Py_DECREF(lambda_def);
            Py_DECREF(lambda_args);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *lambda = PyEval_EvalCode(code, globals, locals);
        Py_DECREF(code);
        Py_DECREF(locals);
        Py_DECREF(globals);
        Py_DECREF(lambda_def);
        Py_DECREF(lambda_args);
        Py_DECREF(decorators);
        
        return lambda;
    }
    
    /* If func is not None and condition is true, apply the decorators */
    if (condition != Py_None && PyObject_IsTrue(condition)) {
        /* Import functools.reduce */
        PyObject *functools = PyImport_ImportModule("functools");
        if (functools == NULL) {
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *reduce = PyObject_GetAttrString(functools, "reduce");
        Py_DECREF(functools);
        
        if (reduce == NULL) {
            Py_DECREF(decorators);
            return NULL;
        }
        
        /* Define the lambda function for reduce */
        PyObject *lambda_args = PyTuple_New(0);
        if (lambda_args == NULL) {
            Py_DECREF(reduce);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *lambda_def = PyUnicode_FromString("lambda f, arg: arg(f)");
        if (lambda_def == NULL) {
            Py_DECREF(lambda_args);
            Py_DECREF(reduce);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *globals = PyDict_New();
        if (globals == NULL) {
            Py_DECREF(lambda_def);
            Py_DECREF(lambda_args);
            Py_DECREF(reduce);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *locals = PyDict_New();
        if (locals == NULL) {
            Py_DECREF(globals);
            Py_DECREF(lambda_def);
            Py_DECREF(lambda_args);
            Py_DECREF(reduce);
            Py_DECREF(decorators);
            return NULL;
        }
        
        /* Compile and evaluate the lambda */
        PyObject *code = Py_CompileString(PyUnicode_AsUTF8(lambda_def), "<string>", Py_eval_input);
        if (code == NULL) {
            Py_DECREF(locals);
            Py_DECREF(globals);
            Py_DECREF(lambda_def);
            Py_DECREF(lambda_args);
            Py_DECREF(reduce);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *lambda = PyEval_EvalCode(code, globals, locals);
        Py_DECREF(code);
        Py_DECREF(locals);
        Py_DECREF(globals);
        Py_DECREF(lambda_def);
        Py_DECREF(lambda_args);
        
        if (lambda == NULL) {
            Py_DECREF(reduce);
            Py_DECREF(decorators);
            return NULL;
        }
        
        /* Call reduce with the lambda, decorators, and func */
        PyObject *reduce_args = Py_BuildValue("(OOO)", lambda, decorators, func);
        if (reduce_args == NULL) {
            Py_DECREF(lambda);
            Py_DECREF(reduce);
            Py_DECREF(decorators);
            return NULL;
        }
        
        PyObject *result = PyObject_CallObject(reduce, reduce_args);
        Py_DECREF(reduce_args);
        Py_DECREF(lambda);
        Py_DECREF(reduce);
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
    {"_raise_exec", (PyCFunction)_raise_exec, METH_VARARGS | METH_KEYWORDS,
     "Create a TypeErrorRaiser instance."},
    {"_get_func_name", (PyCFunction)_get_func_name, METH_O,
     "Get the fully qualified name of a function."},
    {"cm", (PyCFunction)cm, METH_VARARGS | METH_KEYWORDS,
     "Conditionally select function implementations based on a runtime condition."},
    {"_cm_inner", (PyCFunction)_cm_inner, METH_VARARGS,
     "Inner implementation of the conditional method decorator."},
    {"cfg_attr", (PyCFunction)cfg_attr, METH_VARARGS | METH_KEYWORDS,
     "Conditionally apply a chain of decorators to a function."},
    {NULL, NULL, 0, NULL}  /* Sentinel */
};

/* Module definition */
static struct PyModuleDef conditionalmodule = {
    PyModuleDef_HEAD_INIT,
    "_lib",
    "Conditional method decorator module",
    -1,
    ConditionalMethodMethods
};

/* Module initialization function */
PyMODINIT_FUNC
PyInit__lib(void)
{
    /* Initialize the module */
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
    if (PyModule_AddObject(m, "_TypeErrorRaiser", (PyObject *)&TypeErrorRaiserType) < 0) {
        Py_DECREF(&TypeErrorRaiserType);
        Py_DECREF(m);
        return NULL;
    }
    
    /* Create the cache dictionary */
    _cache = PyDict_New();
    if (_cache == NULL) {
        Py_DECREF(m);
        return NULL;
    }
    
    /* Add the cache to the module */
    if (PyModule_AddObject(m, "_cache", _cache) < 0) {
        Py_DECREF(_cache);
        Py_DECREF(m);
        return NULL;
    }
    
    /* Create global aliases for the cm function */
    PyObject *cm_func = PyObject_GetAttrString(m, "cm");
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
    if (PyModule_AddObject(m, "conditional_method", cm_func) < 0) {
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
    
    return m;
}