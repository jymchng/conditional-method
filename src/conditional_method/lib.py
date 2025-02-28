from functools import wraps
from weakref import WeakValueDictionary
from conditional_method._logger import logger

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
            resolved: bool
            
            def __new__(cls, _func, _condition):
                logger.debug("="* 5 + " Start of `Dispatcher.__new__` " + "="*5)
                if cls._instance is UNDEFINED:
                    inst = object.__new__(cls)
                    inst.conditions = []
                    inst.resolved = False
                    # so that for each (Type, Method), there is only one descriptor instance handling it
                    logger.debug("Before `cls._instance = inst`; inst = ", inst)
                    
                    cls._instance = inst
                    logger.debug("After `cls._instance = inst`; cls._instance: ", cls._instance, "; inst: ", inst)
                logger.debug("Returning `cls._instance`: ", cls._instance)
                logger.debug("="* 5 + " End of `Dispatcher.__new__` " + "="*5)
                return cls._instance
            
            def __set_name__(self, owner, name):
                logger.debug("="* 5 + " Start of `__set_name__` " + "="*5)
                logger.debug("owner: ", owner)
                logger.debug("owner.__dict__: ", owner.__dict__)
                logger.debug("name: ", name)
                logger.debug("self.conditions: ", self.conditions)
                if not any(self.conditions):
                    raise ValueError(f"At least one condition must be True for the `@conditional_method` decorator decorated on method: `.{name}(..)` for the class `{owner.__name__}`; the conditions are: `{self.conditions}`")
                self.resolved = True
                self.resolved # trigger `__get__`
                getattr(owner, name)
                setattr(owner, name, self.func)
                logger.debug("owner.__dict__: ", owner.__dict__)
                # logger.debug("`self.resolved` is set to `True`")
                logger.debug("="* 5 + " End of `__set_name__` " + "="*5)
            def __init__(self, func, condition):
                logger.debug("="* 5 + " Start of `__init__` " + "="*5)
                self.conditions.append(condition)
                logger.debug("self.conditions: ", self.conditions)
                
                # if (sum(self.conditions) > 1):
                #     err_msg = f"Only one condition can be True for the `@conditional_method` decorator decorated on method: `{func.__qualname__}(..)`;"
                #     raise ValueError(err_msg)
                
                if condition and not hasattr(self, "func"):
                    logger.debug("condition is: ", condition, " self.func: ", func)
                    self.func = func
                    logger.debug("self.func: ", self.func)
                
                logger.debug("="* 5 + " End of `__init__` " + "="*5)
                
            def __get__(self, inst, owner):
                logger.debug("="* 5 + " Start of `__get__` " + "="*5)
                logger.debug("inst: ", inst)
                logger.debug("owner: ", owner)
                # if self.resolved:
                #     # if isinstance(self.func, (type(logger.debug), type(immediately_invoke))):
                #     #     return self.func
                #     logger.debug("`self.resolved` is True, returning: `_get_dunder_get_of_f(self.func)(inst, owner)`", _get_dunder_get_of_f(self.func)(inst, owner))
                    
                #     return _get_dunder_get_of_f(self.func)(inst, owner)
                if hasattr(self, "func"):
                    logger.debug("owner.__dict__: ", owner.__dict__)
                    logger.debug("Returning `self.func.__get__(inst, owner)`", _get_dunder_get_of_f(self.func)(inst, owner))
                    logger.debug("="* 5 + " End of `__get__` " + "="*5)
                    return self.func
                logger.debug("Returning `self`: ", self)
                logger.debug("="* 5 + " End of `__get__` " + "="*5)
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
    logger.debug("func_name: ", func_name)
    
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

import os

os.environ["DEBUG"] = "True"

class A:
    """The correct `.monday(..)` is a `classmethod`"""
    __slots__ = ()
    
    @conditional_method(condition=True)
    def monday(self):
        return "Instance of A " + "A::Monday"
        
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "False")
    def monday(self):
        return "Instance of A " + "A::Another Monday"
    
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "True")
    @classmethod
    def monday(cls):
        return "Class of A " + "A::Yet Another Monday"
    
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "True") # this is ignored
    @staticmethod
    def monday():
        return "Staticmethod of A" + "A::Yet Another Good Monday"
    
   
    def tuesday(self):
        return "Instance of A " + "A::Tuesday"
    
class B:
    """The correct `.monday(..)` is a regular instance method"""
    __slots__ = ()
    
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "False")
    def monday(self):
        return "Instance of B" + "B::Monday"
        
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "True")
    def monday(self):
        return "Instance of B" + "B::Another Monday"
    
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "False")
    def monday(self):
        return "Instance of B" + "B::Yet Another Monday"
    
    def tuesday(self):
        return "Instance of B" + "B::Tuesday"
    
class C:
    """The correct `.monday(..)` is a `staticmethod`"""
    __slots__ = ()
    
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "False")
    def monday(self):
        return "Instance of C" + "C::Monday"
        
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "True")
    @staticmethod
    def monday():
        return "Staticmethod of C" + "C::Another Monday"
    
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "False")
    def monday(self):
        return "Instance of C" + "C:: Yet Monday"
    
    def tuesday(self):
        return "Instance of C" + "C::Tuesday"
    

class D:
    """The correct `.monday(..)` is a regular instance method but it is the last `.monday(..)` method defined"""
    __slots__ = ()
    
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "False")
    def monday(self):
        return "Instance of D" + "D::Monday"
        
    @conditional_method(condition=lambda : os.environ.get("DEBUG", "False") == "True")
    def monday(self):
        return "Instance of D" + "D::Another Monday"
       
    def tuesday(self):
        return "Instance of D" + "D::Tuesday"
    
    
logger.debug("A.__dict__: ", A.__dict__)
logger.debug("B.__dict__: ", B.__dict__)
logger.debug("C.__dict__: ", C.__dict__)
logger.debug("D.__dict__: ", D.__dict__)
        
logger.debug(A.monday(A()))
logger.debug(B.monday(B()))

logger.debug(B.monday(B()))
logger.debug(A.monday(A()))

logger.debug(A().monday())
logger.debug(B().monday())

logger.debug(B().monday())
logger.debug(A().monday())

assert _get_dispatcher_class(func_name="A") is not _get_dispatcher_class(func_name="B")
assert _get_dispatcher_class(func_name="A") is _get_dispatcher_class(func_name="A")
assert _get_dispatcher_class(func_name="B") is _get_dispatcher_class(func_name="B")

assert id(A()) == id(B())

logger.debug(B.tuesday(B()))
logger.debug(A.tuesday(A()))

logger.debug(A().tuesday())
logger.debug(B().tuesday())

class G:
    
    @staticmethod
    def monday():
        return "Staticmethod of G" + "G::Monday"
    
logger.debug(G.monday())
logger.debug(G().monday())

logger.debug(C().monday())
logger.debug(C.monday())

logger.debug(D.monday(D()))
logger.debug(D().monday())
