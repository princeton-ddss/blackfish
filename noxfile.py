import nox


nox.options.default_venv_backend = "uv|virtualenv"


@nox.session(python=["3.12"])
def tests(session: nox.Session) -> None:
    session.install("pytest")
    session.install("-e", ".")
    session.run("pytest", "-v", "tests")


@nox.session(python=["3.12"])
def lint(session: nox.Session) -> None:
    session.install("pre-commit")
    session.run(
        "pre-commit",
        "run",
        "--all-files",
        "--show-diff-on-failure",
    )
