import nox
from nox.sessions import Session


@nox.session
def test(session: Session):
    session.run("pytest")
