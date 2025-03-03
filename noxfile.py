from functools import wraps
import nox
from nox.sessions import Session
from nox import session as nox_session
import shutil

try:
    import tomli as tomllib

    _ = tomllib
except ImportError:
    pass

TYPE_CHECKING = False
TYPE_EXTENSIONS_IMPORTED = False
if TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Sequence,
        TypedDict,
        Union,
        Optional,
        Dict,
        overload,
        Literal,
    )

    try:
        from typing_extensions import NotRequired

        TYPE_EXTENSIONS_IMPORTED = True
    except ImportError:
        pass

if TYPE_EXTENSIONS_IMPORTED and TYPE_CHECKING:

    class NoxSessionParams(TypedDict):
        """Type hints for Nox session parameters.

        Attributes:
            func: The function to be executed in the session
            python: Python version(s) to use
            py: Alias for python parameter
            reuse_venv: Whether to reuse the virtual environment
            name: Name of the session
            venv_backend: Backend to use for virtual environment
            venv_params: Additional parameters for virtual environment creation
            tags: Tags associated with the session
            default: Whether this is a default session
            requires: Required dependencies for the session
        """

        func: NotRequired[Optional[Union[Callable[..., Any], "Func"]]]  # type: ignore
        python: NotRequired[Optional["PythonVersion"]]  # type: ignore
        py: NotRequired[Optional["PythonVersion"]]  # type: ignore
        reuse_venv: NotRequired[Optional[bool]]
        name: NotRequired[Optional[str]]
        venv_backend: NotRequired[Optional[Any]]
        venv_params: NotRequired[Sequence[str]]
        tags: NotRequired[Optional[Sequence[str]]]
        default: NotRequired[bool]
        requires: NotRequired[Optional[Sequence[str]]]

    Func = Callable[..., Any]
    PythonVersion = Literal["3.8", "3.9", "3.10", "3.11", "3.12"]

    class ExtraSessionParams(TypedDict):
        """Type hints for extra session parameters.

        Attributes:
            dependency_group: Group to run the session in
        """

        dependency_group: NotRequired[Optional[str]]
        environment_mapping: NotRequired[Optional[Dict[str, str]]]
        default_posargs: NotRequired[Optional[Sequence[str]]]

    class SessionParams(NoxSessionParams, ExtraSessionParams):
        """Type hints for **all** session parameters."""

    @overload
    def session(
        f: Callable[..., Any],
        /,
        dependency_group: str = None,
        environment_mapping: "Dict[str, str]" = {},
        default_posargs: "Sequence[str]" = (),
        **kwargs: NoxSessionParams,
    ) -> Callable[..., Any]: ...

    @overload
    def session(
        f: None = None,
        /,
        dependency_group: str = None,
        environment_mapping: "Dict[str, str]" = {},
        default_posargs: "Sequence[str]" = (),
        **kwargs: NoxSessionParams,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...


import nox
from nox.sessions import Session
from nox import session as nox_session


DEFAULT_SESSION_KWARGS: "NoxSessionParams" = {
    "reuse_venv": True, # probably want to reuse it so that you don't keep recreating it
    # you can also pass in other kwargs to nox_session, e.g. pinning a python version
}
MANIFEST_FILENAME = "pyproject.toml"


def uv_install_group_dependencies(session: Session, dependency_group: str):
    pyproject = nox.project.load_toml(MANIFEST_FILENAME)
    dependencies = nox.project.dependency_groups(pyproject, dependency_group)
    session.install(*dependencies)
    session.log(f"Installed dependencies: {dependencies} for {dependency_group}")


class AlteredSession(Session):
    __slots__ = (
        "session",
        "dependency_group",
        "environment_mapping",
        "default_posargs",
    )

    def __init__(
        self,
        session: Session,
        dependency_group: str,
        environment_mapping: "Dict[str, str]",
        default_posargs: "Sequence[str]",
    ):
        super().__init__(session._runner)
        self.dependency_group = dependency_group
        self.environment_mapping = environment_mapping
        self.default_posargs = default_posargs
        self.session = session

    def run(self, *args, **kwargs):
        if self.dependency_group is not None:
            uv_install_group_dependencies(self, self.dependency_group)
        if self.session.posargs is not None:
            args = (*args, *(self.session.posargs or self.default_posargs))
        if "env" in kwargs:
            kwargs.pop("env")
        return self.session.run(*args, env=self.environment_mapping or {}, **kwargs)


def session(
    f: "Callable[..., Any]" = None,
    /,
    dependency_group: str = None,
    environment_mapping: "Dict[str, str]" = {},
    default_posargs: "Sequence[str]" = (),
    **kwargs: "NoxSessionParams",
) -> "Callable[..., Any]":
    if f is None:
        return lambda f: session(
            f,
            dependency_group=dependency_group,
            environment_mapping=environment_mapping,
            default_posargs=default_posargs,
            **kwargs,
        )
    nox_session_kwargs = {
        **DEFAULT_SESSION_KWARGS,
        **kwargs,
    }

    if dependency_group or environment_mapping or default_posargs:

        @wraps(f)
        def wrapper(session: Session, *args, **kwargs):
            altered_session = AlteredSession(
                session, dependency_group, environment_mapping, default_posargs
            )
            return f(altered_session, *args, **kwargs)

        return nox_session(wrapper, **nox_session_kwargs)
    return nox_session(f, **nox_session_kwargs)


# you can either run `nox -s test` or `nox -s test -- tests/test_cfg.py -s -vv`
# former will run all tests (default being: `tests -s -vv`, i.e. test the entire test suite)
# latter will run a single test, e.g. a specific test file (tests/test_cfg.py), or a specific test function, etc.

# dependency_group is used to install the dependencies for the test session
# default_posargs is used to pass additional arguments to the test session
@session(dependency_group="test", default_posargs=["tests", "-s", "-vv"])
def test(session: Session):
    command = [
        shutil.which("uv"),
        "run",
        "--group",
        "test",
        "python",
        "-m",
        "pytest",
    ]
    session.run(*command)


@session(
    dependency_group="examples", default_posargs=["examples/scratchpad.py",]
)
def scratchpad(session: Session):
    command = [
        shutil.which("uv"),
        "run",
        "--group",
        "examples",
        "python",
        "-m",
    ]
    session.run(*command)


@session(
    dependency_group="examples",
    environment_mapping={"ENVIRONMENT_KEY": "staging"},
    default_posargs=["examples/fastapi_auth_staging.py", "-s", "-vv"],
)
def test_staging(session: Session):
    session.run(
        "uv",
        "run",
        "--group",
        "examples",
        "python",
        "-m",
        "pytest",
    )


@session(
    dependency_group="examples",
    environment_mapping={"ENVIRONMENT_KEY": "production"},
    default_posargs=["examples/fastapi_auth_prod.py", "-s", "-vv"],
)
def test_production(session: Session):
    session.run(
        "uv",
        "run",
        "--group",
        "examples",
        "python",
        "-m",
        "pytest",
    )


@session(
    dependency_group="examples",
    environment_mapping={"ENVIRONMENT_KEY": "development"},
    default_posargs=["examples/fastapi_auth_dev.py", "-s", "-vv"],
)
def test_development(session: Session):
    session.run(
        "uv",
        "run",
        "--group",
        "examples",
        "python",
        "-m",
        "pytest",
    )


@session(
    dependency_group="examples",
)
def fastapi_auth(session: Session):
    test_development(session)
    test_staging(session)
    test_production(session)


@session(
    dependency_group="dev",
)
def format(session: Session):
    # clang-format only c files
    # use glob to find all c files
    import os
    import glob

    # Check if the directory exists before trying to format files
    c_files_path = "src/conditional_method"
    if not os.path.exists(c_files_path):
        session.log(f"Directory {c_files_path} does not exist, skipping clang-format")
        return

    # Check if there are any C files to format
    c_files = glob.glob(f"{c_files_path}/*.c")
    if not c_files:
        session.log(f"No C files found in {c_files_path}, skipping clang-format")
        return
    session.run("uv", "tool", "run", "clang-format", "-i", *c_files)
    session.run("uv", "tool", "run", "ruff", "format", ".")


@session(dependency_group="dev")
def check(session: Session):
    session.run("uv", "tool", "run", "ruff", "check", ".")


@session(dependency_group="build")
def build(session: Session):
    command = [
        shutil.which("uv"),
        "run",
        "setup.py",
        "build",
    ]
    session.run(*command)
    # copy from ./build to ./src/conditional_method/_lib.c
    shutil.copy(
        "./build/lib.linux-x86_64-cpython-38/_lib.cpython-38-x86_64-linux-gnu.so",
        "./src/conditional_method/_lib.cpython-38-x86_64-linux-gnu.so",
    )


@session(dependency_group="test", default_posargs=["tests/benchmark.py", "-v"])
def benchmark(session: Session):
    session.run(
        "uv",
        "run",
        "--group",
        "test",
        "python",
        "-m",
        "pytest",
    )
