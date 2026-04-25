import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True


@nox.session(python="3.11", tags=["tests"])
def tests(session: nox.Session):
    session.run_install(
        "uv",
        "sync",
        "--group",
        "test",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )
    session.run("pytest", *session.posargs)


@nox.session(python="3.11", tags=["lint"])
def lint(session: nox.Session):
    session.run_install("uv", "pip", "install", "ruff")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session(python="3.11", tags=["style"])
def style(session: nox.Session):
    session.run_install("uv", "pip", "install", "ruff")
    session.run("ruff", "check", "--fix", ".")
    session.run("ruff", "format", ".")
