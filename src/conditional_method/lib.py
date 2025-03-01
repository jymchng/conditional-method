from ._logger import logger

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import (
        Callable,
        TypeVar,
    )

    T = TypeVar("T", bound=Callable)


def _raise_exec():
    _inst = None

    def _raise_exec_impl(*_args, **_kwargs):
        nonlocal _inst

        if _inst is None:

            class _TypeErrorRaiser:
                __slots__ = ("f_qualnames",)

                def __init__(self):
                    self._raise_typeerror()

                def _raise_typeerror(self):
                    nonlocal _inst
                    _inst = None

                    f_qualnames = ", ".join(self.f_qualnames)
                    cm._cache.clear()
                    raise TypeError(
                        f"None of the conditions is true for `{f_qualnames}`"
                    )

                def __call__(self, *_args, **_kwargs):
                    self._raise_typeerror()

                def __set_name__(self, _owner, _name):
                    logger.debug(f"__set_name__: {_owner} {_name}")
                    logger.debug(f"_owner.__dict__: {_owner.__dict__}")
                    self._raise_typeerror()

            _inst = object.__new__(_TypeErrorRaiser)
            _inst.f_qualnames = set()
        return _inst

    return _raise_exec_impl()


def _get_func_name(f: "Callable") -> str:
    for attr in ("__qualname__", "__name__", ""):
        if hasattr(f, attr):
            return f.__module__ + "." + getattr(f, attr)
    for attr in ("__wrapped__", "__func__", "fget"):
        if hasattr(f, attr):
            return _get_func_name(getattr(f, attr))
    raise TypeError("Cannot get function name")


def _cm_impl():
    _cache = {}

    def cm(
        f=None,
        /,
        condition=None,
    ):
        if condition is None:
            raise TypeError(
                "`@conditional_method` must be used as a decorator and `condition` must be specified as an instance of type `bool`"
            )

        def cm_inner(f):
            nonlocal _cache

            f_qualname = _get_func_name(f)
            logger.debug(f"f_qualname: {f_qualname} in cm_inner")

            if callable(condition):
                try:
                    cond = condition(f)
                except TypeError as e:
                    raise TypeError(
                        f"Error calling `condition` for `{f_qualname}`: {e}"
                    ) from e
            else:
                cond = bool(condition)

            if f_qualname in _cache:
                return _cache.get(f_qualname)

            if cond:
                _cache[f_qualname] = f
                logger.debug(f"_cache: {_cache}")
                logger.debug(
                    f"f_qualname: {f_qualname} is in _cache and cond is true and f is {f} and returning f"
                )
                return f

            inst = _raise_exec()
            inst.f_qualnames.add(f_qualname)
            return inst

        return cm_inner

    cm._cache = _cache
    return cm


conditional_method = if_ = cm = _cm_impl()
