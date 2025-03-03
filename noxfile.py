import nox
from nox.sessions import Session
import shutil

try:
    import tomli as tomllib
except ImportError:
    pass


# export ENVIRONMENT_KEY=staging && uv run --group examples python -m pytest examples/fastapi_auth_staging.py -s -vv
# export ENVIRONMENT_KEY=production && uv run --group examples python -m pytest examples/fastapi_auth_prod.py -s -vv
# export ENVIRONMENT_KEY=development && uv run --group examples python -m pytest examples/fastapi_auth_dev.py -s -vv
# uv run --group examples python -m pytest examples/fastapi_auth.py -s -vv
# uv run --group test python -m pytest tests -s -vv
# uv tool run ruff format .
# uv tool run ruff check . --fix


@nox.session
def test(session: Session):
    command = [
        shutil.which("uv"),
        "run",
        "--group",
        "test",
        "python",
        "-m",
        "pytest",
        "tests",
        "-s",
        "-vv",
    ]
    session.run(*command)


@nox.session
def scratchpad(session: Session):
    command = [
        shutil.which("uv"),
        "run",
        "--group",
        "examples",
        "examples/scratchpad.py",
        "-s",
        "-vv",
    ]
    session.run(*command)


@nox.session
def test_staging(session: Session):
    session.run("pytest", "examples/fastapi_auth_staging.py", "-s", "-vv")


@nox.session
def test_production(session: Session):
    session.run("pytest", "examples/fastapi_auth_prod.py", "-s", "-vv")


@nox.session
def test_development(session: Session):
    session.run("pytest", "examples/fastapi_auth_dev.py", "-s", "-vv")


@nox.session
def format(session: Session):
    session.run("uv", "tool", "run", "ruff", "format", ".")


@nox.session
def check(session: Session):
    session.run("uv", "tool", "run", "ruff", "check", ".")


@nox.session
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


@nox.session
def benchmark(session: Session):
    session.run("pytest", "tests/benchmark.py", "-v")
