from ._logger import logger

TYPE_CHECKING = False
TYPE_EXTENSION_EXISTS = False
if TYPE_CHECKING:
    try:
        import typing_extensions

        _ = typing_extensions
        TYPE_EXTENSION_EXISTS = True
    except ImportError:
        pass

if TYPE_EXTENSION_EXISTS and TYPE_CHECKING:
    from typing import (
        Callable,
        Optional,
        TypeVar,
        Union,
        overload,
        TypeVar,
        Sequence,
        Tuple,
        Literal,
        NoReturn,
        Any,
        Type,
    )
    from typing_extensions import Never

    T = TypeVar("T", Callable, Type)
    F = TypeVar("F", bound=Callable)
    ExceptionT = TypeVar("ExceptionT", bound=Exception)
    RaisingT = TypeVar("RaisingT", bound=Callable[[Any], NoReturn])


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
                    cfg_attr._cache.clear()
                    return inst

                def __init__(self):
                    self._raise_typeerror()

                def _raise_typeerror(self):
                    nonlocal _inst
                    _inst = None

                    cm._cache.clear()
                    cfg_attr._cache.clear()
                    f_qualnames = ", ".join(self.f_qualnames)
                    raise TypeError(
                        f"None of the conditions is true for `{f_qualnames or _TypeErrorRaiser.__qualname__}`"
                    )

                def __del__(self):
                    logger.debug("__del__ is called")
                    nonlocal _inst
                    _inst = None
                    cm._cache.clear()
                    cfg_attr._cache.clear()

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


def _get_mod_qual_func_name(f: "Callable") -> str:
    for attr in ("__qualname__", "__name__"):
        if hasattr(f, attr):
            some_name = getattr(f, attr)
            if not isinstance(some_name, str):
                continue
            return f.__module__ + "." + some_name
    for attr in ("__wrapped__", "__func__", "fget"):
        if hasattr(f, attr):
            return _get_mod_qual_func_name(getattr(f, attr))
    logger.debug("f: ", f, " f.__module__: ", f.__module__, " f.__name__: ", f.__name__)
    raise TypeError("Cannot get fully qualified function name")


def _cm_impl():
    _cache = {}

    if TYPE_CHECKING:

        @overload
        def cm(f: None, /, condition: None = None) -> Never: ...

        @overload
        def cm(
            f: None, /, condition: Callable[[T], bool]
        ) -> Callable[[T], Union[Callable[[T], T], Callable[[Any, Any], Never]]]: ...

        @overload
        def cm(f: None, /, condition: Literal[True]) -> Callable[[T], T]: ...

        @overload
        def cm(
            f: None, /, condition: Literal[False]
        ) -> Callable[[T], Callable[[Any, Any], Never]]: ...

        @overload
        def cm(f: T, /, condition: Literal[True]) -> T: ...

        @overload
        def cm(f: T, /, condition: Literal[False]) -> Callable[[Any, Any], Never]: ...

        @overload
        def cm(
            f: T, /, condition: Callable[[T], bool]
        ) -> Union[
            T, Callable[[Any, Any], Never], Callable[[T], Callable[[Any, Any], Never]]
        ]: ...

    def cm(
        f: "Optional[T]" = None,
        /,
        condition: "Union[bool, Callable[[T], bool], None]" = None,
    ) -> "Optional[T]":
        """Conditionally select function implementations based on a runtime condition.
        This decorator enables defining multiple implementations of a function with the same name,
        where only one implementation is selected based on the provided condition. The condition
        is evaluated when the decorator is applied, not when the function is called.

        Args:

            f: The function to decorate.
            condition: Boolean value or callable that determines if this implementation is used.
            If callable, it will be passed the function and should return a boolean.

        Returns:
            The original function if condition is True, a cached implementation if available,
            or a placeholder that raises TypeError when called.
        Raises:

            TypeError: When used without a condition parameter.

        Example:
        ```python
        import pytest
        from conditional_method import cfg

        @cfg(condition=lambda f: f.__name__.startswith("test_"))
        def test_func():
            return "result"

        assert test_func() == "result"

        @cfg(condition=lambda f: f.__name__.startswith("test_"))
        def non_matching_func():
            return "result"

        with pytest.raises(TypeError):
            non_matching_func()
        ```
        """
        if condition is None:
            raise TypeError(
                "`@conditional_method` must be used as a decorator and `condition` must be specified as an instance of type `bool`"
            )

        def cm_inner(f):
            f_qualname = _get_mod_qual_func_name(f)
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


def _cfg_attrs_impl() -> (
    "Union[F, Callable[..., None], Callable[[F], Union[F, Callable[..., None]]]]"
):
    _cache = {}

    def _cfg_attr_inner(
        f: "Optional[F]" = None,
        /,
        condition: "Optional[bool]" = None,
        decorators: "Sequence[Callable[[F], F]]" = (),
    ):
        """Conditionally apply a chain of decorators to a function.

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
        if f is None and condition is None:
            raise ValueError(
                "`condition` is required and must be a bool or a callable that takes the decorated function and returns a bool"
            )

        if condition is None:
            raise TypeError(
                "`condition` is required and must be a bool or a callable that takes the decorated function and returns a bool"
            )

        logger.debug("f: ", f, " condition: ", condition, " decorators: ", decorators)

        def _cfg_attr_inner_true(
            f: "Callable",
        ):
            logger.debug("inside `_cfg_attr_inner_true`")
            from functools import reduce

            f_qualname: str = _get_mod_qual_func_name(f)
            logger.debug("f_qualname: ", f_qualname)
            logger.debug("f before `reduce`: ", f)
            f = reduce(lambda f, arg: arg(f), reversed(decorators), f)
            _cache[f_qualname] = f
            logger.debug(
                "Resultant `f`: ",
                f,
                " decorators: ",
                decorators,
                " f_qualname: ",
                f_qualname,
            )
            return f

        def _cfg_attr_inner_false(
            f: "Callable",
        ):
            logger.debug("inside `_cfg_attr_inner_false`")
            f_qualname: str = _get_mod_qual_func_name(f)
            logger.debug("f_qualname: ", f_qualname)
            if f_qualname in _cache:
                return _cache[f_qualname]
            inst = _raise_exec(f_qualname)
            inst.f_qualnames.add(f_qualname)
            return inst

        if not callable(condition):
            logger.debug("condition: ", condition, " and is not callable ")
            if condition:
                logger.debug("returning `_cfg_attr_inner_true`")
                if f is None:
                    return _cfg_attr_inner_true
                return _cfg_attr_inner_true(f)
            logger.debug("returning `_cfg_attr_inner_false`")
            if f is None:
                return _cfg_attr_inner_false
            return _cfg_attr_inner_false(f)

        def _cm_attrs_inner_callable(f):
            logger.debug("inside `_cm_attrs_inner_callable`")
            logger.debug("condition: ", condition, " and is callable ")
            f_qualname: str = _get_mod_qual_func_name(f)
            try:
                cond = bool(condition(f))
            except TypeError as e:
                raise TypeError(
                    f"Error calling `condition` for `{f_qualname}`: {e}"
                ) from e
            if cond:
                return _cfg_attr_inner_true(f)
            return _cfg_attr_inner_false(f)

        logger.debug(
            "returning `_cm_attrs_inner_callable`",
            " condition: ",
            condition,
            " and is callable ",
        )
        return _cm_attrs_inner_callable

    _cfg_attr_inner._cache = _cache
    return _cfg_attr_inner


cfg_attr = _cfg_attrs_impl()
