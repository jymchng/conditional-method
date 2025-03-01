import os
import pytest
from conditional_method import conditional_method

ENV_KEY = "_conditional_method_env_"


@pytest.fixture
def debug_env_var_value():
    os.environ[ENV_KEY] = "True"
    yield os.environ[ENV_KEY]
    del os.environ[ENV_KEY]


def test_conditional_method_with_debug_env_var_normal_class(debug_env_var_value):
    assert os.environ.get(ENV_KEY, "False") == "True"

    class DoSomeWorkClass:
        def chosen_tuesday(self, one_or_two: int):
            return f"Tuesday::Two {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        def monday(self, one_or_two: int):
            return f"Monday::One {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        def monday(self, one_or_two: int):
            return f"Monday::Two {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "False"
        )
        def tuesday(self, one_or_two: int):
            return f"Tuesday::One {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "False"
        )
        def tuesday(self, one_or_two: int):
            return f"Tuesday::Three {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        def tuesday(self, one_or_two: int):
            return f"Tuesday::Four {one_or_two}"

    assert DoSomeWorkClass().monday(1) == "Monday::One 1"
    assert DoSomeWorkClass().monday(1) != "Monday::One 69"
    assert DoSomeWorkClass().tuesday(1) == "Tuesday::Four 1"
    assert DoSomeWorkClass().tuesday(69) == "Tuesday::Four 69"

    assert DoSomeWorkClass.monday(DoSomeWorkClass(), 1) == "Monday::One 1"
    assert DoSomeWorkClass.monday(DoSomeWorkClass(), 1) != "Monday::One 69"
    assert DoSomeWorkClass.tuesday(DoSomeWorkClass(), 1) == "Tuesday::Four 1"
    assert DoSomeWorkClass.tuesday(DoSomeWorkClass(), 69) == "Tuesday::Four 69"


def test_conditional_method_with_debug_env_var_normal_class_with_classmethod(
    debug_env_var_value,
):
    assert os.environ.get(ENV_KEY, "False") == "True"

    class DoSomeWorkClass:
        @classmethod
        def chosen_tuesday(cls, one_or_two: int):
            return f"Tuesday::Two {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @classmethod
        def monday(cls, one_or_two: int):
            return f"Monday::One {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @classmethod
        def monday(cls, one_or_two: int):
            return f"Monday::Two {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "False"
        )
        @classmethod
        def tuesday(cls, one_or_two: int):
            return f"Tuesday::One {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @classmethod
        def tuesday(cls, one_or_two: int):
            return f"Tuesday::Three {one_or_two}"

    assert DoSomeWorkClass.monday(1) == "Monday::One 1"
    assert DoSomeWorkClass.monday(1) != "Monday::One 69"
    assert DoSomeWorkClass.tuesday(1) == "Tuesday::Three 1"
    assert DoSomeWorkClass.tuesday(69) == "Tuesday::Three 69"


def test_conditional_method_with_debug_env_var_normal_class_with_staticmethod(
    debug_env_var_value,
):
    assert os.environ.get(ENV_KEY, "False") == "True"

    class DoSomeWorkClass:
        @staticmethod
        def chosen_tuesday(one_or_two: int):
            return f"Tuesday::Two {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @staticmethod
        def monday(one_or_two: int):
            return f"Monday::One {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @staticmethod
        def monday(one_or_two: int):
            return f"Monday::Two {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "False"
        )
        @staticmethod
        def tuesday(one_or_two: int):
            return f"Tuesday::One {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "False"
        )
        @staticmethod
        def tuesday(one_or_two: int):
            return f"Tuesday::Three {one_or_two}"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @staticmethod
        def tuesday(one_or_two: int):
            return f"Tuesday::Four {one_or_two}"

    assert DoSomeWorkClass.monday(1) == "Monday::One 1"
    assert DoSomeWorkClass.monday(1) != "Monday::One 69"
    assert DoSomeWorkClass.tuesday(1) == "Tuesday::Four 1"
    assert DoSomeWorkClass.tuesday(69) == "Tuesday::Four 69"

    assert DoSomeWorkClass().monday(1) == "Monday::One 1"
    assert DoSomeWorkClass().monday(1) != "Monday::One 69"
    assert DoSomeWorkClass().tuesday(1) == "Tuesday::Four 1"
    assert DoSomeWorkClass().tuesday(69) == "Tuesday::Four 69"


def test_conditional_method_with_debug_env_var_normal_class_with_property(
    debug_env_var_value,
):
    assert os.environ.get(ENV_KEY, "False") == "True"

    class DoSomeWorkClass:
        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @property
        def monday(self):
            return "Monday::One"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @property
        def monday(self):
            return "Monday::Two"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "False"
        )
        @property
        def tuesday(self):
            return "Tuesday::One"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "True"
        )
        @property
        def tuesday(self):
            return "Tuesday::Two"

        @conditional_method(
            condition=lambda f: os.environ.get(ENV_KEY, "False") == "False"
        )
        @property
        def tuesday(self):
            return "Tuesday::Three"

    assert DoSomeWorkClass().monday == "Monday::One"
    assert DoSomeWorkClass().monday != "Monday::Two"
    assert DoSomeWorkClass().tuesday == "Tuesday::Two"
    assert DoSomeWorkClass().tuesday != "Tuesday::Three"

    assert DoSomeWorkClass.monday is not DoSomeWorkClass.tuesday
