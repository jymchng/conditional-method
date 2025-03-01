ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER = "__conditional_method_debug__"
TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any, Callable, TypeVar
    from logging import Logger

    T = TypeVar("T")


def _make_noop_logger() -> "Logger":
    class NoopLogger:
        def __getattribute__(self, _name: str) -> "Callable[[Any, Any], Any]":
            return lambda *args, **kwargs: None

        def __bool__(self) -> bool:
            return False

    return NoopLogger()


def immediately_invoke(f: "Callable[[], 'T']") -> "T":
    return f()


@immediately_invoke
def logger():
    import os

    # Print debug information to help diagnose the issue
    env_value = os.environ.get(ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER, "false")

    if env_value.lower() == "false":
        return _make_noop_logger()

    import logging

    # Configure logging before creating the logger
    logging.basicConfig(
        level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger("conditional_method")
