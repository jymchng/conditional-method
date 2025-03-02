from ._logger import logger

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import (
        Callable,
        Optional,
        TypeVar,
        Union,
        overload,
        TypeVar,
        Sequence,
        Tuple,
    )

    T = TypeVar("T", bound=Callable)
    F = TypeVar("F", bound=Callable)


def _raise_exec(qualname: str = ""):
    _inst = None

    def _raise_exec_impl(*_args, **_kwargs):
        nonlocal _inst

        if _inst is None:

            class _TypeErrorRaiser:
                __slots__ = ("f_qualnames", "__qualname__")
                __qualname__ = qualname

                def __new__(cls):
                    inst = object.__new__(cls)
                    inst.__qualname__ = qualname
                    cm._cache.clear()
                    return inst

                def __init__(self):
                    self._raise_typeerror()

                def _raise_typeerror(self):
                    nonlocal _inst
                    _inst = None

                    cm._cache.clear()
                    f_qualnames = ", ".join(self.f_qualnames)
                    raise TypeError(
                        f"None of the conditions is true for `{f_qualnames or _TypeErrorRaiser.__qualname__}`"
                    )

                def __del__(self):
                    logger.debug("__del__ is called")
                    nonlocal _inst
                    _inst = None
                    cm._cache.clear()

                def __call__(self, *_args, **_kwargs):
                    self._raise_typeerror()

                def __set_name__(self, _owner, _name):
                    logger.debug(f"__set_name__: {_owner} {_name}")
                    logger.debug(f"_owner.__dict__: {_owner.__dict__}")
                    self._raise_typeerror()

            _inst = _TypeErrorRaiser.__new__(_TypeErrorRaiser)
            _inst.f_qualnames = set()
        return _inst

    return _raise_exec_impl()


def _get_func_name(f: "Callable") -> str:
    for attr in ("__qualname__", "__name__"):
        if hasattr(f, attr):
            return f.__module__ + "." + getattr(f, attr)
    for attr in ("__wrapped__", "__func__", "fget"):
        if hasattr(f, attr):
            return _get_func_name(getattr(f, attr))
    raise TypeError("Cannot get fully qualified function name")


def _cm_impl():
    _cache = {}

    def cm(
        f: "Optional[T]" = None,
        /,
        condition: "Union[bool, Callable[[T], bool], None]" = None,
    ) -> "Optional[T]":
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

            if cond:
                _cache[f_qualname] = f
                return f

            if f_qualname in _cache:
                return _cache[f_qualname]

            inst = _raise_exec(f_qualname)
            inst.f_qualnames.add(f_qualname)

            return inst

        return cm_inner

    cm._cache = _cache
    return cm


cfg = conditional_method = if_ = cm = _cm_impl()


if TYPE_CHECKING:

    @overload
    def cfg_attr(
        f: F,
        /,
        condition: Optional[bool] = None,
        decorators: Sequence[Callable[[F], F]] = (),
    ) -> Union[F, Callable[..., None]]: ...

    @overload
    def cfg_attr(
        f: None = None,
        /,
        condition: Optional[bool] = None,
        decorators: Tuple[Callable[[F], F], ...] = (),
    ) -> Callable[[F], Union[F, Callable[..., F]]]: ...

    @overload
    def cfg_attr(
        f: None = None,
        /,
        condition: Optional[bool] = None,
        decorators: Tuple[Callable[[F], F], ...] = (),
    ) -> Callable[[F], Union[F, Callable[..., F]]]: ...


def cfg_attr(
    f: "Optional[F]" = None,
    /,
    condition: "Optional[bool]" = None,
    decorators: "Sequence[Callable[[F], F]]" = (),
) -> "Union[F, Callable[..., None], Callable[[F], Union[F, Callable[..., None]]]]":
    """
    Conditionally apply a chain of decorators to a function.

    This decorator allows for conditional application of one or more decorator functions
    to a target function. If the condition is True, the chain of decorators is applied.
    If the condition is False, the function is returned unchanged.

    Args:
        f: The function to be decorated. If None, returns a decorator that can be applied to a function.
        condition: Boolean condition determining whether the decorators should be applied.
                  Required when f is None.
        decorators: A sequence of decorator functions to apply to f if condition is True.
                   Decorators are applied in the order provided.

    Returns:
        If condition is True: The decorated function after applying all decorators.
        If condition is False: The function is returned unchanged.
        If f is None: A decorator function that can be applied to another function.

    Raises:
        ValueError: If condition is None when creating a decorator (f is None).

    Examples:
        ```python
        # Apply decorators only when condition is True
        @cfg_attr(condition=True, decorators=[my_decorator])
        def my_function():
            pass
        ```
    """
    if f is None:
        # if condition is not provided, raise an error because we need a condition to create a decorator
        if condition is None:
            raise ValueError(
                "condition is required and must be a bool or a callable that takes the decorated function and returns a bool"
            )
        # return a decorator that can be applied to a function
        return lambda f: cfg_attr(f, condition=condition, decorators=decorators)

    if f is not None and condition:
        from functools import reduce

        # apply all decorators to the function
        return reduce(lambda f, arg: arg(f), decorators, f)

    return f  # without applying any decorators
