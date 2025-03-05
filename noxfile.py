from functools import wraps
import contextlib
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
    from typing_extensions import ParamSpec
    from nox.sessions import Func

    P = ParamSpec("P")

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
    ) -> Callable[[], Any]: ...

    @overload
    def session(
        f: None = None,
        /,
        dependency_group: str = None,
        environment_mapping: "Dict[str, str]" = {},
        default_posargs: "Sequence[str]" = (),
        **kwargs: NoxSessionParams,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...


DEFAULT_SESSION_KWARGS: "NoxSessionParams" = {
    "reuse_venv": True,  # probably want to reuse it so that you don't keep recreating it
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
        env: "Dict[str, str]" = kwargs.pop("env", {})
        env.update(self.environment_mapping)
        kwargs["env"] = env
        return self.session.run(*args, **kwargs)


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
    f_name = f.__name__.replace("_", "-")
    nox_session_kwargs = {
        **DEFAULT_SESSION_KWARGS,
        **kwargs,
    }
    nox_session_kwargs["name"] = f_name

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
def test(session: AlteredSession):
    command = [
        shutil.which("uv"),
        "run",
        "--group",
        "test",
        "python",
        "-m",
        "pytest",
        # by default will run all tests, e.g. appending `tests -s -vv` to the command
        # but you can also run a single test file, e.g. `nox -s test -- tests/test_cfg.py -s -vv`
        # override the default by appending different `-- <args>` to `nox -s test`
        # save you some time from writing different nox sessions
    ]
    if "--build" in session.posargs:
        session.posargs.remove("--build")
        with alter_session(session, dependency_group="build"):
            build(session)
    session.run(*command)


@contextlib.contextmanager
def alter_session(
    session: AlteredSession,
    dependency_group: str = None,
    environment_mapping: "Dict[str, str]" = {},
    default_posargs: "Sequence[str]" = (),
    **kwargs: "NoxSessionParams",
):
    old_dependency_group = session.dependency_group
    old_environment_mapping = session.environment_mapping
    old_default_posargs = session.default_posargs
    old_kwargs = {}
    for key, value in kwargs.items():
        old_kwargs[key] = getattr(session, key)

    session.dependency_group = dependency_group
    session.environment_mapping = environment_mapping
    session.default_posargs = default_posargs
    for key, value in kwargs.items():
        setattr(session, key, value)
    yield session

    session.dependency_group = old_dependency_group
    session.environment_mapping = old_environment_mapping
    session.default_posargs = old_default_posargs
    for key, value in old_kwargs.items():
        setattr(session, key, value)


@session(
    dependency_group="dev",
)
def clean(session: Session):
    session.run("uv", "clean")
    session.run("rm", "-rf", "build", "dist", "*.egg-info")

@session(
    dependency_group="examples",
)
def fastapi_auth(session: Session):
    test_development(session)
    # test the staging environment
    # change the environment key to "staging"
    with alter_session(session, environment_mapping={"ENVIRONMENT_KEY": "staging"}):
        test_staging(session)
    # test the production environment
    # change the environment key to "production"
    with alter_session(session, environment_mapping={"ENVIRONMENT_KEY": "production"}):
        test_production(session)
    # test the development environment again with the environment key set to "development"
    test_development(session)


@session(
    dependency_group="examples",
    default_posargs=[
        "examples/scratchpad.py",
    ],
)
def scratchpad(session: Session):
    command = [
        shutil.which("uv"),
        "run",
        "--group",
        "examples",
        "python",
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
    # for c extension which is now defuncted
    # command = [
    #     shutil.which("uv"),
    #     "run",
    #     "setup.py",
    #     "build",
    # ]
    # session.run(*command)
    # # copy from ./build to ./src/conditional_method/_lib.c
    # shutil.copy(
    #     "./build/lib.linux-x86_64-cpython-38/_lib.cpython-38-x86_64-linux-gnu.so",
    #     "./src/conditional_method/_lib.cpython-38-x86_64-linux-gnu.so",
    # )
    session.run("uv", "build")


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


@session(dependency_group="dev")
def list_dist_files(session: Session):
    """List all files packaged in the latest distribution."""
    import glob
    import zipfile
    from pathlib import Path
    import os

    # Find the latest wheel file in the dist directory
    wheel_files = sorted(glob.glob("dist/*.whl"), key=os.path.getmtime, reverse=True)
    tarball_files = sorted(
        glob.glob("dist/*.tar.gz"), key=os.path.getmtime, reverse=True
    )

    if not wheel_files and not tarball_files:
        session.error("No distribution files found in dist/ directory")
        return

    # Process wheel file if available
    if wheel_files:
        latest_wheel = wheel_files[0]
        session.log(f"Examining contents of {latest_wheel}")

        # Wheel files are zip files, so we can use zipfile to list contents
        with zipfile.ZipFile(latest_wheel, "r") as wheel:
            file_list = wheel.namelist()

            # Print the files in a readable format
            session.log(f"Contents of {Path(latest_wheel).name}:")
            for file in sorted(file_list):
                session.log(f"  - {file}")

            session.log(f"Total files in wheel: {len(file_list)}")

    # Process tarball file if available
    if tarball_files:
        latest_tarball = tarball_files[0]
        session.log(f"Examining contents of {latest_tarball}")

        # Tarball files can be opened with tarfile
        import tarfile

        with tarfile.open(latest_tarball, "r:gz") as tar:
            file_list = tar.getnames()

            # Print the files in a readable format
            session.log(f"Contents of {Path(latest_tarball).name}:")
            for file in sorted(file_list):
                session.log(f"  - {file}")

            session.log(f"Total files in tarball: {len(file_list)}")


@session(dependency_group="dev", default_posargs=[".", "--check-untyped-defs"])
def type_check(session: Session):
    session.run("uv", "tool", "run", "mypy")
