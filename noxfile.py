import nox


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"])
def tests(session: nox.Session):
    session.install("pytest")
    session.install("-e", ".[tox_to_nox]")
    session.run("pytest", "tests")


@nox.session
def lint(session: nox.Session):
    session.install("pre-commit")
    session.run(
        "pre-commit",
        "run",
        "--all-files",
    )
