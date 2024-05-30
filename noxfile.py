import nox


@nox.session(python=["3.9", "3.10", "3.11", "3.12"])
def tests(session: nox.Session):
    session.install("pytest")
    session.install("-e", ".")
    session.run("pytest", "-v", "tests")


@nox.session
def lint(session: nox.Session):
    session.install("pre-commit")
    session.run(
        "pre-commit",
        "run",
        "--all-files",
    )
