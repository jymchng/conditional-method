import pytest


@pytest.fixture(autouse=True)
def ENV_value():
    import os

    os.environ["ENV"] = "LOCAL"
    yield os.environ["ENV"]
    del os.environ["ENV"]


def test_imports_fn(ENV_value):
    from .imports_fn import env

    assert env() == "LOCAL"


def test_imports_fn_two(ENV_value):
    from .imports_fn_two import env

    with pytest.raises(TypeError):
        assert env() == "LOCAL"
