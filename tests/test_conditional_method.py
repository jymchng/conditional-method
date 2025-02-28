import os
import pytest
from conditional_method.lib import conditional_method, _get_func_name

ENV_KEY = "_conditional_method_env_"

@pytest.fixture
def set_debug_env_var():
    os.environ[ENV_KEY] = "True"
    yield
    del os.environ[ENV_KEY]
    


def test_conditional_method_with_debug_env_var_normal_class(set_debug_env_var):
    
    class DoSomeWorkClass:
        
        def chosen_tuesday(self, one_or_two: int):
            return f"Tuesday::Two {one_or_two}"

        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        def monday(self, one_or_two: int):
            return f"Monday::One {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        def monday(self, one_or_two: int):
            return f"Monday::Two {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        def tuesday(self, one_or_two: int):
            return f"Tuesday::One {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        def tuesday(self, one_or_two: int):
            return f"Tuesday::Three {one_or_two}"
        
        setattr(chosen_tuesday, "__qualname__", getattr(chosen_tuesday, "__qualname__").replace("chosen_tuesday", "tuesday"))
        conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")(chosen_tuesday)
        
    assert DoSomeWorkClass.tuesday is DoSomeWorkClass.chosen_tuesday
    assert DoSomeWorkClass().monday(1) == "Monday::One 1"
    assert DoSomeWorkClass().monday(1) != "Monday::One 69"
    assert DoSomeWorkClass().tuesday(1) == "Tuesday::Two 1"
    assert DoSomeWorkClass().tuesday(69) == "Tuesday::Two 69"
    
    assert DoSomeWorkClass.tuesday is DoSomeWorkClass.chosen_tuesday
    assert DoSomeWorkClass.monday(DoSomeWorkClass(), 1) == "Monday::One 1"
    assert DoSomeWorkClass.monday(DoSomeWorkClass(), 1) != "Monday::One 69"
    assert DoSomeWorkClass.tuesday(DoSomeWorkClass(), 1) == "Tuesday::Two 1"
    assert DoSomeWorkClass.tuesday(DoSomeWorkClass(), 69) == "Tuesday::Two 69"
    
def test_conditional_method_with_debug_env_var_normal_class_with_classmethod(set_debug_env_var):
    
    class DoSomeWorkClass:
        
        @classmethod
        def chosen_tuesday(cls, one_or_two: int):
            return f"Tuesday::Two {one_or_two}"

        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        @classmethod
        def monday(cls, one_or_two: int):
            return f"Monday::One {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        @classmethod
        def monday(cls, one_or_two: int):
            return f"Monday::Two {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        @classmethod
        def tuesday(cls, one_or_two: int):
            return f"Tuesday::One {one_or_two}"
        
        setattr(chosen_tuesday, "__qualname__", _get_func_name(chosen_tuesday).replace("chosen_tuesday", "tuesday"))
        conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")(chosen_tuesday)
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        @classmethod
        def tuesday(cls, one_or_two: int):
            return f"Tuesday::Three {one_or_two}" 
        
    assert DoSomeWorkClass.monday(1) == "Monday::One 1"
    assert DoSomeWorkClass.monday(1) != "Monday::One 69"
    assert DoSomeWorkClass.tuesday(1) == "Tuesday::Two 1"
    assert DoSomeWorkClass.tuesday(69) == "Tuesday::Two 69"
        
def test_conditional_method_with_debug_env_var_normal_class_with_staticmethod(set_debug_env_var):
    
    class DoSomeWorkClass:
        
        @staticmethod
        def chosen_tuesday(one_or_two: int):
            return f"Tuesday::Two {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        @staticmethod
        def monday(one_or_two: int):
            return f"Monday::One {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        @staticmethod
        def monday(one_or_two: int):
            return f"Monday::Two {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        @staticmethod
        def tuesday(one_or_two: int):
            return f"Tuesday::One {one_or_two}"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        @staticmethod
        def tuesday(one_or_two: int):
            return f"Tuesday::Three {one_or_two}" 
       
        setattr(chosen_tuesday, "__qualname__", _get_func_name(chosen_tuesday).replace("chosen_tuesday", "tuesday"))
        conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")(chosen_tuesday)
        
    assert DoSomeWorkClass.tuesday is DoSomeWorkClass.chosen_tuesday
    assert DoSomeWorkClass.monday(1) == "Monday::One 1"
    assert DoSomeWorkClass.monday(1) != "Monday::One 69"
    assert DoSomeWorkClass.tuesday(1) == "Tuesday::Two 1"
    assert DoSomeWorkClass.tuesday(69) == "Tuesday::Two 69"
    
    assert DoSomeWorkClass.tuesday is DoSomeWorkClass.chosen_tuesday
    assert DoSomeWorkClass().monday(1) == "Monday::One 1"
    assert DoSomeWorkClass().monday(1) != "Monday::One 69"
    assert DoSomeWorkClass().tuesday(1) == "Tuesday::Two 1"
    assert DoSomeWorkClass().tuesday(69) == "Tuesday::Two 69"
    
    
def test_conditional_method_with_debug_env_var_normal_class_with_property(set_debug_env_var):
    
    class DoSomeWorkClass:
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        @property
        def monday(self):
            return f"Monday::One"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        @property
        def monday(self):
            return f"Monday::Two"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        @property
        def tuesday(self):
            return f"Tuesday::One"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "True")
        @property
        def tuesday(self):
            return f"Tuesday::Two"
        
        @conditional_method(condition=lambda : os.environ.get(ENV_KEY, "False") == "False")
        @property
        def tuesday(self):
            return f"Tuesday::Three"
        
    assert DoSomeWorkClass().monday == "Monday::One"
    assert DoSomeWorkClass().monday != "Monday::Two"
    assert DoSomeWorkClass().tuesday == "Tuesday::Two"
    assert DoSomeWorkClass().tuesday != "Tuesday::Three"
    
    assert DoSomeWorkClass.monday is not DoSomeWorkClass.tuesday