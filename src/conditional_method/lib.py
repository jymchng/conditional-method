from functools import wraps
from weakref import WeakValueDictionary
from src.conditional_method._logger import logger

UNDEFINED = object()

def immediately_invoke(f):
    return f()

@immediately_invoke
def _get_dispatcher_class():
    
    _cache = WeakValueDictionary()
    
    def _get_dispatcher_class_impl(func_name: str):
        if func_name in _cache:
            return _cache[func_name]
        
        class Dispatcher:
            __slots__ = ('conditions', 'func', 'resolved')
            _instance = UNDEFINED
            conditions: list
            
            def __new__(cls, _func, _condition):
                if cls._instance is UNDEFINED:
                    inst = object.__new__(cls)
                    inst.conditions = []
                    inst.resolved = False
                    # so that for each (Type, Method), there is only one descriptor instance handling it
                    cls._instance = inst
                return cls._instance
            
            def __set_name__(self, owner, name):
                if not any(self.conditions):
                    raise ValueError(f"At least one condition must be True for the `@src.conditional_method` decorator decorated on method: `.{name}(..)` for the class `{owner.__name__}`; the conditions are: `{self.conditions}`")
                getattr(owner, name)
                setattr(owner, name, self.func)
                
                
            def __init__(self, func, condition):
                self.conditions.append(condition)
                
                # TODO: uncomment this if want to raise an error if more than one condition is True
                # if (sum(self.conditions) > 1):
                #     err_msg = f"Only one condition can be True for the `@src.conditional_method` decorator decorated on method: `{func.__qualname__}(..)`;"
                #     raise ValueError(err_msg)
                
                if condition and not hasattr(self, "func"):
                    self.func = func
                
                
            def __get__(self, inst, owner):
                if hasattr(self, "func"):
                    return self.func
                return self
        
        _cache[func_name] = Dispatcher
        
        return Dispatcher
    
    return _get_dispatcher_class_impl

def _get_dunder_get_of_f(f):
    
    if hasattr(f, '__get__'):
        return _get_dunder_get_of_f(f.__get__)
    return f
        
def conditional_method(func=None, *, condition=None):
    
    err_msg = ""
    if func is None and condition is None:
        err_msg += "`@conditional_method` must used with one keyword argument named `condition` and/or it must be used as a decorator;\n"
        raise ValueError(err_msg)
    if func is None:
        return lambda func: conditional_method(func, condition=condition)
    if condition is None:
        err_msg += "`condition` must be specified as either a callable or a boolean;\n"
    if not callable(condition) and not isinstance(condition, bool):
        err_msg += "`condition` must be specified as either a callable or a boolean;\n"
    if err_msg:
        raise ValueError(err_msg)
    
    if callable(condition):
        try:
            condition = condition()
        except TypeError as err:
            err_msg += f"Error occurred while trying to call the callable `condition`: {condition};\nThe callable must have any parameters;\n"
            err_msg += str(err)
            raise ValueError(err_msg)
        
    func_name = _get_func_name(func)
    
    dispatcher_class = _get_dispatcher_class(func_name=func_name)
    
    descriptor_inst = dispatcher_class(func, condition)
    
    try:
        wraps(func)(descriptor_inst)
    except AttributeError as err:
        pass
    return descriptor_inst

def _get_func_name(func):
    if hasattr(func, "__qualname__"):
        return func.__qualname__
    if hasattr(func, "__name__"):
        return func.__name__
    if hasattr(func, "__wrapped__"):
        return _get_func_name(func.__wrapped__)
    if hasattr(func, "__func__"):
        return _get_func_name(func.__func__)
    if hasattr(func, "fget"):
        return _get_func_name(func.fget)
    if hasattr(func, "__get__"):
        return _get_func_name(func.__get__)
    raise ValueError(f"`func` = {func} must have a `__qualname__` or `__name__` attribute")

